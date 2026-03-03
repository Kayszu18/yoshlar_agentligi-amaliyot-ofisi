from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import User, Application
from keyboards import (
    contact_keyboard,
    main_menu_keyboard,
    cancel_keyboard,
    regions_keyboard,
    social_links_keyboard,
)
from config import DISTRICTS
from services import DraftService
from states import PersonalStates, ProfessionalStates, EssayStates, ConfirmStates

router = Router()


@router.callback_query(F.data.in_({"check_all_subs", "check_subs"}))
async def subscription_check_callback(callback: CallbackQuery):
    """Route subscription check callbacks so middleware can process them."""
    try:
        await callback.answer()
    except Exception:
        pass


@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession):
    result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            telegram_id=message.from_user.id,
            full_name=message.from_user.full_name,
            is_verified=False,
        )
        session.add(user)
        await session.commit()

        await message.answer(
            f"🚀 <b>Assalomu alaykum, {message.from_user.full_name}!</b>\n\n"
            "Amaliyot ofisi botiga xush kelibsiz. Avval telefon raqamingizni tasdiqlang.",
            reply_markup=contact_keyboard(),
            parse_mode="HTML",
        )
    elif not user.is_verified:
        await message.answer(
            "📱 Iltimos, <b>Raqamni yuborish</b> tugmasini bosing.",
            reply_markup=contact_keyboard(),
            parse_mode="HTML",
        )
    else:
        await message.answer("🏠 <b>Bosh menyu</b>", reply_markup=main_menu_keyboard(), parse_mode="HTML")


@router.message(Command("continue"))
@router.message(F.text == "▶️ Davom ettirish")
async def continue_draft(message: Message, state: FSMContext, session: AsyncSession):
    draft = await DraftService.get_draft(session, message.from_user.id)
    if not draft:
        await message.answer("ℹ️ Saqlangan draft topilmadi.", reply_markup=main_menu_keyboard())
        return

    state_name = draft["state_name"]
    state_data = draft["state_data"]

    await state.set_state(state_name)
    await state.set_data(state_data)

    prompt_map = {
        str(PersonalStates.full_name): "1/4 Shaxsiy: To'liq F.I.Sh kiriting.",
        str(PersonalStates.birth_date): "1/4 Shaxsiy: Tug'ilgan sana (KK.OO.YYYY).",
        str(PersonalStates.region): "1/4 Shaxsiy: Viloyatni tanlang.",
        str(PersonalStates.district): "1/4 Shaxsiy: Tumanni tanlang.",
        str(PersonalStates.mahalla): "1/4 Shaxsiy: Mahalla nomini kiriting.",
        str(PersonalStates.work_start_date): "1/4 Shaxsiy: Ish boshlagan sana (KK.OO.YYYY).",
        str(ProfessionalStates.obyektivka): "2/4 Professional: CV (PDF) yuklang.",
        str(EssayStates.upload): "3/4 Esse: Word faylni (.doc/.docx) yuklang.",
        str(ConfirmStates.confirm): "4/4 Tasdiqlash: ma'lumotlarni tekshirib tasdiqlang.",
    }

    text = prompt_map.get(state_name, f"Draft tiklandi. Davom eting: {state_name}")

    if state_name == str(PersonalStates.region):
        await message.answer(text, reply_markup=regions_keyboard())
    elif state_name == str(PersonalStates.district):
        region = state_data.get("region")
        if region in DISTRICTS:
            from keyboards import districts_keyboard
            await message.answer(text, reply_markup=districts_keyboard(region))
        else:
            await message.answer("Viloyat qayta tanlanishi kerak.", reply_markup=regions_keyboard())
    elif state_name in (str(PersonalStates.full_name), str(ProfessionalStates.obyektivka)):
        await message.answer(text, reply_markup=cancel_keyboard())
    else:
        await message.answer(text)


@router.message(F.text == "❓ FAQ")
async def faq_menu(message: Message):
    await message.answer(
        "❓ <b>FAQ</b>\n\n"
        "1) Ariza jarayoni: Shaxsiy -> Professional -> Esse -> Tasdiqlash\n"
        "2) Fayl formatlari: CV/PDF, esse/docx\n"
        "3) Holatni tekshirish: '📊 Ariza holati'\n"
        "4) Draftni davom ettirish: /continue",
        parse_mode="HTML",
    )


@router.message(F.text == "📋 Loyiha haqida")
async def about_project(message: Message):
    text = (
        "🌟 <b>\"AMALIYOT OFISI\" LOYIHASI</b>\n\n"
        "Bu shunchaki loyiha emas, bu — <b>imkoniyatlar makoni</b>.\n\n"
        "🎯 <b>Maqsadimiz:</b> yoshlar yetakchilarining bilim va ko'nikmalarini\n"
        "real amaliyot orqali mustahkamlash va yangi darajaga olib chiqish.\n\n"
        "✨ <b>Sizni nimalar kutmoqda?</b>\n"
        "• Eksklyuziv trening va seminarlar\n"
        "• Tajribali mentorlar bilan uchrashuvlar\n"
        "• Real loyihalarda ishtirok etish\n"
        "• Liderlik va tashkiliy ko'nikmalarni rivojlantirish\n\n"
        "🚀 Biz bilan birga o'zgarishga tayyormisiz?"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=social_links_keyboard())


@router.message(F.text == "📞 Bog'lanish")
async def contact_info(message: Message):
    text = (
        "📞 <b>Biz bilan bog'lanish</b>\n\n"
        "Savollaringiz bormi? Bizga yozing 👇\n\n"
        "☎️ Tel: <b>+998 99 476 32 21</b>\n"
        "✈️ Telegram: <b>@amaliyot_ofisi</b>\n"
        "🕘 Ish vaqti: <b>09:00 - 18:00</b>\n\n"
        "🔗 Ijtimoiy sahifalar:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=social_links_keyboard())


@router.message(F.contact)
async def process_contact(message: Message, session: AsyncSession):
    if message.contact.user_id != message.from_user.id:
        await message.answer("❌ Iltimos, o'zingizning raqamingizni yuboring.")
        return

    result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalar_one_or_none()

    if user:
        user.phone_number = message.contact.phone_number
        user.is_verified = True
        await session.commit()
        await message.answer(
            "✅ Raqamingiz tasdiqlandi!", reply_markup=main_menu_keyboard()
        )
