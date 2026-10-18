import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import date
from io import BytesIO
from PIL import Image
import sqlite3
import re
import smtplib
from email.mime.text import MIMEText
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# ==========================================
# 1. PAGE CONFIGURATION & DYNAMIC THEME
# ==========================================
st.set_page_config(page_title="Enterprise Attendance & Productivity Suite", layout="wide", initial_sidebar_state="expanded")

# Initialize Theme Session State
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Dark Mode"

# Theme Toggle in Sidebar
with st.sidebar:
    st.session_state.theme_mode = st.radio("🎨 Display Theme", ["Dark Mode", "Light Mode"], index=0 if st.session_state.theme_mode=="Dark Mode" else 1)

if st.session_state.theme_mode == "Dark Mode":
    st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(rgba(10, 17, 30, 0.8), rgba(15, 23, 42, 0.9)), 
                        url("https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?q=80&w=2070&auto=format&fit=crop");
            background-size: cover; background-position: center; background-attachment: fixed;
            font-family: 'Inter', sans-serif;
        }
        [data-testid="stSidebar"] { background-color: rgba(255, 255, 255, 0.95); border-right: 1px solid rgba(255, 255, 255, 0.2); }
        [data-testid="stMetric"] { background: rgba(255, 255, 255, 0.08) !important; backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.25) !important; border-radius: 14px; }
        [data-testid="stMetricLabel"] p { color: #cbd5e1 !important; font-weight: 700 !important; }
        [data-testid="stMetricValue"] { color: #ffffff !important; font-weight: 900 !important; }
        h1, h2, h3 { color: #ffffff !important; font-weight: 900; }
        p, span { color: #f1f5f9 !important; font-weight: 700; }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, 
        [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { color: #0f172a !important; text-shadow: none !important; }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        .stApp { background: #f8fafc; font-family: 'Inter', sans-serif; color: #1e293b; }
        [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e2e8f0; }
        [data-testid="stMetric"] { background: #ffffff !important; border: 1px solid #cbd5e1 !important; border-radius: 14px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
        [data-testid="stMetricLabel"] p { color: #475569 !important; }
        [data-testid="stMetricValue"] { color: #0f172a !important; }
        h1, h2, h3 { color: #0f172a !important; }
        p, span { color: #334155 !important; }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. SQLITE DATABASE FUNCTIONS & MODULES
# ==========================================
def sanitize_name(name):
    return re.sub(r'[^a-zA-Z0-9]', '_', name).lower()

def init_master_db():
    conn = sqlite3.connect("master_portal.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS companies (company_name TEXT PRIMARY KEY, company_password TEXT, logo BLOB)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS company_admins (company_name TEXT, admin_user_id TEXT, password TEXT, PRIMARY KEY (company_name, admin_user_id))''')
    conn.commit()
    conn.close()

def get_registered_companies():
    conn = sqlite3.connect("master_portal.db")
    cursor = conn.cursor()
    cursor.execute("SELECT company_name FROM companies")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def verify_admin_login(company_name, admin_user_id, password):
    conn = sqlite3.connect("master_portal.db")
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM company_admins WHERE company_name = ? AND admin_user_id = ?", (company_name, admin_user_id))
    row = cursor.fetchone()
    conn.close()
    return row and row[0] == password

def register_company_with_admins(company_name, company_password, admin_list):
    conn = sqlite3.connect("master_portal.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO companies (company_name, company_password) VALUES (?, ?)", (company_name, company_password))
    for admin_id, password in admin_list:
        if admin_id and password:
            cursor.execute("INSERT OR REPLACE INTO company_admins (company_name, admin_user_id, password) VALUES (?, ?, ?)", (company_name, admin_id, password))
    conn.commit()
    conn.close()

def save_company_logo_to_db(company_name, logo_bytes):
    conn = sqlite3.connect("master_portal.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE companies SET logo = ? WHERE company_name = ?", (logo_bytes, company_name))
    conn.commit()
    conn.close()

def load_company_logo_from_db(company_name):
    conn = sqlite3.connect("master_portal.db")
    cursor = conn.cursor()
    cursor.execute("SELECT logo FROM companies WHERE company_name = ?", (company_name,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else None

def init_company_db(company_name):
    db_file = f"company_{sanitize_name(company_name)}.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS employees (employee_id TEXT PRIMARY KEY, department TEXT, total_workdays INTEGER, days_present INTEGER, days_late INTEGER, tasks_completed INTEGER, avg_task_score REAL, days_absent INTEGER, absenteeism_rate REAL, productivity_score REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS employee_credentials (employee_id TEXT PRIMARY KEY, password TEXT, email TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS daily_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, employee_id TEXT, status TEXT, remarks TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS leave_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id TEXT, leave_type TEXT, start_date TEXT, end_date TEXT, reason TEXT, status TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS announcements (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, title TEXT, message TEXT)''')
    
    # Check column migrations
    cursor.execute("PRAGMA table_info(employee_credentials)")
    cols = [c[1] for c in cursor.fetchall()]
    if "email" not in cols:
        cursor.execute("ALTER TABLE employee_credentials ADD COLUMN email TEXT")
        
    conn.commit()
    conn.close()

def load_employees_from_db(company_name):
    init_company_db(company_name)
    conn = sqlite3.connect(f"company_{sanitize_name(company_name)}.db")
    df = pd.read_sql_query("SELECT * FROM employees", conn)
    conn.close()
    if "photo" not in df.columns: df["photo"] = None
    return df

def save_employee_to_db(company_name, row, emp_password=None, emp_email=None):
    init_company_db(company_name)
    conn = sqlite3.connect(f"company_{sanitize_name(company_name)}.db")
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO employees VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (
        row["employee_id"], row["department"], row["total_workdays"], row["days_present"], 
        row["days_late"], row["tasks_completed"], row["avg_task_score"], row["days_absent"], 
        row["absenteeism_rate"], row["productivity_score"]
    ))
    if emp_password:
        cursor.execute('INSERT OR REPLACE INTO employee_credentials (employee_id, password, email) VALUES (?, ?, ?)', (row["employee_id"], emp_password, emp_email))
    conn.commit()
    conn.close()

def verify_employee_password(company_name, emp_id, password):
    init_company_db(company_name)
    conn = sqlite3.connect(f"company_{sanitize_name(company_name)}.db")
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM employee_credentials WHERE employee_id = ?", (emp_id,))
    row = cursor.fetchone()
    conn.close()
    return row and row[0] == password

def load_daily_logs_from_db(company_name):
    init_company_db(company_name)
    conn = sqlite3.connect(f"company_{sanitize_name(company_name)}.db")
    df = pd.read_sql_query("SELECT * FROM daily_logs", conn)
    conn.close()
    return df

def save_daily_log_to_db(company_name, log_row):
    conn = sqlite3.connect(f"company_{sanitize_name(company_name)}.db")
    cursor = conn.cursor()
    cursor.execute('INSERT INTO daily_logs (date, employee_id, status, remarks) VALUES (?, ?, ?, ?)', (str(log_row["Date"]), log_row["Employee ID"], log_row["Status"], log_row["Remarks"]))
    conn.commit()
    conn.close()

init_master_db()

# ==========================================
# 3. AUTHENTICATION STATE
# ==========================================
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "logged_in_company" not in st.session_state: st.session_state.logged_in_company = None
if "user_role" not in st.session_state: st.session_state.user_role = None
if "logged_in_user_id" not in st.session_state: st.session_state.logged_in_user_id = None
if "history" not in st.session_state: st.session_state.history = []
if "redo_stack" not in st.session_state: st.session_state.redo_stack = []

# ==========================================
# 4. LOGIN & REGISTRATION GATEWAY
# ==========================================
if not st.session_state.authenticated:
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>🔐 Secure Enterprise Portal</h1>", unsafe_allow_html=True)
        companies = get_registered_companies()
        
        login_tab1, login_tab2, login_tab3 = st.tabs(["🔑 Admin Sign In", "👤 Employee Sign In", "🏢 Register Company"])
        
        with login_tab1:
            with st.form("admin_login"):
                sel_company = st.selectbox("Select Company", options=companies if companies else ["No Companies Available"])
                admin_id = st.text_input("Admin User ID")
                admin_pass = st.text_input("Password", type="password")
                if st.form_submit_button("Access Admin Dashboard", use_container_width=True):
                    if verify_admin_login(sel_company, admin_id, admin_pass):
                        st.session_state.update(authenticated=True, logged_in_company=sel_company, user_role="Admin", logged_in_user_id=admin_id)
                        st.rerun()
                    else: st.error("Invalid credentials.")

        with login_tab2:
            with st.form("emp_login"):
                emp_company = st.selectbox("Select Company", options=companies if companies else ["No Companies Available"])
                emp_id = st.text_input("Employee ID")
                emp_pass = st.text_input("Password", type="password")
                if st.form_submit_button("Access Employee Portal", use_container_width=True):
                    if verify_employee_password(emp_company, emp_id, emp_pass):
                        st.session_state.update(authenticated=True, logged_in_company=emp_company, user_role="Employee", logged_in_user_id=emp_id)
                        st.rerun()
                    else: st.error("Invalid employee credentials.")

        with login_tab3:
            with st.form("reg_form"):
                new_comp = st.text_input("Company Name")
                comp_pass = st.text_input("Company Master Password", type="password")
                adm_id = st.text_input("Initial Admin ID", value="admin")
                adm_pass = st.text_input("Initial Admin Password", type="password")
                if st.form_submit_button("Register Company", use_container_width=True):
                    if new_comp and comp_pass and adm_id and adm_pass:
                        register_company_with_admins(new_comp, comp_pass, [(adm_id, adm_pass)])
                        init_company_db(new_comp)
                        st.success("Company registered successfully! Please sign in.")
                    else: st.error("Please fill all fields.")
    st.stop()

# ==========================================
# 5. DASHBOARD & ENHANCED FEATURES
# ==========================================
cur_comp = st.session_state.logged_in_company
current_role = st.session_state.user_role
logged_user_id = st.session_state.logged_in_user_id

df = load_employees_from_db(cur_comp)
daily_log = load_daily_logs_from_db(cur_comp)

# Sidebar Info & Navigation
st.sidebar.markdown(f"### 🏢 {cur_comp}")
st.sidebar.markdown(f"Role: **{current_role}** ({logged_user_id})")
if st.sidebar.button("🚪 Log Out", use_container_width=True):
    st.session_state.clear()
    st.rerun()

st.sidebar.markdown("---")

# Feature 6: Announcement Board Header Display
conn = sqlite3.connect(f"company_{sanitize_name(cur_comp)}.db")
announcements_df = pd.read_sql_query("SELECT * FROM announcements ORDER BY id DESC LIMIT 3", conn)
conn.close()

if not announcements_df.empty:
    with st.expander("📢 Company Announcements & Board", expanded=False):
        for _, ann in announcements_df.iterrows():
            st.info(f"**{ann['title']}** ({ann['date']})\n\n{ann['message']}")

# Main Header
hcol1, hcol2 = st.columns([1, 8])
with hcol1:
    logo_bytes = load_company_logo_from_db(cur_comp)
    if logo_bytes: st.image(Image.open(BytesIO(logo_bytes)), width=75)
with hcol2:
    st.title(f"{cur_comp} - {'Admin Management Suite' if current_role=='Admin' else 'Employee Portal'}")

tab1, tab2, tab3 = st.tabs(["📊 Performance Analytics", "📅 Daily Attendance & Leave", "⚙️ Company Settings & Reports"])

# --- TAB 1: PERFORMANCE ANALYTICS ---
with tab1:
    if current_role == "Admin":
        with st.sidebar.expander("🆔 Add / Register Employee"):
            with st.form("new_emp"):
                e_id = st.text_input("Employee ID")
                e_pass = st.text_input("Portal Password", type="password")
                e_email = st.text_input("Email Address")
                e_dept = st.selectbox("Department", ["Engineering", "Sales", "HR", "Marketing"])
                if st.form_submit_button("Create Account"):
                    if e_id and e_pass:
                        new_row = {"employee_id": e_id, "department": e_dept, "total_workdays": 22, "days_present": 0, "days_late": 0, "tasks_completed": 0, "avg_task_score": 0.0, "days_absent": 22, "absenteeism_rate": 100.0, "productivity_score": 0.0}
                        save_employee_to_db(cur_comp, new_row, emp_password=e_pass, emp_email=e_email)
                        st.success(f"Employee {e_id} added!")
                        st.rerun()

    filtered_df = df if current_role == "Admin" else df[df["employee_id"] == logged_user_id]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Headcount" if current_role=="Admin" else "My Workdays", len(filtered_df) if current_role=="Admin" else f"{filtered_df['days_present'].values[0] if not filtered_df.empty else 0}/22")
    col2.metric("Avg Absenteeism", f"{filtered_df['absenteeism_rate'].mean():.2f}%" if not filtered_df.empty else "0%")
    col3.metric("Avg Productivity", f"{filtered_df['productivity_score'].mean():.2f}" if not filtered_df.empty else "0")
    col4.metric("Tasks Completed", int(filtered_df['tasks_completed'].sum()) if not filtered_df.empty else 0)

    st.markdown("---")
    if not filtered_df.empty:
        if current_role == "Admin":
            c1, c2 = st.columns(2)
            with c1:
                fig, ax = plt.subplots(figsize=(5, 3))
                sns.scatterplot(data=filtered_df, x="absenteeism_rate", y="productivity_score", hue="department", ax=ax)
                st.pyplot(fig)
            with c2:
                fig2, ax2 = plt.subplots(figsize=(5, 3))
                sns.barplot(data=df.groupby("department")["productivity_score"].mean().reset_index(), x="department", y="productivity_score", ax=ax2)
                st.pyplot(fig2)
            st.dataframe(filtered_df, use_container_width=True)
        else:
            st.subheader("👤 My Personal Performance Card")
            emp = filtered_df.iloc[0]
            st.write(f"**ID:** {emp['employee_id']} | **Department:** {emp['department']}")
            st.write(f"**Productivity Score:** {emp['productivity_score']} | **Absenteeism Rate:** {emp['absenteeism_rate']}%")

# --- TAB 2: DAILY ATTENDANCE & LEAVE (Feature 3) ---
with tab2:
    if current_role == "Admin":
        st.subheader("📅 Log Attendance")
        if not df.empty:
            with st.form("att_log"):
                ldate = st.date_input("Date", value=date.today())
                lemp = st.selectbox("Employee ID", options=df["employee_id"].unique())
                lstat = st.selectbox("Status", ["Present", "Absent", "Late", "Half-Day"])
                lrem = st.text_input("Remarks")
                if st.form_submit_button("Record Attendance"):
                    save_daily_log_to_db(cur_comp, {"Date": ldate, "Employee ID": lemp, "Status": lstat, "Remarks": lrem})
                    st.success("Attendance saved!")
                    st.rerun()
        
        st.markdown("---")
        st.subheader("🏖️ Manage Pending Leave Requests")
        conn = sqlite3.connect(f"company_{sanitize_name(cur_comp)}.db")
        leaves_df = pd.read_sql_query("SELECT * FROM leave_requests WHERE status='Pending'", conn)
        conn.close()
        
        if not leaves_df.empty:
            for _, leave in leaves_df.iterrows():
                st.write(f"**{leave['employee_id']}** requested **{leave['leave_type']}** from {leave['start_date']} to {leave['end_date']} (Reason: {leave['reason']})")
                col_a, col_b = st.columns(2)
                if col_a.button("Approve", key=f"app_{leave['id']}"):
                    conn = sqlite3.connect(f"company_{sanitize_name(cur_comp)}.db")
                    conn.execute("UPDATE leave_requests SET status='Approved' WHERE id=?", (leave['id'],))
                    conn.commit(); conn.close()
                    st.rerun()
                if col_b.button("Reject", key=f"rej_{leave['id']}"):
                    conn = sqlite3.connect(f"company_{sanitize_name(cur_comp)}.db")
                    conn.execute("UPDATE leave_requests SET status='Rejected' WHERE id=?", (leave['id'],))
                    conn.commit(); conn.close()
                    st.rerun()
        else: st.info("No pending leave requests.")
        
    else:
        st.subheader("🏖️ Apply for Leave / PTO")
        with st.form("leave_form"):
            l_type = st.selectbox("Leave Type", ["Medical Leave", "Casual Leave", "Vacation", "Remote Work"])
            l_start = st.date_input("Start Date")
            l_end = st.date_input("End Date")
            l_reason = st.text_area("Reason")
            if st.form_submit_button("Submit Request"):
                conn = sqlite3.connect(f"company_{sanitize_name(cur_comp)}.db")
                conn.execute("INSERT INTO leave_requests (employee_id, leave_type, start_date, end_date, reason, status) VALUES (?, ?, ?, ?, ?, 'Pending')",
                             (logged_user_id, l_type, str(l_start), str(l_end), l_reason))
                conn.commit(); conn.close()
                st.success("Leave request submitted successfully!")
                st.rerun()

# --- TAB 3: SETTINGS & REPORTS (Feature 1, 5, 6) ---
with tab3:
    if current_role == "Admin":
        st.subheader("📊 Export Reports (PDF & Excel)")
        
        # Excel Export
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Employees')
            daily_log.to_excel(writer, index=False, sheet_name='Attendance Logs')
        st.download_button("📥 Download Full Excel Report (.xlsx)", data=excel_buffer.getvalue(), file_name=f"{cur_comp}_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        st.markdown("---")
        st.subheader("📢 Post Company Announcement (Feature 6)")
        with st.form("ann_form"):
            a_title = st.text_input("Announcement Title")
            a_msg = st.text_area("Message Body")
            if st.form_submit_button("Publish Announcement"):
                if a_title and a_msg:
                    conn = sqlite3.connect(f"company_{sanitize_name(cur_comp)}.db")
                    conn.execute("INSERT INTO announcements (date, title, message) VALUES (?, ?, ?)", (str(date.today()), a_title, a_msg))
                    conn.commit(); conn.close()
                    st.success("Announcement published!")
                    st.rerun()
    else:
        st.info("Settings and report generation tools are managed by Company Admin.")