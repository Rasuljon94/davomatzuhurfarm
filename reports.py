# 📁 reports.py

from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from config import ADMIN_IDS
from database import export_attendance_yearly
import os

router = Router()

@router.message(F.text == "📊 Hisobot")
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
