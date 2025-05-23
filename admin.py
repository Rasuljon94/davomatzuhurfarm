from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from config import ADMIN_IDS, BOT_VERSION
from database import (
    delete_user, export_users_to_excel, export_attendance_yearly,
    clear_user_fields, add_allowed_user, is_user_allowed,
    remove_allowed_user, export_attendance_monthly, export_attendance_previous_month
)
import os

router = Router()

@router.message(F.text == "/start")
async def admin_start_message(message: Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("🔧 Siz adminsiz. Iltimos, /admin komandasidan foydalaning.")

@router.message(F.text == "/admin")
async def admin_panel(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Sizga bu buyruqdan foydalanish ruxsat etilmagan.")
        return

    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Yillik hisobot"), KeyboardButton(text="📅 Oylik hisobot")],
            [KeyboardButton(text="📆 O‘tgan oy hisobot")],
            [KeyboardButton(text="📢 Barchaga"), KeyboardButton(text="👤 Hodimga")],
            [KeyboardButton(text="👥 Hodimlar ro'yxati")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    await message.answer("🛠 Admin paneliga xush kelibsiz!", reply_markup=markup)

@router.message(F.text == "📊 Yillik hisobot")
async def send_excel_report(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    file_path = export_attendance_yearly()
    if not file_path or not os.path.exists(file_path):
        await message.answer("📭 Bu yil uchun ma'lumot yo'q.")
        return
    try:
        await message.answer_document(FSInputFile(file_path), caption="📊 Shu yilgi davomat")
    except Exception as e:
        await message.answer(f"❌ Faylni yuborishda xatolik: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@router.message(F.text == "📅 Oylik hisobot")
async def monthly_report(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    path = export_attendance_monthly()
    if not path or not os.path.exists(path):
        await message.answer("📭 Bu oy uchun ma'lumot topilmadi.")
        return
    await message.answer_document(FSInputFile(path), caption="📅 Oylik davomat hisobot")
    os.remove(path)

@router.message(F.text == "📆 O‘tgan oy hisobot")
async def previous_month_report(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    path = export_attendance_previous_month()
    if not path or not os.path.exists(path):
        await message.answer("📭 O‘tgan oy uchun ma’lumot topilmadi.")
        return
    await message.answer_document(FSInputFile(path), caption="📆 O‘tgan oy hisobot")
    os.remove(path)



@router.message(F.text == "👥 Hodimlar ro'yxati")
async def send_users_excel(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    path = export_users_to_excel()
    if not os.path.exists(path):
        await message.answer("❗ Hodimlar ro'yxati topilmadi.")
        return
    try:
        await message.answer_document(FSInputFile(path), caption="👥 Foydalanuvchilar ro'yxati")
    except Exception as e:
        await message.answer(f"❌ Faylni yuborishda xatolik: {e}")
    finally:
        if os.path.exists(path):
            os.remove(path)

@router.message(F.text.startswith("/delete_user"))
async def delete_user_command(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Sizga bu buyruqdan foydalanish ruxsat etilmagan.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("❗ Format: /delete_user <telegram_id>")
        return

    try:
        telegram_id = int(args[1])
        delete_user(telegram_id)
        remove_allowed_user(telegram_id)
        await message.bot.send_message(
            telegram_id,
            "❌ Siz tizimdan chiqarildingiz. Endi botdan foydalana olmaysiz.",
            reply_markup=ReplyKeyboardRemove()
        )
        await message.answer(f"🗑 Foydalanuvchi {telegram_id} to‘liq o‘chirildi.")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")

@router.message(F.text.startswith("/add_user"))
async def add_user_command(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❗ Format: /add_user <telegram_id>")
        return
    try:
        telegram_id = int(args[1])
        if not is_user_allowed(telegram_id):
            add_allowed_user(telegram_id)
            await message.answer(f"✅ Foydalanuvchi {telegram_id} ro'yxatdan o'tishga ruxsat oldi.")
        else:
            await message.answer("ℹ️ Bu foydalanuvchi allaqachon ro'yxatga olingan.")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")


@router.message(F.text.startswith("/edit_user"))
async def edit_user_command(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("❗ Format: /edit_user <telegram_id>")
        return

    try:
        telegram_id = int(args[1])
        clear_user_fields(telegram_id)  # <-- tozalash, lekin o‘chirmaslik
        await message.bot.send_message(
            telegram_id,
            "♻️ Ma'lumotlaringiz tozalandi. Iltimos, /start tugmasini bosib ro'yxatdan qayta o'ting.",
            reply_markup=ReplyKeyboardRemove()
        )
        await message.answer(f"✅ {telegram_id} ma'lumotlari tozalandi.")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")

@router.message(F.text == "/version")
async def version_command(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer(f"🤖 Bot versiyasi: {BOT_VERSION}")
