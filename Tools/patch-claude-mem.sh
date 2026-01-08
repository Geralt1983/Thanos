#!/bin/bash
# patch-claude-mem.sh - Fix claude-mem plugin exit code issue
#
# Claude Code interprets exit code 3 (USER_MESSAGE_ONLY) as an error,
# causing "hook error" messages. This script patches the plugin to use
# exit code 0 (SUCCESS) instead.
#
# Run after claude-mem plugin updates to reapply the fix.

set -e

PLUGIN_DIR="$HOME/.claude/plugins/cache/thedotmack/claude-mem"
HOOK_FILE="user-message-hook.js"

# Find the latest version directory
if [ ! -d "$PLUGIN_DIR" ]; then
    echo "Error: claude-mem plugin not found at $PLUGIN_DIR"
    exit 1
fi

# Get the latest version (highest semver)
LATEST_VERSION=$(ls -1 "$PLUGIN_DIR" | sort -V | tail -1)

if [ -z "$LATEST_VERSION" ]; then
    echo "Error: No version directories found in $PLUGIN_DIR"
    exit 1
fi

TARGET_FILE="$PLUGIN_DIR/$LATEST_VERSION/scripts/$HOOK_FILE"

if [ ! -f "$TARGET_FILE" ]; then
    echo "Error: Hook file not found: $TARGET_FILE"
    exit 1
fi

echo "Patching claude-mem v$LATEST_VERSION..."

# Check if already patched
if grep -q 'process\.exit(d\.SUCCESS)' "$TARGET_FILE" 2>/dev/null; then
    echo "Already patched - no changes needed"
    exit 0
fi

# Check if the problematic pattern exists
if ! grep -q 'process\.exit(d\.USER_MESSAGE_ONLY)' "$TARGET_FILE" 2>/dev/null; then
    echo "Warning: Expected pattern not found - plugin may have changed"
    echo "Checking current exit pattern..."
    grep -o 'process\.exit([^)]*' "$TARGET_FILE" || echo "No exit patterns found"
    exit 1
fi

# Create backup
cp "$TARGET_FILE" "${TARGET_FILE}.backup"

# Apply patch: replace USER_MESSAGE_ONLY with SUCCESS
sed -i '' 's/process\.exit(d\.USER_MESSAGE_ONLY)/process.exit(d.SUCCESS)/g' "$TARGET_FILE"

# Verify patch
if grep -q 'process\.exit(d\.SUCCESS)' "$TARGET_FILE"; then
    echo "Patch applied successfully"
    echo "Backup saved: ${TARGET_FILE}.backup"

    # Test the patched script
    echo ""
    echo "Testing patched hook..."
    cd "$HOME/Projects/Thanos" 2>/dev/null || cd "$HOME"
    if "$TARGET_FILE" < /dev/null 2>/dev/null; then
        echo "Hook exits cleanly (code 0)"
    else
        EXIT_CODE=$?
        echo "Warning: Hook exit code is $EXIT_CODE"
    fi
else
    echo "Error: Patch verification failed"
    # Restore backup
    mv "${TARGET_FILE}.backup" "$TARGET_FILE"
    exit 1
fi

echo ""
echo "Done. Restart Claude Code to apply changes."
