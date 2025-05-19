from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from config import BRANCH_LOCATIONS, ADMIN_IDS
from database import update_user_fields, is_user_registered
from utils import get_main_keyboard
from datetime import datetime

router = Router()

# === FSM holatlari ===
class FSMEditUser(StatesGroup):
    get_id = State()
    name = State()
    surname = State()
    birthdate = State()
    branch = State()
    confirm = State()

# === Boshlanish komandasi ===
@router.message(F.text == "/edit_user_form")
async def admin_edit_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Siz admin emassiz.")
        return
    await message.answer("✍️ Tahrirlamoqchi bo‘lgan foydalanuvchining Telegram ID raqamini kiriting:")
    await state.set_state(FSMEditUser.get_id)

# === 1. Telegram ID tekshirish ===
@router.message(FSMEditUser.get_id)
async def get_id(message: Message, state: FSMContext):
    try:
        telegram_id = int(message.text)
    except:
        await message.answer("❗ Faqat raqam kiritilishi kerak.")
        return

    if not is_user_registered(telegram_id):
        await message.answer("❌ Bu foydalanuvchi ro‘yxatda mavjud emas.")
        return

    await state.update_data(telegram_id=telegram_id)
    await message.answer("📝 Yangi ismini kiriting:")
    await state.set_state(FSMEditUser.name)

# === 2. Ism ===
@router.message(FSMEditUser.name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("📝 Yangi familiyasini kiriting:")
    await state.set_state(FSMEditUser.surname)

# === 3. Familiya ===
@router.message(FSMEditUser.surname)
async def get_surname(message: Message, state: FSMContext):
    await state.update_data(surname=message.text)
    await message.answer("📅 Tug‘ilgan sanani DD.MM.YYYY formatda kiriting:")
    await state.set_state(FSMEditUser.birthdate)

# === 4. Tug‘ilgan sana ===
@router.message(FSMEditUser.birthdate)
async def get_birthdate(message: Message, state: FSMContext):
    try:
        datetime.strptime(message.text, "%d.%m.%Y")
    except:
        await message.answer("❗ Format noto‘g‘ri. DD.MM.YYYY shaklida yozing.")
        return

    await state.update_data(birthdate=message.text)

    # Filial tanlash tugmalari
    filial_buttons = [[KeyboardButton(text=name)] for name in BRANCH_LOCATIONS]
    markup = ReplyKeyboardMarkup(keyboard=filial_buttons, resize_keyboard=True)
    await message.answer("🏢 Yangi filialni tanlang:", reply_markup=markup)
    await state.set_state(FSMEditUser.branch)

# === 5. Filial tanlash ===
@router.message(FSMEditUser.branch)
async def get_branch(message: Message, state: FSMContext):
    if message.text not in BRANCH_LOCATIONS:
        await message.answer("❗ Filial nomini tugmalardan tanlang.")
        return

    await state.update_data(branch=message.text)
    data = await state.get_data()

    text = (
        f"📋 Tahrir qilishga tayyor:\n"
        f"🆔 ID: {data['telegram_id']}\n"
        f"👤 Ism: {data['name']}\n"
        f"👥 Familiya: {data['surname']}\n"
        f"🎂 Tug‘ilgan sana: {data['birthdate']}\n"
        f"🏢 Filial: {data['branch']}\n\n"
        f"Tasdiqlaysizmi?"
    )
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Tasdiqlash")],
            [KeyboardButton(text="🔙 Bekor qilish")]
        ],
        resize_keyboard=True
    )
    await message.answer(text, reply_markup=markup)
    await state.set_state(FSMEditUser.confirm)

# === 6. Tasdiqlash ===
@router.message(FSMEditUser.confirm, F.text == "✅ Tasdiqlash")
async def confirm_edit(message: Message, state: FSMContext):
    data = await state.get_data()
    update_user_fields(data["telegram_id"], {
        "name": data["name"],
        "surname": data["surname"],
        "birthdate": data["birthdate"],
        "branch": data["branch"]
    })
    await message.answer("✅ Foydalanuvchi ma’lumotlari yangilandi.", reply_markup=get_main_keyboard())
    await state.clear()

# === 7. Bekor qilish ===
@router.message(FSMEditUser.confirm, F.text == "🔙 Bekor qilish")
async def cancel_edit(message: Message, state: FSMContext):
    await message.answer("❌ O‘zgarishlar bekor qilindi.", reply_markup=get_main_keyboard())
    await state.clear()
