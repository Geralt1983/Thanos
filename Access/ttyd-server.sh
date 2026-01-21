#!/bin/bash
# Thanos ttyd web terminal server
# Ubiquitous Access Layer - HTTPS terminal access

set -euo pipefail

PORT=${TTYD_PORT:-7681}
PROJECT_ROOT="$HOME/Projects/Thanos"
CREDENTIAL_FILE="$HOME/.thanos/ttyd-credentials"
PID_FILE="$PROJECT_ROOT/State/ttyd.pid"
LOG_FILE="$PROJECT_ROOT/logs/ttyd.log"
STATE_FILE="$PROJECT_ROOT/State/ttyd_daemon.json"

# Color codes
PURPLE='\033[0;35m'
GOLD='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if ttyd is installed
if ! command -v ttyd &> /dev/null; then
    echo -e "${RED}Error: ttyd not installed${NC}"
    echo "Install with: brew install ttyd"
    exit 1
fi

# Function to generate secure credentials
generate_credentials() {
    echo -e "${GOLD}Generating secure credentials...${NC}"
    mkdir -p "$(dirname "$CREDENTIAL_FILE")"

    # Generate random password
    PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-24)
    echo "thanos:$PASSWORD" > "$CREDENTIAL_FILE"
    chmod 600 "$CREDENTIAL_FILE"

    echo -e "${GOLD}Credentials stored in: $CREDENTIAL_FILE${NC}"
    echo -e "${GOLD}Username: thanos${NC}"
    echo -e "${GOLD}Password: $PASSWORD${NC}"
    echo ""
    echo "Save these credentials securely!"
}

# Function to start ttyd server
start_server() {
    # Check if already running
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo -e "${GOLD}ttyd already running (PID: $PID)${NC}"
            echo "Access at: http://localhost:$PORT"
            return 0
        else
            # Stale PID file
            rm "$PID_FILE"
        fi
    fi

    # Generate credentials if not exist
    if [ ! -f "$CREDENTIAL_FILE" ]; then
        generate_credentials
    fi

    CREDENTIALS=$(cat "$CREDENTIAL_FILE")

    echo -e "${PURPLE}"
    cat << 'EOF'
╔════════════════════════════════════════╗
║   THANOS WEB TERMINAL                  ║
║   Access from anywhere                 ║
╚════════════════════════════════════════╝
EOF
    echo -e "${NC}"

    # Ensure log directory exists
    mkdir -p "$(dirname "$LOG_FILE")"
    mkdir -p "$PROJECT_ROOT/State"

    # Start ttyd in background
    nohup ttyd \
        --port "$PORT" \
        --credential "$CREDENTIALS" \
        --writable \
        --client-option fontSize=14 \
        --client-option fontFamily="'Monaco', 'JetBrains Mono', monospace" \
        --client-option theme='{"background": "#1a1a2e", "foreground": "#ffffff", "cursor": "#9775fa"}' \
        --client-option rendererType=canvas \
        bash -c "$PROJECT_ROOT/Access/thanos-session.sh" \
        > "$LOG_FILE" 2>&1 &

    PID=$!
    echo "$PID" > "$PID_FILE"

    # Store daemon state
    cat > "$STATE_FILE" << EOF
{
  "pid": $PID,
  "port": $PORT,
  "started_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "credential_file": "$CREDENTIAL_FILE",
  "log_file": "$LOG_FILE"
}
EOF

    echo -e "${GOLD}ttyd server started (PID: $PID)${NC}"
    echo -e "${GOLD}Port: $PORT${NC}"
    echo -e "${GOLD}Access: http://localhost:$PORT${NC}"
    echo ""
    echo -e "View logs: tail -f $LOG_FILE"
    echo -e "Stop server: $0 stop"
}

# Function to stop ttyd server
stop_server() {
    if [ ! -f "$PID_FILE" ]; then
        echo -e "${RED}No PID file found. Server not running?${NC}"
        return 1
    fi

    PID=$(cat "$PID_FILE")

    if kill -0 "$PID" 2>/dev/null; then
        echo -e "${GOLD}Stopping ttyd server (PID: $PID)...${NC}"
        kill "$PID"

        # Wait for process to stop
        for i in {1..10}; do
            if ! kill -0 "$PID" 2>/dev/null; then
                break
            fi
            sleep 0.5
        done

        # Force kill if still running
        if kill -0 "$PID" 2>/dev/null; then
            echo -e "${GOLD}Force stopping...${NC}"
            kill -9 "$PID"
        fi

        rm "$PID_FILE"
        echo -e "${GOLD}Server stopped${NC}"
    else
        echo -e "${RED}PID $PID not running. Cleaning up...${NC}"
        rm "$PID_FILE"
    fi
}

# Function to show server status
status_server() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo -e "${GOLD}ttyd server RUNNING${NC}"
            echo "PID: $PID"
            echo "Port: $PORT"
            echo "Access: http://localhost:$PORT"

            if [ -f "$STATE_FILE" ]; then
                echo ""
                echo "State:"
                cat "$STATE_FILE"
            fi
        else
            echo -e "${RED}ttyd server NOT RUNNING (stale PID file)${NC}"
        fi
    else
        echo -e "${RED}ttyd server NOT RUNNING${NC}"
    fi
}

# Main command router
case "${1:-start}" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        stop_server
        sleep 1
        start_server
        ;;
    status)
        status_server
        ;;
    credentials)
        if [ -f "$CREDENTIAL_FILE" ]; then
            cat "$CREDENTIAL_FILE"
        else
            echo -e "${RED}No credentials file found${NC}"
            exit 1
        fi
        ;;
    regenerate)
        if [ -f "$CREDENTIAL_FILE" ]; then
            rm "$CREDENTIAL_FILE"
        fi
        generate_credentials
        echo ""
        echo -e "${GOLD}Restart server for changes to take effect${NC}"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|credentials|regenerate}"
        echo ""
        echo "Commands:"
        echo "  start       - Start ttyd web terminal server"
        echo "  stop        - Stop running server"
        echo "  restart     - Restart server"
        echo "  status      - Check server status"
        echo "  credentials - Show current credentials"
        echo "  regenerate  - Generate new credentials"
        exit 1
        ;;
esac
