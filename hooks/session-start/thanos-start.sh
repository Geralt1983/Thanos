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

# Reset time tracker (may already be done by wrapper, but safe to call again)
RESET_OUTPUT=$(python3 "$THANOS_ROOT/Tools/time_tracker.py" --reset 2>/dev/null || echo '{"status": "unavailable"}')

# Output context for Claude (goes to system-reminder)
cat << EOF
### DESTINY // $TIME_DISPLAY
$TIME_MSG

$RESET_OUTPUT
startup hook success: Success
EOF
