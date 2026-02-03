import os
import json
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# ==========================================
# 👇 YOUR CREDENTIALS 👇
# ==========================================
BOT_TOKEN = "8410712491:AAGKgtXtJorFKjaZTwqmU4Run9Unq80NIro"
CHANNEL_ID = -1003798813712
DB_MESSAGE_ID = 15
# ==========================================

# --- DATABASE FUNCTIONS ---
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

# --- COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ **Bot Online (Hugging Face)!**\n- Send files here to save.\n- Upload to Channel to save.\n- Use `/find name` to get files.")

async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🐛 System Status: **Running on Port 7860**\nchannel_watcher: ON")

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = await get_db(context)
    if not db:
        await update.message.reply_text("📂 Database is empty.")
        return
    files = list(db.keys())[-20:] 
    await update.message.reply_text("📂 **Recent Files:**\n\n" + "\n".join([f"`{f}`" for f in files]))

async def delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: `/delete filename.pdf`")
        return
    target = " ".join(context.args)
    db = await get_db(context)
    if target in db:
        del db[target]
        await save_db(context, db)
        await update.message.reply_text(f"🗑 **Deleted:** `{target}`")
    else:
        await update.message.reply_text(f"❌ Could not find: `{target}`")

# 👇 THE SMART FIND COMMAND (Sends the actual file)
async def find_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: `/find name`")
        return
    
    search = " ".join(context.args).lower()
    db = await get_db(context)
    
    matches = {name: fid for name, fid in db.items() if search in name.lower()}

    if not matches:
        await update.message.reply_text("❌ No files found.")
        return

    # If few matches, SEND them!
    if len(matches) <= 3:
        await update.message.reply_text(f"🔍 Found {len(matches)} match(es). Sending...")
        for name, file_id in matches.items():
            try:
                await context.bot.send_document(chat_id=update.effective_chat.id, document=file_id, caption=f"📄 {name}")
            except:
                try:
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=file_id, caption=f"🖼 {name}")
                except:
                    await update.message.reply_text(f"❌ Error sending `{name}`")
    else:
        await update.message.reply_text(f"🔍 **Found many:**\n" + "\n".join([f"`{n}`" for n in matches.keys()]))

# --- FILE SAVER (Handles Channel + Private) ---
async def store_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.channel_post if update.channel_post else update.message
    if not msg: return

    file_id = None
    file_name = "unknown"
    
    if msg.document:
        file_id = msg.document.file_id
        file_name = msg.document.file_name
    elif msg.video:
        file_id = msg.video.file_id
        file_name = msg.video.file_name or "video.mp4"
    elif msg.photo:
        file_id = msg.photo[-1].file_id
        file_name = f"photo_{file_id[:5]}.jpg"
    
    if not file_id: return

    try:
        # If Private Chat -> Forward to Channel
        if update.message:
            await update.message.forward(chat_id=CHANNEL_ID)
        
        db = await get_db(context)
        db[file_name] = file_id 
        await save_db(context, db)
        
        # If Private Chat -> Confirm
        if update.message:
            await update.message.reply_text(f"✅ **Saved!**\n`{file_name}`")
            
    except Exception as e:
        if update.message:
            await update.message.reply_text(f"❌ Error: {e}")

# --- SERVER KEEPALIVE (PORT 7860) ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.wfile.write(b"Hugging Face Bot Running")

def run_server(): HTTPServer(('0.0.0.0', 7860), SimpleHandler).serve_forever()

if __name__ == '__main__':
    threading.Thread(target=run_server, daemon=True).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("debug", debug))
    app.add_handler(CommandHandler("list", list_files))
    app.add_handler(CommandHandler("delete", delete_file))
    app.add_handler(CommandHandler("find", find_file)) # ✅ Added Find
    
    # Watch Channel AND Private Chats
    app.add_handler(MessageHandler(filters.ALL, store_file))
    
    print("🤖 Bot is Starting on Port 7860...")
    app.run_polling(drop_pending_updates=True)
                                                


