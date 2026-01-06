#!/bin/bash
# Life OS Session Start Hook
# Outputs context for Claude at session start

CLAUDE_DIR="$HOME/.claude"

echo "═══════════════════════════════════════"
echo "         LIFE OS SESSION START          "
echo "═══════════════════════════════════════"
echo ""

# Check inbox for new items
INBOX_DIR="$CLAUDE_DIR/Inbox"
if [ -d "$INBOX_DIR" ]; then
  INBOX_COUNT=$(find "$INBOX_DIR" -type f -not -name ".*" 2>/dev/null | wc -l | tr -d ' ')
  if [ "$INBOX_COUNT" -gt 0 ]; then
    echo "📥 INBOX: $INBOX_COUNT items waiting to process"
    find "$INBOX_DIR" -type f -not -name ".*" -exec basename {} \; 2>/dev/null | head -5 | while read item; do
      echo "   - $item"
    done
    echo ""
  fi
fi

# Show current focus
if [ -f "$CLAUDE_DIR/State/CurrentFocus.md" ]; then
  echo "📋 CURRENT FOCUS:"
  # Extract "Right Now" section
  awk '/^## Right Now/,/^##/' "$CLAUDE_DIR/State/CurrentFocus.md" | head -10 | tail -n +2
  echo ""
fi

# Show today's priorities
if [ -f "$CLAUDE_DIR/State/Today.md" ]; then
  echo "✅ TODAY:"
  head -15 "$CLAUDE_DIR/State/Today.md" | grep -E "^- \[" | head -5
  echo ""
fi

# Check for due commitments (within 48 hours)
if [ -f "$CLAUDE_DIR/State/Commitments.md" ]; then
  # Find lines with "today" or "tomorrow" or dates within 48 hours
  DUE=$(grep -iE "today|tomorrow" "$CLAUDE_DIR/State/Commitments.md" 2>/dev/null | head -5)
  if [ -n "$DUE" ]; then
    echo "⚠️  DUE SOON:"
    echo "$DUE"
    echo ""
  fi
fi

# This week's focus
if [ -f "$CLAUDE_DIR/State/ThisWeek.md" ]; then
  echo "📅 THIS WEEK:"
  head -10 "$CLAUDE_DIR/State/ThisWeek.md" | grep -E "^- |^##" | head -5
  echo ""
fi

echo "═══════════════════════════════════════"
echo ""
echo "To see full Life OS context, say: '/pa:daily'"
echo ""

exit 0
