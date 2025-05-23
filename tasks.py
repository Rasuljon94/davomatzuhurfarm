# 📁 tasks.py

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import get_birthdays_today, has_checked_in_today, conn
from config import ADMIN_IDS
from datetime import datetime,timedelta
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
            start_dt = datetime.strptime(start, "%H:%M")
            end_dt = datetime.strptime(end, "%H:%M")
            early_time = (start_dt - timedelta(minutes=20)).time()

            # 🟩 20 daqiqa oldin ogohlantirish
            scheduler.add_job(
                send_early_reminder,
                trigger="cron",
                hour=early_time.hour,
                minute=early_time.minute,
                args=[bot, user_id],
                id=f"early_{user_id}",
                replace_existing=True
            )

            # 🟩 Ish vaqti boshlandi (faqat ishga kelmagan bo‘lsa)
            scheduler.add_job(
                lambda: remind_if_not_checked_in(bot, user_id),
                trigger="cron",
                hour=start_dt.hour,
                minute=start_dt.minute,
                id=f"start_{user_id}",
                replace_existing=True
            )

            # 🟩 Ish tugashi
            scheduler.add_job(
                send_end_reminder,
                trigger="cron",
                hour=end_dt.hour,
                minute=end_dt.minute,
                args=[bot, user_id],
                id=f"end_{user_id}",
                replace_existing=True
            )

            # 🟩 10 va 20 daqiqa kechikib bosmaganlar uchun ogohlantirish
            for i in range(2):
                remind_time = start_dt + timedelta(minutes=10 * (i + 1))
                scheduler.add_job(
                    remind_unchecked_user_once,
                    trigger="cron",
                    hour=remind_time.hour,
                    minute=remind_time.minute,
                    args=[bot, user_id, i + 1],
                    id=f"remind_{user_id}_{i+1}",
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
async def send_early_reminder(bot: Bot, user_id: int):
    try:
        await bot.send_message(
            user_id,
            "⏰ Ish vaqtingiz boshlanishiga 20 daqiqa qoldi. Iltimos, kech qolmang!"
        )
    except Exception as e:
        print(f"[Xatolik - 20 daqiqa oldin ogohlantirish] {user_id}: {e}")


async def remind_unchecked_user_once(bot: Bot, user_id: int, attempt: int):
    if not has_checked_in_today(user_id, "ishga_keldi"):
        try:
            await bot.send_message(
                user_id,
                f"❗ Siz hali ishga kelganingizni bot orqali qayd etmadingiz. ({attempt}-ogohlantirish)"
            )
        except Exception as e:
            print(f"[Xatolik - {attempt}-ogohlantirish yuborilmadi] {user_id}: {e}")

# Bu yerda joylashgan funksiyalardan so‘ng qo‘y:
# async def send_end_reminder(...)
# ⬇⬇⬇ SHU YERGA QO‘Y

async def remind_if_not_checked_in(bot: Bot, user_id: int):
    if not has_checked_in_today(user_id, "ishga_keldi"):
        try:
            await bot.send_message(
                user_id,
                "✅ Ish vaqtingiz boshlandi. Iltimos, 'Ishga keldim' tugmasini bosing."
            )
        except Exception as e:
            print(f"[Xatolik - ish boshlanishi bildirish] {user_id}: {e}")
