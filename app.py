import os
import json
import random
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from google import genai

app = FastAPI(title="GVHSS KUNIYA Unified Engine")

DATABASE_URL = os.environ.get("DATABASE_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

PRIMARY_MODEL = "gemini-3.6-flash"
BACKUP_MODEL = "gemini-2.0-flash"

ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# ----------------- DATABASE MANAGEMENT -----------------
def get_db():
    if not DATABASE_URL:
        import sqlite3
        conn = sqlite3.connect("kuniya_persistent.db", timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def is_postgres():
    return bool(DATABASE_URL)

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    if is_postgres():
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username VARCHAR(50) PRIMARY KEY,
                password VARCHAR(100) NOT NULL,
                name VARCHAR(100) NOT NULL,
                role VARCHAR(20) NOT NULL,
                student_class VARCHAR(50) NOT NULL,
                medium VARCHAR(30) NOT NULL,
                score INT DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS notices (
                id SERIAL PRIMARY KEY,
                notice_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS questions (
                id SERIAL PRIMARY KEY,
                target_class VARCHAR(50) NOT NULL,
                subject VARCHAR(50) NOT NULL,
                medium VARCHAR(30) NOT NULL,
                level INT NOT NULL,
                question TEXT NOT NULL,
                opt_a TEXT NOT NULL,
                opt_b TEXT NOT NULL,
                opt_c TEXT NOT NULL,
                opt_d TEXT NOT NULL,
                correct_idx INT NOT NULL,
                explanation TEXT NOT NULL
            );
        """)
        c.execute("SELECT username FROM users WHERE username = 'admin';")
        if not c.fetchone():
            c.execute("INSERT INTO users VALUES ('admin', 'admin@kuniya', 'Principal / Administrator', 'admin', 'All', 'All', 0);")
            c.execute("INSERT INTO users VALUES ('teacher1', 'teacher123', 'Suresh Kumar (Maths)', 'teacher', 'Class 10 (SSLC)', 'Malayalam Medium', 0);")
            c.execute("INSERT INTO users VALUES ('student1', 'student123', 'Arjun K', 'student', 'Class 10 (SSLC)', 'English Medium', 0);")
            c.execute("INSERT INTO notices (notice_text) VALUES ('GVHSS KUNIYA Smart Campus Live with Multi-Peer Video Grid.');")
    else:
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, name TEXT, role TEXT, student_class TEXT, medium TEXT, score INT);
            CREATE TABLE IF NOT EXISTS notices (id INTEGER PRIMARY KEY AUTOINCREMENT, notice_text TEXT);
            CREATE TABLE IF NOT EXISTS questions (id INTEGER PRIMARY KEY AUTOINCREMENT, target_class TEXT, subject TEXT, medium TEXT, level INT, question TEXT, opt_a TEXT, opt_b TEXT, opt_c TEXT, opt_d TEXT, correct_idx INT, explanation TEXT);
        """)
        c.execute("SELECT username FROM users WHERE username = 'admin'")
        if not c.fetchone():
            c.execute("INSERT OR IGNORE INTO users VALUES ('admin', 'admin@kuniya', 'Principal / Administrator', 'admin', 'All', 'All', 0)")
            c.execute("INSERT OR IGNORE INTO notices (notice_text) VALUES ('GVHSS KUNIYA Portal Active.')")

    conn.commit()
    conn.close()

try:
    init_db()
except Exception as e:
    print(f"DB Init check: {e}")

# ----------------- CLEAN PLAIN TEXT FORMATTER -----------------
def clean_ai_text(text: str) -> str:
    text = text.replace("$$", "").replace("$", "")
    text = re.sub(r"\\\[(.*?)\\\]", r"\1", text)
    text = re.sub(r"\\\((.*?)\\\)", r"\1", text)
    text = re.sub(r"\\text\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\frac\{([^}]*)\}\{([^}]*)\}", r"(\1 / \2)", text)
    text = text.replace(r"\times", "×").replace(r"\div", "÷").replace(r"\dots", "...")
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
    query = "SELECT role FROM users WHERE username = %s AND password = %s" if is_postgres() else "SELECT role FROM users WHERE username = ? AND password = ?"
    c.execute(query, (u.strip().lower(), p.strip()))
    row = c.fetchone()
    if not row or row["role"] not in ["admin", "teacher"]:
        raise HTTPException(status_code=403, detail="Staff access required.")
    return row["role"]

def verify_admin(c, u, p):
    query = "SELECT role FROM users WHERE username = %s AND password = %s" if is_postgres() else "SELECT role FROM users WHERE username = ? AND password = ?"
    c.execute(query, (u.strip().lower(), p.strip()))
    row = c.fetchone()
    if not row or row["role"] != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required.")

@app.post("/api/login")
def login(req: LoginReq):
    conn = get_db()
    c = conn.cursor()
    query = "SELECT username, name, role, student_class, medium, score FROM users WHERE username = %s AND password = %s" if is_postgres() else "SELECT username, name, role, student_class, medium, score FROM users WHERE username = ? AND password = ?"
    c.execute(query, (req.username.strip().lower(), req.password.strip()))
    user = c.fetchone()
    conn.close()
    if user:
        return {"status": "ok", "user": dict(user)}
    raise HTTPException(status_code=401, detail="Invalid User ID or Password")

@app.get("/api/users")
def get_users(auth_user: str, auth_pass: str):
    conn = get_db()
    c = conn.cursor()
    verify_admin(c, auth_user, auth_pass)
    c.execute("SELECT username, name, role, student_class, medium, score FROM users ORDER BY role, name")
    users = c.fetchall()
    conn.close()
    return {"users": [dict(r) for r in users]}

@app.post("/api/users")
def add_user(req: UserAddReq):
    conn = get_db()
    c = conn.cursor()
    verify_admin(c, req.auth_user, req.auth_pass)
    try:
        query = "INSERT INTO users VALUES (%s, %s, %s, %s, %s, %s, 0)" if is_postgres() else "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, 0)"
        c.execute(query, (req.username.strip().lower(), req.password.strip(), req.name.strip(), req.role, req.student_class, req.medium))
        conn.commit()
        conn.close()
        return {"status": "ok", "message": f"User {req.username} saved permanently."}
    except Exception:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")

@app.post("/api/users/delete/{username}")
def delete_user(username: str, req: AuthActionReq):
    if username == "admin":
        raise HTTPException(status_code=400, detail="Default admin cannot be removed")
    conn = get_db()
    c = conn.cursor()
    verify_admin(c, req.auth_user, req.auth_pass)
    query = "DELETE FROM users WHERE username = %s" if is_postgres() else "DELETE FROM users WHERE username = ?"
    c.execute(query, (username,))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.get("/api/notice")
def get_notice():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT notice_text FROM notices ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    return {"notice": row["notice_text"] if row else "Welcome to GVHSS KUNIYA."}

@app.post("/api/notice")
def set_notice(req: NoticeReq):
    conn = get_db()
    c = conn.cursor()
    verify_staff(c, req.auth_user, req.auth_pass)
    query = "INSERT INTO notices (notice_text) VALUES (%s)" if is_postgres() else "INSERT INTO notices (notice_text) VALUES (?)"
    c.execute(query, (req.notice_text.strip(),))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.get("/api/question")
def get_question(target_class: str, subject: str, medium: str):
    conn = get_db()
    c = conn.cursor()
    query = "SELECT id, question, opt_a, opt_b, opt_c, opt_d, correct_idx, explanation, level FROM questions WHERE target_class = %s AND subject = %s AND medium = %s ORDER BY RANDOM() LIMIT 1" if is_postgres() else "SELECT id, question, opt_a, opt_b, opt_c, opt_d, correct_idx, explanation, level FROM questions WHERE target_class = ? AND subject = ? AND medium = ? ORDER BY RANDOM() LIMIT 1"
    c.execute(query, (target_class, subject, medium))
    row = c.fetchone()
    if not row:
        fallback_query = "SELECT id, question, opt_a, opt_b, opt_c, opt_d, correct_idx, explanation, level FROM questions WHERE medium = %s ORDER BY RANDOM() LIMIT 1" if is_postgres() else "SELECT id, question, opt_a, opt_b, opt_c, opt_d, correct_idx, explanation, level FROM questions WHERE medium = ? ORDER BY RANDOM() LIMIT 1"
        c.execute(fallback_query, (medium,))
        row = c.fetchone()
    conn.close()
    return {"question": dict(row) if row else None}

@app.post("/api/score")
def update_score(req: ScoreUpdateReq):
    conn = get_db()
    c = conn.cursor()
    query = "UPDATE users SET score = score + %s WHERE username = %s" if is_postgres() else "UPDATE users SET score = score + ? WHERE username = ?"
    c.execute(query, (req.points, req.username))
    fetch_query = "SELECT score FROM users WHERE username = %s" if is_postgres() else "SELECT score FROM users WHERE username = ?"
    c.execute(fetch_query, (req.username,))
    new_score = c.fetchone()["score"]
    conn.commit()
    conn.close()
    return {"new_score": new_score}

@app.post("/api/doubt")
def ask_doubt(req: DoubtReq):
    if not ai_client:
        return {"answer": "AI key is not configured."}
    
    prompt = f"""
    You are an expert Kerala SCERT textbook educator for GVHSS KUNIYA.
    Class: {req.student_class}
    Subject: {req.subject}
    Medium: {req.medium}

    Mandatory Output Rules:
    1. Strictly avoid LaTeX, dollar signs ($ or $$), and formatting stars (**).
    2. Write equations in standard plain text only (e.g. x10, S20, +, -, *, /, =, sqrt).
    3. If Medium is 'Malayalam Medium', reply strictly in natural Malayalam.
    4. If Medium is 'English Medium', reply in clear, concise English.

    Question: {req.query}
    """
    try:
        res = ai_client.models.generate_content(model=PRIMARY_MODEL, contents=prompt)
        return {"answer": clean_ai_text(res.text)}
    except Exception:
        try:
            res = ai_client.models.generate_content(model=BACKUP_MODEL, contents=prompt)
            return {"answer": clean_ai_text(res.text)}
        except Exception as e:
            return {"answer": f"Tutor error: {str(e)}"}

# ----------------- FRONTEND UI (PEER-TO-PEER VIDEO GRID) -----------------
@app.get("/", response_class=HTMLResponse)
def index():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GVHSS KUNIYA - Advanced Smart Campus</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <!-- PeerJS for Multi-User P2P Video Mesh -->
    <script src="https://unpkg.com/peerjs@1.5.2/dist/peerjs.min.js"></script>
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; background: #070B14; color: #F8FAFC; }
        .kbc-arena { background: radial-gradient(circle at center, #111D4A 0%, #060A17 100%); border: 2px solid #E5A93B; box-shadow: 0 0 35px rgba(229, 169, 59, 0.25); }
        .kbc-option { background: linear-gradient(180deg, #132247 0%, #0B1530 100%); border: 1.5px solid #C59B27; transition: all 0.2s; }
        .kbc-option:hover:not(:disabled) { background: linear-gradient(180deg, #E5A93B 0%, #B88214 100%); color: #070B14; transform: scale(1.01); }
        .ladder-active { background: #E5A93B !important; color: #070B14 !important; font-weight: 800; }
        .video-box video { width: 100%; height: 100%; object-fit: cover; border-radius: 1rem; }
    </style>
</head>
<body class="min-h-screen p-3 md:p-6 flex flex-col items-center">

    <!-- LOGIN PANEL -->
    <div id="auth-panel" class="w-full max-w-md bg-slate-900 border border-slate-800 p-8 rounded-3xl mt-10 shadow-2xl">
        <div class="text-center mb-6">
            <span class="text-xs bg-amber-500/20 text-amber-400 px-3 py-1 rounded-full border border-amber-500/30 font-bold uppercase tracking-wider">Official Portal</span>
            <h1 class="text-3xl font-black text-white mt-3">GVHSS KUNIYA</h1>
            <p class="text-slate-400 text-sm mt-1">Kerala SCERT • SSLC, +1, +2</p>
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

        <div class="flex space-x-2 border-b border-slate-800 pb-2">
            <button onclick="nav('kbc')" id="tb-kbc" class="px-5 py-2.5 font-bold text-sm rounded-xl bg-amber-500 text-black">🏆 KBC Arena</button>
            <button onclick="nav('live')" id="tb-live" class="px-5 py-2.5 font-bold text-sm rounded-xl text-slate-400 hover:text-white">🎥 In-App Live Classroom</button>
            <button onclick="nav('tutor')" id="tb-tutor" class="px-5 py-2.5 font-bold text-sm rounded-xl text-slate-400 hover:text-white">🤖 SCERT AI Tutor</button>
            <button onclick="nav('admin')" id="tb-admin" class="px-5 py-2.5 font-bold text-sm rounded-xl text-slate-400 hover:text-white hidden">⚙️ Control Panel</button>
        </div>

        <!-- KBC -->
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
                <button onclick="advanceKBC()" id="btn-next" class="w-full bg-amber-500 hover:bg-amber-400 text-black font-black py-3.5 rounded-2xl shadow-xl hidden">👉 Next Question</button>
            </div>

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

        <!-- VIEW 2: MULTI-USER REAL-TIME VIDEO CLASSROOM (PERMANENT & UNLIMITED) -->
        <div id="view-live" class="hidden flex-col space-y-4">
            <div class="flex flex-wrap justify-between items-center bg-slate-900 border border-slate-800 p-4 rounded-2xl gap-3">
                <div>
                    <h3 id="live-header" class="text-lg font-black text-emerald-400">Classroom Live Broadcaster</h3>
                    <p class="text-xs text-slate-400">Multi-Peer Video Mesh • Continuous Session • Direct browser access</p>
                </div>
                <div class="flex space-x-2">
                    <button onclick="startMyStream()" id="btn-stream" class="bg-emerald-600 hover:bg-emerald-500 text-white text-xs px-4 py-2 rounded-xl font-bold">🟢 Join / Turn On Cam</button>
                    <button onclick="toggleMyMic()" id="btn-mic" class="bg-slate-700 hover:bg-slate-600 text-white text-xs px-4 py-2 rounded-xl font-bold">🎤 Mic Muted</button>
                </div>
            </div>

            <!-- Multi-User Video Grid -->
            <div id="video-grid" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 bg-slate-950 p-4 rounded-3xl border border-slate-800 min-h-[500px]">
                <!-- Local User Card -->
                <div id="local-box" class="video-box relative bg-slate-900 rounded-2xl overflow-hidden border border-slate-800 h-64 flex items-center justify-center">
                    <video id="my-video" autoplay playsinline muted></video>
                    <div class="absolute bottom-3 left-3 bg-slate-950/80 px-3 py-1 rounded-lg text-xs font-bold text-amber-400 border border-slate-700">
                        👨‍🏫 <span id="my-tag">My Stream (Click Join)</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- VIEW 3: AI TUTOR -->
        <div id="view-tutor" class="hidden bg-slate-900 border border-slate-800 p-6 rounded-3xl space-y-4">
            <h3 class="text-lg font-bold text-amber-400">🤖 Kerala SCERT Deep Learning Tutor</h3>
            <p class="text-xs text-slate-400">Clean, human-readable textbook solutions without formula symbols or code syntax.</p>
            <textarea id="tutor-in" placeholder="Ask your textbook doubt..." class="w-full bg-slate-800 border border-slate-700 rounded-2xl p-4 text-white text-sm h-32 focus:outline-none focus:border-amber-400"></textarea>
            <button onclick="requestDoubtSolution()" class="bg-amber-500 hover:bg-amber-400 text-black font-black px-6 py-3 rounded-xl shadow-md">Solve Textbook Doubt</button>
            <div id="tutor-out" class="text-slate-200 text-sm leading-relaxed whitespace-pre-line bg-slate-800/80 p-5 rounded-2xl border border-slate-700 hidden"></div>
        </div>

        <!-- VIEW 4: ADMIN -->
        <div id="view-admin" class="hidden bg-slate-900 border border-slate-800 p-6 rounded-3xl space-y-6">
            <div class="border-b border-slate-800 pb-4">
                <h3 class="text-xl font-black text-amber-400">Control Hub (Permanent Storage)</h3>
                <p class="text-xs text-slate-400 mt-1">Users added here are saved permanently in PostgreSQL.</p>
            </div>

            <div id="admin-user-sec" class="hidden space-y-3">
                <h4 class="font-bold text-sm text-slate-300">Enroll New Student / Staff</h4>
                <form onsubmit="createUser(event)" class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <input id="new-u" type="text" placeholder="Username / ID" required class="bg-slate-800 border border-slate-700 px-3.5 py-2.5 rounded-xl text-white text-sm">
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
                    
                    <button type="submit" class="sm:col-span-3 bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 rounded-xl">Enroll Account Permanently</button>
                </form>

                <div>
                    <h4 class="font-bold text-sm text-slate-300 mt-4 mb-2">Registered Directory</h4>
                    <div id="user-table" class="space-y-2 max-h-56 overflow-y-auto pr-2"></div>
                </div>
            </div>

            <div class="border-t border-slate-800 pt-4">
                <h4 class="font-bold text-sm text-slate-300 mb-2">Publish School Notice</h4>
                <div class="flex gap-2">
                    <input id="new-notice" type="text" placeholder="Announcement text..." class="flex-1 bg-slate-800 border border-slate-700 px-4 py-2.5 rounded-xl text-white text-sm">
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

        // WebRTC Multi-Peer Mesh Logic
        let peer = null;
        let myStream = null;
        let peersConnected = {};
        let isMicOn = false;

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
            document.getElementById('live-header').innerText = `${c} • In-App Live Classroom`;
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
                    document.getElementById('my-tag').innerText = `${me.name} (Me)`;
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
            if (myStream) myStream.getTracks().forEach(t => t.stop());
            if (peer) peer.destroy();
            me = null;
            staffAuth = { u: '', p: '' };
            clearInterval(timer);
            document.getElementById('main-panel').classList.add('hidden');
            document.getElementById('main-panel').classList.remove('flex');
            document.getElementById('auth-panel').classList.remove('hidden');
        }

        async function fetchNotice() {
            const r = await fetch('/api/notice');
            const d = await r.json();
            document.getElementById('notice-display').innerText = `📢 Official Announcement: ${d.notice}`;
        }

        // --- MULTI-USER WEBRTC (CONNECT ALL STUDENTS TO TEACHER & PEERS) ---
        async function startMyStream() {
            const btn = document.getElementById('btn-stream');
            try {
                myStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
                document.getElementById('my-video').srcObject = myStream;
                btn.innerText = "🟢 Stream Active";
                btn.className = "bg-emerald-700 text-white text-xs px-4 py-2 rounded-xl font-bold cursor-default";

                // Initialize PeerJS mesh room
                const cls = document.getElementById('sel-class').value.replace(/[^a-zA-Z0-9]/g, '');
                const myPeerId = `KUNIYA_${cls}_${me.username}_${Math.floor(Math.random()*1000)}`;

                peer = new Peer(myPeerId);

                peer.on('open', (id) => {
                    console.log("Connected to WebRTC Mesh with ID: ", id);
                });

                // When someone calls us, answer with our stream
                peer.on('call', (call) => {
                    call.answer(myStream);
                    call.on('stream', (remoteStream) => {
                        addRemoteVideo(call.peer, remoteStream);
                    });
                });

            } catch (e) {
                alert("Camera/Mic Permission Required: " + e.message);
            }
        }

        function addRemoteVideo(peerId, stream) {
            if (document.getElementById(`video-${peerId}`)) return;

            const grid = document.getElementById('video-grid');
            const box = document.createElement('div');
            box.id = `video-${peerId}`;
            box.className = "video-box relative bg-slate-900 rounded-2xl overflow-hidden border border-slate-800 h-64 flex items-center justify-center";

            const vid = document.createElement('video');
            vid.srcObject = stream;
            vid.autoplay = true;
            vid.playsInline = true;

            const tag = document.createElement('div');
            tag.className = "absolute bottom-3 left-3 bg-slate-950/80 px-3 py-1 rounded-lg text-xs font-bold text-emerald-400 border border-slate-700";
            tag.innerText = `🎓 Student Stream`;

            box.appendChild(vid);
            box.appendChild(tag);
            grid.appendChild(box);
        }

        function toggleMyMic() {
            const btn = document.getElementById('btn-mic');
            if (myStream && myStream.getAudioTracks().length > 0) {
                isMicOn = !isMicOn;
                myStream.getAudioTracks()[0].enabled = isMicOn;
            }
            if (isMicOn) {
                btn.innerText = "🎙 Mic Active";
                btn.className = "bg-emerald-600 text-white text-xs px-4 py-2 rounded-xl font-bold";
            } else {
                btn.innerText = "🎤 Mic Muted";
                btn.className = "bg-slate-700 text-white text-xs px-4 py-2 rounded-xl font-bold";
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

            const r = await fetch(`/api/question?target_class=${encodeURIComponent(c)}&subject=${encodeURIComponent(s)}&medium=${encodeURIComponent(m)}`);
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
                alert("Account saved permanently!");
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

            ['kbc', 'live', 'tutor', 'admin'].forEach(i => {
                document.getElementById(`view-${i}`).classList.add('hidden');
                document.getElementById(`tb-${i}`).className = "px-5 py-2.5 font-bold text-sm rounded-xl text-slate-400 hover:text-white";
            });
            document.getElementById(`view-${tabId}`).classList.remove('hidden');
            document.getElementById(`tb-${tabId}`).className = "px-5 py-2.5 font-bold text-sm rounded-xl bg-amber-500 text-black";
        }
    </script>
</body>
</html>
    """
