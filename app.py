import streamlit as st
from google import genai
from PIL import Image
import sqlite3
import random
import json
import os

st.set_page_config(
    page_title="GVHSS കുണിയ - ഡിജിറ്റൽ സ്കൂൾ പോർട്ടൽ",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- MODERN LUXURY TYPOGRAPHY & UI -----------------
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Gayathri:wght@400;700&family=Manjari:wght@400;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"], .stMarkdown, p, span, label {
        font-family: 'Manjari', 'Gayathri', 'Plus Jakarta Sans', sans-serif !important;
        letter-spacing: 0.2px;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Gayathri', 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 700 !important;
    }

    .stApp {
        background-color: #0F172A;
        background-image: radial-gradient(at 0% 0%, rgba(30, 58, 138, 0.3) 0, transparent 50%), 
                          radial-gradient(at 100% 100%, rgba(15, 118, 110, 0.2) 0, transparent 50%);
        color: #F8FAFC;
    }

    /* Top School Banner */
    .premium-header {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 24px 32px;
        border-radius: 20px;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3);
    }
    .school-title {
        font-size: 2.1rem;
        font-weight: 800;
        background: linear-gradient(135deg, #38BDF8 0%, #818CF8 50%, #C084FC 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        line-height: 1.2;
    }
    .school-sub {
        color: #94A3B8;
        font-size: 1rem;
        margin-top: 4px;
    }

    /* Notice Board */
    .notice-pill {
        background: rgba(245, 158, 11, 0.1);
        border: 1px solid rgba(245, 158, 11, 0.3);
        border-left: 4px solid #F59E0B;
        color: #FDE68A;
        padding: 14px 20px;
        border-radius: 12px;
        font-size: 0.98rem;
        margin-bottom: 24px;
        backdrop-filter: blur(8px);
    }

    /* KBC Game Arena */
    .kbc-arena {
        background: linear-gradient(180deg, #090D16 0%, #060911 100%);
        border: 1.5px solid #EAB308;
        border-radius: 24px;
        padding: 35px 25px;
        text-align: center;
        box-shadow: 0 0 35px rgba(234, 179, 8, 0.2);
        margin-bottom: 25px;
        position: relative;
    }
    .kbc-chip {
        display: inline-block;
        background: linear-gradient(90deg, #CA8A04, #EAB308);
        color: #000;
        font-weight: 800;
        font-size: 0.85rem;
        padding: 5px 18px;
        border-radius: 9999px;
        text-transform: uppercase;
        margin-bottom: 15px;
        letter-spacing: 0.5px;
    }
    .kbc-q-text {
        font-size: 1.5rem;
        color: #FFFFFF;
        font-weight: 700;
        line-height: 1.5;
        margin: 10px 0 5px 0;
    }

    /* Modern Login Container */
    .login-box {
        background: rgba(30, 41, 59, 0.75);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.12);
        padding: 40px 35px;
        border-radius: 24px;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        max-width: 440px;
        margin: 40px auto;
        text-align: center;
    }

    /* Inputs & Tabs Styling */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background: rgba(15, 23, 42, 0.6) !important;
        color: #F8FAFC !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 12px !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background: rgba(15, 23, 42, 0.5);
        padding: 6px;
        border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        color: #94A3B8 !important;
        padding: 8px 18px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background: #1E293B !important;
        color: #38BDF8 !important;
        border: 1px solid rgba(56, 189, 248, 0.2);
    }

    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.15);
        padding: 10px 24px;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(37, 99, 235, 0.35);
        border-color: #60A5FA;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------- KERALA SYLLABUS DATA -----------------
KERALA_CLASSES = [
    "ക്ലാസ് 8", "ക്ലാസ് 9", "ക്ലാസ് 10 (SSLC)",
    "പ്ലസ് വൺ (+1 സയൻസ്)", "പ്ലസ് വൺ (+1 കൊമേഴ്‌സ്)", "പ്ലസ് വൺ (+1 ഹ്യുമാനിറ്റീസ്)",
    "പ്ലസ് ടു (+2 സയൻസ്)", "പ്ലസ് ടു (+2 കൊമേഴ്‌സ്)", "പ്ലസ് ടു (+2 ഹ്യുമാനിറ്റീസ്)"
]

def get_subjects(cls_name, medium):
    is_mal = "മലയാളം" in medium
    if cls_name in ["ക്ലാസ് 8", "ക്ലാസ് 9", "ക്ലാസ് 10 (SSLC)"]:
        return [
            "ഗണിതം (Mathematics)", "ഭൗതികശാസ്ത്രം (Physics)", "രസതന്ത്രം (Chemistry)",
            "ജീവശാസ്ത്രം (Biology)", "സാമൂഹ്യശാസ്ത്രം I", "സാമൂഹ്യശാസ്ത്രം II", "English", "മലയാളം"
        ] if is_mal else [
            "Mathematics", "Physics", "Chemistry", "Biology", "Social Science I", "Social Science II", "English"
        ]
    elif "സയൻസ്" in cls_name:
        return [
            "Physics (ഭൗതികശാസ്ത്രം)", "Chemistry (രസതന്ത്രം)", "Mathematics (ഗണിതം)",
            "Biology (ജീവശാസ്ത്രം)", "Computer Science", "English"
        ] if is_mal else [
            "Physics", "Chemistry", "Mathematics", "Biology", "Computer Science", "English"
        ]
    elif "കൊമേഴ്‌സ്" in cls_name:
        return [
            "Accountancy (അക്കൗണ്ടൻസി)", "Business Studies", "Economics (സാമ്പത്തികശാസ്ത്രം)", "English"
        ] if is_mal else [
            "Accountancy", "Business Studies", "Economics", "English"
        ]
    return ["History (ചരിത്രം)", "Economics", "Political Science", "Sociology", "English"]

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
            medium TEXT DEFAULT 'മലയാളം മീഡിയം'
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
    c.execute('SELECT * FROM users WHERE username = ?', ('admin',))
    if not c.fetchone():
        c.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)', ('admin', 'admin@kuniya', 'പ്രിൻസിപ്പൽ / അഡ്മിൻ', 'admin', 'None', 'മലയാളം മീഡിയം'))
        c.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)', ('teacher1', 'teacher123', 'സുരേഷ് സർ (SSLC Maths)', 'teacher', 'None', 'മലയാളം മീഡിയം'))
        c.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)', ('student1', 'student123', 'അർജുൻ കെ', 'student', 'ക്ലാസ് 10 (SSLC)', 'മലയാളം മീഡിയം'))
        c.execute('INSERT INTO notices (notice_text) VALUES (?)', ('ജി.വി.എച്ച്.എസ്.എസ് കുണിയ ഡിജിറ്റൽ സ്കൂൾ പോർട്ടലിലേക്ക് ഏവർക്കും ഹൃദ്യമായ സ്വാഗതം!',))
        
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
    c.execute('SELECT username, name, role, student_class, medium FROM users')
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
        return True, "യൂസറെ വിജയകരമായി ചേർത്തു!"
    except sqlite3.IntegrityError:
        return False, "ഈ യൂസർ ഐഡി നിലവിലുണ്ട്."

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
    return row[0] if row else "പ്രത്യേക അറിയിപ്പുകൾ ഒന്നുമില്ല."

# ----------------- KBC ENGINE -----------------
def fetch_random_kbc_question(target_class, subject, medium):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        SELECT id, question, opt_a, opt_b, opt_c, opt_d, correct_idx, explanation 
        FROM kbc_questions 
        WHERE target_class = ? AND subject = ? AND medium = ?
        ORDER BY RANDOM() LIMIT 1
    ''', (target_class, subject, medium))
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
    c.execute('''
        SELECT COUNT(*) FROM kbc_questions 
        WHERE target_class = ? AND subject = ? AND medium = ?
    ''', (target_class, subject, medium))
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
    prompt = f"""
    You are an expert Kerala SCERT textbook paper setter for GVHSS KUNIYA (ജി.വി.എച്ച്.എസ്.എസ് കുണിയ).
    Generate {count} multiple choice questions in Kaun Banega Crorepati (KBC) style.
    Class: {target_class}
    Subject: {subject}
    Medium: {medium}

    Guidelines:
    1. Base strictly on Kerala State SCERT textbooks.
    2. If Medium is 'മലയാളം മീഡിയം', use clean, grammatically correct and elegant Malayalam without any spelling issues.
    3. Provide 4 distinct options with exactly one correct answer.
    4. Return ONLY a valid JSON array of objects without markdown ticks.

    JSON Structure:
    [
      {{
        "q": "ചോദ്യം ഇവിടെ നൽകുക",
        "options": ["ഓപ്ഷൻ 1", "ഓപ്ഷൻ 2", "ഓപ്ഷൻ 3", "ഓപ്ഷൻ 4"],
        "answer_idx": 0,
        "exp": "ഉത്തരത്തിന്റെ വിശദീകരണം"
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
    st.session_state["medium"] = "മലയാളം മീഡിയം"

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

# ----------------- LOGIN PAGE -----------------
def modern_login_screen():
    c1, c2, c3 = st.columns([1, 1.3, 1])
    with c2:
        st.markdown("""
            <div class="login-box">
                <span style="background: rgba(56, 189, 248, 0.1); color: #38BDF8; padding: 6px 16px; border-radius: 9999px; font-weight: 700; font-size: 0.85rem; border: 1px solid rgba(56, 189, 248, 0.2);">
                    🏛️ കേരള പൊതുവിദ്യാഭ്യാസ വകുപ്പ്
                </span>
                <h2 style="margin: 16px 0 2px 0; color: #FFFFFF; font-size: 1.8rem; font-weight: 800;">GVHSS കുണിയ</h2>
                <p style="color: #94A3B8; font-size: 0.95rem; margin-bottom: 25px;">
                    ഗവ. വൊക്കേഷണൽ ഹയർ സെക്കൻഡറി സ്കൂൾ കുണിയ<br>
                    <small style="color: #64748B;">ഡിജിറ്റൽ ലേണിംഗ് & ലൈവ് പോർട്ടൽ</small>
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            uid = st.text_input("യൂസർ ഐഡി (User ID)", placeholder="eg: student1").strip().lower()
            pwd = st.text_input("പാസ്‌വേർഡ് (Password)", type="password", placeholder="••••••••").strip()
            submit = st.form_submit_button("പ്രവേശിക്കുക (Login)", use_container_width=True)
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
                    st.error("തെറ്റായ യൂസർ ഐഡിയോ പാസ്‌വേർഡോ ആണ്.")

if not st.session_state["authenticated"]:
    modern_login_screen()
    st.stop()

# ----------------- MAIN APP DASHBOARD -----------------

# Header
st.markdown(f"""
    <div class="premium-header">
        <div>
            <h1 class="school-title">GVHSS കുണിയ</h1>
            <div class="school-sub">ഗവ. വൊക്കേഷണൽ ഹയർ സെക്കൻഡറി സ്കൂൾ കുണിയ • കാസർഗോഡ്</div>
        </div>
        <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255,255,255,0.1); padding: 10px 18px; border-radius: 12px; text-align: right;">
            <div style="font-size: 0.8rem; color: #94A3B8;">ലോഗിൻ ചെയ്ത ഉപയോക്താവ്</div>
            <strong style="color: #38BDF8; font-size: 1.05rem;">{st.session_state['display_name']}</strong>
        </div>
    </div>
""", unsafe_allow_html=True)

# Notice
notice = get_latest_notice()
st.markdown(f'<div class="notice-pill">📢 <strong>സ്കൂൾ അറിയിപ്പ്:</strong> {notice}</div>', unsafe_allow_html=True)

# Sidebar
st.sidebar.markdown("### പ്രൊഫൈൽ കാർഡ്")
st.sidebar.info(f"**പേര്:** {st.session_state['display_name']}\n\n**പദവി:** {st.session_state['role']}")

cur_idx = 0 if st.session_state["medium"] == "മലയാളം മീഡിയം" else 1
selected_medium = st.sidebar.radio("പഠന മാധ്യമം (Medium):", ["മലയാളം മീഡിയം", "English Medium"], index=cur_idx)
st.session_state["medium"] = selected_medium

if st.sidebar.button("ലോഗൗട്ട് (Logout)", use_container_width=True):
    st.session_state["authenticated"] = False
    st.session_state["username"] = None
    st.rerun()

# Class & Subject
if st.session_state["role"] in ["admin", "teacher"]:
    selected_class = st.sidebar.selectbox("ക്ലാസ് തിരഞ്ഞെടുക്കുക", KERALA_CLASSES)
else:
    selected_class = st.session_state.get("student_class", "ക്ലാസ് 10 (SSLC)")
    st.sidebar.markdown(f"**ക്ലാസ്:** {selected_class}")

available_subjects = get_subjects(selected_class, selected_medium)
subject = st.sidebar.selectbox("വിഷയം തിരഞ്ഞെടുക്കുക", available_subjects)

# AI Client
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

# Admin Panel
if st.session_state["role"] == "admin":
    with st.expander("⚙️ അഡ്മിനിസ്ട്രേഷൻ കൺട്രോൾ", expanded=False):
        at1, at2, at3 = st.tabs(["➕ പുതിയ യൂസർ", "👥 യൂസർ ലിസ്റ്റ്", "📢 നോട്ടീസ് മാറ്റുക"])
        with at1:
            with st.form("add_user_form"):
                au_id = st.text_input("User ID").strip().lower()
                au_pwd = st.text_input("Password").strip()
                au_name = st.text_input("Full Name").strip()
                au_role = st.selectbox("Role", ["student", "teacher"])
                au_cls = st.selectbox("Class", ["None"] + KERALA_CLASSES)
                au_med = st.selectbox("Medium", ["മലയാളം മീഡിയം", "English Medium"])
                if st.form_submit_button("സേവ് ചെയ്യുക"):
                    ok, msg = add_user(au_id, au_pwd, au_name, au_role, au_cls, au_med)
                    st.success(msg) if ok else st.error(msg)
        with at2:
            for u in get_all_users():
                c1, c2, c3, c4 = st.columns([2, 3, 2, 1])
                c1.write(f"**{u[0]}**")
                c2.write(f"{u[1]} ({u[3]})")
                c3.write(u[4])
                if u[0] != "admin" and c4.button("Delete", key=f"del_{u[0]}"):
                    delete_user(u[0])
                    st.rerun()
        with at3:
            unote = st.text_area("പുതിയ അറിയിപ്പ് നൽകുക:", value=notice)
            if st.button("നോട്ടീസ് പബ്ലിഷ് ചെയ്യുക"):
                set_latest_notice(unote)
                st.success("നോട്ടീസ് അപ്‌ഡേറ്റ് ചെയ്തു!")
                st.rerun()

# ----------------- TABS -----------------
tab_kbc, tab_live, tab_doubt, tab_img = st.tabs([
    "🏆 KBC ക്വിസ് ചലഞ്ച്", 
    "🎥 ലൈവ് ക്ലാസ്റൂം", 
    "🤖 SCERT AI അധ്യാപകൻ", 
    "📸 ഫോട്ടോ അപ്‌ലോഡ്"
])

# 1. KBC QUIZ
with tab_kbc:
    q_count = count_kbc_questions(selected_class, subject, selected_medium)
    
    col_sc1, col_sc2, col_sc3 = st.columns(3)
    with col_sc1:
        st.metric("🏆 നേടിയ പോയിന്റുകൾ", f"{st.session_state['kbc_score']} Pts")
    with col_sc2:
        st.metric("🔥 വിന്നിംഗ് സ്ട്രീക്ക്", f"{st.session_state['kbc_streak']}")
    with col_sc3:
        st.metric("📚 ലഭ്യമായ ചോദ്യങ്ങൾ", f"{q_count}")

    if q_count < 10:
        st.caption("ചോദ്യങ്ങൾ തയ്യാറാക്കാൻ ക്ലിക്ക് ചെയ്യുക:")
        if st.button("⚡ AI വഴി 15 പുതിയ ചോദ്യങ്ങൾ ശേഖരത്തിലേക്ക് ചേർക്കുക"):
            if client:
                with st.spinner("ചോദ്യങ്ങൾ തയ്യാറാക്കുന്നു..."):
                    batch = generate_ai_kbc_batch(client, selected_class, subject, selected_medium, count=15)
                    if batch:
                        insert_batch_kbc_questions(selected_class, subject, selected_medium, batch)
                        st.success("ചോദ്യങ്ങൾ വിജയകരമായി ചേർത്തു!")
                        st.rerun()

    if st.session_state["kbc_q"] is None:
        if st.button("🚀 ചോദ്യം ആരംഭിക്കുക (Next Question)", use_container_width=True):
            loaded = fetch_random_kbc_question(selected_class, subject, selected_medium)
            if loaded:
                st.session_state["kbc_q"] = loaded
                st.session_state["kbc_answered"] = False
                st.session_state["kbc_disabled_options"] = []
                st.session_state["kbc_fifty_used"] = False
                st.rerun()
            elif client:
                with st.spinner("AI പുതിയ ചോദ്യം തയ്യാറാക്കുന്നു..."):
                    batch = generate_ai_kbc_batch(client, selected_class, subject, selected_medium, count=10)
                    if batch:
                        insert_batch_kbc_questions(selected_class, subject, selected_medium, batch)
                        st.session_state["kbc_q"] = fetch_random_kbc_question(selected_class, subject, selected_medium)
                        st.session_state["kbc_answered"] = False
                        st.session_state["kbc_disabled_options"] = []
                        st.rerun()

    curr = st.session_state["kbc_q"]
    if curr:
        st.markdown(f"""
            <div class="kbc-arena">
                <span class="kbc-chip">💰 {selected_class} • {subject}</span>
                <div class="kbc-q-text">{curr['question']}</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Lifeline
        if not st.session_state["kbc_fifty_used"] and not st.session_state["kbc_answered"]:
            if st.button("⚖️ 50:50 ലൈഫ്‌ലൈൻ"):
                correct = curr["correct_idx"]
                wrong_indices = [i for i in range(4) if i != correct]
                st.session_state["kbc_disabled_options"] = random.sample(wrong_indices, 2)
                st.session_state["kbc_fifty_used"] = True
                st.rerun()

        # Options
        labels = ["A", "B", "C", "D"]
        c1, c2 = st.columns(2)
        
        for idx in range(4):
            col = c1 if idx % 2 == 0 else c2
            opt_text = curr["options"][idx]
            is_disabled = idx in st.session_state["kbc_disabled_options"]
            btn_label = f"[{labels[idx]}]  {opt_text}" if not is_disabled else f"[{labels[idx]}]  ————"
            
            if col.button(btn_label, key=f"kbc_opt_{idx}", disabled=is_disabled or st.session_state["kbc_answered"], use_container_width=True):
                st.session_state["kbc_answered"] = True
                if idx == curr["correct_idx"]:
                    st.session_state["kbc_score"] += 1000
                    st.session_state["kbc_streak"] += 1
                    st.balloons()
                    st.success(f"🎉 **ശരിയുത്തരം! +1000 പോയിന്റ്.**\n\n💡 **വിശദീകരണം:** {curr['explanation']}")
                else:
                    st.session_state["kbc_streak"] = 0
                    c_label = labels[curr["correct_idx"]]
                    c_ans = curr["options"][curr["correct_idx"]]
                    st.error(f"❌ **തെറ്റായ ഉത്തരം!** ശരിയുത്തരം: **[{c_label}] {c_ans}**\n\n💡 **വിശദീകരണം:** {curr['explanation']}")
        
        if st.session_state["kbc_answered"]:
            if st.button("👉 അടുത്ത ചോദ്യത്തിലേക്ക് കടക്കുക", use_container_width=True):
                st.session_state["kbc_q"] = None
                st.session_state["kbc_answered"] = False
                st.session_state["kbc_disabled_options"] = []
                st.rerun()

# 2. LIVE CLASSROOM (Replaced with st.iframe)
with tab_live:
    ROOM_SALT = "GVHSS_Kuniya_Secure"
    sanitized_class = selected_class.replace(' ', '_').replace('(', '').replace(')', '').replace('+', 'Plus')
    sanitized_subj = subject.split(' ')[0]
    sanitized_med = "MAL" if "മലയാളം" in selected_medium else "ENG"
    room_id = f"KUNIYA_{sanitized_class}_{sanitized_subj}_{sanitized_med}_{ROOM_SALT}"
    
    st.info(f"🔴 ക്ലാസ്: **{selected_class}** | വിഷയം: **{subject}** ({selected_medium})")
    display_user = f"{st.session_state['display_name']} ({selected_medium})"
    jitsi_url = f"https://meet.jit.si/{room_id}#userInfo.displayName=\"{display_user}\""
    
    # Official Streamlit native iframe integration
    st.iframe(jitsi_url, height=600)

# 3. DOUBT SOLVER
with tab_doubt:
    st.markdown("#### 🤖 SCERT കേരള സിലബസ് AI അധ്യാപകൻ")
    user_q = st.text_area("നിങ്ങളുടെ സംശയം ചോദിക്കുക:")
    if st.button("ഉത്തരം നൽകുക"):
        if client and user_q.strip():
            with st.spinner("അധ്യാപകൻ പരിശോധിക്കുന്നു..."):
                prompt = f"""
                നീ ജി.വി.എച്ച്.എസ്.എസ് കുണിയ (GVHSS KUNIYA) സ്കൂളിലെ കേരള സിലബസ് അധ്യാപകനാണ്.
                ക്ലാസ്: {selected_class}, വിഷയം: {subject}, മാധ്യമം: {selected_medium}.
                ഈ ചോദ്യത്തിന് വളരെ മനോഹരവും ശുദ്ധവുമായ ഭാഷയിൽ SCERT പാഠപുസ്തക രീതിയിൽ സ്റ്റെപ്പ് ബൈ സ്റ്റെപ്പ് ആയി ഉത്തരം നൽകുക: {user_q}
                """
                res = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
                st.markdown(res.text)

# 4. PHOTO SOLVER
with tab_img:
    st.markdown("#### 📸 പുസ്തകത്തിലെ ചോദ്യത്തിന്റെ ചിത്രം അപ്‌ലോഡ് ചെയ്യാം")
    up_img = st.file_uploader("ഫോട്ടോ തിരഞ്ഞെടുക്കുക", type=["png", "jpg", "jpeg"])
    if up_img:
        img = Image.open(up_img)
        st.image(img, use_container_width=True)
        if st.button("പരിഹാരം കണ്ടെത്തുക"):
            if client:
                with st.spinner("ചിത്രം പരിശോധിക്കുന്നു..."):
                    res = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[f"ക്ലാസ്: {selected_class}, വിഷയം: {subject}, മാധ്യമം: {selected_medium}. ചിത്രത്തിലെ ചോദ്യം വായിച്ച് ലളിതമായ മലയാളത്തിൽ പരിഹരിച്ചു നൽകുക.", img]
                    )
                    st.markdown(res.text)
