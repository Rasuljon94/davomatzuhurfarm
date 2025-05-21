from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from config import ADMIN_IDS, BOT_VERSION
from database import (
    delete_user, export_users_to_excel, export_attendance_yearly,
    delete_user_fields, add_allowed_user, is_user_allowed,
    remove_allowed_user, export_attendance_monthly, get_all_users
)
import os
from aiogram.fsm.context import FSMContext

router = Router()
admin_broadcast_flags = {}

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

@router.message(F.text == "📢 Barchaga")
async def notify_all_users(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Sizga bu tugma ruxsat etilmagan.")
        return
    admin_broadcast_flags[message.from_user.id] = True
    await message.answer("✉️ Yubormoqchi bo‘lgan xabaringizni kiriting:")

@router.message(F.text == "👤 Hodimga")
async def choose_user_to_message(message: Message):
    users = get_all_users()
    buttons = [
        [InlineKeyboardButton(text=f"{u['name']} {u['surname']}", callback_data=f"notify_{u['telegram_id']}")]
        for u in users
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("👤 Qaysi hodimga xabar yuborilsin?", reply_markup=markup)

@router.callback_query(F.data.startswith("notify_"))
async def notify_selected_user(callback: CallbackQuery, state: FSMContext):
    telegram_id = int(callback.data.split("_")[1])
    await callback.message.answer("✍️ Yuboriladigan xabar matnini yozing:")
    admin_broadcast_flags[callback.from_user.id] = telegram_id

@router.message()
async def handle_admin_broadcast_text(message: Message, state: FSMContext):
    # Admin umumiy broadcast
    if (
        message.from_user.id in ADMIN_IDS and
        admin_broadcast_flags.get(message.from_user.id) is True and
        await state.get_state() is None
    ):
        for user in get_all_users():
            try:
                await message.bot.send_message(user["telegram_id"], message.text)
            except:
                continue
        await message.answer("✅ Xabar barcha foydalanuvchilarga yuborildi.")
        admin_broadcast_flags[message.from_user.id] = False
        return

    # Admin maxsus foydalanuvchiga xabar
    if (
        message.from_user.id in ADMIN_IDS and
        isinstance(admin_broadcast_flags.get(message.from_user.id), int) and
        await state.get_state() is None
    ):
        try:
            target_id = admin_broadcast_flags[message.from_user.id]
            await message.bot.send_message(target_id, message.text)
            await message.answer("✅ Xabar yuborildi")
        except Exception as e:
            await message.answer(f"❌ Xatolik: {e}")
        admin_broadcast_flags[message.from_user.id] = False

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
        delete_user_fields(telegram_id)
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
