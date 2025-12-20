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
        [
            KeyboardButton(text="📄 Отправить чеки"),
            KeyboardButton(text="🆘 Поддержка"),
        ]
    ],
    resize_keyboard=True
)

# ================= ТЕКСТЫ =================

START_TEXT = (
    "Получи 6-ю процедуру «Сухой Туман» бесплатно! 🎁\n"
    "Воспользуйся услугой 5 раз — 6-я в подарок 💨 Все просто:\n"
    "1️⃣ Загрузи в бот 5 чеков\n"
    "2️⃣ Мы быстро их проверим\n"
    "3️⃣ Получи кешбэк в рублях на 1 полноценную процедуру\n\n"
    "Нажми «Начать» и забери свой бонус уже сегодня!"
)

# ================= ПОЛЬЗОВАТЕЛЬ =================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    uid = str(user_id)

    # 🔐 ЕСЛИ АДМИН — НИКАКИХ ЧЕКОВ
    if user_id in ADMINS:
        await state.clear()
        await message.answer(
            "👨‍💼 Вы администратор\n"
            "Используйте команду /admin для работы с заявками"
        )
        return

    # 👤 ОБЫЧНЫЙ ПОЛЬЗОВАТЕЛЬ
    if uid not in applications:
        applications[uid] = {
            "files": [],
            "status": "pending",
            "reject_reason": None
        }
        save_applications(applications)

    await message.answer(START_TEXT)
    await state.set_state(UploadChecks.waiting_files)


# ⚠️ ВАЖНО: ТОЛЬКО ТЕКСТ
@dp.message(F.text & ~F.text.startswith("/"))
async def handle_user_buttons(message: Message, state: FSMContext):
    uid = str(message.from_user.id)

    if message.text == "📄 Отправить чеки":
        applications.setdefault(uid, {
            "files": [],
            "status": "pending",
            "reject_reason": None
        })
        save_applications(applications)

        await message.answer("📤 Отправьте 5 фото или файла чеков")
        await state.set_state(UploadChecks.waiting_files)

    elif message.text == "🆘 Поддержка":
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✉️ Написать пользователю",
                        url=f"tg://user?id={uid}"
                    )
                ]
            ]
        )

        await bot.send_message(
            SUPPORT_CHAT_ID,
            f"🆘 Пользователю нужна помощь\nID: {uid}",
            reply_markup=kb
        )

        await message.answer("✅ Запрос в поддержку отправлен")

# ================= ЗАГРУЗКА ФАЙЛОВ =================

@dp.message(UploadChecks.waiting_files, F.photo | F.document)
async def handle_files(message: Message, state: FSMContext):
    uid = str(message.from_user.id)

    if message.photo:
        applications[uid]["files"].append({
            "type": "photo",
            "file_id": message.photo[-1].file_id
        })

    elif message.document:
        applications[uid]["files"].append({
            "type": "document",
            "file_id": message.document.file_id
        })

    save_applications(applications)

    count = len(applications[uid]["files"])

    if count < 5:
        await message.answer(f"📄 Принято {count}/5")
        return

    await message.answer("✅ Все чеки получены, заявка отправлена на проверку")
    await state.clear()

    await bot.send_message(
        SUPPORT_CHAT_ID,
        f"🆕 Новая заявка от пользователя {uid}\n"
        f"Чеков: {count}\n"
        f"Команда: /admin"
    )


@dp.message(UploadChecks.waiting_files)
async def wrong_content(message: Message):
    await message.answer("❗ Отправьте именно фото или файл")

# ================= АДМИН =================

def applications_keyboard():
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for uid, app in applications.items():
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{uid} — {app['status']}",
                callback_data=f"view:{uid}"
            )
        ])
    return kb


@dp.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return

    # ❗ ГАРАНТИРОВАННО УБИРАЕМ FSM
    await state.clear()

    if not applications:
        await message.answer("Заявок нет")
        return

    await message.answer(
        "📋 Список заявок:",
        reply_markup=applications_keyboard()
    )


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

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Одобрить",
                    callback_data=f"accept:{uid}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"reject:{uid}"
                )
            ]
        ]
    )

    await callback.message.answer("Выберите действие:", reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("accept:"))
async def accept_application(callback: CallbackQuery):
    uid = callback.data.split(":")[1]

    applications[uid]["status"] = "approved"
    applications[uid]["reject_reason"] = None
    save_applications(applications)

    await bot.send_message(int(uid), "🎉 Ваша заявка одобрена!")
    await callback.message.answer(f"✅ Заявка {uid} одобрена")
    await callback.answer()


@dp.callback_query(F.data.startswith("reject:"))
async def reject_start(callback: CallbackQuery, state: FSMContext):
    uid = callback.data.split(":")[1]
    await state.set_state(RejectReason.waiting_reason)
    await state.update_data(uid=uid)

    await callback.message.answer("✍️ Введите причину отказа:")
    await callback.answer()

@dp.callback_query(F.data.startswith("reject:"))
async def reject_start(callback: CallbackQuery, state: FSMContext):
    uid = callback.data.split(":")[1]

    await state.set_state(RejectReason.waiting_reason)
    await state.update_data(uid=uid)

    await callback.message.answer(
        f"✍️ Введите причину отказа для заявки {uid}:"
    )
    await callback.answer()


@dp.message(RejectReason.waiting_reason)
async def reject_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    uid = data["uid"]
    reason = message.text

    applications[uid]["status"] = "rejected"
    applications[uid]["reject_reason"] = reason
    save_applications(applications)

    await bot.send_message(
        int(uid),
        f"❌ Ваша заявка отклонена.\n\n"
        f"Причина:\n{reason}"
    )

    await message.answer(
        f"❌ Заявка {uid} отклонена\n"
        f"Причина сохранена"
    )

    await state.clear()


# ================= ЗАПУСК =================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
