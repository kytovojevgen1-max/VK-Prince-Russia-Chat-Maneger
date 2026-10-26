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

@app.route('/')
def home():
    return "Prince Russia Core Server: ONLINE 24/7"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

Thread(target=run_flask, daemon=True).start()


# =====================================================================
# 2. КОНФИГУРАЦИЯ И БАЗА ДАННЫХ
# =====================================================================
TOKEN = "vk1.a.qGTN_rCK6d4Yg4ty8YkruE6DbovbX5lwzHcQcN6wQ15aACfSrhsyi5F7R9xip5mq03EeLvxI2gZwJSVvuWMv0eP7vv59FFJvPNYWpRI7R2nzXM0gbobnLpmRaI3yM751Cml4ZOPDcIc380c3hekN0jgZ3QeP76p9hn1Sw6kwK6mOCyomwB33nVy1uBGAbC0mDQpu5eiq2HlVDAKi4YjHYw"
bot = Bot(token=TOKEN)

MAIN_OWNER_ID = 897082738  # Твой главный VK ID

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
if "unions" not in db: db["unions"] = {}
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
            "role_names": DEFAULT_ROLES.copy()
        }
    return db["chats"][p_str]

async def get_chat_owner_id(peer_id):
    try:
        chat_info = await bot.api.messages.get_conversations_by_peer_ids(peer_ids=[peer_id])
        if chat_info and chat_info.items:
            return chat_info.items[0].chat_settings.owner_id
    except Exception:
        pass
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


# =====================================================================
# 3. ЛИЧНЫЕ СООБЩЕНИЯ (ПАНЕЛЬ УПРАВЛЕНИЯ В ЛС)
# =====================================================================

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
        "👑 **PRINCE RUSSIA — ADMIN PANEL** 👑\n"
        "Панель управления проектом и ботом в личных сообщениях.",
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
        f"⚙️ **УПРАВЛЕНИЕ ДОСТУПОМ К РАССЫЛКЕ**\n"
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
                return await message.answer(f"✅ Пользователю [id{tid}|ID {tid}] выдан доступ.")
        return await message.answer("❌ Ошибка ID.")

    if state == "wait_rem_adm" and uid == MAIN_OWNER_ID:
        del user_states[uid]
        clean = text.strip().replace("id", "")
        if clean.isdigit():
            tid = int(clean)
            if tid != MAIN_OWNER_ID and tid in db["broadcast_admins"]:
                db["broadcast_admins"].remove(tid)
                save_db(db)
                return await message.answer(f"✅ Доступ забран у [id{tid}|ID {tid}].")
        return await message.answer("❌ Ошибка ID.")

    if state == "wait_broadcast" and (uid == MAIN_OWNER_ID or uid in db["broadcast_admins"]):
        del user_states[uid]
        count = 0
        for cid in db.get("global_chats", []):
            try:
                await bot.api.messages.send(peer_id=int(cid), message=f"📢 **ГЛОБАЛЬНОЕ СООБЩЕНИЕ:**\n\n{text}", random_id=0)
                count += 1
            except Exception:
                pass
        add_log(f"Глобальная рассылка от ID {uid} в {count} чатов.")
        return await message.answer(f"✅ Успешно отправлено в чатов: {count}")

    await message.answer("❌ Используйте инлайн-кнопки в ЛС или команды в беседах.")


# =====================================================================
# 4. РАБОТА В БЕСЕДАХ (МОДЕРАЦИЯ И КОМАНДЫ)
# =====================================================================

@bot.on.chat_message()
async def chat_handler(message: Message):
    peer_id = message.peer_id
    
    if peer_id not in db["global_chats"]:
        db["global_chats"].append(peer_id)
        save_db(db)

    chat_data = get_chat_data(peer_id)
    chat_owner_id = await get_chat_owner_id(peer_id)

    # Авто-привязка создателя беседы на 100 уровень
    if chat_owner_id:
        o_str = str(chat_owner_id)
        if o_str not in chat_data["members"]:
            chat_data["members"][o_str] = {"level": 100, "nickname": "[Создатель]"}
        else:
            chat_data["members"][o_str]["level"] = 100
        save_db(db)

    # Проверка глобальных банов и банов чата при входе
    if message.action and message.action.type == "chat_invite_user":
        j_id = message.action.member_id
        if str(j_id) in db["global_bans"] or str(j_id) in chat_data.get("bans", {}):
            try:
                await bot.api.messages.remove_chat_user(chat_id=message.chat_id, user_id=j_id)
                await message.answer(f"⛔ Пользователь [id{j_id}|пытался войти], но у него активный Бан!")
            except Exception:
                pass
            return

    uid = str(message.from_id)

    # Проверка мута
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

    for mention in ["[club" + str(message.group_id) + "|@", "@club", "@public"]:
        if mention in clean_text:
            parts = clean_text.split(" ", 1)
            if len(parts) > 1:
                clean_text = parts[1].strip()

    # Интерактивное меню с кнопками в беседе
    if clean_text in ["/menu", "меню"]:
        kb = Keyboard(one_time=False, inline=True)
        kb.add(Text("🌐 Сайт"), color=KeyboardButtonColor.POSITIVE)
        kb.add(Text("📜 Правила"), color=KeyboardButtonColor.PRIMARY)
        kb.row()
        kb.add(Text("📋 Роли"), color=KeyboardButtonColor.POSITIVE)
        kb.add(Text("📊 Стата"), color=KeyboardButtonColor.PRIMARY)
        return await message.answer("👑 **ПАНЕЛЬ УПРАВЛЕНИЯ БЕСЕДОЙ**", keyboard=kb.get_json())

    if clean_text in ["📜 правила", "правила"]:
        return await message.answer("📜 **ПРАВИЛА:**\n1. Без спама и рекламы.\n2. Уважение к администрации.\n3. За 3 варна — кик.")

    if clean_text in ["📋 роли", "/roles", "роли"]:
        r_list = "📋 **ИЕРАРХИЯ ДОЛЖНОСТЕЙ ПРОЕКТА:**\n"
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

    # --- КОМАНДЫ ---

    if cmd == "mute":
        if user_lvl < 45: return await message.answer("❌ Недостаточно прав (нужен 45+).")
        tid, rem = await resolve_target(message, params)
        if not tid: return await message.answer("❌ Укажите цель.")
        mins = int(rem[0]) if rem and rem[0].isdigit() else 10
        chat_data["mutes"][str(tid)] = time.time() + (mins * 60)
        save_db(db)
        add_log(f"Мут: ID {tid} на {mins} мин от ID {message.from_id}")
        return await message.answer(f"🤫 Пользователю [id{tid}|выдан мут] на {mins} минут.")

    elif cmd in ["unmute", "unmite"]:
        if user_lvl < 45: return await message.answer("❌ Недостаточно прав.")
        tid, _ = await resolve_target(message, params)
        if tid and str(tid) in chat_data["mutes"]:
            del chat_data["mutes"][str(tid)]
            save_db(db)
            return await message.answer(f"🔊 С [id{tid}|пользователя] снят мут.")
        return await message.answer("❌ Мут не найден.")

    elif cmd == "ban":
        if user_lvl < 55: return await message.answer("❌ Требуется 55+ уровень.")
        tid, rem = await resolve_target(message, params)
        if not tid: return await message.answer("❌ Укажите цель.")
        reason = " ".join(rem) if rem else "Не указана"
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
        return await message.answer("❌ Его нет в банах.")

    elif cmd == "banlist":
        bans = chat_data.get("bans", {})
        if not bans: return await message.answer("📋 Бан-лист пуст.")
        msg = "📋 **БАН-ЛИСТ БЕСЕДЫ:**\n"
        for b_id, info in bans.items():
            msg += f"• [id{int(b_id)}|Игрок] ➔ Причина: {info.get('reason')}\n"
        return await message.answer(msg)

    elif cmd in ["chekban", "checkban"]:
        tid, _ = await resolve_target(message, params)
        if not tid: tid = message.from_id
        is_b = str(tid) in chat_data.get("bans", {}) or str(tid) in db["global_bans"]
        status = "Забанен 🔴" if is_b else "Чист 🟢"
        return await message.answer(f"🔍 Статус бана [id{tid}|пользователя]: {status}")

    elif cmd in ["stats", "стата"]:
        tid, _ = await resolve_target(message, params)
        if not tid: tid = message.from_id
        lvl = get_user_level(message, chat_data, chat_owner_id)
        all_r = {**db["global_role_names"], **chat_data["role_names"]}
        r_name = all_r.get(lvl, "Игрок")
        warns = len(chat_data.get("warns", {}).get(str(tid), []))
        return await message.answer(f"📊 **СТАТИСТИКА** [id{tid}|Профиль]:\n• Должность: **{r_name}** `[{lvl} lvl]`\n• Варнов: `{warns}/3`")

    elif cmd == "statschat":
        c_count = len(db.get("global_chats", []))
        m_count = len(chat_data.get("members", {}))
        return await message.answer(f"📈 **СТАТИСТИКА БЕСЕДЫ:**\n• Участников в базе: `{m_count}`\n• Всего активных чатов у бота: `{c_count}`")

    elif cmd == "kick":
        if user_lvl < 45: return await message.answer("❌ Недостаточно прав.")
        tid, _ = await resolve_target(message, params)
        if not tid: return await message.answer("❌ Укажите цель.")
        try:
            await bot.api.messages.remove_chat_user(chat_id=message.chat_id, user_id=tid)
            return await message.answer(f"✅ [id{tid}|Кикнут].")
        except Exception as e:
            return await message.answer(f"❌ Ошибка: {e}")

    elif cmd == "warn":
        if user_lvl < 45: return await message.answer("❌ Недостаточно прав.")
        tid, rem = await resolve_target(message, params)
        if not tid: return await message.answer("❌ Укажите цель.")
        reason = " ".join(rem) if rem else "Не указана"
        t_str = str(tid)
        if t_str not in chat_data["warns"]: chat_data["warns"][t_str] = []
        chat_data["warns"][t_str].append(reason)
        save_db(db)
        cnt = len(chat_data["warns"][t_str])
        await message.answer(f"⚠️ [id{tid}|Варн] ({cnt}/3). Причина: {reason}")
        if cnt >= 3:
            try:
                await bot.api.messages.remove_chat_user(chat_id=message.chat_id, user_id=tid)
                chat_data["warns"][t_str] = []
                save_db(db)
                await message.answer(f"🚫 [id{tid}|Авто-кик] за 3 варна!")
            except Exception:
                pass

    elif cmd == "unwarn":
        if user_lvl < 45: return await message.answer("❌ Недостаточно прав.")
        tid, _ = await resolve_target(message, params)
        if tid and str(tid) in chat_data["warns"] and chat_data["warns"][str(tid)]:
            chat_data["warns"][str(tid)].pop()
            save_db(db)
            return await message.answer(f"🟢 Снят варн с [id{tid}|пользователя].")
        return await message.answer("❌ Нет активных варнов.")

    elif cmd == "vig":
        if user_lvl < 55: return await message.answer("❌ Требуется 55+ уровень.")
        tid, rem = await resolve_target(message, params)
        if not tid: return await message.answer("❌ Укажите цель.")
        return await message.answer(f"⚠️ Администратору [id{tid}|выдан выговор]. Причина: {' '.join(rem) if rem else 'Не указана'}")

    elif cmd == "unvig":
        if user_lvl < 55: return await message.answer("❌ Требуется 55+ уровень.")
        tid, _ = await resolve_target(message, params)
        if tid: return await message.answer(f"🟢 С администратора [id{tid}|снят выговор].")

    elif cmd == "logs":
        if user_lvl < 70: return await message.answer("❌ Доступно с 70 уровня.")
        recent = "\n".join(db["logs"][-15:])
        return await message.answer(f"📜 **ПОСЛЕДНИЕ ЛОГИ:**\n{recent if recent else 'Пусто'}")

    elif cmd == "welcome":
        return await message.answer("👋 Добро пожаловать в беседу проекта Prince Russia!")

    elif cmd == "pin":
        if user_lvl < 45: return await message.answer("❌ Нужны права администратора.")
        if not message.reply_message: return await message.answer("❌ Ответьте на сообщение.")
        try:
            await bot.api.messages.pin(peer_id=peer_id, conversation_message_id=message.reply_message.conversation_message_id)
            return await message.answer("📌 Закреплено!")
        except Exception as e:
            return await message.answer(f"❌ Ошибка: {e}")

    elif cmd == "повышение":
        return await message.answer("📈 Для повышения подайте отчет на форуме или обратитесь к руководству.")

    elif cmd == "понижение":
        return await message.answer("📉 Понижение выдается за нарушение регламента.")

    elif cmd == "newrole":
        if user_lvl < 90: return await message.answer("❌ Требуется 90+ уровень.")
        if len(params) < 2: return await message.answer("❌ Формат: `/newrole [ур] [Название]`")
        lvl_s = params[0]
        if not lvl_s.isdigit(): return await message.answer("❌ Уровень должен быть числом.")
        r_name = " ".join(params[1:])
        chat_data["role_names"][int(lvl_s)] = r_name
        save_db(db)
        return await message.answer(f"✅ Создана роль `{lvl_s}` ➔ *{r_name}*")

    elif cmd == "delrole":
        if user_lvl < 90: return await message.answer("❌ Требуется 90+ уровень.")
        if not params or not params[0].isdigit(): return await message.answer("❌ Укажите уровень роли.")
        lvl_i = int(params[0])
        if lvl_i in chat_data["role_names"]:
            del chat_data["role_names"][lvl_i]
            save_db(db)
            return await message.answer(f"🗑 Роль `{lvl_i}` удалена.")
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
        add_log(f"Выдача роли {lvl_val} для ID {tid} от ID {message.from_id}")
        return await message.answer(f"✅ Пользователю [id{tid}|успешно] установлена роль уровня `{lvl_val}`.")

    elif cmd in ["removerole", "снятьроль"]:
        if user_lvl < 70: return await message.answer("❌ Требуется 70+ уровень.")
        tid, _ = await resolve_target(message, params)
        if not tid: return await message.answer("❌ Укажите пользователя.")
        chat_data["members"][str(tid)] = {"level": 0, "nickname": ""}
        save_db(db)
        return await message.answer(f"🟢 С [id{tid}|пользователя] сняты роли (0 уровень).")

    elif cmd == "invite":
        if user_lvl < 45: return await message.answer("❌ Недостаточно прав.")
        if not params: return await message.answer("❌ Укажите ID или ссылку.")
        return await message.answer("🔗 Используйте стандартную ссылку беседы для добавления участников.")

    elif cmd == "grole":
        if user_lvl < 95: return await message.answer("❌ Требуется 95+ уровень.")
        tid, rem = await resolve_target(message, params)
        if not tid or not rem or not rem[0].isdigit(): return await message.answer("❌ Формат: `/grole [ID] [уровень]`")
        db["global_roles"][str(tid)] = int(rem[0])
        save_db(db)
        return await message.answer(f"🌐 Глобальная роль `{rem[0]}` выдана [id{tid}|пользователю].")

    elif cmd == "grr":
        if user_lvl < 95: return await message.answer("❌ Требуется 95+ уровень.")
        tid, _ = await resolve_target(message, params)
        if tid and str(tid) in db["global_roles"]:
            del db["global_roles"][str(tid)]
            save_db(db)
            return await message.answer(f"🟢 Глобальная роль снята с [id{tid}|пользователя].")
        return await message.answer("❌ У игрока нет глобальной роли.")

    elif cmd in ["gnewrole", "gрнав"]:
        if user_lvl < 100: return await message.answer("❌ Только для Основателя (100).")
        if len(params) < 2: return await message.answer("❌ Формат: `/gnewrole [ур] [Название]`")
        db["global_role_names"][int(params[0])] = " ".join(params[1:])
        save_db(db)
        return await message.answer("🌐 Глобальная роль успешно создана.")

    elif cmd == "gdelrole":
        if user_lvl < 100: return await message.answer("❌ Только для Основателя.")
        if params and params[0].isdigit():
            lvl_i = int(params[0])
            if lvl_i in db["global_role_names"]:
                del db["global_role_names"][lvl_i]
                save_db(db)
                return await message.answer("🌐 Глобальная роль удалена.")
        return await message.answer("❌ Ошибка.")

    elif cmd == "gban":
        if user_lvl < 90: return await message.answer("❌ Требуется 90+ уровень.")
        tid, rem = await resolve_target(message, params)
        if not tid: return await message.answer("❌ Укажите цель.")
        reason = " ".join(rem) if rem else "Нарушение проекта"
        db["global_bans"][str(tid)] = reason
        save_db(db)
        add_log(f"Глобальный бан: ID {tid}, причина: {reason}")
        return await message.answer(f"⛔ ГЛОБАЛЬНЫЙ БАН для [id{tid}|игрока]! Причина: {reason}")

    elif cmd == "gkick":
        if user_lvl < 70: return await message.answer("❌ Недостаточно прав.")
        tid, _ = await resolve_target(message, params)
        if tid:
            try:
                await bot.api.messages.remove_chat_user(chat_id=message.chat_id, user_id=tid)
                return await message.answer("✅ Изгнан.")
            except Exception:
                pass

    elif cmd == "gwarn":
        if user_lvl < 70: return await message.answer("❌ Недостаточно прав.")
        tid, _ = await resolve_target(message, params)
        if tid: return await message.answer(f"⚠️ [id{tid}|Игроку] выдан глобальный варн.")

    elif cmd == "createunity":
        if user_lvl < 90: return await message.answer("❌ Требуется 90+ уровень.")
        if not params: return await message.answer("❌ Укажите название.")
        u_name = params[0]
        db["unions"][u_name] = [peer_id]
        save_db(db)
        return await message.answer(f"🤝 Объединение `{u_name}` создано!")

    elif cmd == "addunity":
        if user_lvl < 90: return await message.answer("❌ Требуется 90+ уровень.")
        if len(params) < 2: return await message.answer("❌ Формат: `/addunity [название] [peer_id]`")
        u_name, p_target = params[0], int(params[1])
        if u_name in db["unions"]:
            if p_target not in db["unions"][u_name]:
                db["unions"][u_name].append(p_target)
                save_db(db)
                return await message.answer(f"🤝 Беседа добавлена в объединение `{u_name}`.")
        return await message.answer("❌ Объединение не найдено.")

    elif cmd == "bonus":
        return await message.answer("🎁 Бонус Prince Russia: скачайте игру на сайте и получите 25 000 000$ + 1000 BC!")

    elif cmd == "admins":
        a_msg = "👑 **АДМИНИСТРАЦИЯ В ЧАТЕ:**\n"
        found = False
        for m_id, info in chat_data.get("members", {}).items():
            lvl = info.get("level", 0) if isinstance(info, dict) else info
            if lvl >= 45:
                all_r = {**db["global_role_names"], **chat_data["role_names"]}
                found = True
                a_msg += f"• [id{int(m_id)}|Админ] ➔ {all_r.get(lvl, 'Админ')} `[{lvl} lvl]`\n"
        return await message.answer(a_msg if found else "📋 Активных администраторов в чате нет.")

    elif cmd == "leaders":
        p_str = str(peer_id)
        chat_leads = db["leaders"].get(p_str, {})
        if not chat_leads: return await message.answer("📋 В этой беседе нет лидеров.")
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
        return await message.answer(f"👑 [id{tid}|Назначен лидером]: *{org_name}*")

    elif cmd == "removeleader":
        if user_lvl < 60: return await message.answer("❌ Требуется 60+ уровень.")
        tid, _ = await resolve_target(message, params)
        p_str = str(peer_id)
        if tid and p_str in db["leaders"] and str(tid) in db["leaders"][p_str]:
            del db["leaders"][p_str][str(tid)]
            save_db(db)
            return await message.answer(f"🟢 С [id{tid}|игрока] снят пост лидера.")
        return await message.answer("❌ Лидер не найден.")

    elif cmd == "setadmin":
        if user_lvl < 70: return await message.answer("❌ Требуется 70+ уровень.")
        tid, rem = await resolve_target(message, params)
        if not tid or not rem or not rem[0].isdigit(): return await message.answer("❌ Формат: `/setadmin [ID] [ур]`")
        lvl_v = int(rem[0])
        chat_data["members"][str(tid)] = {"level": lvl_v, "nickname": ""}
        save_db(db)
        return await message.answer(f"✅ [id{tid}|Пользователю] выданы права администратора уровня `{lvl_v}`.")


if __name__ == "__main__":
    print("🚀 Prince Russia Chat Manager Core успешно запущен!")
    bot.run_forever()
```

Выполнен генерационный запрос: создал файл `Chat_manager.txt`, содержащий код бота на Python с системой ролей, модерацией, веб-сервером и без опросов. Ты можешь сразу скопировать или экпортировать этот файл из правой панели.