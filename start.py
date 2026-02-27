from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import User
from keyboards import contact_keyboard, main_menu_keyboard, join_channel_keyboard
from config import TELEGRAM_CHANNEL, INSTAGRAM_URL, LINKEDIN_URL

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession):
    # Foydalanuvchini bazadan qidirish
    result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalar_one_or_none()

    if not user:
        # Yangi foydalanuvchi yaratish
        user = User(
            telegram_id=message.from_user.id,
            full_name=message.from_user.full_name,
            is_verified=False
        )
        session.add(user)
        await session.commit()

        await message.answer(
            f"🚀 <b>Assalomu alaykum, {message.from_user.full_name}!</b>\n\n"
            "Yoshlar ishlari agentligi <b>Amaliyot ofisi</b> botiga xush kelibsiz! 🌟\n\n"
            "Kelajak yetakchisi bo'lish sari ilk qadamni qo'yish uchun, avval telefon raqamingizni tasdiqlang. 👇",
            reply_markup=contact_keyboard()
        )
    elif not user.is_verified:
        await message.answer(
            "📱 Iltimos, <b>'Raqamni yuborish'</b> tugmasini bosing:",
            reply_markup=contact_keyboard()
        )
    else:
        await message.answer(
            "🏠 <b>Bosh menyu</b>\nKerakli bo'limni tanlang:",
            reply_markup=main_menu_keyboard()
        )


@router.message(F.text == "📋 Loyiha haqida")
async def about_project(message: Message):
    text = (
        "🌟 <b>\"AMALIYOT OFISI\" LOYIHASI</b>\n\n"
        "Bu shunchaki loyiha emas, bu — <b>imkoniyatlar makoni!</b> 🚀\n\n"
        "🎯 <b>Maqsadimiz:</b> Yoshlar yetakchilarining bilim va ko‘nikmalarini real amaliyot orqali mustahkamlash va yangi darajaga olib chiqish.\n\n"
        "✨ <b>Sizni nimalar kutmoqda?</b>\n"
        "🔹 Eksklyuziv trening va seminarlar\n"
        "🔹 Tajribali mentorlar bilan uchrashuvlar\n"
        "🔹 Real loyihalarni boshqarish imkoniyati\n"
        "🔹 Liderlik va tashkilotchilik qobiliyatini rivojlantirish\n\n"
        "Biz bilan birga o'zgarishlarga tayyormisiz? 😎\n\n"
        "🔗 <b>Bizni kuzatib boring:</b>\n"
        "📢 <a href=\"https://t.me/amaliyot_ofisi\">Telegram</a>\n"
        "📸 <a href=\"https://www.instagram.com/amaliyot_ofisi?utm_source=qr&igsh=ZGd3aXJ3ZDNiZ3Fo\">Instagram</a>\n"
        "💼 <a href=\"https://www.linkedin.com/company/amaliyot-ofisi/posts/?feedView=all&viewAsMember=true\">LinkedIn</a>"
    )
    await message.answer(text, parse_mode="HTML")




@router.message(F.text == "📞 Bog'lanish")
async def contact_info(message: Message):
    await message.answer(
        "📞 <b>Biz bilan bog'lanish</b>\n\n"
        "Savollaringiz bormi? Bizga yozing! 👇\n\n"
        "📞 <b>Tel:</b> +998 99 476 32 21\n"
        "✈️ <b>Telegram:</b> @amaliyot_ofisi\n"
        "LinkedIn: https://www.linkedin.com/company/amaliyot-ofisi/"
    )

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
        
        # after saving verification, require Telegram channel membership
        try:
            member = await message.bot.get_chat_member(TELEGRAM_CHANNEL, message.from_user.id)
            is_member = member.status not in ("left", "kicked")
        except Exception:
            is_member = False

        if not is_member:
            text = (
                "✅ Raqamingiz tasdiqlandi!\n"
                "🎯 Iltimos, quyidagi ijtimoiy tarmoqlarimizga a'zo bo'ling va qaytib tekshiring:\n\n"
                f"• Telegram: https://t.me/{TELEGRAM_CHANNEL}\n"
                f"• Instagram: {INSTAGRAM_URL}\n"
                f"• LinkedIn: {LINKEDIN_URL}\n\n"
                "Botda davom etish uchun avvalo kanalga a'zo bo'ling.\n"
                "So'ngra \"✅ Tekshirish\" tugmasini bosing."
            )
            await message.answer(text, reply_markup=join_channel_keyboard(TELEGRAM_CHANNEL))
        else:
            await message.answer(
            "✅ Raqamingiz tasdiqlandi!\n"
            "Endi ariza topshirishingiz mumkin.",
            reply_markup=main_menu_keyboard()
        )