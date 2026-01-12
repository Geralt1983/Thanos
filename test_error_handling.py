#!/usr/bin/env python3
"""
Test MCP error handling and retry logic.

Quick verification that error handling system is working correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add Tools to path
sys.path.insert(0, str(Path(__file__).parent / "Tools"))

from adapters.mcp_errors import (
    MCPCircuitBreakerError,
    MCPConnectionError,
    MCPError,
    MCPTimeoutError,
    MCPToolNotFoundError,
    MCPToolValidationError,
    classify_error,
    is_retryable_error,
    log_error_with_context,
)
from adapters.mcp_retry import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    RetryConfig,
    RetryPolicy,
    get_global_registry,
    with_retry_and_circuit_breaker,
)


def test_error_hierarchy():
    """Test error exception hierarchy."""
    print("Testing error hierarchy...")

    # Test base error
    error = MCPError(
        message="Test error",
        context={"key": "value"},
        server_name="test-server",
        retryable=True,
    )
    assert error.message == "Test error"
    assert error.server_name == "test-server"
    assert error.retryable is True
    assert error.context["key"] == "value"

    # Test connection error (should be retryable by default)
    conn_error = MCPConnectionError(
        message="Connection failed",
        server_name="test-server",
    )
    assert conn_error.retryable is True

    # Test tool errors
    tool_error = MCPToolNotFoundError(
        tool_name="invalid_tool",
        available_tools=["tool1", "tool2"],
        server_name="test-server",
    )
    assert tool_error.context["tool_name"] == "invalid_tool"
    assert tool_error.retryable is False

    print("✅ Error hierarchy tests passed")


def test_error_classification():
    """Test error classification utilities."""
    print("\nTesting error classification...")

    # Test retryable detection
    assert is_retryable_error(MCPConnectionError("test"))
    assert is_retryable_error(MCPTimeoutError("test", 30.0))
    assert not is_retryable_error(MCPToolValidationError("test_tool", "validation failed"))

    # Test generic error classification
    generic_error = TimeoutError("Operation timed out")
    classified = classify_error(generic_error, server_name="test-server")
    assert isinstance(classified, MCPTimeoutError)
    assert classified.server_name == "test-server"

    print("✅ Error classification tests passed")


async def test_retry_policy():
    """Test retry policy with exponential backoff."""
    print("\nTesting retry policy...")

    attempts = 0

    async def failing_func():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise MCPConnectionError("Connection failed")
        return "success"

    policy = RetryPolicy(
        RetryConfig(
            max_attempts=3,
            initial_delay=0.1,  # Short delay for testing
            jitter=False,  # Disable jitter for predictable timing
        )
    )

    result = await policy.execute_async(failing_func)
    assert result == "success"
    assert attempts == 3

    print("✅ Retry policy tests passed")


async def test_circuit_breaker():
    """Test circuit breaker pattern."""
    print("\nTesting circuit breaker...")

    breaker = CircuitBreaker(
        server_name="test-server",
        config=CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=0.5,  # Short timeout for testing
        ),
    )

    # Initially closed
    assert breaker.is_closed()

    # Fail enough times to open circuit
    async def failing_func():
        raise MCPConnectionError("Failed")

    for i in range(3):
        try:
            await breaker.call(failing_func)
        except MCPConnectionError:
            pass

    # Circuit should be open now
    assert breaker.is_open()

    # Calls should be blocked
    try:
        await breaker.call(failing_func)
        assert False, "Should have raised MCPCircuitBreakerError"
    except MCPCircuitBreakerError as e:
        assert e.server_name == "test-server"

    # Wait for timeout
    await asyncio.sleep(0.6)

    # Should transition to half-open
    async def success_func():
        return "success"

    # First success in half-open
    result = await breaker.call(success_func)
    assert result == "success"
    assert breaker.is_half_open()

    # Second success should close circuit
    result = await breaker.call(success_func)
    assert result == "success"
    assert breaker.is_closed()

    print("✅ Circuit breaker tests passed")


async def test_combined():
    """Test retry + circuit breaker together."""
    print("\nTesting combined retry and circuit breaker...")

    attempts = 0

    async def intermittent_func():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise MCPConnectionError("Transient failure")
        return "success"

    result = await with_retry_and_circuit_breaker(
        intermittent_func,
        server_name="test-server-2",
        retry_config=RetryConfig(max_attempts=3, initial_delay=0.1),
        circuit_breaker_config=CircuitBreakerConfig(failure_threshold=5),
    )

    assert result == "success"
    assert attempts == 2

    print("✅ Combined retry and circuit breaker tests passed")


async def test_circuit_breaker_registry():
    """Test circuit breaker registry."""
    print("\nTesting circuit breaker registry...")

    registry = get_global_registry()

    # Get breakers for different servers
    breaker1 = await registry.get_breaker("server1")
    breaker2 = await registry.get_breaker("server2")

    assert breaker1.server_name == "server1"
    assert breaker2.server_name == "server2"

    # Get same breaker again
    breaker1_again = await registry.get_breaker("server1")
    assert breaker1 is breaker1_again

    # Get stats
    stats = registry.get_all_stats()
    assert "server1" in stats
    assert "server2" in stats

    print("✅ Circuit breaker registry tests passed")


def test_delay_calculation():
    """Test exponential backoff delay calculation."""
    print("\nTesting delay calculation...")

    policy = RetryPolicy(
        RetryConfig(
            initial_delay=1.0,
            exponential_base=2.0,
            max_delay=10.0,
            jitter=False,
        )
    )

    # Test exponential growth
    assert policy.calculate_delay(0) == 1.0  # 1.0 * 2^0
    assert policy.calculate_delay(1) == 2.0  # 1.0 * 2^1
    assert policy.calculate_delay(2) == 4.0  # 1.0 * 2^2
    assert policy.calculate_delay(3) == 8.0  # 1.0 * 2^3

    # Test max delay cap
    assert policy.calculate_delay(10) == 10.0  # Capped at max_delay

    print("✅ Delay calculation tests passed")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("MCP Error Handling and Retry Logic Tests")
    print("=" * 60)

    try:
        # Synchronous tests
        test_error_hierarchy()
        test_error_classification()
        test_delay_calculation()

        # Async tests
        await test_retry_policy()
        await test_circuit_breaker()
        await test_combined()
        await test_circuit_breaker_registry()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        return 0

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
