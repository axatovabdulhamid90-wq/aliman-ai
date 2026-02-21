# ==============================================================
# Aliman AI - Backend (FastAPI)
# ==============================================================
# Ushbu fayl barcha API endpointlarni o'z ichiga oladi.
# Texnologiyalar: FastAPI, SQLite, JWT, bcrypt
# ==============================================================

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, List
import sqlite3
import hashlib
import os
import json

# JWT uchun jose kutubxonasi
from jose import JWTError, jwt
from passlib.context import CryptContext

# -------------------------------------------------------
# Konfiguratsiya
# -------------------------------------------------------
SECRET_KEY = "aliman-ai-secret-key-2024"  # Production'da env variable'dan oling
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Parol hashlash uchun bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# FastAPI ilovasi
app = FastAPI(title="Aliman AI", version="1.0.0")

# CORS - Frontend bilan ishlash uchun
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------
# Ma'lumotlar bazasi (SQLite)
# -------------------------------------------------------
DB_PATH = "aliman.db"

def get_db():
    """SQLite ulanishini qaytaradi"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Dict ko'rinishida natija
    return conn

def init_db():
    """Jadvallarni yaratadi (birinchi ishga tushganda)"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Foydalanuvchilar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Kunlik rejalar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_text TEXT NOT NULL,
            date DATE DEFAULT (DATE('now')),
            completed INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Focus sessiyalari jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS focus_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            ended_at DATETIME,
            planned_minutes INTEGER DEFAULT 25,
            actual_minutes INTEGER DEFAULT 0,
            exit_reason TEXT,
            exit_type TEXT,  -- 'completed', 'distracted', 'other'
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Chat tarixi jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,  -- 'user' yoki 'assistant'
            content TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Ma'lumotlar bazasi tayyor")

# -------------------------------------------------------
# Pydantic modellari (So'rov/javob sxemalari)
# -------------------------------------------------------

class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class PlanRequest(BaseModel):
    plan_text: str

class FocusStartRequest(BaseModel):
    planned_minutes: int = 25

class FocusEndRequest(BaseModel):
    session_id: int
    exit_reason: Optional[str] = None
    exit_type: str = "completed"  # 'completed', 'distracted', 'other'

class ChatMessage(BaseModel):
    message: str
    context: Optional[str] = None  # 'focus', 'dashboard', 'review'

# -------------------------------------------------------
# Yordamchi funksiyalar
# -------------------------------------------------------

def hash_password(password: str) -> str:
    """Parolni bcrypt bilan hashlaydi"""
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """Parolni tekshiradi"""
    return pwd_context.verify(plain, hashed)

def create_token(user_id: int, username: str) -> str:
    """JWT token yaratadi"""
    data = {
        "sub": str(user_id),
        "username": username,
        "exp": datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    }
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str) -> dict:
    """Token orqali foydalanuvchini topadi"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        username = payload.get("username")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token yaroqsiz")
        return {"id": user_id, "username": username}
    except JWTError:
        raise HTTPException(status_code=401, detail="Token yaroqsiz yoki muddati o'tgan")

def auth_header(authorization: str = None) -> dict:
    """Authorization headeridan foydalanuvchini oladi"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Avtorizatsiya talab etiladi")
    token = authorization.replace("Bearer ", "")
    return get_current_user(token)

# -------------------------------------------------------
# AI Mantiqi (Oddiy, LLM-siz)
# -------------------------------------------------------

def ai_analyze_exit_reason(reason: str) -> dict:
    """
    Foydalanuvchi fokusdan chiqqanda sababni tahlil qiladi.
    Haqiqiy LLM o'rniga oddiy kalit so'z tahlili.
    """
    reason_lower = reason.lower()
    
    # Chalg'ituvchi sabablar
    distraction_keywords = [
        "zerik", "zeri", "bezdim", "ko'ngil", "zavq", "instagram", "youtube",
        "tiktok", "telegram", "o'yin", "game", "film", "video", "kino",
        "qiziq", "boshqa", "keraksiz", "shunchaki"
    ]
    
    # Oqlash mumkin bo'lgan sabablar
    valid_keywords = [
        "hojat", "tualet", "suv", "osh", "ovqat", "qo'ng'iroq", "telefon",
        "favqulodda", "shoshilinch", "zarur", "muhim", "ota", "ona", "yosh",
        "bosh og'riq", "xasta", "kasal"
    ]
    
    is_distraction = any(word in reason_lower for word in distraction_keywords)
    is_valid = any(word in reason_lower for word in valid_keywords)
    
    if is_distraction:
        return {
            "type": "distracted",
            "response": f"""⚠️ Tushundim. "{reason}" - bu chalg'itish.

Eslab qo'y: har safar diqqatingni yo'qotganingda, maqsadingga erishish qiyinlashadi.

💪 Mana haqiqat: Ulug' insonlar ham zerikadi, lekin ular shunga qaramay davom etadi. Zerikish - bu o'sish belgisi!

🔥 Qaytib fokusga kir. Yana {15} daqiqa tur. Faqat {15} daqiqa!"""
        }
    elif is_valid:
        return {
            "type": "valid",
            "response": f"""✅ Yaxshi, tushunarliq sabab.

Tez hal qilib, qaytib kel. Fokusing hali tugamadi!

⏱️ Qaytganingda fokusni davom ettirgin."""
        }
    else:
        return {
            "type": "unknown",
            "response": f"""🤔 "{reason}" - bu haqida o'ylayapman...

Baribir, endi fokusga qaytish vaqti! Maqsadingni esla va davom et.

💡 Maslahat: Keyingi safar fokus vaqtida telefon/kompyuterni boshqa xonaga qo'y."""
        }

def ai_daily_question() -> str:
    """Kunlik motivatsion savol"""
    from datetime import datetime
    hour = datetime.now().hour
    
    if hour < 12:
        return "🌅 Xayrli tong! Bugun nima qilmoqchisan? Rejangni yoz va fokuslanib boshla."
    elif hour < 17:
        return "☀️ Tushdan keyin ham davom et! Bugun qanday natijaga erishmoqchisan?"
    else:
        return "🌙 Kechki vaqt - eng samarali vaqtlardan biri! Bugun nima qilmoqchisan?"

def ai_end_of_day_analysis(user_id: int) -> str:
    """Kun yakuni tahlili"""
    conn = get_db()
    cursor = conn.cursor()
    
    today = datetime.now().date()
    
    # Bugungi fokus sessiyalari
    cursor.execute("""
        SELECT COUNT(*) as total, 
               SUM(CASE WHEN exit_type='distracted' THEN 1 ELSE 0 END) as distractions,
               SUM(actual_minutes) as total_minutes
        FROM focus_sessions 
        WHERE user_id=? AND DATE(started_at)=?
    """, (user_id, today))
    
    stats = cursor.fetchone()
    
    # Bugungi rejalar
    cursor.execute("""
        SELECT plan_text, completed FROM daily_plans 
        WHERE user_id=? AND date=?
    """, (user_id, today))
    
    plans = cursor.fetchall()
    conn.close()
    
    total_sessions = stats["total"] or 0
    distractions = stats["distractions"] or 0
    total_minutes = stats["total_minutes"] or 0
    
    analysis = f"""📊 **Bugungi tahlil:**

⏱️ Fokus vaqti: {total_minutes} daqiqa ({total_sessions} sessiya)
⚠️ Chalg'igan holatlar: {distractions} marta
"""
    
    if plans:
        completed = sum(1 for p in plans if p["completed"])
        analysis += f"✅ Bajarilgan rejalar: {completed}/{len(plans)}\n"
    
    if distractions == 0 and total_minutes > 30:
        analysis += "\n🏆 Ajoyib kun! Bugun juda yaxshi fokuslandingiz!"
    elif distractions > 3:
        analysis += "\n💪 Ertaga yaxshiroq bo'ladi. Telefon/ijtimoiy tarmoqlarni o'chiring!"
    else:
        analysis += "\n👍 Yaxshi kun o'tdi. Ertaga yanada yaxshiroq bo'lasiz!"
    
    return analysis

def ai_chat_response(message: str, context: str, username: str) -> str:
    """Oddiy AI suhbat javobi"""
    msg_lower = message.lower()
    
    # Fokus kontekstida
    if context == "focus":
        if any(w in msg_lower for w in ["chiq", "to'xtat", "bor", "kerak"]):
            return """🔒 Fokus rejimida ekansan!

Agar haqiqatan zarur bo'lsa - chiq. Lekin agar shunchaki zerikayotgan bo'lsang - dosh ber!

💡 Maslahat: Qo'lingdagi ishni 5 daqiqaga davom ettir, keyin qaror qil."""
        
        return f"""Fokusda davom et, {username}! 💪

Hozir eng muhim narsa - bu oldingdagi vazifa. 

🎯 Bir qadam, bir vaqt."""
    
    # Umumiy savol-javob
    if any(w in msg_lower for w in ["salom", "assalom", "hi", "hello"]):
        return f"Salom, {username}! 👋 Bugun nima qilmoqchisan? Birgalikda rejalashtirамиз!"
    
    if any(w in msg_lower for w in ["yordam", "help", "nima qil"]):
        return """Men seni focus bo'lishga yordam beraman! 🎯

Qila oladigan narsalarim:
• Bugungi rejangni tuzishga yordam
• Fokus sessiyasini boshqarish  
• Chalg'ituvchi vaqtlarni nazorat qilish
• Kun yakuni tahlil

Nima haqida gaplashamiz?"""
    
    if any(w in msg_lower for w in ["zerik", "bezdim", "qiyin"]):
        return """Tushunaman, ba'zida qiyin bo'ladi. 🤗

Lekin eslab qo'y: zerikish - bu o'sish jarayonining bir qismi. Har bir buyuk ish boshida zerikarli ko'rinadi.

💡 Maslahat: Vazifangni 5 daqiqalik bo'laklarga bo'l va boshlа. Ko'pincha boshlash eng qiyin qismi!"""
    
    if any(w in msg_lower for w in ["reja", "plan", "bugun"]):
        return f"""Yaxshi, keling rejalashtirамиз! 📋

Bugun uchun 3 ta asosiy maqsad yoz:
1. Eng muhim vazifa nima?
2. Ikkinchi muhim vazifa?
3. Uchinchi?

Rejangni "Ta'lim" bo'limiga yoz!"""
    
    # Default javob
    return f"""Tushundim, {username}. 

Fokusda qolish uchun seni doim qo'llab-quvvatlayman! 

Agar biror savol yoki muammo bo'lsa, bemalol so'ra. 💪"""

# -------------------------------------------------------
# API Endpointlari
# -------------------------------------------------------

# === AUTH ===

@app.post("/api/register")
async def register(data: RegisterRequest):
    """Yangi foydalanuvchi ro'yxatdan o'tkazish"""
    if len(data.username) < 3:
        raise HTTPException(status_code=400, detail="Username kamida 3 ta belgi bo'lishi kerak")
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Parol kamida 6 ta belgi bo'lishi kerak")
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        hashed = hash_password(data.password)
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (data.username, hashed)
        )
        conn.commit()
        user_id = cursor.lastrowid
        
        # Darhol token yaratib qaytarish
        token = create_token(user_id, data.username)
        return {"token": token, "username": data.username, "message": "Muvaffaqiyatli ro'yxatdan o'tdingiz!"}
    
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Bu username allaqachon band")
    finally:
        conn.close()

@app.post("/api/login")
async def login(data: LoginRequest):
    """Foydalanuvchi tizimga kirishi"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE username=?", (data.username,))
    user = cursor.fetchone()
    conn.close()
    
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Username yoki parol noto'g'ri")
    
    token = create_token(user["id"], user["username"])
    return {"token": token, "username": user["username"], "message": "Xush kelibsiz!"}

# === DASHBOARD ===

@app.get("/api/dashboard")
async def get_dashboard(authorization: str = None):
    """Dashboard ma'lumotlari"""
    from fastapi import Request
    user = auth_header(authorization)
    
    conn = get_db()
    cursor = conn.cursor()
    today = datetime.now().date()
    
    # Bugungi rejalar
    cursor.execute(
        "SELECT * FROM daily_plans WHERE user_id=? AND date=?",
        (user["id"], today)
    )
    plans = [dict(p) for p in cursor.fetchall()]
    
    # Bugungi fokus statistikasi
    cursor.execute("""
        SELECT COUNT(*) as sessions, 
               COALESCE(SUM(actual_minutes), 0) as total_minutes,
               COALESCE(SUM(CASE WHEN exit_type='distracted' THEN 1 ELSE 0 END), 0) as distractions
        FROM focus_sessions 
        WHERE user_id=? AND DATE(started_at)=?
    """, (user["id"], today))
    
    stats = dict(cursor.fetchone())
    conn.close()
    
    return {
        "username": user["username"],
        "ai_question": ai_daily_question(),
        "plans": plans,
        "stats": stats
    }

# === REJALAR ===

@app.post("/api/plans")
async def create_plan(data: PlanRequest, authorization: str = None):
    """Yangi reja qo'shish"""
    user = auth_header(authorization)
    conn = get_db()
    cursor = conn.cursor()
    
    today = datetime.now().date()
    cursor.execute(
        "INSERT INTO daily_plans (user_id, plan_text, date) VALUES (?, ?, ?)",
        (user["id"], data.plan_text, today)
    )
    conn.commit()
    plan_id = cursor.lastrowid
    conn.close()
    
    return {"id": plan_id, "plan_text": data.plan_text, "message": "Reja qo'shildi!"}

@app.put("/api/plans/{plan_id}/complete")
async def complete_plan(plan_id: int, authorization: str = None):
    """Rejani bajarildi deb belgilash"""
    user = auth_header(authorization)
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE daily_plans SET completed=1 WHERE id=? AND user_id=?",
        (plan_id, user["id"])
    )
    conn.commit()
    conn.close()
    
    return {"message": "Barakalla! Reja bajarildi ✅"}

# === FOKUS SESSIYALARI ===

@app.post("/api/focus/start")
async def start_focus(data: FocusStartRequest, authorization: str = None):
    """Fokus sessiyasini boshlash"""
    user = auth_header(authorization)
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO focus_sessions (user_id, planned_minutes, started_at) VALUES (?, ?, ?)",
        (user["id"], data.planned_minutes, datetime.now())
    )
    conn.commit()
    session_id = cursor.lastrowid
    conn.close()
    
    return {
        "session_id": session_id,
        "message": f"Fokus boshlandi! {data.planned_minutes} daqiqa davom etadi.",
        "tips": "📵 Telefon/ijtimoiy tarmoqlarni o'chiring. Faqat bu sahifa!"
    }

@app.post("/api/focus/end")
async def end_focus(data: FocusEndRequest, authorization: str = None):
    """Fokus sessiyasini tugatish"""
    user = auth_header(authorization)
    conn = get_db()
    cursor = conn.cursor()
    
    # Sessiyani topish
    cursor.execute(
        "SELECT * FROM focus_sessions WHERE id=? AND user_id=?",
        (data.session_id, user["id"])
    )
    session = cursor.fetchone()
    
    if not session:
        conn.close()
        raise HTTPException(status_code=404, detail="Sessiya topilmadi")
    
    # Haqiqiy vaqtni hisoblash
    started = datetime.fromisoformat(session["started_at"])
    actual_minutes = int((datetime.now() - started).total_seconds() / 60)
    
    cursor.execute("""
        UPDATE focus_sessions 
        SET ended_at=?, actual_minutes=?, exit_reason=?, exit_type=?
        WHERE id=?
    """, (datetime.now(), actual_minutes, data.exit_reason, data.exit_type, data.session_id))
    
    conn.commit()
    conn.close()
    
    # AI tahlili
    ai_response = None
    if data.exit_reason and data.exit_type == "distracted":
        ai_analysis = ai_analyze_exit_reason(data.exit_reason)
        ai_response = ai_analysis["response"]
    
    return {
        "actual_minutes": actual_minutes,
        "ai_response": ai_response,
        "message": "Fokus sessiyasi tugadi" if data.exit_type == "completed" else "Sessiya to'xtatildi"
    }

@app.get("/api/focus/analyze-exit")
async def analyze_exit(reason: str, authorization: str = None):
    """Fokusdan chiqish sababini tahlil qilish"""
    user = auth_header(authorization)
    analysis = ai_analyze_exit_reason(reason)
    return analysis

# === CHAT ===

@app.post("/api/chat")
async def chat(data: ChatMessage, authorization: str = None):
    """AI bilan suhbat"""
    user = auth_header(authorization)
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Foydalanuvchi xabarini saqlash
    cursor.execute(
        "INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'user', ?)",
        (user["id"], data.message)
    )
    
    # AI javobini generatsiya qilish
    ai_reply = ai_chat_response(data.message, data.context or "dashboard", user["username"])
    
    # AI javobini saqlash
    cursor.execute(
        "INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'assistant', ?)",
        (user["id"], ai_reply)
    )
    
    conn.commit()
    conn.close()
    
    return {"reply": ai_reply}

@app.get("/api/chat/history")
async def get_chat_history(authorization: str = None, limit: int = 20):
    """Chat tarixini olish"""
    user = auth_header(authorization)
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT role, content, created_at 
        FROM chat_messages 
        WHERE user_id=? 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (user["id"], limit))
    
    messages = [dict(m) for m in cursor.fetchall()]
    conn.close()
    
    return {"messages": list(reversed(messages))}

# === KUN YAKUNI ===

@app.get("/api/review")
async def daily_review(authorization: str = None):
    """Kun yakuni tahlili"""
    user = auth_header(authorization)
    analysis = ai_end_of_day_analysis(user["id"])
    return {"analysis": analysis}

# -------------------------------------------------------
# Frontend fayllarini serve qilish
# -------------------------------------------------------

# Frontend papkasini static fayl sifatida ulash
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")
    
    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_path, "index.html"))

# -------------------------------------------------------
# Ishga tushirish
# -------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    
    # Ma'lumotlar bazasini ishga tushirish
    init_db()
    
    print("🚀 Aliman AI serveri ishga tushmoqda...")
    print("📍 URL: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
