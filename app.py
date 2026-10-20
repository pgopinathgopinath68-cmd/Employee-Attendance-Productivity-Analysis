import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import date, datetime
from io import BytesIO
from PIL import Image
import sqlite3
import re

# ==========================================
# 1. PAGE CONFIGURATION & DEFAULT LIGHT THEME
# ==========================================
st.set_page_config(page_title="Secure Multi-Admin Attendance Dashboard", layout="wide", initial_sidebar_state="expanded")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Light Mode"

# Global Theme CSS Customization
if not st.session_state.authenticated or st.session_state.theme_mode == "Light Mode":
    st.markdown("""
        <style>
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], .main {
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%) !important;
            font-family: 'Inter', sans-serif;
            color: #0f172a !important;
        }
        [data-testid="stSidebar"] {
            background-color: rgba(255, 255, 255, 0.82) !important;
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            border-right: 1px solid rgba(0, 0, 0, 0.08);
            padding: 24px 14px;
        }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            color: #0f172a !important;
            font-weight: 800 !important;
            letter-spacing: -0.3px;
        }
        [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
            color: #334155 !important;
            font-size: 14px !important;
            font-weight: 600 !important;
        }
        .stButton button {
            background-color: #2563eb !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            border-radius: 8px !important;
            border: none !important;
            transition: all 0.2s ease-in-out;
        }
        .stButton button:hover {
            background-color: #1d4ed8 !important;
        }
        input, textarea, select {
            color: #0f172a !important;
            background-color: #ffffff !important;
            font-weight: 600 !important;
            border-radius: 6px !important;
        }
        [data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.9) !important;
            border: 1px solid rgba(0, 0, 0, 0.08) !important;
            border-radius: 12px;
            padding: 12px;
        }
        [data-testid="stMetricLabel"] p { color: #64748b !important; }
        [data-testid="stMetricValue"] { color: #2563eb !important; }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], .main {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
            font-family: 'Inter', sans-serif;
            color: #f8fafc !important;
        }
        [data-testid="stSidebar"] {
            background-color: rgba(30, 41, 59, 0.78) !important;
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            border-right: 1px solid rgba(255, 255, 255, 0.1);
            padding: 24px 14px;
        }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            color: #f8fafc !important;
            font-weight: 800 !important;
            letter-spacing: -0.3px;
        }
        [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
            color: #cbd5e1 !important;
            font-size: 14px !important;
            font-weight: 600 !important;
        }
        .stButton button {
            background-color: #3b82f6 !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            border-radius: 8px !important;
            border: none !important;
        }
        input, textarea, select {
            color: #0f172a !important;
            background-color: #f1f5f9 !important;
            font-weight: 600 !important;
        }
        [data-testid="stMetric"] {
            background: rgba(30, 41, 59, 0.65) !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            border-radius: 12px;
            padding: 12px;
        }
        [data-testid="stMetricLabel"] p { color: #94a3b8 !important; }
        [data-testid="stMetricValue"] { color: #38bdf8 !important; }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. SQLITE DATABASE FUNCTIONS & BRANDING
# ==========================================
def sanitize_name(name):
    return re.sub(r'[^a-zA-Z0-9]', '_', name).lower()

def init_master_db():
    conn = sqlite3.connect("master_portal.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS companies (
            company_name TEXT PRIMARY KEY,
            company_password TEXT,
            logo BLOB
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS company_admins (
            company_name TEXT,
            admin_user_id TEXT,
            password TEXT,
            PRIMARY KEY (company_name, admin_user_id)
        )
    ''')
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
            cursor.execute("INSERT OR REPLACE INTO company_admins (company_name, admin_user_id, password) VALUES (?, ?, ?)", 
                           (company_name, admin_id, password))
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
    
    cursor.execute("PRAGMA table_info(employees)")
    cols = [col[1] for col in cursor.fetchall()]
    
    expected_cols = [
        'employee_id', 'full_name', 'dob', 'joined_date', 'role', 
        'department', 'email', 'phone', 'city', 'total_workdays', 
        'days_present', 'days_late', 'tasks_completed', 'avg_task_score', 
        'days_absent', 'absenteeism_rate', 'productivity_score'
    ]
    
    if not cols or len(cols) != len(expected_cols):
        cursor.execute("DROP TABLE IF EXISTS employees")
        cursor.execute('''
            CREATE TABLE employees (
                employee_id TEXT PRIMARY KEY,
                full_name TEXT,
                dob TEXT,
                joined_date TEXT,
                role TEXT,
                department TEXT,
                email TEXT,
                phone TEXT,
                city TEXT,
                total_workdays INTEGER,
                days_present INTEGER,
                days_late INTEGER,
                tasks_completed INTEGER,
                avg_task_score REAL,
                days_absent INTEGER,
                absenteeism_rate REAL,
                productivity_score REAL
            )
        ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employee_credentials (
            employee_id TEXT PRIMARY KEY,
            password TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            employee_id TEXT,
            status TEXT,
            remarks TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            title TEXT,
            message TEXT,
            posted_by TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leave_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT,
            leave_type TEXT,
            start_date TEXT,
            end_date TEXT,
            reason TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()

def clear_all_company_records(company_name):
    db_file = f"company_{sanitize_name(company_name)}.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM employees")
    cursor.execute("DELETE FROM employee_credentials")
    cursor.execute("DELETE FROM daily_logs")
    cursor.execute("DELETE FROM announcements")
    cursor.execute("DELETE FROM leave_requests")
    conn.commit()
    conn.close()

def load_employees_from_db(company_name):
    init_company_db(company_name)
    db_file = f"company_{sanitize_name(company_name)}.db"
    conn = sqlite3.connect(db_file)
    df = pd.read_sql_query("SELECT * FROM employees", conn)
    conn.close()
    return df

def save_employee_to_db(company_name, row, emp_password=None):
    init_company_db(company_name)
    db_file = f"company_{sanitize_name(company_name)}.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO employees (
            employee_id, full_name, dob, joined_date, role, department, email, phone, city, 
            total_workdays, days_present, days_late, tasks_completed, 
            avg_task_score, days_absent, absenteeism_rate, productivity_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        row["employee_id"], 
        row.get("full_name", ""),
        str(row.get("dob", "")),
        str(row.get("joined_date", "")),
        row.get("role", ""),
        row["department"], 
        row.get("email", ""), 
        row.get("phone", ""), 
        row.get("city", ""),
        row["total_workdays"], 
        row["days_present"], 
        row["days_late"], 
        row["tasks_completed"], 
        row["avg_task_score"], 
        row["days_absent"], 
        row["absenteeism_rate"], 
        row["productivity_score"]
    ))
    if emp_password:
        cursor.execute('''
            INSERT OR REPLACE INTO employee_credentials (employee_id, password) VALUES (?, ?)
        ''', (row["employee_id"], emp_password))
    conn.commit()
    conn.close()

def verify_employee_password(company_name, emp_id, password):
    init_company_db(company_name)
    db_file = f"company_{sanitize_name(company_name)}.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM employee_credentials WHERE employee_id = ?", (emp_id,))
    row = cursor.fetchone()
    conn.close()
    return row and row[0] == password

def load_daily_logs_from_db(company_name):
    init_company_db(company_name)
    db_file = f"company_{sanitize_name(company_name)}.db"
    conn = sqlite3.connect(db_file)
    df = pd.read_sql_query("SELECT * FROM daily_logs", conn)
    conn.close()
    return df

def save_daily_log_to_db(company_name, log_row):
    db_file = f"company_{sanitize_name(company_name)}.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO daily_logs (date, employee_id, status, remarks)
        VALUES (?, ?, ?, ?)
    ''', (str(log_row["Date"]), log_row["Employee ID"], log_row["Status"], log_row["Remarks"]))
    conn.commit()
    conn.close()

def load_announcements_from_db(company_name):
    init_company_db(company_name)
    db_file = f"company_{sanitize_name(company_name)}.db"
    conn = sqlite3.connect(db_file)
    df = pd.read_sql_query("SELECT * FROM announcements ORDER BY id DESC", conn)
    conn.close()
    return df

def save_announcement_to_db(company_name, title, message, posted_by):
    db_file = f"company_{sanitize_name(company_name)}.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO announcements (date, title, message, posted_by) VALUES (?, ?, ?, ?)", 
                   (str(date.today()), title, message, posted_by))
    conn.commit()
    conn.close()

def load_leave_requests_from_db(company_name):
    init_company_db(company_name)
    db_file = f"company_{sanitize_name(company_name)}.db"
    conn = sqlite3.connect(db_file)
    df = pd.read_sql_query("SELECT * FROM leave_requests ORDER BY id DESC", conn)
    conn.close()
    return df

def save_leave_request_to_db(company_name, emp_id, leave_type, start_date, end_date, reason):
    db_file = f"company_{sanitize_name(company_name)}.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO leave_requests (employee_id, leave_type, start_date, end_date, reason, status) VALUES (?, ?, ?, ?, ?, ?)", 
                   (emp_id, leave_type, str(start_date), str(end_date), reason, "Pending"))
    conn.commit()
    conn.close()

def update_leave_status_in_db(company_name, leave_id, status):
    db_file = f"company_{sanitize_name(company_name)}.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("UPDATE leave_requests SET status = ? WHERE id = ?", (status, leave_id))
    conn.commit()
    conn.close()

def parse_date_safely(date_str, default_date=date(1995, 1, 1)):
    try:
        if date_str and date_str != "N/A":
            return datetime.strptime(str(date_str).strip(), "%Y-%m-%d").date()
    except Exception:
        pass
    return default_date

init_master_db()

# ==========================================
# 3. AUTHENTICATION & ROLE STATE SETUP
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "logged_in_company" not in st.session_state:
    st.session_state.logged_in_company = None

if "user_role" not in st.session_state:
    st.session_state.user_role = None

if "logged_in_user_id" not in st.session_state:
    st.session_state.logged_in_user_id = None

if "just_registered_company" not in st.session_state:
    st.session_state.just_registered_company = None

if "history" not in st.session_state:
    st.session_state.history = []

if "redo_stack" not in st.session_state:
    st.session_state.redo_stack = []

# ==========================================
# 4. LOGIN SCREEN GATEWAY
# ==========================================
if not st.session_state.authenticated:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<h1 style='text-align: center;'>🔐 Secure Enterprise Portal Login</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Sign in as Company Admin, Employee, or Register a Company</p>", unsafe_allow_html=True)
        
        companies = get_registered_companies()
        
        if not companies:
            st.warning("⚠️ No companies registered yet! Please go to the **'Register Company'** tab to create your company and admin accounts.")
            
        login_tab1, login_tab2, login_tab3 = st.tabs(["🔑 Admin Sign In", "👤 Employee Sign In", "🏢 Register Company"])
        
        with login_tab1:
            with st.form("admin_login_form"):
                if companies:
                    default_index = 0
                    if st.session_state.just_registered_company in companies:
                        default_index = companies.index(st.session_state.just_registered_company)
                    
                    sel_company = st.selectbox("Select Company", options=companies, index=default_index, key="admin_sel_comp")
                else:
                    sel_company = st.selectbox("Select Company", options=["No Companies Available"], key="admin_sel_comp_empty")
                
                admin_id_input = st.text_input("Admin User ID", placeholder="e.g., admin or manager1")
                admin_password = st.text_input("Admin Password", type="password", placeholder="Enter admin password")
                
                admin_submitted = st.form_submit_button("Access Admin Dashboard", use_container_width=True)
                
                if admin_submitted:
                    if not companies:
                        st.error("Please register a company first.")
                    elif admin_id_input and verify_admin_login(sel_company, admin_id_input, admin_password):
                        st.session_state.authenticated = True
                        st.session_state.logged_in_company = sel_company
                        st.session_state.user_role = "Admin"
                        st.session_state.logged_in_user_id = admin_id_input
                        st.session_state.history.clear()
                        st.session_state.redo_stack.clear()
                        st.success(f"Welcome Admin '{admin_id_input}' of {sel_company}!")
                        st.rerun()
                    else:
                        st.error("Invalid Admin User ID or Password.")

        with login_tab2:
            with st.form("emp_login_form"):
                st.markdown("##### Select your company and enter your Employee ID & personal password.")
                emp_company = st.selectbox("Select Company", options=companies if companies else ["No Companies Available"], key="emp_sel_comp")
                emp_id_input = st.text_input("Employee ID", placeholder="e.g., EMP101")
                emp_password = st.text_input("Employee Personal Password", type="password", placeholder="Enter your employee password")
                
                emp_submitted = st.form_submit_button("Access Employee Portal", use_container_width=True)
                
                if emp_submitted:
                    if not companies:
                        st.error("Please register a company first.")
                    elif emp_id_input and verify_employee_password(emp_company, emp_id_input, emp_password):
                        st.session_state.authenticated = True
                        st.session_state.logged_in_company = emp_company
                        st.session_state.user_role = "Employee"
                        st.session_state.logged_in_user_id = emp_id_input
                        st.success(f"Welcome, {emp_id_input}!")
                        st.rerun()
                    else:
                        st.error("Invalid Employee ID or Password.")

        with login_tab3:
            st.markdown("### Register Company & Master Password")
            new_comp = st.text_input("New Company Name", placeholder="e.g., Apex Global", key="reg_comp_name")
            company_master_pass = st.text_input("Company Master Password", type="password", placeholder="Set master password for company", key="reg_comp_pass")
            
            # Dynamic Admin count OUTSIDE form so it updates instantly
            num_admins = st.number_input("Number of Admin Accounts Needed", min_value=1, max_value=5, value=1, step=1, key="reg_num_admins")
            
            st.markdown("#### Enter Admin User IDs & Passwords")
            admin_inputs = []
            for i in range(int(num_admins)):
                col_a, col_b = st.columns(2)
                with col_a:
                    a_id = st.text_input(f"Admin #{i+1} User ID", placeholder=f"e.g., admin{i+1}", key=f"reg_aid_{i}")
                with col_b:
                    a_pass = st.text_input(f"Admin #{i+1} Password", type="password", placeholder=f"Password #{i+1}", key=f"reg_apass_{i}")
                admin_inputs.append((a_id, a_pass))
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("Register Company & Create Admins", use_container_width=True, key="btn_register_company"):
                companies_list = get_registered_companies()
                if not new_comp:
                    st.error("Please enter a company name.")
                elif not company_master_pass:
                    st.error("Please provide a Company Master Password.")
                elif new_comp in companies_list:
                    st.error("Company name already exists. Please sign in instead.")
                else:
                    valid_admins = [(aid.strip(), apass.strip()) for aid, apass in admin_inputs if aid.strip() and apass.strip()]
                    if not valid_admins:
                        st.error("Please provide at least one valid Admin User ID and Password.")
                    else:
                        register_company_with_admins(new_comp, company_master_pass, valid_admins)
                        init_company_db(new_comp)
                        
                        st.session_state.just_registered_company = new_comp
                        st.success(f"Company '{new_comp}' registered successfully! Go to 'Admin Sign In' tab to log in.")
                        st.rerun()
                            
    st.stop()

# ==========================================
# 5. SECURE DASHBOARD (ROLE-BASED VIEW)
# ==========================================
cur_comp = st.session_state.logged_in_company
current_role = st.session_state.user_role
logged_user_id = st.session_state.logged_in_user_id

df = load_employees_from_db(cur_comp)
daily_log = load_daily_logs_from_db(cur_comp)
announcements_df = load_announcements_from_db(cur_comp)
leave_df = load_leave_requests_from_db(cur_comp)

def push_history(current_df):
    st.session_state.history.append(current_df.copy())
    st.session_state.redo_stack.clear()

# --- SIDEBAR CONTROL CENTER ---
st.sidebar.markdown(f"## 🏢 {cur_comp}")
st.sidebar.markdown(f"**User:** `{logged_user_id}`  \n**Role:** `{current_role}`")

if st.sidebar.button("🚪 Log Out", use_container_width=True):
    st.session_state.authenticated = False
    st.session_state.logged_in_company = None
    st.session_state.user_role = None
    st.session_state.logged_in_user_id = None
    st.rerun()

st.sidebar.markdown("---")

st.sidebar.markdown("### 🎨 Display Preferences")
st.session_state.theme_mode = st.sidebar.radio("Appearance Theme", ["Light Mode", "Dark Mode"], index=0 if st.session_state.theme_mode=="Light Mode" else 1)

st.sidebar.markdown("---")

if current_role == "Admin":
    st.sidebar.markdown("### ⚙️ Admin Controls")

    ur_col1, ur_col2 = st.sidebar.columns(2)
    with ur_col1:
        if st.button("↩️ Undo", use_container_width=True):
            if st.session_state.history:
                st.session_state.redo_stack.append(df.copy())
                previous_df = st.session_state.history.pop()
                init_company_db(cur_comp)
                conn = sqlite3.connect(f"company_{sanitize_name(cur_comp)}.db")
                previous_df.to_sql("employees", conn, if_exists="replace", index=False)
                conn.close()
                st.success("Undone!")
                st.rerun()
            else:
                st.warning("Nothing to undo")
    with ur_col2:
        if st.button("🔁 Redo", use_container_width=True):
            if st.session_state.redo_stack:
                st.session_state.history.append(df.copy())
                next_df = st.session_state.redo_stack.pop()
                conn = sqlite3.connect(f"company_{sanitize_name(cur_comp)}.db")
                next_df.to_sql("employees", conn, if_exists="replace", index=False)
                conn.close()
                st.success("Redone!")
                st.rerun()
            else:
                st.warning("Nothing to redo")

    with st.sidebar.expander("➕ Register New Employee"):
        with st.form(f"quick_id_form_{cur_comp}"):
            quick_id = st.text_input("Employee ID *", placeholder="e.g., EMP101")
            quick_pass = st.text_input("Password *", type="password", placeholder="Set password")
            quick_name = st.text_input("Full Name", placeholder="e.g., Rajesh Kumar")
            
            quick_dob = st.date_input(
                "Date of Birth", 
                value=date(1995, 1, 1), 
                min_value=date(1950, 1, 1), 
                max_value=date.today()
            )
            quick_joined = st.date_input("Joined Date", value=date.today())
            quick_role = st.text_input("Designation / Role", placeholder="e.g., Senior Analyst")
            quick_email = st.text_input("Email", placeholder="e.g., rajesh@company.com")
            quick_phone = st.text_input("Phone Number", placeholder="e.g., +91 9876543210")
            
            quick_city = st.selectbox("District / City", [
                "Mumbai", "Delhi", "Bengaluru", "Chennai", "Hyderabad", "Kolkata", 
                "Pune", "Ahmedabad", "Jaipur", "Surat", "Lucknow", "Kanpur", 
                "Nagpur", "Indore", "Thane", "Bhopal", "Visakhapatnam", "Patna", 
                "Vadodara", "Ghaziabad", "Ludhiana", "Agra", "Nashik", "Ranchi", "Coimbatore", "Madurai",
                "Gurugram", "Noida", "Chandigarh", "Kochi", "Thiruvananthapuram", "Mysuru", "Bhubaneswar"
            ])
            quick_dept = st.selectbox("Department", ["Engineering", "Sales", "HR", "Marketing"], key=f"q_dept_{cur_comp}")
            
            quick_submit = st.form_submit_button("Save Employee", use_container_width=True)
            
            if quick_submit:
                if not quick_id or not quick_pass:
                    st.sidebar.error("ID and Password are required.")
                elif not df.empty and quick_id in df["employee_id"].values:
                    st.sidebar.error("Employee ID already exists.")
                else:
                    push_history(df)
                    total_workdays = 22
                    new_row = {
                        "employee_id": quick_id,
                        "full_name": quick_name,
                        "dob": str(quick_dob),
                        "joined_date": str(quick_joined),
                        "role": quick_role,
                        "department": quick_dept,
                        "email": quick_email,
                        "phone": quick_phone,
                        "city": quick_city,
                        "total_workdays": total_workdays,
                        "days_present": 0,
                        "days_late": 0,
                        "tasks_completed": 0,
                        "avg_task_score": 0.0,
                        "days_absent": total_workdays,
                        "absenteeism_rate": 100.0,
                        "productivity_score": 0.0
                    }
                    save_employee_to_db(cur_comp, new_row, emp_password=quick_pass)
                    st.sidebar.success(f"Created '{quick_id}' successfully!")
                    st.rerun()

    with st.sidebar.expander("✏️ Update Employee Details"):
        if not df.empty:
            existing_ids = df["employee_id"].unique()
            update_id = st.selectbox("Select Employee ID", options=existing_ids, key=f"up_id_{cur_comp}")
            
            current_row = df[df["employee_id"] == update_id].iloc[0]
            dept_list = ["Engineering", "Sales", "HR", "Marketing"]
            curr_dept_idx = dept_list.index(current_row["department"]) if current_row["department"] in dept_list else 0
            
            update_name = st.text_input("Full Name", value=str(current_row.get("full_name", "")), key=f"up_name_{cur_comp}")
            
            curr_dob = parse_date_safely(current_row.get("dob", ""), date(1995, 1, 1))
            curr_joined = parse_date_safely(current_row.get("joined_date", ""), date.today())
            
            update_dob = st.date_input(
                "Date of Birth (DOB)", 
                value=curr_dob, 
                min_value=date(1950, 1, 1), 
                max_value=date.today(),
                key=f"up_dob_{cur_comp}"
            )
            update_joined = st.date_input(
                "Joined Date", 
                value=curr_joined, 
                min_value=date(1980, 1, 1),
                max_value=date.today(),
                key=f"up_joined_{cur_comp}"
            )
            
            update_role = st.text_input("Role / Designation", value=str(current_row.get("role", "")), key=f"up_role_{cur_comp}")
            update_email = st.text_input("Email", value=str(current_row.get("email", "")), key=f"up_email_{cur_comp}")
            update_phone = st.text_input("Phone Number", value=str(current_row.get("phone", "")), key=f"up_phone_{cur_comp}")
            update_city = st.text_input("City / District", value=str(current_row.get("city", "")), key=f"up_city_{cur_comp}")
            update_dept = st.selectbox("Department", dept_list, index=curr_dept_idx, key=f"up_dept_{cur_comp}")
            
            update_total_workdays = st.number_input("Total Workdays", min_value=1, max_value=31, value=int(current_row["total_workdays"]), key=f"up_total_days_{cur_comp}")
            update_present = st.slider("Days Present", 0, int(update_total_workdays), int(current_row["days_present"]), key=f"up_pres_{cur_comp}")
            update_late = st.slider("Days Late", 0, 5, int(current_row["days_late"]), key=f"up_late_{cur_comp}")
            update_tasks = st.number_input("Tasks Completed", min_value=0, max_value=200, value=int(current_row["tasks_completed"]), key=f"up_tasks_{cur_comp}")
            update_score = st.slider("Avg Task Score", 0.0, 100.0, float(current_row["avg_task_score"]), key=f"up_score_{cur_comp}")
            
            if st.button("Update Employee", key=f"update_btn_{cur_comp}", use_container_width=True):
                push_history(df)
                days_absent = update_total_workdays - update_present
                absenteeism_rate = round((days_absent / update_total_workdays) * 100, 2) if update_total_workdays > 0 else 0.0
                productivity_score = round((update_tasks * 0.6) + (update_score * 0.4), 2)
                
                updated_row = {
                    "employee_id": update_id,
                    "full_name": update_name,
                    "dob": str(update_dob),
                    "joined_date": str(update_joined),
                    "role": update_role,
                    "department": update_dept,
                    "email": update_email,
                    "phone": update_phone,
                    "city": update_city,
                    "total_workdays": update_total_workdays,
                    "days_present": update_present,
                    "days_late": update_late,
                    "tasks_completed": update_tasks,
                    "avg_task_score": update_score,
                    "days_absent": days_absent,
                    "absenteeism_rate": absenteeism_rate,
                    "productivity_score": productivity_score
                }
                save_employee_to_db(cur_comp, updated_row)
                st.sidebar.success(f"Updated '{update_id}'!")
                st.rerun()
        else:
            st.info("No employee records found.")

    with st.sidebar.expander("🖼️ Branding & Logo"):
        uploaded_logo = st.file_uploader(f"Company Logo ({cur_comp})", type=["png", "jpg", "jpeg"], key=f"logo_{cur_comp}")
        if uploaded_logo is not None:
            logo_bytes = uploaded_logo.getvalue()
            save_company_logo_to_db(cur_comp, logo_bytes)
            st.sidebar.success("Logo updated successfully!")
            st.rerun()

    with st.sidebar.expander("🗑️ System Maintenance"):
        st.warning("Deletes all company records permanently.")
        if st.button("Reset Company Data", key=f"clear_data_{cur_comp}", use_container_width=True):
            clear_all_company_records(cur_comp)
            st.sidebar.success("Records cleared!")
            st.rerun()

    st.sidebar.markdown("---")

    st.sidebar.markdown("### 🔍 Filter Records")
    dept_options = ["All"] + list(df["department"].unique()) if not df.empty else ["All"]
    selected_dept = st.sidebar.selectbox("Department Filter", dept_options, key=f"filter_dept_{cur_comp}")
    filtered_df = df[df["department"] == selected_dept] if selected_dept != "All" else df
else:
    st.sidebar.info(f"👤 **Employee Portal Access**\nYou can view your complete personal profile, performance metrics, notices, and submit leave requests.")
    filtered_df = df[df["employee_id"] == logged_user_id]

# Render Top Dynamic Header
header_col1, header_col2 = st.columns([1, 8])
with header_col1:
    db_logo_bytes = load_company_logo_from_db(cur_comp)
    if db_logo_bytes is not None:
        try:
            logo_img = Image.open(BytesIO(db_logo_bytes))
            st.image(logo_img, width=80)
        except:
            st.write("📊")
    else:
        st.write("📊")

with header_col2:
    if current_role == "Admin":
        st.title(f"{cur_comp} - Admin Control Center")
    else:
        st.title(f"{cur_comp} - Employee Workspace")

st.markdown(f"Active Workspace: **{current_role} Mode** | Organization: **{cur_comp}**")

# --- CREATE APPLICATION TABS ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboard & Profile", 
    "📅 Daily Attendance", 
    "📢 Announcements", 
    "📝 Leave Requests"
])

# ==========================================
# TAB 1: DASHBOARD & PROFILE
# ==========================================
with tab1:
    col1, col2, col3, col4 = st.columns(4)
    total_emps = len(filtered_df)
    avg_abs = f"{filtered_df['absenteeism_rate'].mean():.2f}%" if total_emps > 0 else "0.00%"
    avg_prod = f"{filtered_df['productivity_score'].mean():.2f}" if total_emps > 0 else "0.00"
    total_tasks = int(filtered_df['tasks_completed'].sum()) if total_emps > 0 else 0

    if current_role == "Admin":
        col1.metric("Total Employees", total_emps)
        col2.metric("Avg Absenteeism Rate", avg_abs)
        col3.metric("Avg Productivity Score", avg_prod)
        col4.metric("Total Tasks Completed", total_tasks)
        st.markdown("---")

        if total_emps > 0:
            col_left, col_right = st.columns(2)
            with col_left:
                st.subheader("📈 Absenteeism vs. Productivity")
                fig, ax = plt.subplots(figsize=(6, 4))
                sns.scatterplot(data=filtered_df, x="absenteeism_rate", y="productivity_score", hue="department", palette="viridis", s=70, ax=ax, alpha=0.8)
                ax.set_xlabel("Absenteeism Rate (%)")
                ax.set_ylabel("Productivity Score")
                ax.grid(True, linestyle="--", alpha=0.5)
                st.pyplot(fig)

            with col_right:
                st.subheader("📊 Avg Productivity by Department")
                dept_avg = df.groupby("department")["productivity_score"].mean().reset_index()
                fig2, ax2 = plt.subplots(figsize=(6, 4))
                sns.barplot(data=dept_avg, x="department", y="productivity_score", palette="crest", ax=ax2)
                ax2.set_xlabel("Department")
                ax2.set_ylabel("Avg Productivity Score")
                ax2.grid(axis="y", linestyle="--", alpha=0.5)
                st.pyplot(fig2)

            st.subheader("📋 Detailed Employee Records Table")
            st.dataframe(filtered_df, use_container_width=True)

            st.markdown("---")
            st.subheader("🔍 Employee Profile & Performance Viewer")
            selected_emp_profile = st.selectbox("Select Employee ID to View Details", options=filtered_df["employee_id"].unique(), key=f"profile_sel_{cur_comp}")
            
            if selected_emp_profile:
                emp_data = filtered_df[filtered_df["employee_id"] == selected_emp_profile].iloc[0]
                
                col_pers, col_prof = st.columns(2)
                
                with col_pers:
                    st.markdown("### 👤 Personal Details")
                    st.write(f"**Full Name:** {emp_data.get('full_name', 'N/A')}")
                    st.write(f"**Employee ID:** {emp_data['employee_id']}")
                    st.write(f"**Date of Birth (DOB):** {emp_data.get('dob', 'N/A')}")
                    st.write(f"**Role / Designation:** {emp_data.get('role', 'N/A')}")
                    st.write(f"**Email Address:** {emp_data.get('email', 'N/A')}")
                    st.write(f"**Phone Number:** {emp_data.get('phone', 'N/A')}")
                    st.write(f"**Joined Date:** {emp_data.get('joined_date', 'N/A')}")
                    st.write(f"**Location / District:** {emp_data.get('city', 'N/A')}")

                with col_prof:
                    st.markdown("### 💼 Professional Details & Performance")
                    st.write(f"**Employee ID:** {emp_data['employee_id']}")
                    st.write(f"**Department:** {emp_data['department']}")
                    st.write(f"**Role / Designation:** {emp_data.get('role', 'N/A')}")
                    st.write(f"**Days of Attendance:** {emp_data['days_present']} Present / {emp_data['total_workdays']} Total Workdays")
                    st.write(f"**Days Late:** {emp_data['days_late']}")
                    st.write(f"**Tasks Completed:** {emp_data['tasks_completed']}")
                    st.write(f"**Average Task Score:** {emp_data['avg_task_score']}")
                    st.write(f"**Absenteeism Rate:** {emp_data['absenteeism_rate']}%")
                    st.write(f"**Productivity Score:** {emp_data['productivity_score']}")
        else:
            st.info("No records present. Add a new employee using the sidebar controls.")

    else:
        col1.metric("My Attendance Days", f"{int(filtered_df['days_present'].values[0]) if total_emps > 0 else 0} / {int(filtered_df['total_workdays'].values[0]) if total_emps > 0 else 0}")
        col2.metric("My Absenteeism Rate", avg_abs)
        col3.metric("My Productivity Score", avg_prod)
        col4.metric("Tasks Completed", total_tasks)
        st.markdown("---")

        if total_emps > 0:
            emp_data = filtered_df.iloc[0]
            st.subheader(f"👤 Employee Details for {emp_data.get('full_name', logged_user_id)} ({emp_data['employee_id']})")
            
            col_pers, col_prof = st.columns(2)
            
            with col_pers:
                st.markdown("### 👤 Personal Details")
                st.write(f"**Full Name:** {emp_data.get('full_name', 'N/A')}")
                st.write(f"**Employee ID:** {emp_data['employee_id']}")
                st.write(f"**Date of Birth (DOB):** {emp_data.get('dob', 'N/A')}")
                st.write(f"**Role / Designation:** {emp_data.get('role', 'N/A')}")
                st.write(f"**Email Address:** {emp_data.get('email', 'N/A')}")
                st.write(f"**Phone Number:** {emp_data.get('phone', 'N/A')}")
                st.write(f"**Joined Date:** {emp_data.get('joined_date', 'N/A')}")
                st.write(f"**Location / District:** {emp_data.get('city', 'N/A')}")

            with col_prof:
                st.markdown("### 💼 Professional Details & Performance")
                st.write(f"**Employee ID:** {emp_data['employee_id']}")
                st.write(f"**Department:** {emp_data['department']}")
                st.write(f"**Role / Designation:** {emp_data.get('role', 'N/A')}")
                st.write(f"**Days of Attendance:** {emp_data['days_present']} Present / {emp_data['total_workdays']} Total Workdays")
                st.write(f"**Days Late:** {emp_data['days_late']}")
                st.write(f"**Tasks Completed:** {emp_data['tasks_completed']}")
                st.write(f"**Average Task Score:** {emp_data['avg_task_score']}")
                st.write(f"**Absenteeism Rate:** {emp_data['absenteeism_rate']}%")
                st.write(f"**Productivity Score:** {emp_data['productivity_score']}")
        else:
            st.warning("No profile record found for your Employee ID. Please contact your company Admin.")

# ==========================================
# TAB 2: DAILY ATTENDANCE MANAGER
# ==========================================
with tab2:
    if current_role == "Admin":
        st.subheader("📅 Log Daily Attendance")
        if not df.empty:
            with st.form("daily_att_form"):
                att_date = st.date_input("Attendance Date", value=date.today())
                att_emp = st.selectbox("Employee ID", options=df["employee_id"].unique(), key="att_emp_sel")
                att_status = st.selectbox("Status", ["Present", "Absent", "Late", "Half-Day"])
                att_remarks = st.text_input("Remarks", placeholder="e.g., On time, client meeting, sick leave")
                
                att_submit = st.form_submit_button("Record Daily Log")
                if att_submit:
                    log_row = {
                        "Date": att_date,
                        "Employee ID": att_emp,
                        "Status": att_status,
                        "Remarks": att_remarks
                    }
                    save_daily_log_to_db(cur_comp, log_row)
                    st.success(f"Attendance recorded for {att_emp} on {att_date}!")
                    st.rerun()
        else:
            st.warning("No employees available to log attendance.")

        st.markdown("---")
        st.subheader("📋 Company Daily Attendance Logs")
        if not daily_log.empty:
            st.dataframe(daily_log, use_container_width=True)
        else:
            st.info("No attendance logs recorded yet.")
    else:
        st.subheader("📅 My Daily Attendance Logs")
        my_logs = daily_log[daily_log["employee_id"] == logged_user_id] if not daily_log.empty else pd.DataFrame()
        if not my_logs.empty:
            st.dataframe(my_logs, use_container_width=True)
        else:
            st.info("No attendance logs found for your ID.")

# ==========================================
# TAB 3: ANNOUNCEMENTS BOARD
# ==========================================
with tab3:
    st.subheader("📢 Company Announcements & Notices")
    
    if current_role == "Admin":
        with st.expander("➕ Post New Announcement"):
            with st.form("announcement_form"):
                ann_title = st.text_input("Notice Title", placeholder="e.g., Office Holiday Notice")
                ann_msg = st.text_area("Announcement Message", placeholder="Enter announcement details here...")
                ann_submit = st.form_submit_button("Publish Announcement")
                
                if ann_submit:
                    if not ann_title or not ann_msg:
                        st.error("Please fill in both title and message.")
                    else:
                        save_announcement_to_db(cur_comp, ann_title, ann_msg, logged_user_id)
                        st.success("Announcement published successfully!")
                        st.rerun()
        st.markdown("---")

    if not announcements_df.empty:
        for _, row in announcements_df.iterrows():
            with st.container():
                st.markdown(f"### 📌 {row['title']}")
                st.markdown(f"**Date:** {row['date']} | **Posted by:** {row['posted_by']}")
                st.write(row['message'])
                st.markdown("---")
    else:
        st.info("No company announcements posted yet.")

# ==========================================
# TAB 4: LEAVE REQUESTS
# ==========================================
with tab4:
    if current_role == "Admin":
        st.subheader("📝 Manage Employee Leave Applications")
        if not leave_df.empty:
            st.dataframe(leave_df, use_container_width=True)
            
            st.markdown("### ⚙️ Approve or Reject Leave Request")
            pending_ids = leave_df[leave_df["status"] == "Pending"]["id"].tolist()
            if pending_ids:
                selected_leave_id = st.selectbox("Select Pending Leave ID", options=pending_ids)
                col_app, col_rej = st.columns(2)
                with col_app:
                    if st.button("✅ Approve Leave", use_container_width=True):
                        update_leave_status_in_db(cur_comp, selected_leave_id, "Approved")
                        st.success(f"Leave Request #{selected_leave_id} Approved!")
                        st.rerun()
                with col_rej:
                    if st.button("❌ Reject Leave", use_container_width=True):
                        update_leave_status_in_db(cur_comp, selected_leave_id, "Rejected")
                        st.warning(f"Leave Request #{selected_leave_id} Rejected.")
                        st.rerun()
            else:
                st.info("No pending leave requests to review.")
        else:
            st.info("No leave applications submitted yet.")
    else:
        st.subheader("📝 Apply for Leave")
        with st.form("apply_leave_form"):
            leave_type = st.selectbox("Leave Type", ["Casual Leave", "Sick Leave", "Earned Leave", "Maternity/Paternity Leave"])
            start_d = st.date_input("Start Date", value=date.today())
            end_d = st.date_input("End Date", value=date.today())
            reason = st.text_area("Reason for Leave", placeholder="Provide brief reason...")
            
            leave_submit = st.form_submit_button("Submit Leave Application", use_container_width=True)
            if leave_submit:
                if not reason:
                    st.error("Please provide a reason for your leave.")
                else:
                    save_leave_request_to_db(cur_comp, logged_user_id, leave_type, start_d, end_d, reason)
                    st.success("Leave application submitted successfully!")
                    st.rerun()

        st.markdown("---")
        st.subheader("📋 My Leave Application History")
        my_leaves = leave_df[leave_df["employee_id"] == logged_user_id] if not leave_df.empty else pd.DataFrame()
        if not my_leaves.empty:
            st.dataframe(my_leaves, use_container_width=True)
        else:
            st.info("You have not submitted any leave applications yet.")



