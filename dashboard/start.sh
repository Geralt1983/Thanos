#!/bin/bash

# Thanos Dashboard - Quick Start Script
# Starts the FastAPI backend server in the background for quick testing

set -e

# Determine if we're in dashboard directory or parent
if [ -f "main.py" ]; then
    # We're in the dashboard directory - need to go up one level
    cd ..
    DASHBOARD_DIR="dashboard"
elif [ -d "dashboard" ] && [ -f "dashboard/main.py" ]; then
    # We're in the parent directory
    DASHBOARD_DIR="dashboard"
else
    echo "❌ Error: Could not find dashboard directory"
    echo "   Please run this script from the dashboard/ directory or its parent"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found"
    echo "   Please install Python 3.9 or later"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$DASHBOARD_DIR/venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv "$DASHBOARD_DIR/venv"
fi

# Activate virtual environment
source "$DASHBOARD_DIR/venv/bin/activate"

# Install dependencies if needed
if ! python3 -c "import fastapi, uvicorn" 2>/dev/null; then
    echo "📦 Installing Python dependencies..."
    pip install -q -r "$DASHBOARD_DIR/requirements.txt" || pip install -q fastapi==0.109.0 uvicorn==0.27.0 python-dotenv==1.0.0 httpx==0.26.0 pydantic==2.5.3 pydantic-settings==2.1.0
fi

# Check if server is already running
if lsof -i :8001 >/dev/null 2>&1; then
    echo "⚠️  Server already running on port 8001"
    exit 0
fi

echo "🚀 Starting Thanos Dashboard backend server..."
echo "   API URL: http://localhost:8001"
echo "   Health: http://localhost:8001/health"
echo ""

# Start the backend server in the background
# Run from parent directory so imports work correctly
nohup python3 -m uvicorn dashboard.main:app --host 0.0.0.0 --port 8001 > "$DASHBOARD_DIR/backend.log" 2>&1 &
SERVER_PID=$!

echo "✓ Backend server started (PID: $SERVER_PID)"
echo "  Logs: $DASHBOARD_DIR/backend.log"
echo ""
echo "To stop: kill $SERVER_PID"
echo ""

# Save PID for easy stopping
echo $SERVER_PID > "$DASHBOARD_DIR/.server.pid"

# Wait a moment for server to initialize
sleep 2

# Check if server is responding
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "✅ Server is healthy and ready"
    exit 0
else
    echo "⏳ Server is starting... (check logs if it doesn't respond)"
    exit 0
fi
