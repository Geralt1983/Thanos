# Termux Voice Capture Setup

## Installation

### 1. Install termux-api package
```bash
pkg install termux-api
```

### 2. Install Termux:API app
Download and install the **Termux:API** companion app:
- **F-Droid** (recommended): https://f-droid.org/en/packages/com.termux.api/
- **Play Store**: Search "Termux:API" (if available in your region)

### 3. Grant Permissions
Open Android Settings → Apps → Termux:API → Permissions → Enable **Microphone**

### 4. Test Installation
```bash
bash ~/.claude/Tools/termux-voice-capture.sh quick
```

## Usage

### Record (manual stop)
```bash
bash ~/.claude/Tools/termux-voice-capture.sh start
```
Press Ctrl+C when done

### Quick 30-second note
```bash
bash ~/.claude/Tools/termux-voice-capture.sh quick
```

### List recordings
```bash
bash ~/.claude/Tools/termux-voice-capture.sh list
```

### Cleanup old recordings
```bash
bash ~/.claude/Tools/termux-voice-capture.sh cleanup
```

## Current Limitations

1. **No local transcription yet** - recordings saved as .m4a audio files
2. **Transcription options** (coming soon):
   - Compile whisper.cpp for ARM64 (local, privacy-first)
   - Use cloud API (OpenAI Whisper, AssemblyAI, etc.)

## Git Sync

Recordings saved to `~/.claude/Voice/` will sync to Mac via git:
```bash
cd ~/.claude && git pull    # Get latest from Mac
cd ~/.claude && git push    # Push recordings to Mac
```

Mac can transcribe recordings using whisper.cpp, then sync transcripts back to mobile.

## Next Steps

1. Test basic recording on Android
2. Decide on transcription strategy:
   - **Option A**: Compile whisper.cpp for Termux (complex, fully offline)
   - **Option B**: Use cloud API for transcription (simple, requires internet)
   - **Option C**: Record on mobile, transcribe on Mac via git sync (hybrid approach)
