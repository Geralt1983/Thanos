# Thanos Voice Stop Hook Test Plan

## Overview
Test the Thanos-themed voice synthesis on Stop events with pre-cached messages.

## Test Environment Setup

### 1. Prerequisites
- ElevenLabs API key configured in `.env`
- Thanos voice ID configured
- Python 3.9+ with required dependencies
- macOS with `afplay` command available

### 2. Pre-cache Messages
```bash
# Run the pre-cache script to generate all Thanos messages
cd /Users/jeremy/Projects/Thanos
python3 tests/precache_thanos_messages.py
```

Expected output:
- 10+ MP3 files in `~/.thanos/audio-cache/`
- Each file should be 50-200KB
- Console output showing successful caching

## Test Cases

### Test 1: Message Selection Logic
**Objective:** Verify correct Thanos message is selected based on session context

**Test Steps:**
1. Check the message selection function exists in Stop hook
2. Verify it uses Python's `random.choice()` for selection
3. Confirm messages are contextually appropriate

**Expected Result:**
- Random selection from pre-defined Thanos quote pool
- No duplicate logic (each call can return different message)
- Messages are thematic and character-appropriate

**Verification:**
```python
# In Python REPL
from hooks.stop.thanos_voice import select_thanos_message
for i in range(10):
    print(select_thanos_message())
```

---

### Test 2: Cache Verification
**Objective:** Ensure all Thanos messages are pre-cached

**Test Steps:**
1. Run `ls -lh ~/.thanos/audio-cache/`
2. Check file count matches number of messages
3. Verify MD5 hashes are stable

**Expected Result:**
- All messages cached as `.mp3` files
- File naming: `<md5_hash>.mp3`
- Total cache size: ~1-2MB for all messages

**Verification:**
```bash
# Count cached files
ls -1 ~/.thanos/audio-cache/*.mp3 | wc -l

# Check cache stats
cd /Users/jeremy/Projects/Thanos/Shell/lib
python3 voice.py cache-stats
```

---

### Test 3: Stop Hook Integration
**Objective:** Verify Stop hook calls voice synthesis correctly

**Test Steps:**
1. Trigger a Stop event (exit Claude Code session)
2. Listen for audio playback
3. Check hook logs for errors

**Expected Result:**
- Thanos message plays during session stop
- No OpenRouter/LLM API calls
- Playback completes before hook exits
- Log entry confirms successful synthesis

**Verification:**
```bash
# Check Stop hook logs
tail -f ~/.thanos/voice-hook-debug.log

# Manual hook trigger test
echo "Test session stop" | /Users/jeremy/Projects/Thanos/hooks/stop/thanos_voice.py
```

---

### Test 4: No-Cache Flag Removed
**Objective:** Confirm `_no_cache` flag is NOT set for Stop events

**Test Steps:**
1. Review voice.py synthesize() calls in Stop hook
2. Verify `cache=True` is used (default behavior)
3. Check no `_no_cache` parameter is passed

**Expected Result:**
- All Stop hook voice synthesis uses caching
- Cache hits on subsequent Stop events
- Log shows "Cache hit for: ..." message

**Verification:**
```bash
# Trigger multiple stops and check for cache hits
grep "Cache hit" ~/.thanos/voice-hook-debug.log
```

---

### Test 5: No OpenRouter Calls
**Objective:** Ensure no LLM API calls during Stop events

**Test Steps:**
1. Set up network monitoring or check API logs
2. Trigger Stop event
3. Verify no outbound requests to OpenRouter

**Expected Result:**
- Zero OpenRouter API calls
- Zero ElevenLabs API calls (using cache)
- Fast playback (<500ms from trigger to sound)

**Verification:**
```bash
# Check for API calls in logs
grep -i "openrouter\|elevenlabs" ~/.thanos/*.log
```

---

### Test 6: Audio Quality
**Objective:** Verify audio output is clear and properly formatted

**Test Steps:**
1. Listen to cached audio files manually
2. Check audio properties (sample rate, bitrate)
3. Verify volume is appropriate

**Expected Result:**
- Clear speech, no distortion
- Consistent volume across all messages
- Deep, authoritative Thanos voice tone

**Verification:**
```bash
# Play a cached file manually
afplay ~/.thanos/audio-cache/<hash>.mp3

# Check audio properties
file ~/.thanos/audio-cache/<hash>.mp3
afinfo ~/.thanos/audio-cache/<hash>.mp3
```

---

### Test 7: Error Handling
**Objective:** Verify graceful degradation when cache/API fails

**Test Steps:**
1. Delete cache directory
2. Trigger Stop event without API key
3. Check error messages and fallback behavior

**Expected Result:**
- Hook completes without crashing
- Warning logged about missing API key
- Session finalization proceeds normally

**Verification:**
```bash
# Test without cache
rm -rf ~/.thanos/audio-cache
# Trigger stop event
# Restore cache
python3 tests/precache_thanos_messages.py
```

---

### Test 8: Performance Benchmark
**Objective:** Measure Stop hook execution time

**Test Steps:**
1. Time hook execution with cache
2. Time hook execution without cache
3. Compare against baseline (target: <500ms with cache)

**Expected Result:**
- Cached: <500ms total
- Uncached: <5s total (API call)
- No blocking delays in session shutdown

**Verification:**
```bash
# Benchmark with time command
time /Users/jeremy/Projects/Thanos/hooks/stop/thanos_voice.py
```

---

### Test 9: Message Variety
**Objective:** Ensure diverse message selection over multiple sessions

**Test Steps:**
1. Trigger Stop event 10 times
2. Record which message played each time
3. Verify distribution is reasonably random

**Expected Result:**
- At least 5 different messages in 10 stops
- No obvious pattern or bias
- All messages eventually played

**Verification:**
```python
# Statistical test
from collections import Counter
messages = []
for i in range(100):
    msg = select_thanos_message()
    messages.append(msg[:30])  # First 30 chars
print(Counter(messages))
```

---

### Test 10: Integration with Session Lifecycle
**Objective:** Verify voice synthesis doesn't interfere with session cleanup

**Test Steps:**
1. Trigger Stop with orphaned processes
2. Verify cleanup happens after voice
3. Check transcript saving completes

**Expected Result:**
- Voice plays asynchronously (doesn't block)
- Session data saved before hook exits
- Cleanup completes successfully

**Verification:**
```bash
# Check session files created
ls -lh ~/.claude/History/Sessions/

# Check cleanup log
grep "Cleaned up" ~/.thanos/*.log
```

---

## Test Execution Checklist

- [ ] Test 1: Message Selection Logic
- [ ] Test 2: Cache Verification
- [ ] Test 3: Stop Hook Integration
- [ ] Test 4: No-Cache Flag Removed
- [ ] Test 5: No OpenRouter Calls
- [ ] Test 6: Audio Quality
- [ ] Test 7: Error Handling
- [ ] Test 8: Performance Benchmark
- [ ] Test 9: Message Variety
- [ ] Test 10: Integration with Session Lifecycle

## Success Criteria

All tests must pass with:
- ✅ No errors or exceptions
- ✅ Audio playback works consistently
- ✅ Cache is used correctly (no redundant API calls)
- ✅ Stop hook completes in <1 second
- ✅ Session data saved correctly
- ✅ Thanos voice is recognizable and thematic

## Regression Testing

After any changes to:
- `voice.py` - Re-run Tests 2, 4, 5, 6, 8
- Stop hook - Re-run Tests 3, 7, 10
- Message selection - Re-run Tests 1, 9

## Known Limitations

1. **macOS Only:** Uses `afplay` command (Linux/Windows need alternatives)
2. **API Key Required:** First-time setup needs valid ElevenLabs key
3. **Network Dependency:** Initial cache generation requires internet
4. **Async Playback:** Audio may continue after hook exits (background process)
