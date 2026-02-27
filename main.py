import asyncio
import logging
import os
import sys

from fastapi import FastAPI
import uvicorn

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
    SubscriptionMiddleware
)

# Import routers
from start import router as start_router
from status import router as status_router
from admin import router as admin_router
from personal import router as personal_router
from professional import router as professional_router
from essay import router as essay_router
from finish import router as finish_router

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app (health check uchun)
app = FastAPI()

@app.get("/")
async def health():
    return {"status": "running"}


async def start_bot():
    await init_db()
    logger.info("Database initialized")
    
    # Initialize default system settings
    from database import SystemSettings
    from sqlalchemy import select
    async with async_session() as session:
        result = await session.execute(select(SystemSettings).limit(1))
        if not result.scalar_one_or_none():
            settings = SystemSettings(system_status="active", min_passing_score=20)
            session.add(settings)
            await session.commit()
    
    # Proxy sozlamalari (agar mavjud bo'lsa)
    session = None
    if PROXY_URL:
        session = AiohttpSession(proxy=PROXY_URL)

    # Initialize Bot
    bot = Bot(
        token=BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Bot tavsiflarini o'rnatish (Start bosishdan oldin ko'rinadigan matnlar)
    try:
        await bot.set_my_description(
            "🌟 Assalomu alaykum!\n\n"
            "Yoshlar ishlari agentligi \"Amaliyot ofisi\" loyihasining rasmiy botiga xush kelibsiz! 🚀\n\n"
            "Bu yerda siz:\n"
            "✅ Loyiha haqida ma'lumot olishingiz;\n"
            "✅ Ariza topshirishingiz;\n"
            "✅ O'z holatingizni tekshirishingiz mumkin.\n\n"
            "Kelajak yetakchisi bo'lish sari ilk qadamni qo'ying! ✨"
        )
        await bot.set_my_short_description("Amaliyot ofisi — Yoshlar yetakchilari uchun imkoniyatlar makoni! 🚀")

        # Bot buyruqlari menyusini o'rnatish (Menu tugmasi)
        await bot.set_my_commands([
            BotCommand(command="start", description="🚀 Botni ishga tushirish"),
            BotCommand(command="admin", description="🔐 Admin panelga kirish"),
        ])
    except Exception as e:
        logger.warning(f"Tarmoq xatoligi tufayli bot tavsifi o'rnatilmadi: {e}")

    dp = Dispatcher(storage=MemoryStorage())
    
    # Register middlewares
    dp.message.middleware.register(RateLimitMiddleware())
    dp.message.middleware.register(MaintenanceMiddleware(async_session))
    dp.message.middleware.register(PhoneVerificationMiddleware(async_session))
    dp.message.middleware.register(SubscriptionMiddleware(bot))
    dp.callback_query.middleware.register(SubscriptionMiddleware(bot))
    
    # Session middleware - inject DB session (Har bir xabar uchun DB sessiyasini yaratish)
    async def db_session_middleware(handler, event, data):
        data["bot"] = bot
        async with async_session() as session:
            data["session"] = session
            return await handler(event, data)
    
    dp.message.middleware.register(db_session_middleware)
    dp.callback_query.middleware.register(db_session_middleware)
    
    # Routers
    dp.include_router(start_router)
    dp.include_router(admin_router)
    dp.include_router(status_router)
    dp.include_router(personal_router)
    dp.include_router(professional_router)
    dp.include_router(essay_router)
    dp.include_router(finish_router)
    
    # Bot commands
    await bot.set_my_commands([
        BotCommand(command="start", description="🚀 Botni ishga tushirish"),
        BotCommand(command="admin", description="🔐 Admin panel"),
    ])

    logger.info("Bot started polling...")
    await bot.delete_webhook(drop_pending_updates=True)
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


async def main():
    # Botni fonda ishga tushirish
    asyncio.create_task(start_bot())

    # Web serverni ishga tushirish
    port = int(os.environ.get("PORT", 8000))
    config = uvicorn.Config(app, host="0.0.0.0", port=port)
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi")
