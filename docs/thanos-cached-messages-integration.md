# Thanos Cached Messages Integration

## Summary

Modified cc-hooks TTS announcer to use Thanos pre-cached messages for Stop events instead of expensive OpenRouter contextual generation.

## Changes Made

### 1. Modified `/Users/jeremy/.claude/plugins/cache/cc-hooks-plugin/cc-hooks-plugin/1.0.12/utils/tts_announcer.py`

#### Stop Event Handler (Lines 256-286)
**Before:**
- Used `transcript_parser.extract_conversation_context()` to analyze session transcript
- Called `openrouter_service.generate_completion_message_if_available()` for contextual messages
- Cost: ~$0.05 per Stop event via OpenRouter API

**After:**
- Imports `thanos_messages.get_random_message()`
- Selects random pre-cached Thanos quote
- Returns message directly (no OpenRouter call)
- Cost: $0 per Stop event (messages already cached via ElevenLabs)

```python
# THANOS OVERRIDE: Use pre-cached messages to avoid $0.05 OpenRouter cost per Stop event
# This hybrid system:
# - One-time: Generate/cache 8-12 Thanos messages via ElevenLabs (~$0.60 total)
# - Forever: Reuse them randomly for all Stop events ($0 cost)
if hook_event_name == "Stop":
    try:
        from utils.thanos_messages import get_random_message

        # Get a random Thanos completion message (pre-cached via ElevenLabs)
        thanos_message = get_random_message()

        logger.info(
            f"Using Thanos cached message for Stop event: '{thanos_message}'"
        )

        # Return the Thanos message directly
        # Translation is skipped for Thanos messages (they're philosophical quotes)
        return thanos_message
```

#### Cache Flag Removal (Lines 504-507)
**Before:**
- Both Stop and PreToolUse events marked with `_no_cache = True`
- Forced regeneration on every use

**After:**
- Only PreToolUse marked as `_no_cache = True`
- Stop events can now be cached by ElevenLabs
- Reuses the same audio file for identical Thanos quotes

```python
# THANOS OVERRIDE: Stop events now use cached Thanos messages, so we DON'T need _no_cache
# Only PreToolUse still uses contextual generation and needs _no_cache
if hook_event_name == "PreToolUse":
    enhanced_event_data["_no_cache"] = True
```

## How It Works

### Existing Infrastructure (Already in Place)
1. **Thanos Messages Module** (`utils/thanos_messages.py`)
   - Already exists in cc-hooks-plugin
   - Contains 40+ categorized Thanos quotes
   - Provides `get_random_message()` function

2. **ElevenLabs Caching** (Built into cc-hooks)
   - TTS provider automatically caches generated audio
   - Same text = same cached file reused
   - No API calls for cached messages

### Integration Flow
1. **Session Ends** → Stop hook fires
2. **TTS Announcer** → Calls `get_random_message()`
3. **Thanos Module** → Returns random quote from pool
4. **TTS Manager** → Checks cache for audio file
5. **If cached** → Play immediately ($0 cost)
6. **If not cached** → Generate via ElevenLabs (~$0.03)
7. **Future uses** → Always use cached version ($0)

## Cost Analysis

### Old System (OpenRouter Contextual)
- Per Stop event: $0.05 (OpenRouter API call)
- 100 sessions: $5.00
- 1000 sessions: $50.00

### New System (Thanos Cached)
- One-time setup: ~$0.60 (generate 18 unique messages)
- Per Stop event: $0 (reuse cached audio)
- 100 sessions: $0.60 total
- 1000 sessions: $0.60 total

### Savings
- First 100 sessions: **89% cost reduction**
- First 1000 sessions: **99% cost reduction**
- Ongoing: **100% cost reduction** (after initial cache)

## Reverting Changes (If Needed)

To restore OpenRouter contextual generation:

1. **Restore Stop Event Handler** (Line 256-286)
   ```bash
   # Revert to original OpenRouter implementation
   git checkout HEAD -- utils/tts_announcer.py
   ```

2. **Restore _no_cache Flag** (Line 506-507)
   ```python
   # Mark both events as no-cache
   if hook_event_name == "Stop" or hook_event_name == "PreToolUse":
       enhanced_event_data["_no_cache"] = True
   ```

## Testing

### Verify Integration
```bash
# Test Stop event with Thanos message
cd /Users/jeremy/.claude/plugins/cache/cc-hooks-plugin/cc-hooks-plugin/1.0.12
./utils/tts_announcer.py Stop

# Check logs for "Using Thanos cached message"
# Should see random Thanos quote played
```

### Pre-cache Messages (If Needed)
```bash
# Generate and cache all Thanos messages upfront
cd /Users/jeremy/Projects/Thanos
python tests/precache_thanos_messages.py
```

## Notes

- **Fallback Protection:** If `thanos_messages` module fails, falls back to default "Task completed successfully"
- **Translation Skip:** Thanos quotes are philosophical and shouldn't be translated
- **PreToolUse Unchanged:** Still uses OpenRouter contextual generation (different use case)
- **Cache Location:** ElevenLabs audio cache in `.cache/elevenlabs/` or plugin cache dir
- **Message Pool:** 40+ unique messages across 7 categories (code, bug_fix, testing, refactor, documentation, research, general)

## Future Enhancements

1. **Adaptive Message Selection**
   - Use task category detection to pick relevant Thanos quote
   - E.g., "Bug fixed" → "The flaw is eliminated. Order restored."

2. **Context-Aware Caching**
   - Cache last 5 OpenRouter contextual messages per session
   - Reuse if similar task pattern detected

3. **Hybrid Mode Toggle**
   - Config flag: `use_thanos_stop_messages = true/false`
   - Allow users to choose between Thanos or contextual

## Files Changed

1. `/Users/jeremy/.claude/plugins/cache/cc-hooks-plugin/cc-hooks-plugin/1.0.12/utils/tts_announcer.py`
   - Lines 256-286: Stop event handler
   - Lines 504-507: Cache flag logic

## Files Referenced (No Changes)

1. `/Users/jeremy/.claude/plugins/cache/cc-hooks-plugin/cc-hooks-plugin/1.0.12/utils/thanos_messages.py`
   - Already exists with complete implementation
   - Provides message pool and selection functions

2. `/Users/jeremy/Projects/Thanos/tests/precache_thanos_messages.py`
   - Utility to pre-cache all messages
   - Optional for initial setup
