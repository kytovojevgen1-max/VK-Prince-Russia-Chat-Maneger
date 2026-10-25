import os
import json
import time
from vkbottle.bot import Bot, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text

# =====================================================================
# НАСТРОЙКИ ЧАТ-МЕНЕДЖЕРА
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
if "chats" not in db: db["chats"] = {}         # {str(peer_id): {"members": {}, "bans": {}}}
if "global_chats" not in db: db["global_chats"] = [] # Список всех чатов для рассылки из ЛС

def get_chat_data(peer_id):
    p_str = str(peer_id)
    if p_str not in db["chats"]:
        db["chats"][p_str] = {"members": {}, "bans": {}}
    return db["chats"][p_str]

async def resolve_target(message: Message, args: list):
    """Ищет ID пользователя по ответу на сообщение, юзернейму или ID"""
    if message.reply_message:
        return message.reply_message.from_id
    if not args:
        return None
    
    identifier = args[0].strip().replace("@", "").replace("vk.com/", "").replace("id", "")
    if identifier.isdigit():
        return int(identifier)
        
    # Ищем по юзернейму среди участников чата или через API
    try:
        user_info = await bot.api.users.get(user_ids=[identifier])
        if user_info:
            return user_info[0].id
    except Exception:
        pass
    return None


# =====================================================================
# 1. ПАНЕЛЬ ВЛАДЕЛЬЦА В ЛИЧНЫХ СООБЩЕНИЯХ
# =====================================================================

@bot.on.private_message(text=["/start", "Начать", "начать", "Меню", "меню", "🔙 Главное меню", "❌ Отмена"])
async def private_start(message: Message):
    uid = message.from_id
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
    # Состояние через временный файл или глобальную переменную можно зафиксировать
    await message.answer("✍️ Введите команду в формате:\n`/broadcast ваш_текст_рассылки`")

@bot.on.private_message(text=lambda text: text and text.startswith("/broadcast"))
async def private_broadcast_send(message: Message):
    if message.from_id != MAIN_OWNER_ID: return
    text = message.text.replace("/broadcast", "").strip()
    if not text: return
    
    count = 0
    for chat_id in db.get("global_chats", []):
        try:
            await bot.api.messages.send(peer_id=int(chat_id), message=f"📢 **ОФИЦИАЛЬНОЕ СООБЩЕНИЕ ПРОЕКТА:**\n\n{text}", random_id=0)
            count += 1
        except Exception:
            pass
    await message.answer(f"✅ Рассылка завершена! Отправлено в беседы: `{count}` шт.")

@bot.on.private_message(text=["🌐 Наш сайт", "Сайт"])
async def private_site(message: Message):
    await message.answer("🌐 Официальный сайт Prince Russia (скачать игру + бонус 25кк + 1000 BC): https://site-prince-russia.samp.date/")


# =====================================================================
# 2. РАБОТА В БЕСЕДАХ (ЧАТАХ)
# =====================================================================

@bot.on.chat_message()
async def chat_handler(message: Message):
    peer_id = message.peer_id
    p_str = str(peer_id)
    
    # Сохраняем чат в общую базу для рассылок из ЛС
    if peer_id not in db["global_chats"]:
        db["global_chats"].append(peer_id)
        save_db(db)

    chat_data = get_chat_data(peer_id)

    # Если бота добавили в беседу
    if message.action and message.action.type == "chat_invite_user":
        try:
            bot_id = (await bot.api.users.get())[0].id
            if message.action.member_id == bot_id:
                kb = Keyboard(one_time=False, inline=True)
                kb.add(Text("🌐 Сайт"), color=KeyboardButtonColor.POSITIVE)
                kb.add(Text("📋 Команды"), color=KeyboardButtonColor.PRIMARY)
                await message.answer(
                    "👋 Привет! Я **Чат-менеджер Prince Russia**.\n"
                    "⚠️ *Важно:* Выдайте мне **права администратора** и переведите доступ к переписке в режим **«Полный»**, чтобы я мог управлять ролями, банить и кикать нарушителей!",
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

    args = clean_text.split()
    cmd = args[0] if args else ""
    params = args[1:] if len(args) > 1 else []

    # --- КОМАНДЫ ЧАТА ---
    
    if cmd in ["/help", "!хелп", "команды", "📋 команды"]:
        help_text = (
            "🛠 **КОМАНДЫ ЧАТ-МЕНЕДЖЕРА:**\n"
            "───────────────────────────────\n"
            "👑 **Управление ролями (1-8):**\n"
            "• `/role` [@юз или ответ] [1-8] — выдать роль\n"
            "• `/unrole` [@юз или ответ] — снять роль\n"
            "• `лист ников` / `состав` — список ролей в чате\n"
            "───────────────────────────────\n"
            "🛡 **Модерация чата:**\n"
            "• `/ban` [@юз или ответ] [срок] [причина] — забанить\n"
            "• `/unban` [@юз или ID] — разбанить\n"
            "• `/kick` [@юз или ответ] — кикнуть\n"
            "• `/pin` [ответ] — закрепить | `/unpin` — открепить\n"
            "• `сайт` — ссылка на проект"
        )
        await message.answer(help_text)

    elif cmd in ["сайт", "🌐 сайт", "ссылки"]:
        await message.answer("🌐 Официальный сайт Prince Russia (скачать игру + бонус 25кк + 1000 BC): https://site-prince-russia.samp.date/")

    # --- ВЫДАЧА И СНЯТИЕ РОЛИ (1-8) ---
    elif cmd in ["/role", "роль"]:
        target_id = await resolve_target(message, params)
        if not target_id:
            return await message.answer("❌ Укажите пользователя (@юзернейм, ID или ответьте на его сообщение)!")
        
        # Ищем цифру роли (1-8) в аргументах
        role_lvl = None
        for p in params:
            if p.isdigit() and 1 <= int(p) <= 8:
                role_lvl = int(p)
                break
                
        if not role_lvl:
            return await message.answer("❌ Укажите уровень роли от 1 до 8 (например: `/role @durov 5`)!")
            
        chat_data["members"][str(target_id)] = role_lvl
        save_db(db)
        
        try:
            u_info = await bot.api.users.get(user_ids=[target_id])
            u_name = f"{u_info[0].first_name} {u_info[0].last_name}" if u_info else f"id{target_id}"
        except Exception:
            u_name = f"id{target_id}"
            
        await message.answer(f"✅ Пользователю [id{target_id}|{u_name}] успешно присвоена роль **{role_lvl} уровня**!")

    elif cmd in ["/unrole", "снять роль"]:
        target_id = await resolve_target(message, params)
        if not target_id:
            return await message.answer("❌ Укажите пользователя!")
            
        if str(target_id) in chat_data["members"]:
            del chat_data["members"][str(target_id)]
            save_db(db)
            await message.answer(f"✅ С пользователя [id{target_id}|ID {target_id}] снята роль.")
        else:
            await message.answer("❌ У этого пользователя нет роли в данном чате.")

    elif cmd in ["лист ников", "состав", "роли"]:
        members = chat_data.get("members", {})
        if not members:
            return await message.answer("📋 В данном чате пока нет выданных ролей (1-8).")
            
        msg = "📋 **СПИСОК РОЛЕЙ В ЭТОМ ЧАТЕ:**\n───────────────────────────────\n"
        for m_id, lvl in members.items():
            m_int = int(m_id)
            try:
                u_info = await bot.api.users.get(user_ids=[m_int])
                m_name = f"{u_info[0].first_name} {u_info[0].last_name}" if u_info else f"id{m_int}"
            except Exception:
                m_name = f"id{m_int}"
            msg += f"• [id{m_int}|{m_name}] ➔ **Ранг {lvl}**\n"
        await message.answer(msg)

    # --- МОДЕРАЦИЯ (БАН, РАЗБАН, КИК) ---
    elif cmd in ["/ban", "бан"]:
        target_id = await resolve_target(message, params)
        if not target_id:
            return await message.answer("❌ Укажите кого забанить!")
            
        # Формируем причину и срок из оставшихся аргументов
        reason_args = [p for p in params if not (p.isdigit() and int(p) <= 8) and not p.replace("@","").isdigit()]
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

    elif cmd in ["/unban", "разбан"]:
        target_id = await resolve_target(message, params)
        if not target_id:
            return await message.answer("❌ Укажите кого разбанить!")
            
        if str(target_id) in chat_data["bans"]:
            del chat_data["bans"][str(target_id)]
            save_db(db)
            await message.answer(f"🟢 Пользователь [id{target_id}|ID {target_id}] разбанен в чате.")
        else:
            await message.answer("❌ Его нет в бан-листе этого чата.")

    elif cmd in ["/kick", "кик"]:
        if not message.reply_message and not params:
            return await message.answer("❌ Ответьте на сообщение нарушителя или укажите его юз!")
        target_id = await resolve_target(message, params)
        if not target_id:
            return await message.answer("❌ Пользователь не найден!")
        try:
            await bot.api.messages.remove_chat_user(chat_id=message.chat_id, user_id=target_id)
            await message.answer("✅ Нарушитель кикнут из беседы.")
        except Exception as e:
            await message.answer(f"❌ Ошибка (проверьте права админа у бота): {e}")

    elif cmd in ["/pin", "закрепить"]:
        if not message.reply_message:
            return await message.answer("❌ Ответьте на сообщение, которое нужно закрепить!")
        try:
            await bot.api.messages.pin(peer_id=message.peer_id, conversation_message_id=message.reply_message.conversation_message_id)
            await message.answer("📌 Сообщение закреплено!")
        except Exception as e:
            await message.answer(f"❌ Ошибка закрепления: {e}")

    elif cmd in ["/unpin", "открепить"]:
        try:
            await bot.api.messages.delete_pin(peer_id=message.peer_id)
            await message.answer("📌 Закрепление снято.")
        except Exception as e:
            await message.answer(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    print("🚀 Локальный Чат-Менеджер Prince Russia запущен!")
    bot.run_forever()
