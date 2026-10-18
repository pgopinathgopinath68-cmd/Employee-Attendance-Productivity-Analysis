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

# ==========================================
# 1. PAGE CONFIGURATION & BACKEND STYLING
# ==========================================
st.set_page_config(page_title="Secure Multi-Admin Attendance Dashboard", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    /* Main Background with Corporate Glass Building Image & Dark Overlay */
    .stApp {
        background: linear-gradient(rgba(10, 17, 30, 0.7), rgba(15, 23, 42, 0.8)), 
                    url("https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?q=80&w=2070&auto=format&fit=crop");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Inter', sans-serif;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.95);
        border-right: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 4px 0 25px rgba(0,0,0,0.2);
    }

    /* Metric Cards Styling (Transparent Frosted Glass) */
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.08) !important;
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
        padding: 18px 22px;
        border-radius: 14px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    [data-testid="stMetricLabel"] p {
        font-size: 15px !important;
        color: #cbd5e1 !important;
        font-weight: 700 !important;
        text-shadow: 0 1px 3px rgba(0,0,0,0.9);
    }
    [data-testid="stMetricValue"] {
        font-size: 32px !important;
        color: #ffffff !important;
        font-weight: 900 !important;
        text-shadow: 0 2px 6px rgba(0,0,0,0.9);
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(255, 255, 255, 0.12);
        border: 1px solid rgba(255, 255, 255, 0.25);
        border-radius: 8px 8px 0px 0px;
        padding: 10px 24px;
        color: #ffffff;
        font-weight: 700;
        backdrop-filter: blur(10px);
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        color: #ffffff !important;
        border-color: #2563eb !important;
    }

    /* Dashboard Headers and Subtitles */
    h1, h2, h3 {
        color: #ffffff !important;
        font-weight: 900;
        text-shadow: 0 2px 8px rgba(0,0,0,0.8);
    }
    p, span {
        color: #f1f5f9 !important;
        font-weight: 700;
        text-shadow: 0 1px 4px rgba(0,0,0,0.8);
    }

    /* Sidebar Text Dark Color Override */
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, 
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
        color: #0f172a !important;
        text-shadow: none !important;
    }
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

    cursor.execute("PRAGMA table_info(companies)")
    columns = [col[1] for col in cursor.fetchall()]
    if "logo" not in columns:
        cursor.execute("ALTER TABLE companies ADD COLUMN logo BLOB")
    if "company_password" not in columns:
        cursor.execute("ALTER TABLE companies ADD COLUMN company_password TEXT")
        
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
    if row and row[0] == password:
        return True
    return False

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
    if row and row[0]:
        return row[0]
    return None

def init_company_db(company_name):
    db_file = f"company_{sanitize_name(company_name)}.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            employee_id TEXT PRIMARY KEY,
            department TEXT,
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
    conn.commit()
    conn.close()

def load_employees_from_db(company_name):
    init_company_db(company_name)
    db_file = f"company_{sanitize_name(company_name)}.db"
    conn = sqlite3.connect(db_file)
    df = pd.read_sql_query("SELECT * FROM employees", conn)
    conn.close()
    if "photo" not in df.columns:
        df["photo"] = None
    return df

def save_employee_to_db(company_name, row, emp_password=None):
    init_company_db(company_name)
    db_file = f"company_{sanitize_name(company_name)}.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO employees VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        row["employee_id"], row["department"], row["total_workdays"], 
        row["days_present"], row["days_late"], row["tasks_completed"], 
        row["avg_task_score"], row["days_absent"], row["absenteeism_rate"], 
        row["productivity_score"]
    ))
    if emp_password:
        cursor.execute('''
            INSERT OR REPLACE INTO employee_credentials VALUES (?, ?)
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
    if row and row[0] == password:
        return True
    return False

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
        st.markdown("<h1 style='text-align: center;'>🔐 Secure Portal Login</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Sign in as Company Admin, Employee, or Register a Company</p>", unsafe_allow_html=True)
        
        companies = get_registered_companies()
        
        if not companies:
            st.warning("⚠️ No companies registered yet! Please go to the **'Register Company'** tab to create your company and admin accounts.")
            
        login_tab1, login_tab2, login_tab3 = st.tabs(["🔑 Admin Sign In", "👤 Employee Sign In", "🏢 Register Company"])
        
        # --- TAB 1: ADMIN SIGN IN ---
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

        # --- TAB 2: EMPLOYEE SIGN IN (NO COMPANY PASSWORD NEEDED) ---
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

        # --- TAB 3: REGISTER NEW COMPANY & MASTER PASSWORD ---
        with login_tab3:
            with st.form("register_form"):
                st.markdown("### Register Company & Master Password")
                new_comp = st.text_input("New Company Name", placeholder="e.g., Apex Global", key="reg_comp_name")
                company_master_pass = st.text_input("Company Master Password", type="password", placeholder="Set master password for company", key="reg_comp_pass")
                
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
                
                reg_submitted = st.form_submit_button("Register Company & Create Admins", use_container_width=True)
                
                if reg_submitted:
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

def push_history(current_df):
    st.session_state.history.append(current_df.copy())
    st.session_state.redo_stack.clear()

# --- SIDEBAR PROFILE & LOGOUT ---
st.sidebar.markdown(f"### 🏢 Portal: {cur_comp}")
if current_role == "Admin":
    st.sidebar.markdown(f"Role: **Admin** 🛡️\nUser ID: **{logged_user_id}**")
else:
    st.sidebar.markdown(f"Role: **Employee** 👤\nID: **{logged_user_id}**")

if st.sidebar.button("🚪 Log Out", use_container_width=True):
    st.session_state.authenticated = False
    st.session_state.logged_in_company = None
    st.session_state.user_role = None
    st.session_state.logged_in_user_id = None
    st.rerun()

st.sidebar.markdown("---")

if current_role == "Admin":
    uploaded_logo = st.sidebar.file_uploader(f"Update Logo for {cur_comp}", type=["png", "jpg", "jpeg"], key=f"logo_{cur_comp}")
    if uploaded_logo is not None:
        logo_bytes = uploaded_logo.getvalue()
        save_company_logo_to_db(cur_comp, logo_bytes)
        st.sidebar.success("Company logo updated permanently!")
        st.rerun()
    st.sidebar.markdown("---")

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
        st.title(f"{cur_comp} - Admin Dashboard ({logged_user_id})")
    else:
        st.title(f"{cur_comp} - Employee Performance Portal")

st.markdown(f"Workspace mode: **{current_role} Access** for **{cur_comp}**.")

# --- CREATE APPLICATION TABS ---
tab1, tab2 = st.tabs(["📊 Dashboard & Analytics", "📅 Daily Attendance Manager"])

# ==========================================
# TAB 1: DASHBOARD & ANALYTICS
# ==========================================
with tab1:
    if current_role == "Admin":
        st.sidebar.header("⚙️ Employee Management (Admin)")

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
                    st.success("Action undone!")
                    st.rerun()
                else:
                    st.warning("Nothing to undo!")
        with ur_col2:
            if st.button("🔁 Redo", use_container_width=True):
                if st.session_state.redo_stack:
                    st.session_state.history.append(df.copy())
                    next_df = st.session_state.redo_stack.pop()
                    conn = sqlite3.connect(f"company_{sanitize_name(cur_comp)}.db")
                    next_df.to_sql("employees", conn, if_exists="replace", index=False)
                    conn.close()
                    st.success("Action redone!")
                    st.rerun()
                else:
                    st.warning("Nothing to redo!")

        st.sidebar.markdown("---")

        with st.sidebar.expander("🆔 Create Employee ID & Password"):
            with st.form(f"quick_id_form_{cur_comp}"):
                quick_id = st.text_input("New Employee ID", placeholder="e.g., EMP101")
                quick_pass = st.text_input("Employee Login Password", type="password", placeholder="Set password for employee")
                quick_dept = st.selectbox("Department", ["Engineering", "Sales", "HR", "Marketing"], key=f"q_dept_{cur_comp}")
                quick_photo = st.file_uploader("Upload Employee Photo", type=["png", "jpg", "jpeg"], key=f"q_photo_{cur_comp}")
                
                quick_submit = st.form_submit_button("Create ID & Credentials")
                
                if quick_submit:
                    if not quick_id or not quick_pass:
                        st.sidebar.error("Please enter both Employee ID and Password.")
                    elif quick_id in df["employee_id"].values:
                        st.sidebar.error("Error: ID already exists!")
                    else:
                        push_history(df)
                        total_workdays = 22
                        new_row = {
                            "employee_id": quick_id,
                            "department": quick_dept,
                            "total_workdays": total_workdays,
                            "days_present": 0,
                            "days_late": 0,
                            "tasks_completed": 0,
                            "avg_task_score": 0.0,
                            "days_absent": total_workdays,
                            "absenteeism_rate": 100.0,
                            "productivity_score": 0.0,
                            "photo": quick_photo
                        }
                        save_employee_to_db(cur_comp, new_row, emp_password=quick_pass)
                        st.sidebar.success(f"ID '{quick_id}' and login password created successfully!")
                        st.rerun()

        with st.sidebar.expander("📋 Update Employee Details"):
            if not df.empty:
                existing_ids = df["employee_id"].unique()
                update_id = st.selectbox("Select Existing Employee ID", options=existing_ids, key=f"up_id_{cur_comp}")
                
                current_row = df[df["employee_id"] == update_id].iloc[0]
                dept_list = ["Engineering", "Sales", "HR", "Marketing"]
                curr_dept_idx = dept_list.index(current_row["department"]) if current_row["department"] in dept_list else 0
                
                update_dept = st.selectbox("Department", dept_list, index=curr_dept_idx, key=f"up_dept_{cur_comp}")
                update_total_workdays = st.number_input("Total Workdays", min_value=1, max_value=31, value=int(current_row["total_workdays"]), key=f"up_total_days_{cur_comp}")
                update_present = st.slider("Days Present", 0, int(update_total_workdays), int(current_row["days_present"]), key=f"up_pres_{cur_comp}")
                update_late = st.slider("Days Late", 0, 5, int(current_row["days_late"]), key=f"up_late_{cur_comp}")
                update_tasks = st.number_input("Tasks Completed", min_value=0, max_value=200, value=int(current_row["tasks_completed"]), key=f"up_tasks_{cur_comp}")
                update_score = st.slider("Avg Task Score", 0.0, 100.0, float(current_row["avg_task_score"]), key=f"up_score_{cur_comp}")
                
                if st.button("Update Details", key=f"update_btn_{cur_comp}"):
                    push_history(df)
                    days_absent = update_total_workdays - update_present
                    absenteeism_rate = round((days_absent / update_total_workdays) * 100, 2) if update_total_workdays > 0 else 0.0
                    productivity_score = round((update_tasks * 0.6) + (update_score * 0.4), 2)
                    
                    updated_row = {
                        "employee_id": update_id,
                        "department": update_dept,
                        "total_workdays": update_total_workdays,
                        "days_present": update_present,
                        "days_late": update_late,
                        "tasks_completed": update_tasks,
                        "avg_task_score": update_score,
                        "days_absent": days_absent,
                        "absenteeism_rate": absenteeism_rate,
                        "productivity_score": productivity_score,
                        "photo": current_row["photo"] if "photo" in current_row else None
                    }
                    save_employee_to_db(cur_comp, updated_row)
                    st.sidebar.success(f"Details for '{update_id}' updated successfully!")
                    st.rerun()
            else:
                st.info("No employee IDs found.")

        with st.sidebar.expander("📁 Upload CSV Data"):
            st.markdown("Upload a CSV file containing employee records.")
            uploaded_csv = st.file_uploader("Choose CSV File", type=["csv"], key=f"csv_upload_{cur_comp}")
            
            if uploaded_csv is not None:
                try:
                    csv_df = pd.read_csv(uploaded_csv)
                    if "days_absent" not in csv_df.columns:
                        csv_df["days_absent"] = csv_df["total_workdays"] - csv_df["days_present"]
                    if "absenteeism_rate" not in csv_df.columns:
                        csv_df["absenteeism_rate"] = round((csv_df["days_absent"] / csv_df["total_workdays"]) * 100, 2)
                    if "productivity_score" not in csv_df.columns:
                        csv_df["productivity_score"] = round((csv_df["tasks_completed"] * 0.6) + (csv_df["avg_task_score"] * 0.4), 2)
                    if "photo" not in csv_df.columns:
                        csv_df["photo"] = None
                    
                    if st.button("Import CSV Records", key=f"import_csv_{cur_comp}"):
                        push_history(df)
                        for _, row in csv_df.iterrows():
                            save_employee_to_db(cur_comp, row)
                        st.sidebar.success("CSV data successfully imported!")
                        st.rerun()
                except Exception as e:
                    st.sidebar.error(f"Error reading CSV: {e}")
        st.sidebar.markdown("---")
    else:
        st.sidebar.info(f"👤 **Employee Mode**\nLogged in as **{logged_user_id}**.\nYou have access to view your personal performance metrics only.")

    if current_role == "Admin":
        st.sidebar.header("🔍 Filter Options")
        dept_options = ["All"] + list(df["department"].unique()) if not df.empty else ["All"]
        selected_dept = st.sidebar.selectbox("Filter by Department", dept_options, key=f"filter_dept_{cur_comp}")
        filtered_df = df[df["department"] == selected_dept] if selected_dept != "All" else df
    else:
        filtered_df = df[df["employee_id"] == logged_user_id]

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
    else:
        col1.metric("My Attendance Days", f"{int(filtered_df['days_present'].values[0]) if total_emps > 0 else 0} / {int(filtered_df['total_workdays'].values[0]) if total_emps > 0 else 0}")
        col2.metric("My Absenteeism Rate", avg_abs)
        col3.metric("My Productivity Score", avg_prod)
        col4.metric("Tasks Completed", total_tasks)

    st.markdown("---")

    if total_emps > 0:
        if current_role == "Admin":
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
            display_table = filtered_df.drop(columns=["photo"]) if "photo" in filtered_df.columns else filtered_df
            st.dataframe(display_table, use_container_width=True)

            st.markdown("---")
            st.subheader("🔍 Employee Profile & Performance Viewer")
            selected_emp_profile = st.selectbox("Select Employee ID to View Details", options=filtered_df["employee_id"].unique(), key=f"profile_sel_{cur_comp}")
            
            if selected_emp_profile:
                emp_data = filtered_df[filtered_df["employee_id"] == selected_emp_profile].iloc[0]
                p_col1, p_col2 = st.columns([1, 3])
                with p_col1:
                    if "photo" in emp_data and pd.notna(emp_data["photo"]) and emp_data["photo"] is not None:
                        try:
                            img = Image.open(emp_data["photo"])
                            st.image(img, caption=f"{emp_data['employee_id']}", width=150)
                        except:
                            st.info("Photo unavailable.")
                    else:
                        st.info("No photo uploaded.")
                with p_col2:
                    st.write(f"**Employee ID:** {emp_data['employee_id']}")
                    st.write(f"**Department:** {emp_data['department']}")
                    st.write(f"**Days Present:** {emp_data['days_present']} / {emp_data['total_workdays']}")
                    st.write(f"**Days Late:** {emp_data['days_late']}")
                    st.write(f"**Tasks Completed:** {emp_data['tasks_completed']}")
                    st.write(f"**Avg Task Score:** {emp_data['avg_task_score']}")
                    st.write(f"**Absenteeism Rate:** {emp_data['absenteeism_rate']}%")
                    st.write(f"**Productivity Score:** {emp_data['productivity_score']}")
        else:
            st.subheader("👤 My Performance Profile")
            emp_data = filtered_df.iloc[0]
            p_col1, p_col2 = st.columns([1, 3])
            with p_col1:
                if "photo" in emp_data and pd.notna(emp_data["photo"]) and emp_data["photo"] is not None:
                    try:
                        img = Image.open(emp_data["photo"])
                        st.image(img, caption=f"{emp_data['employee_id']}", width=160)
                    except:
                        st.info("Photo unavailable.")
                else:
                    st.info("No photo uploaded.")
            with p_col2:
                st.write(f"**Employee ID:** {emp_data['employee_id']}")
                st.write(f"**Department:** {emp_data['department']}")
                st.write(f"**Days Present:** {emp_data['days_present']} / {emp_data['total_workdays']}")
                st.write(f"**Days Late:** {emp_data['days_late']}")
                st.write(f"**Tasks Completed:** {emp_data['tasks_completed']}")
                st.write(f"**Avg Task Score:** {emp_data['avg_task_score']}")
                st.write(f"**Absenteeism Rate:** {emp_data['absenteeism_rate']}%")
                st.write(f"**Productivity Score:** {emp_data['productivity_score']}")
    else:
        if current_role == "Admin":
            st.info("No employee records found.")
        else:
            st.warning("Your employee record has not been configured in the database yet. Please contact your company Admin.")


# ==========================================
# TAB 2: DAILY ATTENDANCE MANAGER
# ==========================================
with tab2:
    if current_role == "Admin":
        st.header("📅 Daily Attendance Logs (Admin Management)")
        st.markdown("Log daily check-ins (Present, Absent, Late) for company staff.")
        if not df.empty:
            with st.form(f"daily_attendance_form_{cur_comp}"):
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    log_date = st.date_input("Attendance Date", value=date.today())
                with col_b:
                    log_emp_id = st.selectbox("Select Employee ID", options=df["employee_id"].unique(), key=f"log_emp_{cur_comp}")
                with col_c:
                    log_status = st.selectbox("Status", options=["Present", "Absent", "Late", "Half-Day"], key=f"log_status_{cur_comp}")
                
                log_remarks = st.text_input("Remarks / Notes (Optional)", placeholder="e.g., Sick leave, on time", key=f"log_remarks_{cur_comp}")
                
                submit_attendance = st.form_submit_button("Save Daily Attendance")
                
                if submit_attendance:
                    new_log_row = {
                        "Date": log_date,
                        "Employee ID": log_emp_id,
                        "Status": log_status,
                        "Remarks": log_remarks if log_remarks else "-"
                    }
                    save_daily_log_to_db(cur_comp, new_log_row)
                    st.success("Attendance successfully recorded and saved to database!")
                    st.rerun()
        else:
            st.warning("Please add employees first before logging attendance.")
        st.markdown("---")
        st.subheader("📋 Company Attendance History Log")
        display_logs = daily_log
    else:
        st.header("📅 My Attendance History")
        st.markdown("Viewing your personal attendance logs recorded by management.")
        display_logs = daily_log[daily_log["Employee ID"] == logged_user_id] if not daily_log.empty else daily_log

    if not display_logs.empty:
        if current_role == "Admin":
            search_emp = st.text_input("Search by Employee ID in Log", "", key=f"search_log_{cur_comp}")
            if search_emp:
                display_logs = display_logs[display_logs["Employee ID"].str.contains(search_emp, case=False)]
        st.dataframe(display_logs, use_container_width=True)
    else:
        st.info("No attendance logs recorded yet.")