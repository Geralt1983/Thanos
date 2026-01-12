# Input Validation and Rate Limiting

This document describes the comprehensive security measures implemented in the WorkOS MCP server to protect against abuse, resource exhaustion, and malicious inputs.

## Table of Contents

- [Overview](#overview)
- [Rate Limiting](#rate-limiting)
- [Input Validation](#input-validation)
- [Error Response Format](#error-response-format)
- [Configuration](#configuration)
- [Examples](#examples)
- [Adjusting Limits](#adjusting-limits)
- [Architecture](#architecture)

---

## Overview

The WorkOS MCP server implements two layers of security protection:

1. **Rate Limiting** - Prevents abuse and resource exhaustion by limiting request frequency
2. **Input Validation** - Enforces bounds on all input parameters to prevent malicious or malformed data

These measures protect against:
- Denial of Service (DoS) attacks
- Database resource exhaustion
- Memory exhaustion from unbounded inputs
- SQL injection and other injection attacks
- Runaway API/database costs
- Client misconfigurations causing excessive requests

**Security Philosophy**: Fail-fast with clear error messages. All invalid requests are rejected immediately with user-friendly guidance on how to fix the issue.

---

## Rate Limiting

### Overview

The server implements a **three-tier sliding window rate limiter** that tracks request frequency across multiple dimensions:

1. **Global Limit** - Total requests per minute (all operations)
2. **Write Limit** - Write operations per minute (creates, updates, deletes)
3. **Read Limit** - Read operations per minute (queries, retrievals)

### Default Limits

| Limit Type | Per Minute | Per Hour | Description |
|------------|------------|----------|-------------|
| **Global** | 100 | 3,000 | All requests combined (~1.7 req/sec burst) |
| **Write** | 20 | - | Create, update, delete operations |
| **Read** | 60 | - | Query and retrieval operations |

### Operation Classification

Operations are automatically classified as read or write based on their action:

**Write Operations** (20/min limit):
- Task creation, updates, completion, promotion, deletion
- Habit creation, completion
- Brain dump creation, processing
- Energy logging
- Streak recalculation

**Read Operations** (60/min limit):
- Task queries and retrieval
- Habit queries and retrieval
- Brain dump retrieval
- Energy log retrieval
- Metrics and dashboard queries
- Client memory retrieval

### Algorithm

The rate limiter uses a **sliding window algorithm** with in-memory storage:

- Tracks timestamps of all requests in the last 60 minutes
- Checks against all applicable limits (global, write/read)
- Rejects requests that exceed any limit
- Automatically cleans up old timestamps every 5 minutes

**Why sliding window?** Unlike fixed windows, sliding windows prevent burst traffic at window boundaries and provide smoother rate limiting.

### Rate Limit Responses

When a rate limit is exceeded, the server returns an MCP error with:

```json
{
  "isError": true,
  "content": [
    {
      "type": "text",
      "text": "Rate limit exceeded: You have made 21 write requests in the last minute (limit: 20). Please wait 45 seconds and try again."
    }
  ]
}
```

The error message includes:
- Which limit was exceeded (global, write, or read)
- Current request count vs. limit
- Time window description
- **Retry-after** guidance in seconds

---

## Input Validation

### Overview

All MCP tool inputs are validated using **Zod schemas** with comprehensive bounds checking. Every string, number, and enum is validated before processing.

### Validation Layers

1. **Type Validation** - Ensures correct data types (string, number, boolean, enum)
2. **Length Validation** - Enforces min/max lengths on all strings
3. **Range Validation** - Enforces min/max values on all numbers
4. **Enum Validation** - Restricts values to predefined sets
5. **Refinement Validation** - Custom business rules (e.g., can't create task with status "done")

### String Field Limits

| Field Type | Min Length | Max Length | Rationale |
|------------|------------|------------|-----------|
| **Task Title** | 1 | 200 | ~30 words, concise yet descriptive |
| **Task Description** | 0 | 2,000 | ~300 words, comprehensive context |
| **Client Name** | 1 | 100 | Accommodates long company names |
| **Habit Name** | 1 | 100 | Concise habit descriptions |
| **Habit Description** | 0 | 500 | ~75 words, brief explanations |
| **Habit Emoji** | 0 | 10 | Multi-codepoint emoji sequences |
| **Habit Note** | 0 | 500 | Brief completion reflections |
| **Energy Note** | 0 | 500 | Brief energy context |
| **Brain Dump Content** | 1 | 5,000 | ~750 words, longer-form thoughts |

**Rationale**: These limits prevent memory exhaustion while being generous enough for all legitimate use cases.

### Numeric Field Limits

| Field Type | Min Value | Max Value | Rationale |
|------------|-----------|-----------|-----------|
| **Query Limit** | 1 | 100 | Prevents massive result sets |
| **Task/Habit IDs** | 1 | 2,147,483,647 | PostgreSQL INT32_MAX |
| **Client IDs** | 1 | 2,147,483,647 | PostgreSQL INT32_MAX |
| **Days (Streaks)** | 1 | 365 | 1 year max for performance |
| **Days (Dashboard)** | 1 | 90 | 3 months max for readability |
| **Habit Target Count** | 1 | 100 | Prevents absurd values |
| **Oura Readiness** | 0 | 100 | Official Oura Ring range |
| **Oura HRV** | 0 | 300 | Typical 20-100ms, 300ms max |
| **Oura Sleep Score** | 0 | 100 | Official Oura Ring range |

**Rationale**: These limits prevent database overload, ensure valid IDs, and enforce manufacturer-documented metric ranges.

### Enum Validation

All enum fields are strictly validated against predefined sets:

| Field | Valid Values |
|-------|--------------|
| **Task Status** | `active`, `queued`, `backlog`, `done` |
| **Task Category** | `work`, `personal` |
| **Value Tier** | `checkbox`, `progress`, `deliverable`, `milestone` |
| **Drain Type** | `deep`, `shallow`, `admin` |
| **Habit Frequency** | `daily`, `weekly`, `custom` |
| **Habit Time of Day** | `morning`, `afternoon`, `evening`, `anytime` |
| **Habit Category** | `health`, `productivity`, `learning`, `social`, `creative`, `other` |
| **Energy Level** | `high`, `medium`, `low` |
| **Brain Dump Category** | `thought`, `task`, `idea`, `worry` |
| **Dashboard Format** | `compact`, `detailed`, `weekly` |

### Sanitization

All string inputs are automatically **trimmed** of leading/trailing whitespace before validation. This prevents:
- Accidental whitespace causing validation failures
- Inconsistent data in the database
- Misleading character counts

---

## Error Response Format

### Validation Errors

When input validation fails, the server returns an MCP error with a clear, actionable message:

```json
{
  "isError": true,
  "content": [
    {
      "type": "text",
      "text": "title must not exceed 200 characters (received: 247 characters)"
    }
  ]
}
```

**Error Message Format**:
- States which field failed validation
- Shows the constraint that was violated
- Shows the actual value received (for lengths/ranges)
- User-friendly language without technical jargon

### Examples of Validation Errors

**String too long**:
```
title must not exceed 200 characters (received: 247 characters)
```

**String too short**:
```
content must be at least 1 character (received: 0 characters)
```

**Number out of range**:
```
limit must be between 1 and 100 (received: 150)
```

**Invalid enum value**:
```
status must be one of: active, queued, backlog, done (received: "completed")
```

**Positive integer required**:
```
taskId must be a positive integer (received: -5)
```

**Non-integer value**:
```
limit must be an integer (received: 50.5)
```

**Business rule violation**:
```
Cannot create a task with status 'done'
```

### Rate Limit Errors

```json
{
  "isError": true,
  "content": [
    {
      "type": "text",
      "text": "Rate limit exceeded: You have made 21 write requests in the last minute (limit: 20). Please wait 45 seconds and try again."
    }
  ]
}
```

**Components**:
- Limit type exceeded (global, write, or read)
- Current count vs. limit
- Time window description
- Retry-after guidance in seconds

---

## Configuration

### Environment Variables

All limits can be adjusted via environment variables **without code changes**:

#### Rate Limiting

```bash
# Disable rate limiting entirely (for testing only)
export RATE_LIMIT_ENABLED=false

# Adjust global limits
export RATE_LIMIT_GLOBAL_PER_MINUTE=200
export RATE_LIMIT_GLOBAL_PER_HOUR=6000

# Adjust operation-specific limits
export RATE_LIMIT_WRITE_PER_MINUTE=40
export RATE_LIMIT_READ_PER_MINUTE=120
```

#### Defaults

If environment variables are not set, the server uses these defaults:

```typescript
{
  enabled: true,
  globalPerMinute: 100,
  globalPerHour: 3000,
  writeOpsPerMinute: 20,
  readOpsPerMinute: 60
}
```

### When to Adjust Limits

**Increase limits if**:
- Legitimate users frequently hit rate limits
- You have high-frequency automation (CI/CD, monitoring)
- Server resources can handle higher throughput

**Decrease limits if**:
- Experiencing abuse or suspicious activity
- Database costs are too high
- Server resources are constrained

**Disable rate limiting if**:
- Running in a development/testing environment
- Performing bulk data operations
- Server is behind another rate limiter (reverse proxy, API gateway)

⚠️ **Warning**: Disabling rate limiting in production exposes the server to abuse and resource exhaustion.

---

## Examples

### Valid Requests

**Create Task** (all inputs within bounds):
```json
{
  "name": "workos_create_task",
  "arguments": {
    "title": "Implement user authentication",
    "description": "Add JWT-based authentication with refresh tokens and role-based access control",
    "status": "active",
    "category": "work",
    "valueTier": "deliverable"
  }
}
```
✅ **Result**: Task created successfully

**Get Tasks** (query limit within bounds):
```json
{
  "name": "workos_get_tasks",
  "arguments": {
    "status": "active",
    "limit": 50
  }
}
```
✅ **Result**: Returns up to 50 active tasks

### Invalid Requests

**Task Title Too Long**:
```json
{
  "name": "workos_create_task",
  "arguments": {
    "title": "This is an extremely long task title that exceeds the maximum allowed length of 200 characters. It keeps going and going with unnecessary verbosity that makes it hard to read and understand at a glance. This is the kind of title that should be rejected by validation..."
  }
}
```
❌ **Error**: `title must not exceed 200 characters (received: 247 characters)`

**Invalid Query Limit**:
```json
{
  "name": "workos_get_tasks",
  "arguments": {
    "limit": 500
  }
}
```
❌ **Error**: `limit must be between 1 and 100 (received: 500)`

**Invalid Enum Value**:
```json
{
  "name": "workos_create_task",
  "arguments": {
    "title": "Valid title",
    "status": "completed"
  }
}
```
❌ **Error**: `status must be one of: active, queued, backlog, done (received: "completed")`

**Negative ID**:
```json
{
  "name": "workos_update_task",
  "arguments": {
    "taskId": -5,
    "title": "Updated title"
  }
}
```
❌ **Error**: `taskId must be a positive integer (received: -5)`

**Rate Limit Exceeded**:
```bash
# 21st write request in one minute
```
❌ **Error**: `Rate limit exceeded: You have made 21 write requests in the last minute (limit: 20). Please wait 45 seconds and try again.`

---

## Adjusting Limits

### Modifying String Limits

String limits are defined in `src/shared/validation-constants.ts`:

```typescript
export const STRING_LIMITS = {
  TASK_TITLE_MAX: 200,      // Increase if users need longer titles
  TASK_DESCRIPTION_MAX: 2000, // Increase for more detailed descriptions
  // ... other limits
} as const;
```

**After modifying**:
1. Consider database VARCHAR length limits
2. Test with edge cases at the new limit
3. Update this documentation
4. Rebuild: `npm run build`

### Modifying Numeric Limits

Numeric limits are defined in `src/shared/validation-constants.ts`:

```typescript
export const NUMERIC_LIMITS = {
  QUERY_LIMIT_MAX: 100,     // Increase if users need larger result sets
  DAYS_MAX_STREAKS: 365,     // Increase if users need longer streak calculations
  // ... other limits
} as const;
```

**After modifying**:
1. Consider database query performance impact
2. Test with the new limit values
3. Update this documentation
4. Rebuild: `npm run build`

### Modifying Rate Limits

**Recommended**: Use environment variables (no code changes required):

```bash
export RATE_LIMIT_GLOBAL_PER_MINUTE=200
```

**Alternative**: Modify defaults in `src/shared/validation-constants.ts`:

```typescript
export const RATE_LIMITS = {
  GLOBAL_PER_MINUTE: 100,   // Adjust default global limit
  WRITE_OPS_PER_MINUTE: 20,  // Adjust default write limit
  READ_OPS_PER_MINUTE: 60,   // Adjust default read limit
} as const;
```

**After modifying**:
1. Monitor server resource usage
2. Monitor database connection pool usage
3. Test under load to ensure stability
4. Update this documentation
5. Rebuild: `npm run build`

---

## Architecture

### Rate Limiting Architecture

**Components**:

1. **RateLimiter Class** (`src/shared/rate-limiter.ts`)
   - Sliding window algorithm implementation
   - In-memory timestamp tracking
   - Automatic cleanup every 5 minutes

2. **Integration Point** (`src/index.ts`)
   - Rate limiter check before routing to domain handlers
   - Requests blocked before any database access
   - Efficient fail-fast approach

3. **Operation Classification**
   - Automatic classification based on tool name
   - Keywords: `create`, `update`, `delete`, `complete`, `log`, `dump`, `process` = write
   - All other operations = read

**Data Flow**:
```
Request → Rate Limiter Check → [Allowed/Blocked]
                                      ↓
                                   Blocked: Return error with retry-after
                                      ↓
                                   Allowed: Record request + route to handler
```

### Validation Architecture

**Components**:

1. **Validation Constants** (`src/shared/validation-constants.ts`)
   - Centralized limits and error message templates
   - Environment variable overrides
   - Comprehensive JSDoc documentation

2. **Schema Helpers** (`src/shared/validation-schemas.ts`)
   - Reusable Zod schema builders (`minMaxString`, `positiveInt`, `boundedInt`)
   - 29 common field schemas (taskId, taskTitle, etc.)
   - 12 enum schemas
   - Validation utilities (`validateToolInput`, `sanitizeInput`, `validateAndSanitize`)

3. **Domain Validation** (`src/domains/*/validation.ts`)
   - Domain-specific tool input schemas
   - Composed from common field schemas
   - Business rule refinements

4. **Handler Integration** (`src/domains/*/handlers.ts`)
   - `validateAndSanitize()` call at the start of every handler
   - Validates + sanitizes inputs before processing
   - Returns user-friendly errors on validation failure

**Data Flow**:
```
Request → Handler → validateAndSanitize() → [Valid/Invalid]
                                                  ↓
                                               Invalid: Return validation error
                                                  ↓
                                               Valid: Process request
```

### Security Guarantees

1. **Defense in Depth**: Rate limiting AND input validation
2. **Fail-Fast**: Invalid requests rejected immediately
3. **No Bypasses**: All requests go through validation
4. **Type Safety**: TypeScript + Zod prevent type errors
5. **User-Friendly**: Clear error messages guide users to correct inputs

### Performance Considerations

- **Rate Limiter**: O(1) checks with periodic O(n) cleanup (n = requests in window)
- **Validation**: O(1) schema validation per field
- **Memory Usage**: Minimal (timestamps only, auto-cleanup every 5 minutes)
- **Database Impact**: Zero (validation happens before database access)

---

## Testing

The security measures are comprehensively tested:

### Validation Tests

Run validation test suite:
```bash
node test-validation.mjs
```

**Coverage** (80 tests):
- String length validation (14 tests)
- Numeric range validation (16 tests)
- Enum validation (11 tests)
- Missing required fields (6 tests)
- Edge cases (10 tests)
- Complex schema validation (10 tests)
- Sanitization (4 tests)
- Schema helpers (9 tests)

### Rate Limiting Tests

Run rate limiting test suite:
```bash
node test-rate-limiting.mjs
```

**Coverage** (35 tests):
- Initialization & configuration (4 tests)
- Request counting & tracking (4 tests)
- Operation classification (2 tests)
- Rate limit enforcement (7 tests)
- Error messages & retry-after (4 tests)
- Window sliding & time-based reset (4 tests)
- Edge cases (8 tests)
- Concurrent operations (2 tests)

### End-to-End Integration Tests

Run E2E integration tests:
```bash
node test-e2e-integration.mjs
```

**Coverage** (32 tests):
- Valid inputs accepted (6 tests)
- Invalid inputs rejected (9 tests)
- Boundary value handling (9 tests)
- Rate limiting enforcement (1 test)
- Error message quality (4 tests)
- Input sanitization (2 tests)

**All tests pass**: 147/147 ✓

---

## Security Best Practices

### For Operators

1. **Monitor rate limit violations** - Investigate clients that frequently hit limits
2. **Adjust limits conservatively** - Start with defaults, increase only if needed
3. **Never disable rate limiting in production** - Use environment variable overrides instead
4. **Review logs for suspicious patterns** - Repeated validation errors may indicate probing
5. **Keep validation bounds generous** - Overly restrictive limits frustrate legitimate users

### For Developers

1. **Never bypass validation** - All inputs must go through validation schemas
2. **Add tests for new validators** - Test valid, invalid, and edge cases
3. **Use common field schemas** - Reuse existing schemas for consistency
4. **Document rationale for limits** - Explain why each limit is set
5. **Keep error messages user-friendly** - Technical details go in logs, not error messages

### For API Clients

1. **Respect rate limits** - Implement exponential backoff when rate limited
2. **Validate inputs client-side** - Catch errors before sending to server
3. **Use retry-after guidance** - Wait the suggested time before retrying
4. **Batch operations when possible** - Reduce total request count
5. **Cache read results** - Avoid redundant queries

---

## Summary

The WorkOS MCP server implements comprehensive security measures:

✅ **Rate Limiting**: Three-tier sliding window algorithm prevents abuse
✅ **Input Validation**: Comprehensive bounds checking on all inputs
✅ **User-Friendly Errors**: Clear, actionable error messages
✅ **Configurable**: Environment variable overrides without code changes
✅ **Well-Tested**: 147 automated tests covering all scenarios
✅ **Production-Ready**: Fail-fast design with minimal performance impact

These measures protect against:
- Denial of Service attacks
- Resource exhaustion
- Database overload
- Injection attempts
- Runaway costs
- Client misconfigurations

**Result**: A secure, reliable MCP server that handles both legitimate traffic and malicious requests gracefully.

---

## Related Documentation

- **[README.md](README.md)** - Main server documentation
- **[TESTING.md](TESTING.md)** - Testing guide
- **[src/README.md](src/README.md)** - Architecture documentation

---

**Last Updated**: 2026-01-12
**Task**: #014 - MCP Server Lacks Rate Limiting and Input Bounds Checking
