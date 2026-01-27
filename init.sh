#!/bin/bash
# Thanos Development Environment Setup
#
# This script sets up the development environment by installing all required
# Python dependencies including test dependencies.
#
# Usage:
#   chmod +x init.sh
#   ./init.sh

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Thanos Development Environment Setup                          ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check Python version
PYTHON_CMD="python3"
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "✗ Python 3 not found. Please install Python 3.8 or later."
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo "✓ Found Python $PYTHON_VERSION"
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "requirements.txt" ]; then
    echo "  → Installing core dependencies from requirements.txt..."
    $PYTHON_CMD -m pip install --user -r requirements.txt --quiet --upgrade
    echo "  ✓ Core dependencies installed"
else
    echo "  ⚠️  requirements.txt not found, skipping"
fi

echo ""

# Install test dependencies
if [ -f "requirements-test.txt" ]; then
    echo "  → Installing test dependencies from requirements-test.txt..."
    $PYTHON_CMD -m pip install --user -r requirements-test.txt --quiet --upgrade
    echo "  ✓ Test dependencies installed"
else
    echo "  ⚠️  requirements-test.txt not found, skipping test dependencies"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Setup Complete!                                               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  → Run tests:          pytest tests/ -v"
echo "  → Run setup wizard:   python3 Tools/setup_wizard.py"
echo "  → Start Thanos:       ./thanos.py"
echo ""
