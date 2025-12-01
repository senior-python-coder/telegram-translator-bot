import os
import logging
import sqlite3
import threading
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from deep_translator import GoogleTranslator

TOKEN = os.environ.get("TOKEN") or "YOUR_BOT_TOKEN"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DB_PATH = "users.db"
DEFAULT_SOURCE_LANG = "auto"
DEFAULT_TARGET_LANG = "en"

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is running on Render!"

@app.route('/health')
def health():
    return "OK", 200

# --- DB ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            source_lang TEXT NOT NULL,
            target_lang TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def get_user(chat_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT source_lang, target_lang FROM users WHERE chat_id = ?", (chat_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {"src": result[0], "tgt": result[1]}
    return {"src": DEFAULT_SOURCE_LANG, "tgt": DEFAULT_TARGET_LANG}

def set_user(chat_id, src, tgt):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (chat_id, source_lang, target_lang)
        VALUES (?, ?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET 
            source_lang=excluded.source_lang,
            target_lang=excluded.target_lang
    """, (chat_id, src, tgt))
    conn.commit()
    conn.close()

# --- Mashhur tillar bayroqlar bilan ---
LANGS = [
    ("🇺🇿 Uzbek", "uz"),
    ("🇬🇧 English", "en"),
    ("🇷🇺 Russian", "ru"),
    ("🇸🇦 Arabic", "ar"),
    ("🇹🇷 Turkish", "tr"),
    ("🇩🇪 German", "de"),
]

def build_keyboard(mode="src"):
    buttons = [[InlineKeyboardButton(flag, callback_data=f"{mode}:{code}")]
               for flag, code in LANGS]
    return InlineKeyboardMarkup(buttons)

# --- Bot logic ---
def start(update, context):
    chat_id = update.effective_chat.id
    user = get_user(chat_id)
    set_user(chat_id, user["src"], user["tgt"])

    msg = (
        "🌍 Translator Bot\n\n"
        "Tilni tanlash uchun tugmalardan foydalaning.\n"
        "Use the buttons below to set source and target languages.\n\n"
        f"Source: {user['src']} | Target: {user['tgt']}"
    )
    update.message.reply_text(msg, reply_markup=build_keyboard("src"))

def translate_message(update, context):
    chat_id = update.effective_chat.id
    user = get_user(chat_id)
    text = update.message.text

    try:
        translator = GoogleTranslator(source=user["src"], target=user["tgt"])
        translated = translator.translate(text)
    except Exception as e:
        translated = f"Translation error: {e}"

    keyboard = [[InlineKeyboardButton("📋 Copy", callback_data=f"copy:{translated}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(translated, reply_markup=reply_markup)

def button_handler(update, context):
    query = update.callback_query
    chat_id = query.message.chat_id
    user = get_user(chat_id)
    data = query.data

    src, tgt = user["src"], user["tgt"]

    if data.startswith("src:"):
        src = data.split(":")[1]
        set_user(chat_id, src, tgt)
        query.answer(f"Source set: {src}")
        query.edit_message_text(f"Source: {src} | Target: {tgt}", reply_markup=build_keyboard("tgt"))

    elif data.startswith("tgt:"):
        tgt = data.split(":")[1]
        set_user(chat_id, src, tgt)
        query.answer(f"Target set: {tgt}")
        query.edit_message_text(f"Source: {src} | Target: {tgt}")

    elif data.startswith("copy:"):
        copied_text = data.split("copy:")[1]
        query.answer("Copied!")
        query.message.reply_text(f"📋 Copy: {copied_text}")

def run_bot():
    init_db()
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, translate_message))
    dp.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Translator bot polling...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
