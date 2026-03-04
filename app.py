import os
import logging
import asyncio
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, ChatPermissions, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes, ChatMemberHandler
from better_profanity import profanity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

banned_words = ["פורנו", "סקס", "עירום", "זימה"]
profanity.add_censor_words(banned_words)

auto_tasks = {}

def is_admin(user_id):
    admin_id = os.environ.get("ADMIN_ID")
    return str(user_id) == str(admin_id)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["🎮 משחקים", "🎨 לוח ציור"],
        ["📢 הודעה אוטומטית", "👑 פאנל ניהול"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "ברוך הבא לבוט הניהול!",
        reply_markup=reply_markup
    )

async def greet_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if result.new_chat_member.status == "member":
        user = result.new_chat_member.user
        try:
            await context.bot.restrict_chat_member(
                update.effective_chat.id,
                user.id,
                permissions=ChatPermissions(can_send_messages=False)
            )
            keyboard = [[InlineKeyboardButton("אני אדם ✅", callback_data=f"verify_{user.id}")]]
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"שלום {user.first_name}! אשר שאתה אדם כדי לכתוב בקבוצה.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Error: {e}")

async def verify_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    target_id = int(query.data.split("_")[1])
    
    if user_id != target_id:
        await query.answer("הכפתור למשתמש החדש בלבד!", show_alert=True)
        return
    
    await context.bot.restrict_chat_member(
        update.effective_chat.id,
        user_id,
        permissions=ChatPermissions(
            can_send_messages=True, 
            can_send_media_messages=True, 
            can_send_polls=True, 
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
    )
    await query.edit_message_text("אימות הצליח! ✅")

async def admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    cmd = context.args[0] if context.args else ""
    
    if cmd == "add" and len(context.args) > 1:
        word = context.args[1]
        if word not in banned_words:
            banned_words.append(word)
            profanity.add_censor_words([word])
            await update.message.reply_text(f"המילה '{word}' נוספה לרשימת החסימה. ✅")
    
    elif cmd == "list":
        words_str = ", ".join(banned_words)
        await update.message.reply_text(f"רשימת מילים חסומות:\n{words_str}")

async def set_auto_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if len(context.args) < 2:
        await update.message.reply_text("שימוש: /auto [שניות] [טקסט]")
        return

    try:
        seconds = int(context.args[0])
        text = " ".join(context.args[1:])
        chat_id = update.effective_chat.id

        if chat_id in auto_tasks:
            auto_tasks[chat_id].cancel()

        async def loop():
            while True:
                await asyncio.sleep(seconds)
                await context.bot.send_message(chat_id=chat_id, text=f"📢 {text}")

        auto_tasks[chat_id] = asyncio.create_task(loop())
        await update.message.reply_text(f"הודעה הוגדרה כל {seconds} שניות. ✅")
    except:
        await update.message.reply_text("שגיאה.")

async def handle_text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text: return
    user_id = update.effective_user.id

    if text == "🎮 משחקים":
        keyboard = [[InlineKeyboardButton("איקס עיגול ❌⭕️", callback_data="game_ttt")]]
        await update.message.reply_text("בחר משחק:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif text == "🎨 לוח ציור":
        keyboard = [[InlineKeyboardButton("פתח לוח ציור", web_app=WebAppInfo(url="https://r-n-d.github.io/draw/"))]]
        await update.message.reply_text("לחץ לצייר:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif text == "📢 הודעה אוטומטית":
        if is_admin(user_id):
            await update.message.reply_text("שלח: /auto [שניות] [טקסט]")
    elif text == "👑 פאנל ניהול":
        if is_admin(user_id):
            await update.message.reply_text(
                "👑 פאנל ניהול:\n\n"
                "/ban add [מילה] - הוספת מילה לחסימה\n"
                "/ban list - הצגת מילים חסומות\n"
                "/auto [שניות] [טקסט] - הודעה מתוזמנת\n"
                "/stop - עצירת הודעות"
            )
    else:
        url_pattern = r'(https?://|www\.|[a-zA-Z0-9.-]+\.(com|co\.il|net|org|me|info|biz|tv|io))'
        is_banned = any(word in text.lower() for word in banned_words)
        
        if is_banned or profanity.contains_profanity(text) or re.search(url_pattern, text.lower()):
            try:
                await update.message.delete()
            except:
                pass

def main():
    token = os.environ.get("TELEGRAM_TOKEN", "")
    application = Application.builder().token(token).build()
    
    application.add_handler(ChatMemberHandler(greet_new_member, ChatMemberHandler.CHAT_MEMBER))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("auto", set_auto_message))
    application.add_handler(CommandHandler("ban", admin_commands))
    application.add_handler(CallbackQueryHandler(verify_user, pattern="^verify_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_buttons))
    
    application.run_polling()

if __name__ == "__main__":
    main()
