import os
import json
import time
import logging
import asyncio
from threading import Thread
from flask import Flask
from vkbottle.bot import Bot, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Flask-сервер для удержания 24/7 (для Render/Koyeb)
app = Flask(__name__)

@app.route('/')
def home():
    return "Prince Russia Bot: ONLINE 24/7", 200

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

Thread(target=run_flask, daemon=True).start()

# Конфигурация ВК бота
TOKEN = os.environ.get("VK_TOKEN", "vk1.a.qGTN_rCK6d4Yg4ty8YkruE6DbovbX5lwzHcQcN6wQ15aACfSrhsyi5F7R9xip5mq03EeLvxI2gZwJSVvuWMv0eP7vv59FFJvPNYWpRI7R2nzXM0gbobnLpmRaI3yM751Cml4ZOPDcIc380c3hekN0jgZ3QeP76p9hn1Sw6kwK6mOCyomwB33nVy1uBGAbC0mDQpu5eiq2HlVDAKi4YjHYw")
bot = Bot(token=TOKEN)

MAIN_OWNER_ID = 897082738  # Главный ID владельца

DB_FILE = "chat_manager_db.json"

DEFAULT_ROLES = {
    100: "Основатель",
    95: "Зам. Основателя",
    90: "Руководитель Проекта",
    88: "Зам. Руководителя Проекта",
    80: "Спец. Администратор",
    77: "Красная Администрация",
    75: "Зам. Специального Администратора",
    70: "Команда Проекта",
    60: "Главный Администратор",
    55: "ОЗГА/ЗГА",
    45: "Куратор Администрации"
}

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Ошибка чтения БД: {e}")
            return {}
    return {}

def save_db(data):
    try:
        temp_file = DB_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, DB_FILE)
    except Exception as e:
        logging.error(f"Ошибка сохранения БД: {e}")

db = load_db()
if "chats" not in db: db["chats"] = {}
if "global_chats" not in db: db["global_chats"] = []
if "broadcast_admins" not in db: db["broadcast_admins"] = [MAIN_OWNER_ID]
if "global_roles" not in db: db["global_roles"] = {}
if "global_bans" not in db: db["global_bans"] = {}
if "global_role_names" not in db: db["global_role_names"] = DEFAULT_ROLES.copy()
if "leaders" not in db: db["leaders"] = {}
if "unions" not in db: db["unions"] = {}
if "logs" not in db: db["logs"] = []

user_states = {}

def add_log(text):
    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
    entry = f"{timestamp} {text}"
    db["logs"].append(entry)
    if len(db["logs"]) > 200:
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
            "role_names": DEFAULT_ROLES.copy()
        }
    return db["chats"][p_str]

async def get_chat_owner_id(peer_id):
    try:
        chat_info = await bot.api.messages.get_conversations_by_peer_ids(peer_ids=[peer_id])
        if chat_info and chat_info.items:
            return chat_info.items[0].chat_settings.owner_id
    except Exception as e:
        logging.warning(f"Ошибка получения владельца чата {peer_id}: {e}")
    return None

def get_user_level(message: Message, chat_data: dict, chat_owner_id: int) -> int:
    uid = message.from_id
    if uid == MAIN_OWNER_ID or uid in db["broadcast_admins"]:
        return 100
    if chat_owner_id and uid == chat_owner_id:
        return 100
    if str(uid) in db["global_roles"]:
        return db["global_roles"][str(uid)]
    
    m_info = chat_data["members"].get(str(uid), {"level": 0})
    if isinstance(m_info, dict):
        return m_info.get("level", 0)
    return int(m_info)

async def resolve_target(message: Message, args: list):
    if message.reply_message:
        return message.reply_message.from_id, args
    if not args:
        return None, []
    
    target_raw = args[0]
    identifier = target_raw.strip().replace("https://vk.com/", "").replace("vk.com/", "").replace("@", "").replace("id", "")
    
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


# === ОБРАБОТЧИКИ ЛИЧНЫХ СООБЩЕНИЙ ===
@bot.on.private_message(text=["/start", "Начать", "начать", "Меню", "меню", "🔙 Главное меню", "❌ Отмена"])
async def private_start(message: Message):
    uid = message.from_id
    if uid in user_states: del user_states[uid]
    is_main = (uid == MAIN_OWNER_ID)
    has_broadcast = (is_main or uid in db["broadcast_admins"])
    
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("🌐 Сайт проекта"), color=KeyboardButtonColor.POSITIVE)
    if has_broadcast:
        kb.row()
        kb.add(Text("📢 Рассылка"), color=KeyboardButtonColor.NEGATIVE)
    if is_main:
        kb.row()
        kb.add(Text("⚙️ Управление доступами"), color=KeyboardButtonColor.PRIMARY)
    
    await message.answer(
        "👑 **PRINCE RUSSIA — ADMIN PANEL** 👑\n\n"
        "Система управления ботом и проектом активна.",
        keyboard=kb.get_json()
    )

@bot.on.private_message(text="⚙️ Управление доступами")
async def private_access_panel(message: Message):
    if message.from_id != MAIN_OWNER_ID: return
    kb = Keyboard(one_time=False, inline=True)
    kb.add(Text("➕ Выдать доступ"), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("➖ Забрать доступ"), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Text("🔙 Главное меню"), color=KeyboardButtonColor.PRIMARY)
    
    admins_list = ", ".join([f"[id{aid}|ID {aid}]" for aid in db["broadcast_admins"]])
    await message.answer(
        f"⚙️ **УПРАВЛЕНИЕ ДОСТУПОМ К РАССЫЛКЕ**\n\n"
        f"Администраторы рассылки:\n{admins_list}",
        keyboard=kb.get_json()
    )

@bot.on.private_message(text="➕ Выдать доступ")
async def private_add_adm(message: Message):
    if message.from_id != MAIN_OWNER_ID: return
    user_states[message.from_id] = "wait_add_adm"
    await message.answer("✍️ Введите VK ID пользователя:", keyboard=Keyboard(one_time=False, inline=True).add(Text("❌ Отмена"), color=KeyboardButtonColor.NEGATIVE).get_json())

@bot.on.private_message(text="➖ Забрать доступ")
async def private_rem_adm(message: Message):
    if message.from_id != MAIN_OWNER_ID: return
    user_states[message.from_id] = "wait_rem_adm"
    await message.answer("✍️ Введите VK ID пользователя:", keyboard=Keyboard(one_time=False, inline=True).add(Text("❌ Отмена"), color=KeyboardButtonColor.NEGATIVE).get_json())

@bot.on.private_message(text="📢 Рассылка")
async def private_broadcast(message: Message):
    uid = message.from_id
    if uid != MAIN_OWNER_ID and uid not in db["broadcast_admins"]: return
    user_states[uid] = "wait_broadcast"
    await message.answer("✍️ Введите текст для глобальной рассылки:", keyboard=Keyboard(one_time=False, inline=True).add(Text("❌ Отмена"), color=KeyboardButtonColor.NEGATIVE).get_json())

@bot.on.private_message(text="🌐 Сайт проекта")
async def private_site(message: Message):
    await message.answer("🌐 Официальный сайт Prince Russia: https://site-prince-russia.samp.date/")

@bot.on.private_message()
async def private_handler(message: Message):
    uid = message.from_id
    text = message.text
    if not text: return
    state = user_states.get(uid)

    if state == "wait_add_adm" and uid == MAIN_OWNER_ID:
        del user_states[uid]
        clean = text.strip().replace("id", "")
        if clean.isdigit():
            tid = int(clean)
            if tid not in db["broadcast_admins"]:
                db["broadcast_admins"].append(tid)
                save_db(db)
                return await message.answer(f"✅ Пользователю [id{tid}|ID {tid}] выдан доступ к рассылке.")
        return await message.answer("❌ Некорректный ID.")

    if state == "wait_rem_adm" and uid == MAIN_OWNER_ID:
        del user_states[uid]
        clean = text.strip().replace("id", "")
        if clean.isdigit():
            tid = int(clean)
            if tid != MAIN_OWNER_ID and tid in db["broadcast_admins"]:
                db["broadcast_admins"].remove(tid)
                save_db(db)
                return await message.answer(f"✅ Доступ забран у [id{tid}|ID {tid}].")
        return await message.answer("❌ Некорректный ID.")

    if state == "wait_broadcast" and (uid == MAIN_OWNER_ID or uid in db["broadcast_admins"]):
        del user_states[uid]
        count = 0
        for cid in db.get("global_chats", []):
            try:
                await bot.api.messages.send(peer_id=int(cid), message=f"📢 **ГЛОБАЛЬНОЕ СООБЩЕНИЕ:**\n\n{text}", random_id=0)
                count += 1
            except Exception as e:
                logging.error(f"Ошибка рассылки в {cid}: {e}")
        add_log(f"Глобальная рассылка от ID {uid} в {count} чатов.")
        return await message.answer(f"✅ Сообщение успешно доставлено в {count} чат(ов).")

    await message.answer("❌ Воспользуйтесь кнопками меню или отправьте команду.")


# === ОБРАБОТЧИКИ КОМАНД В БЕСЕДАХ ===
@bot.on.chat_message()
async def chat_handler(message: Message):
    peer_id = message.peer_id
    
    if peer_id not in db["global_chats"]:
        db["global_chats"].append(peer_id)
        save_db(db)

    chat_data = get_chat_data(peer_id)
    chat_owner_id = await get_chat_owner_id(peer_id)

    if chat_owner_id:
        o_str = str(chat_owner_id)
        if o_str not in chat_data["members"]:
            chat_data["members"][o_str] = {"level": 100, "nickname": "[Создатель]"}
        else:
            chat_data["members"][o_str]["level"] = 100
        save_db(db)

    # Проверка бана при входе
    if message.action and message.action.type in ["chat_invite_user", "chat_invite_user_by_link"]:
        j_id = message.action.member_id if message.action.member_id else message.from_id
        if str(j_id) in db["global_bans"] or str(j_id) in chat_data.get("bans", {}):
            try:
                await bot.api.messages.remove_chat_user(chat_id=message.chat_id, user_id=j_id)
                await message.answer(f"⛔ Пользователь [id{j_id}|был изгнан]: У него активная блокировка!")
            except Exception:
                pass
            return

    uid = str(message.from_id)

    # Авто-удаление сообщений при муте
    if uid in chat_data.get("mutes", {}):
        if time.time() < chat_data["mutes"][uid]:
            try:
                await bot.api.messages.delete(peer_id=peer_id, conversation_message_ids=[message.conversation_message_id], delete_for_all=True)
            except Exception:
                pass
            return
        else:
            del chat_data["mutes"][uid]
            save_db(db)

    text = message.text
    if not text: return
    clean_text = text.lower().strip()

    # Очистка от упоминаний бота
    for mention in [f"[club{message.group_id}|@", "@club", "@public"]:
        if mention in clean_text:
            parts = clean_text.split(" ", 1)
            if len(parts) > 1:
                clean_text = parts[1].strip()

    if clean_text in ["/menu", "меню"]:
        kb = Keyboard(one_time=False, inline=True)
        kb.add(Text("🌐 Сайт"), color=KeyboardButtonColor.POSITIVE)
        kb.add(Text("📜 Правила"), color=KeyboardButtonColor.PRIMARY)
        kb.row()
        kb.add(Text("📋 Роли"), color=KeyboardButtonColor.POSITIVE)
        kb.add(Text("📊 Стата"), color=KeyboardButtonColor.PRIMARY)
        return await message.answer("👑 **ПАНЕЛЬ УПРАВЛЕНИЯ БЕСЕДОЙ**", keyboard=kb.get_json())

    if clean_text in ["📜 правила", "правила"]:
        return await message.answer("📜 **ПРАВИЛА БЕСЕДЫ:**\n1. Запрещен спам и реклама.\n2. Уважительное отношение к участникам и админам.\n3. Получение 3/3 предупреждений ведет к кику.")

    if clean_text in ["📋 роли", "/roles", "роли"]:
        r_list = "📋 **ИЕРАРХИЯ ДОЛЖНОСТЕЙ:**\n"
        all_roles = {**db["global_role_names"], **chat_data["role_names"]}
        for lvl in sorted(all_roles.keys(), key=int, reverse=True):
            r_list += f"• `{lvl}` ➔ **{all_roles[lvl]}**\n"
        return await message.answer(r_list)

    if not clean_text.startswith("/"):
        return

    args = clean_text[1:].split()
    cmd = args[0] if args else ""
    params = args[1:] if len(args) > 1 else []

    user_lvl = get_user_level(message, chat_data, chat_owner_id)

    # 1. Мут / Размут
    if cmd == "mute":
        if user_lvl < 45: return await message.answer("❌ Требуется 45+ уровень.")
        tid, rem = await resolve_target(message, params)
        if not tid: return await message.answer("❌ Укажите цель.")
        mins = int(rem[0]) if rem and rem[0].isdigit() else 10
        chat_data["mutes"][str(tid)] = time.time() + (mins * 60)
        save_db(db)
        add_log(f"Мут: ID {tid} на {mins} мин от ID {message.from_id}")
        return await message.answer(f"🤫 Пользователю [id{tid}|выдан мут] на {mins} минут.")

    elif cmd in ["unmute", "unmite"]:
        if user_lvl < 45: return await message.answer("❌ Требуется 45+ уровень.")
        tid, _ = await resolve_target(message, params)
        if tid and str(tid) in chat_data["mutes"]:
            del chat_data["mutes"][str(tid)]
            save_db(db)
            return await message.answer(f"🔊 С [id{tid}|пользователя] снят мут.")
        return await message.answer("❌ Активный мут не найден.")

    # 2. Бан / Разбан
    elif cmd == "ban":
        if user_lvl < 55: return await message.answer("❌ Требуется 55+ уровень.")
        tid, rem = await resolve_target(message, params)
        if not tid: return await message.answer("❌ Укажите цель.")
        reason = " ".join(rem) if rem else "Причина не указана"
        chat_data["bans"][str(tid)] = {"reason": reason}
        save_db(db)
        try:
            await bot.api.messages.remove_chat_user(chat_id=message.chat_id, user_id=tid)
        except Exception:
            pass
        add_log(f"Бан в чате: ID {tid}, причина: {reason}")
        return await message.answer(f"🚫 Пользователь [id{tid}|забанен]. Причина: {reason}")

    elif cmd == "unban":
        if user_lvl < 55: return await message.answer("❌ Требуется 55+ уровень.")
        tid, _ = await resolve_target(message, params)
        if tid and str(tid) in chat_data["bans"]:
            del chat_data["bans"][str(tid)]
            save_db(db)
            return await message.answer(f"🟢 [id{tid}|Пользователь] разбанен.")
        return await message.answer("❌ Пользователь не находится в бане.")

    elif cmd == "banlist":
        bans = chat_data.get("bans", {})
        if not bans: return await message.answer("📋 Бан-лист пуст.")
        msg = "📋 **СПИСОК ЗАБЛОКИРОВАННЫХ:**\n"
        for b_id, info in bans.items():
            msg += f"• [id{int(b_id)}|Игрок] ➔ Причина: {info.get('reason')}\n"
        return await message.answer(msg)

    elif cmd in ["chekban", "checkban"]:
        tid, _ = await resolve_target(message, params)
        if not tid: tid = message.from_id
        is_b = str(tid) in chat_data.get("bans", {}) or str(tid) in db["global_bans"]
        status = "Забанен 🔴" if is_b else "Чист 🟢"
        return await message.answer(f"🔍 Статус блокировки [id{tid}|пользователя]: {status}")

    # 3. Статистика / Профиль
    elif cmd in ["stats", "стата"]:
        tid, _ = await resolve_target(message, params)
        if not tid: tid = message.from_id
        lvl = get_user_level(message, chat_data, chat_owner_id)
        all_r = {**db["global_role_names"], **chat_data["role_names"]}
        r_name = all_r.get(lvl, "Участник")
        warns = len(chat_data.get("warns", {}).get(str(tid), []))
        return await message.answer(f"📊 **ПРОФИЛЬ** [id{tid}|пользователя]:\n• Должность: **{r_name}** `[{lvl} lvl]`\n• Предупреждения: `{warns}/3`")

    elif cmd == "statschat":
        c_count = len(db.get("global_chats", []))
        m_count = len(chat_data.get("members", {}))
        return await message.answer(f"📈 **СТАТИСТИКА БЕСЕДЫ:**\n• Сохранённых участников: `{m_count}`\n• Всего подключённых чатов: `{c_count}`")

    # 4. Кик / Варны
    elif cmd == "kick":
        if user_lvl < 45: return await message.answer("❌ Требуется 45+ уровень.")
        tid, _ = await resolve_target(message, params)
        if not tid: return await message.answer("❌ Укажите цель.")
        try:
            await bot.api.messages.remove_chat_user(chat_id=message.chat_id, user_id=tid)
            return await message.answer(f"✅ Пользователь [id{tid}|изгнан].")
        except Exception as e:
            return await message.answer(f"❌ Ошибка исключения: {e}")

    elif cmd == "warn":
        if user_lvl < 45: return await message.answer("❌ Требуется 45+ уровень.")
        tid, rem = await resolve_target(message, params)
        if not tid: return await message.answer("❌ Укажите цель.")
        reason = " ".join(rem) if rem else "Причина не указана"
        t_str = str(tid)
        if t_str not in chat_data["warns"]: chat_data["warns"][t_str] = []
        chat_data["warns"][t_str].append(reason)
        save_db(db)
        cnt = len(chat_data["warns"][t_str])
        await message.answer(f"⚠️ Пользователю [id{tid}|выдано предупреждение] ({cnt}/3). Причина: {reason}")
        if cnt >= 3:
            try:
                await bot.api.messages.remove_chat_user(chat_id=message.chat_id, user_id=tid)
                chat_data["warns"][t_str] = []
                save_db(db)
                await message.answer(f"🚫 [id{tid}|Исключён] за достижение лимита предупреждений (3/3).")
            except Exception:
                pass

    elif cmd == "unwarn":
        if user_lvl < 45: return await message.answer("❌ Требуется 45+ уровень.")
        tid, _ = await resolve_target(message, params)
        if tid and str(tid) in chat_data["warns"] and chat_data["warns"][str(tid)]:
            chat_data["warns"][str(tid)].pop()
            save_db(db)
            return await message.answer(f"🟢 Предупреждение снято с [id{tid}|пользователя].")
        return await message.answer("❌ Предупреждения отсутствуют.")

    # 5. Выговоры
    elif cmd == "vig":
        if user_lvl < 55: return await message.answer("❌ Требуется 55+ уровень.")
        tid, rem = await resolve_target(message, params)
        if not tid: return await message.answer("❌ Укажите цель.")
        return await message.answer(f"⚠️ Администратору [id{tid}|выдан выговор]. Причина: {' '.join(rem) if rem else 'Не указана'}")

    elif cmd == "unvig":
        if user_lvl < 55: return await message.answer("❌ Требуется 55+ уровень.")
        tid, _ = await resolve_target(message, params)
        if tid: return await message.answer(f"🟢 С администратора [id{tid}|снят выговор].")

    # 6. Управление ролями и правами
    elif cmd == "newrole":
        if user_lvl < 90: return await message.answer("❌ Требуется 90+ уровень.")
        if len(params) < 2: return await message.answer("❌ Формат: `/newrole [уровень] [Название]`")
        lvl_s = params[0]
        if not lvl_s.isdigit(): return await message.answer("❌ Уровень должен быть числом.")
        r_name = " ".join(params[1:])
        chat_data["role_names"][int(lvl_s)] = r_name
        save_db(db)
        return await message.answer(f"✅ Назначена роль уровня `{lvl_s}` ➔ *{r_name}*")

    elif cmd == "delrole":
        if user_lvl < 90: return await message.answer("❌ Требуется 90+ уровень.")
        if not params or not params[0].isdigit(): return await message.answer("❌ Укажите уровень роли.")
        lvl_i = int(params[0])
        if lvl_i in chat_data["role_names"]:
            del chat_data["role_names"][lvl_i]
            save_db(db)
            return await message.answer(f"🗑 Локальная роль `{lvl_i}` удалена.")
        return await message.answer("❌ Роль не найдена.")

    elif cmd in ["выдатьроль", "роль"]:
        if user_lvl < 70: return await message.answer("❌ Требуется 70+ уровень.")
        tid, rem = await resolve_target(message, params)
        if not tid: return await message.answer("❌ Укажите пользователя.")
        lvl_val = 0
        for p in rem:
            if p.isdigit():
                lvl_val = int(p)
                break
        chat_data["members"][str(tid)] = {"level": lvl_val, "nickname": chat_data["members"].get(str(tid), {}).get("nickname", "")}
        save_db(db)
        add_log(f"Назначена роль {lvl_val} для ID {tid}")
        return await message.answer(f"✅ Пользователю [id{tid}|установлен] уровень прав `{lvl_val}`.")

    elif cmd in ["removerole", "снятьроль"]:
        if user_lvl < 70: return await message.answer("❌ Требуется 70+ уровень.")
        tid, _ = await resolve_target(message, params)
        if not tid: return await message.answer("❌ Укажите пользователя.")
        chat_data["members"][str(tid)] = {"level": 0, "nickname": ""}
        save_db(db)
        return await message.answer(f"🟢 С [id{tid}|пользователя] сброшены роли.")

    # 7. Глобальное управление
    elif cmd == "grole":
        if user_lvl < 95: return await message.answer("❌ Требуется 95+ уровень.")
        tid, rem = await resolve_target(message, params)
        if not tid or not rem or not rem[0].isdigit(): return await message.answer("❌ Формат: `/grole [ID] [уровень]`")
        db["global_roles"][str(tid)] = int(rem[0])
        save_db(db)
        return await message.answer(f"🌐 Глобальная роль `{rem[0]}` присвоена [id{tid}|пользователю].")

    elif cmd == "grr":
        if user_lvl < 95: return await message.answer("❌ Требуется 95+ уровень.")
        tid, _ = await resolve_target(message, params)
        if tid and str(tid) in db["global_roles"]:
            del db["global_roles"][str(tid)]
            save_db(db)
            return await message.answer(f"🟢 Глобальная роль аннулирована у [id{tid}|пользователя].")
        return await message.answer("❌ Глобальная роль не найдена.")

    elif cmd == "gban":
        if user_lvl < 90: return await message.answer("❌ Требуется 90+ уровень.")
        tid, rem = await resolve_target(message, params)
        if not tid: return await message.answer("❌ Укажите цель.")
        reason = " ".join(rem) if rem else "Глобальное нарушение"
        db["global_bans"][str(tid)] = reason
        save_db(db)
        add_log(f"Глобальный бан: ID {tid}, причина: {reason}")
        return await message.answer(f"⛔ **ГЛОБАЛЬНАЯ БЛОКИРОВКА** для [id{tid}|пользователя]! Причина: {reason}")

    # 8. Инфо и Сервис
    elif cmd == "logs":
        if user_lvl < 70: return await message.answer("❌ Требуется 70+ уровень.")
        recent = "\n".join(db["logs"][-15:])
        return await message.answer(f"📜 **ПОСЛЕДНИЕ СОБЫТИЯ:**\n{recent if recent else 'Записи отсутствуют'}")

    elif cmd == "welcome":
        return await message.answer("👋 Приветствуем в беседе проекта Prince Russia!")

    elif cmd == "pin":
        if user_lvl < 45: return await message.answer("❌ Требуется 45+ уровень.")
        if not message.reply_message: return await message.answer("❌ Сделайте ответ на сообщение.")
        try:
            await bot.api.messages.pin(peer_id=peer_id, conversation_message_id=message.reply_message.conversation_message_id)
            return await message.answer("📌 Сообщение закрепили.")
        except Exception as e:
            return await message.answer(f"❌ Ошибка закрепления: {e}")

    elif cmd == "bonus":
        return await message.answer("🎁 Бонус проекта: Скачайте клиент Prince Russia и получите 25.000.000$ + 1000 BC!")

    elif cmd == "admins":
        a_msg = "👑 **СПИСОК АДМИНИСТРАЦИИ В БЕСЕДЕ:**\n"
        found = False
        for m_id, info in chat_data.get("members", {}).items():
            lvl = info.get("level", 0) if isinstance(info, dict) else info
            if lvl >= 45:
                all_r = {**db["global_role_names"], **chat_data["role_names"]}
                found = True
                a_msg += f"• [id{int(m_id)}|Администратор] ➔ {all_r.get(lvl, 'Админ')} `[{lvl} lvl]`\n"
        return await message.answer(a_msg if found else "📋 В беседе нет админов.")

    elif cmd == "leaders":
        p_str = str(peer_id)
        chat_leads = db["leaders"].get(p_str, {})
        if not chat_leads: return await message.answer("📋 Лидеры в этой беседе не назначены.")
        l_msg = "📋 **СПИСОК ЛИДЕРОВ:**\n"
        for l_id, org in chat_leads.items():
            l_msg += f"• [id{int(l_id)}|Лидер] ➔ Организация: `{org}`\n"
        return await message.answer(l_msg)

    elif cmd == "setleader":
        if user_lvl < 60: return await message.answer("❌ Требуется 60+ уровень.")
        tid, rem = await resolve_target(message, params)
        if not tid or not rem: return await message.answer("❌ Формат: `/setleader [ответ/id] [Организация]`")
        org_name = " ".join(rem)
        p_str = str(peer_id)
        if p_str not in db["leaders"]: db["leaders"][p_str] = {}
        db["leaders"][p_str][str(tid)] = org_name
        save_db(db)
        return await message.answer(f"👑 Пользователь [id{tid}|назначен лидером]: *{org_name}*")

    elif cmd == "removeleader":
        if user_lvl < 60: return await message.answer("❌ Требуется 60+ уровень.")
        tid, _ = await resolve_target(message, params)
        p_str = str(peer_id)
        if tid and p_str in db["leaders"] and str(tid) in db["leaders"][p_str]:
            del db["leaders"][p_str][str(tid)]
            save_db(db)
            return await message.answer(f"🟢 С [id{tid}|пользователя] сняты полномочия лидера.")
        return await message.answer("❌ Пользователь не найден среди лидеров.")

if __name__ == "__main__":
    logging.info("🚀 Запуск Prince Russia VK Core Engine...")
    bot.run_forever()
```
