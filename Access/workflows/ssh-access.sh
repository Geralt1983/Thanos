#!/usr/bin/env bash
# SSH Access Workflow
# Direct SSH and Tailscale SSH access

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
echo -e "${CYAN}║            THANOS SSH ACCESS INFO                  ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
echo ""

# Get hostname and user
HOSTNAME=$(hostname)
USER=$(whoami)

# Check Tailscale status
TAILSCALE_CONNECTED=false
TAILSCALE_IP=""
TAILSCALE_HOSTNAME=""

if command -v tailscale &> /dev/null; then
    if tailscale status --json 2>/dev/null | grep -q '"Running"'; then
        TAILSCALE_CONNECTED=true
        TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "")
        # Get MagicDNS hostname from status
        TAILSCALE_HOSTNAME=$(tailscale status --json 2>/dev/null | jq -r '.Self.HostName' 2>/dev/null || echo "")
    fi
fi

# Direct SSH
echo -e "${CYAN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║               DIRECT SSH ACCESS                    ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${GREEN}ssh ${USER}@${HOSTNAME}${NC}"
echo -e "  (Requires: Same network or port forwarding)"
echo ""

# Tailscale SSH
if [ "$TAILSCALE_CONNECTED" = true ]; then
    echo -e "${CYAN}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║          TAILSCALE VPN SSH (RECOMMENDED)          ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
    echo ""

    if [ -n "$TAILSCALE_HOSTNAME" ]; then
        echo -e "  ${GREEN}Via MagicDNS (Recommended):${NC}"
        echo -e "  ${CYAN}ssh ${USER}@${TAILSCALE_HOSTNAME}${NC}"
        echo ""
    fi

    if [ -n "$TAILSCALE_IP" ]; then
        echo -e "  ${GREEN}Via IP:${NC}"
        echo -e "  ${CYAN}ssh ${USER}@${TAILSCALE_IP}${NC}"
        echo ""
    fi

    echo -e "  ${GREEN}✓ Works from anywhere on your Tailscale network${NC}"
    echo -e "  ${GREEN}✓ No port forwarding needed${NC}"
    echo -e "  ${GREEN}✓ Encrypted by default${NC}"
    echo ""

else
    echo -e "${YELLOW}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║         TAILSCALE VPN NOT CONNECTED                ║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  Enable secure remote SSH access:"
    echo -e "  ${CYAN}thanos-vpn up${NC}"
    echo ""
fi

# SSH Configuration Tips
echo -e "${CYAN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                  SSH TIPS                          ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  ${GREEN}Quick Connect:${NC}"
echo "    Add to ~/.ssh/config on your client:"
echo ""
echo "    Host thanos"
if [ "$TAILSCALE_CONNECTED" = true ] && [ -n "$TAILSCALE_HOSTNAME" ]; then
    echo "      HostName ${TAILSCALE_HOSTNAME}"
else
    echo "      HostName ${HOSTNAME}"
fi
echo "      User ${USER}"
echo "      ForwardAgent yes"
echo ""
echo "    Then connect with: ${CYAN}ssh thanos${NC}"
echo ""

echo "  ${GREEN}Keep Alive:${NC}"
echo "    Add to ~/.ssh/config on your client:"
echo "      ServerAliveInterval 60"
echo "      ServerAliveCountMax 3"
echo ""

echo "  ${GREEN}SSH + tmux:${NC}"
echo "    ${CYAN}ssh ${USER}@${HOSTNAME} -t tmux attach -t thanos-main${NC}"
echo ""

echo -e "${GREEN}✓ SSH access information displayed${NC}"
