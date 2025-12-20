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
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

# ================= НАСТРОЙКИ =================

BOT_TOKEN = "8394021240:AAHHZy_PkUcGSCn_jmj2l6fBVjNvYyghK5E"

ADMINS = [
    123456789,
    7503094593,
    1246638096,
]

SUPPORT_CHAT_ID = -4862737517  # чат поддержки

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "applications.json")

# =============================================

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
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_applications(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

applications = load_applications()

# ================= КНОПКИ =================

user_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📄 Отправить чеки")],
        [KeyboardButton(text="🆘 Поддержка")]
    ],
    resize_keyboard=True
)

# ================= START =================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()

    if message.from_user.id in ADMINS:
        await message.answer(
            "👨‍💼 Вы администратор\nИспользуйте /admin"
        )
        return

    await message.answer(
        "Получи 6-ю процедуру «Сухой Туман» бесплатно! 🎁",
        reply_markup=user_keyboard
    )

# ================= КНОПКИ ПОЛЬЗОВАТЕЛЯ =================

@dp.message(F.text == "📄 Отправить чеки")
async def start_new_application(message: Message, state: FSMContext):
    uid = str(message.from_user.id)

    applications.setdefault(uid, [])

    app_id = len(applications[uid]) + 1
    applications[uid].append({
        "id": app_id,
        "files": [],
        "status": "pending",
        "reject_reason": None
    })
    save_applications(applications)

    await state.set_state(UploadChecks.waiting_files)
    await state.update_data(uid=uid, app_id=app_id)

    await message.answer(
        f"📤 Отправьте {FILES_REQUIRED} файлов чеков"
    )

@dp.message(F.text == "🆘 Поддержка")
async def support_request(message: Message):
    uid = message.from_user.id

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✉️ Написать пользователю",
            url=f"tg://user?id={uid}"
        )
    ]])

    await bot.send_message(
        SUPPORT_CHAT_ID,
        f"🆘 Запрос в поддержку\nПользователь: {uid}",
        reply_markup=kb
    )

    await message.answer("✅ Запрос отправлен в поддержку")

# ================= ЗАГРУЗКА ФАЙЛОВ =================

@dp.message(UploadChecks.waiting_files, F.photo | F.document)
async def handle_files(message: Message, state: FSMContext):
    data = await state.get_data()
    uid = data["uid"]
    app_id = data["app_id"]

    app = next(a for a in applications[uid] if a["id"] == app_id)

    if message.photo:
        app["files"].append({
            "type": "photo",
            "file_id": message.photo[-1].file_id
        })
    else:
        app["files"].append({
            "type": "document",
            "file_id": message.document.file_id
        })

    save_applications(applications)

    count = len(app["files"])
    if count < FILES_REQUIRED:
        await message.answer(f"📄 Принято {count}/{FILES_REQUIRED}")
        return

    await state.clear()
    await message.answer("✅ Все чеки получены, заявка отправлена")

    await bot.send_message(
        SUPPORT_CHAT_ID,
        f"🆕 Новая заявка\nПользователь: {uid}\nЗаявка #{app_id}"
    )

@dp.message(UploadChecks.waiting_files, F.photo | F.document)
async def wrong_content(message: Message):
    await message.answer("❗ Отправьте фото или файл")

# ================= АДМИН =================

@dp.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return

    await state.clear()

    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for uid, apps in applications.items():
        for app in apps:
            kb.inline_keyboard.append([
                InlineKeyboardButton(
                    text=f"{uid} | #{app['id']} — {app['status']}",
                    callback_data=f"view:{uid}:{app['id']}"
                )
            ])

    await message.answer("📋 Заявки:", reply_markup=kb)

@dp.callback_query(F.data.startswith("view:"))
async def view_application(callback: CallbackQuery):
    uid = callback.data.split(":")[1]

    await callback.message.answer(f"📂 Файлы заявки {uid}:")

    for file in applications[uid]["files"]:
        if file["type"] == "photo":
            await bot.send_photo(callback.from_user.id, file["file_id"])
        else:
            await bot.send_document(callback.from_user.id, file["file_id"])

    await callback.message.answer(
        "👤 Перейти в личные сообщения:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✉️ Написать пользователю",
                        url=f"tg://user?id={uid}"
                    )
                ]
            ]
        )
    )


    await callback.message.answer(
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton("✅ Одобрить", callback_data=f"accept:{uid}:{app_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject:{uid}:{app_id}")
        ]])
    )

    await callback.answer()

@dp.callback_query(F.data.startswith("accept:"))
async def accept_app(callback: CallbackQuery):
    _, uid, app_id = callback.data.split(":")
    app_id = int(app_id)

    app = next(a for a in applications[uid] if a["id"] == app_id)
    app["status"] = "approved"
    save_applications(applications)

    await bot.send_message(int(uid), "🎉 Ваша заявка одобрена!")
    await callback.message.answer("✅ Заявка одобрена")
    await callback.answer()

@dp.callback_query(F.data.startswith("reject:"))
async def reject_start(callback: CallbackQuery, state: FSMContext):
    _, uid, app_id = callback.data.split(":")
    await state.set_state(RejectReason.waiting_reason)
    await state.update_data(uid=uid, app_id=int(app_id))
    await callback.message.answer("✍️ Введите причину отказа:")
    await callback.answer()

@dp.message(RejectReason.waiting_reason)
async def reject_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    uid = data["uid"]
    app_id = data["app_id"]
    reason = message.text

    app = next(a for a in applications[uid] if a["id"] == app_id)
    app["status"] = "rejected"
    app["reject_reason"] = reason
    save_applications(applications)

    await bot.send_message(
        int(uid),
        f"❌ Заявка отклонена\nПричина:\n{reason}"
    )

    await message.answer("❌ Заявка отклонена")
    await state.clear()

# ================= ЗАПУСК =================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())