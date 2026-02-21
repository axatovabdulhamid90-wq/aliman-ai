# 🎯 Aliman AI - Ishga Tushirish Qo'llanmasi

## Loyiha Tuzilmasi

```
aliman-ai/
├── backend/
│   ├── main.py          # FastAPI serveri (barcha API)
│   └── requirements.txt # Python kutubxonalari
├── frontend/
│   ├── index.html       # Asosiy HTML sahifa
│   ├── style.css        # Barcha stillар
│   └── app.js           # Frontend JavaScript mantiqi
└── README.md
```

## Texnologiyalar

- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Backend**: Python + FastAPI
- **Ma'lumotlar bazasi**: SQLite (avtomatik yaratiladi)
- **Auth**: JWT token + bcrypt parol hashlash

---

## 🚀 Ishga Tushirish

### 1. Backend sozlash

```bash
# Backend papkasiga o'tish
cd backend

# Virtual muhit yaratish (tavsiya etiladi)
python -m venv venv

# Virtual muhitni faollashtirish
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Kutubxonalarni o'rnatish
pip install -r requirements.txt

# Serverni ishga tushirish
python main.py
```

Backend: http://localhost:8000
API Docs: http://localhost:8000/docs

### 2. Frontend ochish

Frontend oddiy HTML fayllar - to'g'ridan-to'g'ri brauzerde oching:
```bash
# Oddiy yo'l:
cd frontend && open index.html  # Mac
cd frontend && start index.html  # Windows

# Yoki Python simple server bilan:
cd frontend && python -m http.server 3000
# Keyin: http://localhost:3000
```

### 3. API URL sozlash

`frontend/app.js` faylining birinchi qatorida:
```javascript
const API_URL = 'http://localhost:8000'; // Backend manzili
```

---

## 📋 Asosiy Funksiyalar

| Funksiya | Tavsif |
|----------|--------|
| **Register/Login** | Username + parol (bcrypt hash) |
| **Dashboard** | AI savoli, bugungi reja, statistika |
| **Focus Mode** | Fullscreen, taymer, chiqishda ogohlantirish |
| **AI Tahlil** | Chiqish sababi tahlili (chalg'ish/to'g'ri sabab) |
| **Chat** | AI bilan suhbat |
| **Kun Yakuni** | Fokus sessiyalari statistikasi |

---

## 🔐 API Endpointlar

| Endpoint | Metod | Tavsif |
|----------|-------|--------|
| `/api/register` | POST | Ro'yxatdan o'tish |
| `/api/login` | POST | Kirish |
| `/api/dashboard` | GET | Dashboard ma'lumotlari |
| `/api/plans` | POST | Reja qo'shish |
| `/api/plans/{id}/complete` | PUT | Rejani bajarish |
| `/api/focus/start` | POST | Fokus boshlash |
| `/api/focus/end` | POST | Fokus tugatish |
| `/api/chat` | POST | AI chat |
| `/api/chat/history` | GET | Chat tarixi |
| `/api/review` | GET | Kun yakuni tahlili |

---

## 🛠️ Konfiguratsiya

`backend/main.py` da o'zgartirish mumkin:

```python
SECRET_KEY = "..."          # JWT secret (production'da o'zgartiring!)
ACCESS_TOKEN_EXPIRE_HOURS = 24  # Token muddati
DB_PATH = "aliman.db"       # Ma'lumotlar bazasi fayli
```

---

## 🔮 Keyingi Rivojlanish (MVP+)

- [ ] Haqiqiy LLM integratsiyasi (OpenAI/Claude API)
- [ ] Haftalik/oylik tahlil grafiklar
- [ ] Browser extension (sayt bloklash)
- [ ] Mobile ilova (React Native)
- [ ] Ko'p foydalanuvchi statistika raqobati
- [ ] Pomodoro texnikasi integratsiyasi
- [ ] Email eslatmalar
