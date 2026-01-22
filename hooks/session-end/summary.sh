#!/bin/bash
# Thanos Session End - The Reckoning
# Provides comprehensive summary of the session

THANOS_ROOT="${THANOS_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$THANOS_ROOT" || exit 1

# Get time context
HOUR=$(date +%H)
TIME_DISPLAY=$(date "+%I:%M %p")

# Time of day message
if [ "$HOUR" -ge 5 ] && [ "$HOUR" -lt 12 ]; then
    TIME_MSG="Morning session complete"
elif [ "$HOUR" -ge 12 ] && [ "$HOUR" -lt 17 ]; then
    TIME_MSG="Afternoon execution finalized"
elif [ "$HOUR" -ge 17 ] && [ "$HOUR" -lt 21 ]; then
    TIME_MSG="Evening session concluded"
else
    TIME_MSG="Night session ends. Rest now."
fi

# Get session duration
DURATION=$(python3 "$THANOS_ROOT/Tools/time_tracker.py" --json 2>/dev/null | jq -r '.duration_display // "unknown"' 2>/dev/null || echo "unknown")

# Record and get cost stats
python3 "$THANOS_ROOT/Tools/cost_tracker.py" --record-end 2>/dev/null
COST_STATS=$(python3 "$THANOS_ROOT/Tools/cost_tracker.py" --current --json 2>/dev/null || echo '{"status":"unavailable"}')
COST=$(echo "$COST_STATS" | jq -r '.cost // 0' 2>/dev/null || echo "0")
TOKENS=$(echo "$COST_STATS" | jq -r '.total_tokens // 0' 2>/dev/null || echo "0")

# Output session summary
cat << EOF
### DESTINY // $TIME_DISPLAY
$TIME_MSG

Session Duration: $DURATION
Tokens Used: $(printf "%'d" $TOKENS 2>/dev/null || echo $TOKENS)
Cost: \$$COST

The stones are silent. The work is preserved.
EOF
