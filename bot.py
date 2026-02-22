import os
import json
from uuid import uuid4
from PIL import Image, ImageDraw, ImageFont, ImageOps
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, CallbackQueryHandler, ContextTypes
)
import asyncio
import shutil

# ======= НАСТРОЙКИ =======
TELEGRAM_TOKEN = "8578375390:AAEV0xto8D_QB6umLxVtuNsUrx8Pjhk9Qv0"
ADMIN_ID = 1129009422         # Ваш user id (число)
CHANNEL_ID = -1002329753497 # id канала/чата для публикации постов
CHANNEL_USERNAME = "@ANDRO_FILE"
CHANNEL_LINK = "https://t.me/ANDRO_FILE"
FILE_DB = "file_db.json"
SIGNATURE = "@ANDRO_FILE"
MEDIA_DIR = "admin_media"
WATERMARK_DIR = "watermarks"

# Пути к аватаркам и шрифтам
CUSTOM_AVATAR = os.path.join(WATERMARK_DIR, "custom_avatar.png")
DEFAULT_AVATAR = os.path.join(WATERMARK_DIR, "default_avatar.png")
FONT_DIR = "fonts"
os.makedirs(FONT_DIR, exist_ok=True)

os.makedirs(MEDIA_DIR, exist_ok=True)
os.makedirs(WATERMARK_DIR, exist_ok=True)
# =========================

# ------ Состояния админки ------
(ADD_MEDIA, ADD_DESC, ADD_BTN_LABEL, ADD_BTN_URL, 
 ADMIN_PANEL, BTN_EDIT_LABEL, ADD_WATERMARK, 
 EDIT_TITLE, EDIT_DESC, EDIT_BUTTONS) = range(10)

# ------ БЛОК FILEBOT ------
def load_db():
    if not os.path.exists(FILE_DB):
        with open(FILE_DB, "w", encoding="utf-8") as f:
            json.dump({"files": {}, "last_id": 0}, f)
        return {"files": {}, "last_id": 0}
    
    try:
        with open(FILE_DB, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "files" not in data:
                old_files = data
                max_id = 0
                for key, value in old_files.items():
                    if key.isdigit() and int(key) > max_id:
                        max_id = int(key)
                data = {"files": old_files, "last_id": max_id}
                save_db(data)
            return data
    except:
        with open(FILE_DB, "w", encoding="utf-8") as f:
            json.dump({"files": {}, "last_id": 0}, f)
        return {"files": {}, "last_id": 0}

def save_db(db):
    with open(FILE_DB, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

# ========== КОМАНДЫ ==========
async def del_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /del для удаления файла"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Этот бот приватный.")
        return
    
    args = context.args
    if len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text(
            "❌ Используйте: /del ID\n"
            "Например: /del 5"
        )
        return
    
    file_id = args[0]
    db = load_db()
    
    if file_id not in db["files"]:
        await update.message.reply_text("❌ Файл с таким ID не найден.")
        return
    
    file_name = db["files"][file_id]["file_name"]
    del db["files"][file_id]
    
    # Обновляем last_id
    if db["files"]:
        db["last_id"] = max(int(id) for id in db["files"].keys())
    else:
        db["last_id"] = 0
    
    save_db(db)
    
    await update.message.reply_text(f"✅ Файл ID {file_id} ({file_name}) удалён.")

async def clear_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /clear для удаления всех файлов"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Этот бот приватный.")
        return
    
    # Запрашиваем подтверждение
    keyboard = [[
        InlineKeyboardButton("✅ Да, очистить всё", callback_data='clear_confirm'),
        InlineKeyboardButton("❌ Нет, отмена", callback_data='clear_cancel')
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ <b>ВНИМАНИЕ!</b>\n\n"
        "Вы уверены, что хотите удалить ВСЕ файлы?\n"
        "Это действие нельзя отменить!",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def clear_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик подтверждения очистки"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'clear_confirm':
        db = load_db()
        
        # Создаем резервную копию
        if db["files"]:
            backup_file = f"file_db_backup_{len(db['files'])}_files.json"
            shutil.copy2(FILE_DB, backup_file)
        
        # Очищаем базу
        new_db = {"files": {}, "last_id": 0}
        save_db(new_db)
        
        await query.edit_message_text(f"✅ Все файлы удалены.")
    else:
        await query.edit_message_text("❌ Очистка отменена.")

async def handle_apk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Автоматически сохраняет APK файлы"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Этот бот приватный.")
        return
    
    message = update.message
    if message.document and message.document.file_name and message.document.file_name.lower().endswith('.apk'):
        try:
            db = load_db()
            
            next_id = db["last_id"] + 1
            file_id = str(next_id)
            
            db["files"][file_id] = {
                "file_id": message.document.file_id,
                "file_name": message.document.file_name,
                "uploaded_at": message.date.isoformat() if message.date else ""
            }
            
            db["last_id"] = next_id
            save_db(db)
            
            bot_username = (await context.bot.get_me()).username
            botlink = f"https://t.me/{bot_username}?start={file_id}"
            
            # Предлагаем создать пост
            keyboard = [[InlineKeyboardButton("📝 Создать пост", callback_data=f"create_post_{file_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            markup = (
                f"✅ Файл сохранен!\n\n"
                f"📂 ID файла: {file_id}\n"
                f"📂 Имя файла: {message.document.file_name}\n"
                f"📦 Размер: {message.document.file_size // 1024 if message.document.file_size else 0} KB\n\n"
                f"🔗 Ссылка для скачивания:\n"
                f"<code>{botlink}</code>"
            )
            
            await message.reply_text(markup, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        except Exception as e:
            await message.reply_text(f"Ошибка: {e}")
    else:
        await message.reply_text("Это не .apk файл. Пришли .apk документ!")

async def adm_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /post - показывает последний файл"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Этот бот приватный.")
        return ConversationHandler.END
    
    db = load_db()
    files = db["files"]
    
    if not files:
        await update.message.reply_text("📭 Нет файлов. Сначала отправьте .apk файл.")
        return ConversationHandler.END
    
    # Получаем последний файл
    last_file_id = str(db["last_id"])
    last_file = files[last_file_id]
    
    bot_username = (await context.bot.get_me()).username
    botlink = f"https://t.me/{bot_username}?start={last_file_id}"
    
    # Кнопка для создания поста
    keyboard = [[InlineKeyboardButton(
        f"📝 Создать пост", 
        callback_data=f"create_post_{last_file_id}"
    )]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📱 <b>Последний файл:</b>\n\n"
        f"ID: {last_file_id}\n"
        f"Имя: {last_file['file_name']}\n\n"
        f"🔗 Ссылка для скачивания:\n"
        f"<code>{botlink}</code>\n\n"
        f"👇 Нажмите кнопку ниже для создания поста",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    return ADD_MEDIA

async def start_create_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает создание поста"""
    query = update.callback_query
    await query.answer()
    
    file_id = query.data.replace("create_post_", "")
    db = load_db()
    
    if file_id not in db["files"]:
        await query.edit_message_text("❌ Файл не найден.")
        return ConversationHandler.END
    
    # Получаем ссылку на файл
    bot_username = (await context.bot.get_me()).username
    botlink = f"https://t.me/{bot_username}?start={file_id}"
    
    context.user_data['post'] = {
        "media_type": None,
        "media_path": "",
        "media_id": "",
        "title": db["files"][file_id]["file_name"],
        "description": "",
        "buttons": [],
        "watermark": "avatar",
        "file_id": file_id
    }
    
    await query.edit_message_text(
        f"🖼 <b>Создание нового поста</b>\n\n"
        f"📱 <b>Файл:</b> {db['files'][file_id]['file_name']}\n"
        f"🔗 <b>Ссылка:</b>\n"
        f"<code>{botlink}</code>\n\n"
        f"Выберите тип медиа для поста:",
        parse_mode=ParseMode.HTML,
        reply_markup=media_type_keyboard()
    )
    return ADD_MEDIA

async def add_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        file_id = context.user_data['post']['file_id']
        bot_username = (await context.bot.get_me()).username
        botlink = f"https://t.me/{bot_username}?start={file_id}"
        
        if query.data == 'media_photo':
            await query.edit_message_text(
                f"📷 <b>Отправьте фото</b>\n\n"
                f"🔗 <b>Ссылка на файл:</b>\n"
                f"<code>{botlink}</code>\n\n"
                f"Отправьте фото для поста:",
                parse_mode=ParseMode.HTML
            )
            return ADD_MEDIA
            
        elif query.data == 'media_video':
            await query.edit_message_text(
                f"🎬 <b>Отправьте видео</b>\n\n"
                f"🔗 <b>Ссылка на файл:</b>\n"
                f"<code>{botlink}</code>\n\n"
                f"Отправьте видео для поста:",
                parse_mode=ParseMode.HTML
            )
            return ADD_MEDIA
            
        elif query.data == 'media_gif':
            await query.edit_message_text(
                f"🎞 <b>Отправьте GIF</b>\n\n"
                f"🔗 <b>Ссылка на файл:</b>\n"
                f"<code>{botlink}</code>\n\n"
                f"Отправьте GIF для поста:",
                parse_mode=ParseMode.HTML
            )
            return ADD_MEDIA
            
        elif query.data == 'media_skip':
            context.user_data['post']['media_type'] = None
            await query.edit_message_text(
                f"⏭ Медиа пропущено.\n\n"
                f"🔗 <b>Ссылка на файл:</b>\n"
                f"<code>{botlink}</code>\n\n"
                f"Введите описание поста (или нажмите кнопку):",
                parse_mode=ParseMode.HTML,
                reply_markup=desc_keyboard()
            )
            return ADD_DESC
            
        elif query.data == 'media_none':
            context.user_data['post']['media_type'] = 'none'
            context.user_data['post']['media_path'] = ""
            context.user_data['post']['media_id'] = ""
            await query.edit_message_text(
                f"❌ Пост без медиа.\n\n"
                f"🔗 <b>Ссылка на файл:</b>\n"
                f"<code>{botlink}</code>\n\n"
                f"Введите описание поста (или нажмите кнопку):",
                parse_mode=ParseMode.HTML,
                reply_markup=desc_keyboard()
            )
            return ADD_DESC
    elif update.message:
        message = update.message
        
        if message.photo:
            photo = message.photo[-1]
            file = await photo.get_file()
            media_path = os.path.join(MEDIA_DIR, f"{uuid4()}.jpg")
            await file.download_to_drive(media_path)
            
            context.user_data['post']['media_type'] = 'photo'
            context.user_data['post']['media_path'] = media_path
            context.user_data['post']['media_id'] = photo.file_id
            
            file_id = context.user_data['post']['file_id']
            bot_username = (await context.bot.get_me()).username
            botlink = f"https://t.me/{bot_username}?start={file_id}"
            
            await message.reply_text(
                f"✅ Фото сохранено!\n\n"
                f"🔗 <b>Ссылка на файл:</b>\n"
                f"<code>{botlink}</code>\n\n"
                f"Введите описание поста (или нажмите кнопку):",
                parse_mode=ParseMode.HTML,
                reply_markup=desc_keyboard()
            )
            return ADD_DESC
        
        elif message.video:
            video = message.video
            file = await video.get_file()
            media_path = os.path.join(MEDIA_DIR, f"{uuid4()}.mp4")
            await file.download_to_drive(media_path)
            
            context.user_data['post']['media_type'] = 'video'
            context.user_data['post']['media_path'] = media_path
            context.user_data['post']['media_id'] = video.file_id
            
            file_id = context.user_data['post']['file_id']
            bot_username = (await context.bot.get_me()).username
            botlink = f"https://t.me/{bot_username}?start={file_id}"
            
            await message.reply_text(
                f"✅ Видео сохранено!\n\n"
                f"🔗 <b>Ссылка на файл:</b>\n"
                f"<code>{botlink}</code>\n\n"
                f"Введите описание поста (или нажмите кнопку):",
                parse_mode=ParseMode.HTML,
                reply_markup=desc_keyboard()
            )
            return ADD_DESC
        
        elif message.animation:
            gif = message.animation
            file = await gif.get_file()
            media_path = os.path.join(MEDIA_DIR, f"{uuid4()}.gif")
            await file.download_to_drive(media_path)
            
            context.user_data['post']['media_type'] = 'gif'
            context.user_data['post']['media_path'] = media_path
            context.user_data['post']['media_id'] = gif.file_id
            
            file_id = context.user_data['post']['file_id']
            bot_username = (await context.bot.get_me()).username
            botlink = f"https://t.me/{bot_username}?start={file_id}"
            
            await message.reply_text(
                f"✅ GIF сохранен!\n\n"
                f"🔗 <b>Ссылка на файл:</b>\n"
                f"<code>{botlink}</code>\n\n"
                f"Введите описание поста (или нажмите кнопку):",
                parse_mode=ParseMode.HTML,
                reply_markup=desc_keyboard()
            )
            return ADD_DESC
    
    return ADD_MEDIA

async def add_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        file_id = context.user_data['post']['file_id']
        bot_username = (await context.bot.get_me()).username
        botlink = f"https://t.me/{bot_username}?start={file_id}"
        
        if query.data == 'skip_desc':
            context.user_data['post']['description'] = ""
            await query.edit_message_text(
                f"⏭ Описание пропущено.\n\n"
                f"🔗 <b>Ссылка на файл:</b>\n"
                f"<code>{botlink}</code>\n\n"
                f"Настройте пост с помощью клавиатуры:",
                parse_mode=ParseMode.HTML,
                reply_markup=admin_kb()
            )
            return ADMIN_PANEL
            
        elif query.data == 'back_desc':
            await query.edit_message_text(
                f"🖼 Выберите тип медиа для поста:\n\n"
                f"🔗 <b>Ссылка на файл:</b>\n"
                f"<code>{botlink}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=media_type_keyboard()
            )
            return ADD_MEDIA
    elif update.message:
        context.user_data['post']['description'] = update.message.text
        
        file_id = context.user_data['post']['file_id']
        bot_username = (await context.bot.get_me()).username
        botlink = f"https://t.me/{bot_username}?start={file_id}"
        
        await update.message.reply_text(
            f"✅ Описание сохранено!\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>\n\n"
            f"Настройте пост с помощью клавиатуры:",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_kb()
        )
        return ADMIN_PANEL
    
    return ADD_DESC

# ========== РЕДАКТИРОВАНИЕ ==========
async def edit_title_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для редактирования заголовка"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        file_id = context.user_data['post']['file_id']
        bot_username = (await context.bot.get_me()).username
        botlink = f"https://t.me/{bot_username}?start={file_id}"
        
        await query.edit_message_text(
            f"✏️ <b>Редактирование заголовка</b>\n\n"
            f"Текущий заголовок: {context.user_data['post']['title']}\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>\n\n"
            f"Введите новый заголовок:",
            parse_mode=ParseMode.HTML
        )
        return EDIT_TITLE
    
    elif update.message:
        # Сохраняем новый заголовок
        new_title = update.message.text
        context.user_data['post']['title'] = new_title
        
        file_id = context.user_data['post']['file_id']
        bot_username = (await context.bot.get_me()).username
        botlink = f"https://t.me/{bot_username}?start={file_id}"
        
        await update.message.reply_text(
            f"✅ Заголовок изменен!\n\n"
            f"Новый заголовок: {new_title}\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>\n\n"
            f"Настройте пост с помощью клавиатуры:",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_kb()
        )
        return ADMIN_PANEL
    
    return EDIT_TITLE

async def edit_description_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для редактирования описания"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        file_id = context.user_data['post']['file_id']
        bot_username = (await context.bot.get_me()).username
        botlink = f"https://t.me/{bot_username}?start={file_id}"
        
        current_desc = context.user_data['post'].get('description', '')
        if not current_desc:
            current_desc = "Описание отсутствует"
        
        await query.edit_message_text(
            f"📝 <b>Редактирование описания</b>\n\n"
            f"Текущее описание: {current_desc}\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>\n\n"
            f"Введите новое описание:",
            parse_mode=ParseMode.HTML
        )
        return EDIT_DESC
    
    elif update.message:
        # Сохраняем новое описание
        new_desc = update.message.text
        context.user_data['post']['description'] = new_desc
        
        file_id = context.user_data['post']['file_id']
        bot_username = (await context.bot.get_me()).username
        botlink = f"https://t.me/{bot_username}?start={file_id}"
        
        await update.message.reply_text(
            f"✅ Описание изменено!\n\n"
            f"Новое описание: {new_desc}\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>\n\n"
            f"Настройте пост с помощью клавиатуры:",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_kb()
        )
        return ADMIN_PANEL
    
    return EDIT_DESC

async def edit_buttons_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню редактирования кнопок"""
    query = update.callback_query
    await query.answer()
    
    post = context.user_data['post']
    file_id = post['file_id']
    bot_username = (await context.bot.get_me()).username
    botlink = f"https://t.me/{bot_username}?start={file_id}"
    
    # Создаем клавиатуру для управления кнопками
    keyboard = []
    
    # Показываем текущие кнопки
    buttons = post.get('buttons', [])
    if buttons:
        for i, btn in enumerate(buttons):
            keyboard.append([InlineKeyboardButton(
                f"✏️ Кнопка {i+1}: {btn['label']}", 
                callback_data=f'editbtn_{i}'
            )])
    
    # Кнопки действий
    action_buttons = []
    action_buttons.append(InlineKeyboardButton("➕ Добавить", callback_data='add_btn'))
    if buttons:
        action_buttons.append(InlineKeyboardButton("🗑 Очистить все", callback_data='clear_buttons'))
    
    keyboard.append(action_buttons)
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='back_to_admin')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🔘 <b>Редактирование кнопок</b>\n\n"
        f"Текущие кнопки: {len(buttons)} шт.\n\n"
        f"🔗 <b>Ссылка на файл:</b>\n"
        f"<code>{botlink}</code>\n\n"
        f"Выберите действие:",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    return EDIT_BUTTONS

async def clear_all_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очищает все кнопки"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['post']['buttons'] = []
    
    file_id = context.user_data['post']['file_id']
    bot_username = (await context.bot.get_me()).username
    botlink = f"https://t.me/{bot_username}?start={file_id}"
    
    await query.edit_message_text(
        f"✅ Все кнопки удалены!\n\n"
        f"🔗 <b>Ссылка на файл:</b>\n"
        f"<code>{botlink}</code>\n\n"
        f"Настройте пост с помощью клавиатуры:",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_kb()
    )
    return ADMIN_PANEL

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    post = context.user_data['post']
    
    file_id = post['file_id']
    bot_username = (await context.bot.get_me()).username
    botlink = f"https://t.me/{bot_username}?start={file_id}"

    if query.data == "set_media":
        await query.edit_message_text(
            f"🖼 <b>Выберите тип медиа:</b>\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=media_type_keyboard()
        )
        return ADD_MEDIA

    elif query.data == "edit_title":
        return await edit_title_handler(update, context)

    elif query.data == "edit_description":
        return await edit_description_handler(update, context)

    elif query.data == "edit_buttons":
        return await edit_buttons_menu(update, context)

    elif query.data == "clear_buttons":
        return await clear_all_buttons(update, context)

    elif query.data == "back_to_admin":
        await query.edit_message_text(
            f"🔧 <b>Настройка поста</b>\n\n"
            f"📱 Заголовок: {post['title']}\n"
            f"📝 Описание: {post.get('description', 'нет')[:50]}\n"
            f"🔘 Кнопок: {len(post.get('buttons', []))}\n"
            f"💧 Водяной знак: {'✅' if post['watermark'] != 'none' else '❌'}\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>\n\n"
            f"Выберите что хотите изменить:",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_kb()
        )
        return ADMIN_PANEL

    elif query.data == "set_watermark":
        avatar_status = "✅ Есть" if os.path.exists(CUSTOM_AVATAR) else "❌ Нет (будет использована дефолтная)"
        
        await query.edit_message_text(
            f"💎 <b>СТИЛЬНЫЙ ВОДЯНОЙ ЗНАК</b>\n\n"
            f"<b>Аватарка канала:</b> {avatar_status}\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>\n\n"
            "<b>Что будет:</b>\n"
            "✅ <b>Аватарка</b> - круглая в правом верхнем углу\n"
            "✅ <b>Название</b> - яркое под аватаркой\n"
            "✅ <b>Ссылка на канал</b> - в правом нижнем углу",
            parse_mode=ParseMode.HTML,
            reply_markup=watermark_keyboard()
        )
        return ADD_WATERMARK

    elif query.data == "watermark_avatar":
        post['watermark'] = 'avatar'
        
        if os.path.exists(CUSTOM_AVATAR):
            avatar_msg = "✅ Будет использована ВАША аватарка!"
        else:
            avatar_msg = "⚠️ Будет использована дефолтная аватарка!"
        
        await query.edit_message_text(
            f"{avatar_msg}\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>\n\n"
            "💎 <b>СТИЛЬНЫЕ ФИЧИ:</b>\n"
            "1. <b>Круглая аватарка</b> в правом верхнем углу\n"
            "2. <b>Название</b> ЯРКИМ цветом под аватаркой\n"
            "3. <b>Ссылка на канал</b> @ANDRO_FILE в правом нижнем углу\n\n"
            "Настройте пост:",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_kb()
        )
        return ADMIN_PANEL

    elif query.data == "watermark_no":
        post['watermark'] = 'none'
        await query.edit_message_text(
            f"❌ Водяной знак не будет добавлен.\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>\n\n"
            f"Настройте пост:",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_kb()
        )
        return ADMIN_PANEL

    elif query.data == "preview":
        await show_preview(query, context)
        
        await query.message.reply_text(
            f"Используйте клавиатуру:\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>\n\n"
            f"📱 Заголовок: {post['title']}\n"
            f"📝 Описание: {post.get('description', 'нет')[:50]}",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_kb()
        )
        return ADMIN_PANEL

    elif query.data == "add_btn":
        context.user_data['editbtn'] = None
        await query.edit_message_text(
            f"Введите текст для кнопки:\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>",
            parse_mode=ParseMode.HTML
        )
        return ADD_BTN_LABEL

    elif query.data.startswith("editbtn_"):
        idx = int(query.data.split("_")[1])
        context.user_data['editbtn'] = idx
        btn = post['buttons'][idx]
        await query.edit_message_text(
            f"Редактируем кнопку №{idx + 1}: [{btn['label']}]\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>\n\n"
            f"Введите новое название:",
            parse_mode=ParseMode.HTML
        )
        return ADD_BTN_URL

    elif query.data == "back":
        await show_preview(query, context)
        
        await query.message.reply_text(
            f"Используйте клавиатуру:\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>\n\n"
            f"📱 Заголовок: {post['title']}\n"
            f"📝 Описание: {post.get('description', 'нет')[:50]}",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_kb()
        )
        return ADMIN_PANEL

    elif query.data == "publish":
        try:
            caption = render_post(post)
            
            media_path = post.get('media_path')
            watermark_type = post.get('watermark', 'avatar')
            title = post.get('title', '')
            
            print(f"🚀 Публикация поста...")
            
            # Создаем кнопки для поста
            reply_markup = build_buttons(post) if post.get('buttons') else None
            
            if post['media_type'] == 'photo' and media_path and os.path.exists(media_path):
                if watermark_type != 'none':
                    watermarked_path = add_watermark_to_image(media_path, watermark_type, title)
                else:
                    watermarked_path = media_path
                
                with open(watermarked_path, "rb") as img:
                    sent_message = await context.bot.send_photo(
                        chat_id=CHANNEL_ID,
                        photo=img,
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup
                    )
                    
                    post_id = sent_message.message_id
                    print(f"✅ Пост опубликован! ID поста: {post_id}")
                    
                    # Создаем ссылку на пост
                    channel_name = CHANNEL_USERNAME.replace("@", "")
                    post_link = f"https://t.me/{channel_name}/{post_id}"
                    
                    await asyncio.sleep(1)
                    
                    # Добавляем кнопку "Поделиться"
                    share_button = [InlineKeyboardButton("📢 Поделиться", url=f"https://t.me/share/url?url={post_link}")]
                    
                    if reply_markup:
                        existing_buttons = list(reply_markup.inline_keyboard)
                        existing_buttons.append(share_button)
                        new_markup = InlineKeyboardMarkup(existing_buttons)
                    else:
                        new_markup = InlineKeyboardMarkup([share_button])
                    
                    await context.bot.edit_message_reply_markup(
                        chat_id=CHANNEL_ID,
                        message_id=post_id,
                        reply_markup=new_markup
                    )
                    
                    print(f"🔗 Ссылка на пост: {post_link}")
                
                if watermarked_path != media_path and os.path.exists(watermarked_path):
                    try:
                        os.remove(watermarked_path)
                    except:
                        pass
            
            elif post['media_type'] == 'video' and media_path and os.path.exists(media_path):
                with open(media_path, "rb") as video:
                    sent_message = await context.bot.send_video(
                        chat_id=CHANNEL_ID,
                        video=video,
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup
                    )
                    
                    post_id = sent_message.message_id
                    channel_name = CHANNEL_USERNAME.replace("@", "")
                    post_link = f"https://t.me/{channel_name}/{post_id}"
                    
                    await asyncio.sleep(1)
                    
                    share_button = [InlineKeyboardButton("📢 Поделиться", url=f"https://t.me/share/url?url={post_link}")]
                    
                    if reply_markup:
                        existing_buttons = list(reply_markup.inline_keyboard)
                        existing_buttons.append(share_button)
                        new_markup = InlineKeyboardMarkup(existing_buttons)
                    else:
                        new_markup = InlineKeyboardMarkup([share_button])
                    
                    await context.bot.edit_message_reply_markup(
                        chat_id=CHANNEL_ID,
                        message_id=post_id,
                        reply_markup=new_markup
                    )
            
            elif post['media_type'] == 'gif' and media_path and os.path.exists(media_path):
                with open(media_path, "rb") as gif:
                    sent_message = await context.bot.send_animation(
                        chat_id=CHANNEL_ID,
                        animation=gif,
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup
                    )
                    
                    post_id = sent_message.message_id
                    channel_name = CHANNEL_USERNAME.replace("@", "")
                    post_link = f"https://t.me/{channel_name}/{post_id}"
                    
                    await asyncio.sleep(1)
                    
                    share_button = [InlineKeyboardButton("📢 Поделиться", url=f"https://t.me/share/url?url={post_link}")]
                    
                    if reply_markup:
                        existing_buttons = list(reply_markup.inline_keyboard)
                        existing_buttons.append(share_button)
                        new_markup = InlineKeyboardMarkup(existing_buttons)
                    else:
                        new_markup = InlineKeyboardMarkup([share_button])
                    
                    await context.bot.edit_message_reply_markup(
                        chat_id=CHANNEL_ID,
                        message_id=post_id,
                        reply_markup=new_markup
                    )
            
            else:
                sent_message = await context.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
                
                post_id = sent_message.message_id
                channel_name = CHANNEL_USERNAME.replace("@", "")
                post_link = f"https://t.me/{channel_name}/{post_id}"
                
                await asyncio.sleep(1)
                
                share_button = [InlineKeyboardButton("📢 Поделиться", url=f"https://t.me/share/url?url={post_link}")]
                
                if reply_markup:
                    existing_buttons = list(reply_markup.inline_keyboard)
                    existing_buttons.append(share_button)
                    new_markup = InlineKeyboardMarkup(existing_buttons)
                else:
                    new_markup = InlineKeyboardMarkup([share_button])
                
                await context.bot.edit_message_reply_markup(
                    chat_id=CHANNEL_ID,
                    message_id=post_id,
                    reply_markup=new_markup
                )
            
            channel_name = CHANNEL_USERNAME.replace("@", "")
            post_link = f"https://t.me/{channel_name}/{post_id}"
            
            await query.edit_message_text(
                f"✅ <b>Пост опубликован!</b>\n\n"
                f"🔗 <b>Ссылка на пост:</b>\n"
                f"<code>{post_link}</code>",
                parse_mode=ParseMode.HTML
            )
            
        except Exception as e:
            print(f"❌ ОШИБКА: {e}")
            import traceback
            traceback.print_exc()
            await query.edit_message_text(f"❌ Ошибка: {str(e)[:100]}")
        
        return ConversationHandler.END

    elif query.data == "cancel":
        await query.edit_message_text("❌ Создание поста отменено.")
        return ConversationHandler.END

    await query.edit_message_text("❓ Неизвестная команда...")
    return ADMIN_PANEL

async def add_btn_label(update: Update, context: ContextTypes.DEFAULT_TYPE):
    label = update.message.text
    context.user_data['btn_tmp_label'] = label
    
    file_id = context.user_data['post']['file_id']
    bot_username = (await context.bot.get_me()).username
    botlink = f"https://t.me/{bot_username}?start={file_id}"
    
    await update.message.reply_text(
        f"Введите URL для кнопки:\n\n"
        f"🔗 <b>Ссылка на файл:</b>\n"
        f"<code>{botlink}</code>",
        parse_mode=ParseMode.HTML
    )
    return ADD_BTN_URL

async def add_btn_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    label = context.user_data.get('btn_tmp_label', '')
    idx = context.user_data.get('editbtn')
    
    if idx is not None:
        context.user_data['post']['buttons'][idx] = {"label": label, "url": url}
        context.user_data['editbtn'] = None
    else:
        if not label:
            await update.message.reply_text("❌ Ошибка: не найден текст кнопки.")
            return ADMIN_PANEL
        context.user_data['post'].setdefault("buttons", []).append({"label": label, "url": url})
    
    await show_preview(update, context)
    
    file_id = context.user_data['post']['file_id']
    bot_username = (await context.bot.get_me()).username
    botlink = f"https://t.me/{bot_username}?start={file_id}"
    
    await update.message.reply_text(
        f"✅ Кнопка {'изменена' if idx is not None else 'добавлена'}!\n\n"
        f"🔗 <b>Ссылка на файл:</b>\n"
        f"<code>{botlink}</code>\n\n"
        f"Настройте пост с помощью клавиатуры:",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_kb()
    )
    return ADMIN_PANEL

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Действие отменено.")
    return ConversationHandler.END

async def filebot_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) == 1 and args[0].isdigit():
        db = load_db()
        file_key = args[0]
        entry = db["files"].get(file_key)
        if entry and "file_id" in entry:
            caption = f"{SIGNATURE}"
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=entry["file_id"],
                caption=caption
            )
        else:
            await update.message.reply_text("Файл не найден.")
    
    else:
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("⛔ Этот бот приватный.")
            return
        
        user = update.effective_user
        username = user.username if user.username else user.first_name
        
        db = load_db()
        files = db["files"]
        
        response = f"👋 {username}!\n"
        response += f"📊 Файлов: {len(files)}\n"
        response += f"🔢 Последний ID: {db['last_id']}\n\n"
        response += "📋 <b>Команды:</b>\n"
        response += "/post - создать пост для последнего файла\n"
        response += "/del ID - удалить файл\n"
        response += "/clear - очистить все файлы"
        
        await update.message.reply_text(response, parse_mode=ParseMode.HTML)

# ------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ -------
def render_post(post):
    text = ""
    if post.get('title'):
        text += f"<b>{post['title']}</b>\n"
        text += f"<b>____________________________________</b>\n"
    
    if post.get('description'):
        text += f"📝 <b>Описание:</b>\n"
        text += f"{post['description']}\n"
    
    text += f"\n🔗 {CHANNEL_USERNAME}\n"
    text += f"<b>===========================</b>"
    return text

def build_buttons(post):
    buttons = post.get("buttons", [])
    
    if not buttons:
        return None
    
    rows = []
    for i in range(0, len(buttons), 2):
        row = []
        btn_a = buttons[i]
        row.append(InlineKeyboardButton(btn_a["label"], url=btn_a["url"]))
        if i + 1 < len(buttons):
            btn_b = buttons[i + 1]
            row.append(InlineKeyboardButton(btn_b["label"], url=btn_b["url"]))
        rows.append(row)
    return InlineKeyboardMarkup(rows)

def admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 Медиа", callback_data='set_media')],
        [InlineKeyboardButton("✏️ Заголовок", callback_data='edit_title'),
         InlineKeyboardButton("📝 Описание", callback_data='edit_description')],
        [InlineKeyboardButton("🔘 Кнопки", callback_data='edit_buttons')],
        [InlineKeyboardButton("💧 Водяной знак", callback_data='set_watermark')],
        [InlineKeyboardButton("📤 Опубликовать", callback_data='publish'),
         InlineKeyboardButton("👁 Предпросмотр", callback_data='preview')],
        [InlineKeyboardButton("❌ Отмена", callback_data='cancel')]
    ])

def media_type_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 Фото", callback_data='media_photo')],
        [InlineKeyboardButton("🎬 Видео", callback_data='media_video')],
        [InlineKeyboardButton("🎞 GIF", callback_data='media_gif')],
        [InlineKeyboardButton("⏭ Пропустить медиа", callback_data='media_skip')],
        [InlineKeyboardButton("❌ Без медиа", callback_data='media_none')]
    ])

def watermark_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ С аватаркой", callback_data='watermark_avatar')],
        [InlineKeyboardButton("❌ Без водяного знака", callback_data='watermark_no')],
        [InlineKeyboardButton("← Назад", callback_data='back')]
    ])

def desc_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭ Пропустить описание", callback_data='skip_desc')],
        [InlineKeyboardButton("← Назад", callback_data='back_desc')]
    ])

async def show_preview(update, context):
    post = context.user_data['post']
    try:
        if hasattr(update, "message") and update.message:
            send_to = update.message
        else:
            send_to = update
        
        caption = render_post(post)
        
        media_path = post.get('media_path')
        
        if post['media_type'] == 'photo' and media_path and os.path.exists(media_path):
            with open(media_path, "rb") as img:
                await send_to.reply_photo(
                    img,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=build_buttons(post)
                )
        
        elif post['media_type'] == 'video' and media_path and os.path.exists(media_path):
            with open(media_path, "rb") as video:
                await send_to.reply_video(
                    video,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=build_buttons(post)
                )
        
        elif post['media_type'] == 'gif' and media_path and os.path.exists(media_path):
            with open(media_path, "rb") as gif:
                await send_to.reply_animation(
                    gif,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=build_buttons(post)
                )
        
        else:
            await send_to.reply_text(
                caption,
                parse_mode=ParseMode.HTML,
                reply_markup=build_buttons(post)
            )
            
    except Exception as e:
        print(f"Ошибка при показе превью: {e}")
        await send_to.reply_text(
            f"Ошибка при показе превью: {e}\n\n"
            f"Текст поста:\n{render_post(post)}",
            parse_mode=ParseMode.HTML,
            reply_markup=build_buttons(post)
        )

def create_default_avatar():
    """Создает стильную дефолтную аватарку в кружке"""
    try:
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Яркая заливка
        circle_color = (30, 144, 255)
        draw.ellipse([(20, 20), (size - 20, size - 20)], fill=circle_color)
        
        # Белая обводка
        draw.ellipse([(15, 15), (size - 15, size - 15)], outline=(255, 255, 255), width=5)
        
        # Буква A
        try:
            font = ImageFont.truetype("arialbd.ttf", 120)
        except:
            font = ImageFont.load_default()
        
        text = "A"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        position = ((size - text_width) // 2, (size - text_height) // 2)
        draw.text(position, text, font=font, fill=(255, 255, 255, 255))
        
        img.save(DEFAULT_AVATAR, "PNG")
        print(f"✅ Создана дефолтная аватарка")
        return DEFAULT_AVATAR
        
    except Exception as e:
        print(f"❌ Ошибка при создании аватарки: {e}")
        return None

def get_avatar_path():
    """Возвращает путь к аватарке"""
    if os.path.exists(CUSTOM_AVATAR):
        return CUSTOM_AVATAR
    else:
        if not os.path.exists(DEFAULT_AVATAR):
            create_default_avatar()
        return DEFAULT_AVATAR

def make_circular_avatar(avatar_image):
    """Преобразует изображение в круговую аватарку"""
    try:
        size = avatar_image.size[0]
        
        mask = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse([(0, 0), (size, size)], fill=255)
        
        circular_avatar = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        circular_avatar.paste(avatar_image, (0, 0), mask)
        
        # Добавляем белую обводку
        border_size = 10
        bordered_size = size + border_size * 2
        bordered_avatar = Image.new('RGBA', (bordered_size, bordered_size), (0, 0, 0, 0))
        draw_border = ImageDraw.Draw(bordered_avatar)
        
        draw_border.ellipse([(0, 0), (bordered_size, bordered_size)], outline=(255, 255, 255), width=5)
        bordered_avatar.paste(circular_avatar, (border_size, border_size), circular_avatar)
        
        return bordered_avatar
    except Exception as e:
        return avatar_image

def get_random_bright_color():
    """Возвращает случайный яркий цвет"""
    bright_colors = [
        (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
        (255, 0, 255), (0, 255, 255), (255, 128, 0), (255, 0, 128),
        (128, 0, 255), (0, 255, 128),
    ]
    return random.choice(bright_colors)

def get_font(size, bold=True):
    """Получает шрифт"""
    try:
        font_paths = [
            os.path.join(FONT_DIR, "Montserrat-Bold.ttf"),
            os.path.join(FONT_DIR, "Roboto-Bold.ttf"),
            "arialbd.ttf", "arial.ttf"
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
        
        return ImageFont.load_default()
        
    except:
        return ImageFont.load_default()

def add_watermark_to_image(image_path, watermark_type="avatar", title=""):
    """Добавляет водяной знак - аватарка сверху справа, ссылка внизу справа"""
    try:
        if watermark_type == "none":
            return image_path
        
        image = Image.open(image_path).convert('RGBA')
        width, height = image.size
        
        watermark = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(watermark)
        
        if watermark_type == "avatar":
            avatar_path = get_avatar_path()
            
            if avatar_path and os.path.exists(avatar_path):
                avatar = Image.open(avatar_path).convert('RGBA')
                avatar_size = min(120, max(70, min(width, height) // 10))
                avatar = avatar.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
                circular_avatar = make_circular_avatar(avatar)
                
                # Аватарка в правом верхнем углу
                margin = 20
                avatar_position = (width - avatar_size - margin - 10, margin)
                watermark.paste(circular_avatar, avatar_position, circular_avatar)
                
                # Название под аватаркой
                if title:
                    title_color = get_random_bright_color()
                    title_font_size = min(28, max(16, min(width, height) // 25))
                    title_font = get_font(title_font_size, bold=True)
                    
                    if len(title) > 25:
                        title_text = title[:22] + "..."
                    else:
                        title_text = title
                    
                    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
                    title_width = title_bbox[2] - title_bbox[0]
                    title_position = (width - title_width - margin, avatar_position[1] + avatar_size + 5)
                    
                    # Тень для названия
                    for offset in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                        draw.text((title_position[0] + offset[0], title_position[1] + offset[1]),
                                title_text, font=title_font, fill=(0, 0, 0, 200))
                    
                    draw.text(title_position, title_text, font=title_font, fill=(*title_color, 255))
                    
                    # Ссылка на канал в правом НИЖНЕМ углу
                    link_font_size = max(14, min(22, title_font_size - 2))
                    link_font = get_font(link_font_size, bold=True)
                    link_text = CHANNEL_USERNAME
                    
                    link_bbox = draw.textbbox((0, 0), link_text, font=link_font)
                    link_width = link_bbox[2] - link_bbox[0]
                    link_height = link_bbox[3] - link_bbox[1]
                    
                    # Позиция в правом нижнем углу
                    link_margin = 30
                    link_position = (
                        width - link_width - link_margin,
                        height - link_height - link_margin
                    )
                    
                    # Фон для ссылки
                    bg_padding = 8
                    draw.rounded_rectangle(
                        [link_position[0] - bg_padding, link_position[1] - bg_padding,
                         link_position[0] + link_width + bg_padding, link_position[1] + link_height + bg_padding],
                        radius=8, fill=(0, 0, 0, 180)
                    )
                    
                    # Белая ссылка
                    draw.text(link_position, link_text, font=link_font, fill=(255, 255, 255, 255))
        
        watermarked = Image.alpha_composite(image, watermark)
        watermarked_path = os.path.join(MEDIA_DIR, f"watermarked_{uuid4()}.png")
        watermarked.save(watermarked_path, "PNG")
        
        return watermarked_path
        
    except Exception as e:
        print(f"❌ Ошибка водяного знака: {e}")
        return image_path

# =========== MAIN ==========
def main():
    print("=" * 60)
    print("💎 ЗАПУСК БОТА")
    print("=" * 60)
    print(f"👑 Бот работает ТОЛЬКО для ID: {ADMIN_ID}")
    print(f"📢 Канал: {CHANNEL_USERNAME}")
    print("=" * 60)
    
    create_default_avatar()
    
    if TELEGRAM_TOKEN == "ВАШ_ТОКЕН_ЗДЕСЬ":
        print("❌ ОШИБКА: Замените TELEGRAM_TOKEN!")
        return
    
    try:
        from PIL import Image
        print("✅ Библиотека PIL установлена")
    except ImportError:
        print("❌ Установите PIL: pip install Pillow")
        return
    
    db = load_db()
    print(f"📊 Файлов в базе: {len(db['files'])}")
    print(f"🔢 Последний ID: {db['last_id']}")
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # ConversationHandler для /post
    conv = ConversationHandler(
        entry_points=[
            CommandHandler('post', adm_cmd),
            CallbackQueryHandler(start_create_post, pattern='^create_post_')
        ],
        states={
            ADD_MEDIA: [
                CallbackQueryHandler(add_media),
                MessageHandler(filters.PHOTO | filters.VIDEO | filters.ANIMATION, add_media),
            ],
            ADD_DESC: [
                CallbackQueryHandler(add_desc),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_desc),
            ],
            ADMIN_PANEL: [
                CallbackQueryHandler(admin_panel),
            ],
            ADD_WATERMARK: [
                CallbackQueryHandler(admin_panel),
            ],
            ADD_BTN_LABEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_btn_label),
            ],
            ADD_BTN_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_btn_url),
            ],
            EDIT_TITLE: [
                CallbackQueryHandler(edit_title_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_title_handler),
            ],
            EDIT_DESC: [
                CallbackQueryHandler(edit_description_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_description_handler),
            ],
            EDIT_BUTTONS: [
                CallbackQueryHandler(admin_panel),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )
    
    # Регистрируем команды
    app.add_handler(CommandHandler('start', filebot_start))
    app.add_handler(CommandHandler('del', del_file))
    app.add_handler(CommandHandler('clear', clear_files))
    app.add_handler(CallbackQueryHandler(clear_callback, pattern='^clear_'))
    app.add_handler(MessageHandler(filters.Document.ALL & filters.ChatType.PRIVATE, handle_apk))
    app.add_handler(conv)

    print("✅ БОТ ЗАПУЩЕН!")
    print("=" * 60)
    print("📋 КОМАНДЫ:")
    print("   • /start - приветствие")
    print("   • /post - создать пост для последнего файла")
    print("   • /del ID - удалить файл")
    print("   • /clear - очистить все файлы")
    print("=" * 60)
    print("✏️ ПОЛНОЕ РЕДАКТИРОВАНИЕ:")
    print("   • Заголовок - можно изменить")
    print("   • Описание - можно изменить")  
    print("   • Кнопки - можно добавить/изменить/удалить")
    print("=" * 60)
    print("🖼 ВОДЯНОЙ ЗНАК:")
    print("   • Аватарка - в правом верхнем углу")
    print("   • Название - под аватаркой")
    print("   • Ссылка на канал - в правом НИЖНЕМ углу")
    print("=" * 60)
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Бот остановлен")
    except Exception as e:
        print(f"\n\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()            json.dump({"files": {}, "last_id": 0}, f)
        return {"files": {}, "last_id": 0}

def save_db(db):
    with open(FILE_DB, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

# ========== КОМАНДЫ ==========
async def del_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /del для удаления файла"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Этот бот приватный.")
        return
    
    args = context.args
    if len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text(
            "❌ Используйте: /del ID\n"
            "Например: /del 5"
        )
        return
    
    file_id = args[0]
    db = load_db()
    
    if file_id not in db["files"]:
        await update.message.reply_text("❌ Файл с таким ID не найден.")
        return
    
    file_name = db["files"][file_id]["file_name"]
    del db["files"][file_id]
    
    # Обновляем last_id
    if db["files"]:
        db["last_id"] = max(int(id) for id in db["files"].keys())
    else:
        db["last_id"] = 0
    
    save_db(db)
    
    await update.message.reply_text(f"✅ Файл ID {file_id} ({file_name}) удалён.")

async def clear_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /clear для удаления всех файлов"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Этот бот приватный.")
        return
    
    # Запрашиваем подтверждение
    keyboard = [[
        InlineKeyboardButton("✅ Да, очистить всё", callback_data='clear_confirm'),
        InlineKeyboardButton("❌ Нет, отмена", callback_data='clear_cancel')
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ <b>ВНИМАНИЕ!</b>\n\n"
        "Вы уверены, что хотите удалить ВСЕ файлы?\n"
        "Это действие нельзя отменить!",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def clear_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик подтверждения очистки"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'clear_confirm':
        db = load_db()
        
        # Создаем резервную копию
        if db["files"]:
            backup_file = f"file_db_backup_{len(db['files'])}_files.json"
            shutil.copy2(FILE_DB, backup_file)
        
        # Очищаем базу
        new_db = {"files": {}, "last_id": 0}
        save_db(new_db)
        
        await query.edit_message_text(f"✅ Все файлы удалены.")
    else:
        await query.edit_message_text("❌ Очистка отменена.")

async def handle_apk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Автоматически сохраняет APK файлы"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Этот бот приватный.")
        return
    
    message = update.message
    if message.document and message.document.file_name and message.document.file_name.lower().endswith('.apk'):
        try:
            db = load_db()
            
            next_id = db["last_id"] + 1
            file_id = str(next_id)
            
            db["files"][file_id] = {
                "file_id": message.document.file_id,
                "file_name": message.document.file_name,
                "uploaded_at": message.date.isoformat() if message.date else ""
            }
            
            db["last_id"] = next_id
            save_db(db)
            
            bot_username = (await context.bot.get_me()).username
            botlink = f"https://t.me/{bot_username}?start={file_id}"
            
            # Предлагаем создать пост
            keyboard = [[InlineKeyboardButton("📝 Создать пост", callback_data=f"create_post_{file_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            markup = (
                f"✅ Файл сохранен!\n\n"
                f"📂 ID файла: {file_id}\n"
                f"📂 Имя файла: {message.document.file_name}\n"
                f"📦 Размер: {message.document.file_size // 1024 if message.document.file_size else 0} KB\n\n"
                f"🔗 Ссылка для скачивания:\n"
                f"<code>{botlink}</code>"
            )
            
            await message.reply_text(markup, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        except Exception as e:
            await message.reply_text(f"Ошибка: {e}")
    else:
        await message.reply_text("Это не .apk файл. Пришли .apk документ!")

async def adm_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /post - показывает последний файл"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Этот бот приватный.")
        return ConversationHandler.END
    
    db = load_db()
    files = db["files"]
    
    if not files:
        await update.message.reply_text("📭 Нет файлов. Сначала отправьте .apk файл.")
        return ConversationHandler.END
    
    # Получаем последний файл
    last_file_id = str(db["last_id"])
    last_file = files[last_file_id]
    
    bot_username = (await context.bot.get_me()).username
    botlink = f"https://t.me/{bot_username}?start={last_file_id}"
    
    # Кнопка для создания поста
    keyboard = [[InlineKeyboardButton(
        f"📝 Создать пост", 
        callback_data=f"create_post_{last_file_id}"
    )]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📱 <b>Последний файл:</b>\n\n"
        f"ID: {last_file_id}\n"
        f"Имя: {last_file['file_name']}\n\n"
        f"🔗 Ссылка для скачивания:\n"
        f"<code>{botlink}</code>\n\n"
        f"👇 Нажмите кнопку ниже для создания поста",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    return ADD_MEDIA

async def start_create_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает создание поста"""
    query = update.callback_query
    await query.answer()
    
    file_id = query.data.replace("create_post_", "")
    db = load_db()
    
    if file_id not in db["files"]:
        await query.edit_message_text("❌ Файл не найден.")
        return ConversationHandler.END
    
    # Получаем ссылку на файл
    bot_username = (await context.bot.get_me()).username
    botlink = f"https://t.me/{bot_username}?start={file_id}"
    
    context.user_data['post'] = {
        "media_type": None,
        "media_path": "",
        "media_id": "",
        "title": db["files"][file_id]["file_name"],
        "description": "",
        "buttons": [],
        "watermark": "avatar",
        "file_id": file_id
    }
    
    await query.edit_message_text(
        f"🖼 <b>Создание нового поста</b>\n\n"
        f"📱 <b>Файл:</b> {db['files'][file_id]['file_name']}\n"
        f"🔗 <b>Ссылка:</b>\n"
        f"<code>{botlink}</code>\n\n"
        f"Выберите тип медиа для поста:",
        parse_mode=ParseMode.HTML,
        reply_markup=media_type_keyboard()
    )
    return ADD_MEDIA

async def add_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        file_id = context.user_data['post']['file_id']
        bot_username = (await context.bot.get_me()).username
        botlink = f"https://t.me/{bot_username}?start={file_id}"
        
        if query.data == 'media_photo':
            await query.edit_message_text(
                f"📷 <b>Отправьте фото</b>\n\n"
                f"🔗 <b>Ссылка на файл:</b>\n"
                f"<code>{botlink}</code>\n\n"
                f"Отправьте фото для поста:",
                parse_mode=ParseMode.HTML
            )
            return ADD_MEDIA
            
        elif query.data == 'media_video':
            await query.edit_message_text(
                f"🎬 <b>Отправьте видео</b>\n\n"
                f"🔗 <b>Ссылка на файл:</b>\n"
                f"<code>{botlink}</code>\n\n"
                f"Отправьте видео для поста:",
                parse_mode=ParseMode.HTML
            )
            return ADD_MEDIA
            
        elif query.data == 'media_gif':
            await query.edit_message_text(
                f"🎞 <b>Отправьте GIF</b>\n\n"
                f"🔗 <b>Ссылка на файл:</b>\n"
                f"<code>{botlink}</code>\n\n"
                f"Отправьте GIF для поста:",
                parse_mode=ParseMode.HTML
            )
            return ADD_MEDIA
            
        elif query.data == 'media_skip':
            context.user_data['post']['media_type'] = None
            await query.edit_message_text(
                f"⏭ Медиа пропущено.\n\n"
                f"🔗 <b>Ссылка на файл:</b>\n"
                f"<code>{botlink}</code>\n\n"
                f"Введите описание поста (или нажмите кнопку):",
                parse_mode=ParseMode.HTML,
                reply_markup=desc_keyboard()
            )
            return ADD_DESC
            
        elif query.data == 'media_none':
            context.user_data['post']['media_type'] = 'none'
            context.user_data['post']['media_path'] = ""
            context.user_data['post']['media_id'] = ""
            await query.edit_message_text(
                f"❌ Пост без медиа.\n\n"
                f"🔗 <b>Ссылка на файл:</b>\n"
                f"<code>{botlink}</code>\n\n"
                f"Введите описание поста (или нажмите кнопку):",
                parse_mode=ParseMode.HTML,
                reply_markup=desc_keyboard()
            )
            return ADD_DESC
    elif update.message:
        message = update.message
        
        if message.photo:
            photo = message.photo[-1]
            file = await photo.get_file()
            media_path = os.path.join(MEDIA_DIR, f"{uuid4()}.jpg")
            await file.download_to_drive(media_path)
            
            context.user_data['post']['media_type'] = 'photo'
            context.user_data['post']['media_path'] = media_path
            context.user_data['post']['media_id'] = photo.file_id
            
            file_id = context.user_data['post']['file_id']
            bot_username = (await context.bot.get_me()).username
            botlink = f"https://t.me/{bot_username}?start={file_id}"
            
            await message.reply_text(
                f"✅ Фото сохранено!\n\n"
                f"🔗 <b>Ссылка на файл:</b>\n"
                f"<code>{botlink}</code>\n\n"
                f"Введите описание поста (или нажмите кнопку):",
                parse_mode=ParseMode.HTML,
                reply_markup=desc_keyboard()
            )
            return ADD_DESC
        
        elif message.video:
            video = message.video
            file = await video.get_file()
            media_path = os.path.join(MEDIA_DIR, f"{uuid4()}.mp4")
            await file.download_to_drive(media_path)
            
            context.user_data['post']['media_type'] = 'video'
            context.user_data['post']['media_path'] = media_path
            context.user_data['post']['media_id'] = video.file_id
            
            file_id = context.user_data['post']['file_id']
            bot_username = (await context.bot.get_me()).username
            botlink = f"https://t.me/{bot_username}?start={file_id}"
            
            await message.reply_text(
                f"✅ Видео сохранено!\n\n"
                f"🔗 <b>Ссылка на файл:</b>\n"
                f"<code>{botlink}</code>\n\n"
                f"Введите описание поста (или нажмите кнопку):",
                parse_mode=ParseMode.HTML,
                reply_markup=desc_keyboard()
            )
            return ADD_DESC
        
        elif message.animation:
            gif = message.animation
            file = await gif.get_file()
            media_path = os.path.join(MEDIA_DIR, f"{uuid4()}.gif")
            await file.download_to_drive(media_path)
            
            context.user_data['post']['media_type'] = 'gif'
            context.user_data['post']['media_path'] = media_path
            context.user_data['post']['media_id'] = gif.file_id
            
            file_id = context.user_data['post']['file_id']
            bot_username = (await context.bot.get_me()).username
            botlink = f"https://t.me/{bot_username}?start={file_id}"
            
            await message.reply_text(
                f"✅ GIF сохранен!\n\n"
                f"🔗 <b>Ссылка на файл:</b>\n"
                f"<code>{botlink}</code>\n\n"
                f"Введите описание поста (или нажмите кнопку):",
                parse_mode=ParseMode.HTML,
                reply_markup=desc_keyboard()
            )
            return ADD_DESC
    
    return ADD_MEDIA

async def add_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        file_id = context.user_data['post']['file_id']
        bot_username = (await context.bot.get_me()).username
        botlink = f"https://t.me/{bot_username}?start={file_id}"
        
        if query.data == 'skip_desc':
            context.user_data['post']['description'] = ""
            await query.edit_message_text(
                f"⏭ Описание пропущено.\n\n"
                f"🔗 <b>Ссылка на файл:</b>\n"
                f"<code>{botlink}</code>\n\n"
                f"Настройте пост с помощью клавиатуры:",
                parse_mode=ParseMode.HTML,
                reply_markup=admin_kb()
            )
            return ADMIN_PANEL
            
        elif query.data == 'back_desc':
            await query.edit_message_text(
                f"🖼 Выберите тип медиа для поста:\n\n"
                f"🔗 <b>Ссылка на файл:</b>\n"
                f"<code>{botlink}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=media_type_keyboard()
            )
            return ADD_MEDIA
    elif update.message:
        context.user_data['post']['description'] = update.message.text
        
        file_id = context.user_data['post']['file_id']
        bot_username = (await context.bot.get_me()).username
        botlink = f"https://t.me/{bot_username}?start={file_id}"
        
        await update.message.reply_text(
            f"✅ Описание сохранено!\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>\n\n"
            f"Настройте пост с помощью клавиатуры:",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_kb()
        )
        return ADMIN_PANEL
    
    return ADD_DESC

# ========== РЕДАКТИРОВАНИЕ ==========
async def edit_title_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для редактирования заголовка"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        file_id = context.user_data['post']['file_id']
        bot_username = (await context.bot.get_me()).username
        botlink = f"https://t.me/{bot_username}?start={file_id}"
        
        await query.edit_message_text(
            f"✏️ <b>Редактирование заголовка</b>\n\n"
            f"Текущий заголовок: {context.user_data['post']['title']}\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>\n\n"
            f"Введите новый заголовок:",
            parse_mode=ParseMode.HTML
        )
        return EDIT_TITLE
    
    elif update.message:
        # Сохраняем новый заголовок
        new_title = update.message.text
        context.user_data['post']['title'] = new_title
        
        file_id = context.user_data['post']['file_id']
        bot_username = (await context.bot.get_me()).username
        botlink = f"https://t.me/{bot_username}?start={file_id}"
        
        await update.message.reply_text(
            f"✅ Заголовок изменен!\n\n"
            f"Новый заголовок: {new_title}\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>\n\n"
            f"Настройте пост с помощью клавиатуры:",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_kb()
        )
        return ADMIN_PANEL
    
    return EDIT_TITLE

async def edit_description_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для редактирования описания"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        file_id = context.user_data['post']['file_id']
        bot_username = (await context.bot.get_me()).username
        botlink = f"https://t.me/{bot_username}?start={file_id}"
        
        current_desc = context.user_data['post'].get('description', '')
        if not current_desc:
            current_desc = "Описание отсутствует"
        
        await query.edit_message_text(
            f"📝 <b>Редактирование описания</b>\n\n"
            f"Текущее описание: {current_desc}\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>\n\n"
            f"Введите новое описание:",
            parse_mode=ParseMode.HTML
        )
        return EDIT_DESC
    
    elif update.message:
        # Сохраняем новое описание
        new_desc = update.message.text
        context.user_data['post']['description'] = new_desc
        
        file_id = context.user_data['post']['file_id']
        bot_username = (await context.bot.get_me()).username
        botlink = f"https://t.me/{bot_username}?start={file_id}"
        
        await update.message.reply_text(
            f"✅ Описание изменено!\n\n"
            f"Новое описание: {new_desc}\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>\n\n"
            f"Настройте пост с помощью клавиатуры:",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_kb()
        )
        return ADMIN_PANEL
    
    return EDIT_DESC

async def edit_buttons_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню редактирования кнопок"""
    query = update.callback_query
    await query.answer()
    
    post = context.user_data['post']
    file_id = post['file_id']
    bot_username = (await context.bot.get_me()).username
    botlink = f"https://t.me/{bot_username}?start={file_id}"
    
    # Создаем клавиатуру для управления кнопками
    keyboard = []
    
    # Показываем текущие кнопки
    buttons = post.get('buttons', [])
    if buttons:
        for i, btn in enumerate(buttons):
            keyboard.append([InlineKeyboardButton(
                f"✏️ Кнопка {i+1}: {btn['label']}", 
                callback_data=f'editbtn_{i}'
            )])
    
    # Кнопки действий
    action_buttons = []
    action_buttons.append(InlineKeyboardButton("➕ Добавить", callback_data='add_btn'))
    if buttons:
        action_buttons.append(InlineKeyboardButton("🗑 Очистить все", callback_data='clear_buttons'))
    
    keyboard.append(action_buttons)
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='back_to_admin')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🔘 <b>Редактирование кнопок</b>\n\n"
        f"Текущие кнопки: {len(buttons)} шт.\n\n"
        f"🔗 <b>Ссылка на файл:</b>\n"
        f"<code>{botlink}</code>\n\n"
        f"Выберите действие:",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
    return EDIT_BUTTONS

async def clear_all_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очищает все кнопки"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['post']['buttons'] = []
    
    file_id = context.user_data['post']['file_id']
    bot_username = (await context.bot.get_me()).username
    botlink = f"https://t.me/{bot_username}?start={file_id}"
    
    await query.edit_message_text(
        f"✅ Все кнопки удалены!\n\n"
        f"🔗 <b>Ссылка на файл:</b>\n"
        f"<code>{botlink}</code>\n\n"
        f"Настройте пост с помощью клавиатуры:",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_kb()
    )
    return ADMIN_PANEL

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    post = context.user_data['post']
    
    file_id = post['file_id']
    bot_username = (await context.bot.get_me()).username
    botlink = f"https://t.me/{bot_username}?start={file_id}"

    if query.data == "set_media":
        await query.edit_message_text(
            f"🖼 <b>Выберите тип медиа:</b>\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=media_type_keyboard()
        )
        return ADD_MEDIA

    elif query.data == "edit_title":
        return await edit_title_handler(update, context)

    elif query.data == "edit_description":
        return await edit_description_handler(update, context)

    elif query.data == "edit_buttons":
        return await edit_buttons_menu(update, context)

    elif query.data == "clear_buttons":
        return await clear_all_buttons(update, context)

    elif query.data == "back_to_admin":
        await query.edit_message_text(
            f"🔧 <b>Настройка поста</b>\n\n"
            f"📱 Заголовок: {post['title']}\n"
            f"📝 Описание: {post.get('description', 'нет')[:50]}\n"
            f"🔘 Кнопок: {len(post.get('buttons', []))}\n"
            f"💧 Водяной знак: {'✅' if post['watermark'] != 'none' else '❌'}\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>\n\n"
            f"Выберите что хотите изменить:",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_kb()
        )
        return ADMIN_PANEL

    elif query.data == "set_watermark":
        avatar_status = "✅ Есть" if os.path.exists(CUSTOM_AVATAR) else "❌ Нет (будет использована дефолтная)"
        
        await query.edit_message_text(
            f"💎 <b>СТИЛЬНЫЙ ВОДЯНОЙ ЗНАК</b>\n\n"
            f"<b>Аватарка канала:</b> {avatar_status}\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>\n\n"
            "<b>Что будет:</b>\n"
            "✅ <b>Аватарка</b> - круглая в правом верхнем углу\n"
            "✅ <b>Название</b> - яркое под аватаркой\n"
            "✅ <b>Ссылка на канал</b> - в правом нижнем углу",
            parse_mode=ParseMode.HTML,
            reply_markup=watermark_keyboard()
        )
        return ADD_WATERMARK

    elif query.data == "watermark_avatar":
        post['watermark'] = 'avatar'
        
        if os.path.exists(CUSTOM_AVATAR):
            avatar_msg = "✅ Будет использована ВАША аватарка!"
        else:
            avatar_msg = "⚠️ Будет использована дефолтная аватарка!"
        
        await query.edit_message_text(
            f"{avatar_msg}\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>\n\n"
            "💎 <b>СТИЛЬНЫЕ ФИЧИ:</b>\n"
            "1. <b>Круглая аватарка</b> в правом верхнем углу\n"
            "2. <b>Название</b> ЯРКИМ цветом под аватаркой\n"
            "3. <b>Ссылка на канал</b> @ANDRO_FILE в правом нижнем углу\n\n"
            "Настройте пост:",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_kb()
        )
        return ADMIN_PANEL

    elif query.data == "watermark_no":
        post['watermark'] = 'none'
        await query.edit_message_text(
            f"❌ Водяной знак не будет добавлен.\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>\n\n"
            f"Настройте пост:",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_kb()
        )
        return ADMIN_PANEL

    elif query.data == "preview":
        await show_preview(query, context)
        
        await query.message.reply_text(
            f"Используйте клавиатуру:\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>\n\n"
            f"📱 Заголовок: {post['title']}\n"
            f"📝 Описание: {post.get('description', 'нет')[:50]}",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_kb()
        )
        return ADMIN_PANEL

    elif query.data == "add_btn":
        context.user_data['editbtn'] = None
        await query.edit_message_text(
            f"Введите текст для кнопки:\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>",
            parse_mode=ParseMode.HTML
        )
        return ADD_BTN_LABEL

    elif query.data.startswith("editbtn_"):
        idx = int(query.data.split("_")[1])
        context.user_data['editbtn'] = idx
        btn = post['buttons'][idx]
        await query.edit_message_text(
            f"Редактируем кнопку №{idx + 1}: [{btn['label']}]\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>\n\n"
            f"Введите новое название:",
            parse_mode=ParseMode.HTML
        )
        return ADD_BTN_URL

    elif query.data == "back":
        await show_preview(query, context)
        
        await query.message.reply_text(
            f"Используйте клавиатуру:\n\n"
            f"🔗 <b>Ссылка на файл:</b>\n"
            f"<code>{botlink}</code>\n\n"
            f"📱 Заголовок: {post['title']}\n"
            f"📝 Описание: {post.get('description', 'нет')[:50]}",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_kb()
        )
        return ADMIN_PANEL

    elif query.data == "publish":
        try:
            caption = render_post(post)
            
            media_path = post.get('media_path')
            watermark_type = post.get('watermark', 'avatar')
            title = post.get('title', '')
            
            print(f"🚀 Публикация поста...")
            
            # Создаем кнопки для поста
            reply_markup = build_buttons(post) if post.get('buttons') else None
            
            if post['media_type'] == 'photo' and media_path and os.path.exists(media_path):
                if watermark_type != 'none':
                    watermarked_path = add_watermark_to_image(media_path, watermark_type, title)
                else:
                    watermarked_path = media_path
                
                with open(watermarked_path, "rb") as img:
                    sent_message = await context.bot.send_photo(
                        chat_id=CHANNEL_ID,
                        photo=img,
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup
                    )
                    
                    post_id = sent_message.message_id
                    print(f"✅ Пост опубликован! ID поста: {post_id}")
                    
                    # Создаем ссылку на пост
                    channel_name = CHANNEL_USERNAME.replace("@", "")
                    post_link = f"https://t.me/{channel_name}/{post_id}"
                    
                    await asyncio.sleep(1)
                    
                    # Добавляем кнопку "Поделиться"
                    share_button = [InlineKeyboardButton("📢 Поделиться", url=f"https://t.me/share/url?url={post_link}")]
                    
                    if reply_markup:
                        existing_buttons = list(reply_markup.inline_keyboard)
                        existing_buttons.append(share_button)
                        new_markup = InlineKeyboardMarkup(existing_buttons)
                    else:
                        new_markup = InlineKeyboardMarkup([share_button])
                    
                    await context.bot.edit_message_reply_markup(
                        chat_id=CHANNEL_ID,
                        message_id=post_id,
                        reply_markup=new_markup
                    )
                    
                    print(f"🔗 Ссылка на пост: {post_link}")
                
                if watermarked_path != media_path and os.path.exists(watermarked_path):
                    try:
                        os.remove(watermarked_path)
                    except:
                        pass
            
            elif post['media_type'] == 'video' and media_path and os.path.exists(media_path):
                with open(media_path, "rb") as video:
                    sent_message = await context.bot.send_video(
                        chat_id=CHANNEL_ID,
                        video=video,
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup
                    )
                    
                    post_id = sent_message.message_id
                    channel_name = CHANNEL_USERNAME.replace("@", "")
                    post_link = f"https://t.me/{channel_name}/{post_id}"
                    
                    await asyncio.sleep(1)
                    
                    share_button = [InlineKeyboardButton("📢 Поделиться", url=f"https://t.me/share/url?url={post_link}")]
                    
                    if reply_markup:
                        existing_buttons = list(reply_markup.inline_keyboard)
                        existing_buttons.append(share_button)
                        new_markup = InlineKeyboardMarkup(existing_buttons)
                    else:
                        new_markup = InlineKeyboardMarkup([share_button])
                    
                    await context.bot.edit_message_reply_markup(
                        chat_id=CHANNEL_ID,
                        message_id=post_id,
                        reply_markup=new_markup
                    )
            
            elif post['media_type'] == 'gif' and media_path and os.path.exists(media_path):
                with open(media_path, "rb") as gif:
                    sent_message = await context.bot.send_animation(
                        chat_id=CHANNEL_ID,
                        animation=gif,
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup
                    )
                    
                    post_id = sent_message.message_id
                    channel_name = CHANNEL_USERNAME.replace("@", "")
                    post_link = f"https://t.me/{channel_name}/{post_id}"
                    
                    await asyncio.sleep(1)
                    
                    share_button = [InlineKeyboardButton("📢 Поделиться", url=f"https://t.me/share/url?url={post_link}")]
                    
                    if reply_markup:
                        existing_buttons = list(reply_markup.inline_keyboard)
                        existing_buttons.append(share_button)
                        new_markup = InlineKeyboardMarkup(existing_buttons)
                    else:
                        new_markup = InlineKeyboardMarkup([share_button])
                    
                    await context.bot.edit_message_reply_markup(
                        chat_id=CHANNEL_ID,
                        message_id=post_id,
                        reply_markup=new_markup
                    )
            
            else:
                sent_message = await context.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
                
                post_id = sent_message.message_id
                channel_name = CHANNEL_USERNAME.replace("@", "")
                post_link = f"https://t.me/{channel_name}/{post_id}"
                
                await asyncio.sleep(1)
                
                share_button = [InlineKeyboardButton("📢 Поделиться", url=f"https://t.me/share/url?url={post_link}")]
                
                if reply_markup:
                    existing_buttons = list(reply_markup.inline_keyboard)
                    existing_buttons.append(share_button)
                    new_markup = InlineKeyboardMarkup(existing_buttons)
                else:
                    new_markup = InlineKeyboardMarkup([share_button])
                
                await context.bot.edit_message_reply_markup(
                    chat_id=CHANNEL_ID,
                    message_id=post_id,
                    reply_markup=new_markup
                )
            
            channel_name = CHANNEL_USERNAME.replace("@", "")
            post_link = f"https://t.me/{channel_name}/{post_id}"
            
            await query.edit_message_text(
                f"✅ <b>Пост опубликован!</b>\n\n"
                f"🔗 <b>Ссылка на пост:</b>\n"
                f"<code>{post_link}</code>",
                parse_mode=ParseMode.HTML
            )
            
        except Exception as e:
            print(f"❌ ОШИБКА: {e}")
            import traceback
            traceback.print_exc()
            await query.edit_message_text(f"❌ Ошибка: {str(e)[:100]}")
        
        return ConversationHandler.END

    elif query.data == "cancel":
        await query.edit_message_text("❌ Создание поста отменено.")
        return ConversationHandler.END

    await query.edit_message_text("❓ Неизвестная команда...")
    return ADMIN_PANEL

async def add_btn_label(update: Update, context: ContextTypes.DEFAULT_TYPE):
    label = update.message.text
    context.user_data['btn_tmp_label'] = label
    
    file_id = context.user_data['post']['file_id']
    bot_username = (await context.bot.get_me()).username
    botlink = f"https://t.me/{bot_username}?start={file_id}"
    
    await update.message.reply_text(
        f"Введите URL для кнопки:\n\n"
        f"🔗 <b>Ссылка на файл:</b>\n"
        f"<code>{botlink}</code>",
        parse_mode=ParseMode.HTML
    )
    return ADD_BTN_URL

async def add_btn_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    label = context.user_data.get('btn_tmp_label', '')
    idx = context.user_data.get('editbtn')
    
    if idx is not None:
        context.user_data['post']['buttons'][idx] = {"label": label, "url": url}
        context.user_data['editbtn'] = None
    else:
        if not label:
            await update.message.reply_text("❌ Ошибка: не найден текст кнопки.")
            return ADMIN_PANEL
        context.user_data['post'].setdefault("buttons", []).append({"label": label, "url": url})
    
    await show_preview(update, context)
    
    file_id = context.user_data['post']['file_id']
    bot_username = (await context.bot.get_me()).username
    botlink = f"https://t.me/{bot_username}?start={file_id}"
    
    await update.message.reply_text(
        f"✅ Кнопка {'изменена' if idx is not None else 'добавлена'}!\n\n"
        f"🔗 <b>Ссылка на файл:</b>\n"
        f"<code>{botlink}</code>\n\n"
        f"Настройте пост с помощью клавиатуры:",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_kb()
    )
    return ADMIN_PANEL

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Действие отменено.")
    return ConversationHandler.END

async def filebot_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) == 1 and args[0].isdigit():
        db = load_db()
        file_key = args[0]
        entry = db["files"].get(file_key)
        if entry and "file_id" in entry:
            caption = f"{SIGNATURE}"
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=entry["file_id"],
                caption=caption
            )
        else:
            await update.message.reply_text("Файл не найден.")
    
    else:
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("⛔ Этот бот приватный.")
            return
        
        user = update.effective_user
        username = user.username if user.username else user.first_name
        
        db = load_db()
        files = db["files"]
        
        response = f"👋 {username}!\n"
        response += f"📊 Файлов: {len(files)}\n"
        response += f"🔢 Последний ID: {db['last_id']}\n\n"
        response += "📋 <b>Команды:</b>\n"
        response += "/post - создать пост для последнего файла\n"
        response += "/del ID - удалить файл\n"
        response += "/clear - очистить все файлы"
        
        await update.message.reply_text(response, parse_mode=ParseMode.HTML)

# ------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ -------
def render_post(post):
    text = ""
    if post.get('title'):
        text += f"<b>{post['title']}</b>\n"
        text += f"<b>____________________________________</b>\n"
    
    if post.get('description'):
        text += f"📝 <b>Описание:</b>\n"
        text += f"{post['description']}\n"
    
    text += f"\n🔗 {CHANNEL_USERNAME}\n"
    text += f"<b>===========================</b>"
    return text

def build_buttons(post):
    buttons = post.get("buttons", [])
    
    if not buttons:
        return None
    
    rows = []
    for i in range(0, len(buttons), 2):
        row = []
        btn_a = buttons[i]
        row.append(InlineKeyboardButton(btn_a["label"], url=btn_a["url"]))
        if i + 1 < len(buttons):
            btn_b = buttons[i + 1]
            row.append(InlineKeyboardButton(btn_b["label"], url=btn_b["url"]))
        rows.append(row)
    return InlineKeyboardMarkup(rows)

def admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 Медиа", callback_data='set_media')],
        [InlineKeyboardButton("✏️ Заголовок", callback_data='edit_title'),
         InlineKeyboardButton("📝 Описание", callback_data='edit_description')],
        [InlineKeyboardButton("🔘 Кнопки", callback_data='edit_buttons')],
        [InlineKeyboardButton("💧 Водяной знак", callback_data='set_watermark')],
        [InlineKeyboardButton("📤 Опубликовать", callback_data='publish'),
         InlineKeyboardButton("👁 Предпросмотр", callback_data='preview')],
        [InlineKeyboardButton("❌ Отмена", callback_data='cancel')]
    ])

def media_type_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 Фото", callback_data='media_photo')],
        [InlineKeyboardButton("🎬 Видео", callback_data='media_video')],
        [InlineKeyboardButton("🎞 GIF", callback_data='media_gif')],
        [InlineKeyboardButton("⏭ Пропустить медиа", callback_data='media_skip')],
        [InlineKeyboardButton("❌ Без медиа", callback_data='media_none')]
    ])

def watermark_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ С аватаркой", callback_data='watermark_avatar')],
        [InlineKeyboardButton("❌ Без водяного знака", callback_data='watermark_no')],
        [InlineKeyboardButton("← Назад", callback_data='back')]
    ])

def desc_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭ Пропустить описание", callback_data='skip_desc')],
        [InlineKeyboardButton("← Назад", callback_data='back_desc')]
    ])

async def show_preview(update, context):
    post = context.user_data['post']
    try:
        if hasattr(update, "message") and update.message:
            send_to = update.message
        else:
            send_to = update
        
        caption = render_post(post)
        
        media_path = post.get('media_path')
        
        if post['media_type'] == 'photo' and media_path and os.path.exists(media_path):
            with open(media_path, "rb") as img:
                await send_to.reply_photo(
                    img,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=build_buttons(post)
                )
        
        elif post['media_type'] == 'video' and media_path and os.path.exists(media_path):
            with open(media_path, "rb") as video:
                await send_to.reply_video(
                    video,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=build_buttons(post)
                )
        
        elif post['media_type'] == 'gif' and media_path and os.path.exists(media_path):
            with open(media_path, "rb") as gif:
                await send_to.reply_animation(
                    gif,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=build_buttons(post)
                )
        
        else:
            await send_to.reply_text(
                caption,
                parse_mode=ParseMode.HTML,
                reply_markup=build_buttons(post)
            )
            
    except Exception as e:
        print(f"Ошибка при показе превью: {e}")
        await send_to.reply_text(
            f"Ошибка при показе превью: {e}\n\n"
            f"Текст поста:\n{render_post(post)}",
            parse_mode=ParseMode.HTML,
            reply_markup=build_buttons(post)
        )

def create_default_avatar():
    """Создает стильную дефолтную аватарку в кружке"""
    try:
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Яркая заливка
        circle_color = (30, 144, 255)
        draw.ellipse([(20, 20), (size - 20, size - 20)], fill=circle_color)
        
        # Белая обводка
        draw.ellipse([(15, 15), (size - 15, size - 15)], outline=(255, 255, 255), width=5)
        
        # Буква A
        try:
            font = ImageFont.truetype("arialbd.ttf", 120)
        except:
            font = ImageFont.load_default()
        
        text = "A"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        position = ((size - text_width) // 2, (size - text_height) // 2)
        draw.text(position, text, font=font, fill=(255, 255, 255, 255))
        
        img.save(DEFAULT_AVATAR, "PNG")
        print(f"✅ Создана дефолтная аватарка")
        return DEFAULT_AVATAR
        
    except Exception as e:
        print(f"❌ Ошибка при создании аватарки: {e}")
        return None

def get_avatar_path():
    """Возвращает путь к аватарке"""
    if os.path.exists(CUSTOM_AVATAR):
        return CUSTOM_AVATAR
    else:
        if not os.path.exists(DEFAULT_AVATAR):
            create_default_avatar()
        return DEFAULT_AVATAR

def make_circular_avatar(avatar_image):
    """Преобразует изображение в круговую аватарку"""
    try:
        size = avatar_image.size[0]
        
        mask = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse([(0, 0), (size, size)], fill=255)
        
        circular_avatar = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        circular_avatar.paste(avatar_image, (0, 0), mask)
        
        # Добавляем белую обводку
        border_size = 10
        bordered_size = size + border_size * 2
        bordered_avatar = Image.new('RGBA', (bordered_size, bordered_size), (0, 0, 0, 0))
        draw_border = ImageDraw.Draw(bordered_avatar)
        
        draw_border.ellipse([(0, 0), (bordered_size, bordered_size)], outline=(255, 255, 255), width=5)
        bordered_avatar.paste(circular_avatar, (border_size, border_size), circular_avatar)
        
        return bordered_avatar
    except Exception as e:
        return avatar_image

def get_random_bright_color():
    """Возвращает случайный яркий цвет"""
    bright_colors = [
        (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
        (255, 0, 255), (0, 255, 255), (255, 128, 0), (255, 0, 128),
        (128, 0, 255), (0, 255, 128),
    ]
    return random.choice(bright_colors)

def get_font(size, bold=True):
    """Получает шрифт"""
    try:
        font_paths = [
            os.path.join(FONT_DIR, "Montserrat-Bold.ttf"),
            os.path.join(FONT_DIR, "Roboto-Bold.ttf"),
            "arialbd.ttf", "arial.ttf"
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
        
        return ImageFont.load_default()
        
    except:
        return ImageFont.load_default()

def add_watermark_to_image(image_path, watermark_type="avatar", title=""):
    """Добавляет водяной знак - аватарка сверху справа, ссылка внизу справа"""
    try:
        if watermark_type == "none":
            return image_path
        
        image = Image.open(image_path).convert('RGBA')
        width, height = image.size
        
        watermark = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(watermark)
        
        if watermark_type == "avatar":
            avatar_path = get_avatar_path()
            
            if avatar_path and os.path.exists(avatar_path):
                avatar = Image.open(avatar_path).convert('RGBA')
                avatar_size = min(120, max(70, min(width, height) // 10))
                avatar = avatar.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
                circular_avatar = make_circular_avatar(avatar)
                
                # Аватарка в правом верхнем углу
                margin = 20
                avatar_position = (width - avatar_size - margin - 10, margin)
                watermark.paste(circular_avatar, avatar_position, circular_avatar)
                
                # Название под аватаркой
                if title:
                    title_color = get_random_bright_color()
                    title_font_size = min(28, max(16, min(width, height) // 25))
                    title_font = get_font(title_font_size, bold=True)
                    
                    if len(title) > 25:
                        title_text = title[:22] + "..."
                    else:
                        title_text = title
                    
                    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
                    title_width = title_bbox[2] - title_bbox[0]
                    title_position = (width - title_width - margin, avatar_position[1] + avatar_size + 5)
                    
                    # Тень для названия
                    for offset in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                        draw.text((title_position[0] + offset[0], title_position[1] + offset[1]),
                                title_text, font=title_font, fill=(0, 0, 0, 200))
                    
                    draw.text(title_position, title_text, font=title_font, fill=(*title_color, 255))
                    
                    # Ссылка на канал в правом НИЖНЕМ углу
                    link_font_size = max(14, min(22, title_font_size - 2))
                    link_font = get_font(link_font_size, bold=True)
                    link_text = CHANNEL_USERNAME
                    
                    link_bbox = draw.textbbox((0, 0), link_text, font=link_font)
                    link_width = link_bbox[2] - link_bbox[0]
                    link_height = link_bbox[3] - link_bbox[1]
                    
                    # Позиция в правом нижнем углу
                    link_margin = 30
                    link_position = (
                        width - link_width - link_margin,
                        height - link_height - link_margin
                    )
                    
                    # Фон для ссылки
                    bg_padding = 8
                    draw.rounded_rectangle(
                        [link_position[0] - bg_padding, link_position[1] - bg_padding,
                         link_position[0] + link_width + bg_padding, link_position[1] + link_height + bg_padding],
                        radius=8, fill=(0, 0, 0, 180)
                    )
                    
                    # Белая ссылка
                    draw.text(link_position, link_text, font=link_font, fill=(255, 255, 255, 255))
        
        watermarked = Image.alpha_composite(image, watermark)
        watermarked_path = os.path.join(MEDIA_DIR, f"watermarked_{uuid4()}.png")
        watermarked.save(watermarked_path, "PNG")
        
        return watermarked_path
        
    except Exception as e:
        print(f"❌ Ошибка водяного знака: {e}")
        return image_path

# =========== MAIN ==========
def main():
    print("=" * 60)
    print("💎 ЗАПУСК БОТА")
    print("=" * 60)
    print(f"👑 Бот работает ТОЛЬКО для ID: {ADMIN_ID}")
    print(f"📢 Канал: {CHANNEL_USERNAME}")
    print("=" * 60)
    
    create_default_avatar()
    
    if TELEGRAM_TOKEN == "ВАШ_ТОКЕН_ЗДЕСЬ":
        print("❌ ОШИБКА: Замените TELEGRAM_TOKEN!")
        return
    
    try:
        from PIL import Image
        print("✅ Библиотека PIL установлена")
    except ImportError:
        print("❌ Установите PIL: pip install Pillow")
        return
    
    db = load_db()
    print(f"📊 Файлов в базе: {len(db['files'])}")
    print(f"🔢 Последний ID: {db['last_id']}")
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # ConversationHandler для /post
    conv = ConversationHandler(
        entry_points=[
            CommandHandler('post', adm_cmd),
            CallbackQueryHandler(start_create_post, pattern='^create_post_')
        ],
        states={
            ADD_MEDIA: [
                CallbackQueryHandler(add_media),
                MessageHandler(filters.PHOTO | filters.VIDEO | filters.ANIMATION, add_media),
            ],
            ADD_DESC: [
                CallbackQueryHandler(add_desc),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_desc),
            ],
            ADMIN_PANEL: [
                CallbackQueryHandler(admin_panel),
            ],
            ADD_WATERMARK: [
                CallbackQueryHandler(admin_panel),
            ],
            ADD_BTN_LABEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_btn_label),
            ],
            ADD_BTN_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_btn_url),
            ],
            EDIT_TITLE: [
                CallbackQueryHandler(edit_title_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_title_handler),
            ],
            EDIT_DESC: [
                CallbackQueryHandler(edit_description_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_description_handler),
            ],
            EDIT_BUTTONS: [
                CallbackQueryHandler(admin_panel),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )
    
    # Регистрируем команды
    app.add_handler(CommandHandler('start', filebot_start))
    app.add_handler(CommandHandler('del', del_file))
    app.add_handler(CommandHandler('clear', clear_files))
    app.add_handler(CallbackQueryHandler(clear_callback, pattern='^clear_'))
    app.add_handler(MessageHandler(filters.Document.ALL & filters.ChatType.PRIVATE, handle_apk))
    app.add_handler(conv)

    print("✅ БОТ ЗАПУЩЕН!")
    print("=" * 60)
    print("📋 КОМАНДЫ:")
    print("   • /start - приветствие")
    print("   • /post - создать пост для последнего файла")
    print("   • /del ID - удалить файл")
    print("   • /clear - очистить все файлы")
    print("=" * 60)
    print("✏️ ПОЛНОЕ РЕДАКТИРОВАНИЕ:")
    print("   • Заголовок - можно изменить")
    print("   • Описание - можно изменить")  
    print("   • Кнопки - можно добавить/изменить/удалить")
    print("=" * 60)
    print("🖼 ВОДЯНОЙ ЗНАК:")
    print("   • Аватарка - в правом верхнем углу")
    print("   • Название - под аватаркой")
    print("   • Ссылка на канал - в правом НИЖНЕМ углу")
    print("=" * 60)
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Бот остановлен")
    except Exception as e:
        print(f"\n\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
