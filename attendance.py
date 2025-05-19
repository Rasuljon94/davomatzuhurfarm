from aiogram import Router, F
from aiogram.types import Message
from datetime import datetime
from utils import (
    get_current_time,
    get_current_date,
    is_within_radius,
    get_live_location_keyboard,
    get_main_keyboard,
    get_back_keyboard
)
from config import BRANCH_LOCATIONS, BRANCH_WORK_HOURS, ADMIN_IDS
from database import log_attendance, has_checked_in_today, get_user_branch, get_user_name

router = Router()

@router.message(F.text == "✅ Ishga keldim")
async def check_in_start(message: Message):
    if has_checked_in_today(message.from_user.id, "check_in"):
        await message.answer("📌 Siz bugun allaqachon ishga kelgansiz.")
        return
    await message.answer("📍 Iltimos, 15 daqiqalik jonli lokatsiyani yuboring:", reply_markup=get_live_location_keyboard())

@router.message(F.text == "🏁 Ishdan ketdim")
async def check_out_start(message: Message):
    if has_checked_in_today(message.from_user.id, "check_out"):
        await message.answer("📌 Siz bugun allaqachon ishdan chiqqansiz.")
        return
    await message.answer("📍 Iltimos, 15 daqiqalik jonli lokatsiyani yuboring:", reply_markup=get_live_location_keyboard())

@router.message(F.location)
async def receive_location(message: Message):
    if not message.location.live_period:
        await message.answer("❌ Faqat 15 daqiqalik jonli lokatsiya qabul qilinadi. Tugma orqali yuboring.")
        return

    user_id = message.from_user.id
    user_location = (message.location.latitude, message.location.longitude)
    full_name = get_user_name(user_id)
    now = get_current_time()
    today = get_current_date()

    found_branch = None
    for branch_name, coords in BRANCH_LOCATIONS.items():
        if is_within_radius(user_location, coords, radius_km=0.03):
            found_branch = branch_name
            break

    if not found_branch:
        await message.answer("❌ Siz hech bir filial hududida emassiz.")
        return

    start_str, end_str = BRANCH_WORK_HOURS.get(found_branch, ("08:00", "17:00"))
    fmt = "%H:%M"
    now_dt = datetime.strptime(now, fmt)
    start_dt = datetime.strptime(start_str, fmt)
    end_dt = datetime.strptime(end_str, fmt)

    late_minutes = 0
    early_minutes = 0
    action_type = "check_in" if not has_checked_in_today(user_id, "check_in") else "check_out"

    if action_type == "check_in" and now_dt > start_dt:
        late_minutes = int((now_dt - start_dt).total_seconds() // 60)
    elif action_type == "check_out" and now_dt < end_dt:
        early_minutes = int((end_dt - now_dt).total_seconds() // 60)

    log_attendance(
        telegram_id=user_id,
        full_name=full_name,
        time=now,
        date=today,
        branch=found_branch,
        location=user_location,
        late_minutes=late_minutes,
        early_minutes=early_minutes,
        action_type=action_type,
        note=""
    )

    action_text = "🕒 Ishga keldi" if action_type == "check_in" else "🏁 Ishdan ketdi"
    status = []
    if late_minutes > 0:
        status.append(f"⏰ Kechikdi: {late_minutes} daqiqa")
    if early_minutes > 0:
        status.append(f"⚠️ Erta ketdi: {early_minutes} daqiqa")

    info = (
        f"👤 Hodim: {full_name}\n"
        f"🏢 Filial: {found_branch}\n"
        f"{action_text}: {now}\n"
        f"{chr(10).join(status)}"
    ).strip()

    for admin_id in ADMIN_IDS:
        await message.bot.send_message(admin_id, info)

    await message.answer("✅ Ma'lumot qayd etildi.", reply_markup=get_back_keyboard())

@router.message(F.text == "🔙 Orqaga")
async def back_to_menu(message: Message):
    # Agar admin bo‘lsa, user menyusiga qaytirmaymiz
    if message.from_user.id in ADMIN_IDS:
        return
    await message.answer("🏠 Asosiy menyu:", reply_markup=get_main_keyboard())
