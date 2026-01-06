#!/data/data/com.termux/files/usr/bin/bash
# Thanos Voice Capture - Termux/Android version

VOICE_DIR="$HOME/.claude/Voice"
JOURNAL_DIR="$HOME/.claude/Journal"
TIMESTAMP=$(date '+%Y-%m-%d-%H%M')

mkdir -p "$VOICE_DIR"
mkdir -p "$JOURNAL_DIR"

# Check for termux-api
if ! command -v termux-microphone-record &> /dev/null; then
    echo "Error: termux-api not installed"
    echo "Install with: pkg install termux-api"
    echo "Then install Termux:API app from F-Droid or Play Store"
    exit 1
fi

case "$1" in
    "start"|"record")
        # Start recording
        RECORDING="$VOICE_DIR/recording-${TIMESTAMP}.m4a"

        echo "=== Thanos Voice Capture (Android) ==="
        echo "Recording... (Press Ctrl+C to stop)"
        echo ""

        # Record audio using termux-api
        termux-microphone-record -f "$RECORDING"

        echo ""
        echo "✓ Recording saved: $RECORDING"
        echo ""
        echo "Note: Transcription requires whisper.cpp or cloud API"
        echo "For now, audio saved. Will add transcription in next update."
        ;;

    "quick")
        # Quick 30-second recording
        RECORDING="$VOICE_DIR/quick-${TIMESTAMP}.m4a"

        echo "=== Quick Voice Note (30 seconds) ==="
        echo "Recording..."

        # Record for 30 seconds
        termux-microphone-record -f "$RECORDING" -l 30

        echo "✓ Recording saved: $RECORDING"
        echo ""
        echo "Note: Transcription requires whisper.cpp or cloud API"
        ;;

    "list")
        # List voice recordings
        echo "=== Voice Recordings ===="
        find "$VOICE_DIR" -name "*.m4a" -o -name "*.wav" | sort -r | head -10
        ;;

    "cleanup")
        # Clean up old recordings
        echo "Cleaning up old voice recordings..."
        rm -f "$VOICE_DIR"/*.m4a "$VOICE_DIR"/*.wav
        echo "✓ Voice directory cleaned"
        ;;

    "install")
        echo "=== Installing Termux Voice Capture ==="
        echo ""
        echo "Step 1: Install termux-api package"
        pkg install termux-api -y
        echo ""
        echo "Step 2: Install Termux:API app"
        echo "Download from: https://f-droid.org/en/packages/com.termux.api/"
        echo "Or from Play Store (if available)"
        echo ""
        echo "Step 3: Grant microphone permissions to Termux:API app"
        echo ""
        echo "✓ Installation complete"
        ;;

    *)
        echo "Thanos Voice Capture (Android)"
        echo ""
        echo "Usage:"
        echo "  bash ~/.claude/Tools/termux-voice-capture.sh start    - Start recording (Ctrl+C to stop)"
        echo "  bash ~/.claude/Tools/termux-voice-capture.sh quick    - Quick 30-second note"
        echo "  bash ~/.claude/Tools/termux-voice-capture.sh list     - List recordings"
        echo "  bash ~/.claude/Tools/termux-voice-capture.sh cleanup  - Delete old recordings"
        echo "  bash ~/.claude/Tools/termux-voice-capture.sh install  - Installation guide"
        echo ""
        echo "First time? Run: bash ~/.claude/Tools/termux-voice-capture.sh install"
        ;;
esac
