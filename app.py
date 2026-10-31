import base64
from datetime import datetime, date, timedelta, timezone
import hashlib
import hmac
import json
import math
import random
import pandas as pd
import plotly.express as px
import pyotp
import requests
import streamlit as st
from supabase import create_client

st.set_page_config(
    page_title="Student Academic & Attendance Hub", page_icon="📚", layout="wide"
)

# ---------------------------------------------------------
# DATABASE & SECRETS INITIALIZATION
# ---------------------------------------------------------
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(
        "❌ Missing Secrets! Please configure your connection settings in Streamlit Cloud."
    )
    st.stop()


# Helper function to hash passwords securely
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# Helper function to get current Indian Standard Time (IST)
IST = timezone(timedelta(hours=5, minutes=30))


def get_ist_time():
    return datetime.now(IST)


# Helper function to parse DB timestamps into IST safely
def parse_db_time(iso_str):
    if not iso_str:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is not None:
            return dt.astimezone(timezone.utc)
        else:
            return dt.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


# Helper function to send OTP & Emails via API
def send_otp_email(recipient_email, otp_code):
    try:
        api_key = st.secrets.get("RESEND_API_KEY")
        if not api_key:
            return False

        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "from": "Student Hub <onboarding@resend.dev>",
            "to": [recipient_email],
            "subject": "🔐 Password Reset OTP - Student Academic Hub",
            "html": f"""
            <h3>Student Academic & Attendance Hub</h3>
            <p>You requested a password reset for your account.</p>
            <p>Your 6-digit OTP verification code is: <b style="font-size: 20px; color: #d90429;">{otp_code}</b></p>
            <p>This code is valid for 10 minutes.</p>
            """,
        }

        response = requests.post(url, json=payload, headers=headers, timeout=10)
        return response.status_code in [200, 201]
    except Exception:
        return False


def send_report_email(recipient_email, subject_line, report_html):
    try:
        api_key = st.secrets.get("RESEND_API_KEY")
        if not api_key:
            return False

        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "from": "Student Hub <onboarding@resend.dev>",
            "to": [recipient_email],
            "subject": subject_line,
            "html": report_html,
        }

        response = requests.post(url, json=payload, headers=headers, timeout=10)
        return response.status_code in [200, 201]
    except Exception:
        return False


# ---------------------------------------------------------
# NATIVE SECURE AUTHENTICATION STATE
# ---------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_email = None
    st.session_state.user_name = None

if "reset_step" not in st.session_state:
    st.session_state.reset_step = 1
    st.session_state.reset_email = None

if not st.session_state.authenticated:
    st.title("📚 Student Academic & Attendance Hub")
    st.markdown("### Secure Cloud Login & Registration Portal")

    tab_login, tab_register, tab_forgot = st.tabs(
        ["🔑 Login", "📝 Register New Account", "🔄 Forgot Password"]
    )

    with tab_login:
        with st.form("login_form"):
            login_user = st.text_input("Username")
            login_pass = st.text_input("Password", type="password")
            submit_login = st.form_submit_button("Log In", type="primary")

            if submit_login:
                if not login_user or not login_pass:
                    st.error("Please enter both username and password.")
                else:
                    try:
                        response = (
                            supabase.table("users")
                            .select("*")
                            .eq("username", login_user.strip())
                            .execute()
                        )
                        if response.data:
                            db_user = response.data[0]
                            hashed_input = hash_password(login_pass)
                            if db_user["password_hash"] == hashed_input:
                                st.session_state.authenticated = True
                                st.session_state.user_email = db_user["email"]
                                st.session_state.user_name = db_user["name"]
                                st.success("Login successful! Loading dashboard...")
                                st.rerun()
                            else:
                                st.error("Incorrect password.")
                        else:
                            st.error("Username does not exist.")
                    except Exception as err:
                        st.error(f"Database error during login: {err}")

    with tab_register:
        with st.form("register_form"):
            new_user = st.text_input("Choose Username")
            new_name = st.text_input("Full Name")
            new_email = st.text_input("Email Address")
            new_pass = st.text_input("Password", type="password")
            submit_reg = st.form_submit_button("Sign Up")

            if submit_reg:
                if not new_user or not new_pass or not new_email or not new_name:
                    st.error("Please fill in all fields.")
                else:
                    hashed_pass = hash_password(new_pass)
                    try:
                        supabase.table("users").insert(
                            {
                                "username": new_user.strip(),
                                "name": new_name.strip(),
                                "email": new_email.strip(),
                                "password_hash": hashed_pass,
                            }
                        ).execute()
                        st.success(
                            "Account created successfully! You can now switch to the Login tab."
                        )
                    except Exception as err:
                        st.error(
                            f"Registration failed (Username or Email may already be taken): {err}"
                        )

    with tab_forgot:
        st.markdown("### Reset Your Password via Email OTP")

        if st.session_state.reset_step == 1:
            with st.form("forgot_step1_form"):
                reset_email_input = st.text_input("Enter your Registered Email Address")
                submit_send_otp = st.form_submit_button("Send Verification Code", type="primary")

                if submit_send_otp:
                    if not reset_email_input:
                        st.error("Please enter your email address.")
                    else:
                        try:
                            response = (
                                supabase.table("users")
                                .select("*")
                                .eq("email", reset_email_input.strip())
                                .execute()
                            )
                            if response.data:
                                db_user = response.data[0]
                                user_email_db = db_user["email"]
                                
                                otp = str(random.randint(100000, 999999))
                                expiry = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
                                
                                supabase.table("users").update({
                                    "reset_otp": otp,
                                    "otp_expiry": expiry
                                }).eq("email", user_email_db).execute()

                                email_sent = send_otp_email(user_email_db, otp)
                                if email_sent:
                                    st.session_state.reset_step = 2
                                    st.session_state.reset_email = user_email_db
                                    masked_email = user_email_db[:3] + "****" + user_email_db[user_email_db.find("@"):]
                                    st.success(f"Verification code sent to registered email: {masked_email}")
                                    st.rerun()
                                else:
                                    st.error("Failed to send verification email. Please try again.")
                            else:
                                st.error("No account found with this email address.")
                        except Exception as err:
                            st.error(f"Database error: {err}")

        elif st.session_state.reset_step == 2:
            with st.form("forgot_step2_form"):
                st.info(f"Resetting password for email: **{st.session_state.reset_email}**")
                entered_otp = st.text_input("Enter 6-digit OTP Code")
                new_reset_pass = st.text_input("New Password", type="password")
                confirm_reset_pass = st.text_input("Confirm New Password", type="password")
                
                col_sub, col_back = st.columns(2)
                with col_sub:
                    submit_verify = st.form_submit_button("Verify & Update Password", type="primary")
                with col_back:
                    submit_cancel = st.form_submit_button("Cancel / Start Over")

                if submit_cancel:
                    st.session_state.reset_step = 1
                    st.session_state.reset_email = None
                    st.rerun()

                if submit_verify:
                    if not entered_otp or not new_reset_pass or not confirm_reset_pass:
                        st.error("Please fill in all fields.")
                    elif new_reset_pass != confirm_reset_pass:
                        st.error("New passwords do not match.")
                    else:
                        try:
                            res = supabase.table("users").select("*").eq("email", st.session_state.reset_email).execute()
                            if res.data:
                                u_data = res.data[0]
                                db_otp = u_data.get("reset_otp")
                                db_expiry = u_data.get("otp_expiry")
                                
                                now = datetime.now(timezone.utc)
                                expiry_time = datetime.fromisoformat(db_expiry) if db_expiry else now

                                if entered_otp.strip() != str(db_otp):
                                    st.error("Invalid OTP code.")
                                elif now > expiry_time:
                                    st.error("OTP has expired. Please request a new one.")
                                else:
                                    new_hashed_pass = hash_password(new_reset_pass)
                                    supabase.table("users").update({
                                        "password_hash": new_hashed_pass,
                                        "reset_otp": None,
                                        "otp_expiry": None
                                    }).eq("email", st.session_state.reset_email).execute()
                                    
                                    st.success("Password successfully updated! You can now log in.")
                                    st.session_state.reset_step = 1
                                    st.session_state.reset_email = None
                            else:
                                st.error("User not found.")
                        except Exception as err:
                            st.error(f"Database error during update: {err}")

    st.stop()

# If successfully authenticated:
user_email = st.session_state.user_email
user_name = st.session_state.user_name

# Update presence heartbeat (using UTC time)
try:
    supabase.table("users").update({"last_seen": datetime.now(timezone.utc).isoformat()}).eq("email", user_email).execute()
except Exception:
    pass

# Custom CSS for Neon Glowing Buttons & UI Polish
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background-color: #0e1117;
        padding-top: 1rem;
    }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child(6) button {
        width: 100%; border-radius: 12px; font-weight: 700; font-size: 15px; padding: 12px 15px;
        color: white !important; background: linear-gradient(135deg, #a00037, #d90429) !important;
        border: 3px solid #ffb703 !important; box-shadow: 0 0 15px #ffb703, inset 0 0 10px rgba(255, 255, 255, 0.2) !important;
    }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child(7) button {
        width: 100%; border-radius: 12px; font-weight: 700; font-size: 15px; padding: 12px 15px;
        color: white !important; background: linear-gradient(135deg, #1b4332, #2d6a4f) !important;
        border: 3px solid #ffb703 !important; box-shadow: 0 0 15px #ffb703, inset 0 0 10px rgba(255, 255, 255, 0.2) !important;
    }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child(8) button {
        width: 100%; border-radius: 12px; font-weight: 700; font-size: 15px; padding: 12px 15px;
        color: white !important; background: linear-gradient(135deg, #03045e, #0077b6) !important;
        border: 3px solid #ffb703 !important; box-shadow: 0 0 15px #ffb703, inset 0 0 10px rgba(255, 255, 255, 0.2) !important;
    }
    [data-testid="stSidebar"] div.stButton button:hover { transform: scale(1.02); }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# CLOUD DATABASE HELPER FUNCTIONS
# ---------------------------------------------------------
def load_data_from_db(email):
    try:
        response = (
            supabase.table("student_attendance")
            .select("*")
            .eq("user_email", email)
            .execute()
        )
        sem_data = {f"Semester {i}": [] for i in range(1, 9)}
        for row in response.data:
            sem_data[row["semester"]] = row["subjects_json"]
        return sem_data
    except Exception:
        return {f"Semester {i}": [] for i in range(1, 9)}


def save_data_to_db(email, semester, subjects_list):
    supabase.table("student_attendance").upsert(
        {
            "user_email": email,
            "semester": semester,
            "subjects_json": subjects_list,
        },
        on_conflict="user_email,semester",
    ).execute()


def load_locks_from_db(email):
    try:
        response = (
            supabase.table("semester_locks")
            .select("*")
            .eq("user_email", email)
            .execute()
        )
        locks = {f"Semester {i}": False for i in range(1, 9)}
        for row in response.data:
            locks[row["semester"]] = row["is_locked"]
        return locks
    except Exception:
        return {f"Semester {i}": False for i in range(1, 9)}


def save_lock_to_db(email, semester, is_locked):
    supabase.table("semester_locks").upsert(
        {
            "user_email": email,
            "semester": semester,
            "is_locked": is_locked,
        },
        on_conflict="user_email,semester",
    ).execute()


# Helpers for Assignments & Exams
def load_assignments_from_db(email, semester):
    try:
        resp = supabase.table("student_assignments").select("*").eq("user_email", email).eq("semester", semester).execute()
        return resp.data if resp.data else []
    except Exception:
        return []


def save_assignment_to_db(email, semester, subject_code, title, due_date_str, file_url=None):
    try:
        supabase.table("student_assignments").insert({
            "user_email": email,
            "semester": semester,
            "subject_code": subject_code,
            "title": title,
            "due_date": due_date_str,
            "file_url": file_url
        }).execute()
    except Exception as e:
        st.error(f"Error saving assignment: {e}")


def load_exams_from_db(email, semester):
    try:
        resp = supabase.table("student_exams").select("*").eq("user_email", email).eq("semester", semester).execute()
        return resp.data if resp.data else []
    except Exception:
        return []


def save_exam_to_db(email, semester, subject_code, exam_type, exam_date_str, syllabus):
    try:
        supabase.table("student_exams").insert({
            "user_email": email,
            "semester": semester,
            "subject_code": subject_code,
            "exam_type": exam_type,
            "exam_date": exam_date_str,
            "syllabus": syllabus
        }).execute()
    except Exception as e:
        st.error(f"Error saving exam: {e}")


# Helpers for Timetable
def load_timetable_from_db(email, semester):
    try:
        resp = supabase.table("student_timetables").select("*").eq("user_email", email).eq("semester", semester).execute()
        return resp.data if resp.data else []
    except Exception:
        return []


def save_timetable_to_db(email, semester, day_of_week, subject_code, start_time_str, end_time_str, room_number):
    try:
        supabase.table("student_timetables").insert({
            "user_email": email,
            "semester": semester,
            "day_of_week": day_of_week,
            "subject_code": subject_code,
            "start_time": start_time_str,
            "end_time": end_time_str,
            "room_number": room_number
        }).execute()
    except Exception as e:
        st.error(f"Error saving timetable entry: {e}")


# ---------------------------------------------------------
# MAIN APPLICATION INTERFACE
# ---------------------------------------------------------
st.title("📚 Student Academic & Attendance Hub")

if st.sidebar.button("🚪 Logout", key="logout_btn"):
    st.session_state.authenticated = False
    st.session_state.user_email = None
    st.session_state.user_name = None
    st.session_state.admin_unlocked = False
    st.session_state.show_admin_login = False
    st.rerun()

st.sidebar.markdown(f"Welcome, **{user_name}**!")

# Check for Admin Messages directed to this user
try:
    msg_resp = supabase.table("admin_messages").select("*").execute()
    if msg_resp.data:
        for msg in msg_resp.data:
            t_email = msg.get("target_email")
            read_list = msg.get("read_by") if msg.get("read_by") else []
            if (t_email == "ALL" or t_email == user_email) and user_email not in read_list:
                st.info(f"📢 **ADMIN ANNOUNCEMENT:** {msg['message_text']}")
                if st.button("✅ Mark as Read & Clear", key=f"read_msg_{msg['id']}"):
                    read_list.append(user_email)
                    supabase.table("admin_messages").update({"read_by": read_list}).eq("id", msg['id']).execute()
                    st.rerun()
except Exception:
    pass

# ---------------------------------------------------------
# SECURE ADMIN PANEL & GOOGLE AUTHENTICATOR GATE
# ---------------------------------------------------------
admin_email_secret = st.secrets.get("admin_email", "")
is_admin = admin_email_secret and user_email == admin_email_secret

if "admin_unlocked" not in st.session_state:
    st.session_state.admin_unlocked = False
if "show_admin_login" not in st.session_state:
    st.session_state.show_admin_login = False

if is_admin:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🕵️ Admin Controls")
    if not st.session_state.admin_unlocked:
        if st.sidebar.button("🔐 Enter Admin Mode", type="primary"):
            st.session_state.show_admin_login = True
            st.rerun()
        admin_mode = False
    else:
        if st.sidebar.button("🔒 Lock Admin Mode"):
            st.session_state.admin_unlocked = False
            st.session_state.show_admin_login = False
            st.rerun()
        admin_mode = True
else:
    admin_mode = False

# Screen Takeover for Google Authenticator prompt
if is_admin and st.session_state.show_admin_login and not st.session_state.admin_unlocked:
    st.title("🔐 Secure Admin Authentication")
    st.markdown("Please enter your **Google Authenticator 6-digit code** to access the System Administrator Dashboard.")
    
    with st.form("admin_totp_verify_form"):
        totp_input = st.text_input("6-Digit Authenticator Code", max_chars=6, type="default")
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            submit_verify = st.form_submit_button("Verify & Unlock", type="primary")
        with col_v2:
            submit_cancel = st.form_submit_button("Cancel / Return")

        if submit_cancel:
            st.session_state.show_admin_login = False
            st.rerun()

        if submit_verify:
            totp_secret = st.secrets.get("admin_totp_secret", "")
            if not totp_secret:
                st.error("❌ `admin_totp_secret` is missing from your Streamlit secrets configuration.")
            else:
                totp = pyotp.TOTP(totp_secret)
                if totp.verify(totp_input.strip()):
                    st.session_state.admin_unlocked = True
                    st.session_state.show_admin_login = False
                    st.success("Authentication successful! Unlocking admin dashboard...")
                    st.rerun()
                else:
                    st.error("❌ Invalid Authenticator code. Please try again.")
    st.stop()

if is_admin and admin_mode:
    st.header("🕵️ System Administrator Dashboard")
    st.markdown("Monitor user activity, broadcast announcements, manage locked records, and inspect reports.")

    try:
        users_resp = supabase.table("users").select("username, name, email, last_seen").execute()
        att_resp = supabase.table("student_attendance").select("*").execute()
        locks_resp = supabase.table("semester_locks").select("*").execute()

        users_list = users_resp.data if users_resp.data else []
        att_list = att_resp.data if att_resp.data else []
        locks_list = locks_resp.data if locks_resp.data else []

        c_stat1, c_stat2, c_stat3 = st.columns(3)
        with c_stat1:
            st.metric("Total Registered Users", len(users_list))
        with c_stat2:
            st.metric("Active Semester Records", len(att_list))
        with c_stat3:
            locked_count = len([l for l in locks_list if l.get("is_locked")])
            st.metric("Locked Semesters", locked_count)

        # ---------------------------------------------------------
        # MASTER SYSTEM BACKUP FEATURE
        # ---------------------------------------------------------
        st.markdown("---")
        st.subheader("💾 Master System Backup & Data Redundancy")
        st.markdown("Download a complete, single JSON backup file containing all user accounts, attendance records, locks, assignments, exams, timetables, and broadcast messages.")

        if st.button("📥 DOWNLOAD FULL SYSTEM BACKUP (JSON)", type="primary"):
            try:
                backup_data = {
                    "backup_timestamp": datetime.now(timezone.utc).isoformat(),
                    "users": supabase.table("users").select("*").execute().data,
                    "student_attendance": supabase.table("student_attendance").select("*").execute().data,
                    "semester_locks": supabase.table("semester_locks").select("*").execute().data,
                    "student_assignments": supabase.table("student_assignments").select("*").execute().data,
                    "student_exams": supabase.table("student_exams").select("*").execute().data,
                    "student_timetables": supabase.table("student_timetables").select("*").execute().data,
                    "admin_messages": supabase.table("admin_messages").select("*").execute().data,
                }
                
                json_string = json.dumps(backup_data, indent=4, default=str)
                file_name = f"student_hub_full_backup_{date.today()}.json"

                st.download_button(
                    label="💾 Click Here to Save Backup File to Computer",
                    data=json_string,
                    file_name=file_name,
                    mime="application/json",
                    type="primary"
                )
                st.success("✅ Backup generated successfully! Click the button above to save the file.")
            except Exception as backup_err:
                st.error(f"❌ Failed to generate system backup: {backup_err}")

        # ---------------------------------------------------------
        # STEALTH ADMIN SUMMARY DISPATCHER
        # ---------------------------------------------------------
        st.markdown("---")
        st.subheader("🕵️‍♂️ Stealth User Summary Dispatcher")
        st.markdown("Quietly compile and dispatch any student's academic performance report directly to your admin email address without notifying the user.")

        if users_list:
            all_user_emails = [u["email"] for u in users_list]
            with st.form("stealth_dispatch_form"):
                col_sd1, col_sd2 = st.columns(2)
                with col_sd1:
                    stealth_target_email = st.selectbox("Select Target User", options=all_user_emails)
                with col_sd2:
                    stealth_target_sem = st.selectbox("Select Semester", options=[f"Semester {i}" for i in range(1, 9)])
                
                submit_stealth = st.form_submit_button("🚀 Dispatch Stealth Report to My Email", type="primary")

                if submit_stealth:
                    try:
                        # Fetch target user's details
                        t_user_resp = supabase.table("users").select("name").eq("email", stealth_target_email).execute()
                        t_name = t_user_resp.data[0]["name"] if t_user_resp.data else "Unknown Student"

                        # Fetch target user's attendance/subjects for that semester
                        t_att_resp = supabase.table("student_attendance").select("*").eq("user_email", stealth_target_email).eq("semester", stealth_target_sem).execute()
                        
                        subjects = t_att_resp.data[0]["subjects_json"] if t_att_resp.data and t_att_resp.data[0].get("subjects_json") else []

                        if not subjects:
                            st.warning(f"No subject data found for {stealth_target_email} in {stealth_target_sem}.")
                        else:
                            # Calculate SGPA & rows
                            weighted_gp = 0.0
                            total_cred = 0
                            rows_html = ""

                            for subj in subjects:
                                att = subj["attended"]
                                cond = subj["conducted"]
                                gp = subj.get("grade_point", 0.0)
                                cred = subj["credits"]
                                pct = (att / cond * 100) if cond > 0 else 0.0
                                
                                weighted_gp += cred * gp
                                total_cred += cred

                                rows_html += f"""
                                <tr>
                                    <td style="padding: 8px; border: 1px solid #ddd;">{subj['code']}</td>
                                    <td style="padding: 8px; border: 1px solid #ddd;">{subj['name']}</td>
                                    <td style="padding: 8px; border: 1px solid #ddd;">{round(pct, 2)}% ({att}/{cond})</td>
                                    <td style="padding: 8px; border: 1px solid #ddd;">{gp}</td>
                                </tr>
                                """

                            target_sgpa = (weighted_gp / total_cred) if total_cred > 0 else 0.0

                            stealth_html_body = f"""
                            <div style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: auto; padding: 20px; border: 2px dashed #d90429; border-radius: 10px;">
                                <h3 style="color: #d90429; text-align: center;">🕵️‍♂️ STEALTH ADMIN REPORT DISPATCH</h3>
                                <p><b>Student Name:</b> {t_name} ({stealth_target_email})</p>
                                <p><b>Semester:</b> {stealth_target_sem}</p>
                                <p><b>Calculated SGPA:</b> {target_sgpa:.2f} / 10.0</p>
                                
                                <h4 style="margin-top: 15px;">Subject Breakdown:</h4>
                                <table style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: left;">
                                    <thead>
                                        <tr style="background-color: #f8f9fa;">
                                            <th style="padding: 6px; border: 1px solid #ddd;">Code</th>
                                            <th style="padding: 6px; border: 1px solid #ddd;">Subject</th>
                                            <th style="padding: 6px; border: 1px solid #ddd;">Attendance</th>
                                            <th style="padding: 6px; border: 1px solid #ddd;">Grade</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {rows_html}
                                    </tbody>
                                </table>
                                <p style="font-size: 11px; color: #777; margin-top: 15px; text-align: center;">Generated quietly via Admin Stealth Dispatcher.</p>
                            </div>
                            """

                            sent_ok = send_report_email(user_email, f"🕵️‍♂️ Stealth Report: {t_name} ({stealth_target_sem})", stealth_html_body)
                            if sent_ok:
                                st.success(f"✅ Stealth report for **{t_name}** successfully dispatched to your admin email (`{user_email}`)!")
                            else:
                                st.error("Failed to send stealth report email.")
                    except Exception as stealth_err:
                        st.error(f"Error compiling stealth report: {stealth_err}")

        st.markdown("---")
        st.subheader("📢 Direct Messaging & Broadcast Hub")
        st.markdown("Send targeted messages to all students or specific individual accounts with read confirmation tracking.")
        
        all_emails = [u["email"] for u in users_list]
        msg_target = st.selectbox("Select Target Audience", options=["ALL"] + all_emails)
        msg_text = st.text_area("Type Announcement / Message Text")
        
        if st.button("🚀 SEND ANNOUNCEMENT", type="primary"):
            if msg_text.strip():
                supabase.table("admin_messages").insert({
                    "sender_email": user_email,
                    "target_email": msg_target,
                    "message_text": msg_text.strip(),
                    "read_by": []
                }).execute()
                st.success("Message dispatched successfully!")
                st.rerun()
            else:
                st.error("Message text cannot be empty.")

        # Display Message Read Tracker
        try:
            sent_msgs = supabase.table("admin_messages").select("*").execute()
            if sent_msgs.data:
                st.markdown("##### Sent Messages Status Tracker")
                for s_m in sent_msgs.data:
                    readers = ", ".join(s_m.get("read_by", [])) if s_m.get("read_by") else "None yet"
                    st.caption(f"🆔 **Message #{s_m['id']}** to `{s_m['target_email']}`: '{s_m['message_text']}' | **Read by:** {readers}")
        except Exception:
            pass

        st.markdown("---")
        st.subheader("📡 Live Presence Monitor")
        
        if users_list:
            now_utc = datetime.now(timezone.utc)
            for u in users_list:
                u_email = u["email"]
                u_name = u["name"]
                u_last_seen = u.get("last_seen")

                status_label = "🔴 Offline"
                if u_last_seen:
                    try:
                        last_seen_dt = parse_db_time(u_last_seen)
                        diff_sec = (now_utc - last_seen_dt).total_seconds()
                        if 0 <= diff_sec < 20:
                            status_label = "🟢 Online Now"
                        elif diff_sec >= 20:
                            mins = max(1, int(diff_sec / 60))
                            status_label = f"🕒 Last seen {mins}m ago"
                        else:
                            status_label = "🔴 Offline"
                    except Exception:
                        pass

                col_u1, col_u2 = st.columns([3, 2])
                with col_u1:
                    st.markdown(f"**{u_name}** (`{u_email}`)")
                with col_u2:
                    st.write(status_label)

        st.markdown("---")
        st.subheader("🔓 Admin Semester Unlocker")
        if all_emails:
            col_un1, col_un2, col_un3 = st.columns([2, 2, 1])
            with col_un1:
                target_unlock_user = st.selectbox("Select User", options=all_emails, key="unlock_user_sel")
            with col_un2:
                target_unlock_sem = st.selectbox("Select Semester to Unlock", options=[f"Semester {i}" for i in range(1, 9)], key="unlock_sem_sel")
            with col_un3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔓 UNLOCK DATA", type="primary", use_container_width=True):
                    supabase.table("semester_locks").upsert({
                        "user_email": target_unlock_user,
                        "semester": target_unlock_sem,
                        "is_locked": False
                    }, on_conflict="user_email,semester").execute()
                    st.success(f"Successfully unlocked {target_unlock_sem} for {target_unlock_user}!")

    except Exception as err:
        st.error(f"Error loading admin dashboard: {err}")

    st.stop()

# ---------------------------------------------------------
# REGULAR STUDENT NAVIGATION & VIEWS
# ---------------------------------------------------------
st.session_state.sem_locks = load_locks_from_db(user_email)
st.session_state.all_semesters = load_data_from_db(user_email)

st.sidebar.header("Navigation & Settings")
selected_semester = st.sidebar.selectbox(
    "Select Semester", [f"Semester {i}" for i in range(1, 9)]
)

default_target = st.sidebar.slider(
    "Target Attendance Percentage (%)",
    min_value=50.0,
    max_value=95.0,
    value=75.0,
    step=1.0,
)

if selected_semester not in st.session_state.all_semesters:
    st.session_state.all_semesters[selected_semester] = []

is_locked = st.session_state.sem_locks.get(selected_semester, False)
current_subjects = st.session_state.all_semesters[selected_semester]

# TOP-LEVEL MODULE TABS
main_tab_attendance, main_tab_assignments, main_tab_exams, main_tab_timetable = st.tabs([
    "📚 Attendance & SGPA", "📝 Assignments & Tasks", "📅 Exams & Time Table", "⏰ Daily Timetable"
])

# =========================================================
# TAB 1: ATTENDANCE & SGPA MANAGEMENT
# =========================================================
with main_tab_attendance:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Attendance Menu")

    if "nav_mode" not in st.session_state:
        st.session_state.nav_mode = "Data Entry & Management"

    if st.sidebar.button("📝 ENTER DETAILS", key="nav_enter"):
        st.session_state.nav_mode = "Data Entry & Management"
        st.rerun()

    if st.sidebar.button("🔄 UPDATE", key="nav_update"):
        st.session_state.nav_mode = "Update Records"
        st.rerun()

    if st.sidebar.button("📊 CALCULATE", key="nav_calc"):
        st.session_state.nav_mode = "Calculation Dashboard"
        st.rerun()

    nav_mode = st.session_state.nav_mode

    if nav_mode == "Data Entry & Management":
        st.header(f"📌 Add Subjects: {selected_semester}")

        if is_locked:
            st.warning(f"🔒 {selected_semester} is permanently fixed/locked. No further modifications can be made.")
        else:
            st.markdown(f"Register your subjects, credits, and current attendance stats for **{selected_semester}**.")

            with st.form(f"add_subject_form_{selected_semester}", clear_on_submit=True):
                st.subheader("New Subject Registration")
                col1, col2, col3, col4, col5, col6 = st.columns([2, 3, 1, 1, 1, 1])
                with col1:
                    new_code = st.text_input("Subject Code", placeholder="e.g. TCS-401")
                with col2:
                    new_name = st.text_input("Subject Name", placeholder="e.g. Operating Systems")
                with col3:
                    new_credits = st.number_input("Credits", min_value=1, max_value=10, value=3, step=1)
                with col4:
                    new_attended = st.number_input("Attended", min_value=0, value=0, step=1)
                with col5:
                    new_conducted = st.number_input("Conducted", min_value=0, value=0, step=1)
                with col6:
                    st.markdown("<br>", unsafe_allow_html=True)
                    add_btn = st.form_submit_button("Add")

                if add_btn:
                    if new_code.strip() == "" or new_name.strip() == "":
                        st.error("Please enter both Subject Code and Name.")
                    elif new_attended > new_conducted:
                        st.error("Attended classes cannot exceed conducted classes.")
                    else:
                        current_subjects.append({
                            "code": new_code.upper(),
                            "name": new_name,
                            "credits": int(new_credits),
                            "attended": int(new_attended),
                            "conducted": int(new_conducted),
                            "grade_point": 0.0,
                            "attendance_date": str(date.today()),
                        })
                        st.session_state.all_semesters[selected_semester] = current_subjects
                        save_data_to_db(user_email, selected_semester, current_subjects)
                        st.success(f"Added {new_code} - {new_name} successfully!")
                        st.rerun()

        if current_subjects:
            st.markdown("---")
            st.subheader(f"Currently Registered Subjects ({selected_semester})")
            for idx, subj in enumerate(current_subjects, 1):
                att_date = subj.get("attendance_date", str(date.today()))
                st.markdown(f"{idx}. **[{subj['code']}] {subj['name']}** (Credits: {subj['credits']}, Attended: {subj['attended']}/{subj['conducted']}, Grade Point: {subj['grade_point']}, Last Updated: `{att_date}`)")
        else:
            st.info(f"No subjects added for {selected_semester} yet.")

    elif nav_mode == "Update Records":
        st.header(f"🔄 Update Records: {selected_semester}")

        if is_locked:
            st.warning(f"🔒 {selected_semester} is permanently fixed/locked. Records cannot be updated.")
            if current_subjects:
                st.markdown("---")
                st.subheader(f"Locked Records ({selected_semester})")
                for idx, subj in enumerate(current_subjects, 1):
                    att_date = subj.get("attendance_date", str(date.today()))
                    st.markdown(f"{idx}. **[{subj['code']}] {subj['name']}** | Grade Point: **{subj['grade_point']}** | Attended: {subj['attended']}/{subj['conducted']} | Last Updated: `{att_date}`")
        else:
            st.markdown(f"Update your attendance or final grade points for **{selected_semester}**.")

            if current_subjects:
                updated_subjects = []
                data_changed = False

                @st.dialog("⚠️ Confirm Subject Deletion")
                def confirm_delete_dialog(sem_name, sub_index, sub_code, sub_name, subjects_list):
                    st.markdown(f"Are you sure you want to delete **[{sub_code}] {sub_name}** from `{sem_name}`?")
                    col_y, col_n = st.columns(2)
                    with col_y:
                        if st.button("🗑️ Yes, Delete", type="primary", use_container_width=True):
                            subjects_list.pop(sub_index)
                            st.session_state.all_semesters[sem_name] = subjects_list
                            save_data_to_db(user_email, sem_name, subjects_list)
                            st.success(f"Deleted {sub_code} successfully!")
                            st.rerun()
                    with col_n:
                        if st.button("❌ Cancel", use_container_width=True):
                            st.rerun()

                for i, subj in enumerate(current_subjects):
                    existing_date_str = subj.get("attendance_date", str(date.today()))

                    with st.expander(f"📖 [{subj['code']}] {subj['name']} (Credits: {subj['credits']} | Last Updated: {existing_date_str})"):
                        col_del, _ = st.columns([1, 4])
                        with col_del:
                            if st.button("🗑️ Delete", key=f"del_{selected_semester}_{i}"):
                                confirm_delete_dialog(selected_semester, i, subj["code"], subj["name"], current_subjects)

                        c1, c2, c3 = st.columns(3)
                        with c1:
                            code = st.text_input("Subject Code", value=subj["code"], key=f"code_{selected_semester}_{i}")
                        with c2:
                            name = st.text_input("Subject Name", value=subj["name"], key=f"name_{selected_semester}_{i}")
                        with c3:
                            credits = st.number_input("Credits", min_value=1, max_value=10, value=int(subj["credits"]), key=f"cred_{selected_semester}_{i}")

                        c4, c5, c6 = st.columns(3)
                        with c4:
                            attended = st.number_input("Classes Attended", min_value=0, value=int(subj["attended"]), key=f"att_{selected_semester}_{i}")
                        with c5:
                            conducted = st.number_input("Classes Conducted", min_value=0, value=max(int(subj["conducted"]), attended), key=f"cond_{selected_semester}_{i}")
                        with c6:
                            endterm = st.number_input("Final Grade Point (0-10)", min_value=0.0, max_value=10.0, value=float(subj.get("grade_point", 0.0)), step=0.5, key=f"gp_{selected_semester}_{i}")

                        field_changed = (
                            code.upper() != subj["code"]
                            or name != subj["name"]
                            or credits != subj["credits"]
                            or attended != subj["attended"]
                            or conducted != subj["conducted"]
                            or endterm != subj.get("grade_point", 0.0)
                        )
                        final_date = str(date.today()) if field_changed else existing_date_str

                        updated_subjects.append({
                            "code": code.upper(),
                            "name": name,
                            "credits": credits,
                            "attended": attended,
                            "conducted": conducted,
                            "grade_point": endterm,
                            "attendance_date": final_date,
                        })

                if updated_subjects != current_subjects:
                    data_changed = True

                st.session_state.all_semesters[selected_semester] = updated_subjects
                if data_changed:
                    save_data_to_db(user_email, selected_semester, updated_subjects)
                    st.success("Records updated successfully!")
                    st.rerun()
            else:
                st.info(f"No subjects found for {selected_semester}. Please add subjects first.")

    elif nav_mode == "Calculation Dashboard":
        st.header(f"📊 Calculation & Analytics Dashboard ({selected_semester})")

        overall_weighted_gp = 0.0
        overall_credits = 0
        has_any_subjects = False

        for sem, subj_list in st.session_state.all_semesters.items():
            if subj_list:
                has_any_subjects = True
                for s in subj_list:
                    overall_weighted_gp += s["credits"] * s.get("grade_point", 0.0)
                    overall_credits += s["credits"]

        if not has_any_subjects:
            st.warning("No subjects found in any semester. Please add subjects first.")
        else:
            cgpa = (overall_weighted_gp / overall_credits) if overall_credits > 0 else 0.0
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.metric(label="Overall CGPA (All Semesters)", value=f"{cgpa:.2f} / 10.0")

            st.markdown("---")
            sem_subjects = current_subjects

            if sem_subjects:
                att_data = []
                sem_weighted_gp = 0.0
                sem_credits = 0
                all_grades_entered = True

                for idx, subj in enumerate(sem_subjects, 1):
                    if subj["grade_point"] <= 0.0:
                        all_grades_entered = False

                    att = subj["attended"]
                    cond = subj["conducted"]
                    att_date = subj.get("attendance_date", str(date.today()))
                    pct = (att / cond * 100) if cond > 0 else 0.0

                    if pct >= default_target:
                        max_skips = max(0, math.floor((100 * att - default_target * cond) / default_target))
                        current_status = f"Safe (Can skip {max_skips})"
                    else:
                        needed_consecutive = math.ceil((default_target * cond - 100 * att) / (100.0 - default_target))
                        current_status = f"Short (Need next {max(1, needed_consecutive)})"

                    att_data.append({
                        "S.No.": idx,
                        "Code": subj["code"],
                        "Subject": subj["name"],
                        "Credits": subj["credits"],
                        "Attended": att,
                        "Conducted": cond,
                        "Percentage": round(pct, 2),
                        "Current Status": current_status,
                        "Grade Point": subj["grade_point"],
                        "Last Updated": att_date,
                    })

                    sem_weighted_gp += subj["credits"] * subj["grade_point"]
                    sem_credits += subj["credits"]

                df = pd.DataFrame(att_data)
                df.set_index("S.No.", inplace=True)
                sgpa = (sem_weighted_gp / sem_credits) if sem_credits > 0 else 0.0

                st.markdown("---")
                st.subheader(f"📌 Academic Performance & SGPA ({selected_semester})")
                st.metric(label=f"Current {selected_semester} SGPA", value=f"{sgpa:.2f} / 10.0")

                st.markdown("---")
                st.subheader("📋 Attendance & Exam Summary Table")
                st.dataframe(df, use_container_width=True)

                st.markdown("---")
                st.subheader("Attendance Percentage vs Target")
                fig_bar = px.bar(
                    df.reset_index(),
                    x="Code",
                    y="Percentage",
                    text="Percentage",
                    color="Percentage",
                    color_continuous_scale="RdYlGn",
                    range_y=[0, 100],
                )
                fig_bar.add_hline(
                    y=default_target,
                    line_dash="dash",
                    line_color="red",
                    annotation_text=f"Target ({default_target}%)",
                    annotation_position="top right",
                )
                fig_bar.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
                st.plotly_chart(fig_bar, use_container_width=True)

                # Email Dispatcher Hub
                st.markdown("---")
                st.subheader("📧 Email Report Dispatcher")
                st.markdown(f"Dispatch your complete academic performance report for **{selected_semester}** directly to your registered email (`{user_email}`).")

                if st.button("🚀 DISPATCH REPORT TO MY EMAIL", type="primary", use_container_width=True):
                    subject_text = f"📊 Academic Report - {selected_semester}"
                    rows_html = ""
                    for idx, row in df.iterrows():
                        rows_html += f"""
                        <tr>
                            <td style="padding: 8px; border: 1px solid #ddd;">{row['Code']}</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{row['Subject']}</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{row['Percentage']}%</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{row['Current Status']}</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{row['Grade Point']}</td>
                        </tr>
                        """

                    html_body = f"""
                    <div style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 10px;">
                        <h2 style="color: #d90429; text-align: center;">🎓 Student Academic & Attendance Hub</h2>
                        <hr style="border: none; border-top: 1px solid #eee;" />
                        <p>Hello <b>{user_name}</b>,</p>
                        <p>Here is your official academic performance report for <b>{selected_semester}</b>:</p>
                        
                        <ul style="list-style: none; padding: 0;">
                            <li>📅 <b>Semester:</b> {selected_semester}</li>
                            <li>📊 <b>Current SGPA:</b> {sgpa:.2f} / 10.0</li>
                            <li>🏆 <b>Overall CGPA:</b> {cgpa:.2f} / 10.0</li>
                            <li>🎯 <b>Target Attendance:</b> {default_target}%</li>
                        </ul>

                        <h3 style="margin-top: 20px;">Subject Breakdown</h3>
                        <table style="width: 100%; border-collapse: collapse; font-size: 14px; text-align: left;">
                            <thead>
                                <tr style="background-color: #f8f9fa;">
                                    <th style="padding: 8px; border: 1px solid #ddd;">Code</th>
                                    <th style="padding: 8px; border: 1px solid #ddd;">Subject</th>
                                    <th style="padding: 8px; border: 1px solid #ddd;">Attendance</th>
                                    <th style="padding: 8px; border: 1px solid #ddd;">Status</th>
                                    <th style="padding: 8px; border: 1px solid #ddd;">Grade</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows_html}
                            </tbody>
                        </table>
                    </div>
                    """

                    sent = send_report_email(user_email, subject_text, html_body)
                    if sent:
                        st.success(f"Successfully sent the report to **{user_email}**!")
                    else:
                        st.error("Failed to send email. Please check your configuration.")

                # Semester Fixation
                st.markdown("---")
                st.subheader(f"🔒 Semester Fixation ({selected_semester})")

                @st.dialog("⚠️ Confirm Permanent Fixation")
                def confirm_fix_dialog(sem_name):
                    st.markdown(f"Are you sure you want to **permanently lock {sem_name}**?")
                    col_c1, col_c2 = st.columns(2)
                    with col_c1:
                        if st.button("✅ Yes, Lock Permanently", use_container_width=True):
                            st.session_state.sem_locks[sem_name] = True
                            save_lock_to_db(user_email, sem_name, True)
                            st.success(f"{sem_name} has been permanently locked!")
                            st.rerun()
                    with col_c2:
                        if st.button("❌ Cancel", use_container_width=True):
                            st.rerun()

                if is_locked:
                    st.success(f"🔒 Status: {selected_semester} is permanently fixed and locked.")
                else:
                    if not all_grades_entered:
                        st.info("ℹ️ The **FIX** button will become available once final grade points (> 0.0) are entered for all subjects.")
                        st.button("🔒 FIX SEMESTER DATA", disabled=True, use_container_width=True)
                    else:
                        if st.button("🔒 FIX SEMESTER DATA", type="primary", use_container_width=True):
                            confirm_fix_dialog(selected_semester)
            else:
                st.info(f"No subjects recorded for {selected_semester} yet.")

# =========================================================
# TAB 2: ASSIGNMENTS & TASKS
# =========================================================
with main_tab_assignments:
    st.header(f"📝 Assignment & Task Tracker ({selected_semester})")
    
    if not current_subjects:
        st.info("ℹ️ No subjects added for this semester yet. Please add subjects in the Attendance tab first.")
    else:
        subject_options = [f"[{s['code']}] {s['name']}" for s in current_subjects]
        
        with st.expander("➕ Add New Assignment / Project Submission", expanded=True):
            with st.form("add_assignment_form", clear_on_submit=True):
                col_a1, col_a2 = st.columns([2, 2])
                with col_a1:
                    sel_sub_str = st.selectbox("Select Subject", options=subject_options)
                    asgn_title = st.text_input("Assignment Title / Description", placeholder="e.g. Lab Report #3")
                with col_a2:
                    due_date_val = st.date_input("Submission Due Date", value=date.today() + timedelta(days=7))
                    due_time_val = st.time_input("Submission Due Time", value=datetime.strptime("23:59", "%H:%M").time())
                
                assignment_link = st.text_input("Assignment Link, URL or File Path (Optional)", placeholder="e.g. https://github.com/... or C:\\path\\to\\file")
                submit_asgn = st.form_submit_button("Add Assignment", type="primary")
                
                if submit_asgn:
                    if not asgn_title.strip():
                        st.error("Please enter an assignment title.")
                    else:
                        sub_code = sel_sub_str.split("]")[0].replace("[", "")
                        combined_dt = datetime.combine(due_date_val, due_time_val).replace(tzinfo=IST)
                        
                        save_assignment_to_db(user_email, selected_semester, sub_code, asgn_title.strip(), combined_dt.isoformat(), assignment_link.strip() if assignment_link else None)
                        st.success(f"Added assignment '{asgn_title}' for {sub_code}!")
                        st.rerun()

        st.markdown("---")
        st.subheader("📋 Active Assignments & Live Countdown Timers")
        
        assignments = load_assignments_from_db(user_email, selected_semester)
        if assignments:
            now_ist = get_ist_time()
            for asg in assignments:
                sub_code = asg["subject_code"]
                title = asg["title"]
                due_str = asg["due_date"]
                f_url = asg.get("file_url")
                
                due_dt = datetime.fromisoformat(due_str)
                if due_dt.tzinfo is not None:
                    due_dt = due_dt.astimezone(IST)
                
                diff = due_dt - now_ist
                if diff.total_seconds() > 0:
                    days = diff.days
                    hours, remainder = divmod(diff.seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                    timer_str = f"⏳ **{days}d {hours}h {minutes}m remaining**"
                    status_badge = "🟢 In Progress"
                else:
                    timer_str = "⚠️ **OVERDUE / PASSED**"
                    status_badge = "🔴 Past Due"

                with st.container():
                    col_b1, col_b2, col_b3 = st.columns([3, 2, 1])
                    with col_b1:
                        st.markdown(f"**[{sub_code}] {title}** ({status_badge})")
                        if f_url:
                            if f_url.startswith("http://") or f_url.startswith("https://"):
                                st.markdown(f"🔗 [Open Reference Link]({f_url})")
                            else:
                                st.code(f_url, language=None)
                    with col_b2:
                        st.markdown(timer_str)
                        st.caption(f"Due: {due_dt.strftime('%d %b %Y, %I:%M %p')}")
                    with col_b3:
                        if st.button("🗑️ Remove", key=f"del_asg_{asg['id']}"):
                            supabase.table("student_assignments").delete().eq("id", asg['id']).execute()
                            st.rerun()
                    st.divider()
        else:
            st.info("No assignments recorded for this semester yet.")

# =========================================================
# TAB 3: EXAMS & TIME TABLE
# =========================================================
with main_tab_exams:
    st.header(f"📅 Examination Schedule & Time Table ({selected_semester})")
    
    if not current_subjects:
        st.info("ℹ️ No subjects added for this semester yet. Please add subjects in the Attendance tab first.")
    else:
        subject_options = [f"[{s['code']}] {s['name']}" for s in current_subjects]
        
        with st.expander("➕ Log New Exam Date & Syllabus", expanded=True):
            with st.form("add_exam_form", clear_on_submit=True):
                col_e1, col_e2 = st.columns([2, 2])
                with col_e1:
                    sel_sub_exam = st.selectbox("Select Subject", options=subject_options, key="exam_sub_sel")
                    exam_type = st.selectbox("Exam Type", options=["Mid-Term Examination", "End-Term Examination", "Quiz / Test"])
                with col_e2:
                    exam_date_val = st.date_input("Exam Date", value=date.today() + timedelta(days=14))
                    exam_time_val = st.time_input("Exam Start Time", value=datetime.strptime("10:00", "%H:%M").time())
                
                exam_syllabus = st.text_area("Syllabus Outline / Topics Covered", placeholder="e.g. Units 1 to 3, Memory Management, Scheduling Algorithms")
                submit_exam = st.form_submit_button("Save Exam Schedule", type="primary")
                
                if submit_exam:
                    sub_code = sel_sub_exam.split("]")[0].replace("[", "")
                    combined_dt = datetime.combine(exam_date_val, exam_time_val).replace(tzinfo=IST)
                    save_exam_to_db(user_email, selected_semester, sub_code, exam_type, combined_dt.isoformat(), exam_syllabus.strip())
                    st.success(f"Scheduled {exam_type} for {sub_code}!")
                    st.rerun()

        st.markdown("---")
        st.subheader("🗓️ Semester Examination Time Table")
        
        exams = load_exams_from_db(user_email, selected_semester)
        if exams:
            exam_rows = []
            for ex in exams:
                dt_obj = datetime.fromisoformat(ex["exam_date"])
                if dt_obj.tzinfo is not None:
                    dt_obj = dt_obj.astimezone(IST)
                exam_rows.append({
                    "Subject Code": ex["subject_code"],
                    "Exam Type": ex["exam_type"],
                    "Date": dt_obj.strftime("%Y-%m-%d"),
                    "Time": dt_obj.strftime("%I:%M %p"),
                })
            
            ex_df = pd.DataFrame(exam_rows).sort_values("Date")
            st.dataframe(ex_df, use_container_width=True)
            
            st.markdown("---")
            st.subheader("📖 Detailed Exam Breakdown & Syllabus")
            for ex in exams:
                dt_obj = datetime.fromisoformat(ex["exam_date"])
                if dt_obj.tzinfo is not None:
                    dt_obj = dt_obj.astimezone(IST)
                with st.expander(f"📑 [{ex['subject_code']}] {ex['exam_type']} — {dt_obj.strftime('%d %b %Y, %I:%M %p')}"):
                    st.markdown(f"**Syllabus Outline:**")
                    st.write(ex.get("syllabus") if ex.get("syllabus") else "No syllabus entered.")
                    if st.button("🗑️ Delete Exam Entry", key=f"del_ex_{ex['id']}"):
                        supabase.table("student_exams").delete().eq("id", ex['id']).execute()
                        st.rerun()
        else:
            st.info("No exam schedules logged for this semester yet.")

# =========================================================
# TAB 4: DAILY TIMETABLE
# =========================================================
with main_tab_timetable:
    st.header(f"⏰ Daily Class Timetable ({selected_semester})")
    
    if not current_subjects:
        st.info("ℹ️ No subjects added for this semester yet. Please add subjects in the Attendance tab first.")
    else:
        subject_options = [f"[{s['code']}] {s['name']}" for s in current_subjects]
        
        with st.expander("➕ Add Class Slot to Timetable", expanded=True):
            with st.form("add_timetable_form", clear_on_submit=True):
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    tt_day = st.selectbox("Day of the Week", options=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
                    tt_sub = st.selectbox("Select Subject", options=subject_options)
                with col_t2:
                    tt_start = st.time_input("Start Time", value=datetime.strptime("09:00", "%H:%M").time())
                    tt_end = st.time_input("End Time", value=datetime.strptime("10:00", "%H:%M").time())
                
                tt_room = st.text_input("Room / Lecture Hall (Optional)", placeholder="e.g. LH-302 or Lab-2")
                submit_tt = st.form_submit_button("Add to Timetable", type="primary")
                
                if submit_tt:
                    sub_code = tt_sub.split("]")[0].replace("[", "")
                    start_str = tt_start.strftime("%I:%M %p")
                    end_str = tt_end.strftime("%I:%M %p")
                    
                    save_timetable_to_db(user_email, selected_semester, tt_day, sub_code, start_str, end_str, tt_room.strip() if tt_room else "N/A")
                    st.success(f"Added {sub_code} to {tt_day}'s timetable!")
                    st.rerun()

        st.markdown("---")
        
        # Get current day of the week in IST
        current_day_name = get_ist_time().strftime("%A")
        
        st.subheader(f"📅 Today's Schedule ({current_day_name})")
        
        all_timetable_entries = load_timetable_from_db(user_email, selected_semester)
        
        # Filter entries for today
        today_entries = [t for t in all_timetable_entries if t.get("day_of_week") == current_day_name]
        
        if today_entries:
            for entry in today_entries:
                with st.container():
                    col_card1, col_card2, col_card3 = st.columns([2, 3, 1])
                    with col_card1:
                        st.markdown(f"🕒 **{entry['start_time']} - {entry['end_time']}**")
                    with col_card2:
                        st.markdown(f"📚 **[{entry['subject_code']}]** | 📍 Room: `{entry['room_number']}`")
                    with col_card3:
                        if st.button("🗑️ Remove", key=f"del_tt_{entry['id']}"):
                            supabase.table("student_timetables").delete().eq("id", entry['id']).execute()
                            st.rerun()
                    st.divider()
        else:
            st.info(f"🎉 No classes scheduled for today ({current_day_name}) in {selected_semester}!")

        st.markdown("---")
        st.subheader("🗓️ Full Weekly Timetable Overview")
        
        if all_timetable_entries:
            days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            
            for day in days_order:
                day_slots = [t for t in all_timetable_entries if t.get("day_of_week") == day]
                if day_slots:
                    with st.expander(f"📌 {day} ({len(day_slots)} classes)"):
                        for ds in day_slots:
                            col_d1, col_d2, col_d3 = st.columns([2, 3, 1])
                            with col_d1:
                                st.write(f"⏰ {ds['start_time']} - {ds['end_time']}")
                            with col_d2:
                                st.write(f"📖 **[{ds['subject_code']}]** (Room: {ds['room_number']})")
                            with col_d3:
                                if st.button("🗑️ Delete", key=f"del_week_tt_{ds['id']}"):
                                    supabase.table("student_timetables").delete().eq("id", ds['id']).execute()
                                    st.rerun()
        else:
            st.info("No timetable entries logged for this semester yet.")
