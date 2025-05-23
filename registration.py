from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from config import ADMIN_IDS
from database import is_user_registered, register_user,is_user_allowed
from utils import get_main_keyboard
from datetime import datetime
import re

router = Router()

class FSMRegistration(StatesGroup):
    name = State()
    surname = State()
    birthdate = State()
    start_time = State()
    end_time = State()
    address = State()
    phone = State()

@router.message(F.text == "/start")
async def start_registration(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id

    if user_id in ADMIN_IDS:
        await message.answer("🔧 Siz adminsiz. Iltimos, /admin komandasidan foydalaning.")
        return

    if not is_user_allowed(user_id):
        await message.answer("❌ Siz ro'yxatdan o'tish uchun ruxsat etilmagansiz.")
        return

    if is_user_registered(user_id):
        await message.answer("✅ Siz allaqachon ro'yxatdan o'tgansiz.", reply_markup=get_main_keyboard())
        return

    await message.answer("📝 Ismingizni kiriting:")
    await state.set_state(FSMRegistration.name)

@router.message(FSMRegistration.name)
async def ask_surname(message: Message, state: FSMContext):
    if not message.text.strip().isalpha():
        await message.answer("❗ Ism faqat harflardan iborat bo'lishi kerak.")
        return
    await state.update_data(name=message.text.strip())
    await message.answer("👤 Familiyangizni kiriting:")
    await state.set_state(FSMRegistration.surname)

@router.message(FSMRegistration.surname)
async def ask_birthdate(message: Message, state: FSMContext):
    if not message.text.strip().isalpha():
        await message.answer("❗ Familiya faqat harflardan iborat bo'lishi kerak.")
        return
    await state.update_data(surname=message.text.strip())
    await message.answer("🎂 Tug‘ilgan sanangizni DD.MM.YYYY formatda kiriting:")
    await state.set_state(FSMRegistration.birthdate)

@router.message(FSMRegistration.birthdate)
async def ask_start_time(message: Message, state: FSMContext):
    birthdate = message.text.strip()

    if not re.match(r"^\d{2}\.\d{2}\.\d{4}$", birthdate):
        await message.answer("❗ Format noto‘g‘ri. Masalan: 15.03.2000")
        return
    try:
        datetime.strptime(birthdate, "%d.%m.%Y")
    except ValueError:
        await message.answer("❗ Bunday sana mavjud emas. Qayta kiriting.")
        return

    await state.update_data(birthdate=birthdate)
    await message.answer("🕘 Ish boshlanish vaqtini HH:MM formatda kiriting (masalan, 09:00):")
    await state.set_state(FSMRegistration.start_time)

@router.message(FSMRegistration.start_time)
async def ask_end_time(message: Message, state: FSMContext):
    text = message.text.strip()

    if not re.match(r"^\d{2}:\d{2}$", text):
        await message.answer("❗ Format noto‘g‘ri. Masalan: 09:00")
        return

    try:
        datetime.strptime(text, "%H:%M")
    except ValueError:
        await message.answer("❗ Soat noto‘g‘ri. 00:00 dan 23:59 oralig‘ida bo‘lishi kerak.")
        return

    await state.update_data(start_time=text)
    await message.answer("🕔 Ish tugash vaqtini HH:MM formatda kiriting (masalan, 18:00):")
    await state.set_state(FSMRegistration.end_time)


@router.message(FSMRegistration.end_time)
async def ask_address(message: Message, state: FSMContext):
    if not re.match(r"^\d{2}:\d{2}$", message.text.strip()):
        await message.answer("❗ Format noto‘g‘ri. Masalan: 18:00")
        return
    await state.update_data(end_time=message.text.strip())
    await message.answer("📍 Yashash manzilingizni kiriting:")
    await state.set_state(FSMRegistration.address)

@router.message(FSMRegistration.address)
async def ask_phone(message: Message, state: FSMContext):
    await state.update_data(address=message.text.strip())
    await message.answer("📞 Telefon raqamingizni kiriting (masalan, +998901234567):")
    await state.set_state(FSMRegistration.phone)

@router.message(FSMRegistration.phone)
async def complete_registration(message: Message, state: FSMContext):
    phone = message.text.strip()

    if not re.match(r"^\d{9}$", phone):
        await message.answer("❗ Telefon raqam faqat 9 ta raqamdan iborat bo‘lishi kerak (masalan: 901234567)")
        return

    phone = "+998" + phone
    await state.update_data(phone=phone)
    data = await state.get_data()

    register_user(
        telegram_id=message.from_user.id,
        name=data["name"],
        surname=data["surname"],
        birthdate=data["birthdate"],
        start_time=data["start_time"],
        end_time=data["end_time"],
        address=data["address"],
        phone=data["phone"]
    )

    await message.answer("✅ Ro'yxatdan o'tish yakunlandi!", reply_markup=get_main_keyboard())
    await state.clear()

