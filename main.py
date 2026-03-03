import asyncio
import logging
import os
import sys
import tempfile

try:
    from fastapi import FastAPI
    import uvicorn
except ImportError:
    FastAPI = None
    uvicorn = None

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

sys.path.append(os.path.dirname(__file__))

from config import BOT_TOKEN, PROXY_URL
from database import init_db, async_session
from middlewares import (
    MaintenanceMiddleware,
    RateLimitMiddleware,
    PhoneVerificationMiddleware,
    SubscriptionMiddleware,
    DraftMiddleware,
)

# Import routers
from start import router as start_router
from status import router as status_router
from admin import router as admin_router
from personal import router as personal_router
from professional import router as professional_router
from essay import router as essay_router
from finish import router as finish_router
from fallback import router as fallback_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LOCK_PATH = os.path.join(tempfile.gettempdir(), "amaliyot_ofisi_bot.lock")


class SingleInstanceLock:
    def __init__(self, path: str):
        self.path = path
        self.fd = None

    def acquire(self) -> bool:
        try:
            self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.write(self.fd, str(os.getpid()).encode("utf-8"))
            return True
        except FileExistsError:
            return False

    def release(self):
        try:
            if self.fd is not None:
                os.close(self.fd)
            if os.path.exists(self.path):
                os.remove(self.path)
        except Exception:
            pass


app = FastAPI() if FastAPI else None

if app:
    @app.get("/")
    async def health():
        return {"status": "running"}


async def start_bot():
    await init_db()
    logger.info("Database initialized")

    from database import SystemSettings
    from sqlalchemy import select

    async with async_session() as session:
        result = await session.execute(select(SystemSettings).limit(1))
        if not result.scalar_one_or_none():
            settings = SystemSettings(
                system_status="active",
                min_passing_score=20,
                subscription_required=True,
            )
            session.add(settings)
            await session.commit()

    aio_session = None
    if PROXY_URL:
        aio_session = AiohttpSession(proxy=PROXY_URL)

    bot = Bot(
        token=BOT_TOKEN,
        session=aio_session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    try:
        await bot.set_my_commands([
            BotCommand(command="start", description="Botni ishga tushirish"),
            BotCommand(command="admin", description="Admin panel"),
            BotCommand(command="continue", description="Arizani davom ettirish"),
        ])
    except Exception as e:
        logger.warning(f"Bot command o'rnatilmadi: {e}")

    dp = Dispatcher(storage=MemoryStorage())

    async def db_session_middleware(handler, event, data):
        data["bot"] = bot
        async with async_session() as session:
            data["session"] = session
            return await handler(event, data)

    async def reminder_loop():
        from services import ReminderService

        while True:
            try:
                await ReminderService.run(async_session, bot)
            except Exception as e:
                logger.warning(f"Reminder loop error: {e}")
            await asyncio.sleep(900)

    dp.message.middleware.register(db_session_middleware)
    dp.callback_query.middleware.register(db_session_middleware)
    dp.message.middleware.register(RateLimitMiddleware())
    dp.message.middleware.register(MaintenanceMiddleware(async_session))
    dp.message.middleware.register(PhoneVerificationMiddleware(async_session))
    # Mandatory subscription is fully disabled from code (temporary hotfix).
    # Re-enable by registering SubscriptionMiddleware again.
    dp.message.middleware.register(DraftMiddleware())
    dp.callback_query.middleware.register(DraftMiddleware())

    dp.include_router(start_router)
    dp.include_router(admin_router)
    dp.include_router(status_router)
    dp.include_router(personal_router)
    dp.include_router(professional_router)
    dp.include_router(essay_router)
    dp.include_router(finish_router)
    dp.include_router(fallback_router)

    logger.info("Bot started polling...")
    await bot.delete_webhook(drop_pending_updates=True)

    reminder_task = asyncio.create_task(reminder_loop())
    try:
        await dp.start_polling(bot)
    finally:
        reminder_task.cancel()
        await bot.session.close()


async def main():
    if not (FastAPI and uvicorn and app):
        logger.warning("fastapi/uvicorn topilmadi, bot faqat polling rejimida ishga tushirildi.")
        await start_bot()
        return

    asyncio.create_task(start_bot())

    port = int(os.environ.get("PORT", 8000))
    config = uvicorn.Config(app, host="0.0.0.0", port=port)
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    lock = SingleInstanceLock(LOCK_PATH)
    if not lock.acquire():
        logger.error("Ikkinchi bot instance aniqlangan. Avval mavjud jarayonni to'xtating.")
        raise SystemExit(1)

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi")
    finally:
        lock.release()
