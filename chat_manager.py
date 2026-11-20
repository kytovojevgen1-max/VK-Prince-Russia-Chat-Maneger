import os
import json
import time
import asyncio
from threading import Thread
from flask import Flask
from vkbottle.bot import Bot, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text

# =====================================================================
# 1. ВЕБ-СЕРВЕР ДЛЯ РАБОТЫ 24/7 (RENDER)
# =====================================================================
app = Flask(__name__)
START_TIME = time.time()

@app.route('/')
def home():
    uptime_sec = int(time.time() - START_TIME)
    hours, remainder = divmod(uptime_sec, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"Prince Russia Core Server: ONLINE 24/7 | Uptime: {hours}h {minutes}m {seconds}s"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

Thread(target=run_flask, daemon=True).start()


# =====================================================================
# 2. КОНФИГУРАЦИЯ И БАЗА ДАННЫХ
# =====================================================================
TOKEN = "vk1.a.qGTN_rCK6d4Yg4ty8YkruE6DbovbX5lwzHcQcN6wQ15aACfSrhsyi5F7R9xip5mq03EeLvxI2gZwJSVvuWMv0eP7vv59FFJvPNYWpRI7R2nzXM0gbobnLpmRaI3yM751Cml4ZOPDcIc380c3hekN0jgZ3QeP76p9hn1Sw6kwK6mOCyomwB33nVy1uBGAbC0mDQpu5eiq2HlVDAKi4YjHYw"
bot = Bot(token=TOKEN)

MAIN_OWNER_ID = 897082738  # Доступ к панели рассылки в ЛС
DB_FILE = "chat_manager_db.json"

DEFAULT_ROLES = {
    100: "👑 Владелец / Основатель",
    95: "💎 Зам. Основателя",
    90: "🚀 Руководитель Проекта",
    88: "⚡ Зам. Руководителя",
    80: "🛡 Спец. Администратор",
    77: "🔥 Красная Администрация",
    75: "⭐ Зам. Спец. Админа",
    70: "🛠 Команда Проекта",
    60: "📌 Главный Администратор",
    55: "🔸 ОЗГА / ЗГА",
    45: "🔹 Куратор Администрации"
}

WELCOME_GUIDE = (
    "👋 **Привет! Чат-менеджер PRINCE RUSSIA подключен к беседе!**\n\n"
    "👑 **Владелец чата получает `100 lvl` админки** и отображается в `/admins` (`/админс`) и `/stats` (`/стата`).\n"
    "Если бот не определил владельца автоматически — владелец чата может прописать `/явладелец` (если владелец ещё не задан) или `/сетвладелец @ник`.\n"
    "📌 *Совет:* выдай боту права администратора в чате, чтобы работали кики, баны, муты, очистка и закреп сообщений.\n\n"
    "⚡ **Быстрый старт:**\n"
    "• `/menu` или `меню` — интерактивные кнопки в беседе\n"
    "• `/help` или `/хелп` — полный список команд\n"
    "• `/репорт [текст]` — отправить обращение администрации\n"
    "• `/сник @ник [Ник]` — выдать ник (60+ lvl)\n"
    "• `/сетадмин @ник [ур]` — выдать уровень прав (70+ lvl)"
)

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_db(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения БД: {e}")

db = load_db()
if "chats" not in db: db["chats"] = {}
if "global_chats" not in db: db["global_chats"] = []
if "broadcast_admins" not in db: db["broadcast_admins"] = [MAIN_OWNER_ID]
if "global_roles" not in db: db["global_roles"] = {}
if "global_bans" not in db: db["global_bans"] = {}
if "global_role_names" not in db: db["global_role_names"] = DEFAULT_ROLES.copy()
if "leaders" not in db: db["leaders"] = {}
if "reports" not in db: db["reports"] = []
if "logs" not in db: db["logs"] = []

user_states = {}
user_cache = {}

def add_log(text):
    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
    entry = f"{timestamp} {text}"
    db["logs"].append(entry)
    if len(db["logs"]) > 250:
        db["logs"].pop(0)
    save_db(db)

def get_chat_data(peer_id):
    p_str = str(peer_id)
    if p_str not in db["chats"]:
        db["chats"][p_str] = {
            "members": {},
            "bans": {},
            "warns": {},
            "mutes": {},
            "role_names": DEFAULT_ROLES.copy(),
            "welcomed": False,
            "owner_id": None,
            "antispam": False
        }
    chat = db["chats"][p_str]
    chat.setdefault("members", {})
    chat.setdefault("bans", {})
    chat.setdefault("warns", {})
    chat.setdefault("mutes", {})
    chat.setdefault("role_names", DEFAULT_ROLES.copy())
    chat.setdefault("welcomed", False)
    chat.setdefault("owner_id", None)
    chat.setdefault("antispam", False)
    return chat

def sync_owner_member(chat_data: dict, owner_id: int | None):
    if owner_id and int(owner_id) > 0:
        oid = int(owner_id)
        chat_data["owner_id"] = oid
        o_str = str(oid)
        current_data = chat_data["members"].get(o_str, {})
        nick = current_data.get("nickname", "") if isinstance(current_data, dict) else ""
        chat_data["members"][o_str] = {
            "level": 100,
            "nickname": nick,
            "is_owner": True
        }

async def resolve_chat_owner(peer_id, chat_data: dict):
    title = f"Беседа {peer_id}"
    vk_owner_id = None

    try:
        chat_info = await bot.api.messages.get_conversations_by_peer_ids(peer_ids=[peer_id])
        if chat_info and chat_info.items:
            conv = chat_info.items[0]
            settings = getattr(conv, "chat_settings", None)
            if settings:
                if getattr(settings, "title", None):
                    title = settings.title
                raw_owner = getattr(settings, "owner_id", None)
                if raw_owner is not None and int(raw_owner) > 0:
                    vk_owner_id = int(raw_owner)
    except Exception:
        pass

    if vk_owner_id:
        chat_data["owner_id"] = vk_owner_id

    owner_id = chat_data.get("owner_id")
    if owner_id:
        sync_owner_member(chat_data, int(owner_id))

    return title, int(owner_id) if owner_id else None

def is_chat_owner(uid: int, chat_data: dict, owner_id: int | None) -> bool:
    if owner_id and int(uid) == int(owner_id):
        return True
    saved_owner = chat_data.get("owner_id")
    if saved_owner and int(uid) == int(saved_owner):
        return True
    return False

def get_user_level_by_id(uid: int, chat_data: dict, owner_id: int | None) -> int:
    if is_chat_owner(uid, chat_data, owner_id):
        return 100

    m_info = chat_data.get("members", {}).get(str(uid), 0)
    if isinstance(m_info, dict):
        lvl = int(m_info.get("level", 0))
        if lvl > 0:
            return lvl
    elif isinstance(m_info, (int, float)):
        lvl = int(m_info)
        if lvl > 0:
            return lvl

    if str(uid) in db.get("global_roles", {}):
        return int(db["global_roles"][str(uid)])

    return 0

def get_role_title(lvl: int, chat_data: dict, owner_flag: bool = False) -> str:
    all_r = {**db["global_role_names"], **chat_data["role_names"]}
    if owner_flag or lvl >= 100:
        return all_r.get(100) or all_r.get("100") or "👑 Владелец / Основатель"
    if lvl <= 0:
        return "Участник"
    return all_r.get(lvl) or all_r.get(str(lvl)) or "Администратор"

async def format_vk_user(uid: int) -> str:
    if uid <= 0:
        return f"ID {uid}"
    now = time.time()
    cached = user_cache.get(uid)
    if cached and (now - cached["ts"] < 3600):
        return cached["label"]
    try:
        users = await bot.api.users.get(user_ids=[uid], fields=["screen_name"])
        if users:
            u = users[0]
            full_name = f"{u.first_name} {u.last_name}".strip()
            screen = f" (@{u.screen_name})" if getattr(u, "screen_name", None) else ""
            label = f"[id{uid}|{full_name}]{screen}"
            user_cache[uid] = {"label": label, "ts": now}
            return label
    except Exception:
        pass
    return f"[id{uid}|ID {uid}]"

def extract_mention_id(raw_token: str) -> int | None:
    token = raw_token.strip()
    if token.startswith("[id") and "|" in token and token.endswith("]"):
        inner = token[3:].split("|", 1)[0]
        if inner.isdigit():
            return int(inner)
    if token.startswith("[club") and "|" in token and token.endswith("]"):
        inner = token[5:].split("|", 1)[0]
        if inner.isdigit():
            return -int(inner)
    return None

async def resolve_target(message: Message, args: list):
    if message.reply_message:
        return message.reply_message.from_id, args
    if not args:
        return None, []

    target_raw = args[0].strip()
    remaining_args = args[1:]

    mention_id = extract_mention_id(target_raw)
    if mention_id:
        return mention_id, remaining_args

    cleaned = (
        target_raw
        .replace("https://vk.com/", "")
        .replace("http://vk.com/", "")
        .replace("vk.com/", "")
        .replace("m.vk.com/", "")
        .lstrip("@")
        .strip()
    )

    if cleaned.lower().startswith("id") and cleaned[2:].isdigit():
        return int(cleaned[2:]), remaining_args

    if cleaned.isdigit():
        return int(cleaned), remaining_args

    if cleaned:
        try:
            user_info = await bot.api.users.get(user_ids=[cleaned])
            if user_info:
                return int(user_info[0].id), remaining_args
        except Exception:
            pass

    return None, args

def get_chat_inline_keyboard() -> str:
    kb = Keyboard(one_time=False, inline=True)
    kb.add(Text("👑 Админы"), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("📊 Стата"), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("📋 Роли"), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("📜 Правила"), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("🛠 Модерация"), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text("📖 Команды"), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("🌐 Сайт"), color=KeyboardButtonColor.SECONDARY)
    return kb.get_json()


# =====================================================================
# 3. ЛИЧНЫЕ СООБЩЕНИЯ (ПАНЕЛЬ УПРАВЛЕНИЯ В ЛС)
# =====================================================================

@bot.on.private_message(text=["/start", "Начать", "начать", "Меню", "меню", "🔙 Главное меню", "❌ Отмена"])
async def private_start(message: Message):
    uid = message.from_id
    if uid in user_states:
        del user_states[uid]
    is_main = (uid == MAIN_OWNER_ID)
    has_broadcast = (is_main or uid in db["broadcast_admins"])

    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("🌐 Сайт проекта"), color=KeyboardButtonColor.POSITIVE)
    if has_broadcast:
        kb.row()
        kb.add(Text("➕ Выдать доступ к рассылке"), color=KeyboardButtonColor.POSITIVE)
        kb.add(Text("📜 Логи рассылок"), color=KeyboardButtonColor.PRIMARY)
        kb.row()
        kb.add(Text("👥 Список админов рассылки"), color=KeyboardButtonColor.PRIMARY)
        kb.add(Text("📢 Начать рассылку по чатам"), color=KeyboardButtonColor.NEGATIVE)

    await message.answer(
        "👑 **PRINCE RUSSIA — ULTIMATE ADMIN CONTROL x500** 👑\n\n"
        "Добро пожаловать в центр управления сетью чатов проекта.\n"
        "Владелец каждой беседы получает `100 lvl`.",
        keyboard=kb.get_json()
    )

@bot.on.private_message(text="➕ Выдать доступ к рассылке")
async def private_add_adm(message: Message):
    uid = message.from_id
    if uid != MAIN_OWNER_ID and uid not in db["broadcast_admins"]:
        return
    user_states[uid] = "wait_add_adm"
    await message.answer(
        "✍️ Введите цифровой VK ID или @ник пользователя для выдачи доступа к глобальной рассылке:",
        keyboard=Keyboard(one_time=False, inline=True).add(Text("❌ Отмена"), color=KeyboardButtonColor.NEGATIVE).get_json()
    )

@bot.on.private_message(text="📜 Логи рассылок")
async def private_view_logs(message: Message):
    uid = message.from_id
    if uid != MAIN_OWNER_ID and uid not in db["broadcast_admins"]:
        return
    broadcast_logs = [log for log in db["logs"] if "рассылка" in log.lower() or "рассылки" in log.lower()]
    recent = "\n".join(broadcast_logs[-10:]) if broadcast_logs else "📋 Логов рассылок пока нет."
    await message.answer(f"📜 **ИСТОРИЯ ОФИЦИАЛЬНЫХ РАССЫЛОК:**\n\n{recent}")

@bot.on.private_message(text="👥 Список админов рассылки")
async def private_view_admins(message: Message):
    uid = message.from_id
    if uid != MAIN_OWNER_ID and uid not in db["broadcast_admins"]:
        return
    lines = []
    for aid in db["broadcast_admins"]:
        lines.append(f"• {await format_vk_user(aid)}")
    await message.answer(f"👥 **ДОВЕРЕННЫЕ АДМИНЫ РАССЫЛКИ:**\n\n" + "\n".join(lines))

@bot.on.private_message(text="📢 Начать рассылку по чатам")
async def private_broadcast_start(message: Message):
    uid = message.from_id
    if uid != MAIN_OWNER_ID and uid not in db["broadcast_admins"]:
        return
    user_states[uid] = "wait_broadcast"
    await message.answer(
        "✍️ Введите текст для массовой отправки по всем беседам проекта:",
        keyboard=Keyboard(one_time=False, inline=True).add(Text("❌ Отмена"), color=KeyboardButtonColor.NEGATIVE).get_json()
    )

@bot.on.private_message(text="🌐 Сайт проекта")
async def private_site(message: Message):
    await message.answer("🌐 Официальный портал Prince Russia: https://site-prince-russia.samp.date/")

@bot.on.private_message()
async def private_handler(message: Message):
    uid = message.from_id
    text = message.text
    if not text:
        return
    state = user_states.get(uid)

    if state == "wait_add_adm" and (uid == MAIN_OWNER_ID or uid in db["broadcast_admins"]):
        del user_states[uid]
        tid, _ = await resolve_target(message, [text.strip()])
        if tid and tid > 0:
            if tid not in db["broadcast_admins"]:
                db["broadcast_admins"].append(tid)
                save_db(db)
                u_fmt = await format_vk_user(tid)
                add_log(f"Админ {await format_vk_user(uid)} выдал права рассылки для {u_fmt}")
                return await message.answer(f"✅ Успешно! {u_fmt} добавлен в список рассыльщиков.")
            return await message.answer("ℹ️ Этот пользователь уже в списке.")
        return await message.answer("❌ Ошибка: укажите корректный VK ID или @ник.")

    if state == "wait_broadcast" and (uid == MAIN_OWNER_ID or uid in db["broadcast_admins"]):
        del user_states[uid]
        count = 0

        broadcast_text = (
            "📢 **ВНИМАНИЕ! ОФИЦИАЛЬНОЕ СООБЩЕНИЕ ОТ PRINCE RUSSIA** 📢\n\n"
            f"{text}\n\n"
            "═══════════════════════════\n"
            f"👤 Ответственный за рассылку: {await format_vk_user(uid)}\n"
            "🌐 Портал: https://site-prince-russia.samp.date/\n"
            "@all"
        )

        for cid in db.get("global_chats", []):
            try:
                await bot.api.messages.send(peer_id=int(cid), message=broadcast_text, random_id=0)
                count += 1
            except Exception:
                pass

        add_log(f"Массовая рассылка выполнена {await format_vk_user(uid)}. Охвачено чатов: {count}")
        return await message.answer(f"🚀 **Рассылка успешно завершена!**\n• Доставлено в беседы: `{count}`")

    await message.answer(
        "👋 Бот готов к работе в любой беседе! Просто добавь его в чат, выдай права админа и используй `/menu` или `/help`."
    )


# =====================================================================
# 4. РАБОТА В БЕСЕДАХ (МОДЕРАЦИЯ, КНОПКИ, ТИКЕТЫ И КОМАНДЫ)
# =====================================================================

@bot.on.chat_message()
async def chat_handler(message: Message):
    peer_id = message.peer_id
    uid_int = message.from_id
    uid_str = str(uid_int)
    chat_data = get_chat_data(peer_id)

    is_new_chat = peer_id not in db["global_chats"]
    if is_new_chat:
        db["global_chats"].append(peer_id)

    chat_title, owner_id = await resolve_chat_owner(peer_id, chat_data)
    save_db(db)

    if message.action and message.action.type == "chat_invite_user":
        j_id = message.action.member_id
        group_id = getattr(message, "group_id", None)
        is_bot_invited = (group_id and j_id == -group_id) or (j_id is not None and j_id < 0)

        if is_bot_invited or (is_new_chat and not chat_data.get("welcomed")):
            chat_data["welcomed"] = True
            save_db(db)
            await message.answer(WELCOME_GUIDE, keyboard=get_chat_inline_keyboard())
            return

        if j_id and (str(j_id) in db["global_bans"] or str(j_id) in chat_data.get("bans", {})):
            try:
                await bot.api.messages.remove_chat_user(chat_id=message.chat_id, user_id=j_id)
                await message.answer(f"⛔ Вход заблокирован! У {await format_vk_user(j_id)} активный бан.")
            except Exception:
                pass
            return

    if uid_str in chat_data.get("mutes", {}):
        if time.time() < chat_data["mutes"][uid_str]:
            try:
                await bot.api.messages.delete(
                    peer_id=peer_id,
                    conversation_message_ids=[message.conversation_message_id],
                    delete_for_all=True
                )
            except Exception:
                pass
            return
        else:
            del chat_data["mutes"][uid_str]
            save_db(db)

    text = message.text
    if not text:
        return

    raw_text = text.strip()
    clean_text = raw_text.lower()

    user_lvl = get_user_level_by_id(uid_int, chat_data, owner_id)
    if chat_data.get("antispam") and user_lvl < 45:
        if any(bad in clean_text for bad in ["http://", "https://", "t.me/", "vk.me/", "discord.gg/"]):
            try:
                await bot.api.messages.delete(
                    peer_id=peer_id,
                    conversation_message_ids=[message.conversation_message_id],
                    delete_for_all=True
                )
                await message.answer(f"🛡 Антиспам удалил ссылку от {await format_vk_user(uid_int)}.")
            except Exception:
                pass
            return

    for mention in ["[club" + str(message.group_id) + "|@", "@club", "@public"]:
        if mention in clean_text:
            parts = raw_text.split(" ", 1)
            if len(parts) > 1:
                raw_text = parts[1].strip()
                clean_text = raw_text.lower()

    if clean_text in ["/menu", "/panel", "/панель", "меню", "панель"]:
        return await message.answer("👑 **ПАНЕЛЬ УПРАВЛЕНИЯ БЕСЕДОЙ**", keyboard=get_chat_inline_keyboard())

    if clean_text in ["🌐 сайт", "сайт"]:
        return await message.answer("🌐 Официальный портал Prince Russia: https://site-prince-russia.samp.date/", keyboard=get_chat_inline_keyboard())

    if clean_text in ["📜 правила", "правила"]:
        return await message.answer(
            "📜 **РЕГЛАМЕНТ БЕСЕДЫ:**\n"
            "1. Строго без спама и рекламы.\n"
            "2. Уважение к администрации и участникам.\n"
            "3. Лимит предупреждений: 3 варна ➔ автоматический кик.",
            keyboard=get_chat_inline_keyboard()
        )

    if clean_text in ["🛠 модерация", "модерация"]:
        return await message.answer(
            "🛠 **ШПАРГАЛКА МОДЕРАЦИИ И ПРАВ**\n\n"
            "• `45+ lvl`: `/мут`, `/анмут`, `/варн`, `/варны`, `/анварн`, `/кик`, `/очистить`, `/закреп`, `/откреп`\n"
            "• `55+ lvl`: `/бан`, `/анбан`, `/банлист`, `/снятьвсеварны`\n"
            "• `60+ lvl`: `/сник`, `/делник`, `/сетлидер`, `/снятлидера`, `/ответить`\n"
            "• `70+ lvl`: `/сетадмин`, `/снятьроль`, `/логи`, `/размутвсех`, `/антиспам`\n"
            "• `90+ lvl`: `/сетвладелец`, `/сбросвладельца`, `/гбан`, `/новаяроль`, `/удалитьроль`\n\n"
            "💡 *Пример:* `/сетадмин @evgenn09 70` или `/сник @evgenn09 Куратор`",
            keyboard=get_chat_inline_keyboard()
        )

    if clean_text in ["📋 роли", "/roles", "/роли", "роли"]:
        r_list = "📋 **ИЕРАРХИЯ ДОЛЖНОСТЕЙ PRINCE RUSSIA:**\n\n"
        all_roles = {**db["global_role_names"], **chat_data["role_names"]}
        for lvl in sorted((int(k) for k in all_roles.keys()), reverse=True):
            title = all_roles.get(lvl) or all_r_val if (all_r_val := all_roles.get(str(lvl))) else "Роль"
            r_list += f"• `{lvl} lvl` ➔ **{title}**\n"
        return await message.answer(r_list, keyboard=get_chat_inline_keyboard())

    if clean_text in ["👑 админы", "/admins", "/админс", "админы", "админс"]:
        clean_text = "/admins"
        raw_text = "/admins"

    if clean_text in ["📊 стата", "/stats", "/стата", "/профиль", "стата"]:
        clean_text = "/stats"
        raw_text = "/stats"

    if clean_text in ["📖 команды", "/help", "/хелп", "команды", "хелп"]:
        clean_text = "/help"
        raw_text = "/help"

    if not clean_text.startswith("/"):
        return

    args = raw_text[1:].split()
    cmd = args[0].lower() if args else ""
    params = args[1:] if len(args) > 1 else []

    if cmd in ["help", "хелп"]:
        help_msg = (
            "📖 **ЭКСКЛЮЗИВНЫЙ СПИСОК КОМАНД PRINCE RUSSIA x500** 📖\n\n"
            "💡 *Цель можно указать через `@ник`, `id`, ссылку или ответом (реплаем).*\n\n"
            "🌐 **Общий функционал:**\n"
            "• `/menu` (`/панель`) — интерактивные кнопки чата\n"
            "• `/stats` (`/стата`, `/профиль`) — досье участника\n"
            "• `/проверка` (`/check`) `[@ник/id/ответ]` — расширенное досье\n"
            "• `/admins` (`/админс`) — владелец (`100 lvl`) и админы чата\n"
            "• `/staff` (`/состав`) — полный состав чата и лидеры\n"
            "• `/nlist` (`/нлист`) — список ников участников\n"
            "• `/ник [текст]` — установить свой ник\n"
            "• `/roles` (`/роли`) — иерархия рангов\n"
            "• `/leaders` (`/лидеры`) — список лидеров\n"
            "• `/info` (`/инфо`) — информация о беседе\n"
            "• `/репорт [текст]` (`/report`) — создать тикет/репорт\n"
            "• `/бонус` (`/bonus`) — бонусы проекта\n"
            "• `/пинг` (`/ping`) и `/статус` (`/status`) — пинг и аптайм\n"
            "• `/явладелец` — закрепить владельца беседы (`100 lvl`), если он ещё не задан\n\n"
        )
        if user_lvl >= 45:
            help_msg += (
                "🛡 **Модерация чата (45+ lvl):**\n"
                "• `/мут` (`/mute`) `[@ник/id/ответ] [минуты]` — выдать мут\n"
                "• `/анмут` (`/unmute`) `[@ник/id/ответ]` — снять мут\n"
                "• `/кик` (`/kick`) `[@ник/id/ответ]` — исключить из чата\n"
                "• `/варн` (`/warn`) `[@ник/id/ответ] [причина]` — выдать варн (3 = кик)\n"
                "• `/варны` (`/warns`) `[@ник/id/ответ]` — список варнов игрока\n"
                "• `/анварн` (`/unwarn`) `[@ник/id/ответ]` — снять последний варн\n"
                "• `/закреп` (`/pin`) — закрепить сообщение (в ответ на него)\n"
                "• `/откреп` (`/unpin`) — открепить сообщение\n"
                "• `/очистить` (`/clear`) `[кол-во]` — удалить последние сообщения\n\n"
            )
        if user_lvl >= 55:
            help_msg += (
                "🚨 **Старшая модерация (55+ lvl):**\n"
                "• `/бан` (`/ban`) `[@ник/id/ответ] [причина]` — заблокировать в чате\n"
                "• `/анбан` (`/unban`) `[@ник/id]` — разблокировать в чате\n"
                "• `/банлист` (`/banlist`) — чёрный список беседы\n"
                "• `/снятьвсеварны` (`/clearwarns`) `[@ник/id/ответ]` — обнулить варны\n\n"
            )
        if user_lvl >= 60:
            help_msg += (
                "👑 **Руководство (60+ lvl):**\n"
                "• `/сник` (`/snick`, `/setnick`) `[@ник/id/ответ] [Ник]` — выдать ник\n"
                "• `/делник` (`/delnick`) `[@ник/id/ответ]` — удалить ник\n"
                "• `/сетлидер` (`/setleader`) `[@ник/id/ответ] [Организация]` — поставить лидера\n"
                "• `/снятлидера` (`/removeleader`) `[@ник/id/ответ]` — снять лидера\n"
                "• `/репорты` (`/reports`) и `/ответить` `[#id] [ответ]` — работа с репортами\n\n"
            )
        if user_lvl >= 70:
            help_msg += (
                "⚡ **Администрация (70+ lvl):**\n"
                "• `/сетадмин` (`/setadmin`, `/выдатьроль`, `/роль`) `[@ник/id/ответ] [ур]` — выдать уровень\n"
                "• `/снятьроль` (`/removerole`) `[@ник/id/ответ]` — снять уровень (0 lvl)\n"
                "• `/размутвсех` (`/unmuteall`) — снять все муты в чате\n"
                "• `/антиспам` (`/antispam`) — вкл/выкл авто-удаление ссылок\n"
                "• `/логи` (`/logs`) — системные логи\n\n"
            )
        if user_lvl >= 90:
            help_msg += (
                "🔥 **Высший состав (90+ lvl):**\n"
                "• `/сетвладелец` (`/setowner`) `[@ник/id/ответ]` — закрепить владельца чата\n"
                "• `/сбросвладельца` (`/resetowner`) — сбросить владельца чата\n"
                "• `/гбан` (`/gban`) `[@ник/id/ответ] [причина]` — глобальный бан\n"
                "• `/новаяроль` (`/newrole`) `[ур] [Название]` — создать роль\n"
                "• `/удалитьроль` (`/delrole`) `[ур]` — удалить роль\n"
            )
        return await message.answer(help_msg, keyboard=get_chat_inline_keyboard())

    elif cmd in ["явладелец", "claimowner"]:
        if chat_data.get("owner_id"):
            return await message.answer(
                f"❌ Владелец в этой беседе уже зафиксирован: {await format_vk_user(int(chat_data['owner_id']))}."
            )
        sync_owner_member(chat_data, int(uid_int))
        save_db(db)
        return await message.answer("👑 Вы закреплены владельцем этой беседы (`100 lvl`).")

    elif cmd in ["сбросвладельца", "resetowner"]:
        if user_lvl < 90:
            return await message.answer(f"❌ Требуется 90+ уровень (у вас: {user_lvl}).")
        old_owner = chat_data.get("owner_id")
        chat_data["owner_id"] = None
        if old_owner and str(old_owner) in chat_data["members"]:
            del chat_data["members"][str(old_owner)]
        save_db(db)
        return await message.answer("♻️ Владелец беседы сброшен. Теперь можно назначить нового через `/сетвладелец` или `/явладелец`.")

    elif cmd in ["ping", "пинг"]:
        start_t = time.time()
        await message.answer("🏓 Измеряем задержку...")
        end_t = time.time()
        ping_ms = int((end_t - start_t) * 1000)
        status_emoji = "🟢 Молниеносно" if ping_ms < 600 else "🟡 Стабильно" if ping_ms < 1200 else "🔴 Высокий пинг"
        return await message.answer(
            f"🏓 **PONG!**\n"
            f"• Отклик API VK: `{ping_ms} ms`\n"
            f"• Состояние: {status_emoji}"
        )

    elif cmd in ["status", "статус"]:
        uptime_sec = int(time.time() - START_TIME)
        hours, remainder = divmod(uptime_sec, 3600)
        minutes, seconds = divmod(remainder, 60)
        chats_count = len(db.get("global_chats", []))
        return await message.answer(
            f"⚡ **СТАТУС ЯДРА PRINCE RUSSIA x500**\n\n"
            f"• Аптайм сервера: `{hours}ч {minutes}м {seconds}с`\n"
            f"• Подключено чатов: `{chats_count}`\n"
            f"• Репортов в базе: `{len(db.get('reports', []))}`\n"
            f"• Версия сборки: `v10.4 Fixed Owner Sync`"
        )

    elif cmd in ["info", "инфо"]:
        owner_fmt = await format_vk_user(int(owner_id)) if owner_id else "Не определён"
        antispam_str = "🟢 Включён" if chat_data.get("antispam") else "🔴 Выключен"
        return await message.answer(
            f"ℹ️ **ИНФОРМАЦИЯ О БЕСЕДЕ**\n\n"
            f"• Название: **{chat_title}**\n"
            f"• Peer ID: `{peer_id}`\n"
            f"• Владелец: {owner_fmt}\n"
            f"• Антиспам ссылок: {antispam_str}\n"
            f"• Ваш уровень: `{user_lvl} lvl` ({get_role_title(user_lvl, chat_data, is_chat_owner(uid_int, chat_data, owner_id))})\n"
            f"• Участников в базе чата: `{len(chat_data.get('members', {}))}`"
        )

    elif cmd in ["report", "репорт"]:
        if not params:
            return await message.answer("❌ Формат: `/репорт [описание проблемы, жалобы или вопроса]`")
        rep_text = " ".join(params).strip()
        rep_id = len(db["reports"]) + 1
        rep_entry = {
            "id": rep_id,
            "peer_id": peer_id,
            "chat_title": chat_title,
            "from_id": uid_int,
            "text": rep_text,
            "status": "open",
            "reply": None,
            "time": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        db["reports"].append(rep_entry)
        save_db(db)

        sender_fmt = await format_vk_user(uid_int)
        add_log(f"Репорт #{rep_id} в «{chat_title}» от {sender_fmt}: {rep_text}")

        if owner_id and int(owner_id) != uid_int:
            try:
                await bot.api.messages.send(
                    peer_id=int(owner_id),
                    message=(
                        f"📩 **НОВЫЙ РЕПОРТ #{rep_id}**\n"
                        f"• Беседа: **{chat_title}** (`{peer_id}`)\n"
                        f"• Отправитель: {sender_fmt}\n"
                        f"• Сообщение: {rep_text}\n\n"
                        f"💬 Ответить в чате: `/ответить {rep_id} [ваш ответ]`"
                    ),
                    random_id=0
                )
            except Exception:
                pass

        return await message.answer(
            f"✅ **Репорт #{rep_id} принят!**\n"
            f"• От: {sender_fmt}\n"
            f"• Текст: *{rep_text}*\n"
            f"• Статус: `Открыт` — ожидайте ответа администрации."
        )

    elif cmd in ["reports", "репорты"]:
        if user_lvl < 60:
            return await message.answer(f"❌ Требуется 60+ уровень (у вас: {user_lvl}).")
        chat_reps = [r for r in db.get("reports", []) if r.get("peer_id") == peer_id][-8:]
        if not chat_reps:
            return await message.answer("📋 В этой беседе пока нет репортов.")
        lines = []
        for r in chat_reps:
            st_icon = "🟢 Закрыт" if r.get("status") == "closed" else "🟡 Открыт"
            u_fmt = await format_vk_user(r["from_id"])
            line = f"• **#{r['id']}** [{st_icon}] от {u_fmt}: {r['text']}"
            if r.get("reply"):
                line += f"\n   ↳ *Ответ:* {r['reply']}"
            lines.append(line)
        return await message.answer("📩 **РЕПОРТЫ БЕСЕДЫ:**\n\n" + "\n\n".join(lines))

    elif cmd in ["ответить", "answer"]:
        if user_lvl < 60:
            return await message.answer(f"❌ Требуется 60+ уровень (у вас: {user_lvl}).")
        if len(params) < 2 or not params[0].lstrip("#").isdigit():
            return await message.answer("❌ Формат: `/ответить [номер репорта] [текст ответа]`")
        target_rep_id = int(params[0].lstrip("#"))
        ans_text = " ".join(params[1:]).strip()
        found_rep = None
        for r in db.get("reports", []):
            if r.get("id") == target_rep_id:
                found_rep = r
                break
        if not found_rep:
            return await message.answer(f"❌ Репорт #{target_rep_id} не найден.")
        found_rep["reply"] = ans_text
        found_rep["status"] = "closed"
        save_db(db)
        add_log(f"Ответ на репорт #{target_rep_id} от {await format_vk_user(uid_int)}: {ans_text}")
        return await message.answer(
            f"✉️ **Ответ по репорту #{target_rep_id}** для {await format_vk_user(found_rep['from_id'])}:\n"
            f"• *Вопрос:* {found_rep['text']}\n"
            f"• *Ответ:* **{ans_text}**"
        )

    elif cmd in ["ник", "nick"]:
        if not params:
            return await message.answer("❌ Формат: `/ник [Ваш никнейм]`")
        new_nick = " ".join(params).strip()
        if len(new_nick) > 40:
            return await message.answer("❌ Ник не длиннее 40 символов.")
        current_lvl = get_user_level_by_id(uid_int, chat_data, owner_id)
        if uid_str not in chat_data["members"] or not isinstance(chat_data["members"][uid_str], dict):
            chat_data["members"][uid_str] = {"level": current_lvl, "nickname": new_nick}
        else:
            chat_data["members"][uid_str]["nickname"] = new_nick
            chat_data["members"][uid_str]["level"] = current_lvl
        save_db(db)
        return await message.answer(f"✅ Ваш ник в беседе обновлён на: **{new_nick}**")

    elif cmd in ["nlist", "нлист"]:
        members = chat_data.get("members", {})
        nlist_lines = []
        for m_id, info in members.items():
            if isinstance(info, dict):
                nick = info.get("nickname", "")
                if nick and nick.strip():
                    nlist_lines.append(f"• {await format_vk_user(int(m_id))} ➔ **{nick}**")
        if not nlist_lines:
            return await message.answer("📋 В этой беседе пока нет зарегистрированных ников.")
        return await message.answer("📋 **АКТИВНЫЕ КАСТОМНЫЕ НИКНЕЙМЫ:**\n\n" + "\n".join(nlist_lines))

    elif cmd in ["snick", "сник", "setnick", "сетник"]:
        if user_lvl < 60:
            return await message.answer(f"❌ Недостаточно прав! Требуется 60+ уровень (у вас: {user_lvl}).")
        orig_parts = raw_text.split()[1:]
        if not orig_parts:
            return await message.answer("❌ Формат: `/сник [@ник/id/ответ] [Ник]`")

        target_id, remaining = await resolve_target(message, orig_parts)
        if not target_id:
            return await message.answer("❌ Пользователь не найден. Укажите `@ник`, `id` или сделайте реплай.")

        new_nick = " ".join(orig_parts).strip() if message.reply_message else " ".join(remaining).strip()
        if not new_nick:
            return await message.answer("❌ Укажите текст никнейма.")

        t_str = str(target_id)
        current_lvl = get_user_level_by_id(target_id, chat_data, owner_id)

        if t_str not in chat_data["members"] or not isinstance(chat_data["members"][t_str], dict):
            chat_data["members"][t_str] = {"level": current_lvl, "nickname": new_nick}
        else:
            chat_data["members"][t_str]["nickname"] = new_nick
            chat_data["members"][t_str]["level"] = current_lvl
        save_db(db)
        return await message.answer(f"✅ Ник **{new_nick}** выдан {await format_vk_user(target_id)}.")

    elif cmd in ["delnick", "делник"]:
        if user_lvl < 60:
            return await message.answer(f"❌ Требуется 60+ уровень (у вас: {user_lvl}).")
        tid, _ = await resolve_target(message, params)
        if not tid:
            return await message.answer("❌ Укажите пользователя.")
        t_str = str(tid)
        if t_str in chat_data["members"] and isinstance(chat_data["members"][t_str], dict):
            chat_data["members"][t_str]["nickname"] = ""
            save_db(db)
            return await message.answer(f"🟢 Ник удалён у {await format_vk_user(tid)}.")
        return await message.answer("❌ Никнейм не найден в базе.")

    elif cmd in ["stats", "стата", "профиль"]:
        target_id, _ = await resolve_target(message, params)
        if not target_id:
            target_id = uid_int

        t_str = str(target_id)
        owner_flag = is_chat_owner(target_id, chat_data, owner_id)
        target_lvl = 100 if owner_flag else get_user_level_by_id(target_id, chat_data, owner_id)
        r_name = get_role_title(target_lvl, chat_data, owner_flag=owner_flag)

        m_info = chat_data["members"].get(t_str, {})
        nick = m_info.get("nickname", "Не установлен") if isinstance(m_info, dict) and m_info.get("nickname") else "Не установлен"
        warns = len(chat_data.get("warns", {}).get(t_str, []))
        owner_badge = " 👑 **Владелец чата**" if owner_flag else ""

        return await message.answer(
            f"📊 **ДОСЬЕ ИГРОКА** {await format_vk_user(target_id)}{owner_badge}:\n\n"
            f"• Ник в чате: `{nick}`\n"
            f"• Должность: **{r_name}** `[{target_lvl} lvl]`\n"
            f"• Предупреждения: `{warns}/3`"
        )

    elif cmd in ["check", "проверка"]:
        target_id, _ = await resolve_target(message, params)
        if not target_id:
            target_id = uid_int
        t_str = str(target_id)
        owner_flag = is_chat_owner(target_id, chat_data, owner_id)
        target_lvl = 100 if owner_flag else get_user_level_by_id(target_id, chat_data, owner_id)
        r_name = get_role_title(target_lvl, chat_data, owner_flag=owner_flag)
        m_info = chat_data["members"].get(t_str, {})
        nick = m_info.get("nickname", "Нет") if isinstance(m_info, dict) and m_info.get("nickname") else "Нет"
        leader_org = db.get("leaders", {}).get(t_str, "Нет")
        warns_list = chat_data.get("warns", {}).get(t_str, [])
        muted_until = chat_data.get("mutes", {}).get(t_str, 0)
        is_muted = time.time() < muted_until
        mute_str = f"Да (ещё {int((muted_until - time.time()) // 60) + 1} мин)" if is_muted else "Нет"
        is_banned = t_str in chat_data.get("bans", {}) or t_str in db.get("global_bans", {})
        ban_str = "Да 🔴" if is_banned else "Нет 🟢"

        return await message.answer(
            f"🔎 **ПОЛНАЯ ПРОВЕРКА** {await format_vk_user(target_id)}\n\n"
            f"• Владелец беседы: `{'Да 👑' if owner_flag else 'Нет'}`\n"
            f"• Уровень и роль: `{target_lvl} lvl` — **{r_name}**\n"
            f"• Ник: `{nick}`\n"
            f"• Организация (лидер): `{leader_org}`\n"
            f"• Варны: `{len(warns_list)}/3`\n"
            f"• Мут: `{mute_str}`\n"
            f"• Бан: {ban_str}"
        )

    elif cmd in ["mute", "мут"]:
        if user_lvl < 45:
            return await message.answer(f"❌ Ошибка доступа! Требуется 45+ уровень (у вас: {user_lvl}).")
        tid, rem = await resolve_target(message, params)
        if not tid:
            return await message.answer("❌ Укажите цель для мута (`@ник`, `id` или ответ).")
        mins = int(rem[0]) if rem and rem[0].isdigit() else 10
        chat_data["mutes"][str(tid)] = time.time() + (mins * 60)
        save_db(db)
        add_log(f"Мут: {await format_vk_user(tid)} на {mins} мин от {await format_vk_user(uid_int)}")
        return await message.answer(f"🤫 {await format_vk_user(tid)} замучен на `{mins}` мин.")

    elif cmd in ["unmuteall", "размутвсех"]:
        if user_lvl < 70:
            return await message.answer(f"❌ Требуется 70+ уровень (у вас: {user_lvl}).")
        cnt = len(chat_data.get("mutes", {}))
        chat_data["mutes"] = {}
        save_db(db)
        return await message.answer(f"🔊 Сняты все активные муты в беседе (`{cnt}`).")

    elif cmd in ["unmute", "unmite", "анмут", "размут"]:
        if user_lvl < 45:
            return await message.answer(f"❌ Недостаточно прав (нужен 45+, у вас: {user_lvl}).")
        tid, _ = await resolve_target(message, params)
        if tid and str(tid) in chat_data["mutes"]:
            del chat_data["mutes"][str(tid)]
            save_db(db)
            return await message.answer(f"🔊 Мут снят с {await format_vk_user(tid)}.")
        return await message.answer("❌ Активных мутов у игрока не найдено.")

    elif cmd in ["ban", "бан"]:
        if user_lvl < 55:
            return await message.answer(f"❌ Требуется 55+ уровень (у вас: {user_lvl}).")
        tid, rem = await resolve_target(message, params)
        if not tid:
            return await message.answer("❌ Укажите цель для бана.")
        reason = " ".join(rem) if rem else "Нарушение регламента"
        chat_data["bans"][str(tid)] = {"reason": reason}
        save_db(db)
        try:
            await bot.api.messages.remove_chat_user(chat_id=message.chat_id, user_id=tid)
        except Exception:
            pass
        add_log(f"Бан в чате: {await format_vk_user(tid)}, причина: {reason}")
        return await message.answer(f"🚫 {await format_vk_user(tid)} заблокирован в чате. Причина: {reason}")

    elif cmd in ["unban", "анбан", "разбан"]:
        if user_lvl < 55:
            return await message.answer(f"❌ Требуется 55+ уровень (у вас: {user_lvl}).")
        tid, _ = await resolve_target(message, params)
        if tid and str(tid) in chat_data["bans"]:
            del chat_data["bans"][str(tid)]
            save_db(db)
            return await message.answer(f"🟢 {await format_vk_user(tid)} разбанен в чате.")
        return await message.answer("❌ Этого игрока нет в бан-листе чата.")

    elif cmd in ["banlist", "банлист"]:
        bans = chat_data.get("bans", {})
        if not bans:
            return await message.answer("📋 Чёрный список беседы пуст.")
        lines = []
        for b_id, info in bans.items():
            lines.append(f"• {await format_vk_user(int(b_id))} ➔ Причина: {info.get('reason')}")
        return await message.answer("📋 **ЧЁРНЫЙ СПИСОК БЕСЕДЫ:**\n\n" + "\n".join(lines))

    elif cmd in ["chekban", "checkban", "чекбан"]:
        tid, _ = await resolve_target(message, params)
        if not tid:
            tid = uid_int
        is_b = str(tid) in chat_data.get("bans", {}) or str(tid) in db["global_bans"]
        status = "В бане 🔴" if is_b else "Чист 🟢"
        return await message.answer(f"🔍 Проверка статуса {await format_vk_user(tid)}: {status}")

    elif cmd in ["statschat", "статачата"]:
        c_count = len(db.get("global_chats", []))
        m_count = len(chat_data.get("members", {}))
        return await message.answer(f"📈 **СТАТИСТИКА БЕСЕДЫ:**\n• Участников в базе чата: `{m_count}`\n• Всего активных чатов: `{c_count}`")

    elif cmd in ["kick", "кик"]:
        if user_lvl < 45:
            return await message.answer(f"❌ Требуется 45+ уровень (у вас: {user_lvl}).")
        tid, _ = await resolve_target(message, params)
        if not tid:
            return await message.answer("❌ Укажите цель для кика.")
        try:
            await bot.api.messages.remove_chat_user(chat_id=message.chat_id, user_id=tid)
            return await message.answer(f"✅ {await format_vk_user(tid)} исключён из беседы.")
        except Exception as e:
            return await message.answer(f"❌ Ошибка кика (проверьте права бота в беседе): {e}")

    elif cmd in ["warn", "варн"]:
        if user_lvl < 45:
            return await message.answer(f"❌ Требуется 45+ уровень (у вас: {user_lvl}).")
        tid, rem = await resolve_target(message, params)
        if not tid:
            return await message.answer("❌ Укажите цель для варна.")
        reason = " ".join(rem) if rem else "Нарушение"
        t_str = str(tid)
        if t_str not in chat_data["warns"]:
            chat_data["warns"][t_str] = []
        chat_data["warns"][t_str].append(reason)
        save_db(db)
        cnt = len(chat_data["warns"][t_str])
        u_fmt = await format_vk_user(tid)
        await message.answer(f"⚠️ {u_fmt} получил варн (`{cnt}/3`). Причина: {reason}")
        if cnt >= 3:
            try:
                await bot.api.messages.remove_chat_user(chat_id=message.chat_id, user_id=tid)
                chat_data["warns"][t_str] = []
                save_db(db)
                await message.answer(f"🚫 Лимит исчерпан! {u_fmt} — авто-кик за 3 предупреждения.")
            except Exception:
                pass

    elif cmd in ["warns", "варны"]:
        tid, _ = await resolve_target(message, params)
        if not tid:
            tid = uid_int
        w_list = chat_data.get("warns", {}).get(str(tid), [])
        u_fmt = await format_vk_user(tid)
        if not w_list:
            return await message.answer(f"📋 У {u_fmt} нет предупреждений (`0/3`).")
        reasons = "\n".join([f"{idx + 1}. {r}" for idx, r in enumerate(w_list)])
        return await message.answer(f"⚠️ **Варны {u_fmt} (`{len(w_list)}/3`):**\n\n{reasons}")

    elif cmd in ["unwarn", "анварн", "снятварн"]:
        if user_lvl < 45:
            return await message.answer(f"❌ Требуется 45+ уровень (у вас: {user_lvl}).")
        tid, _ = await resolve_target(message, params)
        if tid and str(tid) in chat_data["warns"] and chat_data["warns"][str(tid)]:
            chat_data["warns"][str(tid)].pop()
            save_db(db)
            return await message.answer(f"🟢 Последний варн снят у {await format_vk_user(tid)}.")
        return await message.answer("❌ У игрока нет активных предупреждений.")

    elif cmd in ["clearwarns", "снятьвсеварны"]:
        if user_lvl < 55:
            return await message.answer(f"❌ Требуется 55+ уровень (у вас: {user_lvl}).")
        tid, _ = await resolve_target(message, params)
        if not tid:
            return await message.answer("❌ Укажите пользователя.")
        chat_data["warns"][str(tid)] = []
        save_db(db)
        return await message.answer(f"🟢 Все варны сняты у {await format_vk_user(tid)}.")

    elif cmd in ["antispam", "антиспам"]:
        if user_lvl < 70:
            return await message.answer(f"❌ Требуется 70+ уровень (у вас: {user_lvl}).")
        chat_data["antispam"] = not bool(chat_data.get("antispam"))
        save_db(db)
        state_txt = "🟢 ВКЛЮЧЁН (ссылки у участников <45 lvl удаляются)" if chat_data["antispam"] else "🔴 ВЫКЛЮЧЕН"
        return await message.answer(f"🛡 Режим антиспама в беседе: {state_txt}.")

    elif cmd in ["clear", "очистить", "чистка"]:
        if user_lvl < 45:
            return await message.answer(f"❌ Требуется 45+ уровень (у вас: {user_lvl}).")
        count = int(params[0]) if params and params[0].isdigit() else 10
        count = max(1, min(count, 50))
        cmid = message.conversation_message_id or 0
        ids_to_del = list(range(max(1, cmid - count), cmid + 1))
        try:
            await bot.api.messages.delete(peer_id=peer_id, conversation_message_ids=ids_to_del, delete_for_all=True)
            msg_done = await message.answer(f"🧹 Очищено до `{len(ids_to_del)}` сообщений.")
            await asyncio.sleep(3)
            try:
                await bot.api.messages.delete(peer_id=peer_id, conversation_message_ids=[msg_done.conversation_message_id], delete_for_all=True)
            except Exception:
                pass
        except Exception:
            return await message.answer("❌ Не удалось удалить сообщения (выдайте боту права администратора чата).")

    elif cmd in ["logs", "логи"]:
        if user_lvl < 70:
            return await message.answer(f"❌ Доступно с 70 уровня (у вас: {user_lvl}).")
        recent = "\n".join(db["logs"][-15:])
        return await message.answer(f"📜 **СИСТЕМНЫЕ ЛОГИ ПРОЕКТА:**\n\n{recent if recent else 'Журнал пуст'}")

    elif cmd in ["pin", "закреп"]:
        if user_lvl < 45:
            return await message.answer(f"❌ Нужны права 45+ lvl (у вас: {user_lvl}).")
        if not message.reply_message:
            return await message.answer("❌ Сделайте реплай (ответ) на сообщение для закрепления.")
        try:
            await bot.api.messages.pin(peer_id=peer_id, conversation_message_id=message.reply_message.conversation_message_id)
            return await message.answer("📌 Сообщение закреплено!")
        except Exception:
            return await message.answer("❌ Ошибка закрепления: выдайте боту права администратора беседы в ВК.")

    elif cmd in ["unpin", "откреп"]:
        if user_lvl < 45:
            return await message.answer(f"❌ Нужны права 45+ lvl (у вас: {user_lvl}).")
        try:
            await bot.api.messages.unpin(peer_id=peer_id)
            return await message.answer("📌 Закреплённое сообщение откреплено.")
        except Exception:
            return await message.answer("❌ Ошибка открепления: выдайте боту права администратора беседы в ВК.")

    elif cmd in ["setowner", "сетвладелец"]:
        if user_lvl < 90:
            return await message.answer(f"❌ Требуется 90+ уровень (у вас: {user_lvl}).")
        tid, _ = await resolve_target(message, params)
        if not tid:
            return await message.answer("❌ Формат: `/сетвладелец [@ник/id/ответ]`")
        sync_owner_member(chat_data, int(tid))
        save_db(db)
        return await message.answer(f"👑 Владельцем чата закреплён {await format_vk_user(tid)} (`100 lvl`).")

    elif cmd in ["newrole", "новаяроль"]:
        if user_lvl < 90:
            return await message.answer(f"❌ Требуется 90+ уровень (у вас: {user_lvl}).")
        if len(params) < 2 or not params[0].isdigit():
            return await message.answer("❌ Формат: `/новаяроль [ур] [Название]`")
        lvl_key = str(int(params[0]))
        r_name = " ".join(params[1:])
        chat_data["role_names"][lvl_key] = r_name
        save_db(db)
        return await message.answer(f"✅ Новая роль создана: `{lvl_key} lvl` ➔ **{r_name}**")

    elif cmd in ["delrole", "удалитьроль"]:
        if user_lvl < 90:
            return await message.answer(f"❌ Требуется 90+ уровень (у вас: {user_lvl}).")
        if not params or not params[0].isdigit():
            return await message.answer("❌ Укажите числовой уровень роли.")
        lvl_key = str(int(params[0]))
        if lvl_key in chat_data["role_names"]:
            del chat_data["role_names"][lvl_key]
            save_db(db)
            return await message.answer(f"🗑 Роль уровня `{lvl_key}` удалена.")
        return await message.answer("❌ Указанная роль не найдена.")

    elif cmd in ["setadmin", "сетадмин", "выдатьадм", "выдатьроль", "роль"]:
        if user_lvl < 70:
            return await message.answer(f"❌ Требуется 70+ уровень (у вас: {user_lvl}).")
        tid, rem = await resolve_target(message, params)
        if not tid:
            return await message.answer("❌ Формат: `/сетадмин [@ник/id/ответ] [уровень]`")
        lvl_val = None
        for p in rem:
            if p.isdigit():
                lvl_val = int(p)
                break
        if lvl_val is None:
            return await message.answer("❌ Укажите числовой уровень админки, например: `/сетадмин @evgenn09 70`")

        t_str = str(tid)
        current_data = chat_data["members"].get(t_str, {"nickname": ""})
        current_nick = current_data.get("nickname", "") if isinstance(current_data, dict) else ""

        chat_data["members"][t_str] = {"level": lvl_val, "nickname": current_nick}
        save_db(db)
        add_log(f"Выдача роли {lvl_val} lvl для {await format_vk_user(tid)} от {await format_vk_user(uid_int)}")
        return await message.answer(f"✅ {await format_vk_user(tid)} присвоен ранг `{lvl_val} lvl` (**{get_role_title(lvl_val, chat_data)}**).")

    elif cmd in ["removerole", "снятьроль", "снятадм"]:
        if user_lvl < 70:
            return await message.answer(f"❌ Требуется 70+ уровень (у вас: {user_lvl}).")
        tid, _ = await resolve_target(message, params)
        if not tid:
            return await message.answer("❌ Укажите пользователя.")

        t_str = str(tid)
        current_data = chat_data["members"].get(t_str, {"nickname": ""})
        current_nick = current_data.get("nickname", "") if isinstance(current_data, dict) else ""

        chat_data["members"][t_str] = {"level": 0, "nickname": current_nick}
        save_db(db)
        return await message.answer(f"🟢 С {await format_vk_user(tid)} сняты права админки (0 lvl).")

    elif cmd in ["setleader", "сетлидер", "поставитьлидера"]:
        if user_lvl < 60:
            return await message.answer(f"❌ Требуется 60+ уровень (у вас: {user_lvl}).")
        tid, rem = await resolve_target(message, params)
        if not tid or not rem:
            return await message.answer("❌ Формат: `/сетлидер [@ник/id/ответ] [Организация]`")
        org = " ".join(rem)
        db["leaders"][str(tid)] = org
        save_db(db)
        return await message.answer(f"👔 {await format_vk_user(tid)} назначен лидером организации **{org}**.")

    elif cmd in ["removeleader", "снятлидера"]:
        if user_lvl < 60:
            return await message.answer(f"❌ Требуется 60+ уровень (у вас: {user_lvl}).")
        tid, _ = await resolve_target(message, params)
        if tid and str(tid) in db["leaders"]:
            del db["leaders"][str(tid)]
            save_db(db)
            return await message.answer(f"🟢 {await format_vk_user(tid)} снят с поста лидера.")
        return await message.answer("❌ Лидер не найден в списке.")

    elif cmd in ["leaders", "лидеры"]:
        if not db.get("leaders"):
            return await message.answer("👔 Список лидеров организаций пока пуст.")
        lines = [f"• {await format_vk_user(int(l_id))} ➔ **{org}**" for l_id, org in db["leaders"].items()]
        return await message.answer("👔 **ЛИДЕРЫ ОРГАНИЗАЦИЙ:**\n\n" + "\n".join(lines))

    elif cmd in ["bonus", "бонус"]:
        return await message.answer(
            "🎁 **БОНУСЫ PRINCE RUSSIA**\n\n"
            "• Официальный портал: https://site-prince-russia.samp.date/\n"
            "• Следи за новостями в беседах и на форуме проекта!"
        )

    elif cmd in ["grole", "гроль"]:
        if user_lvl < 95:
            return await message.answer(f"❌ Требуется 95+ уровень (у вас: {user_lvl}).")
        tid, rem = await resolve_target(message, params)
        if not tid or not rem or not rem[0].isdigit():
            return await message.answer("❌ Формат: `/гроль [@ник/id] [уровень]`")
        db["global_roles"][str(tid)] = int(rem[0])
        save_db(db)
        return await message.answer(f"🌐 Глобальная роль `{rem[0]}` выдана {await format_vk_user(tid)} по всей сети.")

    elif cmd in ["grr", "снятьгроль"]:
        if user_lvl < 95:
            return await message.answer(f"❌ Требуется 95+ уровень (у вас: {user_lvl}).")
        tid, _ = await resolve_target(message, params)
        if tid and str(tid) in db["global_roles"]:
            del db["global_roles"][str(tid)]
            save_db(db)
            return await message.answer(f"🟢 Глобальная роль снята у {await format_vk_user(tid)}.")
        return await message.answer("❌ У игрока нет глобальных ролей.")

    elif cmd in ["gban", "гбан"]:
        if user_lvl < 90:
            return await message.answer(f"❌ Требуется 90+ уровень (у вас: {user_lvl}).")
        tid, rem = await resolve_target(message, params)
        if not tid:
            return await message.answer("❌ Укажите цель.")
        reason = " ".join(rem) if rem else "Глобальное нарушение"
        db["global_bans"][str(tid)] = reason
        save_db(db)
        add_log(f"Глобальный бан: {await format_vk_user(tid)}, причина: {reason}")
        return await message.answer(f"⛔ ГЛОБАЛЬНЫЙ БАН для {await format_vk_user(tid)}! Причина: {reason}")

    elif cmd in ["admins", "админс"]:
        lines = []
        shown_ids = set()

        if owner_id:
            owner_int = int(owner_id)
            shown_ids.add(owner_int)
            o_info = chat_data["members"].get(str(owner_int))
            o_nick = f" — `{o_info['nickname']}`" if isinstance(o_info, dict) and o_info.get("nickname") else ""
            lines.append(f"👑 **Владелец чата:** {await format_vk_user(owner_int)}{o_nick} ➔ `100 lvl`")

        for m_id, info in chat_data.get("members", {}).items():
            uid_item = int(m_id)
            if uid_item in shown_ids:
                continue
            lvl = info.get("level", 0) if isinstance(info, dict) else int(info or 0)
            if lvl > 0:
                shown_ids.add(uid_item)
                r_name = get_role_title(lvl, chat_data)
                nick_str = f" — `{info.get('nickname')}`" if isinstance(info, dict) and info.get("nickname") else ""
                lines.append(f"• {await format_vk_user(uid_item)}{nick_str} ➔ **{r_name}** `[{lvl} lvl]`")

        for g_id, lvl in db.get("global_roles", {}).items():
            uid_item = int(g_id)
            if uid_item in shown_ids or int(lvl) <= 0:
                continue
            shown_ids.add(uid_item)
            r_name = get_role_title(int(lvl), chat_data)
            lines.append(f"• 🌐 {await format_vk_user(uid_item)} ➔ **{r_name}** `[{lvl} lvl]`")

        if not lines:
            return await message.answer("👑 В этом чате пока не определён владелец и нет назначенных администраторов.")

        return await message.answer("👑 **АДМИНИСТРАЦИЯ БЕСЕДЫ:**\n\n" + "\n".join(lines), keyboard=get_chat_inline_keyboard())

    elif cmd in ["staff", "состав"]:
        parts = []
        if owner_id:
            parts.append(f"👑 **Владелец чата:** {await format_vk_user(int(owner_id))} (`100 lvl`)")

        adm_lines = []
        for m_id, info in chat_data.get("members", {}).items():
            lvl = info.get("level", 0) if isinstance(info, dict) else int(info or 0)
            if lvl > 0 and int(m_id) != int(owner_id or 0):
                adm_lines.append(f"• {await format_vk_user(int(m_id))} — **{get_role_title(lvl, chat_data)}** `[{lvl} lvl]`")
        if adm_lines:
            parts.append("🛡 **Администраторы:**\n" + "\n".join(adm_lines))

        if db.get("leaders"):
            lead_lines = [f"• {await format_vk_user(int(l_id))} — **{org}**" for l_id, org in db["leaders"].items()]
            parts.append("👔 **Лидеры:**\n" + "\n".join(lead_lines))

        if not parts:
            return await message.answer("📋 Состав беседы пока пуст.")
        return await message.answer("📋 **СОСТАВ БЕСЕДЫ:**\n\n" + "\n\n".join(parts))


# =====================================================================
# 5. ЗАПУСК БОТА
# =====================================================================
if __name__ == "__main__":
    bot.run_forever()
