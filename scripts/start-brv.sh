#!/bin/bash
# Auto-start ByteRover CLI (headless-first)
# Called by launchd at login

cd /Users/jeremy/Projects/Thanos

LOG_FILE="logs/brv-startup.log"
export BRV_FORCE_FILE_TOKEN_STORE=1

# Prefer headless mode (ByteRover CLI >= 1.6.0). Fallback to legacy TTY shim if unsupported.
HEADLESS_TMP="$(mktemp -t brv_headless_status.XXXXXX)"
if brv status --headless >"$HEADLESS_TMP" 2>&1; then
    if grep -q "Logged in" "$HEADLESS_TMP"; then
        echo "[$(date)] ByteRover headless status: logged in" >> "$LOG_FILE"
        rm -f "$HEADLESS_TMP"
        exit 0
    fi

    if grep -q "Not logged in" "$HEADLESS_TMP"; then
        echo "[$(date)] ByteRover headless status: not logged in; trying TTY shim" >> "$LOG_FILE"
        rm -f "$HEADLESS_TMP"
        # Fall through to legacy shim to support keychain-based sessions.
    fi

    echo "[$(date)] ByteRover headless status: unexpected output; falling back to TTY shim" >> "$LOG_FILE"
fi

# Headless failed or unsupported. Fall back to legacy behavior.
if grep -q "headless" "$HEADLESS_TMP"; then
    echo "[$(date)] Headless flag unsupported; falling back to TTY shim" >> "$LOG_FILE"
else
    echo "[$(date)] Headless status failed; falling back to TTY shim" >> "$LOG_FILE"
fi
rm -f "$HEADLESS_TMP"

# Start brv in background via expect or screen
# brv requires interactive terminal, so we use script to fake it
script -q /dev/null brv quit &

# Wait a moment for startup
sleep 2

# Verify
if brv status 2>&1 | grep -q "Status: Logged in"; then
    echo "[$(date)] ByteRover MCP started successfully" >> "$LOG_FILE"
else
    echo "[$(date)] Failed to start ByteRover MCP" >> "$LOG_FILE"
    exit 1
fi
