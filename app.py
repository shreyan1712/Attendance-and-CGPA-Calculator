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
        "❌ Missing Secrets! Please configure your connection settings in Streamlit Cloud."
    )
    st.stop()


# Helper function to hash passwords securely
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# Helper function to get current Indian Standard Time (IST)
def get_ist_time():
    return datetime.utcnow() + timedelta(hours=5, minutes=30)


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
# NATIVE SECURE AUTHENTICATION & SESSION PERSISTENCE
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
            stay_signed_in = st.checkbox("Stay signed in", value=True)
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
                                expiry = (get_ist_time() + timedelta(minutes=10)).isoformat()
                                
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
                                
                                now = get_ist_time()
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

# Update presence heartbeat (using IST time) & check for active pranks
try:
    supabase.table("users").update({"last_seen": get_ist_time().isoformat()}).eq("email", user_email).execute()
except Exception:
    pass

try:
    u_chk = supabase.table("users").select("prank_active").eq("email", user_email).execute()
    if u_chk.data and u_chk.data[0].get("prank_active"):
        supabase.table("users").update({"prank_active": False}).eq("email", user_email).execute()
        st.markdown("""
            <style>
            body { overflow: hidden; background: black; }
            .matrix-screen {
                position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
                background-color: black; color: #00ff00; z-index: 999999;
                font-family: 'Courier New', monospace; overflow: hidden;
            }
            canvas { display: block; position: absolute; top: 0; left: 0; width: 100%; height: 100%; }
            .prank-popup {
                position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
                background: rgba(0, 0, 0, 0.9); border: 4px solid #ff0000; padding: 40px;
                text-align: center; border-radius: 12px; box-shadow: 0 0 40px #ff0000; z-index: 1000000;
                animation: glitch 0.2s infinite;
            }
            @keyframes glitch {
                0% { transform: translate(-50%, -50%) skew(0deg); }
                20% { transform: translate(-52%, -48%) skew(-2deg); }
                40% { transform: translate(-48%, -52%) skew(2deg); }
                60% { transform: translate(-50%, -50%) skew(0deg); }
            }
            .glitch-title { font-size: 40px; color: #ff0000; font-weight: bold; text-shadow: 0 0 15px #ff0000; margin-bottom: 15px; }
            .glitch-sub { font-size: 20px; color: #00ff00; text-shadow: 0 0 8px #00ff00; }
            </style>
            <div class="matrix-screen" id="matrixContainer">
                <canvas id="matrixCanvas"></canvas>
                <div class="prank-popup" id="prankBox">
                    <div class="glitch-title">⚠️ SYSTEM BREACH DETECTED ⚠️</div>
                    <div class="glitch-sub">Extracting local database & student credentials...</div>
                </div>
            </div>
            <script>
                // Matrix Digital Rain Generator (Green numbers/chars cascading fast)
                const canvas = document.getElementById('matrixCanvas');
                const ctx = canvas.getContext('2d');
                canvas.width = window.innerWidth;
                canvas.height = window.innerHeight;

                const characters = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz@#$%^&*()_+-=[]{}|;:,.<>?';
                const fontSize = 16;
                const columns = canvas.width / fontSize;
                const drops = [];
                for (let i = 0; i < columns; i++) {
                    drops[i] = 1;
                }

                function drawMatrix() {
                    ctx.fillStyle = 'rgba(0, 0, 0, 0.08)';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);
                    ctx.fillStyle = '#00ff00';
                    ctx.font = 'bold ' + fontSize + 'px monospace';
                    for (let i = 0; i < drops.length; i++) {
                        const text = characters.charAt(Math.floor(Math.random() * characters.length));
                        ctx.fillText(text, i * fontSize, drops[i] * fontSize);
                        if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
                            drops[i] = 0;
                        }
                        drops[i]++;
                    }
                }
                const matrixInterval = setInterval(drawMatrix, 20);

                // Transition to GET PRANKED! after 4 seconds
                setTimeout(function() {
                    const box = document.getElementById('prankBox');
                    box.style.borderColor = '#00ff00';
                    box.style.boxShadow = '0 0 50px #00ff00';
                    box.style.animation = 'none';
                    box.innerHTML = "<h1 style='color: #00ff00; font-size: 65px; text-shadow: 0 0 25px #00ff00; margin: 0;'>😂 GET PRANKED! 😂</h1><p style='color: white; font-size: 20px; margin-top: 20px; font-weight: bold;'>Your files are completely safe. Nice try though!</p>";
                }, 4000);

                // Close and reload after 8 seconds total
                setTimeout(function() {
                    clearInterval(matrixInterval);
                    document.getElementById('matrixContainer').style.display = 'none';
                    window.location.reload();
                }, 8000);
            </script>
        """, unsafe_allow_html=True)
        st.stop()
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

# ---------------------------------------------------------
# HIDDEN ADMIN PANEL & SURVEILLANCE DASHBOARD
# ---------------------------------------------------------
admin_email_secret = st.secrets.get("admin_email", "")
is_admin = admin_email_secret and user_email == admin_email_secret

if is_admin:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🕵️ Admin Controls")
    admin_mode = st.sidebar.toggle("Enable Admin Dashboard", value=False)
else:
    admin_mode = False

if is_admin and admin_mode:
    st.header("🕵️ System Administrator Dashboard")
    st.markdown("Monitor user activity, manage locked records, search student reports, and execute remote operations.")

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

        st.markdown("---")
        st.subheader("📡 Live Presence & Prank Controller")
        
        if users_list:
            now = get_ist_time()
            for u in users_list:
                u_email = u["email"]
                u_name = u["name"]
                u_last_seen = u.get("last_seen")

                status_label = "🔴 Offline"
                if u_last_seen:
                    try:
                        last_seen_dt = datetime.fromisoformat(u_last_seen)
                        diff_sec = (now - last_seen_dt).total_seconds()
                        if diff_sec < 30:
                            status_label = "🟢 Online Now"
                        else:
                            mins = max(1, int(diff_sec / 60))
                            status_label = f"🕒 Last seen {mins}m ago"
                    except Exception:
                        pass

                col_u1, col_u2, col_u3 = st.columns([3, 2, 1])
                with col_u1:
                    st.markdown(f"**{u_name}** (`{u_email}`)")
                with col_u2:
                    st.write(status_label)
                with col_u3:
                    if st.button("🚨 PRANK", key=f"prank_btn_{u_email}"):
                        supabase.table("users").update({"prank_active": True}).eq("email", u_email).execute()
                        st.success(f"Prank trigger sent to {u_name}!")

        st.markdown("---")
        st.subheader("🔓 Admin Semester Unlocker")
        st.markdown("Override and clear locked status for any user who accidentally fixed their semester.")
        
        all_emails = [u["email"] for u in users_list]
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

        st.markdown("---")
        st.subheader("🔍 Searchable User Reports Directory")
        
        if users_list:
            users_df = pd.DataFrame(users_list)
            search_query = st.text_input("Search Users", placeholder="Filter by Name, Username, or Email...")

            if search_query:
                mask = users_df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
                filtered_df = users_df[mask]
            else:
                filtered_df = users_df

            st.dataframe(filtered_df, use_container_width=True)

            selected_inspect_user = st.selectbox("Inspect Academic Breakdown", options=all_emails, key="inspect_user_sel")
            if selected_inspect_user:
                st.markdown(f"#### 📊 Detailed Breakdown for: `{selected_inspect_user}`")
                user_records = [r for r in att_list if r["user_email"] == selected_inspect_user]
                
                if user_records:
                    for rec in user_records:
                        with st.expander(f"📁 {rec['semester']} ({len(rec['subjects_json'])} subjects)"):
                            if rec['subjects_json']:
                                st.dataframe(pd.DataFrame(rec['subjects_json']), use_container_width=True)
                            else:
                                st.info("No subjects recorded.")
                else:
                    st.info("No semester records logged by this user yet.")

    except Exception as err:
        st.error(f"Error loading admin dashboard: {err}")

    st.stop()

# ---------------------------------------------------------
# REGULAR STUDENT NAVIGATION & VIEWS
# ---------------------------------------------------------
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
            f"Register your subjects, credits, and current attendance stats for **{selected_semester}**."
        )

        with st.form(
            f"add_subject_form_{selected_semester}", clear_on_submit=True
        ):
            st.subheader("New Subject Registration")
            col1, col2, col3, col4, col5, col6 = st.columns(
                [2, 3, 1, 1, 1, 1]
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
                new_attended = st.number_input(
                    "Attended", min_value=0, value=0, step=1
                )
            with col5:
                new_conducted = st.number_input(
                    "Conducted", min_value=0, value=0, step=1
                )
            with col6:
                st.markdown("<br>", unsafe_allow_html=True)
                add_btn = st.form_submit_button("Add")

            if add_btn:
                if new_code.strip() == "" or new_name.strip() == "":
                    st.error("Please enter both Subject Code and Name.")
                elif new_attended > new_conducted:
                    st.error("Attended classes cannot exceed conducted classes.")
                else:
                    current_subjects.append(
                        {
                            "code": new_code.upper(),
                            "name": new_name,
                            "credits": int(new_credits),
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
            att_date = subj.get("attendance_date", str(date.today()))
            st.markdown(
                f"{idx}. **[{subj['code']}] {subj['name']}** (Credits: {subj['credits']}, Attended: {subj['attended']}/{subj['conducted']}, Grade Point: {subj['grade_point']}, Last Updated: `{att_date}`)"
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
                att_date = subj.get("attendance_date", str(date.today()))
                st.markdown(
                    f"{idx}. **[{subj['code']}] {subj['name']}** | Grade Point: **{subj['grade_point']}** | Attended: {subj['attended']}/{subj['conducted']} | Last Updated: `{att_date}`"
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

                    c1, c2, c3 = st.columns(3)
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

                    c4, c5, c6 = st.columns(3)
                    with c4:
                        attended = st.number_input(
                            "Classes Attended",
                            min_value=0,
                            value=int(subj["attended"]),
                            key=f"att_{selected_semester}_{i}",
                        )
                    with c5:
                        conducted = st.number_input(
                            "Classes Conducted",
                            min_value=0,
                            value=max(int(subj["conducted"]), attended),
                            key=f"cond_{selected_semester}_{i}",
                        )
                    with c6:
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
                att_date = subj.get("attendance_date", str(date.today()))
                pct = (att / cond * 100) if cond > 0 else 0.0

                if pct >= default_target:
                    max_skips = max(0, math.floor((100 * att - default_target * cond) / default_target))
                    current_status = f"Safe (Can skip {max_skips})"
                    target_status = "Target Maintained"
                else:
                    needed_consecutive = math.ceil((default_target * cond - 100 * att) / (100.0 - default_target))
                    current_status = f"Short (Need next {max(1, needed_consecutive)})"
                    target_status = f"Need next {max(1, needed_consecutive)} classes"

                att_data.append(
                    {
                        "S.No.": idx,
                        "Code": subj["code"],
                        "Subject": subj["name"],
                        "Credits": subj["credits"],
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
                    
                    <p style="margin-top: 30px; font-size: 12px; color: #777; text-align: center;">
                        Generated automatically via Student Academic & Attendance Hub.
                    </p>
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
