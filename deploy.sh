#!/bin/bash
set -e

# ============================================================
# All-in-One Bot 部署脚本
# 功能：
#   1. 同步本地 repo → N100 VPS 挂载路径
#   2. 自动版本号（Git tag）
#   3. Git 提交 & 推送
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" &>/dev/null && pwd)"
cd "$SCRIPT_DIR"

# ============================================================
# 路径映射（Mac 本地路径 ↔ VPS 容器内路径）
# ============================================================
# Mac 本地挂载路径
LOCAL_PROGRAM_DIR="/Volumes/dav/OpenList-N100/Local/mnt/Download/Program/All-in-One_bot"

# ============================================================
# 检查挂载是否可用
# ============================================================
if [ ! -d "$LOCAL_PROGRAM_DIR" ]; then
    echo "❌ N100 挂载路径不可用: $LOCAL_PROGRAM_DIR"
    echo "   请确保 /Volumes/dav/OpenList-N100 已挂载"
    exit 1
fi

# ============================================================
# 阶段 1：同步本地 repo → VPS 挂载路径
# ============================================================
echo ""
echo "==> 阶段 1：同步文件到 VPS..."

# 排除项：数据文件、macOS 元数据、Git 自身
RSYNC_EXCLUDE=(
    --exclude='.git/'
    --exclude='__pycache__/'
    --exclude='*.pyc'
    --exclude='.DS_Store'
    --exclude='deploy.sh'
    --exclude='*.db'
)

rsync -av --inplace "${RSYNC_EXCLUDE[@]}" "$SCRIPT_DIR/" "$LOCAL_PROGRAM_DIR/"

echo "   ✅ 文件同步完成"

# ============================================================
# 阶段 2：自动版本号
# ============================================================
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")

if [ -z "$LAST_TAG" ]; then
    VERSION="v1.0.001"
else
    LAST_PATCH=$(echo "$LAST_TAG" | grep -oE '[0-9]+$' | head -1)
    NEXT_PATCH=$(printf "%03d" $((LAST_PATCH + 1)))
    VERSION="v1.0.${NEXT_PATCH}"
fi

echo ""
echo "==> 版本: $VERSION"

# 更新 main.py 中的版本号（如有定义）
python3 - <<EOF
import re, sys
filepath = "$SCRIPT_DIR/main.py"
try:
    with open(filepath, 'r') as f:
        content = f.read()
    new_content = re.sub(r'VERSION = "v[^"]*"', f'VERSION = "$VERSION"', content)
    if new_content != content:
        with open(filepath, 'w') as f:
            f.write(new_content)
        print(f"   ✅ 版本号已更新为 $VERSION")
    else:
        print("   ℹ️  main.py 中未定义 VERSION，跳过")
except Exception as e:
    print(f"   ⚠️  版本号更新失败: {e}")
EOF

# ============================================================
# 阶段 3：写 CHANGELOG
# ============================================================
DATE=$(date "+%Y-%m-%d")
CHANGELOG_ENTRY="## [$VERSION] - $DATE

### 更新
- 同步到 N100 容器

"

if [ -f CHANGELOG.md ]; then
    echo "$CHANGELOG_ENTRY" | cat - CHANGELOG.md > /tmp/_changelog_tmp && mv /tmp/_changelog_tmp CHANGELOG.md
fi

# ============================================================
# 阶段 4：Git 提交 & 推送
# ============================================================
echo ""
echo "==> 提交并推送..."
git add .
git commit -m "release: $VERSION"
git tag -f "$VERSION"
git push -u origin main && git push origin "$VERSION"

echo ""
echo "✅ 部署完成！版本 $VERSION"
echo "💡 请在 N100 上手动重启容器: docker restart All-in-One_tgbot"
