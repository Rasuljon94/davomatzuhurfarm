from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from datetime import datetime
from utils import (
    get_current_time,
    get_current_date,
    is_within_radius,
    get_live_location_keyboard,
    get_main_keyboard,
    get_back_keyboard,
    format_minutes
)
from config import BRANCH_LOCATIONS, ADMIN_IDS
from database import (
    log_attendance,
    has_checked_in_today,
    get_user_work_hours,
    get_user_name
)

import random

class FSMAction(StatesGroup):
    ishga_keldi = State()
    ishdan_ketdi = State()

router = Router()

@router.message(F.text == "✅ Ishga keldim")
async def check_in_start(message: Message):
    if has_checked_in_today(message.from_user.id, "ishga_keldi"):
        await message.answer("📌 Siz bugun allaqachon ishga kelgansiz.")
        return
    await message.answer("📍 Iltimos, 15 daqiqalik jonli lokatsiyani yuboring:", reply_markup=get_live_location_keyboard())

@router.message(F.text == "🏁 Ishdan ketdim")
async def check_out_start(message: Message):

    if not has_checked_in_today(message.from_user.id, "ishga_keldi"):
        await message.answer("❌ Siz hali ishga kelmagansiz. Avval '✅ Ishga keldim' tugmasini bosing.")
        return

    if has_checked_in_today(message.from_user.id, "ishdan_ketdi"):
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

    start_str, end_str = get_user_work_hours(user_id)
    if not start_str or not end_str:
        await message.answer("❗ Sizning ish vaqtingiz aniqlanmadi.")
        return

    fmt = "%H:%M"
    now_dt = datetime.strptime(now, fmt)
    start_dt = datetime.strptime(start_str, fmt)
    end_dt = datetime.strptime(end_str, fmt)

    if not has_checked_in_today(user_id, "ishga_keldi"):
        # ✅ ISHGA KELDI
        action_type = "ishga_keldi"
        late_minutes = max(0, int((now_dt - start_dt).total_seconds() // 60)) if now_dt > start_dt else 0
        early_minutes = 0

        if late_minutes > 0:
            await message.answer(
                f"❌ Siz {late_minutes} daqiqaga kech qoldingiz. "
                f"Bunday holat takrorlanmasin. Iltimos, ishga o‘z vaqtida keling."
            )
        else:
            await message.answer(random.choice([
                "💡 Bugungi kuningiz omadli va samarali o‘tsin!",
                "🔥 Keling, bugun eng yaxshi natijalarga erishamiz!",
                "👏 Sizning harakatlaringiz jamoaga ilhom bag‘ishlaydi!",
                "🚀 Har kuni rivojlanish sari bir qadam oldinga!"
            ]))
    else:
        # 🏁 ISHDAN KETDI
        action_type = "ishdan_ketdi"
        late_minutes = 0
        early_minutes = max(0, int((end_dt - now_dt).total_seconds() // 60)) if now_dt < end_dt else 0

        await message.answer("🏁 Ish vaqtingiz tugadi. Endi dam olishingiz mumkin.")
        if early_minutes == 0:
            await message.answer(random.choice([
                "🌇 Bugun qilgan mehnatingiz uchun rahmat! Dam oling!",
                "🔁 Siz ajoyib ish qildingiz! Ertaga yangi kuch bilan qayting!",
                "👌 Qadrli mehnatingiz tufayli jamoamiz rivojlanmoqda!",
                "💤 Endi dam olish vaqti. Siz buni munosib bajardingiz!"
            ]))

    # ⏺ Yozuvni bazaga yozamiz
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

    # 🧾 Adminlarga xabar
    action_text = "🕒 Ishga keldi" if action_type == "ishga_keldi" else "🏁 Ishdan ketdi"
    status = []
    if late_minutes > 0:
        status.append(f"⏰ Kechikdi: {format_minutes(late_minutes)}")
    if early_minutes > 0:
        status.append(f"⚠️ Erta ketdi: {format_minutes(early_minutes)}")

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
    if message.from_user.id in ADMIN_IDS:
        return
    await message.answer("🏠 Asosiy menyu:", reply_markup=get_main_keyboard())

@router.message(F.text == "📘 Joylashuvni qanday yuborish kerak?")
async def explain_live_location(message: Message):
    instruction = (
        "📍 *Jonli lokatsiyani qanday yuborish kerak?*\n\n"
        "1. Telefoningizda pastdan 📎 (yoki +) belgini bosing.\n"
        "2. “Joylashuv” yoki “Location” menyusini tanlang.\n"
        "3. “Jonli joylashuvni ulashish” degan tugmani tanlang.\n"
        "4. *15 daqiqa* variantini tanlab, “Ulashish” tugmasini bosing.\n\n"
        "⚠️ Eslatma: Oddiy lokatsiya yuborilsa, bot qabul qilmaydi.\n\n"
        "✅ Siz faqat 15 daqiqalik jonli lokatsiya yuborganingizdagina tizim sizni ishga kelgan deb qayd etadi."
    )
    await message.answer(instruction, parse_mode="Markdown")

