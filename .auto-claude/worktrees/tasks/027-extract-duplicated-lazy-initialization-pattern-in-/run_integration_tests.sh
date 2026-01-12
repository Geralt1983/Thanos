#!/bin/bash
# Integration Test Runner for Command Router Memory Commands
#
# This script runs the integration tests for subtask 3.4

set -e

echo "=========================================="
echo "Command Router Integration Tests"
echo "=========================================="
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found. Please install it:"
    echo "   pip install pytest pytest-mock pytest-asyncio"
    exit 1
fi

echo "✓ pytest found"
echo ""

# Run the integration tests
echo "Running integration tests..."
echo ""

pytest tests/integration/test_command_router_memory.py \
    -v \
    --tb=short \
    --color=yes \
    -k "" \
    "$@"

echo ""
echo "=========================================="
echo "Test run complete!"
echo "=========================================="
