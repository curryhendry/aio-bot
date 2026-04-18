import logging, requests, asyncio, math, re, time, html, os, sqlite3, threading, zipfile, io, csv
import cloudscraper
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ConversationHandler, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from config import RB_BASE, RB_KEY, FAKE_HEADERS, USD_CNY_RATE, LEGO_INPUT, DB_FILE, RB_CSV_URL

logger = logging.getLogger(__name__)
SESSION = requests.Session()
SESSION.headers.update(FAKE_HEADERS)

async def silent_cancel(update: Update, context):
    return ConversationHandler.END

async def cancel_callback(update: Update, context):
    query = update.callback_query
    if query:
        try:
            await query.answer()
            await query.message.delete()
        except: pass
    return ConversationHandler.END

UPDATE_STATUS = {"active": False, "task_name": "", "progress": "", "last_result": "无记录"}
def get_theme_display(en_name):
    return en_name

def rb_get(ep, p=None):
    try:
        url = f"{RB_BASE.rstrip('/')}/{ep.strip('/')}/"
        headers = {"Authorization": f"key {RB_KEY}", "Accept": "application/json"}
        resp = SESSION.get(url, headers=headers, params=p, timeout=10)
        return resp.json() if resp.status_code == 200 else {}
    except: return {}

def get_brickset_price(set_num):
    try:
        resp = requests.get(f"https://brickset.com/sets/{set_num}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        m = re.search(r'RRP</dt>\s*<dd>.*?\$(\d[\d\.]*)', resp.text, re.DOTALL)
        return float(m.group(1)) if m else None
    except: return None

def clean_id(uid): return uid.replace('-1', '')

def resolve_fig_id(query):
    q = query.strip()
    clean = q.lower().replace('-', '').replace(' ', '')
    target_id = None
    m = re.match(r'^([a-z]+)(\d+)$', clean)
    if m: target_id = f"{m.group(1)}{int(m.group(2)):04d}"
    elif re.match(r'^\d+$', clean): target_id = f"fig-{int(clean):06d}"
    if target_id:
        try:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT rb_id FROM minifig_map WHERE ext_id = ? OR rb_id = ?", (target_id, target_id))
            row = c.fetchone()
            conn.close()
            if row: return row[0]
            return target_id
        except: pass
    return q

def get_fig_bl_id(rb_uid):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT ext_id FROM minifig_map WHERE rb_id = ?", (rb_uid,))
        row = c.fetchone()
        conn.close()
        if row and row[0]: return row[0]
    except: pass
    return None

def get_db_stats():
    try:
        conn = sqlite3.connect(DB_FILE); c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM minifig_map WHERE ext_id != rb_id AND ext_id IS NOT NULL AND ext_id != ''")
        mapped = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM minifig_map")
        total = c.fetchone()[0]; conn.close()
        return mapped, total, UPDATE_STATUS.get("active")
    except: return 0, 0, False

def report_progress(context, chat_id, message_id, text, loop, kb=None):
    UPDATE_STATUS["progress"] = text
    async def _edit():
        try:
            timestamp = time.strftime("%H:%M:%S")
            task_label = "📥 CSV下载" if UPDATE_STATUS["task_name"] == "csv" else "🕷️ 爬虫补全"
            markup = InlineKeyboardMarkup(kb) if kb else None
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, 
                text=f"🛠️ <b>{task_label}</b>\n\n{text}\n\n🕒 {timestamp}", 
                parse_mode=ParseMode.HTML, reply_markup=markup
            )
        except Exception: pass
    asyncio.run_coroutine_threadsafe(_edit(), loop)

def do_download_csv(report_func):
    try:
        report_func("1️⃣ 连接官方 CDN...")
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(RB_CSV_URL, headers=headers, stream=True, timeout=60)
        if r.status_code != 200: return False, "下载失败"
        total_size = int(r.headers.get('content-length', 0))
        block_size = 8192; downloaded = 0; content = io.BytesIO()
        last_report = time.time()
        for data in r.iter_content(block_size):
            content.write(data); downloaded += len(data)
            if time.time() - last_report > 2.0:
                pct = int(downloaded / total_size * 100) if total_size else 0
                report_func(f"📥 下载中: {pct}% ({downloaded / 1048576:.1f}MB)")
                last_report = time.time()
        report_func("2️⃣ 解压并分析数据...")
        content.seek(0)
        with zipfile.ZipFile(content) as z:
            with z.open('minifigs.csv') as f:
                reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))
                conn = sqlite3.connect(DB_FILE); c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM minifig_map"); count_before = c.fetchone()[0]
                batch = []; count = 0; last_db_report = time.time()
                for row in reader:
                    batch.append((row['fig_num'], "", row['name'], row['img_url'], "", row['num_parts']))
                    count += 1
                    if len(batch) >= 5000:
                        c.executemany("INSERT INTO minifig_map (rb_id, ext_id, name, img, year, parts) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(rb_id) DO UPDATE SET name=excluded.name, img=excluded.img, parts=excluded.parts", batch)
                        batch = []
                        if time.time() - last_db_report > 3.0:
                            report_func(f"🔄 处理中: {count} 条..."); last_db_report = time.time()
                if batch: c.executemany("INSERT INTO minifig_map (rb_id, ext_id, name, img, year, parts) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(rb_id) DO UPDATE SET name=excluded.name, img=excluded.img, parts=excluded.parts", batch)
                c.execute("SELECT COUNT(*) FROM minifig_map"); added = c.fetchone()[0] - count_before
                conn.commit(); conn.close()
                return True, f"✅ 导入完成\n📊 总数: {count}\n🆕 新增: {added}\n♻️ 更新: {count - added}"
    except Exception as e: return False, f"异常: {str(e)[:50]}"

def do_scrape_missing(report_func):
    try:
        report_func("🔍 扫描待补全数据...")
        conn = sqlite3.connect(DB_FILE); c = conn.cursor()
        c.execute("SELECT rb_id FROM minifig_map WHERE ext_id IS NULL OR ext_id = '' OR ext_id = rb_id")
        targets = [row[0] for row in c.fetchall()]; conn.close()
        total = len(targets); success = 0; fail = 0
        if total == 0: return True, "✅ 数据已完整，无需补全。"
        session = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
        )
        session.headers.update(FAKE_HEADERS)
        last_report = time.time(); consecutive_fail = 0
        for idx, rb_id in enumerate(targets):
            if not UPDATE_STATUS["active"]: return False, "🛑 任务已手动停止"
            if time.time() - last_report > 3.0:
                report_func(f"🕷️ 补全进度: {idx}/{total}\n✅ 成功: {success}\n❌ 未找到: {fail}")
                last_report = time.time()
            try:
                resp = session.get(f"https://rebrickable.com/minifigs/{rb_id}/", timeout=15)
                if resp.status_code == 200:
                    bl_id = None; txt = resp.text
                    m1 = re.search(r'bricklink\.com.*?catalogitem\.page\?M=([a-zA-Z0-9]+)', txt)
                    if m1: bl_id = m1.group(1)
                    else:
                        m2 = re.search(r'brickset\.com.*?minifigs/([a-zA-Z0-9\-]+)', txt)
                        if m2: bl_id = m2.group(1)
                    if bl_id:
                        conn = sqlite3.connect(DB_FILE)
                        conn.execute("UPDATE minifig_map SET ext_id = ? WHERE rb_id = ?", (bl_id, rb_id))
                        conn.commit(); conn.close()
                        success += 1; consecutive_fail = 0
                    else: fail += 1
                else:
                    fail += 1
                    logger.warning(f"爬虫 {rb_id}: HTTP {resp.status_code}")
                    if resp.status_code == 403:
                        consecutive_fail += 1; time.sleep(5)
                        if consecutive_fail > 5: return False, "⚠️ 触发反爬，任务暂停"
                    elif resp.status_code == 429:
                        consecutive_fail += 1; time.sleep(30)
                        if consecutive_fail > 3: return False, "⚠️ 触发频率限制，任务暂停"
                time.sleep(2)
            except Exception as e:
                fail += 1
                logger.warning(f"爬虫 {rb_id} 异常: {type(e).__name__}: {e}")
                time.sleep(1)
        return True, f"✅ 补全结束\n成功: {success} / 未找到: {fail}"
    except Exception as e: return False, f"爬虫异常: {e}"

def run_task_wrapper(task_type, context, chat_id, message_id, loop):
    global UPDATE_STATUS
    UPDATE_STATUS["active"] = True
    UPDATE_STATUS["task_name"] = task_type
    def _report(text, kb=None): report_progress(context, chat_id, message_id, text, loop, kb)
    try:
        success = False; msg = "未知结果"
        if task_type == 'csv': success, msg = do_download_csv(_report)
        elif task_type == 'scrape': success, msg = do_scrape_missing(_report)
        UPDATE_STATUS["last_result"] = msg
        final_kb = [[InlineKeyboardButton("🕷️ 继续: 2. 爬虫补全", callback_data="lego_do_scrape")]] if task_type == 'csv' and success else None
        _report(msg, kb=final_kb)
    except Exception as e: UPDATE_STATUS["last_result"] = f"⚠️ 崩溃: {e}"; _report(f"⚠️ 严重错误: {e}")
    finally: UPDATE_STATUS["active"] = False; UPDATE_STATUS["progress"] = ""

async def lego_trigger_update_handler(u, c):
    d = u.callback_query.data; await u.callback_query.answer("🚀 启动...")
    if UPDATE_STATUS["active"]: await u.callback_query.message.reply_text(f"⚠️ 任务进行中: {UPDATE_STATUS['task_name']}", quote=True); return
    task_type = "csv" if d == "lego_do_csv" else "scrape"
    init_text = "📥 准备下载..." if task_type == "csv" else "🕷️ 准备爬取..."
    msg = await u.callback_query.message.edit_text(f"⏳ {init_text}", parse_mode=ParseMode.HTML)
    threading.Thread(target=run_task_wrapper, args=(task_type, c, u.effective_chat.id, msg.message_id, asyncio.get_running_loop()), daemon=True).start()

async def get_system_status_text():
    mapped, total, active = get_db_stats(); st = "✅ 空闲"
    if active: st = f"🔄 {UPDATE_STATUS['task_name']}中..."
    return f"📚 <b>人仔收录:</b> <code>{mapped}/{total}</code>\n🕵️ <b>人仔数据库维护:</b> {st}"

async def lego_menu_panel(update, context):
    if getattr(context, 'args', None): await do_lego_search(update.effective_chat.id, context, 'set', " ".join(context.args)); return
    kb = [
        [InlineKeyboardButton("🔢 搜套装", callback_data="L~ASK~set"), InlineKeyboardButton("🧸 搜人仔", callback_data="L~ASK~fig")],
        [InlineKeyboardButton("⚙️ 搜零件", callback_data="L~ASK~part"), InlineKeyboardButton("🧩 搜 MOC", callback_data="L~ASK~moc")],
        [InlineKeyboardButton("🆕 新品速递", callback_data="L~NEW"), InlineKeyboardButton("🌐 网站导航", callback_data="L~NAV")],
        [InlineKeyboardButton("🔄 更新人仔数据库", callback_data="lego_update_ask"), InlineKeyboardButton("📤 导出数据库CSV", callback_data="lego_export")]
    ]
    txt = f"🧱 <b>乐高查询中心</b>\n\n{await get_system_status_text()}"
    try:
        if update.callback_query: await update.callback_query.message.edit_text(txt, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))
        else: await update.message.reply_text(txt, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))
    except: await context.bot.send_message(update.effective_chat.id, txt, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))

async def lego_update_ask_handler(update, context):
    await update.callback_query.answer()
    if UPDATE_STATUS["active"]: await context.bot.send_message(update.effective_chat.id, f"⚠️ 任务运行中: {UPDATE_STATUS.get('progress')}"); return
    kb = [[InlineKeyboardButton("📥 1. 下载官方数据 (CSV)", callback_data="lego_do_csv")], [InlineKeyboardButton("🕷️ 2. 补全第三方ID (爬虫)", callback_data="lego_do_scrape")], [InlineKeyboardButton("🔙 返回", callback_data="L~MENU")]]
    await context.bot.send_message(update.effective_chat.id, "🛠️ <b>数据库维护面板</b>\n\n请选择操作步骤：\n1️⃣ <b>下载官方数据</b>：获取最新的 Rebrickable 人仔列表 (快)\n2️⃣ <b>补全第三方ID</b>：针对无 BrickLink ID 的记录进行爬取 (慢)", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))

async def lego_website_nav(update, context):
    kb = [[InlineKeyboardButton("🏠 LEGO 官网", url="https://www.lego.com")], [InlineKeyboardButton("📘 Blue-Ocean (说明书)", url="https://www.blue-ocean-ag.com/bi")], [InlineKeyboardButton("🧱 Rebrickable (数据库)", url="https://rebrickable.com")], [InlineKeyboardButton("🔗 BrickLink (交易/询价)", url="https://www.bricklink.com")], [InlineKeyboardButton("📚 Brickset (资讯/记录)", url="https://brickset.com")], [InlineKeyboardButton("🔙 返回菜单", callback_data="L~MENU")]]
    await update.callback_query.message.edit_text("🧭 <b>乐高实用网站导航</b>", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))

async def lego_new_sets_year_picker(update, context):
    """新品速递 - 年份选择"""
    now = time.localtime()
    years = []
    if now.tm_mon >= 7:
        years.append(now.tm_year + 1)
    years.append(now.tm_year)
    for i in range(1, 20 - len(years) + 1):
        years.append(now.tm_year - i)
    kb = []
    row = []
    for year in years:
        row.append(InlineKeyboardButton(f"📅 {year}", callback_data=f"L~NL~{year}~1"))
        if len(row) == 3:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([InlineKeyboardButton("🔙 返回菜单", callback_data="L~MENU")])
    try: await update.callback_query.message.delete()
    except: pass
    await context.bot.send_message(update.effective_chat.id, "🆕 <b>新品速递</b>\n\n选择年份查看该年度套装：", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))

async def lego_new_sets_list(update, context):
    """新品速递 - 按年份查看套装列表"""
    pts = update.callback_query.data.split('~')
    year = int(pts[2])
    page = int(pts[3])
    res = await asyncio.to_thread(rb_get, "sets", {"page": page, "page_size": 10, "min_year": year, "max_year": year, "ordering": "-year"})
    total = res.get('count', 0)
    if not res.get('results'):
        await update.callback_query.answer("该年份无结果", show_alert=True)
        return
    await update.callback_query.answer()
    try: await update.callback_query.message.delete()
    except: pass
    kb = []
    for i in res['results']:
        uid = i.get('set_num')
        btn_txt = f"[{clean_id(uid)}] {i.get('name','')[:36]} ({i.get('num_parts','')}p)"
        kb.append([InlineKeyboardButton(btn_txt, callback_data=f"L~D~set~{uid}~1~NL~{year}~{page}")])
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"L~NL~{year}~{page-1}"))
    if total > page * 10:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"L~NL~{year}~{page+1}"))
    if nav:
        kb.append(nav)
    kb.append([InlineKeyboardButton("🔙 选择年份", callback_data="L~NEW"), InlineKeyboardButton("🏠 菜单", callback_data="L~MENU")])
    max_page = math.ceil(total / 10)
    await context.bot.send_message(
        update.effective_chat.id,
        f"🆕 <b>{year}年新品</b>\n\n📊 共 {total} 套 ({page}/{max_page})",
        parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb)
    )

async def lego_mini_shortcut(update, context):
    context.user_data['lego_type'] = 'fig' 
    if getattr(context, 'args', None): await do_lego_search(update.effective_chat.id, context, 'fig', " ".join(context.args))
    else: await context.bot.send_message(update.effective_chat.id, "🧸 请输入人仔关键词/编号:", parse_mode=ParseMode.HTML); return LEGO_INPUT

async def lego_search_entry(update, context):
    q = update.callback_query; await q.answer()
    context.user_data['lego_type'] = q.data.split("~")[2]
    await context.bot.send_message(update.effective_chat.id, "⌨️ 请输入关键词/编号:", parse_mode=ParseMode.HTML)
    return LEGO_INPUT

async def lego_input_handler(update, context):
    await do_lego_search(update.effective_chat.id, context, context.user_data.get('lego_type','set'), update.message.text.strip())
    return ConversationHandler.END

async def do_lego_search(chat_id, context, dtype, query, page=1, edit=False, update_obj=None):
    if not edit: context.user_data[f'lego_q_{dtype}'] = query
    elif not query: query = context.user_data.get(f'lego_q_{dtype}', '')
    if not query:
        if update_obj: await update_obj.callback_query.answer("⚠️ 会话过期", show_alert=True)
        else: await context.bot.send_message(chat_id, "⚠️ 会话过期")
        return
    if dtype == 'moc':
        kb = [[InlineKeyboardButton("🌐 前往 Rebrickable 查看 MOC", url=f"https://rebrickable.com/mocs/?show_printed=on&include_accessory=1&q={query}")], [InlineKeyboardButton("🔍 换关键词", callback_data=f"L~ASK~moc")]]
        txt = f"🧩 <b>MOC 搜索: {query}</b>\n\n👇 点击下方按钮查看结果："
        if edit and update_obj: await update_obj.callback_query.message.edit_text(txt, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))
        else: await context.bot.send_message(chat_id, txt, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))
        return
    ep = "sets" if dtype=='set' else ("minifigs" if dtype=='fig' else "parts")
    final_query = query; is_direct_id = False
    if dtype == 'fig':
        resolved = resolve_fig_id(query); final_query = resolved
        if resolved.startswith('fig-'): is_direct_id = True
    status_msg = None
    if not edit: status_msg = await context.bot.send_message(chat_id, f"⏳ 正在搜索 {dtype}: {final_query}...")
    res = {}
    if is_direct_id:
        detail = await asyncio.to_thread(rb_get, f"{ep}/{final_query}")
        if detail and detail.get('set_num'): res = {'count': 1, 'results': [detail]}
        else: res = await asyncio.to_thread(rb_get, ep, {"page": page, "page_size": 10, "search": final_query})
    else: res = await asyncio.to_thread(rb_get, ep, {"page": page, "page_size": 10, "search": final_query})
    if status_msg: 
        try: await status_msg.delete() 
        except: pass
    if res.get('results'):
        if res.get('count')==1 and page==1:
            uid = res['results'][0].get('set_num') or res['results'][0].get('part_num')
            await show_lego_detail(chat_id, context, dtype, uid, res['results'][0], update_obj=update_obj, page=page); return
        kb = []
        for i in res['results']:
            uid = i.get('set_num') or i.get('part_num')
            if dtype == 'fig':
                bl_id = await asyncio.to_thread(get_fig_bl_id, uid)
                id_display = f"{bl_id} | {clean_id(uid)}" if bl_id else clean_id(uid)
                btn_txt = f"[{id_display}] {i.get('name')[:30]}"
            elif dtype == 'part': btn_txt = f"[{uid}] {i.get('name')[:30]}"
            else: btn_txt = f"[{clean_id(uid)}] {i.get('name')[:25]} ({i.get('year','')}) ({i.get('num_parts','')}p)"
            kb.append([InlineKeyboardButton(btn_txt, callback_data=f"L~D~{dtype}~{uid}~{page}")])
        nav = []; sq = query[:15].replace('~','') 
        if res.get('previous'): nav.append(InlineKeyboardButton("⬅️", callback_data=f"L~P~{dtype}~{page-1}~{sq}"))
        if res.get('next'): nav.append(InlineKeyboardButton("➡️", callback_data=f"L~P~{dtype}~{page+1}~{sq}"))
        if nav: kb.append(nav)
        kb.append([InlineKeyboardButton("🔍 换编号/关键词", callback_data=f"L~ASK~{dtype}")])
        txt = f"🔍 <b>{query}</b> ({page}/{math.ceil(res.get('count',0)/10)})"
        if edit and update_obj: await update_obj.callback_query.message.edit_text(txt, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))
        else: await context.bot.send_message(chat_id, txt, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))
    else: await context.bot.send_message(chat_id, f"❌ 无结果: {final_query}")

async def show_lego_detail(chat_id, context, dtype, uid, item_data=None, update_obj=None, page=1, parent_id=None):
    if update_obj and update_obj.callback_query: await update_obj.callback_query.message.delete()
    data = await asyncio.to_thread(rb_get, f"{'sets' if dtype=='set' else 'minifigs' if dtype=='fig' else 'parts'}/{uid}")
    if not data: return
    price_usd = await asyncio.to_thread(get_brickset_price, uid); p_str = ""
    if price_usd: p_str = f"\n💰 ${price_usd} (约¥{int(price_usd*USD_CNY_RATE)})"
    theme_info = ""; header_title = dtype.upper()
    if dtype == 'set':
        t_res = await asyncio.to_thread(rb_get, f"themes/{data.get('theme_id')}")
        theme_info = f"\n🏷️ {get_theme_display(t_res.get('name'))}"
    if dtype == 'fig': header_title = "ID"
    if dtype == 'part': header_title = "PART"
    cap = ""; kb = []
    query = context.user_data.get(f'lego_q_{dtype}', '')
    safe_q = query[:15].replace('~', '')
    if dtype == 'part':
        cat_info = "未知"
        if data.get('part_cat_id'):
            cat_data = await asyncio.to_thread(rb_get, f"part_categories/{data['part_cat_id']}")
            cat_info = cat_data.get('name', '未知')
        colors_res = await asyncio.to_thread(rb_get, f"parts/{uid}/colors", {"page_size": 1}); color_count = colors_res.get('count', 0)
        cap = f"<b>{header_title}: {uid}</b>\n{data.get('name')}\n\n🏷️ 类别: {cat_info}\n🎨 颜色种类: {color_count} 种"
        row1 = [InlineKeyboardButton("🔗 Rebrickable", url=f"https://rebrickable.com/parts/{uid}")]
        row2 = [InlineKeyboardButton("🔍 换编号/关键词", callback_data=f"L~ASK~{dtype}")]
        if query: row2.append(InlineKeyboardButton("🔙 返回列表", callback_data=f"L~P~{dtype}~{page}~{safe_q}"))
        kb = [row1, row2]
    elif dtype == 'fig':
        bl_id = await asyncio.to_thread(get_fig_bl_id, uid)
        bl_line = f"BrickLink: <code>{bl_id}</code>\n" if bl_id else ""
        sets_res = await asyncio.to_thread(rb_get, f"minifigs/{uid}/sets", {"page_size": 100})
        sets_list = []
        for s in sets_res.get('results', []):
            sets_list.append(f"<code>{clean_id(s['set_num'])}</code>")
        sets_str = f"\n📦 套装({sets_res.get('count',0)}): {', '.join(sets_list)}"
        cap = f"<b>{header_title}: <code>{clean_id(uid)}</code></b>\n{bl_line}{data.get('name')}\n\n🧩 {data.get('num_parts')} pcs{sets_str}"
        row1 = [InlineKeyboardButton(f"📦 所属套装 ({sets_res.get('count',0)})", callback_data=f"L~FS~{uid}~{page}"), InlineKeyboardButton("📜 零件清单", url=f"https://rebrickable.com/minifigs/{uid}/#parts")]
        row2 = [InlineKeyboardButton("🔗 Rebrickable", url=f"https://rebrickable.com/minifigs/{uid}"), InlineKeyboardButton("🔗 BrickLink", url=f"https://www.bricklink.com/v2/search.page?q={uid.replace('fig-','')}#T=M")]
        row3 = [InlineKeyboardButton("🔍 换编号/关键词", callback_data=f"L~ASK~{dtype}")]
        if parent_id and not parent_id.startswith('fig-'): row3.append(InlineKeyboardButton("🔙 返回套装", callback_data=f"L~D~set~{parent_id}~{page}"))
        elif query: row3.append(InlineKeyboardButton("🔙 返回列表", callback_data=f"L~P~{dtype}~{page}~{safe_q}"))
        kb = [row1, row2, row3]
    else: 
        cap = f"<b>{header_title}: <code>{clean_id(uid)}</code></b>\n{data.get('name')}\n\n📅 {data.get('year')}{theme_info}{p_str}\n🧩 {data.get('num_parts')} pcs"
        f_res = await asyncio.to_thread(rb_get, f"sets/{uid}/minifigs", {"page_size": 100})
        f_count = f_res.get('count', 0)
        f_list = []
        for f in f_res.get('results', []):
            f_bl = await asyncio.to_thread(get_fig_bl_id, f['set_num'])
            f_list.append(f"<code>{f_bl if f_bl else clean_id(f['set_num'])}</code>")
        f_str = f"\n👤 人仔({f_count}): {', '.join(f_list)}"
        cap += f_str
        row1 = [InlineKeyboardButton(f"👤 人仔 ({f_count})", callback_data=f"L~F~{uid}~{page}"), InlineKeyboardButton("🧩 MOC", url=f"https://rebrickable.com/sets/{uid}/#alt_builds")]
        row2 = [InlineKeyboardButton("📜 零件清单", url=f"https://rebrickable.com/sets/{uid}/#parts")]

        # 说明书按钮：4-5位用 LEGO.com 说明书，6位用 Blue-Ocean
        _cid = clean_id(uid)
        _cid_len = len(_cid)
        if _cid_len in (4, 5):
            row2.append(InlineKeyboardButton("📖 说明书", url=f"https://www.lego.com/en-us/service/building-instructions/{_cid}"))
        elif _cid_len == 6:
            row2.append(InlineKeyboardButton("📖 说明书", url=f"https://www.blue-ocean-ag.com/bi/?tx_kesearch_pi1%5Bsword%5D={_cid}"))

        row3 = [InlineKeyboardButton("🔗 Rebrickable", url=f"https://rebrickable.com/sets/{uid}")]
        if _cid_len == 5 and not _cid.startswith('3'):
            row3.append(InlineKeyboardButton("🔗 LEGO.com", url=f"https://www.lego.com/en-us/search?q={_cid}"))
        row4 = [InlineKeyboardButton("🔍 换编号/关键词", callback_data=f"L~ASK~{dtype}")]
        if parent_id and parent_id.startswith('fig-'): row4.append(InlineKeyboardButton("🔙 返回人仔", callback_data=f"L~D~fig~{parent_id}~{page}"))
        elif parent_id == 'NL': row4.append(InlineKeyboardButton("🔙 返回新品速递", callback_data=f"L~NL~{context.user_data.get('lego_nl_year','2026')}~{context.user_data.get('lego_nl_page','1')}"))
        elif query: row4.append(InlineKeyboardButton("🔙 返回列表", callback_data=f"L~P~{dtype}~{page}~{safe_q}"))
        kb = [row1, row2, row3, row4]
    img = data.get('set_img_url') or data.get('part_img_url')
    if img: await context.bot.send_photo(chat_id, img, caption=cap, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))
    else: await context.bot.send_message(chat_id, cap, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))

async def lego_check_minifigs(update, context, uid):
    res = await asyncio.to_thread(rb_get, f"sets/{uid}/minifigs", {"page_size": 100})
    if not res.get('results'): await update.callback_query.answer("无人仔数据", show_alert=True); return
    if res.get('count') == 1:
        await show_lego_detail(update.effective_chat.id, context, 'fig', res['results'][0]['set_num'], update_obj=update, parent_id=uid)
        return
    kb = []
    for i in res['results'][:10]:
        bl_id = await asyncio.to_thread(get_fig_bl_id, i['set_num'])
        display_id = bl_id if bl_id else clean_id(i['set_num'])
        btn_text = f"[{display_id}] {i['set_name'][:40]}"
        kb.append([InlineKeyboardButton(btn_text, callback_data=f"L~D~fig~{i['set_num']}~1~{uid}")])
    kb.append([InlineKeyboardButton("🔙 返回套装", callback_data=f"L~D~set~{uid}")])
    await update.callback_query.message.delete()
    await context.bot.send_message(update.effective_chat.id, f"👤 <b>{clean_id(uid)} 人仔列表:</b>", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))

async def lego_check_fig_sets(update, context, uid):
    res = await asyncio.to_thread(rb_get, f"minifigs/{uid}/sets", {"page_size": 10})
    if not res.get('results'): await update.callback_query.answer("无数据", show_alert=True); return
    if res.get('count') == 1:
        await show_lego_detail(update.effective_chat.id, context, 'set', res['results'][0]['set_num'], update_obj=update, parent_id=uid)
        return
    kb = []
    for i in res['results']:
        kb.append([InlineKeyboardButton(f"[{clean_id(i['set_num'])}] {i['name'][:30]}", callback_data=f"L~D~set~{i['set_num']}~1~{uid}")])
    kb.append([InlineKeyboardButton("🔙 返回人仔", callback_data=f"L~D~fig~{uid}")])
    await update.callback_query.message.delete()
    await context.bot.send_message(update.effective_chat.id, f"📦 <b>{uid} 所属套装:</b>", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))

async def handle_callback(u, c):
    d = u.callback_query.data; pts = d.split('~')
    try: await u.callback_query.answer()
    except: pass
    if pts[1] == 'D': 
        parent = pts[5] if len(pts) > 5 else None
        if parent == 'NL' and len(pts) > 7:
            c.user_data['lego_nl_year'] = pts[6]
            c.user_data['lego_nl_page'] = pts[7]
        await show_lego_detail(u.effective_chat.id, c, pts[2], pts[3], page=int(pts[4]) if len(pts)>4 else 1, update_obj=u, parent_id=parent)
    elif pts[1] == 'P': 
        q = pts[4] if len(pts)>4 else None
        if q and len(q.strip()) > 0: await do_lego_search(u.effective_chat.id, c, pts[2], q, page=int(pts[3]), edit=True, update_obj=u)
        else: await c.bot.send_message(u.effective_chat.id, "⚠️ 页面已过期，请重新搜索")
    elif pts[1] == 'F': await lego_check_minifigs(u, c, pts[2])
    elif pts[1] == 'FS': await lego_check_fig_sets(u, c, pts[2])
    elif pts[1] == 'ASK': await lego_search_entry(u, c)
    elif pts[1] == 'NAV': await lego_website_nav(u, c)
    elif pts[1] == 'NEW': await lego_new_sets_year_picker(u, c)
    elif pts[1] == 'NL': await lego_new_sets_list(u, c)
    elif pts[1] == 'MENU': await lego_menu_panel(u, c)

async def lego_export_handler(update, context):
    try:
        await update.callback_query.answer("正在生成 CSV...")
        chat_id = update.effective_chat.id
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT * FROM minifig_map")
        rows = c.fetchall()
        names = [description[0] for description in c.description]
        file_path = f"/tmp/minifigs_db_{int(time.time())}.csv"
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(names)
            writer.writerows(rows)
        conn.close()
        await context.bot.send_document(
            chat_id=chat_id, document=open(file_path, 'rb'),
            filename=os.path.basename(file_path),
            caption=f"📊 <b>人仔数据库导出</b>\n📅 {time.strftime('%Y-%m-%d %H:%M')}\n🔢 总记录: {len(rows)}",
            parse_mode=ParseMode.HTML
        )
        os.remove(file_path)
    except Exception as e: await context.bot.send_message(chat_id, f"❌ 导出失败: {e}")

def get_conv_handler(extra_fallbacks=None):
    _MENU_TEXT = filters.Regex(r'^(🔍 搜图书|🧱 乐高查询|⚙️ 系统状态)')
    fallbacks = list(extra_fallbacks or [])
    fallbacks.append(MessageHandler(filters.Regex(r'^/cancel$'), silent_cancel))
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(lego_search_entry, pattern=r'^L~ASK~'), CommandHandler("mini", lego_mini_shortcut)],
        states={LEGO_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~_MENU_TEXT, lego_input_handler)]},
        fallbacks=fallbacks
    )

def get_handlers():
    return [
        CommandHandler("lego", lego_menu_panel), 
        CallbackQueryHandler(lego_trigger_update_handler, pattern="^lego_do_"),
        CallbackQueryHandler(lego_update_ask_handler, pattern="^lego_update_ask$"),
        CallbackQueryHandler(lego_export_handler, pattern="^lego_export$"),
        CallbackQueryHandler(handle_callback, pattern=r'^L~')
    ]
