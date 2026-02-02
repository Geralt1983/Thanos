#!/bin/bash
# Auto-start ByteRover MCP server
# Called by launchd at login

cd /Users/jeremy/Projects/Thanos

# Check if MCP is already running
if brv status 2>&1 | grep -q "Status: Logged in"; then
    echo "[$(date)] ByteRover MCP already running" >> logs/brv-startup.log
    exit 0
fi

# Start brv in background via expect or screen
# brv requires interactive terminal, so we use script to fake it
script -q /dev/null brv quit &

# Wait a moment for startup
sleep 2

# Verify
if brv status 2>&1 | grep -q "Status: Logged in"; then
    echo "[$(date)] ByteRover MCP started successfully" >> logs/brv-startup.log
else
    echo "[$(date)] Failed to start ByteRover MCP" >> logs/brv-startup.log
    exit 1
fi
