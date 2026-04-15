#!/bin/bash
set -e

cd "$(dirname "$0")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[deploy]${NC} $1"; }
warn() { echo -e "${YELLOW}[warn]${NC} $1"; }
die() { echo -e "${RED}[error]${NC} $1" && exit 1; }

git rev-parse --git-dir > /dev/null 2>&1 || die "请在 git 仓库目录下运行此脚本"
[ -f CHANGELOG.md ] || die "CHANGELOG.md 不存在"

# 提取最新版本号（格式：## [v1.2.3] - YYYY-MM-DD）
CURRENT_VERSION=$(grep -m1 "^## \[" CHANGELOG.md | sed -E "s/^## \[v?([^]]+)\].*/\1/" | tr -d " ")
[ -z "$CURRENT_VERSION" ] && die "无法从 CHANGELOG.md 解析版本号"
log "当前版本: $CURRENT_VERSION"

# +1 patch
IFS='.' read -r major minor patch <<< "$CURRENT_VERSION"
patch=$((patch + 1))
NEW_VERSION="${major}.${minor}.${patch}"
log "新版本: $NEW_VERSION"

# 更新 CHANGELOG.md：在顶部插入新版本条目
TODAY=$(date +%Y-%m-%d)
FIRST_TAG_LINE=$(grep -n "^## \[" CHANGELOG.md | head -1 | cut -d: -f1)

if [ -z "$FIRST_TAG_LINE" ]; then
    { echo "# Changelog"; echo ""; echo "## [v$NEW_VERSION] - $TODAY"; echo ""; echo "### Added"; echo "- 新版本发布"; echo ""; cat CHANGELOG.md; } > /tmp/changelog_new.md
    mv /tmp/changelog_new.md CHANGELOG.md
else
    HEAD=$(head -n $((FIRST_TAG_LINE - 1)) CHANGELOG.md)
    TAIL=$(tail -n +$FIRST_TAG_LINE CHANGELOG.md)
    { echo "$HEAD"; echo "## [v$NEW_VERSION] - $TODAY"; echo ""; echo "### Added"; echo "- 新版本发布"; echo ""; echo "$TAIL"; } > /tmp/changelog_new.md
    mv /tmp/changelog_new.md CHANGELOG.md
fi

log "CHANGELOG.md 已更新"

# Git 提交
git add CHANGELOG.md
git add -A
COMMIT_MSG="release: v$NEW_VERSION"
git commit -m "$COMMIT_MSG"
log "已提交: $COMMIT_MSG"

# 打 tag
git tag -f "v$NEW_VERSION"
log "已打 tag: v$NEW_VERSION"

# 推送
log "推送到远程仓库..."
git push && git push origin "v$NEW_VERSION"

log ""
log "✅ 完成，版本 v$NEW_VERSION 已发布"
log "   下次发布将自动更新为 v$((major)).$((minor)).$((patch + 1))"
