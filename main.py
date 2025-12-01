import os
import logging
import sqlite3
import threading
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from deep_translator import GoogleTranslator

# Telegram bot token
TOKEN = os.environ.get("8318611647:AAEqRT_USD6tBDpmfYCVCQtV4bdpUjRa6Bw") or "8318611647:AAEqRT_USD6tBDpmfYCVCQtV4bdpUjRa6Bw"

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DEFAULT_TARGET_LANG = "en"
DB_PATH = "users.db"

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            lang_code TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def get_target_lang(chat_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT lang_code FROM users WHERE chat_id = ?", (chat_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else DEFAULT_TARGET_LANG

def set_target_lang(chat_id, lang_code):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (chat_id, lang_code)
        VALUES (?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET lang_code=excluded.lang_code
    """, (chat_id, lang_code))
    conn.commit()
    conn.close()

def translate_text(text, target_lang):
    try:
        translator = GoogleTranslator(source="auto", target=target_lang)
        return translator.translate(text)
    except Exception as e:
        logger.exception("Translation error")
        return f"Tarjima xatosi: {e}"

# --- Inline tugmalar bilan start ---
def start(update, context):
    chat_id = update.effective_chat.id
    set_target_lang(chat_id, DEFAULT_TARGET_LANG)

    keyboard = [
        [InlineKeyboardButton("🇺🇿 Uzbek", callback_data="lang:uz"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang:en"),
         InlineKeyboardButton("🇷🇺 Russian", callback_data="lang:ru")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    msg = (
        "Salom! Men tarjimon botman.\nTilni tanlash uchun tugmalardan foydalaning.\n"
        f"Hozirgi maqsad tili: {get_target_lang(chat_id)}"
    )
    update.message.reply_text(msg, reply_markup=reply_markup)

def help_cmd(update, context):
    chat_id = update.effective_chat.id
    msg = (
        "Foydalanish:\n"
        "1) /lang <kod> — maqsad tilini o‘rnating (en, uz, ru, tr, de, fr ...)\n"
        "2) Oddiy matn yuboring — bot uni tanlangan tilga tarjima qiladi.\n\n"
        f"Hozirgi maqsad tili: {get_target_lang(chat_id)}"
    )
    update.message.reply_text(msg)

def lang_cmd(update, context):
    chat_id = update.effective_chat.id
    if not context.args:
        update.message.reply_text("Til kodini kiriting, masalan: /lang uz")
        return
    lang_code = context.args[0].lower().strip()
    if not (2 <= len(lang_code) <= 5):
        update.message.reply_text("Xato til kodi. Masalan: en, uz, ru, tr, de.")
        return
    set_target_lang(chat_id, lang_code)
    update.message.reply_text(f"Maqsad tili o‘rnatildi: {lang_code}")

def translate_message(update, context):
    chat_id = update.effective_chat.id
    target_lang = get_target_lang(chat_id)
    text = update.message.text
    translated = translate_text(text, target_lang)

    # Inline tugma bilan "Nusxa olish"
    keyboard = [[InlineKeyboardButton("📋 Nusxa olish", callback_data=f"copy:{translated}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(translated, reply_markup=reply_markup)

def button_handler(update, context):
    query = update.callback_query
    chat_id = query.message.chat_id
    data = query.data

    if data.startswith("lang:"):
        lang_code = data.split(":")[1]
        set_target_lang(chat_id, lang_code)
        query.answer(f"Til o‘zgartirildi: {lang_code}")
        query.edit_message_text(f"Maqsad tili o‘rnatildi: {lang_code}")
    elif data == "help":
        query.answer("Yordam")
        query.edit_message_text(
            "Foydalanish:\n"
            "1) /lang <kod> — maqsad tilini o‘rnating (en, uz, ru, tr, de, fr ...)\n"
            "2) Oddiy matn yuboring — bot uni tanlangan tilga tarjima qiladi."
        )
    elif data.startswith("copy:"):
        copied_text = data.split("copy:")[1]
        query.answer("Matn nusxalandi!")
        query.message.reply_text(f"📋 Nusxa: {copied_text}")

def run_bot():
    init_db()
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_cmd))
    dp.add_handler(CommandHandler("lang", lang_cmd))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, translate_message))
    dp.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Translator bot polling boshlanyapti...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
