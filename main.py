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
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

BOT_TOKEN = "8394021240:AAHHZy_PkUcGSCn_jmj2l6fBVjNvYyghK5E"

# === ADMIN IDS (зашиты в файл) ===
ADMINS = [
    123456789,
    7503094593,
    1246638096,
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "applications.txt")
SUPPORT_CHAT_ID = -4862737517  # <-- сюда вставь ID нужного чата
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
    "1️⃣ Загрузи в бот 5 чеков\n"
    "2️⃣ Мы быстро их проверим\n"
    "3️⃣ Получи кешбэк в рублях на 1 полноценную процедуру\n\n"
    "Нажми «Начать» и забери свой бонус уже сегодня!"
)

# ================== Клавиатура для пользователя ==================
user_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📄 Отправить чеки"), KeyboardButton(text="🆘 Поддержка")]
    ],
    resize_keyboard=True
)

# ================== Старт ==================
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

    await message.answer(START_TEXT, reply_markup=user_kb)

# ================== Обработка кнопок пользователя ==================
@dp.message()
async def handle_user_buttons(message: Message, state: FSMContext):
    uid = str(message.from_user.id)
    text = message.text

    if text == "📄 Отправить чеки":
        await state.set_state(UploadChecks.waiting_files)
        await message.answer("Отправь 5 файлов/фото чеков по одному.")

    elif text == "🆘 Поддержка":
        for admin_id in ADMINS:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✉️ Написать пользователю",
                        url=f"tg://user?id={uid}"  # открывает чат, не вызывает send_message
                    )
                ]
            ])
            await bot.send_message(
                SUPPORT_CHAT_ID,
                f"🆘 Пользователю {uid} нужна помощь!",
                reply_markup=kb
            )
        await message.answer("✅ Запрос отправлен администраторам, ожидайте ответа.")
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
    if count < 5:
        await message.answer(f"Принято {count}/5")
        return

    await message.answer("✅ Все чеки получены. Ожидай проверки")
    await state.clear()

    # 🔔 Уведомляем всех админов о новой заявке
    for admin_id in ADMINS:
        # Сообщение с текстом о новой заявке
        await bot.send_message(
            admin_id,
            f"🆕 Новая заявка от пользователя {uid}!\n"
            "Используй команду /admin для просмотра заявок."
        )


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
async def admin_panel(message: Message):
    if message.from_user.id not in ADMINS:
        return

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

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✉️ Написать пользователю",
                url=f"tg://user?id={uid}"
            )
        ],
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
    ])

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
    await callback.answer("Одобрено")


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
        f"❌ Ваша заявка отклонена.\n\nПричина:\n{reason}"
    )

    await message.answer(f"❌ Заявка {uid} отклонена\nПричина сохранена")
    await state.clear()


# ================= ЗАПУСК =================

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())