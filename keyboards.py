from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import REGIONS, DISTRICTS, MEGA_PROJECTS, LANGUAGE_CERTS, INITIATIVE_LEVELS


def contact_keyboard():
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📲 Raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return kb


def main_menu_keyboard():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Loyiha haqida"), KeyboardButton(text="✍️ Ariza topshirish")],
            [KeyboardButton(text="📊 Ariza holati"), KeyboardButton(text="📞 Bog'lanish")],
        ],
        resize_keyboard=True
    )
    return kb


def regions_keyboard():
    builder = InlineKeyboardBuilder()
    for region in REGIONS:
        builder.button(text=region, callback_data=f"region:{region}")
    builder.adjust(2)
    return builder.as_markup()


def districts_keyboard(region: str):
    builder = InlineKeyboardBuilder()
    districts = DISTRICTS.get(region, [])
    for d in districts:
        builder.button(text=d, callback_data=f"district:{d}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga (Viloyatni o'zgartirish)", callback_data="back_to_regions"))
    return builder.as_markup()


def yes_no_keyboard(prefix: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha", callback_data=f"{prefix}:ha")
    builder.button(text="❌ Yo'q", callback_data=f"{prefix}:yoq")
    builder.adjust(2)
    return builder.as_markup()


def lang_cert_keyboard(selected: list = None):
    if selected is None:
        selected = []
    builder = InlineKeyboardBuilder()
    for cert in LANGUAGE_CERTS:
        mark = "✅ " if cert in selected else ""
        builder.button(text=f"{mark}{cert}", callback_data=f"cert:{cert}")
    builder.button(text="➡️ Davom etish", callback_data="cert:done")
    builder.adjust(2)
    return builder.as_markup()


def mega_projects_keyboard(selected: list = None):
    if selected is None:
        selected = []
    builder = InlineKeyboardBuilder()
    for project in MEGA_PROJECTS:
        mark = "✅ " if project in selected else ""
        builder.button(text=f"{mark}{project}", callback_data=f"mega:{project}")
    builder.button(text="➡️ Davom etish", callback_data="mega:done")
    builder.adjust(2)
    return builder.as_markup()


def initiative_keyboard():
    builder = InlineKeyboardBuilder()
    for level in INITIATIVE_LEVELS:
        builder.button(text=level, callback_data=f"initiative:{level}")
    builder.button(text="❌ Yo'q", callback_data="initiative:yoq")
    builder.adjust(1)
    return builder.as_markup()


def confirm_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Tasdiqlash", callback_data="confirm:yes")
    builder.button(text="🔄 Tahrirlash", callback_data="confirm:edit")
    builder.adjust(2)
    return builder.as_markup()


def skip_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭ O'tkazib yuborish", callback_data="skip")
    return builder.as_markup()


def cancel_keyboard():
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True
    )
    return kb

def back_keyboard(callback_data: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Orqaga", callback_data=callback_data)
    return builder.as_markup()


def admin_management_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Admin qo'shish"), KeyboardButton(text="➖ Admin o'chirish")],
            [KeyboardButton(text="📋 Adminlar ro'yxati")],
            [KeyboardButton(text="⬅️ Orqaga")]
        ],
        resize_keyboard=True
    )
    return kb


def admin_roles_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Admin", callback_data="role:admin")
    builder.button(text="Good Admin", callback_data="role:good_admin")
    builder.adjust(2)
    return builder.as_markup()

# ── ADMIN keyboards ──────────────────────────────



def join_channel_keyboard(channel_username: str):
    """Return inline keyboard with a link to the Telegram channel and a check button."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔗 Kanalga yozilish", url=f"https://t.me/{channel_username}")
    builder.button(text="✅ Tekshirish", callback_data="check_membership")
    builder.adjust(1)
    return builder.as_markup()


def admin_main_keyboard(role: str):
    buttons = [
        [KeyboardButton(text="👥 Nomzodlar ro'yxati")],
        [KeyboardButton(text="📊 Statistika")],
    ]
    if role in ("good_admin", "super_admin", "excel_uploader"):
        buttons.append([KeyboardButton(text="📤 Export")])
    if role in ("super_admin", "excel_uploader"):
        buttons.append([KeyboardButton(text="⚙️ Tizim sozlamalari")])
        buttons.append([KeyboardButton(text="👤 Adminlar boshqaruvi")])
    if role == "excel_uploader":
        buttons.append([KeyboardButton(text="🔐 Master Panel")])
    buttons.append([KeyboardButton(text="🚪 Chiqish")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def candidates_filter_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📍 Viloyat bo'yicha", callback_data="filter:region")
    builder.button(text="📊 Status bo'yicha", callback_data="filter:status")
    builder.button(text="🔍 Qidirish", callback_data="filter:search")
    builder.button(text="📋 Hammasi", callback_data="filter:all")
    builder.adjust(2)
    return builder.as_markup()


def candidate_action_keyboard(app, role: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="📄 Hujjatlarni ko'rish", callback_data=f"docs:{app.id}")
    
    if app.final_status == 'pending' and role in ("admin", "good_admin", "super_admin", "excel_uploader"):
        builder.button(text="⭐ 1-bosqichni baholash", callback_data=f"score1:{app.id}")
        
    if app.final_status == 'essay_submitted' and role in ("admin", "good_admin", "super_admin", "excel_uploader"):
        builder.button(text="📝 Esseni baholash", callback_data=f"score_essay:{app.id}")
        
    if app.final_status == 'stage2_passed' and role in ("good_admin", "super_admin", "excel_uploader"):
        builder.button(text="📅 Suhbat belgilash", callback_data=f"interview:{app.id}")
        
    builder.adjust(1)
    return builder.as_markup()


def score_keyboard(current: int, max_score: int, prefix: str):
    builder = InlineKeyboardBuilder()
    for i in range(0, max_score + 1, 2 if max_score >= 10 else 1):
        builder.button(text=str(i), callback_data=f"{prefix}:{i}")
    builder.adjust(5)
    return builder.as_markup()


def interview_status_keyboard(app_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Qabul qilindi", callback_data=f"istatus:{app_id}:accepted")
    builder.button(text="🔄 Zaxira", callback_data=f"istatus:{app_id}:reserve")
    builder.button(text="❌ Rad etildi", callback_data=f"istatus:{app_id}:rejected")
    builder.adjust(1)
    return builder.as_markup()


def system_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🛑 Botni to'xtatish", callback_data="sys:stop")
    builder.button(text="▶️ Botni ishga tushirish", callback_data="sys:start")
    builder.button(text="🔢 Min ball o'zgartirish", callback_data="sys:minscore")
    builder.adjust(1)
    return builder.as_markup()


def export_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Excel export", callback_data="export:excel")
    builder.button(text="📦 ZIP export", callback_data="export:zip")
    builder.adjust(2)
    return builder.as_markup()
