#!/bin/bash
# Smart Swarm Cleanup Hook
# Archives swarm session data - actual cleanup done via MCP tools
# Fast execution - no external CLI calls

set -euo pipefail

SWARM_STATE_FILE="${HOME}/.claude-flow-swarm-state.json"
ARCHIVE_DIR="${HOME}/.claude-flow-swarm-history"

main() {
    if [ ! -f "$SWARM_STATE_FILE" ]; then
        exit 0
    fi

    # Archive the session
    mkdir -p "$ARCHIVE_DIR"

    # Add end time and archive
    local ended_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local archive_file="$ARCHIVE_DIR/session-$(date +%Y%m%d-%H%M%S).json"

    jq --arg ended "$ended_at" '. + {endedAt: $ended}' "$SWARM_STATE_FILE" > "$archive_file" 2>/dev/null || \
        cp "$SWARM_STATE_FILE" "$archive_file"

    # Clean up state file
    rm -f "$SWARM_STATE_FILE"

    echo "Swarm session archived to: $archive_file"
    echo "Note: Use mcp__claude-flow__swarm_destroy to cleanup active swarms"
}

main
