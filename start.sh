#!/usr/bin/env bash
# CF 活动自动领取 · 一键启动（macOS / Linux）
# 用法：./start.sh            普通启动
#       ./start.sh --show-browser   显示真实浏览器窗口
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

PY="$DIR/.venv/bin/python"

if [[ ! -x "$PY" ]]; then
  echo "==> 首次运行：正在创建虚拟环境并安装依赖（约一两分钟）"
  if command -v uv >/dev/null 2>&1; then
    uv venv .venv --python 3.12
    uv pip install --python .venv -r requirements.txt
  elif command -v python3 >/dev/null 2>&1; then
    python3 -m venv .venv
    "$PY" -m pip install --upgrade pip >/dev/null
    "$PY" -m pip install -r requirements.txt
  else
    echo "找不到 python3，请先安装 Python 3.10+" >&2
    exit 1
  fi
fi

echo "==> 启动 UI，浏览器会自动打开…"
exec "$PY" "$DIR/ui.py" "$@"
