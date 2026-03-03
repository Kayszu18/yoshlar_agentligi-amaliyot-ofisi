from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import (
    REGIONS,
    DISTRICTS,
    MEGA_PROJECTS,
    LANGUAGE_CERTS,
    INITIATIVE_LEVELS,
    TELEGRAM_CHANNEL,
    INSTAGRAM_URL,
    LINKEDIN_URL,
)


def contact_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📲 Raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Loyiha haqida"), KeyboardButton(text="✍️ Ariza topshirish")],
            [KeyboardButton(text="📊 Ariza holati"), KeyboardButton(text="📞 Bog'lanish")],
            [KeyboardButton(text="▶️ Davom ettirish"), KeyboardButton(text="❓ FAQ")],
        ],
        resize_keyboard=True,
    )


def _telegram_channel_url() -> str:
    raw = str(TELEGRAM_CHANNEL or "").strip()
    raw = raw.replace("https://t.me/", "").replace("http://t.me/", "").strip().strip("/")
    if raw.startswith("@"):
        raw = raw[1:]
    raw = raw.split()[0] if raw else ""
    if not raw or raw.lstrip("-").isdigit():
        return "https://t.me"
    return f"https://t.me/{raw}"


def social_links_keyboard():
    builder = InlineKeyboardBuilder()

    tg_url = _telegram_channel_url()
    if tg_url:
        builder.button(text="📣 Telegram", url=tg_url)
    if str(INSTAGRAM_URL or "").strip():
        builder.button(text="📸 Instagram", url=str(INSTAGRAM_URL).strip())
    if str(LINKEDIN_URL or "").strip():
        builder.button(text="💼 LinkedIn", url=str(LINKEDIN_URL).strip())

    builder.adjust(1)
    return builder.as_markup()


def regions_keyboard():
    builder = InlineKeyboardBuilder()
    for region in REGIONS:
        builder.button(text=region, callback_data=f"region:{region}")
    builder.adjust(2)
    return builder.as_markup()


def districts_keyboard(region: str):
    builder = InlineKeyboardBuilder()
    for d in DISTRICTS.get(region, []):
        builder.button(text=d, callback_data=f"district:{d}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga (Viloyat)", callback_data="back_to_regions"))
    return builder.as_markup()


def yes_no_keyboard(prefix: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha", callback_data=f"{prefix}:ha")
    builder.button(text="❌ Yo'q", callback_data=f"{prefix}:yoq")
    builder.adjust(2)
    return builder.as_markup()


def lang_cert_keyboard(selected: list | None = None):
    selected = selected or []
    builder = InlineKeyboardBuilder()
    for cert in LANGUAGE_CERTS:
        mark = "✅ " if cert in selected else ""
        builder.button(text=f"{mark}{cert}", callback_data=f"cert:{cert}")
    builder.button(text="➡️ Davom etish", callback_data="cert:done")
    builder.adjust(2)
    return builder.as_markup()


def mega_projects_keyboard(selected: list | None = None):
    selected = selected or []
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


def edit_application_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 Shaxsiy ma'lumotlar", callback_data="edit:personal")
    builder.button(text="💼 Professional ma'lumotlar", callback_data="edit:professional")
    builder.button(text="⬅️ Orqaga", callback_data="edit:back_to_confirm")
    builder.adjust(1)
    return builder.as_markup()


def skip_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭ O'tkazib yuborish", callback_data="skip")
    return builder.as_markup()


def cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True,
    )


def back_keyboard(callback_data: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Orqaga", callback_data=callback_data)
    return builder.as_markup()


def admin_management_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Admin qo'shish"), KeyboardButton(text="➖ Admin o'chirish")],
            [KeyboardButton(text="📋 Adminlar ro'yxati")],
            [KeyboardButton(text="⬅️ Orqaga")],
        ],
        resize_keyboard=True,
    )


def admin_roles_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Admin", callback_data="role:admin")
    builder.button(text="Good Admin", callback_data="role:good_admin")
    builder.adjust(2)
    return builder.as_markup()


def join_channel_keyboard(channel_username: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔗 Kanalga yozilish", url=f"https://t.me/{channel_username}")
    builder.button(text="✅ Tekshirish", callback_data="check_membership")
    builder.adjust(1)
    return builder.as_markup()


def admin_main_keyboard(role: str):
    buttons = [
        [KeyboardButton(text="👥 Nomzodlar ro'yxati"), KeyboardButton(text="📊 Statistika")],
    ]
    if role in ("good_admin", "super_admin", "excel_uploader"):
        buttons.append([KeyboardButton(text="📤 Export"), KeyboardButton(text="📣 Bulk xabar")])
    if role in ("super_admin", "excel_uploader"):
        buttons.append([KeyboardButton(text="⚙️ Tizim sozlamalari"), KeyboardButton(text="👤 Adminlar boshqaruvi")])
        buttons.append([KeyboardButton(text="☁️ Google Sheet Sync"), KeyboardButton(text="🧾 Audit log")])
    if role == "excel_uploader":
        buttons.append([KeyboardButton(text="🔐 Master Panel")])
    buttons.append([KeyboardButton(text="🚪 Chiqish")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def candidates_filter_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📌 Viloyat bo'yicha", callback_data="filter:region")
    builder.button(text="📊 Status bo'yicha", callback_data="filter:status")
    builder.button(text="🔍 Qidirish", callback_data="filter:search")
    builder.button(text="🧩 Murakkab filter", callback_data="filter:advanced")
    builder.button(text="📋 Hammasi", callback_data="filter:all")
    builder.adjust(2)
    return builder.as_markup()


def candidate_action_keyboard(app, role: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="📄 Hujjatlarni ko'rish", callback_data=f"docs:{app.id}")

    if app.final_status == "pending" and role in ("admin", "good_admin", "super_admin", "excel_uploader"):
        builder.button(text="⭐ 1-bosqichni baholash", callback_data=f"score1:{app.id}")

    if app.final_status == "essay_submitted" and role in ("admin", "good_admin", "super_admin", "excel_uploader"):
        builder.button(text="📝 Esseni baholash", callback_data=f"score_essay:{app.id}")

    if app.final_status == "stage2_passed" and role in ("good_admin", "super_admin", "excel_uploader"):
        builder.button(text="📅 Suhbat belgilash", callback_data=f"interview:{app.id}")

    builder.adjust(1)
    return builder.as_markup()


def score_keyboard(current: int, max_score: int, prefix: str):
    builder = InlineKeyboardBuilder()
    step = 2 if max_score >= 10 else 1
    for i in range(0, max_score + 1, step):
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


def system_keyboard(subscription_required: bool = True):
    builder = InlineKeyboardBuilder()
    builder.button(text="🛑 Botni to'xtatish", callback_data="sys:stop")
    builder.button(text="▶️ Botni ishga tushirish", callback_data="sys:start")
    builder.button(text="🔢 Min ball o'zgartirish", callback_data="sys:minscore")
    sub_text = "✅ Majburiy obuna: ON" if subscription_required else "❌ Majburiy obuna: OFF"
    builder.button(text=sub_text, callback_data="sys:subtoggle")
    builder.adjust(1)
    return builder.as_markup()


def export_keyboard(role: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Excel export", callback_data="export:excel")
    if role in ("super_admin", "excel_uploader"):
        builder.button(text="📦 ZIP export", callback_data="export:zip")
        builder.adjust(2)
    else:
        builder.adjust(1)
    return builder.as_markup()


def paginated_candidates_keyboard(rows, page: int, total_pages: int, callback_prefix: str):
    builder = InlineKeyboardBuilder()
    for app, user in rows:
        builder.button(text=f"#{app.id} | {(user.full_name or '')[:20]}", callback_data=f"view_app:{app.id}")
    builder.adjust(1)

    if total_pages > 1:
        pagination_buttons = []
        if page > 0:
            pagination_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"{callback_prefix}:{page - 1}"))

        pagination_buttons.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="noop"))

        if page < total_pages - 1:
            pagination_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"{callback_prefix}:{page + 1}"))

        builder.row(*pagination_buttons)

    builder.row(InlineKeyboardButton(text="⬅️ Orqaga (Filtrlar)", callback_data="back_to_filters"))
    return builder.as_markup()
