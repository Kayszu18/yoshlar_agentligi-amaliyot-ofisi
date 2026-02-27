from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from typing import Callable, Dict, Any, Awaitable
from datetime import datetime, timedelta
import asyncio


class MaintenanceMiddleware(BaseMiddleware):
    """Block users when bot is in maintenance mode"""
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        from database import SystemSettings, Admin
        from sqlalchemy import select
        
        async with self.session_factory() as session:
            result = await session.execute(select(SystemSettings).limit(1))
            settings = result.scalar_one_or_none()
            
            if settings and settings.system_status == "maintenance":
                # Check if user is admin
                if hasattr(event, 'from_user') and event.from_user:
                    admin_result = await session.execute(
                        select(Admin).where(
                            Admin.telegram_id == event.from_user.id,
                            Admin.is_active == True
                        )
                    )
                    admin = admin_result.scalar_one_or_none()
                    if admin:
                        return await handler(event, data)
                
                if isinstance(event, Message):
                    await event.answer(
                        "⚙️ Bot texnik ishlar sababli vaqtincha ishlamayapti.\n"
                        "Iltimos, keyinroq urinib ko'ring."
                    )
                return
        
        return await handler(event, data)


class RateLimitMiddleware(BaseMiddleware):
    """Rate limiting - max 30 messages per minute per user"""
    
    def __init__(self):
        self.user_timestamps: Dict[int, list] = {}
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not hasattr(event, 'from_user') or not event.from_user:
            return await handler(event, data)
        
        user_id = event.from_user.id
        now = datetime.now()
        
        if user_id not in self.user_timestamps:
            self.user_timestamps[user_id] = []
        
        # Remove timestamps older than 1 minute
        self.user_timestamps[user_id] = [
            ts for ts in self.user_timestamps[user_id]
            if now - ts < timedelta(minutes=1)
        ]
        
        if len(self.user_timestamps[user_id]) >= 30:
            if isinstance(event, Message):
                await event.answer("⚠️ Juda ko'p so'rovlar. Iltimos, bir daqiqa kuting.")
            return
        
        self.user_timestamps[user_id].append(now)
        return await handler(event, data)


class PhoneVerificationMiddleware(BaseMiddleware):
    """Ensure user has verified phone before accessing features"""
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.exempt_handlers = {'start', 'contact_handler', 'admin_handler'}
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Only check Messages
        if not isinstance(event, Message):
            return await handler(event, data)
        
        if not event.from_user:
            return await handler(event, data)
        
        # Skip /start and /admin commands
        if event.text and event.text.startswith(('/start', '/admin', '/help')):
            return await handler(event, data)
        
        # Skip contact messages
        if event.contact:
            return await handler(event, data)
        
        from database import User
        from sqlalchemy import select
        
        async with self.session_factory() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == event.from_user.id)
            )
            user = result.scalar_one_or_none()
            
            if not user or not user.is_verified:
                from keyboards import contact_keyboard
                await event.answer(
                    "📲 Davom etish uchun telefon raqamingizni yuboring:",
                    reply_markup=contact_keyboard()
                )
                return
        
        return await handler(event, data)


class SubscriptionMiddleware(BaseMiddleware):
    """Majburiy obuna tekshiruvi"""
    
    def __init__(self, bot):
        self.bot = bot
        self.required_channels = [
            # Kanal ID va Linklarini shu yerga kiritasiz
            {"id": "@yoshlar_agentligi", "name": "Yoshlar Agentligi", "url": "https://t.me/yoshlar_agentligi"},
        ]

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        from aiogram.enums import ChatMemberStatus

        if not isinstance(event, (Message, CallbackQuery)):
            return await handler(event, data)

        user = event.from_user
        if not user:
            return await handler(event, data)

        # Kontakt yuborilayotgan yoki start bosilgan bo'lsa o'tkazib yuboramiz
        if isinstance(event, Message):
            if event.contact or (event.text and event.text.startswith("/start")):
                return await handler(event, data)

        not_subscribed = []
        for channel in self.required_channels:
            try:
                member = await self.bot.get_chat_member(chat_id=channel["id"], user_id=user.id)
                if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED, ChatMemberStatus.RESTRICTED]:
                    not_subscribed.append(channel)
            except Exception:
                pass
        
        if not_subscribed:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[])
            for ch in not_subscribed:
                keyboard.inline_keyboard.append([InlineKeyboardButton(text=f"➕ {ch['name']}", url=ch['url'])])
            keyboard.inline_keyboard.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subs")])
            
            text = "⚠️ <b>Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:</b>"
            
            if isinstance(event, Message):
                await event.answer(text, reply_markup=keyboard, parse_mode="HTML")
            elif isinstance(event, CallbackQuery):
                if event.data == "check_subs":
                    await event.answer("❌ Hali hammasiga obuna bo'lmadingiz!", show_alert=True)
                else:
                    await event.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
                    await event.answer()
            return

        if isinstance(event, CallbackQuery) and event.data == "check_subs":
            await event.message.delete()
            await event.message.answer("✅ Obuna tasdiqlandi! Davom etishingiz mumkin.")
            return

        return await handler(event, data)
