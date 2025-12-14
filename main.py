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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "applications.txt")

# ============================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


# ================= FSM =================

class UploadChecks(StatesGroup):
    waiting_files = State()


# ================= ХРАНЕНИЕ =================
def load_applications():
    if not os.path.exists(DATA_FILE):
        return {}
    if os.path.getsize(DATA_FILE) == 0:
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def save_applications(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


applications = load_applications()

# ================= ТЕКСТЫ =================
START_TEXT = (
    "Получи 6-ю процедуру «Сухой Туман» бесплатно! 🎁\n"
    "Воспользуйся услугой 5 раз — 6-я в подарок 💨 Все просто:\n"
    "1️⃣ Загрузи в бот 4 чека\n"
    "2️⃣ Мы быстро их проверим\n"
    "3️⃣ Получи кешбэк в рублях на 1 полноценную процедуру\n\n"
    "Нажми «Начать» и забери свой бонус уже сегодня!"
)

# ================= ПОЛЬЗОВАТЕЛЬ =================
@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    uid = str(message.from_user.id)
    if uid not in applications:
        applications[uid] = {"files": [], "status": "pending"}
        save_applications(applications)
    await message.answer(START_TEXT)
    await state.set_state(UploadChecks.waiting_files)

@dp.message(UploadChecks.waiting_files)
async def handle_files(message: Message, state: FSMContext):
    uid = str(message.from_user.id)

    if not message.document and not message.photo:
        await message.answer("Отправь фото или файл чека")
        return

    if message.document:
        applications[uid]["files"].append({"type": "document", "file_id": message.document.file_id})
    else:
        applications[uid]["files"].append({"type": "photo", "file_id": message.photo[-1].file_id})

    save_applications(applications)

    count = len(applications[uid]["files"])
    if count < 4:
        await message.answer(f"Принято {count}/4")
        return

    await message.answer("✅ Все чеки получены. Ожидай проверки")
    await state.clear()

    for admin_id in ADMINS:
        # Отправляем текстовое уведомление о новой заявке
        await bot.send_message(admin_id,
                               f"🆕 Новая заявка от пользователя {uid}!\n"
                               "Используй /view {uid} для просмотра файлов, "
                               "/accept {uid} для одобрения, /reject {uid} для отклонения.")
        # Отправляем все файлы заявки
        for file in applications[uid]["files"]:
            if file["type"] == "photo":
                await bot.send_photo(admin_id, file["file_id"])
            else:
                await bot.send_document(admin_id, file["file_id"])
# ================= АДМИН =================
@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id not in ADMINS:
        return

    if not applications:
        await message.answer("Заявок нет")
        return

    text = "📋 Заявки:\n\n"
    for uid, app in applications.items():
        text += f"{uid} — {app['status']}\n"

    text += (
        "\nКоманды:\n"
        "/view USER_ID — посмотреть файлы\n"
        "/accept USER_ID — одобрить\n"
        "/reject USER_ID — отклонить"
    )

    await message.answer(text)

@dp.message(Command("view"))
async def view_application(message: Message):
    if message.from_user.id not in ADMINS:
        return

    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Использование: /view USER_ID")
        return

    uid = parts[1]
    if uid not in applications:
        await message.answer("Заявка не найдена")
        return

    files = applications[uid]["files"]
    if not files:
        await message.answer("В заявке нет файлов")
        return

    await message.answer(f"📂 Файлы заявки {uid}:")
    for file in files:
        if file["type"] == "photo":
            await bot.send_photo(message.from_user.id, file["file_id"])
        else:
            await bot.send_document(message.from_user.id, file["file_id"])

@dp.message(Command("accept"))
async def accept_application(message: Message):
    if message.from_user.id not in ADMINS:
        return

    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Использование: /accept USER_ID")
        return

    uid = parts[1]
    if uid not in applications:
        await message.answer("Заявка не найдена")
        return

    applications[uid]["status"] = "approved"
    save_applications(applications)

    await bot.send_message(int(uid), "🎉 Ваша заявка одобрена!")
    await message.answer(f"Заявка {uid} одобрена")

@dp.message(Command("reject"))
async def reject_application(message: Message):
    if message.from_user.id not in ADMINS:
        return

    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Использование: /reject USER_ID")
        return

    uid = parts[1]
    if uid not in applications:
        await message.answer("Заявка не найдена")
        return

    applications[uid]["status"] = "rejected"
    save_applications(applications)

    await bot.send_message(int(uid), "❌ Ваша заявка отклонена")
    await message.answer(f"Заявка {uid} отклонена")

# ================= ЗАПУСК =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
