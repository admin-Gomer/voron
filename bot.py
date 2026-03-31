import os
import json
from uuid import uuid4
from PIL import Image, ImageDraw, ImageFont, ImageOps
import random
import warnings
import io
import asyncio
import shutil
from datetime import datetime, timedelta
import re
import glob

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, CallbackQueryHandler, ContextTypes, ChatMemberHandler
)
from telegram.warnings import PTBUserWarning

# Подавляем предупреждения
warnings.filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

# Для отслеживания недавних приветствий
recent_welcome = {}

# ======= НАСТРОЙКИ =======
TELEGRAM_TOKEN = "8578375390:AAEV0xo8D_QB6umLxVtuNsUrx8Pjhk9Qv0"
ADMIN_ID = 1129009422
CHANNEL_ID = -1002329753497
CHANNEL_USERNAME = "@ANDRO_FILE"
CHANNEL_LINK = "https://t.me/ANDRO_FILE"
FILE_DB = "file_db.json"
SIGNATURE = "@ANDRO_FILE"
MEDIA_DIR = "admin_media"
WATERMARK_DIR = "watermarks"
FONT_DIR = "fonts"
DEFAULT_AVATARS_DIR = "default_avatars"

DONATE_LINK = "https://www.donationalerts.com/r/Mikhail36"
REACTIONS = ["🔥", "❤️", "👍", "🎉", "👏", "😍", "😎", "🤔", "😱", "🥰", "💯", "✨"]

ENABLE_GROUP_GREETINGS = True
ENABLE_ALL_GROUPS = True
GROUP_IDS_FILE = "group_ids.json"

CUSTOM_AVATAR = os.path.join(WATERMARK_DIR, "custom_avatar.png")
DEFAULT_AVATAR = os.path.join(WATERMARK_DIR, "default_avatar.png")

os.makedirs(MEDIA_DIR, exist_ok=True)
os.makedirs(WATERMARK_DIR, exist_ok=True)
os.makedirs(FONT_DIR, exist_ok=True)
os.makedirs(DEFAULT_AVATARS_DIR, exist_ok=True)
# =========================

(ADD_MEDIA, ADD_DESC, ADD_BTN_LABEL, ADD_BTN_URL, 
 ADMIN_PANEL, BTN_EDIT_LABEL, ADD_WATERMARK, 
 EDIT_TITLE, EDIT_DESC, EDIT_BUTTONS,
 ADD_DONATION) = range(11)

# ========== ФУНКЦИЯ ДЛЯ ИЗВЛЕЧЕНИЯ ВЕРСИИ ==========
def extract_version_from_filename(filename):
    name_without_ext = filename.rsplit('.', 1)[0]
    patterns = [
        r'_([\d\.]+)_',
        r'_([\d\.]+)$',
        r'[vV](\d+\.\d+(?:\.\d+)?)',
        r'(\d+\.\d+(?:\.\d+)?)',
    ]
    for pattern in patterns:
        match = re.search(pattern, name_without_ext)
        if match:
            version = match.group(1)
            version = re.sub(r'[^0-9.]', '', version)
            if version:
                return version
    return "Неизвестно"

def generate_file_signature(filename):
    name_without_ext = filename.rsplit('.', 1)[0]
    name_clean = re.sub(r'[vV]\d+\.\d+(\.\d+)?', '', name_without_ext)
    name_clean = re.sub(r'_\d+\.\d+(\.\d+)?', '', name_clean)
    name_clean = re.sub(r'[_\-\.]+$', '', name_clean)
    name_clean = re.sub(r'[_\-\.]+', ' ', name_clean).strip()
    if len(name_clean) < 3:
        name_clean = name_without_ext
    version = extract_version_from_filename(filename)
    current_date = datetime.now().strftime("%d.%m.%Y")
    signature = f"""Имя: {name_clean}
Версия: {version}
Mod: @ANDRO_FILE
Дата: {current_date}"""
    return signature

# ========== ФУНКЦИЯ ДЛЯ РЕАКЦИЙ ==========
async def add_random_reaction(chat_id: int, message_id: int, context: ContextTypes.DEFAULT_TYPE):
    try:
        delay = random.randint(3, 10)
        await asyncio.sleep(delay)
        reaction = random.choice(REACTIONS)
        await context.bot.set_message_reaction(
            chat_id=chat_id,
            message_id=message_id,
            reaction=[reaction]
        )
        return True
    except Exception:
        try:
            await context.bot.set_message_reaction(
                chat_id=chat_id,
                message_id=message_id,
                reaction=["👍"]
            )
        except:
            pass
        return False

# ========== ФУНКЦИИ ДЛЯ ПРИВЕТСТВИЯ И ПРОЩАНИЯ ==========
async def download_avatar(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = await context.bot.get_chat(user_id)
        if user.photo:
            photo_file = await context.bot.get_file(user.photo.big_file_id)
            avatar_bytes = io.BytesIO()
            await photo_file.download_to_memory(avatar_bytes)
            avatar_bytes.seek(0)
            avatar = Image.open(avatar_bytes).convert('RGBA')
            avatar = avatar.resize((200, 200), Image.Resampling.LANCZOS)
            return avatar, False
        default_avatar_path = get_default_avatar()
        if default_avatar_path and os.path.exists(default_avatar_path):
            if is_gif_file(default_avatar_path):
                return default_avatar_path, True
            else:
                avatar = Image.open(default_avatar_path).convert('RGBA')
                avatar = avatar.resize((200, 200), Image.Resampling.LANCZOS)
                return avatar, False
        else:
            return create_placeholder_avatar(), False
    except Exception:
        return create_placeholder_avatar(), False

def create_placeholder_avatar():
    size = 200
    img = Image.new('RGBA', (size, size), (30, 144, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arialbd.ttf", 80)
    except:
        font = ImageFont.load_default()
    text = "👤"
    try:
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except:
        text_width = 60
        text_height = 60
    text_x = (size - text_width) // 2
    text_y = (size - text_height) // 2
    draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255))
    return img

def get_default_avatar():
    try:
        avatar_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp']:
            avatar_files.extend(glob.glob(os.path.join(DEFAULT_AVATARS_DIR, ext)))
            avatar_files.extend(glob.glob(os.path.join(DEFAULT_AVATARS_DIR, ext.upper())))
        if avatar_files:
            return random.choice(avatar_files)
        else:
            return create_default_avatar_placeholder()
    except Exception:
        return create_default_avatar_placeholder()

def create_default_avatar_placeholder():
    try:
        placeholder_path = os.path.join(DEFAULT_AVATARS_DIR, "default_placeholder.png")
        if os.path.exists(placeholder_path):
            return placeholder_path
        size = 500
        img = Image.new('RGBA', (size, size), (30, 144, 255, 255))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arialbd.ttf", 200)
        except:
            font = ImageFont.load_default()
        text = "👤"
        try:
            bbox = font.getbbox(text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except:
            text_width = 100
            text_height = 100
        text_x = (size - text_width) // 2
        text_y = (size - text_height) // 2
        draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255, 255))
        img.save(placeholder_path, "PNG")
        return placeholder_path
    except Exception:
        return None

def is_gif_file(file_path):
    return file_path and file_path.lower().endswith('.gif')

async def create_welcome_image_group(username: str, user_id: int, context: ContextTypes.DEFAULT_TYPE, chat_info: dict):
    try:
        width, height = 650, 750
        avatar, is_gif = await download_avatar(user_id, context)
        if is_gif and isinstance(avatar, str):
            import shutil
            gif_path = os.path.join(MEDIA_DIR, f"welcome_gif_{user_id}.gif")
            shutil.copy2(avatar, gif_path)
            return gif_path, True
        if avatar:
            img = avatar.resize((width, height), Image.Resampling.LANCZOS).convert('RGBA')
        else:
            img = Image.new('RGBA', (width, height), (200, 200, 200, 255))
        draw = ImageDraw.Draw(img)
        try:
            name_font = ImageFont.truetype("arialbd.ttf", 50)
        except:
            name_font = ImageFont.load_default()
        name_text = f"{username}"
        try:
            bbox = name_font.getbbox(name_text)
            name_width = bbox[2] - bbox[0]
            name_height = bbox[3] - bbox[1]
        except:
            name_width = len(name_text) * 25
            name_height = 50
        name_x = (width - name_width) // 2
        name_y = height - name_height - 50
        bg_padding = 15
        bg_rect = [
            name_x - bg_padding,
            name_y - bg_padding,
            name_x + name_width + bg_padding,
            name_y + name_height + bg_padding
        ]
        draw.rounded_rectangle(bg_rect, radius=12, fill=(0, 0, 0, 180))
        draw.text((name_x, name_y), name_text, font=name_font, fill=(255, 255, 255))
        img_path = os.path.join(MEDIA_DIR, f"welcome_{user_id}.png")
        img.save(img_path, "PNG", optimize=True)
        return img_path, False
    except Exception:
        return None, False

async def create_goodbye_image_group(username: str, user_id: int, context: ContextTypes.DEFAULT_TYPE, chat_info: dict):
    try:
        width, height = 650, 750
        avatar, is_gif = await download_avatar(user_id, context)
        if is_gif and isinstance(avatar, str):
            try:
                from PIL import ImageSequence
                gif = Image.open(avatar)
                for frame in ImageSequence.Iterator(gif):
                    avatar = frame.convert('RGBA')
                    break
            except:
                avatar = None
        if avatar and not isinstance(avatar, str):
            img = avatar.resize((width, height), Image.Resampling.LANCZOS).convert('RGBA')
        else:
            img = Image.new('RGBA', (width, height), (200, 200, 200, 255))
        draw = ImageDraw.Draw(img)
        try:
            name_font = ImageFont.truetype("arialbd.ttf", 50)
        except:
            name_font = ImageFont.load_default()
        name_text = f"{username}"
        try:
            bbox = name_font.getbbox(name_text)
            name_width = bbox[2] - bbox[0]
            name_height = bbox[3] - bbox[1]
        except:
            name_width = len(name_text) * 25
            name_height = 50
        name_x = (width - name_width) // 2
        name_y = height - name_height - 50
        bg_padding = 15
        bg_rect = [
            name_x - bg_padding,
            name_y - bg_padding,
            name_x + name_width + bg_padding,
            name_y + name_height + bg_padding
        ]
        draw.rounded_rectangle(bg_rect, radius=12, fill=(0, 0, 0, 180))
        draw.text((name_x, name_y), name_text, font=name_font, fill=(255, 255, 255))
        img_path = os.path.join(MEDIA_DIR, f"goodbye_{user_id}.png")
        img.save(img_path, "PNG", optimize=True)
        return img_path
    except Exception:
        return None

# ========== РАБОТА С ГРУППАМИ ==========
def load_allowed_groups():
    if not os.path.exists(GROUP_IDS_FILE):
        with open(GROUP_IDS_FILE, "w", encoding="utf-8") as f:
            json.dump({"groups": []}, f)
        return {"groups": []}
    try:
        with open(GROUP_IDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"groups": []}

def save_allowed_groups(groups_data):
    with open(GROUP_IDS_FILE, "w", encoding="utf-8") as f:
        json.dump(groups_data, f, indent=2, ensure_ascii=False)

def is_group_allowed(group_id: int) -> bool:
    if not ENABLE_GROUP_GREETINGS:
        return False
    if ENABLE_ALL_GROUPS:
        return True
    groups_data = load_allowed_groups()
    return group_id in groups_data["groups"]

async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    chat_id = update.message.chat_id
    chat = update.message.chat
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ Эта команда работает только в группах!")
        return
    groups_data = load_allowed_groups()
    if chat_id not in groups_data["groups"]:
        groups_data["groups"].append(chat_id)
        save_allowed_groups(groups_data)
        await update.message.reply_text(f"✅ Группа <b>{chat.title}</b> добавлена в список разрешённых!", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"❌ Группа уже в списке разрешённых.")

async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    chat_id = update.message.chat_id
    chat = update.message.chat
    groups_data = load_allowed_groups()
    if chat_id in groups_data["groups"]:
        groups_data["groups"].remove(chat_id)
        save_allowed_groups(groups_data)
        await update.message.reply_text(f"✅ Группа <b>{chat.title}</b> удалена из списка разрешённых!", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"❌ Группа не найдена в списке.")

async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    groups_data = load_allowed_groups()
    if not groups_data["groups"]:
        await update.message.reply_text("📭 Нет разрешённых групп.")
        return
    text = "📋 <b>Список групп с приветствиями:</b>\n\n"
    for group_id in groups_data["groups"]:
        try:
            chat = await context.bot.get_chat(group_id)
            text += f"• {chat.title} (ID: <code>{group_id}</code>)\n"
        except:
            text += f"• Группа ID: <code>{group_id}</code> (недоступна)\n"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def show_more_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает описание группы по кнопке Далее"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[2]
    chat_id = query.message.chat_id
    
    # Получаем описание группы из Telegram
    try:
        chat = await context.bot.get_chat(chat_id)
        description = chat.description
        if description:
            more_text = f"ℹ️ <b>О группе:</b>\n\n{description}"
        else:
            more_text = "ℹ️ У этой группы нет описания."
    except:
        more_text = "ℹ️ Не удалось получить описание группы."
    
    await query.edit_message_reply_markup(reply_markup=None)
    
    # Отправляем описание
    sent_msg = await query.message.reply_text(more_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    
    # Автоматически удаляем через 10 секунд
    asyncio.create_task(auto_hide_callback(chat_id, sent_msg.message_id, context))
async def auto_hide_callback(chat_id: int, message_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Автоматически сворачивает описание через 10 секунд"""
    await asyncio.sleep(10)
    try:
        # Удаляем сообщение с описанием
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass    

# ========== КОМАНДА УДАЛЕНИЯ #удалить @username ==========
async def remove_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаляет пользователя из группы по команде #удалить"""
    
    chat_id = update.message.chat_id
    chat = update.message.chat
    
    # Проверяем, что это группа
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ Эта команда работает только в группах!")
        return
    
    # Проверяем права админа
    user_id = update.effective_user.id
    is_admin = user_id == ADMIN_ID
    
    if not is_admin:
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            if member.status not in ['administrator', 'creator']:
                await update.message.reply_text("❌ У вас нет прав на удаление пользователей!")
                return
        except:
            await update.message.reply_text("❌ Ошибка проверки прав!")
            return
    
    message_text = update.message.text
    user_to_remove = None
    
    # СПОСОБ 1: Ответ на сообщение
    if update.message.reply_to_message:
        user_to_remove = update.message.reply_to_message.from_user
        print(f"✅ Удаление по ответу: {user_to_remove.first_name}")
    
    # СПОСОБ 2: По ID в тексте
    if not user_to_remove:
        numbers = re.findall(r'\d+', message_text)
        for num in numbers:
            if len(num) >= 5:  # ID обычно длинный
                try:
                    user_to_remove = await context.bot.get_chat(int(num))
                    print(f"✅ Удаление по ID: {num}")
                    break
                except:
                    pass
    
    if not user_to_remove:
        await update.message.reply_text("❌ Не найден пользователь.\n\nИспользуйте:\n1. Ответьте на сообщение и напишите #удалить\n2. Или: #удалить ID_пользователя")
        return
    
    # Проверки
    if user_to_remove.id == update.effective_user.id:
        await update.message.reply_text("❌ Нельзя удалить самого себя!")
        return
    
    if user_to_remove.id == context.bot.id:
        await update.message.reply_text("❌ Нельзя удалить бота!")
        return
    
    # Проверка прав бота
    try:
        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        if bot_member.status != 'administrator':
            await update.message.reply_text("❌ Бот не администратор! Добавьте бота в администраторы.")
            return
        if not bot_member.can_restrict_members:
            await update.message.reply_text("❌ У бота нет прав на удаление! Включите 'Блокировать пользователей'.")
            return
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка прав бота: {e}")
        return
    
    # Проверка, что цель не админ
    try:
        target = await context.bot.get_chat_member(chat_id, user_to_remove.id)
        if target.status in ['administrator', 'creator']:
            await update.message.reply_text("❌ Нельзя удалить администратора!")
            return
    except:
        pass
    
    # Удаляем
    user_name = user_to_remove.first_name or user_to_remove.username or str(user_to_remove.id)
    
    try:
        await context.bot.ban_chat_member(chat_id, user_to_remove.id)
        await context.bot.unban_chat_member(chat_id, user_to_remove.id)
        await update.message.reply_text(f"✅ Пользователь <b>{user_name}</b> удалён из группы!", parse_mode=ParseMode.HTML)
        print(f"✅ Удалён: {user_name} (ID: {user_to_remove.id})")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка удаления: {e}")
        print(f"❌ Ошибка: {e}")
        
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список всех команд по запросу #меню"""
    
    menu_text = """
📋 <b>ДОСТУПНЫЕ КОМАНДЫ</b>

<b>👤 ОБЩИЕ КОМАНДЫ:</b>
• /start - приветствие и информация о боте
• /donate - поддержать проект (статистика донатов)

<b>👑 АДМИН-КОМАНДЫ (только для админа бота):</b>
• /post - создать пост для последнего файла
• /del ID - удалить файл по ID
• /clear - очистить все файлы

<b>👥 КОМАНДЫ ДЛЯ ГРУПП (админы группы):</b>
• /addgroup - добавить текущую группу в список разрешённых
• /removegroup - удалить группу из списка
• /listgroups - показать список групп с приветствиями
• #удалить - удалить пользователя (ответом на сообщение)
• #меню - показать это меню

<b>📌 Как использовать #удалить:</b>
1. Нажмите "Ответить" на сообщение пользователя
2. Напишите #удалить
3. Отправьте - пользователь будет удалён

<b>🔗 Полезные ссылки:</b>
• <a href='{}'>Наш канал</a>
• <a href='{}'>Поддержать проект</a>
""".format(CHANNEL_LINK, DONATE_LINK)
    
    await update.message.reply_text(menu_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)        

# ========== ОБРАБОТЧИК СОБЫТИЙ ==========
async def handle_channel_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global recent_welcome
    try:
        chat_member_update = update.chat_member
        chat = chat_member_update.chat
        chat_id = chat.id
        chat_type = chat.type
        user = chat_member_update.new_chat_member.user
        user_id = user.id
        username = user.first_name or user.username or "Пользователь"
        old_status = chat_member_update.old_chat_member.status
        new_status = chat_member_update.new_chat_member.status
        
        should_process = False
        chat_info = None
        
        if chat_id == CHANNEL_ID:
            should_process = True
            chat_info = {'type': 'channel', 'name': CHANNEL_USERNAME, 'link': CHANNEL_LINK, 'id': CHANNEL_ID}
        elif chat_type in ['group', 'supergroup']:
            if ENABLE_GROUP_GREETINGS and (ENABLE_ALL_GROUPS or is_group_allowed(chat_id)):
                should_process = True
                chat_info = {'type': 'group', 'name': chat.title or "Группа", 'link': None, 'id': chat_id}
        
        if not should_process:
            return
        
        if old_status in ['left', 'kicked'] and new_status == 'member':
            recent_welcome[user_id] = datetime.now()
            result = await create_welcome_image_group(username, user_id, context, chat_info)
            if result:
                welcome_image_path, is_gif = result
                if welcome_image_path and os.path.exists(welcome_image_path):
                    if chat_info['type'] == 'channel':
                        more_text = """💬 <b>О НАШЕМ КАНАЛЕ</b>

📱 Лучшие моды и приложения для Android
🔧 Ежедневные обновления
💎 Только проверенный контент
🎯 Скачивай безопасно и быстро

📌 <b>Правила:</b>
• Без спама и флуда
• Уважайте других участников
• Запрещена реклама

🔗 <b>Полезные ссылки:</b>
• <a href='{}'>Наш канал</a>
• <a href='{}'>Поддержать проект</a>""".format(CHANNEL_LINK, DONATE_LINK)
                    else:
                        more_text = """💬 <b>О НАШЕЙ ГРУППЕ</b>

💬 Дружеское общение
🎮 Обсуждение модов и приложений
🔧 Помощь и поддержка
📢 Актуальные новости первыми

📌 <b>Правила:</b>
• Без спама и флуда
• Уважайте других участников
• Запрещена реклама
• Офтоп только в разрешённых темах

🔗 <b>Полезные ссылки:</b>
• <a href='{}'>Наш канал</a>
• <a href='{}'>Поддержать проект</a>""".format(CHANNEL_LINK, DONATE_LINK)
                    
                    more_button = InlineKeyboardButton("📖 Далее...", callback_data=f"show_more_{user_id}")
                    reply_markup = InlineKeyboardMarkup([[more_button]])
                    caption = f"👋 <b>Добро пожаловать, {username}!</b>\n\nРады видеть тебя! 🎉"
                    
                    context.bot_data[f"more_text_{user_id}"] = more_text
                    
                    if is_gif:
                        with open(welcome_image_path, "rb") as gif:
                            await context.bot.send_animation(chat_id=chat_id, animation=gif, caption=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
                    else:
                        with open(welcome_image_path, "rb") as photo:
                            await context.bot.send_photo(chat_id=chat_id, photo=photo, caption=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
                    
                    try:
                        os.remove(welcome_image_path)
                    except:
                        pass
        
        elif old_status == 'member' and new_status in ['left', 'kicked']:
            last_welcome = recent_welcome.get(user_id)
            if last_welcome:
                time_diff = (datetime.now() - last_welcome).total_seconds()
                if time_diff < 10:
                    del recent_welcome[user_id]
                    return
            goodbye_image_path = await create_goodbye_image_group(username, user_id, context, chat_info)
            if goodbye_image_path and os.path.exists(goodbye_image_path):
                with open(goodbye_image_path, "rb") as photo:
                    await context.bot.send_photo(chat_id=chat_id, photo=photo, caption=f"👋 <b>До свидания, {username}!</b>\n\nБудем ждать тебя снова! 😢", parse_mode=ParseMode.HTML)
                try:
                    os.remove(goodbye_image_path)
                except:
                    pass
            if user_id in recent_welcome:
                del recent_welcome[user_id]
    except Exception:
        pass

# ========== БАЗА ФАЙЛОВ ==========
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

async def donate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /donate - показывает кнопку поддержки"""
    
    text = """
💰 <b>ПОДДЕРЖАТЬ ПРОЕКТ</b>

Если вам нравится то, что мы делаем, 
вы можете поддержать нас донатом!

Любая сумма поможет проекту развиваться!
"""
    
    donate_btn = InlineKeyboardButton("💰 Поддержать проект", url=DONATE_LINK)
    reply_markup = InlineKeyboardMarkup([[donate_btn]])
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

async def subscription_required(update: Update, context: ContextTypes.DEFAULT_TYPE, file_id: str = None):
    subscribe_btn = InlineKeyboardButton("📢 Подписаться на канал", url=CHANNEL_LINK)
    check_btn = InlineKeyboardButton("✅ Я подписался", callback_data=f"check_sub_{file_id}" if file_id else "check_sub")
    keyboard = [[subscribe_btn], [check_btn]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🔒 <b>Для скачивания файла необходимо подписаться на канал</b>\n\nКанал: {CHANNEL_USERNAME}\n\n1. Нажмите кнопку ниже, чтобы подписаться\n2. После подписки нажмите 'Я подписался'",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if await check_subscription(query.from_user.id, context):
        data = query.data.split('_')
        if len(data) > 2 and data[2]:
            file_id = data[2]
            db = load_db()
            if file_id in db["files"]:
                entry = db["files"][file_id]
                await context.bot.send_document(chat_id=query.from_user.id, document=entry["file_id"], caption=SIGNATURE)
                await query.edit_message_text("✅ <b>Спасибо за подписку! Файл отправлен.</b>", parse_mode=ParseMode.HTML)
            else:
                await query.edit_message_text("❌ Файл не найден.")
        else:
            await query.edit_message_text("✅ <b>Спасибо за подписку!</b>", parse_mode=ParseMode.HTML)
    else:
        await query.edit_message_text(f"❌ <b>Вы еще не подписались на канал!</b>\nПожалуйста, подпишитесь: {CHANNEL_USERNAME}", parse_mode=ParseMode.HTML)

async def del_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    args = context.args
    if len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text("❌ Используйте: /del ID\nНапример: /del 5")
        return
    file_id = args[0]
    db = load_db()
    if file_id not in db["files"]:
        await update.message.reply_text("❌ Файл не найден.")
        return
    file_name = db["files"][file_id]["file_name"]
    del db["files"][file_id]
    if db["files"]:
        db["last_id"] = max(int(id) for id in db["files"].keys())
    else:
        db["last_id"] = 0
    save_db(db)
    await update.message.reply_text(f"✅ Файл ID {file_id} ({file_name}) удалён.")

async def clear_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    confirm_btn = InlineKeyboardButton("✅ Да, очистить всё", callback_data='clear_confirm')
    cancel_btn = InlineKeyboardButton("❌ Нет, отмена", callback_data='clear_cancel')
    keyboard = [[confirm_btn, cancel_btn]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("⚠️ <b>ВНИМАНИЕ!</b>\n\nВы уверены, что хотите удалить ВСЕ файлы?", parse_mode=ParseMode.HTML, reply_markup=reply_markup)

async def clear_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'clear_confirm':
        db = load_db()
        if db["files"]:
            backup_file = f"file_db_backup_{len(db['files'])}_files.json"
            shutil.copy2(FILE_DB, backup_file)
        new_db = {"files": {}, "last_id": 0}
        save_db(new_db)
        await query.edit_message_text("✅ Все файлы удалены.")
    else:
        await query.edit_message_text("❌ Очистка отменена.")

async def handle_apk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
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
            create_btn = InlineKeyboardButton("📝 Создать пост", callback_data=f"create_post_{file_id}")
            reply_markup = InlineKeyboardMarkup([[create_btn]])
            markup = (f"✅ Файл сохранен!\n\n📂 ID файла: {file_id}\n📂 Имя файла: {message.document.file_name}\n📦 Размер: {message.document.file_size // 1024 if message.document.file_size else 0} KB\n\n🔗 Ссылка для скачивания:\n<code>{botlink}</code>")
            await message.reply_text(markup, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        except Exception as e:
            await message.reply_text(f"Ошибка: {e}")
    else:
        await message.reply_text("Это не .apk файл. Пришли .apk документ!")

# ========== СОЗДАНИЕ ПОСТОВ ==========
async def adm_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return ConversationHandler.END
    db = load_db()
    files = db["files"]
    if not files:
        await update.message.reply_text("📭 Нет файлов. Сначала отправьте .apk файл.")
        return ConversationHandler.END
    last_file_id = str(db["last_id"])
    last_file = files[last_file_id]
    bot_username = (await context.bot.get_me()).username
    botlink = f"https://t.me/{bot_username}?start={last_file_id}"
    create_btn = InlineKeyboardButton("📝 Создать пост", callback_data=f"create_post_{last_file_id}")
    reply_markup = InlineKeyboardMarkup([[create_btn]])
    await update.message.reply_text(f"📱 <b>Последний файл:</b>\n\nID: {last_file_id}\nИмя: {last_file['file_name']}\n\n🔗 Ссылка для скачивания:\n<code>{botlink}</code>\n\n👇 Нажмите кнопку ниже для создания поста", parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    return ADD_MEDIA

async def start_create_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    file_id = query.data.replace("create_post_", "")
    db = load_db()
    if file_id not in db["files"]:
        await query.edit_message_text("❌ Файл не найден.")
        return ConversationHandler.END
    bot_username = (await context.bot.get_me()).username
    botlink = f"https://t.me/{bot_username}?start={file_id}"
    context.user_data['post'] = {
        "media_type": None,
        "media_path": "",
        "media_id": "",
        "title": db["files"][file_id]["file_name"],
        "description": "",
        "buttons": [],
        "watermark": "on",
        "file_id": file_id
    }
    await query.edit_message_text(f"🖼 <b>Создание нового поста</b>\n\n📱 <b>Файл:</b> {db['files'][file_id]['file_name']}\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>\n\nВыберите тип медиа для поста:", parse_mode=ParseMode.HTML, reply_markup=media_type_keyboard())
    return ADD_MEDIA

async def add_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        file_id = context.user_data['post']['file_id']
        bot_username = (await context.bot.get_me()).username
        botlink = f"https://t.me/{bot_username}?start={file_id}"
        if query.data == 'media_photo':
            await query.edit_message_text(f"📷 <b>Отправьте фото</b>\n\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>\n\nОтправьте фото для поста:", parse_mode=ParseMode.HTML)
            return ADD_MEDIA
        elif query.data == 'media_video':
            await query.edit_message_text(f"🎬 <b>Отправьте видео</b>\n\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>\n\nОтправьте видео для поста:", parse_mode=ParseMode.HTML)
            return ADD_MEDIA
        elif query.data == 'media_gif':
            await query.edit_message_text(f"🎞 <b>Отправьте GIF</b>\n\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>\n\nОтправьте GIF для поста:", parse_mode=ParseMode.HTML)
            return ADD_MEDIA
        elif query.data == 'media_skip':
            context.user_data['post']['media_type'] = None
            await query.edit_message_text(f"⏭ Медиа пропущено.\n\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>\n\nВведите описание поста (или нажмите кнопку):", parse_mode=ParseMode.HTML, reply_markup=desc_keyboard())
            return ADD_DESC
        elif query.data == 'media_none':
            context.user_data['post']['media_type'] = 'none'
            context.user_data['post']['media_path'] = ""
            context.user_data['post']['media_id'] = ""
            await query.edit_message_text(f"❌ Пост без медиа.\n\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>\n\nВведите описание поста (или нажмите кнопку):", parse_mode=ParseMode.HTML, reply_markup=desc_keyboard())
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
            await message.reply_text(f"✅ Фото сохранено!\n\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>\n\nВведите описание поста (или нажмите кнопку):", parse_mode=ParseMode.HTML, reply_markup=desc_keyboard())
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
            await message.reply_text(f"✅ Видео сохранено!\n\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>\n\nВведите описание поста (или нажмите кнопку):", parse_mode=ParseMode.HTML, reply_markup=desc_keyboard())
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
            await message.reply_text(f"✅ GIF сохранен!\n\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>\n\nВведите описание поста (или нажмите кнопку):", parse_mode=ParseMode.HTML, reply_markup=desc_keyboard())
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
            await query.edit_message_text(f"⏭ Описание пропущено.\n\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>\n\nНастройте пост с помощью клавиатуры:", parse_mode=ParseMode.HTML, reply_markup=admin_kb())
            return ADMIN_PANEL
        elif query.data == 'back_desc':
            await query.edit_message_text(f"🖼 Выберите тип медиа для поста:\n\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>", parse_mode=ParseMode.HTML, reply_markup=media_type_keyboard())
            return ADD_MEDIA
    elif update.message:
        context.user_data['post']['description'] = update.message.text
        file_id = context.user_data['post']['file_id']
        bot_username = (await context.bot.get_me()).username
        botlink = f"https://t.me/{bot_username}?start={file_id}"
        await update.message.reply_text(f"✅ Описание сохранено!\n\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>\n\nНастройте пост с помощью клавиатуры:", parse_mode=ParseMode.HTML, reply_markup=admin_kb())
        return ADMIN_PANEL
    return ADD_DESC

async def edit_title_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        file_id = context.user_data['post']['file_id']
        bot_username = (await context.bot.get_me()).username
        botlink = f"https://t.me/{bot_username}?start={file_id}"
        await query.edit_message_text(f"✏️ <b>Редактирование заголовка</b>\n\nТекущий заголовок: {context.user_data['post']['title']}\n\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>\n\nВведите новый заголовок:", parse_mode=ParseMode.HTML)
        return EDIT_TITLE
    elif update.message:
        context.user_data['post']['title'] = update.message.text
        file_id = context.user_data['post']['file_id']
        bot_username = (await context.bot.get_me()).username
        botlink = f"https://t.me/{bot_username}?start={file_id}"
        await update.message.reply_text(f"✅ Заголовок изменен!\n\nНовый заголовок: {update.message.text}\n\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>\n\nНастройте пост с помощью клавиатуры:", parse_mode=ParseMode.HTML, reply_markup=admin_kb())
        return ADMIN_PANEL
    return EDIT_TITLE

async def edit_description_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        file_id = context.user_data['post']['file_id']
        bot_username = (await context.bot.get_me()).username
        botlink = f"https://t.me/{bot_username}?start={file_id}"
        current_desc = context.user_data['post'].get('description', '')
        if not current_desc:
            current_desc = "Описание отсутствует"
        await query.edit_message_text(f"📝 <b>Редактирование описания</b>\n\nТекущее описание: {current_desc}\n\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>\n\nВведите новое описание:", parse_mode=ParseMode.HTML)
        return EDIT_DESC
    elif update.message:
        context.user_data['post']['description'] = update.message.text
        file_id = context.user_data['post']['file_id']
        bot_username = (await context.bot.get_me()).username
        botlink = f"https://t.me/{bot_username}?start={file_id}"
        await update.message.reply_text(f"✅ Описание изменено!\n\nНовое описание: {update.message.text}\n\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>\n\nНастройте пост с помощью клавиатуры:", parse_mode=ParseMode.HTML, reply_markup=admin_kb())
        return ADMIN_PANEL
    return EDIT_DESC

async def edit_buttons_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    post = context.user_data['post']
    file_id = post['file_id']
    bot_username = (await context.bot.get_me()).username
    botlink = f"https://t.me/{bot_username}?start={file_id}"
    keyboard = []
    buttons = post.get('buttons', [])
    if buttons:
        for i, btn in enumerate(buttons):
            keyboard.append([InlineKeyboardButton(f"✏️ Кнопка {i+1}: {btn['label']}", callback_data=f'editbtn_{i}')])
    action_buttons = [InlineKeyboardButton("➕ Добавить", callback_data='add_btn')]
    if buttons:
        action_buttons.append(InlineKeyboardButton("🗑 Очистить все", callback_data='clear_buttons'))
    keyboard.append(action_buttons)
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='back_to_admin')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"🔘 <b>Редактирование кнопок</b>\n\nТекущие кнопки: {len(buttons)} шт.\n\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>\n\nВыберите действие:", parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    return EDIT_BUTTONS

async def clear_all_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['post']['buttons'] = []
    file_id = context.user_data['post']['file_id']
    bot_username = (await context.bot.get_me()).username
    botlink = f"https://t.me/{bot_username}?start={file_id}"
    await query.edit_message_text(f"✅ Все кнопки удалены!\n\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>\n\nНастройте пост с помощью клавиатуры:", parse_mode=ParseMode.HTML, reply_markup=admin_kb())
    return ADMIN_PANEL

def watermark_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Включить водяной знак", callback_data='watermark_on')],
        [InlineKeyboardButton("❌ Выключить водяной знак", callback_data='watermark_off')],
        [InlineKeyboardButton("← Назад", callback_data='back_to_admin')]
    ])

def admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 Медиа", callback_data='set_media')],
        [InlineKeyboardButton("✏️ Заголовок", callback_data='edit_title'), InlineKeyboardButton("📝 Описание", callback_data='edit_description')],
        [InlineKeyboardButton("🔘 Кнопки", callback_data='edit_buttons')],
        [InlineKeyboardButton("💧 Водяной знак", callback_data='set_watermark')],
        [InlineKeyboardButton("📤 Опубликовать", callback_data='publish'), InlineKeyboardButton("👁 Предпросмотр", callback_data='preview')],
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

def desc_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭ Пропустить описание", callback_data='skip_desc')],
        [InlineKeyboardButton("← Назад", callback_data='back_desc')]
    ])

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    post = context.user_data['post']
    file_id = post['file_id']
    bot_username = (await context.bot.get_me()).username
    botlink = f"https://t.me/{bot_username}?start={file_id}"
    if query.data == "set_media":
        await query.edit_message_text(f"🖼 <b>Выберите тип медиа:</b>\n\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>", parse_mode=ParseMode.HTML, reply_markup=media_type_keyboard())
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
        watermark_status = "✅ Включен" if post.get('watermark') == 'on' else "❌ Выключен"
        await query.edit_message_text(f"🔧 <b>Настройка поста</b>\n\n📱 Заголовок: {post['title']}\n📝 Описание: {post.get('description', 'нет')[:50]}\n🔘 Кнопок: {len(post.get('buttons', []))}\n💧 Водяной знак: {watermark_status}\n\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>\n\nВыберите что хотите изменить:", parse_mode=ParseMode.HTML, reply_markup=admin_kb())
        return ADMIN_PANEL
    elif query.data == "set_watermark":
        await query.edit_message_text(f"💧 <b>Управление водяным знаком</b>\n\nТекущий статус: {'✅ Включен' if post.get('watermark') == 'on' else '❌ Выключен'}\n\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>\n\nВыберите действие:", parse_mode=ParseMode.HTML, reply_markup=watermark_keyboard())
        return ADD_WATERMARK
    elif query.data == "watermark_on":
        post['watermark'] = 'on'
        await query.edit_message_text(f"✅ Водяной знак включен!\n\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>\n\nНастройте пост с помощью клавиатуры:", parse_mode=ParseMode.HTML, reply_markup=admin_kb())
        return ADMIN_PANEL
    elif query.data == "watermark_off":
        post['watermark'] = 'off'
        await query.edit_message_text(f"❌ Водяной знак выключен!\n\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>\n\nНастройте пост с помощью клавиатуры:", parse_mode=ParseMode.HTML, reply_markup=admin_kb())
        return ADMIN_PANEL
    elif query.data == "preview":
        await show_preview(query, context)
        await query.message.reply_text(f"Используйте клавиатуру:\n\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>\n\n📱 Заголовок: {post['title']}\n📝 Описание: {post.get('description', 'нет')[:50]}", parse_mode=ParseMode.HTML, reply_markup=admin_kb())
        return ADMIN_PANEL
    elif query.data == "add_btn":
        context.user_data['editbtn'] = None
        await query.edit_message_text(f"Введите текст для кнопки:\n\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>", parse_mode=ParseMode.HTML)
        return ADD_BTN_LABEL
    elif query.data.startswith("editbtn_"):
        idx = int(query.data.split("_")[1])
        context.user_data['editbtn'] = idx
        btn = post['buttons'][idx]
        await query.edit_message_text(f"Редактируем кнопку №{idx + 1}: [{btn['label']}]\n\n🔗 <b>Ссылка на файл:</b>\n<code>{botlink}</code>\n\nВведите новое название:", parse_mode=ParseMode.HTML)
        return ADD_BTN_URL
    elif query.data == "publish":
        try:
            caption = render_post(post)
            media_path = post.get('media_path')
            title = post.get('title', '')
            watermark_enabled = post.get('watermark') == 'on'
            buttons = post.get('buttons', []).copy()
            reply_markup = build_buttons(post) if buttons else None
            if post['media_type'] == 'photo' and media_path and os.path.exists(media_path):
                if watermark_enabled:
                    watermarked_path = add_watermark_to_image(media_path, title)
                else:
                    watermarked_path = media_path
                with open(watermarked_path, "rb") as img:
                    sent_message = await context.bot.send_photo(chat_id=CHANNEL_ID, photo=img, caption=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
                    post_id = sent_message.message_id
                    await add_random_reaction(CHANNEL_ID, post_id, context)
                    channel_name = CHANNEL_USERNAME.replace("@", "")
                    post_link = f"https://t.me/{channel_name}/{post_id}"
                if watermarked_path != media_path and os.path.exists(watermarked_path):
                    try:
                        os.remove(watermarked_path)
                    except:
                        pass
            elif post['media_type'] == 'video' and media_path and os.path.exists(media_path):
                with open(media_path, "rb") as video:
                    sent_message = await context.bot.send_video(chat_id=CHANNEL_ID, video=video, caption=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
                    post_id = sent_message.message_id
                    await add_random_reaction(CHANNEL_ID, post_id, context)
                    channel_name = CHANNEL_USERNAME.replace("@", "")
                    post_link = f"https://t.me/{channel_name}/{post_id}"
            elif post['media_type'] == 'gif' and media_path and os.path.exists(media_path):
                with open(media_path, "rb") as gif:
                    sent_message = await context.bot.send_animation(chat_id=CHANNEL_ID, animation=gif, caption=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
                    post_id = sent_message.message_id
                    await add_random_reaction(CHANNEL_ID, post_id, context)
                    channel_name = CHANNEL_USERNAME.replace("@", "")
                    post_link = f"https://t.me/{channel_name}/{post_id}"
            else:
                sent_message = await context.bot.send_message(chat_id=CHANNEL_ID, text=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
                post_id = sent_message.message_id
                await add_random_reaction(CHANNEL_ID, post_id, context)
                channel_name = CHANNEL_USERNAME.replace("@", "")
                post_link = f"https://t.me/{channel_name}/{post_id}"
            await query.edit_message_text(f"✅ <b>Пост опубликован!</b>\n\n🔗 <b>Ссылка на пост:</b>\n<code>{post_link}</code>\n\n📱 <b>Ссылка на файл:</b>\n<code>{botlink}</code>", parse_mode=ParseMode.HTML)
        except Exception as e:
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
    file_link = f"https://t.me/{bot_username}?start={file_id}"
    await update.message.reply_text(f"✅ Текст кнопки сохранен: {label}\n\n🔗 <b>Ссылка на файл:</b>\n<code>{file_link}</code>\n\nТеперь введите URL для кнопки:", parse_mode=ParseMode.HTML)
    return ADD_BTN_URL

async def add_btn_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    label = context.user_data.get('btn_tmp_label', '')
    idx = context.user_data.get('editbtn')
    file_id = context.user_data['post']['file_id']
    bot_username = (await context.bot.get_me()).username
    file_link = f"https://t.me/{bot_username}?start={file_id}"
    if idx is not None:
        context.user_data['post']['buttons'][idx] = {"label": label, "url": url}
        context.user_data['editbtn'] = None
        action_text = "изменена"
    else:
        if not label:
            await update.message.reply_text("❌ Ошибка: не найден текст кнопки.")
            return ADMIN_PANEL
        context.user_data['post']['buttons'].append({"label": label, "url": url})
        action_text = "добавлена"
    await show_preview(update, context)
    await update.message.reply_text(f"✅ Кнопка {action_text}!\n\n🔗 <b>Ссылка на файл:</b>\n<code>{file_link}</code>\n\nНастройте пост с помощью клавиатуры:", parse_mode=ParseMode.HTML, reply_markup=admin_kb())
    return ADMIN_PANEL

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Действие отменено.")
    return ConversationHandler.END

async def filebot_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) == 1 and args[0].isdigit():
        user_id = update.effective_user.id
        file_id = args[0]
        db = load_db()
        if not await check_subscription(user_id, context):
            await subscription_required(update, context, file_id)
            return
        entry = db["files"].get(file_id)
        if entry:
            signature = generate_file_signature(entry["file_name"])
            caption = f"{signature}\n\n{SIGNATURE}"
            await context.bot.send_document(chat_id=update.effective_chat.id, document=entry["file_id"], caption=caption, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("Файл не найден.")
    else:
        user = update.effective_user
        username = user.username if user.username else user.first_name
        db = load_db()
        files = db["files"]
        response = f"👋 {username}!\n📊 Файлов: {len(files)}\n🔢 Последний ID: {db['last_id']}\n\n📋 <b>Команды:</b>\n/post - создать пост для последнего файла\n/donate - поддержать проект\n/del ID - удалить файл\n/clear - очистить все файлы"
        await update.message.reply_text(response, parse_mode=ParseMode.HTML)

def render_post(post):
    text = ""
    if post.get('title'):
        text += f"<b>{post['title']}</b>\n<b>____________________________________</b>\n"
    if post.get('description'):
        text += f"📝 <b>Описание:</b>\n{post['description']}\n"
    text += f"\n🔗 {CHANNEL_USERNAME}\n\n💰 <a href='{DONATE_LINK}'>Поддержать проект</a>\n<b>===========================</b>"
    return text

def build_buttons(post):
    buttons = post.get("buttons", [])
    if not buttons:
        return None
    rows = []
    for i in range(0, len(buttons), 2):
        row = [InlineKeyboardButton(btn["label"], url=btn["url"]) for btn in buttons[i:i+2]]
        rows.append(row)
    return InlineKeyboardMarkup(rows)

async def show_preview(update, context):
    post = context.user_data['post']
    try:
        caption = render_post(post)
        media_path = post.get('media_path')
        send_to = update.message if hasattr(update, "message") and update.message else update
        title = post.get('title', '')
        watermark_enabled = post.get('watermark') == 'on'
        if post['media_type'] == 'photo' and media_path and os.path.exists(media_path):
            if watermark_enabled:
                preview_path = add_watermark_to_image(media_path, title)
            else:
                preview_path = media_path
            with open(preview_path, "rb") as img:
                await send_to.reply_photo(img, caption=caption, parse_mode=ParseMode.HTML, reply_markup=build_buttons(post))
            if preview_path != media_path:
                try:
                    os.remove(preview_path)
                except:
                    pass
        elif post['media_type'] == 'video' and media_path and os.path.exists(media_path):
            with open(media_path, "rb") as video:
                await send_to.reply_video(video, caption=caption, parse_mode=ParseMode.HTML, reply_markup=build_buttons(post))
        elif post['media_type'] == 'gif' and media_path and os.path.exists(media_path):
            with open(media_path, "rb") as gif:
                await send_to.reply_animation(gif, caption=caption, parse_mode=ParseMode.HTML, reply_markup=build_buttons(post))
        else:
            await send_to.reply_text(caption, parse_mode=ParseMode.HTML, reply_markup=build_buttons(post))
    except Exception:
        pass

def create_default_avatar():
    try:
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        circle_color = (30, 144, 255)
        draw.ellipse([(20, 20), (size - 20, size - 20)], fill=circle_color)
        draw.ellipse([(15, 15), (size - 15, size - 15)], outline=(255, 255, 255), width=5)
        try:
            font = ImageFont.truetype("arialbd.ttf", 120)
        except:
            font = ImageFont.load_default()
        text = "A"
        try:
            bbox = font.getbbox(text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except:
            text_width = 60
            text_height = 60
        position = ((size - text_width) // 2, (size - text_height) // 2)
        draw.text(position, text, font=font, fill=(255, 255, 255, 255))
        img.save(DEFAULT_AVATAR, "PNG")
        return DEFAULT_AVATAR
    except Exception:
        return None

def get_avatar_path():
    if os.path.exists(CUSTOM_AVATAR):
        return CUSTOM_AVATAR
    else:
        if not os.path.exists(DEFAULT_AVATAR):
            create_default_avatar()
        return DEFAULT_AVATAR

def make_circular_avatar(avatar_image):
    try:
        size = avatar_image.size[0]
        mask = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse([(0, 0), (size, size)], fill=255)
        circular_avatar = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        circular_avatar.paste(avatar_image, (0, 0), mask)
        border_size = 10
        bordered_size = size + border_size * 2
        bordered_avatar = Image.new('RGBA', (bordered_size, bordered_size), (0, 0, 0, 0))
        draw_border = ImageDraw.Draw(bordered_avatar)
        draw_border.ellipse([(0, 0), (bordered_size, bordered_size)], outline=(255, 255, 255), width=5)
        bordered_avatar.paste(circular_avatar, (border_size, border_size), circular_avatar)
        return bordered_avatar
    except Exception:
        return avatar_image

def get_random_bright_color():
    bright_colors = [
        (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
        (255, 0, 255), (0, 255, 255), (255, 128, 0), (255, 0, 128),
        (128, 0, 255), (0, 255, 128),
    ]
    return random.choice(bright_colors)

def get_font(size, bold=True):
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

def add_watermark_to_image(image_path, title=""):
    try:
        if not os.path.exists(image_path):
            return image_path
        image = Image.open(image_path).convert('RGBA')
        width, height = image.size
        watermark = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(watermark)
        avatar_path = get_avatar_path()
        if avatar_path and os.path.exists(avatar_path):
            avatar = Image.open(avatar_path).convert('RGBA')
            channel_avatar_size = min(150, max(100, min(width, height) // 8))
            avatar = avatar.resize((channel_avatar_size, channel_avatar_size), Image.Resampling.LANCZOS)
            circular_avatar = make_circular_avatar(avatar)
            margin = 25
            channel_avatar_position = (width - channel_avatar_size - margin - 15, margin)
            watermark.paste(circular_avatar, channel_avatar_position, circular_avatar)
            if title:
                title_color = get_random_bright_color()
                title_font_size = min(40, max(28, min(width, height) // 18))
                title_font = get_font(title_font_size, bold=True)
                if len(title) > 25:
                    title_text = title[:22] + "..."
                else:
                    title_text = title
                try:
                    bbox = title_font.getbbox(title_text)
                    title_width = bbox[2] - bbox[0]
                except:
                    title_width = len(title_text) * title_font_size // 2
                title_position = (width - title_width - margin, channel_avatar_position[1] + channel_avatar_size + 20)
                for offset in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
                    draw.text((title_position[0] + offset[0], title_position[1] + offset[1]), title_text, font=title_font, fill=(0, 0, 0, 200))
                draw.text(title_position, title_text, font=title_font, fill=(*title_color, 255))
            link_font_size = max(22, min(30, min(width, height) // 28))
            link_font = get_font(link_font_size, bold=True)
            link_text = CHANNEL_USERNAME
            try:
                bbox = link_font.getbbox(link_text)
                link_width = bbox[2] - bbox[0]
                link_height = bbox[3] - bbox[1]
            except:
                link_width = len(link_text) * link_font_size // 2
                link_height = link_font_size
            link_margin = 25
            link_position = (width - link_width - link_margin, height - link_height - link_margin)
            bg_padding = 12
            draw.rounded_rectangle([link_position[0] - bg_padding, link_position[1] - bg_padding, link_position[0] + link_width + bg_padding, link_position[1] + link_height + bg_padding], radius=12, fill=(0, 0, 0, 200))
            draw.text(link_position, link_text, font=link_font, fill=(255, 255, 255, 255))
        watermarked = Image.alpha_composite(image, watermark)
        watermarked_path = os.path.join(MEDIA_DIR, f"watermarked_{uuid4()}.png")
        watermarked.save(watermarked_path, "PNG")
        return watermarked_path
    except Exception:
        return image_path

# =========== MAIN ==========
def main():
    print("=" * 50)
    print("💎 ЗАПУСК БОТА")
    print("=" * 50)
    print(f"👑 Админ ID: {ADMIN_ID}")
    print(f"📢 Канал: {CHANNEL_USERNAME}")
    print(f"💰 Ссылка для донатов: {DONATE_LINK}")
    print("=" * 50)
    
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
    
    app.add_handler(CommandHandler('start', filebot_start))
    app.add_handler(CommandHandler('donate', donate_command))
    app.add_handler(CommandHandler('del', del_file))
    app.add_handler(CommandHandler('clear', clear_files))
    app.add_handler(CommandHandler('addgroup', add_group))
    app.add_handler(CommandHandler('removegroup', remove_group))
    app.add_handler(CommandHandler('listgroups', list_groups))
    app.add_handler(CallbackQueryHandler(clear_callback, pattern='^clear_'))
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern='^check_sub'))
    app.add_handler(MessageHandler(filters.Document.ALL & filters.ChatType.PRIVATE, handle_apk))
    app.add_handler(conv)
    app.add_handler(ChatMemberHandler(handle_channel_member_update, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CallbackQueryHandler(show_more_callback, pattern='^show_more_'))
    
    # Обработчик для команды #удалить (как текст, не как команда)
    app.add_handler(MessageHandler(filters.Regex(r'^#удалить'), remove_user_command))
    app.add_handler(MessageHandler(filters.Regex(r'^#меню'), menu_command))
    
    print("✅ БОТ ЗАПУЩЕН!")
    print("=" * 50)
    print("💡 Напишите #меню в группе или личке, чтобы увидеть список команд")
    print("=" * 50)
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Бот остановлен")
    except Exception as e:
        print(f"\n\n❌ Ошибка: {e}")

