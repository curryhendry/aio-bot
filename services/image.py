import os
import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, MessageHandler, filters
from config import DOWNLOAD_DIR, logger

if not os.path.exists(DOWNLOAD_DIR): os.makedirs(DOWNLOAD_DIR, exist_ok=True)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        photo_file = await update.message.photo[-1].get_file()
        file_path = os.path.join(DOWNLOAD_DIR, f"{user.id}.jpg")
        await photo_file.download_to_drive(file_path)
        
        status_msg = await update.message.reply_text("✅ 图片已接收，正在生成 Google 搜索链接...")
        
        try:
            with open(file_path, 'rb') as f:
                r = requests.post('https://catbox.moe/user/api.php', data={'reqtype':'fileupload'}, files={'fileToUpload':f})
            if r.status_code == 200:
                google_url = f"https://lens.google.com/upload?url={r.text.strip()}"
                kb = [[InlineKeyboardButton("🚀 Google Lens", url=google_url)]]
                await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=status_msg.message_id, text="✅ 链接已生成 (24h有效)", reply_markup=InlineKeyboardMarkup(kb))
            else: raise Exception("图床上传失败")
        except Exception as e:
            await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=status_msg.message_id, text=f"❌ 搜图失败: {e}")
    except Exception as e: logger.error(e)

def get_handler():
    return MessageHandler(filters.PHOTO, handle_photo)
