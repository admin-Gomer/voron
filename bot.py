
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
import os
import json

api_id = 28981340            # Замените на свой
api_hash = "8dbce7bed757e9e1ddfedad1e9c680d2" # Замените на свой
bot_token = "8503713213:AAFw2fj83nqOTIGz6XBEfYfNYs0P3DvKNxY"  # Замените на токен вашего бота
bot_username = "M_FileBot"    # Имя вашего бота (без @)

# Укажите свой user_id и ник
ADMIN_USER_ID = 1129009422  # Замените на ваш user_id
SIGNATURE = "@ANDRO_FILE"  # Замените на ваш ник или имя

app = Client(
    "file_bot",
    api_id=api_id,
    api_hash=api_hash,
    bot_token=bot_token,
    parse_mode=ParseMode.HTML
)

# Файл для хранения базы данных
DB_FILE = "file_db.json"

# Функция для загрузки базы данных из JSON файла
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# Функция для сохранения базы данных в JSON файл
def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f)

# Проверка пользователя
def check_admin(user_id):
    return user_id == ADMIN_USER_ID

# Обработчик новых сообщений с документами
@app.on_message(filters.document & filters.private)
def handle_apk(client, message):
    if not check_admin(message.from_user.id):
        return  # Игнорируем запросы от других пользователей

    if (
        message.document 
        and message.document.file_name 
        and message.document.file_name.lower().endswith('.apk')
    ):
        try:
            db = load_db()
            counter = str(len(db) + 1)
            file_id = message.document.file_id
            db[counter] = {
                "file_id": file_id,
                "file_name": message.document.file_name
            }
            save_db(db)

            botlink = f"http://t.me/{bot_username}?start={counter}"
            markup = f'<a href="{botlink}">Открыть файл №{counter} в боте</a>'
            client.send_message(
                message.chat.id,
                markup,
                reply_to_message_id=message.id
            )
        except Exception as e:
            client.send_message(
                message.chat.id,
                f"Ошибка: {e}",
                reply_to_message_id=message.id
            )
    else:
        client.send_message(
            message.chat.id,
            "Это не .apk файл. Пришли .apk документ!",
            reply_to_message_id=message.id
        )

# Обработчик команды /list
@app.on_message(filters.command("list") & filters.private)
def list_files(client, message):
    if not check_admin(message.from_user.id):
        return  # Игнорируем запросы от других пользователей

    db = load_db()
    if db:
        response = "Список загруженных файлов:\n"
        for key, value in db.items():
            response += f"№{key}: {value['file_name']}\n"
        client.send_message(message.chat.id, response)
    else:
        message.reply("Нет загруженных файлов.")

# Обработчик команды /info
@app.on_message(filters.command("info") & filters.private)
def file_info(client, message):
    if not check_admin(message.from_user.id):
        return  # Игнорируем запросы от других пользователей

    args = message.text.strip().split()
    if len(args) == 2 and args[1].isdigit():
        db = load_db()
        file_key = args[1]
        entry = db.get(file_key)
        if entry:
            client.send_message(
                message.chat.id,
                f"Файл: {entry['file_name']}\nID: {entry['file_id']}"
            )
        else:
            message.reply("Файл не найден.")
    else:
        message.reply("Используйте: /info N, где N - номер файла.")

# Обработчик команды /clear
@app.on_message(filters.command("clear") & filters.private)
def clear_files(client, message):
    if not check_admin(message.from_user.id):
        return  # Игнорируем запросы от других пользователей

    db = load_db()
    if db:
        os.remove(DB_FILE)
        client.send_message(message.chat.id, "Все файлы были успешно удалены.")
    else:
        message.reply("База данных уже пуста.")

# Обработчик команды /start
@app.on_message(filters.command("start") & filters.private)
def send_file(client, message):
    if not check_admin(message.from_user.id):
        return  # Игнорируем запросы от других пользователей

    args = message.text.strip().split()
    if len(args) == 2 and args[1].isdigit():
        db = load_db()
        file_key = args[1]
        entry = db.get(file_key)
        if entry and "file_id" in entry:
            # Добавляем подпись к отправляемому файлу
            caption = f"Ваш файл: {entry.get('file_name', 'File')}\nПодпись: {SIGNATURE}"
            client.send_document(
                chat_id=message.chat.id,
                document=entry["file_id"],
                caption=caption
            )
        else:
            message.reply("Файл не найден.")
    else:
        # Получаем имя пользователя
        username = message.from_user.username if message.from_user.username else message.from_user.first_name
        message.reply(f"Привет, {username}! Ну что, продолжим?")

print("БОТ ЗАПУЩЕН!")
app.run()
