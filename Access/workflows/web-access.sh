#!/usr/bin/env bash
# Web Access Workflow
# Browser-based terminal access

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║           THANOS WEB ACCESS SETUP                  ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
echo ""

# Ensure ttyd is running
if ! pgrep -f "ttyd" > /dev/null; then
    echo -e "${YELLOW}▶ Starting web terminal...${NC}"
    "$PROJECT_ROOT/Access/thanos-web" start
    sleep 2

    if ! pgrep -f "ttyd" > /dev/null; then
        echo -e "${RED}✗ Failed to start web terminal${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✓ Web terminal running${NC}"
echo ""

# Get access URLs
LOCAL_URL=$("$PROJECT_ROOT/Access/thanos-access" urls | grep "local_web" | awk '{print $2}' || echo "")
TAILSCALE_URL=$("$PROJECT_ROOT/Access/thanos-access" urls | grep "tailscale_web" | awk '{print $2}' || echo "")

# Show URLs
echo -e "${CYAN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                  ACCESS URLS                       ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
echo ""

if [ -n "$LOCAL_URL" ]; then
    echo -e "${GREEN}Local Network:${NC}"
    echo -e "  ${CYAN}${LOCAL_URL}${NC}"
    echo -e "  (Works on same WiFi/network)"
    echo ""
fi

if [ -n "$TAILSCALE_URL" ]; then
    echo -e "${GREEN}Tailscale VPN (Recommended):${NC}"
    echo -e "  ${CYAN}${TAILSCALE_URL}${NC}"
    echo -e "  (Works from anywhere on your Tailscale network)"
    echo ""
fi

# Show credentials
CREDS_FILE="$PROJECT_ROOT/Access/config/ttyd-credentials.json"
if [ -f "$CREDS_FILE" ]; then
    USERNAME=$(jq -r '.username' "$CREDS_FILE")
    PASSWORD=$(jq -r '.password' "$CREDS_FILE")

    echo -e "${CYAN}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                  CREDENTIALS                       ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  Username: ${GREEN}${USERNAME}${NC}"
    echo -e "  Password: ${GREEN}${PASSWORD}${NC}"
    echo ""
fi

# Browser tips
echo -e "${CYAN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                  BROWSER TIPS                      ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  • Use Chrome/Firefox for best experience"
echo "  • Ctrl+Shift+C / Cmd+Shift+C to copy"
echo "  • Ctrl+Shift+V / Cmd+Shift+V to paste"
echo "  • F11 for fullscreen mode"
echo "  • Bookmark the URL for quick access"
echo ""

# Offer to open browser
if [ -n "$LOCAL_URL" ]; then
    read -p "Open in browser? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if command -v open &> /dev/null; then
            # macOS
            open "$LOCAL_URL"
        elif command -v xdg-open &> /dev/null; then
            # Linux
            xdg-open "$LOCAL_URL"
        else
            echo -e "${YELLOW}Could not auto-open browser. Please visit URL manually.${NC}"
        fi
    fi
fi

echo -e "${GREEN}✓ Web access ready!${NC}"
