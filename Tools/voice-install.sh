#!/bin/bash
# Install whisper.cpp for local voice transcription

set -e

INSTALL_DIR="$HOME/whisper.cpp"

echo "=== Installing Whisper.cpp for Voice Transcription ==="

# Clone whisper.cpp if not exists
if [[ ! -d "$INSTALL_DIR" ]]; then
    echo "Cloning whisper.cpp..."
    git clone https://github.com/ggerganov/whisper.cpp.git "$INSTALL_DIR"
else
    echo "whisper.cpp already exists, updating..."
    cd "$INSTALL_DIR" && git pull
fi

cd "$INSTALL_DIR"

# Build
echo "Building whisper.cpp..."
make

# Download base model (smaller, faster)
echo "Downloading base model..."
bash ./models/download-ggml-model.sh base.en

echo ""
echo "✓ Whisper.cpp installed successfully"
echo "✓ Model: base.en (English, optimized for speed)"
echo ""
echo "Test with: bash ~/.claude/Tools/voice-test.sh"
