#!/bin/bash
# Hydrate context on session start

THANOS_ROOT="${THANOS_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"

echo "=== Thanos Session Hydration ==="

# Update current state
if [ -f "$THANOS_ROOT/tools/state_manager.py" ]; then
    python3 "$THANOS_ROOT/tools/state_manager.py" refresh 2>/dev/null || echo "State refresh pending"
fi

# Output current state for context
if [ -f "$THANOS_ROOT/context/current_state.md" ]; then
    cat "$THANOS_ROOT/context/current_state.md"
fi

echo ""
echo "=== Ready ==="
