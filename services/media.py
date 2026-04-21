import os, requests, asyncio, docker, yt_dlp, html, time, re, urllib.parse
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ConversationHandler
from config import TMDB_TOKEN, NEODB_TOKEN, METUBE_URL, METUBE_CONTAINER_NAME, SEARCH_WAIT, COOKIES_FILE, FAKE_HEADERS, logger

NEODB_CACHE = {}
TMDB_CACHE = {}

def check_metube_status():
    try:
        client = docker.from_env()
        for c in client.containers.list(all=True):
            if METUBE_CONTAINER_NAME in c.name or "metube" in c.name.lower():
                return (True, f"运行中 ({c.name})") if c.status == 'running' else (False, f"已停止 ({c.name})")
        return (False, "未找到容器")
    except Exception as e: return (False, f"Docker失败: {str(e)}")

def start_metube_container():
    try:
        client = docker.from_env()
        for c in client.containers.list(all=True):
            if METUBE_CONTAINER_NAME in c.name or "metube" in c.name.lower():
                if c.status != 'running': c.start(); return True, "已启动，预热中"
                return True, "运行中"
        return False, "未找到容器"
    except Exception as e: return False, f"容器控制失败: {e}"

def push_to_metube_api(url, was_stopped=False):
    api_url = METUBE_URL or "http://MeTube:8081"
    if not api_url.endswith("/add"): api_url = f"{api_url.rstrip('/')}/add"
    retries = 5 if was_stopped else 1
    for i in range(retries):
        try:
            resp = requests.post(api_url, json={"url": url, "quality": "best"}, timeout=30)
            if resp.status_code == 200: return True, "已添加"
            return False, f"HTTP {resp.status_code}"
        except Exception as e:
            if i == 0: logger.error(f"MeTube推送异常: {e}")
        if was_stopped: time.sleep(3)
    return False, "推送失败"

def run_ytdlp_internal(url):
    cookie_path = COOKIES_FILE if os.path.exists(COOKIES_FILE) else None
    ydl_opts = {'format': 'best[ext=mp4]/best', 'outtmpl': '/downloads/%(title)s.%(ext)s', 'quiet': True, 'cookiefile': cookie_path, 'ignoreerrors': True, 'no_warnings': True, 'nocheckcertificate': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info: return False, "解析失败", None
            return True, ydl.prepare_filename(info), info.get('title', 'video')
    except Exception as e: return False, str(e), None

def search_tmdb_list(query):
    if not TMDB_TOKEN: return []
    try:
        resp = requests.get("https://api.themoviedb.org/3/search/multi", params={"api_key": TMDB_TOKEN, "query": query, "language": "zh-CN"}, timeout=8)
        res = []
        for item in resp.json().get('results', [])[:10]:
            if item.get('media_type') in ['movie', 'tv']:
                t = item.get('title') or item.get('name')
                y = (item.get('release_date') or item.get('first_air_date') or 'N/A')[:4]
                TMDB_CACHE[str(item['id'])] = item
                res.append({"label": f"{'🎬' if item['media_type']=='movie' else '📺'} 🌟 {t} ({y})", "id": f"t:{item['id']}", "type": item['media_type']})
        return res
    except: return []

def search_neodb_list(query):
    if not NEODB_TOKEN: return []
    try:
        resp = requests.get("https://neodb.social/api/catalog/search", headers={"Authorization": f"Bearer {NEODB_TOKEN}"}, params={"query": query}, timeout=8)
        res = []
        for item in resp.json().get('data', [])[:60]:
            if item.get('category') in ['book', 'movie', 'tv']:
                cat = item.get('category')
                y = str(item.get('year', item.get('pub_year', '')))
                NEODB_CACHE[f"n:{item['url']}"] = item
                res.append({"label": f"{'📖' if cat=='book' else '🎬' if cat=='movie' else '📺'} 🐙 {item['display_title']} ({y})" if y else f"{'📖' if cat=='book' else '🎬' if cat=='movie' else '📺'} 🐙 {item['display_title']}", "id": f"n:{item['url']}", "type": cat})
        return res
    except: return []

async def do_search(chat_id, q, context):
    context.user_data['last_search_q'] = q
    tmdb_res = await asyncio.to_thread(search_tmdb_list, q)
    neodb_res = await asyncio.to_thread(search_neodb_list, q)
    if not tmdb_res and not neodb_res and q[0].islower(): return await do_search(chat_id, q.title(), context)
    
    books = [x for x in neodb_res if x['type'] == 'book'][:12]
    movies = ([x for x in tmdb_res if x['type'] == 'movie'] + [x for x in neodb_res if x['type'] == 'movie'])[:10]
    tvs = ([x for x in tmdb_res if x['type'] == 'tv'] + [x for x in neodb_res if x['type'] == 'tv'])[:10]
    
    def build_rows(items):
        rows, row = [], []
        for item in items:
            row.append(InlineKeyboardButton(item['label'][:32] + ".." if len(item['label'])>34 else item['label'], callback_data=item['id']))
            if len(row) == 2: rows.append(row); row = []
        if row: rows.append(row)
        return rows

    kb = []
    if books: kb.extend(build_rows(books))
    if movies: kb.extend(build_rows(movies))
    if tvs: kb.extend(build_rows(tvs))
    kb.append([InlineKeyboardButton("🔄 换个关键词搜索", callback_data="media_retry")])
    await context.bot.send_message(chat_id, f"🔍 '{q}' 结果:" if (books or movies or tvs) else f"❌ '{q}' 无结果", reply_markup=InlineKeyboardMarkup(kb))

async def search_entry(update, context):
    if update.callback_query:
        await update.callback_query.answer()
        await context.bot.send_message(update.effective_chat.id, "🔍 **请重新输入关键词**\n(搜图书/电影/电视)", parse_mode=ParseMode.MARKDOWN)
        return SEARCH_WAIT
    if getattr(context, 'args', None): 
        await do_search(update.effective_chat.id, " ".join(context.args), context)
        return ConversationHandler.END
    await update.message.reply_text("🔍 **请输入关键词**\n(搜图书/电影/电视)", parse_mode=ParseMode.MARKDOWN)
    return SEARCH_WAIT

async def search_input_s(u, c): 
    await do_search(u.effective_chat.id, u.message.text, c); return ConversationHandler.END

async def handle_callback(u, c):
    q = u.callback_query; d = q.data; chat_id = u.effective_chat.id
    if d == "restore_search":
        try: await q.message.delete()
        except: pass
        if c.user_data.get('last_search_q'): await do_search(chat_id, c.user_data['last_search_q'], c)
        else: await c.bot.send_message(chat_id, "❌ 搜索记录已过期")
        return

    if d.startswith("t:"): 
        try: await q.message.delete()
        except: pass
        tid = d.split(":")[1]
        item = TMDB_CACHE.get(tid)
        m_type = item.get('media_type') if item else None
        
        detail = None
        if TMDB_TOKEN:
             types_to_try = [m_type] if m_type else ['movie', 'tv']
             for t in types_to_try:
                 try: 
                     res = requests.get(f"https://api.themoviedb.org/3/{t}/{tid}", params={"api_key": TMDB_TOKEN, "append_to_response": "credits", "language": "zh-CN"}, timeout=5)
                     if res.status_code == 200: detail = res.json(); m_type = t; break
                 except: pass
        
        if not detail and item: detail = item
        if not detail: await c.bot.send_message(chat_id, "❌ 数据获取失败"); return
        
        m_type = m_type or 'movie'
        title = detail.get('title') or detail.get('name') or '未知'
        year = (detail.get('release_date') or detail.get('first_air_date') or '未知')[:4]
        rating_val = detail.get('vote_average', 0)
        
        area_str = "/".join([cc.get('name') for cc in detail.get('production_countries', [])])
        genre_str = "/".join([g.get('name') for g in detail.get('genres', [])])
        
        info_lines = [f"{'🎬' if m_type=='movie' else '📺'} <b>{title}</b> ({year})", f"⭐️ 评分: {round(rating_val, 1)}/10" if rating_val else "⭐️ 评分: 暂无"]
        if genre_str: info_lines.append(f"🏷️ 类型: {genre_str}")
        if area_str: info_lines.append(f"🌍 地区: {area_str}")
        
        if m_type == 'tv':
            s_num, e_num = detail.get('number_of_seasons'), detail.get('number_of_episodes')
            if s_num and e_num: info_lines.append(f"📺 共 {s_num} 季 | {e_num} 集")
            elif s_num: info_lines.append(f"📺 共 {s_num} 季")
            elif e_num: info_lines.append(f"📺 集数: {e_num} 集")
        elif m_type == 'movie':
            r_time = detail.get('runtime')
            if r_time: info_lines.append(f"⏳ 时长: {r_time} 分钟")
        
        credits = detail.get('credits', {})
        if credits:
            director = [cr['name'] for cr in credits.get('crew', []) if cr.get('job') == 'Director']
            cast = [cr['name'] for cr in credits.get('cast', [])[:4]]
            if director: info_lines.append(f"🎬 导演: {', '.join(director)}")
            if cast: info_lines.append(f"🎭 主演: {', '.join(cast)}")
            
        overview = detail.get('overview', '无简介')
        info_lines.append(f"\n📝 {overview[:200] + '...' if len(overview)>200 else overview}")
        
        kb = [[InlineKeyboardButton("🌟 TMDB", url=f"https://www.themoviedb.org/{m_type}/{tid}")], [InlineKeyboardButton("🔙 返回列表", callback_data="restore_search")]]
        img = f"https://image.tmdb.org/t/p/w500{detail.get('poster_path')}" if detail.get('poster_path') else None
        
        if img: await c.bot.send_photo(chat_id, img, caption="\n".join(info_lines), parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))
        else: await c.bot.send_message(chat_id, "\n".join(info_lines), parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))
        return

    if d.startswith("n:"):
        try: await q.message.delete()
        except: pass
        url_path = d[2:]
        item = NEODB_CACHE.get(d)
        
        detail = item
        if NEODB_TOKEN:
            try:
                res = requests.get(f"https://neodb.social/api/catalog/fetch?url=https://neodb.social{url_path}", headers={"Authorization": f"Bearer {NEODB_TOKEN}"}, timeout=5)
                if res.status_code == 200: detail = res.json()
            except: pass
            
        if not detail: await c.bot.send_message(chat_id, "❌ 数据获取失败"); return
        
        cat = detail.get('category') or (item.get('category') if item else ('tv' if '/tv/' in url_path else 'book' if '/book/' in url_path else 'movie'))
        type_emoji = '📖' if cat == 'book' else ('🎬' if cat == 'movie' else '📺')
        
        title = detail.get('display_title', '未知')
        year = str(detail.get('year', detail.get('pub_year', '')))
        rating_val = detail.get('rating')
        
        def safe_join(f):
            v = detail.get(f); return ", ".join(map(str, v)) if isinstance(v, list) else str(v) if v else ""
            
        area = safe_join('area') or safe_join('country')
        genre = safe_join('genre')
        
        info_lines = [f"{type_emoji} <b>{title}</b> ({year})" if year else f"{type_emoji} <b>{title}</b>", f"⭐️ 评分: {rating_val}/10" if rating_val else "⭐️ 评分: 暂无"]
        if genre: info_lines.append(f"🏷️ 类型: {genre}")
        if area: info_lines.append(f"🌍 地区: {area}")
        
        if cat == 'tv':
            s_num = detail.get('season_count') or detail.get('seasons')
            e_num = detail.get('episode_count') or detail.get('episodes')
            if s_num and e_num: info_lines.append(f"📺 共 {s_num} 季 | {e_num} 集")
            elif s_num: info_lines.append(f"📺 共 {s_num} 季")
            elif e_num: info_lines.append(f"📺 集数: {e_num} 集")
        elif cat == 'movie':
            r_time = detail.get('duration') or detail.get('runtime')
            if r_time: info_lines.append(f"⏳ 时长: {r_time}")
        elif cat == 'book':
            p_num = detail.get('pages') or detail.get('page_count')
            if p_num: info_lines.append(f"📄 页数: {p_num} 页")
        
        author, translator, director, actor = safe_join('author'), safe_join('translator'), safe_join('director'), safe_join('actor')
        if author: info_lines.append(f"✍️ 作者: {author}")
        if translator: info_lines.append(f"🗣️ 译者: {translator}")
        if director: info_lines.append(f"🎬 导演: {director}")
        if actor: info_lines.append(f"🎭 主演: {actor[:50] + '...' if len(actor)>50 else actor}")
            
        brief = detail.get('brief', '无简介')
        info_lines.append(f"\n📝 {brief[:200] + '...' if len(brief)>200 else brief}")
        
        douban_url = next((ext.get('url') for ext in detail.get('external_resources', []) if 'douban.com' in ext.get('url', '')), f"https://m.douban.com/search/?query={urllib.parse.quote(title)}")
        
        kb = [[InlineKeyboardButton("🐙 NeoDB", url=f"https://neodb.social{url_path}"), InlineKeyboardButton("🥒 豆瓣", url=douban_url)], [InlineKeyboardButton("🔙 返回列表", callback_data="restore_search")]]
        img = detail.get('cover_image_url') or (item.get('cover_image_url') if item else None)
        
        if img: await c.bot.send_photo(chat_id, img, caption="\n".join(info_lines), parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))
        else: await c.bot.send_message(chat_id, "\n".join(info_lines), parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))
        return

def clean_url(raw):
    CHARS = "?!.,;:'\"\u201c\u201d\uff0c\u3002\uff1b\uff1a\uff01\uff1f\u3001\uff09\u300b\u300d\u300f\u3011>"
    while raw and raw[-1] in CHARS:
        raw = raw[:-1]
    while raw and ord(raw[-1]) > 0x2000:
        raw = raw[:-1]
    return raw

async def handle_file(update, context):
    msg = update.message; text = msg.text or msg.caption or ""; chat_id = update.effective_chat.id
    urls = re.findall(r'https?://[^\s]+', text); url = clean_url(urls[0]) if urls else text.strip() if 'magnet:?' in text else None
    if not url: return
    # 小红书短链接先解析完整 URL
    if 'xhslink.com' in url:
        try:
            real_url = requests.head(url, allow_redirects=True, timeout=10).url
            if real_url and real_url != url: url = real_url
        except: pass

    if any(x in url for x in ['youtube.com', 'youtu.be', 'bilibili.com', 'b23.tv']):
        status_msg = await msg.reply_text("⚙️ 检查 MeTube 状态...")
        c_suc, c_msg = start_metube_container()
        if not c_suc:
            await status_msg.edit_text("⚙️ MeTube 未运行，尝试直接下载...")
        else:
            if "已启动" in c_msg:
                await status_msg.edit_text(f"🚀 {c_msg}，等待服务就绪...")
                await asyncio.sleep(30)
            await status_msg.edit_text(f"🚀 {c_msg}，推送中...")
            p_suc, p_msg = push_to_metube_api(url, was_stopped="已启动" in c_msg)
            if p_suc:
                await status_msg.edit_text(f"✅ {p_msg}")
                return
            await status_msg.edit_text("⚙️ MeTube 推送失败，尝试直接下载...")

    elif any(x in url for x in ['douyin.com', 'v.douyin.com']):
        status_msg = await msg.reply_text("⚙️ 检查 MeTube 状态...")
        c_suc, c_msg = start_metube_container()
        if not c_suc:
            await status_msg.edit_text("⚙️ MeTube 未运行，尝试直接下载...")
        else:
            if "已启动" in c_msg:
                await status_msg.edit_text(f"🚀 {c_msg}，等待服务就绪...")
                await asyncio.sleep(30)
            await status_msg.edit_text(f"🚀 {c_msg}，推送中...")
            p_suc, p_msg = push_to_metube_api(url, was_stopped="已启动" in c_msg)
            if p_suc:
                await status_msg.edit_text(f"✅ {p_msg}")
                return
            await status_msg.edit_text("⚙️ MeTube 推送失败，尝试直接下载...")

    status_msg = await msg.reply_text("📥 正在下载...")
    suc, res, title = await asyncio.to_thread(run_ytdlp_internal, url)
    if suc:
        try:
            await status_msg.edit_text("✅ 发送中...")
            await context.bot.send_video(chat_id=chat_id, video=open(res, 'rb'), caption=f"✅ {title}")
            await status_msg.delete(); os.remove(res)
        except Exception as e:
            await status_msg.edit_text(f"❌ 发送失败: {str(e)}")
            if os.path.exists(res): os.remove(res)
    else: await status_msg.edit_text(f"❌ 下载失败: {res}")
