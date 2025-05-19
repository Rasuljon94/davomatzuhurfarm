
import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from config import API_TOKEN, ADMIN_IDS
from database import create_tables
from registration import router as registration_router
from attendance import router as attendance_router
from comments import router as comments_router
from admin import router as admin_router
from reports import router as reports_router
from tasks import send_birthday_congratulations
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
create_tables()

dp.include_router(attendance_router)
dp.include_router(registration_router)
dp.include_router(admin_router)
dp.include_router(comments_router)
dp.include_router(reports_router)

async def set_bot_commands(bot):
    await bot.set_my_commands([], scope=BotCommandScopeDefault())
    commands = [BotCommand(command="/delete_user", description="Foydalanuvchini o‘chirish")]
    for admin_id in ADMIN_IDS:
        try:
            await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception as e:
            print(f"[Xatolik] Slash komandalar {admin_id} uchun o‘rnatilmadi: {e}")

async def setup_scheduler():
    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
    scheduler.add_job(send_birthday_congratulations, "cron", hour=9, minute=0, args=[bot])
    scheduler.start()

async def main():
    await setup_scheduler()
    await set_bot_commands(bot)
    logging.info("✅ Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
