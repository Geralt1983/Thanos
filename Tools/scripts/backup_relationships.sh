#!/bin/bash
# Automated backup script for relationships.db
# Run daily via cron: 0 0 * * * /path/to/backup_relationships.sh

THANOS_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
DB_PATH="$THANOS_DIR/State/relationships.db"
BACKUP_DIR="$THANOS_DIR/State/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory if needed
mkdir -p "$BACKUP_DIR"

# Create backup
cp "$DB_PATH" "$BACKUP_DIR/relationships_${TIMESTAMP}.db"

# Keep only last 7 backups
ls -t "$BACKUP_DIR"/relationships_*.db 2>/dev/null | tail -n +8 | xargs -r rm

echo "Backup created: relationships_${TIMESTAMP}.db"
echo "Backups retained: $(ls "$BACKUP_DIR"/relationships_*.db 2>/dev/null | wc -l)"
