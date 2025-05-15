import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import ContentType, Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime
import sqlite3
from geopy.distance import geodesic

# 🔐 Token va admin ID lar
API_TOKEN = "7667153118:AAEB7Rjkfs1LKbtU37DcsbE25qdh07pPuN0"
ADMIN_IDS = [7563660599, 1234567890]

# Ruxsat etilgan foydalanuvchilar
allowed_users = [1148653866, 7412677650]

# Filial koordinatalari
BRANCH_LOCATIONS = [
    (40.108663, 67.834875),
    (40.108663, 67.834875),
    (40.108663, 67.834875),
    (40.108663, 67.834875),
]

# Bot va Dispatcher
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# 📊 SQLite baza va jadval
def init_db():
    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            full_name TEXT,
            action TEXT,
            latitude REAL,
            longitude REAL,
            datetime TEXT
        )
    ''')
    conn.commit()
    conn.close()

def log_attendance(user_id, full_name, action, latitude, longitude):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO attendance_logs (user_id, full_name, action, latitude, longitude, datetime)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, full_name, action, latitude, longitude, now))
    conn.commit()
    conn.close()

init_db()

# Foydalanuvchi holatlarini saqlash
user_data = {}  # user_id: {full_name, is_checked_in, last_check_date, last_action}

# Asosiy klaviatura: 3 tugma
def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Ishga keldim")],
            [KeyboardButton(text="🃽 Ishdan ketdim")],
            [KeyboardButton(text="📱 Lokatsiya jo'natish", request_location=True)]
        ],
        resize_keyboard=True
    )

# Ro‘yxatdan o‘tish
class Registration(StatesGroup):
    lastname = State()
    firstname = State()
    dob = State()

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    uid = message.from_user.id
    if uid not in allowed_users:
        await message.answer("Siz ro‘yxatdan o‘ta olmaysiz. Iltimos, admin bilan bog‘laning.")
        return
    if uid in user_data:
        await message.answer("Siz avval ro‘yxatdan o‘tgan ekansiz.", reply_markup=main_keyboard())
        return
    await state.set_state(Registration.lastname)
    await message.answer("Familiyangizni kiriting:")

@dp.message(Registration.lastname)
async def process_lastname(message: Message, state: FSMContext):
    await state.update_data(lastname=message.text)
    await state.set_state(Registration.firstname)
    await message.answer("Ismingizni kiriting:")

@dp.message(Registration.firstname)
async def process_firstname(message: Message, state: FSMContext):
    await state.update_data(firstname=message.text)
    await state.set_state(Registration.dob)
    await message.answer("Tug‘ilgan sanangizni DD.MM.YYYY formatda kiriting:")

@dp.message(Registration.dob)
async def process_dob(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    full_name = f"{data['firstname']} {data['lastname']}"
    user_data[message.from_user.id] = {
        "full_name": full_name,
        "is_checked_in": False,
        "last_check_date": "",
        "last_action": ""
    }
    await message.answer("Ro‘yxatdan o‘tdingiz.", reply_markup=main_keyboard())

@dp.message(lambda m: m.text in ["✅ Ishga keldim", "🃽 Ishdan ketdim"])
async def store_action(message: Message):
    uid = message.from_user.id
    if uid not in user_data:
        await message.answer("Avval /start buyrug‘ini bering.")
        return
    user_data[uid]['last_action'] = 'checkin' if message.text == '✅ Ishga keldim' else 'checkout'
    await message.answer("Lokatsiyani jo'natish uchun 📱 tugmasini bosing.", reply_markup=main_keyboard())

@dp.message(F.content_type == ContentType.LOCATION)
async def handle_location(message: Message):
    uid = message.from_user.id
    info = user_data.get(uid)
    if not info or not info.get('last_action'):
        await message.answer("Avval 'Ishga keldim' yoki 'Ishdan ketdim' tugmasini bosing.", reply_markup=main_keyboard())
        return
    action = info['last_action']
    lat, lon = message.location.latitude, message.location.longitude
    manzil = f"{lat}, {lon}"
    now = datetime.now()
    today = now.strftime("%d.%m.%Y")
    time_str = now.strftime("%H:%M:%S")

    if not any(geodesic((lat, lon), branch).meters <= 100 for branch in BRANCH_LOCATIONS):
        await message.answer("Siz filial hududida emassiz!", reply_markup=main_keyboard())
        for aid in ADMIN_IDS:
            await bot.send_message(aid, f"⚠️ {info['full_name']} filialdan tashqarida lokatsiya yubordi! 📍 {manzil}")
        info['last_action'] = ''
        return

    if action == 'checkin':
        if info['last_check_date'] == today and info['is_checked_in']:
            await message.answer("Siz bugun allaqachon ishga kelgansiz.", reply_markup=main_keyboard())
            info['last_action'] = ''
            return
        status = 'Ishga keldi'
        info['is_checked_in'] = True
        info['last_check_date'] = today
    else:
        if not info['is_checked_in'] or info['last_check_date'] != today:
            await message.answer("Avval 'Ishga keldim' tugmasini bosing.", reply_markup=main_keyboard())
            info['last_action'] = ''
            return
        status = 'Ishdan ketdi'
        info['is_checked_in'] = False

    log_attendance(uid, info['full_name'], status, lat, lon)

    msg = f"👤 {info['full_name']}\n🕒 {status}\n📅 {today} {time_str}\n📍 {manzil}"
    for aid in ADMIN_IDS:
        await bot.send_message(aid, msg)

    if status == 'Ishga keldi':
        await message.answer("✅ Ishga kelishingiz qayd etildi. Ish kuningiz muborak!", reply_markup=main_keyboard())
    else:
        await message.answer("✅ Ishdan ketishingiz qayd etildi. Xayr, yaxshi dam oling!", reply_markup=main_keyboard())
    await message.answer("🔔 Admin ma'lumotni qabul qildi.", reply_markup=main_keyboard())
    info['last_action'] = ''

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
