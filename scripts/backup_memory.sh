#!/bin/bash
# Automated backup script for Thanos Memory V2
# Run daily via cron: 0 2 * * * /path/to/backup_memory.sh

THANOS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="$THANOS_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/memory_${TIMESTAMP}"

# Create backup directory if needed
mkdir -p "$BACKUP_DIR"

# Run memory export using the memory_export.py tool
echo "Starting memory backup at $(date)"
cd "$THANOS_DIR"

# Add user site-packages to PYTHONPATH for dependencies installed with --user
USER_SITE=$(python3 -c "import site; print(site.USER_SITE)" 2>/dev/null)
if [ -n "$USER_SITE" ]; then
    export PYTHONPATH="$USER_SITE:$PYTHONPATH"
fi

python3 Tools/memory_export.py --format json --output "$BACKUP_PATH"

if [ $? -ne 0 ]; then
    echo "Error: Memory backup failed"
    exit 1
fi

echo "Backup created: memory_${TIMESTAMP}"

# Retention policy: Keep last 7 daily backups + 4 weekly backups
# Daily backups: Keep all backups from last 7 days
SEVEN_DAYS_AGO=$(date -v-7d +%Y%m%d 2>/dev/null || date -d "7 days ago" +%Y%m%d)

# Weekly backups: Keep one backup per week for last 4 weeks (every Sunday)
# Mark Sunday backups as weekly keepers
WEEKLY_KEEPERS=()
for i in {1..4}; do
    SUNDAY=$(date -v-${i}w -v1w +%Y%m%d 2>/dev/null || date -d "$((i)) weeks ago sunday" +%Y%m%d)
    WEEKLY_KEEPERS+=("$SUNDAY")
done

# Get all backup directories
ALL_BACKUPS=($(ls -d "$BACKUP_DIR"/memory_* 2>/dev/null | sort))

# Delete old backups that don't match retention policy
for backup in "${ALL_BACKUPS[@]}"; do
    backup_name=$(basename "$backup")
    backup_date=${backup_name#memory_}
    backup_date=${backup_date:0:8}  # Extract YYYYMMDD

    # Keep if within last 7 days
    if [ "$backup_date" -ge "$SEVEN_DAYS_AGO" ]; then
        continue
    fi

    # Keep if it's a weekly backup (Sunday)
    keep_weekly=false
    for weekly_date in "${WEEKLY_KEEPERS[@]}"; do
        if [ "$backup_date" = "$weekly_date" ]; then
            keep_weekly=true
            break
        fi
    done

    if [ "$keep_weekly" = true ]; then
        continue
    fi

    # Delete if it doesn't match retention criteria
    echo "Removing old backup: $backup_name"
    rm -rf "$backup"
done

# Count remaining backups
BACKUP_COUNT=$(ls -d "$BACKUP_DIR"/memory_* 2>/dev/null | wc -l)
echo "Backups retained: $BACKUP_COUNT"
echo "Backup complete at $(date)"
