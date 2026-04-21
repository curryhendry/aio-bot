import os, requests
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
        
        status_msg = await update.message.reply_text("✅ 图片已接收，正在生成以图搜图链接...")
        
        imgbb_url = "https://api.imgbb.com/1/upload"
        imgbb_key = os.getenv("IMGBB_API_KEY", "")
        
        uploaded_url = None
        
        if imgbb_key:
            # 优先使用 imgbb（需要配置 IMGBB_API_KEY）
            try:
                with open(file_path, 'rb') as f:
                    r = requests.post(imgbb_url, data={'key': imgbb_key}, files={'image': f}, timeout=30)
                j = r.json()
                if r.status_code == 200 and j.get('data', {}).get('url'):
                    uploaded_url = j['data']['url']
                    logger.info(f"imgbb 上传成功: {uploaded_url}")
            except Exception as e:
                logger.warning(f"imgbb 上传失败: {e}")
        
        if not uploaded_url:
            # 降级：使用 Telegram 文件 URL（仅 Telegram 客户端内可用）
            try:
                tg_file_url = f"https://api.telegram.org/file/bot{context.bot.token}/{photo_file.file_path}"
                uploaded_url = tg_file_url
                logger.info(f"使用 Telegram 文件 URL: {tg_file_url[:60]}")
            except Exception as e:
                logger.warning(f"Telegram 文件 URL 获取失败: {e}")
        
        if uploaded_url:
            google_url = f"https://lens.google.com/upload?url={requests.utils.quote(uploaded_url)}"
            kb = [[InlineKeyboardButton("🔍 Google Lens 搜图", url=google_url)]]
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id, message_id=status_msg.message_id,
                text="✅ 链接已生成（有效期约 24h）",
                reply_markup=InlineKeyboardMarkup(kb)
            )
        else:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id, message_id=status_msg.message_id,
                text="❌ 图片上传失败，请稍后重试"
            )
    except Exception as e:
        logger.error(f"以图搜图异常: {e}")
        try:
            await update.message.reply_text(f"❌ 搜图失败: {str(e)[:100]}")
        except: pass

def get_handler():
    return MessageHandler(filters.PHOTO, handle_photo)
