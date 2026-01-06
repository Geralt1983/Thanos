#!/bin/bash
# Thanos Voice Capture - Terminal-native voice journaling

VOICE_DIR="$HOME/.claude/Voice"
JOURNAL_DIR="$HOME/.claude/Journal"
WHISPER_DIR="$HOME/whisper.cpp"
TIMESTAMP=$(date '+%Y-%m-%d-%H%M')

mkdir -p "$VOICE_DIR"
mkdir -p "$JOURNAL_DIR"

case "$1" in
    "start"|"record")
        # Start recording
        RECORDING="$VOICE_DIR/recording-${TIMESTAMP}.wav"

        echo "=== Thanos Voice Capture ==="
        echo "Recording... (Press Ctrl+C to stop)"
        echo ""

        # Record audio (16kHz mono WAV for whisper)
        rec -r 16000 -c 1 "$RECORDING"

        echo ""
        echo "✓ Recording saved: $RECORDING"
        echo "Processing transcription..."

        # Transcribe
        TRANSCRIPT=$("$WHISPER_DIR/build/bin/whisper-cli" -m "$WHISPER_DIR/models/ggml-base.en.bin" -f "$RECORDING" -nt -otxt 2>/dev/null | tail -n +2)

        if [[ -n "$TRANSCRIPT" ]]; then
            # Save to journal
            JOURNAL_FILE="$JOURNAL_DIR/${TIMESTAMP}-voice.md"
            cat > "$JOURNAL_FILE" << EOF
# Voice Journal - $TIMESTAMP

$TRANSCRIPT

---
*Transcribed via Whisper.cpp*
*Recording: $(basename "$RECORDING")*
EOF

            echo "✓ Transcribed and saved to journal: $JOURNAL_FILE"

            # Delete audio file to save space (keep if you want to preserve)
            # rm "$RECORDING"
            # echo "✓ Audio file deleted"
        else
            echo "✗ Transcription failed"
            exit 1
        fi
        ;;

    "quick")
        # Quick 30-second voice note
        RECORDING="$VOICE_DIR/quick-${TIMESTAMP}.wav"

        echo "=== Quick Voice Note (30 seconds) ==="
        echo "Recording..."

        # Record for 30 seconds
        rec -r 16000 -c 1 "$RECORDING" trim 0 30

        echo "Processing transcription..."

        # Transcribe
        TRANSCRIPT=$("$WHISPER_DIR/build/bin/whisper-cli" -m "$WHISPER_DIR/models/ggml-base.en.bin" -f "$RECORDING" -nt -otxt 2>/dev/null | tail -n +2)

        if [[ -n "$TRANSCRIPT" ]]; then
            # Save to journal
            JOURNAL_FILE="$JOURNAL_DIR/${TIMESTAMP}-voice.md"
            cat > "$JOURNAL_FILE" << EOF
# Quick Voice Note - $TIMESTAMP

$TRANSCRIPT

---
*Quick capture (30s) via Whisper.cpp*
EOF

            echo "✓ Saved to journal: $JOURNAL_FILE"
            rm "$RECORDING"
        else
            echo "✗ Transcription failed"
            exit 1
        fi
        ;;

    "list")
        # List voice journal entries
        echo "=== Voice Journal Entries ==="
        find "$JOURNAL_DIR" -name "*-voice.md" | sort -r | head -10
        ;;

    "cleanup")
        # Clean up old recordings
        echo "Cleaning up old voice recordings..."
        rm -f "$VOICE_DIR"/*.wav
        echo "✓ Voice directory cleaned"
        ;;

    *)
        echo "Thanos Voice Capture"
        echo ""
        echo "Usage:"
        echo "  bash ~/.claude/Tools/voice-capture.sh start    - Start recording (Ctrl+C to stop)"
        echo "  bash ~/.claude/Tools/voice-capture.sh quick    - Quick 30-second note"
        echo "  bash ~/.claude/Tools/voice-capture.sh list     - List voice entries"
        echo "  bash ~/.claude/Tools/voice-capture.sh cleanup  - Delete old recordings"
        echo ""
        echo "First time? Run: bash ~/.claude/Tools/voice-install.sh"
        ;;
esac
