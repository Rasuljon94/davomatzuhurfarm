# 📁 utils.py + keyboards

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime
from geopy.distance import geodesic

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Ishga keldim"), KeyboardButton(text="🏁 Ishdan ketdim")],
            [KeyboardButton(text="📩 Izoh yuborish")]
        ],
        resize_keyboard=True
    )

def get_back_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Orqaga")]],
        resize_keyboard=True
    )

def get_live_location_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 Orqaga")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_current_time():
    return datetime.now().strftime("%H:%M")

def get_current_date():
    return datetime.now().strftime("%d.%m.%Y")

def is_within_radius(user_location, branch_location, radius_km=0.03):
    try:
        distance = geodesic(user_location, branch_location).km
        return distance <= radius_km
    except Exception as e:
        print(f"[Xatolik] Lokatsiyani tekshirishda muammo: {e}")
        return False

def format_minutes(minutes):
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}:{str(mins).zfill(2)}"