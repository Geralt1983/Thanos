#!/bin/bash
# Install cron job for automated daily memory backups
# Runs backup_memory.sh daily at 2am with logging

set -euo pipefail

THANOS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_SCRIPT="$THANOS_DIR/scripts/backup_memory.sh"
LOG_DIR="$THANOS_DIR/backups"
LOG_FILE="$LOG_DIR/backup.log"

# Colors for output
PURPLE='\033[0;35m'
GOLD='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${PURPLE}"
cat << 'EOF'
╔════════════════════════════════════════╗
║   THANOS MEMORY BACKUP SCHEDULER       ║
║   Daily automated backups at 2am       ║
╚════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Check if backup script exists
if [ ! -f "$BACKUP_SCRIPT" ]; then
    echo -e "${RED}Error: Backup script not found at $BACKUP_SCRIPT${NC}"
    exit 1
fi

# Ensure backup script is executable
chmod +x "$BACKUP_SCRIPT"

# Create log directory if needed
mkdir -p "$LOG_DIR"

# Cron job entry
CRON_JOB="0 2 * * * $BACKUP_SCRIPT >> $LOG_FILE 2>&1"
CRON_COMMENT="# Thanos Memory Backup - Daily at 2am"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$BACKUP_SCRIPT"; then
    echo -e "${GOLD}Cron job already exists. Updating...${NC}"
    # Remove old entry
    crontab -l 2>/dev/null | grep -v "$BACKUP_SCRIPT" | crontab -
fi

# Add new cron job
echo -e "${GOLD}Installing cron job...${NC}"
(crontab -l 2>/dev/null; echo "$CRON_COMMENT"; echo "$CRON_JOB") | crontab -

# Verify installation
if crontab -l 2>/dev/null | grep -q "$BACKUP_SCRIPT"; then
    echo ""
    echo -e "${GREEN}✓ Cron job installed successfully${NC}"
    echo ""
    echo -e "${GOLD}Configuration:${NC}"
    echo "  Schedule: Daily at 2:00 AM"
    echo "  Script: $BACKUP_SCRIPT"
    echo "  Log: $LOG_FILE"
    echo ""
    echo -e "${GOLD}Current crontab:${NC}"
    crontab -l | grep -A1 "Thanos Memory Backup"
    echo ""
    echo -e "${GOLD}Commands:${NC}"
    echo "  crontab -l              - List all cron jobs"
    echo "  crontab -e              - Edit cron jobs"
    echo "  tail -f $LOG_FILE  - Watch backup logs"
    echo "  bash $BACKUP_SCRIPT     - Run backup manually"
    echo ""
    echo -e "${GOLD}To uninstall:${NC}"
    echo "  crontab -l | grep -v '$BACKUP_SCRIPT' | crontab -"
    echo ""
else
    echo -e "${RED}Error: Failed to install cron job${NC}"
    exit 1
fi
