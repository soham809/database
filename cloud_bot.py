import os
import json
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# ==========================================
# 👇 PASTE YOUR TOKEN HERE 👇
# ==========================================
BOT_TOKEN = "8410712491:AAGm9dIzF3tgnLkDOGveixXd09Ktb4K5Tco"
CHANNEL_ID = -1003798813712
DB_MESSAGE_ID = 15
# ==========================================

async def get_db(context):
    try:
        chat = await context.bot.get_chat(CHANNEL_ID)
        pinned = chat.pinned_message
        return json.loads(pinned.text) if pinned else {}
    except: return {}

async def save_db(context, new_db):
    try:
        await context.bot.edit_message_text(chat_id=CHANNEL_ID, message_id=DB_MESSAGE_ID, text=json.dumps(new_db))
    except Exception as e: print(f"❌ Save Error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ **Bot Updated!**\nSend me a file, and I will save it for Direct Download.")

async def store_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. GET FILE ID (The secret key for downloads)
    file_id = None
    file_name = "unknown"
    
    if update.message.document:
        file_id = update.message.document.file_id
        file_name = update.message.document.file_name
    elif update.message.video:
        file_id = update.message.video.file_id
        file_name = update.message.video.file_name or "video.mp4"
    elif update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_name = f"photo_{file_id[:5]}.jpg"

    msg = await update.message.reply_text("☁️ Saving...")

    try:
        # 2. Forward to Channel (Backup)
        await update.message.forward(chat_id=CHANNEL_ID)
        
        # 3. Save FILE ID to Database (Not Message ID!)
        db = await get_db(context)
        db[file_name] = file_id  # <--- This is the key change!
        await save_db(context, db)
        
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, 
            text=f"✅ **Saved for Direct Download!**\nName: `{file_name}`")
    except Exception as e:
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text=f"❌ Error: {e}")

# --- SERVER & HANDLERS ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.wfile.write(b"Bot Alive")

def run_server(): HTTPServer(('0.0.0.0', 8080), SimpleHandler).serve_forever()

if __name__ == '__main__':
    threading.Thread(target=run_server, daemon=True).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO | filters.PHOTO, store_file))
    app.run_polling()
    
