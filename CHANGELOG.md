## v1.0.119

v1.0.119 (2026-04-30)
Fixed:
- 修复 N100 容器互通：FLARESOLVERR_URL 从容器名改为 127.0.0.1:8191
- 修复 MeTube 端口：METUBE_URL 从 8081 改为 8083
- deploy.sh：config.py 不再推送到 git维护/，仅到 N100 主目录
- restore.sh：config.py 改为从 N100 主目录同步回 Mac 本地

## v1.0.118

v1.0.118 (2026-04-29)
Fixed:
- 修复 CHANGELOG 换行丢失问题
- 修复 FlareSolverr 连接失败（Docker 容器内 127.0.0.1 不可达，改用容器名）
Changed:
- CHANGELOG 输出过滤冗余版本号行
- config.py.template 补充 FlareSolverr 配置段

## v1.0.117

v1.0.117 (2026-04-29)
Fixed:
- 修复 CHANGELOG 格式，移除 HTML 标签和 --- 分隔符
- 修复乐高人仔导入统计数字，新增数字不再混淆
Changed:
- 更新版本号 v1.0.117，更新人 Garry

## v1.0.116

v1.0.116 (2026-04-29)
Fixed:
- 修复 CHANGELOG 格式，Telegram HTML 兼容
- 移除 lego.py 导出按钮
Changed:
- 更新版本号 v1.0.116，更新人 Garry

## v1.0.115

v1.0.115 (2026-04-22)
Fixed:
- 小红书视频发送超时：send_video timeout 120s→180s

## v1.0.114

v1.0.114 (2026-04-21)
Fixed:
- 小红书短链接502：改用 NO_PROXY='*' + GET请求
- resolve_fig_id：修复 fig-012384 格式丢失连字符
- resolve_fig_id：LEGO ID（sh/sw前缀）DB不存在时走 Rebrickable 搜索兜底
Changed:
- 以图搜图：优先 imgbb（需配置 IMGBB_API_KEY），次选 Telegram 文件 URL
Reverted:
- 小红书下载回退至 v1.0.100 风格

## v1.0.112

v1.0.112 (2026-04-21)
Fixed:
- LEGO搜索无结果时添加"换编号/关键词"按钮
- 小红书短链接处理：支持 xhslink.com 解析
- resolve_fig_id：支持 sh0016a 等变体后缀查询
- 以图搜图：改用 litterbox 临时图床

## v1.0.106

v1.0.106 (2026-04-21)
Fixed:
- LEGO搜索：SESSION 加代理支持
- 小红书：短链接 xhslink.com 先 HEAD 请求解析完整 URL 再送 yt-dlp

## v1.0.105

v1.0.105 (2026-04-21)
Fixed:
- LEGO搜索：移除 handle_callback 中对 L~ASK~ 的重复处理

## v1.0.100

v1.0.100 (2026-04-20)
Fixed:
- clean_url 媒体下载修复

## v1.0.099

v1.0.099 (2026-04-19)
Changed:
- 初始稳定版发布

## v1.0.093

v1.0.093 (2026-04-06)
Added:
- 项目初始化
- LEGO 人仔搜索功能
- 媒体下载功能（TMDB/NeoDB）
- 小红书内容下载
