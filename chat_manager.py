import os
import json
import time
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

MAIN_OWNER_ID = 897082738  # Твой главный VK ID
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
    "👑 **Владелец чата автоматически получает `100 lvl` админки** и отображается в списке `/admins`.\n"
    "📌 *Совет:* выдай боту права администратора в чате, чтобы работали кики, баны, муты и закреп сообщений.\n\n"
    "📖 **Как пользоваться ботом:**\n"
    "• `/help` или `/хелп` — полный список команд по уровням\n"
    "• `/admins` или `/админс` — владелец и администраторы чата\n"
    "• `/stats` или `/стата` — профиль и уровень прав\n"
    "• `/setnick [id/ответ] [Ник]` — выдать ник (60+ lvl)\n"
    "• `/выдатьроль [id/ответ] [ур]` — выдать уровень админки (70+ lvl)\n"
    "• `/mute`, `/warn`, `/kick`, `/ban` — модерация чата\n"
    "• `/menu` или `меню` — быстрые кнопки беседы"
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
if "logs" not in db: db["logs"] = []

user_states = {}

def add_log(text):
    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
    entry = f"{timestamp} {text}"
    db["logs"].append(entry)
    if len(db["logs"]) > 150:
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
            "welcomed": False
        }
    chat = db["chats"][p_str]
    chat.setdefault("members", {})
    chat.setdefault("bans", {})
    chat.setdefault("warns", {})
    chat.setdefault("mutes", {})
    chat.setdefault("role_names", DEFAULT_ROLES.copy())
    chat.setdefault("welcomed", False)
    return chat

async def get_chat_owner_id(peer_id):
    try:
        chat_info = await bot.api.messages.get_conversations_by_peer_ids(peer_ids=[peer_id])
        if chat_info and chat_info.items:
            settings = chat_info.items[0].chat_settings
            if settings and settings.owner_id:
                return int(settings.owner_id)
    except Exception:
        pass
    return None

def sync_chat_owner(chat_data: dict, chat_owner_id: int | None):
    if not chat_owner_id:
        return
    o_str = str(chat_owner_id)
    current_data = chat_data["members"].get(o_str, {})
    nick = current_data.get("nickname", "") if isinstance(current_data, dict) else ""
    chat_data["members"][o_str] = {
        "level": 100,
        "nickname": nick,
        "is_owner": True
    }

def get_user_level_by_id(uid: int, chat_data: dict, chat_owner_id: int | None) -> int:
    if uid == MAIN_OWNER_ID or uid in db["broadcast_admins"]:
        return 100
    if chat_owner_id and uid == chat_owner_id:
        return 100
    if str(uid) in db["global_roles"]:
        return int(db["global_roles"][str(uid)])

    m_info = chat_data["members"].get(str(uid), 0)
    if isinstance(m_info, dict):
        return int(m_info.get("level", 0))
    elif isinstance(m_info, (int, float)):
        return int(m_info)
    return 0

async def resolve_target(message: Message, args: list):
    if message.reply_message:
        return message.reply_message.from_id, args
    if not args:
        return None, []

    target_raw = args[0]
    identifier = (
        target_raw.strip()
        .replace("https://vk.com/", "")
        .replace("http://vk.com/", "")
        .replace("vk.com/", "")
        .replace("@", "")
        .replace("id", "")
    )

    target_id = None
    remaining_args = args[1:]

    if identifier.isdigit():
        target_id = int(identifier)
    else:
        try:
            user_info = await bot.api.users.get(user_ids=[identifier])
            if user_info:
                target_id = user_info[0].id
        except Exception:
            pass

    if not target_id:
        return None, args

    return target_id, remaining_args


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
        "👑 **PRINCE RUSSIA — ULTIMATE ADMIN CONTROL** 👑\n\n"
        "Добро пожаловать в центр управления сетью чатов проекта.\n"
        "Выберите нужную опцию на клавиатуре ниже:",
        keyboard=kb.get_json()
    )

@bot.on.private_message(text="➕ Выдать доступ к рассылке")
async def private_add_adm(message: Message):
    uid = message.from_id
    if uid != MAIN_OWNER_ID and uid not in db["broadcast_admins"]:
        return
    user_states[uid] = "wait_add_adm"
    await message.answer(
        "✍️ Введите цифровой VK ID пользователя для выдачи доступа к глобальной рассылке:",
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
    admins_list = "\n".join([f"• [id{aid}|Перейти к профилю ID {aid}]" for aid in db["broadcast_admins"]])
    await message.answer(f"👥 **ДОВЕРЕННЫЕ АДМИНЫ РАССЫЛКИ:**\n\n{admins_list}")

@bot.on.private_message(text="📢 Начать рассылку по чатам")
async def private_broadcast_start(message: Message):
    uid = message.from_id
    if uid != MAIN_OWNER_ID and uid not in db["broadcast_admins"]:
        return
    user_states[uid] = "wait_broadcast"
    await message.answer(
        "✍️ Введите текст для массовой отправки по всем беседам проекта:\n*(Сообщение уйдет со всеми тегами и официальным статусом Prince Russia)*",
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
        clean = text.strip().replace("id", "")
        if clean.isdigit():
            tid = int(clean)
            if tid not in db["broadcast_admins"]:
                db["broadcast_admins"].append(tid)
                save_db(db)
                add_log(f"Админ [id{uid}|ID {uid}] выдал права рассылки для [id{tid}|ID {tid}]")
                return await message.answer(f"✅ Успешно! Пользователь [id{tid}|ID {tid}] добавлен в список рассыльщиков.")
        return await message.answer("❌ Ошибка: Неверный формат VK ID.")

    if state == "wait_broadcast" and (uid == MAIN_OWNER_ID or uid in db["broadcast_admins"]):
        del user_states[uid]
        count = 0

        broadcast_text = (
            "📢 **ВНИМАНИЕ! ОФИЦИАЛЬНОЕ СООБЩЕНИЕ ОТ PRINCE RUSSIA** 📢\n\n"
            f"{text}\n\n"
            "═══════════════════════════\n"
            f"👤 Ответственный за рассылку: [id{uid}|Администрация проекта]\n"
            "🌐 Портал: https://site-prince-russia.samp.date/\n"
            "@all"
        )

        for cid in db.get("global_chats", []):
            try:
                await bot.api.messages.send(peer_id=int(cid), message=broadcast_text, random_id=0)
                count += 1
            except Exception:
                pass

        add_log(f"Массовая рассылка выполнена администратором [id{uid}|ID {uid}]. Охвачено чатов: {count}")
        return await message.answer(f"🚀 **Рассылка успешно завершена!**\n• Доставлено в беседы: `{count}`")

    await message.answer("❌ Используйте инлайн-кнопки или команды управления в беседах.")


# =====================================================================
# 4. РАБОТА В БЕСЕДАХ (МОДЕРАЦИЯ И КОМАНДЫ)
# =====================================================================

@bot.on.chat_message()
async def chat_handler(message: Message):
    peer_id = message.peer_id
    chat_data = get_chat_data(peer_id)
    chat_owner_id = await get_chat_owner_id(peer_id)

    is_new_chat = peer_id not in db["global_chats"]
    if is_new_chat:
        db["global_chats"].append(peer_id)

    # Автоматически закрепляем 100 уровень за владельцем чата
    sync_chat_owner(chat_data, chat_owner_id)
    save_db(db)

    # Если бота только что добавили в беседу — отправляем инструкцию
    if message.action and message.action.type == "chat_invite_user":
        j_id = message.action.member_id
        group_id = getattr(message, "group_id", None)
        if j_id == message.from_id or (group_id and j_id == -group_id) or is_new_chat and not chat_data.get("welcomed"):
            if j_id < 0 or not chat_data.get("welcomed"):
                chat_data["welcomed"] = True
                save_db(db)
                await message.answer(WELCOME_GUIDE)

        if str(j_id) in db["global_bans"] or str(j_id) in chat_data.get("bans", {}):
            try:
                await bot.api.messages.remove_chat_user(chat_id=message.chat_id, user_id=j_id)
                await message.answer(f"⛔ Вход заблокирован! У [id{j_id}|нарушителя] активный бан.")
            except Exception:
                pass
            return

    uid = str(message.from_id)

    if uid in chat_data.get("mutes", {}):
        if time.time() < chat_data["mutes"][uid]:
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
            del chat_data["mutes"][uid]
            save_db(db)

    text = message.text
    if not text:
        return

    raw_text = text.strip()
    clean_text = raw_text.lower()

    for mention in ["[club" + str(message.group_id) + "|@", "@club", "@public"]:
        if mention in clean_text:
            parts = raw_text.split(" ", 1)
            if len(parts) > 1:
                raw_text = parts[1].strip()
                clean_text = raw_text.lower()

    if clean_text in ["/menu", "меню"]:
        kb = Keyboard(one_time=False, inline=True)
        kb.add(Text("🌐 Сайт"), color=KeyboardButtonColor.POSITIVE)
        kb.add(Text("📜 Правила"), color=KeyboardButtonColor.PRIMARY)
        kb.row()
        kb.add(Text("📋 Роли"), color=KeyboardButtonColor.POSITIVE)
        kb.add(Text("📊 Стата"), color=KeyboardButtonColor.PRIMARY)
        return await message.answer("👑 **ПАНЕЛЬ УПРАВЛЕНИЯ БЕСЕДОЙ**", keyboard=kb.get_json())

    if clean_text in ["🌐 сайт", "сайт"]:
        return await message.answer("🌐 Официальный портал Prince Russia: https://site-prince-russia.samp.date/")

    if clean_text in ["📊 стата", "стата"]:
        raw_text = "/stats"
        clean_text = "/stats"

    if clean_text in ["📜 правила", "правила"]:
        return await message.answer(
            "📜 **РЕГЛАМЕНТ БЕСЕДЫ:**\n"
            "1. Строго без спама и рекламы.\n"
            "2. Уважение к администрации и участникам.\n"
            "3. Лимит предупреждений: 3 варна ➔ автоматический кик."
        )

    if clean_text in ["📋 роли", "/roles", "роли"]:
        r_list = "📋 **ИЕРАРХИЯ ДОЛЖНОСТЕЙ PRINCE RUSSIA:**\n\n"
        all_roles = {**db["global_role_names"], **chat_data["role_names"]}
        for lvl in sorted((int(k) for k in all_roles.keys()), reverse=True):
            r_list += f"• `{lvl} lvl` ➔ **{all_roles[str(lvl)] if str(lvl) in all_roles else all_roles[lvl]}**\n"
        return await message.answer(r_list)

    if not clean_text.startswith("/"):
        return

    args = raw_text[1:].split()
    cmd = args[0].lower() if args else ""
    params = args[1:] if len(args) > 1 else []

    user_lvl = get_user_level_by_id(message.from_id, chat_data, chat_owner_id)

    # --- СПРАВКА / HELP ---
    if cmd in ["help", "хелп"]:
        help_msg = (
            "📖 **ЭКСКЛЮЗИВНЫЙ СПИСОК КОМАНД PRINCE RUSSIA** 📖\n\n"
            "🌐 **Общий функционал:**\n"
            "• `/stats` (или `/стата`) — ваш профиль или профиль игрока\n"
            "• `/nlist` (или `/нлист`) — список ников участников чата\n"
            "• `/roles` (или `роли`) — иерархия рангов проекта\n"
            "• `/admins` (или `/админс`) — владелец и админы чата\n"
            "• `/leaders` — список лидеров организаций\n"
            "• `/bonus` — информация о бонусах проекта\n"
            "• `/ping` — задержка и пинг серверов\n"
            "• `/status` — аптайм ядра\n\n"
        )
        if user_lvl >= 45:
            help_msg += (
                "🛡 **Модерация чата (45+ lvl):**\n"
                "• `/mute [ид/ответ] [минуты]` — ограничить чат\n"
                "• `/unmute [ид/ответ]` — снять мут\n"
                "• `/kick [ид/ответ]` — изгнать из беседы\n"
                "• `/warn [ид/ответ] [причина]` — выдать варн\n"
                "• `/unwarn [ид/ответ]` — снять варн\n"
                "• `/pin` — закрепить важное сообщение\n\n"
            )
        if user_lvl >= 55:
            help_msg += (
                "🚨 **Старшая модерация (55+ lvl):**\n"
                "• `/ban [ид/ответ] [причина]` — заблокировать\n"
                "• `/unban [ид]` — разблокировать\n"
                "• `/banlist` — черный список чата\n\n"
            )
        if user_lvl >= 60:
            help_msg += (
                "👑 **Руководство (60+ lvl):**\n"
                "• `/setleader [ид] [Организация]` — поставить лидера\n"
                "• `/removeleader [ид]` — снять с поста лидера\n"
                "• `/setnick [ид/ответ] [Ник]` — выдать кастомный ник\n"
                "• `/delnick [ид/ответ]` — стереть ник\n\n"
            )
        if user_lvl >= 70:
            help_msg += (
                "⚡ **Администрация проекта (70+ lvl):**\n"
                "• `/setadmin [ид] [уровень]` — назначить ранг админки\n"
                "• `/выдатьроль [ид] [ур]` — выдать должность\n"
                "• `/снятьроль [ид]` — обнулить ранг\n"
                "• `/logs` — системные логи\n\n"
            )
        if user_lvl >= 90:
            help_msg += (
                "🔥 **Высший состав (90+ lvl):**\n"
                "• `/gban [ид] [причина]` — глобальный бан\n"
                "• `/newrole [ур] [Название]` — создать роль\n"
                "• `/delrole [ур]` — удалить роль\n"
            )
        return await message.answer(help_msg)

    elif cmd == "ping":
        start_t = time.time()
        msg_test = await message.answer("🏓 Измеряем задержку...")
        end_t = time.time()
        ping_ms = int((end_t - start_t) * 1000)
        status_emoji = "🟢 Молниеносно" if ping_ms < 600 else "🟡 Стабильно" if ping_ms < 1200 else "🔴 Высокий пинг"
        return await message.answer(
            f"🏓 **PONG!**\n"
            f"• Отклик API VK: `{ping_ms} ms`\n"
            f"• Состояние: {status_emoji}"
        )

    elif cmd == "status":
        uptime_sec = int(time.time() - START_TIME)
        hours, remainder = divmod(uptime_sec, 3600)
        minutes, seconds = divmod(remainder, 60)
        chats_count = len(db.get("global_chats", []))
        return await message.answer(
            f"⚡ **СТАТУС ЯДРА PRINCE RUSSIA**\n\n"
            f"• Аптайм сервера: `{hours}ч {minutes}м {seconds}с`\n"
            f"• Подключено чатов: `{chats_count}`\n"
            f"• База данных: `ONLINE (JSON Secure)`\n"
            f"• Версия сборки: `v8.0 Owner Auto-100 & Guide`"
        )

    elif cmd in ["nlist", "нлист"]:
        members = chat_data.get("members", {})
        nlist_msg = "📋 **АКТИВНЫЕ КАСТОМНЫЕ НИКНЕЙМЫ:**\n\n"
        found_nicks = False

        for m_id, info in members.items():
            if isinstance(info, dict):
                nick = info.get("nickname", "")
                if nick and nick.strip():
                    found_nicks = True
                    nlist_msg += f"• [id{int(m_id)}|Профиль игрока] ➔ **{nick}**\n"

        if not found_nicks:
            return await message.answer("📋 В этой беседе пока не зарегистрировано кастомных ников.")
        return await message.answer(nlist_msg)

    elif cmd == "setnick":
        if user_lvl < 60:
            return await message.answer(f"❌ Недостаточно прав! Требуется 60+ уровень (у вас: {user_lvl}).")
        orig_parts = raw_text.split()[1:]
        if not orig_parts:
            return await message.answer("❌ Формат: `/setnick [ответ/id] [Ник/Звание]`")

        target_id, remaining = await resolve_target(message, orig_parts)
        if not target_id:
            return await message.answer("❌ Пользователь не найден.")

        new_nick = " ".join(orig_parts) if message.reply_message else " ".join(remaining)
        if not new_nick:
            return await message.answer("❌ Укажите текст для никнейма.")

        t_str = str(target_id)
        current_lvl = get_user_level_by_id(target_id, chat_data, chat_owner_id)

        if t_str not in chat_data["members"] or not isinstance(chat_data["members"][t_str], dict):
            chat_data["members"][t_str] = {"level": current_lvl, "nickname": new_nick}
        else:
            chat_data["members"][t_str]["nickname"] = new_nick
            chat_data["members"][t_str]["level"] = current_lvl
        save_db(db)
        return await message.answer(f"✅ Ник успешно применен для [id{target_id}|игрока]: **{new_nick}**")

    elif cmd == "delnick":
        if user_lvl < 60:
            return await message.answer(f"❌ Требуется 60+ уровень (у вас: {user_lvl}).")
        tid, _ = await resolve_target(message, params)
        if not tid:
            return await message.answer("❌ Укажите пользователя.")
        t_str = str(tid)
        if t_str in chat_data["members"] and isinstance(chat_data["members"][t_str], dict):
            chat_data["members"][t_str]["nickname"] = ""
            save_db(db)
            return await message.answer(f"🟢 Кастомный ник стерт у [id{tid}|пользователя].")
        return await message.answer("❌ Никнейм не обнаружен в базе.")

    elif cmd in ["stats", "стата", "профиль"]:
        target_id, _ = await resolve_target(message, params)
        if not target_id:
            target_id = message.from_id

        t_str = str(target_id)
        target_lvl = get_user_level_by_id(target_id, chat_data, chat_owner_id)
        all_r = {**db["global_role_names"], **chat_data["role_names"]}
        r_name = all_r.get(target_lvl) or all_r.get(str(target_lvl)) or ("Администратор" if target_lvl > 0 else "Игрок")

        m_info = chat_data["members"].get(t_str, {})
        nick = m_info.get("nickname", "Не установлен") if isinstance(m_info, dict) and m_info.get("nickname") else "Не установлен"
        warns = len(chat_data.get("warns", {}).get(t_str, []))
        owner_badge = " 👑 (Владелец чата)" if chat_owner_id and target_id == chat_owner_id else ""

        return await message.answer(
            f"📊 **ДОСЬЕ ИГРОКА** [id{target_id}|Открыть профиль]{owner_badge}:\n\n"
            f"• Кастомный ник: `{nick}`\n"
            f"• Должность: **{r_name}** `[{target_lvl} lvl]`\n"
            f"• Предупреждения: `{warns}/3`"
        )

    elif cmd == "mute":
        if user_lvl < 45:
            return await message.answer(f"❌ Ошибка доступа! Требуется 45+ уровень (у вас: {user_lvl}).")
        tid, rem = await resolve_target(message, params)
        if not tid:
            return await message.answer("❌ Укажите цель для мута.")
        mins = int(rem[0]) if rem and rem[0].isdigit() else 10
        chat_data["mutes"][str(tid)] = time.time() + (mins * 60)
        save_db(db)
        add_log(f"Мут: ID {tid} на {mins} мин от [id{message.from_id}|админа]")
        return await message.answer(f"🤫 Игрок [id{tid}|получил мут] на `{mins}` минут.")

    elif cmd in ["unmute", "unmite"]:
        if user_lvl < 45:
            return await message.answer(f"❌ Недостаточно прав (нужен 45+, у вас: {user_lvl}).")
        tid, _ = await resolve_target(message, params)
        if tid and str(tid) in chat_data["mutes"]:
            del chat_data["mutes"][str(tid)]
            save_db(db)
            return await message.answer(f"🔊 Мут успешно снят с [id{tid}|игрока].")
        return await message.answer("❌ Активных мутов у игрока не найдено.")

    elif cmd == "ban":
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
        add_log(f"Бан в чате: ID {tid}, причина: {reason}")
        return await message.answer(f"🚫 Пользователь [id{tid}|изгнан и заблокирован]. Причина: {reason}")

    elif cmd == "unban":
        if user_lvl < 55:
            return await message.answer(f"❌ Требуется 55+ уровень (у вас: {user_lvl}).")
        tid, _ = await resolve_target(message, params)
        if tid and str(tid) in chat_data["bans"]:
            del chat_data["bans"][str(tid)]
            save_db(db)
            return await message.answer(f"🟢 [id{tid}|Игрок] помилован и разбанен.")
        return await message.answer("❌ Этого игрока нет в бан-листе чата.")

    elif cmd == "banlist":
        bans = chat_data.get("bans", {})
        if not bans:
            return await message.answer("📋 Черный список беседы пуст.")
        msg = "📋 **ЧЕРНЫЙ СПИСОК БЕСЕДЫ:**\n\n"
        for b_id, info in bans.items():
            msg += f"• [id{int(b_id)}|Нарушитель] ➔ Причина: {info.get('reason')}\n"
        return await message.answer(msg)

    elif cmd in ["chekban", "checkban"]:
        tid, _ = await resolve_target(message, params)
        if not tid:
            tid = message.from_id
        is_b = str(tid) in chat_data.get("bans", {}) or str(tid) in db["global_bans"]
        status = "В бане 🔴" if is_b else "Чист 🟢"
        return await message.answer(f"🔍 Проверка статуса [id{tid}|игрока]: {status}")

    elif cmd == "statschat":
        c_count = len(db.get("global_chats", []))
        m_count = len(chat_data.get("members", {}))
        return await message.answer(f"📈 **СТАТИСТИКА БЕСЕДЫ:**\n• Участников в базе бота: `{m_count}`\n• Всего активных чатов: `{c_count}`")

    elif cmd == "kick":
        if user_lvl < 45:
            return await message.answer(f"❌ Требуется 45+ уровень (у вас: {user_lvl}).")
        tid, _ = await resolve_target(message, params)
        if not tid:
            return await message.answer("❌ Укажите цель для кика.")
        try:
            await bot.api.messages.remove_chat_user(chat_id=message.chat_id, user_id=tid)
            return await message.answer(f"✅ Пользователь [id{tid}|исключен] из беседы.")
        except Exception as e:
            return await message.answer(f"❌ Ошибка выполнения: {e}")

    elif cmd == "warn":
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
        await message.answer(f"⚠️ [id{tid}|Варн выдан] (`{cnt}/3`). Причина: {reason}")
        if cnt >= 3:
            try:
                await bot.api.messages.remove_chat_user(chat_id=message.chat_id, user_id=tid)
                chat_data["warns"][t_str] = []
                save_db(db)
                await message.answer(f"🚫 Лимит исчерпан! [id{tid}|Авто-кик] за 3 предупреждения.")
            except Exception:
                pass

    elif cmd == "unwarn":
        if user_lvl < 45:
            return await message.answer(f"❌ Требуется 45+ уровень (у вас: {user_lvl}).")
        tid, _ = await resolve_target(message, params)
        if tid and str(tid) in chat_data["warns"] and chat_data["warns"][str(tid)]:
            chat_data["warns"][str(tid)].pop()
            save_db(db)
            return await message.answer(f"🟢 Последний варн аннулирован у [id{tid}|игрока].")
        return await message.answer("❌ У игрока нет активных предупреждений.")

    elif cmd == "logs":
        if user_lvl < 70:
            return await message.answer(f"❌ Доступно с 70 уровня (у вас: {user_lvl}).")
        recent = "\n".join(db["logs"][-15:])
        return await message.answer(f"📜 **СИСТЕМНЫЕ ЛОГИ ПРОЕКТА:**\n\n{recent if recent else 'Журнал пуст'}")

    elif cmd == "pin":
        if user_lvl < 45:
            return await message.answer(f"❌ Нужны права администратора (нужен 45+, у вас: {user_lvl}).")
        if not message.reply_message:
            return await message.answer("❌ Сделайте реплай (ответ) на сообщение для закрепления.")
        try:
            await bot.api.messages.pin(peer_id=peer_id, conversation_message_id=message.reply_message.conversation_message_id)
            return await message.answer("📌 Сообщение успешно закреплено в беседе!")
        except Exception:
            return await message.answer(
                "❌ **Ошибка закрепления:**\n"
                "ВКонтакте запрещает ботам закреплять сообщения, если у бота **нет прав администратора беседы**!\n"
                "👉 *Назначьте бота администратором чата в настройках ВК.*"
            )

    elif cmd == "newrole":
        if user_lvl < 90:
            return await message.answer(f"❌ Требуется 90+ уровень (у вас: {user_lvl}).")
        if len(params) < 2:
            return await message.answer("❌ Формат: `/newrole [ур] [Название]`")
        lvl_s = params[0]
        if not lvl_s.isdigit():
            return await message.answer("❌ Уровень должен быть числом.")
        r_name = " ".join(params[1:])
        chat_data["role_names"][str(int(lvl_s))] = r_name
        save_db(db)
        return await message.answer(f"✅ Новая роль создана: `{lvl_s} lvl` ➔ **{r_name}**")

    elif cmd == "delrole":
        if user_lvl < 90:
            return await message.answer(f"❌ Требуется 90+ уровень (у вас: {user_lvl}).")
        if not params or not params[0].isdigit():
            return await message.answer("❌ Укажите числовой уровень роли.")
        lvl_key = str(int(params[0]))
        if lvl_key in chat_data["role_names"]:
            del chat_data["role_names"][lvl_key]
            save_db(db)
            return await message.answer(f"🗑 Роль уровня `{lvl_key}` успешно удалена.")
        return await message.answer("❌ Указанная роль не найдена в базе.")

    elif cmd in ["setadmin", "выдатьроль", "роль"]:
        if user_lvl < 70:
            return await message.answer(f"❌ Требуется 70+ уровень (у вас: {user_lvl}).")
        tid, rem = await resolve_target(message, params)
        if not tid:
            return await message.answer("❌ Укажите пользователя.")
        lvl_val = 0
        for p in rem:
            if p.isdigit():
                lvl_val = int(p)
                break

        t_str = str(tid)
        current_data = chat_data["members"].get(t_str, {"nickname": ""})
        current_nick = current_data.get("nickname", "") if isinstance(current_data, dict) else ""

        chat_data["members"][t_str] = {"level": lvl_val, "nickname": current_nick}
        save_db(db)
        add_log(f"Выдача роли {lvl_val} lvl для [id{tid}|игрока] от [id{message.from_id}|админа]")
        return await message.answer(f"✅ [id{tid}|Игроку] успешно присвоен ранг уровня `{lvl_val}`.")

    elif cmd in ["removerole", "снятьроль"]:
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
        return await message.answer(f"🟢 С [id{tid}|пользователя] сняты привилегии (0 уровень).")

    elif cmd == "setleader":
        if user_lvl < 60:
            return await message.answer(f"❌ Требуется 60+ уровень (у вас: {user_lvl}).")
        tid, rem = await resolve_target(message, params)
        if not tid or not rem:
            return await message.answer("❌ Формат: `/setleader [id/ответ] [Организация]`")
        org = " ".join(rem)
        db["leaders"][str(tid)] = org
        save_db(db)
        return await message.answer(f"👔 [id{tid}|Игрок] назначен лидером организации **{org}**.")

    elif cmd == "removeleader":
        if user_lvl < 60:
            return await message.answer(f"❌ Требуется 60+ уровень (у вас: {user_lvl}).")
        tid, _ = await resolve_target(message, params)
        if tid and str(tid) in db["leaders"]:
            del db["leaders"][str(tid)]
            save_db(db)
            return await message.answer(f"🟢 [id{tid}|Игрок] снят с поста лидера.")
        return await message.answer("❌ Лидер не найден в списке.")

    elif cmd == "leaders":
        if not db.get("leaders"):
            return await message.answer("👔 Список лидеров организаций пока пуст.")
        l_msg = "👔 **ЛИДЕРЫ ОРГАНИЗАЦИЙ:**\n\n"
        for l_id, org in db["leaders"].items():
            l_msg += f"• [id{int(l_id)}|Лидер] ➔ **{org}**\n"
        return await message.answer(l_msg)

    elif cmd == "bonus":
        return await message.answer(
            "🎁 **БОНУСЫ PRINCE RUSSIA**\n\n"
            "• Официальный портал: https://site-prince-russia.samp.date/\n"
            "• Следи за новостями в беседах и на форуме проекта!"
        )

    elif cmd == "grole":
        if user_lvl < 95:
            return await message.answer(f"❌ Требуется 95+ уровень (у вас: {user_lvl}).")
        tid, rem = await resolve_target(message, params)
        if not tid or not rem or not rem[0].isdigit():
            return await message.answer("❌ Формат: `/grole [ID] [уровень]`")
        db["global_roles"][str(tid)] = int(rem[0])
        save_db(db)
        return await message.answer(f"🌐 Глобальная роль `{rem[0]}` выдана [id{tid}|пользователю] по всей сети.")

    elif cmd == "grr":
        if user_lvl < 95:
            return await message.answer(f"❌ Требуется 95+ уровень (у вас: {user_lvl}).")
        tid, _ = await resolve_target(message, params)
        if tid and str(tid) in db["global_roles"]:
            del db["global_roles"][str(tid)]
            save_db(db)
            return await message.answer(f"🟢 Глобальная роль аннулирована у [id{tid}|пользователя].")
        return await message.answer("❌ У игрока отсутствуют глобальные роли.")

    elif cmd == "gban":
        if user_lvl < 90:
            return await message.answer(f"❌ Требуется 90+ уровень (у вас: {user_lvl}).")
        tid, rem = await resolve_target(message, params)
        if not tid:
            return await message.answer("❌ Укажите цель.")
        reason = " ".join(rem) if rem else "Глобальное нарушение"
        db["global_bans"][str(tid)] = reason
        save_db(db)
        add_log(f"Глобальный бан: [id{tid}|нарушитель], причина: {reason}")
        return await message.answer(f"⛔ ГЛОБАЛЬНЫЙ БАН ПРОЕКТА для [id{tid}|игрока]! Причина: {reason}")

    elif cmd in ["admins", "админс"]:
        all_r = {**db["global_role_names"], **chat_data["role_names"]}
        lines = []

        if chat_owner_id:
            o_nick = ""
            o_info = chat_data["members"].get(str(chat_owner_id))
            if isinstance(o_info, dict) and o_info.get("nickname"):
                o_nick = f" ({o_info['nickname']})"
            lines.append(f"👑 **Владелец чата:** [id{chat_owner_id}|Профиль]{o_nick} ➔ `100 lvl`")

        shown_ids = {chat_owner_id} if chat_owner_id else set()

        for m_id, info in chat_data.get("members", {}).items():
            uid_int = int(m_id)
            if uid_int in shown_ids:
                continue
            lvl = info.get("level", 0) if isinstance(info, dict) else int(info or 0)
            if lvl > 0:
                shown_ids.add(uid_int)
                r_name = all_r.get(lvl) or all_r.get(str(lvl)) or "Администратор"
                nick_str = f" — `{info.get('nickname')}`" if isinstance(info, dict) and info.get("nickname") else ""
                lines.append(f"• [id{uid_int}|Администратор]{nick_str} ➔ **{r_name}** `[{lvl} lvl]`")

        for g_id, lvl in db.get("global_roles", {}).items():
            uid_int = int(g_id)
            if uid_int in shown_ids or int(lvl) <= 0:
                continue
            shown_ids.add(uid_int)
            r_name = all_r.get(int(lvl)) or all_r.get(str(lvl)) or "Админ сети"
            lines.append(f"• 🌐 [id{uid_int}|Админ сети] ➔ **{r_name}** `[{lvl} lvl]`")

        if not lines:
            return await message.answer("👑 В этом чате пока нет назначенных администраторов.")

        return await message.answer("👑 **АДМИНИСТРАЦИЯ БЕСЕДЫ:**\n\n" + "\n".join(lines))


# =====================================================================
# 5. ЗАПУСК БОТА
# =====================================================================
if __name__ == "__main__":
    bot.run_forever()
