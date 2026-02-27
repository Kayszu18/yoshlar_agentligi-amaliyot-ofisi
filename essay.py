from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from states import EssayStates
from database import Application, Document, User

router = Router()


async def start_essay(message: Message, state: FSMContext):
    await state.set_state(EssayStates.upload)
    await message.answer(
        "📝 <b>2-BOSQICH: ESSE YOZISH</b>\n\n"
        "Mavzu: <b>\"Nega aynan meni Amaliyot ofisi loyihasiga qabul qilinishim kerak?\"</b> 🤔\n\n"
        "📋 <b>Talablar:</b>\n"
        "🔹 Hajmi: 3–5 sahifa\n"
        "🔹 Shrift: Times New Roman, 14\n"
        "🔹 Interval: 1.5\n\n"
        "📎 Iltimos, esseni <b>Word (.docx)</b> formatida tayyorlab, shu yerga yuklang:",
        parse_mode="HTML"
    )


@router.message(EssayStates.upload, F.document)
async def process_essay(message: Message, state: FSMContext, session: AsyncSession):
    doc = message.document
    
    # Accept .docx or .doc
    if not (doc.file_name.lower().endswith('.docx') or doc.file_name.lower().endswith('.doc')):
        await message.answer(
            "❌ Faqat Word (.docx yoki .doc) formatda yuklang.\n"
            "Esseni Microsoft Word da yozib, .docx formatda saqlang."
        )
        return
    
    # Find user and their application
    user_result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = user_result.scalar_one_or_none()
    if not user:
        await message.answer("❌ Xatolik: Foydalanuvchi topilmadi.")
        return
        
    app_result = await session.execute(select(Application).where(Application.user_id == user.id))
    app = app_result.scalar_one_or_none()
    if not app or app.final_status != 'stage1_passed':
        await message.answer("❌ Sizda esse topshirish uchun ruxsat yo'q yoki ariza topilmadi.")
        return

    # Save essay as a document
    essay_doc = Document(
        application_id=app.id,
        file_type='essay',
        file_path=doc.file_id,
        file_name=doc.file_name
    )
    session.add(essay_doc)
    
    # Update application status
    app.final_status = 'essay_submitted'
    app.current_stage = 2
    await session.commit()
    await state.clear()
    
    await message.answer("✅ Essengiz qabul qilindi va ko'rib chiqish uchun yuborildi.")
