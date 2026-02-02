import os
import json
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# ==========================================
# 👇 YOUR TOKEN IS ALREADY FILLED 👇
# ==========================================
BOT_TOKEN = "8410712491:AAGm9dIzF3tgnLkDOGveixXd09Ktb4K5Tco"
CHANNEL_ID = -1003798813712
DB_MESSAGE_ID = 15
# ==========================================

# --- PART 1: MEMORY SYSTEM ---
async def get_db(context):
    try:
        chat = await context.bot.get_chat(CHANNEL_ID)
        pinned = chat.pinned_message
        return json.loads(pinned.text) if pinned else {}
    except: return {}

async def save_db(context, new_db):
    try:
        await context.bot.edit_message_text(
            chat_id=CHANNEL_ID, 
            message_id=DB_MESSAGE_ID, 
            text=json.dumps(new_db)
        )
    except Exception as e: print(f"❌ Save Error: {e}")

# --- PART 2: BOT COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ **Bot is Online!**\n\n"
        "📂 **Send File:** Auto-saves for download\n"
        "📜 **List:** `/list`\n"
        "🗑️ **Delete:** `/delete name`\n"
        "🔍 **Find:** `/find name`"
    )

async def store_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = None
    file_name = "unknown"
    
    # 1. GET THE FILE ID (Secret key for downloads)
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
        
        # 3. Save FILE ID to Database
        db = await get_db(context)
        db[file_name] = file_id 
        await save_db(context, db)
        
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id, 
            message_id=msg.message_id, 
            text=f"✅ **Saved!**\nName: `{file_name}`"
        )
    except Exception as e:
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text=f"❌ Error: {e}")

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = await get_db(context)
    if not db:
        await update.message.reply_text("📂 Cloud is empty.")
        return

    files = list(db.keys())[-20:] # Show last 20 files
    text = "📂 **Your Files:**\n(Copy name to delete)\n\n" + "\n".join([f"`{f}`" for f in files])
    await update.message.reply_text(text)

async def delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Use: `/delete name`")
        return

    target_name = " ".join(context.args)
    db = await get_db(context)

    if target_name in db:
        del db[target_name]
        await save_db(context, db)
        await update.message.reply_text(f"🗑️ **Deleted:** `{target_name}`")
    else:
        await update.message.reply_text(f"❌ File `{target_name}` not found.")

async def find_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Use: `/find name`")
        return
    
    search = " ".join(context.args).lower()
    db = await get_db(context)
    found = [name for name in db if search in name.lower()]

    if not found:
        await update.message.reply_text("❌ No files found.")
    else:
        await update.message.reply_text(f"🔍 Found:\n" + "\n".join(found))

# --- SERVER ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.wfile.write(b"Bot Alive")

def run_server(): HTTPServer(('0.0.0.0', 8080), SimpleHandler).serve_forever()

if __name__ == '__main__':
    threading.Thread(target=run_server, daemon=True).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # HANDLERS (Restored!)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_files))
    app.add_handler(CommandHandler("delete", delete_file))
    app.add_handler(CommandHandler("find", find_file))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO | filters.PHOTO, store_file))
    
    app.run_polling()
    
