# 🤖 Amaliyot Ofisi - Tanlov Boti

Yoshlar ishlari agentligi "Amaliyot Ofisi" loyihasi uchun maxsus ishlab chiqilgan Telegram bot.
Ushbu bot orqali nomzodlar ariza topshirishi, hujjatlarini yuklashi va saralash bosqichlaridan o'tishi mumkin.

## 📚 Texnologiyalar

- **Til:** Python 3.11+
- **Framework:** aiogram 3.x
- **Ma'lumotlar bazasi:** SQLite (aiosqlite) + SQLAlchemy (Async)
- **Boshqa:** pandas/openpyxl (Excel export), aiofiles

## 📁 Loyiha tuzilmasi

```
bot/
├── main.py                    # Asosiy kirish nuqtasi
├── config.py                  # Konfiguratsiya va viloyatlar
├── requirements.txt
├── .env.example
│
├── database.py                # SQLAlchemy modellari
│
├── handlers/
│   ├── start.py               # /start, kontakt
│   ├── status.py              # Holat tekshirish
│   ├── admin.py               # Admin panel
│   └── application/
│       ├── personal.py        # 1-bosqich: Shaxsiy
│       ├── professional.py    # 1-bosqich: Professional
│       ├── essay.py           # 2-bosqich: Esse
│       └── finish.py          # Tasdiqlash va saqlash
│
├── keyboards/
│   └── keyboards.py           # Barcha klaviaturalar
│
├── middlewares/
│   └── middlewares.py         # Auth, rate limit, texnik ish
│
├── states/
│   └── states.py              # FSM holatlari
│
└── services/
    └── services.py            # Fayl, validatsiya, export
```

## ⚙️ O'rnatish

### 1. Talablarni o'rnatish
```bash
pip install -r requirements.txt
```

### 2. PostgreSQL bazasini yaratish
```sql
CREATE DATABASE botdb;
CREATE USER botuser WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE botdb TO botuser;
```

### 3. .env fayl yaratish
```bash
cp .env.example .env
nano .env
```

`.env` faylini to'ldiring:
```
BOT_TOKEN=7123456789:AAH...your_token
DATABASE_URL=postgresql+asyncpg://botuser:password@localhost:5432/botdb
SUPER_ADMIN_PASSWORD=JudaKuchlíParol!123
GOOD_ADMIN_PASSWORD=YaxshiAdminParol!456
ADMIN_PASSWORD=OddiyAdminParol!789
UPLOAD_DIR=uploads
```

### 4. Uploads papkasini yaratish
```bash
mkdir -p uploads/exports
```

### 5. Botni ishga tushirish
```bash
python main.py
```

## 🔐 Rol tizimi

| Rol | Imkoniyatlar |
|-----|-------------|
| `super_admin` | Hamma narsa + Bot on/off + Adminlar boshqaruvi |
| `good_admin` | Ball berish + Suhbat + Export |
| `admin` | Nomzodlar + Ball berish |

## 📋 Foydalanuvchi oqimi

```
/start → Telefon → F.I.Sh → Sana → Viloyat → Tuman → Mahalla → Ish sanasi
       → Obyektivka → Sertifikat → Namunali → Top100 → Tashabbus
       → Yutuqlar → Mukofot → Argos → Ijtimoiy → Mega loyiha
       → Esse (.docx) → Tasdiqlash → ✅ Ariza qabul qilindi
```

## 👨‍💼 Admin oqimi

```
/admin → Parol → Panel
       → Nomzodlar ro'yxati → Ko'rish → Ball berish
       → Suhbat belgilash → Status o'zgartirish
       → Export (Excel/ZIP)
       → [super_admin] Bot holati, Min ball, Adminlar
```

## 🛠 Texnik talablar

- Python 3.11+
- PostgreSQL 14+
- RAM: 512MB+
- Disk: 10GB+ (fayllar uchun)

## 📝 Loglash

Botning barcha amallar `bot.log` faylida saqlanadi.

## 🔄 Yangilash

Admin parollarini o'zgartirish uchun `.env` faylini tahrirlang va botni qayta yoqing.
