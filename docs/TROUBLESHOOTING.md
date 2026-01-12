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

The cache automatically detects corruption during read operations using defensive exception handling. **No logging occurs** - corruption detection is entirely silent and transparent to the application.

### Detection Mechanism

**Detection Points**:
1. **During cache reads** (`get()` method) - corruption treated as cache miss
2. **During cleanup** (`clear_expired()` method) - corrupted files immediately deleted

**How Detection Works**:
```python
# In ResponseCache.get() - Lines 113-121
try:
    cached = json.loads(cache_file.read_text())
    cached_time = datetime.fromisoformat(cached["timestamp"])
    if datetime.now() - cached_time < timedelta(seconds=self.ttl_seconds):
        return cached["response"]
    else:
        cache_file.unlink()  # Remove expired cache
except (json.JSONDecodeError, KeyError, ValueError):
    pass  # ← Silent failure - treated as cache miss

return None
```

### Three Types of Corruption Detected

#### 1. JSON Decode Errors (json.JSONDecodeError)

**What it detects**:
- Invalid JSON syntax (unclosed braces, missing quotes)
- Truncated files (incomplete write operations)
- Binary data or non-JSON content
- Corrupted file encoding

**Example corrupted file**:
```json
{
  "timestamp": "2026-01-11T12:00:00",
  "model": "claude-opus-4-5-202
```
*(File truncated mid-write)*

**Handling**: Silent failure, treated as cache miss

#### 2. Missing Keys (KeyError)

**What it detects**:
- Cache file missing required fields: `timestamp`, `model`, or `response`
- Schema changes in cached data structure
- Partial write operations that completed JSON but missed fields

**Example corrupted file**:
```json
{
  "timestamp": "2026-01-11T12:00:00",
  "model": "claude-opus-4-5-20251101"
}
```
*(Missing "response" field)*

**Handling**: Silent failure on read, automatic deletion on cleanup

#### 3. Invalid Values (ValueError)

**What it detects**:
- Invalid ISO format in `timestamp` field
- `datetime.fromisoformat()` parsing failures
- Corrupted timestamp data

**Example corrupted file**:
```json
{
  "timestamp": "not-a-valid-timestamp",
  "model": "claude-opus-4-5-20251101",
  "response": "cached response"
}
```

**Handling**: Same as JSONDecodeError - silent failure

### What Is NOT Detected

**File System Errors** (not caught by corruption detection):
- `PermissionError`: File permission issues
- `OSError`: Disk errors, file system failures
- `IOError`: General I/O failures
- Disk full conditions during writes

These errors **propagate up** and may cause application failures. They require manual intervention.

### Detection Characteristics

| Aspect | Behavior |
|--------|----------|
| **Logging** | None - completely silent |
| **Monitoring** | No built-in monitoring |
| **Notifications** | None |
| **Performance Impact** | Negligible (single exception catch) |
| **User Visibility** | Zero - transparent to application |
| **Automatic Cleanup** | Only during `clear_expired()` calls |
| **Cache Miss Behavior** | Identical to expired or missing cache |

### Detection Flow Diagram

```
Cache Read Request
        ↓
   File exists?
    ↙       ↘
  NO        YES
   ↓         ↓
Return   Read file
 None      ↓
      Parse JSON
        ↓
   Valid JSON?
    ↙       ↘
  NO        YES
   ↓         ↓
Catch     Extract
exception  fields
   ↓         ↓
Return   Valid fields?
 None    ↙       ↘
       NO        YES
        ↓         ↓
      Catch    Check
      exception  expiry
        ↓         ↓
      Return   Expired?
       None   ↙       ↘
            YES       NO
             ↓         ↓
           Delete   Return
            file    response
             ↓
           Return
            None
```

**Key Insight**: All corruption paths lead to `return None` (cache miss). The application sees identical behavior whether cache is corrupted, expired, or simply doesn't exist.

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

**Automatic Cleanup Details**:

The `clear_expired()` method provides automatic corruption cleanup as a side effect of expiration cleanup:

```python
# In ResponseCache.clear_expired() - Lines 136-146
def clear_expired(self):
    """Remove expired cache entries."""
    cutoff = datetime.now() - timedelta(seconds=self.ttl_seconds)
    for cache_file in self.cache_path.glob("*.json"):
        try:
            cached = json.loads(cache_file.read_text())
            cached_time = datetime.fromisoformat(cached["timestamp"])
            if cached_time < cutoff:
                cache_file.unlink()  # Delete expired
        except (json.JSONDecodeError, KeyError, ValueError):
            cache_file.unlink()  # ← Delete corrupted files immediately
```

**Cleanup Behavior**:

| Scenario | Action | Disk Space | Logging |
|----------|--------|------------|---------|
| **Expired entry** | Deleted | Recovered | None |
| **Corrupted entry** | Deleted | Recovered | None |
| **Valid, not expired** | Kept | Consumed | None |
| **File system error** | Propagates up | Not recovered | Exception raised |

**Performance Characteristics**:
- **Time Complexity**: O(n) where n = number of cache files
- **I/O Operations**: One read + one delete per file
- **Typical Duration**: <100ms for 1000 cache files
- **Resource Usage**: Low CPU, moderate I/O, no memory accumulation
- **Safe During Operations**: Can run while cache is actively being used

**Self-Healing Behavior**:

The combination of silent failures on read and automatic cleanup on maintenance creates a self-healing system:

```
Time T0: Cache file becomes corrupted
         ↓
Time T1: Application reads corrupted file
         → Treats as cache miss
         → Makes API call
         → Caches new response
         → May overwrite corrupted key
         ↓
Time T2: clear_expired() runs
         → Finds corrupted file (if still present)
         → Deletes immediately
         → Disk space recovered
         ↓
Result: System fully recovered, no user intervention
```

**Important Notes**:

⚠️ **No Scheduled Cleanup**: The ResponseCache class does not automatically schedule `clear_expired()`. It must be called explicitly by:
- Application code
- Cron jobs
- Startup scripts
- Manual execution

⚠️ **Accumulation Risk**: Without scheduled cleanup, corrupted files accumulate indefinitely, consuming disk space despite being unusable.

✅ **Recommendation**: Schedule `clear_expired()` to run at least daily:
```bash
# Add to crontab
0 3 * * * cd /path/to/Thanos && python -c "from Tools.litellm.response_cache import ResponseCache; ResponseCache('Memory/cache', 86400).clear_expired()"
```

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

## When Manual Intervention Is Needed

While cache corruption is handled automatically in most cases, certain situations require user action:

### 1. Repeated Cache Corruption

**Symptoms**:
- Frequent cache misses despite stable workload
- Unexpectedly high API costs
- Growing cache directory with many files

**Possible Causes**:
- Disk hardware issues (bad sectors, failing drive)
- File system corruption
- Insufficient disk space causing interrupted writes
- Concurrent access conflicts

**Action Required**:

1. **Check disk health**:
   ```bash
   # macOS
   diskutil verifyDisk disk0

   # Linux with smartctl
   sudo smartctl -H /dev/sda

   # Check for file system errors
   # (macOS) Disk Utility -> First Aid
   # (Linux) sudo fsck /dev/sda1
   ```

2. **Verify file system integrity**:
   ```bash
   # Check for errors in system log
   # macOS
   log show --predicate 'eventMessage contains "disk"' --last 1d

   # Linux
   dmesg | grep -i "error\|warning" | grep -i "disk\|filesystem"
   ```

3. **Inspect cache corruption patterns**:
   ```bash
   # Test all cache files for corruption
   corrupted_count=0
   for f in Memory/cache/*.json; do
       if ! jq empty "$f" 2>/dev/null; then
           echo "Corrupted: $f"
           corrupted_count=$((corrupted_count + 1))
       fi
   done
   echo "Total corrupted files: $corrupted_count"
   ```

4. **Clear cache and monitor**:
   ```bash
   # Clear all cache
   rm -rf Memory/cache/*.json

   # Run application and monitor for new corruption
   # Check again after 24 hours
   ```

5. **If corruption continues**: Consider hardware replacement or file system repair.

### 2. Performance Degradation

**Symptoms**:
- Increased API response latency
- Higher than expected API costs
- Lower cache hit rates in monitoring

**Diagnosis**:

Check cache effectiveness:
```bash
# Count cache files
echo "Cache files: $(ls Memory/cache/*.json 2>/dev/null | wc -l)"

# Check cache directory size
echo "Cache size: $(du -sh Memory/cache/ 2>/dev/null | cut -f1)"

# Check for corrupted files
echo "Testing cache integrity..."
corrupted=0
total=0
for f in Memory/cache/*.json 2>/dev/null; do
    total=$((total + 1))
    jq empty "$f" 2>/dev/null || corrupted=$((corrupted + 1))
done
echo "Corrupted: $corrupted / $total files"
```

**Action Required**:

1. If corruption rate > 5%: Clear cache and investigate root cause
2. Monitor API usage before/after cache clear to verify impact
3. Check disk space and ensure adequate free space (>10% of disk)

### 3. Cache Directory Size Issues

**Symptoms**:
- Disk space warnings
- Cache directory unexpectedly large
- Write failures during cache operations

**Diagnosis**:
```bash
# Check cache size and file count
echo "Cache directory size:"
du -sh Memory/cache/

echo "Number of cache files:"
find Memory/cache/ -name "*.json" | wc -l

echo "Largest cache files:"
ls -lhS Memory/cache/*.json | head -10

echo "Available disk space:"
df -h .
```

**Action Required**:

1. **Clear expired entries**:
   ```python
   from Tools.litellm.response_cache import ResponseCache
   cache = ResponseCache(cache_path="Memory/cache", ttl_seconds=86400)
   cache.clear_expired()
   ```

2. **Reduce cache TTL** if cache grows too quickly:
   ```python
   # In your configuration, reduce TTL
   cache = ResponseCache(
       cache_path="Memory/cache",
       ttl_seconds=3600  # 1 hour instead of 24
   )
   ```

3. **Schedule automatic cleanup**:
   ```bash
   # Add to crontab (runs daily at 2 AM)
   0 2 * * * cd /path/to/Thanos && python -c "from Tools.litellm.response_cache import ResponseCache; ResponseCache('Memory/cache', 86400).clear_expired()"
   ```

### 4. Silent Corruption Accumulation

**Symptom**: Cache directory growing but API costs also increasing (indicates corrupted cache not being used).

**Detection Strategy**:

Monitor cache hit rate over time:
```bash
# Create monitoring script: monitor_cache.sh
#!/bin/bash

CACHE_DIR="Memory/cache"
FILE_COUNT=$(find "$CACHE_DIR" -name "*.json" 2>/dev/null | wc -l)
CACHE_SIZE=$(du -sm "$CACHE_DIR" 2>/dev/null | cut -f1)
CORRUPTED=0

for f in "$CACHE_DIR"/*.json 2>/dev/null; do
    jq empty "$f" 2>/dev/null || CORRUPTED=$((CORRUPTED + 1))
done

echo "$(date): Files=$FILE_COUNT, Size=${CACHE_SIZE}MB, Corrupted=$CORRUPTED" >> cache_monitor.log

# Alert if corruption rate > 5%
if [ "$FILE_COUNT" -gt 0 ]; then
    CORRUPTION_RATE=$((CORRUPTED * 100 / FILE_COUNT))
    if [ "$CORRUPTION_RATE" -gt 5 ]; then
        echo "WARNING: Cache corruption rate is ${CORRUPTION_RATE}%"
    fi
fi
```

**Action Required**:
- Run monitoring script daily or weekly
- Investigate if corruption rate increases over time
- Clear cache if corruption rate exceeds 5%

### 5. No Automatic Cleanup Configured

**Symptom**: Cache directory grows indefinitely, expired entries never removed.

**Background**: The `clear_expired()` method must be called explicitly - there is no automatic scheduled cleanup in the ResponseCache class.

**Action Required**:

**Option 1: Scheduled Cleanup (Recommended)**
```bash
# Add to crontab for automatic cleanup
# Run daily at 3 AM
0 3 * * * cd /path/to/Thanos && python -c "from Tools.litellm.response_cache import ResponseCache; ResponseCache('Memory/cache', 86400).clear_expired()"
```

**Option 2: Application-Level Cleanup**
```python
# Add to your application startup or periodic maintenance
from Tools.litellm.response_cache import ResponseCache
import time

def periodic_cache_cleanup():
    cache = ResponseCache(cache_path="Memory/cache", ttl_seconds=86400)
    while True:
        cache.clear_expired()
        time.sleep(86400)  # Run daily

# Run in background thread
import threading
cleanup_thread = threading.Thread(target=periodic_cache_cleanup, daemon=True)
cleanup_thread.start()
```

**Option 3: Manual Cleanup**
```bash
# Run manually when needed
python -c "from Tools.litellm.response_cache import ResponseCache; ResponseCache('Memory/cache', 86400).clear_expired()"
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

Since cache corruption is silent and not logged, monitoring is essential for detecting issues:

#### Basic Monitoring Commands

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

#### Advanced Monitoring Script

Create a comprehensive cache health monitoring script:

```bash
#!/bin/bash
# cache_health_check.sh - Comprehensive cache monitoring

CACHE_DIR="Memory/cache"
LOG_FILE="cache_health.log"

echo "=== Cache Health Check - $(date) ===" | tee -a "$LOG_FILE"

# 1. Cache Size
CACHE_SIZE_MB=$(du -sm "$CACHE_DIR" 2>/dev/null | cut -f1)
echo "Cache Size: ${CACHE_SIZE_MB}MB" | tee -a "$LOG_FILE"

# 2. File Count
FILE_COUNT=$(find "$CACHE_DIR" -name "*.json" 2>/dev/null | wc -l)
echo "Cache Files: $FILE_COUNT" | tee -a "$LOG_FILE"

# 3. Corruption Check
CORRUPTED=0
VALID=0
echo "Checking cache integrity..." | tee -a "$LOG_FILE"

for f in "$CACHE_DIR"/*.json 2>/dev/null; do
    if jq empty "$f" 2>/dev/null; then
        VALID=$((VALID + 1))
    else
        CORRUPTED=$((CORRUPTED + 1))
        echo "  Corrupted: $(basename "$f")" | tee -a "$LOG_FILE"
    fi
done

echo "Valid Files: $VALID" | tee -a "$LOG_FILE"
echo "Corrupted Files: $CORRUPTED" | tee -a "$LOG_FILE"

# 4. Calculate Corruption Rate
if [ "$FILE_COUNT" -gt 0 ]; then
    CORRUPTION_RATE=$((CORRUPTED * 100 / FILE_COUNT))
    echo "Corruption Rate: ${CORRUPTION_RATE}%" | tee -a "$LOG_FILE"

    # Alert if corruption rate exceeds threshold
    if [ "$CORRUPTION_RATE" -gt 5 ]; then
        echo "⚠️  WARNING: High corruption rate detected!" | tee -a "$LOG_FILE"
        echo "   Consider clearing cache and investigating root cause." | tee -a "$LOG_FILE"
    fi
else
    echo "No cache files found" | tee -a "$LOG_FILE"
fi

# 5. Disk Space Check
AVAILABLE_MB=$(df -m . | tail -1 | awk '{print $4}')
echo "Available Disk Space: ${AVAILABLE_MB}MB" | tee -a "$LOG_FILE"

if [ "$AVAILABLE_MB" -lt 1000 ]; then
    echo "⚠️  WARNING: Low disk space!" | tee -a "$LOG_FILE"
fi

# 6. Oldest Cache File
OLDEST=$(find "$CACHE_DIR" -name "*.json" -type f -print0 2>/dev/null | xargs -0 stat -f "%m %N" 2>/dev/null | sort -n | head -1 | cut -d' ' -f2-)
if [ -n "$OLDEST" ]; then
    OLDEST_DATE=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$OLDEST" 2>/dev/null)
    echo "Oldest Cache File: $OLDEST_DATE" | tee -a "$LOG_FILE"
fi

echo "===========================================" | tee -a "$LOG_FILE"
echo "" >> "$LOG_FILE"
```

**Usage**:
```bash
# Make executable
chmod +x cache_health_check.sh

# Run manually
./cache_health_check.sh

# Schedule in cron (daily at 2 AM)
0 2 * * * cd /path/to/Thanos && ./cache_health_check.sh
```

#### Monitoring Metrics to Track

| Metric | Normal Range | Action Threshold |
|--------|--------------|------------------|
| **Cache Size** | < 500MB | > 1GB - investigate |
| **File Count** | 100-1000 | > 5000 - consider cleanup |
| **Corruption Rate** | < 1% | > 5% - clear cache, investigate |
| **Disk Space** | > 10GB free | < 1GB - urgent cleanup needed |
| **Growth Rate** | Stable | Rapid growth - check for issues |

#### Detecting Cache Corruption Impact

Since corruption is silent, look for these indirect indicators:

**1. Increased API Costs**:
```bash
# Compare API usage before/after cache clear
# High costs despite large cache → corruption likely
```

**2. Higher Latency**:
```bash
# Monitor response times
# Consistent cache hits should be <10ms
# If latency high despite cache → corruption or cache bypass
```

**3. Unusual Disk Growth**:
```bash
# Track cache directory size over time
# Steady growth without cleanup → accumulating corrupted files
watch -n 60 'du -sh Memory/cache/'
```

#### Proactive Monitoring Strategy

**Daily Monitoring** (automated):
```bash
# Check cache health daily
0 2 * * * /path/to/cache_health_check.sh

# Clear expired entries daily
0 3 * * * cd /path/to/Thanos && python -c "from Tools.litellm.response_cache import ResponseCache; ResponseCache('Memory/cache', 86400).clear_expired()"
```

**Weekly Review** (manual):
- Review `cache_health.log` for trends
- Check corruption rate history
- Investigate if corruption increasing
- Verify disk space adequate

**Monthly Maintenance**:
```bash
# Full cache clear to start fresh
rm -rf Memory/cache/*.json

# Monitor for 1 week to establish baseline
# Compare corruption rates before/after clear
```

#### Cache Hit Rate Monitoring (Advanced)

To track cache effectiveness, instrument your application:

```python
from Tools.litellm.response_cache import ResponseCache

class MonitoredCache(ResponseCache):
    """ResponseCache with hit/miss tracking."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hits = 0
        self.misses = 0
        self.corrupted = 0

    def get(self, prompt, model, params):
        result = super().get(prompt, model, params)
        if result is not None:
            self.hits += 1
        else:
            # Could be miss, corruption, or expiration
            cache_key = self._get_cache_key(prompt, model, params)
            cache_file = self.cache_path / f"{cache_key}.json"
            if cache_file.exists():
                self.corrupted += 1
            else:
                self.misses += 1
        return result

    def get_stats(self):
        total = self.hits + self.misses + self.corrupted
        if total == 0:
            return "No cache operations yet"

        hit_rate = (self.hits / total) * 100
        corruption_rate = (self.corrupted / total) * 100

        return f"""
Cache Statistics:
  Hits: {self.hits} ({hit_rate:.1f}%)
  Misses: {self.misses}
  Corrupted: {self.corrupted} ({corruption_rate:.1f}%)
  Total: {total}
  Effectiveness: {hit_rate:.1f}%
"""

# Usage
cache = MonitoredCache(cache_path="Memory/cache", ttl_seconds=3600)
# ... use cache normally ...
print(cache.get_stats())
```

**Interpreting Cache Stats**:
- **Hit rate > 50%**: Cache working well
- **Hit rate < 20%**: Investigate (corruption, short TTL, or unique queries)
- **Corruption rate > 5%**: Serious issue, investigate disk health
- **Corruption rate < 1%**: Normal operational noise

### Cache Configuration

**TTL (Time-To-Live)**: Configured in `ResponseCache` initialization
- Default: Varies by usage
- Location: `Tools/litellm/response_cache.py`

**Cache Path**: `Memory/cache/` relative to Thanos directory

**No Configuration File**: Cache settings are hardcoded in source

## Cache Error Prevention

Prevention is better than recovery. Follow these best practices to minimize cache corruption:

### 1. Ensure Adequate Disk Space

**Goal**: Prevent interrupted writes due to disk full conditions.

❌ **Bad**: No monitoring, cache fills disk
```bash
# No space left
df -h .
# Filesystem  Size  Used  Avail  Capacity
# /dev/disk1  500G  500G     0B   100%
```

✅ **Good**: Regular monitoring and cleanup
```bash
# Monitor script - add to cron
#!/bin/bash
CACHE_SIZE=$(du -sm Memory/cache/ | cut -f1)
DISK_FREE=$(df -m . | tail -1 | awk '{print $4}')

# Alert if cache too large
if [ "$CACHE_SIZE" -gt 1000 ]; then  # 1GB threshold
    echo "WARNING: Cache size: ${CACHE_SIZE}MB - clearing old entries"
    find Memory/cache/ -name "*.json" -mtime +7 -delete
fi

# Alert if disk space low
if [ "$DISK_FREE" -lt 1000 ]; then  # Less than 1GB free
    echo "CRITICAL: Only ${DISK_FREE}MB disk space remaining!"
    # Aggressive cleanup
    find Memory/cache/ -name "*.json" -mtime +3 -delete
fi
```

**Best Practice**:
- Maintain at least 10% free disk space
- Monitor disk usage daily
- Set up alerts for low disk space
- Schedule automatic cleanup

### 2. Graceful Shutdown

**Goal**: Allow cache write operations to complete before termination.

❌ **Bad**: Kill processes during cache writes
```bash
kill -9 $(pgrep python)  # Force kill may corrupt cache
```

✅ **Good**: Allow graceful shutdown
```bash
# Use SIGTERM instead of SIGKILL
kill -TERM $(pgrep python)  # Graceful shutdown

# Or use Ctrl+C in terminal (sends SIGINT)
# Python will catch signal and clean up

# Wait for process to exit
kill -TERM $PID && wait $PID
```

**Best Practice**:
- Always use `kill -TERM` (or just `kill`) instead of `kill -9`
- Use `Ctrl+C` instead of `Ctrl+\` or force quit
- Implement signal handlers in applications for cleanup
- Wait for processes to exit before system shutdown

### 3. Avoid External Modifications

**Goal**: Prevent manual corruption of cache files.

❌ **Bad**: Manually editing cache files
```bash
# Don't do this!
vim Memory/cache/a1b2c3d4e5f6.json
nano Memory/cache/*.json
sed -i 's/old/new/g' Memory/cache/*.json
```

✅ **Good**: Clear entire cache or use programmatic access
```bash
# Safe cache operations
rm -rf Memory/cache/*.json  # Clear all cache

# Or use Python API
python -c "from Tools.litellm.response_cache import ResponseCache; ResponseCache('Memory/cache', 86400).clear_expired()"
```

**Best Practice**:
- Never manually edit cache files
- Use provided APIs for cache operations
- Clear and regenerate instead of editing
- Document cache directory as "do not touch"

### 4. Schedule Regular Cleanup

**Goal**: Prevent accumulation of expired and corrupted cache entries.

❌ **Bad**: No scheduled cleanup, cache grows forever
```bash
# Cache accumulates indefinitely
$ du -sh Memory/cache/
15G  Memory/cache/  # Growing without bounds
```

✅ **Good**: Automated daily cleanup
```bash
# Add to crontab
# Run cleanup daily at 3 AM
0 3 * * * cd /path/to/Thanos && python -c "from Tools.litellm.response_cache import ResponseCache; ResponseCache('Memory/cache', 86400).clear_expired()"

# Or create cleanup script
#!/bin/bash
# cleanup_cache.sh
cd /path/to/Thanos
python3 << 'EOF'
from Tools.litellm.response_cache import ResponseCache
cache = ResponseCache(cache_path="Memory/cache", ttl_seconds=86400)
cache.clear_expired()
print("Cache cleanup completed")
EOF
```

**Best Practice**:
- Schedule `clear_expired()` to run at least daily
- Run during low-usage hours (e.g., 3 AM)
- Log cleanup results for monitoring
- Verify cron job is actually running (`grep CRON /var/log/syslog`)

### 5. Use Appropriate TTL Values

**Goal**: Balance cache effectiveness with freshness and disk usage.

❌ **Bad**: Extremely long TTL causes accumulation
```python
# 30 days - cache rarely expires, grows very large
cache = ResponseCache(cache_path="Memory/cache", ttl_seconds=2592000)
```

❌ **Bad**: Extremely short TTL defeats caching purpose
```python
# 1 minute - constant cache misses, no benefit
cache = ResponseCache(cache_path="Memory/cache", ttl_seconds=60)
```

✅ **Good**: Appropriate TTL based on use case
```python
# Development: 1 hour (content changes frequently)
cache = ResponseCache(cache_path="Memory/cache", ttl_seconds=3600)

# Production: 24 hours (balance freshness and cost)
cache = ResponseCache(cache_path="Memory/cache", ttl_seconds=86400)

# Static content: 7 days (rarely changes)
cache = ResponseCache(cache_path="Memory/cache", ttl_seconds=604800)
```

**Best Practice**:
- Start with 24-hour TTL as default
- Adjust based on how often content changes
- Shorter TTL for development (1 hour)
- Longer TTL for stable production workloads
- Monitor cache hit rates to verify TTL effectiveness

### 6. Monitor Disk Health

**Goal**: Detect hardware issues before they cause widespread corruption.

✅ **Good**: Regular disk health monitoring
```bash
# macOS: Check SMART status
diskutil info disk0 | grep SMART

# Linux: Detailed SMART analysis
sudo smartctl -a /dev/sda

# Check system logs for disk errors
# macOS
log show --predicate 'eventMessage contains "disk"' --last 7d | grep -i error

# Linux
dmesg | grep -i "error\|fail" | grep -i "disk\|sda"
```

**Best Practice**:
- Check SMART status monthly
- Monitor system logs for I/O errors
- Set up disk health alerts
- Replace failing drives proactively
- Use redundant storage (RAID) if critical

### 7. Implement Cache Validation

**Goal**: Detect and clean corrupted cache proactively.

✅ **Good**: Periodic validation script
```bash
#!/bin/bash
# validate_cache.sh - Run weekly

CACHE_DIR="Memory/cache"
CORRUPTED_COUNT=0
TOTAL_COUNT=0

echo "Validating cache files..."

for f in "$CACHE_DIR"/*.json; do
    [ -f "$f" ] || continue
    TOTAL_COUNT=$((TOTAL_COUNT + 1))

    if ! jq empty "$f" 2>/dev/null; then
        echo "Corrupted: $f"
        CORRUPTED_COUNT=$((CORRUPTED_COUNT + 1))
        # Optional: Auto-delete corrupted files
        # rm "$f"
    fi
done

CORRUPTION_RATE=0
if [ "$TOTAL_COUNT" -gt 0 ]; then
    CORRUPTION_RATE=$((CORRUPTED_COUNT * 100 / TOTAL_COUNT))
fi

echo "Validation complete:"
echo "  Total: $TOTAL_COUNT"
echo "  Corrupted: $CORRUPTED_COUNT"
echo "  Corruption rate: ${CORRUPTION_RATE}%"

# Alert if corruption rate high
if [ "$CORRUPTION_RATE" -gt 5 ]; then
    echo "⚠️  HIGH CORRUPTION RATE - Investigate disk health!"
    exit 1
fi
```

**Schedule validation**:
```bash
# Add to crontab - run weekly on Sunday at 1 AM
0 1 * * 0 /path/to/validate_cache.sh
```

**Best Practice**:
- Run validation weekly
- Auto-delete corrupted files during validation
- Alert on high corruption rates
- Investigate root cause if corruption > 1%

### 8. Avoid Concurrent Cache Access

**Goal**: Prevent race conditions during cache writes.

⚠️ **Current Limitation**: The ResponseCache does **not** implement file locking. Concurrent writes to the same cache key may corrupt the file.

**Best Practice**:
- Avoid running multiple instances writing to same cache
- If multi-process access needed, implement external locking
- Consider cache-per-process pattern
- Or use a proper cache server (Redis, Memcached) for concurrent access

**Example file locking implementation** (if needed):
```python
import fcntl

def atomic_cache_write(cache_file, data):
    """Write cache file with exclusive lock."""
    with open(cache_file, 'w') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.write(data)
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

### Prevention Checklist

Use this checklist to ensure robust cache operation:

- [ ] Disk space monitoring configured (daily checks)
- [ ] Alerts set up for low disk space (< 1GB)
- [ ] Automated cache cleanup scheduled (daily at 3 AM)
- [ ] TTL configured appropriately for use case
- [ ] Graceful shutdown procedures documented
- [ ] Cache directory marked as "do not edit manually"
- [ ] Disk health monitoring (monthly SMART checks)
- [ ] Cache validation script (weekly validation)
- [ ] Corruption rate monitoring (track in logs)
- [ ] Response plan for high corruption rates (> 5%)
- [ ] Backup strategy documented (or cache regeneration plan)
- [ ] No concurrent cache access (or locking implemented)

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

## Hook Performance Characteristics

### Typical Execution Times

Hooks are designed for fast, non-blocking operation:

**Morning Brief Hook**:
- State file reads: ~10-20ms
- Context parsing: ~5-10ms
- JSON output: ~1ms
- **Total**: ~20-30ms typically
- **Target**: < 100ms maximum

**Session End Hook**:
- State file reads: ~10-20ms
- File creation: ~5-10ms
- Text write: ~5ms
- **Total**: ~20-35ms typically
- **Target**: < 100ms maximum

**Error Handling Overhead**:
- Exception catching: negligible (<1ms)
- Error logging: ~5-10ms (file append)
- **Total impact**: minimal even on error path

### Why Performance Matters

- **Fast startup**: Morning brief must not delay session start
- **Clean exit**: Session end must not slow down Claude Code exit
- **No API calls**: All hook operations are local file operations only
- **No blocking**: No network calls, no long computations

**Performance Issues to Monitor**:

```bash
# If hooks feel slow, check log file size
ls -lh ~/.claude/logs/hooks.log

# Large log files slow down appends
# Rotate if > 10MB

# Check for repeated errors (indicates persistent issue)
grep -c "error" ~/.claude/logs/hooks.log

# High error count slows down hooks due to repeated logging
```

## Hook Log File Management

### Log File Rotation

**Current Behavior**:
- ✅ **Append-only**: New errors added to end of file
- ❌ **No automatic rotation**: File grows indefinitely
- ❌ **No size limit**: Can consume disk space over time
- ❌ **No cleanup**: Manual deletion required

**Recommended Rotation Strategy**:

**Option 1: Manual Rotation**
```bash
# Archive old logs (weekly or monthly)
mv ~/.claude/logs/hooks.log ~/.claude/logs/hooks.log.$(date +%Y%m%d)

# Keep only last 4 weeks of archives
find ~/.claude/logs/ -name "hooks.log.*" -mtime +28 -delete
```

**Option 2: Truncate If Not Needed**
```bash
# Clear log file (lose history)
echo "" > ~/.claude/logs/hooks.log

# Or delete and recreate
rm ~/.claude/logs/hooks.log
touch ~/.claude/logs/hooks.log
```

**Option 3: Automated Rotation (Linux/macOS)**
```bash
# Create logrotate config: /etc/logrotate.d/claude-hooks
cat > /tmp/claude-hooks-logrotate <<'EOF'
/home/*/.claude/logs/hooks.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
    create 0644 $USER $USER
}
EOF

# Install (requires sudo)
sudo mv /tmp/claude-hooks-logrotate /etc/logrotate.d/claude-hooks
```

**Option 4: Custom Rotation Script**
```bash
#!/bin/bash
# Save as: ~/bin/rotate-hooks-log.sh

LOG_FILE=~/.claude/logs/hooks.log

if [ -f "$LOG_FILE" ]; then
    # Check if file > 10MB
    file_size=$(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null)
    if [ "$file_size" -gt 10485760 ]; then
        echo "Rotating large hook log ($file_size bytes)"
        mv "$LOG_FILE" "$LOG_FILE.$(date +%Y%m%d)"
        touch "$LOG_FILE"
        # Keep only last 4 rotated files
        ls -t ~/.claude/logs/hooks.log.* | tail -n +5 | xargs rm -f
    fi
fi
```

**Add to crontab**:
```bash
# Run weekly on Sunday at 2 AM
0 2 * * 0 ~/bin/rotate-hooks-log.sh
```

### Log Analysis and Monitoring

**Common Log Patterns to Monitor**:

1. **Repeated "State file not found"**
   ```bash
   grep -c "State file not found" ~/.claude/logs/hooks.log
   ```
   - **Indicates**: State management not initialized
   - **Action**: Verify Thanos state directory structure
   - **Fix**: Run initialization to create State/Today.md

2. **"Cannot write to log file"**
   ```bash
   grep "Cannot write to log file" ~/.claude/logs/hooks.log
   ```
   - **Indicates**: Disk space or permissions issue
   - **Action**: Check `~/.claude/logs/` permissions and space
   - **Fix**: Free disk space or fix permissions

3. **"Unknown hook event"**
   ```bash
   grep "Unknown hook event" ~/.claude/logs/hooks.log
   ```
   - **Indicates**: Claude Code version mismatch or configuration issue
   - **Action**: Check if Thanos needs update for new hook events
   - **Fix**: Update Thanos or adjust hook configuration

4. **Timestamp Gaps**
   ```bash
   # Show dates of all hook events
   cut -d']' -f1 ~/.claude/logs/hooks.log | cut -d'[' -f2 | sort | uniq -c
   ```
   - **Indicates**: Large gaps may mean hooks not being called
   - **Action**: Check Claude Code hook configuration
   - **Fix**: Verify hook integration is active

**Monitoring Script**:
```bash
#!/bin/bash
# Save as: ~/bin/monitor-hooks.sh

LOG_FILE=~/.claude/logs/hooks.log

if [ ! -f "$LOG_FILE" ]; then
    echo "✓ No hook errors (log file doesn't exist yet)"
    exit 0
fi

# Count errors in last 7 days
recent_errors=$(grep "$(date -d '7 days ago' +%Y-%m-%d)" "$LOG_FILE" 2>/dev/null | wc -l)

if [ "$recent_errors" -eq 0 ]; then
    echo "✓ No hook errors in last 7 days"
else
    echo "⚠️  $recent_errors hook errors in last 7 days"
    echo "Recent errors:"
    tail -10 "$LOG_FILE"
    echo ""
    echo "Review full log: cat $LOG_FILE"
fi

# Check log file size
file_size=$(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null)
file_size_mb=$((file_size / 1024 / 1024))

if [ "$file_size_mb" -gt 10 ]; then
    echo "⚠️  Hook log is ${file_size_mb}MB (consider rotating)"
fi
```

## Error Logging Integration

### Two Logging Mechanisms

The hook system uses **two separate logging mechanisms** for different purposes:

| Aspect | `_log_hook_error()` | `log_error()` |
|--------|-------------------|---------------|
| **Purpose** | Hook lifecycle errors | General application errors |
| **Log File** | `~/.claude/logs/hooks.log` | `~/.claude/logs/errors.log` |
| **Format** | `[timestamp] [thanos-orchestrator] <message>` | Structured error with component |
| **When Used** | Top-level hook failures | Nested operation failures |
| **Fallback** | stderr if file write fails | Depends on error_logger config |
| **Dependencies** | None (standalone) | Requires `Tools.error_logger` |
| **Example** | `morning-brief error: State file missing` | `[thanos_orchestrator] Failed to read state: FileNotFoundError` |

**Why Two Mechanisms?**

1. **Separation of Concerns**:
   - Hook errors are lifecycle issues (Claude Code integration)
   - Application errors are operational issues (Thanos functionality)

2. **Different Audiences**:
   - `hooks.log` is for debugging hook integration
   - `errors.log` is for monitoring application health

3. **Fallback Safety**:
   - `_log_hook_error()` has no dependencies (even if error_logger fails)
   - Critical for fail-safe design (hooks must never fail)

**Example: Nested Error Logging**

When session-end hook reads state files:

```python
# In handle_hook() for session-end event
try:
    from Tools.state_reader import StateReader
    reader = StateReader(base_dir / "State")
    ctx = reader.get_quick_context()
    # ... use context ...
except (OSError, IOError) as e:
    # Logs to ~/.claude/logs/errors.log
    log_error("thanos_orchestrator", e, "Failed to read state for session log")
    session_log += "- [Context unavailable]\n"
    # Hook continues, context marked as unavailable
except Exception as e:
    # Logs to ~/.claude/logs/errors.log
    log_error("thanos_orchestrator", e, "Unexpected error reading context for session log")
    session_log += "- [Context unavailable]\n"
```

If the entire hook fails:

```python
# In handle_hook() top-level exception handler
try:
    if event == "morning-brief":
        # ... hook logic ...
    elif event == "session-end":
        # ... hook logic ...
except Exception as e:
    # Logs to ~/.claude/logs/hooks.log
    _log_hook_error(f"{event} error: {e}")
    pass  # Hook exits cleanly
```

**Finding Errors Across Both Logs**:

```bash
# Check hook lifecycle errors
cat ~/.claude/logs/hooks.log

# Check application errors from hooks
grep "thanos_orchestrator" ~/.claude/logs/errors.log

# Recent errors from both sources
echo "=== Hook Errors ===" && tail -10 ~/.claude/logs/hooks.log
echo ""
echo "=== Application Errors ===" && grep "thanos_orchestrator" ~/.claude/logs/errors.log | tail -10
```

## Comparison with Other Error Handling

### Hook vs. Cache vs. API Error Handling

Understanding how hooks differ from other error handling systems:

| Aspect | Hook Errors | Cache Errors | API Errors |
|--------|------------|--------------|------------|
| **Failure Mode** | Log and continue | Silent failure | Automatic fallback |
| **Logging** | Explicit to hooks.log | None (completely silent) | Detailed to component logs |
| **User Visibility** | Log file + optional stderr | None | Error messages may surface |
| **Automatic Recovery** | Retry next hook invocation | Next cache operation retries | Fallback chain to next model |
| **Manual Cleanup** | Fix underlying issue | Clear cache directory | Check API keys, quotas |
| **Impact on Operation** | Missing context/logs | Cache miss, triggers API call | May fail user request |
| **Retry Logic** | None (one-shot operation) | None (treats as cache miss) | Immediate fallback chain |
| **Performance Impact** | None (exits immediately) | Minimal (graceful degradation) | Moderate (tries multiple models) |
| **Configuration** | Hardcoded paths | Environment variables | config/api.json |

**Similarity Across All Three**:
- ✅ All prioritize reliability over strict error reporting
- ✅ All catch exceptions at system boundaries
- ✅ All implement graceful degradation
- ✅ All prevent errors from disrupting user workflow

**Key Differences**:

1. **Hooks Never Retry**
   - Cache: Treats corruption as cache miss, automatically retries next read
   - API: Immediately tries next model in fallback chain
   - **Hooks**: One-shot operation, next invocation is the "retry"

2. **Logging Strategy**
   - Hooks: Explicit logging to dedicated log file
   - Cache: Completely silent (by design, not a bug)
   - API: Detailed logging with fallback tracking

3. **User Notification**
   - Hooks: Silent unless log file write fails (stderr fallback)
   - Cache: Never notifies user
   - API: May show error messages if entire fallback chain fails

**When Each Error Type Matters**:

- **Hook errors**: Matter if you need morning context or session history
- **Cache errors**: Matter if API costs are high or performance is critical
- **API errors**: Matter immediately (blocks user request if all fallbacks fail)

**Debugging Priority**:

1. **Critical**: API errors (user-facing, immediate impact)
2. **Important**: Cache errors (cost and performance impact)
3. **Low Priority**: Hook errors (convenience features, non-blocking)

### Example: Cascade of Errors

What happens when multiple systems fail together:

```
User starts Claude Code session
         ↓
┌────────────────────────┐
│ Morning Brief Hook     │
│ Tries to read State/   │
│ Today.md               │
└────────┬───────────────┘
         │ (file missing)
         ▼
┌────────────────────────┐
│ Hook Error Handling    │ ← Logs to hooks.log
│ Marks context as       │   Hook exits cleanly
│ unavailable            │   Session starts normally
└────────┬───────────────┘
         │
         ▼
User makes API request
         ↓
┌────────────────────────┐
│ Check Response Cache   │
│ for previous result    │
└────────┬───────────────┘
         │ (cache corrupted)
         ▼
┌────────────────────────┐
│ Cache Error Handling   │ ← Silent failure
│ Treats as cache miss   │   No log entry
│ Continues to API       │   User unaware
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│ LiteLLM API Call       │
│ Try first model        │
└────────┬───────────────┘
         │ (rate limit)
         ▼
┌────────────────────────┐
│ API Error Handling     │ ← Logs fallback
│ Try next model in      │   May show warning
│ fallback chain         │   Request succeeds
└────────┬───────────────┘
         │ (success)
         ▼
Response returned to user
```

**Result**:
- ✅ User gets response (all systems degraded gracefully)
- ✅ Missing morning context (logged to hooks.log)
- ✅ Cache miss (silent, no record)
- ✅ Fallback model used (logged)

**Each layer handled its error independently and appropriately.**

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

## Scenario 6: "No morning context shown at session start"

**Symptoms**:
- Claude Code session starts without morning brief
- No context displayed at startup
- Session continues normally

**Diagnosis**:
```bash
# 1. Check hook logs for errors
tail -20 ~/.claude/logs/hooks.log | grep "morning-brief"

# 2. Verify State directory structure
ls -la State/
cat State/Today.md

# 3. Test hook manually
python Tools/thanos_orchestrator.py hook morning-brief

# 4. Check StateReader functionality
python -c "from Tools.state_reader import StateReader; print('StateReader OK')"
```

**Common Causes**:
1. `State/Today.md` file missing
2. StateReader module import failure
3. Corrupted state files
4. Permission denied on State directory
5. Hook not configured in Claude Code

**Resolution**:
```bash
# 1. Create State directory and Today.md if missing
mkdir -p State
cat > State/Today.md <<'EOF'
# Today

## Focus
- Main tasks for today

## Notes
- Important context
EOF

# 2. Fix permissions
chmod 755 State
chmod 644 State/Today.md

# 3. Verify hook works
python Tools/thanos_orchestrator.py hook morning-brief
# Should output JSON with context

# 4. Check for errors in hook log
tail -10 ~/.claude/logs/hooks.log
```

**Impact**:
- No functional impact (session works normally)
- Missing convenience feature only
- Can continue without morning context

## Scenario 7: "Cache not improving performance"

**Symptoms**:
- API calls still slow despite cache
- Expected cache hits not occurring
- API costs higher than expected with caching enabled

**Diagnosis**:
```bash
# 1. Check cache directory exists and has files
ls -la Memory/cache/
echo "Cache files: $(ls Memory/cache/*.json 2>/dev/null | wc -l)"

# 2. Test cache file integrity
corrupted=0
total=0
for f in Memory/cache/*.json; do
    [ -f "$f" ] || continue
    total=$((total + 1))
    jq empty "$f" 2>/dev/null || {
        echo "Corrupted: $f"
        corrupted=$((corrupted + 1))
    }
done
echo "Corruption rate: $corrupted / $total"

# 3. Check cache file ages
ls -lt Memory/cache/*.json | head -10

# 4. Verify cache TTL configuration
# Check ResponseCache initialization in code for ttl_seconds value

# 5. Monitor for cache usage
# Make same request twice and check timing
time python -c "from Tools.litellm.client import LiteLLMClient; ..."
```

**Common Causes**:
1. Cache TTL too short (entries expire quickly)
2. High corruption rate preventing cache reads
3. Cache key mismatch (different parameters/prompts)
4. Frequent model changes bypass cache
5. Cache directory permissions prevent reads
6. Requests always unique (no repeating patterns)

**Resolution**:
```bash
# 1. Clear corrupted cache and start fresh
rm -rf Memory/cache/*.json

# 2. Check cache permissions
ls -ld Memory/cache/
chmod 755 Memory/cache/

# 3. Review cache TTL setting
# For production, consider 24 hours (86400 seconds)
# Edit code where ResponseCache is instantiated:
# cache = ResponseCache(cache_path="Memory/cache", ttl_seconds=86400)

# 4. Monitor cache hit patterns
# Add instrumentation using MonitoredCache class (see Cache Monitoring section)

# 5. Verify requests are actually cacheable
# Check if prompts and parameters are consistent
```

**Performance Expectations**:
- **Cache Hit**: < 10ms response time
- **Cache Miss**: Full API call latency (1-5 seconds)
- **Good Hit Rate**: > 50% for production workloads
- **Poor Hit Rate**: < 20% indicates caching ineffective

## Scenario 8: "Intermittent API failures"

**Symptoms**:
- Some requests succeed, others fail
- Errors appear randomly
- Fallback chain sometimes helps, sometimes doesn't

**Diagnosis**:
```bash
# 1. Check for network issues
ping -c 5 api.anthropic.com
ping -c 5 api.openai.com

# 2. Test API connectivity
curl -I https://api.anthropic.com/v1/messages
curl -I https://api.openai.com/v1/chat/completions

# 3. Review error patterns in logs
grep -i "error\|fail" ~/.claude/logs/thanos.log | tail -50

# 4. Check for rate limiting patterns
grep -i "rate limit\|429" ~/.claude/logs/thanos.log | tail -20

# 5. Monitor API status
# Anthropic: https://status.anthropic.com
# OpenAI: https://status.openai.com
```

**Common Causes**:
1. Network instability (WiFi, VPN, ISP issues)
2. Intermittent rate limiting (burst usage)
3. Provider service degradation
4. DNS resolution issues
5. Firewall/proxy intermittently blocking requests
6. Timeout settings too aggressive

**Resolution**:
```bash
# 1. Test network stability
for i in {1..10}; do
    echo "Test $i:"
    curl -s -w "Time: %{time_total}s\n" -o /dev/null \
        -H "x-api-key: $ANTHROPIC_API_KEY" \
        https://api.anthropic.com/v1/messages
    sleep 2
done

# 2. Check DNS resolution
nslookup api.anthropic.com
nslookup api.openai.com

# 3. Review firewall/proxy logs if applicable
# Check corporate network policies

# 4. Add timeout buffer if errors are timeout-related
# (Would require code change to increase timeout values)

# 5. Enable detailed logging
export LITELLM_LOG_LEVEL=DEBUG
# Run application and review detailed logs

# 6. Diversify fallback chain across providers
# Ensure config/api.json uses multiple providers
cat config/api.json | jq '.litellm.fallback_chain'
```

**Prevention**:
- Use diverse providers in fallback chain
- Monitor network quality regularly
- Set up provider status monitoring
- Configure reasonable timeout values
- Consider request throttling for burst protection

## Scenario 9: "Inconsistent responses from same prompt"

**Symptoms**:
- Same prompt returns different responses unexpectedly
- Response quality varies significantly
- Cache doesn't seem to return consistent results

**Diagnosis**:
```bash
# 1. Check if different models being used
grep "model" ~/.claude/logs/thanos.log | tail -20

# 2. Review fallback chain activity
export LITELLM_LOG_LEVEL=DEBUG
# Make request and observe which model responds

# 3. Check cache for the prompt
# (Cache key depends on prompt + model + parameters)
ls -lt Memory/cache/*.json | head -10

# 4. Verify model parameters are consistent
# Check temperature, max_tokens, etc. in request
```

**Common Causes**:
1. Fallback chain switching models due to failures
2. Cache miss causes new API call with different response
3. Model parameters (temperature) not deterministic
4. Different models in fallback have different capabilities
5. Cache key mismatch due to parameter variations
6. Cached response expired, new model response cached

**Resolution**:
```bash
# 1. Fix primary model to avoid fallbacks
# Investigate why primary model failing
grep "fallback" ~/.claude/logs/thanos.log

# 2. Use temperature=0 for deterministic responses
# (Requires code change or configuration option)

# 3. Clear cache if stale responses
rm -rf Memory/cache/*.json

# 4. Simplify fallback chain to single model for consistency
# Edit config/api.json:
{
  "litellm": {
    "fallback_chain": ["claude-sonnet-4-20250514"]
  }
}

# 5. Review usage tracking to see which models actually used
# (Note: Current tracking shows requested model, not actual)
```

**Understanding**:
- **Fallback changes models**: Different models = different responses
- **Cache uses requested model**: Not actual model used
- **Temperature > 0**: Non-deterministic responses
- **Parameter changes**: Break cache key matching

**Recommendations**:
- For consistent responses: Use single reliable model
- For diverse responses: Embrace fallback variety
- For debugging: Enable DEBUG logging to see which model responds
- For cost tracking: Monitor provider dashboards directly

## Scenario 10: "Cannot write session logs"

**Symptoms**:
- No session files appearing in `History/Sessions/`
- Hook logs show write errors
- Session ends normally but no history recorded

**Diagnosis**:
```bash
# 1. Check hook logs
grep "session-end" ~/.claude/logs/hooks.log | tail -20

# 2. Verify directory permissions
ls -ld History/
ls -ld History/Sessions/

# 3. Check disk space
df -h .

# 4. Test manual file creation
touch History/Sessions/test.md
rm History/Sessions/test.md

# 5. Test hook manually
python Tools/thanos_orchestrator.py hook session-end
ls -lt History/Sessions/ | head -5
```

**Common Causes**:
1. Permission denied on `History/Sessions/` directory
2. Disk full or quota exceeded
3. Parent `History/` directory missing
4. Filesystem mounted read-only
5. StateReader fails to gather context (logs error but continues)

**Resolution**:
```bash
# 1. Create directory structure
mkdir -p History/Sessions
chmod 755 History
chmod 755 History/Sessions

# 2. Fix ownership if needed
# If running as different user:
# sudo chown -R $USER:$USER History/

# 3. Free up disk space if needed
df -h .
# If low, clean cache or other temporary files
find Memory/cache/ -name "*.json" -mtime +30 -delete

# 4. Verify filesystem is writable
touch /tmp/test && rm /tmp/test && echo "Filesystem OK"

# 5. Check for SELinux/AppArmor restrictions
# (If on Linux with mandatory access controls)
getenforce  # SELinux
sudo aa-status  # AppArmor

# 6. Test hook end-to-end
python Tools/thanos_orchestrator.py hook session-end
ls -lt History/Sessions/*.md | head -1
cat $(ls -t History/Sessions/*.md | head -1)
```

**Prevention**:
```bash
# Add to initialization/setup script
mkdir -p History/Sessions Memory/cache State ~/.claude/logs
chmod -R 755 History Memory State ~/.claude

# Monitor disk space regularly
df -h . | tail -1 | awk '{if ($5+0 > 90) print "WARNING: Disk usage high: " $5}'
```

## Scenario 11: "Fallback chain exhausted too quickly"

**Symptoms**:
- All models in fallback chain fail rapidly
- Request fails with "all models failed" error
- Fallback doesn't provide expected resilience

**Diagnosis**:
```bash
# 1. Enable debug logging to see fallback progression
export LITELLM_LOG_LEVEL=DEBUG

# 2. Check fallback chain configuration
cat config/api.json | jq '.litellm.fallback_chain'

# 3. Test each model individually
# Anthropic
curl -X POST https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-sonnet-4-20250514","messages":[{"role":"user","content":"test"}],"max_tokens":10}'

# OpenAI
curl -X POST https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "content-type: application/json" \
  -d '{"model":"gpt-4-turbo","messages":[{"role":"user","content":"test"}],"max_tokens":10}'

# 4. Review recent errors
tail -100 ~/.claude/logs/thanos.log | grep -i "error\|fail"
```

**Common Causes**:
1. All API keys invalid or expired simultaneously
2. Request parameters incompatible with all models
3. All providers experiencing outages (very rare)
4. Network blocking all API endpoints
5. Request too large for all configured models
6. Billing issues across all providers

**Resolution**:
```bash
# 1. Verify each API key individually
echo "Testing Anthropic..."
curl -I -H "x-api-key: $ANTHROPIC_API_KEY" https://api.anthropic.com/v1/messages
echo "Testing OpenAI..."
curl -I -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models

# 2. Check account status on provider dashboards
# - Anthropic Console: https://console.anthropic.com
# - OpenAI Platform: https://platform.openai.com

# 3. Review billing and quotas
# Ensure accounts are active and have available credits

# 4. Simplify request to test
# Remove special parameters, reduce size

# 5. Try single known-working model
# Edit config/api.json temporarily:
{
  "litellm": {
    "fallback_chain": ["claude-sonnet-4-20250514"]
  }
}

# 6. Check request parameters
# Ensure max_tokens, temperature within valid ranges
# Ensure model names are correct and currently available
```

**Common Request Parameter Issues**:
```bash
# Check for these problems:
# - max_tokens too large (exceeds model limit)
# - Invalid model names (model deprecated or renamed)
# - System prompts not supported by all models
# - Special features (tools, vision) not available on all models
```

**Emergency Fallback**:
```json
{
  "litellm": {
    "fallback_chain": [
      "claude-3-5-haiku-20241022"  // Fastest, most reliable Anthropic model
    ]
  }
}
```

**Long-term Fix**:
- Maintain valid API keys across providers
- Monitor provider status pages
- Set up billing alerts
- Test fallback chain regularly
- Keep model list updated with current model names
- Use diverse providers to avoid single point of failure

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
