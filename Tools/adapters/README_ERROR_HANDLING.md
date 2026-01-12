# MCP Error Handling and Retry Logic

Comprehensive error handling system for MCP operations with exponential backoff, circuit breaker pattern, and graceful degradation strategies.

## Overview

The MCP error handling system provides:

- **Custom Exception Hierarchy**: Detailed error classification for different failure modes
- **Retry Logic**: Exponential backoff with jitter for transient failures
- **Circuit Breaker**: Prevents cascading failures by temporarily blocking requests to failing servers
- **Graceful Degradation**: Fallback strategies for different error scenarios
- **Detailed Logging**: Rich context for debugging and monitoring

> **Note**: This guide covers MCP-specific error handling. For general Thanos runtime errors (API failures, cache corruption, hook errors), see the **[Thanos Runtime Error Troubleshooting Guide](../../docs/TROUBLESHOOTING.md)**.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Application                         │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              with_retry_and_circuit_breaker             │
│  ┌───────────────────────────────────────────────────┐  │
│  │            RetryPolicy (exponential backoff)      │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │   CircuitBreaker (fault isolation)          │  │  │
│  │  │  ┌───────────────────────────────────────┐  │  │  │
│  │  │  │      MCP Operation (call_tool, etc)   │  │  │  │
│  │  │  └───────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Exception Hierarchy

### Base Exceptions

#### `MCPError`
Base exception for all MCP-related errors. Contains:
- `message`: Human-readable error description
- `context`: Additional error context (dict)
- `server_name`: Server where error occurred
- `retryable`: Whether operation can be retried

### Connection Errors

#### `MCPConnectionError`
Connection or transport failures. Usually retryable.

**Example**:
```python
raise MCPConnectionError(
    message="Failed to connect to MCP server",
    server_name="workos-mcp",
)
```

**Recovery**: Retry with exponential backoff.

#### `MCPTransportError`
Transport-specific failures (stdio, SSE, HTTP).

**Example**:
```python
raise MCPTransportError(
    message="Subprocess terminated unexpectedly",
    transport_type="stdio",
    server_name="workos-mcp",
)
```

**Recovery**: Check process/network configuration, retry.

#### `MCPTimeoutError`
Operation timed out waiting for response.

**Example**:
```python
raise MCPTimeoutError(
    message="Server did not respond",
    timeout_seconds=30.0,
    server_name="workos-mcp",
)
```

**Recovery**: Increase timeout or check server health, retry.

### Protocol Errors

#### `MCPProtocolError`
MCP protocol violation or communication error. Usually not retryable.

**Example**:
```python
raise MCPProtocolError(
    message="Malformed JSON-RPC response",
    server_name="workos-mcp",
    retryable=False,
)
```

**Recovery**: Report to server maintainer, use alternative server.

#### `MCPInitializationError`
Failed to initialize MCP session.

**Example**:
```python
raise MCPInitializationError(
    message="Capability negotiation failed",
    server_name="workos-mcp",
)
```

**Recovery**: Check server version compatibility, verify configuration.

#### `MCPCapabilityError`
Server lacks required capability.

**Example**:
```python
raise MCPCapabilityError(
    message="Server does not support tools",
    capability="tools",
    server_name="workos-mcp",
)
```

**Recovery**: Use different server or alternative approach.

### Tool Errors

#### `MCPToolError`
Base for tool-related errors.

#### `MCPToolNotFoundError`
Requested tool doesn't exist.

**Example**:
```python
raise MCPToolNotFoundError(
    tool_name="invalid_tool",
    available_tools=["list_tasks", "create_task"],
    server_name="workos-mcp",
)
```

**Recovery**: Refresh tool list, verify tool name spelling.

#### `MCPToolExecutionError`
Tool execution failed on server.

**Example**:
```python
raise MCPToolExecutionError(
    tool_name="create_task",
    error_message="Database connection failed",
    server_name="workos-mcp",
    retryable=True,
)
```

**Recovery**: Check tool arguments, retry if transient error.

#### `MCPToolValidationError`
Invalid tool arguments.

**Example**:
```python
raise MCPToolValidationError(
    tool_name="create_task",
    validation_error="Missing required field: title",
    provided_arguments={"description": "test"},
    server_name="workos-mcp",
)
```

**Recovery**: Fix arguments, check tool schema.

### Configuration Errors

#### `MCPConfigurationError`
Invalid MCP configuration.

**Example**:
```python
raise MCPConfigurationError(
    message="Missing required field: command",
    config_path="~/.claude.json",
)
```

**Recovery**: Fix configuration file.

#### `MCPDiscoveryError`
Server discovery failed.

**Example**:
```python
raise MCPDiscoveryError(
    message="No configuration files found",
    search_paths=["~/.claude.json", ".mcp.json"],
)
```

**Recovery**: Create configuration file in searched location.

### Availability Errors

#### `MCPServerUnavailableError`
Server is unavailable or unhealthy.

**Example**:
```python
raise MCPServerUnavailableError(
    message="Server failed health check",
    server_name="workos-mcp",
)
```

**Recovery**: Wait and retry, check server logs.

#### `MCPCircuitBreakerError`
Circuit breaker is open due to repeated failures.

**Example**:
```python
raise MCPCircuitBreakerError(
    server_name="workos-mcp",
    failure_count=5,
    timeout_seconds=30.0,
)
```

**Recovery**: Wait for circuit breaker timeout, check server health.

### Resource Errors

#### `MCPResourceError`
Resource limit or availability error.

#### `MCPRateLimitError`
Rate limit exceeded.

**Example**:
```python
raise MCPRateLimitError(
    message="Too many requests",
    retry_after_seconds=60.0,
    server_name="workos-mcp",
)
```

**Recovery**: Wait specified time, implement request throttling.

## Retry Logic

### Exponential Backoff

The `RetryPolicy` class implements exponential backoff with jitter:

```python
from mcp_retry import RetryPolicy, RetryConfig

# Create policy
policy = RetryPolicy(RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True,
))

# Execute with retry
result = await policy.execute_async(async_function, arg1, arg2)
```

### Retry Configuration

```python
@dataclass
class RetryConfig:
    max_attempts: int = 3          # Maximum retry attempts
    initial_delay: float = 1.0     # Initial delay in seconds
    max_delay: float = 60.0        # Maximum delay between retries
    exponential_base: float = 2.0  # Base for exponential backoff
    jitter: bool = True            # Add random jitter
    jitter_factor: float = 0.1     # Jitter randomness (0.0-1.0)
    timeout: Optional[float] = None # Overall timeout for all attempts
```

### Delay Calculation

```
attempt 0: 1.0s ± 10% jitter
attempt 1: 2.0s ± 10% jitter  (1.0 * 2^1)
attempt 2: 4.0s ± 10% jitter  (1.0 * 2^2)
attempt 3: 8.0s ± 10% jitter  (1.0 * 2^3)
...
max: 60.0s ± 10% jitter
```

Jitter prevents "thundering herd" problem when multiple clients retry simultaneously.

## Circuit Breaker

### States

1. **CLOSED**: Normal operation, requests pass through
2. **OPEN**: Too many failures, requests blocked
3. **HALF_OPEN**: Testing if service recovered

### State Transitions

```
           failure_threshold reached
   CLOSED ─────────────────────────────> OPEN
     ▲                                     │
     │                                     │ timeout expires
     │                                     ▼
     └────────────────────────────── HALF_OPEN
       success_threshold reached
```

### Circuit Breaker Configuration

```python
@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5      # Failures before opening
    success_threshold: int = 2      # Successes to close
    timeout: float = 60.0           # Seconds before half-open
    half_open_max_calls: int = 1    # Max concurrent calls in half-open
```

### Usage

```python
from mcp_retry import CircuitBreaker, CircuitBreakerConfig

# Create circuit breaker
breaker = CircuitBreaker(
    server_name="workos-mcp",
    config=CircuitBreakerConfig(
        failure_threshold=5,
        timeout=60.0,
    ),
)

# Execute with protection
try:
    result = await breaker.call(async_function, arg1, arg2)
except MCPCircuitBreakerError as e:
    print(f"Circuit open, wait {e.context['timeout_seconds']}s")
```

### Circuit Breaker Registry

Manage circuit breakers for multiple servers:

```python
from mcp_retry import get_global_registry

registry = get_global_registry()
breaker = await registry.get_breaker("workos-mcp")

# Get stats for all servers
stats = registry.get_all_stats()

# Reset specific breaker
registry.reset_breaker("workos-mcp")
```

## Combined Retry + Circuit Breaker

Use both patterns together for maximum resilience:

```python
from mcp_retry import (
    with_retry_and_circuit_breaker,
    RetryConfig,
    CircuitBreakerConfig,
)

result = await with_retry_and_circuit_breaker(
    call_mcp_tool,
    server_name="workos-mcp",
    retry_config=RetryConfig(max_attempts=3),
    circuit_breaker_config=CircuitBreakerConfig(failure_threshold=5),
    tool_name="get_tasks",
    arguments={"status": "active"},
)
```

This combines:
1. Exponential backoff for transient failures
2. Circuit breaker to prevent cascading failures
3. Automatic recovery testing

## Fallback Strategies

### Strategy by Error Type

| Error Type | Primary Action | Fallback Strategy |
|------------|---------------|-------------------|
| `MCPConnectionError` | Retry with backoff | Use cached data, try backup server |
| `MCPTimeoutError` | Retry with increased timeout | Return partial results, use cache |
| `MCPToolNotFoundError` | Refresh tool list | Use alternative tool, manual fallback |
| `MCPCapabilityError` | Use different server | Degrade functionality, manual mode |
| `MCPCircuitBreakerError` | Wait for timeout | Use backup server, cached results |
| `MCPRateLimitError` | Wait retry_after duration | Queue request, use cache |
| `MCPConfigurationError` | Fix configuration | Use default config, disable feature |
| `MCPProtocolError` | Report to maintainer | Use alternative server |

### Implementation Example

```python
from mcp_errors import MCPError, classify_error, ErrorRecoveryStrategy

async def call_with_fallback(bridge, tool_name, arguments):
    """Call MCP tool with fallback strategies."""
    try:
        # Try primary approach
        return await with_retry_and_circuit_breaker(
            bridge.call_tool,
            server_name=bridge.name,
            tool_name=tool_name,
            arguments=arguments,
        )
    except MCPCircuitBreakerError as e:
        # Circuit breaker open - try backup server
        logger.warning(f"Circuit open for {bridge.name}, trying backup")
        backup_bridge = get_backup_bridge(bridge.name)
        if backup_bridge:
            return await backup_bridge.call_tool(tool_name, arguments)
        raise

    except MCPToolNotFoundError as e:
        # Tool not found - refresh and retry
        logger.warning(f"Tool not found, refreshing list")
        await bridge.refresh_tools()
        return await bridge.call_tool(tool_name, arguments)

    except MCPCapabilityError as e:
        # Missing capability - degrade gracefully
        logger.error(f"Capability missing: {e.context['missing_capability']}")
        return use_alternative_approach(tool_name, arguments)

    except MCPRateLimitError as e:
        # Rate limited - wait and retry
        wait_time = e.context.get('retry_after_seconds', 60)
        logger.info(f"Rate limited, waiting {wait_time}s")
        await asyncio.sleep(wait_time)
        return await bridge.call_tool(tool_name, arguments)

    except MCPError as e:
        # Generic MCP error - log and handle
        logger.error(f"MCP error: {e}")
        action = ErrorRecoveryStrategy.get_fallback_action(e)
        logger.info(f"Fallback action: {action}")
        raise
```

## Utility Functions

### Error Classification

```python
from mcp_errors import classify_error, is_retryable_error

# Convert generic exception to MCP error
try:
    await operation()
except Exception as e:
    mcp_error = classify_error(e, server_name="workos-mcp")
    if is_retryable_error(mcp_error):
        # Retry logic
        pass
```

### Error Logging

```python
from mcp_errors import log_error_with_context

try:
    await operation()
except Exception as e:
    log_error_with_context(
        e,
        component="tool_execution",
        additional_context={
            "tool_name": "create_task",
            "arguments": arguments,
        },
    )
```

## Best Practices

### 1. Use Specific Exceptions

Raise the most specific exception type:

```python
# ❌ Too generic
raise MCPError("Tool not found")

# ✅ Specific and actionable
raise MCPToolNotFoundError(
    tool_name=tool_name,
    available_tools=bridge.list_tools(),
    server_name=bridge.name,
)
```

### 2. Provide Rich Context

Include relevant context for debugging:

```python
raise MCPToolExecutionError(
    tool_name="create_task",
    error_message=str(e),
    context={
        "arguments": arguments,
        "server_version": server_version,
        "elapsed_time": elapsed,
    },
    server_name=bridge.name,
)
```

### 3. Configure Retry Appropriately

Different operations need different retry strategies:

```python
# Quick operations - fewer retries, shorter delays
quick_config = RetryConfig(
    max_attempts=2,
    initial_delay=0.5,
    max_delay=5.0,
)

# Long operations - more retries, longer delays
long_config = RetryConfig(
    max_attempts=5,
    initial_delay=2.0,
    max_delay=120.0,
)
```

### 4. Monitor Circuit Breaker State

Track circuit breaker metrics:

```python
registry = get_global_registry()
stats = registry.get_all_stats()

for server_name, server_stats in stats.items():
    if server_stats["state"] == "open":
        alert(f"Circuit open for {server_name}")

    if server_stats["failure_count"] > 3:
        warn(f"High failure rate for {server_name}")
```

### 5. Handle Non-Retryable Errors Immediately

Don't retry operations that will always fail:

```python
try:
    result = await operation()
except MCPCapabilityError:
    # Server doesn't support this - don't retry
    return fallback_result()
except MCPConfigurationError:
    # Config is broken - don't retry
    raise
except MCPConnectionError:
    # Transient - retry with backoff
    result = await retry_operation()
```

## Integration with MCPBridge

The error handling system integrates seamlessly with `MCPBridge`:

```python
from mcp_bridge import MCPBridge
from mcp_retry import with_retry_and_circuit_breaker

async def resilient_tool_call(bridge: MCPBridge, tool_name: str, arguments: dict):
    """Call MCP tool with full error handling."""
    return await with_retry_and_circuit_breaker(
        bridge.call_tool,
        server_name=bridge.name,
        tool_name=tool_name,
        arguments=arguments,
    )
```

## Testing

Test error handling and recovery:

```python
import pytest
from mcp_errors import MCPConnectionError
from mcp_retry import RetryPolicy, CircuitBreaker

@pytest.mark.asyncio
async def test_retry_on_connection_error():
    attempts = 0

    async def failing_func():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise MCPConnectionError("Connection failed")
        return "success"

    policy = RetryPolicy(RetryConfig(max_attempts=3))
    result = await policy.execute_async(failing_func)

    assert result == "success"
    assert attempts == 3

@pytest.mark.asyncio
async def test_circuit_breaker_opens():
    breaker = CircuitBreaker("test-server")

    async def failing_func():
        raise MCPConnectionError("Failed")

    # Fail threshold times
    for _ in range(5):
        with pytest.raises(MCPConnectionError):
            await breaker.call(failing_func)

    # Circuit should be open now
    assert breaker.is_open()
```

---

## Related Documentation

### General Thanos Error Handling

For non-MCP runtime errors in Thanos, see:
- **[Thanos Runtime Error Troubleshooting Guide](../../docs/TROUBLESHOOTING.md)**: Comprehensive troubleshooting for:
  - API Error Handling (LiteLLM fallback chains, rate limits, connection failures)
  - Cache Corruption Recovery (silent failures, automatic cleanup, monitoring)
  - Hook Error Management (fail-safe execution, log locations, debugging)
  - Common troubleshooting scenarios and resolution steps
  - Best practices for error prevention

### MCP Integration

For MCP deployment and integration:
- **[MCP Integration Guide](../../docs/mcp-integration-guide.md)**: Integrating MCP servers with Thanos
- **[MCP Deployment Guide](../../docs/mcp-deployment-guide.md)**: Deploying and operating MCP servers

---

## Summary

The MCP error handling system provides:

- ✅ **Comprehensive error classification** for all failure modes
- ✅ **Exponential backoff with jitter** for retry logic
- ✅ **Circuit breaker pattern** to prevent cascading failures
- ✅ **Graceful degradation** with fallback strategies
- ✅ **Rich logging context** for debugging
- ✅ **Easy integration** with existing MCP code

This ensures robust and resilient MCP operations even in the face of failures.
