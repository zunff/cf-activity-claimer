#!/usr/bin/env bash
# macOS 双击启动用的外壳（Finder 里双击 .command 才会执行）。
# 双击后若提示无法打开，右键 -> 打开，或先执行：chmod +x start.command
cd "$(dirname "${BASH_SOURCE[0]}")"
exec ./start.sh "$@"
