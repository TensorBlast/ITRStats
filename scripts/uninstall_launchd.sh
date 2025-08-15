#!/usr/bin/env bash
set -euo pipefail

PLIST_DST="$HOME/Library/LaunchAgents/com.moot.itrstats.collector.plist"

launchctl bootout gui/$(id -u) "$PLIST_DST" 2>/dev/null || true
rm -f "$PLIST_DST"
echo "Uninstalled LaunchAgent: $PLIST_DST"
