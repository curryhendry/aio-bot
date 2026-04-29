**CHANGELOG**

**v1.0.115 (2026-04-22)**
**Fixed:**
- 小红书视频发送超时：`send_video` timeout 120s→180s

---

**v1.0.114 (2026-04-21)**
**Fixed:**
- 小红书短链接502：改用 `NO_PROXY='*'` + GET请求
- `resolve_fig_id`：修复 fig-012384 格式丢失连字符
- `resolve_fig_id`：LEGO ID（sh/sw前缀）DB不存在时走 Rebrickable 搜索兜底

**Changed:**
- 以图搜图：优先 imgbb（需配置 IMGBB_API_KEY），次选 Telegram 文件 URL

**Reverted:**
- 小红书下载回退至 v1.0.100 风格

---

**v1.0.112 (2026-04-21)**
**Fixed:**
- LEGO搜索无结果时添加"换编号/关键词"按钮
- 小红书短链接处理：支持 xhslink.com 解析
- `resolve_fig_id`：支持 sh0016a 等变体后缀查询
- 以图搜图：改用 litterbox 临时图床

---

**v1.0.106 (2026-04-21)**
**Fixed:**
- LEGO搜索：SESSION 加代理支持
- 小红书：短链接 xhslink.com 先 HEAD 请求解析完整 URL 再送 yt-dlp

---

**v1.0.105 (2026-04-21)**
**Fixed:**
- LEGO搜索：移除 handle_callback 中对 L~ASK~ 的重复处理

---

**v1.0.100 (2026-04-20)**
**Fixed:**
- `clean_url` 媒体下载修复

---

**v1.0.099 (2026-04-19)**
**Changed:**
- 初始稳定版发布

---

**v1.0.093 (2026-04-06)**
**Added:**
- 项目初始化
- LEGO 人仔搜索功能
- 媒体下载功能（TMDB/NeoDB）
- 小红书内容下载
