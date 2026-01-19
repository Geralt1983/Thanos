#!/bin/bash
#
# Thanos Statusline Hook for Claude Code
#
# This script generates a statusline showing Thanos-relevant metrics:
# - Work progress (points/target)
# - Oura readiness score
# - Current streak
# - Active tasks
# - Git branch
#
# Usage:
#   Called by Claude Code's statusLine hook configuration.
#   Reads JSON context from stdin if available.
#
# Fallback:
#   If the Python generator fails, outputs a minimal statusline.
#

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THANOS_ROOT="${THANOS_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

# Export for Python script
export THANOS_ROOT

# Read stdin if available (Claude Code passes context as JSON)
INPUT=""
if [ ! -t 0 ]; then
    INPUT=$(cat)
fi

# Try Python statusline generator first (prefer Tools version with better data fetching)
TOOLS_STATUSLINE="$THANOS_ROOT/Tools/thanos_statusline.py"
if [ -f "$TOOLS_STATUSLINE" ]; then
    if python3 "$TOOLS_STATUSLINE" 2>/dev/null; then
        exit 0
    fi
fi

# Fallback to local version
if [ -f "$SCRIPT_DIR/thanos_statusline.py" ]; then
    if echo "$INPUT" | python3 "$SCRIPT_DIR/thanos_statusline.py" 2>/dev/null; then
        exit 0
    fi
fi

# Fallback: Basic statusline if Python fails
MODEL=""
BRANCH=""
CWD=""

# Try to parse context from input
if [ -n "$INPUT" ]; then
    MODEL=$(echo "$INPUT" | jq -r '.model.display_name // .model // "Claude"' 2>/dev/null || echo "Claude")
    CWD=$(echo "$INPUT" | jq -r '.workspace.current_dir // .cwd // ""' 2>/dev/null)
fi

# Get git branch
if [ -n "$CWD" ]; then
    BRANCH=$(cd "$CWD" 2>/dev/null && git branch --show-current 2>/dev/null || echo "")
elif [ -d "$THANOS_ROOT/.git" ]; then
    BRANCH=$(cd "$THANOS_ROOT" && git branch --show-current 2>/dev/null || echo "")
fi

# Build fallback statusline
printf "\033[1m\033[35mThanos\033[0m"

if [ -n "$MODEL" ] && [ "$MODEL" != "null" ]; then
    # Shorten model name
    case "$MODEL" in
        *opus*|*Opus*)    MODEL="Opus 4.5" ;;
        *sonnet*|*Sonnet*) MODEL="Sonnet 4" ;;
        *haiku*|*Haiku*)  MODEL="Haiku 3.5" ;;
    esac
    printf " | \033[36m$MODEL\033[0m"
fi

if [ -n "$BRANCH" ]; then
    printf " | \033[33m$BRANCH\033[0m"
fi

# Try to get basic metrics from TimeState
if [ -f "$THANOS_ROOT/State/TimeState.json" ]; then
    INTERACTIONS=$(jq -r '.interaction_count_today // 0' "$THANOS_ROOT/State/TimeState.json" 2>/dev/null || echo "0")
    if [ "$INTERACTIONS" != "0" ] && [ "$INTERACTIONS" != "null" ]; then
        printf " | \033[2m#$INTERACTIONS\033[0m"
    fi
fi

echo ""
