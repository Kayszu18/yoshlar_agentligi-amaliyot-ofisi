from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import User, Application, Score, Interview
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text == "📊 Ariza holati")
async def check_status(message: Message, session: AsyncSession):
    try:
        logger.info(f"Status check requested by user {message.from_user.id}")
        
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"User {message.from_user.id} not found in database")
            await message.answer("Siz hali ro'yxatdan o'tmagansiz. /start ni bosing.")
            return

        app_result = await session.execute(
            select(Application).where(Application.user_id == user.id)
        )
        app = app_result.scalar_one_or_none()

        if not app:
            logger.info(f"No application found for user {user.id}")
            await message.answer("📭 Siz hali ariza topshirmagansiz.")
            return

        status_text = {
            "pending": "⏳ <b>Ko'rib chiqilmoqda...</b> (Tez orada javob beramiz)",
            "stage1_passed": "🎉 <b>Tabriklaymiz! 1-bosqichdan o'tdingiz!</b>\nEndi esse yuborishingiz kerak.",
            "stage1_rejected": "❌ <b>Afsuski, 1-bosqichdan o'ta olmadingiz.</b>",
            "essay_submitted": "📝 <b>Essengiz qabul qilindi.</b> Tekshirilmoqda...",
            "stage2_passed": "🎉 <b>Ajoyib! Essengiz ma'qullandi.</b>\nSuhbat kutilmoqda.",
            "stage2_rejected": "❌ <b>Afsuski, esse bosqichidan o'ta olmadingiz.</b>",
            "interview_scheduled": "📅 <b>Suhbat belgilandi!</b> Tayyorgarlik ko'ring.",
            "accepted": "🥳 <b>TABRIKLAYMIZ! SIZ QABUL QILINDINGIZ!</b> 🚀",
            "reserve": "🔄 <b>Siz zaxira ro'yxatiga kiritildingiz.</b>",
            "rejected": "❌ <b>Arizangiz rad etildi.</b>"
        }

        text = (
            f"🆔 <b>ARIZA #{app.id}</b>\n"
            f"📅 Topshirilgan vaqt: {app.submitted_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"📊 Holat: <b>{status_text.get(app.final_status, app.final_status)}</b>\n"
        )

        score_result = await session.execute(
            select(Score).where(Score.application_id == app.id).order_by(Score.scored_at.desc()).limit(1)
        )
        score = score_result.scalar_one_or_none()
        if score:
            stage1_score = score.experience_score + score.results_score + score.motivation_score
            total_max_score = 60 if score.essay_score is not None else 40
            text += (
                f"\n⭐ <b>Ballar:</b>\n"
                f"   • 1-bosqich: {stage1_score}/40\n"
            )
            if score.essay_score is not None:
                text += f"   • Esse: {score.essay_score}/20\n"
            text += f"   • <b>Jami: {score.total_score}/{total_max_score}</b>\n"

        interview_result = await session.execute(
            select(Interview).where(Interview.application_id == app.id).order_by(Interview.created_at.desc()).limit(1)
        )
        interview = interview_result.scalar_one_or_none()
        if interview and app.final_status == "interview_scheduled":
            text += (
                f"\n📅 Suhbat vaqti: {interview.interview_date} {interview.interview_time}\n"
                f"📍 Manzil: {interview.location}\n"
            )

        logger.info(f"Sending status to user {message.from_user.id}")
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error in check_status: {str(e)}", exc_info=True)
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")