#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/openai_file_search_sync.log"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
SYNC_CMD="cd $ROOT_DIR && $PYTHON_BIN Tools/openai_file_search.py sync-drive --ensure-folders >> $LOG_FILE 2>&1"

CRON_COMMENT="# Thanos OpenAI File Search Drive Sync"
CRON_JOB="*/30 * * * * $SYNC_CMD"

mkdir -p "$LOG_DIR"

# Remove existing job if present
if crontab -l 2>/dev/null | grep -q "$CRON_COMMENT"; then
  crontab -l 2>/dev/null | grep -v "$CRON_COMMENT" | grep -v "openai_file_search.py sync-drive" | crontab -
fi

# Install new cron job
(crontab -l 2>/dev/null; echo "$CRON_COMMENT"; echo "$CRON_JOB") | crontab -

echo "Installed cron job:"
echo "$CRON_COMMENT"
echo "$CRON_JOB"
