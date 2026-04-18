#!/bin/bash
set -e

# ============================================================
# All-in-One Bot 自动化部署脚本
#
# 使用方式：
#   1. 将本脚本上传到 VPS 部署目录
#   2. 编辑本文件底部的 DEPLOY 配置（WEBHOOK_URL 等）
#   3. 执行 ./deploy.sh
#
# 功能：
#   1. 从 GitHub 拉取最新代码（不包含 config.py）
#   2. 重启 Docker 容器
#   3. 发送部署通知
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
cd "$SCRIPT_DIR"

# ============================================================
# 工具函数
# ============================================================
info()  { echo "[INFO]  $1"; }
warn()  { echo "[WARN]  $1"; }
error() { echo "[ERROR] $1" >&2; }

# 发送通知（支持自定义回调）
notify() {
    local msg="$1"
    if [ -n "$WEBHOOK_URL" ]; then
        curl -s -X POST "$WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"text\": \"$msg\"}" \
            2>/dev/null || true
    fi
    echo "📢 $msg"
}

# ============================================================
# 拉取最新代码（git pull）
# ============================================================
info "更新代码..."
if git rev-parse --git-dir > /dev/null 2>&1; then
    git fetch origin main
    LOCAL=$(git rev-parse @)
    REMOTE=$(git rev-parse origin/main)
    if [ "$LOCAL" = "$REMOTE" ]; then
        info "代码已是最新，无需更新"
    else
        info "检测到更新，开始拉取..."
        git checkout -f origin/main
        git reset --hard origin/main
        info "✅ 代码已更新到最新版本"
    fi
else
    warn "非 Git 仓库，跳过代码更新"
fi

# ============================================================
# 恢复 config.py（如被 GitHub 覆盖）
# 注意：config.py 不应提交到 GitHub，此处仅作保险
# ============================================================
if [ ! -f config.py ] || [ -z "$(grep -v '^#' config.py | grep 'BOT_TOKEN' | grep -v '""' | grep -v 'os.getenv')" ]; then
    warn "config.py 缺失或未配置，请手动创建"
fi

# ============================================================
# 版本号
# ============================================================
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
if [ -n "$LAST_TAG" ]; then
    info "当前版本: $LAST_TAG"
fi

# ============================================================
# 重启容器
# ============================================================
CONTAINER_NAME="${CONTAINER_NAME:-All-in-One_tgbot}"
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    info "重启容器: $CONTAINER_NAME ..."
    docker restart "$CONTAINER_NAME"
    sleep 3
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        notify "🤖 All-in-One Bot 已重启（$LAST_TAG）"
    else
        error "容器启动失败，请检查日志: docker logs $CONTAINER_NAME"
        exit 1
    fi
else
    error "容器不存在: $CONTAINER_NAME"
    error "请先手动创建容器"
    exit 1
fi

info "✅ 部署完成"

# ============================================================
# 配置区（编辑这里定制你的部署）
# ============================================================
# Docker 容器名称
# CONTAINER_NAME="All-in-One_tgbot"

# 部署通知 Webhook（支持 Bark、钉钉、Telegram 等）
# 留空则不发送通知
# 示例（Bark）：WEBHOOK_URL="https://api.day.app/你的KEY/部署通知"
# 示例（TG）：   WEBHOOK_URL="https://api.telegram.org/botTOKEN/sendMessage?chat_id=ID&text=%s"
WEBHOOK_URL=""
