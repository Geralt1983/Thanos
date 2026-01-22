# Audio Hooks: cc-hooks vs Thanos Custom

## What We Built (5 minutes ago)

**File**: `hooks/post-tool-use/voice-announce.py`

**Features**:
- ✅ Voice after tool execution (Read, Write, Bash, etc.)
- ✅ Uses your custom Thanos voice (ElevenLabs)
- ✅ Cached audio (instant playback)
- ✅ Contextual Thanos phrases
- ✅ Zero external dependencies (uses existing Shell/lib/voice.py)

**Hooks Active**:
- PostToolUse only

**Example**:
```
[You use Read tool]
🔊 "The file reveals its secrets"
```

---

## cc-hooks Plugin (Community)

**Repository**: https://github.com/husniadil/cc-hooks

**Features**:
- ✅ All hooks (SessionStart/End, PreToolUse, PostToolUse, Stop, Notification, SubagentStop)
- ✅ Multi-provider TTS (Google, ElevenLabs, prerecorded)
- ✅ AI-generated contextual messages (via OpenRouter)
- ✅ Smart fallback chain
- ✅ Sound effects (tek.mp3 on tool start, cetek.mp3 on completion)
- ✅ Per-session configuration
- ✅ Multiple languages

**Installation**:
```bash
claude plugin marketplace add https://github.com/husniadil/cc-hooks.git
claude plugin install cc-hooks-plugin@cc-hooks-plugin
/cc-hooks-plugin:setup
```

**Usage Examples**:
```bash
# Indonesian with Google TTS
cld --audio=gtts --language=id

# Premium voice with AI messages
cld --audio=elevenlabs --ai=full

# Silent mode (meetings)
cld --silent
```

**Example with AI**:
```
[You complete a feature]
🔊 "I've successfully implemented the authentication system with JWT tokens"
```

---

## Comparison

| Feature | Thanos Custom | cc-hooks |
|---------|---------------|----------|
| **PostToolUse voice** | ✅ Active now | ✅ |
| **Custom Thanos voice** | ✅ | ✅ (configurable) |
| **SessionStart/End** | ❌ | ✅ |
| **PreToolUse** | ❌ | ✅ |
| **Notification hook** | ❌ | ✅ |
| **AI-generated messages** | ❌ | ✅ (requires OpenRouter) |
| **Sound effects** | ❌ | ✅ |
| **Multi-language** | ❌ | ✅ |
| **Setup complexity** | None (already done) | Plugin install + config |
| **Dependencies** | Existing infra | Python 3.12+, uv |

---

## Your Options

### A) Keep What We Built
**Pros**: Already working, zero setup, uses your Thanos voice, lightweight
**Cons**: Only PostToolUse, no AI messages, no sound effects

### B) Install cc-hooks
**Pros**: Full feature set, AI messages, all hooks, community maintained
**Cons**: Plugin install, configuration, might conflict with our hook

### C) Enhance What We Built (inspired by cc-hooks)
**Pros**: Best of both worlds, full control, custom Thanos integration
**Cons**: We'd need to implement:
- PreToolUse hook (sound before tools)
- SessionStart/End hooks (greetings/farewells)
- Notification hook
- Sound effects library

---

## Recommended Path

**Short term**: Keep our PostToolUse hook (it's working)

**If you want more**:
1. Try cc-hooks alongside (different sessions)
2. OR enhance our hooks with:
   - SessionStart → "The stones have been gathered"
   - SessionEnd → "The work is complete"
   - PreToolUse → Sound effect (tek.mp3)
   - Stop → "Perfect balance achieved"

**Prerequisites Met**:
- ✅ Python 3.13.5 (requires 3.12+)
- ✅ uv installed
- ⚠️ Claude plugin system (need to verify)

The choice is yours.
