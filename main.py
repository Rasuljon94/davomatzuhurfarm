import logging
import asyncio
from datetime import datetime  # tepada import qilingan bo‘lishi kerak
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
from tasks import scheduler, schedule_user_notifications, schedule_birthday_check
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR




logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
create_tables()

# 🚏 Routerlar (tartib muhim)
dp.include_router(registration_router)
dp.include_router(admin_router)
dp.include_router(attendance_router)
dp.include_router(reports_router)
dp.include_router(comments_router)   # ← keyin hodimlar izohlari



# 🛠 Adminlar va foydalanuvchilar uchun slash komandalarni belgilash
async def set_bot_commands(bot):
    # Oddiy foydalanuvchilarga faqat /start
    await bot.set_my_commands(
        [BotCommand(command="/start", description="Ro'yxatdan o'tish")],
        scope=BotCommandScopeDefault()
    )

    # Adminlar uchun to‘liq komandalar
    admin_commands = [
        BotCommand(command="/admin", description="Admin panel"),
        BotCommand(command="/add_user", description="Foydalanuvchini qo‘shish"),
        BotCommand(command="/edit_user", description="Foydalanuvchini tahrirlash"),
        BotCommand(command="/delete_user", description="Foydalanuvchini o‘chirish"),
        BotCommand(command="/version", description="Bot versiyasi"),
    ]

    for admin_id in ADMIN_IDS:
        try:
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception as e:
            print(f"[Xatolik] Slash komandalar {admin_id} uchun o‘rnatilmadi: {e}")


# 🚀 Botni ishga tushirish
async def main():
    print("🕒 Bot ishga tushgan vaqt:", datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
    await set_bot_commands(bot)
    logging.info("✅ Bot ishga tushdi!")

    # 📅 Bildirishnomalarni rejalashtirish
    # logging.getLogger("apscheduler").setLevel(logging.DEBUG)

    schedule_user_notifications(bot)
    schedule_birthday_check(bot)

    def listener(event):
        if event.exception:
            print(f"❌ Xatolik: {event}")
        else:
            print(f"✅ Eslatma yuborildi: {event.job_id}")


    scheduler.add_listener(listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    scheduler.start()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
