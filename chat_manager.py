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

def get_user_level_by_id(uid: int, chat_data: dict, chat_owner_id: int) -> int:
    if uid == MAIN_OWNER_ID or uid in db["broadcast_admins"]:
        return 100
    if chat_owner_id and uid == chat_owner_id:
        return 100
    if str(uid) in db["global_roles"]:
        return int(db["global_roles"][str(uid)])
    
    m_info = chat_data["members"].get(str(uid), {"level": 0})
    if isinstance(m_info, dict):
        return int(m_info.get("level", 0))
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
# 3. ЛИЧНЫЕ СООБЩЕНИЯ (ПАНЕЛЬ УПРАВЛЕНИЯ В ЛС С 4 КНОПКАМИ)
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
        kb.add(Text("➕ Выдать доступ к рассылке"), color=KeyboardButtonColor.POSITIVE)
        kb.add(Text("📜 Логи рассылок"), color=KeyboardButtonColor.PRIMARY)
        kb.row()
        kb.add(Text("👥 Список админов рассылки"), color=KeyboardButtonColor.PRIMARY)
        kb.add(Text("📢 Начать рассылку по чатам"), color=KeyboardButtonColor.NEGATIVE)
    
    await message.answer(
        "👑 PRINCE RUSSIA — ULTIMATE ADMIN PANEL 👑\n"
        "Выберите нужное действие с помощью кнопок ниже:",
        keyboard=kb.get_json()
    )

@bot.on.private_message(text="➕ Выдать доступ к рассылке")
async def private_add_adm(message: Message):
    uid = message.from_id
    if uid != MAIN_OWNER_ID and uid not in db["broadcast_admins"]: return
    user_states[uid] = "wait_add_adm"
    await message.answer("✍️ Введите VK ID пользователя для выдачи доступа к рассылке:", keyboard=Keyboard(one_time=False, inline=True).add(Text("❌ Отмена"), color=KeyboardButtonColor.NEGATIVE).get_json())

@bot.on.private_message(text="📜 Логи рассылок")
async def private_view_logs(message: Message):
    uid = message.from_id
    if uid != MAIN_OWNER_ID and uid not in db["broadcast_admins"]: return
    broadcast_logs = [log for log in db["logs"] if "рассылка" in log.lower() or "рассылки" in log.lower()]
    recent = "\n".join(broadcast_logs[-10:]) if broadcast_logs else "📋 Логов рассылок пока нет."
    await message.answer(f"📜 **ПОСЛЕДНИЕ ЛОГИ РАССЫЛОК:**\n\n{recent}")

@bot.on.private_message(text="👥 Список админов рассылки")
async def private_view_admins(message: Message):
    uid = message.from_id
    if uid != MAIN_OWNER_ID and uid not in db["broadcast_admins"]: return
    admins_list = "\n".join([f"• [id{aid}|ID {aid}]" for aid in db["broadcast_admins"]])
    await message.answer(f"👥 **АДМИНИСТРАТОРЫ РАССЫЛКИ:**\n\n{admins_list}")

@bot.on.private_message(text="📢 Начать рассылку по чатам")
async def private_broadcast_start(message: Message):
    uid = message.from_id
    if uid != MAIN_OWNER_ID and uid not in db["broadcast_admins"]: return
    user_states[uid] = "wait_broadcast"
    await message.answer("✍️ Введите текст для глобальной рассылки по всем беседам:\n*(Сообщение будет отправлено с тегом `@all` от лица официального управления Prince Russia)*", keyboard=Keyboard(one_time=False, inline=True).add(Text("❌ Отмена"), color=KeyboardButtonColor.NEGATIVE).get_json())

@bot.on.private_message(text="🌐 Сайт проекта")
async def private_site(message: Message):
    await message.answer("🌐 Официальный сайт Prince Russia: https://site-prince-russia.samp.date/")

@bot.on.private_message()
async def private_handler(message: Message):
    uid = message.from_id
    text = message.text
    if not text: return
    state = user_states.get(uid)

    if state == "wait_add_adm" and (uid == MAIN_OWNER_ID or uid in db["broadcast_admins"]):
        del user_states[uid]
        clean = text.strip().replace("id", "")
        if clean.isdigit():
            tid = int(clean)
            if tid not in db["broadcast_admins"]:
                db["broadcast_admins"].append(tid)
                save_db(db)
                add_log(f"Админ ID {uid} выдал доступ к рассылке для ID {tid}")
                return await message.answer(f"✅ Пользователю [id{tid}|ID {tid}] успешно выдан доступ к рассылке.")
        return await message.answer("❌ Ошибка: Неверный VK ID.")

    if state == "wait_broadcast" and (uid == MAIN_OWNER_ID or uid in db["broadcast_admins"]):
        del user_states[uid]
        count = 0
        
        broadcast_text = (
            "📢 ВНИМАНИЕ! ОФИЦИАЛЬНОЕ СООБЩЕНИЕ ОТ PRINCE RUSSIA 📢\n\n"
            f"{text}\n\n"
            "────────────────────────\n"
            f"👤 Запустил рассылку: [id{uid}|Администрация]\n"
            "🌐 Сайт проекта: https://site-prince-russia.samp.date/\n"
            "@all"
        )
        
        for cid in db.get("global_chats", []):
            try:
                await bot.api.messages.send(peer_id=int(cid), message=broadcast_text, random_id=0)
                count += 1
            except Exception:
                pass
                
        add_log(f"Глобальная рассылка выполнена админом ID {uid}. Успешно отправлено в чатов: {count}")
        return await message.answer(f"🚀 **Рассылка завершена!**\n• Успешно доставлено в чатов: `{count}`")

    await message.answer("❌ Используйте удобные кнопки в меню или команды в беседах.")


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

    # АВТОМАТИЧЕСКИ ВЫДАЕМ 100 УРОВЕНЬ ВЛАДЕЛЬЦУ ЧАТА
    if chat_owner_id:
        o_str = str(chat_owner_id)
        current_data = chat_data["members"].get(o_str, {"nickname": "[Создатель]"})
        nick = current_data.get("nickname", "[Создатель]") if isinstance(current_data, dict) else "[Создатель]"
        chat_data["members"][o_str] = {"level": 100, "nickname": nick}
        save_db(db)

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
        return await message.answer("👑 ПАНЕЛЬ УПРАВЛЕНИЯ БЕСЕДОЙ", keyboard=kb.get_json())

    if clean_text in ["📜 правила", "правила"]:
        return await message.answer("📜 ПРАВИЛА:\n1. Без спама и рекламы.\n2. Уважение к администрации.\n3. За 3 варна — кик.")

    if clean_text in ["📋 роли", "/roles", "роли"]:
        r_list = "📋 ИЕРАРХИЯ ДОЛЖНОСТЕЙ ПРОЕКТА:\n"
        all_roles = {**db["global_role_names"], **chat_data["role_names"]}
        for lvl in sorted(all_roles.keys(), key=int, reverse=True):
            r_list += f"• {lvl} ➔ {all_roles[lvl]}\n"
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
            "📖 **СПИСОК КОМАНД PRINCE RUSSIA** 📖\n\n"
            "🌐 **Общие команды:**\n"
            "• `/stats` (или `/стата`) — ваш профиль или профиль игрока\n"
            "• `/roles` (или `роли`) — список ролей и иерархия\n"
            "• `/admins` — список администраторов в чате\n"
            "• `/leaders` — список лидеров организаций\n"
            "• `/bonus` — получить бонус проекта\n"
            "• `/ping` — проверка пинга и задержки API\n"
            "• `/status` — аптайм и статус сервера\n\n"
        )
        if user_lvl >= 45:
            help_msg += (
                "🛡 **Модерация (45+ lvl):**\n"
                "• `/mute [ид/ответ] [минуты]` — выдать мут\n"
                "• `/unmute [ид/ответ]` — снять мут\n"
                "• `/kick [ид/ответ]` — кикнуть из беседы\n"
                "• `/warn [ид/ответ] [причина]` — варн (3 варна = кик)\n"
                "• `/unwarn [ид/ответ]` — снять варн\n"
                "• `/pin` — закрепить сообщение (ответом)\n\n"
            )
        if user_lvl >= 55:
            help_msg += (
                "🚨 **Старшая модерация (55+ lvl):**\n"
                "• `/ban [ид/ответ] [причина]` — бан в беседе\n"
                "• `/unban [ид]` — разбан в беседе\n"
                "• `/banlist` — список забаненных\n\n"
            )
        if user_lvl >= 60:
            help_msg += (
                "👑 **Руководство / Лидеры (60+ lvl):**\n"
                "• `/setleader [ид/ответ] [Организация]` — назначить лидера\n"
                "• `/removeleader [ид/ответ]` — снять лидера\n"
                "• `/setnick [ид/ответ] [Ник]` — установить кастомный ник\n"
                "• `/delnick [ид/ответ]` — удалить кастомный ник\n\n"
            )
        if user_lvl >= 70:
            help_msg += (
                "⚡ **Администрация (70+ lvl):**\n"
                "• `/setadmin [ид] [уровень]` — выдать админку\n"
                "• `/выдатьроль [ид] [ур]` — выдать роль\n"
                "• `/снятьроль [ид]` — снять роль\n"
                "• `/logs` — просмотр последних логов\n\n"
            )
        if user_lvl >= 90:
            help_msg += (
                "🔥 **Высшая администрация (90+ lvl):**\n"
                "• `/gban [ид] [причина]` — глобальный бан\n"
                "• `/newrole [ур] [Название]` — создать роль в чате\n"
                "• `/delrole [ур]` — удалить роль\n"
            )
        return await message.answer(help_msg)

    elif cmd == "ping":
        start_t = time.time()
        msg_test = await message.answer("🏓 Проверка пинга...")
        end_t = time.time()
        ping_ms = int((end_t - start_t) * 1000)
        status_emoji = "🟢 Отлично" if ping_ms < 600 else "🟡 Нормально" if ping_ms < 1200 else "🔴 Высокий"
        return await message.edit(message_id=msg_test.conversation_message_id, message=f"🏓 **PONG!**\n• Задержка API VK: `{ping_ms} ms`\n• Соединение: {status_emoji}")

    elif cmd == "status":
        uptime_sec = int(time.time() - START_TIME)
        hours, remainder = divmod(uptime_sec, 3600)
        minutes, seconds = divmod(remainder, 60)
        chats_count = len(db.get("global_chats", []))
        return await message.answer(
            f"⚡ **СТАТУС СЕРВЕРА PRINCE RUSSIA**\n"
            f"• Аптайм: `{hours}ч {minutes}м {seconds}с`\n"
            f"• Активных чатов: `{chats_count}`\n"
            f"• База данных: `ONLINE (JSON)`\n"
            f"• Ядро: `v6.2 Ultimate Stable`"
        )

    elif cmd == "setnick":
        if user_lvl < 60: return await message.answer(f"❌ Требуется 60+ уровень (у вас: {user_lvl}).")
        orig_parts = raw_text.split()[1:]
        if not orig_parts: return await message.answer("❌ Формат: `/setnick [ответ/id] [Ник/Звание]`")
        
        target_id, remaining = await resolve_target(message, orig_parts)
        if not target_id: return await message.answer("❌ Укажите пользователя.")
        
        if message.reply_message:
            new_nick = " ".join(orig_parts)
        else:
            new_nick = " ".join(remaining)
            
        if not new_nick: return await message.answer("❌ Укажите текст никнейма.")

        t_str = str(target_id)
        if t_str not in chat_data["members"]:
            chat_data["members"][t_str] = {"level": 0, "nickname": new_nick}
        else:
            if isinstance(chat_data["members"][t_str], dict):
                chat_data["members"][t_str]["nickname"] = new_nick
            else:
                old_lvl = chat_data["members"][t_str]
                chat_data["members"][t_str] = {"level": old_lvl, "nickname": new_nick}
        save_db(db)
        return await message.answer(f"✅ Пользователю [id{target_id}|успешно установлен ник]: *{new_nick}*")

    elif cmd == "delnick":
        if user_lvl < 60: return await message.answer(f"❌ Требуется 60+ уровень (у вас: {user_lvl}).")
        tid, _ = await resolve_target(message, params)
        if not tid: return await message.answer("❌ Укажите пользователя.")
        t_str = str(tid)
        if t_str in chat_data["members"] and isinstance(chat_data["members"][t_str], dict):
            chat_data["members"][t_str]["nickname"] = ""
            save_db(db)
            return await message.answer(f"🟢 С [id{tid}|пользователя] снят кастомный ник.")
        return await message.answer("❌ Ник не найден.")

    elif cmd in ["stats", "стата", "профиль"]:
        target_id, _ = await resolve_target(message, params)
        if not target_id:
            target_id = message.from_id
            
        t_str = str(target_id)
        target_lvl = get_user_level_by_id(target_id, chat_data, chat_owner_id)
        all_r = {**db["global_role_names"], **chat_data["role_names"]}
        r_name = all_r.get(target_lvl, "Игрок")
        
        m_info = chat_data["members"].get(t_str, {})
        nick = m_info.get("nickname", "Не установлен") if isinstance(m_info, dict) else "Не установлен"
        warns = len(chat_data.get("warns", {}).get(t_str, []))
        
        return await message.answer(
            f"📊 **ПРОФИЛЬ ИГРОКА** [id{target_id}|Ссылка]:\n"
            f"• Кастомный ник: `{nick}`\n"
            f"• Должность: **{r_name}** `[{target_lvl} lvl]`\n"
            f"• Предупреждения: `{warns}/3`"
        )

    elif cmd == "mute":
        if user_lvl < 45: return await message.answer(f"❌ Недостаточно прав (нужен 45+, у вас: {user_lvl}).")
        tid, rem = await resolve_target(message, params)
        if not tid: return await message.answer("❌ Укажите цель.")
        mins = int(rem[0]) if rem and rem[0].isdigit() else 10
        chat_data["mutes"][str(tid)] = time.time() + (mins * 60)
        save_db(db)
        add_log(f"Мут: ID {tid} на {mins} мин от ID {message.from_id}")
        return await message.answer(f"🤫 Пользователю [id{tid}|выдан мут] на {mins} минут.")

    elif cmd in ["unmute", "unmite"]:
        if user_lvl < 45: return await message.answer(f"❌ Недостаточно прав (нужен 45+, у вас: {user_lvl}).")
        tid, _ = await resolve_target(message, params)
        if tid and str(tid) in chat_data["mutes"]:
            del chat_data["mutes"][str(tid)]
            save_db(db)
            return await message.answer(f"🔊 С [id{tid}|пользователя] снят мут.")
        return await message.answer("❌ Мут не найден.")

    elif cmd == "ban":
        if user_lvl < 55: return await message.answer(f"❌ Требуется 55+ уровень (у вас: {user_lvl}).")
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
        if user_lvl < 55: return await message.answer(f"❌ Требуется 55+ уровень (у вас: {user_lvl}).")
        tid, _ = await resolve_target(message, params)
        if tid and str(tid) in chat_data["bans"]:
            del chat_data["bans"][str(tid)]
            save_db(db)
            return await message.answer(f"🟢 [id{tid}|Пользователь] разбанен.")
        return await message.answer("❌ Его нет в банах.")

    elif cmd == "banlist":
        bans = chat_data.get("bans", {})
        if not bans: return await message.answer("📋 Бан-лист пуст.")
        msg = "📋 БАН-ЛИСТ БЕСЕДЫ:\n"
        for b_id, info in bans.items():
            msg += f"• [id{int(b_id)}|Игрок] ➔ Причина: {info.get('reason')}\n"
        return await message.answer(msg)

    elif cmd in ["chekban", "checkban"]:
        tid, _ = await resolve_target(message, params)
        if not tid: tid = message.from_id
        is_b = str(tid) in chat_data.get("bans", {}) or str(tid) in db["global_bans"]
        status = "Забанен 🔴" if is_b else "Чист 🟢"
        return await message.answer(f"🔍 Статус бана [id{tid}|пользователя]: {status}")

    elif cmd == "statschat":
        c_count = len(db.get("global_chats", []))
        m_count = len(chat_data.get("members", {}))
        return await message.answer(f"📈 СТАТИСТИКА БЕСЕДЫ:\n• Участников в базе: {m_count}\n• Всего активных чатов у бота: {c_count}")

    elif cmd == "kick":
        if user_lvl < 45: return await message.answer(f"❌ Недостаточно прав (нужен 45+, у вас: {user_lvl}).")
        tid, _ = await resolve_target(message, params)
        if not tid: return await message.answer("❌ Укажите цель.")
        try:
            await bot.api.messages.remove_chat_user(chat_id=message.chat_id, user_id=tid)
            return await message.answer(f"✅ [id{tid}|Кикнут].")
        except Exception as e:
            return await message.answer(f"❌ Ошибка: {e}")

    elif cmd == "warn":
        if user_lvl < 45: return await message.answer(f"❌ Недостаточно прав (нужен 45+, у вас: {user_lvl}).")
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
        if user_lvl < 45: return await message.answer(f"❌ Недостаточно прав (нужен 45+, у вас: {user_lvl}).")
        tid, _ = await resolve_target(message, params)
        if tid and str(tid) in chat_data["warns"] and chat_data["warns"][str(tid)]:
            chat_data["warns"][str(tid)].pop()
            save_db(db)
            return await message.answer(f"🟢 Снят варн с [id{tid}|пользователя].")
        return await message.answer("❌ Нет активных варнов.")

    elif cmd == "logs":
        if user_lvl < 70: return await message.answer(f"❌ Доступно с 70 уровня (у вас: {user_lvl}).")
        recent = "\n".join(db["logs"][-15:])
        return await message.answer(f"📜 ПОСЛЕДНИЕ ЛОГИ:\n{recent if recent else 'Пусто'}")

    elif cmd == "pin":
        if user_lvl < 45: return await message.answer(f"❌ Нужны права администратора (нужен 45+, у вас: {user_lvl}).")
        if not message.reply_message: return await message.answer("❌ Ответьте на сообщение, которое нужно закрепить.")
        try:
            await bot.api.messages.pin(peer_id=peer_id, conversation_message_id=message.reply_message.conversation_message_id)
            return await message.answer("📌 Сообщение успешно закреплено!")
        except Exception as e:
            # Улучшенный вывод: подсказка, если бот не админ беседы
            return await message.answer(
                f"❌ **Ошибка закрепления:**\n"
                f"ВКонтакте запрещает ботам закреплять сообщения, если у бота **нет прав администратора беседы**!\n"
                f"👉 *Назначьте бота администратором чата в настройках ВК.*"
            )

    elif cmd == "newrole":
        if user_lvl < 90: return await message.answer(f"❌ Требуется 90+ уровень (у вас: {user_lvl}).")
        if len(params) < 2: return await message.answer("❌ Формат: `/newrole [ур] [Название]`")
        lvl_s = params[0]
        if not lvl_s.isdigit(): return await message.answer("❌ Уровень должен быть числом.")
        r_name = " ".join(params[1:])
        chat_data["role_names"][int(lvl_s)] = r_name
        save_db(db)
        return await message.answer(f"✅ Создана роль {lvl_s} ➔ {r_name}")

    elif cmd == "delrole":
        if user_lvl < 90: return await message.answer(f"❌ Требуется 90+ уровень (у вас: {user_lvl}).")
        if not params or not params[0].isdigit(): return await message.answer("❌ Укажите уровень роли.")
        lvl_i = int(params[0])
        if lvl_i in chat_data["role_names"]:
            del chat_data["role_names"][lvl_i]
            save_db(db)
            return await message.answer(f"🗑 Роль {lvl_i} удалена.")
        return await message.answer("❌ Роль не найдена.")

    elif cmd in ["выдатьроль", "роль"]:
        if user_lvl < 70: return await message.answer(f"❌ Требуется 70+ уровень (у вас: {user_lvl}).")
        tid, rem = await resolve_target(message, params)
        if not tid: return await message.answer("❌ Укажите пользователя.")
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
        add_log(f"Выдача роли {lvl_val} для ID {tid} от ID {message.from_id}")
        return await message.answer(f"✅ Пользователю [id{tid}|успешно] установлена роль уровня {lvl_val}.")

    elif cmd in ["removerole", "снятьроль"]:
        if user_lvl < 70: return await message.answer(f"❌ Требуется 70+ уровень (у вас: {user_lvl}).")
        tid, _ = await resolve_target(message, params)
        if not tid: return await message.answer("❌ Укажите пользователя.")
        
        t_str = str(tid)
        current_data = chat_data["members"].get(t_str, {"nickname": ""})
        current_nick = current_data.get("nickname", "") if isinstance(current_data, dict) else ""
        
        chat_data["members"][t_str] = {"level": 0, "nickname": current_nick}
        save_db(db)
        return await message.answer(f"🟢 С [id{tid}|пользователя] сняты роли (0 уровень).")

    elif cmd == "grole":
        if user_lvl < 95: return await message.answer(f"❌ Требуется 95+ уровень (у вас: {user_lvl}).")
        tid, rem = await resolve_target(message, params)
        if not tid or not rem or not rem[0].isdigit(): return await message.answer("❌ Формат: `/grole [ID] [уровень]`")
        db["global_roles"][str(tid)] = int(rem[0])
        save_db(db)
        return await message.answer(f"🌐 Глобальная роль {rem[0]} выдана [id{tid}|пользователю].")

    elif cmd == "grr":
        if user_lvl < 95: return await message.answer(f"❌ Требуется 95+ уровень (у вас: {user_lvl}).")
        tid, _ = await resolve_target(message, params)
        if tid and str(tid) in db["global_roles"]:
            del db["global_roles"][str(tid)]
            save_db(db)
            return await message.answer(f"🟢 Глобальная роль снята с [id{tid}|пользователя].")
        return await message.answer("❌ У игрока нет глобальной роли.")

    elif cmd == "gban":
        if user_lvl < 90: return await message.answer(f"❌ Требуется 90+ уровень (у вас: {user_lvl}).")
        tid, rem = await resolve_target(message, params)
        if not tid: return await message.answer("❌ Укажите цель.")
        reason = " ".join(rem) if rem else "Нарушение проекта"
        db["global_bans"][str(tid)] = reason
        save_db(db)
        add_log(f"Глобальный бан: ID {tid}, причина: {reason}")
        return await message.answer(f"⛔ ГЛОБАЛЬНЫЙ БАН для [id{tid}|игрока]! Причина: {reason}")

    elif cmd == "admins":
        a_msg = "👑 АДМИНИСТРАЦИЯ В ЧАТЕ:\n"
        found = False
        for m_id, info in chat_data.get("members", {}).items():
            lvl = info.get("level", 0) if isinstance(info, dict) else info
            if lvl >= 45:
                all_r = {**db["global_role_names"], **chat_data["role_names"]}
                found = True
                a_msg += f"• [id{int(m_id)}|Админ] ➔ {all_r.get(lvl, 'Админ')} [{lvl} lvl]\n"
        return await message.answer(a_msg if found else "📋 Активных администраторов в чате нет.")

    elif cmd == "leaders":
        p_str = str(peer_id)
        chat_leads = db["leaders"].get(p_str, {})
        if not chat_leads: return await message.answer("📋 В этой беседе нет лидеров.")
        l_msg = "📋 СПИСОК ЛИДЕРОВ:\n"
        for l_id, org in chat_leads.items():
            l_msg += f"• [id{int(l_id)}|Лидер] ➔ Организация: {org}\n"
        return await message.answer(l_msg)

    elif cmd == "setleader":
        if user_lvl < 60: return await message.answer(f"❌ Требуется 60+ уровень (у вас: {user_lvl}).")
        tid, rem = await resolve_target(message, params)
        if not tid or not rem: return await message.answer("❌ Формат: `/setleader [ответ/id] [Организация]`")
        org_name = " ".join(rem)
        p_str = str(peer_id)
        if p_str not in db["leaders"]: db["leaders"][p_str] = {}
        db["leaders"][p_str][str(tid)] = org_name
        save_db(db)
        return await message.answer(f"👑 [id{tid}|Назначен лидером]: {org_name}")

    elif cmd == "removeleader":
        if user_lvl < 60: return await message.answer(f"❌ Требуется 60+ уровень (у вас: {user_lvl}).")
        tid, _ = await resolve_target(message, params)
        p_str = str(peer_id)
        if tid and p_str in db["leaders"] and str(tid) in db["leaders"][p_str]:
            del db["leaders"][p_str][str(tid)]
            save_db(db)
            return await message.answer(f"🟢 С [id{tid}|игрока] снят пост лидера.")
        return await message.answer("❌ Лидер не найден.")

    elif cmd == "setadmin":
        if user_lvl < 70: return await message.answer(f"❌ Требуется 70+ уровень (у вас: {user_lvl}).")
        tid, rem = await resolve_target(message, params)
        if not tid or not rem or not rem[0].isdigit(): return await message.answer("❌ Формат: `/setadmin [ID] [ур]`")
        lvl_v = int(rem[0])
        
        t_str = str(tid)
        current_data = chat_data["members"].get(t_str, {"nickname": ""})
        current_nick = current_data.get("nickname", "") if isinstance(current_data, dict) else ""
        
        chat_data["members"][t_str] = {"level": lvl_v, "nickname": current_nick}
        save_db(db)
        return await message.answer(f"✅ [id{tid}|Пользователю] выданы права администратора уровня {lvl_v}.")


if __name__ == "__main__":
    print("🚀 Prince Russia Chat Manager Core успешно запущен!")
    bot.run_forever()
