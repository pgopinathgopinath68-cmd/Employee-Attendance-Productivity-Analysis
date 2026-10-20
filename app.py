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
st.set_page_config(page_title="Student Portal | Attendance & Academic Progress", layout="wide", initial_sidebar_state="expanded")

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
        CREATE TABLE IF NOT EXISTS schools (
            school_name TEXT PRIMARY KEY,
            school_password TEXT,
            logo BLOB
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS school_admins (
            school_name TEXT,
            admin_user_id TEXT,
            password TEXT,
            PRIMARY KEY (school_name, admin_user_id)
        )
    ''')
    conn.commit()
    conn.close()

def get_registered_schools():
    conn = sqlite3.connect("master_portal.db")
    cursor = conn.cursor()
    cursor.execute("SELECT school_name FROM schools")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def verify_admin_login(school_name, admin_user_id, password):
    conn = sqlite3.connect("master_portal.db")
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM school_admins WHERE school_name = ? AND admin_user_id = ?", (school_name, admin_user_id))
    row = cursor.fetchone()
    conn.close()
    return row and row[0] == password

def register_school_with_admins(school_name, school_password, admin_list):
    conn = sqlite3.connect("master_portal.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO schools (school_name, school_password) VALUES (?, ?)", (school_name, school_password))
    for admin_id, password in admin_list:
        if admin_id and password:
            cursor.execute("INSERT OR REPLACE INTO school_admins (school_name, admin_user_id, password) VALUES (?, ?, ?)", 
                           (school_name, admin_id, password))
    conn.commit()
    conn.close()

def save_school_logo_to_db(school_name, logo_bytes):
    conn = sqlite3.connect("master_portal.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE schools SET logo = ? WHERE school_name = ?", (logo_bytes, school_name))
    conn.commit()
    conn.close()

def load_school_logo_from_db(school_name):
    conn = sqlite3.connect("master_portal.db")
    cursor = conn.cursor()
    cursor.execute("SELECT logo FROM schools WHERE school_name = ?", (school_name,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else None

def init_school_db(school_name):
    db_file = f"school_{sanitize_name(school_name)}.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(students)")
    cols = [col[1] for col in cursor.fetchall()]
    
    expected_cols = [
        'student_id', 'full_name', 'dob', 'enrollment_date', 'grade_level', 
        'program', 'email', 'phone', 'city', 'school_days', 
        'days_present', 'late_arrivals', 'assignments_completed', 'exam_average', 
        'days_absent', 'absence_rate', 'academic_progress'
    ]
    
    if not cols or len(cols) != len(expected_cols):
        cursor.execute("DROP TABLE IF EXISTS students")
        cursor.execute('''
            CREATE TABLE students (
                student_id TEXT PRIMARY KEY,
                full_name TEXT,
                dob TEXT,
                enrollment_date TEXT,
                grade_level TEXT,
                program TEXT,
                email TEXT,
                phone TEXT,
                city TEXT,
                school_days INTEGER,
                days_present INTEGER,
                late_arrivals INTEGER,
                assignments_completed INTEGER,
                exam_average REAL,
                days_absent INTEGER,
                absence_rate REAL,
                academic_progress REAL
            )
        ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_credentials (
            student_id TEXT PRIMARY KEY,
            password TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            student_id TEXT,
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
        CREATE TABLE IF NOT EXISTS absence_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            request_type TEXT,
            start_date TEXT,
            end_date TEXT,
            reason TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()

def clear_all_school_records(school_name):
    db_file = f"school_{sanitize_name(school_name)}.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students")
    cursor.execute("DELETE FROM student_credentials")
    cursor.execute("DELETE FROM daily_logs")
    cursor.execute("DELETE FROM announcements")
    cursor.execute("DELETE FROM absence_requests")
    conn.commit()
    conn.close()

def load_students_from_db(school_name):
    init_school_db(school_name)
    db_file = f"school_{sanitize_name(school_name)}.db"
    conn = sqlite3.connect(db_file)
    df = pd.read_sql_query("SELECT * FROM students", conn)
    conn.close()
    return df

def save_student_to_db(school_name, row, emp_password=None):
    init_school_db(school_name)
    db_file = f"school_{sanitize_name(school_name)}.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO students (
            student_id, full_name, dob, enrollment_date, grade_level, program, email, phone, city, 
            school_days, days_present, late_arrivals, assignments_completed, 
            exam_average, days_absent, absence_rate, academic_progress
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        row["student_id"], 
        row.get("full_name", ""),
        str(row.get("dob", "")),
        str(row.get("enrollment_date", "")),
        row.get("grade_level", ""),
        row["program"], 
        row.get("email", ""), 
        row.get("phone", ""), 
        row.get("city", ""),
        row["school_days"], 
        row["days_present"], 
        row["late_arrivals"], 
        row["assignments_completed"], 
        row["exam_average"], 
        row["days_absent"], 
        row["absence_rate"], 
        row["academic_progress"]
    ))
    if emp_password:
        cursor.execute('''
            INSERT OR REPLACE INTO student_credentials (student_id, password) VALUES (?, ?)
        ''', (row["student_id"], emp_password))
    conn.commit()
    conn.close()

def verify_student_password(school_name, emp_id, password):
    init_school_db(school_name)
    db_file = f"school_{sanitize_name(school_name)}.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM student_credentials WHERE student_id = ?", (emp_id,))
    row = cursor.fetchone()
    conn.close()
    return row and row[0] == password

def load_daily_logs_from_db(school_name):
    init_school_db(school_name)
    db_file = f"school_{sanitize_name(school_name)}.db"
    conn = sqlite3.connect(db_file)
    df = pd.read_sql_query("SELECT * FROM daily_logs", conn)
    conn.close()
    return df

def save_daily_log_to_db(school_name, log_row):
    db_file = f"school_{sanitize_name(school_name)}.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO daily_logs (date, student_id, status, remarks)
        VALUES (?, ?, ?, ?)
    ''', (str(log_row["Date"]), log_row["Student ID"], log_row["Status"], log_row["Remarks"]))
    conn.commit()
    conn.close()

def load_announcements_from_db(school_name):
    init_school_db(school_name)
    db_file = f"school_{sanitize_name(school_name)}.db"
    conn = sqlite3.connect(db_file)
    df = pd.read_sql_query("SELECT * FROM announcements ORDER BY id DESC", conn)
    conn.close()
    return df

def save_announcement_to_db(school_name, title, message, posted_by):
    db_file = f"school_{sanitize_name(school_name)}.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO announcements (date, title, message, posted_by) VALUES (?, ?, ?, ?)", 
                   (str(date.today()), title, message, posted_by))
    conn.commit()
    conn.close()

def load_absence_requests_from_db(school_name):
    init_school_db(school_name)
    db_file = f"school_{sanitize_name(school_name)}.db"
    conn = sqlite3.connect(db_file)
    df = pd.read_sql_query("SELECT * FROM absence_requests ORDER BY id DESC", conn)
    conn.close()
    return df

def save_absence_request_to_db(school_name, emp_id, request_type, start_date, end_date, reason):
    db_file = f"school_{sanitize_name(school_name)}.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO absence_requests (student_id, request_type, start_date, end_date, reason, status) VALUES (?, ?, ?, ?, ?, ?)", 
                   (emp_id, request_type, str(start_date), str(end_date), reason, "Pending"))
    conn.commit()
    conn.close()

def update_absence_status_in_db(school_name, absence_id, status):
    db_file = f"school_{sanitize_name(school_name)}.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("UPDATE absence_requests SET status = ? WHERE id = ?", (status, absence_id))
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

if "logged_in_school" not in st.session_state:
    st.session_state.logged_in_school = None

if "user_role" not in st.session_state:
    st.session_state.user_role = None

if "logged_in_user_id" not in st.session_state:
    st.session_state.logged_in_user_id = None

if "just_registered_school" not in st.session_state:
    st.session_state.just_registered_school = None

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
        st.markdown("<h1 style='text-align: center;'>🔐 Secure Portal Login</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Sign in as School Admin, Student, or Register a School</p>", unsafe_allow_html=True)
        
        schools = get_registered_schools()
        
        if not schools:
            st.warning("⚠️ No schools registered yet! Please go to the **'Register School'** tab to create your school and admin accounts.")
            
        login_tab1, login_tab2, login_tab3 = st.tabs(["🔑 Admin Sign In", "👤 Student Sign In", "🏢 Register School"])
        
        with login_tab1:
            with st.form("admin_login_form"):
                if schools:
                    default_index = 0
                    if st.session_state.just_registered_school in schools:
                        default_index = schools.index(st.session_state.just_registered_school)
                    
                    sel_school = st.selectbox("Select School", options=schools, index=default_index, key="admin_sel_comp")
                else:
                    sel_school = st.selectbox("Select School", options=["No Schools Available"], key="admin_sel_comp_empty")
                
                admin_id_input = st.text_input("Admin User ID", placeholder="e.g., admin or registrar1")
                admin_password = st.text_input("Admin Password", type="password", placeholder="Enter admin password")
                
                admin_submitted = st.form_submit_button("Access Admin Dashboard", use_container_width=True)
                
                if admin_submitted:
                    if not schools:
                        st.error("Please register a school first.")
                    elif admin_id_input and verify_admin_login(sel_school, admin_id_input, admin_password):
                        st.session_state.authenticated = True
                        st.session_state.logged_in_school = sel_school
                        st.session_state.user_role = "Admin"
                        st.session_state.logged_in_user_id = admin_id_input
                        st.session_state.history.clear()
                        st.session_state.redo_stack.clear()
                        st.success(f"Welcome Admin '{admin_id_input}' of {sel_school}!")
                        st.rerun()
                    else:
                        st.error("Invalid Admin User ID or Password.")

        with login_tab2:
            with st.form("emp_login_form"):
                st.markdown("##### Select your school and enter your Student ID & personal password.")
                emp_school = st.selectbox("Select School", options=schools if schools else ["No Schools Available"], key="emp_sel_comp")
                emp_id_input = st.text_input("Student ID", placeholder="e.g., STU101")
                emp_password = st.text_input("Student Personal Password", type="password", placeholder="Enter your student password")
                
                emp_submitted = st.form_submit_button("Access Student Portal", use_container_width=True)
                
                if emp_submitted:
                    if not schools:
                        st.error("Please register a school first.")
                    elif emp_id_input and verify_student_password(emp_school, emp_id_input, emp_password):
                        st.session_state.authenticated = True
                        st.session_state.logged_in_school = emp_school
                        st.session_state.user_role = "Student"
                        st.session_state.logged_in_user_id = emp_id_input
                        st.success(f"Welcome, {emp_id_input}!")
                        st.rerun()
                    else:
                        st.error("Invalid Student ID or Password.")

        with login_tab3:
            st.markdown("### Register Company & Master Password")
            
            # 1. Company Name & Password
            new_comp = st.text_input("New Company Name", placeholder="e.g., Apex Global", key="reg_comp_name")
            company_master_pass = st.text_input("Company Master Password", type="password", placeholder="Set master password for company", key="reg_comp_pass")
            
            # 2. Number input OUTSIDE the form so changing it immediately reruns and creates dynamic inputs
            num_admins = st.number_input("Number of Admin Accounts Needed", min_value=1, max_value=5, value=1, step=1, key="reg_num_admins")
            
            # 3. Dynamic Admin Inputs generated based on 'num_admins'
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
            
            # 4. Submit button to register company
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
cur_comp = st.session_state.logged_in_school
current_role = st.session_state.user_role
logged_user_id = st.session_state.logged_in_user_id

df = load_students_from_db(cur_comp)
daily_log = load_daily_logs_from_db(cur_comp)
announcements_df = load_announcements_from_db(cur_comp)
absence_df = load_absence_requests_from_db(cur_comp)

def push_history(current_df):
    st.session_state.history.append(current_df.copy())
    st.session_state.redo_stack.clear()

# --- SIDEBAR CONTROL CENTER ---
st.sidebar.markdown(f"## 🏢 {cur_comp}")
st.sidebar.markdown(f"**User:** `{logged_user_id}`  \n**Role:** `{current_role}`")

if st.sidebar.button("🚪 Log Out", use_container_width=True):
    st.session_state.authenticated = False
    st.session_state.logged_in_school = None
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
                init_school_db(cur_comp)
                conn = sqlite3.connect(f"school_{sanitize_name(cur_comp)}.db")
                previous_df.to_sql("students", conn, if_exists="replace", index=False)
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
                conn = sqlite3.connect(f"school_{sanitize_name(cur_comp)}.db")
                next_df.to_sql("students", conn, if_exists="replace", index=False)
                conn.close()
                st.success("Redone!")
                st.rerun()
            else:
                st.warning("Nothing to redo")

    with st.sidebar.expander("➕ Register New Student"):
        with st.form(f"quick_id_form_{cur_comp}"):
            quick_id = st.text_input("Student ID *", placeholder="e.g., STU101")
            quick_pass = st.text_input("Password *", type="password", placeholder="Set password")
            quick_name = st.text_input("Full Name", placeholder="e.g., Rajesh Kumar")
            
            # ALLOW ANY YEAR FOR DOB FROM 1950 UP TO TODAY
            quick_dob = st.date_input(
                "Date of Birth", 
                value=date(1995, 1, 1), 
                min_value=date(1950, 1, 1), 
                max_value=date.today()
            )
            quick_joined = st.date_input("Enrollment Date", value=date.today())
            quick_grade_level = st.text_input("Grade / Level", placeholder="e.g., Grade 10")
            quick_email = st.text_input("Email", placeholder="e.g., alex@northview.edu")
            quick_phone = st.text_input("Phone Number", placeholder="e.g., +91 9876543210")
            
            quick_city = st.selectbox("District / City", [
                "Mumbai", "Delhi", "Bengaluru", "Chennai", "Hyderabad", "Kolkata", 
                "Pune", "Ahmedabad", "Jaipur", "Surat", "Lucknow", "Kanpur", 
                "Nagpur", "Indore", "Thane", "Bhopal", "Visakhapatnam", "Patna", 
                "Vadodara", "Ghaziabad", "Ludhiana", "Agra", "Nashik", "Ranchi", "Coimbatore", "Madurai",
                "Gurugram", "Noida", "Chandigarh", "Kochi", "Thiruvananthapuram", "Mysuru", "Bhubaneswar"
            ])
            quick_dept = st.selectbox("Program", ["Grade 9", "Grade 10", "Grade 11", "Grade 12", "Science", "Arts", "Commerce", "Computer Science"], key=f"q_dept_{cur_comp}")
            
            quick_submit = st.form_submit_button("Save Student", use_container_width=True)
            
            if quick_submit:
                if not quick_id or not quick_pass:
                    st.sidebar.error("ID and Password are required.")
                elif not df.empty and quick_id in df["student_id"].values:
                    st.sidebar.error("Student ID already exists.")
                else:
                    push_history(df)
                    school_days = 22
                    new_row = {
                        "student_id": quick_id,
                        "full_name": quick_name,
                        "dob": str(quick_dob),
                        "enrollment_date": str(quick_joined),
                        "grade_level": quick_grade_level,
                        "program": quick_dept,
                        "email": quick_email,
                        "phone": quick_phone,
                        "city": quick_city,
                        "school_days": school_days,
                        "days_present": 0,
                        "late_arrivals": 0,
                        "assignments_completed": 0,
                        "exam_average": 0.0,
                        "days_absent": school_days,
                        "absence_rate": 100.0,
                        "academic_progress": 0.0
                    }
                    save_student_to_db(cur_comp, new_row, emp_password=quick_pass)
                    st.sidebar.success(f"Created '{quick_id}' successfully!")
                    st.rerun()

    with st.sidebar.expander("✏️ Update Student Details"):
        if not df.empty:
            existing_ids = df["student_id"].unique()
            update_id = st.selectbox("Select Student ID", options=existing_ids, key=f"up_id_{cur_comp}")
            
            current_row = df[df["student_id"] == update_id].iloc[0]
            dept_list = ["Grade 9", "Grade 10", "Grade 11", "Grade 12", "Science", "Arts", "Commerce", "Computer Science"]
            curr_dept_idx = dept_list.index(current_row["program"]) if current_row["program"] in dept_list else 0
            
            update_name = st.text_input("Full Name", value=str(current_row.get("full_name", "")), key=f"up_name_{cur_comp}")
            
            curr_dob = parse_date_safely(current_row.get("dob", ""), date(1995, 1, 1))
            curr_joined = parse_date_safely(current_row.get("enrollment_date", ""), date.today())
            
            # ALLOW ANY YEAR FOR DOB FROM 1950 UP TO TODAY
            update_dob = st.date_input(
                "Date of Birth", 
                value=curr_dob, 
                min_value=date(1950, 1, 1), 
                max_value=date.today(),
                key=f"up_dob_{cur_comp}"
            )
            update_joined = st.date_input(
                "Enrollment Date", 
                value=curr_joined, 
                min_value=date(1980, 1, 1),
                max_value=date.today(),
                key=f"up_joined_{cur_comp}"
            )
            
            update_grade_level = st.text_input("Grade / Level", value=str(current_row.get("grade_level", "")), key=f"up_grade_level_{cur_comp}")
            update_email = st.text_input("Email", value=str(current_row.get("email", "")), key=f"up_email_{cur_comp}")
            update_phone = st.text_input("Phone Number", value=str(current_row.get("phone", "")), key=f"up_phone_{cur_comp}")
            update_city = st.text_input("City / District", value=str(current_row.get("city", "")), key=f"up_city_{cur_comp}")
            update_dept = st.selectbox("Program", dept_list, index=curr_dept_idx, key=f"up_dept_{cur_comp}")
            
            update_school_days = st.number_input("Total School Days", min_value=1, max_value=31, value=int(current_row["school_days"]), key=f"up_total_days_{cur_comp}")
            update_present = st.slider("Days Present", 0, int(update_school_days), int(current_row["days_present"]), key=f"up_pres_{cur_comp}")
            update_late = st.slider("Days Late", 0, 5, int(current_row["late_arrivals"]), key=f"up_late_{cur_comp}")
            update_tasks = st.number_input("Assignments Completed", min_value=0, max_value=200, value=int(current_row["assignments_completed"]), key=f"up_tasks_{cur_comp}")
            update_score = st.slider("Exam Average", 0.0, 100.0, float(current_row["exam_average"]), key=f"up_score_{cur_comp}")
            
            if st.button("Update Student", key=f"update_btn_{cur_comp}", use_container_width=True):
                push_history(df)
                days_absent = update_school_days - update_present
                absence_rate = round((days_absent / update_school_days) * 100, 2) if update_school_days > 0 else 0.0
                academic_progress = round(update_score, 2)
                
                updated_row = {
                    "student_id": update_id,
                    "full_name": update_name,
                    "dob": str(update_dob),
                    "enrollment_date": str(update_joined),
                    "grade_level": update_grade_level,
                    "program": update_dept,
                    "email": update_email,
                    "phone": update_phone,
                    "city": update_city,
                    "school_days": update_school_days,
                    "days_present": update_present,
                    "late_arrivals": update_late,
                    "assignments_completed": update_tasks,
                    "exam_average": update_score,
                    "days_absent": days_absent,
                    "absence_rate": absence_rate,
                    "academic_progress": academic_progress
                }
                save_student_to_db(cur_comp, updated_row)
                st.sidebar.success(f"Updated '{update_id}'!")
                st.rerun()
        else:
            st.info("No student records found.")

    with st.sidebar.expander("🖼️ Branding & Logo"):
        uploaded_logo = st.file_uploader(f"School Logo ({cur_comp})", type=["png", "jpg", "jpeg"], key=f"logo_{cur_comp}")
        if uploaded_logo is not None:
            logo_bytes = uploaded_logo.getvalue()
            save_school_logo_to_db(cur_comp, logo_bytes)
            st.sidebar.success("Logo updated successfully!")
            st.rerun()

    with st.sidebar.expander("🗑️ System Maintenance"):
        st.warning("Deletes all school records permanently.")
        if st.button("Reset School Data", key=f"clear_data_{cur_comp}", use_container_width=True):
            clear_all_school_records(cur_comp)
            st.sidebar.success("Records cleared!")
            st.rerun()

    st.sidebar.markdown("---")

    st.sidebar.markdown("### 🔍 Filter Records")
    dept_options = ["All"] + list(df["program"].unique()) if not df.empty else ["All"]
    selected_dept = st.sidebar.selectbox("Program Filter", dept_options, key=f"filter_dept_{cur_comp}")
    filtered_df = df[df["program"] == selected_dept] if selected_dept != "All" else df
else:
    st.sidebar.info(f"👤 **Student Portal Access**\nYou can view your complete personal profile, academic progress, notices, and submit absence requests.")
    filtered_df = df[df["student_id"] == logged_user_id]

# Render Top Dynamic Header
header_col1, header_col2 = st.columns([1, 8])
with header_col1:
    db_logo_bytes = load_school_logo_from_db(cur_comp)
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
        st.title(f"{cur_comp} - Student Workspace")

st.markdown(f"Active Workspace: **{current_role} Mode** | School: **{cur_comp}**")

# --- CREATE APPLICATION TABS ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboard & Profile", 
    "📅 Class Attendance", 
    "📢 Announcements", 
    "📝 Absence Requests"
])

# ==========================================
# TAB 1: DASHBOARD & PROFILE
# ==========================================
with tab1:
    col1, col2, col3, col4 = st.columns(4)
    total_emps = len(filtered_df)
    avg_abs = f"{filtered_df['absence_rate'].mean():.2f}%" if total_emps > 0 else "0.00%"
    avg_prod = f"{filtered_df['academic_progress'].mean():.2f}" if total_emps > 0 else "0.00"
    total_tasks = int(filtered_df['assignments_completed'].sum()) if total_emps > 0 else 0

    if current_role == "Admin":
        col1.metric("Total Students", total_emps)
        col2.metric("Avg Absence Rate", avg_abs)
        col3.metric("Avg Academic Progress Score", avg_prod)
        col4.metric("Total Assignments Completed", total_tasks)
        st.markdown("---")

        if total_emps > 0:
            col_left, col_right = st.columns(2)
            with col_left:
                st.subheader("📈 Attendance vs. Academic Progress")
                fig, ax = plt.subplots(figsize=(6, 4))
                sns.scatterplot(data=filtered_df, x="absence_rate", y="academic_progress", hue="program", palette="viridis", s=70, ax=ax, alpha=0.8)
                ax.set_xlabel("Absence Rate (%)")
                ax.set_ylabel("Academic Progress Score")
                ax.grid(True, linestyle="--", alpha=0.5)
                st.pyplot(fig)

            with col_right:
                st.subheader("📊 Avg Academic Progress by Program")
                dept_avg = df.groupby("program")["academic_progress"].mean().reset_index()
                fig2, ax2 = plt.subplots(figsize=(6, 4))
                sns.barplot(data=dept_avg, x="program", y="academic_progress", palette="crest", ax=ax2)
                ax2.set_xlabel("Program")
                ax2.set_ylabel("Avg Academic Progress Score")
                ax2.grid(axis="y", linestyle="--", alpha=0.5)
                st.pyplot(fig2)

            st.subheader("📋 Detailed Student Records Table")
            st.dataframe(filtered_df, use_container_width=True)

            st.markdown("---")
            st.subheader("🔍 Student Profile & Performance Viewer")
            selected_emp_profile = st.selectbox("Select Student ID to View Details", options=filtered_df["student_id"].unique(), key=f"profile_sel_{cur_comp}")
            
            if selected_emp_profile:
                emp_data = filtered_df[filtered_df["student_id"] == selected_emp_profile].iloc[0]
                
                col_pers, col_prof = st.columns(2)
                
                with col_pers:
                    st.markdown("### 👤 Personal Details")
                    st.write(f"**Full Name:** {emp_data.get('full_name', 'N/A')}")
                    st.write(f"**Student ID:** {emp_data['student_id']}")
                    st.write(f"**Date of Birth:** {emp_data.get('dob', 'N/A')}")
                    st.write(f"**Grade / Level:** {emp_data.get('grade_level', 'N/A')}")
                    st.write(f"**Email Address:** {emp_data.get('email', 'N/A')}")
                    st.write(f"**Phone Number:** {emp_data.get('phone', 'N/A')}")
                    st.write(f"**Enrollment Date:** {emp_data.get('enrollment_date', 'N/A')}")
                    st.write(f"**City:** {emp_data.get('city', 'N/A')}")

                with col_prof:
                    st.markdown("### 💼 Academic Details")
                    st.write(f"**Student ID:** {emp_data['student_id']}")
                    st.write(f"**Program:** {emp_data['program']}")
                    st.write(f"**Grade / Level:** {emp_data.get('grade_level', 'N/A')}")
                    st.write(f"**Days of Attendance:** {emp_data['days_present']} Present / {emp_data['school_days']} Total School Days")
                    st.write(f"**Days Late:** {emp_data['late_arrivals']}")
                    st.write(f"**Assignments Completed:** {emp_data['assignments_completed']}")
                    st.write(f"**Exam Average:** {emp_data['exam_average']}")
                    st.write(f"**Absence Rate:** {emp_data['absence_rate']}%")
                    st.write(f"**Academic Progress Score:** {emp_data['academic_progress']}")
        else:
            st.info("No records present. Add a new student using the sidebar controls.")

    else:
        col1.metric("My Attendance Days", f"{int(filtered_df['days_present'].values[0]) if total_emps > 0 else 0} / {int(filtered_df['school_days'].values[0]) if total_emps > 0 else 0}")
        col2.metric("My Absence Rate", avg_abs)
        col3.metric("My Academic Progress Score", avg_prod)
        col4.metric("Assignments Completed", total_tasks)
        st.markdown("---")

        if total_emps > 0:
            emp_data = filtered_df.iloc[0]
            st.subheader(f"👤 Student Details for {emp_data.get('full_name', logged_user_id)} ({emp_data['student_id']})")
            
            col_pers, col_prof = st.columns(2)
            
            with col_pers:
                st.markdown("### 👤 Personal Details")
                st.write(f"**Full Name:** {emp_data.get('full_name', 'N/A')}")
                st.write(f"**Student ID:** {emp_data['student_id']}")
                st.write(f"**Date of Birth:** {emp_data.get('dob', 'N/A')}")
                st.write(f"**Grade / Level:** {emp_data.get('grade_level', 'N/A')}")
                st.write(f"**Email Address:** {emp_data.get('email', 'N/A')}")
                st.write(f"**Phone Number:** {emp_data.get('phone', 'N/A')}")
                st.write(f"**Enrollment Date:** {emp_data.get('enrollment_date', 'N/A')}")
                st.write(f"**City:** {emp_data.get('city', 'N/A')}")

            with col_prof:
                st.markdown("### 💼 Academic Details")
                st.write(f"**Student ID:** {emp_data['student_id']}")
                st.write(f"**Program:** {emp_data['program']}")
                st.write(f"**Grade / Level:** {emp_data.get('grade_level', 'N/A')}")
                st.write(f"**Days of Attendance:** {emp_data['days_present']} Present / {emp_data['school_days']} Total School Days")
                st.write(f"**Days Late:** {emp_data['late_arrivals']}")
                st.write(f"**Assignments Completed:** {emp_data['assignments_completed']}")
                st.write(f"**Exam Average:** {emp_data['exam_average']}")
                st.write(f"**Absence Rate:** {emp_data['absence_rate']}%")
                st.write(f"**Academic Progress Score:** {emp_data['academic_progress']}")
        else:
            st.warning("No profile record found for your Student ID. Please contact your school Admin.")

# ==========================================
# TAB 2: DAILY ATTENDANCE MANAGER
# ==========================================
with tab2:
    if current_role == "Admin":
        st.subheader("📅 Log Daily Attendance")
        if not df.empty:
            with st.form("daily_att_form"):
                att_date = st.date_input("Attendance Date", value=date.today())
                att_emp = st.selectbox("Student ID", options=df["student_id"].unique(), key="att_emp_sel")
                att_status = st.selectbox("Status", ["Present", "Absent", "Late", "Half-Day"])
                att_remarks = st.text_input("Remarks", placeholder="e.g., Present, excused absence, school trip")
                
                att_submit = st.form_submit_button("Record Daily Log")
                if att_submit:
                    log_row = {
                        "Date": att_date,
                        "Student ID": att_emp,
                        "Status": att_status,
                        "Remarks": att_remarks
                    }
                    save_daily_log_to_db(cur_comp, log_row)
                    st.success(f"Attendance recorded for {att_emp} on {att_date}!")
                    st.rerun()
        else:
            st.warning("No students available to log attendance.")

        st.markdown("---")
        st.subheader("📋 School Attendance Records")
        if not daily_log.empty:
            st.dataframe(daily_log, use_container_width=True)
        else:
            st.info("No attendance logs recorded yet.")
    else:
        st.subheader("📅 My Attendance Records")
        my_logs = daily_log[daily_log["student_id"] == logged_user_id] if not daily_log.empty else pd.DataFrame()
        if not my_logs.empty:
            st.dataframe(my_logs, use_container_width=True)
        else:
            st.info("No attendance logs found for your ID.")

# ==========================================
# TAB 3: ANNOUNCEMENTS BOARD
# ==========================================
with tab3:
    st.subheader("📢 School Announcements & Notices")
    
    if current_role == "Admin":
        with st.expander("➕ Post New Announcement"):
            with st.form("announcement_form"):
                ann_title = st.text_input("Notice Title", placeholder="e.g., School Closure Notice")
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
        st.info("No school announcements posted yet.")

# ==========================================
# TAB 4: ABSENCE REQUESTS
# ==========================================
with tab4:
    if current_role == "Admin":
        st.subheader("📝 Manage Student Absence Applications")
        if not absence_df.empty:
            st.dataframe(absence_df, use_container_width=True)
            
            st.markdown("### ⚙️ Approve or Reject Absence Request")
            pending_ids = absence_df[absence_df["status"] == "Pending"]["id"].tolist()
            if pending_ids:
                selected_absence_id = st.selectbox("Select Pending Absence ID", options=pending_ids)
                col_app, col_rej = st.columns(2)
                with col_app:
                    if st.button("✅ Approve Absence", use_container_width=True):
                        update_absence_status_in_db(cur_comp, selected_absence_id, "Approved")
                        st.success(f"Absence Request #{selected_absence_id} Approved!")
                        st.rerun()
                with col_rej:
                    if st.button("❌ Reject Absence", use_container_width=True):
                        update_absence_status_in_db(cur_comp, selected_absence_id, "Rejected")
                        st.warning(f"Absence Request #{selected_absence_id} Rejected.")
                        st.rerun()
            else:
                st.info("No pending absence requests to review.")
        else:
            st.info("No absence applications submitted yet.")
    else:
        st.subheader("📝 Apply for Absence")
        with st.form("apply_absence_form"):
            request_type = st.selectbox("Absence Type", ["Medical", "Family Emergency", "School Activity", "Other"])
            start_d = st.date_input("Start Date", value=date.today())
            end_d = st.date_input("End Date", value=date.today())
            reason = st.text_area("Reason for Absence", placeholder="Provide brief reason...")
            
            absence_submit = st.form_submit_button("Submit Absence Application", use_container_width=True)
            if absence_submit:
                if not reason:
                    st.error("Please provide a reason for your absence.")
                else:
                    save_absence_request_to_db(cur_comp, logged_user_id, request_type, start_d, end_d, reason)
                    st.success("Absence application submitted successfully!")
                    st.rerun()

        st.markdown("---")
        st.subheader("📋 My Absence Application History")
        my_absences = absence_df[absence_df["student_id"] == logged_user_id] if not absence_df.empty else pd.DataFrame()
        if not my_absences.empty:
            st.dataframe(my_absences, use_container_width=True)
        else:
            st.info("You have not submitted any absence applications yet.")



