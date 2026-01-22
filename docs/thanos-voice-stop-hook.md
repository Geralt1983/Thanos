# Thanos Voice Stop Hook

## Overview

When you exit a Claude Code session, Thanos speaks one final message before you go. These messages are pre-cached for instant playback without any API calls.

## Features

- **18 Thanos Quotes**: Randomly selected from iconic movie lines
- **Pre-Cached Audio**: No API calls, instant playback (<200ms)
- **Zero Blocking**: Voice plays asynchronously, session ends immediately
- **Graceful Degradation**: If voice fails, session proceeds normally

## Setup

### Initial Cache Generation

Run once to pre-cache all Thanos messages:

```bash
cd ~/Projects/Thanos
python3 tests/precache_thanos_messages.py
```

Expected output:
```
✓ Successfully cached: 18/18
📊 Cache Statistics:
  - Total files: 34
  - Total size: 1.42 MB
```

### Verify Installation

```bash
# Check cache status
python3 Shell/lib/voice.py cache-stats

# Test Stop hook manually
echo "test" | python3 hooks/stop/thanos_voice.py
```

## Thanos Message Pool

1. "The work is done. The universe is grateful."
2. "You could not live with your own failure. Where did that bring you? Back to me."
3. "I am inevitable."
4. "The hardest choices require the strongest wills."
5. "A small price to pay for salvation."
6. "Perfectly balanced, as all things should be."
7. "You should have gone for the head."
8. "I ignored my destiny once. I cannot do that again."
9. "Fun isn't something one considers when balancing the universe. But this does put a smile on my face."
10. "Reality is often disappointing."
11. "I know what it's like to lose. To feel so desperately that you're right, yet to fail nonetheless."
12. "The strongest choices require the strongest wills."
13. "Dread it. Run from it. Destiny arrives all the same."
14. "I will shred this universe down to its last atom."
15. "You're not the only one cursed with knowledge."
16. "The work is complete. Rest now."
17. "I have finally found the courage to do what I must."
18. "The universe required correction."

## Configuration

The Stop hook is configured in `.claude/settings.json`:

```json
"Stop": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "python3 ~/Projects/Thanos/hooks/stop/thanos_voice.py",
        "timeout": 3000,
        "continueOnError": true
      }
    ]
  }
]
```

## How It Works

1. **Session Ends**: You exit Claude Code
2. **Hook Triggers**: Stop hook executes
3. **Message Selected**: Random Thanos quote chosen
4. **Cache Lookup**: Pre-cached audio file retrieved (5ms)
5. **Audio Plays**: `afplay` plays sound in background
6. **Hook Exits**: Session finalization continues immediately

**Total Time:** ~156ms (imperceptible to user)

## Cache Management

### View Cache Statistics
```bash
python3 Shell/lib/voice.py cache-stats
```

### Clear Cache
```bash
python3 Shell/lib/voice.py clear-cache
```

### Regenerate Cache
```bash
python3 tests/precache_thanos_messages.py
```

## Troubleshooting

### No Sound on Stop

**Check 1:** Verify cache exists
```bash
ls -lh ~/.thanos/audio-cache/*.mp3 | wc -l
# Should show at least 18 files
```

**Check 2:** Test audio playback
```bash
afplay ~/.thanos/audio-cache/*.mp3 | head -1
# Should hear Thanos voice
```

**Check 3:** Verify hook configuration
```bash
grep -A5 '"Stop"' ~/.claude/settings.json
# Should show thanos_voice.py command
```

**Check 4:** Test hook manually
```bash
echo "test" | python3 ~/Projects/Thanos/hooks/stop/thanos_voice.py
# Should hear a Thanos message
```

### API Key Errors

The Stop hook uses **only cached audio**. API key is only needed for initial cache generation.

If you see API errors during Stop events:
1. This shouldn't happen (cache should be used)
2. Re-run `python3 tests/precache_thanos_messages.py` to ensure cache is complete

### Cache Misses

If you see "Cached audio" instead of "Cache hit" in logs:
- This means a new message was synthesized (requires API call)
- Shouldn't happen with pre-cached messages
- Verify all 18 messages are cached:

```bash
python3 -c "
import sys; sys.path.insert(0, 'Shell/lib')
from voice import VoiceSynthesizer
s = VoiceSynthesizer()
print(f'Cache files: {s.cache_stats()[\"file_count\"]}')
"
```

## Performance

- **Execution Time:** ~156ms
- **Cache Hit Rate:** 100%
- **API Calls:** 0 (uses only cached audio)
- **Blocking:** None (async playback)

## Testing

Run comprehensive test suite:

```bash
bash tests/run_voice_tests.sh
```

Expected result:
```
Passed: 9
Failed: 0
🎯 All tests passed!
```

## Files

- **Hook Script:** `hooks/stop/thanos_voice.py`
- **Pre-Cache Script:** `tests/precache_thanos_messages.py`
- **Voice Module:** `Shell/lib/voice.py`
- **Cache Directory:** `~/.thanos/audio-cache/`
- **Test Plan:** `tests/test_thanos_voice_stop.md`
- **Test Results:** `tests/THANOS_VOICE_TEST_RESULTS.md`

## FAQ

**Q: Can I add more Thanos quotes?**
A: Yes! Edit `THANOS_MESSAGES` in both:
- `hooks/stop/thanos_voice.py`
- `tests/precache_thanos_messages.py`

Then regenerate cache: `python3 tests/precache_thanos_messages.py`

**Q: Can I use a different voice?**
A: Yes! Set `THANOS_VOICE_ID` in `.env` to your ElevenLabs voice ID.

**Q: Does this work on Linux/Windows?**
A: The hook works, but audio playback uses `afplay` (macOS only). For Linux, change to `aplay` or `mpg123`. For Windows, use `start` or PowerShell.

**Q: How much does this cost?**
A: Initial cache generation uses ElevenLabs API (~18 requests, <10,000 characters). After that, it's 100% free (cached audio only).

**Q: Can I disable it?**
A: Yes! Comment out or remove the Stop hook in `.claude/settings.json`:

```json
"Stop": [
  {
    "hooks": [
      // {
      //   "type": "command",
      //   "command": "python3 ~/Projects/Thanos/hooks/stop/thanos_voice.py",
      //   "timeout": 3000,
      //   "continueOnError": true
      // }
    ]
  }
]
```

---

*"The hardest choices require the strongest wills."*
