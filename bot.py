
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
TELEGRAM_TOKEN = "8503713213:AAFw2fj83nqOTIGz6XBEfYfNYs0P3DvKNxY"
ADMIN_ID = 1129009422         # Ваш user id (число)
CHANNEL_ID = -1002329753497  # id канала/чата для публикации постов
FILE_DB = "file_db.json"
SIGNATURE = "@M_FileBot"
IMAGES_DIR = "admin_images"
os.makedirs(IMAGES_DIR, exist_ok=True)
# =========================

# ------ Состояния админки ------
ADD_PHOTO, ADD_TITLE, ADD_DESC, ADD_BTN_LABEL, ADD_BTN_URL, ADMIN_PANEL, BTN_EDIT_LABEL, BTN_EDIT_URL = range(8)

# ------ БЛОК FILEBOT ------
def load_db():
    if os.path.exists(FILE_DB):
        with open(FILE_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_db(db):
    with open(FILE_DB, "w", encoding="utf-8") as f:
        json.dump(db, f)

async def handle_apk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message.document and message.document.file_name and message.document.file_name.lower().endswith('.apk'):
        try:
            db = load_db()
            counter = str(len(db) + 1)
            file_id = message.document.file_id
            db[counter] = {
                "file_id": file_id,
                "file_name": message.document.file_name
            }
            save_db(db)
            bot_username = (await context.bot.get_me()).username
            botlink = f"https://t.me/{bot_username}?start={counter}"
            markup = f'<a href="{botlink}">Открыть файл №{counter} в боте</a>'
            await message.reply_text(markup, parse_mode=ParseMode.HTML)
        except Exception as e:
            await message.reply_text(f"Ошибка: {e}")
    else:
        await message.reply_text("Это не .apk файл. Пришли .apk документ!")

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    if db:
        response = "Список загруженных файлов:\n"
        for key, value in db.items():
            response += f"№{key}: {value['file_name']}\n"
        await update.message.reply_text(response)
    else:
        await update.message.reply_text("Нет загруженных файлов.")

async def file_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) == 1 and args[0].isdigit():
        db = load_db()
        file_key = args[0]
        entry = db.get(file_key)
        if entry:
            await update.message.reply_text(
                f"Файл: {entry['file_name']}\nID: {entry['file_id']}"
            )
        else:
            await update.message.reply_text("Файл не найден.")
    else:
        await update.message.reply_text("Используйте: /info N, где N - номер файла.")

async def clear_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    if db:
        os.remove(FILE_DB)
        await update.message.reply_text("Все файлы были успешно удалены.")
    else:
        await update.message.reply_text("База данных уже пуста.")

async def del_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            f"Привет, {username}! Доступные команды:\n"
            "/adm — админ-панель постинга и bot\n"
            "/list — Список загруженных файлов\n"
            "/info N — Инфо по файлу\n"
            "/clear — Очистить базу файлов\n"
            "/del N — Удалить файл с номером N\n"
            "Отправь .apk документ — получишь ссылку!"
        )

# ------- БЛОК АДМИНКИ -------
def render_post(post):
    return (
        f"<b>______________________</b>\n"  # Верхняя линия
        f"<b>{post['title']}</b>\n"
        f"<b>=========================</b>\n"  # Нижняя линия с "==="
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
    await update.message.reply_text("🔹 Отправьте картинку для поста или /skip")
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
        await query.edit_message_text("Отправьте новую картинку или /skip")
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
        entry_points=[CommandHandler('adm', adm_cmd)],
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
