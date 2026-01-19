#!/bin/bash
#
# fix-calendar-oauth-warning.sh
#
# Fixes the Google Calendar OAuth warning that appears in Thanos by removing
# the mcp-gsuite MCP server from Claude Code's project configuration.
#
# The warning: "WARNING:root:No stored Oauth2 credentials yet at path: ./.oauth2.*.json"
#
# This warning comes from the mcp-gsuite MCP server which is NOT needed since
# Thanos has its own Google Calendar adapter (Tools/adapters/google_calendar/).
#
# Usage:
#   ./scripts/fix-calendar-oauth-warning.sh
#
# What it does:
#   1. Backs up ~/.claude.json
#   2. Removes mcp-gsuite from the Thanos project's MCP server list
#   3. Shows the result
#

set -e

CLAUDE_CONFIG="$HOME/.claude.json"
THANOS_PROJECT="/Users/jeremy/Projects/Thanos"

echo "Google Calendar OAuth Warning Fix"
echo "================================="
echo ""

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed."
    echo "Install with: brew install jq"
    exit 1
fi

# Check if config exists
if [ ! -f "$CLAUDE_CONFIG" ]; then
    echo "Error: Claude config not found at $CLAUDE_CONFIG"
    exit 1
fi

# Check if mcp-gsuite is configured for Thanos
HAS_MCP_GSUITE=$(jq -r ".projects[\"$THANOS_PROJECT\"].mcpServers[\"mcp-gsuite\"] // \"null\"" "$CLAUDE_CONFIG")

if [ "$HAS_MCP_GSUITE" = "null" ]; then
    echo "mcp-gsuite is not configured for the Thanos project."
    echo "The OAuth warning may be coming from a different source."
    echo ""
    echo "Possible causes:"
    echo "  1. A parent directory's MCP config (check ~/.claude.json for /Users/jeremy)"
    echo "  2. A global MCP server configuration"
    echo ""

    # Check parent config
    PARENT_HAS=$(jq -r ".projects[\"/Users/jeremy\"].mcpServers[\"mcp-gsuite\"] // \"null\"" "$CLAUDE_CONFIG")
    if [ "$PARENT_HAS" != "null" ]; then
        echo "Found: mcp-gsuite is configured at the home directory level."
        echo "To remove it from home directory, run:"
        echo "  jq 'del(.projects[\"/Users/jeremy\"].mcpServers[\"mcp-gsuite\"])' ~/.claude.json > ~/.claude.json.tmp && mv ~/.claude.json.tmp ~/.claude.json"
    fi
    exit 0
fi

# Backup config
BACKUP_FILE="$CLAUDE_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"
cp "$CLAUDE_CONFIG" "$BACKUP_FILE"
echo "Backed up config to: $BACKUP_FILE"

# Remove mcp-gsuite from Thanos project
echo "Removing mcp-gsuite from Thanos project configuration..."
jq "del(.projects[\"$THANOS_PROJECT\"].mcpServers[\"mcp-gsuite\"])" "$CLAUDE_CONFIG" > "${CLAUDE_CONFIG}.tmp" && mv "${CLAUDE_CONFIG}.tmp" "$CLAUDE_CONFIG"

echo ""
echo "Done! mcp-gsuite has been removed from the Thanos project."
echo ""
echo "Note: Thanos uses its own Google Calendar adapter (Tools/adapters/google_calendar/)"
echo "which provides calendar integration without needing the mcp-gsuite server."
echo ""
echo "Restart Claude Code for changes to take effect."
