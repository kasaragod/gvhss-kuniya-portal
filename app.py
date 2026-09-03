import os
import json
import random
import re
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from google import genai

app = FastAPI(title="GVHSS KUNIYA Unified Engine")

DB_FILE = "kuniya_persistent.db"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

PRIMARY_MODEL = "gemini-3.6-flash"
BACKUP_MODEL = "gemini-2.0-flash"

ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# ----------------- DATABASE -----------------
def get_db():
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                student_class TEXT NOT NULL,
                medium TEXT NOT NULL,
                score INTEGER DEFAULT 0
            );
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                notice_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS live_links (
                target_class TEXT PRIMARY KEY,
                meet_url TEXT NOT NULL,
                updated_by TEXT NOT NULL
            );
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_class TEXT NOT NULL,
                subject TEXT NOT NULL,
                medium TEXT NOT NULL,
                level INTEGER NOT NULL,
                question TEXT NOT NULL,
                opt_a TEXT NOT NULL,
                opt_b TEXT NOT NULL,
                opt_c TEXT NOT NULL,
                opt_d TEXT NOT NULL,
                correct_idx INTEGER NOT NULL,
                explanation TEXT NOT NULL
            );
        """)
        
        # Default Accounts
        c.execute("SELECT username FROM users WHERE username = 'admin'")
        if not c.fetchone():
            c.execute("INSERT OR IGNORE INTO users VALUES ('admin', 'admin@kuniya', 'Principal / Administrator', 'admin', 'All', 'All', 0)")
            c.execute("INSERT OR IGNORE INTO users VALUES ('teacher1', 'teacher123', 'Suresh Kumar (Maths)', 'teacher', 'Class 10 (SSLC)', 'Malayalam Medium', 0)")
            c.execute("INSERT OR IGNORE INTO users VALUES ('student1', 'student123', 'Arjun K', 'student', 'Class 10 (SSLC)', 'English Medium', 0)")
            c.execute("INSERT OR IGNORE INTO users VALUES ('student2', 'student123', 'Fathima N', 'student', 'Class 10 (SSLC)', 'Malayalam Medium', 0)")
            c.execute("INSERT INTO notices (notice_text) VALUES ('GVHSS KUNIYA Smart Portal is officially live for 10th, +1, and +2.')")
            
        # Default Meet Links
        classes = ["Class 10 (SSLC)", "Plus One (+1 Science)", "Plus One (+1 Commerce)", "Plus Two (+2 Science)", "Plus Two (+2 Commerce)"]
        for cls in classes:
            c.execute("INSERT OR IGNORE INTO live_links VALUES (?, ?, ?)", (cls, "https://meet.google.com/", "Admin"))
            
        # Seed questions
        c.execute("SELECT COUNT(*) FROM questions")
        if c.fetchone()[0] == 0:
            sample_qs = [
                ("Class 10 (SSLC)", "Mathematics", "English Medium", 1, "What is the common difference of the sequence: 5, 9, 13, 17...?", "2", "3", "4", "5", 2, "Common difference d = 9 - 5 = 4."),
                ("Class 10 (SSLC)", "Mathematics", "English Medium", 2, "What is the 10th term of the sequence: 3, 7, 11, 15...?", "35", "39", "41", "43", 1, "x_n = 4n - 1. x_10 = 4(10) - 1 = 39."),
                ("Class 10 (SSLC)", "Mathematics", "English Medium", 3, "What is the angle subtended in a semicircle?", "45°", "60°", "90°", "180°", 2, "Angle in a semicircle is always a right angle (90°)."),
                ("Class 10 (SSLC)", "Physics", "English Medium", 1, "What is the SI unit of electric resistance?", "Volt", "Ohm", "Ampere", "Watt", 1, "Resistance is measured in Ohms (Ω)."),
                ("Class 10 (SSLC)", "Physics", "English Medium", 2, "Which law explains heating effect: H = I^2 * R * t?", "Ohm's Law", "Joule's Law", "Faraday's Law", "Lenz's Law", 1, "Joule's Law of Heating states heat produced is H = I^2 * R * t."),
                ("Class 10 (SSLC)", "ഗണിതം (Mathematics)", "Malayalam Medium", 1, "5, 9, 13, 17... എന്ന സമാന്തരശ്രേണിയുടെ പൊതുവ്യത്യാസം എത്ര?", "2", "3", "4", "5", 2, "പൊതുവ്യത്യാസം d = 9 - 5 = 4."),
                ("Class 10 (SSLC)", "ഗണിതം (Mathematics)", "Malayalam Medium", 2, "ഒരു അർദ്ധവൃത്തത്തിലെ കോണിന്റെ അളവ് എത്ര?", "45°", "60°", "90°", "180°", 2, "അർദ്ധവൃത്തത്തിലെ കോൺ എപ്പോഴും 90 ഡിഗ്രി (മട്ടക്കോൺ) ആണ്."),
                ("Class 10 (SSLC)", "ഭൗതികശാസ്ത്രം (Physics)", "Malayalam Medium", 1, "വൈദ്യുത പ്രതിരോധത്തിന്റെ SI യൂണിറ്റ് ഏത്?", "വോൾട്ട്", "ഓം", "ആമ്പിയർ", "വാട്ട്", 1, "പ്രതിരോധം ഓം (Ohm) ൽ അളക്കുന്നു."),
                ("Class 10 (SSLC)", "ഭൗതികശാസ്ത്രം (Physics)", "Malayalam Medium", 2, "ആകാശത്തിന്റെ നീലനിറത്തിന് കാരണമായ പ്രകാശ പ്രതിഭാസം ഏത്?", "പ്രതിപതനം", "വിസരണം", "പ്രകീർണ്ണനം", "അപവർത്തനം", 1, "പ്രകാശ വിസരണം (Scattering of Light) കാരണമാണ് ആകാശം നീലയായി കാണപ്പെടുന്നത്."),
                ("Plus Two (+2 Science)", "Physics", "English Medium", 1, "What is the SI unit of electric charge?", "Coulomb", "Volt", "Ampere", "Tesla", 0, "Charge is measured in Coulombs (C)."),
                ("Plus Two (+2 Science)", "Physics", "English Medium", 2, "What is the capacitance of a capacitor storing 1 Coulomb at 1 Volt?", "1 Henry", "1 Farad", "1 Tesla", "1 Ohm", 1, "C = Q / V = 1 Farad.")
            ]
            for q in sample_qs:
                c.execute("INSERT INTO questions (target_class, subject, medium, level, question, opt_a, opt_b, opt_c, opt_d, correct_idx, explanation) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", q)
        conn.commit()

init_db()

# ----------------- CLEAN PLAIN TEXT FORMATTER -----------------
def sanitize_ai_output(text: str) -> str:
    # Strip markdown math and LaTeX delimiters
    text = text.replace("$$", "").replace("$", "")
    text = re.sub(r"\\\[(.*?)\\\]", r"\1", text)
    text = re.sub(r"\\\((.*?)\\\)", r"\1", text)
    text = re.sub(r"\\text\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\frac\{([^}]*)\}\{([^}]*)\}", r"(\1 / \2)", text)
    text = text.replace(r"\times", "×").replace(r"\div", "÷").replace(r"\dots", "...")
    # Clean unwanted asterisks and hashes
    text = text.replace("**", "").replace("###", "").replace("##", "")
    return text.strip()

# ----------------- SCHEMAS -----------------
class LoginReq(BaseModel):
    username: str
    password: str

class UserAddReq(BaseModel):
    auth_user: str
    auth_pass: str
    username: str
    password: str
    name: str
    role: str
    student_class: str
    medium: str

class AuthActionReq(BaseModel):
    auth_user: str
    auth_pass: str

class MeetUpdateReq(BaseModel):
    auth_user: str
    auth_pass: str
    target_class: str
    meet_url: str

class ScoreUpdateReq(BaseModel):
    username: str
    points: int

class DoubtReq(BaseModel):
    student_class: str
    subject: str
    medium: str
    query: str

class NoticeReq(BaseModel):
    auth_user: str
    auth_pass: str
    notice_text: str

# ----------------- API ROUTES -----------------
def verify_staff(c, u, p):
    c.execute("SELECT role FROM users WHERE username = ? AND password = ?", (u.strip().lower(), p.strip()))
    row = c.fetchone()
    if not row or row["role"] not in ["admin", "teacher"]:
        raise HTTPException(status_code=403, detail="Permission Denied: Staff access required.")
    return row["role"]

def verify_admin(c, u, p):
    c.execute("SELECT role FROM users WHERE username = ? AND password = ?", (u.strip().lower(), p.strip()))
    row = c.fetchone()
    if not row or row["role"] != "admin":
        raise HTTPException(status_code=403, detail="Permission Denied: Only Administrator can perform this action.")

@app.post("/api/login")
def login(req: LoginReq):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT username, name, role, student_class, medium, score FROM users WHERE username = ? AND password = ?", (req.username.strip().lower(), req.password.strip()))
        user = c.fetchone()
        if user:
            return {"status": "ok", "user": dict(user)}
        raise HTTPException(status_code=401, detail="Invalid User ID or Password")

@app.get("/api/users")
def get_users(auth_user: str, auth_pass: str):
    with get_db() as conn:
        c = conn.cursor()
        verify_admin(c, auth_user, auth_pass)
        c.execute("SELECT username, name, role, student_class, medium, score FROM users ORDER BY role, name")
        return {"users": [dict(r) for r in c.fetchall()]}

@app.post("/api/users")
def add_user(req: UserAddReq):
    with get_db() as conn:
        c = conn.cursor()
        verify_admin(c, req.auth_user, req.auth_pass)
        try:
            c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, 0)", 
                      (req.username.strip().lower(), req.password.strip(), req.name.strip(), req.role, req.student_class, req.medium))
            conn.commit()
            return {"status": "ok", "message": f"User {req.username} created successfully"}
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Username already exists")

@app.post("/api/users/delete/{username}")
def delete_user(username: str, req: AuthActionReq):
    if username == "admin":
        raise HTTPException(status_code=400, detail="Default admin cannot be removed")
    with get_db() as conn:
        c = conn.cursor()
        verify_admin(c, req.auth_user, req.auth_pass)
        c.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
        return {"status": "ok"}

@app.get("/api/live-link")
def get_live_link(target_class: str):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT meet_url, updated_by FROM live_links WHERE target_class = ?", (target_class,))
        row = c.fetchone()
        return {"meet_url": row["meet_url"] if row else "https://meet.google.com/", "updated_by": row["updated_by"] if row else "Admin"}

@app.post("/api/live-link")
def set_live_link(req: MeetUpdateReq):
    with get_db() as conn:
        c = conn.cursor()
        verify_staff(c, req.auth_user, req.auth_pass)
        clean_url = req.meet_url.strip()
        if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
            clean_url = "https://" + clean_url
        c.execute("INSERT OR REPLACE INTO live_links (target_class, meet_url, updated_by) VALUES (?, ?, ?)", 
                  (req.target_class, clean_url, req.auth_user))
        conn.commit()
        return {"status": "ok", "meet_url": clean_url}

@app.get("/api/notice")
def get_notice():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT notice_text FROM notices ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        return {"notice": row["notice_text"] if row else "Welcome to GVHSS KUNIYA."}

@app.post("/api/notice")
def set_notice(req: NoticeReq):
    with get_db() as conn:
        c = conn.cursor()
        verify_staff(c, req.auth_user, req.auth_pass)
        c.execute("INSERT INTO notices (notice_text) VALUES (?)", (req.notice_text.strip(),))
        conn.commit()
        return {"status": "ok"}

@app.get("/api/question")
def get_question(target_class: str, subject: str, medium: str, level: int = 1):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, question, opt_a, opt_b, opt_c, opt_d, correct_idx, explanation, level 
            FROM questions 
            WHERE target_class = ? AND subject = ? AND medium = ?
            ORDER BY RANDOM() LIMIT 1
        """, (target_class, subject, medium))
        row = c.fetchone()
        if not row:
            c.execute("SELECT id, question, opt_a, opt_b, opt_c, opt_d, correct_idx, explanation, level FROM questions WHERE target_class = ? AND medium = ? ORDER BY RANDOM() LIMIT 1", (target_class, medium))
            row = c.fetchone()
        if not row:
            c.execute("SELECT id, question, opt_a, opt_b, opt_c, opt_d, correct_idx, explanation, level FROM questions WHERE medium = ? ORDER BY RANDOM() LIMIT 1", (medium,))
            row = c.fetchone()
        if row:
            return {"question": dict(row)}
        return {"question": None}

@app.post("/api/score")
def update_score(req: ScoreUpdateReq):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET score = score + ? WHERE username = ?", (req.points, req.username))
        c.execute("SELECT score FROM users WHERE username = ?", (req.username,))
        new_score = c.fetchone()["score"]
        conn.commit()
        return {"new_score": new_score}

@app.post("/api/doubt")
def ask_doubt(req: DoubtReq):
    if not ai_client:
        return {"answer": "AI key is not configured in Koyeb environment variables."}
    
    prompt = f"""
    You are an expert Kerala SCERT textbook teacher for GVHSS KUNIYA school.
    Class: {req.student_class}
    Subject: {req.subject}
    Medium: {req.medium}

    Formatting and Syntax Rules (STRICT):
    1. Do NOT use LaTeX or any dollar signs ($ or $$).
    2. Do NOT use markdown bold stars (**) or headers (###).
    3. Write all mathematical steps, equations, and expressions using standard plain text and readable symbols only (e.g. x10, S20, +, -, *, /, =, sqrt()).
    4. If Medium is 'Malayalam Medium', explain in clear, natural Malayalam.
    5. If Medium is 'English Medium', explain in direct, student-friendly English.
    6. Provide a concise, step-by-step solution matching the Kerala SCERT textbook standard.

    Question: {req.query}
    """
    try:
        res = ai_client.models.generate_content(model=PRIMARY_MODEL, contents=prompt)
        return {"answer": sanitize_ai_output(res.text)}
    except Exception:
        try:
            res = ai_client.models.generate_content(model=BACKUP_MODEL, contents=prompt)
            return {"answer": sanitize_ai_output(res.text)}
        except Exception as e:
            return {"answer": f"Tutor engine error: {str(e)}"}

# ----------------- FRONTEND UI -----------------
@app.get("/", response_class=HTMLResponse)
def index():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GVHSS KUNIYA - Advanced KBC Learning Platform</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Gayathri:wght@700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; background: #070B14; color: #F8FAFC; }
        .kbc-arena { background: radial-gradient(circle at center, #111D4A 0%, #060A17 100%); border: 2px solid #E5A93B; box-shadow: 0 0 35px rgba(229, 169, 59, 0.25); }
        .kbc-option { background: linear-gradient(180deg, #132247 0%, #0B1530 100%); border: 1.5px solid #C59B27; transition: all 0.2s; }
        .kbc-option:hover:not(:disabled) { background: linear-gradient(180deg, #E5A93B 0%, #B88214 100%); color: #070B14; transform: scale(1.01); }
        .ladder-active { background: #E5A93B !important; color: #070B14 !important; font-weight: 800; }
    </style>
</head>
<body class="min-h-screen p-3 md:p-6 flex flex-col items-center">

    <!-- LOGIN PANEL -->
    <div id="auth-panel" class="w-full max-w-md bg-slate-900 border border-slate-800 p-8 rounded-3xl mt-10 shadow-2xl">
        <div class="text-center mb-6">
            <span class="text-xs bg-amber-500/20 text-amber-400 px-3 py-1 rounded-full border border-amber-500/30 font-bold uppercase tracking-wider">Official Portal</span>
            <h1 class="text-3xl font-black text-white mt-3">GVHSS KUNIYA</h1>
            <p class="text-slate-400 text-sm mt-1">Kerala SCERT • SSLC, +1, +2 Campus</p>
        </div>
        <form onsubmit="handleLogin(event)" class="space-y-4">
            <div>
                <label class="text-xs font-bold text-slate-300">User ID</label>
                <input id="uid" type="text" placeholder="admin / student1" required class="w-full mt-1 bg-slate-800 border border-slate-700 px-4 py-3 rounded-xl text-white focus:outline-none focus:border-amber-400">
            </div>
            <div>
                <label class="text-xs font-bold text-slate-300">Password</label>
                <input id="pwd" type="password" placeholder="••••••••" required class="w-full mt-1 bg-slate-800 border border-slate-700 px-4 py-3 rounded-xl text-white focus:outline-none focus:border-amber-400">
            </div>
            <button type="submit" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3.5 rounded-xl shadow-lg transition">Enter Portal</button>
            <p id="auth-err" class="text-rose-400 text-sm text-center hidden"></p>
        </form>
    </div>

    <!-- MAIN DASHBOARD -->
    <div id="main-panel" class="w-full max-w-6xl hidden flex-col space-y-5">
        <header class="bg-slate-900 border border-slate-800 p-5 rounded-2xl flex flex-wrap justify-between items-center shadow-lg gap-4">
            <div>
                <h1 class="text-2xl font-black text-amber-400">GVHSS KUNIYA</h1>
                <p class="text-slate-400 text-xs">Govt Vocational Higher Secondary School, Kuniya • Kasaragod</p>
            </div>
            <div class="flex items-center space-x-4">
                <div class="text-right">
                    <p id="usr-tag" class="font-bold text-white text-sm"></p>
                    <p id="score-tag" class="text-amber-400 font-black text-sm">🏆 0 Pts</p>
                </div>
                <button onclick="handleLogout()" class="bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 text-xs px-3.5 py-2 rounded-xl border border-rose-500/30">Logout</button>
            </div>
        </header>

        <div id="notice-display" class="bg-amber-500/10 border-l-4 border-amber-500 p-4 rounded-xl text-amber-200 text-sm font-medium"></div>

        <!-- Academic Selectors -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-slate-900 p-4 rounded-2xl border border-slate-800">
            <div>
                <label class="text-xs text-slate-400 font-bold uppercase">Class Level</label>
                <select id="sel-class" onchange="syncClass()" class="w-full bg-slate-800 border border-slate-700 text-white p-2.5 rounded-xl text-sm mt-1">
                    <option value="Class 10 (SSLC)">Class 10 (SSLC)</option>
                    <option value="Plus One (+1 Science)">Plus One (+1 Science)</option>
                    <option value="Plus One (+1 Commerce)">Plus One (+1 Commerce)</option>
                    <option value="Plus Two (+2 Science)">Plus Two (+2 Science)</option>
                    <option value="Plus Two (+2 Commerce)">Plus Two (+2 Commerce)</option>
                </select>
            </div>
            <div>
                <label class="text-xs text-slate-400 font-bold uppercase">Medium</label>
                <select id="sel-med" onchange="syncClass()" class="w-full bg-slate-800 border border-slate-700 text-white p-2.5 rounded-xl text-sm mt-1">
                    <option value="Malayalam Medium">Malayalam Medium</option>
                    <option value="English Medium">English Medium</option>
                </select>
            </div>
            <div>
                <label class="text-xs text-slate-400 font-bold uppercase">Subject</label>
                <select id="sel-subj" onchange="resetKBC()" class="w-full bg-slate-800 border border-slate-700 text-white p-2.5 rounded-xl text-sm mt-1"></select>
            </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="flex space-x-2 border-b border-slate-800 pb-2">
            <button onclick="nav('kbc')" id="tb-kbc" class="px-5 py-2.5 font-bold text-sm rounded-xl bg-amber-500 text-black">🏆 KBC Arena</button>
            <button onclick="nav('live')" id="tb-live" class="px-5 py-2.5 font-bold text-sm rounded-xl text-slate-400 hover:text-white">🎥 Live Classroom (Meet)</button>
            <button onclick="nav('tutor')" id="tb-tutor" class="px-5 py-2.5 font-bold text-sm rounded-xl text-slate-400 hover:text-white">🤖 SCERT AI Tutor</button>
            <button onclick="nav('admin')" id="tb-admin" class="px-5 py-2.5 font-bold text-sm rounded-xl text-slate-400 hover:text-white hidden">⚙️ Control Panel</button>
        </div>

        <!-- VIEW 1: KBC ARENA -->
        <div id="view-kbc" class="grid grid-cols-1 lg:grid-cols-4 gap-5">
            <div class="lg:col-span-3 space-y-4">
                <div class="flex justify-between items-center bg-slate-900 border border-slate-800 p-3 rounded-2xl">
                    <div class="flex items-center space-x-2">
                        <span class="text-xs font-bold text-slate-400">⏱ TIMER:</span>
                        <span id="timer-box" class="bg-rose-600 text-white font-black text-sm px-3 py-1 rounded-lg">30s</span>
                    </div>
                    <div class="flex space-x-2">
                        <button onclick="useFiftyFifty()" id="btn-5050" class="text-xs font-bold bg-indigo-600/30 border border-indigo-500 text-indigo-300 px-3 py-1.5 rounded-lg hover:bg-indigo-600/50">⚖️ 50:50</button>
                        <button onclick="useAudiencePoll()" id="btn-poll" class="text-xs font-bold bg-teal-600/30 border border-teal-500 text-teal-300 px-3 py-1.5 rounded-lg hover:bg-teal-600/50">📊 Audience Poll</button>
                    </div>
                </div>

                <div class="kbc-arena p-6 md:p-8 rounded-3xl text-center relative overflow-hidden">
                    <span id="kbc-step-tag" class="text-xs font-black text-amber-400 uppercase tracking-widest bg-amber-500/20 px-3 py-1 rounded-full border border-amber-500/40">QUESTION 1 • ₹1,000 PTS</span>
                    <h2 id="q-content" class="text-lg md:text-2xl font-bold text-white mt-4 leading-relaxed">Loading challenge...</h2>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                    <button onclick="verifyAnswer(0)" id="op-0" class="kbc-option p-4 rounded-2xl text-left font-bold text-white text-sm md:text-base"></button>
                    <button onclick="verifyAnswer(1)" id="op-1" class="kbc-option p-4 rounded-2xl text-left font-bold text-white text-sm md:text-base"></button>
                    <button onclick="verifyAnswer(2)" id="op-2" class="kbc-option p-4 rounded-2xl text-left font-bold text-white text-sm md:text-base"></button>
                    <button onclick="verifyAnswer(3)" id="op-3" class="kbc-option p-4 rounded-2xl text-left font-bold text-white text-sm md:text-base"></button>
                </div>

                <div id="ans-feedback" class="hidden p-4 rounded-2xl text-sm font-semibold"></div>
                <button onclick="advanceKBC()" id="btn-next" class="w-full bg-amber-500 hover:bg-amber-400 text-black font-black py-3.5 rounded-2xl shadow-xl hidden">👉 Next Question (അടുത്ത ചോദ്യം)</button>
            </div>

            <!-- Ladder -->
            <div class="bg-slate-900 border border-slate-800 p-4 rounded-3xl space-y-1.5 text-xs font-bold">
                <div class="text-slate-400 uppercase tracking-wider text-[11px] mb-3 text-center">Score Progress Ladder</div>
                <div id="ladder-10" class="flex justify-between p-2 rounded-lg bg-slate-800/40 text-amber-300"><span>10. Jackpot</span><span>1,00,00,000 Pts</span></div>
                <div id="ladder-9" class="flex justify-between p-2 rounded-lg bg-slate-800/40"><span>9. Expert</span><span>50,00,000 Pts</span></div>
                <div id="ladder-8" class="flex justify-between p-2 rounded-lg bg-slate-800/40"><span>8. Master</span><span>25,00,000 Pts</span></div>
                <div id="ladder-7" class="flex justify-between p-2 rounded-lg bg-slate-800/40"><span>7. Scholar</span><span>12,50,000 Pts</span></div>
                <div id="ladder-6" class="flex justify-between p-2 rounded-lg bg-slate-800/40"><span>6. Prodigy</span><span>6,40,000 Pts</span></div>
                <div id="ladder-5" class="flex justify-between p-2 rounded-lg bg-slate-800/40 text-blue-400 font-extrabold"><span>5. Safe Zone</span><span>3,20,000 Pts</span></div>
                <div id="ladder-4" class="flex justify-between p-2 rounded-lg bg-slate-800/40"><span>4. Intermediate</span><span>1,60,000 Pts</span></div>
                <div id="ladder-3" class="flex justify-between p-2 rounded-lg bg-slate-800/40"><span>3. Explorer</span><span>10,000 Pts</span></div>
                <div id="ladder-2" class="flex justify-between p-2 rounded-lg bg-slate-800/40"><span>2. Apprentice</span><span>5,000 Pts</span></div>
                <div id="ladder-1" class="flex justify-between p-2 rounded-lg ladder-active"><span>1. Starter</span><span>1,000 Pts</span></div>
            </div>
        </div>

        <!-- VIEW 2: LIVE CLASSROOM (GOOGLE MEET) -->
        <div id="view-live" class="hidden bg-slate-900 border border-slate-800 p-8 rounded-3xl text-center space-y-6">
            <div class="max-w-xl mx-auto space-y-3">
                <div class="inline-flex p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-2xl text-emerald-400">
                    <svg class="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                </div>
                <h3 id="live-class-header" class="text-2xl font-black text-white">Live Classroom</h3>
                <p id="live-class-sub" class="text-slate-400 text-sm">Join the official high-speed Google Meet session for your registered batch.</p>
                <div class="pt-4">
                    <a id="btn-join-meet" href="https://meet.google.com/" target="_blank" class="inline-block w-full sm:w-auto bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black text-lg px-8 py-4 rounded-2xl shadow-xl transition transform hover:scale-105">
                        🎥 Join Google Meet Session
                    </a>
                </div>
                <p id="meet-updated-tag" class="text-xs text-slate-500 pt-2"></p>
            </div>
        </div>

        <!-- VIEW 3: AI SCERT TUTOR -->
        <div id="view-tutor" class="hidden bg-slate-900 border border-slate-800 p-6 rounded-3xl space-y-4">
            <h3 class="text-lg font-bold text-amber-400">🤖 Kerala SCERT Deep Learning Tutor</h3>
            <p class="text-xs text-slate-400">Explanations in clean, readable text without code or formula clutter.</p>
            <textarea id="tutor-in" placeholder="Ask your textbook doubt..." class="w-full bg-slate-800 border border-slate-700 rounded-2xl p-4 text-white text-sm h-32 focus:outline-none focus:border-amber-400"></textarea>
            <button onclick="requestDoubtSolution()" class="bg-amber-500 hover:bg-amber-400 text-black font-black px-6 py-3 rounded-xl shadow-md">Solve Textbook Doubt</button>
            <div id="tutor-out" class="text-slate-200 text-sm leading-relaxed whitespace-pre-line bg-slate-800/80 p-5 rounded-2xl border border-slate-700 hidden"></div>
        </div>

        <!-- VIEW 4: ADMIN & TEACHER CONTROL PANEL -->
        <div id="view-admin" class="hidden bg-slate-900 border border-slate-800 p-6 rounded-3xl space-y-6">
            <div class="border-b border-slate-800 pb-4">
                <h3 class="text-xl font-black text-amber-400">Control Hub</h3>
                <p class="text-xs text-slate-400 mt-1">Manage Google Meet classrooms, school notices, and student registrations.</p>
            </div>

            <!-- Google Meet Link Updater -->
            <div class="bg-slate-800/40 border border-slate-800 p-4 rounded-2xl space-y-3">
                <h4 class="font-bold text-sm text-emerald-400">🎥 Update Google Meet Link for Class</h4>
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <select id="meet-cls" class="bg-slate-800 border border-slate-700 text-white p-2.5 rounded-xl text-sm">
                        <option value="Class 10 (SSLC)">Class 10 (SSLC)</option>
                        <option value="Plus One (+1 Science)">Plus One (+1 Science)</option>
                        <option value="Plus One (+1 Commerce)">Plus One (+1 Commerce)</option>
                        <option value="Plus Two (+2 Science)">Plus Two (+2 Science)</option>
                        <option value="Plus Two (+2 Commerce)">Plus Two (+2 Commerce)</option>
                    </select>
                    <input id="meet-link-input" type="text" placeholder="Paste Google Meet Link (e.g. meet.google.com/abc-defg-hij)" class="sm:col-span-2 bg-slate-800 border border-slate-700 px-3.5 py-2.5 rounded-xl text-white text-sm">
                </div>
                <button onclick="saveMeetLink()" class="bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-6 py-2.5 rounded-xl text-sm">Save Meet Link</button>
            </div>

            <!-- Add User Form (Admin Only) -->
            <div id="admin-user-sec" class="hidden space-y-3 border-t border-slate-800 pt-4">
                <h4 class="font-bold text-sm text-slate-300">Enroll New Student / Staff</h4>
                <form onsubmit="createUser(event)" class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <input id="new-u" type="text" placeholder="Username / Student ID" required class="bg-slate-800 border border-slate-700 px-3.5 py-2.5 rounded-xl text-white text-sm">
                    <input id="new-p" type="password" placeholder="Password" required class="bg-slate-800 border border-slate-700 px-3.5 py-2.5 rounded-xl text-white text-sm">
                    <input id="new-name" type="text" placeholder="Full Name" required class="bg-slate-800 border border-slate-700 px-3.5 py-2.5 rounded-xl text-white text-sm">
                    
                    <select id="new-role" class="bg-slate-800 border border-slate-700 text-white p-2.5 rounded-xl text-sm">
                        <option value="student">Student</option>
                        <option value="teacher">Teacher</option>
                        <option value="admin">Administrator</option>
                    </select>
                    
                    <select id="new-cls" class="bg-slate-800 border border-slate-700 text-white p-2.5 rounded-xl text-sm">
                        <option value="Class 10 (SSLC)">Class 10 (SSLC)</option>
                        <option value="Plus One (+1 Science)">Plus One (+1 Science)</option>
                        <option value="Plus One (+1 Commerce)">Plus One (+1 Commerce)</option>
                        <option value="Plus Two (+2 Science)">Plus Two (+2 Science)</option>
                        <option value="Plus Two (+2 Commerce)">Plus Two (+2 Commerce)</option>
                    </select>
                    
                    <select id="new-med" class="bg-slate-800 border border-slate-700 text-white p-2.5 rounded-xl text-sm">
                        <option value="English Medium">English Medium</option>
                        <option value="Malayalam Medium">Malayalam Medium</option>
                    </select>
                    
                    <button type="submit" class="sm:col-span-3 bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 rounded-xl">Enroll & Register Account</button>
                </form>

                <div>
                    <h4 class="font-bold text-sm text-slate-300 mt-4 mb-2">Enrolled Student & Staff Directory</h4>
                    <div id="user-table" class="space-y-2 max-h-56 overflow-y-auto pr-2"></div>
                </div>
            </div>

            <!-- Broadcast Notice -->
            <div class="border-t border-slate-800 pt-4">
                <h4 class="font-bold text-sm text-slate-300 mb-2">Publish Notice</h4>
                <div class="flex gap-2">
                    <input id="new-notice" type="text" placeholder="Type school announcement..." class="flex-1 bg-slate-800 border border-slate-700 px-4 py-2.5 rounded-xl text-white text-sm">
                    <button onclick="postNotice()" class="bg-amber-500 hover:bg-amber-400 text-black font-bold px-5 py-2.5 rounded-xl text-sm">Broadcast</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        let me = null;
        let staffAuth = { u: '', p: '' };
        let activeQ = null;
        let timer = null;
        let timeLeft = 30;
        let currentStep = 1;
        const prizeLadder = [1000, 5000, 10000, 160000, 320000, 640000, 1250000, 2500000, 5000000, 10000000];

        const subjectMatrix = {
            "Class 10 (SSLC)": {
                "Malayalam Medium": ["ഗണിതം (Mathematics)", "ഭൗതികശാസ്ത്രം (Physics)", "രസതന്ത്രം (Chemistry)", "ജീവശാസ്ത്രം (Biology)"],
                "English Medium": ["Mathematics", "Physics", "Chemistry", "Biology"]
            },
            "Plus One (+1 Science)": {
                "Malayalam Medium": ["Physics", "Chemistry", "Mathematics", "Biology"],
                "English Medium": ["Physics", "Chemistry", "Mathematics", "Biology"]
            },
            "Plus One (+1 Commerce)": {
                "Malayalam Medium": ["Accountancy", "Business Studies", "Economics"],
                "English Medium": ["Accountancy", "Business Studies", "Economics"]
            },
            "Plus Two (+2 Science)": {
                "Malayalam Medium": ["Physics", "Chemistry", "Mathematics", "Biology"],
                "English Medium": ["Physics", "Chemistry", "Mathematics", "Biology"]
            },
            "Plus Two (+2 Commerce)": {
                "Malayalam Medium": ["Accountancy", "Business Studies", "Economics"],
                "English Medium": ["Accountancy", "Business Studies", "Economics"]
            }
        };

        function syncClass() {
            const c = document.getElementById('sel-class').value;
            const m = document.getElementById('sel-med').value;
            const list = (subjectMatrix[c] && subjectMatrix[c][m]) ? subjectMatrix[c][m] : ["General"];
            const s = document.getElementById('sel-subj');
            s.innerHTML = '';
            list.forEach(i => {
                const opt = document.createElement('option');
                opt.value = i; opt.innerText = i; s.appendChild(opt);
            });
            resetKBC();
            updateLiveMeetButton();
        }

        async function handleLogin(e) {
            e.preventDefault();
            const u = document.getElementById('uid').value;
            const p = document.getElementById('pwd').value;
            const err = document.getElementById('auth-err');
            try {
                const r = await fetch('/api/login', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username: u, password: p}) });
                const d = await r.json();
                if(r.ok) {
                    me = d.user;
                    if(me.role === 'admin' || me.role === 'teacher') {
                        staffAuth = { u: u, p: p };
                    }

                    document.getElementById('auth-panel').classList.add('hidden');
                    document.getElementById('main-panel').classList.remove('hidden');
                    document.getElementById('main-panel').classList.add('flex');
                    document.getElementById('usr-tag').innerText = `${me.name} (${me.role.toUpperCase()})`;
                    document.getElementById('score-tag').innerText = `🏆 ${me.score.toLocaleString()} Pts`;
                    
                    if(me.role === 'student') {
                        document.getElementById('sel-class').value = me.student_class;
                        document.getElementById('sel-med').value = me.medium;
                        document.getElementById('sel-class').disabled = true;
                        document.getElementById('sel-med').disabled = true;
                        document.getElementById('tb-admin').classList.add('hidden');
                        document.getElementById('view-admin').classList.add('hidden');
                    } else {
                        document.getElementById('sel-class').disabled = false;
                        document.getElementById('sel-med').disabled = false;
                        document.getElementById('tb-admin').classList.remove('hidden');
                        if(me.role === 'admin') {
                            document.getElementById('admin-user-sec').classList.remove('hidden');
                            fetchUserDirectory();
                        } else {
                            document.getElementById('admin-user-sec').classList.add('hidden');
                        }
                    }
                    
                    syncClass();
                    fetchNotice();
                } else {
                    err.innerText = d.detail; err.classList.remove('hidden');
                }
            } catch(e) {
                err.innerText = "Network connection failed."; err.classList.remove('hidden');
            }
        }

        function handleLogout() {
            me = null;
            staffAuth = { u: '', p: '' };
            clearInterval(timer);
            document.getElementById('main-panel').classList.add('hidden');
            document.getElementById('main-panel').classList.remove('flex');
            document.getElementById('auth-panel').classList.remove('hidden');
            document.getElementById('tb-admin').classList.add('hidden');
            document.getElementById('view-admin').classList.add('hidden');
        }

        async function fetchNotice() {
            const r = await fetch('/api/notice');
            const d = await r.json();
            document.getElementById('notice-display').innerText = `📢 Official Announcement: ${d.notice}`;
        }

        async function updateLiveMeetButton() {
            const targetClass = document.getElementById('sel-class').value;
            document.getElementById('live-class-header').innerText = `${targetClass} • Live Classroom`;
            const r = await fetch(`/api/live-link?target_class=${encodeURIComponent(targetClass)}`);
            const d = await r.json();
            const btn = document.getElementById('btn-join-meet');
            btn.href = d.meet_url;
            document.getElementById('meet-updated-tag').innerText = `Current Link: ${d.meet_url} (Updated by: ${d.updated_by})`;
        }

        async function saveMeetLink() {
            const targetClass = document.getElementById('meet-cls').value;
            const meetUrl = document.getElementById('meet-link-input').value;
            if(!meetUrl) {
                alert("Please paste a valid Google Meet link.");
                return;
            }
            const r = await fetch('/api/live-link', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    auth_user: staffAuth.u,
                    auth_pass: staffAuth.p,
                    target_class: targetClass,
                    meet_url: meetUrl
                })
            });
            if(r.ok) {
                alert(`Google Meet link updated for ${targetClass}!`);
                document.getElementById('meet-link-input').value = '';
                updateLiveMeetButton();
            } else {
                const d = await r.json();
                alert(d.detail);
            }
        }

        function startClock() {
            clearInterval(timer);
            timeLeft = 30;
            document.getElementById('timer-box').innerText = `${timeLeft}s`;
            timer = setInterval(() => {
                timeLeft--;
                document.getElementById('timer-box').innerText = `${timeLeft}s`;
                if(timeLeft <= 0) {
                    clearInterval(timer);
                    lockOptionsOnTimeout();
                }
            }, 1000);
        }

        function lockOptionsOnTimeout() {
            for(let i=0; i<4; i++) document.getElementById(`op-${i}`).disabled = true;
            const fb = document.getElementById('ans-feedback');
            fb.className = "p-4 rounded-2xl text-sm font-bold bg-rose-500/20 border border-rose-500/40 text-rose-300";
            fb.innerText = `⏱ TIME OVER! You ran out of time. Correct answer was [${String.fromCharCode(65 + activeQ.correct_idx)}]`;
            fb.classList.remove('hidden');
            document.getElementById('btn-next').classList.remove('hidden');
        }

        function resetKBC() {
            currentStep = 1;
            updateLadderUI();
            fetchQuestion();
        }

        async function fetchQuestion() {
            clearInterval(timer);
            document.getElementById('ans-feedback').classList.add('hidden');
            document.getElementById('btn-next').classList.add('hidden');
            for(let i=0; i<4; i++) {
                const b = document.getElementById(`op-${i}`);
                b.disabled = false;
                b.className = "kbc-option p-4 rounded-2xl text-left font-bold text-white text-sm md:text-base";
            }
            const c = document.getElementById('sel-class').value;
            const m = document.getElementById('sel-med').value;
            const s = document.getElementById('sel-subj').value;
            const prize = prizeLadder[currentStep - 1] || 1000;
            document.getElementById('kbc-step-tag').innerText = `QUESTION ${currentStep} • ₹${prize.toLocaleString()} PTS (${m})`;

            const r = await fetch(`/api/question?target_class=${encodeURIComponent(c)}&subject=${encodeURIComponent(s)}&medium=${encodeURIComponent(m)}&level=${currentStep}`);
            const d = await r.json();
            activeQ = d.question;
            if(activeQ) {
                document.getElementById('q-content').innerText = activeQ.question;
                document.getElementById('op-0').innerText = `[A]  ${activeQ.opt_a}`;
                document.getElementById('op-1').innerText = `[B]  ${activeQ.opt_b}`;
                document.getElementById('op-2').innerText = `[C]  ${activeQ.opt_c}`;
                document.getElementById('op-3').innerText = `[D]  ${activeQ.opt_d}`;
                startClock();
            } else {
                document.getElementById('q-content').innerText = "No questions available for this selection.";
            }
        }

        async function verifyAnswer(idx) {
            clearInterval(timer);
            for(let i=0; i<4; i++) document.getElementById(`op-${i}`).disabled = true;
            const fb = document.getElementById('ans-feedback');
            fb.classList.remove('hidden');

            const prize = prizeLadder[currentStep - 1];
            if(idx === activeQ.correct_idx) {
                document.getElementById(`op-${idx}`).className = "p-4 rounded-2xl text-left font-bold bg-emerald-600 border border-emerald-400 text-white";
                fb.className = "p-4 rounded-2xl text-sm font-semibold bg-emerald-500/10 border border-emerald-500/30 text-emerald-400";
                fb.innerText = `🎉 CORRECT ANSWER! You won ₹${prize.toLocaleString()} Points!\\n\\n📘 Solution: ${activeQ.explanation}`;
                
                const r = await fetch('/api/score', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username: me.username, points: prize}) });
                const d = await r.json();
                me.score = d.new_score;
                document.getElementById('score-tag').innerText = `🏆 ${me.score.toLocaleString()} Pts`;
                
                if(currentStep < 10) currentStep++;
            } else {
                document.getElementById(`op-${idx}`).className = "p-4 rounded-2xl text-left font-bold bg-rose-600 border border-rose-400 text-white";
                document.getElementById(`op-${activeQ.correct_idx}`).className = "p-4 rounded-2xl text-left font-bold bg-emerald-600 border border-emerald-400 text-white";
                fb.className = "p-4 rounded-2xl text-sm font-semibold bg-rose-500/10 border border-rose-500/30 text-rose-400";
                fb.innerText = `❌ WRONG ANSWER! Correct answer: [${String.fromCharCode(65 + activeQ.correct_idx)}]\\n\\n📘 Solution: ${activeQ.explanation}`;
                currentStep = 1;
            }
            updateLadderUI();
            document.getElementById('btn-next').classList.remove('hidden');
        }

        function updateLadderUI() {
            for(let i=1; i<=10; i++) {
                const el = document.getElementById(`ladder-${i}`);
                if(i === currentStep) el.className = "flex justify-between p-2 rounded-lg ladder-active";
                else el.className = "flex justify-between p-2 rounded-lg bg-slate-800/40";
            }
        }

        function advanceKBC() {
            fetchQuestion();
        }

        function useFiftyFifty() {
            if(!activeQ) return;
            const correct = activeQ.correct_idx;
            const wrongs = [0,1,2,3].filter(i => i !== correct);
            const shuffled = wrongs.sort(() => 0.5 - Math.random());
            document.getElementById(`op-${shuffled[0]}`).innerText = "[ ELIMINATED ]";
            document.getElementById(`op-${shuffled[0]}`).disabled = true;
            document.getElementById(`op-${shuffled[1]}`).innerText = "[ ELIMINATED ]";
            document.getElementById(`op-${shuffled[1]}`).disabled = true;
            document.getElementById('btn-5050').disabled = true;
            document.getElementById('btn-5050').classList.add('opacity-40');
        }

        function useAudiencePoll() {
            if(!activeQ) return;
            alert(`📊 AUDIENCE POLL RESULT:\\nOption [${String.fromCharCode(65 + activeQ.correct_idx)}]: 78% Voters\\nOther Options: 22% Combined.`);
            document.getElementById('btn-poll').disabled = true;
            document.getElementById('btn-poll').classList.add('opacity-40');
        }

        async function requestDoubtSolution() {
            const q = document.getElementById('tutor-in').value;
            const out = document.getElementById('tutor-out');
            if(!q) return;
            out.innerText = "Consulting Kerala SCERT master curriculum...";
            out.classList.remove('hidden');
            const r = await fetch('/api/doubt', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    student_class: document.getElementById('sel-class').value,
                    subject: document.getElementById('sel-subj').value,
                    medium: document.getElementById('sel-med').value,
                    query: q
                })
            });
            const d = await r.json();
            out.innerText = d.answer;
        }

        async function fetchUserDirectory() {
            if(!me || me.role !== 'admin') return;
            const r = await fetch(`/api/users?auth_user=${encodeURIComponent(staffAuth.u)}&auth_pass=${encodeURIComponent(staffAuth.p)}`);
            const d = await r.json();
            if(!r.ok) return;
            const box = document.getElementById('user-table');
            box.innerHTML = '';
            d.users.forEach(u => {
                box.innerHTML += `
                    <div class="flex justify-between items-center bg-slate-800/60 p-2.5 rounded-xl text-xs">
                        <span><strong>${u.username}</strong> (${u.name}) - <span class="text-amber-400 font-bold">${u.student_class} (${u.medium})</span> [${u.role}]</span>
                        <div class="flex items-center space-x-2">
                            <span>🏆 ${u.score}</span>
                            ${u.username !== 'admin' ? `<button onclick="removeUser('${u.username}')" class="text-rose-400 hover:text-rose-300 font-bold">Delete</button>` : ''}
                        </div>
                    </div>
                `;
            });
        }

        async function createUser(e) {
            e.preventDefault();
            if(!me || me.role !== 'admin') return;
            const body = {
                auth_user: staffAuth.u,
                auth_pass: staffAuth.p,
                username: document.getElementById('new-u').value,
                password: document.getElementById('new-p').value,
                name: document.getElementById('new-name').value,
                role: document.getElementById('new-role').value,
                student_class: document.getElementById('new-cls').value,
                medium: document.getElementById('new-med').value
            };
            const r = await fetch('/api/users', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body) });
            if(r.ok) {
                alert("Account enrolled successfully!");
                e.target.reset();
                fetchUserDirectory();
            } else {
                const d = await r.json();
                alert(d.detail);
            }
        }

        async function removeUser(username) {
            if(!me || me.role !== 'admin') return;
            if(!confirm(`Delete user ${username}?`)) return;
            const r = await fetch(`/api/users/delete/${username}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ auth_user: staffAuth.u, auth_pass: staffAuth.p })
            });
            if(r.ok) fetchUserDirectory();
        }

        async function postNotice() {
            if(!me || (me.role !== 'admin' && me.role !== 'teacher')) return;
            const text = document.getElementById('new-notice').value;
            if(!text) return;
            const r = await fetch('/api/notice', { 
                method: 'POST', 
                headers: {'Content-Type': 'application/json'}, 
                body: JSON.stringify({ auth_user: staffAuth.u, auth_pass: staffAuth.p, notice_text: text }) 
            });
            if(r.ok) {
                document.getElementById('new-notice').value = '';
                fetchNotice();
                alert("Broadcast published!");
            }
        }

        function nav(tabId) {
            if(tabId === 'admin' && (!me || (me.role !== 'admin' && me.role !== 'teacher'))) {
                alert("Access Denied: Staff access only.");
                return;
            }

            ['kbc', 'tutor', 'live', 'admin'].forEach(i => {
                document.getElementById(`view-${i}`).classList.add('hidden');
                document.getElementById(`tb-${i}`).className = "px-5 py-2.5 font-bold text-sm rounded-xl text-slate-400 hover:text-white";
            });
            document.getElementById(`view-${tabId}`).classList.remove('hidden');
            document.getElementById(`tb-${tabId}`).className = "px-5 py-2.5 font-bold text-sm rounded-xl bg-amber-500 text-black";
            if(tabId === 'live') updateLiveMeetButton();
        }
    </script>
</body>
</html>
    """
