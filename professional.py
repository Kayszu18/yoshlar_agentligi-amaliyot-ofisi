from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from states import ProfessionalStates
from keyboards import (
    yes_no_keyboard, lang_cert_keyboard, mega_projects_keyboard,
    initiative_keyboard, skip_keyboard, cancel_keyboard, back_keyboard, main_menu_keyboard
)
from services import ValidationService, FileService, UIService
from config import UPLOAD_DIR

router = Router()


async def start_professional(message: Message, state: FSMContext):
    await message.answer(UIService.progress(2, 4, "Professional ma'lumotlar"), parse_mode="HTML")
    await state.set_state(ProfessionalStates.obyektivka)
    await message.answer(
        "💼 <b>Navbat professional ma'lumotlarga!</b>\n\n"
        "7️⃣ Iltimos, <b>Obyektivkangizni (CV)</b> yuklang 📄\n"
        "<i>(PDF formatda, 5MB dan oshmasin)</i>\n\n"
        "<i>Jarayonni bekor qilish uchun '❌ Bekor qilish' tugmasini bosing.</i>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )


@router.message(ProfessionalStates.obyektivka, F.document)
async def process_obyektivka(message: Message, state: FSMContext):
    doc = message.document
    if not doc.file_name.lower().endswith('.pdf'):
        await message.answer("❌ Faqat PDF format qabul qilinadi.")
        return
    
    await state.update_data(obyektivka_file_id=doc.file_id, obyektivka_name=doc.file_name)
    await state.update_data(selected_certs=[])
    await state.set_state(ProfessionalStates.lang_cert_choice)
    await message.answer(
        "8️⃣ <b>Xorijiy tillarni bilasizmi?</b> 🌍\n\n"
        "Qaysi sertifikatlarga egasiz? (Bir nechtasini tanlashingiz mumkin):",
        reply_markup=lang_cert_keyboard([]),
        parse_mode="HTML"
    )


@router.message(ProfessionalStates.obyektivka)
async def process_obyektivka_invalid(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Ariza bekor qilindi.", reply_markup=main_menu_keyboard())
        return
    await message.answer("❌ Iltimos, PDF fayl yuboring.")


@router.message(
    F.text == "❌ Bekor qilish",
    ProfessionalStates.lang_cert_doc,
    ProfessionalStates.namunali_doc,
    ProfessionalStates.top100_doc,
    ProfessionalStates.initiative_doc,
    ProfessionalStates.additional_achievements_doc,
    ProfessionalStates.state_award_doc,
    ProfessionalStates.argos_doc,
)
async def cancel_at_doc_upload(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Ariza bekor qilindi.", reply_markup=main_menu_keyboard())


async def ask_for_next_cert_doc(message: Message, state: FSMContext):
    data = await state.get_data()
    certs_to_upload = data.get("certs_to_upload", [])

    if certs_to_upload:
        next_cert = certs_to_upload[0]
        await state.update_data(current_cert_upload=next_cert)
        await state.set_state(ProfessionalStates.lang_cert_doc)
        await message.answer(
            f"📎 <b>{next_cert}</b> sertifikatini yuklang (PDF, max 5MB):",
            parse_mode="HTML"
        )
    else:
        # All documents uploaded, move to the next step
        await message.answer("✅ Barcha sertifikatlar qabul qilindi.")
        await state.set_state(ProfessionalStates.namunali)
        await message.answer(
            "9️⃣ <b>\"Yilning eng namunali mahalla yoshlar yetakchisi\" tanlovida g'olib bo'lganmisiz?</b> 🏆",
            reply_markup=yes_no_keyboard("namunali"),
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("cert:"), ProfessionalStates.lang_cert_choice)
async def process_cert_choice(callback: CallbackQuery, state: FSMContext):
    cert = callback.data.split(":", 1)[1]
    data = await state.get_data()
    selected = data.get("selected_certs", [])

    if cert == "done":
        # If nothing selected or "Yo'q" is selected, just move on
        if not selected or "Yo'q" in selected:
            final_certs = ["Yo'q"] if not selected else selected
            await state.update_data(lang_certs=",".join(final_certs))
            await callback.message.edit_text("✅ Sertifikatlar bo'limi yakunlandi.")
            # Move to next question
            await state.set_state(ProfessionalStates.namunali)
            await callback.message.answer(
                "9️⃣ <b>\"Yilning eng namunali mahalla yoshlar yetakchisi\" tanlovida g'olib bo'lganmisiz?</b> 🏆",
                reply_markup=yes_no_keyboard("namunali"),
                parse_mode="HTML"
            )
        else:
            # Start the document upload loop
            await state.update_data(lang_certs=",".join(selected))
            await state.update_data(certs_to_upload=selected.copy())
            await callback.message.edit_text(f"✅ Tanlangan sertifikatlar: {', '.join(selected)}")
            await ask_for_next_cert_doc(callback.message, state)
        return

    if cert == "Yo'q":
        selected = ["Yo'q"]
    elif "Yo'q" in selected:
        selected = [cert]
    elif cert in selected:
        selected.remove(cert)
    else:
        selected.append(cert)

    await state.update_data(selected_certs=selected)
    await callback.message.edit_reply_markup(reply_markup=lang_cert_keyboard(selected))


@router.message(ProfessionalStates.lang_cert_doc, F.document)
async def process_cert_doc(message: Message, state: FSMContext):
    doc = message.document
    if not doc.file_name.lower().endswith('.pdf'):
        await message.answer("❌ Faqat PDF format qabul qilinadi.")
        return

    data = await state.get_data()
    current_cert = data.get("current_cert_upload")

    # Initialize cert_docs if it doesn't exist
    cert_docs = data.get("cert_docs", {})
    cert_docs[current_cert] = {
        "file_id": doc.file_id,
        "file_name": doc.file_name
    }
    await state.update_data(cert_docs=cert_docs)

    # Remove the uploaded cert from the list
    certs_to_upload = data.get("certs_to_upload", [])
    if certs_to_upload:
        certs_to_upload.pop(0)
    await state.update_data(certs_to_upload=certs_to_upload)

    await message.answer(f"✅ {current_cert} sertifikati qabul qilindi.")

    # Ask for the next one or finish
    await ask_for_next_cert_doc(message, state)


@router.callback_query(F.data.startswith("namunali:"), ProfessionalStates.namunali)
async def process_namunali(callback: CallbackQuery, state: FSMContext):
    answer = callback.data.split(":")[1]
    await state.update_data(namunali_winner=(answer == "ha"))
    
    if answer == "ha":
        await state.set_state(ProfessionalStates.namunali_doc)
        await callback.message.edit_text(
            "📎 Diplom yoki guvohnomasini yuklang (PDF, max 5MB):",
            reply_markup=back_keyboard("back_to_namunali_choice")
        )
    else:
        await callback.message.edit_text("✅ Qabul qilindi.")
        await process_next_after_namunali(callback.message, state)


@router.message(ProfessionalStates.namunali_doc, F.document)
async def process_namunali_doc(message: Message, state: FSMContext):
    await state.update_data(namunali_doc_id=message.document.file_id,
                             namunali_doc_name=message.document.file_name)
    await process_next_after_namunali(message, state)


@router.callback_query(F.data == "back_to_namunali_choice", ProfessionalStates.namunali_doc)
async def back_to_namunali(callback: CallbackQuery, state: FSMContext):
    # Reset the flag
    await state.update_data(namunali_winner=False)
    await state.set_state(ProfessionalStates.namunali)
    await callback.message.edit_text(
        "9️⃣ <b>\"Yilning eng namunali mahalla yoshlar yetakchisi\" tanlovida g'olib bo'lganmisiz?</b> 🏆",
        reply_markup=yes_no_keyboard("namunali"),
        parse_mode="HTML"
    )

async def process_next_after_namunali(message: Message, state: FSMContext):
    await state.set_state(ProfessionalStates.top100)
    await message.answer(
        "🔟 <b>\"Top 100\" yetakchilar reytingiga kirganmisiz?</b> 🥇",
        reply_markup=yes_no_keyboard("top100"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("top100:"), ProfessionalStates.top100)
async def process_top100(callback: CallbackQuery, state: FSMContext):
    answer = callback.data.split(":")[1]
    await state.update_data(top100_winner=(answer == "ha"))
    
    if answer == "ha":
        await state.set_state(ProfessionalStates.top100_doc)
        await callback.message.edit_text(
            "📎 Diplom yoki guvohnomasini yuklang (PDF, max 5MB):",
            reply_markup=back_keyboard("back_to_top100_choice")
        )
    else:
        await callback.message.edit_text("✅ Qabul qilindi.")
        await process_next_after_top100(callback.message, state)


@router.message(ProfessionalStates.top100_doc, F.document)
async def process_top100_doc(message: Message, state: FSMContext):
    await state.update_data(top100_doc_id=message.document.file_id,
                             top100_doc_name=message.document.file_name)
    await process_next_after_top100(message, state)


@router.callback_query(F.data == "back_to_top100_choice", ProfessionalStates.top100_doc)
async def back_to_top100(callback: CallbackQuery, state: FSMContext):
    await state.update_data(top100_winner=False)
    await state.set_state(ProfessionalStates.top100)
    await callback.message.edit_text(
        "🔟 <b>\"Top 100\" yetakchilar reytingiga kirganmisiz?</b> 🥇",
        reply_markup=yes_no_keyboard("top100"),
        parse_mode="HTML"
    )


async def process_next_after_top100(message: Message, state: FSMContext):
    await state.set_state(ProfessionalStates.initiative)
    await message.answer(
        "1️⃣1️⃣ <b>Besh tashabbus olimpiadasida yutuqlaringiz bormi?</b> 🎖\n"
        "Qaysi bosqichda g'olib bo'lgansiz?",
        reply_markup=initiative_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("initiative:"), ProfessionalStates.initiative)
async def process_initiative(callback: CallbackQuery, state: FSMContext):
    level = callback.data.split(":", 1)[1]
    
    if level == "yoq":
        await state.update_data(initiative_respublika=False, initiative_hudud=False, initiative_tuman=False)
        await callback.message.edit_text("✅ Qabul qilindi.")
        await process_next_after_initiative(callback.message, state)
    elif level == "Respublika bosqichi":
        await state.update_data(initiative_respublika=True)
        await state.set_state(ProfessionalStates.initiative_doc)
        await state.update_data(initiative_level=level)
        await callback.message.edit_text(
            f"📎 {level} diplom/guvohnomani yuklang (PDF):",
            reply_markup=back_keyboard("back_to_initiative_choice")
        )
    elif level == "Hududiy bosqich":
        await state.update_data(initiative_hudud=True)
        await state.set_state(ProfessionalStates.initiative_doc)
        await state.update_data(initiative_level=level)
        await callback.message.edit_text(
            f"📎 {level} diplom/guvohnomani yuklang (PDF):",
            reply_markup=back_keyboard("back_to_initiative_choice")
        )
    elif level == "Tuman bosqichi":
        await state.update_data(initiative_tuman=True)
        await state.set_state(ProfessionalStates.initiative_doc)
        await state.update_data(initiative_level=level)
        await callback.message.edit_text(
            f"📎 {level} diplom/guvohnomani yuklang (PDF):",
            reply_markup=back_keyboard("back_to_initiative_choice")
        )


@router.message(ProfessionalStates.initiative_doc, F.document)
async def process_initiative_doc(message: Message, state: FSMContext):
    data = await state.get_data()
    level = data.get("initiative_level", "initiative")
    safe_level = level.replace(" ", "_").lower()
    await state.update_data(**{
        f"initiative_{safe_level}_doc_id": message.document.file_id,
        f"initiative_{safe_level}_doc_name": message.document.file_name,
    })
    await process_next_after_initiative(message, state)


@router.callback_query(F.data == "back_to_initiative_choice", ProfessionalStates.initiative_doc)
async def back_to_initiative(callback: CallbackQuery, state: FSMContext):
    await state.update_data(initiative_respublika=False, initiative_hudud=False, initiative_tuman=False)
    await state.set_state(ProfessionalStates.initiative)
    await callback.message.edit_text(
        "1️⃣1️⃣ <b>Besh tashabbus olimpiadasida yutuqlaringiz bormi?</b> 🎖\n"
        "Qaysi bosqichda g'olib bo'lgansiz?",
        reply_markup=initiative_keyboard(),
        parse_mode="HTML"
    )


async def process_next_after_initiative(message: Message, state: FSMContext):
    await state.set_state(ProfessionalStates.additional_achievements)
    await message.answer(
        "1️⃣2️⃣ <b>Boshqa yutuqlaringiz bormi?</b> 🌟\n\n"
        "Sizda faxrlanadigan yana qanday natijalar bor?",
        reply_markup=yes_no_keyboard("achievements"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("achievements:"), ProfessionalStates.additional_achievements)
async def process_achievements_choice(callback: CallbackQuery, state: FSMContext):
    answer = callback.data.split(":")[1]
    if answer == "ha":
        await state.update_data(additional_achievements="Mavjud (Fayl yuklangan)")
        await state.set_state(ProfessionalStates.additional_achievements_doc)
        await callback.message.edit_text(
            "📎 Yutuqlaringizni tasdiqlovchi hujjatni yuklang (PDF, max 5MB):",
            reply_markup=back_keyboard("back_to_achievements_choice")
        )
    else:
        await state.update_data(additional_achievements="Yo'q")
        await state.update_data(achievements_doc_id=None)
        await callback.message.edit_text("✅ Qabul qilindi.")
        await ask_state_award(callback.message, state)


@router.message(ProfessionalStates.additional_achievements_doc, F.document)
async def process_achievements_doc(message: Message, state: FSMContext):
    doc = message.document
    if not doc.file_name.lower().endswith('.pdf'):
        await message.answer("❌ Faqat PDF format qabul qilinadi.")
        return
    await state.update_data(achievements_doc_id=doc.file_id,
                             achievements_doc_name=doc.file_name)
    await ask_state_award(message, state)


@router.callback_query(F.data == "back_to_achievements_choice", ProfessionalStates.additional_achievements_doc)
async def back_to_achievements(callback: CallbackQuery, state: FSMContext):
    await state.update_data(additional_achievements=None)
    await state.set_state(ProfessionalStates.additional_achievements)
    await callback.message.edit_text(
        "1️⃣2️⃣ <b>Boshqa yutuqlaringiz bormi?</b> 🌟\n\n"
        "Sizda faxrlanadigan yana qanday natijalar bor?",
        reply_markup=yes_no_keyboard("achievements"),
        parse_mode="HTML"
    )


async def ask_state_award(message: Message, state: FSMContext):
    await state.set_state(ProfessionalStates.state_award)
    await message.answer(
        "1️⃣3️⃣ <b>Davlat mukofoti yoki ko'krak nishoni bilan taqdirlanganmisiz?</b> 🎖",
        reply_markup=yes_no_keyboard("award"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("award:"), ProfessionalStates.state_award)
async def process_state_award(callback: CallbackQuery, state: FSMContext):
    answer = callback.data.split(":")[1]
    await state.update_data(state_award=(answer == "ha"))
    
    if answer == "ha":
        await state.set_state(ProfessionalStates.state_award_doc)
        await callback.message.edit_text(
            "📎 Hujjatni yuklang (PDF, max 5MB):",
            reply_markup=back_keyboard("back_to_award_choice")
        )
    else:
        await callback.message.edit_text("✅ Qabul qilindi.")
        await ask_argos(callback.message, state)


@router.message(ProfessionalStates.state_award_doc, F.document)
async def process_award_doc(message: Message, state: FSMContext):
    await state.update_data(award_doc_id=message.document.file_id,
                             award_doc_name=message.document.file_name)
    await ask_argos(message, state)


@router.callback_query(F.data == "back_to_award_choice", ProfessionalStates.state_award_doc)
async def back_to_award(callback: CallbackQuery, state: FSMContext):
    await state.update_data(state_award=False)
    await state.set_state(ProfessionalStates.state_award)
    await callback.message.edit_text(
        "1️⃣3️⃣ <b>Davlat mukofoti yoki ko'krak nishoni bilan taqdirlanganmisiz?</b> 🎖",
        reply_markup=yes_no_keyboard("award"),
        parse_mode="HTML"
    )


async def ask_argos(message: Message, state: FSMContext):
    await state.set_state(ProfessionalStates.argos)
    await message.answer(
        "1️⃣4️⃣ <b>Argos zaxira kadrlar ro'yxatida bormisiz?</b> 📋",
        reply_markup=yes_no_keyboard("argos"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("argos:"), ProfessionalStates.argos)
async def process_argos(callback: CallbackQuery, state: FSMContext):
    answer = callback.data.split(":")[1]
    await state.update_data(argos_status=(answer == "ha"))
    
    if answer == "ha":
        await state.set_state(ProfessionalStates.argos_doc)
        await callback.message.edit_text(
            "📎 Hujjatni yuklang (PDF, max 5MB):",
            reply_markup=back_keyboard("back_to_argos_choice")
        )
    else:
        await callback.message.edit_text("✅ Qabul qilindi.")
        await ask_social(callback.message, state)


@router.message(ProfessionalStates.argos_doc, F.document)
async def process_argos_doc(message: Message, state: FSMContext):
    await state.update_data(argos_doc_id=message.document.file_id,
                             argos_doc_name=message.document.file_name)
    await ask_social(message, state)


@router.callback_query(F.data == "back_to_argos_choice", ProfessionalStates.argos_doc)
async def back_to_argos(callback: CallbackQuery, state: FSMContext):
    await state.update_data(argos_status=False)
    await state.set_state(ProfessionalStates.argos)
    await callback.message.edit_text(
        "1️⃣4️⃣ <b>Argos zaxira kadrlar ro'yxatida bormisiz?</b> 📋",
        reply_markup=yes_no_keyboard("argos"),
        parse_mode="HTML"
    )


async def ask_social(message: Message, state: FSMContext):
    await state.set_state(ProfessionalStates.social_telegram)
    await message.answer(
        "1️⃣5️⃣ <b>Ijtimoiy tarmoqlarda faolmisiz?</b> 📱\n\n"
        "Siz yuritayotgan <b>Telegram</b> kanal yoki guruhingiz bormi? (Linkini yuboring)",
        reply_markup=yes_no_keyboard("social_tg"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("social_tg:"), ProfessionalStates.social_telegram)
async def process_social_tg_choice(callback: CallbackQuery, state: FSMContext):
    answer = callback.data.split(":")[1]
    if answer == "ha":
        await state.set_state(ProfessionalStates.social_telegram_input)
        await callback.message.edit_text("Telegram kanal yoki guruh havolasini (link) yuboring:")
    else:
        await state.update_data(social_telegram="")
        await callback.message.edit_text("✅ Qabul qilindi.")
        await ask_facebook(callback.message, state)


@router.message(ProfessionalStates.social_telegram_input)
async def process_social_tg_input(message: Message, state: FSMContext):
    await state.update_data(social_telegram=message.text.strip())
    await ask_facebook(message, state)


async def ask_facebook(message: Message, state: FSMContext):
    await state.set_state(ProfessionalStates.social_facebook)
    await message.answer(
        "Siz yuritayotgan <b>Facebook</b> sahifangiz yoki guruhingiz bormi?",
        reply_markup=yes_no_keyboard("social_fb"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("social_fb:"), ProfessionalStates.social_facebook)
async def process_social_fb_choice(callback: CallbackQuery, state: FSMContext):
    answer = callback.data.split(":")[1]
    if answer == "ha":
        await state.set_state(ProfessionalStates.social_facebook_input)
        await callback.message.edit_text("Facebook havolasini yuboring:")
    else:
        await state.update_data(social_facebook="")
        await callback.message.edit_text("✅ Qabul qilindi.")
        await ask_instagram(callback.message, state)


@router.message(ProfessionalStates.social_facebook_input)
async def process_social_fb_input(message: Message, state: FSMContext):
    await state.update_data(social_facebook=message.text.strip())
    await ask_instagram(message, state)


async def ask_instagram(message: Message, state: FSMContext):
    await state.set_state(ProfessionalStates.social_instagram)
    await message.answer(
        "Siz yuritayotgan <b>Instagram</b> sahifangiz bormi?",
        reply_markup=yes_no_keyboard("social_insta"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("social_insta:"), ProfessionalStates.social_instagram)
async def process_social_insta_choice(callback: CallbackQuery, state: FSMContext):
    answer = callback.data.split(":")[1]
    if answer == "ha":
        await state.set_state(ProfessionalStates.social_instagram_input)
        await callback.message.edit_text("Instagram havolasini yuboring:")
    else:
        await state.update_data(social_instagram="")
        await callback.message.edit_text("✅ Qabul qilindi.")
        await ask_mega_projects(callback.message, state)


@router.message(ProfessionalStates.social_instagram_input)
async def process_social_insta_input(message: Message, state: FSMContext):
    await state.update_data(social_instagram=message.text.strip())
    await ask_mega_projects(message, state)


async def ask_mega_projects(message: Message, state: FSMContext):
    await state.update_data(selected_mega=[])
    await state.set_state(ProfessionalStates.mega_projects)
    await message.answer(
        "1️⃣6️⃣ <b>Mega loyihalarda ishtirok etganmisiz?</b> 🚀\n\n"
        "Qaysi loyihalarda faol bo'lgansiz? (Bir nechtasini tanlash mumkin):",
        reply_markup=mega_projects_keyboard([]),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("mega:"), ProfessionalStates.mega_projects)
async def process_mega_projects(callback: CallbackQuery, state: FSMContext):
    project = callback.data.split(":", 1)[1]
    data = await state.get_data()
    selected = data.get("selected_mega", [])
    
    if project == "done":
        if not selected:
            await state.update_data(mega_projects="Yo'q")
            # Unset editing flag if it exists
            if data.get("is_editing"):
                await state.update_data(is_editing=False)

            await callback.message.edit_text("✅ Tanlangan: Yo'q")
            from finish import show_confirmation
            await show_confirmation(callback.message, state)
        else:
            await state.set_state(ProfessionalStates.mega_projects_count)
            await callback.message.edit_text(
                f"✅ Tanlangan: {', '.join(selected)}\n\n"
                "🔢 <b>Ushbu loyihalarga jami qancha yoshlarni jalb qilgansiz?</b>\n"
                "Raqam kiriting (masalan: 50):",
                parse_mode="HTML"
            )
        return
    
    if project in selected:
        selected.remove(project)
    else:
        selected.append(project)
    
    await state.update_data(selected_mega=selected)
    await callback.message.edit_reply_markup(reply_markup=mega_projects_keyboard(selected))


@router.message(ProfessionalStates.mega_projects_count)
async def process_mega_projects_count(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Iltimos, faqat raqam kiriting.")
        return
    
    count = message.text.strip()
    data = await state.get_data()
    selected = data.get("selected_mega", [])
    
    final_str = f"{', '.join(selected)} (Jalb qilinganlar: {count})"
    await state.update_data(mega_projects=final_str)
    
    # Unset editing flag if it exists
    if data.get("is_editing"):
        await state.update_data(is_editing=False)

    from finish import show_confirmation
    await show_confirmation(message, state)

