#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/Users/moot/Library/Mobile Documents/com~apple~CloudDocs/Documents/Programs/ITRStats"
PLIST_SRC="$PROJECT_DIR/scripts/com.moot.itrstats.collector.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.moot.itrstats.collector.plist"
LOG_DIR="$HOME/Library/Logs/ITRStats"

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"
cp "$PLIST_SRC" "$PLIST_DST"

launchctl bootout gui/$(id -u) "$PLIST_DST" 2>/dev/null || true
launchctl bootstrap gui/$(id -u) "$PLIST_DST"
launchctl enable gui/$(id -u)/com.moot.itrstats.collector
launchctl kickstart -k gui/$(id -u)/com.moot.itrstats.collector

launchctl print gui/$(id -u)/com.moot.itrstats.collector | sed -n '1,200p' | cat

echo "Installed LaunchAgent at: $PLIST_DST"
