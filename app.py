import streamlit as st
from google import genai
from PIL import Image
import sqlite3
import random
import json
import os

# Page configuration
st.set_page_config(
    page_title="GVHSS KUNIYA - Digital Learning Portal",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- MODERN SLEEK CSS DESIGN -----------------
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    * {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    .stApp {
        background-color: #0B0F19;
        background-image: 
            radial-gradient(at 0% 0%, rgba(37, 99, 235, 0.18) 0px, transparent 50%),
            radial-gradient(at 100% 100%, rgba(14, 165, 233, 0.15) 0px, transparent 50%);
        color: #F8FAFC;
    }

    /* Top Brand Header */
    .portal-header {
        background: rgba(17, 24, 39, 0.85);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 24px 32px;
        border-radius: 20px;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 20px 30px -10px rgba(0, 0, 0, 0.5);
    }
    .portal-title {
        font-size: 2rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        background: linear-gradient(135deg, #38BDF8 0%, #818CF8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .portal-sub {
        color: #94A3B8;
        font-size: 0.95rem;
        font-weight: 500;
        margin-top: 4px;
    }

    /* Broadcast Pill */
    .broadcast-box {
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.25);
        border-left: 4px solid #F59E0B;
        color: #FDE68A;
        padding: 14px 20px;
        border-radius: 12px;
        font-size: 0.95rem;
        margin-bottom: 24px;
        backdrop-filter: blur(8px);
    }

    /* KBC Game Arena */
    .kbc-container {
        background: radial-gradient(circle at center, #1E1B4B 0%, #090A15 100%);
        border: 2px solid #EAB308;
        border-radius: 24px;
        padding: 40px 30px;
        text-align: center;
        box-shadow: 0 0 40px rgba(234, 179, 8, 0.25);
        margin-bottom: 25px;
    }
    .kbc-badge {
        display: inline-block;
        background: linear-gradient(90deg, #CA8A04, #FACC15);
        color: #000;
        font-weight: 800;
        font-size: 0.8rem;
        padding: 6px 20px;
        border-radius: 9999px;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 18px;
    }
    .kbc-question {
        font-size: 1.45rem;
        color: #FFFFFF;
        font-weight: 700;
        line-height: 1.6;
        margin: 10px auto 20px auto;
        max-width: 850px;
    }

    /* Auth Container */
    .login-wrapper {
        background: rgba(17, 24, 39, 0.85);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 45px 35px;
        border-radius: 24px;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.6);
        max-width: 440px;
        margin: 40px auto;
        text-align: center;
    }

    /* Inputs and Buttons */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, select {
        background: rgba(15, 23, 42, 0.8) !important;
        color: #F8FAFC !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 12px !important;
    }
    .stButton>button {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        color: #FFFFFF !important;
        font-weight: 600 !important;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.15);
        padding: 10px 24px;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(37, 99, 235, 0.4);
    }
    </style>
""", unsafe_allow_html=True)

# ----------------- KERALA SYLLABUS DATA -----------------
KERALA_CLASSES = [
    "Class 8", "Class 9", "Class 10 (SSLC)",
    "Plus One (+1 Science)", "Plus One (+1 Commerce)", "Plus One (+1 Humanities)",
    "Plus Two (+2 Science)", "Plus Two (+2 Commerce)", "Plus Two (+2 Humanities)"
]

def get_subjects(cls_name):
    if cls_name in ["Class 8", "Class 9", "Class 10 (SSLC)"]:
        return ["Mathematics", "Physics", "Chemistry", "Biology", "Social Science I", "Social Science II", "English"]
    elif "Science" in cls_name:
        return ["Physics", "Chemistry", "Mathematics", "Biology", "Computer Science", "English"]
    elif "Commerce" in cls_name:
        return ["Accountancy", "Business Studies", "Economics", "English"]
    return ["History", "Economics", "Political Science", "Sociology", "English"]

# ----------------- DATABASE MANAGEMENT -----------------
DB_FILE = "kuniya_portal.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            student_class TEXT,
            medium TEXT DEFAULT 'English Medium'
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notice_text TEXT NOT NULL,
            posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS kbc_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_class TEXT NOT NULL,
            subject TEXT NOT NULL,
            question TEXT NOT NULL,
            opt_a TEXT NOT NULL,
            opt_b TEXT NOT NULL,
            opt_c TEXT NOT NULL,
            opt_d TEXT NOT NULL,
            correct_idx INTEGER NOT NULL,
            explanation TEXT NOT NULL
        )
    ''')
    
    # Pre-seed Admin
    c.execute('SELECT * FROM users WHERE username = ?', ('admin',))
    if not c.fetchone():
        c.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)', 
                  ('admin', 'admin@kuniya', 'Principal / Administrator', 'admin', 'None', 'English Medium'))
        c.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)', 
                  ('teacher1', 'teacher123', 'Suresh Sir (Dept. of Maths)', 'teacher', 'None', 'English Medium'))
        c.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)', 
                  ('student1', 'student123', 'Arjun K', 'student', 'Class 10 (SSLC)', 'English Medium'))
        c.execute('INSERT INTO notices (notice_text) VALUES (?)', 
                  ('Welcome to the official digital portal of GVHSS Kuniya, Kasaragod. Terminal examinations start next week.',))
        
    # Pre-seed sample questions so KBC is NEVER empty!
    c.execute('SELECT COUNT(*) FROM kbc_questions')
    if c.fetchone()[0] == 0:
        sample_questions = [
            ("Class 10 (SSLC)", "Mathematics", "What is the common difference of the Arithmetic Progression: 4, 7, 10, 13...?", "2", "3", "4", "5", 1, "Common difference d = 7 - 4 = 3."),
            ("Class 10 (SSLC)", "Physics", "Which law states that induced electromotive force is directly proportional to the rate of change of magnetic flux?", "Ohm's Law", "Faraday's Law", "Coulomb's Law", "Joule's Law", 1, "Faraday's Law of Electromagnetic Induction governs this principle."),
            ("Class 10 (SSLC)", "Chemistry", "What is the pH of pure neutral water at 25°C?", "0", "7", "14", "1", 1, "Pure water has a neutral pH of 7."),
            ("Class 10 (SSLC)", "Biology", "Which part of the human brain controls involuntary actions like heartbeat and breathing?", "Cerebrum", "Cerebellum", "Medulla Oblongata", "Thalamus", 2, "Medulla oblongata coordinates vital autonomous physiological activities."),
            ("Plus Two (+2 Science)", "Physics", "What is the SI unit of electric capacitance?", "Henry", "Farad", "Weber", "Tesla", 1, "Capacitance is measured in Farads (F)."),
            ("Plus Two (+2 Science)", "Chemistry", "Which process is used for the commercial synthesis of ammonia?", "Ostwald Process", "Haber Process", "Contact Process", "Bessemer Process", 1, "The Haber-Bosch process synthesizes ammonia from atmospheric nitrogen and hydrogen.")
        ]
        for q in sample_questions:
            c.execute('''
                INSERT INTO kbc_questions (target_class, subject, question, opt_a, opt_b, opt_c, opt_d, correct_idx, explanation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', q)
            
    conn.commit()
    conn.close()

init_db()

def get_user(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT username, password, name, role, student_class, medium FROM users WHERE username = ?', (username,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"username": row[0], "password": row[1], "name": row[2], "role": row[3], "class": row[4], "medium": row[5]}
    return None

def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT username, name, role, student_class FROM users ORDER BY role, name')
    rows = c.fetchall()
    conn.close()
    return rows

def add_user(username, password, name, role, student_class, medium="English Medium"):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)', (username, password, name, role, student_class, medium))
        conn.commit()
        conn.close()
        return True, f"User '{username}' ({role}) created successfully!"
    except sqlite3.IntegrityError:
        return False, "This Username already exists. Please choose a different one."

def delete_user(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE username = ?', (username,))
    conn.commit()
    conn.close()

def set_latest_notice(text):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT INTO notices (notice_text) VALUES (?)', (text,))
    conn.commit()
    conn.close()

def get_latest_notice():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT notice_text FROM notices ORDER BY id DESC LIMIT 1')
    row = c.fetchone()
    conn.close()
    return row[0] if row else "No new official notices at this moment."

# ----------------- KBC ENGINE -----------------
def fetch_kbc_question(target_class, subject):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Try exact match first
    c.execute('''
        SELECT id, question, opt_a, opt_b, opt_c, opt_d, correct_idx, explanation 
        FROM kbc_questions 
        WHERE target_class = ? AND subject = ?
        ORDER BY RANDOM() LIMIT 1
    ''', (target_class, subject))
    row = c.fetchone()
    
    # Fallback to any question in database if specific subject is empty
    if not row:
        c.execute('''
            SELECT id, question, opt_a, opt_b, opt_c, opt_d, correct_idx, explanation 
            FROM kbc_questions 
            ORDER BY RANDOM() LIMIT 1
        ''')
        row = c.fetchone()
        
    conn.close()
    if row:
        return {
            "id": row[0], "question": row[1],
            "options": [row[2], row[3], row[4], row[5]],
            "correct_idx": row[6], "explanation": row[7]
        }
    return None

def count_kbc_questions(target_class, subject):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM kbc_questions WHERE target_class = ? AND subject = ?', (target_class, subject))
    cnt = c.fetchone()[0]
    conn.close()
    return cnt

def insert_batch_kbc_questions(target_class, subject, q_list):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for q in q_list:
        try:
            c.execute('''
                INSERT INTO kbc_questions (target_class, subject, question, opt_a, opt_b, opt_c, opt_d, correct_idx, explanation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (target_class, subject, q["q"], q["options"][0], q["options"][1], q["options"][2], q["options"][3], q["answer_idx"], q["exp"]))
        except Exception:
            continue
    conn.commit()
    conn.close()

def generate_ai_kbc_batch(client, target_class, subject, count=10):
    prompt = f"""
    You are an expert Kerala SCERT textbook curriculum exam specialist for GVHSS KUNIYA.
    Generate {count} multiple-choice quiz questions in KBC (Kaun Banega Crorepati) game format.
    Target Class: {target_class}
    Subject: {subject}
    Language: Clean English

    Rules:
    1. Base strictly on Kerala State SCERT textbooks.
    2. Provide 4 distinct options with exactly one correct answer (index 0, 1, 2, or 3).
    3. Return ONLY a valid JSON array of objects. Do not include markdown code block quotes.

    JSON Format:
    [
      {{
        "q": "Question text here?",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "answer_idx": 0,
        "exp": "Detailed explanatory note about the answer"
      }}
    ]
    """
    try:
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        return json.loads(res.text)
    except Exception:
        return []

# ----------------- SESSION STATE -----------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["username"] = None
    st.session_state["role"] = None
    st.session_state["display_name"] = None
    st.session_state["student_class"] = None

if "kbc_q" not in st.session_state:
    st.session_state["kbc_q"] = None
if "kbc_score" not in st.session_state:
    st.session_state["kbc_score"] = 0
if "kbc_streak" not in st.session_state:
    st.session_state["kbc_streak"] = 0
if "kbc_answered" not in st.session_state:
    st.session_state["kbc_answered"] = False
if "kbc_fifty_used" not in st.session_state:
    st.session_state["kbc_fifty_used"] = False
if "kbc_disabled_options" not in st.session_state:
    st.session_state["kbc_disabled_options"] = []
if "kbc_selected_idx" not in st.session_state:
    st.session_state["kbc_selected_idx"] = None

# ----------------- AUTHENTICATION PAGE -----------------
def login_screen():
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown("""
            <div class="login-wrapper">
                <span style="background: rgba(56, 189, 248, 0.12); color: #38BDF8; padding: 6px 18px; border-radius: 9999px; font-weight: 700; font-size: 0.8rem; border: 1px solid rgba(56, 189, 248, 0.25);">
                    GOVERNMENT OF KERALA • GENERAL EDUCATION
                </span>
                <h1 style="margin: 18px 0 2px 0; color: #FFFFFF; font-size: 2.1rem; font-weight: 800; letter-spacing: -0.5px;">GVHSS KUNIYA</h1>
                <p style="color: #94A3B8; font-size: 0.95rem; margin-bottom: 25px;">
                    Govt Vocational Higher Secondary School, Kuniya<br>
                    <span style="color: #64748B; font-size: 0.85rem;">Integrated Smart Campus Portal</span>
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            uid = st.text_input("User ID", placeholder="e.g. admin or student1").strip().lower()
            pwd = st.text_input("Password", type="password", placeholder="••••••••").strip()
            submit = st.form_submit_button("Sign In to Portal", use_container_width=True)
            if submit:
                user = get_user(uid)
                if user and user["password"] == pwd:
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = user["username"]
                    st.session_state["role"] = user["role"]
                    st.session_state["display_name"] = user["name"]
                    st.session_state["student_class"] = user["class"]
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please verify your username and password.")

if not st.session_state["authenticated"]:
    login_screen()
    st.stop()

# ----------------- MAIN APP DASHBOARD -----------------

# Header
st.markdown(f"""
    <div class="portal-header">
        <div>
            <h1 class="portal-title">GVHSS KUNIYA</h1>
            <div class="portal-sub">Govt Vocational Higher Secondary School Kuniya • Kasaragod, Kerala</div>
        </div>
        <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255,255,255,0.1); padding: 10px 20px; border-radius: 12px; text-align: right;">
            <div style="font-size: 0.8rem; color: #94A3B8; text-transform: uppercase; font-weight: 600;">Active Account</div>
            <strong style="color: #38BDF8; font-size: 1.05rem;">{st.session_state['display_name']}</strong>
            <div style="font-size: 0.8rem; color: #F59E0B; font-weight: 600;">{st.session_state['role'].upper()}</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# School Notice
notice = get_latest_notice()
st.markdown(f'<div class="broadcast-box">📢 <strong>School Announcement:</strong> {notice}</div>', unsafe_allow_html=True)

# Sidebar
st.sidebar.markdown("### Profile Overview")
st.sidebar.info(f"**User:** {st.session_state['display_name']}\n\n**Role:** {st.session_state['role'].capitalize()}")

if st.sidebar.button("Logout", use_container_width=True):
    st.session_state["authenticated"] = False
    st.session_state["username"] = None
    st.rerun()

# Class & Subject Selection
if st.session_state["role"] in ["admin", "teacher"]:
    selected_class = st.sidebar.selectbox("Select Academic Class", KERALA_CLASSES)
else:
    selected_class = st.session_state.get("student_class", "Class 10 (SSLC)")
    st.sidebar.markdown(f"**Enrolled Class:** `{selected_class}`")

available_subjects = get_subjects(selected_class)
subject = st.sidebar.selectbox("Select Subject", available_subjects)

# Gemini AI Client
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

# ----------------- ADMIN CONTROLS -----------------
if st.session_state["role"] == "admin":
    with st.expander("⚙️ Administrator Management Console", expanded=False):
        adm_tab1, adm_tab2, adm_tab3 = st.tabs(["➕ Add New User / Admin", "👥 Registered Accounts", "📢 Update Notice"])
        
        # 1. Add User (Admin / Teacher / Student)
        with adm_tab1:
            st.markdown("##### Create a New User or Administrator")
            with st.form("add_user_form"):
                au_id = st.text_input("User ID (Login ID)", placeholder="e.g. principal_kuniya").strip().lower()
                au_pwd = st.text_input("Password", type="password", placeholder="Enter secure password").strip()
                au_name = st.text_input("Full Name & Designation", placeholder="e.g. Dr. K. Radhakrishnan").strip()
                # 'admin' role added here as requested!
                au_role = st.selectbox("Role Permission", ["admin", "teacher", "student"], help="Select 'admin' to grant full administrative privileges")
                au_cls = st.selectbox("Associated Class (For Students only)", ["None"] + KERALA_CLASSES)
                
                if st.form_submit_button("Create Account", use_container_width=True):
                    if au_id and au_pwd and au_name:
                        ok, msg = add_user(au_id, au_pwd, au_name, au_role, au_cls)
                        st.success(msg) if ok else st.error(msg)
                    else:
                        st.warning("Please fill in all required fields.")
        
        # 2. View / Delete Users
        with adm_tab2:
            st.markdown("##### Manage Existing System Accounts")
            for u in get_all_users():
                c1, c2, c3, c4 = st.columns([2, 3, 2, 1])
                c1.write(f"**{u[0]}**")
                c2.write(f"{u[1]}")
                badge_color = "red" if u[2] == "admin" else "blue" if u[2] == "teacher" else "green"
                c3.markdown(f":{badge_color}[{u[2].upper()}]")
                if u[0] != "admin" and c4.button("Remove", key=f"del_{u[0]}"):
                    delete_user(u[0])
                    st.rerun()
                    
        # 3. Publish Notice
        with adm_tab3:
            st.markdown("##### Publish Digital Noticeboard Announcement")
            unote = st.text_area("Announcement Text:", value=notice, height=100)
            if st.button("Publish Broadcast to All"):
                set_latest_notice(unote)
                st.success("Official notice updated successfully!")
                st.rerun()

# ----------------- MAIN NAVIGATION TABS -----------------
tab_kbc, tab_live, tab_doubt, tab_img = st.tabs([
    "🏆 KBC Challenge Quiz", 
    "🎥 Live Classroom", 
    "🤖 SCERT AI Study Mentor", 
    "📸 Question Lens"
])

# ----------------- TAB 1: KBC CHALLENGE QUIZ -----------------
with tab_kbc:
    q_count = count_kbc_questions(selected_class, subject)
    
    col_sc1, col_sc2, col_sc3 = st.columns(3)
    with col_sc1:
        st.metric("🏆 Total Score", f"{st.session_state['kbc_score']:,} Pts")
    with col_sc2:
        st.metric("🔥 Streak", f"{st.session_state['kbc_streak']} in a row")
    with col_sc3:
        st.metric("📚 Subject Question Pool", f"{q_count} Questions")

    # Load initial question if empty
    if st.session_state["kbc_q"] is None:
        q_data = fetch_kbc_question(selected_class, subject)
        if q_data:
            st.session_state["kbc_q"] = q_data
            st.session_state["kbc_answered"] = False
            st.session_state["kbc_fifty_used"] = False
            st.session_state["kbc_disabled_options"] = []
            st.session_state["kbc_selected_idx"] = None

    # AI Generator button if pool is small
    if client:
        with st.expander("⚡ Expand Question Bank with AI", expanded=False):
            if st.button("Generate 10 New SCERT Questions via AI"):
                with st.spinner("Compiling curriculum questions..."):
                    batch = generate_ai_kbc_batch(client, selected_class, subject, count=10)
                    if batch:
                        insert_batch_kbc_questions(selected_class, subject, batch)
                        st.success(f"Generated and added {len(batch)} questions!")
                        st.rerun()

    curr = st.session_state["kbc_q"]
    if curr:
        st.markdown(f"""
            <div class="kbc-container">
                <span class="kbc-badge">💰 KBC HOT SEAT • {selected_class} • {subject}</span>
                <div class="kbc-question">{curr['question']}</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Lifeline Section
        c_life, _ = st.columns([1, 3])
        with c_life:
            if not st.session_state["kbc_fifty_used"] and not st.session_state["kbc_answered"]:
                if st.button("⚖️ 50:50 Lifeline"):
                    correct = curr["correct_idx"]
                    wrong_indices = [i for i in range(4) if i != correct]
                    st.session_state["kbc_disabled_options"] = random.sample(wrong_indices, 2)
                    st.session_state["kbc_fifty_used"] = True
                    st.rerun()

        # Options Grid
        labels = ["A", "B", "C", "D"]
        c1, c2 = st.columns(2)
        
        for idx in range(4):
            col = c1 if idx % 2 == 0 else c2
            opt_text = curr["options"][idx]
            is_disabled = idx in st.session_state["kbc_disabled_options"]
            btn_label = f"{labels[idx]}:  {opt_text}" if not is_disabled else f"{labels[idx]}:  [ ELIMINATED ]"
            
            if col.button(btn_label, key=f"kbc_opt_{idx}", disabled=is_disabled or st.session_state["kbc_answered"], use_container_width=True):
                st.session_state["kbc_answered"] = True
                st.session_state["kbc_selected_idx"] = idx
                if idx == curr["correct_idx"]:
                    st.session_state["kbc_score"] += 1000
                    st.session_state["kbc_streak"] += 1
                else:
                    st.session_state["kbc_streak"] = 0
                st.rerun()

        # Feedback block after answering
        if st.session_state["kbc_answered"]:
            sel = st.session_state["kbc_selected_idx"]
            corr = curr["correct_idx"]
            if sel == corr:
                st.balloons()
                st.success(f"🎉 **Correct Answer! (+1,000 Points)**\n\n💡 **Explanation:** {curr['explanation']}")
            else:
                correct_label = labels[corr]
                correct_ans = curr["options"][corr]
                st.error(f"❌ **Incorrect!** The correct answer was **[{correct_label}] {correct_ans}**.\n\n💡 **Explanation:** {curr['explanation']}")
            
            if st.button("👉 Next Question", use_container_width=True):
                new_q = fetch_kbc_question(selected_class, subject)
                st.session_state["kbc_q"] = new_q
                st.session_state["kbc_answered"] = False
                st.session_state["kbc_fifty_used"] = False
                st.session_state["kbc_disabled_options"] = []
                st.session_state["kbc_selected_idx"] = None
                st.rerun()
    else:
        st.info("No questions currently available. Please click 'Generate New Questions' above or select another subject.")

# ----------------- TAB 2: LIVE CLASSROOM -----------------
with tab_live:
    ROOM_SALT = "GVHSS_Kuniya_HQ"
    sanitized_class = selected_class.replace(' ', '_').replace('(', '').replace(')', '').replace('+', 'Plus')
    sanitized_subj = subject.split(' ')[0]
    room_id = f"KUNIYA_{sanitized_class}_{sanitized_subj}_{ROOM_SALT}"
    
    st.info(f"🔴 **Live Classroom Stream:** {selected_class} • {subject}")
    display_user = f"{st.session_state['display_name']} ({st.session_state['role'].capitalize()})"
    jitsi_url = f"https://meet.jit.si/{room_id}#userInfo.displayName=\"{display_user}\""
    
    st.iframe(jitsi_url, height=620)

# ----------------- TAB 3: SCERT AI STUDY MENTOR -----------------
with tab_doubt:
    st.markdown("#### 🤖 24/7 Kerala SCERT Syllabus AI Tutor")
    st.caption(f"Currently configured for: **{selected_class} - {subject}**")
    user_q = st.text_area("Ask any question or concept doubt from your textbook:", placeholder="e.g. Explain Lenz's law with practical examples and formula.")
    if st.button("Solve Doubt"):
        if client and user_q.strip():
            with st.spinner("Teacher is formulating an explanation..."):
                prompt = f"""
                You are an expert Kerala SCERT textbook teacher at GVHSS KUNIYA school.
                Class: {selected_class}
                Subject: {subject}
                Provide a clear, pedagogical, step-by-step answer formatted in clean markdown for this student question:
                {user_q}
                """
                res = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
                st.markdown(res.text)
        elif not client:
            st.warning("Please configure your GEMINI_API_KEY environment variable to use AI tutoring.")

# ----------------- TAB 4: QUESTION LENS (PHOTO UPLOAD) -----------------
with tab_img:
    st.markdown("#### 📸 Snap & Solve Textbook Questions")
    up_img = st.file_uploader("Upload an image of the textbook page or question", type=["png", "jpg", "jpeg"])
    if up_img:
        img = Image.open(up_img)
        st.image(img, caption="Uploaded Problem Image", use_container_width=True)
        if st.button("Analyze & Solve Problem"):
            if client:
                with st.spinner("Analyzing question image..."):
                    res = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[f"Class: {selected_class}, Subject: {subject}. Read the question from this image and provide the step-by-step solution based on Kerala state syllabus standards.", img]
                    )
                    st.markdown(res.text)
            else:
                st.warning("Please configure GEMINI_API_KEY to use Photo Solver.")
