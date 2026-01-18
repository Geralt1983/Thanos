#!/bin/bash
# Start ChromaDB server pointing to the shared memory directory

MEMORY_DIR="$HOME/.claude/Memory/vectors"
PORT=8000

echo "Starting ChromaDB server..."
echo "Storage Path: $MEMORY_DIR"
echo "Port: $PORT"

mkdir -p "$MEMORY_DIR"

# Check if chroma is installed
if ! command -v chroma &> /dev/null; then
    echo "chroma-cli not found. Installing chromadb..."
    pip install chromadb
fi

# Run the server
# Note: chroma run might need to be run in a separate terminal or backgrounded
# This script assumes it's being run to start the service
chroma run --path "$MEMORY_DIR" --port "$PORT"
