## [v1.0.108] - 2026-04-21

### 回退
- 回退 xiaohongshu 处理代码至 v1.0.100 风格（删除无效的 extractor_args 和 http_headers）

## [v1.0.106] - 2026-04-21

### 修复
- LEGO 搜索：SESSION 加代理支持，读取容器 HTTP_PROXY/HTTPS_PROXY 环境变量
- 小红书：短链接 xhslink.com 先 head 请求解析完整 URL 再送 yt-dlp
- 命令列表：修复 delete_my_commands 的 language code，添加更多容错处理


## [v1.0.104] - 2026-04-20

### 更新
- 同步到 N100


## [v1.0.103] - 2026-04-20

### 修复
- 修复重启 404：容器名从 HOSTNAME 改为硬编码 "All-in-One_tgbot"
- CHANGELOG 同步干净版本到 N100（清除含 Telegram ID 的旧条目）

## [v1.0.102] - 2026-04-19

### 修复
- 修复配置默认值

## [v1.0.101] - 2026-04-19

### 修复
- 命令菜单去掉 /export，保留 /start /s /lego /mini /reboot

## [v1.0.100] - 2026-04-19

### 修复
- media.py 新增 clean_url() 清理 URL 末尾的 emoji/标点/CJK 字符，修复头条链接下载失败问题

## [v1.0.099] - 2026-04-19

### 更新
- 同步到 N100
