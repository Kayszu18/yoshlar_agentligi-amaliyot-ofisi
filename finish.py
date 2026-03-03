from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database import User, Application, Document, Admin
from states import ConfirmStates, PersonalStates, ProfessionalStates
from keyboards import confirm_keyboard, main_menu_keyboard, edit_application_keyboard
from services import UIService, DraftService

router = Router()


async def show_confirmation(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.set_state(ConfirmStates.confirm)
    await message.answer(UIService.progress(4, 4, "Yakuniy tasdiqlash"), parse_mode="HTML")
    
    certs = data.get("lang_certs", "Yo'q")
    cert_docs = data.get("cert_docs", {})
    if cert_docs:
        certs += f" (✅ {len(cert_docs)} ta hujjat yuklandi)"
        
    mega = data.get("mega_projects", "Yo'q")
    
    summary = (
        "🏁 <b>AJOYIB! ARIZANGIZ DEYARLI TAYYOR!</b> 🤩\n\n"
        f"👤 <b>F.I.Sh:</b> {data.get('full_name', '-')}\n"
        f"🎂 <b>Tug'ilgan sana:</b> {data.get('birth_date', '-')}\n"
        f"📍 <b>Viloyat:</b> {data.get('region', '-')}\n"
        f"🏙 <b>Tuman:</b> {data.get('district', '-')}\n"
        f"🏘 <b>Mahalla:</b> {data.get('mahalla', '-')}\n"
        f"📅 <b>Ish boshlagan sana:</b> {data.get('work_start_date', '-')}\n"
        f"⏳ <b>Tajriba:</b> {data.get('experience_years', 0)} yil\n\n"
        f"🌐 <b>Til sertifikatlari:</b> {certs}\n"
        f"🏆 <b>Namunali g'olib:</b> {'Ha' if data.get('namunali_winner') else 'Yo‘q'}\n"
        f"🥇 <b>Top 100:</b> {'Ha' if data.get('top100_winner') else 'Yo‘q'}\n"
        f"🎖 <b>Tashabbus (Res):</b> {'Ha' if data.get('initiative_respublika') else 'Yo‘q'}\n"
        f"🎖 <b>Tashabbus (Hud):</b> {'Ha' if data.get('initiative_hudud') else 'Yo‘q'}\n"
        f"🎖 <b>Tashabbus (Tum):</b> {'Ha' if data.get('initiative_tuman') else 'Yo‘q'}\n"
        f"🏅 <b>Davlat mukofoti:</b> {'Ha' if data.get('state_award') else 'Yo‘q'}\n"
        f"📋 <b>Argos:</b> {'Ha' if data.get('argos_status') else 'Yo‘q'}\n"
        f"📱 <b>Telegram:</b> {data.get('social_telegram', '-')}\n"
        f"🚀 <b>Mega loyihalar:</b> {mega}\n\n"
        f"🏅 <b>Qo'shimcha yutuqlar hujjati:</b> {'✅ Yuklangan' if data.get('achievements_doc_id') else '❌ Yuklanmagan'}\n"
        "<b>Barcha ma'lumotlar to'g'rimi? Tasdiqlaysizmi?</b> ✅"
    )
    
    await message.answer(summary, reply_markup=confirm_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "confirm:yes", ConfirmStates.confirm)
async def confirm_application(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot=None):
    data = await state.get_data()
    
    # Get user
    result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await callback.message.answer("❌ Foydalanuvchi topilmadi.")
        return
    
    # Create application
    app = Application(
        user_id=user.id,
        birth_date=data.get("birth_date"),
        region=data.get("region"),
        district=data.get("district"),
        mahalla=data.get("mahalla"),
        work_start_date=data.get("work_start_date"),
        experience_years=data.get("experience_years", 0),
        lang_certs=data.get("lang_certs"),
        namunali_winner=data.get("namunali_winner", False),
        top100_winner=data.get("top100_winner", False),
        initiative_respublika=data.get("initiative_respublika", False),
        initiative_hudud=data.get("initiative_hudud", False),
        initiative_tuman=data.get("initiative_tuman", False),
        additional_achievements=data.get("additional_achievements"),
        state_award=data.get("state_award", False),
        argos_status=data.get("argos_status", False),
        social_telegram=data.get("social_telegram"),
        social_facebook=data.get("social_facebook"),
        social_instagram=data.get("social_instagram"),
        mega_projects=data.get("mega_projects"),
        final_status="pending"
    )
    session.add(app)
    await session.flush()
    
    # Save documents references (file_ids stored, actual download optional)
    doc_pairs = [
        ("obyektivka", data.get("obyektivka_file_id"), data.get("obyektivka_name")),
        ("diploma_namunali", data.get("namunali_doc_id"), data.get("namunali_doc_name")),
        ("diploma_top100", data.get("top100_doc_id"), data.get("top100_doc_name")),
        ("achievements", data.get("achievements_doc_id"), data.get("achievements_doc_name")),
        ("award", data.get("award_doc_id"), data.get("award_doc_name")),
        ("argos", data.get("argos_doc_id"), data.get("argos_doc_name")),
    ]

    # Add certificate documents dynamically
    cert_docs = data.get("cert_docs", {})
    for cert_name, doc_info in cert_docs.items():
        safe_cert_name = cert_name.lower().replace(" ", "_")
        doc_pairs.append((f"sertifikat_{safe_cert_name}", doc_info.get("file_id"), doc_info.get("file_name")))

    # Add initiative documents dynamically
    from config import INITIATIVE_LEVELS
    for level in INITIATIVE_LEVELS:
        safe_level = level.replace(" ", "_").lower()
        doc_id_key = f"initiative_{safe_level}_doc_id"
        doc_name_key = f"initiative_{safe_level}_doc_name"
        if data.get(doc_id_key):
            doc_pairs.append((f"initiative_{safe_level}", data.get(doc_id_key), data.get(doc_name_key)))
    
    for file_type, file_id, file_name in doc_pairs:
        if file_id:
            doc = Document(
                application_id=app.id,
                file_type=file_type,
                file_path=file_id,  # Store Telegram file_id as path
                file_name=file_name or f"{file_type}.pdf"
            )
            session.add(doc)
    
    await session.commit()
    await state.clear()
    await DraftService.clear_draft(session, callback.from_user.id)
    
    # --- NEW ADMIN NOTIFICATION LOGIC ---
    if bot: # Ensure bot object is available
        try:
            admin_notification_text = (
                "🔔 <b>Yangi ariza kelib tushdi!</b>\n\n"
                f"🆔 Ariza ID: <code>#{app.id}</code>\n"
                f"👤 F.I.Sh: <b>{user.full_name}</b>\n"
                f"📞 Telefon: <code>{user.phone_number}</code>\n"
                f"📍 Manzil: {app.region}, {app.district}\n"
                f"⏰ Topshirilgan vaqt: {app.submitted_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                "Ko'rib chiqish uchun admin panelga kiring: /admin"
            )
            
            # Fetch all active admins
            admins_result = await session.execute(select(Admin).where(Admin.is_active == True))
            active_admins = admins_result.scalars().all()

            for admin in active_admins:
                try:
                    await bot.send_message(admin.telegram_id, admin_notification_text, parse_mode="HTML")
                except Exception as e:
                    import logging
                    logging.error(f"Failed to send new application notification to admin {admin.telegram_id}: {e}")
        except Exception as e:
            import logging
            logging.error(f"Error during admin notification for new application {app.id}: {e}")
    # --- END NEW ADMIN NOTIFICATION LOGIC ---

    await callback.message.edit_text(
        "🎉 <b>TABRIKLAYMIZ! ARIZANGIZ MUVAFFAQIYATLI QABUL QILINDI!</b> 🥳\n\n"
        f"📋 Ariza raqami: <code>#{app.id}</code>\n\n"
        "Sizning arizangiz ko'rib chiqish uchun yuborildi. Tez orada siz bilan bog'lanamiz! 🚀\n\n"
        "Holatingizni <b>'📊 Ariza holati'</b> tugmasi orqali kuzatib borishingiz mumkin.",
        parse_mode="HTML"
    )
    await callback.message.answer("🏠 Bosh menyu:", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "confirm:edit", ConfirmStates.confirm)
async def edit_application(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ConfirmStates.edit_choice)
    await callback.message.edit_text(
        "🔄 Qaysi bo'limni tahrirlashni xohlaysiz?",
        reply_markup=edit_application_keyboard()
    )


@router.callback_query(F.data == "edit:back_to_confirm", ConfirmStates.edit_choice)
async def back_to_confirmation(callback: CallbackQuery, state: FSMContext):
    """Returns user to the confirmation summary screen."""
    await callback.message.delete()
    await show_confirmation(callback.message, state)


@router.callback_query(F.data == "edit:personal", ConfirmStates.edit_choice)
async def edit_personal_info(callback: CallbackQuery, state: FSMContext):
    """Starts the personal info editing flow."""
    await state.update_data(is_editing=True)
    await state.set_state(PersonalStates.full_name)
    await callback.message.edit_text(
        "🔄 <b>Shaxsiy ma'lumotlarni tahrirlash</b>\n\n"
        "1️⃣ Iltimos, <b>to'liq ism-familiyangizni</b> qaytadan kiriting:",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "edit:professional", ConfirmStates.edit_choice)
async def edit_professional_info(callback: CallbackQuery, state: FSMContext):
    """Starts the professional info editing flow."""
    await state.update_data(is_editing=True)
    from professional import start_professional
    await callback.message.delete()
    await start_professional(callback.message, state)
