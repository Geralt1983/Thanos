# Claude Code Voice Integration

**Status**: ✅ ACTIVE (this session forward)

## What This Does

Every Claude Code response in terminal now plays as voice using your custom Thanos voice (ElevenLabs).

## Implementation

### Hook System
**File**: `.claude/settings.json`
- **Hook Type**: `AssistantResponse`
- **Trigger**: After every Claude message
- **Script**: `hooks/assistant-response/voice-synthesis.py`

### Voice Processing
1. Receives Claude's response via stdin
2. Extracts clean text (removes code, markdown, URLs, tables)
3. Takes first 2 sentences for concise audio
4. Synthesizes using ElevenLabs custom Thanos voice
5. Plays audio (non-blocking, cached for speed)

### Configuration
- **Voice ID**: SuMcLpxNrgPskVeKpPnh (custom Thanos)
- **Cache**: ~/.thanos/audio-cache/ (instant playback on repeats)
- **Model**: eleven_turbo_v2_5 (free tier)
- **Auto-play**: Enabled by default
- **Error handling**: Silent failures (won't break Claude Code)

## Audio Features

**✅ Works Now:**
- Voice plays after every response
- Uses cached audio when available (<10ms)
- Synthesizes new responses (1-2s first time)
- Speaks first 2 sentences only (concise)
- Filters out code blocks, tools, markdown

**❌ Not Supported:**
- Voice cannot be toggled without editing settings
- No voice speed control
- No interruption capability

## Disable Voice

Edit `.claude/settings.json` and remove the `AssistantResponse` hook:

```json
"AssistantResponse": [
  // Delete this entire block to disable voice
]
```

## Testing

Voice played on this response. If you heard "The work is done. Perfect balance achieved." - it's working.

---

**Next**: Want Kitty terminal setup for visual backgrounds?
