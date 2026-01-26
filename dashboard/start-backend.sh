#!/bin/bash

# Thanos Dashboard - Backend Startup Script
# Starts the FastAPI backend server on port 8001

set -e

echo "========================================="
echo "🎯 THANOS DASHBOARD - Backend Server"
echo "========================================="
echo ""

# Check if we're in the dashboard directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found"
    echo "   Please run this script from the dashboard/ directory"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found"
    echo "   Please install Python 3.9 or later"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -q -r requirements.txt

# Check if dependencies are installed
python3 -c "import fastapi, uvicorn" 2>/dev/null || {
    echo "❌ Error: Failed to install dependencies"
    exit 1
}

echo ""
echo "✓ Dependencies installed"
echo ""
echo "========================================="
echo "🚀 Starting Backend Server..."
echo "========================================="
echo ""
echo "   API URL: http://localhost:8001"
echo "   API Docs: http://localhost:8001/docs"
echo "   Health: http://localhost:8001/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the backend server
python3 -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
