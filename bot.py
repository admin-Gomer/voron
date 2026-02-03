import os
import json
from uuid import uuid4
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, CallbackQueryHandler, ContextTypes
)

# ======= НАСТРОЙКИ =======
TELEGRAM_TOKEN = "5807314796:AAGjTJMoU6_gSJok"
ADMIN_ID = 1129009422         # Ваш user id (число)
CHANNEL_ID = -1003405549440 # id канала/чата для публикации постов
FILE_DB = "file_db.json"
SIGNATURE = "@ANDRO_FILE"
MEDIA_DIR = "admin_media"
os.makedirs(MEDIA_DIR, exist_ok=True)
# =========================

# ------ Состояния админки ------
ADD_MEDIA, ADD_TITLE, ADD_DESC, ADD_BTN_LABEL, ADD_BTN_URL, ADMIN_PANEL, BTN_EDIT_LABEL, BTN_EDIT_URL = range(8)

# ------ БЛОК FILEBOT ------
def load_db():
    """Загружает базу данных файлов"""
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
                for key in old_files.keys():
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
    """Сохраняет базу данных файлов"""
    with open(FILE_DB, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

async def handle_apk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка APK файлов - ТОЛЬКО ДЛЯ АДМИНА"""
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
                "downloads": 0,
                "uploaded_at": message.date.isoformat() if message.date else ""
            }
            
            db["last_id"] = next_id
            save_db(db)
            
            bot_username = (await context.bot.get_me()).username
            botlink = f"https://t.me/{bot_username}?start={file_id}"
            
            markup = (
                f"✅ Файл сохранен!\n\n"
                f"📂 ID файла: {file_id}\n"
                f"📂 Имя файла: {message.document.file_name}\n"
                f"📦 Размер: {message.document.file_size // 1024 if message.document.file_size else 0} KB\n\n"
                f"🔗 Ссылка для скачивания:\n"
                f"<code>{botlink}</code>\n\n"
                f"📋 Быстрая команда:\n"
                f"/info {file_id}"
            )
            
            await message.reply_text(markup, parse_mode=ParseMode.HTML)
        except Exception as e:
            await message.reply_text(f"Ошибка: {e}")
    else:
        await message.reply_text("Это не .apk файл. Пришли .apk документ!")

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список файлов - ТОЛЬКО ДЛЯ АДМИНА"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Этот бот приватный.")
        return
    
    db = load_db()
    files = db["files"]
    
    if files:
        response = "📋 <b>Список загруженных файлов:</b>\n\n"
        for key, value in sorted(files.items(), key=lambda x: int(x[0])):
            downloads = value.get('downloads', 0)
            response += f"📁 <b>ID {key}:</b> {value['file_name']}\n"
            response += f"⬇️ Скачиваний: {downloads}\n\n"
        await update.message.reply_text(response, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("Нет загруженных файлов.")

async def file_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о файле - ТОЛЬКО ДЛЯ АДМИНА"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Этот бот приватный.")
        return
    
    args = context.args
    if len(args) == 1 and args[0].isdigit():
        db = load_db()
        file_key = args[0]
        entry = db["files"].get(file_key)
        if entry:
            downloads = entry.get('downloads', 0)
            uploaded_at = entry.get('uploaded_at', 'Неизвестно')[:10]
            
            bot_username = (await context.bot.get_me()).username
            botlink = f"https://t.me/{bot_username}?start={file_key}"
            
            response = (
                f"📊 <b>Информация о файле ID {file_key}:</b>\n\n"
                f"📂 Имя файла: {entry['file_name']}\n"
                f"⬇️ Скачиваний: {downloads}\n"
                f"📅 Загружен: {uploaded_at}\n\n"
                f"🔗 Ссылка для скачивания:\n"
                f"<code>{botlink}</code>"
            )
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("Файл не найден.")
    else:
        await update.message.reply_text("Используйте: /info ID")

async def clear_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очистка файлов - ТОЛЬКО ДЛЯ АДМИНА"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Этот бот приватный.")
        return
    
    db = load_db()
    if db["files"]:
        new_db = {"files": {}, "last_id": 0}
        save_db(new_db)
        await update.message.reply_text("✅ Все файлы были успешно удалены.")
    else:
        await update.message.reply_text("База данных уже пуста.")

async def del_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление файла - ТОЛЬКО ДЛЯ АДМИНА"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Этот бот приватный.")
        return
    
    args = context.args
    if len(args) == 1 and args[0].isdigit():
        db = load_db()
        file_key = args[0]
        if file_key in db["files"]:
            fname = db["files"][file_key]["file_name"]
            downloads = db["files"][file_key].get('downloads', 0)
            del db["files"][file_key]
            save_db(db)
            await update.message.reply_text(f"✅ Файл ID {file_key} ({fname}) удалён.\n📊 Было скачиваний: {downloads}")
        else:
            await update.message.reply_text("Файл с таким ID не найден.")
    else:
        await update.message.reply_text("Используйте: /del ID")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика - ТОЛЬКО ДЛЯ АДМИНА"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Этот бот приватный.")
        return
    
    db = load_db()
    files = db["files"]
    
    if not files:
        await update.message.reply_text("📭 Нет загруженных файлов.")
        return
    
    total_files = len(files)
    total_downloads = sum(file_data.get('downloads', 0) for file_data in files.values())
    
    sorted_files = sorted(files.items(), key=lambda x: x[1].get('downloads', 0), reverse=True)[:10]
    
    response = "📊 <b>Статистика скачиваний</b>\n\n"
    response += f"📁 Всего файлов: <b>{total_files}</b>\n"
    response += f"⬇️ Всего скачиваний: <b>{total_downloads}</b>\n"
    response += f"🔢 Последний ID: <b>{db['last_id']}</b>\n"
    
    if total_files > 0:
        avg_downloads = total_downloads / total_files
        response += f"📈 Среднее скачиваний на файл: <b>{avg_downloads:.1f}</b>\n\n"
    
    response += "🏆 <b>Топ-10 самых скачиваемых файлов:</b>\n\n"
    
    for i, (file_id, file_data) in enumerate(sorted_files, 1):
        downloads = file_data.get('downloads', 0)
        filename = file_data['file_name']
        if len(filename) > 30:
            filename = filename[:27] + "..."
        
        response += f"{i}. <b>ID {file_id}:</b> {filename}\n"
        response += f"   ⬇️ <b>{downloads}</b> скачиваний\n\n"
    
    recent_files = list(files.items())[-5:]
    if len(recent_files) > 0:
        response += "🆕 <b>Последние добавленные файлы:</b>\n\n"
        for file_id, file_data in recent_files[-5:]:
            downloads = file_data.get('downloads', 0)
            filename = file_data['file_name']
            if len(filename) > 25:
                filename = filename[:22] + "..."
            response += f"• ID {file_id}: {filename} (⬇️ {downloads})\n"
    
    await update.message.reply_text(response, parse_mode=ParseMode.HTML)

async def filebot_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - ПРЯМАЯ ВЫДАЧА ФАЙЛА БЕЗ ПРИВЕТСТВИЯ"""
    args = context.args
    if len(args) == 1 and args[0].isdigit():
        db = load_db()
        file_key = args[0]
        entry = db["files"].get(file_key)
        if entry and "file_id" in entry:
            entry['downloads'] = entry.get('downloads', 0) + 1
            save_db(db)
            
            caption = f"{SIGNATURE}"
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=entry["file_id"],
                caption=caption
            )
        else:
            await update.message.reply_text("Файл не найден.")
    else:
        # Если команда /start без аргументов - ТОЛЬКО ДЛЯ АДМИНА
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("⛔ Этот бот приватный.")
            return
        
        # Для админа показываем минимальную информацию
        user = update.effective_user
        username = user.username if user.username else user.first_name
        
        db = load_db()
        files = db["files"]
        
        if files:
            response = f"👋 Привет, {username}!\n"
            response += f"📊 Файлов в базе: {len(files)}\n"
            response += f"🔢 Последний ID: {db['last_id']}\n\n"
            response += "📋 <b>Команды:</b>\n"
            response += "/list - список файлов\n"
            response += "/stats - статистика\n"
            response += "/post - создать пост\n"
            response += "/info ID - информация о файле"
        else:
            response = (
                f"Привет, {username}!\n"
                "📁 Нет загруженных файлов.\n"
                "📎 Отправьте APK файл чтобы сохранить его."
            )
        
        await update.message.reply_text(response, parse_mode=ParseMode.HTML)

# ------- БЛОК АДМИНКИ (ОСТАЕТСЯ ТОЛЬКО ДЛЯ АДМИНА) -------
def render_post(post):
    text = ""
    if post.get('title'):
        text += f"<b>{post['title']}</b>\n"
        text += f"<b>____________________________________</b>\n"
    
    if post.get('description'):
        text += f"📝 <b>Описание:</b>\n"
        text += f"{post['description']}\n"
    
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
        [InlineKeyboardButton("📷 Фото/Видео/GIF", callback_data='set_media')],
        [InlineKeyboardButton("✏️ Заголовок", callback_data='set_title'),
         InlineKeyboardButton("📄 Описание", callback_data='set_desc')],
        [InlineKeyboardButton("🔘 Кнопки", callback_data='manage_buttons')],
        [InlineKeyboardButton("📤 Опубликовать", callback_data='publish'),
         InlineKeyboardButton("👁 Предпросмотр", callback_data='preview')],
        [InlineKeyboardButton("📊 Статистика", callback_data='stats_admin'),
         InlineKeyboardButton("❌ Отмена", callback_data='cancel')]
    ])

def media_type_keyboard():
    """Клавиатура для выбора типа медиа"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 Фото", callback_data='media_photo'),
         InlineKeyboardButton("🎬 Видео", callback_data='media_video'),
         InlineKeyboardButton("🎞 GIF", callback_data='media_gif')],
        [InlineKeyboardButton("⏭ Пропустить", callback_data='media_skip'),
         InlineKeyboardButton("❌ Без медиа", callback_data='media_none')]
    ])

def btn_manage_kb(post):
    kb = [[InlineKeyboardButton(f"✏ {i + 1}: {btn['label']}", callback_data=f'editbtn_{i}')]
          for i, btn in enumerate(post.get('buttons', []))]
    kb.append([InlineKeyboardButton("➕ Добавить", callback_data='add_btn')])
    kb.append([InlineKeyboardButton("← Назад", callback_data='back')])
    return InlineKeyboardMarkup(kb)

def edit_btn_kb(idx):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("↩ Название", callback_data=f'editbtn_label_{idx}')],
        [InlineKeyboardButton("🌐 URL", callback_data=f'editbtn_url_{idx}')],
        [InlineKeyboardButton("❌ Удалить", callback_data=f'delbtn_{idx}')],
        [InlineKeyboardButton("← Назад", callback_data='manage_buttons')]
    ])

async def adm_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создание поста - ТОЛЬКО ДЛЯ АДМИНА"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Доступ запрещён.")
        return ConversationHandler.END
    
    context.user_data['post'] = {
        "media_type": None,
        "media_path": "",
        "media_id": "",
        "title": "",
        "description": "",
        "buttons": []
    }
    
    await update.message.reply_text(
        "🖼 <b>Создание нового поста</b>\n\n"
        "Выберите тип медиа для поста или пропустите:",
        parse_mode=ParseMode.HTML,
        reply_markup=media_type_keyboard()
    )
    return ADD_MEDIA

async def add_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if query:
        await query.answer()
        
        if query.data == 'media_photo':
            await query.edit_message_text(
                "📷 <b>Отправьте фото</b>\n\n"
                "Отправьте фото для поста или /skip чтобы пропустить:",
                parse_mode=ParseMode.HTML
            )
            return ADD_MEDIA
            
        elif query.data == 'media_video':
            await query.edit_message_text(
                "🎬 <b>Отправьте видео</b>\n\n"
                "Отправьте видео для поста или /skip чтобы пропустить:",
                parse_mode=ParseMode.HTML
            )
            return ADD_MEDIA
            
        elif query.data == 'media_gif':
            await query.edit_message_text(
                "🎞 <b>Отправьте GIF</b>\n\n"
                "Отправьте GIF для поста или /skip чтобы пропустить:",
                parse_mode=ParseMode.HTML
            )
            return ADD_MEDIA
            
        elif query.data == 'media_skip':
            context.user_data['post']['media_type'] = None
            await query.edit_message_text(
                "⏭ Медиа пропущено.\n\n"
                "Теперь введите заголовок поста или /skip чтобы пропустить:"
            )
            return ADD_TITLE
            
        elif query.data == 'media_none':
            context.user_data['post']['media_type'] = 'none'
            context.user_data['post']['media_path'] = ""
            context.user_data['post']['media_id'] = ""
            await query.edit_message_text(
                "❌ Пост без медиа.\n\n"
                "Теперь введите заголовок поста или /skip чтобы пропустить:"
            )
            return ADD_TITLE
    
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
            
            await message.reply_text(
                "✅ Фото сохранено!\n\n"
                "Теперь введите заголовок поста или /skip чтобы пропустить:"
            )
            return ADD_TITLE
        
        elif message.video:
            video = message.video
            file = await video.get_file()
            media_path = os.path.join(MEDIA_DIR, f"{uuid4()}.mp4")
            await file.download_to_drive(media_path)
            
            context.user_data['post']['media_type'] = 'video'
            context.user_data['post']['media_path'] = media_path
            context.user_data['post']['media_id'] = video.file_id
            
            await message.reply_text(
                "✅ Видео сохранено!\n\n"
                "Теперь введите заголовок поста или /skip чтобы пропустить:"
            )
            return ADD_TITLE
        
        elif message.animation:
            gif = message.animation
            file = await gif.get_file()
            media_path = os.path.join(MEDIA_DIR, f"{uuid4()}.gif")
            await file.download_to_drive(media_path)
            
            context.user_data['post']['media_type'] = 'gif'
            context.user_data['post']['media_path'] = media_path
            context.user_data['post']['media_id'] = gif.file_id
            
            await message.reply_text(
                "✅ GIF сохранен!\n\n"
                "Теперь введите заголовок поста или /skip чтобы пропустить:"
            )
            return ADD_TITLE
        
        elif message.text and message.text.lower() == '/skip':
            context.user_data['post']['media_type'] = None
            await message.reply_text(
                "⏭ Медиа пропущено.\n\n"
                "Теперь введите заголовок поста или /skip чтобы пропустить:"
            )
            return ADD_TITLE
    
    return ADD_MEDIA

async def add_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == '/skip':
        context.user_data['post']['title'] = ""
        await update.message.reply_text(
            "⏭ Заголовок пропущен.\n\n"
            "Теперь введите описание поста или /skip чтобы пропустить:"
        )
        return ADD_DESC
    else:
        context.user_data['post']['title'] = update.message.text
        await update.message.reply_text(
            "✅ Заголовок сохранен!\n\n"
            "Теперь введите описание поста или /skip чтобы пропустить:"
        )
        return ADD_DESC

async def add_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == '/skip':
        context.user_data['post']['description'] = ""
        await update.message.reply_text(
            "⏭ Описание пропущено.\n\n"
            "Настройте пост с помощью клавиатуры:",
            reply_markup=admin_kb()
        )
        return ADMIN_PANEL
    else:
        context.user_data['post']['description'] = update.message.text
        await update.message.reply_text(
            "✅ Описание сохранено!\n\n"
            "Настройте пост с помощью клавиатуры:",
            reply_markup=admin_kb()
        )
        return ADMIN_PANEL

async def show_preview(update, context):
    post = context.user_data['post']
    try:
        if hasattr(update, "message") and update.message:
            send_to = update.message
        else:
            send_to = update
        
        caption = render_post(post)
        
        if post['media_type'] == 'photo' and post.get('media_path') and os.path.exists(post['media_path']):
            with open(post['media_path'], "rb") as img:
                await send_to.reply_photo(
                    img,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=build_buttons(post)
                )
        
        elif post['media_type'] == 'video' and post.get('media_path') and os.path.exists(post['media_path']):
            with open(post['media_path'], "rb") as video:
                await send_to.reply_video(
                    video,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=build_buttons(post)
                )
        
        elif post['media_type'] == 'gif' and post.get('media_path') and os.path.exists(post['media_path']):
            with open(post['media_path'], "rb") as gif:
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

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    post = context.user_data['post']

    if query.data == "set_media":
        await query.edit_message_text(
            "🖼 <b>Выберите тип медиа:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=media_type_keyboard()
        )
        return ADD_MEDIA

    elif query.data == "set_title":
        await query.edit_message_text("Введите новый заголовок или /skip чтобы пропустить:")
        return ADD_TITLE

    elif query.data == "set_desc":
        await query.edit_message_text("Введите новое описание или /skip чтобы пропустить:")
        return ADD_DESC

    elif query.data == "manage_buttons":
        await query.edit_message_text("Редактирование кнопок:", reply_markup=btn_manage_kb(post))
        return ADMIN_PANEL

    elif query.data == "preview":
        await show_preview(query, context)
        await query.message.reply_text("Используйте клавиатуру для редактирования:", reply_markup=admin_kb())
        return ADMIN_PANEL

    elif query.data == "add_btn":
        context.user_data['editbtn'] = None
        await query.edit_message_text("Текст кнопки:")
        return ADD_BTN_LABEL

    elif query.data.startswith("editbtn_"):
        idx = int(query.data.split("_")[1])
        context.user_data['editbtn'] = idx
        btn = post['buttons'][idx]
        await query.edit_message_text(f"Редактируем кнопку №{idx + 1}: [{btn['label']}]",
                                      reply_markup=edit_btn_kb(idx))
        return ADMIN_PANEL

    elif query.data.startswith("editbtn_label_"):
        idx = int(query.data.split("_")[2])
        context.user_data['editbtn'] = idx
        await query.edit_message_text("Новое название для кнопки:")
        return BTN_EDIT_LABEL

    elif query.data.startswith("editbtn_url_"):
        idx = int(query.data.split("_")[2])
        context.user_data['editbtn'] = idx
        await query.edit_message_text("Новый URL кнопки:")
        return BTN_EDIT_URL

    elif query.data.startswith("delbtn_"):
        idx = int(query.data.split("_")[1])
        post['buttons'].pop(idx)
        await query.edit_message_text("Кнопка удалена.", reply_markup=btn_manage_kb(post))
        return ADMIN_PANEL

    elif query.data == "back":
        await show_preview(query, context)
        await query.message.reply_text("Используйте клавиатуру.", reply_markup=admin_kb())
        return ADMIN_PANEL

    elif query.data == "publish":
        try:
            caption = render_post(post)
            
            if post['media_type'] == 'photo' and post.get('media_path') and os.path.exists(post['media_path']):
                with open(post['media_path'], "rb") as img:
                    await context.bot.send_photo(
                        chat_id=CHANNEL_ID,
                        photo=img,
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=build_buttons(post)
                    )
            
            elif post['media_type'] == 'video' and post.get('media_path') and os.path.exists(post['media_path']):
                with open(post['media_path'], "rb") as video:
                    await context.bot.send_video(
                        chat_id=CHANNEL_ID,
                        video=video,
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=build_buttons(post)
                    )
            
            elif post['media_type'] == 'gif' and post.get('media_path') and os.path.exists(post['media_path']):
                with open(post['media_path'], "rb") as gif:
                    await context.bot.send_animation(
                        chat_id=CHANNEL_ID,
                        animation=gif,
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=build_buttons(post)
                    )
            
            else:
                await context.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=build_buttons(post)
                )
            
            await query.edit_message_text("✅ Пост успешно опубликован!")
            
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка при публикации: {e}")
        
        return ConversationHandler.END

    elif query.data == "stats_admin":
        await stats_command(Update(message=query.message, callback_query=query), context)
        return ADMIN_PANEL

    elif query.data == "cancel":
        await query.edit_message_text("❌ Создание поста отменено.")
        return ConversationHandler.END

    await query.edit_message_text("❓ Неизвестная команда...")
    return ADMIN_PANEL

async def add_btn_label(update: Update, context: ContextTypes.DEFAULT_TYPE):
    label = update.message.text
    context.user_data['btn_tmp_label'] = label
    await update.message.reply_text("URL кнопки:")
    return ADD_BTN_URL

async def add_btn_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    label = context.user_data.get('btn_tmp_label', '')
    context.user_data['post'].setdefault("buttons", []).append({"label": label, "url": url})
    await show_preview(update, context)
    await update.message.reply_text("✅ Кнопка добавлена!", reply_markup=btn_manage_kb(context.user_data['post']))
    return ADMIN_PANEL

async def btn_edit_label(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data.get('editbtn')
    context.user_data['post']['buttons'][idx]['label'] = update.message.text
    await show_preview(update, context)
    await update.message.reply_text("✅ Название кнопки изменено.", reply_markup=btn_manage_kb(context.user_data['post']))
    return ADMIN_PANEL

async def btn_edit_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data.get('editbtn')
    context.user_data['post']['buttons'][idx]['url'] = update.message.text
    await show_preview(update, context)
    await update.message.reply_text("✅ URL кнопки изменён.", reply_markup=btn_manage_kb(context.user_data['post']))
    return ADMIN_PANEL

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Действие отменено.")
    return ConversationHandler.END

# =========== MAIN/START ==========

def main():
    print("=" * 50)
    print("🤖 ЗАПУСК ПРИВАТНОГО БОТА")
    print("=" * 50)
    print(f"👑 Бот работает ТОЛЬКО для ID: {ADMIN_ID}")
    print("👥 Другие пользователи увидят только сообщение '⛔ Этот бот приватный.'")
    print("=" * 50)
    
    if TELEGRAM_TOKEN == "ВАШ_ТОКЕН_ЗДЕСЬ":
        print("❌ ОШИБКА: Замените TELEGRAM_TOKEN на ваш токен!")
        return
    
    db = load_db()
    print(f"📊 Загружено файлов в БД: {len(db['files'])}")
    print(f"🔢 Последний ID: {db['last_id']}")
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler('post', adm_cmd)],
        states={
            ADD_MEDIA: [
                CallbackQueryHandler(add_media),
                MessageHandler(filters.PHOTO | filters.VIDEO | filters.ANIMATION, add_media),
                MessageHandler(filters.TEXT & filters.Regex("^/skip$"), add_media)
            ],
            ADD_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_title),
                MessageHandler(filters.TEXT & filters.Regex("^/skip$"), add_title)
            ],
            ADD_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_desc),
                MessageHandler(filters.TEXT & filters.Regex("^/skip$"), add_desc)
            ],
            ADMIN_PANEL: [
                CallbackQueryHandler(admin_panel),
            ],
            ADD_BTN_LABEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_btn_label)],
            ADD_BTN_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_btn_url)],
            BTN_EDIT_LABEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, btn_edit_label)],
            BTN_EDIT_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, btn_edit_url)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True,
    )
    
    app.add_handler(CommandHandler('start', filebot_start))
    app.add_handler(CommandHandler('list', list_files))
    app.add_handler(CommandHandler('info', file_info))
    app.add_handler(CommandHandler('clear', clear_files))
    app.add_handler(CommandHandler('del', del_file))
    app.add_handler(CommandHandler('stats', stats_command))
    app.add_handler(MessageHandler(filters.Document.ALL & filters.ChatType.PRIVATE, handle_apk))
    app.add_handler(conv)

    print("✅ БОТ УСПЕШНО ЗАПУЩЕН!")
    print("=" * 50)
    print(f"📢 Канал: {CHANNEL_ID}")
    print(f"📁 Файлы хранятся в: {FILE_DB}")
    print(f"🖼 Медиа сохраняются в: {MEDIA_DIR}")
    print("=" * 50)
    
    app.run_polling()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"\n\n❌ Ошибка при запуске бота: {e}")async def del_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) == 1 and args[0].isdigit():
        db = load_db()
        file_key = args[0]
        if file_key in db:
            fname = db[file_key]["file_name"]
            del db[file_key]
            save_db(db)
            await update.message.reply_text(f"Файл №{file_key} ({fname}) удалён.")
        else:
            await update.message.reply_text("Файл с таким номером не найден.")
    else:
        await update.message.reply_text("Используйте: /del N, где N — номер файла.")

async def filebot_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) == 1 and args[0].isdigit():
        db = load_db()
        file_key = args[0]
        entry = db.get(file_key)
        if entry and "file_id" in entry:
            caption = f"Ваш файл: {entry.get('file_name', 'File')}\nПодпись: {SIGNATURE}"
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=entry["file_id"],
                caption=caption
            )
        else:
            await update.message.reply_text("Файл не найден.")
    else:
        user = update.effective_user
        username = user.username if user.username else user.first_name
        await update.message.reply_text(
            f"Привет, {username}!\n"
            "Это Бот для выдачи файлов с канала.\n"
            "@ANDRO_FILE"
        )

# ------- БЛОК АДМИНКИ -------
def render_post(post):
    return (
        f"<b>{post['title']}</b>\n"
        f"<b>________________________________</b>\n"  # Верхняя линия
        f"📝 <b>Описание:</b>\n"
        f"{post['description']}\n"
        f"<b>=========================</b>"  # Нижняя линия с "===" в конце
    )

# --- Кнопки по 2 в ряд ---
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
        [InlineKeyboardButton("📷 Фото", callback_data='set_photo'),
         InlineKeyboardButton("Заголовок", callback_data='set_title')],
        [InlineKeyboardButton("Описание", callback_data='set_desc')],
        [InlineKeyboardButton("Кнопки", callback_data='manage_buttons')],
        [InlineKeyboardButton("📤 Опубликовать", callback_data='publish')],
        [InlineKeyboardButton("❌ Отмена", callback_data='cancel')]
    ])

def btn_manage_kb(post):
    kb = [[InlineKeyboardButton(f"✏ {i + 1}: {btn['label']}", callback_data=f'editbtn_{i}')]
          for i, btn in enumerate(post.get('buttons', []))]
    kb.append([InlineKeyboardButton("➕ Добавить", callback_data='add_btn')])
    kb.append([InlineKeyboardButton("← Назад", callback_data='back')])
    return InlineKeyboardMarkup(kb)

def edit_btn_kb(idx):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("↩ Название", callback_data=f'editbtn_label_{idx}')],
        [InlineKeyboardButton("🌐 URL", callback_data=f'editbtn_url_{idx}')],
        [InlineKeyboardButton("❌ Удалить", callback_data=f'delbtn_{idx}')],
        [InlineKeyboardButton("← Назад", callback_data='manage_buttons')]
    ])

async def adm_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Доступ запрещён.")
        return ConversationHandler.END
    context.user_data['post'] = {
        "image_path": "",
        "title": "",
        "description": "",
        "buttons": []
    }
    await update.message.reply_text("🔹 Отправьте картинку для поста.")
    return ADD_PHOTO

async def add_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        img_path = os.path.join(IMAGES_DIR, f"{uuid4()}.jpg")
        await file.download_to_drive(img_path)
        context.user_data['post']['image_path'] = img_path
        await update.message.reply_text("Теперь введите заголовок:")
        return ADD_TITLE
    else:
        await update.message.reply_text("Теперь введите заголовок:")
        return ADD_TITLE

async def add_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['post']["title"] = update.message.text
    await update.message.reply_text("Введите описание поста:")
    return ADD_DESC

async def add_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['post']["description"] = update.message.text
    await show_preview(update, context)
    await update.message.reply_text("Используйте клавиатуру.", reply_markup=admin_kb())
    return ADMIN_PANEL

async def show_preview(update, context):
    post = context.user_data['post']
    try:
        if hasattr(update, "message") and update.message:
            send_to = update.message
        else:
            send_to = update
        if post['image_path']:
            with open(post['image_path'], "rb") as img:
                await send_to.reply_photo(img,
                                           caption=render_post(post),
                                           parse_mode=ParseMode.HTML, reply_markup=build_buttons(post))
        else:
            await send_to.reply_text(render_post(post), parse_mode=ParseMode.HTML, reply_markup=build_buttons(post))
    except Exception:
        pass

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    post = context.user_data['post']

    if query.data == "set_photo":
        await query.edit_message_text("Отправьте новую картинку.")
        return ADD_PHOTO

    if query.data == "set_title":
        await query.edit_message_text("Введите новый заголовок:")
        return ADD_TITLE

    if query.data == "set_desc":
        await query.edit_message_text("Введите новое описание:")
        return ADD_DESC

    if query.data == "manage_buttons":
        await query.edit_message_text("Редактирование кнопок:", reply_markup=btn_manage_kb(post))
        return ADMIN_PANEL

    if query.data == "add_btn":
        context.user_data['editbtn'] = None
        await query.edit_message_text("Текст кнопки:")
        return ADD_BTN_LABEL

    if query.data.startswith("editbtn_"):
        idx = int(query.data.split("_")[1])
        context.user_data['editbtn'] = idx
        btn = post['buttons'][idx]
        await query.edit_message_text(f"Редактируем кнопку №{idx + 1}: [{btn['label']}]",
                                      reply_markup=edit_btn_kb(idx))
        return ADMIN_PANEL

    if query.data.startswith("editbtn_label_"):
        idx = int(query.data.split("_")[2])
        context.user_data['editbtn'] = idx
        await query.edit_message_text("Новое название для кнопки:")
        return BTN_EDIT_LABEL

    if query.data.startswith("editbtn_url_"):
        idx = int(query.data.split("_")[2])
        context.user_data['editbtn'] = idx
        await query.edit_message_text("Новый URL кнопки:")
        return BTN_EDIT_URL

    if query.data.startswith("delbtn_"):
        idx = int(query.data.split("_")[1])
        post['buttons'].pop(idx)
        await query.edit_message_text("Кнопка удалена.", reply_markup=btn_manage_kb(post))
        return ADMIN_PANEL

    if query.data == "back":
        await show_preview(query, context)
        await query.message.reply_text("Используйте клавиатуру.", reply_markup=admin_kb())
        return ADMIN_PANEL

    if query.data == "publish":
        try:
            if post['image_path']:
                with open(post['image_path'], "rb") as img:
                    await context.bot.send_photo(
                        chat_id=CHANNEL_ID,
                        photo=img,
                        caption=render_post(post),
                        parse_mode=ParseMode.HTML,
                        reply_markup=build_buttons(post)
                    )
            else:
                await context.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=render_post(post),
                    parse_mode=ParseMode.HTML,
                    reply_markup=build_buttons(post)
                )
            await query.edit_message_text("✅ Пост опубликован!")
        except Exception as e:
            await query.edit_message_text(f"Ошибка: {e}")
        return ConversationHandler.END

    if query.data == "cancel":
        await query.edit_message_text("Создание поста отменено.")
        return ConversationHandler.END

    await query.edit_message_text("?? Неизвестная команда...")
    return ADMIN_PANEL

async def add_btn_label(update: Update, context: ContextTypes.DEFAULT_TYPE):
    label = update.message.text
    context.user_data['btn_tmp_label'] = label
    await update.message.reply_text("URL кнопки:")
    return ADD_BTN_URL

async def add_btn_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    label = context.user_data.get('btn_tmp_label', '')
    context.user_data['post'].setdefault("buttons", []).append({"label": label, "url": url})
    await show_preview(update, context)
    await update.message.reply_text("Кнопка добавлена!", reply_markup=btn_manage_kb(context.user_data['post']))
    return ADMIN_PANEL

async def btn_edit_label(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data.get('editbtn')
    context.user_data['post']['buttons'][idx]['label'] = update.message.text
    await show_preview(update, context)
    await update.message.reply_text("Название кнопки изменено.", reply_markup=btn_manage_kb(context.user_data['post']))
    return ADMIN_PANEL

async def btn_edit_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data.get('editbtn')
    context.user_data['post']['buttons'][idx]['url'] = update.message.text
    await show_preview(update, context)
    await update.message.reply_text("URL кнопки изменён.", reply_markup=btn_manage_kb(context.user_data['post']))
    return ADMIN_PANEL

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено.")
    return ConversationHandler.END

# =========== MAIN/START ==========

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler('post', adm_cmd)],
        states={
            ADD_PHOTO: [MessageHandler(filters.PHOTO, add_photo),
                        MessageHandler(filters.TEXT & filters.Regex("^/skip$"), add_photo)],
            ADD_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_title)],
            ADD_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_desc)],
            ADMIN_PANEL: [
                CallbackQueryHandler(admin_panel),
            ],
            ADD_BTN_LABEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_btn_label)],
            ADD_BTN_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_btn_url)],
            BTN_EDIT_LABEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, btn_edit_label)],
            BTN_EDIT_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, btn_edit_url)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True,
    )
    app.add_handler(CommandHandler('start', filebot_start))
    app.add_handler(CommandHandler('list', list_files))
    app.add_handler(CommandHandler('info', file_info))
    app.add_handler(CommandHandler('clear', clear_files))
    app.add_handler(CommandHandler('del', del_file))
    app.add_handler(MessageHandler(filters.Document.ALL & filters.ChatType.PRIVATE, handle_apk))
    app.add_handler(conv)

    print("\nБОТ ЗАПУЩЕН!\n")
    app.run_polling()

if __name__ == "__main__":
    main()

