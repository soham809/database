import os
import json
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# ==========================================
# 👇 YOUR CONFIGURATION 👇
# ==========================================
BOT_TOKEN = "8410712491:AAG8RAbd2rql_0yiAlt8HuUWKyQwTn6jO2E"
CHANNEL_ID = -1003798813712
DB_MESSAGE_ID = 15
# ==========================================

# --- PART 1: MEMORY SYSTEM ---

async def get_db(context):
    """Downloads the file list from the PINNED message."""
    try:
        chat = await context.bot.get_chat(CHANNEL_ID)
        pinned_msg = chat.pinned_message
        if not pinned_msg:
            return {}
        return json.loads(pinned_msg.text)
    except Exception as e:
        print(f"⚠️ Error loading DB: {e}")
        return {}

async def save_db(context, new_db):
    """Uploads the new list back to the Pinned Message."""
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
        "🔍 **Find:** `/find name`\n"
        "🗑️ **Delete:** `/delete name`\n"
        "📜 **List:** `/list`"
    )

async def store_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_name = "unknown"
    if update.message.document: file_name = update.message.document.file_name
    elif update.message.video: file_name = update.message.video.file_name or "video.mp4"
    elif update.message.photo: file_name = f"photo_{update.message.photo[-1].file_id[:5]}.jpg"

    msg = await update.message.reply_text("☁️ Saving...")

    try:
        forwarded = await update.message.forward(chat_id=CHANNEL_ID)
        db = await get_db(context)
        db[file_name] = forwarded.message_id
        await save_db(context, db)
        
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            text=f"✅ **Saved!**\nName: `{file_name}`"
        )
    except Exception as e:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            text=f"❌ Error: {e}"
        )

async def find_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use: `/find <name>`")
        return
    
    search = " ".join(context.args).lower()
    db = await get_db(context)
    found = [name for name in db if search in name.lower()]

    if not found:
        await update.message.reply_text("❌ No files found.")
        return
        
    await update.message.reply_text(f"🔍 Found {len(found)} files.")
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

async def delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """NEW: Deletes a file from the database."""
    if not context.args:
        await update.message.reply_text("❌ Use: `/delete <exact_name>`\n(Tip: Copy the name from /list)")
        return

    target_name = " ".join(context.args)
    db = await get_db(context)

    if target_name not in db:
        await update.message.reply_text(f"❌ File `{target_name}` not found in list.")
        return

    # Delete from the dictionary
    del db[target_name]
    
    # Save the new list
    await save_db(context, db)
    
    await update.message.reply_text(f"🗑️ **Deleted:** `{target_name}`")

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = await get_db(context)
    if not db:
        await update.message.reply_text("📂 Cloud is empty.")
        return

    files = list(db.keys())[-20:]
    text = "📂 **Your Files:**\n(Copy name to find or delete)\n\n" + "\n".join([f"`{f}`" for f in files])
    await update.message.reply_text(text)

# --- PART 3: SERVER ---

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_server():
    server = HTTPServer(('0.0.0.0', 8080), SimpleHandler)
    server.serve_forever()

if __name__ == '__main__':
    threading.Thread(target=run_server, daemon=True).start()
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # HANDLERS
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("find", find_file))
    application.add_handler(CommandHandler("list", list_files))
    application.add_handler(CommandHandler("delete", delete_file))  # <--- NEW COMMAND
    application.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO | filters.PHOTO, store_file))
    
    print("Bot is running...")
    application.run_polling()
    
