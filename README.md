# All-in-One Telegram Bot

> Telegram 多功能机器人，整合图书影视搜索、媒体下载、乐高查询、以图搜图。

[![GitHub release](https://img.shields.io/github/v/release/curryhendry/aio-bot?style=flat-square)](https://github.com/curryhendry/aio-bot/releases/latest)
[![MIT License](https://img.shields.io/github/license/curryhendry/aio-bot?style=flat-square)](LICENSE)

---

## 项目背景
- 0 代码基础实现 全🤖AI指导完成
- 推荐部署在VPS 配合Docker容器实现

## 功能

| 模块 | 说明 |
|------|------|
| 🔍 图书/影视搜索 | 对接 NeoDB + TMDB，支持搜索图书、电影、电视剧 |
| 📥 媒体下载 | 支持 YouTube / B站 / 抖音，优先推送 MeTube 容器下载，支持 fallback 直接下载 |
| 🧱 乐高查询 | 套装、人仔、MOC、零件查询，对接 Rebrickable API；人仔自建数据库（SQLite） |
| 🖼️ 以图搜图 | 上传图片，生成 Google Lens 链接（需 Telegram 内置浏览器打开） |
| 🔧 FlareSolverr | 绕过 Cloudflare 验证，爬取 rebrickable.com 人仔数据；按需自动启动/关闭 |
| ⚙️ 系统状态 | CPU / 磁盘 / MeTube / FlareSolverr 状态，重启机器人，关闭 MeTube / FlareSolverr |

### 一级菜单

```
🔍 搜图书/电影/电视  ｜  🧱 乐高查询
⚙️ 系统状态
```

**图书/电影/电视 搜索：**
<br><img src="https://github.com/user-attachments/assets/b7edd093-c512-4929-8ade-9ea875595cd5" width="400" />  <img src="https://github.com/user-attachments/assets/1a5bcbb3-dc33-483f-aa37-8ad8e040545d" width="400" />

**乐高产品查询：**
<br><img src="https://github.com/user-attachments/assets/bdb67823-19de-4778-81a5-08fe19391dfa" width="400" />  <img src="https://github.com/user-attachments/assets/9750ff7f-6c29-46e0-9adc-9672f096d1b7" width="400" />

**视频下载：**
<br><img src="https://github.com/user-attachments/assets/88e3ddda-20f9-437c-aab3-dd78acfdef97" width="400" />


## 快速部署

### 前置要求

- VPS（本文以 Ubuntu 为例）
- Docker 已安装

### 步骤 1：创建 Telegram Bot

1. 在 Telegram 搜索 **@BotFather**
2. 发送 `/newbot`
3. 按提示输入机器人名称（如 `MyAIOBot`）
4. 按提示输入机器人用户名（如 `my_aio_bot`，必须以 `bot` 结尾）
5. BotFather 会返回 **Bot Token**，格式如 `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

> 💡 保存好 Token，后面配置要用

### 步骤 2：获取你的 Chat ID

机器人需要知道谁是主人，通过 Chat ID 白名单控制。

1. 在 Telegram 搜索 **@get_id_bot**
2. 发送任意消息
3. 它会回复你的 Chat ID（一串数字）

> 💡 多人使用时，把每个人的 Chat ID 都加入白名单

### 步骤 3：获取 API Key

| 服务 | 获取地址 | 说明 |
|------|----------|------|
| NeoDB Token | https://neodb.cc/oauth2/applications/ | 创建应用获取，用于图书/影视搜索 |
| TMDB Token | https://www.themoviedb.org/settings/api | 注册后申请 API Key，用于影视搜索 |
| Rebrickable Key | https://rebrickable.com/api/register/ | 注册后申请，用于乐高数据 |

> ⚠️ MeTube 下载 YouTube/B站需要 Cookie，需自行解决（Chrome 插件获取）

### 步骤 4：克隆仓库并配置

```bash
# 克隆仓库
git clone https://github.com/curryhendry/aio-bot.git /home/ubuntu/aio_bot
cd /home/ubuntu/aio_bot

# 复制配置模板
cp config.py.template config.py

# 编辑配置（填入真实 Token）
nano config.py
```

`config.py` 内容示例：

```python
BOT_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"  # 你的 Bot Token
ALLOWED_IDS = [123456789]  # 你的 Chat ID，多人用逗号分隔

TMDB_TOKEN = "你的TMDB Token"
NEODB_TOKEN = "你的NeoDB Token"
RB_KEY = "你的Rebrickable API Key"

METUBE_URL = "http://MeTube:8081"
METUBE_CONTAINER_NAME = "MeTube"

FLARESOLVERR_URL = "http://127.0.0.1:8191"
FLARESOLVERR_CONTAINER_NAME = "FlareSolverr"
```

> 🔒 **安全提示**：`config.py` 含真实 Token，不要提交到 GitHub！

### 步骤 5：部署 Docker 容器

```bash
cd /home/ubuntu/aio_bot

# 构建机器人镜像
docker build -t aio_bot:latest .

# 创建 Docker 网络（机器人与 MeTube 通信用）
docker network create aio-net 2>/dev/null || true

# 部署 MeTube（视频下载器）
docker run -d \
  --name MeTube \
  --network aio-net \
  --restart=unless-stopped \
  -p 8083:8081 \
  -v /home/ubuntu/metube_downloads:/downloads \
  ghcr.io/alexta69/metube:latest

# 部署 FlareSolverr（Cloudflare 绕过服务，用于乐高数据爬取）
docker run -d \
  --name FlareSolverr \
  --network aio-net \
  --restart=unless-stopped \
  -p 8191:8191 \
  -e TZ=Asia/Shanghai \
  ghcr.io/flaresolverr/flaresolverr:latest

# 部署机器人（N100）
docker run -d \
  --name All-in-One_tgbot \
  --hostname All-in-One_tgbot \
  --network host \
  --restart unless-stopped \
  -v /mnt/Download/Program/All-in-One_bot:/aio_bot \
  -v /mnt/Download/Program:/cookies \
  -v /mnt/Download/youtube-dl:/downloads \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e TZ=Asia/Shanghai \
  aio_bot:latest \
  python main.py
```

> 📌 MeTube 与机器人必须在同一 `aio-net` 网络下才能互通
> 📌 FlareSolverr 平时关闭，爬虫触发时由 Bot 自动启动，节省资源

### 步骤 6：开始使用

在 Telegram 搜索你的机器人用户名，发送 `/start` 即可看到菜单：

```
🔍 搜图书/电影/电视  ｜  🧱 乐高查询
⚙️ 系统状态
```

**常用操作：**
- 发送链接（YouTube/B站/抖音）→ 自动下载
- 发送图片 → 生成 Google Lens 搜索链接
- 点击菜单按钮 → 进入对应功能

### 更新版本

```bash
cd /home/ubuntu/aio_bot
git pull
docker restart All-in-One_tgbot
```

---

## 项目结构

```
aio-bot/
├── Dockerfile              # 容器镜像构建
├── main.py                 # 入口：系统模块（Start / Status / Help）
├── config.py.template      # 配置模板（不含真实token）
├── database.py             # SQLite 数据库连接层（人仔映射）
├── lego_db.sqlite          # 乐高人仔本地数据库（7.5MB）
├── services/
│   ├── __init__.py
│   ├── lego.py             # 乐高模块（独立 ConversationHandler）
│   ├── media.py            # 媒体模块（下载逻辑）
│   └── image.py            # 图片处理（Google Lens）
├── CHANGELOG.md            # 版本更新记录
├── README.md
├── .gitignore
└── deploy.sh               # 发布脚本（自动版本号 + git tag）
```

> **注意**：`config.py`（含真实 Token）仅存在于 VPS，不提交到 GitHub。`history/` 目录（含历史备份和旧 Token）不提交。

---

## 乐高模块说明

### 说明书 URL 规则

| 类型 | 来源 | URL |
|------|------|-----|
| 4~5位套装编号 | LEGO.com | `lego.com/en-us/service/building-instructions/{编号}` |
| 6位套装编号 | Blue-Ocean | `blue-ocean-ag.com/bi/?tx_kesearch_pi1[sword]={编号}` |

### 人仔数据库

- 数据来源：Rebrickable API
- 本地存储：`lego_db.sqlite`
- 手动更新：在 Telegram 内发送 `/update` 命令

---

## 更新日志

详见 [CHANGELOG.md](CHANGELOG.md)

---

## 致谢

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [NeoDB](https://neodb.cc)
- [The Movie Database (TMDB)](https://www.themoviedb.org)
- [Rebrickable](https://rebrickable.com)
- [MeTube](https://github.com/alexta69/metube)
- [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr)

---

欢迎提交 Issue 和 Pull Request！
