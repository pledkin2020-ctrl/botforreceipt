# pip install aiogram==3.*

import asyncio
import json
import os

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

BOT_TOKEN = "8394021240:AAHHZy_PkUcGSCn_jmj2l6fBVjNvYyghK5E"

# === ADMIN IDS (зашиты в файл) ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "applications.txt")
ADMINS_FILE = os.path.join(BASE_DIR, "admins.txt")



def load_admins() -> set[int]:
    if not os.path.exists(ADMINS_FILE):
        return set()
    with open(ADMINS_FILE, "r", encoding="utf-8") as f:
        return {int(line.strip()) for line in f if line.strip().isdigit()}


def save_admins(admins: set[int]):
    with open(ADMINS_FILE, "w", encoding="utf-8") as f:
        for admin_id in admins:
            f.write(f"{admin_id}\n")


admins = load_admins()


# ============================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


# ================= FSM =================

class UploadChecks(StatesGroup):
    waiting_files = State()


class RejectReason(StatesGroup):
    waiting_reason = State()


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
        applications[uid] = {
            "files": [],
            "status": "pending",
            "reject_reason": None
        }
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
        applications[uid]["files"].append({
            "type": "document",
            "file_id": message.document.file_id
        })
    else:
        applications[uid]["files"].append({
            "type": "photo",
            "file_id": message.photo[-1].file_id
        })

    save_applications(applications)

    count = len(applications[uid]["files"])
    if count < 4:
        await message.answer(f"Принято {count}/4")
        return

    await message.answer("✅ Все чеки получены. Ожидай проверки")
    await state.clear()

    for admin_id in ADMINS:
        await bot.send_message(
            admin_id,
            f"🆕 Новая заявка от пользователя {uid}\nИспользуй /admin"
        )

# ================== ADMIN PANEL ==================
@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{uid} ({app['status']})",
                    callback_data=f"view:{uid}",
                )
            ]
            for uid, app in applications.items()
        ]
    )

    await message.answer("📋 Заявки:", reply_markup=kb)


@dp.callback_query(F.data.startswith("view:"))
async def view_app(callback: CallbackQuery):
    uid = callback.data.split(":")[1]

    app = applications.get(uid)
    if not app:
        await callback.answer("Заявка не найдена")
        return

    for f in app["files"]:
        if f["type"] == "photo":
            await bot.send_photo(callback.from_user.id, f["file_id"])
        else:
            await bot.send_document(callback.from_user.id, f["file_id"])

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Одобрить", callback_data=f"accept:{uid}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить", callback_data=f"reject:{uid}"
                ),
            ]
        ]
    )

    await bot.send_message(callback.from_user.id, "Решение:", reply_markup=kb)


@dp.callback_query(F.data.startswith("accept:"))
async def accept(callback: CallbackQuery):
    uid = callback.data.split(":")[1]

    applications[uid]["status"] = "approved"
    save_apps(applications)

    await bot.send_message(int(uid), "🎉 Ваша заявка одобрена!")
    await callback.message.answer("✅ Одобрено")


@dp.callback_query(F.data.startswith("reject:"))
async def reject(callback: CallbackQuery, state: FSMContext):
    uid = callback.data.split(":")[1]
    await state.update_data(uid=uid)
    await state.set_state(UploadFSM.reject_reason)
    await callback.message.answer("✍️ Введите причину отказа")


@dp.message(UploadFSM.reject_reason)
async def reject_reason(message: Message, state: FSMContext):
    data = await state.get_data()
    uid = data["uid"]

    applications[uid]["status"] = "rejected"
    applications[uid]["reason"] = message.text
    save_apps(applications)

    await bot.send_message(
        int(uid), f"❌ Заявка отклонена\nПричина: {message.text}"
    )
    await message.answer("❌ Заявка отклонена")
    await state.clear()


# ================== ADMIN MANAGEMENT ==================
@dp.message(Command("add_admin"))
async def add_admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    _, uid = message.text.split()
    admins.add(int(uid))
    save_admins(admins)
    await message.answer("✅ Админ добавлен")


@dp.message(Command("del_admin"))
async def del_admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    _, uid = message.text.split()
    admins.discard(int(uid))
    save_admins(admins)
    await message.answer("🗑 Админ удалён")


@dp.message(Command("admins"))
async def admins_list(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("\n".join(map(str, admins)))


# ================== START ==================
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())