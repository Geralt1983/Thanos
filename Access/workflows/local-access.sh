#!/usr/bin/env bash
# Local Access Workflow
# Direct local terminal access via tmux

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
echo -e "${CYAN}║         THANOS LOCAL TERMINAL ACCESS               ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo -e "${RED}✗ tmux is not installed${NC}"
    echo ""
    echo "Install tmux:"
    echo "  ${CYAN}brew install tmux${NC}"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ tmux is installed${NC}"
echo ""

# Check for existing sessions
SESSIONS=$(tmux list-sessions 2>/dev/null || echo "")

if echo "$SESSIONS" | grep -q "thanos-main"; then
    echo -e "${GREEN}✓ thanos-main session is running${NC}"
    echo ""

    # Show session info
    echo -e "${CYAN}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                SESSION STATUS                      ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
    echo ""
    tmux display-message -p -t thanos-main "  Created: #{session_created_string}"
    tmux display-message -p -t thanos-main "  Windows: #{session_windows}"
    tmux display-message -p -t thanos-main "  Attached: #{session_attached}"
    echo ""

    # Attach option
    echo -e "${CYAN}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                  ATTACH NOW                        ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "  Option 1 (Quick): ${CYAN}thanos-tmux${NC}"
    echo "  Option 2 (Direct): ${CYAN}tmux attach -t thanos-main${NC}"
    echo ""

    read -p "Attach now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        exec tmux attach -t thanos-main
    fi

else
    echo -e "${YELLOW}⚠ No thanos-main session found${NC}"
    echo ""

    # Create option
    echo -e "${CYAN}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║             CREATE NEW SESSION                     ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "  ${CYAN}thanos-tmux${NC} - Create and attach to thanos-main"
    echo ""

    read -p "Create session now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        exec "$PROJECT_ROOT/Access/thanos-tmux"
    fi
fi

# Show other sessions
if [ -n "$SESSIONS" ]; then
    OTHER_SESSIONS=$(echo "$SESSIONS" | grep -v "thanos-main" || echo "")
    if [ -n "$OTHER_SESSIONS" ]; then
        echo -e "${CYAN}╔════════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║               OTHER SESSIONS                       ║${NC}"
        echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo "$OTHER_SESSIONS" | while IFS= read -r line; do
            SESSION_NAME=$(echo "$line" | cut -d: -f1)
            echo "  - ${SESSION_NAME}"
            echo "    ${CYAN}tmux attach -t ${SESSION_NAME}${NC}"
        done
        echo ""
    fi
fi

# Tmux tips
echo -e "${CYAN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                  TMUX TIPS                         ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  ${GREEN}Quick Keys (Prefix: Ctrl-b):${NC}"
echo "    c         - Create new window"
echo "    n/p       - Next/Previous window"
echo "    d         - Detach session"
echo "    [         - Enter copy mode (scroll/search)"
echo "    ?         - Show all keybindings"
echo ""
echo "  ${GREEN}Session Management:${NC}"
echo "    ${CYAN}tmux ls${NC}                    - List sessions"
echo "    ${CYAN}tmux attach -t <name>${NC}      - Attach to session"
echo "    ${CYAN}tmux kill-session -t <name>${NC} - Kill session"
echo ""

echo -e "${GREEN}✓ Local access ready!${NC}"
