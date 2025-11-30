import logging
import sqlite3
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from deep_translator import GoogleTranslator

# Telegram bot token
TOKEN = "8344960977:AAGYIO9sLXLWp9Syt0VriHmU7XVOUidr_x8"

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Default target language
DEFAULT_TARGET_LANG = "en"

# Database setup
DB_PATH = "users.db"

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

# Handlers
def start(update, context):
    chat_id = update.effective_chat.id
    set_target_lang(chat_id, DEFAULT_TARGET_LANG)
    msg = (
        "Salom! Men tarjimon botman.\n\n"
        "Buyruqlar:\n"
        "• /lang <kod> — maqsad tilini o‘rnatish (masalan: /lang uz, /lang en, /lang ru)\n"
        "• /help — foydalanish bo‘yicha yo‘riqnoma\n\n"
        "Matn yuboring — men uni tanlangan tilga tarjima qilaman.\n"
        f"Hozirgi maqsad tili: {get_target_lang(chat_id)}"
    )
    update.message.reply_text(msg)

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
    update.message.reply_text(translated)

def main():
    init_db()
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_cmd))
    dp.add_handler(CommandHandler("lang", lang_cmd))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, translate_message))

    logger.info("Translator bot ishga tushdi.")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
