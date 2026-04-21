## [v1.0.114] - 2026-04-21

### 修复
- LEGO 搜索无结果时添加"换关键词"按钮
- 小红书短链接 xhslink.com 解析：改用 GET + NO_PROXY='*' 直连绕过代理/透明劫持，完整解析出直链 URL
- 小红书短链接 xhslink.com 返回 502 根因：服务器直连 307 OK，走 ShellCrash 代理 502（节点 IP 被封），用 NO_PROXY='*' + GET 请求可解决

## [v1.0.109] - 2026-04-21

### 修复
- `resolve_fig_id`: 修复 fig-012384 格式丢失连字符导致 ID 显示错误的问题（同时影响 BrickLink ID 显示）
- `resolve_fig_id`: 修复 LEGO ID（如 sh/sw 前缀）即使 DB 不存在也不崩溃，改走 Rebrickable 搜索兜底
- 以图搜图: image.py 降级支持，优先 imgbb（需配置 IMGBB_API_KEY），次选 Telegram 文件 URL

### 回退
- 小红书下载：回退至 v1.0.100 风格（无特殊处理）

## [v1.0.108] - 2026-04-21

### 回退
- 回退 xiaohongshu 处理代码至 v1.0.100 风格（删除无效的 extractor_args 和 http_headers）

## [v1.0.107] - 2026-04-21

### 回退
- 回退 xiaohongshu 处理代码至 v1.0.100 风格（删除无效的 extractor_args 和 http_headers）

## [v1.0.106] - 2026-04-21

### 修复
- LEGO 搜索：SESSION 加代理支持，读取容器 HTTP_PROXY/HTTPS_PROXY 环境变量
- 小红书：短链接 xhslink.com 先 head 请求解析完整 URL 再送 yt-dlp

## [v1.0.105] - 2026-04-21

### 修复
- LEGO 搜索：移除 handle_callback 中对 L~ASK~ 的重复处理，避免与 ConversationHandler 冲突
