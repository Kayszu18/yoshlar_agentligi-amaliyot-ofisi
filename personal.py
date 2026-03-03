from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database import User, Application
from states import PersonalStates
from keyboards import (
    regions_keyboard, districts_keyboard, cancel_keyboard, main_menu_keyboard, back_keyboard
)
from services import ValidationService, UIService
from finish import show_confirmation

router = Router()


@router.message(F.text == "✍️ Ariza topshirish")
async def start_application(message: Message, session: AsyncSession, state: FSMContext):
    try:
        # Check if user already has an application
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            app_result = await session.execute(
                select(Application).where(Application.user_id == user.id)
            )
            existing_app = app_result.scalar_one_or_none()
            if existing_app:
                # If user passed stage 1, prompt for essay
                if existing_app.final_status == 'stage1_passed':
                    from essay import start_essay
                    await message.answer("✅ Siz 1-bosqichdan muvaffaqiyatli o'tdingiz!\n\nEndi 2-bosqich uchun esse yuborishingiz mumkin.")
                    await start_essay(message, state)
                    return

                # Show full application details
                from database import Score, Interview
                
                status_text = {
                    "pending": "⏳ Ko'rib chiqilmoqda",
                    "stage1_passed": "✅ 1-bosqichdan o'tdingiz (Esse yuborishingiz kutilmoqda)",
                    "stage1_rejected": "❌ 1-bosqichdan o'ta olmadingiz",
                    "essay_submitted": "📝 Essengiz qabul qilindi. Tekshirilmoqda...",
                    "stage2_passed": "✅ 2-bosqichdan (esse) o'tdingiz (Suhbat kutilmoqda)",
                    "stage2_rejected": "❌ 2-bosqichdan (esse) o'ta olmadingiz",
                    "interview_scheduled": "📅 Suhbat belgilandi",
                    "accepted": "🎉 Tabriklaymiz! Qabul qilindingiz",
                    "reserve": "🔄 Zaxiraga olindingiz",
                    "rejected": "❌ Rad etildi"
                }
                
                text = (
                    f"📋 <b>Sizning arizangiz</b>\n\n"
                    f"<b>Ariza raqami:</b> #{existing_app.id}\n"
                    f"<b>F.I.Sh:</b> {existing_app.user.full_name}\n"
                    f"<b>Topshirilgan vaqt:</b> {existing_app.submitted_at.strftime('%d.%m.%Y %H:%M')}\n"
                    f"<b>Holat:</b> {status_text.get(existing_app.final_status, existing_app.final_status)}\n\n"
                )
                
                # Get score if exists
                score_result = await session.execute(
                    select(Score).where(Score.application_id == existing_app.id).order_by(Score.scored_at.desc()).limit(1)
                )
                score = score_result.scalar_one_or_none()
                if score:
                    stage1_score = score.experience_score + score.results_score + score.motivation_score
                    total_max_score = 60 if score.essay_score is not None else 40
                    text += (
                        f"\n📊 <b>Ballar:</b>\n"
                        f"   • 1-bosqich: {stage1_score}/40\n"
                    )
                    if score.essay_score is not None:
                        text += f"   • Esse: {score.essay_score}/20\n"
                    text += f"   • <b>Jami: {score.total_score}/{total_max_score}</b>\n"
                
                # Get interview if exists
                interview_result = await session.execute(
                    select(Interview).where(Interview.application_id == existing_app.id).order_by(Interview.created_at.desc()).limit(1)
                )
                interview = interview_result.scalar_one_or_none()
                if interview and existing_app.final_status == "interview_scheduled":
                    text += (
                        f"\n📅 <b>Suhbat vaqti:</b> {interview.interview_date} {interview.interview_time}\n"
                        f"📍 <b>Manzil:</b> {interview.location}\n"
                    )
                
                text += "\n💡 <b>Yangi ariza yuborib bo'lmaydi.</b>\nHolatingizni '📊 Holatimni tekshirish' orqali kuzatib boring."
                
                await message.answer(text, parse_mode="HTML")
                return
    except Exception as e:
        import logging
        logging.error(f"Error in start_application: {str(e)}", exc_info=True)
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
        return
    
    await state.set_state(PersonalStates.full_name)
    await message.answer(UIService.progress(1, 4, "Shaxsiy ma'lumotlar"), parse_mode="HTML")
    await message.answer(
        "✍️ <b>1-BOSQICH: SHAXSIY MA'LUMOTLAR</b>\n\n"
        "🚀 <b>Keling, tanishib olamiz!</b>\n\n"
        "1️⃣ Iltimos, <b>to'liq ism-familiyangizni</b> kiriting:\n"
        "Misol: Sobirov Dilshodbek Saydullo o'g'li",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(PersonalStates.full_name)
async def process_full_name(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=main_menu_keyboard())
        return
    
    is_valid, error = ValidationService.validate_full_name(message.text)
    if not is_valid:
        await message.answer(error)
        return
    
    await state.update_data(full_name=message.text.strip())
    await state.set_state(PersonalStates.birth_date)
    await message.answer(
        "2️⃣ <b>Tug'ilgan sanangiz qachon?</b> 🎂\n"
        "Format: KK.OO.YYYY\nMisol: 15.06.1995",
        parse_mode="HTML"
    )


@router.message(PersonalStates.birth_date)
async def process_birth_date(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=main_menu_keyboard())
        return
    
    is_valid, error = ValidationService.validate_age(message.text.strip())
    if not is_valid:
        await message.answer(error)
        return
    
    await state.update_data(birth_date=message.text.strip())
    await state.set_state(PersonalStates.region)
    await message.answer(
        "3️⃣ <b>Qaysi viloyatdansiz?</b> 📍",
        reply_markup=regions_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("region:"), PersonalStates.region)
async def process_region(callback: CallbackQuery, state: FSMContext):
    region = callback.data.split(":", 1)[1]
    await state.update_data(region=region)
    
    from config import DISTRICTS
    from keyboards import districts_keyboard
    
    # Viloyat uchun tumanlar mavjudligini tekshirish
    if region not in DISTRICTS or not DISTRICTS.get(region):
        await callback.message.answer(f"Kechirasiz, '{region}' uchun tumanlar ro'yxati topilmadi. Iltimos, `config.py` faylini tekshiring.")
        await callback.answer() # To remove the "loading" icon on the button
        return
        
    await state.set_state(PersonalStates.district)
    await callback.message.edit_text(
        f"✅ Viloyat: <b>{region}</b>\n\n"
        f"4️⃣ <b>Tumaningizni belgilang:</b> 🏙",
        reply_markup=districts_keyboard(region),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "back_to_regions", PersonalStates.district)
async def back_to_region_select(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PersonalStates.region)
    await callback.message.edit_text(
        "3️⃣ <b>Qaysi viloyatdansiz?</b> 📍",
        reply_markup=regions_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("district:"), PersonalStates.district)
async def process_district(callback: CallbackQuery, state: FSMContext):
    district = callback.data.split(":", 1)[1]
    await state.update_data(district=district)
    await state.set_state(PersonalStates.mahalla)
    
    await callback.message.edit_text(
        f"✅ Tuman: <b>{district}</b>",
        parse_mode="HTML"
    )
    await callback.message.answer(
        "5️⃣ <b>Mahallangiz nomini yozing:</b> 🏘",
        parse_mode="HTML"
    )


@router.message(PersonalStates.mahalla)
async def process_mahalla(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=main_menu_keyboard())
        return
    
    await state.update_data(mahalla=message.text.strip())
    await state.set_state(PersonalStates.work_start_date)
    await message.answer(
        "6️⃣ <b>Yoshlar yetakchisi sifatida qachondan beri ishlaysiz?</b> 📅\n"
        "Format: KK.OO.YYYY\nMisol: 01.03.2022",
        parse_mode="HTML"
    )


@router.message(PersonalStates.work_start_date)
async def process_work_start_date(message: Message, state: FSMContext, session: AsyncSession):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=main_menu_keyboard())
        return
    
    try:
        datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except ValueError:
        await message.answer("❌ Sana formati noto'g'ri. Misol: 01.03.2022")
        return
    
    work_date_str = message.text.strip()
    experience = ValidationService.calculate_experience(work_date_str)
    await state.update_data(work_start_date=work_date_str, experience_years=experience)
    
    data = await state.get_data()
    
    # Check if we are in editing mode
    if data.get("is_editing"):
        await state.update_data(is_editing=False)  # Unset the flag
        await show_confirmation(message, state)
    else:
        await message.answer(
            f"✅ <b>Ajoyib! Sizda {experience} yillik tajriba bor.</b> 😎\n\n"
        )
        # Move to professional stage
        from professional import start_professional
        await start_professional(message, state)
