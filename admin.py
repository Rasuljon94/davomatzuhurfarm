# 📁 admin.py

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from config import ADMIN_IDS, ALLOWED_USER_IDS, BOT_VERSION
from database import delete_user, export_users_to_excel, export_attendance_yearly, update_user_fields
import os

router = Router()

# Admin panel faqat /admin komanda orqali

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
            [KeyboardButton(text="📊 Hisobot"), KeyboardButton(text="👥 Hodimlar ro'yxati")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    await message.answer("🛠 Admin paneliga xush kelibsiz!", reply_markup=markup)

# Hodimlar ro'yxati
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

# Davomat hisobot
@router.message(F.text == "📊 Hisobot")
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

# Foydalanuvchini o‘chirish
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
        await message.answer(f"🗑 Foydalanuvchi {telegram_id} o‘chirildi.")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")

# ✅ /add_user <telegram_id>
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
        if telegram_id not in ALLOWED_USER_IDS:
            ALLOWED_USER_IDS.append(telegram_id)
            await message.answer(f"✅ Foydalanuvchi {telegram_id} ro'yxatdan o'tishga ruxsat oldi.")
        else:
            await message.answer("ℹ️ Bu foydalanuvchi allaqachon ro'yxatga olingan.")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")

# ✅ /edit_user <telegram_id>
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
        update_user_fields(telegram_id, {
            "name": None,
            "surname": None,
            "birthdate": None,
            "start_time": None,
            "end_time": None,
            "address": None,
            "phone": None
        })
        await message.answer(f"♻️ {telegram_id} ma'lumotlari tozalandi. Endi u qayta ro'yxatdan o'tishi mumkin.")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")

# ✅ /version
@router.message(F.text == "/version")
async def version_command(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer(f"🤖 Bot versiyasi: {BOT_VERSION}")
