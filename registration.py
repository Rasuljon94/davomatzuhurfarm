from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from config import ADMIN_IDS, ALLOWED_USER_IDS, BRANCH_LOCATIONS
from database import is_user_registered, register_user
from utils import get_main_keyboard
from datetime import datetime

router = Router()
BRANCH_NAMES = list(BRANCH_LOCATIONS.keys())

class FSMRegistration(StatesGroup):
    name = State()
    surname = State()
    birthdate = State()
    branch = State()

@router.message(F.text == "/start")
async def start_registration(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id

    if user_id in ADMIN_IDS:
        await message.answer("🔧 Siz adminsiz. Iltimos, /admin komandasidan foydalaning.")
        return

    if user_id not in ALLOWED_USER_IDS:
        await message.answer("❌ Siz ro'yxatdan o'tish uchun ruxsat etilmagansiz.")
        return

    if is_user_registered(user_id):
        await message.answer("✅ Siz allaqachon ro'yxatdan o'tgansiz.", reply_markup=get_main_keyboard())
        return

    await message.answer("📝 Ismingizni kiriting:")
    await state.set_state(FSMRegistration.name)

@router.message(FSMRegistration.name)
async def ask_surname(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("👤 Familiyangizni kiriting:")
    await state.set_state(FSMRegistration.surname)

@router.message(FSMRegistration.surname)
async def ask_birthdate(message: Message, state: FSMContext):
    await state.update_data(surname=message.text)
    await message.answer("🎂 Tug‘ilgan sanangizni DD.MM.YYYY formatda kiriting:")
    await state.set_state(FSMRegistration.birthdate)

@router.message(FSMRegistration.birthdate)
async def ask_branch(message: Message, state: FSMContext):
    birthdate = message.text.strip()
    try:
        datetime.strptime(birthdate, "%d.%m.%Y")
    except ValueError:
        await message.answer("❗ Tug‘ilgan sana noto‘g‘ri. DD.MM.YYYY formatida yozing.")
        return

    await state.update_data(birthdate=birthdate)

    buttons = [[KeyboardButton(text=branch)] for branch in BRANCH_NAMES]
    markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
    await message.answer("📍 Filialingizni tanlang:", reply_markup=markup)
    await state.set_state(FSMRegistration.branch)

@router.message(FSMRegistration.branch)
async def complete_registration(message: Message, state: FSMContext):
    if message.text not in BRANCH_NAMES:
        await message.answer("❗ Noto‘g‘ri filial tanlandi. Iltimos, tugma orqali tanlang.")
        return

    await state.update_data(branch=message.text)
    data = await state.get_data()

    register_user(
        telegram_id=message.from_user.id,
        name=data["name"],
        surname=data["surname"],
        birthdate=data["birthdate"],
        branch=data["branch"]
    )

    await message.answer("✅ Ro'yxatdan o'tish yakunlandi!", reply_markup=get_main_keyboard())
    await state.clear()
