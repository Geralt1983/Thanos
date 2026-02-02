#!/bin/bash
# Start Graphiti MCP server

# Check if already running
if curl -s -I http://localhost:8000/sse 2>/dev/null | grep -q "200 OK"; then
    echo "Graphiti already running on port 8000"
    exit 0
fi

# Check Neo4j
if ! docker ps | grep -q neo4j; then
    echo "ERROR: Neo4j not running. Start with: docker start neo4j"
    exit 1
fi

cd /Users/jeremy/Projects/mcp-graphiti
export NEO4J_URI=bolt://localhost:7687

echo "Starting Graphiti MCP server..."
nohup uv run python graphiti_mcp_server.py > /tmp/graphiti.log 2>&1 &

sleep 3

if curl -s -I http://localhost:8000/sse 2>/dev/null | grep -q "200 OK"; then
    echo "✅ Graphiti running on http://localhost:8000"
else
    echo "⚠️ Graphiti may still be starting. Check /tmp/graphiti.log"
fi
