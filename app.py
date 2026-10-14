from datetime import date
import json
import math
import os
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(
    page_title="Student Academic & Attendance Hub", page_icon="📚", layout="wide"
)

# Custom CSS for Neon Glowing Buttons & UI Polish
st.markdown(
    """
    <style>
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #0e1117;
        padding-top: 1rem;
    }
    
    /* Target the first sidebar navigation button (Enter Details - Red Gradient) */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child(6) button {
        width: 100%;
        border-radius: 12px;
        font-weight: 700;
        font-size: 15px;
        padding: 12px 15px;
        color: white !important;
        background: linear-gradient(135deg, #a00037, #d90429) !important;
        border: 3px solid #ffb703 !important;
        box-shadow: 0 0 15px #ffb703, inset 0 0 10px rgba(255, 255, 255, 0.2) !important;
        transition: all 0.3s ease;
    }
    
    /* Target the second sidebar navigation button (Update - Green Gradient) */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child(7) button {
        width: 100%;
        border-radius: 12px;
        font-weight: 700;
        font-size: 15px;
        padding: 12px 15px;
        color: white !important;
        background: linear-gradient(135deg, #1b4332, #2d6a4f) !important;
        border: 3px solid #ffb703 !important;
        box-shadow: 0 0 15px #ffb703, inset 0 0 10px rgba(255, 255, 255, 0.2) !important;
        transition: all 0.3s ease;
    }
    
    /* Target the third sidebar navigation button (Calculate - Blue Gradient) */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:nth-child(8) button {
        width: 100%;
        border-radius: 12px;
        font-weight: 700;
        font-size: 15px;
        padding: 12px 15px;
        color: white !important;
        background: linear-gradient(135deg, #03045e, #0077b6) !important;
        border: 3px solid #ffb703 !important;
        box-shadow: 0 0 15px #ffb703, inset 0 0 10px rgba(255, 255, 255, 0.2) !important;
        transition: all 0.3s ease;
    }
    
    /* Hover effects */
    [data-testid="stSidebar"] div.stButton button:hover {
        transform: scale(1.02);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

DATA_FILE = "attendance_data.json"
LOCK_FILE = "semester_locks.json"
SUBSCRIBERS_FILE = "telegram_users.json"
OFFSET_FILE = "telegram_offset.json"


# Load all semester data from local JSON file or return empty structure
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {f"Semester {i}": [] for i in range(1, 9)}


# Save data to local JSON file
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


# Load lock status for semesters
def load_locks():
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {f"Semester {i}": False for i in range(1, 9)}


# Save lock status
def save_locks(locks):
    with open(LOCK_FILE, "w") as f:
        json.dump(locks, f, indent=4)


# Load telegram subscribers
def load_subscribers():
    if os.path.exists(SUBSCRIBERS_FILE):
        try:
            with open(SUBSCRIBERS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


# Save telegram subscribers
def save_subscribers(subs):
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(subs, f, indent=4)


# Load telegram update offset
def load_offset():
    if os.path.exists(OFFSET_FILE):
        try:
            with open(OFFSET_FILE, "r") as f:
                return json.load(f).get("offset", 0)
        except Exception:
            pass
    return 0


# Save telegram update offset
def save_offset(offset):
    with open(OFFSET_FILE, "w") as f:
        json.dump({"offset": offset}, f)


# Fetch new subscribers via Telegram getUpdates with proper offset consumption
def fetch_telegram_updates(token):
    offset = load_offset()
    url = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                subs = load_subscribers()
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
                        username = chat.get("username", "")
                        name_label = f"{first_name} (@{username})" if username else first_name
                        if chat_id not in subs:
                            new_found = True
                        subs[chat_id] = name_label

                save_subscribers(subs)
                save_offset(max_update_id)
                return True, new_found
    except Exception:
        pass
    return False, False


# Send Telegram Alert
def send_telegram_alert(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 200
    except Exception:
        return False


st.title("📚 Student Attendance & SGPA/CGPA Tracker")

# Initialize session state for navigation mode and locks
if "nav_mode" not in st.session_state:
    st.session_state.nav_mode = "Data Entry & Management"

if "sem_locks" not in st.session_state:
    st.session_state.sem_locks = load_locks()

# Load data into session state
if "all_semesters" not in st.session_state:
    st.session_state.all_semesters = load_data()

# ---------------------------------------------------------
# SIDEBAR CONFIGURATIONS & UNIFIED SEMESTER SELECTOR
# ---------------------------------------------------------
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

# Telegram Bot Configuration via st.secrets or Sidebar Fallback
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
# VIEW 1: DATA ENTRY & MANAGEMENT (Add Only)
# ---------------------------------------------------------
if nav_mode == "Data Entry & Management":
    st.header(f"📌 Add Subjects: {selected_semester}")

    if is_locked:
        st.warning(f"🔒 {selected_semester} is permanently fixed/locked. No further modifications can be made.")
    else:
        st.markdown(f"Use the form below to register your subjects, credits, and total semester classes for **{selected_semester}**.")

        with st.form(f"add_subject_form_{selected_semester}", clear_on_submit=True):
            st.subheader("New Subject Registration")
            col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 3, 1, 1.3, 1, 1, 1])
            with col1:
                new_code = st.text_input("Subject Code", placeholder="e.g. TCS-401")
            with col2:
                new_name = st.text_input("Subject Name", placeholder="e.g. Operating Systems")
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
                    st.error("Conducted classes cannot exceed total semester classes.")
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
                    st.session_state.all_semesters[selected_semester] = current_subjects
                    save_data(st.session_state.all_semesters)
                    st.success(f"Added {new_code} - {new_name} successfully!")
                    st.rerun()

    if current_subjects:
        st.markdown("---")
        st.subheader(f"Currently Registered Subjects ({selected_semester})")
        for idx, subj in enumerate(current_subjects, 1):
            total_cls = subj.get("total_classes", 40)
            att_date = subj.get("attendance_date", str(date.today()))
            st.markdown(f"{idx}. **[{subj['code']}] {subj['name']}** (Credits: {subj['credits']}, Total: {total_cls}, Attended: {subj['attended']}/{subj['conducted']}, Grade Point: {subj['grade_point']}, Last Updated: `{att_date}`)")
    else:
        st.info(f"No subjects added for {selected_semester} yet.")

# ---------------------------------------------------------
# VIEW 2: UPDATE RECORDS (Attendance & Grade Points)
# ---------------------------------------------------------
elif nav_mode == "Update Records":
    st.header(f"🔄 Update Records: {selected_semester}")

    if is_locked:
        st.warning(f"🔒 {selected_semester} is permanently fixed/locked. Records cannot be updated.")
        if current_subjects:
            st.markdown("---")
            st.subheader(f"Locked Records ({selected_semester})")
            for idx, subj in enumerate(current_subjects, 1):
                total_cls = subj.get("total_classes", 40)
                att_date = subj.get("attendance_date", str(date.today()))
                st.markdown(f"{idx}. **[{subj['code']}] {subj['name']}** | Total: {total_cls} | Grade Point: **{subj['grade_point']}** | Attended: {subj['attended']}/{subj['conducted']} | Last Updated: `{att_date}`")
    else:
        st.markdown(f"Update your attendance numbers or final grade points for **{selected_semester}**. Changes will automatically stamp today's date.")

        if current_subjects:
            updated_subjects = []
            data_changed = False

            for i, subj in enumerate(current_subjects):
                existing_date_str = subj.get("attendance_date", str(date.today()))

                with st.expander(
                    f"📖 [{subj['code']}] {subj['name']} (Credits: {subj['credits']} | Last Updated: {existing_date_str})"
                ):
                    col_del, _ = st.columns([1, 4])
                    with col_del:
                        delete_clicked = st.button("🗑️ Delete", key=f"del_{selected_semester}_{i}")

                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        code = st.text_input("Subject Code", value=subj["code"], key=f"code_{selected_semester}_{i}")
                    with c2:
                        name = st.text_input("Subject Name", value=subj["name"], key=f"name_{selected_semester}_{i}")
                    with c3:
                        credits = st.number_input(
                            "Credits", min_value=1, max_value=10, value=int(subj["credits"]), key=f"cred_{selected_semester}_{i}"
                        )
                    with c4:
                        total_classes = st.number_input(
                            "Total Semester Classes", min_value=1, value=int(subj.get("total_classes", 40)), key=f"tot_{selected_semester}_{i}"
                        )

                    c5, c6, c7 = st.columns(3)
                    with c5:
                        attended = st.number_input(
                            "Classes Attended", min_value=0, value=int(subj["attended"]), key=f"att_{selected_semester}_{i}"
                        )
                    with c6:
                        conducted = st.number_input(
                            "Classes Conducted", min_value=0, value=max(int(subj["conducted"]), attended), key=f"cond_{selected_semester}_{i}"
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
                            code.upper() != subj["code"] or
                            name != subj["name"] or
                            credits != subj["credits"] or
                            total_classes != subj.get("total_classes", 40) or
                            attended != subj["attended"] or
                            conducted != subj["conducted"] or
                            endterm != subj.get("grade_point", 0.0)
                        )

                        final_date = str(date.today()) if field_changed else existing_date_str

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
                save_data(st.session_state.all_semesters)
                st.success("Records updated successfully!")
                st.rerun()
        else:
            st.info(f"No subjects found for {selected_semester}. Please add subjects in 'Enter Details' first.")

# ---------------------------------------------------------
# VIEW 3: CALCULATION DASHBOARD (Read-Only Results + FIX + Telegram QR & Dispatch)
# ---------------------------------------------------------
elif nav_mode == "Calculation Dashboard":
    st.header(f"📊 Calculation & Analytics Dashboard ({selected_semester})")
    st.markdown("View your computed semester SGPA, cumulative CGPA, attendance percentages, and semester-long eligibility status.")

    # Calculate Overall CGPA across all semesters
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
                total_cls = subj.get("total_classes", 40)
                att_date = subj.get("attendance_date", str(date.today()))
                pct = (att / cond * 100) if cond > 0 else 0.0

                remaining_classes = max(0, total_cls - cond)
                target_ratio = default_target / 100.0
                required_total_attended = math.ceil(target_ratio * total_cls)
                needed_from_remaining = max(0, required_total_attended - att)

                if pct >= default_target:
                    margin = int((100 * att - default_target * cond) / default_target)
                    current_status = f"Safe (Can skip {margin})"
                else:
                    needed_consecutive = math.ceil((target_ratio * cond - att) / (1.0 - target_ratio))
                    current_status = f"Short (Need next {max(1, needed_consecutive)})"

                if pct >= default_target:
                    target_status = "Target Maintained"
                else:
                    if needed_from_remaining <= remaining_classes:
                        target_status = f"Need {needed_from_remaining} of {remaining_classes} left"
                    else:
                        target_status = f"Unachievable (Need {needed_from_remaining}/{remaining_classes})"

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

            # ---------------------------------------------------------
            # TELEGRAM QR CODE & SUBSCRIBER DISPATCH HUB
            # ---------------------------------------------------------
            st.markdown("---")
            st.subheader("📱 Telegram Bot Subscriber Hub & Dispatcher")
            st.markdown("Scan the QR code below to start the bot, then sync and dispatch your academic report to any subscriber.")

            col_qr, col_disp = st.columns([1, 2])

            with col_qr:
                if TELEGRAM_BOT_USERNAME:
                    bot_url = f"https://t.me/{TELEGRAM_BOT_USERNAME.strip('@')}"
                    qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={bot_url}"
                    st.image(qr_api_url, caption=f"Scan to open @{TELEGRAM_BOT_USERNAME.strip('@')}")
                else:
                    st.info("💡 Configure your **Bot Username** to generate your Telegram QR code.")

            with col_disp:
                st.markdown("#### 👥 Select Subscriber & Dispatch")
                
                c_sync, _ = st.columns([1, 1])
                with c_sync:
                    if st.button("🔄 Sync New Subscribers"):
                        if not TELEGRAM_BOT_TOKEN:
                            st.error("Please configure your Bot Token.")
                        else:
                            success, found_new = fetch_telegram_updates(TELEGRAM_BOT_TOKEN)
                            if success:
                                st.success("Subscribers synced successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to fetch updates from Telegram. Check your Bot Token.")

                subscribers = load_subscribers()
                if subscribers:
                    subscriber_options = {name: cid for cid, name in subscribers.items()}
                    selected_subscriber_label = st.selectbox(
                        "Choose Recipient", options=list(subscriber_options.keys())
                    )
                    selected_chat_id = subscriber_options.get(selected_subscriber_label)

                    if st.button("🚀 DISPATCH REPORT", type="primary", use_container_width=True):
                        if not TELEGRAM_BOT_TOKEN:
                            st.error("Please configure your Bot Token.")
                        else:
                            msg_lines = [
                                f"*🎓 GEU ACADEMIC REPORT*",
                                f"📅 *Semester:* {selected_semester}",
                                f"📊 *Current SGPA:* `{sgpa:.2f} / 10.0`",
                                f"🏆 *Overall CGPA:* `{cgpa:.2f} / 10.0`",
                                f"🎯 *Target Attendance:* `{default_target}%`",
                                f"\n*📖 Subject Breakdown:*",
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
                            sent = send_telegram_alert(TELEGRAM_BOT_TOKEN, selected_chat_id, full_report)
                            if sent:
                                st.success(f"Report successfully dispatched to {selected_subscriber_label}!")
                            else:
                                st.error("Failed to dispatch message. Ensure the user has started your bot first.")
                else:
                    st.warning("No subscribers found yet. Scan the QR code, press **Start** on your bot, and click **Sync New Subscribers**.")

            # ---------------------------------------------------------
            # FIX BUTTON & MODAL CONFIRMATION DIALOG
            # ---------------------------------------------------------
            st.markdown("---")
            st.subheader(f"🔒 Semester Fixation ({selected_semester})")

            @st.dialog("⚠️ Confirm Permanent Fixation")
            def confirm_fix_dialog(sem_name):
                st.markdown(
                    f"Are you sure you want to **permanently fix and lock {sem_name}**? "
                    "Once locked, you will no longer be able to edit subjects, attendance, or grade points for this semester."
                )
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    if st.button("✅ Yes, Lock Permanently", use_container_width=True):
                        st.session_state.sem_locks[sem_name] = True
                        save_locks(st.session_state.sem_locks)
                        st.success(f"{sem_name} has been permanently fixed!")
                        st.rerun()
                with col_c2:
                    if st.button("❌ Cancel", use_container_width=True):
                        st.rerun()

            if is_locked:
                st.success(f"🔒 Status: {selected_semester} is permanently fixed and locked.")
            else:
                if not all_grades_entered:
                    st.info(f"ℹ️ The **FIX** button will become available once final grade points (> 0.0) are entered for all subjects in {selected_semester}.")
                    st.button("🔒 FIX SEMESTER DATA", disabled=True, use_container_width=True)
                else:
                    if st.button("🔒 FIX SEMESTER DATA", type="primary", use_container_width=True):
                        confirm_fix_dialog(selected_semester)
        else:
            st.info(f"No subjects recorded for {selected_semester} yet.")