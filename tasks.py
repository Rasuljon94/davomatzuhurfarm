# 📁 tasks.py

from aiogram import Bot
from database import get_birthdays_today

async def send_birthday_congratulations(bot: Bot):
    birthdays = get_birthdays_today()
    if not birthdays:
        return

    for name, surname, telegram_id in birthdays:
        try:
            await bot.send_message(
                telegram_id,
                f"🎉 Hurmatli {name} {surname},\n"
                f"Tug‘ilgan kuningiz muborak bo‘lsin! 🎂\n"
                f"Sizga sog‘liq, omad va yutuqlar tilaymiz! 🎈"
            )
        except Exception as e:
            print(f"⚠️ Tabrik yuborishda xatolik: {telegram_id} — {e}")
