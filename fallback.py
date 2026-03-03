from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from keyboards import main_menu_keyboard

router = Router()


@router.message()
async def fallback_message(message: Message, state: FSMContext):
    """Handle unmatched messages so user is never left without feedback."""
    current_state = await state.get_state()
    if current_state:
        await message.answer(
            "❗️Xabar formati mos kelmadi. Iltimos, joriy bosqich bo'yicha kerakli ma'lumotni yuboring."
        )
        return

    await message.answer(
        "❗️Buyruq topilmadi. Iltimos, menyudan foydalaning.",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query()
async def fallback_callback(callback: CallbackQuery):
    """Handle unmatched callbacks from outdated or unknown buttons."""
    await callback.answer("❗️Bu tugma hozir ishlamaydi. Menyudan qayta urinib ko'ring.")

