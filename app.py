import os
import logging
import asyncio
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from better_profanity import profanity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# רשימת מילים אסורות נוספת בעברית
HEBREW_BAD_WORDS = ["פורנו", "סקס", "עירום", "זימה"]
profanity.add_censor_words(HEBREW_BAD_WORDS)

# משתנה גלובלי להודעות אוטומטיות
auto_messages_task = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("אני אדם ✅", callback_data="verify_human")],
        [InlineKeyboardButton("משחקים 🎮", callback_data="games_menu")],
        [InlineKeyboardButton("הגדרות ניהול ⚙️", callback_data="admin_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"שלום {user.first_name}!\nאני בוט הניהול והמשחקים של הקבוצה.\nאנא אשר שאתה אדם כדי להמשיך.",
        reply_markup=reply_markup
    )

async def filter_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text
    # בדיקת קישורים
    url_pattern = r'(https?://[^\s]+|www\.[^\s]+)'
    
    if profanity.contains_profanity(text) or re.search(url_pattern, text):
        try:
            await update.message.delete()
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🚫 {update.effective_user.mention_html()} ההודעה נמחקה כי היא מכילה תוכן אסור או קישור.",
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error deleting message: {e}")

async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "verify_human":
        await query.edit_message_text("אימות הצליח! כעת יש לך גישה מלאה לקבוצה. ✅")
    
    elif query.data == "games_menu":
        keyboard = [
            [InlineKeyboardButton("4 בשורה 🔴", callback_data="game_4row")],
            [InlineKeyboardButton("דמקה 🏁", callback_data="game_checkers")],
            [InlineKeyboardButton("לוח ציור 🎨", web_app=WebAppInfo(url="https://r-n-d.github.io/draw/"))],
            [InlineKeyboardButton("חזרה 🔙", callback_data="main_menu")]
        ]
        await query.edit_message_text("בחר משחק:", reply_markup=InlineKeyboardMarkup(keyboard))

async def set_auto_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # פורמט: /auto [שניות] [הודעה]
    if len(context.args) < 2:
        await update.message.reply_text("שימוש: /auto [שניות] [הודעה]")
        return
    
    seconds = int(context.args[0])
    message = " ".join(context.args[1:])
    chat_id = update.effective_chat.id
    
    if chat_id in auto_messages_task:
        auto_messages_task[chat_id].cancel()
    
    async def send_loop():
        while True:
            await asyncio.sleep(seconds)
            await context.bot.send_message(chat_id=chat_id, text=f"📢 הודעה אוטומטית:\n{message}")
    
    task = asyncio.create_task(send_loop())
    auto_messages_task[chat_id] = task
    await update.message.reply_text(f"הודעה אוטומטית הוגדרה כל {seconds} שניות.")

def main():
    token = os.environ.get("TELEGRAM_TOKEN", "")
    if not token: return
    
    application = Application.builder().token(token).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("auto", set_auto_msg))
    application.add_handler(CallbackQueryHandler(verify_callback))
    
    # סינון הודעות (טקסט וקישורים)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, filter_content))
    
    application.run_polling()

if __name__ == "__main__":
    main()
