import os
import json
import random
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from google import genai

app = FastAPI(title="GVHSS KUNIYA Smart Campus")

# ----------------- CONFIGURATION & POSTGRESQL -----------------
DATABASE_URL = os.environ.get("DATABASE_URL") # Neon.tech / Supabase PostgreSQL URL
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash"

ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

def get_db():
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL environment variable is missing.")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    if not DATABASE_URL:
        return
    with get_db() as conn:
        with conn.cursor() as cur:
            # Users table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username VARCHAR(50) PRIMARY KEY,
                    password VARCHAR(100) NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    student_class VARCHAR(50),
                    medium VARCHAR(30) DEFAULT 'Malayalam Medium',
                    score INT DEFAULT 0
                );
            """)
            # Notices table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS notices (
                    id SERIAL PRIMARY KEY,
                    notice_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # KBC Questions table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS kbc_questions (
                    id SERIAL PRIMARY KEY,
                    target_class VARCHAR(50) NOT NULL,
                    subject VARCHAR(50) NOT NULL,
                    chapter VARCHAR(100) NOT NULL,
                    medium VARCHAR(30) NOT NULL,
                    question TEXT NOT NULL,
                    opt_a TEXT NOT NULL,
                    opt_b TEXT NOT NULL,
                    opt_c TEXT NOT NULL,
                    opt_d TEXT NOT NULL,
                    correct_idx INT NOT NULL,
                    explanation TEXT NOT NULL
                );
            """)
            # Default Accounts
            cur.execute("SELECT username FROM users WHERE username = 'admin';")
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO users (username, password, name, role, student_class, medium, score)
                    VALUES ('admin', 'admin@kuniya', 'Principal / Administrator', 'admin', 'None', 'Malayalam Medium', 0),
                           ('student1', 'student123', 'Arjun K', 'student', 'Class 10 (SSLC)', 'English Medium', 0);
                """)
                cur.execute("""
                    INSERT INTO notices (notice_text)
                    VALUES ('Welcome to GVHSS KUNIYA High-Speed Digital Campus (SSLC, +1, +2).');
                """)
            
            # Default Seed Questions
            cur.execute("SELECT COUNT(*) as cnt FROM kbc_questions;")
            if cur.fetchone()['cnt'] == 0:
                cur.execute("""
                    INSERT INTO kbc_questions (target_class, subject, chapter, medium, question, opt_a, opt_b, opt_c, opt_d, correct_idx, explanation)
                    VALUES 
                    ('Class 10 (SSLC)', 'Mathematics', '1. Arithmetic Sequences', 'English Medium', 
                     'What is the common difference of the AP: 4, 7, 10, 13...?', '2', '3', '4', '5', 1, 'Common difference d = 7 - 4 = 3.'),
                    ('Class 10 (SSLC)', 'Mathematics', '1. Arithmetic Sequences', 'Malayalam Medium', 
                     '4, 7, 10, 13... എന്ന സമാന്തരശ്രേണിയുടെ പൊതുവ്യത്യാസം എത്രയാണ്?', '2', '3', '4', '5', 1, 'പൊതുവ്യത്യാസം d = 7 - 4 = 3 ആണ്.'),
                    ('Class 10 (SSLC)', 'Physics', '1. Effects of Electric Current', 'English Medium', 
                     'Which law states that H = I^2 * R * t?', 'Ohm Law', 'Joule Law', 'Faraday Law', 'Lenz Law', 1, 'Joules Law of Heating governs heating effect.'),
                    ('Plus Two (+2 Science)', 'Physics', '1. Electric Charges and Fields', 'English Medium', 
                     'What is the SI unit of electric charge?', 'Ampere', 'Coulomb', 'Volt', 'Ohm', 1, 'The SI unit of electric charge is the Coulomb (C).');
                """)
        conn.commit()

try:
    init_db()
except Exception as e:
    print(f"Database init warning: {e}")

# ----------------- API SCHEMAS -----------------
class LoginReq(BaseModel):
    username: str
    password: str

class ScoreReq(BaseModel):
    username: str
    points: int

class DoubtReq(BaseModel):
    student_class: str
    subject: str
    medium: str
    query: str

# ----------------- API ENDPOINTS -----------------
@app.post("/api/login")
def login(req: LoginReq):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT username, name, role, student_class, medium, score FROM users WHERE username=%s AND password=%s", (req.username.strip().lower(), req.password.strip()))
            user = cur.fetchone()
            if user:
                return {"status": "ok", "user": user}
            raise HTTPException(status_code=401, detail="Invalid Username or Password")

@app.get("/api/notice")
def get_notice():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT notice_text FROM notices ORDER BY id DESC LIMIT 1;")
            row = cur.fetchone()
            return {"notice": row["notice_text"] if row else "Welcome to GVHSS KUNIYA."}

@app.get("/api/question")
def get_question(target_class: str, subject: str, medium: str):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, question, opt_a, opt_b, opt_c, opt_d, correct_idx, explanation 
                FROM kbc_questions 
                WHERE target_class = %s AND subject = %s AND medium = %s 
                ORDER BY RANDOM() LIMIT 1;
            """, (target_class, subject, medium))
            q = cur.fetchone()
            if not q:
                # Fallback to any question in medium
                cur.execute("SELECT id, question, opt_a, opt_b, opt_c, opt_d, correct_idx, explanation FROM kbc_questions WHERE medium = %s ORDER BY RANDOM() LIMIT 1;", (medium,))
                q = cur.fetchone()
            return {"question": q}

@app.post("/api/score")
def update_score(req: ScoreReq):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET score = score + %s WHERE username = %s RETURNING score;", (req.points, req.username))
            updated = cur.fetchone()
        conn.commit()
        return {"status": "ok", "new_score": updated["score"] if updated else 0}

@app.get("/api/leaderboard")
def leaderboard():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name, student_class, score FROM users WHERE role = 'student' ORDER BY score DESC LIMIT 5;")
            return {"leaders": cur.fetchall()}

@app.post("/api/doubt")
def solve_doubt(req: DoubtReq):
    if not ai_client:
        return {"answer": "AI service is currently offline. Please ensure GEMINI_API_KEY is configured."}
    prompt = f"""
    You are an expert Kerala SCERT teacher for GVHSS KUNIYA.
    Class: {req.student_class}
    Subject: {req.subject}
    Medium: {req.medium}
    
    Explain step-by-step strictly according to Kerala SCERT syllabus:
    {req.query}
    """
    try:
        res = ai_client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        return {"answer": res.text}
    except Exception as e:
        return {"answer": f"Error consulting tutor: {e}"}

# ----------------- ULTRA-FAST HTML FRONTEND -----------------
@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GVHSS KUNIYA - Smart Learning Portal</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #0B0F19; color: #F8FAFC; }
        .kbc-card { background: radial-gradient(circle at center, #162447 0%, #0b132b 100%); border: 2px solid #D4AF37; box-shadow: 0 0 25px rgba(212, 175, 55, 0.25); }
        .kbc-btn { background: linear-gradient(180deg, #1f4068 0%, #162447 100%); border: 1.5px solid #d4af37; transition: all 0.2s; }
        .kbc-btn:hover:not(:disabled) { background: linear-gradient(180deg, #d4af37 0%, #aa820a 100%); color: #0b132b; transform: translateY(-2px); }
    </style>
</head>
<body class="min-h-screen p-4 md:p-6 flex flex-col items-center">

    <!-- Auth View -->
    <div id="auth-view" class="w-full max-w-md bg-slate-900 border border-slate-800 p-8 rounded-2xl mt-12 shadow-2xl">
        <div class="text-center mb-6">
            <span class="text-xs bg-amber-500/20 text-amber-400 px-3 py-1 rounded-full border border-amber-500/30 font-bold uppercase">Official Portal</span>
            <h1 class="text-3xl font-extrabold text-white mt-3">GVHSS KUNIYA</h1>
            <p class="text-slate-400 text-sm mt-1">High-Speed Digital Campus (10th, +1, +2)</p>
        </div>
        <form onsubmit="handleLogin(event)" class="space-y-4">
            <div>
                <label class="text-xs font-semibold text-slate-300">User ID</label>
                <input id="login-uid" type="text" placeholder="admin / student1" required class="w-full mt-1 bg-slate-800 border border-slate-700 px-4 py-3 rounded-lg text-white focus:outline-none focus:border-amber-400">
            </div>
            <div>
                <label class="text-xs font-semibold text-slate-300">Password</label>
                <input id="login-pwd" type="password" placeholder="••••••••" required class="w-full mt-1 bg-slate-800 border border-slate-700 px-4 py-3 rounded-lg text-white focus:outline-none focus:border-amber-400">
            </div>
            <button type="submit" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 rounded-lg shadow-lg">Sign In</button>
            <p id="login-err" class="text-red-400 text-sm text-center hidden"></p>
        </form>
    </div>

    <!-- Portal Dashboard View -->
    <div id="dash-view" class="w-full max-w-5xl hidden flex-col space-y-6">
        <!-- Top Bar -->
        <header class="bg-slate-900 border border-slate-800 p-5 rounded-2xl flex flex-wrap justify-between items-center shadow-lg gap-4">
            <div>
                <h1 class="text-2xl font-black text-amber-400">GVHSS KUNIYA</h1>
                <p class="text-slate-400 text-xs">Govt Vocational Higher Secondary School, Kuniya • Kasaragod</p>
            </div>
            <div class="flex items-center space-x-4">
                <div class="text-right">
                    <p id="user-display" class="font-bold text-white text-sm"></p>
                    <p id="score-display" class="text-amber-400 font-extrabold text-sm">🏆 0 Pts</p>
                </div>
                <button onclick="handleLogout()" class="bg-red-500/20 hover:bg-red-500/30 text-red-400 text-xs px-3 py-2 rounded-lg border border-red-500/40">Logout</button>
            </div>
        </header>

        <!-- Notice -->
        <div id="notice-box" class="bg-amber-500/10 border-l-4 border-amber-500 p-4 rounded-xl text-amber-300 text-sm font-medium"></div>

        <!-- Filter Controls -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-slate-900 p-4 rounded-xl border border-slate-800">
            <div>
                <label class="text-xs text-slate-400 font-bold">Class</label>
                <select id="sel-class" onchange="updateSubjects(); loadQuestion();" class="w-full bg-slate-800 border border-slate-700 text-white p-2 rounded-lg text-sm mt-1">
                    <option value="Class 10 (SSLC)">Class 10 (SSLC)</option>
                    <option value="Plus One (+1 Science)">Plus One (+1 Science)</option>
                    <option value="Plus One (+1 Commerce)">Plus One (+1 Commerce)</option>
                    <option value="Plus Two (+2 Science)">Plus Two (+2 Science)</option>
                    <option value="Plus Two (+2 Commerce)">Plus Two (+2 Commerce)</option>
                </select>
            </div>
            <div>
                <label class="text-xs text-slate-400 font-bold">Medium</label>
                <select id="sel-med" onchange="updateSubjects(); loadQuestion();" class="w-full bg-slate-800 border border-slate-700 text-white p-2 rounded-lg text-sm mt-1">
                    <option value="Malayalam Medium">Malayalam Medium</option>
                    <option value="English Medium">English Medium</option>
                </select>
            </div>
            <div>
                <label class="text-xs text-slate-400 font-bold">Subject</label>
                <select id="sel-subj" onchange="loadQuestion();" class="w-full bg-slate-800 border border-slate-700 text-white p-2 rounded-lg text-sm mt-1"></select>
            </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="flex space-x-2 border-b border-slate-800 pb-2">
            <button onclick="switchTab('kbc')" id="tab-btn-kbc" class="px-4 py-2 font-bold text-sm rounded-lg bg-amber-500 text-black">🏆 KBC Quiz</button>
            <button onclick="switchTab('live')" id="tab-btn-live" class="px-4 py-2 font-bold text-sm rounded-lg text-slate-400 hover:text-white">🎥 Live Classroom</button>
            <button onclick="switchTab('tutor')" id="tab-btn-tutor" class="px-4 py-2 font-bold text-sm rounded-lg text-slate-400 hover:text-white">🤖 AI Tutor</button>
        </div>

        <!-- TAB 1: KBC QUIZ -->
        <div id="tab-kbc" class="space-y-6">
            <div class="kbc-card p-6 md:p-8 rounded-2xl text-center">
                <span id="kbc-tag" class="text-xs font-bold text-amber-400 uppercase tracking-widest bg-amber-500/10 px-3 py-1 rounded-full border border-amber-500/30">Hot Seat</span>
                <h2 id="kbc-q-text" class="text-xl md:text-2xl font-extrabold text-white mt-4 leading-relaxed">Loading question...</h2>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <button onclick="answer(0)" id="opt-0" class="kbc-btn p-4 rounded-xl text-left font-semibold text-white"></button>
                <button onclick="answer(1)" id="opt-1" class="kbc-btn p-4 rounded-xl text-left font-semibold text-white"></button>
                <button onclick="answer(2)" id="opt-2" class="kbc-btn p-4 rounded-xl text-left font-semibold text-white"></button>
                <button onclick="answer(3)" id="opt-3" class="kbc-btn p-4 rounded-xl text-left font-semibold text-white"></button>
            </div>
            <div id="kbc-feedback" class="hidden p-4 rounded-xl text-sm font-semibold"></div>
            <button onclick="loadQuestion()" id="btn-next" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 rounded-xl shadow-lg hidden">👉 Next Question</button>
            
            <!-- Hall of Fame -->
            <div class="bg-slate-900 border border-slate-800 p-5 rounded-2xl mt-8">
                <h3 class="font-bold text-amber-400 text-sm mb-3">🏅 School Leaderboard</h3>
                <div id="leader-list" class="space-y-2 text-sm"></div>
            </div>
        </div>

        <!-- TAB 2: LIVE CLASSROOM -->
        <div id="tab-live" class="hidden">
            <iframe id="jitsi-frame" src="" class="w-full h-[600px] rounded-2xl border border-slate-800" allow="camera; microphone; fullscreen; display-capture"></iframe>
        </div>

        <!-- TAB 3: AI TUTOR -->
        <div id="tab-tutor" class="hidden bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-4">
            <h3 class="text-lg font-bold text-amber-400">🤖 Kerala SCERT AI Doubt Solver</h3>
            <textarea id="tutor-q" placeholder="Type your syllabus doubt here..." class="w-full bg-slate-800 border border-slate-700 rounded-xl p-4 text-white text-sm h-32 focus:outline-none focus:border-amber-400"></textarea>
            <button onclick="askTutor()" class="bg-amber-500 hover:bg-amber-400 text-black font-bold px-6 py-3 rounded-xl">Ask Doubt</button>
            <div id="tutor-ans" class="text-slate-300 text-sm leading-relaxed whitespace-pre-line bg-slate-800/60 p-4 rounded-xl border border-slate-700 hidden"></div>
        </div>
    </div>

    <script>
        let currentUser = null;
        let currentQ = null;

        const subjectMap = {
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

        function updateSubjects() {
            const cls = document.getElementById('sel-class').value;
            const med = document.getElementById('sel-med').value;
            const subjs = subjectMap[cls][med] || ["General"];
            const sel = document.getElementById('sel-subj');
            sel.innerHTML = '';
            subjs.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s; opt.innerText = s; sel.appendChild(opt);
            });
            updateLiveStream();
        }

        async function handleLogin(e) {
            e.preventDefault();
            const u = document.getElementById('login-uid').value;
            const p = document.getElementById('login-pwd').value;
            const err = document.getElementById('login-err');
            try {
                const res = await fetch('/api/login', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username: u, password: p}) });
                const data = await res.json();
                if(res.ok) {
                    currentUser = data.user;
                    document.getElementById('auth-view').classList.add('hidden');
                    document.getElementById('dash-view').classList.remove('hidden');
                    document.getElementById('dash-view').classList.add('flex');
                    document.getElementById('user-display').innerText = `${currentUser.name} (${currentUser.role.toUpperCase()})`;
                    document.getElementById('score-display').innerText = `🏆 ${currentUser.score} Pts`;
                    updateSubjects();
                    loadNotice();
                    loadQuestion();
                    loadLeaders();
                } else {
                    err.innerText = data.detail; err.classList.remove('hidden');
                }
            } catch(e) {
                err.innerText = "Network Error connecting to server."; err.classList.remove('hidden');
            }
        }

        function handleLogout() {
            currentUser = null;
            document.getElementById('dash-view').classList.add('hidden');
            document.getElementById('dash-view').classList.remove('flex');
            document.getElementById('auth-view').classList.remove('hidden');
        }

        async function loadNotice() {
            const res = await fetch('/api/notice');
            const data = await res.json();
            document.getElementById('notice-box').innerText = `📢 Notice: ${data.notice}`;
        }

        async function loadQuestion() {
            document.getElementById('kbc-feedback').classList.add('hidden');
            document.getElementById('btn-next').classList.add('hidden');
            for(let i=0; i<4; i++) {
                const b = document.getElementById(`opt-${i}`);
                b.disabled = false;
                b.className = "kbc-btn p-4 rounded-xl text-left font-semibold text-white";
            }
            const cls = document.getElementById('sel-class').value;
            const med = document.getElementById('sel-med').value;
            const subj = document.getElementById('sel-subj').value;
            document.getElementById('kbc-tag').innerText = `${cls} • ${subj}`;
            const res = await fetch(`/api/question?target_class=${encodeURIComponent(cls)}&subject=${encodeURIComponent(subj)}&medium=${encodeURIComponent(med)}`);
            const data = await res.json();
            currentQ = data.question;
            if(currentQ) {
                document.getElementById('kbc-q-text').innerText = currentQ.question;
                document.getElementById('opt-0').innerText = `[A]  ${currentQ.opt_a}`;
                document.getElementById('opt-1').innerText = `[B]  ${currentQ.opt_b}`;
                document.getElementById('opt-2').innerText = `[C]  ${currentQ.opt_c}`;
                document.getElementById('opt-3').innerText = `[D]  ${currentQ.opt_d}`;
            } else {
                document.getElementById('kbc-q-text').innerText = "No questions available in this category yet.";
            }
        }

        async function answer(idx) {
            if(!currentQ) return;
            for(let i=0; i<4; i++) document.getElementById(`opt-${i}`).disabled = true;
            const fb = document.getElementById('kbc-feedback');
            fb.classList.remove('hidden');
            if(idx === currentQ.correct_idx) {
                document.getElementById(`opt-${idx}`).className = "p-4 rounded-xl text-left font-semibold bg-emerald-600 border border-emerald-400 text-white";
                fb.className = "p-4 rounded-xl text-sm font-semibold bg-emerald-500/10 border border-emerald-500/30 text-emerald-400";
                fb.innerText = `🎉 Correct Answer! (+1,000 Points)\\n\\nExplanation: ${currentQ.explanation}`;
                const res = await fetch('/api/score', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username: currentUser.username, points: 1000}) });
                const d = await res.json();
                currentUser.score = d.new_score;
                document.getElementById('score-display').innerText = `🏆 ${currentUser.score} Pts`;
                loadLeaders();
            } else {
                document.getElementById(`opt-${idx}`).className = "p-4 rounded-xl text-left font-semibold bg-rose-600 border border-rose-400 text-white";
                document.getElementById(`opt-${currentQ.correct_idx}`).className = "p-4 rounded-xl text-left font-semibold bg-emerald-600 border border-emerald-400 text-white";
                fb.className = "p-4 rounded-xl text-sm font-semibold bg-rose-500/10 border border-rose-500/30 text-rose-400";
                fb.innerText = `❌ Incorrect!\\n\\nExplanation: ${currentQ.explanation}`;
            }
            document.getElementById('btn-next').classList.remove('hidden');
        }

        async function loadLeaders() {
            const res = await fetch('/api/leaderboard');
            const data = await res.json();
            const div = document.getElementById('leader-list');
            div.innerHTML = '';
            data.leaders.forEach((l, i) => {
                div.innerHTML += `<div class="flex justify-between py-1 border-b border-slate-800"><span>#${i+1} ${l.name} (${l.student_class})</span><strong class="text-amber-400">${l.score} Pts</strong></div>`;
            });
        }

        function switchTab(t) {
            ['kbc', 'live', 'tutor'].forEach(tab => {
                document.getElementById(`tab-${tab}`).classList.add('hidden');
                document.getElementById(`tab-btn-${tab}`).className = "px-4 py-2 font-bold text-sm rounded-lg text-slate-400 hover:text-white";
            });
            document.getElementById(`tab-${t}`).classList.remove('hidden');
            document.getElementById(`tab-btn-${t}`).className = "px-4 py-2 font-bold text-sm rounded-lg bg-amber-500 text-black";
            if(t === 'live') updateLiveStream();
        }

        function updateLiveStream() {
            const cls = document.getElementById('sel-class').value.replace(/[^a-zA-Z0-9]/g, '');
            const med = document.getElementById('sel-med').value.replace(/[^a-zA-Z0-9]/g, '');
            const room = `GVHSS_KUNIYA_${cls}_${med}_ROOM`;
            document.getElementById('jitsi-frame').src = `https://meet.jit.si/${room}#userInfo.displayName="${currentUser ? currentUser.name : 'Student'}"`;
        }

        async function askTutor() {
            const q = document.getElementById('tutor-q').value;
            const ans = document.getElementById('tutor-ans');
            if(!q) return;
            ans.innerText = "Consulting teacher...";
            ans.classList.remove('hidden');
            const res = await fetch('/api/doubt', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    student_class: document.getElementById('sel-class').value,
                    subject: document.getElementById('sel-subj').value,
                    medium: document.getElementById('sel-med').value,
                    query: q
                })
            });
            const data = await res.json();
            ans.innerText = data.answer;
        }
    </script>
</body>
</html>
    """
