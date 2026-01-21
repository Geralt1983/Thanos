#!/usr/bin/env bash
# Emergency Access Workflow
# Minimal dependencies - for when things go wrong

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${RED}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║              EMERGENCY ACCESS MODE                 ║${NC}"
echo -e "${RED}╚════════════════════════════════════════════════════╝${NC}"
echo ""

HOSTNAME=$(hostname)
USER=$(whoami)

# Diagnostic Information
echo -e "${CYAN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║              SYSTEM INFORMATION                    ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  Hostname: ${HOSTNAME}"
echo "  User: ${USER}"
echo "  Current Dir: $(pwd)"
echo "  TTY: $(tty 2>/dev/null || echo 'none')"
echo ""

# Check what's available
echo -e "${CYAN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║            AVAILABLE TOOLS                         ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
echo ""

TMUX_AVAIL=false
TTYD_AVAIL=false
TAILSCALE_AVAIL=false

if command -v tmux &> /dev/null; then
    echo -e "  ${GREEN}✓ tmux${NC}"
    TMUX_AVAIL=true
else
    echo -e "  ${RED}✗ tmux${NC}"
fi

if command -v ttyd &> /dev/null; then
    echo -e "  ${GREEN}✓ ttyd${NC}"
    TTYD_AVAIL=true
else
    echo -e "  ${RED}✗ ttyd${NC}"
fi

if command -v tailscale &> /dev/null; then
    echo -e "  ${GREEN}✓ tailscale${NC}"
    TAILSCALE_AVAIL=true
else
    echo -e "  ${RED}✗ tailscale${NC}"
fi

echo ""

# Running processes
echo -e "${CYAN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║            RUNNING PROCESSES                       ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
echo ""

if pgrep -f ttyd > /dev/null; then
    echo -e "  ${GREEN}✓ ttyd running${NC}"
    TTYD_PID=$(pgrep -f ttyd)
    echo "    PID: $TTYD_PID"
    echo "    Port: 7681 (likely)"
else
    echo -e "  ${RED}✗ ttyd not running${NC}"
fi

if [ "$TMUX_AVAIL" = true ]; then
    SESSIONS=$(tmux list-sessions 2>/dev/null || echo "")
    if [ -n "$SESSIONS" ]; then
        echo -e "  ${GREEN}✓ tmux sessions running${NC}"
        echo "$SESSIONS" | while IFS= read -r line; do
            echo "    - $(echo "$line" | cut -d: -f1)"
        done
    else
        echo -e "  ${RED}✗ No tmux sessions${NC}"
    fi
fi

echo ""

# Emergency Access Methods
echo -e "${CYAN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║          EMERGENCY ACCESS METHODS                  ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${GREEN}1. Direct SSH (Always Available):${NC}"
echo "   ${CYAN}ssh ${USER}@${HOSTNAME}${NC}"
echo ""

if [ "$TMUX_AVAIL" = true ]; then
    echo -e "${GREEN}2. Local tmux:${NC}"
    echo "   ${CYAN}tmux attach -t thanos-main${NC}"
    echo "   Or create new: ${CYAN}tmux new -s thanos-main${NC}"
    echo ""
fi

if [ "$TTYD_AVAIL" = true ]; then
    echo -e "${GREEN}3. Manual ttyd (if not running):${NC}"
    echo "   ${CYAN}ttyd -p 7681 bash${NC}"
    echo "   Then visit: http://localhost:7681"
    echo ""
fi

echo -e "${GREEN}4. Direct shell:${NC}"
echo "   You're already here!"
echo ""

# Recovery Commands
echo -e "${CYAN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║             RECOVERY COMMANDS                      ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}Kill all daemons:${NC}"
echo "  ${CYAN}pkill ttyd${NC}"
echo "  ${CYAN}pkill -f thanos${NC}"
echo ""

echo -e "${YELLOW}Check processes:${NC}"
echo "  ${CYAN}ps aux | grep ttyd${NC}"
echo "  ${CYAN}ps aux | grep tmux${NC}"
echo ""

echo -e "${YELLOW}View logs:${NC}"
echo "  ${CYAN}tail -f logs/ttyd.log${NC}"
echo "  ${CYAN}tail -f logs/tailscale.log${NC}"
echo "  ${CYAN}tail -f logs/access_coordinator.log${NC}"
echo ""

echo -e "${YELLOW}Check ports:${NC}"
echo "  ${CYAN}lsof -i :7681${NC}  # ttyd port"
echo "  ${CYAN}netstat -an | grep LISTEN${NC}"
echo ""

echo -e "${YELLOW}Restart services:${NC}"
echo "  ${CYAN}Access/thanos-web restart${NC}"
echo "  ${CYAN}Access/thanos-tmux${NC}"
echo "  ${CYAN}Access/thanos-vpn up${NC}"
echo ""

# Nuclear Options
echo -e "${RED}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║              NUCLEAR OPTIONS                       ║${NC}"
echo -e "${RED}╚════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${RED}Complete reset (use with caution):${NC}"
echo "  ${CYAN}pkill -9 ttyd tmux${NC}                 # Kill everything"
echo "  ${CYAN}rm State/*.pid State/*.json${NC}       # Clear state"
echo "  ${CYAN}Access/thanos-web start${NC}           # Fresh start"
echo ""

echo -e "${RED}Remove all config (last resort):${NC}"
echo "  ${CYAN}rm -rf Access/config/${NC}             # Remove all configs"
echo "  ${CYAN}rm -rf State/${NC}                     # Clear all state"
echo "  ${CYAN}Access/install_ttyd.sh${NC}            # Reinstall"
echo ""

# Quick Actions
echo -e "${CYAN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║              QUICK ACTIONS                         ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
echo ""

read -p "Kill all daemons and restart? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Killing all daemons...${NC}"
    pkill ttyd 2>/dev/null || true
    sleep 1

    echo -e "${YELLOW}Starting fresh...${NC}"
    if [ -f "Access/thanos-web" ]; then
        Access/thanos-web start
        echo -e "${GREEN}✓ Web terminal restarted${NC}"
    fi

    if [ "$TMUX_AVAIL" = true ]; then
        if ! tmux has-session -t thanos-main 2>/dev/null; then
            tmux new-session -d -s thanos-main
            echo -e "${GREEN}✓ tmux session created${NC}"
        fi
    fi

    echo ""
    echo -e "${GREEN}Recovery complete!${NC}"
    echo ""
    echo "Check status: ${CYAN}Access/thanos-access status${NC}"
fi

echo ""
echo -e "${YELLOW}Emergency access information displayed.${NC}"
