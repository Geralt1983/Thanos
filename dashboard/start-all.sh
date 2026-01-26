#!/bin/bash

# Thanos Dashboard - Complete Startup Script
# Starts both backend and frontend servers in separate terminal windows

set -e

echo "========================================="
echo "🎯 THANOS DASHBOARD - Complete Startup"
echo "========================================="
echo ""

# Check if we're in the dashboard directory
if [ ! -f "main.py" ] || [ ! -d "frontend" ]; then
    echo "❌ Error: Not in the dashboard/ directory"
    echo "   Please run this script from the dashboard/ directory"
    exit 1
fi

echo "This script will start both backend and frontend servers"
echo "in separate terminal windows."
echo ""

# Check for required commands
command -v python3 &> /dev/null || {
    echo "❌ Error: python3 not found"
    exit 1
}

command -v node &> /dev/null || {
    echo "❌ Error: node not found"
    echo "   Install from: https://nodejs.org/"
    exit 1
}

# Detect OS and terminal emulator
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS - use Terminal.app or iTerm
    echo "🍎 Detected macOS"
    echo ""
    echo "Starting backend server..."
    osascript <<EOF
        tell application "Terminal"
            do script "cd $(pwd) && ./start-backend.sh"
            activate
        end tell
EOF
    sleep 2

    echo "Starting frontend server..."
    osascript <<EOF
        tell application "Terminal"
            do script "cd $(pwd) && ./start-frontend.sh"
            activate
        end tell
EOF

elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux - try various terminal emulators
    echo "🐧 Detected Linux"
    echo ""

    if command -v gnome-terminal &> /dev/null; then
        echo "Starting backend server..."
        gnome-terminal -- bash -c "cd $(pwd) && ./start-backend.sh; exec bash"
        sleep 2

        echo "Starting frontend server..."
        gnome-terminal -- bash -c "cd $(pwd) && ./start-frontend.sh; exec bash"

    elif command -v xterm &> /dev/null; then
        echo "Starting backend server..."
        xterm -e "cd $(pwd) && ./start-backend.sh" &
        sleep 2

        echo "Starting frontend server..."
        xterm -e "cd $(pwd) && ./start-frontend.sh" &

    else
        echo "⚠️  No supported terminal emulator found"
        echo "   Please run these commands manually in separate terminals:"
        echo ""
        echo "   Terminal 1: cd $(pwd) && ./start-backend.sh"
        echo "   Terminal 2: cd $(pwd) && ./start-frontend.sh"
        exit 1
    fi

elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    # Windows Git Bash or Cygwin
    echo "🪟 Detected Windows"
    echo ""
    echo "Starting backend server..."
    start cmd.exe /k "cd /d $(pwd) && bash start-backend.sh"
    sleep 2

    echo "Starting frontend server..."
    start cmd.exe /k "cd /d $(pwd) && bash start-frontend.sh"

else
    echo "⚠️  Unsupported OS: $OSTYPE"
    echo "   Please run these commands manually in separate terminals:"
    echo ""
    echo "   Terminal 1: ./start-backend.sh"
    echo "   Terminal 2: ./start-frontend.sh"
    exit 1
fi

echo ""
echo "========================================="
echo "✅ Dashboard servers are starting!"
echo "========================================="
echo ""
echo "Backend:  http://localhost:8001"
echo "Frontend: http://localhost:3000"
echo "API Docs: http://localhost:8001/docs"
echo ""
echo "Wait a few seconds, then open:"
echo "  http://localhost:3000"
echo ""
echo "To stop: Close the terminal windows or press Ctrl+C in each"
echo ""
