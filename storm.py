import telebot
import sqlite3
import re
import time
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
import random

# Replace with your actual API token
API_TOKEN = '7594782829:AAFM9zaEblSxSnMWrVLyjsmXBieU_pfEXxQ'

# ID чата, в котором бот должен работать
TARGET_CHAT_ID = -1002208229823  # Замените на ваш ID чата

# ID пользователя, который может выдавать админки
SUPER_ADMIN_ID = 1971188182  # Замените на нужный ID

bot = telebot.TeleBot(API_TOKEN)

# Initialize the database
conn = sqlite3.connect('rules.db', check_same_thread=False)
cursor = conn.cursor()

# Create tables
cursor.execute('''CREATE TABLE IF NOT EXISTS rules (
                  id INTEGER PRIMARY KEY,
                  text TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS activity (
                  user_id INTEGER PRIMARY KEY,
                  message_count INTEGER DEFAULT 0,
                  last_message_time INTEGER DEFAULT 0,
                  last_bounty INTEGER DEFAULT 0)''')  # Добавлено поле для отслеживания последнего использования команды //благо
conn.commit()


@bot.message_handler(func=lambda message: message.chat.id != TARGET_CHAT_ID)
def ignore_other_chats(message):
    # Игнорировать сообщения из других чатов
    return


@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    for new_member in message.new_chat_members:
        # Создаем инлайн-клавиатуру
        keyboard = InlineKeyboardMarkup()
        rules_button = InlineKeyboardButton("Правила", callback_data="правила нахуй")
        keyboard.add(rules_button)

        # Отправляем приветственное сообщение с упоминанием нового участника
        bot.send_message(
            message.chat.id,
            f"@{new_member.username if new_member.username else new_member.first_name}, Привет!",
            reply_markup=keyboard
        )


# Обработчик нажатия кнопки "Правила"
@bot.callback_query_handler(func=lambda call: call.data == "правила нахуй")
def send_rules(call):
    cursor.execute("SELECT id, text FROM rules ORDER BY id")
    rules = cursor.fetchall()
    if rules:
        response = "Правила чата:\n" + "\n".join([f"{rule[0]}. {rule[1]}" for rule in rules])
    else:
        response = "Правила чата не установлены"

    bot.send_message(call.message.chat.id, response)

@bot.message_handler(func=lambda message: message.chat.id == TARGET_CHAT_ID and message.text.startswith('//правила'))
def show_rules(message):
    cursor.execute("SELECT id, text FROM rules ORDER BY id")
    rules = cursor.fetchall()
    if rules:
        response = "Правила чата:\n" + "\n".join([f"{rule[0]}. {rule[1]}" for rule in rules])
    else:
        response = "правил нету ура"
    bot.send_message(message.chat.id, response)

def is_admin(user_id):
    cursor.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None or user_id == SUPER_ADMIN_ID

@bot.message_handler(func=lambda message: message.chat.id == TARGET_CHAT_ID and message.text.lower() == 'админы')
def show_admins(message):
    cursor.execute("SELECT user_id FROM admins")
    admins = cursor.fetchall()
    if not admins:
        bot.send_message(message.chat.id, "анархия")
        return

    admin_list = []
    for admin in admins:
        user_id = admin[0]
        try:
            user = bot.get_chat_member(TARGET_CHAT_ID, user_id).user
            username = user.username or "лох без юза"
            full_name = user.first_name + (f" {user.last_name}" if user.last_name else "")
            admin_list.append(f"{full_name} (@{username}) - {user_id}")
        except:
            admin_list.append(f"Неизвестный пользователь - {user_id}")

    response = "Администраторы чата:\n" + "\n".join(admin_list)
    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['+админ'])
def add_admin(message):
    user_id = message.from_user.id
    if user_id != SUPER_ADMIN_ID:
        bot.send_message(message.chat.id, "нехачу")
        return

    try:
        parts = message.text.split()
        if len(parts) == 2:
            username = parts[1].strip('@')
            user_info = bot.get_chat_member(TARGET_CHAT_ID, username)
            new_admin_id = user_info.user.id
            cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (new_admin_id,))
            conn.commit()
            bot.send_message(message.chat.id, f"раб системы {username} (ID: {new_admin_id}) добавлен в администраторы")
        else:
            bot.send_message(message.chat.id, "нехачу")
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка: {str(e)}")

@bot.message_handler(func=lambda message: message.chat.id == TARGET_CHAT_ID and message.text.startswith('+правило'))
def add_rule(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.send_message(message.chat.id, "только рабы системы могут изменять")
        return

    try:
        rule_text = re.match(r'^\+правило\s+(.+)', message.text, re.DOTALL)
        if rule_text:
            rule_text = rule_text.group(1).strip()
            if rule_text:
                cursor.execute("INSERT INTO rules (text) VALUES (?)", (rule_text,))
                # Перенумерация оставшихся правил после добавления
                cursor.execute("SELECT id FROM rules ORDER BY id")
                remaining_rules = cursor.fetchall()
                for new_id, (old_id,) in enumerate(remaining_rules, start=1):
                    cursor.execute("UPDATE rules SET id = ? WHERE id = ?", (new_id, old_id))
                conn.commit()
                bot.send_message(message.chat.id, "Правило добавлено")
            else:
                bot.send_message(message.chat.id, "Пожалуйста, сходите нахуй")
        else:
            bot.send_message(message.chat.id, "Пожалуйста, еще раз")
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка: {str(e)}")

@bot.message_handler(func=lambda message: message.chat.id == TARGET_CHAT_ID and message.text.startswith('-правило'))
def delete_rule(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.send_message(message.chat.id, "только рабы системы могут их удалять")
        return

    try:
        parts = message.text.split()
        if len(parts) == 2 and parts[1].isdigit():
            rule_id = int(parts[1])
            cursor.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
            conn.commit()

            # Перенумерация оставшихся правил после удаления
            cursor.execute("SELECT id FROM rules ORDER BY id")
            remaining_rules = cursor.fetchall()
            for new_id, (old_id,) in enumerate(remaining_rules, start=1):
                cursor.execute("UPDATE rules SET id = ? WHERE id = ?", (new_id, old_id))
            conn.commit()

            bot.reply_to(message, "Правило удалено")
        elif len(parts) == 2 and parts[1] == 'все':
            cursor.execute("DELETE FROM rules")
            conn.commit()
            bot.send_message(message.chat.id, "Все правила удалены плаке плаке...")
        else:
            bot.send_message(message.chat.id, "Пожалуйста, научитесь пользоваться командами")
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка: {str(e)}")


@bot.message_handler(func=lambda message: message.chat.id == TARGET_CHAT_ID and message.text.lower().startswith('активность'))
def show_activity(message):
    cursor.execute("SELECT user_id, message_count FROM activity")
    all_users_activity = cursor.fetchall()
    if not all_users_activity:
        bot.reply_to(message, "Нет активности пользователей.")
        return
    # Сортировка по количеству сообщений
    all_users_activity.sort(key=lambda x: x[1], reverse=True)
    response = "📊 Статистика по общительным пользователям:\n"
    total_messages = 0
    for idx, (user_id, count) in enumerate(all_users_activity[:5], start=1):
        try:
            user = bot.get_chat_member(TARGET_CHAT_ID, user_id).user
            username = user.username or "без юзернейма"
            full_name = user.first_name + (f" {user.last_name}" if user.last_name else "")
            response += f"{idx}. {full_name} - {count} сообщений\n"
            total_messages += count
        except Exception as e:
            print(f"Ошибка при получении информации о пользователе: {e}")
            continue  # Игнорируем пользователей, если они не найдены
    response += f"\nВсего сообщений: {total_messages}"
    # Отправляем ответ без использования Markdown
    bot.reply_to(message, response)  # Убрали parse_mode

@bot.message_handler(func=lambda message: message.chat.id == TARGET_CHAT_ID and message.text)
def track_activity(message):
    user_id = message.from_user.id
    current_time = int(time.time())
    # Увеличиваем счетчик активности
    cursor.execute(
        "INSERT INTO activity (user_id, message_count, last_message_time) VALUES (?, 1, ?) ON CONFLICT(user_id) DO UPDATE SET message_count = message_count + 1, last_message_time = ?",
        (user_id, current_time, current_time))
    conn.commit()

bot.polling()
