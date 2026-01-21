#!/bin/bash
# Install Thanos ttyd LaunchAgent for auto-start on boot

set -euo pipefail

PLIST_SOURCE="$HOME/Projects/Thanos/Access/LaunchAgent/com.thanos.ttyd.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.thanos.ttyd.plist"

PURPLE='\033[0;35m'
GOLD='\033[1;33m'
NC='\033[0m'

echo -e "${PURPLE}"
cat << 'EOF'
╔════════════════════════════════════════╗
║   THANOS LAUNCHAGENT INSTALLER         ║
║   Auto-start ttyd on boot              ║
╚════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Check if LaunchAgents directory exists
mkdir -p "$HOME/Library/LaunchAgents"

# Unload existing LaunchAgent if running
if launchctl list | grep -q "com.thanos.ttyd"; then
    echo -e "${GOLD}Unloading existing LaunchAgent...${NC}"
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi

# Copy plist to LaunchAgents
echo -e "${GOLD}Installing LaunchAgent...${NC}"
cp "$PLIST_SOURCE" "$PLIST_DEST"

# Load LaunchAgent
echo -e "${GOLD}Loading LaunchAgent...${NC}"
launchctl load "$PLIST_DEST"

echo ""
echo -e "${GOLD}✓ LaunchAgent installed successfully${NC}"
echo ""
echo "ttyd will now start automatically on boot."
echo ""
echo "Commands:"
echo "  launchctl start com.thanos.ttyd   - Start now"
echo "  launchctl stop com.thanos.ttyd    - Stop"
echo "  launchctl unload $PLIST_DEST - Uninstall"
