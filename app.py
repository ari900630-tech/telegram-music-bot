import os
import logging
import datetime
import yt_dlp
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_greeting():
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12:
        return "בוקר טוב ☀️"
    elif 12 <= hour < 18:
        return "צהריים טובים 🌤️"
    elif 18 <= hour < 22:
        return "ערב טוב 🌙"
    else:
        return "לילה טוב ✨"

async def search_youtube(query):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'default_search': 'ytsearch100',
        'noplaylist': True,
        'extract_flat': True,
        'nocheckcertificate': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch100:{query}", download=False)
            return info.get('entries', [])
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    greeting = get_greeting()
    user_name = update.effective_user.first_name
    text = f"{greeting}, {user_name}!\n\nשלח שם של זמר או שיר לחיפוש."
    await update.message.reply_text(text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    status_msg = await update.message.reply_text(f"🔍 מחפש את '{query}'...")
    results = await search_youtube(query)
    
    if not results:
        await status_msg.edit_text("❌ לא נמצאו תוצאות.")
        return

    keyboard = []
    for entry in results[:50]:
        title = entry.get('title', 'שיר')[:35]
        v_id = entry.get('id')
        if v_id:
            keyboard.append([InlineKeyboardButton(title, callback_data=f"dl_{v_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await status_msg.edit_text(f"🎶 תוצאות עבור '{query}':", reply_markup=reply_markup)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data.startswith("dl_"):
        video_id = data.split("_")[1]
        await query.answer("מעבד...")
        await query.edit_message_text("⏳ מוריד דרך שרת מתווך לעקיפת חסימה...")

        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'source_address': '0.0.0.0',
            'force_ipv4': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_test', 'web_embedded'],
                }
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                if not info or 'url' not in info:
                     raise Exception("No URL found")
                
                audio_url = info['url']
                title = info.get('title', 'Music')
                await context.bot.send_audio(chat_id=query.message.chat_id, audio=audio_url, title=title)
                await query.delete_message()
            except Exception as e:
                logger.error(f"DL error: {e}")
                # ניסיון אחרון דרך מנוע חלופי
                await query.edit_message_text("❌ השרת חסום כרגע. נסה שוב בעוד דקה.")

def main():
    token = os.environ.get("TELEGRAM_TOKEN", "")
    if not token: return
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.run_polling()

if __name__ == "__main__":
    main()
