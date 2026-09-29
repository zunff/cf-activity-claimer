#!/bin/bash
# 安装 macOS launchd 每日定时领取任务（默认每天 10:30）。
# 用法：  bash install_schedule.sh          # 安装
#        bash install_schedule.sh remove   # 卸载
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$DIR/.venv/bin/python"
PLIST="$HOME/Library/LaunchAgents/com.cfclaim.daily.plist"
LABEL="com.cfclaim.daily"

if [[ "${1:-}" == "remove" ]]; then
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "已卸载定时任务"
  exit 0
fi

if [[ ! -x "$PY" ]]; then
  echo "找不到解释器：$PY，请先创建 venv 并安装依赖" >&2
  exit 1
fi

mkdir -p "$DIR/output"

cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PY</string>
    <string>$DIR/main.py</string>
  </array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>10</integer>
    <key>Minute</key><integer>30</integer>
  </dict>
  <key>StandardOutPath</key><string>$DIR/output/launchd.log</string>
  <key>StandardErrorPath</key><string>$DIR/output/launchd.err</string>
</dict>
</plist>
PLIST_EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "已安装：每天 10:30 自动领取（$PLIST）"
echo "日志：$DIR/output/launchd.log"
echo "卸载：bash install_schedule.sh remove"
