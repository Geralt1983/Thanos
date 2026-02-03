#!/bin/bash
# Google Chat Monitor - Captures chat window and analyzes for new messages

set -e

# Paths
WORKSPACE="/Users/jeremy/Projects/Thanos"
STATE_FILE="$WORKSPACE/data/google-chat-state.json"
SCREENSHOT_DIR="$WORKSPACE/data/screenshots/google-chat"
LOG_FILE="$WORKSPACE/logs/google-chat-monitor.log"

# Create directories
mkdir -p "$(dirname "$STATE_FILE")" "$SCREENSHOT_DIR" "$(dirname "$LOG_FILE")"

# Log function
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting Google Chat monitoring..."

# Check if Safari with Google Chat is open
if ! peekaboo list windows --app Safari 2>/dev/null | grep -q "Chat"; then
  log "Google Chat window not found in Safari. Skipping."
  exit 0
fi

# Bring Safari Chat window to front
open -a Safari 2>/dev/null
sleep 1
peekaboo window focus --app Safari --window-title "Chat" 2>/dev/null || true
sleep 1

# Capture timestamp
TIMESTAMP=$(date +%s)
SCREENSHOT_PATH="$SCREENSHOT_DIR/chat-$TIMESTAMP.png"

# Capture Google Chat window
log "Capturing Google Chat window..."
if ! peekaboo image --app Safari --window-title "Chat" --path "$SCREENSHOT_PATH" --retina 2>/dev/null; then
  log "Failed to capture window"
  exit 1
fi

# Analyze for new messages
log "Analyzing screenshot..."
ANALYSIS=$(peekaboo see --path "$SCREENSHOT_PATH" --analyze "List any unread messages, new notifications, or chat activity visible. If nothing new, say 'No new activity'. Be concise." --json 2>/dev/null || echo '{"analysis":"Error analyzing"}')

RESULT=$(echo "$ANALYSIS" | jq -r '.analysis // .result // "Unknown"')

log "Analysis result: $RESULT"

# Load previous state
if [ -f "$STATE_FILE" ]; then
  LAST_RESULT=$(jq -r '.lastAnalysis // "none"' "$STATE_FILE")
else
  LAST_RESULT="none"
fi

# Compare with previous
if [ "$RESULT" != "$LAST_RESULT" ] && [ "$RESULT" != "No new activity" ]; then
  log "New activity detected!"
  
  # Save state
  jq -n \
    --arg ts "$TIMESTAMP" \
    --arg analysis "$RESULT" \
    --arg screenshot "$SCREENSHOT_PATH" \
    '{lastCheck: $ts, lastAnalysis: $analysis, lastScreenshot: $screenshot}' \
    > "$STATE_FILE"
  
  # Notify via Telegram
  MESSAGE="🗨️ **Google Chat Activity**\n\n$RESULT\n\nScreenshot: $SCREENSHOT_PATH"
  
  curl -s -X POST "http://localhost:18789/api/message/send" \
    -H "Authorization: Bearer 71d632f95e9c08ade4dfe00bd841a860f2025e98286827ef" \
    -H "Content-Type: application/json" \
    -d "{\"channel\":\"telegram\",\"to\":\"6135558908\",\"message\":\"$MESSAGE\"}" \
    > /dev/null 2>&1 || log "Failed to send Telegram notification"
  
else
  log "No new activity"
  
  # Update state anyway
  jq -n \
    --arg ts "$TIMESTAMP" \
    --arg analysis "$RESULT" \
    --arg screenshot "$SCREENSHOT_PATH" \
    '{lastCheck: $ts, lastAnalysis: $analysis, lastScreenshot: $screenshot}' \
    > "$STATE_FILE"
fi

# Cleanup old screenshots (keep last 50)
ls -t "$SCREENSHOT_DIR"/chat-*.png 2>/dev/null | tail -n +51 | xargs rm -f 2>/dev/null || true

log "Google Chat monitoring complete"
