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
        
        uploaded_url = None
        error_msg = None
        
        # 方案1: litterbox.catbox.moe (临时图床，无需认证)
        try:
            with open(file_path, 'rb') as f:
                r = requests.post(
                    'https://litterbox.catbox.moe/resources/internals/api.php',
                    data={'reqtype': 'fileupload', 'time': '24h'},
                    files={'fileToUpload': f},
                    timeout=30, verify=False
                )
            if r.status_code == 200 and r.text.startswith('http'):
                uploaded_url = r.text.strip()
                logger.info(f"litterbox 上传成功: {uploaded_url}")
        except Exception as e:
            error_msg = f"litterbox: {e}"
            logger.warning(error_msg)
        
        # 方案2: imgbb (需要配置 IMGBB_API_KEY)
        if not uploaded_url:
            imgbb_key = os.getenv("IMGBB_API_KEY", "")
            if imgbb_key:
                try:
                    with open(file_path, 'rb') as f:
                        r = requests.post(
                            'https://api.imgbb.com/1/upload',
                            data={'key': imgbb_key},
                            files={'image': f},
                            timeout=30
                        )
                    j = r.json()
                    if r.status_code == 200 and j.get('data', {}).get('url'):
                        uploaded_url = j['data']['url']
                        logger.info(f"imgbb 上传成功: {uploaded_url}")
                except Exception as e:
                    error_msg = f"imgbb: {e}"
                    logger.warning(error_msg)
        
        if uploaded_url:
            google_url = f"https://lens.google.com/upload?url={requests.utils.quote(uploaded_url)}"
            kb = [[InlineKeyboardButton("🔍 Google Lens 搜图", url=google_url)]]
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id, message_id=status_msg.message_id,
                text="✅ 链接已生成（24h有效）",
                reply_markup=InlineKeyboardMarkup(kb)
            )
        else:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id, message_id=status_msg.message_id,
                text=f"❌ 图片上传失败 ({error_msg or '网络错误'})"
            )
    except Exception as e:
        logger.error(f"以图搜图异常: {e}")
        try:
            await update.message.reply_text(f"❌ 搜图失败: {str(e)[:100]}")
        except: pass

def get_handler():
    return MessageHandler(filters.PHOTO, handle_photo)
