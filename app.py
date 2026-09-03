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

# ----------------- GEMINI MODEL CONFIGURATION -----------------
GEMINI_MODEL = "gemini-2.0-flash"

# ----------------- KBC THEME STYLING -----------------
st.markdown("""
<style>
    .kbc-question-card {
        background: linear-gradient(135deg, #0b132b 0%, #1c2541 50%, #0b132b 100%);
        border: 2px solid #e5a93b;
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        box-shadow: 0 0 20px rgba(229, 169, 59, 0.35);
        margin-bottom: 25px;
    }
    .kbc-question-text {
        color: #ffffff !important;
        font-size: 1.25rem !important;
        font-weight: 700;
        line-height: 1.6;
        margin: 0;
    }
    .kbc-meta-tag {
        display: inline-block;
        background-color: rgba(229, 169, 59, 0.2);
        color: #fbd46d;
        border: 1px solid #e5a93b;
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 12px;
    }
    div[data-testid="column"] button {
        background: linear-gradient(180deg, #162447 0%, #1f4068 100%) !important;
        color: #ffffff !important;
        border: 1.5px solid #d4af37 !important;
        border-radius: 12px !important;
        padding: 14px 16px !important;
        font-size: 1.05rem !important;
        font-weight: 600 !important;
        transition: all 0.25s ease-in-out !important;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3) !important;
    }
    div[data-testid="column"] button:hover {
        background: linear-gradient(180deg, #d4af37 0%, #aa820a 100%) !important;
        color: #0b132b !important;
        border-color: #ffffff !important;
        transform: scale(1.02);
        box-shadow: 0 0 15px rgba(229, 169, 59, 0.7) !important;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- KERALA SCERT SYLLABUS & CHAPTERS -----------------
KERALA_CLASSES = [
    "Class 8", "Class 9", "Class 10 (SSLC)",
    "Plus One (+1 Science)", "Plus One (+1 Commerce)", "Plus One (+1 Humanities)",
    "Plus Two (+2 Science)", "Plus Two (+2 Commerce)", "Plus Two (+2 Humanities)"
]

SCERT_CHAPTERS = {
    ("Class 10 (SSLC)", "Mathematics"): [
        "All Chapters (എല്ലാ പാഠങ്ങളും)",
        "1. Arithmetic Sequences (സമാന്തരശ്രേണികൾ)",
        "2. Circles (വൃത്തങ്ങൾ)",
        "3. Mathematics of Chance (സാധ്യതകളുടെ ഗണിതം)",
        "4. Second Degree Equations (രണ്ടാംകൃതി സമവാക്യങ്ങൾ)",
        "5. Trigonometry (ത്രികോണമിതി)",
        "6. Coordinates (സൂചകസംഖ്യകൾ)",
        "7. Tangents (തൊടുവരകൾ)",
        "8. Solids (ഘനരൂപങ്ങൾ)",
        "9. Geometry and Algebra (ജ്യാമിതിയും ബീജഗണിതവും)",
        "10. Polynomials (ബഹുപദങ്ങൾ)",
        "11. Statistics (സ്ഥിതിവിവരക്കണക്ക്)"
    ],
    ("Class 10 (SSLC)", "Physics"): [
        "All Chapters (എല്ലാ പാഠങ്ങളും)",
        "1. Effects of Electric Current (വൈദ്യുതി പ്രവാഹത്തിന്റെ ഫലങ്ങൾ)",
        "2. Magnetic Effect of Electric Current (വൈദ്യുതപ്രവാഹത്തിന്റെ കാന്തികഫലം)",
        "3. Electromagnetic Induction (വൈദ്യുതകാന്തിക പ്രേരണ)",
        "4. Reflection of Light (പ്രകാശത്തിന്റെ പ്രതിപതനം)",
        "5. Refraction of Light (പ്രകാശത്തിന്റെ അപവർത്തനം)",
        "6. Vision and the World of Colours (കാഴ്ചയും വർണ്ണങ്ങളുടെ ലോകവും)",
        "7. Energy Management (ഊർജ്ജപരിപാലനം)"
    ],
    ("Class 10 (SSLC)", "Chemistry"): [
        "All Chapters (എല്ലാ പാഠങ്ങളും)",
        "1. Periodic Table and Electronic Configuration (പീരിയോഡിക് ടേബിളും ഇലക്ട്രോൺ വിന്യാസവും)",
        "2. Gas Laws and Mole Concept (വാതകനിയമങ്ങളും മോൾ സങ്കല്പനവും)",
        "3. Reactivity Series and Electrochemistry (പ്രവർത്തനതീവ്രതാ ശ്രേണിയും വൈദ്യുതരസതന്ത്രവും)",
        "4. Production of Metals (ലോഹനിർമ്മാണം)",
        "5. Compounds of Non-Metals (അലോഹസംയുക്തങ്ങൾ)",
        "6. Nomenclature of Organic Compounds (ഓർഗാനിക് സംയുക്തങ്ങളുടെ നാമകരണം)",
        "7. Chemical Reactions of Organic Compounds (ഓർഗാനിക് രാസപ്രവർത്തനങ്ങൾ)"
    ],
    ("Class 10 (SSLC)", "Biology"): [
        "All Chapters (എല്ലാ പാഠങ്ങളും)",
        "1. Sensations and Responses (അറിയാനും പ്രതികരിക്കാനും)",
        "2. Windows of Knowledge (അറിവിന്റെ വാതായനങ്ങൾ)",
        "3. Chemical Messages for Homeostasis (സമസ്ഥിതിക്കായുള്ള രാസസന്ദേശങ്ങൾ)",
        "4. Keeping Diseases Away (രോഗങ്ങളെ അകറ്റിനിർത്താം)",
        "5. Soldiers of Defense (പ്രതിരോധത്തിന്റെ കാവലാളുകൾ)",
        "6. Unravelling Genetic Mysteries (ജനിതക രഹസ്യങ്ങൾ തേടി)",
        "7. Genetics for Future (നാളെയുടെ ജനിതകം)",
        "8. The Paths Traversed by Life (ജീവന്റെ നാൾവഴികൾ)"
    ]
}

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

def get_chapters_for_selection(cls_name, subj_name):
    norm_subj = "Mathematics" if "ഗണിതം" in subj_name or "Math" in subj_name else \
                "Physics" if "ഭൗതിക" in subj_name or "Physic" in subj_name else \
                "Chemistry" if "രസതന്ത്രം" in subj_name or "Chemi" in subj_name else \
                "Biology" if "ജീവശാസ്ത്രം" in subj_name or "Bio" in subj_name else subj_name
    
    key = (cls_name, norm_subj)
    if key in SCERT_CHAPTERS:
        return SCERT_CHAPTERS[key]
    return ["All Chapters (എല്ലാ പാഠങ്ങളും)", "Unit 1", "Unit 2", "Unit 3", "Unit 4"]

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
            medium TEXT DEFAULT 'Malayalam Medium',
            score INTEGER DEFAULT 0
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
            chapter TEXT NOT NULL DEFAULT 'All Chapters',
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
        c.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)', 
                  ('admin', 'admin@kuniya', 'Principal / Administrator', 'admin', 'None', 'Malayalam Medium', 0))
        c.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)', 
                  ('teacher1', 'teacher123', 'Suresh Sir (Dept. of Maths)', 'teacher', 'None', 'Malayalam Medium', 0))
        c.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)', 
                  ('student1', 'student123', 'Arjun K', 'student', 'Class 10 (SSLC)', 'English Medium', 0))
        c.execute('INSERT INTO notices (notice_text) VALUES (?, ?)', 
                  ('Welcome to the official digital campus portal of GVHSS KUNIYA, Kasaragod.', '2026-09-04'))

    conn.commit()
    conn.close()

init_db()

def get_user(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT username, password, name, role, student_class, medium, score FROM users WHERE username = ?', (username,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"username": row[0], "password": row[1], "name": row[2], "role": row[3], "class": row[4], "medium": row[5], "score": row[6] or 0}
    return None

def update_user_score(username, points):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE users SET score = score + ? WHERE username = ?', (points, username))
    conn.commit()
    conn.close()

def get_top_students():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT name, student_class, score FROM users WHERE role = "student" ORDER BY score DESC LIMIT 5')
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT username, name, role, student_class, score FROM users ORDER BY role, name')
    rows = c.fetchall()
    conn.close()
    return rows

def add_user(username, password, name, role, student_class, medium):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)', (username, password, name, role, student_class, medium, 0))
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
def fetch_kbc_question(target_class, subject, chapter, medium, exclude_ids=[]):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    placeholders = ','.join('?' for _ in exclude_ids) if exclude_ids else '0'
    
    if "All Chapters" not in chapter:
        c.execute(f'''
            SELECT id, question, opt_a, opt_b, opt_c, opt_d, correct_idx, explanation 
            FROM kbc_questions 
            WHERE target_class = ? AND subject = ? AND chapter = ? AND medium = ? AND id NOT IN ({placeholders})
            ORDER BY RANDOM() LIMIT 1
        ''', [target_class, subject, chapter, medium] + list(exclude_ids))
        row = c.fetchone()
        if row:
            conn.close()
            return {"id": row[0], "question": row[1], "options": [row[2], row[3], row[4], row[5]], "correct_idx": row[6], "explanation": row[7]}
    
    c.execute(f'''
        SELECT id, question, opt_a, opt_b, opt_c, opt_d, correct_idx, explanation 
        FROM kbc_questions 
        WHERE target_class = ? AND subject = ? AND medium = ? AND id NOT IN ({placeholders})
        ORDER BY RANDOM() LIMIT 1
    ''', [target_class, subject, medium] + list(exclude_ids))
    row = c.fetchone()
    
    if not row:
        c.execute(f'''
            SELECT id, question, opt_a, opt_b, opt_c, opt_d, correct_idx, explanation 
            FROM kbc_questions 
            WHERE medium = ? AND id NOT IN ({placeholders})
            ORDER BY RANDOM() LIMIT 1
        ''', [medium] + list(exclude_ids))
        row = c.fetchone()
        
    if not row:
        c.execute('''
            SELECT id, question, opt_a, opt_b, opt_c, opt_d, correct_idx, explanation 
            FROM kbc_questions 
            WHERE medium = ? 
            ORDER BY RANDOM() LIMIT 1
        ''', (medium,))
        row = c.fetchone()
        
    conn.close()
    if row:
        return {"id": row[0], "question": row[1], "options": [row[2], row[3], row[4], row[5]], "correct_idx": row[6], "explanation": row[7]}
    return None

def count_kbc_questions(target_class, subject, chapter, medium):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if "All Chapters" not in chapter:
        c.execute('SELECT COUNT(*) FROM kbc_questions WHERE target_class = ? AND subject = ? AND chapter = ? AND medium = ?', (target_class, subject, chapter, medium))
    else:
        c.execute('SELECT COUNT(*) FROM kbc_questions WHERE target_class = ? AND subject = ? AND medium = ?', (target_class, subject, medium))
    cnt = c.fetchone()[0]
    conn.close()
    return cnt

def insert_batch_kbc_questions(target_class, subject, chapter, medium, q_list):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for q in q_list:
        try:
            c.execute('''
                INSERT INTO kbc_questions (target_class, subject, chapter, medium, question, opt_a, opt_b, opt_c, opt_d, correct_idx, explanation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (target_class, subject, chapter, medium, q["q"], q["options"][0], q["options"][1], q["options"][2], q["options"][3], q["answer_idx"], q["exp"]))
        except Exception:
            continue
    conn.commit()
    conn.close()

def generate_ai_kbc_batch(client, target_class, subject, chapter, medium, count=10):
    lang_inst = "Generate questions and options strictly in standard Malayalam based on SCERT Kerala textbooks." if "Malayalam" in medium else "Generate questions and options in English based on SCERT Kerala textbooks."
    prompt = f"""
    Create {count} multiple-choice quiz questions based strictly on the official Kerala SCERT curriculum for GVHSS KUNIYA.
    Class: {target_class}
    Subject: {subject}
    Textbook Chapter / Unit: {chapter}
    Medium: {medium}
    {lang_inst}
    
    Return ONLY a valid JSON array of objects without markdown formatting:
    [
      {{
        "q": "Question text?",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "answer_idx": 0,
        "exp": "Textbook reference and step-by-step reason"
      }}
    ]
    """
    try:
        res = client.models.generate_content(
            model=GEMINI_MODEL,
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

if "seen_question_ids" not in st.session_state:
    st.session_state["seen_question_ids"] = set()
if "kbc_q" not in st.session_state:
    st.session_state["kbc_q"] = None
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
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        st.header("🎓 GVHSS KUNIYA")
        st.caption("Govt Vocational Higher Secondary School, Kuniya • Kasaragod")
        st.write("---")
        with st.form("login_form"):
            st.subheader("Portal Sign In")
            uid = st.text_input("User ID", placeholder="admin / student1").strip().lower()
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
current_user = get_user(st.session_state["username"])
live_score = current_user["score"] if current_user else 0

c_head1, c_head2 = st.columns([3, 1])
with c_head1:
    st.title("🎓 GVHSS KUNIYA")
    st.caption("Govt Vocational Higher Secondary School, Kuniya • Kasaragod, Kerala")
with c_head2:
    st.info(f"**{st.session_state['display_name']}**\n\nRole: `{st.session_state['role'].upper()}` | 🏆 **{live_score:,} Pts**")

# Notice
notice = get_latest_notice()
st.warning(f"📢 **School Notice:** {notice}")
st.write("---")

# Sidebar
st.sidebar.title("My Profile")
st.sidebar.write(f"**Name:** {st.session_state['display_name']}")
st.sidebar.write(f"**Role:** {st.session_state['role'].capitalize()}")
st.sidebar.write(f"**Total Score:** 🏆 {live_score:,} Pts")

# Medium Selector
medium_idx = 0 if st.session_state["medium"] == "Malayalam Medium" else 1
selected_medium = st.sidebar.radio(
    "Instruction Medium", 
    ["Malayalam Medium", "English Medium"], 
    index=medium_idx
)
if selected_medium != st.session_state["medium"]:
    st.session_state["medium"] = selected_medium
    st.session_state["kbc_q"] = None
    st.session_state["seen_question_ids"] = set()
    st.rerun()

if st.sidebar.button("Logout", use_container_width=True):
    st.session_state["authenticated"] = False
    st.session_state["username"] = None
    st.rerun()

# Class, Subject & Chapter Selection
col_sel1, col_sel2, col_sel3 = st.columns([1.2, 1.2, 1.6])
with col_sel1:
    if st.session_state["role"] in ["admin", "teacher"]:
        selected_class = st.selectbox("Academic Class", KERALA_CLASSES)
    else:
        selected_class = st.session_state.get("student_class", "Class 10 (SSLC)")
        st.write(f"Enrolled Class: **{selected_class}**")
with col_sel2:
    available_subjects = get_subjects(selected_class, selected_medium)
    subject = st.selectbox("Subject", available_subjects)

with col_sel3:
    chapter_list = get_chapters_for_selection(selected_class, subject)
    selected_chapter = st.selectbox("Textbook Chapter / Unit", chapter_list)

# AI Setup
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

# ----------------- ADMIN CONSOLE -----------------
if st.session_state["role"] == "admin":
    with st.expander("⚙️ Admin Management Console", expanded=False):
        adm1, adm2, adm3 = st.tabs(["➕ Add User / Admin", "👥 Registered Users & Scores", "📢 Update Notice"])
        with adm1:
            with st.form("add_user_form"):
                c_u1, c_u2 = st.columns(2)
                with c_u1:
                    new_uid = st.text_input("User ID", placeholder="e.g. teacher_maths").strip().lower()
                    new_pwd = st.text_input("Password", type="password", placeholder="Password").strip()
                with c_u2:
                    new_name = st.text_input("Full Name", placeholder="e.g. Suresh Kumar").strip()
                    new_role = st.selectbox("Role Permission", ["student", "teacher", "admin"])
                
                c_u3, c_u4 = st.columns(2)
                with c_u3:
                    new_cls = st.selectbox("Class (For Students)", ["None"] + KERALA_CLASSES)
                with c_u4:
                    new_med = st.selectbox("Medium", ["Malayalam Medium", "English Medium"])
                
                if st.form_submit_button("Save Account", use_container_width=True):
                    if new_uid and new_pwd and new_name:
                        ok, msg = add_user(new_uid, new_pwd, new_name, new_role, new_cls, new_med)
                        if ok:
                            st.success(msg)
                        else:
                            st.error(msg)
                    else:
                        st.warning("Please fill in all fields.")
        with adm2:
            all_u = get_all_users()
            for u in all_u:
                c1, c2, c3, c4, c5 = st.columns([2, 2.5, 1.5, 2, 1])
                c1.write(f"**{u[0]}**")
                c2.write(f"{u[1]}")
                c3.write(f"`{u[2].upper()}`")
                c4.write(f"🏆 {u[4]} Pts")
                if u[0] != "admin" and c5.button("Delete", key=f"del_{u[0]}"):
                    delete_user(u[0])
                    st.rerun()
        with adm3:
            unote = st.text_area("Notice Text:", value=notice)
            if st.button("Publish Notice"):
                set_latest_notice(unote)
                st.success("Notice updated!")
                st.rerun()

# ----------------- MAIN TABS -----------------
tab_kbc, tab_live, tab_doubt, tab_img = st.tabs([
    "🏆 KBC Challenge", 
    "🎥 Live Classroom", 
    "🤖 AI Study Mentor", 
    "📸 Question Lens"
])

# 1. KBC QUIZ
with tab_kbc:
    q_count = count_kbc_questions(selected_class, subject, selected_chapter, selected_medium)
    
    col_sc1, col_sc2, col_sc3 = st.columns(3)
    with col_sc1:
        st.metric("🏆 Total Score", f"{live_score:,} Pts")
    with col_sc2:
        st.metric("🔥 Current Streak", f"{st.session_state['kbc_streak']}")
    with col_sc3:
        st.metric("📚 Questions in Chapter", f"{q_count} Available")

    if st.session_state["kbc_q"] is None:
        q_data = fetch_kbc_question(selected_class, subject, selected_chapter, selected_medium, st.session_state["seen_question_ids"])
        if q_data:
            st.session_state["kbc_q"] = q_data
            st.session_state["seen_question_ids"].add(q_data["id"])
            st.session_state["kbc_answered"] = False
            st.session_state["kbc_fifty_used"] = False
            st.session_state["kbc_disabled_options"] = []
            st.session_state["kbc_selected_idx"] = None

    if client:
        col_gen1, col_gen2 = st.columns([3, 1])
        with col_gen2:
            if st.button(f"⚡ Add 10 Chapter Questions", use_container_width=True):
                with st.spinner(f"Fetching SCERT questions for {selected_chapter}..."):
                    batch = generate_ai_kbc_batch(client, selected_class, subject, selected_chapter, selected_medium, count=10)
                    if batch:
                        insert_batch_kbc_questions(selected_class, subject, selected_chapter, selected_medium, batch)
                        st.success("Added textbook questions successfully!")
                        st.rerun()

    curr = st.session_state["kbc_q"]
    if curr:
        q_html = f"""
        <div class="kbc-question-card">
            <span class="kbc-meta-tag">📖 {selected_class} • {subject} | {selected_chapter}</span>
            <p class="kbc-question-text">{curr['question']}</p>
        </div>
        """
        st.markdown(q_html, unsafe_allow_html=True)
        
        if not st.session_state["kbc_fifty_used"] and not st.session_state["kbc_answered"]:
            if st.button("⚖️ 50:50 Lifeline (Use Once)"):
                correct = curr["correct_idx"]
                wrong_indices = [i for i in range(4) if i != correct]
                st.session_state["kbc_disabled_options"] = random.sample(wrong_indices, 2)
                st.session_state["kbc_fifty_used"] = True
                st.rerun()

        labels = ["A", "B", "C", "D"]
        c1, c2 = st.columns(2)
        
        for idx in range(4):
            col = c1 if idx % 2 == 0 else c2
            opt_text = curr["options"][idx]
            is_disabled = idx in st.session_state["kbc_disabled_options"]
            btn_label = f"♦  [{labels[idx]}]   {opt_text}" if not is_disabled else f"♦  [{labels[idx]}]   ─────────"
            
            if col.button(btn_label, key=f"kbc_opt_{idx}", disabled=is_disabled or st.session_state["kbc_answered"], use_container_width=True):
                st.session_state["kbc_answered"] = True
                st.session_state["kbc_selected_idx"] = idx
                if idx == curr["correct_idx"]:
                    update_user_score(st.session_state["username"], 1000)
                    st.session_state["kbc_streak"] += 1
                else:
                    st.session_state["kbc_streak"] = 0
                st.rerun()

        if st.session_state["kbc_answered"]:
            sel = st.session_state["kbc_selected_idx"]
            corr = curr["correct_idx"]
            if sel == corr:
                st.balloons()
                st.success(f"🎉 **Correct Answer! (+1,000 Points Added)**\n\n💡 **SCERT Textbook Solution:** {curr['explanation']}")
            else:
                st.error(f"❌ **Incorrect!** Correct Answer: **[{labels[corr]}] {curr['options'][corr]}**\n\n💡 **SCERT Textbook Solution:** {curr['explanation']}")
            
            if st.button("👉 Next Question (അടുത്ത ചോദ്യം)", use_container_width=True):
                next_q = fetch_kbc_question(selected_class, subject, selected_chapter, selected_medium, st.session_state["seen_question_ids"])
                st.session_state["kbc_q"] = next_q
                if next_q:
                    st.session_state["seen_question_ids"].add(next_q["id"])
                st.session_state["kbc_answered"] = False
                st.session_state["kbc_fifty_used"] = False
                st.session_state["kbc_disabled_options"] = []
                st.session_state["kbc_selected_idx"] = None
                st.rerun()

    st.write("---")
    st.subheader("🏅 School Top Achievers (Leaderboard)")
    leaders = get_top_students()
    if leaders:
        for idx, l in enumerate(leaders, 1):
            st.write(f"**#{idx} {l[0]}** ({l[1]}) — 🏆 **{l[2]:,} Points**")
    else:
        st.caption("No points scored yet. Be the first to top the leaderboard!")

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
    st.subheader(f"🤖 Kerala SCERT AI Tutor ({selected_medium})")
    hint_msg = f"ഉദാ: {selected_chapter} എന്ന പാഠത്തിലെ പ്രധാന ആശയങ്ങൾ വിശദീകരിക്കാമോ?" if "Malayalam" in selected_medium else f"e.g. Explain key concepts in {selected_chapter}."
    user_q = st.text_area("Ask any textbook concept or doubt:", placeholder=hint_msg)
    if st.button("Get Explanation"):
        if client and user_q.strip():
            with st.spinner("Analyzing Kerala SCERT textbook..."):
                lang_target = "Explain strictly in clear Malayalam adhering to SCERT Malayalam textbook standards." if "Malayalam" in selected_medium else "Explain in English adhering to SCERT English medium textbook standards."
                prompt = f"""
                You are an expert Kerala SCERT teacher for GVHSS KUNIYA school.
                Class: {selected_class}
                Subject: {subject}
                Textbook Chapter: {selected_chapter}
                Instruction Medium: {selected_medium}
                Language Requirement: {lang_target}
                Question: {user_q}
                """
                try:
                    res = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
                    st.markdown(res.text)
                except Exception as e:
                    st.error(f"Error fetching response: {e}")
        elif not client:
            st.warning("Please configure GEMINI_API_KEY to enable AI Tutoring.")

# 4. QUESTION LENS
with tab_img:
    st.subheader(f"📸 Snap & Solve Textbook Questions ({selected_medium})")
    up_img = st.file_uploader("Upload question image", type=["png", "jpg", "jpeg"])
    if up_img:
        img = Image.open(up_img)
        st.image(img, use_container_width=True)
        if st.button("Solve Problem"):
            if client:
                with st.spinner("Processing image..."):
                    lang_target = "Solve in clear Malayalam." if "Malayalam" in selected_medium else "Solve in English."
                    try:
                        res = client.models.generate_content(
                            model=GEMINI_MODEL,
                            contents=[f"Class: {selected_class}, Subject: {subject}, Chapter: {selected_chapter}, Medium: {selected_medium}. {lang_target} Solve this textbook problem step-by-step.", img]
                        )
                        st.markdown(res.text)
                    except Exception as e:
                        st.error(f"Error processing image: {e}")
            else:
                st.warning("Please configure GEMINI_API_KEY.")
