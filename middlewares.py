from datetime import datetime, timedelta
from typing import Callable, Dict, Any, Awaitable
import logging

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)


class MaintenanceMiddleware(BaseMiddleware):
    """Block users when bot is in maintenance mode."""

    def __init__(self, session_factory):
        self.session_factory = session_factory
        self._status_cache: str | None = None
        self._status_cached_at: datetime | None = None
        self._status_ttl = timedelta(seconds=5)

    async def _get_system_status(self, session) -> str:
        from database import SystemSettings
        from sqlalchemy import select

        now = datetime.now()
        if (
            self._status_cache is not None
            and self._status_cached_at is not None
            and now - self._status_cached_at < self._status_ttl
        ):
            return self._status_cache

        result = await session.execute(select(SystemSettings).limit(1))
        settings = result.scalar_one_or_none()
        status = settings.system_status if settings else "active"

        self._status_cache = status
        self._status_cached_at = now
        return status

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        from database import Admin
        from sqlalchemy import select

        session = data.get("session")
        session_ctx = None
        if session is None:
            session_ctx = self.session_factory()
            session = await session_ctx.__aenter__()

        try:
            if await self._get_system_status(session) == "maintenance":
                if hasattr(event, "from_user") and event.from_user:
                    admin_result = await session.execute(
                        select(Admin).where(
                            Admin.telegram_id == event.from_user.id,
                            Admin.is_active == True,
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
        finally:
            if session_ctx is not None:
                await session_ctx.__aexit__(None, None, None)

        return await handler(event, data)


class RateLimitMiddleware(BaseMiddleware):
    """Rate limiting - max 30 messages per minute per user."""

    def __init__(self):
        self.user_timestamps: Dict[int, list] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not hasattr(event, "from_user") or not event.from_user:
            return await handler(event, data)

        user_id = event.from_user.id
        now = datetime.now()

        if user_id not in self.user_timestamps:
            self.user_timestamps[user_id] = []

        self.user_timestamps[user_id] = [
            ts for ts in self.user_timestamps[user_id] if now - ts < timedelta(minutes=1)
        ]

        if len(self.user_timestamps[user_id]) >= 30:
            if isinstance(event, Message):
                await event.answer("⚠️ Juda ko'p so'rovlar. Iltimos, bir daqiqa kuting.")
            return

        self.user_timestamps[user_id].append(now)
        return await handler(event, data)


class PhoneVerificationMiddleware(BaseMiddleware):
    """Ensure user has verified phone before accessing features."""

    def __init__(self, session_factory):
        self.session_factory = session_factory
        self._verify_cache: Dict[int, tuple[bool, datetime]] = {}
        self._cache_ttl = timedelta(seconds=30)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        if not event.from_user:
            return await handler(event, data)

        if event.text and event.text.startswith(("/start", "/admin", "/help")):
            return await handler(event, data)

        if event.contact:
            return await handler(event, data)

        user_id = event.from_user.id
        now = datetime.now()
        cached = self._verify_cache.get(user_id)
        if cached and (now - cached[1] < self._cache_ttl):
            if cached[0]:
                return await handler(event, data)
            from keyboards import contact_keyboard

            await event.answer(
                "📲 Davom etish uchun telefon raqamingizni yuboring:",
                reply_markup=contact_keyboard(),
            )
            return

        from database import User
        from sqlalchemy import select

        session = data.get("session")
        session_ctx = None
        if session is None:
            session_ctx = self.session_factory()
            session = await session_ctx.__aenter__()

        try:
            result = await session.execute(select(User).where(User.telegram_id == user_id))
            user = result.scalar_one_or_none()
            is_verified = bool(user and user.is_verified)
            self._verify_cache[user_id] = (is_verified, now)

            if not is_verified:
                from keyboards import contact_keyboard

                await event.answer(
                    "📲 Davom etish uchun telefon raqamingizni yuboring:",
                    reply_markup=contact_keyboard(),
                )
                return
        finally:
            if session_ctx is not None:
                await session_ctx.__aexit__(None, None, None)

        return await handler(event, data)


class SubscriptionMiddleware(BaseMiddleware):
    """Mandatory subscription check for Telegram channel + social links flow."""

    def __init__(self, bot):
        self.bot = bot
        from config import TELEGRAM_CHANNEL, INSTAGRAM_URL, LINKEDIN_URL

        raw_channel = str(TELEGRAM_CHANNEL or "").strip()
        raw_channel = raw_channel.split("#", 1)[0].strip()
        raw_channel = raw_channel.replace("https://t.me/", "").replace("http://t.me/", "").strip("/")
        raw_channel = raw_channel.split()[0] if raw_channel else ""

        if raw_channel.startswith("@"):
            raw_channel = raw_channel[1:]

        if raw_channel.lstrip("-").isdigit():
            channel_id = raw_channel
            channel_username = ""
        elif raw_channel:
            channel_id = f"@{raw_channel}"
            channel_username = raw_channel
        else:
            channel_id = ""
            channel_username = ""

        self.required_channels = [
            {
                "id": channel_id,
                "name": "Rasmiy kanal",
                "url": f"https://t.me/{channel_username}" if channel_username else "https://t.me",
            },
        ]

        raw_links = [
            f"https://t.me/{channel_username}" if channel_username else "https://t.me",
            str(INSTAGRAM_URL or "").strip(),
            str(LINKEDIN_URL or "").strip(),
        ]
        deduped_links: list[str] = []
        for link in raw_links:
            if not link:
                continue
            if not (link.startswith("http://") or link.startswith("https://")):
                continue
            if link not in deduped_links:
                deduped_links.append(link)
        self.required_links = deduped_links or ["https://t.me"]

        self._sub_cache: Dict[int, tuple[bool, datetime]] = {}
        self._sub_cache_ttl = timedelta(minutes=5)
        self._sub_error_cache: Dict[int, tuple[str, datetime]] = {}
        self._sub_error_ttl = timedelta(minutes=1)
        self._required_cache: bool | None = None
        self._required_cached_at: datetime | None = None
        self._required_ttl = timedelta(seconds=5)

    def _build_sub_keyboard(self) -> InlineKeyboardMarkup:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for link in self.required_links:
            keyboard.inline_keyboard.append([InlineKeyboardButton(text="❌ A'zo bo'lish", url=link)])
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔄 Tekshirish", callback_data="check_all_subs")])
        return keyboard

    @staticmethod
    def _format_subscription_error(exc: Exception) -> str:
        err_type = type(exc).__name__
        err_text = str(exc).strip()
        err_lower = err_text.lower()

        if err_type == "TelegramBadRequest":
            if "member list is inaccessible" in err_lower:
                return (
                    "⚙️ Kanal obunasini tekshirib bo'lmadi: kanal a'zolari ro'yxati yopiq. "
                    "Botni kanalga admin qilib qo'ying."
                )
            if "chat not found" in err_lower:
                return (
                    "⚙️ Kanal topilmadi. TELEGRAM_CHANNEL qiymati yoki botning kanalga qo'shilganini tekshiring."
                )
            if "bot is not a member" in err_lower:
                return "⚙️ Bot kanalga qo'shilmagan. Avval botni kanalga qo'shing."
            return "⚙️ Telegram kanal tekshiruvida xatolik. Kanal sozlamalari va bot huquqlarini tekshiring."

        if err_type == "TelegramNetworkError":
            return "⚙️ Telegram bilan aloqa vaqtincha uzildi. Bir necha soniyadan keyin qayta urinib ko'ring."

        return f"⚙️ Obuna tekshiruvida xatolik: {err_type}"

    async def _is_subscription_required(self, session) -> bool:
        from database import SystemSettings
        from sqlalchemy import select

        now = datetime.now()
        if (
            self._required_cache is not None
            and self._required_cached_at is not None
            and now - self._required_cached_at < self._required_ttl
        ):
            return self._required_cache

        try:
            result = await session.execute(select(SystemSettings).limit(1))
            settings = result.scalar_one_or_none()
            required = (
                settings.subscription_required
                if settings and settings.subscription_required is not None
                else True
            )
        except Exception:
            required = True

        self._required_cache = bool(required)
        self._required_cached_at = now
        return self._required_cache

    async def _is_subscribed(self, user_id: int, force_refresh: bool = False) -> tuple[bool, str]:
        from aiogram.enums import ChatMemberStatus

        if not self.required_channels[0]["id"]:
            return True, ""

        now = datetime.now()
        cached = self._sub_cache.get(user_id)
        if cached and not force_refresh and now - cached[1] < self._sub_cache_ttl:
            err_cached = self._sub_error_cache.get(user_id)
            err_text = (
                err_cached[0]
                if err_cached and now - err_cached[1] < self._sub_error_ttl
                else "Obuna tasdiqlanmadi."
            )
            return cached[0], err_text

        for channel in self.required_channels:
            try:
                member = await self.bot.get_chat_member(chat_id=channel["id"], user_id=user_id)
                if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
                    reason = "Telegram kanalga hali a'zo bo'lmagansiz."
                    self._sub_cache[user_id] = (False, now)
                    self._sub_error_cache[user_id] = (reason, now)
                    return False, reason
            except Exception as e:
                reason = self._format_subscription_error(e)
                logger.warning("Subscription check failed for user %s: %s", user_id, reason)
                self._sub_cache[user_id] = (False, now)
                self._sub_error_cache[user_id] = (reason, now)
                return False, reason

        self._sub_cache[user_id] = (True, now)
        self._sub_error_cache[user_id] = ("", now)
        return True, ""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, (Message, CallbackQuery)):
            return await handler(event, data)

        user = event.from_user
        if not user:
            return await handler(event, data)

        session = data.get("session")
        if session is not None and not await self._is_subscription_required(session):
            return await handler(event, data)

        if isinstance(event, Message) and event.text and event.text.startswith(("/start", "/admin")):
            return await handler(event, data)

        check_callbacks = {"check_all_subs", "check_subs"}
        is_check_click = isinstance(event, CallbackQuery) and event.data in check_callbacks

        subscribed, reason = await self._is_subscribed(user.id, force_refresh=is_check_click)

        if not subscribed:
            text = "⚠️ <b>Davom etish uchun quyidagi sahifalarga a'zo bo'ling:</b>"
            keyboard = self._build_sub_keyboard()

            if isinstance(event, Message):
                await event.answer(text, reply_markup=keyboard, parse_mode="HTML")
                return

            # CallbackQuery path
            if is_check_click:
                try:
                    if reason.startswith("⚙️"):
                        await event.answer("⚠️ Tekshiruvda texnik muammo", show_alert=False)
                    else:
                        await event.answer(f"❌ {reason}", show_alert=True)
                except Exception:
                    pass

                # Also send visible chat message so user always sees a result
                if event.message:
                    await event.message.answer(
                        f"❌ <b>Tekshirish natijasi:</b> {reason}",
                        reply_markup=keyboard,
                        parse_mode="HTML",
                    )
                return

            if event.message:
                await event.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            try:
                await event.answer()
            except Exception:
                pass
            return

        # Subscribed flow for check button
        if is_check_click:
            try:
                await event.answer("✅ Tekshirildi")
            except Exception:
                pass

            if event.message:
                try:
                    await event.message.delete()
                except Exception:
                    pass
                await event.message.answer("✅ Hammasi tasdiqlandi! Davom etishingiz mumkin.")
            return

        return await handler(event, data)


class DraftMiddleware(BaseMiddleware):
    """Autosave FSM draft after each handled update."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        result = await handler(event, data)

        user = getattr(event, "from_user", None)
        session = data.get("session")
        fsm_state = data.get("state")
        if not user or not session or not fsm_state:
            return result

        try:
            state_name = await fsm_state.get_state()
            if state_name:
                state_data = await fsm_state.get_data()
                from services import DraftService

                await DraftService.save_draft(session, user.id, state_name, state_data)
        except Exception:
            # Draft save must never break user flow
            pass

        return result
