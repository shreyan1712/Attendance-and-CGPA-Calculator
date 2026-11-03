import base64
from datetime import datetime, date, timedelta, timezone
import hashlib
import hmac
import io
import json
import math
import random
import zipfile
import pandas as pd
import plotly.express as px
import pyotp
import requests
import streamlit as st
from supabase import create_client

st.set_page_config(
page_title="Student Academic & Attendance Hub", page_icon="📚", layout="wide"
)

---------------------------------------------------------

DATABASE & SECRETS INITIALIZATION

---------------------------------------------------------

try:
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
st.error(
"❌ Missing Secrets! Please configure your connection settings in Streamlit Cloud."
)
st.stop()

Helper function to hash passwords securely

def hash_password(password):
return hashlib.sha256(password.encode()).hexdigest()

Helper function to get current Indian Standard Time (IST)

IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_time():
return datetime.now(IST)

Helper function to parse DB timestamps into IST safely

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

Helper function to send OTP & Emails via API

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


---------------------------------------------------------

NATIVE SECURE AUTHENTICATION STATE & REFINED UI

---------------------------------------------------------

if "authenticated" not in st.session_state:
st.session_state.authenticated = False
st.session_state.user_email = None
st.session_state.user_name = None

if "reset_step" not in st.session_state:
st.session_state.reset_step = 1
st.session_state.reset_email = None

if "current_page" not in st.session_state:
st.session_state.current_page = "Home"

if "admin_unlocked" not in st.session_state:
st.session_state.admin_unlocked = False
if "show_admin_login" not in st.session_state:
st.session_state.show_admin_login = False
if "admin_active_tab" not in st.session_state:
st.session_state.admin_active_tab = True
if "admin_page" not in st.session_state:
st.session_state.admin_page = "AdminHome"

---------------------------------------------------------

UNIFIED GLOBAL DARK THEME & CROSS-DEVICE CSS ENGINE

---------------------------------------------------------

st.markdown(
"""

@keyframes fadeIn {
from { opacity: 0; transform: translateY(4px); }
to { opacity: 1; transform: translateY(0); }
}

/* Force dark theme variables and base backgrounds globally */
:root {
    color-scheme: dark;
}

.stApp {
    background: radial-gradient(circle at 50% 0%, #161b22 0%, #0d1117 100%) !important;
    color: #e6edf3 !important;
    animation: fadeIn 0.3s ease-in-out !important;
}

/* Typography & Hierarchy Improvements - Ensuring High Contrast */
p, span, label, div, li, .stMarkdown, [data-testid="stMarkdownContainer"] {
    color: #e6edf3 !important;
}

small, .stCaption, [data-testid="stCaptionContainer"] {
    color: #8b949e !important;
}

h1 {
    font-weight: 800 !important;
    letter-spacing: -0.5px !important;
    margin-bottom: 0.5rem !important;
    color: #ffffff !important;
}
h2 {
    font-weight: 700 !important;
    letter-spacing: -0.3px !important;
    margin-top: 1.5rem !important;
    margin-bottom: 1rem !important;
    color: #ffffff !important;
}
h3 {
    font-weight: 600 !important;
    margin-top: 1.2rem !important;
    margin-bottom: 0.8rem !important;
    color: #c9d1d9 !important;
}
hr {
    margin: 2.5rem 0 !important;
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, rgba(255,255,255,0), rgba(255,183,3,0.3), rgba(255,255,255,0)) !important;
}

/* Metric Cards */
[data-testid="stMetric"] {
    background: rgba(22, 27, 34, 0.7) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 16px !important;
    padding: 1.6rem !important;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-4px) !important;
    border-color: rgba(255, 183, 3, 0.4) !important;
    box-shadow: 0 14px 40px 0 rgba(0, 0, 0, 0.6), 0 0 20px rgba(217, 4, 41, 0.25) !important;
}
[data-testid="stMetricValue"] {
    background: linear-gradient(135deg, #ffb703 0%, #d90429 50%, #58a6ff 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    font-size: 2.4rem !important;
    font-weight: 800 !important;
    filter: drop-shadow(0 2px 8px rgba(217, 4, 41, 0.3));
}

/* Expanders */
div[data-testid="stExpander"] {
    background: rgba(22, 27, 34, 0.6) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 14px !important;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35) !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
    margin-bottom: 1rem !important;
    transition: all 0.3s ease !important;
}
div[data-testid="stExpander"]:hover {
    border-color: rgba(255, 255, 255, 0.22) !important;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5) !important;
}

/* Input & Select Fields - Hardened Cross-Device Dark Theme */
input, textarea, select {
    color: #e6edf3 !important;
    background-color: rgba(13, 17, 23, 0.85) !important;
}

div[data-baseweb="input"] > div, 
div[data-baseweb="select"] > div, 
div[data-baseweb="base-input"] {
    background-color: rgba(13, 17, 23, 0.85) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 10px !important;
    box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.4) !important;
    color: #e6edf3 !important;
    transition: all 0.3s ease !important;
}

div[data-baseweb="input"] input, 
div[data-baseweb="select"] span, 
div[data-baseweb="select"] div {
    color: #e6edf3 !important;
}

div[data-baseweb="input"] > div:focus-within, 
div[data-baseweb="select"] > div:focus-within {
    border-color: #ffb703 !important;
    box-shadow: 0 0 12px rgba(255, 183, 3, 0.3), inset 0 2px 4px rgba(0, 0, 0, 0.4) !important;
}

/* Dropdown Popover Menus (BaseWeb Menu / Dropdown lists) */
div[data-baseweb="popover"], div[data-baseweb="menu"], ul[role="listbox"] {
    background-color: #161b22 !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    border-radius: 10px !important;
}

li[role="option"] {
    background-color: #161b22 !important;
    color: #e6edf3 !important;
}

li[role="option"]:hover, li[role="option"][aria-selected="true"] {
    background-color: rgba(217, 4, 41, 0.25) !important;
    color: #ffffff !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #0b0f15 !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    padding-top: 1rem !important;
}
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
    color: #c9d1d9 !important;
}

/* Buttons */
.stButton button {
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    padding: 0.5rem 1rem !important;
    color: #ffffff !important;
}
.stButton button:hover {
    transform: translateY(-2px) !important;
    filter: brightness(1.12) !important;
    box-shadow: 0 6px 20px rgba(217, 4, 41, 0.4) !important;
}
.stButton button[kind="primary"] {
    background: linear-gradient(135deg, rgba(160, 0, 55, 0.85), rgba(217, 4, 41, 0.85)) !important;
    border: 1px solid rgba(255, 183, 3, 0.4) !important;
    border-radius: 10px !important;
    box-shadow: 0 4px 15px rgba(217, 4, 41, 0.3) !important;
    backdrop-filter: blur(6px) !important;
    color: #ffffff !important;
}

/* Native Components Customization */
div[data-baseweb="notification"], .stAlert {
    background: rgba(22, 27, 34, 0.85) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 12px !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
    color: #e6edf3 !important;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4) !important;
}

[data-testid="stFileUploader"] section {
    background: rgba(13, 17, 23, 0.75) !important;
    border: 2px dashed rgba(255, 183, 3, 0.4) !important;
    border-radius: 14px !important;
    padding: 1.5rem !important;
    transition: all 0.3s ease !important;
}
[data-testid="stFileUploader"] section:hover {
    border-color: #ffb703 !important;
    background: rgba(22, 27, 34, 0.85) !important;
    box-shadow: 0 0 15px rgba(255, 183, 3, 0.2) !important;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background-color: rgba(13, 17, 23, 0.6);
    padding: 6px;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.08);
}
.stTabs [data-baseweb="tab"] {
    background-color: transparent !important;
    border-radius: 8px !important;
    color: #c9d1d9 !important;
    font-weight: 600 !important;
    padding: 8px 16px !important;
    transition: all 0.25s ease !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, rgba(160, 0, 55, 0.85), rgba(217, 4, 41, 0.85)) !important;
    color: #ffffff !important;
    box-shadow: 0 4px 15px rgba(217, 4, 41, 0.3) !important;
    border: 1px solid rgba(255, 183, 3, 0.4) !important;
}

[data-testid="stDataFrame"], .stDataFrame {
    border-radius: 12px !important;
    overflow: hidden !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5) !important;
}
</style>
""",
unsafe_allow_html=True,


)

---------------------------------------------------------

GLOBAL MAINTENANCE MODE CHECK

---------------------------------------------------------

def check_maintenance_mode():
try:
resp = supabase.table("system_settings").select("*").eq("key", "maintenance_mode").execute()
if resp.data:
return resp.data[0].get("value", False)
except Exception:
pass
return False

def set_maintenance_mode(status: bool):
try:
supabase.table("system_settings").upsert({
"key": "maintenance_mode",
"value": status
}, on_conflict="key").execute()
except Exception as e:
st.error(f"Failed to update maintenance mode: {e}")

is_maintenance = check_maintenance_mode()

If not authenticated, show login page

if not st.session_state.authenticated:
if is_maintenance:
admin_email_secret = st.secrets.get("admin_email", "")
st.markdown(
"""

.maintenance-container {
max-width: 600px;
margin: 4rem auto;
padding: 3rem;
background: rgba(14, 17, 23, 0.85) !important;
border: 2px solid #ffb703 !important;
border-radius: 20px !important;
box-shadow: 0 0 30px rgba(255, 183, 3, 0.25), 0 12px 40px rgba(0, 0, 0, 0.6) !important;
backdrop-filter: blur(16px) !important;
text-align: center;
}
.maintenance-container h1 {
color: #ffb703 !important;
font-size: 2.2rem;
font-weight: 800;
margin-bottom: 1rem;
}
.maintenance-container p {
color: #e6edf3;
font-size: 1.1rem;
}


🚧 SITE IS UNDER MAINTENANCE
We are currently upgrading our systems and performing scheduled improvements. Please check back soon!

""",
unsafe_allow_html=True,
)

    with st.expander("🔐 Admin Emergency Login Bypass"):
        with st.form("maint_admin_login"):
            m_user = st.text_input("Admin Username / Email")
            m_pass = st.text_input("Password", type="password")
            m_sub = st.form_submit_button("Bypass & Log In", type="primary")
            if m_sub:
                try:
                    res = supabase.table("users").select("*").eq("email", m_user.strip()).execute()
                    if not res.data:
                        res = supabase.table("users").select("*").eq("username", m_user.strip()).execute()
                    if res.data:
                        u_rec = res.data[0]
                        if u_rec["email"] == admin_email_secret and u_rec["password_hash"] == hash_password(m_pass):
                            st.session_state.authenticated = True
                            st.session_state.user_email = u_rec["email"]
                            st.session_state.user_name = u_rec["name"]
                            st.session_state.current_page = "Home"
                            st.success("Admin emergency bypass successful!")
                            st.rerun()
                        else:
                            st.error("Invalid admin credentials.")
                    else:
                        st.error("User not found.")
                except Exception as err:
                    st.error(f"Error: {err}")
    st.stop()

st.markdown(
    """
    <style>
    .auth-container {
        max-width: 500px;
        margin: 2rem auto;
        padding: 2.5rem;
        background: rgba(14, 17, 23, 0.75) !important;
        border: 1px solid rgba(255, 183, 3, 0.3) !important;
        border-radius: 16px !important;
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6) !important;
        backdrop-filter: blur(16px) !important;
    }
    .auth-header {
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .auth-header h1 {
        font-size: 1.8rem;
        color: #ffffff;
        font-weight: 700;
    }
    .auth-header p {
        color: #c9d1d9;
        font-size: 0.95rem;
    }
    .stForm [data-testid="stFormSubmitButton"] button {
        width: 100%;
        border-radius: 10px;
        font-weight: 700;
        padding: 0.6rem 1rem;
        background: linear-gradient(135deg, #a00037, #d90429) !important;
        color: white !important;
        border: 2px solid #ffb703 !important;
        box-shadow: 0 0 10px rgba(217, 4, 41, 0.4);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="auth-header">
        <h1>📚 Student Academic & Attendance Hub</h1>
        <p>Secure Cloud Portal • Analytics, Timetables & Materials</p>
    </div>
    """,
    unsafe_allow_html=True,
)

col_spacer1, col_auth, col_spacer2 = st.columns([1, 2, 1])

with col_auth:
    tab_login, tab_register, tab_forgot = st.tabs(
        ["🔑 Login", "📝 Register", "🔄 Reset"]
    )

    with tab_login:
        st.markdown("### Welcome Back!")
        with st.form("login_form"):
            login_user = st.text_input("Username")
            login_pass = st.text_input("Password", type="password")
            submit_login = st.form_submit_button("Log In to Dashboard", type="primary")

            if submit_login:
                if not login_user or not login_pass:
                    st.error("Please enter both username and password.")
                else:
                    try:
                        clean_username = login_user.strip()
                        response = (
                            supabase.table("users")
                            .select("*")
                            .eq("username", clean_username)
                            .execute()
                        )
                        if not response.data:
                            response = (
                                supabase.table("users")
                                .select("*")
                                .eq("email", clean_username)
                                .execute()
                            )

                        if response.data:
                            db_user = response.data[0]
                            hashed_input = hash_password(login_pass)
                            if db_user["password_hash"] == hashed_input:
                                admin_email_secret = st.secrets.get("admin_email", "")
                                if is_maintenance and db_user["email"] != admin_email_secret:
                                    st.error("🚧 SITE IS UNDER MAINTENANCE. Regular logins are currently disabled.")
                                else:
                                    st.session_state.authenticated = True
                                    st.session_state.user_email = db_user["email"]
                                    st.session_state.user_name = db_user["name"]
                                    st.session_state.current_page = "Home"
                                    st.success("Login successful! Loading dashboard...")
                                    st.rerun()
                            else:
                                st.error("Incorrect password. Please check your credentials.")
                        else:
                            st.error("Username or email does not exist.")
                    except Exception as err:
                        st.error(f"Database error during login: {err}")

    with tab_register:
        st.markdown("### Create New Account")
        with st.form("register_form"):
            new_user = st.text_input("Choose Username")
            new_name = st.text_input("Full Name")
            new_email = st.text_input("Email Address")
            new_pass = st.text_input("Password", type="password")
            submit_reg = st.form_submit_button("Create Account")

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
                            "Account created successfully! Switch to the Login tab."
                        )
                    except Exception as err:
                        st.error(
                            f"Registration failed (Username/Email taken): {err}"
                        )

    with tab_forgot:
        st.markdown("### Password Recovery")

        if st.session_state.reset_step == 1:
            with st.form("forgot_step1_form"):
                reset_email_input = st.text_input("Registered Email Address")
                submit_send_otp = st.form_submit_button("Send OTP Code", type="primary")

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
                                    st.success(f"OTP sent to: {masked_email}")
                                    st.rerun()
                                else:
                                    st.error("Failed to send email. Try again.")
                            else:
                                st.error("No account found with this email.")
                        except Exception as err:
                            st.error(f"Database error: {err}")

        elif st.session_state.reset_step == 2:
            with st.form("forgot_step2_form"):
                st.info(f"Resetting for: **{st.session_state.reset_email}**")
                entered_otp = st.text_input("Enter 6-digit OTP")
                new_reset_pass = st.text_input("New Password", type="password")
                confirm_reset_pass = st.text_input("Confirm Password", type="password")
                
                col_sub, col_back = st.columns(2)
                with col_sub:
                    submit_verify = st.form_submit_button("Update Password", type="primary")
                with col_back:
                    submit_cancel = st.form_submit_button("Cancel")

                if submit_cancel:
                    st.session_state.reset_step = 1
                    st.session_state.reset_email = None
                    st.rerun()

                if submit_verify:
                    if not entered_otp or not new_reset_pass or not confirm_reset_pass:
                        st.error("Please fill in all fields.")
                    elif new_reset_pass != confirm_reset_pass:
                        st.error("Passwords do not match.")
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
                                    st.error("OTP has expired.")
                                else:
                                    new_hashed_pass = hash_password(new_reset_pass)
                                    supabase.table("users").update({
                                        "password_hash": new_hashed_pass,
                                        "reset_otp": None,
                                        "otp_expiry": None
                                    }).eq("email", st.session_state.reset_email).execute()
                                    
                                    st.success("Password successfully updated! Please log in.")
                                    st.session_state.reset_step = 1
                                    st.session_state.reset_email = None
                            else:
                                st.error("User not found.")
                        except Exception as err:
                            st.error(f"Error during update: {err}")

st.stop()


If successfully authenticated:

user_email = st.session_state.user_email
user_name = st.session_state.user_name

admin_email_secret = st.secrets.get("admin_email", "")
is_admin = admin_email_secret and user_email == admin_email_secret

if is_maintenance and not is_admin:
st.session_state.authenticated = False
st.session_state.user_email = None
st.session_state.user_name = None
st.session_state.admin_unlocked = False
st.session_state.show_admin_login = False
st.rerun()

try:
supabase.table("users").update({"last_seen": datetime.now(timezone.utc).isoformat()}).eq("email", user_email).execute()
except Exception:
pass

---------------------------------------------------------

CLOUD DATABASE HELPER FUNCTIONS

---------------------------------------------------------

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

def load_holidays_from_db(email, semester):
try:
resp = supabase.table("student_holidays").select("*").eq("user_email", email).eq("semester", semester).execute()
return resp.data if resp.data else []
except Exception:
return []

def save_holiday_to_db(email, semester, holiday_date_str, reason):
try:
supabase.table("student_holidays").insert({
"user_email": email,
"semester": semester,
"holiday_date": holiday_date_str,
"reason": reason
}).execute()
return True
except Exception as e:
st.error(f"Database error saving holiday: {e}")
return False

def is_second_or_fourth_saturday(d: date):
if d.weekday() != 5:
return False
dom = d.day
occurrence = (dom - 1) // 7 + 1
return occurrence in [2, 4]

def get_user_material_permissions(email, is_admin_user=False):
if is_admin_user:
return {"can_access": True, "can_upload": True}
try:
resp = supabase.table("study_material_permissions").select("*").eq("user_email", email).execute()
if resp.data:
return resp.data[0]
return {"can_access": False, "can_upload": False}
except Exception:
return {"can_access": False, "can_upload": False}

def load_materials_from_db(semester, email=None):
try:
resp = supabase.table("study_materials").select("*").eq("semester", semester).execute()
mats = resp.data if resp.data else []
filtered = []
for m in mats:
approved = m.get("is_approved", True)
uploader = m.get("uploader_email")
if approved or (email and uploader == email):
filtered.append(m)
return filtered
except Exception:
return []

---------------------------------------------------------

CLEAN SIDEBAR: ONLY GLOBAL SETTINGS & USER INFO

---------------------------------------------------------

st.sidebar.markdown(f"### 👋 Welcome, {user_name}")
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Global Settings")

selected_semester = st.sidebar.selectbox(
"Active Semester", [f"Semester {i}" for i in range(1, 9)]
)

default_target = st.sidebar.slider(
"Target Attendance (%)",
min_value=50.0,
max_value=95.0,
value=75.0,
step=1.0,
)

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Logout", key="logout_btn", use_container_width=True):
st.session_state.authenticated = False
st.session_state.user_email = None
st.session_state.user_name = None
st.session_state.admin_unlocked = False
st.session_state.show_admin_login = False
st.rerun()

Check for Admin Messages directed to this user

try:
msg_resp = supabase.table("admin_messages").select("*").execute()
if msg_resp.data:
for msg in msg_resp.data:
t_email = msg.get("target_email")
read_list = msg.get("read_by") if msg.get("read_by") else []
if (t_email == "ALL" or t_email == user_email) and user_email not in read_list:
st.info(f"📢 ADMIN ANNOUNCEMENT: {msg['message_text']}")
if st.button("✅ Mark as Read & Clear", key=f"read_msg_{msg['id']}"):
read_list.append(user_email)
supabase.table("admin_messages").update({"read_by": read_list}).eq("id", msg['id']).execute()
st.rerun()
except Exception:
pass

---------------------------------------------------------

SECURE ADMIN PANEL & PERSISTENT GOOGLE AUTHENTICATOR GATE

---------------------------------------------------------

if is_admin:
st.sidebar.markdown("---")
st.sidebar.markdown("### 🕵️ Admin Controls")

if not st.session_state.admin_unlocked:
    if st.sidebar.button("🔐 Enter Admin Mode", type="primary", use_container_width=True):
        st.session_state.show_admin_login = True
        st.rerun()
    admin_mode = False
else:
    col_sb1, col_sb2 = st.sidebar.columns(2)
    with col_sb1:
        if st.session_state.admin_active_tab:
            if st.button("👁️ View Hub", use_container_width=True):
                st.session_state.admin_active_tab = False
                st.rerun()
        else:
            if st.button("🕵️ Admin Panel", type="primary", use_container_width=True):
                st.session_state.admin_active_tab = True
                st.rerun()
    with col_sb2:
        if st.button("🔒 Lock Admin", use_container_width=True):
            st.session_state.admin_unlocked = False
            st.session_state.show_admin_login = False
            st.session_state.admin_active_tab = True
            st.session_state.admin_page = "AdminHome"
            st.rerun()
    
    admin_mode = st.session_state.admin_active_tab


else:
admin_mode = False

Screen Takeover for Google Authenticator prompt

if is_admin and st.session_state.show_admin_login and not st.session_state.admin_unlocked:
st.title("🔐 Secure Admin Authentication")
st.markdown("Please enter your Google Authenticator 6-digit code to access the System Administrator Dashboard.")

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
                st.session_state.admin_active_tab = True
                st.session_state.admin_page = "AdminHome"
                st.success("Authentication successful! Unlocking admin dashboard...")
                st.rerun()
            else:
                st.error("❌ Invalid Authenticator code. Please try again.")
st.stop()


---------------------------------------------------------

ADMIN DASHBOARD VIEW (HOMEPAGE + SUB-PAGES ARCHITECTURE)

---------------------------------------------------------

if is_admin and admin_mode:
def render_admin_back():
if st.button("🏠 Back to Admin Dashboard", type="secondary"):
st.session_state.admin_page = "AdminHome"
st.rerun()

current_admin_page = st.session_state.get("admin_page", "AdminHome")

if current_admin_page == "AdminHome":
    st.header("🕵️ System Administrator Dashboard")
    st.markdown("Monitor user activity, broadcast announcements, manage locked records, permissions, backups, and secret report inspections.")

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
        st.subheader("⚡ Admin Features & Modules")
        st.markdown("Select any admin tool below:")

        col_ap1, col_ap2, col_ap3 = st.columns(3)
        with col_ap1:
            if st.button("🛠️ Maintenance Mode", use_container_width=True, type="primary"):
                st.session_state.admin_page = "Maintenance"
                st.rerun()
        with col_ap2:
            if st.button("💾 Master System Backup", use_container_width=True, type="primary"):
                st.session_state.admin_page = "Backup"
                st.rerun()
        with col_ap3:
            if st.button("🔑 Permissions Manager", use_container_width=True, type="primary"):
                st.session_state.admin_page = "Permissions"
                st.rerun()

        col_ap4, col_ap5, col_ap6 = st.columns(3)
        with col_ap4:
            if st.button("📋 Material Moderation", use_container_width=True, type="primary"):
                st.session_state.admin_page = "Moderation"
                st.rerun()
        with col_ap5:
            if st.button("📢 Broadcast Hub", use_container_width=True, type="primary"):
                st.session_state.admin_page = "Broadcast"
                st.rerun()
        with col_ap6:
            if st.button("🕵️ Secret User Report Eavesdropper", use_container_width=True, type="primary"):
                st.session_state.admin_page = "Eavesdropper"
                st.rerun()

        col_ap7, _, _ = st.columns(3)
        with col_ap7:
            if st.button("🔗 Share Course Data", use_container_width=True, type="primary"):
                st.session_state.admin_page = "DataSharer"
                st.rerun()

    except Exception as err:
        st.error(f"Error loading admin dashboard metrics: {err}")

elif current_admin_page == "Maintenance":
    render_admin_back()
    st.subheader("🛠️ Maintenance Mode Control")
    current_maint_status = check_maintenance_mode()
    
    col_m1, col_m2 = st.columns([2, 2])
    with col_m1:
        st.markdown(f"Current Status: **{'🔴 ACTIVE (Site Locked for Users)'}**" if current_maint_status else "Current Status: **🟢 NORMAL (Site Accessible)**")
    with col_m2:
        if current_maint_status:
            if st.button("🟢 DISABLE MAINTENANCE MODE", type="primary", use_container_width=True):
                set_maintenance_mode(False)
                st.success("Maintenance mode disabled! Users can now log back in.")
                st.rerun()
        else:
            if st.button("🔴 ENABLE MAINTENANCE MODE", type="primary", use_container_width=True):
                set_maintenance_mode(True)
                st.warning("Maintenance mode enabled! All users have been logged out/blocked.")
                st.rerun()

elif current_admin_page == "Backup":
    render_admin_back()
    st.subheader("💾 Master System Backup & Full Asset Archive")
    st.markdown("Download a complete, comprehensive zip archive containing your master JSON database backup, all physical study material files, and a text inventory of all saved web links.")

    if st.button("📥 DOWNLOAD FULL SYSTEM & ASSETS ARCHIVE (.ZIP)", type="primary"):
        try:
            backup_data = {
                "backup_timestamp": datetime.now(timezone.utc).isoformat(),
                "users": supabase.table("users").select("*").execute().data,
                "student_attendance": supabase.table("student_attendance").select("*").execute().data,
                "semester_locks": supabase.table("semester_locks").select("*").execute().data,
                "student_assignments": supabase.table("student_assignments").select("*").execute().data,
                "student_exams": supabase.table("student_exams").select("*").execute().data,
                "student_timetables": supabase.table("student_timetables").select("*").execute().data,
                "student_holidays": supabase.table("student_holidays").select("*").execute().data,
                "study_materials": supabase.table("study_materials").select("*").execute().data,
                "study_material_permissions": supabase.table("study_material_permissions").select("*").execute().data,
                "admin_messages": supabase.table("admin_messages").select("*").execute().data,
            }
            
            json_string = json.dumps(backup_data, indent=4, default=str)
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.writestr("student_hub_full_backup.json", json_string)

                materials_list = backup_data.get("study_materials", [])
                links_inventory_lines = ["STUDENT HUB - EXTERNAL LINKS INVENTORY\n" + "="*40 + "\n"]

                for mat in materials_list:
                    sem = mat.get("semester", "General")
                    title = mat.get("title", "Untitled").replace("/", "_")
                    mat_type = mat.get("material_type", "URL")
                    file_url = mat.get("file_url", "")
                    sub_code = mat.get("subject_code", "GEN")

                    if mat_type == "URL" or not file_url.startswith("http"):
                        links_inventory_lines.append(f"Semester: {sem}\nSubject: {sub_code}\nTitle: {title}\nURL: {file_url}\n{'-'*30}\n")
                    else:
                        try:
                            resp = requests.get(file_url, timeout=10)
                            if resp.status_code == 200:
                                ext = file_url.split(".")[-1].split("?")[0]
                                file_name_in_zip = f"{sem}/{sub_code}_{title}.{ext}"
                                zip_file.writestr(file_name_in_zip, resp.content)
                        except Exception:
                            pass

                zip_file.writestr("links_inventory.txt", "".join(links_inventory_lines))

            zip_buffer.seek(0)
            st.download_button(
                label="💾 Click Here to Save Complete Archive (.ZIP)",
                data=zip_buffer,
                file_name=f"student_hub_complete_archive_{date.today()}.zip",
                mime="application/zip",
                type="primary"
            )
            st.success("✅ Complete archive generated successfully!")
        except Exception as backup_err:
            st.error(f"❌ Failed to generate full system archive: {backup_err}")

elif current_admin_page == "Permissions":
    render_admin_back()
    st.subheader("🔑 Notes & Study Material Access Control Manager")
    try:
        users_resp = supabase.table("users").select("username, name, email").execute()
        users_list = users_resp.data if users_resp.data else []
        all_user_emails = [u["email"] for u in users_list if u["email"] != user_email]
        if all_user_emails:
            perm_target_user = st.selectbox("Select User to Manage Permissions", options=all_user_emails)
            curr_perms = get_user_material_permissions(perm_target_user)
            
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                grant_access = st.checkbox("Can View Notes & Materials Hub", value=curr_perms.get("can_access", False))
            with col_p2:
                grant_upload = st.checkbox("Can Upload Notes & Files", value=curr_perms.get("can_upload", False))

            if st.button("💾 SAVE PERMISSIONS", type="primary"):
                supabase.table("study_material_permissions").upsert({
                    "user_email": perm_target_user,
                    "can_access": grant_access,
                    "can_upload": grant_upload
                }, on_conflict="user_email").execute()
                st.success(f"Updated permissions for **{perm_target_user}**!")
                st.rerun()
    except Exception as e:
        st.error(f"Error loading permissions: {e}")

elif current_admin_page == "Moderation":
    render_admin_back()
    st.subheader("📋 Study Material Moderation & Approval Queue")
    try:
        pending_resp = supabase.table("study_materials").select("*").eq("is_approved", False).execute()
        pending_materials = pending_resp.data if pending_resp.data else []
        if pending_materials:
            st.info(f"There are **{len(pending_materials)}** study material(s) waiting for approval.")
            for p_mat in pending_materials:
                with st.container():
                    col_pm1, col_pm2, col_pm3, col_pm4 = st.columns([2, 2, 2, 2])
                    with col_pm1:
                        st.markdown(f"**[{p_mat['subject_code']}] {p_mat['title']}**")
                        st.caption(f"Sem: {p_mat['semester']} | Type: `{p_mat['material_type']}`")
                    with col_pm2:
                        st.caption(f"Uploaded by: `{p_mat['uploader_email']}`")
                        if p_mat.get("description"):
                            st.caption(f"Desc: {p_mat['description']}")
                    with col_pm3:
                        st.markdown(f"🔗 [Open Link]({p_mat['file_url']})")
                    with col_pm4:
                        col_ap_btn1, col_ap_btn2 = st.columns(2)
                        with col_ap_btn1:
                            if st.button("✅ Approve", key=f"appr_{p_mat['id']}"):
                                supabase.table("study_materials").update({"is_approved": True}).eq("id", p_mat['id']).execute()
                                st.success("Material approved!")
                                st.rerun()
                        with col_ap_btn2:
                            if st.button("❌ Reject", key=f"rej_{p_mat['id']}"):
                                supabase.table("study_materials").delete().eq("id", p_mat['id']).execute()
                                st.success("Material rejected & deleted.")
                                st.rerun()
                    st.divider()
        else:
            st.success("🎉 No pending study materials in the queue. All clear!")
    except Exception as mod_err:
        st.error(f"Error loading moderation queue: {mod_err}")

elif current_admin_page == "Broadcast":
    render_admin_back()
    st.subheader("📢 Direct Messaging & Broadcast Hub")
    try:
        users_resp = supabase.table("users").select("email").execute()
        users_list = users_resp.data if users_resp.data else []
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
    except Exception as e:
        st.error(f"Error: {e}")

elif current_admin_page == "Eavesdropper":
    render_admin_back()
    st.subheader("🕵️ Secret User Report Eavesdropper")
    st.markdown("Select any registered user and semester to silently email their academic breakdown report directly to your admin inbox without their knowledge.")
    try:
        users_resp = supabase.table("users").select("name, email").execute()
        users_list = users_resp.data if users_resp.data else []
        if users_list:
            user_options = {f"{u['name']} ({u['email']})": u['email'] for u in users_list}
            sel_user_label = st.selectbox("Select Target Student", options=list(user_options.keys()))
            target_student_email = user_options[sel_user_label]
            target_sem = st.selectbox("Select Semester", options=[f"Semester {i}" for i in range(1, 9)])

            if st.button("🕵️ SILENTLY SEND STUDENT REPORT TO MY ADMIN EMAIL", type="primary"):
                student_sem_data = load_data_from_db(target_student_email)
                subj_list = student_sem_data.get(target_sem, [])
                
                sem_weighted_gp = 0.0
                sem_credits = 0
                rows_html = ""
                for s in subj_list:
                    att = s["attended"]
                    cond = s["conducted"]
                    pct = (att / cond * 100) if cond > 0 else 0.0
                    gp = s.get("grade_point", 0.0)
                    sem_weighted_gp += s["credits"] * gp
                    sem_credits += s["credits"]
                    
                    rows_html += f"""
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;">{s['code']}</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{s['name']}</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{pct:.1f}% ({att}/{cond})</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{gp}</td>
                    </tr>
                    """
                
                sgpa = (sem_weighted_gp / sem_credits) if sem_credits > 0 else 0.0

                secret_report_html = f"""
                <div style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: auto; padding: 20px; border: 2px solid #d90429; border-radius: 10px;">
                    <h2 style="color: #d90429; text-align: center;">🕵️ Secret Surveillance Report</h2>
                    <p><b>Target Student:</b> {target_student_email}</p>
                    <p><b>Semester:</b> {target_sem}</p>
                    <p><b>Calculated SGPA:</b> {sgpa:.2f} / 10.0</p>
                    <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                        <thead>
                            <tr style="background: #f4f4f4;">
                                <th style="padding: 8px; border: 1px solid #ddd;">Code</th>
                                <th style="padding: 8px; border: 1px solid #ddd;">Subject</th>
                                <th style="padding: 8px; border: 1px solid #ddd;">Attendance</th>
                                <th style="padding: 8px; border: 1px solid #ddd;">Grade Point</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html if rows_html else '<tr><td colspan="4" style="text-align:center; padding:10px;">No subjects found for this semester.</td></tr>'}
                        </tbody>
                    </table>
                    <p style="font-size: 11px; color: #777; margin-top: 20px; text-align: center;">Generated silently by System Eavesdropper Module.</p>
                </div>
                """

                success_sent = send_report_email(user_email, f"🕵️ Eavesdrop Report: {target_student_email} - {target_sem}", secret_report_html)
                if success_sent:
                    st.success(f"✅ Successfully and silently dispatched **{target_student_email}**'s report to your inbox (`{user_email}`)!")
                else:
                    st.error("❌ Failed to dispatch email. Please check Resend API configuration.")
    except Exception as eavesdrop_err:
        st.error(f"Error during eavesdropping: {eavesdrop_err}")

elif current_admin_page == "DataSharer":
    render_admin_back()
    st.subheader("🔗 Share Course Data / Timetable Cloner")
    st.markdown("Easily clone your subject structures (names, codes, credits) or timetable slots into another student's account without exposing your attendance numbers or grades.")

    try:
        users_resp = supabase.table("users").select("name, email").execute()
        users_list = users_resp.data if users_resp.data else []
        other_users = [u for u in users_list if u["email"] != user_email]

        if other_users:
            user_options = {f"{u['name']} ({u['email']})": u['email'] for u in other_users}
            target_user_label = st.selectbox("Select Recipient Student", options=list(user_options.keys()))
            target_user_email = user_options[target_user_label]
            
            target_sem = st.selectbox("Select Semester to Populate", options=[f"Semester {i}" for i in range(1, 9)])
            
            st.markdown("#### Choose What Data to Copy:")
            copy_subjects = st.checkbox("📚 Copy Subject Structure (Codes, Names & Credits)", value=True)
            copy_timetable = st.checkbox("⏰ Copy Daily Timetable Slots & Lecture Rooms", value=True)
            copy_exams = st.checkbox("📅 Copy Exam Schedule & Syllabi Outline", value=False)

            if st.button("🚀 CLONE & SHARE DATA TO STUDENT", type="primary"):
                success_msgs = []
                
                if copy_subjects:
                    admin_sem_data = load_data_from_db(user_email)
                    my_subjects = admin_sem_data.get(target_sem, [])
                    if my_subjects:
                        cleaned_subjects = []
                        for s in my_subjects:
                            cleaned_subjects.append({
                                "code": s["code"],
                                "name": s["name"],
                                "credits": s["credits"],
                                "attended": 0,
                                "conducted": 0,
                                "grade_point": 0.0,
                                "attendance_date": str(date.today()),
                            })
                        save_data_to_db(target_user_email, target_sem, cleaned_subjects)
                        success_msgs.append(f"Copied {len(cleaned_subjects)} subjects")
                    else:
                        st.warning(f"You have no subjects saved in your own {target_sem} to share.")

                if copy_timetable:
                    my_tt = load_timetable_from_db(user_email, target_sem)
                    if my_tt:
                        for tt_slot in my_tt:
                            save_timetable_to_db(
                                target_user_email,
                                target_sem,
                                tt_slot["day_of_week"],
                                tt_slot["subject_code"],
                                tt_slot["start_time"],
                                tt_slot["end_time"],
                                tt_slot.get("room_number", "N/A")
                            )
                        success_msgs.append(f"Copied {len(my_tt)} timetable slots")
                    else:
                        st.warning(f"You have no timetable slots saved in your own {target_sem} to share.")

                if copy_exams:
                    my_exams = load_exams_from_db(user_email, target_sem)
                    if my_exams:
                        for ex in my_exams:
                            save_exam_to_db(
                                target_user_email,
                                target_sem,
                                ex["subject_code"],
                                ex["exam_type"],
                                ex["exam_date"],
                                ex.get("syllabus", "")
                            )
                        success_msgs.append(f"Copied {len(my_exams)} exam schedules")
                    else:
                        st.warning(f"You have no exams saved in your own {target_sem} to share.")

                if success_msgs:
                    st.success(f"✅ Successfully shared: {', '.join(success_msgs)} to **{target_user_email}** for {target_sem}!")
        else:
            st.info("No other registered users found in the system.")
    except Exception as share_err:
        st.error(f"Error while sharing data: {share_err}")

st.stop()


---------------------------------------------------------

REGULAR STUDENT DATA LOADERS

---------------------------------------------------------

st.session_state.sem_locks = load_locks_from_db(user_email)
st.session_state.all_semesters = load_data_from_db(user_email)

is_locked = st.session_state.sem_locks.get(selected_semester, False)
current_subjects = st.session_state.all_semesters[selected_semester]

Helper function for back button

def render_back_button():
if st.button("🏠 Back to Home Dashboard", type="secondary"):
st.session_state.current_page = "Home"
st.rerun()

=========================================================

PAGE ROUTING (HOME vs MODULES)

=========================================================

current_page = st.session_state.current_page

---------------------------------------------------------

HOME PAGE

---------------------------------------------------------

if current_page == "Home":
st.title("📚 Student Academic & Attendance Hub")
st.markdown(f"Welcome back, {user_name}! Here is your quick academic overview.")

overall_weighted_gp = 0.0
overall_credits = 0
total_subjects_count = 0
for sem, subj_list in st.session_state.all_semesters.items():
    if subj_list:
        for s in subj_list:
            total_subjects_count += 1
            overall_weighted_gp += s["credits"] * s.get("grade_point", 0.0)
            overall_credits += s["credits"]

cgpa = (overall_weighted_gp / overall_credits) if overall_credits > 0 else 0.0

c_m1, c_m2, c_m3 = st.columns(3)
with c_m1:
    st.metric(label="Overall CGPA", value=f"{cgpa:.2f} / 10.0")
with c_m2:
    st.metric(label="Active Semester", value=selected_semester)
with c_m3:
    st.metric(label="Total Registered Subjects", value=total_subjects_count)

st.markdown("---")
st.subheader("⚡ Quick Navigation & Modules")
st.markdown("Click any button below to open the module:")

col_btn1, col_btn2, col_btn3 = st.columns(3)
with col_btn1:
    if st.button("📚 Attendance & SGPA Manager", use_container_width=True, type="primary"):
        st.session_state.current_page = "Attendance"
        st.rerun()
with col_btn2:
    if st.button("📝 Assignments & Tasks", use_container_width=True, type="primary"):
        st.session_state.current_page = "Assignments"
        st.rerun()
with col_btn3:
    if st.button("📅 Exams & Timetable", use_container_width=True, type="primary"):
        st.session_state.current_page = "Exams"
        st.rerun()

user_perms_home = get_user_material_permissions(user_email, is_admin)
has_notes_access = user_perms_home.get("can_access", False)

if has_notes_access:
    col_btn4, col_btn5, _ = st.columns(3)
    with col_btn4:
        if st.button("⏰ Daily Schedule", use_container_width=True, type="primary"):
            st.session_state.current_page = "Schedule"
            st.rerun()
    with col_btn5:
        if st.button("📖 Notes & Study Material", use_container_width=True, type="primary"):
            st.session_state.current_page = "Notes"
            st.rerun()
else:
    col_btn4, _ = st.columns(2)
    with col_btn4:
        if st.button("⏰ Daily Schedule", use_container_width=True, type="primary"):
            st.session_state.current_page = "Schedule"
            st.rerun()

st.markdown("---")
st.subheader("📅 Today's Schedule Overview")
current_day_name = get_ist_time().strftime("%A")
all_timetable_entries = load_timetable_from_db(user_email, selected_semester)
today_entries = [t for t in all_timetable_entries if t.get("day_of_week") == current_day_name]

if today_entries:
    for entry in today_entries:
        st.info(f"🕒 **{entry['start_time']} - {entry['end_time']}** | Subject: **[{entry['subject_code']}]** | Room: `{entry['room_number']}`")
else:
    st.success(f"🎉 No classes scheduled for today ({current_day_name})!")


---------------------------------------------------------

ATTENDANCE & SGPA MANAGER PAGE (WITH UNIFIED ANALYTICS & FEASIBILITY TABLE)

---------------------------------------------------------

elif current_page == "Attendance":
render_back_button()
st.title("📚 Attendance & SGPA Management")

att_sub_mode = st.radio(
    "Select Action",
    options=["📊 Calculation & Analytics Dashboard", "📌 Add New Subjects", "🔄 Update Existing Records"],
    horizontal=True
)

if att_sub_mode == "📌 Add New Subjects":
    st.header(f"📌 Add Subjects: {selected_semester}")
    if is_locked:
        st.warning(f"🔒 {selected_semester} is permanently fixed/locked. No further modifications can be made.")
    else:
        with st.form(f"add_subject_form_{selected_semester}", clear_on_submit=True):
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

elif att_sub_mode == "🔄 Update Existing Records":
    st.header(f"🔄 Update Records: {selected_semester}")
    if is_locked:
        st.warning(f"🔒 {selected_semester} is permanently fixed/locked. Records cannot be updated.")
    else:
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
                    if st.button("🗑️ Delete Subject", key=f"del_{selected_semester}_{i}"):
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
            st.info(f"No subjects found for {selected_semester}.")

elif att_sub_mode == "📊 Calculation & Analytics Dashboard":
    st.header(f"📊 Unified Calculation & Exam Feasibility Dashboard ({selected_semester})")
    sem_subjects = current_subjects

    if sem_subjects:
        # 1. Exam & Working Days Calculation
        exams_list = load_exams_from_db(user_email, selected_semester)
        exam_countdown_banner = None
        remaining_periods_per_subject = {s["code"]: 0 for s in sem_subjects}
        working_days_count = 0
        has_exam_schedule = False

        if exams_list:
            exam_dates = []
            for ex in exams_list:
                dt_obj = datetime.fromisoformat(ex["exam_date"])
                if dt_obj.tzinfo is not None:
                    dt_obj = dt_obj.astimezone(IST)
                exam_dates.append(dt_obj.date())
            
            first_exam_date = min(exam_dates)
            today_date = date.today()
            days_left_to_exam = (first_exam_date - today_date).days

            if days_left_to_exam > 0:
                has_exam_schedule = True
                custom_holidays_data = load_holidays_from_db(user_email, selected_semester)
                holiday_set = {h["holiday_date"] for h in custom_holidays_data}
                timetable_slots = load_timetable_from_db(user_email, selected_semester)

                schedule_map = {}
                for slot in timetable_slots:
                    dname = slot["day_of_week"]
                    schedule_map.setdefault(dname, []).append(slot["subject_code"])

                curr = today_date + timedelta(days=1)
                while curr < first_exam_date:
                    is_sunday = (curr.weekday() == 6)
                    is_2nd_4th_sat = is_second_or_fourth_saturday(curr)
                    is_custom_holiday = (str(curr) in holiday_set)

                    if not is_sunday and not is_2nd_4th_sat and not is_custom_holiday:
                        working_days_count += 1
                        day_name = curr.strftime("%A")
                        day_subjects = schedule_map.get(day_name, [])
                        for scode in day_subjects:
                            if scode in remaining_periods_per_subject:
                                remaining_periods_per_subject[scode] += 1
                    curr += timedelta(days=1)

                st.info(f"⏳ **Exam Countdown:** {days_left_to_exam} calendar day(s) until your first exam on **{first_exam_date}** | 🏫 **{working_days_count} Working Days** remaining.")
            else:
                st.warning(f"ℹ️ First exam date ({first_exam_date}) has passed or is today.")
        else:
            st.caption("💡 *Tip: Log exam dates in the Exams page to calculate exact class periods left before exams.*")

        # 2. Build Unified Analytical Table
        att_data = []
        sem_weighted_gp = 0.0
        sem_credits = 0

        for idx, subj in enumerate(sem_subjects, 1):
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

            row_dict = {
                "S.No.": idx,
                "Code": subj["code"],
                "Subject": subj["name"],
                "Credits": subj["credits"],
                "Current Attendance": f"{pct:.1f}% ({att}/{cond})",
                "Status / Skips": current_status,
                "Grade Point": subj.get("grade_point", 0.0),
            }

            if has_exam_schedule:
                rem_classes = remaining_periods_per_subject.get(subj["code"], 0)
                proj_attended = att + rem_classes
                proj_conducted = cond + rem_classes
                proj_pct = (proj_attended / proj_conducted * 100) if proj_conducted > 0 else 0.0

                if proj_pct >= default_target:
                    feas_badge = f"✅ Feasible ({proj_pct:.1f}%)"
                else:
                    feas_badge = f"❌ At Risk ({proj_pct:.1f}%)"

                row_dict["Classes Left"] = rem_classes
                row_dict["Max Projected %"] = f"{proj_pct:.1f}%"
                row_dict["Exam Feasibility"] = feas_badge

            att_data.append(row_dict)
            sem_weighted_gp += subj["credits"] * subj.get("grade_point", 0.0)
            sem_credits += subj["credits"]

        df = pd.DataFrame(att_data)
        df.set_index("S.No.", inplace=True)
        sgpa = (sem_weighted_gp / sem_credits) if sem_credits > 0 else 0.0

        st.metric(label=f"Current {selected_semester} SGPA", value=f"{sgpa:.2f} / 10.0")
        st.markdown("---")
        st.subheader("📋 Comprehensive Academic & Attendance Analysis Table")
        
        # Display larger unified dataframe with full column width
        st.dataframe(df, use_container_width=True, height=len(df)*45 + 40)

        # Bar Chart Visualizer
        chart_df = []
        for subj in sem_subjects:
            att = subj["attended"]
            cond = subj["conducted"]
            pct = (att / cond * 100) if cond > 0 else 0.0
            chart_df.append({"Code": subj["code"], "Percentage": round(pct, 2)})
        
        df_chart = pd.DataFrame(chart_df)
        fig_bar = px.bar(
            df_chart,
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

        st.markdown("---")
        st.subheader("📧 Email Report Dispatcher")
        if st.button("🚀 DISPATCH REPORT TO MY EMAIL", type="primary", use_container_width=True):
            rows_html = ""
            for idx, row in df.iterrows():
                rows_html += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">{row['Code']}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{row['Subject']}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{row['Current Attendance']}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{row['Status / Skips']}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{row['Grade Point']}</td>
                </tr>
                """

            html_body = f"""
            <div style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 10px;">
                <h2 style="color: #d90429; text-align: center;">🎓 Student Academic Hub</h2>
                <p>Hello <b>{user_name}</b>,</p>
                <p>Here is your official academic performance report for <b>{selected_semester}</b>:</p>
                <ul>
                    <li>📅 <b>Semester:</b> {selected_semester}</li>
                    <li>📊 <b>Current SGPA:</b> {sgpa:.2f} / 10.0</li>
                </ul>
            </div>
            """
            if send_report_email(user_email, f"📊 Academic Report - {selected_semester}", html_body):
                st.success(f"Successfully sent the report to **{user_email}**!")
            else:
                st.error("Failed to send email.")
    else:
        st.info(f"No subjects recorded for {selected_semester}.")


---------------------------------------------------------

ASSIGNMENTS & TASKS PAGE

---------------------------------------------------------

elif current_page == "Assignments":
render_back_button()
st.title(f"📝 Assignment & Task Tracker ({selected_semester})")

if not current_subjects:
    st.info("ℹ️ Please add subjects in the Attendance manager first.")
else:
    subject_options = [f"[{s['code']}] {s['name']}" for s in current_subjects]
    
    with st.expander("➕ Add New Assignment / Project Submission", expanded=True):
        with st.form("add_assignment_form", clear_on_submit=True):
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                sel_sub_str = st.selectbox("Select Subject", options=subject_options)
                asgn_title = st.text_input("Assignment Title", placeholder="e.g. Lab Report #3")
            with col_a2:
                due_date_val = st.date_input("Due Date", value=date.today() + timedelta(days=7))
                due_time_val = st.time_input("Due Time", value=datetime.strptime("23:59", "%H:%M").time())
            
            assignment_link = st.text_input("Assignment Link or File Path (Optional)")
            submit_asgn = st.form_submit_button("Add Assignment", type="primary")
            
            if submit_asgn:
                if not asgn_title.strip():
                    st.error("Please enter an assignment title.")
                else:
                    sub_code = sel_sub_str.split("]")[0].replace("[", "")
                    combined_dt = datetime.combine(due_date_val, due_time_val).replace(tzinfo=IST)
                    save_assignment_to_db(user_email, selected_semester, sub_code, asgn_title.strip(), combined_dt.isoformat(), assignment_link.strip() if assignment_link else None)
                    st.success(f"Added assignment '{asgn_title}'!")
                    st.rerun()

    st.markdown("---")
    st.subheader("📋 Active Assignments")
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
                timer_str = "⚠️ **OVERDUE**"
                status_badge = "🔴 Past Due"

            with st.container():
                col_b1, col_b2, col_b3 = st.columns([3, 2, 1])
                with col_b1:
                    st.markdown(f"**[{sub_code}] {title}** ({status_badge})")
                    if f_url:
                        if f_url.startswith("http://") or f_url.startswith("https://"):
                            st.markdown(f"🔗 [Open Link]({f_url})")
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
        st.info("No assignments recorded for this semester.")


---------------------------------------------------------

EXAMS & TIMETABLE PAGE (WITH DATE RANGE HOLIDAY MANAGER)

---------------------------------------------------------

elif current_page == "Exams":
render_back_button()
st.title(f"📅 Examination Schedule & Holiday Manager ({selected_semester})")

exam_tab1, exam_tab2 = st.tabs(["📅 Exam Schedule", "🏖️ Holiday Manager"])

with exam_tab1:
    if not current_subjects:
        st.info("ℹ️ Please add subjects in the Attendance manager first.")
    else:
        subject_options = [f"[{s['code']}] {s['name']}" for s in current_subjects]
        
        with st.expander("➕ Log New Exam Date & Syllabus", expanded=True):
            with st.form("add_exam_form", clear_on_submit=True):
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    sel_sub_exam = st.selectbox("Select Subject", options=subject_options, key="exam_sub_sel")
                    exam_type = st.selectbox("Exam Type", options=["Mid-Term Examination", "End-Term Examination", "Quiz / Test"])
                with col_e2:
                    exam_date_val = st.date_input("Exam Date", value=date.today() + timedelta(days=14))
                    exam_time_val = st.time_input("Exam Start Time", value=datetime.strptime("10:00", "%H:%M").time())
                
                exam_syllabus = st.text_area("Syllabus Outline", placeholder="e.g. Units 1 to 3")
                submit_exam = st.form_submit_button("Save Exam Schedule", type="primary")
                
                if submit_exam:
                    sub_code = sel_sub_exam.split("]")[0].replace("[", "")
                    combined_dt = datetime.combine(exam_date_val, exam_time_val).replace(tzinfo=IST)
                    save_exam_to_db(user_email, selected_semester, sub_code, exam_type, combined_dt.isoformat(), exam_syllabus.strip())
                    st.success(f"Scheduled {exam_type}!")
                    st.rerun()

        st.markdown("---")
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
            st.dataframe(pd.DataFrame(exam_rows).sort_values("Date"), use_container_width=True)
            
            for ex in exams:
                dt_obj = datetime.fromisoformat(ex["exam_date"])
                if dt_obj.tzinfo is not None:
                    dt_obj = dt_obj.astimezone(IST)
                with st.expander(f"📑 [{ex['subject_code']}] {ex['exam_type']} — {dt_obj.strftime('%d %b %Y, %I:%M %p')}"):
                    st.write(ex.get("syllabus") if ex.get("syllabus") else "No syllabus entered.")
                    if st.button("🗑️ Delete Exam Entry", key=f"del_ex_{ex['id']}"):
                        supabase.table("student_exams").delete().eq("id", ex['id']).execute()
                        st.rerun()
        else:
            st.info("No exam schedules logged.")

with exam_tab2:
    st.subheader("🏖️ Holiday Manager")
    st.markdown("Add single-day holidays or full date ranges for breaks, festivals, or study leaves.")
    
    with st.form("add_holiday_range_form", clear_on_submit=True):
        col_h1, col_h2, col_h3 = st.columns([2, 2, 3])
        with col_h1:
            h_start_date = st.date_input("Start Date", value=date.today())
        with col_h2:
            h_end_date = st.date_input("End Date (Inclusive)", value=date.today())
        with col_h3:
            h_reason = st.text_input("Holiday Reason / Title", placeholder="e.g. Diwali Vacation / Winter Break")
        
        sub_holiday = st.form_submit_button("Save Holiday / Range", type="primary")
        if sub_holiday:
            if not h_reason.strip():
                st.error("Please enter a holiday reason.")
            elif h_end_date < h_start_date:
                st.error("End Date cannot be earlier than Start Date.")
            else:
                curr_d = h_start_date
                added_count = 0
                while curr_d <= h_end_date:
                    save_holiday_to_db(user_email, selected_semester, str(curr_d), h_reason.strip())
                    curr_d += timedelta(days=1)
                    added_count += 1
                st.success(f"Successfully saved {added_count} holiday date(s)!")
                st.rerun()

    st.markdown("---")
    st.subheader("📋 Comprehensive Holiday & Off-Day Schedule")
    
    saved_holidays = load_holidays_from_db(user_email, selected_semester)
    custom_dict = {h["holiday_date"]: h for h in saved_holidays}

    # Render complete holiday schedule (Next 60 days overview)
    holiday_entries_list = []
    today = date.today()
    for i in range(0, 90):
        check_date = today + timedelta(days=i)
        d_str = str(check_date)
        
        is_sun = (check_date.weekday() == 6)
        is_sat = is_second_or_fourth_saturday(check_date)
        is_custom = d_str in custom_dict

        if is_custom or is_sun or is_sat:
            reason = custom_dict[d_str]["reason"] if is_custom else ("Sunday (Weekly Off)" if is_sun else "2nd / 4th Saturday Off")
            htype = "Custom Holiday" if is_custom else "Automatic Off Day"
            db_id = custom_dict[d_str].get("id") if is_custom else None
            
            holiday_entries_list.append({
                "date": check_date,
                "date_str": d_str,
                "day_name": check_date.strftime("%A"),
                "reason": reason,
                "type": htype,
                "id": db_id
            })

    if holiday_entries_list:
        for hol in holiday_entries_list:
            with st.container():
                col_h_info1, col_h_info2 = st.columns([5, 1])
                with col_h_info1:
                    badge_bg = "linear-gradient(135deg, rgba(160, 0, 55, 0.85), rgba(217, 4, 41, 0.85))" if hol["type"] == "Custom Holiday" else "rgba(48, 54, 61, 0.85)"
                    st.markdown(
                        f"""
                        <div style="background: rgba(22, 27, 34, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 12px 18px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 16px rgba(0,0,0,0.3); margin-bottom: 8px;">
                            <div>
                                <span style="font-weight: 700; color: #ffffff; font-size: 1.05rem;">📅 {hol['date_str']}</span>
                                <span style="color: #8b949e; font-weight: 500; margin-left: 6px;">({hol['day_name']})</span>
                                <span style="color: #c9d1d9; margin-left: 12px; font-weight: 500;">— {hol['reason']}</span>
                            </div>
                            <span style="background: {badge_bg}; color: #ffffff; padding: 4px 10px; border-radius: 8px; font-size: 0.78rem; font-weight: 600; border: 1px solid rgba(255,255,255,0.15);">{hol['type']}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                with col_h_info2:
                    if hol["id"]:
                        if st.button("🗑️ Delete", key=f"del_hol_{hol['id']}"):
                            supabase.table("student_holidays").delete().eq("id", hol['id']).execute()
                            st.rerun()
    else:
        st.info("No upcoming holidays found.")


---------------------------------------------------------

DAILY SCHEDULE PAGE (WITH MULTI-DAY TIMETABLE VIEWER)

---------------------------------------------------------

elif current_page == "Schedule":
render_back_button()
st.title(f"⏰ Daily Class Timetable ({selected_semester})")

if not current_subjects:
    st.info("ℹ️ Please add subjects in the Attendance manager first.")
else:
    subject_options = [f"[{s['code']}] {s['name']}" for s in current_subjects]
    
    with st.expander("➕ Add Class Slot to Timetable", expanded=True):
        with st.form("add_timetable_form", clear_on_submit=True):
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                tt_day = st.selectbox("Day", options=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
                tt_sub = st.selectbox("Subject", options=subject_options)
            with col_t2:
                tt_start = st.time_input("Start Time", value=datetime.strptime("09:00", "%H:%M").time())
                tt_end = st.time_input("End Time", value=datetime.strptime("10:00", "%H:%M").time())
            
            tt_room = st.text_input("Room / Lecture Hall", placeholder="e.g. LH-302")
            submit_tt = st.form_submit_button("Add to Timetable", type="primary")
            
            if submit_tt:
                sub_code = tt_sub.split("]")[0].replace("[", "")
                save_timetable_to_db(user_email, selected_semester, tt_day, sub_code, tt_start.strftime("%I:%M %p"), tt_end.strftime("%I:%M %p"), tt_room.strip() if tt_room else "N/A")
                st.success("Added to timetable!")
                st.rerun()

    st.markdown("---")
    current_day_name = get_ist_time().strftime("%A")
    st.subheader("📅 Timetable Viewer by Day")
    
    days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    default_index = days_list.index(current_day_name) if current_day_name in days_list else 0
    
    selected_day_view = st.selectbox(
        "Select Day to View Timetable",
        options=days_list,
        index=default_index
    )
    
    all_timetable_entries = load_timetable_from_db(user_email, selected_semester)
    day_entries = [t for t in all_timetable_entries if t.get("day_of_week") == selected_day_view]
    
    if day_entries:
        for entry in day_entries:
            with st.container():
                col_c1, col_c2, col_c3 = st.columns([2, 3, 1])
                with col_c1:
                    st.markdown(f"🕒 **{entry['start_time']} - {entry['end_time']}**")
                with col_c2:
                    st.markdown(f"📚 **[{entry['subject_code']}]** | Room: `{entry['room_number']}`")
                with col_c3:
                    if st.button("🗑️ Remove", key=f"del_tt_{entry['id']}_{selected_day_view}"):
                        supabase.table("student_timetables").delete().eq("id", entry['id']).execute()
                        st.rerun()
                st.divider()
    else:
        st.info(f"🎉 No classes scheduled for {selected_day_view}!")


---------------------------------------------------------

NOTES & STUDY MATERIAL PAGE

---------------------------------------------------------

elif current_page == "Notes":
render_back_button()
st.title(f"📖 Notes & Study Material Repository ({selected_semester})")

user_perms = get_user_material_permissions(user_email, is_admin)

if not user_perms.get("can_access", False):
    st.warning("🔒 **Access Restricted:** You do not have permission to view study materials. Contact an Admin.")
else:
    if user_perms.get("can_upload", False):
        with st.expander("➕ Upload Study Material / Reference Link", expanded=False):
            with st.form("upload_material_form", clear_on_submit=True):
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    mat_sub = st.text_input("Subject Code", placeholder="e.g. TCS-401")
                    mat_title = st.text_input("Resource Title", placeholder="e.g. Lecture Notes")
                with col_m2:
                    mat_type = st.selectbox("Type", options=["External URL / Website Link", "PDF Document", "Word Document (.docx)", "Text File (.txt)", "Photo / Diagram"])
                    mat_desc = st.text_input("Description (Optional)")

                tab_upload_link, tab_upload_file = st.tabs(["🔗 External URL Link", "📁 Upload File to Cloud"])
                with tab_upload_link:
                    mat_link_input = st.text_input("Web Link (URL)")
                with tab_upload_file:
                    uploaded_file = st.file_uploader("Choose File", type=["pdf", "docx", "txt", "png", "jpg", "jpeg"])

                submit_material = st.form_submit_button("🚀 Upload & Save Resource", type="primary")

                if submit_material:
                    if not mat_sub.strip() or not mat_title.strip():
                        st.error("Please enter Subject Code and Title.")
                    else:
                        final_url = None
                        saved_type = "URL"
                        if uploaded_file is not None:
                            try:
                                file_bytes = uploaded_file.read()
                                ext = uploaded_file.name.split(".")[-1]
                                file_path = f"{selected_semester}/{user_email}_{int(datetime.now().timestamp())}.{ext}"
                                supabase.storage.from_("study_materials").upload(file_path, file_bytes)
                                final_url = supabase.storage.from_("study_materials").get_public_url(file_path)
                                saved_type = ext.upper()
                            except Exception as storage_err:
                                st.error(f"Storage upload error: {storage_err}")
                        elif mat_link_input.strip():
                            final_url = mat_link_input.strip()
                            saved_type = "URL"

                        if final_url:
                            supabase.table("study_materials").insert({
                                "uploader_email": user_email,
                                "semester": selected_semester,
                                "subject_code": mat_sub.strip().upper(),
                                "title": mat_title.strip(),
                                "description": mat_desc.strip() if mat_desc else "",
                                "material_type": saved_type,
                                "file_url": final_url,
                                "is_approved": is_admin
                            }).execute()
                            st.success("Resource uploaded successfully! Awaiting admin approval." if not is_admin else "Resource uploaded and published successfully!")
                            st.rerun()

    st.markdown("---")
    materials = load_materials_from_db(selected_semester, user_email)
    if materials:
        for mat in materials:
            is_approved = mat.get("is_approved", True)
            status_label = "" if is_approved else " ⏳ *(Pending Admin Approval)*"
            
            with st.container():
                col_res1, col_res2, col_res3 = st.columns([3, 2, 1])
                with col_res1:
                    st.markdown(f"**[{mat['subject_code']}] {mat['title']}** (`{mat['material_type']}`){status_label}")
                    if mat.get("description"):
                        st.caption(mat["description"])
                    st.caption(f"Uploaded by: `{mat['uploader_email']}`")
                with col_res2:
                    st.markdown(f"🔗 [Open Link]({mat['file_url']})")
                    if mat["file_url"].startswith("http"):
                        try:
                            res = requests.get(mat["file_url"], timeout=5)
                            if res.status_code == 200:
                                file_ext = mat["file_url"].split(".")[-1].split("?")[0]
                                st.download_button(
                                    label="💾 Download",
                                    data=res.content,
                                    file_name=f"{mat['subject_code']}_{mat['title']}.{file_ext}",
                                    key=f"dl_btn_{mat['id']}"
                                )
                        except Exception:
                            pass
                with col_res3:
                    if is_admin or mat["uploader_email"] == user_email:
                        if st.button("🗑️ Delete", key=f"del_mat_{mat['id']}"):
                            supabase.table("study_materials").delete().eq("id", mat['id']).execute()
                            st.rerun()
                st.divider()
    else:
        st.info("No approved study materials available for this semester.")
