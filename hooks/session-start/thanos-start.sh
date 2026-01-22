#!/bin/bash
# Thanos Session Start - The Executor Awakens
# Note: Banner display is handled by ~/Projects/Thanos/Tools/thanos-claude wrapper
# This hook provides context to Claude and resets state as fallback

THANOS_ROOT="${THANOS_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$THANOS_ROOT" || exit 1

# Get current time context
HOUR=$(date +%H)
TIME_DISPLAY=$(date "+%I:%M %p")

# Time of day message
if [ "$HOUR" -ge 5 ] && [ "$HOUR" -lt 12 ]; then
    TIME_MSG="The day begins..."
elif [ "$HOUR" -ge 12 ] && [ "$HOUR" -lt 17 ]; then
    TIME_MSG="Midday execution..."
elif [ "$HOUR" -ge 17 ] && [ "$HOUR" -lt 21 ]; then
    TIME_MSG="The day draws to close..."
else
    TIME_MSG="The universe rests. Should you?"
fi

# Get session context (reset already done by wrapper to avoid race condition)
CONTEXT_OUTPUT=$(python3 "$THANOS_ROOT/Tools/time_tracker.py" --context 2>/dev/null || echo '{"status": "unavailable"}')

# Output context for Claude (goes to system-reminder)
cat << EOF
### DESTINY // $TIME_DISPLAY
$TIME_MSG

$CONTEXT_OUTPUT
EOF

# Run daily brief for meaningful context (suppress errors)
bun "$THANOS_ROOT/Tools/daily-brief.ts" 2>/dev/null || true

# Set visual state to CHAOS (morning disorder, unsorted tasks)
python3 "$THANOS_ROOT/Tools/wallpaper_manager.py" --auto 2>/dev/null || true

# Ensure Operator daemon is running (background monitoring)
if ! launchctl list | grep -q com.thanos.operator 2>/dev/null; then
    echo "[Daemon] Starting Operator..." >&2
    launchctl start com.thanos.operator 2>/dev/null || true
fi
