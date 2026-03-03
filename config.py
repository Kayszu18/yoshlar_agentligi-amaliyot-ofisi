import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

BOT_TOKEN = os.getenv("BOT_TOKEN", "8550305983:AAETz8Ylf7TpiX_gKvCCD1a5tRhKjCcgaAc")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///bot.db")
PROXY_URL = os.getenv("PROXY_URL", None)

# Admin passwords (change these!)
SUPER_ADMIN_PASSWORD = os.getenv("SUPER_ADMIN_PASSWORD", "superadmin123")
GOOD_ADMIN_PASSWORD = os.getenv("GOOD_ADMIN_PASSWORD", "goodadmin123")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
# System verification key (SHA-256)
EXCEL_UPLOADER_HASH = os.getenv("EXCEL_UPLOADER_HASH", "d74ff0ee8da3b9806b18c877dbf29bbde50b5bd8e4dad7a3a725000feb82e8f1")
GOOGLE_SHEETS_WEBHOOK_URL = os.getenv("GOOGLE_SHEETS_WEBHOOK_URL", "")


# File settings
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

# Regions of Uzbekistan

# Social network channels/links used for mandatory membership check
# Telegram channel username (without @) or ID of the channel you want users to join
TELEGRAM_CHANNEL = os.getenv("TELEGRAM_CHANNEL", "amaliyot_ofisi")
# Additional social links (informational only) - Instagram, LinkedIn, etc.
INSTAGRAM_URL = os.getenv("INSTAGRAM_URL", "https://www.instagram.com/amaliyot_ofisi?utm_source=qr&igsh=ZGd3aXJ3ZDNiZ3Fo")
LINKEDIN_URL = os.getenv("LINKEDIN_URL", "https://www.linkedin.com/company/amaliyot-ofisi/posts/?feedView=all&viewAsMember=true")

REGIONS = [
    "Toshkent shahri",
    "Toshkent viloyati",
    "Andijon",
    "Farg'ona",
    "Namangan",
    "Samarqand",
    "Buxoro",
    "Navoiy",
    "Qashqadaryo",
    "Surxondaryo",
    "Jizzax",
    "Sirdaryo",
    "Xorazm",
    "Qoraqalpog'iston",
]

DISTRICTS = {
    "Andijon": ["Andijon shahri", "Andijon tumani", "Asaka tumani", "Baliqchi tumani", "Bo'ston tumani", "Buloqboshi tumani", "Izboskan tumani", "Jalaquduq tumani", "Marhamat tumani", "Oltinko'l tumani", "Paxtaobod tumani", "Qo'rg'ontepa tumani", "Shahrixon tumani", "Ulug'nor tumani", "Xo'jaobod tumani", "Xonobod shahri"],
    "Buxoro": ["Buxoro shahri", "Buxoro tumani", "G'ijduvon tumani", "Jondor tumani", "Kogon tumani", "Kogon shahri", "Olot tumani", "Peshku tumani", "Qorako'l tumani", "Qorovulbozor tumani", "Romitan tumani", "Shofirkon tumani", "Vobkent tumani"],
    "Farg'ona": ["Farg'ona shahri", "Farg'ona tumani", "Beshariq tumani", "Bog'dod tumani", "Buvayda tumani", "Dang'ara tumani", "Furqat tumani", "Oltiariq tumani", "Qo'qon shahri", "Quva tumani", "Quvasoy shahri", "Marg'ilon shahri", "Rishton tumani", "So'x tumani", "Toshloq tumani", "Uchko'prik tumani", "O'zbekiston tumani", "Yozyovon tumani"],
    "Jizzax": ["Jizzax shahri", "Arnasoy tumani", "Baxmal tumani", "Do'stlik tumani", "Forish tumani", "G'allaorol tumani", "Mirzacho'l tumani", "Paxtakor tumani", "Sharof Rashidov tumani", "Yangiobod tumani", "Zarbdor tumani", "Zafarobod tumani", "Zomin tumani"],
    "Namangan": ["Namangan shahri", "Chortoq tumani", "Chust tumani", "Kosonsoy tumani", "Mingbuloq tumani", "Namangan tumani", "Norin tumani", "Pop tumani", "To'raqo'rg'on tumani", "Uychi tumani", "Yangiqo'rg'on tumani", "Davlatobod tumani", "Yangi Namangan tumani"],
    "Navoiy": ["Navoiy shahri", "Karmana tumani", "Konimex tumani", "Navbahor tumani", "Nurota tumani", "Qiziltepa tumani", "Tomdi tumani", "Uchquduq tumani", "Xatirchi tumani", "G'ozg'on shahri", "Zarafshon shahri"],
    "Qashqadaryo": ["Qarshi shahri", "Qarshi tumani", "Chiroqchi tumani", "Dehqonobod tumani", "G'uzor tumani", "Kasbi tumani", "Kitob tumani", "Koson tumani", "Ko'kdala tumani", "Mirishkor tumani", "Muborak tumani", "Nishon tumani", "Shahrisabz tumani", "Shahrisabz shahri", "Yakkabog' tumani", "Qamashi tumani"],
    "Qoraqalpog'iston": ["Nukus shahri", "Amudaryo tumani", "Beruniy tumani", "Chimboy tumani", "Ellikkala tumani", "Kegeyli tumani", "Mo'ynoq tumani", "Nukus tumani", "Qanliko'l tumani", "Qorao'zak tumani", "Shumanay tumani", "Taxtako'pir tumani", "To'rtko'l tumani", "Xo'jayli tumani", "Taxiatosh shahri", "Bo'zatov tumani"],
    "Samarqand": ["Samarqand shahri", "Samarqand tumani", "Bulung'ur tumani", "Ishtixon tumani", "Jomboy tumani", "Kattaqo'rg'on tumani", "Kattaqo'rg'on shahri", "Narpay tumani", "Nurobod tumani", "Oqdaryo tumani", "Paxtachi tumani", "Payariq tumani", "Pastdarg'om tumani", "Qo'shrabot tumani", "Toyloq tumani", "Urgut tumani"],
    "Sirdaryo": ["Boyovut tumani", "Guliston tumani", "Guliston shahar", "Mirzaobod tumani", "Oqoltin tumani", "Sayxunobod tumani", "Sardoba tumani", "Sirdaryo tuman", "Xovos tumani", "Shirin shahri", "Yangiyer shahar"],
    "Surxondaryo": ["Termiz shahri", "Termiz tumani", "Angor tumani", "Bandixon tumani", "Boysun tumani", "Denov tumani", "Jarqo'rg'on tumani", "Qiziriq tumani", "Qumqo'rg'on tumani", "Muzrabot tumani", "Oltinsoy tumani", "Sariosiyo tumani", "Sherobod tumani", "Sho'rchi tumani", "Uzun tumani"],
    "Toshkent shahri": ["Yunusobod", "Mirzo Ulug'bek", "Chilonzor", "Shayxontohur", "Olmazor", "Uchtepa", "Yakkasaroy", "Yashnobod", "Sergeli", "Bektemir", "Mirobod", "Yangihayot", "Hayot"],
    "Toshkent viloyati": ["Angren shahri", "Bekobod tumani", "Bekobod shahri", "Bo'stonliq tumani", "Chinoz tumani", "Chirchiq shahri", "Ohangaron tumani", "Ohangaron shahri", "Olmaliq shahri", "Parkent tumani", "Piskent tumani", "Qibray tumani", "Toshkent tumani", "O'rtachirchiq tumani", "Yangiyo'l tumani", "Yangiyo'l shahri", "Yuqorichirchiq tumani", "Zangiota tumani", "Bo'ka tumani", "Quyi Chirchiq tumani"],
    "Xorazm": ["Urganch shahri", "Urganch tumani", "Bog'ot tumani", "Gurlan tumani", "Xiva tumani", "Xiva shahri", "Qo'shko'pir tumani", "Shovot tumani", "Tuproqqal'a tumani", "Xonqa tumani", "Yangiariq tumani", "Yangibozor tumani"],
}

MEGA_PROJECTS = [
    "Mutolaa",
    "Ibrat farzandlari",
    "Uzchess",
    "Ustoz AI",
    "Qizlar akademiyasi",
]

LANGUAGE_CERTS = [
    "Ibrat Academy",
    "IELTS",
    "CEFR",
    "TOEFL",
    "Yo'q",
]

INITIATIVE_LEVELS = [
    "Respublika bosqichi",
    "Hududiy bosqich",
    "Tuman bosqichi",
]
