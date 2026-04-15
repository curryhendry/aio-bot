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
| ⚙️ 系统状态 | CPU / 磁盘 / MeTube 状态，重启机器人，关闭 MeTube |

### 一级菜单

```
🔍 搜图书/电影/电视  ｜  🧱 乐高查询
⚙️ 系统状态
```
<img src="https://img.curryhendry.com/乱七八糟/All-in-One%20Telegram%20Bot/IMG_5915.png" width="400">  <img src="https://img.curryhendry.com/乱七八糟/All-in-One%20Telegram%20Bot/IMG_5912.png" width="400">

<img src="https://img.curryhendry.com/乱七八糟/All-in-One%20Telegram%20Bot/IMG_5916.png" width="400">  <img src="https://img.curryhendry.com/乱七八糟/All-in-One%20Telegram%20Bot/IMG_5914.png" width="400">

<img src="https://img.curryhendry.com/乱七八糟/All-in-One%20Telegram%20Bot/IMG_5917.png" width="400">  <img src="https://img.curryhendry.com/乱七八糟/All-in-One%20Telegram%20Bot/IMG_5918.png" width="400">

---

## 快速部署

### 前置要求

- VPS（本文以 Ubuntu 为例）
- Docker 已安装
- Telegram Bot Token（找 [@BotFather](https://t.me/BotFather) 创建）

### 1. 获取 API Key

| 服务 | 获取地址 | 说明 |
|------|----------|------|
| Telegram Bot Token | [@BotFather](https://t.me/BotFather) | 必填 |
| Telegram ChatID | [@get_id_bot](https://t.me/get_id_bot) | 强烈建议填写 |
| NeoDB Token | https://neodb.cc/oauth2/applications/ | 创建应用获取 |
| TMDB Token | https://www.themoviedb.org/settings/api | 注册后申请 API Key |
| Rebrickable Key | https://rebrickable.com/api/register/ | 注册后申请 |
| MeTube Cookie | Chrome获取Cookies插件 | YouTube/BiliBili 下载需要（自行解决） |

### 2. 配置 config.py

```python
# config.py  — 复制自 config.py.template，填入真实值

BOT_TOKEN = "你的Telegram Bot Token"
ALLOWED_IDS = [你的Telegram用户ID]   # 多人白名单用逗号分隔

TMDB_TOKEN = "你的TMDB Token"
NEODB_TOKEN = "你的NeoDB Token"
RB_KEY = "你的Rebrickable API Key"

METUBE_URL = "http://MeTube:8081"
METUBE_CONTAINER_NAME = "MeTube"
```

> **安全提示**：不要将 config.py 提交到 GitHub，敏感信息只存在于 VPS 本地。GitHub 仅保存 `config.py.template` 模板文件。

### 3. 运行容器

```bash
# 克隆仓库
git clone https://github.com/curryhendry/aio-bot.git /home/ubuntu/aio_bot
cd /home/ubuntu/aio_bot

# 构建镜像
docker build -t aio_bot:latest .

# 创建 docker 网络（如果尚未创建）
docker network create aio-net 2>/dev/null || true

# 创建 MeTube 容器（如果尚未创建）
docker run -d \
  --name MeTube \
  --network aio-net \
  --restart=unless-stopped \
  -p 8083:8081 \
  -v /path/to/cookies:/app/data \
  curlimages/curl:latest \
  sh -c "echo '配置你的MeTube cookie后启动'"

# 运行机器人
docker run -d \
  --name All-in-One_tgbot \
  --network aio-net \
  --restart=unless-stopped \
  -w /aio_bot \
  -v /home/ubuntu/aio_bot:/aio_bot \
  -v /home/ubuntu/aio_bot/downloads:/downloads \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /path/to/cookies:/cookies \
  -e TZ=Asia/Shanghai \
  aio_bot:latest \
  python main.py
```

> MeTube 与机器人必须在同一 `aio-net` 网络下才能互通。

### 4. 更新版本

```bash
cd /home/ubuntu/aio_bot

# 拉取最新代码
git pull

# 重启容器
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
├── lego_db.sqlite        # 乐高人仔本地数据库（7.5MB）
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

## 开发说明

### 本地开发环境

```bash
# 克隆仓库
git clone https://github.com/curryhendry/aio-bot.git ~/Projects/aio-bot
cd ~/Projects/aio-bot

# 安装依赖
pip install python-telegram-bot flask psutil requests yt-dlp docker

# 复制配置
cp config.py.template config.py
# 编辑 config.py 填入真实 Token

# 本地运行
python main.py
```

### 发布流程

```bash
./deploy.sh
```

`deploy.sh` 会自动：
1. 读取 `CHANGELOG.md` 生成版本号
2. 更新 `config.py.template`（如有变化）
3. 提交并推送
4. 打 Git Tag

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

---

欢迎提交 Issue 和 Pull Request！
