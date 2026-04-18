#!/bin/bash
set -e

# ============================================================
# All-in-One Bot 部署脚本
# 功能：
#   1. 同步必要文件到 N100（rsync 增量）
#   2. 提交推送 GitHub（版本号 + CHANGELOG）
#   3. 在 N100 上执行 git pull 拉取最新代码
#
# 注意：
#   - config.py 通过 rsync 同步到 N100（.gitignore 保护不推 GitHub）
#   - 推送内容不含任何个人 token/ID
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
cd "$SCRIPT_DIR"

# ============================================================
# 路径配置（本地项目路径 ↔ N100 挂载路径）
# N100_PATH 可以通过环境变量覆盖，默认从 .deploy.conf 读取
# ============================================================
N100_PATH="${N100_PATH:-}"

if [ -z "$N100_PATH" ] && [ -f ".deploy.conf" ]; then
    N100_PATH="$(cat .deploy.conf 2>/dev/null | grep '^N100_PATH=' | cut -d= -f2- | tr -d '"' | tr -d "'")"
fi

if [ -z "$N100_PATH" ]; then
    echo "❌ 未找到 N100 路径"
    echo "   方式 1：创建 .deploy.conf 文件，内容：N100_PATH=/Volumes/dav/..."
    echo "   方式 2：export N100_PATH=/Volumes/dav/..."
    exit 1
fi

# ============================================================
# 工具函数
# ============================================================
info()  { echo "[INFO]  $1"; }
warn()  { echo "[WARN]  $1"; }
ok()    { echo "✅ $1"; }

# ============================================================
# 阶段 1：同步文件到 N100
# ============================================================
info "阶段 1：同步到 N100..."

if [ ! -d "$N100_PATH" ]; then
    echo "❌ N100 挂载路径不可用: $N100_PATH"
    exit 1
fi

# 排除项：代码缓存、Git 自身、配置文件、数据文件
RSYNC_EXCLUDE=(
    --exclude='.git/'
    --exclude='__pycache__/'
    --exclude='*.pyc'
    --exclude='.DS_Store'
    --exclude='config.py.template'
    --exclude='config.py.template'
    --exclude='deploy.sh'
    --exclude='*.db'             # 本地数据库不覆盖远程
    --exclude='.deploy.conf'
)

rsync -av --inplace "${RSYNC_EXCLUDE[@]}" "$SCRIPT_DIR/" "$N100_PATH/"
ok "文件同步完成"

# ============================================================
# 阶段 2：自动版本号
# ============================================================
info "阶段 2：版本号..."

LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")

if [ -z "$LAST_TAG" ]; then
    VERSION="v1.0.001"
else
    LAST_PATCH=$(echo "$LAST_TAG" | grep -oE '[0-9]+$' | head -1)
    NEXT_PATCH=$(printf "%03d" $((LAST_PATCH + 1)))
    VERSION="v1.0.${NEXT_PATCH}"
fi

info "新版本: $VERSION"

# 更新 main.py 中的 VERSION（如有定义）
python3 - <<EOF
import re, sys
filepath = "$SCRIPT_DIR/main.py"
try:
    with open(filepath) as f:
        content = f.read()
    new = re.sub(r'VERSION = "v[^"]*"', f'VERSION = "$VERSION"', content)
    if new != content:
        with open(filepath, 'w') as f:
            f.write(new)
        print(f"[INFO]  版本号已更新为 $VERSION")
    else:
        print("[INFO]  main.py 中无 VERSION 定义，跳过")
except Exception as e:
    print(f"[WARN]  版本号更新失败: {e}")
EOF

# ============================================================
# 阶段 3：写 CHANGELOG
# ============================================================
info "阶段 3：更新 CHANGELOG..."

DATE=$(date "+%Y-%m-%d")
ENTRY="## [$VERSION] - $DATE

### 更新
- 同步到 N100

"

if [ -f CHANGELOG.md ]; then
    { echo "$ENTRY"; cat CHANGELOG.md; } > /tmp/_changelog_tmp && mv /tmp/_changelog_tmp CHANGELOG.md
    ok "CHANGELOG.md 已更新"
fi

# ============================================================
# 阶段 4：Git 提交 & 推送
# ============================================================
info "阶段 4：Git 提交..."

git add .
git commit -m "release: $VERSION" || { warn "无变更，跳过提交"; }
git tag -f "$VERSION"
git push -u origin main 2>/dev/null && git push origin "$VERSION" 2>/dev/null || warn "GitHub 推送失败"

# ============================================================
# 阶段 5：N100 执行 git pull（自动拉取最新代码）
# ============================================================
info "阶段 5：N100 拉取最新代码..."

# 通过 git hook 目录是否存在判断是否在 Git 仓库内
if [ -d "$N100_PATH/.git" ]; then
    cd "$N100_PATH"
    git fetch origin main
    LOCAL=$(git rev-parse @)
    REMOTE=$(git rev-parse origin/main)
    if [ "$LOCAL" = "$REMOTE" ]; then
        info "N100 已是最新，无需 pull"
    else
        git reset --hard origin/main
        ok "N100 已拉取最新代码"
    fi
    cd "$SCRIPT_DIR"
else
    warn "N100 目录不是 Git 仓库，跳过 pull（手动执行 git clone 或 git init）"
fi

ok "部署完成！版本 $VERSION"
echo ""
echo "💡 如需重启容器，请在 N100 上执行：docker restart All-in-One_tgbot"
