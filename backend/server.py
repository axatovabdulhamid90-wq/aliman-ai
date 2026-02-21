#!/usr/bin/env python3
# ==============================================================
# Aliman AI - Backend (Flask)
# ==============================================================
# Texnologiyalar: Flask, SQLite, PyJWT, hashlib (sha256)
# Ishga tushirish: python3 server.py
# ==============================================================

import sqlite3
import hashlib
import hmac
import jwt
import json
import os
import time
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, send_file

# -------------------------------------------------------
# Konfiguratsiya
# -------------------------------------------------------
SECRET_KEY = "aliman-ai-secret-2024-uzbekistan"
JWT_EXPIRE_HOURS = 24
DB_PATH = os.path.join(os.path.dirname(__file__), "aliman.db")
FRONTEND_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_PATH)
app.config['JSON_AS_ASCII'] = False  # O'zbek harflar uchun

# -------------------------------------------------------
# CORS (Frontend bilan ishlash uchun)
# -------------------------------------------------------
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    return response

@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    return jsonify({}), 200

# -------------------------------------------------------
# Ma'lumotlar bazasi
# -------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Jadvallarni yaratish"""
    conn = get_db()
    c = conn.cursor()
    
    # Foydalanuvchilar
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    
    # Kunlik rejalar
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_text TEXT NOT NULL,
            date TEXT DEFAULT (date('now')),
            completed INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Fokus sessiyalari
    c.execute("""
        CREATE TABLE IF NOT EXISTS focus_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            started_at TEXT DEFAULT (datetime('now')),
            ended_at TEXT,
            planned_minutes INTEGER DEFAULT 25,
            actual_minutes INTEGER DEFAULT 0,
            exit_reason TEXT,
            exit_type TEXT DEFAULT 'completed',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Chat tarixi
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Ma'lumotlar bazasi tayyor:", DB_PATH)

# -------------------------------------------------------
# Parol va Token funksiyalari
# -------------------------------------------------------
def hash_password(password: str) -> str:
    """SHA-256 bilan parolni hashlash (salt bilan)"""
    salt = "aliman_salt_2024"
    return hashlib.sha256(f"{salt}{password}{salt}".encode()).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    return hash_password(plain) == hashed

def create_token(user_id: int, username: str) -> str:
    """JWT token yaratish"""
    payload = {
        "sub": user_id,
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def decode_token(token: str) -> dict:
    """Token ni tekshirish va decode qilish"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"], options={"verify_exp": False})
        return payload
    except Exception:
        return None

# -------------------------------------------------------
# Auth decorator
# -------------------------------------------------------
def require_auth(f):
    """Token talab qiluvchi endpointlar uchun decorator"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return jsonify({"detail": "Avtorizatsiya talab etiladi"}), 401
        
        token = auth.replace('Bearer ', '')
        payload = decode_token(token)
        
        if not payload:
            return jsonify({"detail": "Token yaroqsiz yoki muddati o'tgan"}), 401
        
        request.user = {"id": payload["sub"], "username": payload["username"]}
        return f(*args, **kwargs)
    return decorated

# -------------------------------------------------------
# AI Mantiq (Kalit so'z tahlili)
# -------------------------------------------------------
def ai_analyze_exit(reason: str) -> dict:
    """Fokusdan chiqish sababini tahlil qilish"""
    r = reason.lower()
    
    distractions = ["zerik", "bezdim", "zavq", "instagram", "youtube", "tiktok",
                    "telegram", "o'yin", "game", "film", "video", "kino", "shunchaki",
                    "ko'ngil", "keraksiz", "boshqa", "dam", "uxla"]
    
    valid_reasons = ["hojat", "tualet", "suv", "ovqat", "osh", "qo'ng'iroq",
                     "favqulodda", "shoshilinch", "zarur", "muhim", "ota", "ona",
                     "bosh og'riq", "xasta", "kasal", "dori", "tez yordam"]
    
    is_distraction = any(w in r for w in distractions)
    is_valid = any(w in r for w in valid_reasons)
    
    if is_distraction:
        return {
            "type": "distracted",
            "response": (
                f'⚠️ "{reason}" — bu chalg\'itish!\n\n'
                "Eslab qo'y: har safar fokusni yo'qotganingda, maqsadingga erishish "
                "qiyinlashadi. Ulug' insonlar ham zerikadi, lekin ular davom etadi!\n\n"
                "💪 Yana 10 daqiqa tur. Faqat 10 daqiqa! Keyin ko'rasan — engib o'tasan."
            )
        }
    elif is_valid:
        return {
            "type": "valid",
            "response": (
                "✅ Tushunarliq sabab.\n\n"
                "Tez hal qilib, qaytib kel. Fokusingni yo'qotma — "
                "qaytganingda davom ettirishni unutma!"
            )
        }
    else:
        return {
            "type": "unknown",
            "response": (
                f'🤔 "{reason}" — baribir, endi fokusga qaytish vaqti!\n\n'
                "Maqsadingni esla va davom et. 💡 Maslahat: telefon/ijtimoiy "
                "tarmoqlarni boshqa xonaga qo'y — ko'zdan uzoq, ko'ngildan uzoq!"
            )
        }

def ai_daily_question() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "🌅 Xayrli tong! Bugun nima qilmoqchisan? Rejangni yoz va fokuslanib boshla."
    elif hour < 17:
        return "☀️ Tushdan keyin ham davom et! Bugun qanday natijaga erishmoqchisan?"
    else:
        return "🌙 Kechqi vaqt — eng samarali vaqtlardan biri! Bugun nima qilmoqchisan?"

def ai_chat_response(message: str, context: str, uname: str) -> str:
    m = message.lower()
    
    if context == "focus":
        if any(w in m for w in ["chiq", "to'xtat", "bor", "kerak", "ko'r"]):
            return ("🔒 Fokus rejimida ekansiz!\n\n"
                    "Agar haqiqatan zarur bo'lsa — chiq. Lekin shunchaki zerikayotgan "
                    "bo'lsang — dosh ber! 5 daqiqa davom ettir, keyin qaror qil. 💪")
        return f"Fokusda davom et, {uname}! 🎯\nHozir eng muhim narsa — oldingdagi vazifa."
    
    if any(w in m for w in ["salom", "assalom", "hi"]):
        return f"Salom, {uname}! 👋 Bugun nima qilmoqchisan? Birgalikda rejalashtirамиз!"
    
    if any(w in m for w in ["zerik", "bezdim", "qiyin", "charchad"]):
        return ("Tushunaman, ba'zida qiyin bo'ladi. 🤗\n\n"
                "Lekin zerikish — bu o'sish chegarasida turganingizning belgisi! "
                "Har bir buyuk ish boshida zerikarli ko'rinadi.\n\n"
                "💡 Vazifangni 5 daqiqalik bo'laklarga bo'l va boshlа. "
                "Ko'pincha boshlash eng qiyin qism!")
    
    if any(w in m for w in ["reja", "plan", "bugun", "nima qil"]):
        return (f"Keling rejalashtirамиз! 📋\n\nBugun uchun 3 ta asosiy maqsad yoz:\n"
                "1. Eng muhim vazifa nima?\n2. Ikkinchi muhim vazifa?\n3. Uchinchi?\n\n"
                "Rejangni 'Reja' bo'limiga yoz!")
    
    if any(w in m for w in ["yordam", "help", "nima"]):
        return ("Men seni fokus bo'lishga yordam beraman! 🎯\n\n"
                "• Bugungi rejani tuzishga yordam\n"
                "• Fokus sessiyasini boshqarish\n"
                "• Chalg'ituvchi vaqtlarni nazorat qilish\n"
                "• Kun yakuni tahlil\n\nNima haqida gaplashamiz?")
    
    return (f"Tushundim, {uname}. 💪\n\n"
            "Fokusda qolish uchun doim qo'llab-quvvatlayman! "
            "Biror savol yoki muammo bo'lsa, bemalol so'ra.")

def ai_end_of_day(user_id: int) -> str:
    conn = get_db()
    c = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    
    c.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN exit_type='distracted' THEN 1 ELSE 0 END) as dist,
               COALESCE(SUM(actual_minutes), 0) as mins
        FROM focus_sessions WHERE user_id=? AND date(started_at)=?
    """, (user_id, today))
    s = dict(c.fetchone())
    
    c.execute("SELECT plan_text, completed FROM daily_plans WHERE user_id=? AND date=?",
              (user_id, today))
    plans = c.fetchall()
    conn.close()
    
    total = s['total'] or 0
    dist = s['dist'] or 0
    mins = s['mins'] or 0
    completed_plans = sum(1 for p in plans if p['completed'])
    
    result = f"📊 Bugungi tahlil:\n\n"
    result += f"⏱️  Fokus vaqti: {mins} daqiqa ({total} sessiya)\n"
    result += f"⚠️  Chalg'igan holatlar: {dist} marta\n"
    
    if plans:
        result += f"✅  Bajarilgan rejalar: {completed_plans}/{len(plans)}\n"
    
    result += "\n"
    if dist == 0 and mins >= 60:
        result += "🏆 Ajoyib kun! Bugun a'lo fokuslandingiz!"
    elif dist == 0 and mins > 0:
        result += "👍 Yaxshi boshlash! Ertaga yanada ko'proq fokus vaqti qo'shing."
    elif dist > 3:
        result += "💪 Ertaga yaxshiroq bo'ladi. Telefon/ijtimoiy tarmoqlarni o'chiring!"
    elif mins == 0:
        result += "📅 Bugun fokus sessiyasi bo'lmadi. Ertaga boshlang — birinchi qadam eng muhimi!"
    else:
        result += "📈 Yaxshi kun o'tdi. Ertaga yanada yaxshiroq bo'lasiz!"
    
    return result

# -------------------------------------------------------
# API Endpointlar
# -------------------------------------------------------

# === AUTH ===

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    uname = (data.get('username') or '').strip()
    pwd = data.get('password') or ''
    
    if len(uname) < 3:
        return jsonify({"detail": "Username kamida 3 ta belgi bo'lishi kerak"}), 400
    if len(pwd) < 6:
        return jsonify({"detail": "Parol kamida 6 ta belgi bo'lishi kerak"}), 400
    
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                  (uname, hash_password(pwd)))
        conn.commit()
        uid = c.lastrowid
        token = create_token(uid, uname)
        return jsonify({"token": token, "username": uname, "message": "Muvaffaqiyatli ro'yxatdan o'tdingiz!"})
    except sqlite3.IntegrityError:
        return jsonify({"detail": "Bu username allaqachon band"}), 400
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    uname = (data.get('username') or '').strip()
    pwd = data.get('password') or ''
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (uname,))
    user = c.fetchone()
    conn.close()
    
    if not user or not verify_password(pwd, user['password_hash']):
        return jsonify({"detail": "Username yoki parol noto'g'ri"}), 401
    
    token = create_token(user['id'], user['username'])
    return jsonify({"token": token, "username": user['username'], "message": "Xush kelibsiz!"})

# === DASHBOARD ===

@app.route('/api/dashboard', methods=['GET'])
@require_auth
def dashboard():
    uid = request.user['id']
    today = datetime.now().strftime('%Y-%m-%d')
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT * FROM daily_plans WHERE user_id=? AND date=? ORDER BY id DESC",
              (uid, today))
    plans = [dict(p) for p in c.fetchall()]
    
    c.execute("""
        SELECT COUNT(*) as sessions,
               COALESCE(SUM(actual_minutes), 0) as total_minutes,
               COALESCE(SUM(CASE WHEN exit_type='distracted' THEN 1 ELSE 0 END), 0) as distractions
        FROM focus_sessions WHERE user_id=? AND date(started_at)=?
    """, (uid, today))
    stats = dict(c.fetchone())
    conn.close()
    
    return jsonify({
        "username": request.user['username'],
        "ai_question": ai_daily_question(),
        "plans": plans,
        "stats": stats
    })

# === REJALAR ===

@app.route('/api/plans', methods=['POST'])
@require_auth
def create_plan():
    data = request.get_json()
    text = (data.get('plan_text') or '').strip()
    if not text:
        return jsonify({"detail": "Reja matni bo'sh bo'lmasin"}), 400
    
    today = datetime.now().strftime('%Y-%m-%d')
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO daily_plans (user_id, plan_text, date) VALUES (?, ?, ?)",
              (request.user['id'], text, today))
    conn.commit()
    pid = c.lastrowid
    conn.close()
    
    return jsonify({"id": pid, "plan_text": text, "message": "Reja qo'shildi!"})

@app.route('/api/plans/<int:plan_id>/complete', methods=['PUT'])
@require_auth
def complete_plan(plan_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE daily_plans SET completed=1 WHERE id=? AND user_id=?",
              (plan_id, request.user['id']))
    conn.commit()
    conn.close()
    return jsonify({"message": "Barakalla! Reja bajarildi ✅"})

# === FOKUS ===

@app.route('/api/focus/start', methods=['POST'])
@require_auth
def focus_start():
    data = request.get_json()
    minutes = int(data.get('planned_minutes', 25))
    
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO focus_sessions (user_id, planned_minutes, started_at) VALUES (?, ?, ?)",
              (request.user['id'], minutes, datetime.now().isoformat()))
    conn.commit()
    sid = c.lastrowid
    conn.close()
    
    return jsonify({
        "session_id": sid,
        "message": f"Fokus boshlandi! {minutes} daqiqa.",
        "tips": "📵 Telefon/ijtimoiy tarmoqlarni o'chiring!"
    })

@app.route('/api/focus/end', methods=['POST'])
@require_auth
def focus_end():
    data = request.get_json()
    sid = data.get('session_id')
    reason = data.get('exit_reason')
    etype = data.get('exit_type', 'completed')
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM focus_sessions WHERE id=? AND user_id=?",
              (sid, request.user['id']))
    session = c.fetchone()
    
    if not session:
        conn.close()
        return jsonify({"detail": "Sessiya topilmadi"}), 404
    
    started = datetime.fromisoformat(session['started_at'])
    actual = int((datetime.now() - started).total_seconds() / 60)
    
    c.execute("""
        UPDATE focus_sessions 
        SET ended_at=?, actual_minutes=?, exit_reason=?, exit_type=?
        WHERE id=?
    """, (datetime.now().isoformat(), actual, reason, etype, sid))
    conn.commit()
    conn.close()
    
    ai_resp = None
    if reason and etype == 'distracted':
        ai_resp = ai_analyze_exit(reason)['response']
    
    return jsonify({
        "actual_minutes": actual,
        "ai_response": ai_resp,
        "message": "Sessiya tugadi" if etype == 'completed' else "Sessiya to'xtatildi"
    })

@app.route('/api/focus/analyze-exit', methods=['GET'])
@require_auth
def analyze_exit():
    reason = request.args.get('reason', '')
    return jsonify(ai_analyze_exit(reason))

# === CHAT ===

@app.route('/api/chat', methods=['POST'])
@require_auth
def chat():
    data = request.get_json()
    message = (data.get('message') or '').strip()
    context = data.get('context', 'dashboard')
    uid = request.user['id']
    uname = request.user['username']
    
    if not message:
        return jsonify({"detail": "Xabar bo'sh"}), 400
    
    reply = ai_chat_response(message, context, uname)
    
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'user', ?)", (uid, message))
    c.execute("INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'assistant', ?)", (uid, reply))
    conn.commit()
    conn.close()
    
    return jsonify({"reply": reply})

@app.route('/api/chat/history', methods=['GET'])
@require_auth
def chat_history():
    uid = request.user['id']
    limit = int(request.args.get('limit', 20))
    
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT role, content, created_at FROM chat_messages
        WHERE user_id=? ORDER BY created_at DESC LIMIT ?
    """, (uid, limit))
    messages = [dict(m) for m in reversed(c.fetchall())]
    conn.close()
    
    return jsonify({"messages": messages})

# === KUN YAKUNI ===

@app.route('/api/review', methods=['GET'])
@require_auth
def review():
    analysis = ai_end_of_day(request.user['id'])
    return jsonify({"analysis": analysis})

# === FRONTEND SERVE ===

@app.route('/')
def index():
    return send_file(os.path.join(FRONTEND_PATH, 'index.html'))

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(FRONTEND_PATH, filename)

# -------------------------------------------------------
# Ishga tushirish
# -------------------------------------------------------
if __name__ == '__main__':
    print("=" * 50)
    print("🎯 ALIMAN AI serveri ishga tushmoqda...")
    print("=" * 50)
    init_db()
    print("🌐 Manzil: http://localhost:8000")
    print("📚 API: http://localhost:8000/api/")
    print("=" * 50)
    app.run(host='0.0.0.0', port=8000, debug=False)
