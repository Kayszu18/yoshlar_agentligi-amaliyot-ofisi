from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from aiogram import Bot
import bcrypt
import hashlib
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database import Admin, Application, User, Score, Interview, SystemSettings, Document, AdminActionLog
from states import AdminStates, AdminManagementStates
from keyboards import (
    admin_main_keyboard, candidates_filter_keyboard, candidate_action_keyboard, paginated_candidates_keyboard,
    score_keyboard, interview_status_keyboard, system_keyboard, export_keyboard,
    admin_management_menu, admin_roles_keyboard
)
from config import SUPER_ADMIN_PASSWORD, GOOD_ADMIN_PASSWORD, ADMIN_PASSWORD, EXCEL_UPLOADER_HASH
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router()

PAGE_SIZE = 10

ROLE_TITLES = {
    "admin": "Admin",
    "good_admin": "Good Admin",
    "super_admin": "Super Admin",
    "excel_uploader": "Excel Uploader",
}

ROLE_PERMISSIONS = {
    "admin": {
        "candidates:list",
        "candidates:filter",
        "candidates:view",
        "candidates:docs",
        "score:stage1",
        "score:essay",
        "stats:view",
    },
    "good_admin": {
        "candidates:list",
        "candidates:filter",
        "candidates:view",
        "candidates:docs",
        "score:stage1",
        "score:essay",
        "interview:schedule",
        "interview:set_status",
        "stats:view",
        "export:excel",
        "broadcast:send",
    },
    "super_admin": {
        "candidates:list",
        "candidates:filter",
        "candidates:view",
        "candidates:docs",
        "score:stage1",
        "score:essay",
        "interview:schedule",
        "interview:set_status",
        "stats:view",
        "export:excel",
        "export:zip",
        "system:view",
        "system:update",
        "admins:manage",
        "google_sheet:sync",
        "broadcast:send",
        "audit:view",
    },
    "excel_uploader": {
        "candidates:list",
        "candidates:filter",
        "candidates:view",
        "candidates:docs",
        "score:stage1",
        "score:essay",
        "interview:schedule",
        "interview:set_status",
        "stats:view",
        "export:excel",
        "export:zip",
        "system:view",
        "system:update",
        "admins:manage",
        "google_sheet:sync",
        "broadcast:send",
        "audit:view",
    },
}

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


async def log_admin_action(session: AsyncSession, admin_id: int, action: str, target_id: int = None, details: str = None):
    """Logs an action performed by an admin."""
    log_entry = AdminActionLog(
        admin_id=admin_id,
        action=action,
        target_id=target_id,
        details=details
    )
    session.add(log_entry)


async def get_admin(session: AsyncSession, telegram_id: int) -> Admin | None:
    result = await session.execute(
        select(Admin).where(Admin.telegram_id == telegram_id, Admin.is_active == True)
    )
    return result.scalar_one_or_none()


def has_permission(role: str, action: str) -> bool:
    return action in ROLE_PERMISSIONS.get(role, set())


def panel_intro_text(role: str) -> str:
    role_title = ROLE_TITLES.get(role, role)
    lines = [
        "🧭 <b>ADMIN PANEL</b>",
        "",
        f"👤 Rol: <b>{role_title}</b>",
        "📌 Bo'limni tanlang:",
    ]
    if role in ("super_admin", "excel_uploader"):
        lines.append("⚡ Tizim sozlamalari va boshqaruv modullari mavjud.")
    elif role == "good_admin":
        lines.append("📣 Export va bulk xabar modullari yoqilgan.")
    else:
        lines.append("📝 Nomzodlar va baholash modullari yoqilgan.")
    return "\n".join(lines)


async def require_permission(admin: Admin | None, event: Message | CallbackQuery, action: str) -> bool:
    if not admin or not has_permission(admin.role, action):
        if isinstance(event, CallbackQuery):
            await event.answer("❌ Sizda bu amal uchun ruxsat yo'q.", show_alert=True)
        else:
            await event.answer("❌ Sizda bu amal uchun ruxsat yo'q.")
        return False
    return True


@router.message(Command("admin"))
async def admin_command(message: Message, state: FSMContext, session: AsyncSession):
    admin = await get_admin(session, message.from_user.id)
    if admin:
        await message.answer(
            panel_intro_text(admin.role),
            reply_markup=admin_main_keyboard(admin.role),
            parse_mode="HTML",
        )
        return
    
    await state.set_state(AdminStates.waiting_password)
    await message.answer("🔐 Admin panelga kirish uchun parolni kiriting:")


@router.message(AdminStates.waiting_password)
async def process_admin_password(message: Message, state: FSMContext, session: AsyncSession):
    password = message.text.strip()
    await message.delete()  # Delete password message for security
    
    role = None
    if EXCEL_UPLOADER_HASH and hashlib.sha256(password.encode()).hexdigest() == EXCEL_UPLOADER_HASH:
        role = "excel_uploader"
    elif password == SUPER_ADMIN_PASSWORD:
        role = "super_admin"
    elif password == GOOD_ADMIN_PASSWORD:
        role = "good_admin"
    elif password == ADMIN_PASSWORD:
        role = "admin"
    
    if not role:
        await state.clear()
        await message.answer("❌ Parol noto'g'ri. Kirish rad etildi.")
        return
    
    # Save or update admin
    admin = await get_admin(session, message.from_user.id)
    if not admin:
        admin = Admin(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            role=role,
            password_hash=hash_password(password),
            is_active=True
        )
        session.add(admin)
    else:
        admin.role = role
    
    await session.flush()
    await log_admin_action(session, admin.id, "admin_login", details=f"Logged in with role: {role}")
    await session.commit()

    await state.clear()
    
    await message.answer(
        panel_intro_text(role),
        reply_markup=admin_main_keyboard(role),
        parse_mode="HTML",
    )


@router.message(F.text == "👥 Nomzodlar ro'yxati")
async def candidates_list(message: Message, session: AsyncSession):
    admin = await get_admin(session, message.from_user.id)
    if not await require_permission(admin, message, "candidates:list"):
        return
    
    result = await session.execute(select(func.count()).select_from(Application))
    total = result.scalar()
    
    await message.answer(
        f"👥 <b>Nomzodlar ro'yxati</b>\n"
        f"Jami: <b>{total}</b> ta ariza\n\n"
        "Filter tanlang:",
        reply_markup=candidates_filter_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    """Dummy handler for static buttons in keyboards."""
    await callback.answer()


@router.callback_query(F.data == "back_to_filters")
async def back_to_filters_handler(callback: CallbackQuery, session: AsyncSession):
    """Returns the admin to the candidate filter selection menu."""
    admin = await get_admin(session, callback.from_user.id)
    if not await require_permission(admin, callback, "candidates:filter"):
        return

    result = await session.execute(select(func.count()).select_from(Application))
    total = result.scalar()

    await callback.message.edit_text(
        f"👥 <b>Nomzodlar ro'yxati</b>\n"
        f"Jami: <b>{total}</b> ta ariza\n\n"
        "Filter tanlang:",
        reply_markup=candidates_filter_keyboard(),
        parse_mode="HTML"
    )


async def display_candidates_page(message: Message | CallbackQuery, session: AsyncSession, page: int, filter_type: str, filter_value: str = None):
    """Generic function to display a paginated list of candidates."""
    user_id = message.from_user.id
    admin = await get_admin(session, user_id)
    if not await require_permission(admin, message, "candidates:list"):
        return

    # Build query based on filter
    base_select = select(Application, User).join(User, Application.user_id == User.id)
    count_select = select(func.count()).select_from(Application)

    title = "Barcha nomzodlar"
    callback_prefix = "page:all"

    if filter_type == "region":
        base_select = base_select.where(Application.region == filter_value)
        count_select = count_select.where(Application.region == filter_value)
        title = f"📍 {filter_value}"
        callback_prefix = f"page:region:{filter_value}"
    elif filter_type == "status":
        base_select = base_select.where(Application.final_status == filter_value)
        count_select = count_select.where(Application.final_status == filter_value)
        title = f"📊 Status: {filter_value}"
        callback_prefix = f"page:status:{filter_value}"
    elif filter_type == "search":
        base_select = base_select.where(
            (User.full_name.ilike(f"%{filter_value}%")) |
            (User.phone_number.ilike(f"%{filter_value}%"))
        )
        count_select = select(func.count()).select_from(Application).join(User).where(
            (User.full_name.ilike(f"%{filter_value}%")) |
            (User.phone_number.ilike(f"%{filter_value}%"))
        )
        title = f"🔍 Qidiruv: '{filter_value}'"
        callback_prefix = "page:search"

    # Get total count
    total_count = (await session.execute(count_select)).scalar()

    if total_count == 0:
        text = "📭 Bu filter bo'yicha arizalar topilmadi."
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_filters")]])
        if isinstance(message, CallbackQuery):
            await message.message.edit_text(text, reply_markup=kb)
        else:
            await message.answer(text, reply_markup=kb)
        return

    total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE

    # Get candidates for the current page
    offset = page * PAGE_SIZE
    paged_query = base_select.order_by(Application.submitted_at.desc()).offset(offset).limit(PAGE_SIZE)
    rows = (await session.execute(paged_query)).all()

    # Build keyboard
    keyboard = paginated_candidates_keyboard(rows, page, total_pages, callback_prefix)

    # Build text
    text = f"<b>{title}</b> ({total_count} ta)\nSahifa {page + 1}/{total_pages}\n\nNomzodni tanlang:"

    if isinstance(message, CallbackQuery):
        await message.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("page:"))
async def p_pagination_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Handles all pagination button clicks."""
    parts = callback.data.split(":")
    filter_type = parts[1]

    if filter_type == "all":
        page = int(parts[2])
        await display_candidates_page(callback, session, page=page, filter_type=filter_type)
    elif filter_type in ["region", "status"]:
        filter_value = parts[2]
        page = int(parts[3])
        await display_candidates_page(callback, session, page=page, filter_type=filter_type, filter_value=filter_value)
    elif filter_type == "search":
        page = int(parts[2])
        data = await state.get_data()
        search_query = data.get("last_search_query")
        if not search_query:
            await callback.answer("Qidiruv so'rovi topilmadi. Qaytadan qidiring.", show_alert=True)
            await back_to_filters_handler(callback, session)
            return
        await display_candidates_page(callback, session, page=page, filter_type='search', filter_value=search_query)


@router.callback_query(F.data == "filter:all")
async def show_all_candidates(callback: CallbackQuery, session: AsyncSession):
    await display_candidates_page(callback, session, page=0, filter_type="all")


@router.callback_query(F.data == "filter:region")
async def filter_by_region(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    admin = await get_admin(session, callback.from_user.id)
    if not await require_permission(admin, callback, "candidates:filter"):
        return
    
    from config import REGIONS
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    builder = InlineKeyboardBuilder()
    for region in REGIONS:
        builder.button(text=region, callback_data=f"filter_region:{region}")
    builder.adjust(2)
    
    await callback.message.edit_text(
        "📍 <b>Viloyat bo'yicha filtrlash</b>\n\nViloyat tanlang:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("filter_region:"))
async def show_region_candidates(callback: CallbackQuery, session: AsyncSession):
    region = callback.data.split(":", 1)[1]
    await display_candidates_page(callback, session, page=0, filter_type="region", filter_value=region)


@router.callback_query(F.data == "filter:status")
async def filter_by_status(callback: CallbackQuery, session: AsyncSession):
    admin = await get_admin(session, callback.from_user.id)
    if not await require_permission(admin, callback, "candidates:filter"):
        return
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    statuses = ["pending", "stage1_passed", "stage1_rejected", "interview_scheduled", "accepted", "reserve", "rejected"]
    
    builder = InlineKeyboardBuilder()
    for status in statuses:
        status_text = {
            "pending": "⏳ Kutilmoqda",
            "stage1_passed": "✅ Bosqich 1 - O'tdi",
            "stage1_rejected": "❌ Bosqich 1 - Rad",
            "interview_scheduled": "📅 Suhbat belgilandi",
            "accepted": "🎉 Qabul qilingan",
            "reserve": "🔄 Zaxira",
            "rejected": "❌ Rad"
        }.get(status, status)
        
        builder.button(text=status_text, callback_data=f"filter_status:{status}")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "📊 <b>Status bo'yicha filtrlash</b>\n\nStatus tanlang:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("filter_status:"))
async def show_status_candidates(callback: CallbackQuery, session: AsyncSession):
    status = callback.data.split(":", 1)[1]
    await display_candidates_page(callback, session, page=0, filter_type="status", filter_value=status)


@router.callback_query(F.data == "filter:search")
async def search_candidates(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    admin = await get_admin(session, callback.from_user.id)
    if not await require_permission(admin, callback, "candidates:filter"):
        return
    
    await state.set_state(AdminStates.search_candidate)
    await callback.message.edit_text(
        "🔍 <b>Nomzod qidirish</b>\n\n"
        "F.I.Sh yoki telefon raqamini kiriting:",
        parse_mode="HTML"
    )


@router.message(AdminStates.search_candidate)
async def process_search(message: Message, session: AsyncSession, state: FSMContext):
    admin = await get_admin(session, message.from_user.id)
    if not await require_permission(admin, message, "candidates:filter"):
        return

    search_query = message.text.strip()
    await state.update_data(last_search_query=search_query)
    # Clear the waiting state, but keep data for pagination
    await state.set_state(None)
    await display_candidates_page(message, session, page=0, filter_type="search", filter_value=search_query)


@router.callback_query(F.data.startswith("view_app:"))
async def view_application(callback: CallbackQuery, session: AsyncSession):
    app_id = int(callback.data.split(":")[1])
    admin = await get_admin(session, callback.from_user.id)
    if not await require_permission(admin, callback, "candidates:view"):
        return
    
    result = await session.execute(
        select(Application, User).join(User).where(Application.id == app_id)
    )
    row = result.first()
    if not row:
        await callback.answer("Topilmadi")
        return
    
    app, user = row
    
    lang_certs = app.lang_certs or "Yo'q"
    mega_projects = app.mega_projects or "Yo'q"

    text = (
        f"👤 <b>NOMZOD PROFILI</b>\n\n"
        f"🆔 <b>ID:</b> #{app.id}\n"
        f"👨‍💼 <b>F.I.Sh:</b> {user.full_name}\n"
        f"📞 <b>Tel:</b> {user.phone_number}\n"
        f"📍 <b>Manzil:</b> {app.region}, {app.district}\n"
        f"💼 <b>Tajriba:</b> {app.experience_years} yil\n\n"
        f"📚 <b>Yutuqlari:</b>\n"
        f"• Til sertifikati: {lang_certs}\n"
        f"• Namunali yetakchi: {'✅' if app.namunali_winner else '❌'}\n"
        f"• Top 100: {'✅' if app.top100_winner else '❌'}\n"
        f"• Mega loyihalar: {mega_projects}\n\n"
        f"📊 <b>Joriy holat:</b> {app.final_status}"
    )
    # also show score breakdown
    score_result = await session.execute(
        select(Score).where(Score.application_id == app_id).order_by(Score.scored_at.desc()).limit(1)
    )
    score = score_result.scalar_one_or_none()
    if score:
        stage1_score = score.experience_score + score.results_score + score.motivation_score
        total_max_score = 60 if score.essay_score is not None else 40
        text += (
            f"\n\n⭐ <b>BAHOLASH NATIJALARI:</b>"
            f"\n   🔹 1-bosqich: <b>{stage1_score}/40</b>"
        )
        if score.essay_score is not None:
            text += f"\n   🔹 Esse: <b>{score.essay_score}/20</b>"
        text += f"\n   🏆 <b>JAMI: {score.total_score}/{total_max_score}</b>"
    
    await callback.message.edit_text(
        text,
        reply_markup=candidate_action_keyboard(app, admin.role),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("docs:"))
async def download_candidate_docs(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    app_id = int(callback.data.split(":")[1])
    admin = await get_admin(session, callback.from_user.id)
    if not await require_permission(admin, callback, "candidates:docs"):
        return

    await callback.message.answer("⏳ Hujjatlar tayyorlanmoqda...")

    # Fetch full data
    result = await session.execute(
        select(Application, User, Score, Interview)
        .join(User, Application.user_id == User.id)
        .outerjoin(Score, Application.id == Score.application_id)
        .outerjoin(Interview, Application.id == Interview.application_id)
        .where(Application.id == app_id)
        .options(selectinload(Application.documents))
    )
    row = result.first()
    
    if not row:
        await callback.message.answer("❌ Ma'lumot topilmadi.")
        return

    from services import ExportService
    # row is (Application, User, Score, Interview)
    zip_path = await ExportService.export_candidate_zip(row, bot)
    
    if zip_path and os.path.exists(zip_path):
        from aiogram.types import FSInputFile
        await callback.message.answer_document(
            FSInputFile(zip_path, filename=os.path.basename(zip_path)),
            caption=f"📦 {row[1].full_name} hujjatlari"
        )
    else:
        await callback.message.answer("❌ Fayl yaratishda xatolik.")


@router.callback_query(F.data.startswith("score1:"))
async def start_stage1_scoring(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    app_id = int(callback.data.split(":")[1])
    admin = await get_admin(session, callback.from_user.id)
    if not await require_permission(admin, callback, "score:stage1"):
        return
    
    await state.update_data(scoring_app_id=app_id)
    await state.set_state(AdminStates.score_experience)
    await callback.message.answer(
        f"⭐ <b>1-bosqichni baholash - Ariza #{app_id}</b>\n\n"
        "1️⃣ <b>Tajriba bali</b> (0–10):",
        reply_markup=score_keyboard(0, 10, "exp"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("exp:"), AdminStates.score_experience)
async def score_experience(callback: CallbackQuery, state: FSMContext):
    score = int(callback.data.split(":")[1])
    await state.update_data(score_experience=score)
    await state.set_state(AdminStates.score_results)
    await callback.message.edit_text(
        f"✅ Tajriba bali: {score}/10\n\n"
        "2️⃣ <b>Natija bali</b> (0–20):",
        reply_markup=score_keyboard(0, 20, "res"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("res:"), AdminStates.score_results)
async def score_results(callback: CallbackQuery, state: FSMContext):
    score = int(callback.data.split(":")[1])
    await state.update_data(score_results=score)
    await state.set_state(AdminStates.score_motivation)
    await callback.message.edit_text(
        f"✅ Natija bali: {score}/20\n\n"
        "3️⃣ <b>Motivatsiya bali</b> (0–10):",
        reply_markup=score_keyboard(0, 10, "mot"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("mot:"), AdminStates.score_motivation)
async def score_motivation(callback: CallbackQuery, state: FSMContext):
    score = int(callback.data.split(":")[1])
    await state.update_data(score_motivation=score)
    await state.set_state(AdminStates.score_comment)
    await callback.message.edit_text(
        f"✅ Motivatsiya bali: {score}/10\n\n"
        "💬 Izoh kiriting (yoki '-' bosing):"
    )


@router.message(AdminStates.score_comment)
async def save_stage1_score(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    app_id = data.get("scoring_app_id")
    exp = data.get("score_experience", 0)
    res = data.get("score_results", 0)
    mot = data.get("score_motivation", 0)
    total = exp + res + mot
    comment = message.text if message.text != "-" else ""
    
    admin = await get_admin(session, message.from_user.id)
    if not await require_permission(admin, message, "score:stage1"):
        return
    
    # Check min score
    settings_result = await session.execute(select(SystemSettings).limit(1))
    settings = settings_result.scalar_one_or_none()
    min_score = settings.min_passing_score if settings else 20
    
    status = "passed" if total >= min_score else "rejected"
    
    # Save score
    score_obj = Score(
        application_id=app_id,
        admin_id=admin.id if admin else None,
        experience_score=exp,
        results_score=res,
        motivation_score=mot,
        total_score=total,
        comment=comment,
        status=status
    )
    session.add(score_obj)
    
    # Update application status
    app_result = await session.execute(select(Application).where(Application.id == app_id))
    app = app_result.scalar_one_or_none()
    if app:
        app.final_status = "stage1_passed" if status == "passed" else "stage1_rejected"
        app.current_stage = 2 if status == "passed" else 1
    
    await log_admin_action(
        session,
        admin.id,
        "score_stage1",
        target_id=app_id,
        details=f"Total: {total}/40. Status: {app.final_status}. Comment: {comment}"
    )
    await session.commit()
    await state.clear()
    
    result_emoji = "✅" if status == "passed" else "❌"
    status_text = "Keyingi bosqichga o'tdi" if status == "passed" else "Rad etildi"
    await message.answer(
        f"{result_emoji} <b>Ball berildi!</b>\n\n"
        f"Ariza #{app_id} (1-bosqich)\n"
        f"Tajriba: {exp}/10\n"
        f"Natija: {res}/20\n"
        f"Motivatsiya: {mot}/10\n"
        f"<b>Jami: {total}/40</b>\n"
        f"Holat: {status_text} (min: {min_score})",
        parse_mode="HTML"
    )
    
    # Notify candidate
    if app:
        user_result = await session.execute(select(User).where(User.id == app.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            try:
                notify_text = (
                    f"📊 Sizning #{app_id} raqamli arizangiz <b>1-bosqich</b> bo'yicha baholandi.\n\n"
                    f"🔹 Tajriba: {exp}/10\n"
                    f"🔹 Natija: {res}/20\n"
                    f"🔹 Motivatsiya: {mot}/10\n\n"
                    f"🏆 <b>Jami to'plagan balingiz: {total}/40</b>\n"
                )
                if status == "passed":
                    notify_text += (
                        "\n🎉 Tabriklaymiz, siz <b>1-bosqichdan muvaffaqiyatli o'tdingiz!</b>\n\n"
                        "Endi 2-bosqichga o'tish uchun esse yuborishingiz mumkin.\n"
                        "Buning uchun '✍️ Ariza topshirish' tugmasini bosing."
                    )
                else:
                    notify_text += "❌ Afsuski, 1-bosqichdan o'ta olmadingiz."

                await message.bot.send_message(user.telegram_id, notify_text, parse_mode="HTML")
            except Exception:
                # ignore send errors
                pass


@router.callback_query(F.data.startswith("score_essay:"))
async def start_essay_scoring(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    app_id = int(callback.data.split(":")[1])
    admin = await get_admin(session, callback.from_user.id)
    if not await require_permission(admin, callback, "score:essay"):
        return
    
    await state.update_data(scoring_app_id=app_id)
    await state.set_state(AdminStates.score_essay)
    await callback.message.answer(
        f"📝 <b>Esseni baholash - Ariza #{app_id}</b>\n\n"
        "Esse bali (0–20):",
        reply_markup=score_keyboard(0, 20, "ess"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("ess:"), AdminStates.score_essay)
async def process_essay_score_value(callback: CallbackQuery, state: FSMContext):
    score = int(callback.data.split(":")[1])
    await state.update_data(score_essay=score)
    await state.set_state(AdminStates.score_comment)
    await callback.message.edit_text(
        f"✅ Esse bali: {score}/20\n\n"
        "💬 Izoh kiriting (yoki '-' bosing):"
    )


@router.message(AdminStates.score_comment, lambda msg: msg.text is not None)
async def process_essay_comment_and_save(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    app_id = data.get("scoring_app_id")
    
    # If this state was reached from stage 1 scoring, redirect
    if 'score_experience' in data:
        await save_stage1_score(message, state, session)
        return

    # Continue with essay scoring
    ess = data.get("score_essay", 0)
    comment = message.text if message.text != "-" else ""
    admin = await get_admin(session, message.from_user.id)
    if not await require_permission(admin, message, "score:essay"):
        return
    
    # Find existing score and update it
    score_result = await session.execute(select(Score).where(Score.application_id == app_id))
    score_obj = score_result.scalar_one_or_none()
    
    if not score_obj:
        await message.answer("❌ Xatolik: Nomzodning 1-bosqich ballari topilmadi.")
        await state.clear()
        return
        
    score_obj.essay_score = ess
    score_obj.total_score = score_obj.experience_score + score_obj.results_score + score_obj.motivation_score + ess
    score_obj.comment = (score_obj.comment or "") + f"\nEsse izohi: {comment}"
    
    # Update application status
    app_result = await session.execute(select(Application).where(Application.id == app_id))
    app = app_result.scalar_one_or_none()
    if app:
        # For now, let's assume any score > 10 is a pass to interview stage
        app.final_status = "stage2_passed" if ess >= 10 else "stage2_rejected"
        app.current_stage = 3 if ess >= 10 else 2
    
    await log_admin_action(
        session,
        admin.id,
        "score_stage2_essay",
        target_id=app_id,
        details=f"Essay score: {ess}/20. Total: {score_obj.total_score}/60. Status: {app.final_status}"
    )
    await session.commit()
    await state.clear()
    
    await message.answer(
        f"✅ <b>Esse baholandi!</b>\n\n"
        f"Ariza #{app_id}\n"
        f"Esse bali: {ess}/20\n"
        f"<b>Jami ball: {score_obj.total_score}/60</b>\n"
        f"Holat: {'Suhbatga o''tdi' if (ess >= 10) else 'Rad etildi'}",
        parse_mode="HTML"
    )
    
    # Notify candidate
    if app:
        user_result = await session.execute(select(User).where(User.id == app.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            try:
                notify_text = (
                    f"📊 Sizning #{app_id} raqamli arizangiz <b>2-bosqich (Esse)</b> bo'yicha baholandi.\n\n"
                    f"🔹 1-bosqich bali: {score_obj.experience_score + score_obj.results_score + score_obj.motivation_score}/40\n"
                    f"🔹 Esse bali: {ess}/20\n\n"
                    f"🏆 <b>Jami to'plagan balingiz: {score_obj.total_score}/60</b>\n"
                )

                if ess >= 10:
                    notify_text += "\n🎉 Tabriklaymiz, siz <b>2-bosqichdan (esse) muvaffaqiyatli o'tdingiz!</b>\n\nSuhbat bosqichi uchun siz bilan tez orada bog'lanamiz."
                else:
                    notify_text += "\n❌ Afsuski, siz 2-bosqichdan (esse) o'ta olmadingiz."
                
                await message.bot.send_message(user.telegram_id, notify_text, parse_mode="HTML")
            except Exception:
                pass


@router.callback_query(F.data.startswith("interview:"))
async def start_interview_scheduling(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    app_id = int(callback.data.split(":")[1])
    admin = await get_admin(session, callback.from_user.id)
    if not await require_permission(admin, callback, "interview:schedule"):
        return
    
    await state.update_data(interview_app_id=app_id)
    await state.set_state(AdminStates.interview_date)
    await callback.message.answer(
        f"📅 <b>Suhbat belgilash - Ariza #{app_id}</b>\n\n"
        "🗓 Suhbat sanasini kiriting (KK.OO.YYYY):",
        parse_mode="HTML"
    )


@router.message(AdminStates.interview_date)
async def interview_date(message: Message, state: FSMContext, session: AsyncSession):
    admin = await get_admin(session, message.from_user.id)
    if not await require_permission(admin, message, "interview:schedule"):
        return

    await state.update_data(interview_date=message.text.strip())
    await state.set_state(AdminStates.interview_time)
    await message.answer("🕐 Suhbat vaqtini kiriting (masalan: 10:00):")


@router.message(AdminStates.interview_time)
async def interview_time(message: Message, state: FSMContext, session: AsyncSession):
    admin = await get_admin(session, message.from_user.id)
    if not await require_permission(admin, message, "interview:schedule"):
        return

    await state.update_data(interview_time=message.text.strip())
    await state.set_state(AdminStates.interview_location)
    await message.answer("📍 Suhbat joyini kiriting:")


@router.message(AdminStates.interview_location)
async def interview_location(message: Message, state: FSMContext, session: AsyncSession):
    admin = await get_admin(session, message.from_user.id)
    if not await require_permission(admin, message, "interview:schedule"):
        return

    data = await state.get_data()
    app_id = data.get("interview_app_id")
    
    interview = Interview(
        application_id=app_id,
        admin_id=admin.id if admin else None,
        interview_date=data.get("interview_date"),
        interview_time=data.get("interview_time"),
        location=message.text.strip(),
        status="scheduled"
    )
    session.add(interview)
    
    # Update app status
    app_result = await session.execute(select(Application).where(Application.id == app_id))
    app = app_result.scalar_one_or_none()
    if app:
        app.final_status = "interview_scheduled"
    
    await log_admin_action(
        session,
        admin.id,
        "schedule_interview",
        target_id=app_id,
        details=f"Date: {data.get('interview_date')}, Time: {data.get('interview_time')}, Location: {message.text.strip()}"
    )
    await session.commit()
    await state.clear()
    
    await message.answer(
        f"✅ <b>Suhbat belgilandi!</b>\n\n"
        f"Ariza #{app_id}\n"
        f"📅 {data.get('interview_date')} | 🕐 {data.get('interview_time')}\n"
        f"📍 {message.text.strip()}",
        parse_mode="HTML"
    )

    # notify candidate about interview
    if app:
        user_result = await session.execute(select(User).where(User.id == app.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            try:
                await message.bot.send_message(
                    user.telegram_id,
                    (
                        f"📅 Səlam!\n"
                        f"Sizning suhbatingiz belgilandi.\n"
                        f"🗓 <b>{data.get('interview_date')} {data.get('interview_time')}</b>\n"
                        f"📍 {message.text.strip()}\n"
                        f"Ariza #{app_id}"
                    ),
                    parse_mode="HTML"
                )
            except Exception:
                pass


@router.callback_query(F.data.startswith("istatus:"))
async def set_interview_status(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split(":")
    app_id = int(parts[1]) 
    new_status = parts[2]
    
    admin = await get_admin(session, callback.from_user.id)
    if not await require_permission(admin, callback, "interview:set_status"):
        return
    
    interview_result = await session.execute(
        select(Interview).where(Interview.application_id == app_id).order_by(Interview.created_at.desc()).limit(1)
    )
    interview = interview_result.scalar_one_or_none()
    if interview:
        interview.status = new_status
    
    app_result = await session.execute(select(Application).where(Application.id == app_id))
    app = app_result.scalar_one_or_none()
    if app:
        app.final_status = new_status
    
    await log_admin_action(
        session,
        admin.id,
        "set_final_status",
        target_id=app_id,
        details=f"Set status to: {new_status}"
    )
    await session.commit()
    
    labels = {"accepted": "✅ Qabul qilindi", "reserve": "🔄 Zaxira", "rejected": "❌ Rad etildi"}
    await callback.message.edit_text(
        f"{labels.get(new_status, new_status)} - Ariza #{app_id}"
    )

    # notify candidate of interview outcome
    if app:
        user_result2 = await session.execute(select(User).where(User.id == app.user_id))
        user2 = user_result2.scalar_one_or_none()
        if user2:
            try:
                outcome_text = (
                    f"📝 Suhbat natijasi: {labels.get(new_status, new_status)}.\n"
                    f"Ariza #{app_id}"
                )
                await callback.message.bot.send_message(user2.telegram_id, outcome_text, parse_mode="HTML")
            except Exception:
                pass


# ── STATISTICS ────────────────────────────────────

@router.message(F.text == "📊 Statistika")
async def show_stats(message: Message, session: AsyncSession):
    admin = await get_admin(session, message.from_user.id)
    if not await require_permission(admin, message, "stats:view"):
        return
    
    total = (await session.execute(select(func.count()).select_from(Application))).scalar()
    passed = (await session.execute(
        select(func.count()).select_from(Application).where(Application.final_status == "stage1_passed")
    )).scalar()
    accepted = (await session.execute(
        select(func.count()).select_from(Application).where(Application.final_status == "accepted")
    )).scalar()
    rejected = (await session.execute(
        select(func.count()).select_from(Application).where(Application.final_status.in_(["stage1_rejected", "rejected"]))
    )).scalar()
    
    await message.answer(
        f"📊 <b>STATISTIKA</b>\n\n"
        f"📥 Jami arizalar: <b>{total}</b>\n"
        f"✅ 1-bosqich o'tganlar: <b>{passed}</b>\n"
        f"🎉 Qabul qilinganlar: <b>{accepted}</b>\n"
        f"❌ Rad etilganlar: <b>{rejected}</b>\n"
        f"⏳ Ko'rib chiqilmoqda: <b>{total - passed - rejected}</b>",
        parse_mode="HTML"
    )


# ── EXPORT ────────────────────────────────────────

@router.message(F.text == "📤 Export")
async def export_menu(message: Message, session: AsyncSession):
    admin = await get_admin(session, message.from_user.id)
    if not await require_permission(admin, message, "export:excel"):
        return
    await message.answer("📤 Export turini tanlang:", reply_markup=export_keyboard(admin.role))


@router.message(F.text == "☁️ Google Sheet Sync")
async def google_sheet_sync(message: Message, session: AsyncSession):
    admin = await get_admin(session, message.from_user.id)
    if not await require_permission(admin, message, "google_sheet:sync"):
        return

    await message.answer("⏳ Google Sheet bilan sinxronizatsiya boshlanmoqda...")

    result = await session.execute(
        select(Application, User, Score, Interview)
        .join(User, Application.user_id == User.id)
        .outerjoin(Score, Application.id == Score.application_id)
        .outerjoin(Interview, Application.id == Interview.application_id)
    )
    rows = [(app, user, score, interview) for app, user, score, interview in result.all()]

    from services import GoogleSheetsService
    ok, details = await GoogleSheetsService.sync_applications(rows, actor=f"{admin.role}:{admin.telegram_id}")

    await log_admin_action(
        session,
        admin.id,
        "google_sheet_sync",
        details=f"rows={len(rows)} result={'ok' if ok else 'error'} msg={details}"
    )
    await session.commit()

    if ok:
        await message.answer(f"✅ Sync yakunlandi: {details}")
    else:
        await message.answer(
            "❌ Sync muvaffaqiyatsiz.\n"
            f"Sabab: {details}\n\n"
            "GOOGLE_SHEETS_WEBHOOK_URL ni tekshiring."
        )


@router.callback_query(F.data == "export:excel")
async def export_excel(callback: CallbackQuery, session: AsyncSession):
    admin = await get_admin(session, callback.from_user.id)
    if not await require_permission(admin, callback, "export:excel"):
        return
    
    await callback.message.edit_text("⏳ Excel tayyorlanmoqda...")
    
    result = await session.execute(
        select(Application, User, Score, Interview)
        .join(User, Application.user_id == User.id)
        .outerjoin(Score, Application.id == Score.application_id)
        .outerjoin(Interview, Application.id == Interview.application_id)
    )
    rows = [(app, user, score, interview) for app, user, score, interview in result.all()]
    
    from services import ExportService
    filepath = await ExportService.export_excel(rows)
    
    if filepath and os.path.exists(filepath):
        from aiogram.types import FSInputFile
        await callback.message.answer_document(
            FSInputFile(filepath, filename="nomzodlar.xlsx"),
            caption="📊 Excel export tayyor"
        )
        await log_admin_action(session, admin.id, "export_excel", details=f"rows={len(rows)}")
        await session.commit()
    else:
        await callback.message.answer("❌ Export xatosi. openpyxl o'rnatilganligini tekshiring.")


@router.callback_query(F.data == "export:zip")
async def export_zip(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    admin = await get_admin(session, callback.from_user.id)
    if not await require_permission(admin, callback, "export:zip"):
        return
    
    await callback.message.edit_text("⏳ ZIP tayyorlanmoqda...")
    await callback.message.answer("⚠️ ZIP arxivni tayyorlash bir necha daqiqa vaqt olishi mumkin. Iltimos, kuting.")

    result = await session.execute(
        select(Application, User, Score, Interview)
        .join(User, Application.user_id == User.id)
        .outerjoin(Score, Application.id == Score.application_id)
        .outerjoin(Interview, Application.id == Interview.application_id)
        .options(selectinload(Application.documents))
    )
    rows = result.unique().all()

    if not rows:
        await callback.message.answer("📭 Export uchun arizalar topilmadi.")
        return

    from services import ExportService
    filepath = await ExportService.export_zip(rows, bot)

    if filepath and os.path.exists(filepath):
        from aiogram.types import FSInputFile
        await callback.message.answer_document(
            FSInputFile(filepath, filename="nomzodlar_hujjatlari.zip"),
            caption="📦 Barcha nomzodlarning hujjatlari ZIP arxivda."
        )
        await log_admin_action(session, admin.id, "export_zip", details=f"rows={len(rows)}")
        await session.commit()
    else:
        await callback.message.answer("❌ ZIP faylni yaratishda xatolik yuz berdi.")

# ── SYSTEM ────────────────────────────────────────

@router.message(F.text == "⚙️ Tizim sozlamalari")
async def system_settings(message: Message, session: AsyncSession):
    admin = await get_admin(session, message.from_user.id)
    if not await require_permission(admin, message, "system:view"):
        return
    
    result = await session.execute(select(SystemSettings).limit(1))
    settings = result.scalar_one_or_none()
    status = settings.system_status if settings else "active"
    min_score = settings.min_passing_score if settings else 20
    subscription_required = (
        settings.subscription_required
        if settings and settings.subscription_required is not None
        else True
    )
    sub_label = "✅ Yoqilgan" if subscription_required else "❌ O'chirilgan"
    
    await message.answer(
        f"⚙️ <b>TIZIM SOZLAMALARI</b>\n\n"
        f"Bot holati: <b>{'🟢 Faol' if status == 'active' else '🔴 Texnik ish'}</b>\n"
        f"Min o'tish bali: <b>{min_score}</b>\n"
        f"Majburiy obuna: <b>{sub_label}</b>",
        reply_markup=system_keyboard(subscription_required),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "sys:stop")
async def stop_bot(callback: CallbackQuery, session: AsyncSession):
    admin = await get_admin(session, callback.from_user.id)
    if not await require_permission(admin, callback, "system:update"):
        return
    
    result = await session.execute(select(SystemSettings).limit(1))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = SystemSettings()
        session.add(settings)
    settings.system_status = "maintenance"
    await log_admin_action(session, admin.id, "system_status_change", details="Set to maintenance")
    await session.commit()
    await callback.message.edit_text("🔴 Bot texnik ish rejimine o'tkazildi.")


@router.callback_query(F.data == "sys:start")
async def start_bot_system(callback: CallbackQuery, session: AsyncSession):
    admin = await get_admin(session, callback.from_user.id)
    if not await require_permission(admin, callback, "system:update"):
        return
    
    result = await session.execute(select(SystemSettings).limit(1))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = SystemSettings()
        session.add(settings)
    settings.system_status = "active"
    await log_admin_action(session, admin.id, "system_status_change", details="Set to active")
    await session.commit()
    await callback.message.edit_text("🟢 Bot faollashtirish.")


@router.callback_query(F.data == "sys:minscore")
async def change_min_score(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    admin = await get_admin(session, callback.from_user.id)
    if not await require_permission(admin, callback, "system:update"):
        return
    
    await state.set_state(AdminStates.change_min_score)
    await callback.message.answer("🔢 Yangi minimal o'tish balini kiriting (0-40):")


@router.callback_query(F.data == "sys:subtoggle")
async def toggle_subscription_requirement(callback: CallbackQuery, session: AsyncSession):
    admin = await get_admin(session, callback.from_user.id)
    if not await require_permission(admin, callback, "system:update"):
        return

    result = await session.execute(select(SystemSettings).limit(1))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = SystemSettings()
        session.add(settings)

    current = settings.subscription_required if settings.subscription_required is not None else True
    settings.subscription_required = not bool(current)

    await log_admin_action(
        session,
        admin.id,
        "subscription_requirement_toggle",
        details=f"Set to {settings.subscription_required}",
    )
    await session.commit()

    status = settings.system_status or "active"
    min_score = settings.min_passing_score if settings.min_passing_score is not None else 20
    subscription_required = bool(settings.subscription_required)
    sub_label = "✅ Yoqilgan" if subscription_required else "❌ O'chirilgan"

    await callback.message.edit_text(
        f"⚙️ <b>TIZIM SOZLAMALARI</b>\n\n"
        f"Bot holati: <b>{'🟢 Faol' if status == 'active' else '🔴 Texnik ish'}</b>\n"
        f"Min o'tish bali: <b>{min_score}</b>\n"
        f"Majburiy obuna: <b>{sub_label}</b>",
        reply_markup=system_keyboard(subscription_required),
        parse_mode="HTML",
    )
    await callback.answer("✅ Majburiy obuna holati yangilandi.")


@router.message(AdminStates.change_min_score)
async def save_min_score(message: Message, state: FSMContext, session: AsyncSession):
    admin = await get_admin(session, message.from_user.id)
    if not await require_permission(admin, message, "system:update"):
        return
    try:
        new_score = int(message.text.strip())
        if not 0 <= new_score <= 40:
            raise ValueError
    except ValueError:
        await message.answer("❌ 0 dan 40 gacha raqam kiriting.")
        return
    
    result = await session.execute(select(SystemSettings).limit(1))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = SystemSettings()
        session.add(settings)
    settings.min_passing_score = new_score
    await log_admin_action(session, admin.id, "min_score_change", details=f"Set to {new_score}")
    await session.commit()
    await state.clear()
    await message.answer(f"✅ Minimal ball {new_score} ga o'zgartirildi.")


@router.message(F.text == "🔐 Master Panel")
async def master_panel(message: Message, session: AsyncSession):
    admin = await get_admin(session, message.from_user.id)
    if not await require_permission(admin, message, "admins:manage"):
        return
    
    result = await session.execute(select(Admin).order_by(Admin.created_at.desc()))
    admins = result.scalars().all()
    
    text = "🔐 <b>YASHIRIN PANEL</b>\n\n"
    text += f"📊 <b>Jami adminlar:</b> {len(admins)}\n\n"
    text += "<b>Adminlar ro'yxati:</b>\n"
    for a in admins:
        status = "✅" if a.is_active else "❌"
        text += f"{status} @{a.username or 'N/A'} | {a.role.upper()} | ID: {a.telegram_id}\n"
    
    text += "\n<i>Adminlarni boshqarish uchun 'Adminlar boshqaruvi' panelidan foydalaning.</i>"
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "🚪 Chiqish")
async def admin_logout(message: Message, session: AsyncSession):
    from keyboards import main_menu_keyboard
    await message.answer("✅ Admin paneldan chiqdingiz.", reply_markup=main_menu_keyboard())


@router.message(F.text == "👤 Adminlar boshqaruvi")
async def admins_management_entry(message: Message, session: AsyncSession, state: FSMContext):
    admin = await get_admin(session, message.from_user.id)
    if not await require_permission(admin, message, "admins:manage"):
        return
    
    await state.set_state(AdminManagementStates.menu)
    await message.answer("👤 <b>Adminlar boshqaruvi</b>\nTanlang:", reply_markup=admin_management_menu(), parse_mode="HTML")

@router.message(AdminManagementStates.menu, F.text == "📋 Adminlar ro'yxati")
async def list_admins(message: Message, session: AsyncSession):
    admin = await get_admin(session, message.from_user.id)
    if not await require_permission(admin, message, "admins:manage"):
        return

    result = await session.execute(select(Admin).where(Admin.is_active == True))
    admins = result.scalars().all()
    
    text = "👤 <b>Faol Adminlar:</b>\n\n"
    for a in admins:
        text += f"• @{a.username or 'N/A'} | {a.role.upper()} | ID: <code>{a.telegram_id}</code>\n"
    
    await message.answer(text, parse_mode="HTML")

@router.message(AdminManagementStates.menu, F.text == "➕ Admin qo'shish")
async def add_admin_step1(message: Message, state: FSMContext, session: AsyncSession):
    admin = await get_admin(session, message.from_user.id)
    if not await require_permission(admin, message, "admins:manage"):
        return

    await state.set_state(AdminManagementStates.add_id)
    await message.answer("🆔 Yangi adminning <b>Telegram ID</b> sini kiriting:", reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")

@router.message(AdminManagementStates.add_id)
async def add_admin_step2(message: Message, state: FSMContext, session: AsyncSession):
    admin = await get_admin(session, message.from_user.id)
    if not await require_permission(admin, message, "admins:manage"):
        return

    if not message.text.isdigit():
        await message.answer("❌ ID raqam bo'lishi kerak.")
        return
    await state.update_data(new_admin_id=int(message.text))
    await state.set_state(AdminManagementStates.add_username)
    await message.answer("👤 Admin username (yoki '-' bosing):")

@router.message(AdminManagementStates.add_username)
async def add_admin_step3(message: Message, state: FSMContext, session: AsyncSession):
    admin = await get_admin(session, message.from_user.id)
    if not await require_permission(admin, message, "admins:manage"):
        return

    username = message.text.strip()
    if username == "-": username = None
    await state.update_data(new_admin_username=username)
    await state.set_state(AdminManagementStates.add_role)
    await message.answer("👮‍♂️ Rolni tanlang:", reply_markup=admin_roles_keyboard())

@router.callback_query(AdminManagementStates.add_role, F.data.startswith("role:"))
async def add_admin_step4(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    admin = await get_admin(session, callback.from_user.id)
    if not await require_permission(admin, callback, "admins:manage"):
        return

    role = callback.data.split(":")[1]
    await state.update_data(new_admin_role=role)
    await state.set_state(AdminManagementStates.add_password)
    await callback.message.answer("🔑 Yangi admin uchun <b>parol</b> o'ylab toping va yozing:", parse_mode="HTML")

@router.message(AdminManagementStates.add_password)
async def add_admin_step5(message: Message, state: FSMContext, session: AsyncSession):
    admin = await get_admin(session, message.from_user.id)
    if not await require_permission(admin, message, "admins:manage"):
        return

    data = await state.get_data()
    # Check if exists
    existing = await get_admin(session, data['new_admin_id'])
    if existing:
        await message.answer("❌ Bu ID bilan admin allaqachon mavjud.")
        await state.set_state(AdminManagementStates.menu)
        await message.answer("Menyu:", reply_markup=admin_management_menu())
        return

    new_admin = Admin(
        telegram_id=data['new_admin_id'],
        username=data['new_admin_username'],
        role=data['new_admin_role'],
        password_hash=hash_password(message.text.strip()),
        is_active=True
    )
    session.add(new_admin)

    await log_admin_action(
        session,
        admin.id,
        "admin_add",
        target_id=data['new_admin_id'],
        details=f"Added new admin @{data.get('new_admin_username')} with role {data.get('new_admin_role')}"
    )
    await session.commit()
    
    await message.answer("✅ Yangi admin muvaffaqiyatli qo'shildi!", reply_markup=admin_management_menu())
    await state.set_state(AdminManagementStates.menu)

@router.message(AdminManagementStates.menu, F.text == "➖ Admin o'chirish")
async def delete_admin_step1(message: Message, state: FSMContext, session: AsyncSession):
    admin = await get_admin(session, message.from_user.id)
    if not await require_permission(admin, message, "admins:manage"):
        return

    await state.set_state(AdminManagementStates.delete_id)
    await message.answer("🗑 O'chiriladigan adminning <b>Telegram ID</b> sini kiriting:", reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")

@router.message(AdminManagementStates.delete_id)
async def delete_admin_step2(message: Message, state: FSMContext, session: AsyncSession):
    current_admin = await get_admin(session, message.from_user.id)
    if not await require_permission(current_admin, message, "admins:manage"):
        return

    if not message.text.isdigit():
        await message.answer("❌ ID raqam bo'lishi kerak.")
        return
    
    target_id = int(message.text)
    if target_id == message.from_user.id:
        await message.answer("❌ O'zingizni o'chira olmaysiz.")
        return

    admin = await get_admin(session, target_id)
    if not admin:
        await message.answer("❌ Admin topilmadi.")
    else:
        admin.is_active = False
        await log_admin_action(
            session,
            current_admin.id,
            "admin_delete",
            target_id=target_id,
            details=f"Deactivated admin @{admin.username or target_id}"
        )
        await session.commit()
        await message.answer(f"✅ Admin {target_id} o'chirildi.")
    
    await state.set_state(AdminManagementStates.menu)
    await message.answer("Menyu:", reply_markup=admin_management_menu())

@router.message(AdminManagementStates.menu, F.text == "⬅️ Orqaga")
async def back_to_main_admin(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    admin = await get_admin(session, message.from_user.id)
    await message.answer("Bosh menyu:", reply_markup=admin_main_keyboard(admin.role))

# --- ADVANCED FILTER / BULK / AUDIT ---

@router.callback_query(F.data == "filter:advanced")
async def advanced_filter_entry(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    admin = await get_admin(session, callback.from_user.id)
    if not await require_permission(admin, callback, "candidates:filter"):
        return

    await state.set_state(AdminStates.advanced_filter_input)
    await callback.message.edit_text(
        "🧩 <b>Murakkab filter</b>\n\n"
        "Format: <code>region=..., status=..., q=...</code>\n"
        "Misol: <code>region=Toshkent shahri, status=pending, q=Ali</code>\n"
        "Bo'sh qoldirish mumkin.",
        parse_mode="HTML",
    )


@router.message(AdminStates.advanced_filter_input)
async def advanced_filter_apply(message: Message, session: AsyncSession, state: FSMContext):
    admin = await get_admin(session, message.from_user.id)
    if not await require_permission(admin, message, "candidates:filter"):
        return

    raw = message.text.strip()
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    filt = {}
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            filt[k.strip().lower()] = v.strip()

    region = filt.get("region")
    status = filt.get("status")
    q = filt.get("q")

    query = select(Application, User).join(User, Application.user_id == User.id)
    if region:
        query = query.where(Application.region == region)
    if status:
        query = query.where(Application.final_status == status)
    if q:
        query = query.where((User.full_name.ilike(f"%{q}%")) | (User.phone_number.ilike(f"%{q}%")))

    rows = (await session.execute(query.order_by(Application.submitted_at.desc()).limit(50))).all()
    if not rows:
        await state.set_state(None)
        await message.answer("📭 Bu parametrlar bo'yicha nomzod topilmadi.")
        return

    builder = InlineKeyboardBuilder()
    for app, user in rows[:20]:
        builder.button(text=f"#{app.id} | {(user.full_name or '')[:20]}", callback_data=f"view_app:{app.id}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga (Filtrlar)", callback_data="back_to_filters"))
    await state.set_state(None)
    await message.answer(
        f"✅ Topildi: <b>{len(rows)}</b> ta\nNomzodni tanlang:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


@router.message(F.text == "📣 Bulk xabar")
async def bulk_entry(message: Message, session: AsyncSession, state: FSMContext):
    admin = await get_admin(session, message.from_user.id)
    if not await require_permission(admin, message, "broadcast:send"):
        return

    statuses = ["pending", "stage1_passed", "essay_submitted", "interview_scheduled", "accepted", "reserve", "rejected"]
    builder = InlineKeyboardBuilder()
    for st in statuses:
        builder.button(text=st, callback_data=f"bcast_status:{st}")
    builder.adjust(2)
    await state.set_state(AdminStates.broadcast_status)
    await message.answer("📣 Statusni tanlang:", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("bcast_status:"), AdminStates.broadcast_status)
async def bulk_status_selected(callback: CallbackQuery, state: FSMContext):
    status = callback.data.split(":", 1)[1]
    await state.update_data(broadcast_status=status)
    await state.set_state(AdminStates.broadcast_text)
    await callback.message.edit_text(
        f"✍️ Xabar matnini kiriting.\nTanlangan status: <b>{status}</b>",
        parse_mode="HTML",
    )


@router.message(AdminStates.broadcast_text)
async def bulk_send(message: Message, session: AsyncSession, state: FSMContext):
    admin = await get_admin(session, message.from_user.id)
    if not await require_permission(admin, message, "broadcast:send"):
        return

    data = await state.get_data()
    target_status = data.get("broadcast_status")
    text = message.text.strip()

    result = await session.execute(
        select(User.telegram_id)
        .join(Application, Application.user_id == User.id)
        .where(Application.final_status == target_status)
    )
    ids = [r[0] for r in result.all()]

    sent = 0
    for tg_id in ids:
        try:
            await message.bot.send_message(tg_id, f"📢 {text}")
            sent += 1
        except Exception:
            pass

    await log_admin_action(session, admin.id, "bulk_broadcast", details=f"status={target_status}, sent={sent}")
    await session.commit()
    await state.clear()
    await message.answer(f"✅ Bulk xabar yuborildi: {sent}/{len(ids)}")


@router.message(F.text == "🧾 Audit log")
async def audit_log_view(message: Message, session: AsyncSession):
    admin = await get_admin(session, message.from_user.id)
    if not await require_permission(admin, message, "audit:view"):
        return

    rows = (
        await session.execute(
            select(AdminActionLog, Admin)
            .join(Admin, Admin.id == AdminActionLog.admin_id)
            .order_by(AdminActionLog.created_at.desc())
            .limit(20)
        )
    ).all()

    if not rows:
        await message.answer("🧾 Audit log bo'sh.")
        return

    text = "🧾 <b>Oxirgi admin amallari</b>\n\n"
    for log_row, adm in rows:
        ts = log_row.created_at.strftime("%d.%m %H:%M") if log_row.created_at else "-"
        text += (
            f"• <b>{ts}</b> | @{adm.username or adm.telegram_id}\n"
            f"  {log_row.action} | target={log_row.target_id or '-'}\n"
            f"  {log_row.details or '-'}\n\n"
        )

    await message.answer(text[:4000], parse_mode="HTML")

