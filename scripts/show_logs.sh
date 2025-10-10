#!/usr/bin/env bash
set -euo pipefail

clear
cat <<'BANNER'
#      ___________    _____
#  /               \ |  o  | 
# |                |/   __\| 
# |  _______________  /     
#   |_|_|     |_|_|
#
# HopeTurtle GPS Service is live! 🐢
BANNER
echo

if ! command -v journalctl >/dev/null 2>&1; then
  echo "⚠️  journalctl not found. Please install systemd or view logs manually."
  exit 1
fi

echo "📡 Following logs for: hopeturtle-gps.service"
echo "🕒 Showing the last 10 minutes of logs..."
echo "Press Ctrl+C to stop."
echo

journalctl -u hopeturtle-gps.service --since "10 min ago" --no-pager
echo
journalctl -fu hopeturtle-gps.service
