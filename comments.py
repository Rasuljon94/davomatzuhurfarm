from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database import (
    is_user_allowed, is_user_registered, get_user_name, save_note_to_today_attendance, get_all_users
)
from config import ADMIN_IDS
from utils import get_main_keyboard, get_current_date, get_current_time

router = Router()
admin_broadcast_flags = {}

class FSMComment(StatesGroup):
    waiting_for_comment = State()

@router.message(F.text == "📩 Izoh yuborish")
async def ask_for_comment(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in ADMIN_IDS:
        return
    if not is_user_allowed(user_id) or not is_user_registered(user_id):
        await message.answer("❌ Siz tizimdan o‘chirilgansiz yoki ruxsat yo‘q.")
        return
    await message.answer("✍️ Iltimos, izohingizni yozing:")
    await state.set_state(FSMComment.waiting_for_comment)

@router.message(FSMComment.waiting_for_comment)
async def receive_comment(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not is_user_allowed(user_id) or not is_user_registered(user_id):
        await message.answer("❌ Siz tizimdan o‘chirilgansiz yoki ruxsat yo‘q.")
        await state.clear()
        return

    text = message.text.strip()
    save_note_to_today_attendance(user_id, text)

    date = get_current_date()
    time = get_current_time()
    full_name = get_user_name(user_id)

    for admin_id in ADMIN_IDS:
        await message.bot.send_message(
            admin_id,
            f"📩 Yangi izoh\n👤 {full_name}\n📅 {date} – {time}\n📝 {text}"
        )
    await message.answer("✅ Izoh qabul qilindi!", reply_markup=get_main_keyboard())
    await state.clear()

@router.message(F.text == "📢 Barchaga")
async def ask_broadcast_text(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    admin_broadcast_flags[message.from_user.id] = True
    await message.answer("✉️ Barchaga yuboriladigan xabarni yozing:")

@router.message(F.text == "👤 Hodimga")
async def choose_user_to_message(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    users = get_all_users()
    buttons = [
        [InlineKeyboardButton(text=f"{u['name']} {u['surname']}", callback_data=f"notify_{u['telegram_id']}")]
        for u in users
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("👤 Qaysi hodimga yuborilsin?", reply_markup=markup)

@router.callback_query(F.data.startswith("notify_"))
async def notify_selected_user(callback: CallbackQuery):
    telegram_id = int(callback.data.split("_")[1])
    admin_broadcast_flags[callback.from_user.id] = telegram_id
    await callback.message.answer("✍️ Hodimga yuboriladigan xabarni yozing:")

@router.message()
async def universal_message_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id

    # 📢 Barchaga
    if user_id in ADMIN_IDS and admin_broadcast_flags.get(user_id) is True:
        for user in get_all_users():
            try:
                await message.bot.send_message(user["telegram_id"], message.text)
            except:
                continue
        await message.answer("✅ Barchaga yuborildi.")
        admin_broadcast_flags[user_id] = False
        return

    # 👤 Hodimga
    if user_id in ADMIN_IDS and isinstance(admin_broadcast_flags.get(user_id), int):
        try:
            target_id = admin_broadcast_flags[user_id]
            await message.bot.send_message(target_id, message.text)
            await message.answer("✅ Xabar yuborildi.")
        except Exception as e:
            await message.answer(f"❌ Xatolik: {e}")
        admin_broadcast_flags[user_id] = False
        return

    # 🧍 Hodimdan oddiy matn
    if not is_user_allowed(user_id) or not is_user_registered(user_id):
        return  # hech nima demaymiz
    full_name = get_user_name(user_id)
    for admin_id in ADMIN_IDS:
        await message.bot.send_message(
            admin_id,
            f"📨 Hodimdan xabar\n👤 {full_name}\n📝 {message.text}"
        )
