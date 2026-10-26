import asyncio
import io
import json
import logging
import os
import random
import sqlite3
import time
import zipfile
import html

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

# ====================== CONFIG & CONSTANTS ======================
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
ADMIN_ID = 123456789

BOT_NAME = "BLACK STUDIO"
SETTINGS_FILE = "settings.json"
IMG = "images"
LINE = "----------------------------------------"

PAY_TEXT = "Для оплаты переведите нужную сумму и укажите ID профиля в комментарии."
SUPPORT_URL = "https://t.me/your_support"
REVIEWS_URL = "https://t.me/your_reviews"
OWNER_USERNAME = "@your_owner"
STARS_MODE = True
SUB_CHANNELS = []
AD_CHANNEL = "@your_channel"

TRIALS = {
    "mod": 1,
    "sql": 1,
    "adm": 1,
    "conv": 1,
    "apk": 1
}

ADS = {
    "24": (24, 150, 50),
    "48": (48, 250, 90),
    "72": (72, 350, 130)
}

# ====================== DATABASE & SETTINGS ======================

def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

SET = {
    "pay_text": PAY_TEXT,
    "support": SUPPORT_URL,
    "reviews": REVIEWS_URL,
    "owner": OWNER_USERNAME,
    "stars_mode": STARS_MODE,
    "prices": {},
    "subs": SUB_CHANNELS,
    "subs_on": True,
    "ad_channel": AD_CHANNEL,
    "admins": []
}
SET.update(load_json(SETTINGS_FILE, {}))

def save_set():
    save_json(SETTINGS_FILE, SET)

db = sqlite3.connect("nexus.db", check_same_thread=False)
db.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY,
    premium INTEGER DEFAULT 0,
    mod INTEGER,
    sql INTEGER,
    adm INTEGER,
    conv INTEGER,
    apk INTEGER,
    banned INTEGER DEFAULT 0,
    username TEXT,
    joined INTEGER,
    ban_until INTEGER,
    ref_by INTEGER,
    seen INTEGER
)
""")
db.commit()

def is_admin(uid):
    return uid == ADMIN_ID or uid in SET.get("admins", [])

def get_user(uid, username=None):
    r = db.execute(
        "SELECT premium, mod, sql, adm, conv, apk, banned, ban_until FROM users WHERE id=?", 
        (uid,)
    ).fetchone()
    
    if not r:
        db.execute(
            "INSERT INTO users(id, premium, mod, sql, adm, conv, apk, banned, username, joined) "
            "VALUES(?, 0, ?, ?, ?, ?, ?, 0, ?, ?)",
            (uid, TRIALS["mod"], TRIALS["sql"], TRIALS["adm"], TRIALS["conv"], TRIALS["apk"], username, int(time.time()))
        )
        db.commit()
        return get_user(uid, username)
        
    if username:
        db.execute("UPDATE users SET username=? WHERE id=?", (username, uid))
        db.commit()
        
    d = dict(zip(("premium", "mod", "sql", "adm", "conv", "apk", "banned", "ban_until"), r))
    d["banned"] = d["banned"] or 0
    return d

# ====================== KEYBOARDS & HELPERS ======================

def main_menu(uid=None):
    rows = [
        [KeyboardButton(text="🔥 Бесплатный проект")],
        [KeyboardButton(text="📊 Приобрести рекламу"), KeyboardButton(text="📍 Предложить слив")],
        [KeyboardButton(text="⚡ Купить MOD ULTRA"), KeyboardButton(text="🔧 Разработка")],
        [KeyboardButton(text="🎁 Промокод"), KeyboardButton(text="👥 Пригласить друзей")],
        [KeyboardButton(text="🔨 Компиляция"), KeyboardButton(text="🎰 Рулетка")]
    ]
    if is_admin(uid):
        rows.append([KeyboardButton(text="🛠 Админ-панель")])
    return ReplyKeyboardMarkup(resize_keyboard=True, input_field_placeholder="Выбери нужный раздел...", keyboard=rows)

def head(emoji, title):
    return f"{emoji} <b>{title}</b>\n{LINE}\n\n"

async def send_banner(m: Message, banner_name, text, markup=None):
    path = os.path.join(IMG, banner_name) if banner_name else None
    if path and os.path.exists(path):
        try:
            return await m.answer_photo(FSInputFile(path), caption=text, reply_markup=markup, parse_mode=ParseMode.HTML)
        except Exception:
            pass
    return await m.answer(text, reply_markup=markup, parse_mode=ParseMode.HTML)

# ====================== STATES ======================

class States(StatesGroup):
    promo = State()
    admin_broadcast = State()
    admin_user = State()
    dev_pwn = State()
    dev_sql = State()
    roulette = State()

# ====================== ROUTERS & HANDLERS ======================

router = Router()

@router.message(CommandStart())
@router.message(F.text == "Главное меню")
async def cmd_start(m: Message, state: FSMContext):
    await state.clear()
    u = m.from_user
    get_user(u.id, u.username)
    text = (
        head("🖐", f"Добро пожаловать, {html.escape(u.full_name)}!") +
        f"<b>{BOT_NAME}</b> — профессиональная студия разработки, модов и скриптов.\n\n"
        "🔥 <b>Доступные услуги:</b>\n"
        "• Бесплатные проекты и сливы\n"
        "• Компилятор и конвертер кода\n"
        "• Заказ разработки и модов (MOD ULTRA)\n"
        "• Покупка рекламы и продвижение\n\n" +
        LINE + "\n<i>Используй кнопки ниже для навигации.</i>"
    )
    await send_banner(m, "main.jpg", text, main_menu(u.id))

@router.message(F.text == "🔥 Бесплатный проект")
async def free_project(m: Message):
    text = (
        head("🔥", "Бесплатный проект") +
        "Вот твой бесплатный стартовый проект от BLACK STUDIO!\n\n"
        "Скачивай архив и приступай к работе."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Скачать проект (.zip)", callback_data="download_free")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_home")]
    ])
    await send_banner(m, "shop.jpg", text, kb)

@router.callback_query(F.data == "download_free")
async def cb_download_free(call: CallbackQuery):
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.txt", "Black Studio Free Project Template\nEnjoy coding!")
        zf.writestr("main.pwn", "// Main Pawn script code here\nmain() {\n    print(\"Hello Black Studio!\");\n}")
    bio.seek(0)
    await call.message.answer_document(
        BufferedInputFile(bio.read(), filename="BlackStudio_FreeProject.zip"),
        caption="🎁 Вот твой бесплатный проект! Распакуй архив и открой в редакторе."
    )
    await call.answer()

@router.message(F.text == "⚡ Купить MOD ULTRA")
async def buy_mod(m: Message):
    text = (
        head("⚡", "MOD ULTRA") +
        "Получи максимальные возможности и эксклюзивные исходники скриптов!\n\n"
        "Цена: <b>450 ₽</b> или <b>150 Звёзд</b>."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Купить за Рубли", callback_data="pay:mod_rub")],
        [InlineKeyboardButton(text="⭐ Купить за Звёзды", callback_data="pay:mod_stars")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_home")]
    ])
    await send_banner(m, "mod.jpg", text, kb)

@router.callback_query(F.data.startswith("pay:"))
async def cb_pay(call: CallbackQuery):
    method = call.data.split(":")[1]
    pay_type = 'Звёзды Telegram' if 'stars' in method else 'Перевод / Банковская карта'
    text = (
        head("💳", "Оплата заказа") +
        f"Способ оплаты: <b>{pay_type}</b>\n\n"
        f"{SET['pay_text']}\n\n"
        f"После оплаты отправь скриншот чека в поддержку: <a href='{SUPPORT_URL}'>Написать в поддержку</a>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Написать в поддержку", url=SUPPORT_URL)],
        [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_home")]
    ])
    await call.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await call.answer()

@router.message(F.text == "📊 Приобрести рекламу")
async def buy_ads(m: Message):
    text = head("📊", "Реклама в сети студии") + "Выбери подходящий тариф для продвижения своего канала или проекта:"
    kb = []
    for k, (hours, rub, stars) in ADS.items():
        kb.append([InlineKeyboardButton(text=f"📢 Реклама {hours}ч — {rub}₽ / {stars}⭐", callback_data=f"buyad:{k}")])
    kb.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_home")])
    await send_banner(m, "ads.jpg", text, InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("buyad:"))
async def cb_buyad(call: CallbackQuery):
    hours_key = call.data.split(":")[1]
    h, rub, stars = ADS[hours_key]
    text = (
        head("📢", f"Реклама на {h} часов") +
        f"Стоимость: <b>{rub} ₽</b> (или <b>{stars} ⭐</b>)\n\n"
        f"{SET['pay_text']}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Связаться с менеджером", url=SUPPORT_URL)],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_home")]
    ])
    await call.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await call.answer()

@router.message(F.text == "📍 Предложить слив")
async def offer_leak(m: Message):
    text = (
        head("📍", "Предложить слив / скрипт") +
        "Хочешь поделиться крутым модом или скриптом?\n"
        "Отправь файлы или ссылку напрямую администратору студии:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📬 Отправить слив", url=SUPPORT_URL)],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_home")]
    ])
    await m.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)

@router.message(F.text == "🔧 Разработка")
async def development_menu(m: Message):
    text = (
        head("🔧", "Заказ разработки") +
        "Мы выполняем любые заказы: от написания модов до настройки MySQL и создания APK приложений."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💻 Заказать мод / скрипт", url=SUPPORT_URL)],
        [InlineKeyboardButton(text="🗄 Настройка MySQL", url=SUPPORT_URL)],
        [InlineKeyboardButton(text="📱 Создание APK", url=SUPPORT_URL)],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_home")]
    ])
    await send_banner(m, "dev.jpg", text, kb)

@router.message(F.text == "🎁 Промокод")
async def promo_start(m: Message, state: FSMContext):
    await state.set_state(States.promo)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Главное меню")]], resize_keyboard=True)
    await m.answer(head("🎁", "Активация промокода") + "Введи промокод в чат:", reply_markup=kb, parse_mode=ParseMode.HTML)

@router.message(States.promo)
async def promo_process(m: Message, state: FSMContext):
    await state.clear()
    code = m.text.strip()
    if code.upper() == "BLACK2025":
        await m.answer("🎉 Промокод успешно активирован! Тебе начислена премиум-подписка на 24 часа.", reply_markup=main_menu(m.from_user.id))
    else:
        await m.answer("❌ Неверный или просроченный промокод.", reply_markup=main_menu(m.from_user.id))

@router.message(F.text == "👥 Пригласить друзей")
async def invite_friends(m: Message):
    bot_info = await m.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{m.from_user.id}"
    text = (
        head("👥", "Реферальная система") +
        "Приглашай друзей в нашу студию и получай бонусы!\n\n"
        f"🔗 Твоя реферальная ссылка:\n<code>{link}</code>"
    )
    await m.answer(text, reply_markup=main_menu(m.from_user.id), parse_mode=ParseMode.HTML)

@router.message(F.text == "🔨 Компиляция")
async def compiler_info(m: Message):
    text = head("🔨", "Онлайн Компилятор") + "Отправь свой файл с кодом (.pwn или текст скрипта), и бот выполнит тестовую проверку."
    await m.answer(text, reply_markup=main_menu(m.from_user.id), parse_mode=ParseMode.HTML)

@router.message(F.text == "🎰 Рулетка")
async def roulette(m: Message):
    prizes = ["50 рублей на баланс", "Премиум на 1 час", "Бесплатный мод", "Попробуй еще раз!", "Скидка 20%"]
    prize = random.choice(prizes)
    text = head("🎰", "Колесо Фортуны") + f"🎰 Результат розыгрыша:\n\n<b>{prize}</b>!"
    await m.answer(text, reply_markup=main_menu(m.from_user.id), parse_mode=ParseMode.HTML)

@router.callback_query(F.data == "back_home")
async def cb_back(call: CallbackQuery, state: FSMContext):
    await state.clear()
    u = call.from_user
    text = head("🖐", f"Главное меню, {html.escape(u.full_name)}") + "Выбери нужный раздел в меню ниже:"
    await call.message.delete()
    await send_banner(call.message, "main.jpg", text, main_menu(u.id))

# ====================== MAIN LAUNCHER ======================

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    
    print("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())