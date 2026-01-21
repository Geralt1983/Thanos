#!/usr/bin/env bash
# Mobile Access Workflow
# Optimized for phone/tablet access with QR codes

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║          THANOS MOBILE ACCESS SETUP                ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if ttyd is running
if ! pgrep -f "ttyd" > /dev/null; then
    echo -e "${YELLOW}▶ Starting web terminal...${NC}"
    "$PROJECT_ROOT/Access/thanos-web" start
    sleep 2
fi

# Check if Tailscale is connected
TAILSCALE_CONNECTED=false
if command -v tailscale &> /dev/null; then
    if tailscale status --json 2>/dev/null | grep -q '"Running"'; then
        TAILSCALE_CONNECTED=true
    fi
fi

# Determine access URL
if [ "$TAILSCALE_CONNECTED" = true ]; then
    echo -e "${GREEN}✓ Tailscale VPN connected${NC}"
    ACCESS_URL=$("$PROJECT_ROOT/Access/thanos-access" urls | grep "tailscale_web" | awk '{print $2}')
    ACCESS_TYPE="Tailscale VPN (Secure Remote)"
else
    echo -e "${YELLOW}⚠ Using local network access${NC}"
    ACCESS_URL=$("$PROJECT_ROOT/Access/thanos-access" urls | grep "local_web" | awk '{print $2}')
    ACCESS_TYPE="Local Network (Same WiFi required)"
fi

if [ -z "$ACCESS_URL" ]; then
    echo -e "${RED}✗ Failed to get access URL${NC}"
    exit 1
fi

echo ""
echo -e "${CYAN}Access Type: ${ACCESS_TYPE}${NC}"
echo -e "${CYAN}URL: ${ACCESS_URL}${NC}"
echo ""

# Generate QR code if qrencode is available
if command -v qrencode &> /dev/null; then
    echo -e "${CYAN}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║              SCAN WITH YOUR PHONE                  ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
    echo ""
    qrencode -t ANSIUTF8 "$ACCESS_URL"
    echo ""
else
    echo -e "${YELLOW}Tip: Install qrencode for QR codes${NC}"
    echo -e "${YELLOW}     brew install qrencode${NC}"
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

# Mobile tips
echo -e "${CYAN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                  MOBILE TIPS                       ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  • Tap and hold to paste in the terminal"
echo "  • Swipe down to access special keys (Ctrl, Alt, Esc)"
echo "  • Landscape mode recommended for better view"
echo "  • Add to Home Screen for quick access"
echo ""

echo -e "${GREEN}✓ Mobile access ready!${NC}"
