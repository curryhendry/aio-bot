# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v1.0.115] - 2026-04-22

### Fixed
- 小红书视频发送超时：`send_video` timeout 120s→180s

---

## [v1.0.114] - 2026-04-21

### Fixed
- 小红书短链接502：改用 `NO_PROXY='*'` + GET请求（HEAD不被支持）
- `resolve_fig_id`：修复 fig-012384 格式丢失连字符导致ID错误
- `resolve_fig_id`：修复 LEGO ID（sh/sw前缀）DB不存在时不崩溃，改走 Rebrickable 搜索兜底

### Changed
- 以图搜图：优先 imgbb（需配置IMGBB_API_KEY），次选 Telegram 文件 URL

### Reverted
- 小红书下载回退至 v1.0.100 风格（无特殊处理）

---

## [v1.0.113] - 2026-04-21

*版本跳过，未发布*

---

## [v1.0.112] - 2026-04-21

### Fixed
- LEGO搜索无结果时添加"换编号/关键词"按钮
- 小红书短链接处理：支持 xhslink.com 解析
- `resolve_fig_id`：支持 sh0016a 等变体后缀查询
- 以图搜图：改用 litterbox 临时图床（无需认证）

---

## [v1.0.111] - 2026-04-21

*版本跳过，未单独发布*

---

## [v1.0.110] - 2026-04-21

*版本跳过，未发布*

---

## [v1.0.109] - 2026-04-21

*版本跳过，未发布*

---

## [v1.0.108] - 2026-04-21

### Reverted
- 回退 xiaohongshu 处理代码至 v1.0.100 风格（删除无效的 extractor_args 和 http_headers）

---

## [v1.0.107] - 2026-04-21

### Reverted
- 回退 xiaohongshu 处理代码至 v1.0.100 风格

---

## [v1.0.106] - 2026-04-21

### Fixed
- LEGO搜索：SESSION 加代理支持，读取容器 HTTP_PROXY/HTTPS_PROXY 环境变量
- 小红书：短链接 xhslink.com 先 HEAD 请求解析完整 URL 再送 yt-dlp

---

## [v1.0.105] - 2026-04-21

### Fixed
- LEGO搜索：移除 handle_callback 中对 L~ASK~ 的重复处理，避免与 ConversationHandler 冲突

---

## [v1.0.104] - 2026-04-21

### Changed
- 版本发布

---

## [v1.0.103] - 2026-04-21

### Changed
- 版本发布

---

## [v1.0.102] - 2026-04-20

### Fixed
- CHANGELOG 修复
- 恢复 lego_db.sqlite 到版本控制
- 设置 ALLOWED_IDS 默认值

---

## [v1.0.101] - 2026-04-20

### Removed
- 移除 /export 命令（从命令菜单中删除）

---

## [v1.0.100] - 2026-04-20

### Fixed
- `clean_url` 媒体下载修复

---

## [v1.0.099] - 2026-04-19

### Changed
- 初始稳定版发布

---

## [v1.0.098] - 2026-04-19

*版本记录缺失*

---

## [v1.0.097] - 2026-04-19

*版本记录缺失*

---

## [v1.0.096] - 2026-04-18

*版本记录缺失*

---

## [v1.0.095] - 2026-04-18

*版本记录缺失*

---

## [v1.0.094] - 2026-04-18

*版本记录缺失*

---

## [v1.0.093] - 2026-04-06

### Added
- 项目初始化
- Git 仓库初始化
- 基础架构：Dockerfile、deploy.sh、CHANGELOG
- LEGO 人仔搜索功能
- 媒体下载功能（TMDB/NeoDB）
- 小红书内容下载

---

## [v1.0.001] - 2026-04-01

### Added
- 初始版本发布

---
