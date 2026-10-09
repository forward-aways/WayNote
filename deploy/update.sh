#!/usr/bin/env bash
# 途笺 WayNote · 服务器端更新脚本（依赖同步 → 数据库迁移 → 重启 → 健康检查）
#
# 为什么不用 git pull：
#   这台服务器在国内直连 github.com 会被 TLS 重置
#   （fatal: unable to access ... GnuTLS recv error (-110): The TLS connection was non-properly terminated.）
#   所以「取代码」由本地打包送进来（git bundle），脚本负责应用它。
#
# 用法：
#   本地（Windows PowerShell，仓库根目录）：
#     git bundle create waynote.bundle main
#     scp waynote.bundle ubuntu@<服务器IP>:/tmp/
#   服务器：
#     bash /home/ubuntu/ai-project/WayNote/deploy/update.sh /tmp/waynote.bundle
#
#   不带参数运行 = 只做「依赖同步 + 迁移 + 重启 + 健康检查」（代码已更新时用）。
set -euo pipefail

# uv 装在 ~/.local/bin，非交互 shell 的 PATH 里没有
export PATH="$HOME/.local/bin:$PATH"

BUNDLE="${1:-}"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

if [ -n "$BUNDLE" ]; then
  echo "==> 1/4 应用代码（git bundle）：$BUNDLE"
  [ -f "$BUNDLE" ] || { echo "找不到 bundle 文件：$BUNDLE"; exit 1; }
  if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    echo "工作区有未提交改动，先处理（git status）再更新"; exit 1
  fi
  git bundle verify "$BUNDLE" >/dev/null
  git fetch "$BUNDLE" main
  git merge --ff-only FETCH_HEAD
  git --no-pager log --oneline -1
else
  echo "==> 1/4 跳过代码更新（未提供 bundle，视为代码已更新）"
fi

echo "==> 2/4 后端依赖（仓库根：uv sync --frozen --no-dev）"
uv sync --frozen --no-dev

echo "==> 3/4 数据库迁移（backend/ 下：uv run alembic upgrade head）"
cd "$APP_DIR/backend"
uv run --no-sync alembic upgrade head
uv run --no-sync alembic current

echo "==> 4/4 重启服务并自检"
sudo systemctl restart waynote
sleep 2
systemctl is-active waynote
curl -fsS http://127.0.0.1:8010/api/v1/health
echo
echo "==> 完成"
