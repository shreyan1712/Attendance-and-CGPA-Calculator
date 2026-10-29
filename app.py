from datetime import datetime, date, timedelta
import hashlib
import math
import random
import pandas as pd
import plotly.express as px
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
        "❌ Missing Supabase Secrets! Please configure `SUPABASE_URL` and `SUPABASE_KEY` in your Streamlit Cloud Secrets settings."
    )
    st.stop()


# Helper function to hash passwords securely
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# Helper function to send OTP via Resend API
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


# ---------------------------------------------------------
# NATIVE SECURE AUTHENTICATION (Supabase-backed)
# ---------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_email = None
    st.session_state.user_name = None

if "reset_step" not in st.session_state:
    st.session_state.reset_step = 1
    st.session_state.reset_username = None

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
                reset_user = st.text_input("Enter your Username")
                submit_send_otp = st.form_submit_button("Send Verification Code", type="primary")

                if submit_send_otp:
                    if not reset_user:
                        st.error("Please enter your username.")
                    else:
                        try:
                            response = (
                                supabase.table("users")
                                .select("*")
                                .eq("username", reset_user.strip())
                                .execute()
                            )
                            if response.data:
                                db_user = response.data[0]
                                user_email_db = db_user["email"]
                                
                                # Generate OTP and set 10-minute expiry time
                                otp = str(random.randint(100000, 999999))
                                expiry = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
                                
                                # Save OTP in database
                                supabase.table("users").update({
                                    "reset_otp": otp,
                                    "otp_expiry": expiry
                                }).eq("username", reset_user.strip()).execute()

                                # Send email via Resend
                                email_sent = send_otp_email(user_email_db, otp)
                                if email_sent:
                                    st.session_state.reset_step = 2
                                    st.session_state.reset_username = reset_user.strip()
                                    masked_email = user_email_db[:3] + "****" + user_email_db[user_email_db.find("@"):]
                                    st.success(f"Verification code sent to registered email: {masked_email}")
                                    st.rerun()
                                else:
                                    st.error("Failed to send email. Check RESEND_API_KEY in secrets.")
                            else:
                                st.error("Username does not exist.")
                        except Exception as err:
                            st.error(f"Database error: {err}")

        elif st.session_state.reset_step == 2:
            with st.form("forgot_step2_form"):
                st.info(f"Resetting password for username: **{st.session_state.reset_username}**")
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
                    st.session_state.reset_username = None
                    st.rerun()

                if submit_verify:
                    if not entered_otp or not new_reset_pass or not confirm_reset_pass:
                        st.error("Please fill in all fields.")
                    elif new_reset_pass != confirm_reset_pass:
                        st.error("New passwords do not match.")
                    else:
                        try:
                            res = supabase.table("users").select("*").eq("username", st.session_state.reset_username).execute()
                            if res.data:
                                u_data = res.data[0]
                                db_otp = u_data.get("reset_otp")
                                db_expiry = u_data.get("otp_expiry")
                                
                                now = datetime.utcnow()
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
                                    }).eq("username", st.session_state.reset_username).execute()
                                    
                                    st.success("Password successfully updated! You can now log in.")
                                    st.session_state.reset_step = 1
                                    st.session_state.reset_username = None
                            else:
                                st.error("User not found.")
                        except Exception as err:
                            st.error(f"Database error during update: {err}")

    st.stop()

# If successfully authenticated:
user_email = st.session_state.user_email
user_name = st.session_state.user_name

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
# CLOUD DATABASE HELPER FUNCTIONS (Scoped to user_email)
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


def load_subscribers_from_db(email):
    try:
        response = (
            supabase.table("telegram_subscribers")
            .select("*")
            .eq("user_email", email)
            .execute()
        )
        if response.data:
            return response.data[0].get("subscribers_json", {})
    except Exception:
        pass
    return {}


def save_subscribers_to_db(email, subs):
    supabase.table("telegram_subscribers").upsert(
        {
            "user_email": email,
            "subscribers_json": subs,
        },
        on_conflict="user_email",
    ).execute()


def load_offset_from_db(email):
    try:
        response = (
            supabase.table("telegram_offsets")
            .select("*")
            .eq("user_email", email)
            .execute()
        )
        if response.data:
            return response.data[0].get("offset_val", 0)
    except Exception:
        pass
    return 0


def save_offset_to_db(email, offset):
    supabase.table("telegram_offsets").upsert(
        {
            "user_email": email,
            "offset_val": offset,
        },
        on_conflict="user_email",
    ).execute()


def fetch_telegram_updates(token, email):
    offset = load_offset_from_db(email)
    url = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                subs = load_subscribers_from_db(email)
                new_found = False
                max_update_id = offset

                for result in data.get("result", []):
                    update_id = result.get("update_id", 0)
                    if update_id >= max_update_id:
                        max_update_id = update_id + 1

                    message = result.get("message", {})
                    chat = message.get("chat", {})
                    chat_id = str(chat.get("id"))
                    if chat_id:
                        first_name = chat.get("first_name", "User")
                        username_tg = chat.get("username", "")
                        name_label = (
                            f"{first_name} (@{username_tg})"
                            if username_tg
                            else first_name
                        )
                        if chat_id not in subs:
                            new_found = True
                        subs[chat_id] = name_label

                save_subscribers_to_db(email, subs)
                save_offset_to_db(email, max_update_id)
                return True, new_found
    except Exception:
        pass
    return False, False


def send_telegram_alert(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------
# MAIN APPLICATION INTERFACE
# ---------------------------------------------------------
st.title("📚 Student Academic & Attendance Hub")

if st.sidebar.button("🚪 Logout", key="logout_btn"):
    st.session_state.authenticated = False
    st.session_state.user_email = None
    st.session_state.user_name = None
    st.rerun()

st.sidebar.markdown(f"Welcome, **{user_name}**!")

if "nav_mode" not in st.session_state:
    st.session_state.nav_mode = "Data Entry & Management"

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

if (
    hasattr(st, "secrets")
    and "telegram" in st.secrets
    and "bot_token" in st.secrets.telegram
):
    TELEGRAM_BOT_TOKEN = st.secrets.telegram.bot_token
    TELEGRAM_BOT_USERNAME = st.secrets.telegram.get(
        "bot_username", "GEU_Academic_Bot"
    )
else:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Telegram Bot Settings")
    TELEGRAM_BOT_TOKEN = st.sidebar.text_input(
        "Bot Token", type="password", placeholder="Enter Bot Token"
    )
    TELEGRAM_BOT_USERNAME = st.sidebar.text_input(
        "Bot Username", placeholder="e.g. GEU_Academic_Bot"
    )

st.sidebar.markdown("---")
st.sidebar.markdown("### Menu")

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
if selected_semester not in st.session_state.all_semesters:
    st.session_state.all_semesters[selected_semester] = []

is_locked = st.session_state.sem_locks.get(selected_semester, False)
current_subjects = st.session_state.all_semesters[selected_semester]

# ---------------------------------------------------------
# VIEW 1: DATA ENTRY & MANAGEMENT
# ---------------------------------------------------------
if nav_mode == "Data Entry & Management":
    st.header(f"📌 Add Subjects: {selected_semester}")

    if is_locked:
        st.warning(
            f"🔒 {selected_semester} is permanently fixed/locked. No further modifications can be made."
        )
    else:
        st.markdown(
            f"Register your subjects, credits, and total semester classes for **{selected_semester}**."
        )

        with st.form(
            f"add_subject_form_{selected_semester}", clear_on_submit=True
        ):
            st.subheader("New Subject Registration")
            col1, col2, col3, col4, col5, col6, col7 = st.columns(
                [2, 3, 1, 1.3, 1, 1, 1]
            )
            with col1:
                new_code = st.text_input("Subject Code", placeholder="e.g. TCS-401")
            with col2:
                new_name = st.text_input(
                    "Subject Name", placeholder="e.g. Operating Systems"
                )
            with col3:
                new_credits = st.number_input(
                    "Credits", min_value=1, max_value=10, value=3, step=1
                )
            with col4:
                new_total = st.number_input(
                    "Total Classes", min_value=1, value=40, step=1
                )
            with col5:
                new_attended = st.number_input(
                    "Attended", min_value=0, value=0, step=1
                )
            with col6:
                new_conducted = st.number_input(
                    "Conducted", min_value=0, value=0, step=1
                )
            with col7:
                st.markdown("<br>", unsafe_allow_html=True)
                add_btn = st.form_submit_button("Add")

            if add_btn:
                if new_code.strip() == "" or new_name.strip() == "":
                    st.error("Please enter both Subject Code and Name.")
                elif new_attended > new_conducted:
                    st.error("Attended classes cannot exceed conducted classes.")
                elif new_conducted > new_total:
                    st.error(
                        "Conducted classes cannot exceed total semester classes."
                    )
                else:
                    current_subjects.append(
                        {
                            "code": new_code.upper(),
                            "name": new_name,
                            "credits": int(new_credits),
                            "total_classes": int(new_total),
                            "attended": int(new_attended),
                            "conducted": int(new_conducted),
                            "grade_point": 0.0,
                            "attendance_date": str(date.today()),
                        }
                    )
                    st.session_state.all_semesters[selected_semester] = (
                        current_subjects
                    )
                    save_data_to_db(
                        user_email, selected_semester, current_subjects
                    )
                    st.success(f"Added {new_code} - {new_name} successfully!")
                    st.rerun()

    if current_subjects:
        st.markdown("---")
        st.subheader(f"Currently Registered Subjects ({selected_semester})")
        for idx, subj in enumerate(current_subjects, 1):
            total_cls = subj.get("total_classes", 40)
            att_date = subj.get("attendance_date", str(date.today()))
            st.markdown(
                f"{idx}. **[{subj['code']}] {subj['name']}** (Credits: {subj['credits']}, Total: {total_cls}, Attended: {subj['attended']}/{subj['conducted']}, Grade Point: {subj['grade_point']}, Last Updated: `{att_date}`)"
            )
    else:
        st.info(f"No subjects added for {selected_semester} yet.")

# ---------------------------------------------------------
# VIEW 2: UPDATE RECORDS
# ---------------------------------------------------------
elif nav_mode == "Update Records":
    st.header(f"🔄 Update Records: {selected_semester}")

    if is_locked:
        st.warning(
            f"🔒 {selected_semester} is permanently fixed/locked. Records cannot be updated."
        )
        if current_subjects:
            st.markdown("---")
            st.subheader(f"Locked Records ({selected_semester})")
            for idx, subj in enumerate(current_subjects, 1):
                total_cls = subj.get("total_classes", 40)
                att_date = subj.get("attendance_date", str(date.today()))
                st.markdown(
                    f"{idx}. **[{subj['code']}] {subj['name']}** | Total: {total_cls} | Grade Point: **{subj['grade_point']}** | Attended: {subj['attended']}/{subj['conducted']} | Last Updated: `{att_date}`"
                )
    else:
        st.markdown(
            f"Update your attendance or final grade points for **{selected_semester}**."
        )

        if current_subjects:
            updated_subjects = []
            data_changed = False

            for i, subj in enumerate(current_subjects):
                existing_date_str = subj.get(
                    "attendance_date", str(date.today())
                )

                with st.expander(
                    f"📖 [{subj['code']}] {subj['name']} (Credits: {subj['credits']} | Last Updated: {existing_date_str})"
                ):
                    col_del, _ = st.columns([1, 4])
                    with col_del:
                        delete_clicked = st.button(
                            "🗑️ Delete", key=f"del_{selected_semester}_{i}"
                        )

                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        code = st.text_input(
                            "Subject Code",
                            value=subj["code"],
                            key=f"code_{selected_semester}_{i}",
                        )
                    with c2:
                        name = st.text_input(
                            "Subject Name",
                            value=subj["name"],
                            key=f"name_{selected_semester}_{i}",
                        )
                    with c3:
                        credits = st.number_input(
                            "Credits",
                            min_value=1,
                            max_value=10,
                            value=int(subj["credits"]),
                            key=f"cred_{selected_semester}_{i}",
                        )
                    with c4:
                        total_classes = st.number_input(
                            "Total Semester Classes",
                            min_value=1,
                            value=int(subj.get("total_classes", 40)),
                            key=f"tot_{selected_semester}_{i}",
                        )

                    c5, c6, c7 = st.columns(3)
                    with c5:
                        attended = st.number_input(
                            "Classes Attended",
                            min_value=0,
                            value=int(subj["attended"]),
                            key=f"att_{selected_semester}_{i}",
                        )
                    with c6:
                        conducted = st.number_input(
                            "Classes Conducted",
                            min_value=0,
                            value=max(int(subj["conducted"]), attended),
                            key=f"cond_{selected_semester}_{i}",
                        )
                    with c7:
                        endterm = st.number_input(
                            "Final Grade Point (0-10)",
                            min_value=0.0,
                            max_value=10.0,
                            value=float(subj.get("grade_point", 0.0)),
                            step=0.5,
                            key=f"gp_{selected_semester}_{i}",
                        )

                    if not delete_clicked:
                        field_changed = (
                            code.upper() != subj["code"]
                            or name != subj["name"]
                            or credits != subj["credits"]
                            or total_classes != subj.get("total_classes", 40)
                            or attended != subj["attended"]
                            or conducted != subj["conducted"]
                            or endterm != subj.get("grade_point", 0.0)
                        )
                        final_date = (
                            str(date.today())
                            if field_changed
                            else existing_date_str
                        )

                        updated_subjects.append(
                            {
                                "code": code.upper(),
                                "name": name,
                                "credits": credits,
                                "total_classes": total_classes,
                                "attended": attended,
                                "conducted": conducted,
                                "grade_point": endterm,
                                "attendance_date": final_date,
                            }
                        )
                    else:
                        data_changed = True

            if updated_subjects != current_subjects:
                data_changed = True

            st.session_state.all_semesters[selected_semester] = updated_subjects
            if data_changed:
                save_data_to_db(user_email, selected_semester, updated_subjects)
                st.success("Records updated successfully!")
                st.rerun()
        else:
            st.info(
                f"No subjects found for {selected_semester}. Please add subjects first."
            )

# ---------------------------------------------------------
# VIEW 3: CALCULATION DASHBOARD
# ---------------------------------------------------------
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
        cgpa = (
            (overall_weighted_gp / overall_credits)
            if overall_credits > 0
            else 0.0
        )
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric(
                label="Overall CGPA (All Semesters)", value=f"{cgpa:.2f} / 10.0"
            )

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
                total_cls = subj.get("total_classes", 40)
                att_date = subj.get("attendance_date", str(date.today()))
                pct = (att / cond * 100) if cond > 0 else 0.0

                remaining_classes = max(0, total_cls - cond)
                target_ratio = default_target / 100.0
                required_total_attended = math.ceil(target_ratio * total_cls)
                needed_from_remaining = max(
                    0, required_total_attended - att
                )

                if pct >= default_target:
                    margin = int(
                        (100 * att - default_target * cond) / default_target
                    )
                    current_status = f"Safe (Can skip {margin})"
                else:
                    needed_consecutive = math.ceil(
                        (target_ratio * cond - att) / (1.0 - target_ratio)
                    )
                    current_status = (
                        f"Short (Need next {max(1, needed_consecutive)})"
                    )

                if pct >= default_target:
                    target_status = "Target Maintained"
                else:
                    if needed_from_remaining <= remaining_classes:
                        target_status = (
                            f"Need {needed_from_remaining} of {remaining_classes} left"
                        )
                    else:
                        target_status = (
                            f"Unachievable (Need {needed_from_remaining}/{remaining_classes})"
                        )

                att_data.append(
                    {
                        "S.No.": idx,
                        "Code": subj["code"],
                        "Subject": subj["name"],
                        "Credits": subj["credits"],
                        "Total Classes": total_cls,
                        "Attended": att,
                        "Conducted": cond,
                        "Percentage": round(pct, 2),
                        "Current Status": current_status,
                        "Target Projection": target_status,
                        "Grade Point": subj["grade_point"],
                        "Last Updated": att_date,
                    }
                )

                sem_weighted_gp += subj["credits"] * subj["grade_point"]
                sem_credits += subj["credits"]

            df = pd.DataFrame(att_data)
            df.set_index("S.No.", inplace=True)
            sgpa = (sem_weighted_gp / sem_credits) if sem_credits > 0 else 0.0

            st.markdown("---")
            st.subheader(
                f"📌 Academic Performance & SGPA ({selected_semester})"
            )
            st.metric(
                label=f"Current {selected_semester} SGPA",
                value=f"{sgpa:.2f} / 10.0",
            )

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
            fig_bar.update_traces(
                texttemplate="%{text:.1f}%", textposition="outside"
            )
            st.plotly_chart(fig_bar, use_container_width=True)

            # Telegram Hub
            st.markdown("---")
            st.subheader("📱 Telegram Bot Subscriber Hub & Dispatcher")
            col_qr, col_disp = st.columns([1, 2])

            with col_qr:
                if TELEGRAM_BOT_USERNAME:
                    bot_url = f"https://t.me/{TELEGRAM_BOT_USERNAME.strip('@')}"
                    qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={bot_url}"
                    st.image(
                        qr_api_url,
                        caption=f"Scan to open @{TELEGRAM_BOT_USERNAME.strip('@')}",
                    )
                else:
                    st.info("💡 Configure your Bot Username.")

            with col_disp:
                st.markdown("#### 👥 Select Subscriber & Dispatch")
                if st.button("🔄 Sync New Subscribers"):
                    if not TELEGRAM_BOT_TOKEN:
                        st.error("Please configure your Bot Token.")
                    else:
                        success, found_new = fetch_telegram_updates(
                            TELEGRAM_BOT_TOKEN, user_email
                        )
                        if success:
                            st.success("Subscribers synced successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to fetch updates from Telegram.")

                subscribers = load_subscribers_from_db(user_email)
                if subscribers:
                    subscriber_options = {
                        name_val: cid for cid, name_val in subscribers.items()
                    }
                    selected_subscriber_label = st.selectbox(
                        "Choose Recipient", options=list(subscriber_options.keys())
                    )
                    selected_chat_id = subscriber_options.get(
                        selected_subscriber_label
                    )

                    if st.button(
                        "🚀 DISPATCH REPORT",
                        type="primary",
                        use_container_width=True,
                    ):
                        if not TELEGRAM_BOT_TOKEN:
                            st.error("Please configure your Bot Token.")
                        else:
                            msg_lines = [
                                "*🎓 GEU ACADEMIC REPORT*",
                                f"📅 *Semester:* {selected_semester}",
                                f"📊 *Current SGPA:* `{sgpa:.2f} / 10.0`",
                                f"🏆 *Overall CGPA:* `{cgpa:.2f} / 10.0`",
                                f"🎯 *Target Attendance:* `{default_target}%`",
                                "\n*📖 Subject Breakdown:*",
                            ]
                            for idx, row in df.iterrows():
                                msg_lines.append(
                                    f"• *{row['Code']}* ({row['Subject']})\n"
                                    f"  └ Percentage: `{row['Percentage']}%`\n"
                                    f"  └ Current: _{row['Current Status']}_\n"
                                    f"  └ Target Plan: _{row['Target Projection']}_\n"
                                    f"  └ Last Updated: `{row['Last Updated']}`\n"
                                )
                            full_report = "\n".join(msg_lines)
                            sent = send_telegram_alert(
                                TELEGRAM_BOT_TOKEN, selected_chat_id, full_report
                            )
                            if sent:
                                st.success(
                                    f"Report dispatched to {selected_subscriber_label}!"
                                )
                            else:
                                st.error(
                                    "Failed to dispatch. Ensure the user has started your bot first."
                                )
                else:
                    st.warning(
                        "No subscribers found yet. Scan QR code, press Start on your bot, and click Sync."
                    )

            # Semester Fixation
            st.markdown("---")
            st.subheader(f"🔒 Semester Fixation ({selected_semester})")

            @st.dialog("⚠️ Confirm Permanent Fixation")
            def confirm_fix_dialog(sem_name):
                st.markdown(
                    f"Are you sure you want to **permanently lock {sem_name}**?"
                )
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    if st.button(
                        "✅ Yes, Lock Permanently", use_container_width=True
                    ):
                        st.session_state.sem_locks[sem_name] = True
                        save_lock_to_db(user_email, sem_name, True)
                        st.success(f"{sem_name} has been permanently locked!")
                        st.rerun()
                with col_c2:
                    if st.button("❌ Cancel", use_container_width=True):
                        st.rerun()

            if is_locked:
                st.success(
                    f"🔒 Status: {selected_semester} is permanently fixed and locked."
                )
            else:
                if not all_grades_entered:
                    st.info(
                        "ℹ️ The **FIX** button will become available once final grade points (> 0.0) are entered for all subjects."
                    )
                    st.button(
                        "🔒 FIX SEMESTER DATA",
                        disabled=True,
                        use_container_width=True,
                    )
                else:
                    if st.button(
                        "🔒 FIX SEMESTER DATA",
                        type="primary",
                        use_container_width=True,
                    ):
                        confirm_fix_dialog(selected_semester)
        else:
            st.info(f"No subjects recorded for {selected_semester} yet.")
