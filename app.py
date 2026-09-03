import streamlit as st
import streamlit.components.v1 as components
from google import genai
from PIL import Image
import sqlite3
import random
import json
import os

# പേജ് കോൺഫിഗറേഷൻ
st.set_page_config(
    page_title="GVHSS KUNIYA - KBC ക്വിസ് & ക്ലാസ്റൂം",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- MODERN KBC STYLING -----------------
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    }
    
    .stApp {
        background: #F8FAFC;
    }
    
    .school-banner {
        background: linear-gradient(135deg, #064E3B 0%, #047857 50%, #0F766E 100%);
        padding: 22px 28px;
        border-radius: 16px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 10px 25px -5px rgba(6, 78, 59, 0.2);
    }
    .school-banner h1 {
        color: #FFFFFF !important;
        font-size: 1.9rem !important;
        font-weight: 800;
        margin: 0;
    }
    .school-banner p {
        color: #A7F3D0 !important;
        font-size: 0.9rem;
        margin: 4px 0 0 0;
    }

    /* KBC Golden Stage Box */
    .kbc-stage {
        background: radial-gradient(circle at center, #0B192C 0%, #000B58 100%);
        border: 2px solid #F1C40F;
        border-radius: 20px;
        padding: 25px 20px;
        color: #FFFFFF;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 0 20px rgba(241, 196, 15, 0.25);
    }
    .kbc-question {
        font-size: 1.3rem;
        font-weight: 700;
        color: #FFFDF0;
        letter-spacing: 0.3px;
        margin-top: 10px;
    }
    .kbc-points {
        background: #FFD700;
        color: #000B58;
        padding: 4px 16px;
        border-radius: 9999px;
        font-weight: 800;
        font-size: 0.9rem;
        display: inline-block;
    }

    /* Login Form */
    .login-container {
        max-width: 440px;
        margin: 30px auto;
        background: #FFFFFF;
        padding: 35px 30px;
        border-radius: 20px;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.05);
        border: 1px solid #E2E8F0;
        text-align: center;
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
            "അക്കൗണ്ടൻസി (Accountancy)", "ബിസിനസ് സ്റ്റഡീസ്", "Economics (സാമ്പത്തികശാസ്ത്രം)", "English"
        ] if is_mal else [
            "Accountancy", "Business Studies", "Economics", "English"
        ]
    return ["History (ചരിത്രം)", "Economics", "Political Science", "Sociology", "English"]

# ----------------- DATABASE (SQLite with Question Bank) -----------------
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
    # KBC Question Bank Table
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
        c.execute('INSERT INTO notices (notice_text) VALUES (?)', ('GVHSS KUNIYA KBC ക്വിസ് ചലഞ്ചിലേക്ക് സ്വാഗതം! പങ്കെടുത്ത് പോയിന്റുകൾ നേടൂ.',))
        
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
        return True, "യൂസറെ ചേർത്തു!"
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

# ----------------- KBC QUESTION BANK FUNCTIONS -----------------
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
    You are an expert SCERT Kerala Syllabus textbook exam paper designer for GVHSS KUNIYA.
    Generate {count} unique, high-quality multiple choice questions (MCQ) in Kaun Banega Crorepati (KBC) style.
    Class: {target_class}
    Subject: {subject}
    Medium: {medium}

    Guidelines:
    1. Base strictly on SCERT Kerala State Syllabus textbooks.
    2. If Medium is 'മലയാളം മീഡിയം', everything must be in clear Malayalam.
    3. If Medium is 'English Medium', questions and options must be in English.
    4. Provide 4 distinct options (Option A, B, C, D) with exactly one correct answer.
    5. Return ONLY a pure JSON array of objects. No markdown ticks, no commentary.

    Schema:
    [
      {{
        "q": "ചോദ്യം ഇവിടെ നൽകുക?",
        "options": ["ഓപ്ഷൻ A", "ഓപ്ഷൻ B", "ഓപ്ഷൻ C", "ഓപ്ഷൻ D"],
        "answer_idx": 0,
        "exp": "ഉത്തരത്തിന്റെ സമഗ്രമായ വിശദീകരണം."
      }}
    ]
    """
    try:
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        data = json.loads(res.text)
        return data
    except Exception as e:
        return []

# ----------------- SESSION STATE -----------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["username"] = None
    st.session_state["role"] = None
    st.session_state["display_name"] = None
    st.session_state["student_class"] = None
    st.session_state["medium"] = "മലയാളം മീഡിയം"

# KBC Game State
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

# ----------------- LOGIN SCREEN -----------------
def login_screen():
    c1, c2, c3 = st.columns([1, 1.4, 1])
    with c2:
        st.markdown("""
            <div class="login-container">
                <span style="background: #ECFDF5; color: #047857; padding: 5px 14px; border-radius: 9999px; font-weight: 700; font-size: 0.8rem;">
                    🌴 KERALA SYLLABUS & KBC QUIZ
                </span>
                <h2 style="margin: 8px 0 0 0; color: #064E3B; font-weight: 800;">GVHSS KUNIYA</h2>
                <p style="color: #64748B; font-size: 0.9rem; margin-bottom: 22px;">
                    ഗവ. വൊക്കേഷണൽ ഹയർ സെക്കൻഡറി സ്കൂൾ കുനിയ
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            uid = st.text_input("യൂസർ ഐഡി (User ID)", placeholder="eg: student1").strip().lower()
            pwd = st.text_input("പാസ്‌വേർഡ് (Password)", type="password", placeholder="••••••••").strip()
            submit = st.form_submit_button("പോർട്ടലിൽ പ്രവേശിക്കുക", use_container_width=True)
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
    login_screen()
    st.stop()

# ----------------- MAIN PORTAL -----------------

# Header
st.markdown(f"""
    <div class="school-banner">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <div>
                <h1>GVHSS KUNIYA</h1>
                <p>കേരള സ്റ്റേറ്റ് സിലബസ് • KBC മോഡൽ AI ക്വിസ് & ലൈവ് ക്ലാസുകൾ</p>
            </div>
            <div style="background: rgba(255,255,255,0.18); padding: 8px 16px; border-radius: 12px; margin-top: 5px;">
                <span style="font-size: 0.85rem; color: #D1FAE5;">ഹലോ, </span>
                <strong style="color: #FFFFFF;">{st.session_state['display_name']}</strong>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

# Notice
notice = get_latest_notice()
st.markdown(f"<div style='background: #FEF3C7; border-left: 4px solid #F59E0B; padding: 10px 16px; border-radius: 8px; color: #92400E; margin-bottom: 20px;'>📢 <strong>സ്കൂൾ അറിയിപ്പ്:</strong> {notice}</div>", unsafe_allow_html=True)

# Sidebar
st.sidebar.markdown("### പ്രൊഫൈൽ")
st.sidebar.info(f"**പേര്:** {st.session_state['display_name']}\n\n**റോൾ:** {st.session_state['role']}")

# Medium Selection
cur_idx = 0 if st.session_state["medium"] == "മലയാളം മീഡിയം" else 1
selected_medium = st.sidebar.radio("പഠന മാധ്യമം (Medium):", ["മലയാളം മീഡിയം", "English Medium"], index=cur_idx)
st.session_state["medium"] = selected_medium

if st.sidebar.button("ലോഗൗട്ട് (Logout)", use_container_width=True):
    st.session_state["authenticated"] = False
    st.session_state["username"] = None
    st.rerun()

# Class & Subject Selection
if st.session_state["role"] in ["admin", "teacher"]:
    selected_class = st.sidebar.selectbox("ക്ലാസ് തിരഞ്ഞെടുക്കുക", KERALA_CLASSES)
else:
    selected_class = st.session_state.get("student_class", "ക്ലാസ് 10 (SSLC)")
    st.sidebar.markdown(f"**ക്ലാസ്:** {selected_class}")

available_subjects = get_subjects(selected_class, selected_medium)
subject = st.sidebar.selectbox("വിഷയം തിരഞ്ഞെടുക്കുക", available_subjects)

# API Engine
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

# ----------------- ADMIN PANEL -----------------
if st.session_state["role"] == "admin":
    with st.expander("⚙️ സ്കൂൾ അഡ്മിൻ പാനൽ (യൂസർ മാനേജ്‌മെന്റ്)", expanded=False):
        at1, at2, at3 = st.tabs(["➕ യൂസറെ ചേർക്കുക", "👥 രജിസ്റ്റർ ചെയ്തവർ", "📢 നോട്ടീസ്"])
        with at1:
            with st.form("add_user_form"):
                au_id = st.text_input("User ID").strip().lower()
                au_pwd = st.text_input("Password").strip()
                au_name = st.text_input("Full Name").strip()
                au_role = st.selectbox("Role", ["student", "teacher"])
                au_cls = st.selectbox("Class", ["None"] + KERALA_CLASSES)
                au_med = st.selectbox("Medium", ["മലയാളം മീഡിയം", "English Medium"])
                if st.form_submit_button("Save User"):
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
            unote = st.text_area("പുതിയ അറിയിപ്പ്:", value=notice)
            if st.button("Publish Notice"):
                set_latest_notice(unote)
                st.success("Updated!")
                st.rerun()

# ----------------- MAIN TABS -----------------
tab_kbc, tab_live, tab_doubt, tab_img = st.tabs([
    "🏆 KBC ക്വിസ് ചലഞ്ച് (Crorepati Quiz)", 
    "🎥 ലൈവ് ക്ലാസ്റൂം", 
    "🤖 SCERT AI ഡൗട്ട് സോൾവർ", 
    "📸 ഫോട്ടോ അപ്‌ലോഡ്"
])

# ----------------- 1. KBC QUIZ CHALLENGE -----------------
with tab_kbc:
    q_count = count_kbc_questions(selected_class, subject, selected_medium)
    
    col_sc1, col_sc2, col_sc3 = st.columns([1.5, 1.5, 2])
    with col_sc1:
        st.metric("🏆 നേടിയ സ്കോർ", f"{st.session_state['kbc_score']} Points")
    with col_sc2:
        st.metric("🔥 വിന്നിംഗ് സ്ട്രീക്ക്", f"{st.session_state['kbc_streak']} ശരിയുത്തരങ്ങൾ")
    with col_sc3:
        st.metric("📚 ലഭ്യമായ ചോദ്യങ്ങൾ", f"{q_count} ചോദ്യങ്ങൾ ലഭ്യമാണ്")

    # ബാങ്ക് കുറവാണെങ്കിൽ തനിയെ AI വഴി പുതിയ ചോദ്യങ്ങൾ ജനറേറ്റ് ചെയ്യുന്ന ബട്ടൺ
    if q_count < 10:
        st.warning(f"ഈ വിഷയത്തിൽ ചോദ്യങ്ങൾ കുറവാണ്. AI വഴി ഇപ്പോൾത്തന്നെ പുതിയ ചോദ്യങ്ങൾ ലഭ്യമാക്കാം.")
        if st.button("⚡ AI വഴി 15 പുതിയ ചോദ്യങ്ങൾ ഉടൻ തയ്യാറാക്കുക"):
            if client:
                with st.spinner("SCERT പാഠപുസ്തകത്തിൽ നിന്ന് ചോദ്യങ്ങൾ തയ്യാറാക്കുന്നു..."):
                    batch = generate_ai_kbc_batch(client, selected_class, subject, selected_medium, count=15)
                    if batch:
                        insert_batch_kbc_questions(selected_class, subject, selected_medium, batch)
                        st.success("പുതിയ 15 KBC ചോദ്യങ്ങൾ വിജയകരമായി ചേർത്തു!")
                        st.rerun()
            else:
                st.error("API Key ലഭ്യമല്ല.")

    # ചോദ്യം ലോഡ് ചെയ്യുക
    if st.session_state["kbc_q"] is None:
        if st.button("🚀 പുതിയ ചോദ്യം കളിക്കുക (Next Question)", use_container_width=True):
            loaded = fetch_random_kbc_question(selected_class, subject, selected_medium)
            if loaded:
                st.session_state["kbc_q"] = loaded
                st.session_state["kbc_answered"] = False
                st.session_state["kbc_disabled_options"] = []
                st.session_state["kbc_fifty_used"] = False
                st.rerun()
            elif client:
                with st.spinner("AI വഴി പുതിയ ചോദ്യം തയ്യാറാക്കുന്നു..."):
                    batch = generate_ai_kbc_batch(client, selected_class, subject, selected_medium, count=10)
                    if batch:
                        insert_batch_kbc_questions(selected_class, subject, selected_medium, batch)
                        st.session_state["kbc_q"] = fetch_random_kbc_question(selected_class, subject, selected_medium)
                        st.session_state["kbc_answered"] = False
                        st.session_state["kbc_disabled_options"] = []
                        st.rerun()
    
    # ചോദ്യം ഡിസ്പ്ലേ
    curr = st.session_state["kbc_q"]
    if curr:
        st.markdown(f"""
            <div class="kbc-stage">
                <span class="kbc-points">💰 {selected_class} • {subject}</span>
                <div class="kbc-question">❓ {curr['question']}</div>
            </div>
        """, unsafe_allow_html=True)
        
        # ലൈഫ്‌ലൈൻ ബട്ടണുകൾ
        ll_col1, ll_col2 = st.columns(2)
        with ll_col1:
            if not st.session_state["kbc_fifty_used"] and not st.session_state["kbc_answered"]:
                if st.button("⚖️ 50:50 ലൈഫ്‌ലൈൻ (രണ്ട് തെറ്റായ ഓപ്ഷനുകൾ ഒഴിവാക്കുക)"):
                    correct = curr["correct_idx"]
                    wrong_indices = [i for i in range(4) if i != correct]
                    to_disable = random.sample(wrong_indices, 2)
                    st.session_state["kbc_disabled_options"] = to_disable
                    st.session_state["kbc_fifty_used"] = True
                    st.rerun()
        with ll_col2:
            if st.session_state["kbc_fifty_used"]:
                st.caption("✅ 50:50 ലൈഫ്‌ലൈൻ ഉപയോഗിച്ചു കഴിഞ്ഞു.")

        # KBC ഓപ്ഷൻ ഗ്രിഡ് (2x2)
        labels = ["A", "B", "C", "D"]
        c1, c2 = st.columns(2)
        
        for idx in range(4):
            col = c1 if idx % 2 == 0 else c2
            opt_text = curr["options"][idx]
            is_disabled = idx in st.session_state["kbc_disabled_options"]
            btn_label = f"[{labels[idx]}] {opt_text}" if not is_disabled else f"[{labels[idx]}] ———"
            
            if col.button(btn_label, key=f"kbc_opt_{idx}", disabled=is_disabled or st.session_state["kbc_answered"], use_container_width=True):
                st.session_state["kbc_answered"] = True
                if idx == curr["correct_idx"]:
                    st.session_state["kbc_score"] += 1000
                    st.session_state["kbc_streak"] += 1
                    st.balloons()
                    st.success(f"🎉 **ശരിയുത്തരം! കോടിപതി പോയിന്റുകൾ +1000.**\n\n💡 **വിശദീകരണം:** {curr['explanation']}")
                else:
                    st.session_state["kbc_streak"] = 0
                    correct_char = labels[curr["correct_idx"]]
                    correct_val = curr["options"][curr["correct_idx"]]
                    st.error(f"❌ **തെറ്റായ ഉത്തരം!** ശരിയുത്തരം: **[{correct_char}] {correct_val}**\n\n💡 **വിശദീകരണം:** {curr['explanation']}")
        
        # അടുത്ത ചോദ്യത്തിനായുള്ള ബട്ടൺ
        if st.session_state["kbc_answered"]:
            if st.button("👉 അടുത്ത ചോദ്യത്തിലേക്ക് കടക്കുക (Next Question)", use_container_width=True):
                st.session_state["kbc_q"] = None
                st.session_state["kbc_answered"] = False
                st.session_state["kbc_disabled_options"] = []
                st.rerun()

# ----------------- 2. LIVE CLASSROOM -----------------
with tab_live:
    ROOM_SALT = "Kuniya_Kerala_2026"
    sanitized_class = selected_class.replace(' ', '_').replace('(', '').replace(')', '').replace('+', 'Plus')
    sanitized_subj = subject.split(' ')[0]
    sanitized_med = "MAL" if "മലയാളം" in selected_medium else "ENG"
    room_id = f"KUNIYA_{sanitized_class}_{sanitized_subj}_{sanitized_med}_{ROOM_SALT}"
    
    st.info(f"🔴 ക്ലാസ്: **{selected_class}** | വിഷയം: **{subject}** ({selected_medium})")
    display_user = f"{st.session_state['display_name']} ({selected_medium})"
    jitsi_url = f"https://meet.jit.si/{room_id}#userInfo.displayName=\"{display_user}\""
    
    components.html(f"""
        <iframe src="{jitsi_url}" 
                style="height: 580px; width: 100%; border-radius: 12px; border: 1px solid #CBD5E1;" 
                allow="camera; microphone; fullscreen; display-capture; autoplay">
        </iframe>
    """, height=600)

# ----------------- 3. SCERT AI DOUBT SOLVER -----------------
with tab_doubt:
    st.markdown("#### 🤖 SCERT കേരള സിലബസ് AI സംശയനിവാരണം")
    user_q = st.text_area("നിങ്ങളുടെ സംശയം ചോദിക്കുക:")
    if st.button("ഉത്തരം നൽകുക"):
        if client and user_q.strip():
            with st.spinner("അധ്യാപകൻ പരിശോധിക്കുന്നു..."):
                prompt = f"""
                നീ GVHSS KUNIYA സ്കൂളിലെ അധ്യാപകനാണ്.
                ക്ലാസ്: {selected_class}, വിഷയം: {subject}, മീഡിയം: {selected_medium}.
                ഈ ചോദ്യത്തിന് കേരള സിലബസ് രീതിയിൽ വ്യക്തമായ സ്റ്റെപ്പുകളോടെ വിശദീകരണം നൽകുക: {user_q}
                """
                res = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
                st.markdown(res.text)
        elif not client:
            st.error("API Key ലഭ്യമല്ല.")

# ----------------- 4. PHOTO SOLVER -----------------
with tab_img:
    st.markdown("#### 📸 പുസ്തകത്തിലെ ചോദ്യത്തിന്റെ ഫോട്ടോ നൽകാം")
    up_img = st.file_uploader("ചിത്രം തിരഞ്ഞെടുക്കുക", type=["png", "jpg", "jpeg"])
    if up_img:
        img = Image.open(up_img)
        st.image(img, use_container_width=True)
        if st.button("പരിഹാരം കണ്ടെത്തുക"):
            if client:
                with st.spinner("ചിത്രം പരിശോധിക്കുന്നു..."):
                    res = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[f"ക്ലാസ്: {selected_class}, വിഷയം: {subject}, മീഡിയം: {selected_medium}. ഈ ചിത്രത്തിലെ ചോദ്യം കേരള സിലബസ് രീതിയിൽ സ്റ്റെപ്പ് ബൈ സ്റ്റെപ്പ് ആയി പരിഹരിച്ചു നൽകുക.", img]
                    )
                    st.markdown(res.text)
