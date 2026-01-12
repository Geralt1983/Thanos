# Thanos Runtime Error Troubleshooting Guide

Comprehensive guide for diagnosing and resolving common runtime errors in Thanos, including API failures, cache corruption, and hook execution issues.

## Overview

Thanos implements robust error handling across three major subsystems:

- **API Error Handling**: Automatic fallback chain for LLM provider failures
- **Cache Corruption Recovery**: Silent failure with automatic cleanup for cache issues
- **Hook Error Management**: Fail-safe lifecycle event handling that never interrupts workflow
- **Graceful Degradation**: Systems continue operating even when individual components fail
- **Comprehensive Logging**: Detailed error context for debugging and monitoring

## Quick Reference

Common issues and their resolutions:

| Symptom | Automatic Behavior | User Action Required |
|---------|-------------------|---------------------|
| API rate limit hit | Immediately tries next model in fallback chain | None - verify fallback chain configured |
| API connection fails | Falls back to next model | Check network, verify API keys |
| All fallback models fail | Request fails with last error | Check API keys, quotas, network |
| Cache corruption detected | Treats as cache miss, continues normally | None - corrupted files cleaned automatically |
| Cache directory full | Write may fail silently | Monitor disk space, clear old cache |
| Hook execution error | Logs error, continues workflow | Check `~/.claude/logs/hooks.log` for details |
| Missing morning context | Silent failure, session starts normally | Verify `State/Today.md` exists |
| Session log not created | Silent failure, no session history | Check `History/Sessions/` permissions |

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Thanos Orchestrator                        │
└────────┬──────────────────┬─────────────────┬───────────────┘
         │                  │                 │
         ▼                  ▼                 ▼
┌─────────────────┐  ┌──────────────┐  ┌──────────────────┐
│  LiteLLM Client │  │ Response     │  │  Hook System     │
│                 │  │ Cache        │  │                  │
│  ┌───────────┐  │  │              │  │  ┌────────────┐  │
│  │ Fallback  │  │  │  ┌────────┐  │  │  │  Fail-Safe │  │
│  │ Chain     │  │  │  │ Silent │  │  │  │  Execution │  │
│  │           │  │  │  │ Failure│  │  │  │            │  │
│  │ Model 1   │  │  │  └────────┘  │  │  └────────────┘  │
│  │ Model 2   │  │  │              │  │                  │
│  │ Model 3   │  │  │  ┌────────┐  │  │  ┌────────────┐  │
│  └───────────┘  │  │  │ Auto   │  │  │  │  Error Log │  │
│                 │  │  │ Cleanup│  │  │  │  to File   │  │
│  Errors: Try    │  │  └────────┘  │  │  └────────────┘  │
│  next model     │  │              │  │                  │
└─────────────────┘  └──────────────┘  └──────────────────┘
```

---

# API Error Handling

## Overview

The LiteLLM client implements a **fallback chain mechanism** that automatically tries alternative models when API calls fail. Unlike traditional retry logic, this system immediately moves to the next configured model on any failure.

### How It Works

1. **Fallback Chain Configuration** (`config/api.json`):
   ```json
   {
     "litellm": {
       "fallback_chain": [
         "claude-opus-4-5-20251101",
         "claude-sonnet-4-20250514"
       ]
     }
   }
   ```

2. **Chain Construction**:
   - If requested model is not in the chain, it's automatically prepended
   - Example: Request for `claude-3-5-haiku` → Chain becomes:
     ```
     ["claude-3-5-haiku", "claude-opus-4-5-20251101", "claude-sonnet-4-20250514"]
     ```

3. **Execution Flow**:
   - Try first model in chain
   - On any error → immediately try next model
   - Continue until success or chain exhausted
   - If all fail → raise last error

**Important**: There is NO exponential backoff or waiting between attempts. The system immediately tries the next model.

### Fallback Chain vs. Retry Logic

**Critical Distinction**: The fallback chain is **NOT retry logic** - these are separate mechanisms with different purposes.

| Feature | Fallback Chain | Retry Logic |
|---------|---------------|-------------|
| **What it does** | Tries different models | Retries same model |
| **When triggered** | On any API error | On transient failures only |
| **Delay between attempts** | None (immediate) | Exponential backoff |
| **Purpose** | Alternative models/providers | Handle temporary issues |
| **Location** | LiteLLM Client | External RetryMiddleware |
| **User Action** | Configure in `config/api.json` | Configured separately |

**How They Work Together**:

```
User Request
    │
    ▼
┌─────────────────────┐
│  Fallback Chain     │  ← Tries different MODELS
│  (Client-level)     │     (immediate, no delay)
└──────────┬──────────┘
           │
           ▼
     ┌─────────┐
     │ Model 1 │ → Fail → Try Model 2 → Fail → Try Model 3 → Success
     └─────────┘
           │
           ▼
   ┌─────────────────┐
   │ Retry Logic     │  ← Retries SAME model
   │ (Middleware)    │     (with backoff delay)
   └─────────────────┘
```

**Example Scenario**:
```
1. Request sent to claude-opus-4-5-20251101
2. Retry Middleware: Tries same model 3 times with backoff
3. All retries fail → RateLimitError raised
4. Fallback Chain: Immediately tries claude-sonnet-4-20250514
5. Success → Response returned to user
```

**Key Takeaway**:
- **Fallback** = Model-level (try different models)
- **Retry** = Request-level (retry same request)
- Both work together for maximum reliability

## API Error Types

### RateLimitError

**Symptom**: API provider returns 429 status code indicating rate limit exceeded.

**Cause**: Too many requests sent to the API provider in a short time period.

**Automatic Behavior**:
- Immediately tries next model in fallback chain
- No waiting or backoff delay
- Chain continues until success or exhaustion

**User Action Required**:
- **If single provider**: Wait for rate limit to reset, or upgrade API tier
- **If multiple providers**: Configure fallback chain with models from different providers
- **Prevention**: Monitor API usage, implement request throttling at application level

**Example Log Output**:
```
[ERROR] LiteLLM call failed for claude-opus-4-5-20251101: Rate limit exceeded
[INFO] Trying fallback model: claude-sonnet-4-20250514
```

**Resolution**:
1. Check current fallback chain configuration:
   ```bash
   cat config/api.json | jq '.litellm.fallback_chain'
   ```

2. Add models from different providers to fallback chain:
   ```json
   {
     "litellm": {
       "fallback_chain": [
         "claude-opus-4-5-20251101",        // Anthropic
         "gpt-4-turbo",                      // OpenAI
         "claude-sonnet-4-20250514"          // Anthropic fallback
       ]
     }
   }
   ```

3. Verify all API keys are configured:
   ```bash
   # Check environment variables
   echo $ANTHROPIC_API_KEY
   echo $OPENAI_API_KEY
   ```

### APIConnectionError

**Symptom**: Network connection fails, timeouts, or DNS resolution errors.

**Cause**: Network issues, firewall blocks, proxy problems, or API service outage.

**Automatic Behavior**:
- Immediately tries next model in fallback chain
- No retry with backoff (just moves to next model)
- Request fails if all models unreachable

**User Action Required**:
- Check network connectivity
- Verify firewall/proxy settings
- Check API service status pages
- Ensure correct API endpoints configured

**Example Error**:
```
[ERROR] Connection failed: HTTPSConnectionPool(host='api.anthropic.com', port=443):
        Max retries exceeded with url: /v1/messages
```

**Resolution**:
1. Test network connectivity:
   ```bash
   curl -I https://api.anthropic.com/v1/messages
   curl -I https://api.openai.com/v1/chat/completions
   ```

2. Check for proxy requirements:
   ```bash
   echo $HTTP_PROXY
   echo $HTTPS_PROXY
   ```

3. Verify DNS resolution:
   ```bash
   nslookup api.anthropic.com
   nslookup api.openai.com
   ```

4. Review system logs for network errors:
   ```bash
   tail -f ~/.claude/logs/thanos.log | grep -i "connection"
   ```

### APIStatusError

**Symptom**: API returns error status codes (4xx, 5xx).

**Cause**:
- **4xx**: Invalid request, authentication failure, malformed parameters
- **5xx**: API service error, temporary outage, overload

**Automatic Behavior**:
- All status errors treated equally
- Immediately tries next model in fallback chain
- No distinction between retriable (5xx) and non-retriable (4xx) errors

**User Action Required**:
- **401/403**: Check API keys, verify account status
- **400/422**: Review request parameters, check model availability
- **500/503**: API service issue, wait and retry or use different provider

**Example Errors**:
```
[ERROR] APIStatusError 401: Invalid API key
[ERROR] APIStatusError 503: Service temporarily unavailable
[ERROR] APIStatusError 400: Model 'invalid-model' not found
```

**Resolution**:

For **401 Unauthorized**:
```bash
# Verify API key is set and valid
echo $ANTHROPIC_API_KEY | cut -c1-10  # Shows first 10 chars
# Visit provider dashboard to verify key status
```

For **400 Bad Request**:
```bash
# Check available models in fallback chain match provider's current offerings
# Update config/api.json with correct model names
```

For **5xx Server Errors**:
```bash
# Check API status pages:
# - https://status.anthropic.com
# - https://status.openai.com
# Monitor logs for automatic recovery via fallback
tail -f ~/.claude/logs/thanos.log
```

### All Models Failed

**Symptom**: Request fails after exhausting entire fallback chain.

**Cause**:
- All providers experiencing issues
- All API keys invalid or quota exceeded
- Network completely down
- Misconfigured fallback chain

**Automatic Behavior**:
- Returns last error from final model in chain
- Request fails completely
- No automatic retry queue or persistence

**User Action Required**: Investigate and fix underlying issue.

**Example Error**:
```
[ERROR] All models in fallback chain failed
[ERROR] Last error: APIStatusError 401 from claude-sonnet-4-20250514
```

**Resolution**:
1. Check all API keys are valid:
   ```bash
   # Test each provider
   curl -H "x-api-key: $ANTHROPIC_API_KEY" https://api.anthropic.com/v1/messages
   curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
   ```

2. Verify account quotas and billing:
   - Check provider dashboards for usage limits
   - Verify billing information is current
   - Review rate limit status

3. Test fallback chain manually:
   ```bash
   # Enable debug logging to see each fallback attempt
   export LOG_LEVEL=DEBUG
   # Run your request and observe fallback behavior
   ```

4. Simplify fallback chain to known-working model:
   ```json
   {
     "litellm": {
       "fallback_chain": ["claude-sonnet-4-20250514"]  // Single known-working model
     }
   }
   ```

## API Error Prevention

### Configure Robust Fallback Chains

**Best Practice**: Use models from multiple providers

❌ **Bad** (all same provider):
```json
{
  "litellm": {
    "fallback_chain": [
      "claude-opus-4-5-20251101",
      "claude-sonnet-4-20250514",
      "claude-3-5-haiku-20241022"
    ]
  }
}
```

✅ **Good** (diverse providers):
```json
{
  "litellm": {
    "fallback_chain": [
      "claude-opus-4-5-20251101",    // Anthropic primary
      "gpt-4-turbo",                  // OpenAI fallback
      "claude-sonnet-4-20250514"      // Anthropic final fallback
    ]
  }
}
```

### Maintain Valid API Keys

**Best Practice**: Regularly verify API key validity

```bash
# Add to monitoring/health check script
#!/bin/bash
# test_api_keys.sh

test_anthropic() {
    curl -s -o /dev/null -w "%{http_code}" \
        -H "x-api-key: $ANTHROPIC_API_KEY" \
        -H "anthropic-version: 2023-06-01" \
        https://api.anthropic.com/v1/messages
}

test_openai() {
    curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $OPENAI_API_KEY" \
        https://api.openai.com/v1/models
}

echo "Anthropic: $(test_anthropic)"
echo "OpenAI: $(test_openai)"
```

### Monitor API Usage

**Best Practice**: Track usage to avoid rate limits

- Review provider dashboards regularly
- Set up billing alerts
- Monitor request patterns in logs
- Consider caching frequently-requested content

### Configuration File Location

**Primary Config**: `config/api.json`

**Environment Variables**:
- `ANTHROPIC_API_KEY`: Anthropic API key
- `OPENAI_API_KEY`: OpenAI API key
- `LITELLM_LOG_LEVEL`: Set to `DEBUG` for detailed logging

## Fallback Chain Behavior Details

### Silent Failures and Logging

**Important**: Individual model failures in the fallback chain are **silent by default**.

**What This Means**:
- When a model fails, the system immediately tries the next model
- No log entry is created for intermediate failures
- Only the final result (success or exhaustion) is visible
- You cannot see which models were tried or why they failed

**Automatic Behavior**:
- ✅ Seamless user experience
- ✅ No interruption on transient failures
- ❌ No visibility into failure patterns
- ❌ Hard to debug recurring issues

**User Action for Debugging**:

Enable verbose logging to see fallback chain progression:

```bash
# Set environment variable for detailed logging
export LITELLM_LOG_LEVEL=DEBUG

# Run your application
# You'll see detailed logs for each fallback attempt
```

**Example Debug Output**:
```
[DEBUG] Attempting model: claude-opus-4-5-20251101
[DEBUG] APIError: Rate limit exceeded
[DEBUG] Attempting fallback model: claude-sonnet-4-20250514
[DEBUG] Success with fallback model
```

**When to Enable Debug Logging**:
- Diagnosing rate limit patterns
- Understanding which models are failing
- Monitoring fallback chain effectiveness
- Troubleshooting persistent API issues

### Cache Behavior with Fallbacks

**Important**: Cache keys include the **originally requested model**, not the fallback model that actually processed the request.

**How Cache Works**:
1. Cache key calculated from: `(prompt, selected_model, parameters)`
2. Request for Model A fails → fallback to Model B succeeds
3. Response cached against Model A (not Model B)
4. Next identical request → cache lookup for Model A
5. Cache hit returns previous response

**Implications**:

❌ **Cache Miss After Fallback**:
```
Request 1: Model A → fails → Model B succeeds → cached as "Model A"
Request 2: Model A → cache miss (was cached as "Model A" but actually from Model B)
          → Model A tries again → may succeed or fallback
```

✅ **Cache Hit (Same Model)**:
```
Request 1: Model A → succeeds → cached as "Model A"
Request 2: Model A → cache hit → returns cached response
```

**Why This Matters**:
- Cache efficiency may be lower than expected after fallbacks
- Subsequent requests may retry failed models instead of using cache
- Cache doesn't "remember" which fallback model succeeded

**User Action**: None required - this is expected behavior. Be aware that fallback responses don't improve cache hit rates for the original model.

### Usage Tracking with Fallbacks

**Important**: Usage tracking records the **requested model**, not the fallback model that actually processed the request.

**How Tracking Works**:
```python
# User requests: claude-opus-4-5-20251101
# Actual model used: claude-sonnet-4-20250514 (after fallback)
# Tracked as: claude-opus-4-5-20251101 ← INCORRECT
```

**Implications**:

❌ **Inaccurate Cost Calculation**:
- Cost calculated for requested model, not actual model
- If fallback model has different pricing → cost tracking is wrong
- Budget monitoring may be inaccurate

❌ **No Fallback Visibility**:
- Usage stats don't show which model actually processed requests
- Can't identify fallback patterns from usage data
- Monitoring doesn't reflect actual provider usage

❌ **Token Attribution**:
- Tokens attributed to requested model
- Actual model's token usage not recorded
- Provider-specific statistics are incorrect

**User Action for Accurate Tracking**:

Currently, there's no built-in way to track actual fallback model usage. If accurate tracking is critical:

1. **Monitor Provider Dashboards**:
   ```bash
   # Check actual usage at provider level
   # - Anthropic: https://console.anthropic.com
   # - OpenAI: https://platform.openai.com/usage
   ```

2. **Enable Debug Logging** (see above) and parse logs for fallback patterns

3. **Consider Custom Logging** in production:
   - Log which model actually responds
   - Track fallback occurrences separately
   - Correlate with provider billing

**When This Matters**:
- Strict budget tracking required
- Billing reconciliation with providers
- Monitoring fallback frequency
- Understanding actual model usage patterns

---

# Cache Error Handling

## Overview

The Response Cache implements a **silent failure and automatic cleanup** strategy. Cache corruption never interrupts service - corrupted entries are treated as cache misses and automatically removed during cleanup cycles.

### Cache Storage

**Location**: `Memory/cache/` (relative to Thanos directory)

**Format**: Individual JSON files named by cache key:
```
Memory/cache/
├── a1b2c3d4e5f6.json
├── 1a2b3c4d5e6f.json
└── ...
```

**File Structure**:
```json
{
  "timestamp": "2026-01-11T20:30:00.123456",
  "model": "claude-sonnet-4-20250514",
  "response": "The actual cached response text..."
}
```

## Cache Corruption Detection

The cache automatically detects three types of corruption:

1. **JSON Decode Errors**: Invalid JSON syntax
2. **Missing Keys**: File missing required fields (`timestamp`, `model`, `response`)
3. **Invalid Values**: Unparseable timestamp format

## Cache Error Types

### Corrupted Cache File on Read

**Symptom**: No visible symptoms - system continues normally.

**Cause**:
- Interrupted write (process kill, power loss, disk full)
- Disk corruption or bad sectors
- External file modification
- Invalid JSON syntax

**Automatic Behavior**:
1. Corruption detected when reading cache file
2. Error silently caught (no logging)
3. Returns `None` (cache miss)
4. Original API request proceeds normally
5. Corrupted file remains until cleanup

**User Action Required**: None - system self-heals automatically.

**Example Internal Flow**:
```
1. Request for cached response
2. Read cache file → json.JSONDecodeError
3. Catch exception silently
4. Return None (cache miss)
5. Proceed with fresh API call
6. Cache new response (may overwrite corrupted file)
```

**Impact**:
- Slight performance degradation (extra API call)
- No service interruption
- Disk space consumed by corrupted file until cleanup

### Cache Corruption During Cleanup

**Symptom**: No visible symptoms - corrupted files silently removed.

**Cause**: Same as read corruption, detected during expiration cleanup.

**Automatic Behavior**:
1. `clear_expired()` iterates through cache files
2. Attempts to read each file
3. Corrupted files → exception caught
4. Corrupted file immediately deleted
5. Cleanup continues to next file

**User Action Required**: None - automatic cleanup.

**Cleanup Trigger**: When `ResponseCache.clear_expired()` is called (timing depends on system configuration).

**Impact**:
- Disk space recovered
- No logging or notification
- No way to track corruption incidents

### Disk Full During Cache Write

**Symptom**: Cache writes may fail silently or raise errors.

**Cause**: No disk space available for cache files.

**Automatic Behavior**:
- **NO automatic handling** - write errors propagate
- May create partial/corrupted cache files
- Could cause application errors

**User Action Required**: Free up disk space immediately.

**Resolution**:
1. Check disk space:
   ```bash
   df -h .
   ```

2. Identify large cache files:
   ```bash
   du -sh Memory/cache/
   ls -lhS Memory/cache/ | head -20  # Largest files
   ```

3. Clear all cache:
   ```bash
   rm -rf Memory/cache/*.json
   ```

4. Or clear old cache programmatically:
   ```python
   from Tools.litellm.response_cache import ResponseCache
   cache = ResponseCache(cache_path="Memory/cache", ttl_seconds=86400)
   cache.clear_expired()
   ```

### Permission Denied on Cache Directory

**Symptom**: Cache operations fail, potentially causing errors.

**Cause**: Insufficient permissions on `Memory/cache/` directory.

**Automatic Behavior**: None - permission errors propagate.

**User Action Required**: Fix permissions.

**Resolution**:
```bash
# Check current permissions
ls -ld Memory/cache/

# Fix permissions (user read/write)
chmod 755 Memory/cache/

# Verify
ls -ld Memory/cache/
```

## Cache Maintenance

### Manual Cache Cleanup

**When to clear cache**:
- Disk space running low
- Suspecting corrupted cache causing issues
- After configuration changes
- As part of troubleshooting

**Safe to clear**: Yes - cache is purely a performance optimization. Clearing cache does not affect functionality, only temporarily increases API usage.

**Methods**:

1. **Delete all cache**:
   ```bash
   rm -rf Memory/cache/*.json
   ```

2. **Clear expired entries only** (requires Python):
   ```python
   from pathlib import Path
   from Tools.litellm.response_cache import ResponseCache

   cache = ResponseCache(
       cache_path=Path("Memory/cache"),
       ttl_seconds=86400  # 24 hours
   )
   cache.clear_expired()
   print("Expired cache entries cleared")
   ```

3. **Clear cache older than specific date**:
   ```bash
   # Delete cache files older than 7 days
   find Memory/cache/ -name "*.json" -mtime +7 -delete
   ```

### Cache Monitoring

**Monitor disk space**:
```bash
# Add to cron or monitoring system
du -sh Memory/cache/ && df -h .
```

**Check cache file count**:
```bash
ls Memory/cache/*.json | wc -l
```

**Identify potential corruption** (requires manual inspection):
```bash
# Test JSON validity of all cache files
for f in Memory/cache/*.json; do
    jq empty "$f" 2>/dev/null || echo "Corrupted: $f"
done
```

### Cache Configuration

**TTL (Time-To-Live)**: Configured in `ResponseCache` initialization
- Default: Varies by usage
- Location: `Tools/litellm/response_cache.py`

**Cache Path**: `Memory/cache/` relative to Thanos directory

**No Configuration File**: Cache settings are hardcoded in source

## Cache Error Prevention

### Ensure Adequate Disk Space

❌ **Bad**: No monitoring, cache fills disk
```bash
# No space left
df -h .
# Filesystem  Size  Used  Avail  Capacity
# /dev/disk1  500G  500G     0B   100%
```

✅ **Good**: Regular monitoring and cleanup
```bash
# Monitor script
#!/bin/bash
CACHE_SIZE=$(du -sm Memory/cache/ | cut -f1)
if [ "$CACHE_SIZE" -gt 1000 ]; then  # 1GB threshold
    echo "Cache size: ${CACHE_SIZE}MB - clearing old entries"
    find Memory/cache/ -name "*.json" -mtime +7 -delete
fi
```

### Graceful Shutdown

❌ **Bad**: Kill processes during cache writes
```bash
kill -9 $(pgrep python)  # Force kill may corrupt cache
```

✅ **Good**: Allow graceful shutdown
```bash
kill -TERM $(pgrep python)  # Graceful shutdown
# Or use Ctrl+C in terminal
```

### Avoid External Modifications

❌ **Bad**: Manually editing cache files

✅ **Good**: Clear entire cache or use programmatic access

---

# Hook Error Handling

## Overview

The Thanos hook system implements a **fail-safe design** where all errors are caught, logged, and never propagate to Claude Code. Hooks are "best effort" enhancements that must never disrupt the user's workflow.

### Hook Philosophy

**Core Principle**: Hooks must never fail the operation.

**Why**:
- Hooks are lifecycle events, not critical operations
- Hook failures shouldn't disrupt Claude Code workflow
- User experience must be uninterrupted
- Debugging information is logged but doesn't block execution

### Hook Types

1. **morning-brief**: Provides quick context at session start
2. **session-end**: Logs session summary to History/Sessions/

## Hook Error Management

### Error Capture and Logging

**All hook errors are**:
- ✅ Caught at top level (no propagation)
- ✅ Logged to `~/.claude/logs/hooks.log`
- ✅ Silently handled (no interruption)
- ✅ Exit with code 0 (success)

**Logging Location**: `~/.claude/logs/hooks.log`

**Log Format**:
```
[2026-01-11 20:30:45] [thanos-orchestrator] morning-brief error: StateReader failed
[2026-01-11 20:31:10] [thanos-orchestrator] Unknown hook event: invalid-event
```

### Multi-Level Error Handling

The hook system has **three layers** of error handling:

```
Layer 1: Hook Logic (try/except around specific operations)
         ↓ (error) → Log to hooks.log
         ↓
Layer 2: Hook Function (try/except around entire hook)
         ↓ (error) → Log to hooks.log, pass
         ↓
Layer 3: Log Function (try/except in _log_hook_error)
         ↓ (error) → Fallback to stderr
         ↓
Always: Exit with code 0 (success)
```

This ensures hooks **never** fail the Claude Code lifecycle.

## Hook Error Types

### Morning Brief Hook Errors

**Purpose**: Display quick context at session start

**Symptom**: No morning context shown, session starts normally

**Common Causes**:
- Missing `State/Today.md` file
- StateReader import failure
- Corrupted state files
- JSON parsing errors

**Automatic Behavior**:
1. Error caught and logged to `~/.claude/logs/hooks.log`
2. No morning context displayed
3. Claude Code session starts normally
4. User may not notice anything wrong

**User Action Required**: Only if morning context is desired.

**Resolution**:
1. Check hook log for errors:
   ```bash
   tail -20 ~/.claude/logs/hooks.log
   ```

2. Look for morning-brief errors:
   ```bash
   grep "morning-brief" ~/.claude/logs/hooks.log
   ```

3. Verify State directory structure:
   ```bash
   ls -la State/
   cat State/Today.md  # Should exist and be readable
   ```

4. Test hook manually:
   ```bash
   python Tools/thanos_orchestrator.py hook morning-brief
   # Should output JSON with context or show error in hooks.log
   ```

5. Fix common issues:
   ```bash
   # Create missing Today.md
   mkdir -p State
   echo "# Today\n\n## Tasks\n" > State/Today.md

   # Verify StateReader works
   python -c "from Tools.state_reader import StateReader; print('OK')"
   ```

### Session End Hook Errors

**Purpose**: Log session summary to `History/Sessions/`

**Symptom**: No session log created, session ends normally

**Common Causes**:
- Permission denied on History directory
- Disk full
- StateReader errors when capturing context
- File write failures

**Automatic Behavior**:
1. Error caught and logged to `~/.claude/logs/hooks.log`
2. No session log file created
3. Claude Code session ends normally
4. User exits without errors
5. Session history may be incomplete

**User Action Required**: Only if session logging is desired.

**Resolution**:
1. Check hook log:
   ```bash
   tail -20 ~/.claude/logs/hooks.log | grep "session-end"
   ```

2. Verify History directory permissions:
   ```bash
   ls -ld History/Sessions/
   # Should be drwxr-xr-x or similar
   ```

3. Fix permissions:
   ```bash
   mkdir -p History/Sessions
   chmod 755 History/Sessions
   ```

4. Check disk space:
   ```bash
   df -h .
   ```

5. Test hook manually:
   ```bash
   python Tools/thanos_orchestrator.py hook session-end
   # Check if session log created
   ls -lt History/Sessions/ | head -5
   ```

6. Review recent session logs:
   ```bash
   ls -lt History/Sessions/*.md | head -5
   cat History/Sessions/session_YYYYMMDD_HHMMSS.md
   ```

### Hook Log File Write Errors

**Symptom**: Stderr messages about logging failures

**Cause**: Cannot write to `~/.claude/logs/hooks.log`

**Common Causes**:
- Permission denied on `~/.claude/logs/` directory
- Disk full
- Filesystem read-only

**Automatic Behavior**:
- First attempts to write to `~/.claude/logs/hooks.log`
- On OSError → writes to stderr
- On any other error → writes critical error to stderr
- Hook still exits with code 0

**User Action Required**: Fix logging directory permissions.

**Resolution**:
1. Check stderr output for hook logging errors:
   ```
   [hooks] Cannot write to log file: [Errno 13] Permission denied
   ```

2. Fix permissions:
   ```bash
   mkdir -p ~/.claude/logs
   chmod 755 ~/.claude/logs
   ```

3. Check disk space:
   ```bash
   df -h ~
   ```

4. Verify log file writeable:
   ```bash
   touch ~/.claude/logs/hooks.log
   echo "test" >> ~/.claude/logs/hooks.log
   ```

### Unknown Hook Events

**Symptom**: Hook called with invalid event name

**Cause**: Misconfiguration or unsupported hook event

**Automatic Behavior**:
1. Logs `Unknown hook event: <event-name>`
2. No output produced
3. Exits cleanly with code 0

**User Action Required**: None - indicates configuration issue.

**Resolution**:
1. Check hook log:
   ```bash
   grep "Unknown hook event" ~/.claude/logs/hooks.log
   ```

2. Valid hook events are:
   - `morning-brief`
   - `session-end`

3. Verify Claude Code configuration if custom hooks configured

## Hook Debugging

### View Hook Logs in Real-Time

```bash
# Monitor hook activity during Claude Code session
tail -f ~/.claude/logs/hooks.log
```

### Test Hooks Manually

```bash
# Test morning-brief hook
python Tools/thanos_orchestrator.py hook morning-brief

# Test session-end hook
python Tools/thanos_orchestrator.py hook session-end

# Check for errors in log
tail -20 ~/.claude/logs/hooks.log
```

### Enable Debug Mode

Hooks are designed to be fast and don't support debug mode, but you can:

1. **Add temporary logging**:
   ```python
   # In Tools/thanos_orchestrator.py handle_hook()
   # Add debug prints (temporary, for debugging only)
   ```

2. **Check StateReader directly**:
   ```bash
   python -c "
   from Tools.state_reader import StateReader
   from pathlib import Path
   reader = StateReader(Path('State'))
   ctx = reader.get_quick_context()
   print(ctx)
   "
   ```

### Verify Directory Structure

```bash
# Thanos directory should have:
ls -la
# drwxr-xr-x  State/           # State files for morning brief
# drwxr-xr-x  History/         # Session logs
# drwxr-xr-x  History/Sessions/  # Individual session files
# drwxr-xr-x  Memory/          # Cache and other memory

# Verify each directory exists and is writable
for dir in State History History/Sessions Memory; do
    if [ -d "$dir" ]; then
        echo "✓ $dir exists"
    else
        echo "✗ $dir missing - creating..."
        mkdir -p "$dir"
    fi
done
```

## Hook Error Prevention

### Maintain Directory Structure

✅ **Good**: Ensure required directories exist
```bash
# Setup script or initialization
mkdir -p State
mkdir -p History/Sessions
mkdir -p Memory/cache
mkdir -p ~/.claude/logs
```

### Monitor Hook Logs

✅ **Good**: Periodically review hook logs
```bash
# Add to monitoring script
if grep -q "error" ~/.claude/logs/hooks.log; then
    echo "Hook errors detected - review ~/.claude/logs/hooks.log"
fi
```

### Graceful Degradation

**Remember**: Hook failures are not critical
- Morning brief missing → session still starts
- Session log missing → history incomplete but not critical
- Hook errors logged → can debug later

**User experience is prioritized** over complete hook execution.

---

# Common Troubleshooting Scenarios

## Scenario 1: "All API calls are failing"

**Symptoms**:
- Every request fails
- Multiple fallback attempts visible in logs
- Last error indicates exhausted fallback chain

**Diagnosis**:
```bash
# 1. Check API keys configured
echo $ANTHROPIC_API_KEY | cut -c1-10
echo $OPENAI_API_KEY | cut -c1-10

# 2. Test network connectivity
curl -I https://api.anthropic.com/v1/messages
curl -I https://api.openai.com/v1/chat/completions

# 3. Review fallback chain config
cat config/api.json | jq '.litellm.fallback_chain'

# 4. Check recent error logs
tail -50 ~/.claude/logs/thanos.log | grep -i error
```

**Common Causes**:
1. All API keys invalid or expired
2. Network completely down
3. All providers experiencing outages (rare)
4. Firewall blocking all API endpoints

**Resolution**:
1. Verify and update API keys
2. Check network and proxy settings
3. Review provider status pages
4. Temporarily simplify to single known-working model

## Scenario 2: "Responses are slow"

**Symptoms**:
- Noticeable delays in responses
- Performance degradation over time

**Diagnosis**:
```bash
# 1. Check cache hit rate (indirect measure)
ls Memory/cache/*.json | wc -l

# 2. Check disk space
df -h .

# 3. Review error logs for fallback patterns
grep "fallback" ~/.claude/logs/thanos.log | tail -20

# 4. Check for corrupted cache (manual)
for f in Memory/cache/*.json; do
    jq empty "$f" 2>/dev/null || echo "Corrupted: $f"
done | head -10
```

**Common Causes**:
1. Cache corruption causing cache misses
2. Frequent fallback chain traversal
3. Network latency to API providers
4. Disk full affecting cache writes

**Resolution**:
1. Clear corrupted cache files
2. Review and optimize fallback chain
3. Check network performance to API endpoints
4. Free up disk space

## Scenario 3: "Missing session history"

**Symptoms**:
- No files in `History/Sessions/`
- Session logs not being created

**Diagnosis**:
```bash
# 1. Check hook logs
grep "session-end" ~/.claude/logs/hooks.log

# 2. Verify directory exists and is writable
ls -ld History/Sessions/

# 3. Test hook manually
python Tools/thanos_orchestrator.py hook session-end

# 4. Check recent session logs
ls -lt History/Sessions/ | head -10
```

**Common Causes**:
1. session-end hook failing silently
2. Permission denied on History directory
3. Disk full
4. Hook not configured in Claude Code

**Resolution**:
1. Fix directory permissions
2. Free up disk space
3. Verify Claude Code hook configuration
4. Review hook logs for specific errors

## Scenario 4: "High disk usage"

**Symptoms**:
- Disk space running low
- Large cache directory

**Diagnosis**:
```bash
# 1. Check total disk usage
df -h .

# 2. Check cache size
du -sh Memory/cache/

# 3. Find largest cache files
ls -lhS Memory/cache/*.json | head -20

# 4. Check cache file count and age
ls -lt Memory/cache/*.json | wc -l
ls -lt Memory/cache/*.json | tail -5  # Oldest files
```

**Common Causes**:
1. Cache never cleaned up
2. Very large cached responses
3. Corrupted files not removed
4. No automatic cache expiration

**Resolution**:
```bash
# 1. Clear all cache (safe)
rm -rf Memory/cache/*.json

# 2. Or clear old cache only
find Memory/cache/ -name "*.json" -mtime +7 -delete

# 3. Monitor disk usage regularly
du -sh Memory/cache/ && df -h .

# 4. Consider implementing periodic cleanup
# Add to cron:
# 0 2 * * * find /path/to/Memory/cache/ -name "*.json" -mtime +30 -delete
```

## Scenario 5: "API key rotation"

**Symptoms**:
- Need to update API keys
- Want to ensure no service interruption

**Procedure**:
```bash
# 1. Verify new key works before updating
export NEW_ANTHROPIC_KEY="sk-ant-..."
curl -H "x-api-key: $NEW_ANTHROPIC_KEY" \
     -H "anthropic-version: 2023-06-01" \
     https://api.anthropic.com/v1/messages

# 2. Update environment variable
export ANTHROPIC_API_KEY="$NEW_ANTHROPIC_KEY"

# 3. Update in persistent config if applicable
# (e.g., .bashrc, .zshrc, systemd service, etc.)

# 4. Verify Thanos uses new key
# Make a test request and check it succeeds

# 5. Invalidate old key in provider dashboard
# Only after confirming new key works
```

**Best Practices**:
- Test new keys before updating
- Update one provider at a time
- Keep fallback chain functional during rotation
- Invalidate old keys only after confirming new ones work

---

# Best Practices

## 1. Configure Resilient Fallback Chains

✅ **Use diverse providers** to avoid single point of failure:
```json
{
  "litellm": {
    "fallback_chain": [
      "claude-opus-4-5-20251101",    // Primary: Anthropic
      "gpt-4-turbo",                  // Fallback 1: OpenAI
      "claude-sonnet-4-20250514"      // Fallback 2: Anthropic
    ]
  }
}
```

❌ **Avoid** single-provider chains:
```json
{
  "litellm": {
    "fallback_chain": [
      "claude-opus-4-5-20251101",
      "claude-sonnet-4-20250514",
      "claude-3-5-haiku-20241022"
    ]
  }
}
```

## 2. Maintain Valid API Keys

✅ **Regular verification** prevents surprise failures:
```bash
#!/bin/bash
# add to monitoring/healthcheck

# Test Anthropic
curl -s -H "x-api-key: $ANTHROPIC_API_KEY" \
     https://api.anthropic.com/v1/messages &>/dev/null
[ $? -eq 0 ] && echo "✓ Anthropic OK" || echo "✗ Anthropic FAIL"

# Test OpenAI
curl -s -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models &>/dev/null
[ $? -eq 0 ] && echo "✓ OpenAI OK" || echo "✗ OpenAI FAIL"
```

## 3. Monitor Disk Space

✅ **Proactive cleanup** prevents disk full errors:
```bash
# Add to cron: daily at 2am
0 2 * * * find /path/to/Memory/cache/ -name "*.json" -mtime +30 -delete
```

✅ **Monitor cache size**:
```bash
#!/bin/bash
CACHE_SIZE_MB=$(du -sm Memory/cache/ | cut -f1)
THRESHOLD_MB=1000

if [ "$CACHE_SIZE_MB" -gt "$THRESHOLD_MB" ]; then
    echo "WARNING: Cache size ${CACHE_SIZE_MB}MB exceeds ${THRESHOLD_MB}MB"
    # Clear old entries
    find Memory/cache/ -name "*.json" -mtime +7 -delete
fi
```

## 4. Review Logs Periodically

✅ **Regular log review** catches issues early:
```bash
# Weekly log review
grep -i error ~/.claude/logs/thanos.log | tail -50
grep -i error ~/.claude/logs/hooks.log | tail -20

# Check for patterns
grep "fallback" ~/.claude/logs/thanos.log | wc -l
# High count indicates frequent API issues
```

## 5. Test Hooks After Configuration Changes

✅ **Verify hooks work** after updates:
```bash
# After any Thanos configuration change
python Tools/thanos_orchestrator.py hook morning-brief
python Tools/thanos_orchestrator.py hook session-end

# Check for errors
tail -10 ~/.claude/logs/hooks.log
```

## 6. Understand Error Severity

Different errors have different impacts:

**Critical** (require immediate action):
- All API keys invalid
- Disk full
- Permission denied on critical directories

**Warning** (investigate but not urgent):
- Single API provider failing (fallback working)
- Cache corruption (self-healing)
- Hook errors (non-critical features)

**Info** (normal operation):
- Rate limits with successful fallback
- Cache misses
- Expired cache cleanup

## 7. Implement Monitoring

✅ **Production monitoring setup**:
```bash
#!/bin/bash
# healthcheck.sh - Run via cron every 5 minutes

# Check API keys
curl -s -H "x-api-key: $ANTHROPIC_API_KEY" \
     https://api.anthropic.com/v1/messages &>/dev/null
API_STATUS=$?

# Check disk space
DISK_USAGE=$(df -h . | tail -1 | awk '{print $5}' | sed 's/%//')

# Check recent errors
ERROR_COUNT=$(grep -i error ~/.claude/logs/thanos.log | tail -100 | wc -l)

# Alert if issues
if [ "$API_STATUS" -ne 0 ]; then
    echo "ALERT: API health check failed"
fi

if [ "$DISK_USAGE" -gt 90 ]; then
    echo "ALERT: Disk usage at ${DISK_USAGE}%"
fi

if [ "$ERROR_COUNT" -gt 50 ]; then
    echo "WARNING: High error count: $ERROR_COUNT in last 100 lines"
fi
```

---

# Related Documentation

## MCP Error Handling

For MCP-specific errors (MCP servers, tools, protocols), see:
- **[MCP Error Handling Guide](../Tools/adapters/README_ERROR_HANDLING.md)**: Comprehensive guide for MCP adapter errors
  - MCP connection errors
  - Tool execution errors
  - Circuit breaker and retry logic
  - MCP-specific recovery strategies

## Hook Integration

For detailed hook configuration and development:
- **[Hooks Integration Guide](./hooks-integration.md)**: Hook system architecture and configuration

## MCP Integration

For MCP server integration and deployment:
- **[MCP Integration Guide](./mcp-integration-guide.md)**: Integrating MCP servers with Thanos
- **[MCP Deployment Guide](./mcp-deployment-guide.md)**: Deploying and operating MCP servers

---

# Summary

Thanos implements robust error handling across all subsystems:

- ✅ **API Fallback Chain**: Automatic failover between models and providers
- ✅ **Cache Self-Healing**: Silent failure with automatic cleanup of corrupted files
- ✅ **Fail-Safe Hooks**: Lifecycle events never disrupt workflow
- ✅ **Graceful Degradation**: Service continues even when components fail
- ✅ **Comprehensive Logging**: Detailed error context for debugging (`~/.claude/logs/`)

**Key Principle**: Errors are handled to minimize user disruption while providing debugging visibility through logs.

**When in Doubt**:
1. Check logs: `~/.claude/logs/thanos.log` and `~/.claude/logs/hooks.log`
2. Verify configuration: `config/api.json`
3. Test connectivity: API endpoints and network
4. Clear cache: Safe to delete `Memory/cache/*.json`
5. Check disk space: `df -h .`

Most errors are handled automatically. Manual intervention is only needed for persistent issues or when debugging specific problems.
