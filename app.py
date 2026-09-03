import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from google import genai

app = FastAPI(title="GVHSS KUNIYA Smart Campus")

# ----------------- CONFIGURATION -----------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash"
ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# ----------------- IN-MEMORY ULTRA-FAST DATA -----------------
# സെർവർ ക്രാഷ് ആവാതെ ഞൊടിയിടയിൽ ലോഡ് ആകുന്ന ആർക്കിടെക്ചർ
USERS = {
    "admin": {"password": "admin@kuniya", "name": "Principal / Admin", "role": "admin", "score": 0},
    "student1": {"password": "student123", "name": "Arjun K", "role": "student", "score": 0}
}

NOTICES = ["Welcome to GVHSS KUNIYA High-Speed Digital Campus (SSLC, +1, +2)."]

QUESTIONS = [
    # Class 10 English Medium
    {"class": "Class 10 (SSLC)", "subject": "Mathematics", "medium": "English Medium",
     "q": "What is the common difference of the Arithmetic Progression: 4, 7, 10, 13...?",
     "options": ["2", "3", "4", "5"], "ans": 1, "exp": "Common difference d = 7 - 4 = 3."},
    {"class": "Class 10 (SSLC)", "subject": "Mathematics", "medium": "English Medium",
     "q": "What is the angle subtended by a diameter in a semicircle?",
     "options": ["45°", "60°", "90°", "180°"], "ans": 2, "exp": "Angle in a semicircle is always 90°."},
    {"class": "Class 10 (SSLC)", "subject": "Physics", "medium": "English Medium",
     "q": "Which law states that the heat produced is H = I^2 * R * t?",
     "options": ["Ohm's Law", "Joule's Law", "Faraday's Law", "Lenz's Law"], "ans": 1, "exp": "Joule's Law of Heating states H = I^2 * R * t."},
    
    # Class 10 Malayalam Medium
    {"class": "Class 10 (SSLC)", "subject": "ഗണിതം (Mathematics)", "medium": "Malayalam Medium",
     "q": "4, 7, 10, 13... എന്ന സമാന്തരശ്രേണിയുടെ പൊതുവ്യത്യാസം എത്രയാണ്?",
     "options": ["2", "3", "4", "5"], "ans": 1, "exp": "പൊതുവ്യത്യാസം d = 7 - 4 = 3 ആണ്."},
    {"class": "Class 10 (SSLC)", "subject": "ഗണിതം (Mathematics)", "medium": "Malayalam Medium",
     "q": "ഒരു അർദ്ധവൃത്തത്തിലെ കോണിന്റെ അളവ് എത്രയാണ്?",
     "options": ["45°", "60°", "90°", "180°"], "ans": 2, "exp": "അർദ്ധവൃത്തത്തിലെ കോൺ എപ്പോഴും 90 ഡിഗ്രി ആയിരിക്കും."},
    {"class": "Class 10 (SSLC)", "subject": "ഭൗതികശാസ്ത്രം (Physics)", "medium": "Malayalam Medium",
     "q": "ആകാശത്തിന് നീലനിറം കാണപ്പെടാൻ കാരണമായ പ്രകാശ പ്രതിഭാസം ഏത്?",
     "options": ["പ്രതിപതനം", "പൂർണ്ണാന്തര പ്രതിപതനം", "പ്രകാശ വിസരണം", "പ്രകീർണ്ണനം"], "ans": 2, "exp": "പ്രകാശത്തിന്റെ വിസരണം (Scattering) കാരണമാണ് നീലനിറം കാണുന്നത്."},
    
    # Plus One & Plus Two
    {"class": "Plus One (+1 Science)", "subject": "Physics", "medium": "English Medium",
     "q": "What is the dimensional formula of force?",
     "options": ["[M L T^-1]", "[M L T^-2]", "[M L^2 T^-2]", "[M L^-1 T^-2]"], "ans": 1, "exp": "Force = mass * acceleration = [M][L T^-2]."},
    {"class": "Plus Two (+2 Science)", "subject": "Physics", "medium": "English Medium",
     "q": "What is the SI unit of electric capacitance?",
     "options": ["Henry", "Farad", "Weber", "Tesla"], "ans": 1, "exp": "The SI unit of capacitance is Farad (F)."}
]

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

class AddQReq(BaseModel):
    student_class: str
    subject: str
    medium: str

# ----------------- API ROUTES -----------------
@app.post("/api/login")
def login(req: LoginReq):
    u = req.username.strip().lower()
    if u in USERS and USERS[u]["password"] == req.password.strip():
        user_info = USERS[u].copy()
        user_info["username"] = u
        return {"status": "ok", "user": user_info}
    raise HTTPException(status_code=401, detail="Invalid User ID or Password")

@app.get("/api/notice")
def get_notice():
    return {"notice": NOTICES[-1]}

@app.get("/api/question")
def get_question(target_class: str, subject: str, medium: str):
    matched = [q for q in QUESTIONS if q["class"] == target_class and q["medium"] == medium]
    if not matched:
        matched = [q for q in QUESTIONS if q["medium"] == medium]
    if matched:
        import random
        return {"question": random.choice(matched)}
    return {"question": QUESTIONS[0]}

@app.post("/api/score")
def update_score(req: ScoreReq):
    if req.username in USERS:
        USERS[req.username]["score"] += req.points
        return {"new_score": USERS[req.username]["score"]}
    return {"new_score": 0}

@app.get("/api/leaderboard")
def get_leaderboard():
    leaders = [{"name": v["name"], "score": v["score"]} for k, v in USERS.items() if v["role"] == "student"]
    leaders.sort(key=lambda x: x["score"], reverse=True)
    return {"leaders": leaders[:5]}

@app.post("/api/doubt")
def ask_doubt(req: DoubtReq):
    if not ai_client:
        return {"answer": "AI key is not configured in environment variables."}
    lang = "Malayalam strictly based on Kerala SCERT textbook." if "Malayalam" in req.medium else "English based on Kerala SCERT textbook."
    prompt = f"You are an expert Kerala SCERT teacher for GVHSS Kuniya. Class: {req.student_class}, Subject: {req.subject}. Language: {lang}. Answer clearly step-by-step: {req.query}"
    try:
        res = ai_client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        return {"answer": res.text}
    except Exception as e:
        return {"answer": f"Error from tutor: {e}"}

# ----------------- ULTRA-FAST PURE HTML/JS FRONTEND -----------------
@app.get("/", response_class=HTMLResponse)
def serve_portal():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GVHSS KUNIYA - Smart Campus</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; background: #0B0F19; color: #F8FAFC; }
        .kbc-card { background: radial-gradient(circle at center, #162447 0%, #0b132b 100%); border: 2px solid #D4AF37; box-shadow: 0 0 25px rgba(212, 175, 55, 0.25); }
        .kbc-btn { background: linear-gradient(180deg, #1f4068 0%, #162447 100%); border: 1.5px solid #d4af37; transition: all 0.2s; }
        .kbc-btn:hover:not(:disabled) { background: linear-gradient(180deg, #d4af37 0%, #aa820a 100%); color: #0b132b; transform: translateY(-2px); }
    </style>
</head>
<body class="min-h-screen p-4 md:p-6 flex flex-col items-center">

    <!-- Login Container -->
    <div id="auth-box" class="w-full max-w-md bg-slate-900 border border-slate-800 p-8 rounded-2xl mt-12 shadow-2xl">
        <div class="text-center mb-6">
            <span class="text-xs bg-amber-500/20 text-amber-400 px-3 py-1 rounded-full border border-amber-500/30 font-bold uppercase tracking-wider">Fast Learning Portal</span>
            <h1 class="text-3xl font-extrabold text-white mt-3">GVHSS KUNIYA</h1>
            <p class="text-slate-400 text-sm mt-1">High-Speed Campus (10th, +1, +2)</p>
        </div>
        <form onsubmit="handleLogin(event)" class="space-y-4">
            <div>
                <label class="text-xs font-semibold text-slate-300">User ID</label>
                <input id="uid" type="text" placeholder="admin / student1" required class="w-full mt-1 bg-slate-800 border border-slate-700 px-4 py-3 rounded-xl text-white focus:outline-none focus:border-amber-400">
            </div>
            <div>
                <label class="text-xs font-semibold text-slate-300">Password</label>
                <input id="pwd" type="password" placeholder="••••••••" required class="w-full mt-1 bg-slate-800 border border-slate-700 px-4 py-3 rounded-xl text-white focus:outline-none focus:border-amber-400">
            </div>
            <button type="submit" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 rounded-xl shadow-lg transition">Sign In to Campus</button>
            <p id="auth-err" class="text-red-400 text-sm text-center hidden"></p>
        </form>
    </div>

    <!-- Main Dashboard Container -->
    <div id="dash-box" class="w-full max-w-5xl hidden flex-col space-y-6">
        <!-- Header -->
        <header class="bg-slate-900 border border-slate-800 p-5 rounded-2xl flex flex-wrap justify-between items-center shadow-lg gap-4">
            <div>
                <h1 class="text-2xl font-black text-amber-400 tracking-tight">GVHSS KUNIYA</h1>
                <p class="text-slate-400 text-xs">Govt Vocational Higher Secondary School, Kuniya • Kasaragod</p>
            </div>
            <div class="flex items-center space-x-4">
                <div class="text-right">
                    <p id="u-name" class="font-bold text-white text-sm"></p>
                    <p id="u-score" class="text-amber-400 font-extrabold text-sm">🏆 0 Pts</p>
                </div>
                <button onclick="logout()" class="bg-red-500/20 hover:bg-red-500/30 text-red-400 text-xs px-3 py-2 rounded-lg border border-red-500/40">Logout</button>
            </div>
        </header>

        <!-- Notice -->
        <div id="notice-text" class="bg-amber-500/10 border-l-4 border-amber-500 p-4 rounded-xl text-amber-300 text-sm font-medium"></div>

        <!-- Class & Medium Selectors (10th, +1, +2 only) -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-slate-900 p-4 rounded-xl border border-slate-800">
            <div>
                <label class="text-xs text-slate-400 font-bold">Class</label>
                <select id="sel-class" onchange="changeClass()" class="w-full bg-slate-800 border border-slate-700 text-white p-2.5 rounded-lg text-sm mt-1">
                    <option value="Class 10 (SSLC)">Class 10 (SSLC)</option>
                    <option value="Plus One (+1 Science)">Plus One (+1 Science)</option>
                    <option value="Plus One (+1 Commerce)">Plus One (+1 Commerce)</option>
                    <option value="Plus Two (+2 Science)">Plus Two (+2 Science)</option>
                    <option value="Plus Two (+2 Commerce)">Plus Two (+2 Commerce)</option>
                </select>
            </div>
            <div>
                <label class="text-xs text-slate-400 font-bold">Medium</label>
                <select id="sel-med" onchange="changeClass()" class="w-full bg-slate-800 border border-slate-700 text-white p-2.5 rounded-lg text-sm mt-1">
                    <option value="Malayalam Medium">Malayalam Medium</option>
                    <option value="English Medium">English Medium</option>
                </select>
            </div>
            <div>
                <label class="text-xs text-slate-400 font-bold">Subject</label>
                <select id="sel-subj" onchange="loadQ()" class="w-full bg-slate-800 border border-slate-700 text-white p-2.5 rounded-lg text-sm mt-1"></select>
            </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="flex space-x-2 border-b border-slate-800 pb-2">
            <button onclick="tab('kbc')" id="tb-kbc" class="px-5 py-2.5 font-bold text-sm rounded-xl bg-amber-500 text-black">🏆 KBC Quiz</button>
            <button onclick="tab('live')" id="tb-live" class="px-5 py-2.5 font-bold text-sm rounded-xl text-slate-400 hover:text-white">🎥 Live Classroom</button>
            <button onclick="tab('tutor')" id="tb-tutor" class="px-5 py-2.5 font-bold text-sm rounded-xl text-slate-400 hover:text-white">🤖 AI Doubt Solver</button>
        </div>

        <!-- KBC QUIZ VIEW -->
        <div id="view-kbc" class="space-y-6">
            <div class="kbc-card p-6 md:p-8 rounded-2xl text-center">
                <span id="kbc-badge" class="text-xs font-bold text-amber-400 uppercase tracking-widest bg-amber-500/10 px-3 py-1 rounded-full border border-amber-500/30">Hot Seat</span>
                <h2 id="q-title" class="text-xl md:text-2xl font-extrabold text-white mt-4 leading-relaxed">Loading question...</h2>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <button onclick="handleAns(0)" id="op-0" class="kbc-btn p-4 rounded-xl text-left font-semibold text-white"></button>
                <button onclick="handleAns(1)" id="op-1" class="kbc-btn p-4 rounded-xl text-left font-semibold text-white"></button>
                <button onclick="handleAns(2)" id="op-2" class="kbc-btn p-4 rounded-xl text-left font-semibold text-white"></button>
                <button onclick="handleAns(3)" id="op-3" class="kbc-btn p-4 rounded-xl text-left font-semibold text-white"></button>
            </div>
            <div id="q-feedback" class="hidden p-4 rounded-xl text-sm font-semibold"></div>
            <button onclick="loadQ()" id="btn-next" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3.5 rounded-xl shadow-lg hidden">👉 Next Question (അടുത്ത ചോദ്യം)</button>
            
            <!-- Leaderboard -->
            <div class="bg-slate-900 border border-slate-800 p-5 rounded-2xl">
                <h3 class="font-bold text-amber-400 text-sm mb-3">🏅 School Leaderboard</h3>
                <div id="leaders-box" class="space-y-2 text-sm"></div>
            </div>
        </div>

        <!-- LIVE CLASS VIEW -->
        <div id="view-live" class="hidden">
            <iframe id="jitsi-frame" src="" class="w-full h-[600px] rounded-2xl border border-slate-800" allow="camera; microphone; fullscreen; display-capture"></iframe>
        </div>

        <!-- AI TUTOR VIEW -->
        <div id="view-tutor" class="hidden bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-4">
            <h3 class="text-lg font-bold text-amber-400">🤖 Kerala SCERT AI Tutor</h3>
            <textarea id="tutor-in" placeholder="Ask any question or concept doubt from your syllabus..." class="w-full bg-slate-800 border border-slate-700 rounded-xl p-4 text-white text-sm h-32 focus:outline-none focus:border-amber-400"></textarea>
            <button onclick="askDoubt()" class="bg-amber-500 hover:bg-amber-400 text-black font-bold px-6 py-3 rounded-xl">Ask Teacher</button>
            <div id="tutor-out" class="text-slate-300 text-sm leading-relaxed whitespace-pre-line bg-slate-800/60 p-4 rounded-xl border border-slate-700 hidden"></div>
        </div>
    </div>

    <script>
        let user = null;
        let q = null;

        const subjs = {
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

        function changeClass() {
            const c = document.getElementById('sel-class').value;
            const m = document.getElementById('sel-med').value;
            const list = subjs[c][m] || ["General"];
            const s = document.getElementById('sel-subj');
            s.innerHTML = '';
            list.forEach(item => {
                const opt = document.createElement('option');
                opt.value = item; opt.innerText = item; s.appendChild(opt);
            });
            loadQ();
            updateLive();
        }

        async function handleLogin(e) {
            e.preventDefault();
            const u = document.getElementById('uid').value;
            const p = document.getElementById('pwd').value;
            const err = document.getElementById('auth-err');
            try {
                const res = await fetch('/api/login', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username: u, password: p}) });
                const d = await res.json();
                if(res.ok) {
                    user = d.user;
                    document.getElementById('auth-box').classList.add('hidden');
                    document.getElementById('dash-box').classList.remove('hidden');
                    document.getElementById('dash-box').classList.add('flex');
                    document.getElementById('u-name').innerText = `${user.name} (${user.role.toUpperCase()})`;
                    document.getElementById('u-score').innerText = `🏆 ${user.score} Pts`;
                    changeClass();
                    fetch('/api/notice').then(r => r.json()).then(d => document.getElementById('notice-text').innerText = `📢 Notice: ${d.notice}`);
                    loadLeaders();
                } else {
                    err.innerText = d.detail; err.classList.remove('hidden');
                }
            } catch(e) {
                err.innerText = "Connection error."; err.classList.remove('hidden');
            }
        }

        function logout() {
            user = null;
            document.getElementById('dash-box').classList.add('hidden');
            document.getElementById('dash-box').classList.remove('flex');
            document.getElementById('auth-box').classList.remove('hidden');
        }

        async function loadQ() {
            document.getElementById('q-feedback').classList.add('hidden');
            document.getElementById('btn-next').classList.add('hidden');
            for(let i=0; i<4; i++) {
                const b = document.getElementById(`op-${i}`);
                b.disabled = false;
                b.className = "kbc-btn p-4 rounded-xl text-left font-semibold text-white";
            }
            const c = document.getElementById('sel-class').value;
            const m = document.getElementById('sel-med').value;
            const s = document.getElementById('sel-subj').value;
            document.getElementById('kbc-badge').innerText = `${c} • ${s}`;
            const res = await fetch(`/api/question?target_class=${encodeURIComponent(c)}&subject=${encodeURIComponent(s)}&medium=${encodeURIComponent(m)}`);
            const d = await res.json();
            q = d.question;
            if(q) {
                document.getElementById('q-title').innerText = q.q;
                for(let i=0; i<4; i++) {
                    document.getElementById(`op-${i}`).innerText = `[${String.fromCharCode(65+i)}]  ${q.options[i]}`;
                }
            }
        }

        async function handleAns(idx) {
            if(!q) return;
            for(let i=0; i<4; i++) document.getElementById(`op-${i}`).disabled = true;
            const fb = document.getElementById('q-feedback');
            fb.classList.remove('hidden');
            if(idx === q.ans) {
                document.getElementById(`op-${idx}`).className = "p-4 rounded-xl text-left font-semibold bg-emerald-600 border border-emerald-400 text-white";
                fb.className = "p-4 rounded-xl text-sm font-semibold bg-emerald-500/10 border border-emerald-500/30 text-emerald-400";
                fb.innerText = `🎉 Correct Answer! (+1,000 Points)\\n\\nExplanation: ${q.exp}`;
                const res = await fetch('/api/score', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username: user.username, points: 1000}) });
                const d = await res.json();
                user.score = d.new_score;
                document.getElementById('u-score').innerText = `🏆 ${user.score} Pts`;
                loadLeaders();
            } else {
                document.getElementById(`op-${idx}`).className = "p-4 rounded-xl text-left font-semibold bg-rose-600 border border-rose-400 text-white";
                document.getElementById(`op-${q.ans}`).className = "p-4 rounded-xl text-left font-semibold bg-emerald-600 border border-emerald-400 text-white";
                fb.className = "p-4 rounded-xl text-sm font-semibold bg-rose-500/10 border border-rose-500/30 text-rose-400";
                fb.innerText = `❌ Incorrect! Correct was [${String.fromCharCode(65+q.ans)}]\\n\\nExplanation: ${q.exp}`;
            }
            document.getElementById('btn-next').classList.remove('hidden');
        }

        async function loadLeaders() {
            const res = await fetch('/api/leaderboard');
            const d = await res.json();
            const b = document.getElementById('leaders-box');
            b.innerHTML = '';
            d.leaders.forEach((l, i) => {
                b.innerHTML += `<div class="flex justify-between py-1 border-b border-slate-800"><span>#${i+1} ${l.name}</span><strong class="text-amber-400">${l.score} Pts</strong></div>`;
            });
        }

        function tab(t) {
            ['kbc', 'live', 'tutor'].forEach(item => {
                document.getElementById(`view-${item}`).classList.add('hidden');
                document.getElementById(`tb-${item}`).className = "px-5 py-2.5 font-bold text-sm rounded-xl text-slate-400 hover:text-white";
            });
            document.getElementById(`view-${t}`).classList.remove('hidden');
            document.getElementById(`tb-${t}`).className = "px-5 py-2.5 font-bold text-sm rounded-xl bg-amber-500 text-black";
            if(t === 'live') updateLive();
        }

        function updateLive() {
            const c = document.getElementById('sel-class').value.replace(/[^a-zA-Z0-9]/g, '');
            const m = document.getElementById('sel-med').value.replace(/[^a-zA-Z0-9]/g, '');
            document.getElementById('jitsi-frame').src = `https://meet.jit.si/GVHSS_KUNIYA_${c}_${m}_ROOM#userInfo.displayName="${user ? user.name : 'Student'}"`;
        }

        async function askDoubt() {
            const txt = document.getElementById('tutor-in').value;
            const out = document.getElementById('tutor-out');
            if(!txt) return;
            out.innerText = "Consulting Kerala SCERT syllabus...";
            out.classList.remove('hidden');
            const res = await fetch('/api/doubt', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    student_class: document.getElementById('sel-class').value,
                    subject: document.getElementById('sel-subj').value,
                    medium: document.getElementById('sel-med').value,
                    query: txt
                })
            });
            const d = await res.json();
            out.innerText = d.answer;
        }
    </script>
</body>
</html>
    """
