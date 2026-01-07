#!/bin/bash
# Thanos Journaling System - Terminal-native journaling

JOURNAL_DIR="$HOME/.claude/Journal"
TIMESTAMP=$(date '+%Y-%m-%d-%H%M')
DATE=$(date '+%Y-%m-%d')

# Ensure journal directory exists
mkdir -p "$JOURNAL_DIR"

case "$1" in
    "")
        # Interactive journal entry
        echo "=== Thanos Journal ==="
        echo "Type your entry (Ctrl+D when done):"
        echo ""

        ENTRY=$(cat)

        if [[ -n "$ENTRY" ]]; then
            FILENAME="$JOURNAL_DIR/${TIMESTAMP}.md"
            cat > "$FILENAME" << EOF
# Journal Entry - $TIMESTAMP

$ENTRY

---
*Captured via Thanos*
EOF
            echo "✓ Journal entry saved: $FILENAME"
        else
            echo "No entry provided."
            exit 1
        fi
        ;;

    "morning"|"evening"|"work"|"personal")
        # Session-based entry
        SESSION_TYPE="$1"
        FILENAME="$JOURNAL_DIR/${DATE}-${SESSION_TYPE}.md"

        echo "=== ${SESSION_TYPE^^} Journal Session ==="
        echo "Type your entry (Ctrl+D when done):"
        echo ""

        ENTRY=$(cat)

        if [[ -n "$ENTRY" ]]; then
            cat > "$FILENAME" << EOF
# ${SESSION_TYPE^^} Journal - $DATE

$ENTRY

---
*Session: ${SESSION_TYPE} | Time: $(date '+%H:%M')*
EOF
            echo "✓ ${SESSION_TYPE} journal saved: $FILENAME"
        else
            echo "No entry provided."
            exit 1
        fi
        ;;

    "review")
        # Review journal entries
        TARGET_DATE="${2:-$DATE}"

        if [[ "$TARGET_DATE" == "today" ]]; then
            TARGET_DATE="$DATE"
        elif [[ "$TARGET_DATE" == "yesterday" ]]; then
            TARGET_DATE=$(date -v-1d '+%Y-%m-%d')
        fi

        echo "=== Journal Entries for $TARGET_DATE ==="
        echo ""

        ENTRIES=$(find "$JOURNAL_DIR" -name "${TARGET_DATE}*.md" -type f | sort)

        if [[ -z "$ENTRIES" ]]; then
            echo "No entries found for $TARGET_DATE"
            exit 0
        fi

        for entry in $ENTRIES; do
            echo "--- $(basename "$entry") ---"
            cat "$entry"
            echo ""
        done
        ;;

    "search")
        # Search journal entries
        if [[ -z "$2" ]]; then
            echo "Usage: thanos journal search <keyword>"
            exit 1
        fi

        KEYWORD="$2"
        echo "=== Searching for: $KEYWORD ==="
        echo ""

        grep -r -i "$KEYWORD" "$JOURNAL_DIR" --include="*.md" -H -n
        ;;

    "list")
        # List all journal entries
        echo "=== All Journal Entries ==="
        find "$JOURNAL_DIR" -name "*.md" -type f | sort -r | head -20
        ;;

    *)
        # Quick single-line entry
        ENTRY="$*"
        FILENAME="$JOURNAL_DIR/${TIMESTAMP}.md"

        cat > "$FILENAME" << EOF
# Journal Entry - $TIMESTAMP

$ENTRY

---
*Quick capture via Thanos*
EOF
        echo "✓ Journal entry saved: $FILENAME"
        ;;
esac

exit 0
