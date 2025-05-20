# 📁 comments.py

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from utils import get_current_time, get_current_date, get_main_keyboard
from database import save_note_to_today_attendance, get_user_name
from config import ADMIN_IDS

router = Router()

class FSMComment(StatesGroup):
    waiting_for_comment = State()

@router.message(F.text == "📩 Izoh yuborish")
async def ask_for_comment(message: Message, state: FSMContext):
    if message.from_user.id in ADMIN_IDS:
        return
    await message.answer("✍️ Iltimos, izohingizni yozing:")
    await state.set_state(FSMComment.waiting_for_comment)

from database import save_note_to_today_attendance

@router.message(FSMComment.waiting_for_comment)
async def receive_comment(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in ADMIN_IDS:
        await state.clear()
        return

    text = message.text.strip()
    date = get_current_date()
    time = get_current_time()
    full_name = get_user_name(user_id)

    await state.clear()

    # 🔁 YANGI: Izohni attendance.note ga qo‘shamiz
    save_note_to_today_attendance(user_id, text)

    # 🔔 Adminlarga yuboriladi
    for admin_id in ADMIN_IDS:
        await message.bot.send_message(
            admin_id,
            f"📩 Yangi izoh\n👤 {full_name}\n📅 {date} – {time}\n📝 {text}"
        )

    await message.answer("✅ Izoh qabul qilindi!", reply_markup=get_main_keyboard())


@router.message(F.text)
async def regular_text(message: Message):
    user_id = message.from_user.id
    if user_id in ADMIN_IDS:
        return

    full_name = get_user_name(user_id)
    for admin_id in ADMIN_IDS:
        await message.bot.send_message(
            admin_id,
            f"📨 Xodimdan xabar yubordi\n👤 {full_name}\n📝 {message.text}"
        )
