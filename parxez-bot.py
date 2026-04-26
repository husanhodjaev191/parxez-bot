import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ─────────────────────────────────────────
# НАСТРОЙКИ
# ─────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Добавь его в Railway Variables")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ─────────────────────────────────────────
# ТЕКСТЫ
# ─────────────────────────────────────────
TEXTS = {
    "ru": {
        "choose_lang": "Выберите язык / Tilni tanlang:",
        "welcome": "👋 Добро пожаловать в бот ресторана *Parxez Dietka*!\nВыберите действие:",
        "btn_review": "⭐ Оставить отзыв",
        "btn_complaint": "⚠️ Оставить жалобу",
        "write_review": "✍️ Напишите ваш отзыв:",
        "write_complaint": "✍️ Опишите вашу жалобу:",
        "empty_msg": "❌ Сообщение не может быть пустым.",
        "ask_contacts": "Хотите оставить контактные данные?",
        "btn_yes": "✅ Да",
        "btn_no": "❌ Нет",
        "ask_name": "Введите имя и фамилию:",
        "ask_phone": "Введите номер телефона:",
        "thanks": "✅ Спасибо! Отправлено.",
        "admin_review": "⭐ Новый отзыв",
        "admin_complaint": "⚠️ Новая жалоба",
        "admin_anon": "Анонимно",
    },
    "uz": {
        "choose_lang": "Выберите язык / Tilni tanlang:",
        "welcome": "👋 *Parxez Dietka* botiga xush kelibsiz!\nAmalni tanlang:",
        "btn_review": "⭐ Fikr qoldirish",
        "btn_complaint": "⚠️ Shikoyat",
        "write_review": "✍️ Fikringizni yozing:",
        "write_complaint": "✍️ Shikoyatingizni yozing:",
        "empty_msg": "❌ Xabar bo'sh bo'lmasligi kerak.",
        "ask_contacts": "Kontakt qoldirasizmi?",
        "btn_yes": "✅ Ha",
        "btn_no": "❌ Yo'q",
        "ask_name": "Ism familiya:",
        "ask_phone": "Telefon:",
        "thanks": "✅ Rahmat!",
        "admin_review": "⭐ Yangi fikr",
        "admin_complaint": "⚠️ Yangi shikoyat",
        "admin_anon": "Anonim",
    },
}

def t(lang, key):
    return TEXTS.get(lang, TEXTS["ru"]).get(key, key)

# ─────────────────────────────────────────
# FSM
# ─────────────────────────────────────────
class Form(StatesGroup):
    lang = State()
    action = State()
    text = State()
    contact = State()
    name = State()
    phone = State()

# ─────────────────────────────────────────
# КНОПКИ
# ─────────────────────────────────────────
def kb_lang():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🇷🇺 Русский"), KeyboardButton(text="🇺🇿 O'zbekcha")]],
        resize_keyboard=True
    )

def kb_main(lang):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "btn_review")),
                   KeyboardButton(text=t(lang, "btn_complaint"))]],
        resize_keyboard=True
    )

def kb_yesno(lang):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "btn_yes")),
                   KeyboardButton(text=t(lang, "btn_no"))]],
        resize_keyboard=True
    )

# ─────────────────────────────────────────
# ЛОГИКА
# ─────────────────────────────────────────
@dp.message(CommandStart())
async def start(msg: Message, state: FSMContext):
    await state.set_state(Form.lang)
    await msg.answer(TEXTS["ru"]["choose_lang"], reply_markup=kb_lang())

@dp.message(Form.lang)
async def set_lang(msg: Message, state: FSMContext):
    lang = "ru" if "Рус" in msg.text else "uz"
    await state.update_data(lang=lang)
    await state.set_state(Form.action)
    await msg.answer(t(lang, "welcome"), reply_markup=kb_main(lang), parse_mode="Markdown")

@dp.message(Form.action)
async def action(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = data["lang"]

    if msg.text == t(lang, "btn_review"):
        await state.update_data(action="review")
        await state.set_state(Form.text)
        await msg.answer(t(lang, "write_review"), reply_markup=ReplyKeyboardRemove())
    elif msg.text == t(lang, "btn_complaint"):
        await state.update_data(action="complaint")
        await state.set_state(Form.text)
        await msg.answer(t(lang, "write_complaint"), reply_markup=ReplyKeyboardRemove())
    else:
        await msg.answer(t(lang, "welcome"), reply_markup=kb_main(lang))

@dp.message(Form.text)
async def get_text(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = data["lang"]

    if not msg.text.strip():
        await msg.answer(t(lang, "empty_msg"))
        return

    await state.update_data(text=msg.text)
    await state.set_state(Form.contact)
    await msg.answer(t(lang, "ask_contacts"), reply_markup=kb_yesno(lang))

@dp.message(Form.contact)
async def contact(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = data["lang"]

    if msg.text == t(lang, "btn_yes"):
        await state.set_state(Form.name)
        await msg.answer(t(lang, "ask_name"), reply_markup=ReplyKeyboardRemove())
    else:
        await send_admin(state, anonymous=True)
        await state.clear()
        await msg.answer(t(lang, "thanks"), reply_markup=kb_main(lang))

@dp.message(Form.name)
async def name(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text)
    await state.set_state(Form.phone)
    data = await state.get_data()
    await msg.answer(t(data["lang"], "ask_phone"))

@dp.message(Form.phone)
async def phone(msg: Message, state: FSMContext):
    await state.update_data(phone=msg.text)
    await send_admin(state, anonymous=False)
    await state.clear()
    data = await state.get_data()
    await msg.answer(t(data.get("lang","ru"), "thanks"), reply_markup=kb_main(data.get("lang","ru")))

# ─────────────────────────────────────────
# ОТПРАВКА
# ─────────────────────────────────────────
async def send_admin(state: FSMContext, anonymous):
    data = await state.get_data()
    lang = data["lang"]

    header = t(lang, "admin_review") if data["action"] == "review" else t(lang, "admin_complaint")

    if anonymous:
        contacts = t(lang, "admin_anon")
    else:
        contacts = f"{data.get('name')}\n{data.get('phone')}"

    text = f"{header}\n\n{data.get('text')}\n\n{contacts}"

    await bot.send_message(ADMIN_ID, text)

# ─────────────────────────────────────────
# ЗАПУСК
# ─────────────────────────────────────────
async def main():
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print("Ошибка:", e)

if __name__ == "__main__":
    asyncio.run(main())
