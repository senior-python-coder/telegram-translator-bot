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

DB_PATH = "users.db"
DEFAULT_SOURCE_LANG = "auto"
DEFAULT_TARGET_LANG = "en"

app = Flask(__name__)

# --- Soxta HTTP route (Render health check uchun) ---
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
            target_lang TEXT NOT NULL,
            page INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def get_user(chat_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT source_lang, target_lang, page FROM users WHERE chat_id = ?", (chat_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {"src": result[0], "tgt": result[1], "page": result[2]}
    return {"src": DEFAULT_SOURCE_LANG, "tgt": DEFAULT_TARGET_LANG, "page": 0}

def set_user(chat_id, src, tgt, page):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (chat_id, source_lang, target_lang, page)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET 
            source_lang=excluded.source_lang,
            target_lang=excluded.target_lang,
            page=excluded.page
    """, (chat_id, src, tgt, page))
    conn.commit()
    conn.close()

# --- Barcha tillarni olish (to‘g‘ri usul) ---
translator = GoogleTranslator(source="auto", target="en")
LANGS = translator.get_supported_languages(as_dict=True)
LANG_ITEMS = list(LANGS.items())  # [('english','en'), ('uzbek','uz'), ...]

PAGE_SIZE = 6  # har sahifada 6 til

def build_keyboard(page, mode="src"):
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    slice_items = LANG_ITEMS[start:end]

    buttons = [[InlineKeyboardButton(f"{name.title()} ({code})", callback_data=f"{mode}:{code}")]
               for name, code in slice_items]

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f"page:{mode}:{page-1}"))
    if end < len(LANG_ITEMS):
        nav.append(InlineKeyboardButton("➡️ Keyingi", callback_data=f"page:{mode}:{page+1}"))
    if nav:
        buttons.append(nav)

    return InlineKeyboardMarkup(buttons)

# --- Bot logic ---
def start(update, context):
    chat_id = update.effective_chat.id
    user = get_user(chat_id)
    set_user(chat_id, user["src"], user["tgt"], 0)

    msg = (
        "Salom! Men tarjimon botman.\nTilni tanlash uchun tugmalardan foydalaning.\n\n"
        "Hello! I am a translation bot.\nUse the buttons below to set source and target languages.\n\n"
        f"Source: {user['src']} | Target: {user['tgt']}"
    )
    update.message.reply_text(msg, reply_markup=build_keyboard(user["page"], "src"))

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

    src, tgt, page = user["src"], user["tgt"], user["page"]

    if data.startswith("src:"):
        src = data.split(":")[1]
        set_user(chat_id, src, tgt, page)
        query.answer(f"Source set: {src}")
        query.edit_message_text(f"Source: {src} | Target: {tgt}", reply_markup=build_keyboard(page, "tgt"))

    elif data.startswith("tgt:"):
        tgt = data.split(":")[1]
        set_user(chat_id, src, tgt, page)
        query.answer(f"Target set: {tgt}")
        query.edit_message_text(f"Source: {src} | Target: {tgt}")

    elif data.startswith("page:"):
        _, mode, new_page = data.split(":")
        new_page = int(new_page)
        set_user(chat_id, src, tgt, new_page)
        query.answer("Page switched")
        query.edit_message_reply_markup(reply_markup=build_keyboard(new_page, mode))

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
