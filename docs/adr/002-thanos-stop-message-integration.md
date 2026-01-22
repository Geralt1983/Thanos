# ADR 002: Thanos Stop Message Integration with cc-hooks

## Context

The cc-hooks plugin currently generates contextual completion messages for Stop events using OpenRouter API calls. These messages are dynamic, based on transcript analysis of the user's request and Claude's response. We want to inject Thanos-themed messages while maintaining this contextual intelligence, but with a hybrid caching approach: cached messages for low-energy states, dynamic OpenRouter calls for high-energy states.

## Current Implementation Analysis

### 1. Stop Event Flow

```
Stop Event Trigger (hooks.py)
    ↓
send_to_api() → API Server
    ↓
API processes event (server.py)
    ↓
announce_event() in tts_announcer.py
    ↓
_prepare_text_for_event()
    ↓
[Stop Event Detected]
    ↓
extract_conversation_context(transcript_path)
    ↓
generate_completion_message_if_available()
    ↓
OpenRouter API Call (contextual message)
    ↓
Set _no_cache = True
    ↓
TTS Provider (gtts/elevenlabs)
    ↓
Checks _no_cache flag
    ↓
Generates temporary audio (no caching)
```

### 2. Key Components

#### transcript_parser.py
**Location:** `~/.claude/plugins/cache/cc-hooks-plugin/cc-hooks-plugin/1.0.12/utils/transcript_parser.py`

**Responsibilities:**
- Parses JSONL transcript files from Claude Code sessions
- Extracts last user prompt and Claude response
- Handles Stop event context (only considers messages AFTER last Stop event)
- Tracks processed messages via hash to avoid duplicate processing
- Stores tracking files in `/tmp/cc-hooks-transcripts/`

**Key Functions:**
```python
extract_conversation_context(transcript_path) -> ConversationContext
    # Returns: {last_user_prompt, last_claude_response, session_id}
    # Returns empty context if no meaningful conversation found
```

**Duplicate Prevention:**
- Generates hash: `SHA256(timestamp + msg_type + message_content)[:16]`
- Stores: `/tmp/cc-hooks-transcripts/last-processed-{session_id}.txt`
- Skips if current message hash == last processed hash

#### openrouter_service.py
**Location:** `~/.claude/plugins/cache/cc-hooks-plugin/cc-hooks-plugin/1.0.12/utils/openrouter_service.py`

**Responsibilities:**
- Wraps OpenRouter API (OpenAI SDK with custom base_url)
- Handles translation AND contextual message generation
- Uses system prompts to guide LLM behavior
- Supports session-specific overrides for `contextual_stop` flag

**Key Functions:**
```python
generate_completion_message_if_available(
    session_id: str,
    user_prompt: Optional[str],
    claude_response: Optional[str],
    target_language: str = "en",
    fallback_message: str = "Task completed successfully",
    override_contextual_stop: Optional[bool] = None
) -> str
```

**Authorization Logic:**
- If `override_contextual_stop` is provided → Session-specific mode (only check API key)
- If `override_contextual_stop` is None → Global mode (check `enabled` flag + API key)
- Fallback to `fallback_message` if OpenRouter unavailable

**System Prompt:** `COMPLETION_SYSTEM_PROMPT`
```
You are a helpful AI assistant specialized in generating natural, contextually-aware
completion messages for Claude Code sessions.

Task: Generate a short, friendly completion message (5-15 words) that acknowledges
what the user requested and what action was taken.

Rules:
- Be conversational and natural
- Reference specific actions or context when available
- Keep it brief (5-15 words)
- Don't use emojis or special characters
- Use appropriate language based on the conversation context
```

#### tts_announcer.py
**Location:** `~/.claude/plugins/cache/cc-hooks-plugin/cc-hooks-plugin/1.0.12/utils/tts_announcer.py`

**Responsibilities:**
- Coordinates TTS generation for all hook events
- Special handling for Stop events (contextual messages)
- Sets `_no_cache` flag for dynamic content
- Cleans text for TTS (removes markdown, camelCase conversion)

**Key Logic:**
```python
def _prepare_text_for_event(hook_event_name, event_data, language, session_settings):
    if hook_event_name == "Stop":
        # Extract conversation context from transcript
        context = extract_conversation_context(transcript_path)

        # Get session-specific contextual_stop setting
        override = session_settings.get("openrouter_contextual_stop")

        # Generate contextual completion message
        message = generate_completion_message_if_available(
            session_id,
            user_prompt,
            claude_response,
            target_language,
            fallback="Task completed successfully",
            override_contextual_stop=override
        )

        # Mark as no-cache in event_data
        enhanced_event_data["_no_cache"] = True

        return message
```

**Text Cleaning:**
```python
def _clean_text_for_tts(text: str) -> str:
    # Removes backticks, markdown formatting
    # Converts camelCase to "camel Case"
    # Converts to lowercase for better TTS pronunciation
    # Removes multiple spaces
```

### 3. The _no_cache Flag

**Purpose:** Prevent caching of dynamic, contextual messages that should be regenerated each time.

**Flow:**
1. **Set in tts_announcer.py (line 562):**
   ```python
   if hook_event_name == "Stop" or hook_event_name == "PreToolUse":
       enhanced_event_data["_no_cache"] = True
   ```

2. **Read in TTS providers:**
   - **gtts_provider.py (line 77):**
     ```python
     no_cache = event_data.get("_no_cache", False)

     if self.cache_enabled and not no_cache and cached_file.exists():
         return cached_file  # Use cache

     if self.cache_enabled and not no_cache:
         tts.save(str(cached_file))  # Save to cache
     else:
         temp_file = Path(tempfile.mktemp(suffix=".mp3"))
         tts.save(str(temp_file))  # Temporary file
     ```

   - **elevenlabs_provider.py (line 123):**
     ```python
     no_cache = event_data.get("_no_cache", False)

     if self.cache_enabled and not no_cache and cached_file.exists():
         return cached_file  # Use cache

     # Generate audio...

     if self.cache_enabled and not no_cache:
         # Write to cache
     else:
         # Write to temp file
     ```

**Key Insight:** The flag completely bypasses caching. Audio is generated every time and stored in temporary files.

### 4. Configuration System

**Global Config (config.py):**
```python
@dataclass
class Config:
    openrouter_enabled: bool = False
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_contextual_stop: bool = False
    openrouter_contextual_pretooluse: bool = False
```

**Session-Specific Overrides (hooks.py SessionStart):**
```python
def register_session(session_id, claude_pid, port):
    payload = {
        "session_id": session_id,
        "openrouter_contextual_stop": os.getenv("CC_OPENROUTER_CONTEXTUAL_STOP", "").lower() == "true",
        "openrouter_contextual_pretooluse": os.getenv("CC_OPENROUTER_CONTEXTUAL_PRETOOLUSE", "").lower() == "true",
        # ... other settings
    }
```

**Priority:**
- Session settings (from `CC_*` env vars) override global config
- Allows per-session customization

## Proposed Integration Points

### Option 1: Inject at OpenRouter Service Layer (RECOMMENDED)

**Location:** `openrouter_service.py::generate_completion_message_if_available()`

**Advantages:**
- ✅ Single injection point for all contextual messages
- ✅ Can access full conversation context (user prompt + Claude response)
- ✅ Can check Oura readiness score before deciding
- ✅ Maintains existing fallback logic
- ✅ Works with existing session-specific overrides

**Implementation:**
```python
def generate_completion_message_if_available(...):
    # [Existing authorization checks]

    # NEW: Thanos integration
    try:
        from thanos_integration import get_thanos_completion_message

        thanos_message = get_thanos_completion_message(
            user_prompt=user_prompt,
            claude_response=claude_response,
            session_id=session_id,
            readiness_score=get_oura_readiness()  # From WorkOS MCP
        )

        if thanos_message:
            # Thanos provided a message (either cached or dynamic)
            return thanos_message
    except ImportError:
        pass  # Thanos integration not available

    # [Existing OpenRouter API call logic]
```

**Thanos Integration Module (`thanos_integration.py`):**
```python
THANOS_CACHED_MESSAGES = {
    "low_energy": [
        "The snap is complete. Rest now.",
        "A small price to pay for salvation. Good work.",
        "The hardest choices require the strongest wills. You delivered.",
        "Destiny fulfilled. The work is done.",
        "Perfect balance achieved. Well done."
    ],
    "high_energy": None  # Will use OpenRouter for dynamic messages
}

def get_thanos_completion_message(
    user_prompt: str,
    claude_response: str,
    session_id: str,
    readiness_score: int
) -> Optional[str]:
    """
    Returns Thanos-themed completion message based on energy level.

    Low energy (<75): Return cached Thanos message (random selection)
    High energy (>=75): Return None to trigger OpenRouter dynamic generation
    """
    if readiness_score < 75:
        # Low energy: Use cached Thanos messages
        import random
        message = random.choice(THANOS_CACHED_MESSAGES["low_energy"])
        logger.info(f"Using cached Thanos message (readiness={readiness_score}): {message}")
        return message
    else:
        # High energy: Let OpenRouter generate contextual message
        logger.info(f"High energy (readiness={readiness_score}), using OpenRouter for dynamic message")
        return None  # Signal to use OpenRouter
```

**_no_cache Handling:**
When using cached Thanos messages, we should NOT set `_no_cache = True` since the message is the same every time. The TTS provider can cache the audio.

**Changes Required:**
1. Create `thanos_integration.py` module in cc-hooks utils
2. Modify `openrouter_service.py::generate_completion_message_if_available()`
3. Add Oura readiness score retrieval (via WorkOS MCP or direct Oura MCP)
4. Update `tts_announcer.py` to conditionally set `_no_cache` based on message source

### Option 2: Inject at TTS Announcer Layer

**Location:** `tts_announcer.py::_prepare_text_for_event()`

**Advantages:**
- ✅ Direct control over final message before TTS
- ✅ Can modify _no_cache flag based on message type
- ✅ Simpler integration (no OpenRouter dependency)

**Disadvantages:**
- ❌ Doesn't have access to OpenRouter for high-energy dynamic messages
- ❌ Requires duplicating OpenRouter integration at a different layer
- ❌ Less maintainable

### Option 3: Custom TTS Provider

**Location:** New `thanos_provider.py` in `utils/tts_providers/`

**Advantages:**
- ✅ Clean separation of Thanos logic
- ✅ Can be enabled/disabled like other providers
- ✅ Follows existing provider pattern

**Disadvantages:**
- ❌ Doesn't integrate with OpenRouter contextual message generation
- ❌ Only handles audio, not message generation
- ❌ Wrong layer for business logic

## Recommended Approach

**Hybrid Integration: OpenRouter Service Layer + Thanos Module**

### Implementation Steps

1. **Create Thanos Integration Module**
   - Location: `/Users/jeremy/Projects/Thanos/integrations/cc-hooks/thanos_stop_messages.py`
   - Exports: `get_thanos_completion_message(user_prompt, claude_response, session_id, readiness_score)`
   - Returns: Cached message (low energy) or None (high energy → use OpenRouter)

2. **Modify OpenRouter Service**
   - File: `~/.claude/plugins/cache/cc-hooks-plugin/cc-hooks-plugin/1.0.12/utils/openrouter_service.py`
   - Function: `generate_completion_message_if_available()`
   - Add Thanos integration call before OpenRouter API
   - Early return if Thanos provides message

3. **Update TTS Announcer**
   - File: `~/.claude/plugins/cache/cc-hooks-plugin/cc-hooks-plugin/1.0.12/utils/tts_announcer.py`
   - Function: `_prepare_text_for_event()`
   - Conditionally set `_no_cache` flag:
     - If readiness_score >= 75 → `_no_cache = True` (dynamic OpenRouter)
     - If readiness_score < 75 → `_no_cache = False` (cached Thanos messages)

4. **Add Oura Integration**
   - Use WorkOS MCP `workos_get_energy()` or Oura MCP `oura__get_daily_readiness()`
   - Cache readiness score for session (avoid repeated API calls)
   - Fallback to `readiness_score = 70` if unavailable

### Cache Strategy

**Low Energy (<75) - Cached Thanos Messages:**
- Message is pre-written, selected randomly
- TTS audio CAN be cached (same message = same audio)
- Set `_no_cache = False`
- Cache key: `SHA256(message_text + language + voice_id)`
- First generation takes ~2-3 seconds, subsequent plays are instant

**High Energy (>=75) - Dynamic OpenRouter:**
- Message is generated via OpenRouter API
- TTS audio should NOT be cached (unique every time)
- Set `_no_cache = True`
- Temporary audio file deleted after use

### File Structure

```
Thanos/
└── integrations/
    └── cc-hooks/
        ├── __init__.py
        ├── thanos_stop_messages.py    # Core logic
        ├── message_templates.py       # Thanos message variations
        └── README.md                  # Integration documentation

~/.claude/plugins/cache/cc-hooks-plugin/cc-hooks-plugin/1.0.12/
└── utils/
    ├── openrouter_service.py          # MODIFY: Add Thanos integration call
    └── tts_announcer.py               # MODIFY: Conditional _no_cache flag
```

### Message Templates

```python
# message_templates.py

THANOS_STOP_MESSAGES = {
    "completion_low_energy": [
        "The snap is complete. Rest now.",
        "A small price to pay for salvation. Good work.",
        "The hardest choices require the strongest wills. You delivered.",
        "Destiny fulfilled. The work is done.",
        "Perfect balance achieved. Well done.",
        "The universe is balanced once more.",
        "Your sacrifice is complete. Excellent.",
        "Reality bends to your will. Task complete.",
        "The stones have spoken. Work is finished.",
        "Inevitable. And now it is done."
    ]
}

def get_random_thanos_message(category: str = "completion_low_energy") -> str:
    """Get random Thanos message from category."""
    import random
    return random.choice(THANOS_STOP_MESSAGES[category])
```

## Technical Constraints

1. **Python Version:** >=3.12 (uv script dependencies)
2. **Dependencies:** Keep minimal, use existing WorkOS/Oura MCP
3. **Error Handling:** Must gracefully fall back to OpenRouter if Thanos integration fails
4. **Logging:** Use cc-hooks colored_logger for consistency
5. **Session Isolation:** Each Claude session has its own server instance

## Success Criteria

- ✅ Stop events with readiness <75 use cached Thanos messages
- ✅ Stop events with readiness >=75 use dynamic OpenRouter messages
- ✅ Cached messages have instant TTS playback (no generation delay)
- ✅ Dynamic messages still get contextual intelligence
- ✅ Fallback to OpenRouter if Thanos integration unavailable
- ✅ No breaking changes to existing cc-hooks functionality

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Oura API unavailable | Default to `readiness_score = 70` (use cached) |
| Thanos module import fails | Catch ImportError, fall back to OpenRouter |
| Message selection breaks | Validate message list on startup, use fallback |
| Cache key collision | Use full SHA256, not just [:16] for Thanos messages |
| Session settings override | Respect `CC_OPENROUTER_CONTEXTUAL_STOP` env var |

## Future Enhancements

1. **Multiple Message Tiers:**
   - Very low energy (<60): "You're exhausted. Task complete."
   - Low energy (60-74): Current Thanos messages
   - High energy (>=75): Dynamic OpenRouter

2. **Context-Aware Selection:**
   - Parse `user_prompt` and `claude_response` for keywords
   - Select Thanos messages that match task type
   - Example: Code tasks → "Reality bends to your will. Task complete."

3. **Learning System:**
   - Track which messages users react positively to
   - Store in WorkOS brain_dump or claude-mem
   - Adjust selection probabilities over time

4. **Voice Modulation:**
   - Low energy → Slower, deeper voice
   - High energy → Normal voice
   - Requires ElevenLabs voice settings API

## References

- [cc-hooks Documentation](~/.claude/plugins/cache/cc-hooks-plugin/cc-hooks-plugin/1.0.12/README.md)
- [WorkOS MCP](~/Projects/Thanos/mcp-servers/workos-mcp/)
- [Oura MCP](~/Projects/Thanos/mcp-servers/oura-mcp/)
- [CLAUDE.md Thanos Identity](~/Projects/Thanos/CLAUDE.md)
