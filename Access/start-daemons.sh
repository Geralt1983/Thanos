#!/bin/bash
# Start all Thanos daemons in tmux monitor session
#
# This creates a dedicated tmux session for background daemons with
# separate windows for each daemon, making monitoring and debugging easy.
#
# Usage:
#   ./Access/start-daemons.sh
#
# Then attach with:
#   thanos-tmux monitor

set -e

THANOS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SESSION="thanos-monitor"

echo "Starting Thanos daemons in tmux session: $SESSION"
echo "================================================"

# Check if tmux is available
if ! command -v tmux &> /dev/null; then
    echo "Error: tmux is not installed"
    echo "Install with: brew install tmux"
    exit 1
fi

# Create monitor session if it doesn't exist
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "Creating new session: $SESSION"
    tmux new-session -d -s "$SESSION" -c "$THANOS_ROOT" -n "status"
    tmux send-keys -t "$SESSION:status" "echo 'Thanos Daemon Monitor'; echo ''; echo 'Active daemons:'; tmux list-windows" C-m
else
    echo "Session $SESSION already exists"
fi

# Function to create or recreate window
create_window() {
    local window_id=$1
    local window_name=$2
    local command=$3

    # Kill window if it exists
    tmux kill-window -t "$SESSION:$window_name" 2>/dev/null || true

    # Create new window
    echo "  ✓ Starting $window_name (window $window_id)"
    tmux new-window -t "$SESSION:$window_id" -n "$window_name" -c "$THANOS_ROOT"
    tmux send-keys -t "$SESSION:$window_name" "$command" C-m
}

# Create daemon windows
echo ""
echo "Creating daemon windows..."

create_window 1 "telegram" "python3 Tools/telegram_bot.py"
create_window 2 "alerts" "python3 Tools/daemons/alert_daemon.py"
create_window 3 "vigilance" "python3 Tools/daemons/vigilance_daemon.py"

echo ""
echo "Daemons started successfully!"
echo ""
echo "To monitor:"
echo "  thanos-tmux monitor"
echo ""
echo "To switch windows inside tmux:"
echo "  Ctrl-a 0   - Status window"
echo "  Ctrl-a 1   - Telegram bot"
echo "  Ctrl-a 2   - Alert daemon"
echo "  Ctrl-a 3   - Vigilance daemon"
echo ""
echo "To detach:"
echo "  Ctrl-a d"
echo ""
