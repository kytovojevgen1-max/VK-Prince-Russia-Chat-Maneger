import os
import json
import time
from threading import Thread
from flask import Flask
from vkbottle.bot import Bot, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text

# =====================================================================
# 1. ВЕБ-СЕРВЕР ДЛЯ RENDER (24/7 ACTIVE)
# =====================================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Prince Russia Chat Manager Core: ACTIVE 24/7"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

Thread(target=run_flask, daemon=True).start()


# =====================================================================
# 2. НАСТРОЙКИ И БАЗЫ ДАННЫХ
# =====================================================================
TOKEN = "vk1.a.qGTN_rCK6d4Yg4ty8YkruE6DbovbX5lwzHcQcN6wQ15aACfSrhsyi5F7R9xip5mq03EeLvxI2gZwJSVvuWMv0eP7vv59FFJvPNYWpRI7R2nzXM0gbobnLpmRaI3yM751Cml4ZOPDcIc380c3hekN0jgZ3QeP76p9hn1Sw6kwK6mOCyomwB33nVy1uBGAbC0mDQpu5eiq2HlVDAKi4YjHYw"
bot = Bot(token=TOKEN)

MAIN_OWNER_ID = 897082738  # Твой VK ID (Владелец)

DB_FILE = "chat_manager_db.json"

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
        print(f"Ошибка сохранения базы: {e}")

db = load_db()
if "chats" not in db: db["chats"] = {}
if "global_chats" not in db: db["global_chats"] = []

user_states = {} # Состояния для ЛС (рассылка)

def get_chat_data(peer_id):
    p_str = str(peer_id)
    if p_str not in db["chats"]:
        db["chats"][p_str] = {
            "members": {}, 
            "bans": {},
            "role_names": {
                1: "Медиа",
                2: "Модератор",
                3: "Администратор",
                4: "Спец. Администратор",
                5: "Главный Администратор",
                6: "Руководитель",
                7: "Заместитель",
                8: "Разработчик"
            }
        }
    return db["chats"][p_str]

async def resolve_target(message: Message, args: list):
    """Ищет ID пользователя по ответу, ссылке, юзернейму или ID"""
    if message.reply_message:
        return message.reply_message.from_id, args # Если ответ, то все аргументы идут дальше (например для ника)
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
            
    # Если первый аргумент не распознался как юзер, но это часть текста (например, если забыли упомянуть через @)
    if not target_id:
        return None, args
        
    return target_id, remaining_args


# =====================================================================
# 3. ПАНЕЛЬ ВЛАДЕЛЬЦА В ЛИЧНЫХ СООБЩЕНИЯХ (РАССЫЛКА)
# =====================================================================

@bot.on.private_message(text=["/start", "Начать", "начать", "Меню", "меню", "🔙 Главное меню", "❌ Отмена"])
async def private_start(message: Message):
    uid = message.from_id
    if uid in user_states: del user_states[uid]
    is_owner = (uid == MAIN_OWNER_ID)
    
    keyboard = Keyboard(one_time=False, inline=False)
    keyboard.add(Text("🌐 Наш сайт"), color=KeyboardButtonColor.POSITIVE)
    if is_owner:
        keyboard.row()
        keyboard.add(Text("📢 Рассылка по всем чатам"), color=KeyboardButtonColor.NEGATIVE)
    
    await message.answer(
        "👑 **PRINCE RUSSIA — CHAT MANAGER** 👑\n"
        "Я управляю порядком и ролями в ваших беседах.\n"
        "Добавьте меня в беседу и выдайте права администратора!",
        keyboard=keyboard.get_json()
    )

@bot.on.private_message(text="📢 Рассылка по всем чатам")
async def private_broadcast_prompt(message: Message):
    if message.from_id != MAIN_OWNER_ID: return
    user_states[message.from_id] = "waiting_broadcast_text"
    
    kb = Keyboard(one_time=False, inline=True)
    kb.add(Text("❌ Отмена"), color=KeyboardButtonColor.NEGATIVE)
    
    await message.answer("✍️ Введите текст сообщения для **рассылки по всем чатам**:", keyboard=kb.get_json())

@bot.on.private_message(text=["🌐 Наш сайт", "Сайт"])
async def private_site(message: Message):
    await message.answer("🌐 Официальный сайт Prince Russia (скачать игру + бонус 25кк + 1000 BC): https://site-prince-russia.samp.date/")

@bot.on.private_message()
async def private_text_handler(message: Message):
    uid = message.from_id
    text = message.text
    if not text: return

    if uid in user_states and user_states.get(uid) == "waiting_broadcast_text" and uid == MAIN_OWNER_ID:
        del user_states[uid]
        count = 0
        for chat_id in db.get("global_chats", []):
            try:
                await bot.api.messages.send(peer_id=int(chat_id), message=f"📢 **ОФИЦИАЛЬНОЕ СООБЩЕНИЕ ПРОЕКТА:**\n\n{text}", random_id=0)
                count += 1
            except Exception:
                pass
        
        is_owner = (uid == MAIN_OWNER_ID)
        keyboard = Keyboard(one_time=False, inline=False)
        keyboard.add(Text("🌐 Наш сайт"), color=KeyboardButtonColor.POSITIVE)
        if is_owner:
            keyboard.row()
            keyboard.add(Text("📢 Рассылка по всем чатам"), color=KeyboardButtonColor.NEGATIVE)

        return await message.answer(f"✅ Рассылка успешно завершена! Отправлено в беседы: `{count}` шт.", keyboard=keyboard.get_json())
    
    await message.answer("❌ В личных сообщениях я не работаю как менеджер. Добавь меня в беседу!")


# =====================================================================
# 4. РАБОТА В БЕСЕДАХ (ЧАТАХ) — ТОЛЬКО ЧЕРЕЗ СЛЭШ (/)
# =====================================================================

@bot.on.chat_message()
async def chat_handler(message: Message):
    peer_id = message.peer_id
    
    if peer_id not in db["global_chats"]:
        db["global_chats"].append(peer_id)
        save_db(db)

    chat_data = get_chat_data(peer_id)

    if message.action and message.action.type == "chat_invite_user":
        try:
            bot_id = (await bot.api.users.get())[0].id
            if message.action.member_id == bot_id:
                kb = Keyboard(one_time=False, inline=True)
                kb.add(Text("🌐 Сайт"), color=KeyboardButtonColor.POSITIVE)
                kb.add(Text("📋 /help"), color=KeyboardButtonColor.PRIMARY)
                await message.answer(
                    "👋 Привет! Я **Чат-менеджер Prince Russia**.\n"
                    "⚠️ *Важно:* Выдайте мне **права администратора** и переведите доступ к переписке в режим **«Полный»**!\n"
                    "Все команды вводятся со слэша (`/`). Напишите `/help` для списка.",
                    keyboard=kb.get_json()
                )
        except Exception:
            pass

    text = message.text
    if not text: return
    
    # Очистка упоминания бота
    clean_text = text.lower()
    for mention in ["[club" + str(message.group_id) + "|@", "@club", "@public"]:
        if mention in clean_text:
            parts = clean_text.split(" ", 1)
            if len(parts) > 1:
                clean_text = parts[1].strip()

    # СТРОГАЯ ПРОВЕРКА: Команда должна начинаться со слэша "/"
    if not clean_text.startswith("/"):
        return

    args = clean_text[1:].split() # Убираем слеш и разбиваем на аргументы
    cmd = args[0] if args else ""
    params = args[1:] if len(args) > 1 else []

    if cmd in ["help", "помощь", "команды"]:
        help_text = (
            "🛠 **КОМАНДЫ ЧАТ-МЕНЕДЖЕРА:**\n"
            "───────────────────────────────\n"
            "👑 **Роли и ники:**\n"
            "• `/rnick` [@юз или ответ] [1-8] — выдать роль\n"
            "• `/snick` [@юз или ответ] [текст] — сменить ник\n"
            "• `/nlist` — список состава и ролей\n"
            "• `/setrolename` [1-8] [название] — переименовать ранг\n"
            "───────────────────────────────\n"
            "🛡 **Модерация:**\n"
            "• `/ban` [@юз или ответ] [срок] [причина]\n"
            "• `/unban` [@юз или ID]\n"
            "• `/kick` [@юз или ответ]\n"
            "• `/pin` / `/unpin` — закреп / открепи\n"
            "• `/site` — ссылка на проект"
        )
        await message.answer(help_text)

    elif cmd in ["site", "сайт", "ссылки"]:
        await message.answer("🌐 Официальный сайт Prince Russia (скачать игру + бонус 25кк + 1000 BC): https://site-prince-russia.samp.date/")

    # --- ВЫДАЧА РОЛИ (/rnick) ---
    elif cmd == "rnick":
        target_id, rem_args = await resolve_target(message, params)
        if not target_id:
            return await message.answer("❌ Укажите пользователя (@юзернейм, ID или ответьте на его сообщение)!")
        
        role_lvl = None
        for p in rem_args:
            if p.isdigit() and 1 <= int(p) <= 8:
                role_lvl = int(p)
                break
                
        if not role_lvl:
            return await message.answer("❌ Укажите уровень роли от 1 до 8 (например: `/rnick @durov 5`)!")
            
        if str(target_id) not in chat_data["members"]:
            chat_data["members"][str(target_id)] = {"level": role_lvl, "nickname": ""}
        else:
            chat_data["members"][str(target_id)]["level"] = role_lvl
        save_db(db)
        
        r_name = chat_data["role_names"].get(str(role_lvl), f"Ранг {role_lvl}")
        await message.answer(f"✅ Пользователю [id{target_id}|успешно] присвоена роль: **{r_name}** `[{role_lvl} lvl]`")

    elif cmd == "unrole":
        target_id, _ = await resolve_target(message, params)
        if not target_id:
            return await message.answer("❌ Укажите пользователя!")
            
        if str(target_id) in chat_data["members"]:
            chat_data["members"][str(target_id)]["level"] = 0
            save_db(db)
            await message.answer(f"✅ Роль с пользователя [id{target_id}|успешно] снята.")
        else:
            await message.answer("❌ У этого пользователя нет роли в данном чате.")

    # --- УСТАНОВКА НИКА (/snick) ---
    elif cmd == "snick":
        target_id, rem_args = await resolve_target(message, params)
        if not target_id:
            return await message.answer("❌ Укажите пользователя (@юзернейм или ответьте на его сообщение)!")
            
        if message.reply_message:
            new_nick = " ".join(params)
        else:
            new_nick = " ".join(rem_args)
            
        if not new_nick:
            return await message.answer("❌ Введите текст ника/префикса (например: `/snick @durov [Куратор]` или ответом на сообщение: `/snick [Куратор]`)!")

        if str(target_id) not in chat_data["members"]:
            chat_data["members"][str(target_id)] = {"level": 0, "nickname": new_nick}
        else:
            chat_data["members"][str(target_id)]["nickname"] = new_nick
        save_db(db)
        
        await message.answer(f"✅ Пользователю [id{target_id}|установлен] ник/префикс: **{new_nick}**")

    # --- ПЕРЕИМЕНОВАНИЕ РАНГОВ ---
    elif cmd == "setrolename":
        if len(params) < 2:
            return await message.answer("❌ Формат: `/setrolename [1-8] [Название]`")
        lvl_str = params[0]
        if not lvl_str.isdigit() or not (1 <= int(lvl_str) <= 8):
            return await message.answer("❌ Уровень должен быть от 1 до 8!")
        
        new_role_name = " ".join(params[1:])
        chat_data["role_names"][lvl_str] = new_role_name
        save_db(db)
        await message.answer(f"✅ Название роли **{lvl_str} уровня** изменено на: *{new_role_name}*")

    # --- СПИСОК НИКОВ (/nlist) ---
    elif cmd in ["nlist", "листников", "состав", "роли"]:
        members = chat_data.get("members", {})
        if not members:
            return await message.answer("📋 В данном чате пока нет выданных ролей или ников.")
            
        msg = "📋 **СОСТАВ И РОЛИ В ЭТОМ ЧАТЕ:**\n───────────────────────────────\n"
        for m_id, info in members.items():
            if isinstance(info, int):
                lvl = info
                nick = ""
            else:
                lvl = info.get("level", 0)
                nick = info.get("nickname", "")
                
            if lvl == 0 and not nick: continue
            
            m_int = int(m_id)
            r_name = chat_data["role_names"].get(str(lvl), f"Ранг {lvl}") if lvl > 0 else "Игрок"
            prefix = f"{nick} " if nick else ""
            
            msg += f"• {prefix}[id{m_int}|Игрок] ➔ **{r_name}** `[{lvl} lvl]`\n"
            
        await message.answer(msg)

    # --- МОДЕРАЦИЯ ---
    elif cmd == "ban":
        target_id, rem_args = await resolve_target(message, params)
        if not target_id:
            return await message.answer("❌ Укажите кого забанить!")
            
        reason_args = [p for p in rem_args if not (p.isdigit() and int(p) <= 8)]
        term = "Навсегда"
        reason = "Не указана"
        if reason_args:
            term = reason_args[0]
            if len(reason_args) > 1:
                reason = " ".join(reason_args[1:])
                
        chat_data["bans"][str(target_id)] = {"reason": reason, "term": term}
        save_db(db)
        
        try:
            await bot.api.messages.remove_chat_user(chat_id=message.chat_id, user_id=target_id)
        except Exception:
            pass
            
        await message.answer(f"🚫 Пользователь [id{target_id}|забанен в чате]!\n📌 Причина: {reason}\n⏳ Срок: {term}")

    elif cmd == "unban":
        target_id, _ = await resolve_target(message, params)
        if not target_id:
            return await message.answer("❌ Укажите кого разбанить!")
            
        if str(target_id) in chat_data["bans"]:
            del chat_data["bans"][str(target_id)]
            save_db(db)
            await message.answer(f"🟢 Пользователь [id{target_id}|разбанен].")
        else:
            await message.answer("❌ Его нет в бан-листе этого чата.")

    elif cmd == "kick":
        target_id, _ = await resolve_target(message, params)
        if not target_id:
            return await message.answer("❌ Укажите нарушителя (через @, ID или ответом на его сообщение)!")
        try:
            await bot.api.messages.remove_chat_user(chat_id=message.chat_id, user_id=target_id)
            await message.answer(f"✅ Пользователь [id{target_id}|кикнут] из беседы.")
        except Exception as e:
            await message.answer(f"❌ Ошибка (проверьте права админа у бота): {e}")

    elif cmd == "pin":
        if not message.reply_message:
            return await message.answer("❌ Ответьте на сообщение, которое нужно закрепить!")
        try:
            await bot.api.messages.pin(peer_id=message.peer_id, conversation_message_id=message.reply_message.conversation_message_id)
            await message.answer("📌 Сообщение закреплено!")
        except Exception as e:
            await message.answer(f"❌ Ошибка закрепления: {e}")

    elif cmd == "unpin":
        try:
            await bot.api.messages.delete_pin(peer_id=message.peer_id)
            await message.answer("📌 Закрепление снято.")
        except Exception as e:
            await message.answer(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    print("🚀 Локальный Чат-Менеджер Prince Russia запущен и работает по слэшам!")
    bot.run_forever()
