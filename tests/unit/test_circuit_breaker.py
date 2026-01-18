"""
Comprehensive unit tests for the CircuitBreaker pattern implementation.

Tests state transitions, failure thresholds, recovery timeouts,
fallback behavior, concurrent access, and configurable parameters.
"""

import asyncio
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from Tools.circuit_breaker import (
    CircuitBreaker,
    CircuitMetadata,
    CircuitMetrics,
    CircuitOpenError,
    CircuitState,
    FileCache,
    ResilientAdapter,
    circuit_protected,
    get_all_circuits,
    get_circuit,
    get_circuit_health,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def circuit():
    """Create a circuit breaker with test-friendly parameters."""
    return CircuitBreaker(
        name="test_circuit",
        failure_threshold=3,
        recovery_timeout=1,  # 1 second for faster tests
        half_open_max_calls=1,
        success_threshold=2,
        log_events=False,
    )


@pytest.fixture
def fast_circuit():
    """Circuit breaker with minimal thresholds for quick state transitions."""
    return CircuitBreaker(
        name="fast_circuit",
        failure_threshold=2,
        recovery_timeout=0.5,
        half_open_max_calls=1,
        success_threshold=1,
        log_events=False,
    )


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create a temporary cache directory."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def file_cache(temp_cache_dir):
    """Create a FileCache instance for testing."""
    return FileCache(temp_cache_dir, default_ttl=3600)


@pytest.fixture
def resilient_adapter(temp_cache_dir):
    """Create a ResilientAdapter for testing."""
    return ResilientAdapter(
        name="test_adapter",
        cache_dir=temp_cache_dir,
        failure_threshold=3,
        recovery_timeout=1,
        cache_ttl=3600,
    )


# ============================================================================
# Helper Functions
# ============================================================================


async def successful_async_func():
    """Async function that always succeeds."""
    return "success"


async def failing_async_func():
    """Async function that always fails."""
    raise Exception("API error")


def successful_sync_func():
    """Sync function that always succeeds."""
    return "sync_success"


def failing_sync_func():
    """Sync function that always fails."""
    raise Exception("Sync API error")


def fallback_func():
    """Fallback function returning cached data."""
    return "cached_data"


async def async_fallback_func():
    """Async fallback function returning cached data."""
    return "async_cached_data"


# ============================================================================
# Test Class: CircuitState Transitions
# ============================================================================


class TestCircuitStateTransitions:
    """Test state transitions: CLOSED -> OPEN -> HALF_OPEN -> CLOSED."""

    @pytest.mark.asyncio
    async def test_initial_state_is_closed(self, circuit):
        """Circuit should start in CLOSED state."""
        assert circuit.state == CircuitState.CLOSED
        assert circuit.is_closed
        assert not circuit.is_open

    @pytest.mark.asyncio
    async def test_closed_to_open_after_threshold_failures(self, circuit):
        """Circuit should transition from CLOSED to OPEN after threshold failures."""
        # Cause 3 failures (threshold)
        for i in range(circuit.failure_threshold):
            try:
                await circuit.call(func=failing_async_func)
            except Exception:
                pass

        assert circuit.state == CircuitState.OPEN
        assert circuit.is_open
        assert not circuit.is_closed

    @pytest.mark.asyncio
    async def test_open_to_half_open_after_timeout(self, fast_circuit):
        """Circuit should transition to HALF_OPEN after recovery timeout."""
        # Open the circuit
        for _ in range(fast_circuit.failure_threshold):
            try:
                await fast_circuit.call(func=failing_async_func)
            except Exception:
                pass

        assert fast_circuit.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(fast_circuit.recovery_timeout + 0.2)

        # Next call should transition to HALF_OPEN and attempt the call
        try:
            await fast_circuit.call(func=failing_async_func)
        except Exception:
            pass

        # After failed half-open attempt, circuit reopens
        assert fast_circuit.state == CircuitState.OPEN
        assert fast_circuit.recovery_attempts >= 1

    @pytest.mark.asyncio
    async def test_half_open_to_closed_on_success(self, fast_circuit):
        """Circuit should transition from HALF_OPEN to CLOSED on success."""
        # Open the circuit
        for _ in range(fast_circuit.failure_threshold):
            try:
                await fast_circuit.call(func=failing_async_func)
            except Exception:
                pass

        assert fast_circuit.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(fast_circuit.recovery_timeout + 0.2)

        # Successful call should close the circuit
        result, metadata = await fast_circuit.call(func=successful_async_func)

        assert result == "success"
        assert fast_circuit.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_to_open_on_failure(self, fast_circuit):
        """Circuit should reopen from HALF_OPEN on any failure."""
        # Open the circuit
        for _ in range(fast_circuit.failure_threshold):
            try:
                await fast_circuit.call(func=failing_async_func)
            except Exception:
                pass

        # Wait for recovery timeout
        await asyncio.sleep(fast_circuit.recovery_timeout + 0.2)

        # Failed call in half-open should reopen circuit
        try:
            await fast_circuit.call(func=failing_async_func)
        except Exception:
            pass

        assert fast_circuit.state == CircuitState.OPEN


# ============================================================================
# Test Class: Failure Threshold
# ============================================================================


class TestFailureThreshold:
    """Test failure threshold triggering OPEN state."""

    @pytest.mark.asyncio
    async def test_circuit_remains_closed_below_threshold(self, circuit):
        """Circuit should remain CLOSED if failures are below threshold."""
        # Cause failures below threshold
        for _ in range(circuit.failure_threshold - 1):
            try:
                await circuit.call(func=failing_async_func)
            except Exception:
                pass

        assert circuit.state == CircuitState.CLOSED
        assert circuit.failure_count == circuit.failure_threshold - 1

    @pytest.mark.asyncio
    async def test_circuit_opens_at_threshold(self, circuit):
        """Circuit should OPEN exactly at threshold."""
        for _ in range(circuit.failure_threshold):
            try:
                await circuit.call(func=failing_async_func)
            except Exception:
                pass

        assert circuit.state == CircuitState.OPEN
        assert circuit.failure_count == circuit.failure_threshold

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self, circuit):
        """Success should reset failure count after success_threshold."""
        # Cause some failures
        for _ in range(circuit.failure_threshold - 1):
            try:
                await circuit.call(func=failing_async_func)
            except Exception:
                pass

        assert circuit.failure_count == circuit.failure_threshold - 1

        # Successful calls should reset failure count after success_threshold
        for _ in range(circuit.success_threshold):
            await circuit.call(func=successful_async_func)

        assert circuit.failure_count == 0

    @pytest.mark.asyncio
    async def test_configurable_failure_threshold(self):
        """Circuit should respect custom failure threshold."""
        custom_circuit = CircuitBreaker(
            name="custom",
            failure_threshold=5,
            log_events=False,
        )

        for _ in range(4):
            try:
                await custom_circuit.call(func=failing_async_func)
            except Exception:
                pass

        assert custom_circuit.state == CircuitState.CLOSED

        try:
            await custom_circuit.call(func=failing_async_func)
        except Exception:
            pass

        assert custom_circuit.state == CircuitState.OPEN


# ============================================================================
# Test Class: Recovery Timeout
# ============================================================================


class TestRecoveryTimeout:
    """Test timeout expiry transitioning to HALF_OPEN."""

    @pytest.mark.asyncio
    async def test_no_recovery_before_timeout(self, circuit):
        """Circuit should not attempt recovery before timeout."""
        # Open the circuit
        for _ in range(circuit.failure_threshold):
            try:
                await circuit.call(func=failing_async_func)
            except Exception:
                pass

        # Without waiting, circuit should use fallback
        result, metadata = await circuit.call(
            func=failing_async_func, fallback=fallback_func
        )

        assert result == "cached_data"
        assert metadata.is_fallback

    @pytest.mark.asyncio
    async def test_recovery_attempt_after_timeout(self, fast_circuit):
        """Circuit should attempt recovery after timeout expires."""
        # Open the circuit
        for _ in range(fast_circuit.failure_threshold):
            try:
                await fast_circuit.call(func=failing_async_func)
            except Exception:
                pass

        initial_recovery_attempts = fast_circuit.recovery_attempts

        # Wait for timeout
        await asyncio.sleep(fast_circuit.recovery_timeout + 0.2)

        # This call should trigger recovery attempt
        await fast_circuit.call(
            func=successful_async_func, fallback=fallback_func
        )

        assert fast_circuit.recovery_attempts > initial_recovery_attempts

    @pytest.mark.asyncio
    async def test_configurable_recovery_timeout(self):
        """Circuit should respect custom recovery timeout."""
        custom_circuit = CircuitBreaker(
            name="custom_timeout",
            failure_threshold=2,
            recovery_timeout=2,
            log_events=False,
        )

        # Open circuit
        for _ in range(2):
            try:
                await custom_circuit.call(func=failing_async_func)
            except Exception:
                pass

        # Wait less than timeout
        await asyncio.sleep(0.5)

        # Should still use fallback
        result, metadata = await custom_circuit.call(
            func=failing_async_func, fallback=fallback_func
        )
        assert metadata.is_fallback

        # Wait for full timeout
        await asyncio.sleep(2.0)

        # Now should attempt recovery
        result, metadata = await custom_circuit.call(
            func=successful_async_func, fallback=fallback_func
        )
        assert not metadata.is_fallback


# ============================================================================
# Test Class: Fallback Behavior
# ============================================================================


class TestFallbackBehavior:
    """Test cached fallback when circuit is OPEN."""

    @pytest.mark.asyncio
    async def test_fallback_used_when_circuit_open(self, fast_circuit):
        """Fallback should be used when circuit is OPEN."""
        # Open the circuit
        for _ in range(fast_circuit.failure_threshold):
            try:
                await fast_circuit.call(func=failing_async_func)
            except Exception:
                pass

        result, metadata = await fast_circuit.call(
            func=failing_async_func, fallback=fallback_func
        )

        assert result == "cached_data"
        assert metadata.is_fallback
        assert metadata.circuit_state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_fallback_increments_fallback_calls(self, fast_circuit):
        """Using fallback should increment fallback_calls metric."""
        # Open the circuit
        for _ in range(fast_circuit.failure_threshold):
            try:
                await fast_circuit.call(func=failing_async_func)
            except Exception:
                pass

        initial_fallback_calls = fast_circuit.fallback_calls

        await fast_circuit.call(func=failing_async_func, fallback=fallback_func)

        assert fast_circuit.fallback_calls == initial_fallback_calls + 1

    @pytest.mark.asyncio
    async def test_circuit_open_error_without_fallback(self, fast_circuit):
        """CircuitOpenError should be raised when open without fallback."""
        # Open the circuit
        for _ in range(fast_circuit.failure_threshold):
            try:
                await fast_circuit.call(func=failing_async_func)
            except Exception:
                pass

        with pytest.raises(CircuitOpenError) as exc_info:
            await fast_circuit.call(func=failing_async_func)

        assert "fast_circuit" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_async_fallback_function(self, fast_circuit):
        """Async fallback functions should work correctly."""
        # Open the circuit
        for _ in range(fast_circuit.failure_threshold):
            try:
                await fast_circuit.call(func=failing_async_func)
            except Exception:
                pass

        result, metadata = await fast_circuit.call(
            func=failing_async_func, fallback=async_fallback_func
        )

        assert result == "async_cached_data"
        assert metadata.is_fallback

    @pytest.mark.asyncio
    async def test_fallback_after_circuit_opens_from_failure(self, circuit):
        """Fallback should be used immediately after circuit opens."""
        # Cause threshold - 1 failures
        for _ in range(circuit.failure_threshold - 1):
            try:
                await circuit.call(func=failing_async_func)
            except Exception:
                pass

        # This failure should open circuit AND return fallback
        result, metadata = await circuit.call(
            func=failing_async_func, fallback=fallback_func
        )

        assert result == "cached_data"
        assert metadata.is_fallback
        assert circuit.state == CircuitState.OPEN


# ============================================================================
# Test Class: Configurable Thresholds
# ============================================================================


class TestConfigurableThresholds:
    """Test configurable threshold parameters."""

    @pytest.mark.asyncio
    async def test_custom_failure_threshold(self):
        """Custom failure threshold should be respected."""
        circuit = CircuitBreaker(
            name="custom_failure",
            failure_threshold=5,
            log_events=False,
        )

        for _ in range(4):
            try:
                await circuit.call(func=failing_async_func)
            except Exception:
                pass

        assert circuit.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_custom_half_open_max_calls(self):
        """Custom half_open_max_calls should be respected."""
        circuit = CircuitBreaker(
            name="custom_half_open",
            failure_threshold=2,
            recovery_timeout=0.5,
            half_open_max_calls=3,
            log_events=False,
        )

        # Open circuit
        for _ in range(2):
            try:
                await circuit.call(func=failing_async_func)
            except Exception:
                pass

        await asyncio.sleep(0.6)

        # Need 3 successes to close
        await circuit.call(func=successful_async_func)
        assert circuit.state == CircuitState.HALF_OPEN or circuit.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_custom_success_threshold(self):
        """Custom success_threshold should reset failure count."""
        circuit = CircuitBreaker(
            name="custom_success",
            failure_threshold=5,
            success_threshold=3,
            log_events=False,
        )

        # Cause some failures
        for _ in range(3):
            try:
                await circuit.call(func=failing_async_func)
            except Exception:
                pass

        assert circuit.failure_count == 3

        # 3 successes should reset
        for _ in range(3):
            await circuit.call(func=successful_async_func)

        assert circuit.failure_count == 0


# ============================================================================
# Test Class: Sync Function Support
# ============================================================================


class TestSyncFunctionSupport:
    """Test that synchronous functions work correctly."""

    @pytest.mark.asyncio
    async def test_sync_function_success(self, circuit):
        """Sync functions should work through circuit breaker."""
        result, metadata = await circuit.call(func=successful_sync_func)

        assert result == "sync_success"
        assert not metadata.is_fallback

    @pytest.mark.asyncio
    async def test_sync_function_failure(self, circuit):
        """Sync function failures should be tracked."""
        try:
            await circuit.call(func=failing_sync_func)
        except Exception:
            pass

        assert circuit.failure_count == 1

    @pytest.mark.asyncio
    async def test_sync_fallback_function(self, fast_circuit):
        """Sync fallback should work when circuit is open."""
        for _ in range(fast_circuit.failure_threshold):
            try:
                await fast_circuit.call(func=failing_async_func)
            except Exception:
                pass

        result, metadata = await fast_circuit.call(
            func=failing_async_func, fallback=fallback_func
        )

        assert result == "cached_data"
        assert metadata.is_fallback


# ============================================================================
# Test Class: Metrics and Monitoring
# ============================================================================


class TestMetricsAndMonitoring:
    """Test circuit breaker metrics collection."""

    @pytest.mark.asyncio
    async def test_total_calls_metric(self, circuit):
        """Total calls should be tracked."""
        for _ in range(5):
            try:
                await circuit.call(func=successful_async_func)
            except Exception:
                pass

        metrics = circuit.get_metrics()
        assert metrics.total_calls == 5

    @pytest.mark.asyncio
    async def test_failure_count_metric(self, circuit):
        """Failure count should be tracked."""
        for _ in range(3):
            try:
                await circuit.call(func=failing_async_func)
            except Exception:
                pass

        metrics = circuit.get_metrics()
        assert metrics.failure_count == 3

    @pytest.mark.asyncio
    async def test_success_count_metric(self, circuit):
        """Success count should be tracked."""
        for _ in range(4):
            await circuit.call(func=successful_async_func)

        metrics = circuit.get_metrics()
        assert metrics.success_count == 4

    @pytest.mark.asyncio
    async def test_last_failure_time(self, circuit):
        """Last failure time should be recorded."""
        try:
            await circuit.call(func=failing_async_func)
        except Exception:
            pass

        metrics = circuit.get_metrics()
        assert metrics.last_failure_time is not None

    @pytest.mark.asyncio
    async def test_last_success_time(self, circuit):
        """Last success time should be recorded."""
        await circuit.call(func=successful_async_func)

        metrics = circuit.get_metrics()
        assert metrics.last_success_time is not None

    @pytest.mark.asyncio
    async def test_recovery_attempts_metric(self, fast_circuit):
        """Recovery attempts should be tracked."""
        # Open circuit
        for _ in range(fast_circuit.failure_threshold):
            try:
                await fast_circuit.call(func=failing_async_func)
            except Exception:
                pass

        await asyncio.sleep(fast_circuit.recovery_timeout + 0.2)

        # Trigger recovery attempt
        await fast_circuit.call(
            func=successful_async_func, fallback=fallback_func
        )

        metrics = fast_circuit.get_metrics()
        assert metrics.recovery_attempts >= 1


# ============================================================================
# Test Class: Reset Functionality
# ============================================================================


class TestResetFunctionality:
    """Test manual circuit reset."""

    @pytest.mark.asyncio
    async def test_reset_returns_to_closed(self, circuit):
        """Reset should return circuit to CLOSED state."""
        # Open circuit
        for _ in range(circuit.failure_threshold):
            try:
                await circuit.call(func=failing_async_func)
            except Exception:
                pass

        assert circuit.state == CircuitState.OPEN

        circuit.reset()

        assert circuit.state == CircuitState.CLOSED
        assert circuit.failure_count == 0

    @pytest.mark.asyncio
    async def test_reset_clears_counts(self, circuit):
        """Reset should clear failure and success counts."""
        for _ in range(2):
            try:
                await circuit.call(func=failing_async_func)
            except Exception:
                pass

        for _ in range(3):
            await circuit.call(func=successful_async_func)

        circuit.reset()

        assert circuit.failure_count == 0
        assert circuit.success_count == 0
        assert circuit.half_open_calls == 0

    @pytest.mark.asyncio
    async def test_reset_clears_last_error(self, circuit):
        """Reset should clear last error."""
        try:
            await circuit.call(func=failing_async_func)
        except Exception:
            pass

        assert circuit.last_error is not None

        circuit.reset()

        assert circuit.last_error is None


# ============================================================================
# Test Class: Timeout Functionality
# ============================================================================


class TestTimeoutFunctionality:
    """Test call timeout functionality."""

    @pytest.mark.asyncio
    async def test_timeout_triggers_failure(self, circuit):
        """Timeout should be treated as failure."""
        async def slow_func():
            await asyncio.sleep(2)
            return "completed"

        try:
            await circuit.call(func=slow_func, timeout=0.1)
        except asyncio.TimeoutError:
            pass

        assert circuit.failure_count == 1

    @pytest.mark.asyncio
    async def test_successful_call_within_timeout(self, circuit):
        """Calls completing within timeout should succeed."""
        async def quick_func():
            await asyncio.sleep(0.05)
            return "quick_result"

        result, metadata = await circuit.call(func=quick_func, timeout=1.0)

        assert result == "quick_result"
        assert not metadata.is_fallback


# ============================================================================
# Test Class: CircuitMetadata
# ============================================================================


class TestCircuitMetadata:
    """Test CircuitMetadata information."""

    @pytest.mark.asyncio
    async def test_metadata_circuit_state(self, circuit):
        """Metadata should include circuit state."""
        result, metadata = await circuit.call(func=successful_async_func)

        assert metadata.circuit_state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_metadata_is_fallback(self, fast_circuit):
        """Metadata should indicate if result is from fallback."""
        result, metadata = await fast_circuit.call(func=successful_async_func)
        assert not metadata.is_fallback

        for _ in range(fast_circuit.failure_threshold):
            try:
                await fast_circuit.call(func=failing_async_func)
            except Exception:
                pass

        result, metadata = await fast_circuit.call(
            func=failing_async_func, fallback=fallback_func
        )
        assert metadata.is_fallback

    @pytest.mark.asyncio
    async def test_metadata_failure_count(self, circuit):
        """Metadata should include current failure count after circuit opens."""
        # Cause enough failures to open circuit
        for _ in range(circuit.failure_threshold):
            try:
                await circuit.call(func=failing_async_func)
            except Exception:
                pass

        # Now get metadata from fallback call
        result, metadata = await circuit.call(
            func=failing_async_func, fallback=fallback_func
        )

        assert metadata.failure_count >= 1

    @pytest.mark.asyncio
    async def test_metadata_last_error(self, circuit):
        """Metadata should include last error message after circuit opens."""
        # Cause enough failures to open circuit
        for _ in range(circuit.failure_threshold):
            try:
                await circuit.call(func=failing_async_func)
            except Exception:
                pass

        # Now get metadata from fallback call
        result, metadata = await circuit.call(
            func=failing_async_func, fallback=fallback_func
        )

        assert "API error" in metadata.last_error


# ============================================================================
# Test Class: FileCache
# ============================================================================


class TestFileCache:
    """Test FileCache functionality."""

    def test_set_and_get(self, file_cache):
        """Cache should store and retrieve values."""
        file_cache.set("key1", {"data": "value"})
        result = file_cache.get("key1")

        assert result == {"data": "value"}

    def test_cache_miss(self, file_cache):
        """Cache should return None for missing keys."""
        result = file_cache.get("nonexistent")
        assert result is None

    def test_cache_expiration(self, temp_cache_dir):
        """Expired entries should return None."""
        cache = FileCache(temp_cache_dir, default_ttl=1)
        cache.set("expire_key", "value", ttl=1)

        time.sleep(1.1)

        result = cache.get("expire_key")
        assert result is None

    def test_get_timestamp(self, file_cache):
        """Should return cache timestamp."""
        file_cache.set("timed_key", "value")
        timestamp = file_cache.get_timestamp("timed_key")

        assert timestamp is not None
        assert isinstance(timestamp, datetime)

    def test_delete(self, file_cache):
        """Should delete cached entries."""
        file_cache.set("delete_key", "value")
        assert file_cache.get("delete_key") == "value"

        result = file_cache.delete("delete_key")
        assert result is True
        assert file_cache.get("delete_key") is None

    def test_clear(self, file_cache):
        """Should clear all cached entries."""
        file_cache.set("key1", "value1")
        file_cache.set("key2", "value2")
        file_cache.set("key3", "value3")

        count = file_cache.clear()

        assert count == 3
        assert file_cache.get("key1") is None
        assert file_cache.get("key2") is None
        assert file_cache.get("key3") is None

    def test_custom_ttl(self, file_cache):
        """Custom TTL should override default."""
        file_cache.set("long_key", "value", ttl=7200)
        file_cache.set("short_key", "value", ttl=1)

        time.sleep(1.1)

        assert file_cache.get("long_key") == "value"
        assert file_cache.get("short_key") is None


# ============================================================================
# Test Class: ResilientAdapter
# ============================================================================


class TestResilientAdapter:
    """Test ResilientAdapter functionality."""

    @pytest.mark.asyncio
    async def test_fetch_and_cache(self, resilient_adapter):
        """Should fetch and cache data."""
        async def fetch_data():
            return {"data": "fresh"}

        result, metadata = await resilient_adapter.fetch_with_fallback(
            cache_key="test_key", fetch_func=fetch_data
        )

        assert result == {"data": "fresh"}
        assert not metadata["is_stale"]

    @pytest.mark.asyncio
    async def test_fallback_to_cache(self, resilient_adapter):
        """Should fall back to cache when API fails."""
        # First, cache some data
        async def successful_fetch():
            return {"data": "cached"}

        await resilient_adapter.fetch_with_fallback(
            cache_key="cache_key", fetch_func=successful_fetch
        )

        # Now fail the API
        async def failing_fetch():
            raise Exception("API down")

        # Trigger circuit open
        for _ in range(3):
            try:
                await resilient_adapter.fetch_with_fallback(
                    cache_key="cache_key", fetch_func=failing_fetch
                )
            except Exception:
                pass

        # Should get cached data
        result, metadata = await resilient_adapter.fetch_with_fallback(
            cache_key="cache_key", fetch_func=failing_fetch
        )

        assert result == {"data": "cached"}
        assert metadata["is_stale"]

    def test_get_status(self, resilient_adapter):
        """Should return adapter status."""
        status = resilient_adapter.get_status()

        assert status["name"] == "test_adapter"
        assert "circuit" in status
        assert "is_healthy" in status

    @pytest.mark.asyncio
    async def test_transform_function(self, resilient_adapter):
        """Should apply transform to fetched data."""
        async def fetch_data():
            return {"raw": "data"}

        def transform(data):
            data["transformed"] = True
            return data

        result, metadata = await resilient_adapter.fetch_with_fallback(
            cache_key="transform_key",
            fetch_func=fetch_data,
            transform=transform,
        )

        assert result["transformed"] is True


# ============================================================================
# Test Class: Circuit Registry
# ============================================================================


class TestCircuitRegistry:
    """Test circuit breaker registry functions."""

    def test_get_circuit_creates_new(self):
        """get_circuit should create new circuit if not exists."""
        circuit = get_circuit("registry_test_1", log_events=False)
        assert circuit is not None
        assert circuit.name == "registry_test_1"

    def test_get_circuit_returns_existing(self):
        """get_circuit should return existing circuit."""
        circuit1 = get_circuit("registry_test_2", log_events=False)
        circuit2 = get_circuit("registry_test_2")

        assert circuit1 is circuit2

    def test_get_all_circuits(self):
        """get_all_circuits should return all registered circuits."""
        get_circuit("registry_test_3", log_events=False)
        get_circuit("registry_test_4", log_events=False)

        all_circuits = get_all_circuits()

        assert "registry_test_3" in all_circuits
        assert "registry_test_4" in all_circuits

    def test_get_circuit_health(self):
        """get_circuit_health should return health of all circuits."""
        get_circuit("health_test", log_events=False)

        health = get_circuit_health()

        assert "health_test" in health
        assert health["health_test"] == "closed"


# ============================================================================
# Test Class: Decorator
# ============================================================================


class TestCircuitProtectedDecorator:
    """Test @circuit_protected decorator."""

    @pytest.mark.asyncio
    async def test_decorator_basic(self):
        """Decorator should protect function."""
        call_count = 0

        @circuit_protected("decorator_test_1", failure_threshold=2)
        async def protected_func():
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}"

        result = await protected_func()
        assert result == "result_1"

    @pytest.mark.asyncio
    async def test_decorator_with_fallback(self):
        """Decorator should use fallback when circuit opens."""

        def get_fallback():
            return "fallback_data"

        @circuit_protected(
            "decorator_test_2",
            failure_threshold=2,
            fallback=get_fallback,
        )
        async def failing_func():
            raise Exception("Always fails")

        # First calls fail while circuit is closed (exceptions propagate before circuit opens)
        # Once circuit opens, fallback should be used
        result = None
        for _ in range(5):
            try:
                result = await failing_func()
            except Exception:
                # Exceptions are raised while circuit is opening
                pass

        # After circuit opens, should get fallback
        assert result == "fallback_data"

    @pytest.mark.asyncio
    async def test_decorator_with_metadata(self):
        """Decorator should return metadata when requested."""
        @circuit_protected(
            "decorator_test_3",
            failure_threshold=3,
            return_metadata=True,
        )
        async def metadata_func():
            return "data"

        result, metadata = await metadata_func()

        assert result == "data"
        assert isinstance(metadata, CircuitMetadata)
        assert metadata.circuit_state == CircuitState.CLOSED


# ============================================================================
# Test Class: Concurrent Access
# ============================================================================


class TestConcurrentAccess:
    """Test concurrent access patterns."""

    @pytest.mark.asyncio
    async def test_concurrent_calls(self, circuit):
        """Multiple concurrent calls should be handled correctly."""
        call_count = 0

        async def tracked_func():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)
            return f"result_{call_count}"

        # Execute concurrent calls
        tasks = [circuit.call(func=tracked_func) for _ in range(5)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert circuit.total_calls == 5

    @pytest.mark.asyncio
    async def test_concurrent_failures(self, circuit):
        """Concurrent failures should correctly update state."""
        async def concurrent_fail():
            await asyncio.sleep(0.05)
            raise Exception("Concurrent failure")

        # Execute concurrent failing calls with return_exceptions to handle all
        tasks = [
            circuit.call(func=concurrent_fail, fallback=fallback_func)
            for _ in range(10)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Circuit should be open due to failures
        assert circuit.state == CircuitState.OPEN
        # All tasks should complete (either with result or exception)
        assert len(results) == 10

    @pytest.mark.asyncio
    async def test_mixed_concurrent_calls(self, circuit):
        """Mixed success/failure concurrent calls should be handled."""
        counter = 0

        async def mixed_func():
            nonlocal counter
            counter += 1
            await asyncio.sleep(0.05)
            if counter % 2 == 0:
                raise Exception(f"Failure {counter}")
            return f"success_{counter}"

        tasks = []
        for _ in range(8):
            tasks.append(circuit.call(func=mixed_func, fallback=fallback_func))

        # Use return_exceptions to handle mixed results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All calls should complete (with success, fallback, or exception)
        assert len(results) == 8
        assert circuit.total_calls == 8


# ============================================================================
# Test Class: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_immediate_reset_after_open(self, fast_circuit):
        """Manual reset after open should allow new calls."""
        for _ in range(fast_circuit.failure_threshold):
            try:
                await fast_circuit.call(func=failing_async_func)
            except Exception:
                pass

        assert fast_circuit.state == CircuitState.OPEN

        fast_circuit.reset()

        result, metadata = await fast_circuit.call(func=successful_async_func)
        assert result == "success"
        assert not metadata.is_fallback

    @pytest.mark.asyncio
    async def test_zero_recovery_timeout(self):
        """Zero recovery timeout should immediately allow recovery."""
        circuit = CircuitBreaker(
            name="zero_timeout",
            failure_threshold=2,
            recovery_timeout=0,
            log_events=False,
        )

        for _ in range(2):
            try:
                await circuit.call(func=failing_async_func)
            except Exception:
                pass

        # Should immediately attempt recovery
        result, metadata = await circuit.call(func=successful_async_func)

        assert result == "success"

    @pytest.mark.asyncio
    async def test_fallback_failure_when_circuit_opens(self):
        """When circuit opens and fallback also fails, original error should propagate."""
        circuit = CircuitBreaker(
            name="fallback_fail_test",
            failure_threshold=2,
            recovery_timeout=1,
            log_events=False,
        )

        # Cause failures up to threshold - 1
        for _ in range(circuit.failure_threshold - 1):
            try:
                await circuit.call(func=failing_async_func)
            except Exception:
                pass

        assert circuit.state == CircuitState.CLOSED

        def failing_fallback():
            raise Exception("Fallback also failed")

        # This failure opens circuit AND tries fallback, which also fails
        # Original error should propagate
        with pytest.raises(Exception) as exc_info:
            await circuit.call(
                func=failing_async_func, fallback=failing_fallback
            )

        assert "API error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fallback_failure_when_circuit_already_open(self, fast_circuit):
        """When circuit is already open and fallback fails, fallback error propagates."""
        # First open the circuit
        for _ in range(fast_circuit.failure_threshold):
            try:
                await fast_circuit.call(func=failing_async_func)
            except Exception:
                pass

        assert fast_circuit.state == CircuitState.OPEN

        def failing_fallback():
            raise Exception("Fallback also failed")

        # When circuit is already open, fallback is called directly
        # If it fails, fallback error propagates
        with pytest.raises(Exception) as exc_info:
            await fast_circuit.call(
                func=failing_async_func, fallback=failing_fallback
            )

        assert "Fallback also failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_none_result_handling(self, circuit):
        """None return values should be handled correctly."""
        async def returns_none():
            return None

        result, metadata = await circuit.call(func=returns_none)

        assert result is None
        assert not metadata.is_fallback

    @pytest.mark.asyncio
    async def test_empty_string_result(self, circuit):
        """Empty string return values should be handled correctly."""
        async def returns_empty():
            return ""

        result, metadata = await circuit.call(func=returns_empty)

        assert result == ""
        assert not metadata.is_fallback


# ============================================================================
# Run Tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
