import os, threading, psutil, asyncio, sqlite3, socket as _sock_mod, logging
from flask import Flask
from telegram import Update, BotCommand, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
from telegram.request import HTTPXRequest
from config import BOT_TOKEN, PORT, DB_FILE, SEARCH_WAIT, LEGO_INPUT, restricted, logger, CHANGELOG_FILE, ALLOWED_IDS

# 抑制 httpx 轮询日志刷屏
logging.getLogger("httpx").setLevel(logging.WARNING)

try:
    with open("CHANGELOG.md", "r", encoding="utf-8") as _f:
        VERSION = next((ln.strip().replace("## ", "") for ln in _f if ln.startswith("## v")), "未知版本")
except:
    VERSION = "未知版本"
from database import init_db
import services.lego as lego
import services.media as media
try:
    import services.image as image
except ImportError:
    image = None

app_flask = Flask(__name__)
@app_flask.route('/')
def health(): return "OK", 200
def run_flask(): app_flask.run(host='0.0.0.0', port=PORT, use_reloader=False)

def get_changelog():
    """返回纯文本 changelog（去除所有格式标签），防止 Telegram 误解析特殊字符"""
    try:
        with open(CHANGELOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        blocks, current = [], []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('## '):
                if current: blocks.append(''.join(current))
                current = [stripped[3:]]  # 去掉 "## " 前缀
            elif stripped and stripped not in ('---',):
                # 跳过重复的版本行（如 "v1.0.117 (2026-04-29)"，已在标题出现）
                if current and stripped.startswith('v1.') and '(' in stripped:
                    continue
                # 跳过更新版本号等冗余行
                if '更新版本号' in stripped or '更新人' in stripped:
                    continue
                current.append('\n' + stripped)
        if current: blocks.append(''.join(current))
        return '\n\n'.join(blocks[:5]).strip()
    except: return "暂无更新说明"

async def start(u, c):
    txt = f"🤖 <b>All in One Bot</b>\n\n{get_changelog()}"
    kb = [[KeyboardButton("🔍 搜图书/电影/电视"), KeyboardButton("🧱 乐高查询")], [KeyboardButton("⚙️ 系统状态")]]
    await u.message.reply_text(txt, parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def handle_reply_menu(u, c):
    t = u.message.text
    if "乐高查询" in t:
        await lego.lego_menu_panel(u, c)
        return ConversationHandler.END
    elif "系统状态" in t:
        await status(u, c)
        return ConversationHandler.END
    elif t.startswith("🔍"):
        return await media.search_entry(u, c)

def get_system_stats():
    try:
        cpu = psutil.cpu_percent(interval=0.2)
        mem = psutil.virtual_memory()
        d = psutil.disk_usage('/')
        return cpu, mem.percent, d.percent, round(d.used/(1024**3),2), round(d.total/(1024**3),2)
    except: return 0, 0, 0, 0, 0

async def status(u, c):
    cpu, ram, dp, du, dt = await asyncio.to_thread(get_system_stats)
    
    is_run = False
    try:
        is_run, mt_msg = await asyncio.to_thread(media.check_metube_status)
        metube_str = f"{'🟢' if is_run else '🔴'} {mt_msg}"
    except: 
        metube_str = "🔴 未知"
        
    try: 
        lego_st = await lego.get_system_status_text()
    except: 
        lego_st = "📚 人仔收录: N/A\n🕵️ 人仔数据库维护: N/A\n🛡️ FlareSolverr: 未知"
    
    fs_is_run = False
    try:
        fs_is_run, fs_msg = await asyncio.to_thread(lego.check_flaresolverr_status)
    except: pass
        
    msg = (
        f"📊 <b>系统状态</b>\n"
        f"⚙️ CPU: {cpu}%\n"
        f"⚡️ RAM: {ram}%\n"
        f"💾 Disk: {dp}% ({du}G / {dt}G)\n"
        f"🔗 MeTube: {metube_str}\n\n"
        f"{lego_st}"
    )
    keyboard = []
    if is_run:
        keyboard.append([InlineKeyboardButton("⏹️ 关闭 MeTube", callback_data="stop_metube")])
    if fs_is_run:
        keyboard.append([InlineKeyboardButton("⏹️ 关闭 FlareSolverr", callback_data="stop_flaresolverr")])
    keyboard.append([InlineKeyboardButton("♻️ 重启机器人", callback_data="restart_bot")])
    await u.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

async def stop_metube_callback(u, c):
    """关闭 MeTube 容器"""
    query = u.callback_query
    await query.answer("⏹️ 正在关闭 MeTube...")
    try:
        import docker as _docker
        client = _docker.from_env()
        for container in client.containers.list():
            if "MeTube" in container.name or "metube" in container.name.lower():
                container.stop()
                break
    except Exception as e:
        await query.edit_message_text(f"❌ 关闭失败: {str(e)}")
        return
    # 关闭后刷新系统状态
    await query.message.delete()
    cpu, ram, dp, du, dt = await asyncio.to_thread(get_system_stats)
    is_run = False
    metube_str = "🔴 已关闭"
    try:
        lego_st = await lego.get_system_status_text()
    except:
        lego_st = "📚 人仔收录: N/A\n🕵️ 人仔数据库维护: N/A\n🛡️ FlareSolverr: 未知"
    msg = (
        f"📊 <b>系统状态</b>\n"
        f"⚙️ CPU: {cpu}%\n"
        f"⚡️ RAM: {ram}%\n"
        f"💾 Disk: {dp}% ({du}G / {dt}G)\n"
        f"🔗 MeTube: {metube_str}\n\n"
        f"{lego_st}"
    )
    keyboard = []
    try:
        _fs_run, _fs_msg = await asyncio.to_thread(lego.check_flaresolverr_status)
        if _fs_run:
            keyboard.append([InlineKeyboardButton("⏹️ 关闭 FlareSolverr", callback_data="stop_flaresolverr")])
    except: pass
    keyboard.append([InlineKeyboardButton("♻️ 重启机器人", callback_data="restart_bot")])
    await c.bot.send_message(u.effective_chat.id, msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

async def stop_flaresolverr_callback(u, c):
    """关闭 FlareSolverr 容器"""
    query = u.callback_query
    await query.answer("⏹️ 正在关闭 FlareSolverr...")
    try:
        import docker as _docker
        client = _docker.from_env()
        for container in client.containers.list():
            if "flaresolverr" in container.name.lower():
                container.stop()
                break
    except Exception as e:
        await query.edit_message_text(f"❌ 关闭失败: {str(e)}")
        return
    await query.message.delete()
    cpu, ram, dp, du, dt = await asyncio.to_thread(get_system_stats)
    is_run = False
    try:
        is_run, mt_msg = await asyncio.to_thread(media.check_metube_status)
        metube_str = f"{'🟢' if is_run else '🔴'} {mt_msg}"
    except:
        metube_str = "🔴 未知"
    try:
        lego_st = await lego.get_system_status_text()
    except:
        lego_st = "📚 人仔收录: N/A\n🕵️ 人仔数据库维护: N/A\n🛡️ FlareSolverr: 未知"
    msg = (
        f"📊 <b>系统状态</b>\n"
        f"⚙️ CPU: {cpu}%\n"
        f"⚡️ RAM: {ram}%\n"
        f"💾 Disk: {dp}% ({du}G / {dt}G)\n"
        f"🔗 MeTube: {metube_str}\n\n"
        f"{lego_st}"
    )
    keyboard = []
    if is_run:
        keyboard.append([InlineKeyboardButton("⏹️ 关闭 MeTube", callback_data="stop_metube")])
    keyboard.append([InlineKeyboardButton("♻️ 重启机器人", callback_data="restart_bot")])
    await c.bot.send_message(u.effective_chat.id, msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

async def reboot_cmd(u, c):
    """处理 /reboot 命令"""
    await c.bot.send_message(u.effective_chat.id, "♻️ 正在重启机器人...")
    try:
        container_name = "All-in-One_bot"
        s = _sock_mod.socket(_sock_mod.AF_UNIX, _sock_mod.SOCK_STREAM)
        s.connect("/var/run/docker.sock")
        s.settimeout(15)
        req = f"POST /containers/{container_name}/restart?t=5 HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
        s.sendall(req.encode())
        resp = b""
        while True:
            chunk = s.recv(4096)
            if not chunk: break
            resp += chunk
        s.close()
        status_line = resp.split(b"\r\n")[0].decode()
        if "200" in status_line:
            await c.bot.send_message(u.effective_chat.id, "✅ 机器人已重启")
        else:
            await c.bot.send_message(u.effective_chat.id, f"❌ 重启失败: {status_line}")
    except Exception as e:
        await c.bot.send_message(u.effective_chat.id, f"❌ 重启失败: {str(e)}")

async def restart_bot_callback(u, c):
    """处理重启机器人按钮回调（通过 Docker Socket API）"""
    query = u.callback_query
    await query.answer("♻️ 正在重启机器人...")
    try:
        container_name = "All-in-One_bot"
        s = _sock_mod.socket(_sock_mod.AF_UNIX, _sock_mod.SOCK_STREAM)
        s.connect("/var/run/docker.sock")
        s.settimeout(15)
        req = f"POST /containers/{container_name}/restart?t=5 HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
        s.sendall(req.encode())
        resp = b""
        while True:
            chunk = s.recv(4096)
            if not chunk: break
            resp += chunk
        s.close()
        status_line = resp.split(b"\r\n")[0].decode()
        if "200" in status_line:
            await query.edit_message_text("✅ 机器人已重启")
        else:
            await query.edit_message_text(f"❌ 重启失败: {status_line}")
    except Exception as e:
        await query.edit_message_text(f"❌ 重启失败: {str(e)}")

async def post_init(app):
    try:
        # 清空所有语言码的命令缓存
        await app.bot.delete_my_commands()
        for lc in ["zh-cn", "zh-tw", "zh-hans", "zh-hant", "en", ""]:
            try: await app.bot.delete_my_commands(language_code=lc)
            except: pass
    except Exception as e:
        logging.error(f"删除命令缓存失败: {e}")

    try:
        await app.bot.set_my_commands([
            BotCommand("start", "🤖 开始 / 主菜单"),
            BotCommand("s", "🔍 搜书/ 影视"),
            BotCommand("lego", "🧱 乐高查询"),
            BotCommand("mini", "🧸 查人仔"),
            BotCommand("reboot", "🔄 重启机器人")
        ])
    except Exception as e:
        logging.error(f"设置命令列表失败: {e}")

    # 上线通知：展示完整菜单和版本说明（与 /start 一致）
    if ALLOWED_IDS:
        try:
            txt = f"🤖 <b>All in One Bot</b>\n\n{get_changelog()}"
            kb_data = [[KeyboardButton("🔍 搜图书/电影/电视"), KeyboardButton("🧱 乐高查询")], [KeyboardButton("⚙️ 系统状态")]]
            await app.bot.send_message(ALLOWED_IDS[0], txt, parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardMarkup(kb_data, resize_keyboard=True))
        except Exception as e:
            logging.warning(f"上线通知发送失败: {e}")

def main():
    if not os.path.exists(DB_FILE): init_db()
    
    # 自定义 HTTPXRequest：代理 + 连接池
    proxy_url = os.getenv('HTTPS_PROXY', 'http://192.168.100.1:7890')
    request = HTTPXRequest(
        connection_pool_size=128,
        connect_timeout=30,
        read_timeout=60,
        write_timeout=30,
        pool_timeout=30,
    )
    
    app = Application.builder().token(BOT_TOKEN).request(request).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reboot", reboot_cmd))

    # [Fix 1] 搜书必须是最先注册的，确保能进入 SEARCH_WAIT 状态机
    _MENU_TEXT = filters.Regex(r'^(🔍 搜图书|🧱 乐高查询|⚙️ 系统状态)')
    search_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r'^🔍'), media.search_entry), 
            CommandHandler("s", media.search_entry),
            CallbackQueryHandler(media.search_entry, pattern=r'^media_retry$')
        ],
        states={SEARCH_WAIT: [
            CallbackQueryHandler(media.handle_callback, pattern=r'^(restore_search|t:|n:)'),
            MessageHandler(filters.TEXT & ~filters.COMMAND & ~_MENU_TEXT, media.search_input_s)
        ]},
        fallbacks=[MessageHandler(_MENU_TEXT, handle_reply_menu)]
    )
    app.add_handler(search_conv)

    # [Fix 2] 专属菜单拦截 (只拦截乐高和系统状态，不拦截搜书)
    app.add_handler(MessageHandler(filters.Regex(r'(乐高查询|系统状态)'), handle_reply_menu))

    # 乐高专属对话与回调
    app.add_handler(lego.get_conv_handler(extra_fallbacks=[MessageHandler(_MENU_TEXT, handle_reply_menu)]))
    for h in lego.get_handlers(): app.add_handler(h)

    # Media 通用回调与文件拦截 (放在最后，兜底处理网址)
    app.add_handler(CallbackQueryHandler(media.handle_callback, pattern=r'^(restore_search|t:|n:)'))
    app.add_handler(MessageHandler((filters.TEXT | filters.Document.VIDEO | filters.VIDEO) & ~filters.COMMAND, media.handle_file))
    app.add_handler(CallbackQueryHandler(restart_bot_callback, pattern=r'^restart_bot$'))
    app.add_handler(CallbackQueryHandler(stop_metube_callback, pattern=r'^stop_metube$'))
    app.add_handler(CallbackQueryHandler(stop_flaresolverr_callback, pattern=r'^stop_flaresolverr$'))

    # Image Handler
    if image and hasattr(image, 'get_handler'): 
        app.add_handler(image.get_handler())

    threading.Thread(target=run_flask, daemon=True).start()
    import asyncio; asyncio.get_event_loop().run_until_complete(app.run_polling()))

if __name__ == '__main__': main()
