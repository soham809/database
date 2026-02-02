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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ **Bot Online!**\nSend a file to save it.\nUse `/find name` to get files.")

async def store_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await update.message.forward(chat_id=CHANNEL_ID)
        db = await get_db(context)
        db[file_name] = file_id 
        await save_db(context, db)
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text=f"✅ **Saved!**\n`{file_name}`")
    except Exception as e:
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text=f"❌ Error: {e}")

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = await get_db(context)
    if not db:
        await update.message.reply_text("📂 Empty.")
        return
    files = list(db.keys())[-20:]
    await update.message.reply_text("📂 **Recent Files:**\n" + "\n".join([f"`{f}`" for f in files]))

async def delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Use: `/delete name`")
        return
    target = " ".join(context.args)
    db = await get_db(context)
    if target in db:
        del db[target]
        await save_db(context, db)
        await update.message.reply_text(f"🗑️ Deleted `{target}`")
    else:
        await update.message.reply_text("❌ Not found.")

# 👇👇👇 THE NEW SMART FIND COMMAND 👇👇👇
async def find_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Use: `/find name`")
        return
    
    search = " ".join(context.args).lower()
    db = await get_db(context)
    
    # Find all matches
    matches = {name: fid for name, fid in db.items() if search in name.lower()}

    if not matches:
        await update.message.reply_text("❌ No files found.")
        return

    # IF FEW MATCHES -> SEND THE FILES!
    if len(matches) <= 3:
        await update.message.reply_text(f"🔍 Found {len(matches)} match(es). Sending...")
        for name, file_id in matches.items():
            try:
                # Try sending as document (PDF, Video, etc.)
                await context.bot.send_document(chat_id=update.effective_chat.id, document=file_id, caption=f"📄 {name}")
            except:
                # If failed, it might be a photo
                try:
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=file_id, caption=f"🖼 {name}")
                except:
                    await update.message.reply_text(f"❌ Error sending `{name}`")
    
    # IF MANY MATCHES -> SHOW LIST
    else:
        await update.message.reply_text(f"🔍 **Found many files:**\n" + "\n".join([f"`{n}`" for n in matches.keys()]))

# --- SERVER ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.wfile.write(b"Bot Alive")

def run_server(): HTTPServer(('0.0.0.0', 8080), SimpleHandler).serve_forever()

if __name__ == '__main__':
    threading.Thread(target=run_server, daemon=True).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_files))
    app.add_handler(CommandHandler("delete", delete_file))
    app.add_handler(CommandHandler("find", find_file))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO | filters.PHOTO, store_file))
    app.run_polling()
    
