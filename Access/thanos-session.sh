#!/bin/bash
# Thanos tmux session manager
# Ubiquitous Access Layer - persistent terminal sessions

set -euo pipefail

SESSION_NAME="thanos"
PROJECT_ROOT="$HOME/Projects/Thanos"

# Color codes for Thanos aesthetic
PURPLE='\033[0;35m'
GOLD='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${PURPLE}"
cat << 'EOF'
╔════════════════════════════════════════╗
║   THANOS SESSION ORCHESTRATOR          ║
║   Reality bends to tmux                ║
╚════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo "Error: tmux not installed. Install with: brew install tmux"
    exit 1
fi

# Create or attach to session
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo -e "${GOLD}Attaching to existing Thanos session...${NC}"
    tmux attach-session -t "$SESSION_NAME"
else
    echo -e "${GOLD}Creating new Thanos session...${NC}"

    # Create session with main window
    tmux new-session -d -s "$SESSION_NAME" -n "main" -c "$PROJECT_ROOT"

    # Window 1: Main Thanos CLI
    tmux send-keys -t "$SESSION_NAME:main" "clear" C-m
    tmux send-keys -t "$SESSION_NAME:main" "echo '### DESTINY // tmux session initialized'" C-m
    tmux send-keys -t "$SESSION_NAME:main" "echo ''" C-m
    tmux send-keys -t "$SESSION_NAME:main" "./Tools/thanos-claude" C-m

    # Window 2: Logs (operator, telegram, system)
    tmux new-window -t "$SESSION_NAME" -n "logs" -c "$PROJECT_ROOT/logs"
    tmux send-keys -t "$SESSION_NAME:logs" "clear && echo '### DESTINY // Log surveillance active'" C-m
    tmux send-keys -t "$SESSION_NAME:logs" "echo '' && echo 'Available logs:'" C-m
    tmux send-keys -t "$SESSION_NAME:logs" "ls -lh *.log 2>/dev/null || echo 'No logs yet'" C-m

    # Window 3: State (CurrentFocus, TimeState, visual state)
    tmux new-window -t "$SESSION_NAME" -n "state" -c "$PROJECT_ROOT/State"
    tmux send-keys -t "$SESSION_NAME:state" "clear && echo '### DESTINY // State monitoring'" C-m
    tmux send-keys -t "$SESSION_NAME:state" "echo ''" C-m
    tmux send-keys -t "$SESSION_NAME:state" "cat CurrentFocus.md 2>/dev/null || echo 'Focus not set'" C-m

    # Window 4: Tools (quick access to utilities)
    tmux new-window -t "$SESSION_NAME" -n "tools" -c "$PROJECT_ROOT/Tools"
    tmux send-keys -t "$SESSION_NAME:tools" "clear && echo '### DESTINY // Tools arsenal'" C-m
    tmux send-keys -t "$SESSION_NAME:tools" "echo ''" C-m
    tmux send-keys -t "$SESSION_NAME:tools" "echo 'Available tools:'" C-m
    tmux send-keys -t "$SESSION_NAME:tools" "ls -1 *.py *.sh 2>/dev/null | head -20" C-m

    # Configure status bar with Thanos aesthetic
    tmux set-option -t "$SESSION_NAME" status-style "bg=#1a1a2e,fg=#9775fa"
    tmux set-option -t "$SESSION_NAME" status-left "#[bg=#9775fa,fg=#1a1a2e,bold] THANOS #[bg=#1a1a2e,fg=#9775fa] "
    tmux set-option -t "$SESSION_NAME" status-right "#[fg=#9775fa]%H:%M #[fg=#6272a4]│ #[fg=#9775fa]%Y-%m-%d "
    tmux set-option -t "$SESSION_NAME" window-status-current-style "bg=#9775fa,fg=#1a1a2e,bold"

    # Select main window and attach
    tmux select-window -t "$SESSION_NAME:main"

    echo -e "${GOLD}Session created. Attaching...${NC}"
    sleep 1
    tmux attach-session -t "$SESSION_NAME"
fi
