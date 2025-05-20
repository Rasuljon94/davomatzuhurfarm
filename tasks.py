# 📁 tasks.py

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import get_birthdays_today, conn
from config import ADMIN_IDS
from datetime import datetime
from pytz import timezone

# ✅ Tashkent vaqti asosida scheduler
scheduler = AsyncIOScheduler(timezone=timezone("Asia/Tashkent"))

# 🎂 Tug‘ilgan kun tabrigi
async def send_birthday_congratulations(bot: Bot):
    birthdays = get_birthdays_today()
    if not birthdays:
        return

    # Tug‘ilgan kun egasiga va boshqalarga yuborish
    for name, surname, telegram_id in birthdays:
        full_name = f"{name} {surname}"
        # Hodimga o‘ziga tabrik
        try:
            await bot.send_message(
                telegram_id,
                f"🎉 Hurmatli {full_name},\n"
                f"Tug‘ilgan kuningiz muborak bo‘lsin! 🎂\n"
                f"Sizga sog‘liq, omad va yutuqlar tilaymiz! 🎈"
            )
        except Exception as e:
            print(f"⚠️ Hodimga yuborishda xatolik: {telegram_id} — {e}")

        # Adminlar va barcha boshqa hodimlarga e'lon
        cursor = conn.cursor()
        cursor.execute("SELECT telegram_id FROM users WHERE telegram_id != ?", (telegram_id,))
        recipients = [row[0] for row in cursor.fetchall()] + ADMIN_IDS
        for uid in recipients:
            try:
                await bot.send_message(
                    uid,
                    f"📢 Bugun {full_name} ning tug‘ilgan kuni! 🎉"
                )
            except Exception as e:
                print(f"⚠️ E'lon yuborishda xatolik: {uid} — {e}")

# ⏰ Har bir hodim uchun ish vaqti eslatmalari
async def send_start_reminder(bot: Bot, user_id: int):
    try:
        await bot.send_message(user_id, "⏰ Ish vaqtingiz boshlandi. 'Ishga keldim' tugmasini bosing.")
    except Exception as e:
        print(f"[Xatolik - ish boshlanishi] {user_id}: {e}")

async def send_end_reminder(bot: Bot, user_id: int):
    try:
        await bot.send_message(user_id, "🏁 Ish vaqtingiz tugadi. 'Ishdan ketdim' tugmasini bosing.")
    except Exception as e:
        print(f"[Xatolik - ish tugashi] {user_id}: {e}")

def schedule_user_notifications(bot: Bot):
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_id, start_time, end_time FROM users")
    for user_id, start, end in cursor.fetchall():
        try:
            hour_s, min_s = map(int, start.split(":"))
            scheduler.add_job(
                send_start_reminder,
                trigger="cron",
                hour=hour_s,
                minute=min_s,
                args=[bot, user_id],
                id=f"start_{user_id}",
                replace_existing=True
            )

            hour_e, min_e = map(int, end.split(":"))
            scheduler.add_job(
                send_end_reminder,
                trigger="cron",
                hour=hour_e,
                minute=min_e,
                args=[bot, user_id],
                id=f"end_{user_id}",
                replace_existing=True
            )
        except Exception as e:
            print(f"[Xatolik - bildirishnoma sozlash] {user_id}: {e}")

# 🎉 Tug‘ilgan kunni har kuni 08:00 da tekshirish
def schedule_birthday_check(bot: Bot):
    scheduler.add_job(
        send_birthday_congratulations,
        trigger="cron",
        hour=8,
        minute=0,
        args=[bot],
        id="birthday_job",
        replace_existing=True
    )
