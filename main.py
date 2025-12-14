# requirements:
# pip install aiogram==3.*

import asyncio
import json
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

BOT_TOKEN = "8394021240:AAHHZy_PkUcGSCn_jmj2l6fBVjNvYyghK5E"

# === ADMIN IDS (зашиты в файл) ===
ADMINS = [
    123456789,
    7503094593,
]

DATA_FILE = "applications.txt"

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# === FSM ===
class UploadChecks(StatesGroup):
    waiting_files = State()

# === FILE STORAGE ===
def load_applications():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_applications(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


applications = load_applications()

START_TEXT = (
    "Получи 6-ю процедуру «Сухой Туман» бесплатно! 🎁\n"
    "Воспользуйся услугой 5 раз — 6-я в подарок 💨 Все просто:\n"
    "1️⃣ Загрузи в бот 4 чека\n"
    "2️⃣ Мы быстро их проверим\n"
    "3️⃣ Получи кешбэк в рублях на 1 полноценную процедуру\n\n"
    "💸 Никаких баллов — только реальные деньги\n"
    "⚡️ Быстрое начисление\n"
    "📲 Все через удобный Telegram-бот\n\n"
    "Нажми «Начать» и забери свой бонус уже сегодня!"
)

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    applications[str(message.from_user.id)] = {
        "files": [],
        "status": "pending"
    }
    save_applications(applications)
    await message.answer(START_TEXT)
    await state.set_state(UploadChecks.waiting_files)

@dp.message(UploadChecks.waiting_files)
async def handle_files(message: Message, state: FSMContext):
    uid = str(message.from_user.id)

    if not message.document and not message.photo:
        await message.answer("Пожалуйста, отправь файл (фото или документ).")
        return

    file_id = message.document.file_id if message.document else message.photo[-1].file_id
    applications[uid]["files"].append(file_id)
    save_applications(applications)

    if len(applications[uid]["files"]) < 4:
        await message.answer(f"Принято {len(applications[uid]['files'])}/4. Отправь ещё чек.")
        return

    await message.answer("Все 4 чека получены ✅ Ожидай проверки.")
    await state.clear()

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Одобрено", callback_data=f"approve:{uid}"),
        InlineKeyboardButton(text="❌ Отказано", callback_data=f"reject:{uid}")
    ]])

    for admin_id in ADMINS:
        await bot.send_message(admin_id, f"🆕 Новая заявка\nПользователь: {uid}")
        for f_id in applications[uid]["files"]:
            await bot.send_document(admin_id, f_id)
        await bot.send_message(admin_id, "Выберите действие:", reply_markup=kb)

# === ADMIN PANEL ===
@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id not in ADMINS:
        return

    if not applications:
        await message.answer("Заявок нет")
        return

    text = "📋 Список заявок:\n\n"
    for uid, app in applications.items():
        status = app["status"]
        emoji = "⏳" if status == "pending" else "✅" if status == "approved" else "❌"
        text += f"{emoji} Пользователь {uid} — {status}\n"

    await message.answer(text)

@dp.callback_query(F.data.startswith("approve:"))
async def approve(call: CallbackQuery):
    if call.from_user.id not in ADMINS:
        return
    uid = call.data.split(":")[1]
    applications[uid]["status"] = "approved"
    save_applications(applications)
    await bot.send_message(int(uid), "🎉 Ваши чеки одобрены! Заявка принята.")
    await call.message.edit_text("Заявка одобрена ✅")

@dp.callback_query(F.data.startswith("reject:"))
async def reject(call: CallbackQuery):
    if call.from_user.id not in ADMINS:
        return
    uid = call.data.split(":")[1]
    applications[uid]["status"] = "rejected"
    save_applications(applications)
    await bot.send_message(int(uid), "❌ К сожалению, заявка отклонена.")
    await call.message.edit_text("Заявка отклонена ❌")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
