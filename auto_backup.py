"""
Automatic database backup for the Student Hub.

Runs on GitHub Actions (see .github/workflows/auto_backup.yml). It reads every row of every table
from Supabase, packs them into a .zip (same format as the admin-panel backup, so datarestoration.py
can restore it) and emails the zip to you through Resend.

Needs these GitHub repository secrets (Settings -> Secrets and variables -> Actions):
    SUPABASE_URL, SUPABASE_KEY (the secret/service key), RESEND_API_KEY, BACKUP_EMAIL_TO
Optional:
    RESEND_FROM_EMAIL   (e.g. "Student Hub <noreply@yourdomain.com>" once you have a verified domain)

NOTE: this backs up the database rows only (not uploaded files). The admin panel's
"Master System Backup" button still gives you the full archive including files.
"""
import base64
import io
import json
import os
import sys
import zipfile
from datetime import datetime, timedelta, timezone

import requests
from supabase import create_client


def need(name):
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"❌ Missing GitHub secret: {name}")
        sys.exit(1)
    return value


SUPABASE_URL = need("SUPABASE_URL")
SUPABASE_KEY = need("SUPABASE_KEY")
RESEND_API_KEY = need("RESEND_API_KEY")
BACKUP_EMAIL_TO = need("BACKUP_EMAIL_TO")
SENDER = os.environ.get("RESEND_FROM_EMAIL", "").strip() or "Student Hub <onboarding@resend.dev>"

MAX_ZIP_BYTES = 15 * 1024 * 1024  # keeps the email comfortably under Gmail's 25 MB limit

# (table, column used for stable paging)
TABLES = [
    ("users", "id"),
    ("student_attendance", "id"),
    ("semester_locks", "id"),
    ("student_assignments", "id"),
    ("student_exams", "id"),
    ("student_timetables", "id"),
    ("student_holidays", "id"),
    ("study_materials", "id"),
    ("study_material_permissions", "id"),
    ("admin_messages", "id"),
    ("system_settings", "key"),
]


def fetch_all_rows(supabase, table_name, order_by, page_size=1000):
    rows, start = [], 0
    while True:
        resp = (
            supabase.table(table_name)
            .select("*")
            .order(order_by)
            .range(start, start + page_size - 1)
            .execute()
        )
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        start += page_size
    return rows


def send_email(subject, html, attachment_name=None, attachment_bytes=None):
    payload = {"from": SENDER, "to": [BACKUP_EMAIL_TO], "subject": subject, "html": html}
    if attachment_bytes is not None:
        payload["attachments"] = [
            {"filename": attachment_name, "content": base64.b64encode(attachment_bytes).decode()}
        ]
    resp = requests.post(
        "https://api.resend.com/emails",
        json=payload,
        headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
        timeout=60,
    )
    return resp.status_code in (200, 201), resp.status_code, resp.text[:300]


def main():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    now_ist = datetime.now(timezone(timedelta(hours=5, minutes=30)))

    backup_data = {"backup_timestamp": datetime.now(timezone.utc).isoformat()}
    counts = {}
    for table_name, order_by in TABLES:
        rows = fetch_all_rows(supabase, table_name, order_by)
        backup_data[table_name] = rows
        counts[table_name] = len(rows)
        print(f"  {table_name}: {len(rows)} rows")  # counts only - never print the data itself

    json_bytes = json.dumps(backup_data, indent=4, default=str).encode("utf-8")
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("student_hub_full_backup.json", json_bytes)
    zip_bytes = zip_buffer.getvalue()
    zip_name = f"student_hub_auto_backup_{now_ist.date()}.zip"

    rows_html = "".join(f"<li>{t}: <b>{c}</b> rows</li>" for t, c in counts.items())
    if len(zip_bytes) > MAX_ZIP_BYTES:
        ok, code, text = send_email(
            f"⚠️ Student Hub backup too large to attach ({now_ist.date()})",
            "<p>The automatic backup was created but is too large to email. "
            "Please download a full backup from Admin Mode → Master System Backup.</p>"
            f"<ul>{rows_html}</ul>",
        )
        print("❌ Backup too large to attach; warning email sent." if ok else f"❌ Email failed: {code} {text}")
        sys.exit(1)

    ok, code, text = send_email(
        f"✅ Student Hub automatic backup ({now_ist.date()})",
        "<p>Your automatic database backup is attached. It contains student data and password "
        "hashes - keep it private, and restore it with <code>datarestoration.py</code>.</p>"
        f"<ul>{rows_html}</ul><p>(Database rows only - uploaded files are not included.)</p>",
        zip_name,
        zip_bytes,
    )
    if not ok:
        print(f"❌ Could not email the backup: HTTP {code} {text}")
        sys.exit(1)
    print(f"✅ Backup emailed ({len(zip_bytes) / 1024:.1f} KB).")


if __name__ == "__main__":
    main()
