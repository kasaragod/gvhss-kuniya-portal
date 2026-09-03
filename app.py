import streamlit as st
from google import genai
from PIL import Image
import sqlite3
import random
import json
import os

st.set_page_config(
    page_title="GVHSS KUNIYA - Smart Learning Portal",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ----------------- MODERN LIGHT / RESPONSIVE UI -----------------
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Manjari:wght@400;700&display=swap');

    html, body, [class*="css"], * {
        font-family: 'Inter', 'Manjari', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    .stApp {
        background-color: #F8FAFC !important;
        color: #0F172A !important;
    }

    .main .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 1200px !important;
    }

    /* Header */
    .school-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 20px 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
    }
    .school-title {
        font-size: 1.6rem;
        font-weight: 800;
        color: #1E3A8A;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .school-sub {
        color: #64748B;
        font-size: 0.9rem;
        font-weight: 500;
        margin-top: 4px;
    }
    .user-badge {
        background: #EFF6FF;
        border: 1px solid #BFDBFE;
        padding: 8px 16px;
        border-radius: 12px;
        text-align: right;
    }

    /* Notice Card */
    .notice-card {
        background: #FFFBEB;
        border: 1px solid #FDE68A;
        border-left: 4px solid #F59E0B;
        padding: 14px 18px;
        border-radius: 10px;
        color: #92400E;
        font-size: 0.92rem;
        font-weight: 500;
        margin-bottom: 20px;
        line-height: 1.5;
    }

    /* Form Fields */
    input, textarea, select {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        border: 1.5px solid #CBD5E1 !important;
        border-radius: 8px !important;
        font-size: 0.95rem !important;
    }
    input:focus, textarea:focus {
        border-color: #2563EB !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15) !important;
    }

    /* KBC Hot Seat Card */
    .kbc-box {
        background: #0F172A;
        border: 2px solid #F59E0B;
        border-radius: 18px;
        padding: 28px 20px;
        text-align: center;
        color: #FFFFFF;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.25);
        margin-bottom: 22px;
    }
    .kbc-label {
        display: inline-block;
        background: #F59E0B;
        color: #000000;
        font-weight: 700;
        font-size: 0.78rem;
        padding: 4px 14px;
        border-radius: 9999px;
        text-transform: uppercase;
        margin-bottom: 12px;
    }
    .kbc-q-title {
        font-size: 1.35rem;
        font-weight: 700;
        color: #FFFFFF;
        line-height: 1.6;
        margin: 5px auto;
        max-width: 800px;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #E2E8F0;
        padding: 6px;
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 8px;
        color: #475569 !important;
        font-weight: 600;
        padding: 8px 18px;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        color: #1E3A8A !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    /* Buttons */
    .stButton>button {
        background: #2563EB;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        border-radius: 8px;
        border: none;
        padding: 8px 18px;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background: #1D4ED8;
    }

    /* Login Box */
    .auth-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 35px 28px;
        max-width: 420px;
        margin: 40px auto;
        box-shadow: 0 15px 30px -10px rgba(0, 0, 0, 0.08);
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------- KERALA SYLLABUS DATA -----------------
KERALA_CLASSES = [
    "Class 8", "Class 9", "Class 10 (SSLC)",
    "Plus One (+1 Science)", "Plus One (+1 Commerce)", "Plus One (+1 Humanities)",
    "Plus Two (+2 Science)", "Plus Two (+2 Commerce)", "Plus Two (+2 Humanities)"
]

def get_subjects(cls_name, medium):
    is_mal = "Malayalam" in medium
    if cls_name in ["Class 8", "Class 9", "Class 10 (SSLC)"]:
        return [
            "ഗണിതം (Mathematics)", "ഭൗതികശാസ്ത്രം (Physics)", "രസതന്ത്രം (Chemistry)",
            "ജീവശാസ്ത്രം (Biology)", "സാമൂഹ്യശാസ്ത്രം I", "സാമൂഹ്യശാസ്ത്രം II", "English", "മലയാളം"
        ] if is_mal else [
            "Mathematics", "Physics", "Chemistry", "Biology", "Social Science I", "Social Science II", "English", "Malayalam"
        ]
    elif "Science" in cls_name:
        return [
            "ഭൗതികശാസ്ത്രം (Physics)", "രസതന്ത്രം (Chemistry)", "ഗണിതം (Mathematics)",
            "ജീവശാസ്ത്രം (Biology)", "Computer Science", "English"
        ] if is_mal else [
            "Physics", "Chemistry", "Mathematics", "Biology", "Computer Science", "English"
        ]
    elif "Commerce" in cls_name:
        return [
            "അക്കൗണ്ടൻസി (Accountancy)", "Business Studies", "സാമ്പത്തികശാസ്ത്രം (Economics)", "English"
        ] if is_mal else [
            "Accountancy", "Business Studies", "Economics", "English"
        ]
    return [
        "ചരിത്രം (History)", "സാമ്പത്തികശാസ്ത്രം (Economics)", "Political Science", "Sociology", "English"
    ] if is_mal else [
        "History", "Economics", "Political Science", "Sociology", "English"
    ]

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
            medium TEXT DEFAULT 'Malayalam Medium'
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
            medium TEXT NOT NULL,
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
                  ('admin', 'admin@kuniya', 'Principal / Administrator', 'admin', 'None', 'Malayalam Medium'))
        c.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)', 
                  ('teacher1', 'teacher123', 'Suresh Sir (Dept. of Maths)', 'teacher', 'None', 'Malayalam Medium'))
        c.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)', 
                  ('student1', 'student123', 'Arjun K', 'student', 'Class 10 (SSLC)', 'Malayalam Medium'))
        c.execute('INSERT INTO notices (notice_text) VALUES (?)', 
                  ('Welcome to the official digital portal of GVHSS KUNIYA. Academic sessions are active.',))

    # Pre-seed Questions for both Malayalam and English medium
    c.execute('SELECT COUNT(*) FROM kbc_questions')
    if c.fetchone()[0] == 0:
        sample_q = [
            # Malayalam Medium Questions
            ("Class 10 (SSLC)", "ഗണിതം (Mathematics)", "Malayalam Medium", "4, 7, 10, 13... എന്ന സമാന്തരശ്രേണിയുടെ പൊതുവ്യത്യാസം എത്രയാണ്?", "2", "3", "4", "5", 1, "പൊതുവ്യത്യാസം d = 7 - 4 = 3 ആണ്."),
            ("Class 10 (SSLC)", "ഭൗതികശാസ്ത്രം (Physics)", "Malayalam Medium", "ആകാശത്തിന് നീലനിറം കാണപ്പെടാൻ കാരണമായ പ്രതിഭാസം ഏത്?", "പ്രതിപതനം", "പൂർണ്ണാന്തര പ്രതിപതനം", "പ്രകാശ വിസരണം", "പ്രകീർണ്ണനം", 2, "പ്രകാശത്തിന്റെ വിസരണം (Scattering) കാരണമാണ് ആകാശം നീലനിറമായി കാണപ്പെടുന്നത്."),
            ("Class 10 (SSLC)", "രസതന്ത്രം (Chemistry)", "Malayalam Medium", "ബേക്കിംഗ് സോഡയുടെ രാസനാമം എന്താണ്?", "സോഡിയം ക്ലോറൈഡ്", "സോഡിയം ഹൈഡ്രജൻ കാർബണേറ്റ്", "കാൽസ്യം ഹൈഡ്രോക്സൈഡ്", "സോഡിയം ഹൈഡ്രോക്സൈഡ്", 1, "സോഡിയം ഹൈഡ്രജൻ കാർബണേറ്റ് (NaHCO3) ആണ് ബേക്കിംഗ് സോഡ."),
            ("Class 10 (SSLC)", "ജീവശാസ്ത്രം (Biology)", "Malayalam Medium", "കോശത്തിന്റെ ഊർജ്ജ നിലയം എന്നറിയപ്പെടുന്നത് ഏത് ഭാഗമാണ്?", "റൈബോസോം", "മൈറ്റോകോൺഡ്രിയ", "ന്യൂക്ലിയസ്", "ഗോൾഗി ബോഡി", 1, "കോശത്തിന് ആവശ്യമായ ATP ഊർജ്ജം ഉൽപ്പാദിപ്പിക്കുന്നത് മൈറ്റോകോൺഡ്രിയ ആണ്."),
            
            # English Medium Questions
            ("Class 10 (SSLC)", "Mathematics", "English Medium", "What is the common difference of the Arithmetic Progression: 4, 7, 10, 13...?", "2", "3", "4", "5", 1, "Common difference d = 7 - 4 = 3."),
            ("Class 10 (SSLC)", "Physics", "English Medium", "Which optical phenomenon causes the blue appearance of the sky?", "Reflection", "Total Internal Reflection", "Scattering of Light", "Dispersion", 2, "Rayleigh scattering of sunlight causes the blue appearance of the sky."),
            ("Class 10 (SSLC)", "Chemistry", "English Medium", "What is the chemical formula of baking soda?", "NaCl", "NaHCO3", "NaOH", "Ca(OH)2", 1, "Sodium Hydrogen Carbonate (NaHCO3) is baking soda.")
        ]
        for q in sample_q:
            c.execute('''
                INSERT INTO kbc_questions (target_class, subject, medium, question, opt_a, opt_b, opt_c, opt_d, correct_idx, explanation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    c.execute('SELECT username, name, role, student_class, medium FROM users ORDER BY role, name')
    rows = c.fetchall()
    conn.close()
    return rows

def add_user(username, password, name, role, student_class, medium):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)', (username, password, name, role, student_class, medium))
        conn.commit()
        conn.close()
        return True, f"User '{username}' created successfully!"
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
    return row[0] if row else "Welcome to GVHSS KUNIYA Digital Campus."

# ----------------- KBC ENGINE -----------------
def fetch_kbc_question(target_class, subject, medium):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        SELECT id, question, opt_a, opt_b, opt_c, opt_d, correct_idx, explanation 
        FROM kbc_questions 
        WHERE target_class = ? AND subject = ? AND medium = ?
        ORDER BY RANDOM() LIMIT 1
    ''', (target_class, subject, medium))
    row = c.fetchone()
    if not row:
        # Fallback to any question in that medium
        c.execute('''
            SELECT id, question, opt_a, opt_b, opt_c, opt_d, correct_idx, explanation 
            FROM kbc_questions 
            WHERE medium = ? 
            ORDER BY RANDOM() LIMIT 1
        ''', (medium,))
        row = c.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0], "question": row[1],
            "options": [row[2], row[3], row[4], row[5]],
            "correct_idx": row[6], "explanation": row[7]
        }
    return None

def count_kbc_questions(target_class, subject, medium):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM kbc_questions WHERE target_class = ? AND subject = ? AND medium = ?', (target_class, subject, medium))
    cnt = c.fetchone()[0]
    conn.close()
    return cnt

def insert_batch_kbc_questions(target_class, subject, medium, q_list):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for q in q_list:
        try:
            c.execute('''
                INSERT INTO kbc_questions (target_class, subject, medium, question, opt_a, opt_b, opt_c, opt_d, correct_idx, explanation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (target_class, subject, medium, q["q"], q["options"][0], q["options"][1], q["options"][2], q["options"][3], q["answer_idx"], q["exp"]))
        except Exception:
            continue
    conn.commit()
    conn.close()

def generate_ai_kbc_batch(client, target_class, subject, medium, count=10):
    lang_inst = "Generate the questions, options, and explanations in clear and authentic Malayalam." if "Malayalam" in medium else "Generate the questions, options, and explanations in English."
    prompt = f"""
    Create {count} multiple-choice quiz questions based on the Kerala SCERT textbook curriculum for GVHSS KUNIYA.
    Class: {target_class}
    Subject: {subject}
    Medium: {medium}
    
    Instruction: {lang_inst}
    
    Provide 4 options with one correct answer index (0, 1, 2, or 3).
    Return ONLY a JSON array with this schema:
    [
      {{
        "q": "Question text here?",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "answer_idx": 0,
        "exp": "Detailed explanation note"
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
    st.session_state["medium"] = "Malayalam Medium"

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

# ----------------- AUTH SCREEN -----------------
def login_screen():
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown("""
            <div class="auth-card">
                <h2 style="color: #1E3A8A; font-weight: 800; margin-bottom: 4px;">GVHSS KUNIYA</h2>
                <div style="color: #64748B; font-size: 0.9rem; margin-bottom: 24px;">Digital Campus Learning Portal</div>
            </div>
        """, unsafe_allow_html=True)
        with st.form("login_form"):
            uid = st.text_input("User ID", placeholder="e.g. admin or student1").strip().lower()
            pwd = st.text_input("Password", type="password", placeholder="••••••••").strip()
            submit = st.form_submit_button("Sign In", use_container_width=True)
            if submit:
                user = get_user(uid)
                if user and user["password"] == pwd:
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = user["username"]
                    st.session_state["role"] = user["role"]
                    st.session_state["display_name"] = user["name"]
                    st.session_state["student_class"] = user["class"]
                    st.session_state["medium"] = user["medium"]
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

if not st.session_state["authenticated"]:
    login_screen()
    st.stop()

# ----------------- MAIN DASHBOARD -----------------

# Header Card
st.markdown(f"""
    <div class="school-card">
        <div>
            <h1 class="school-title">GVHSS KUNIYA</h1>
            <div class="school-sub">Govt Vocational Higher Secondary School, Kuniya • Kasaragod</div>
        </div>
        <div class="user-badge">
            <div style="font-size: 0.75rem; color: #64748B; font-weight: 600;">ACTIVE SESSION</div>
            <div style="color: #1E3A8A; font-weight: 700; font-size: 0.95rem;">{st.session_state['display_name']} ({st.session_state['role'].upper()})</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# School Notice
notice = get_latest_notice()
st.markdown(f'<div class="notice-card">📢 <strong>Notice:</strong> {notice}</div>', unsafe_allow_html=True)

# Sidebar
st.sidebar.markdown("### Profile")
st.sidebar.write(f"**Name:** {st.session_state['display_name']}")
st.sidebar.write(f"**Role:** {st.session_state['role'].capitalize()}")

# Medium Switcher
medium_idx = 0 if st.session_state["medium"] == "Malayalam Medium" else 1
selected_medium = st.sidebar.radio("Instruction Medium", ["Malayalam Medium", "English Medium"], index=medium_idx)
if selected_medium != st.session_state["medium"]:
    st.session_state["medium"] = selected_medium
    st.session_state["kbc_q"] = None
    st.rerun()

if st.sidebar.button("Logout", use_container_width=True):
    st.session_state["authenticated"] = False
    st.session_state["username"] = None
    st.rerun()

# Class & Subject Chooser
col_sel1, col_sel2 = st.columns(2)
with col_sel1:
    if st.session_state["role"] in ["admin", "teacher"]:
        selected_class = st.selectbox("Academic Class", KERALA_CLASSES)
    else:
        selected_class = st.session_state.get("student_class", "Class 10 (SSLC)")
        st.info(f"Class: **{selected_class}**")
with col_sel2:
    available_subjects = get_subjects(selected_class, selected_medium)
    subject = st.selectbox("Subject", available_subjects)

# AI Setup
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

# ----------------- ADMIN CONSOLE -----------------
if st.session_state["role"] == "admin":
    with st.expander("⚙️ Admin Management Console", expanded=False):
        adm1, adm2, adm3 = st.tabs(["➕ Add User / Admin", "👥 User Directory", "📢 Update Notice"])
        with adm1:
            with st.form("add_user_form"):
                c_u1, c_u2 = st.columns(2)
                with c_u1:
                    new_uid = st.text_input("User ID", placeholder="e.g. teacher_maths").strip().lower()
                    new_pwd = st.text_input("Password", type="password", placeholder="Password").strip()
                with c_u2:
                    new_name = st.text_input("Full Name", placeholder="e.g. Ramesh Kumar").strip()
                    new_role = st.selectbox("Role", ["student", "teacher", "admin"])
                
                c_u3, c_u4 = st.columns(2)
                with c_u3:
                    new_cls = st.selectbox("Class (For Students)", ["None"] + KERALA_CLASSES)
                with c_u4:
                    new_med = st.selectbox("Medium", ["Malayalam Medium", "English Medium"])
                
                if st.form_submit_button("Save Account"):
                    if new_uid and new_pwd and new_name:
                        ok, msg = add_user(new_uid, new_pwd, new_name, new_role, new_cls, new_med)
                        st.success(msg) if ok else st.error(msg)
                    else:
                        st.warning("Please fill in all fields.")
        with adm2:
            all_u = get_all_users()
            for u in all_u:
                c1, c2, c3, c4, c5 = st.columns([2, 3, 2, 2, 1])
                c1.write(f"**{u[0]}**")
                c2.write(f"{u[1]}")
                c3.write(f"`{u[2].upper()}`")
                c4.write(f"{u[4] if len(u) > 4 else '-'}")
                if u[0] != "admin" and c5.button("Delete", key=f"del_{u[0]}"):
                    delete_user(u[0])
                    st.rerun()
        with adm3:
            unote = st.text_area("Notice Text:", value=notice)
            if st.button("Publish Notice"):
                set_latest_notice(unote)
                st.success("Notice updated!")
                st.rerun()

# ----------------- TABS (MOBILE & DESKTOP FRIENDLY) -----------------
tab_kbc, tab_live, tab_doubt, tab_img = st.tabs([
    "🏆 KBC Challenge", 
    "🎥 Live Classroom", 
    "🤖 AI Study Mentor", 
    "📸 Question Lens"
])

# 1. KBC QUIZ
with tab_kbc:
    q_count = count_kbc_questions(selected_class, subject, selected_medium)
    
    col_sc1, col_sc2, col_sc3 = st.columns(3)
    with col_sc1:
        st.metric("🏆 Score", f"{st.session_state['kbc_score']:,} Pts")
    with col_sc2:
        st.metric("🔥 Streak", f"{st.session_state['kbc_streak']}")
    with col_sc3:
        st.metric(f"📚 Question Pool ({selected_medium})", f"{q_count}")

    if st.session_state["kbc_q"] is None:
        q_data = fetch_kbc_question(selected_class, subject, selected_medium)
        if q_data:
            st.session_state["kbc_q"] = q_data
            st.session_state["kbc_answered"] = False
            st.session_state["kbc_fifty_used"] = False
            st.session_state["kbc_disabled_options"] = []
            st.session_state["kbc_selected_idx"] = None

    if client and q_count < 10:
        if st.button(f"⚡ Generate 10 Questions via AI ({selected_medium})"):
            with st.spinner("Preparing questions..."):
                batch = generate_ai_kbc_batch(client, selected_class, subject, selected_medium, count=10)
                if batch:
                    insert_batch_kbc_questions(selected_class, subject, selected_medium, batch)
                    st.success("Questions added to pool!")
                    st.rerun()

    curr = st.session_state["kbc_q"]
    if curr:
        st.markdown(f"""
            <div class="kbc-box">
                <span class="kbc-label">KBC Hot Seat • {selected_class} • {subject} ({selected_medium})</span>
                <div class="kbc-q-title">{curr['question']}</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Lifeline
        if not st.session_state["kbc_fifty_used"] and not st.session_state["kbc_answered"]:
            if st.button("⚖️ 50:50 Lifeline"):
                correct = curr["correct_idx"]
                wrong_indices = [i for i in range(4) if i != correct]
                st.session_state["kbc_disabled_options"] = random.sample(wrong_indices, 2)
                st.session_state["kbc_fifty_used"] = True
                st.rerun()

        # 2x2 Clean Responsive Options
        labels = ["A", "B", "C", "D"]
        c1, c2 = st.columns(2)
        
        for idx in range(4):
            col = c1 if idx % 2 == 0 else c2
            opt_text = curr["options"][idx]
            is_disabled = idx in st.session_state["kbc_disabled_options"]
            btn_label = f"[{labels[idx]}]  {opt_text}" if not is_disabled else f"[{labels[idx]}]  ---"
            
            if col.button(btn_label, key=f"kbc_opt_{idx}", disabled=is_disabled or st.session_state["kbc_answered"], use_container_width=True):
                st.session_state["kbc_answered"] = True
                st.session_state["kbc_selected_idx"] = idx
                if idx == curr["correct_idx"]:
                    st.session_state["kbc_score"] += 1000
                    st.session_state["kbc_streak"] += 1
                else:
                    st.session_state["kbc_streak"] = 0
                st.rerun()

        if st.session_state["kbc_answered"]:
            sel = st.session_state["kbc_selected_idx"]
            corr = curr["correct_idx"]
            if sel == corr:
                st.balloons()
                st.success(f"🎉 **Correct Answer! (+1,000 Pts)**\n\n💡 **Explanation:** {curr['explanation']}")
            else:
                st.error(f"❌ **Incorrect!** Correct Answer: **[{labels[corr]}] {curr['options'][corr]}**\n\n💡 **Explanation:** {curr['explanation']}")
            
            if st.button("👉 Next Question", use_container_width=True):
                st.session_state["kbc_q"] = fetch_kbc_question(selected_class, subject, selected_medium)
                st.session_state["kbc_answered"] = False
                st.session_state["kbc_fifty_used"] = False
                st.session_state["kbc_disabled_options"] = []
                st.session_state["kbc_selected_idx"] = None
                st.rerun()

# 2. LIVE CLASSROOM
with tab_live:
    ROOM_SALT = "GVHSS_Kuniya_HQ"
    sanitized_class = selected_class.replace(' ', '_').replace('(', '').replace(')', '').replace('+', 'Plus')
    sanitized_subj = subject.split(' ')[0]
    sanitized_med = "MAL" if "Malayalam" in selected_medium else "ENG"
    room_id = f"KUNIYA_{sanitized_class}_{sanitized_subj}_{sanitized_med}_{ROOM_SALT}"
    
    st.info(f"🔴 Live Stream: **{selected_class} - {subject}** ({selected_medium})")
    display_user = f"{st.session_state['display_name']} ({st.session_state['role'].capitalize()})"
    jitsi_url = f"https://meet.jit.si/{room_id}#userInfo.displayName=\"{display_user}\""
    
    st.iframe(jitsi_url, height=580)

# 3. AI STUDY MENTOR
with tab_doubt:
    st.markdown(f"#### 🤖 24/7 Kerala SCERT AI Tutor ({selected_medium})")
    hint_msg = "ഉദാ: വൃത്തങ്ങൾ എന്ന പാഠത്തിലെ പ്രധാന സമവാക്യങ്ങൾ വിശദീകരിക്കാമോ?" if "Malayalam" in selected_medium else "e.g. Explain Lenz's law with formula."
    user_q = st.text_area("Ask any textbook concept or doubt:", placeholder=hint_msg)
    if st.button("Get Explanation"):
        if client and user_q.strip():
            with st.spinner("Analyzing syllabus..."):
                lang_target = "Explain strictly in clear Malayalam adhering to SCERT Malayalam textbook standards." if "Malayalam" in selected_medium else "Explain in English adhering to SCERT English medium textbook standards."
                prompt = f"""
                You are an expert Kerala SCERT teacher for GVHSS KUNIYA school.
                Class: {selected_class}
                Subject: {subject}
                Instruction Medium: {selected_medium}
                
                Language Requirement: {lang_target}
                
                Question: {user_q}
                """
                res = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
                st.markdown(res.text)
        elif not client:
            st.warning("Please configure GEMINI_API_KEY to enable AI Tutoring.")

# 4. QUESTION LENS
with tab_img:
    st.markdown(f"#### 📸 Snap & Solve Textbook Questions ({selected_medium})")
    up_img = st.file_uploader("Upload question image", type=["png", "jpg", "jpeg"])
    if up_img:
        img = Image.open(up_img)
        st.image(img, use_container_width=True)
        if st.button("Solve Problem"):
            if client:
                with st.spinner("Processing image..."):
                    lang_target = "Solve in clear Malayalam." if "Malayalam" in selected_medium else "Solve in English."
                    res = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[f"Class: {selected_class}, Subject: {subject}, Medium: {selected_medium}. {lang_target} Solve this problem step-by-step.", img]
                    )
                    st.markdown(res.text)
            else:
                st.warning("Please configure GEMINI_API_KEY.")
