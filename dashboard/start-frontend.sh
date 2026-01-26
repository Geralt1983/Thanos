#!/bin/bash

# Thanos Dashboard - Frontend Startup Script
# Starts the React + Vite frontend dev server on port 3000

set -e

echo "========================================="
echo "🎯 THANOS DASHBOARD - Frontend Server"
echo "========================================="
echo ""

# Check if we're in the dashboard directory
if [ ! -d "frontend" ]; then
    echo "❌ Error: frontend/ directory not found"
    echo "   Please run this script from the dashboard/ directory"
    exit 1
fi

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo "❌ Error: node not found"
    echo "   Please install Node.js 18 or later"
    echo "   Download from: https://nodejs.org/"
    exit 1
fi

# Check if npm is available
if ! command -v npm &> /dev/null; then
    echo "❌ Error: npm not found"
    echo "   Please install npm (usually comes with Node.js)"
    exit 1
fi

cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
else
    echo "✓ Dependencies already installed"
fi

echo ""
echo "========================================="
echo "🚀 Starting Frontend Dev Server..."
echo "========================================="
echo ""
echo "   App URL: http://localhost:3000"
echo "   Backend API: http://localhost:8001"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the frontend dev server
npm run dev
