import os
import json
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# ==========================================
# 👇 CONFIGURATION (ALREADY FILLED FOR YOU) 👇
# ==========================================
# 1. PASTE YOUR TOKEN HERE (Keep the quotes!)
BOT_TOKEN = "8410712491:AAG8RAbd2rql_0yiAIt8HuUWKyQwTn6j02E" 

# 2. YOUR CHANNEL DETAILS (Do not change these)
CHANNEL_ID = -1003798813712
DB_MESSAGE_ID = 10
# ==========================================

# --- PART 1: TELEGRAM DATABASE SYSTEM ---
# This system reads/writes the file list directly to your Pinned Message.

async def get_db(context):
    """Downloads the list of files from the Pinned Message in your channel."""
    try:
        pinned_msg = await context.bot.get_message(chat_id=CHANNEL_ID, message_id=DB_MESSAGE_ID)
        db_text = pinned_msg.text
        return json.loads(db_text)
    except Exception as e:
        print(f"⚠️ Error loading DB (Ignore if first time): {e}")
        return {}

async def save_db(context, new_db):
    """Uploads the new list of files back to the Pinned Message."""
    try:
        db_text = json.dumps(new_db)
        await context.bot.edit_message_text(
            chat_id=CHANNEL_ID,
            message_id=DB_MESSAGE_ID,
            text=db_text
        )
    except Exception as e:
        print(f"❌ Error saving DB: {e}")

# --- PART 2: BOT COMMANDS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **I am your Permanent Cloud Bot.**\n\n"
        "📂 **Store:** Send me any file.\n"
        "🔍 **Find:** Send `/find name`\n"
        "📜 **List:** Send `/list`"
    )

async def store_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Get File Name
    file_name = "unknown"
    if update.message.document: file_name = update.message.document.file_name
    elif update.message.video: file_name = update.message.video.file_name or "video.mp4"
    elif update.message.photo: file_name = f"photo_{update.message.photo[-1].file_id[:5]}.jpg"

    msg = await update.message.reply_text("☁️ Saving...")

    try:
        # 2. Forward to Channel
        forwarded = await update.message.forward(chat_id=CHANNEL_ID)
        
        # 3. Update The Pinned Message Database
        db = await get_db(context)           # Download current list
        db[file_name] = forwarded.message_id # Add new file
        await save_db(context, db)           # Upload new list back to channel
        
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            text=f"✅ **Saved!**\nName: `{file_name}`"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def find_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use: `/find <name>`")
        return
    
    search = " ".join(context.args).lower()
    db = await get_db(context) # Get fresh list from channel
    
    # Find matches
    found = [name for name in db if search in name.lower()]

    if not found:
        await update.message.reply_text("❌ No files found.")
        return
        
    await update.message.reply_text(f"🔍 Found {len(found)} files.")
    
    # Send files back to user
    for name in found:
        try:
            msg_id = db[name]
            await context.bot.copy_message(
                chat_id=update.effective_chat.id,
                from_chat_id=CHANNEL_ID,
                message_id=msg_id,
                caption=f"📄 {name}"
            )
        except:
            pass

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = await get_db(context)
    if not db:
        await update.message.reply_text("📂 Cloud is empty.")
        return

    # Show last 20 files
    files = list(db.keys())[-20:]
    text = "📂 **Your Files:**\n\n" + "\n".join([f"• `{f}`" for f in files])
    await update.message.reply_text(text)

# --- PART 3: KEEP-ALIVE SERVER (For Free Hosting) ---

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_server():
    server = HTTPServer(('0.0.0.0', 8080), SimpleHandler)
    server.serve_forever()

# --- PART 4: MAIN EXECUTION ---

if __name__ == '__main__':
    # Start the dummy web server in background (Keeps Render awake)
    threading.Thread(target=run_server, daemon=True).start()
    
    # Start the Bot
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("find", find_file))
    application.add_handler(CommandHandler("list", list_files))
    application.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO | filters.PHOTO, store_file))
    
    print("✅ Bot is running...")
    application.run_polling()