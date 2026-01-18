#!/usr/bin/env python3
"""
Circuit Breaker Pattern for Thanos.

Provides resilience for fragile/unofficial APIs with automatic fallback
to cached data when services are unavailable.

Usage:
    from Tools.circuit_breaker import CircuitBreaker, CircuitState

    circuit = CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=3600
    )

    result, is_fallback = await circuit.call(
        func=fetch_from_api,
        fallback=get_cached_data
    )
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import TypeVar, Callable, Optional, Tuple, Any, Dict
from enum import Enum
from dataclasses import dataclass, asdict
from functools import wraps
import logging

# Import journal for event logging
try:
    from Tools.journal import get_journal, log_circuit_event, EventType
except ImportError:
    get_journal = None
    log_circuit_event = None


T = TypeVar('T')
logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, using fallback
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitOpenError(Exception):
    """Raised when circuit is open and no fallback provided."""
    pass


@dataclass
class CircuitMetrics:
    """Metrics for circuit breaker monitoring."""
    state: str
    failure_count: int
    success_count: int
    last_failure_time: Optional[str]
    last_success_time: Optional[str]
    total_calls: int
    fallback_calls: int
    recovery_attempts: int


class CircuitBreaker:
    """
    Circuit breaker for resilient API calls.

    States:
        - CLOSED: Normal operation, requests pass through
        - OPEN: Requests fail fast, fallback used
        - HALF_OPEN: Testing if service recovered

    Transitions:
        - CLOSED -> OPEN: After failure_threshold consecutive failures
        - OPEN -> HALF_OPEN: After recovery_timeout seconds
        - HALF_OPEN -> CLOSED: After half_open_max_calls successes
        - HALF_OPEN -> OPEN: On any failure during testing
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 3,
        recovery_timeout: int = 3600,  # 1 hour
        half_open_max_calls: int = 1,
        success_threshold: int = 2,
        log_events: bool = True
    ):
        """Initialize circuit breaker.

        Args:
            name: Identifier for this circuit
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            half_open_max_calls: Successes needed in half-open to close
            success_threshold: Consecutive successes to reset failure count
            log_events: Whether to log state changes to journal
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.success_threshold = success_threshold
        self.log_events = log_events

        # State
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None
        self.last_error: Optional[Exception] = None

        # Metrics
        self.total_calls = 0
        self.fallback_calls = 0
        self.recovery_attempts = 0

    async def call(
        self,
        func: Callable[[], T],
        fallback: Optional[Callable[[], T]] = None,
        timeout: Optional[float] = None
    ) -> Tuple[T, bool]:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Async or sync function to execute
            fallback: Fallback function if circuit is open
            timeout: Optional timeout in seconds

        Returns:
            Tuple of (result, is_fallback)

        Raises:
            CircuitOpenError: If circuit is open and no fallback provided
        """
        self.total_calls += 1

        # Check if we should attempt recovery
        if self.state == CircuitState.OPEN:
            if self._should_attempt_recovery():
                self._transition_to(CircuitState.HALF_OPEN)
                self.half_open_calls = 0
                self.recovery_attempts += 1
            else:
                # Circuit is open, use fallback
                if fallback:
                    self.fallback_calls += 1
                    result = await self._execute(fallback, timeout)
                    return result, True
                raise CircuitOpenError(
                    f"Circuit '{self.name}' is open (last error: {self.last_error})"
                )

        # Attempt the call
        try:
            result = await self._execute(func, timeout)
            self._on_success()
            return result, False

        except Exception as e:
            self._on_failure(e)

            # Try fallback if available and circuit just opened
            if fallback and self.state == CircuitState.OPEN:
                self.fallback_calls += 1
                try:
                    result = await self._execute(fallback, timeout)
                    return result, True
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {fallback_error}")
                    raise e

            raise

    async def _execute(
        self,
        func: Callable[[], T],
        timeout: Optional[float] = None
    ) -> T:
        """Execute function with optional timeout."""
        if asyncio.iscoroutinefunction(func):
            if timeout:
                return await asyncio.wait_for(func(), timeout=timeout)
            return await func()
        else:
            # Run sync function in thread pool
            loop = asyncio.get_event_loop()
            if timeout:
                return await asyncio.wait_for(
                    loop.run_in_executor(None, func),
                    timeout=timeout
                )
            return await loop.run_in_executor(None, func)

    def _on_success(self):
        """Handle successful call."""
        self.last_success_time = datetime.now()
        self.success_count += 1

        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                self._transition_to(CircuitState.CLOSED)
                self.failure_count = 0
                self.success_count = 0

        elif self.state == CircuitState.CLOSED:
            # Reset failure count after consecutive successes
            if self.success_count >= self.success_threshold:
                self.failure_count = 0

    def _on_failure(self, error: Exception):
        """Handle failed call."""
        self.failure_count += 1
        self.success_count = 0
        self.last_failure_time = datetime.now()
        self.last_error = error

        if self.state == CircuitState.HALF_OPEN:
            # Any failure during half-open reopens circuit
            self._transition_to(CircuitState.OPEN)

        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self._transition_to(CircuitState.OPEN)

    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.last_failure_time is None:
            return True

        elapsed = datetime.now() - self.last_failure_time
        return elapsed > timedelta(seconds=self.recovery_timeout)

    def _transition_to(self, new_state: CircuitState):
        """Transition to new state with logging."""
        old_state = self.state
        self.state = new_state

        logger.info(
            f"Circuit '{self.name}' transition: {old_state.value} -> {new_state.value}"
        )

        # Log to journal if available
        if self.log_events and log_circuit_event:
            try:
                log_circuit_event(
                    source=self.name,
                    state=new_state.value,
                    reason=str(self.last_error) if self.last_error else None
                )
            except Exception as e:
                logger.warning(f"Failed to log circuit event: {e}")

    def get_metrics(self) -> CircuitMetrics:
        """Get current circuit metrics."""
        return CircuitMetrics(
            state=self.state.value,
            failure_count=self.failure_count,
            success_count=self.success_count,
            last_failure_time=self.last_failure_time.isoformat() if self.last_failure_time else None,
            last_success_time=self.last_success_time.isoformat() if self.last_success_time else None,
            total_calls=self.total_calls,
            fallback_calls=self.fallback_calls,
            recovery_attempts=self.recovery_attempts
        )

    def reset(self):
        """Manually reset circuit to closed state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
        self.last_error = None

    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self.state == CircuitState.OPEN

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed."""
        return self.state == CircuitState.CLOSED


class FileCache:
    """Simple file-based cache for fallback data."""

    def __init__(self, cache_dir: Path, default_ttl: int = 86400):
        """Initialize file cache.

        Args:
            cache_dir: Directory for cache files
            default_ttl: Default time-to-live in seconds
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        filepath = self.cache_dir / f"{key}.json"

        if not filepath.exists():
            return None

        try:
            data = json.loads(filepath.read_text())

            # Check expiration
            if 'expires_at' in data:
                expires_at = datetime.fromisoformat(data['expires_at'])
                if datetime.now() > expires_at:
                    filepath.unlink()
                    return None

            return data.get('value')

        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Cache read error for '{key}': {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set cached value.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds

        Returns:
            True if cached successfully
        """
        filepath = self.cache_dir / f"{key}.json"

        if ttl is None:
            ttl = self.default_ttl

        try:
            data = {
                'value': value,
                'cached_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(seconds=ttl)).isoformat()
            }
            filepath.write_text(json.dumps(data, indent=2))
            return True

        except (TypeError, OSError) as e:
            logger.warning(f"Cache write error for '{key}': {e}")
            return False

    def get_timestamp(self, key: str) -> Optional[datetime]:
        """Get when a key was cached."""
        filepath = self.cache_dir / f"{key}.json"

        if not filepath.exists():
            return None

        try:
            data = json.loads(filepath.read_text())
            if 'cached_at' in data:
                return datetime.fromisoformat(data['cached_at'])
        except (json.JSONDecodeError, OSError, ValueError):
            pass

        return None

    def delete(self, key: str) -> bool:
        """Delete cached value."""
        filepath = self.cache_dir / f"{key}.json"

        try:
            if filepath.exists():
                filepath.unlink()
                return True
        except OSError as e:
            logger.warning(f"Cache delete error for '{key}': {e}")

        return False

    def clear(self) -> int:
        """Clear all cached values.

        Returns:
            Number of items cleared
        """
        count = 0
        for filepath in self.cache_dir.glob("*.json"):
            try:
                filepath.unlink()
                count += 1
            except OSError:
                pass
        return count


class ResilientAdapter:
    """Base class for adapters with circuit breaker protection."""

    def __init__(
        self,
        name: str,
        cache_dir: Optional[Path] = None,
        failure_threshold: int = 3,
        recovery_timeout: int = 3600,
        cache_ttl: int = 86400
    ):
        """Initialize resilient adapter.

        Args:
            name: Adapter name (used for circuit and cache)
            cache_dir: Directory for cache files
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            cache_ttl: Default cache TTL in seconds
        """
        self.name = name

        # Initialize circuit breaker
        self.circuit = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )

        # Initialize cache
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent / "State" / "cache" / name

        self.cache = FileCache(cache_dir, default_ttl=cache_ttl)

    async def fetch_with_fallback(
        self,
        cache_key: str,
        fetch_func: Callable[[], T],
        transform: Optional[Callable[[T], T]] = None,
        cache_ttl: Optional[int] = None
    ) -> Tuple[T, Dict[str, Any]]:
        """
        Fetch data with circuit breaker and cache fallback.

        Args:
            cache_key: Key for caching
            fetch_func: Function to fetch live data
            transform: Optional transform for fetched data
            cache_ttl: Optional override for cache TTL

        Returns:
            Tuple of (data, metadata) where metadata includes staleness info
        """
        async def fetch_and_cache():
            data = await self._execute(fetch_func)
            if transform:
                data = transform(data)
            self.cache.set(cache_key, data, cache_ttl)
            return data

        def get_cached():
            return self.cache.get(cache_key)

        try:
            result, is_fallback = await self.circuit.call(
                func=fetch_and_cache,
                fallback=get_cached
            )

            metadata = {
                'is_stale': is_fallback,
                'as_of': (
                    self.cache.get_timestamp(cache_key) if is_fallback
                    else datetime.now()
                ),
                'circuit_state': self.circuit.state.value,
                'source': self.name
            }

            if is_fallback and get_journal:
                try:
                    journal = get_journal()
                    journal.log(
                        event_type=EventType.SYNC_FAILED,
                        source=self.name,
                        title=f"Using cached data - API unavailable",
                        data=metadata,
                        severity="warning"
                    )
                except Exception:
                    pass

            return result, metadata

        except CircuitOpenError:
            # No cached data available
            return None, {
                'is_stale': True,
                'as_of': None,
                'circuit_state': self.circuit.state.value,
                'source': self.name,
                'error': 'No cached data available'
            }

    async def _execute(self, func: Callable[[], T]) -> T:
        """Execute function, handling async/sync."""
        if asyncio.iscoroutinefunction(func):
            return await func()
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, func)

    def get_status(self) -> Dict[str, Any]:
        """Get adapter status including circuit state."""
        metrics = self.circuit.get_metrics()
        return {
            'name': self.name,
            'circuit': asdict(metrics),
            'is_healthy': self.circuit.is_closed,
            'using_cache': self.circuit.is_open
        }


# Circuit breaker registry for global access
_circuits: Dict[str, CircuitBreaker] = {}


def get_circuit(name: str, **kwargs) -> CircuitBreaker:
    """Get or create a named circuit breaker."""
    if name not in _circuits:
        _circuits[name] = CircuitBreaker(name=name, **kwargs)
    return _circuits[name]


def get_all_circuits() -> Dict[str, CircuitBreaker]:
    """Get all registered circuits."""
    return _circuits.copy()


def get_circuit_health() -> Dict[str, str]:
    """Get health status of all circuits."""
    return {name: circuit.state.value for name, circuit in _circuits.items()}


# Decorator for circuit-protected functions
def circuit_protected(
    name: str,
    failure_threshold: int = 3,
    recovery_timeout: int = 3600,
    fallback: Optional[Callable] = None
):
    """
    Decorator to protect a function with circuit breaker.

    Usage:
        @circuit_protected("monarch", fallback=get_cached_accounts)
        async def fetch_accounts():
            return await api.get_accounts()
    """
    def decorator(func: Callable[[], T]) -> Callable[[], T]:
        circuit = get_circuit(
            name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )

        @wraps(func)
        async def wrapper(*args, **kwargs):
            async def call_func():
                return await func(*args, **kwargs)

            result, is_fallback = await circuit.call(
                func=call_func,
                fallback=fallback
            )
            return result

        return wrapper
    return decorator


if __name__ == "__main__":
    import asyncio

    async def test_circuit_breaker():
        """Test circuit breaker functionality."""
        print("Circuit Breaker Test")
        print("=" * 60)

        circuit = CircuitBreaker(
            name="test",
            failure_threshold=2,
            recovery_timeout=5,  # 5 seconds for testing
            log_events=False
        )

        call_count = 0

        async def flaky_api():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise Exception(f"API error {call_count}")
            return f"Success on call {call_count}"

        def fallback():
            return "Cached fallback data"

        # Test failing calls
        for i in range(5):
            try:
                result, is_fallback = await circuit.call(
                    func=flaky_api,
                    fallback=fallback
                )
                print(f"Call {i+1}: {result} (fallback={is_fallback})")
            except Exception as e:
                print(f"Call {i+1}: Error - {e}")

            metrics = circuit.get_metrics()
            print(f"   State: {metrics.state}, Failures: {metrics.failure_count}")

        # Wait for recovery
        print("\nWaiting for recovery timeout...")
        await asyncio.sleep(6)

        # Test recovery
        print("\nTesting recovery:")
        for i in range(3):
            try:
                result, is_fallback = await circuit.call(
                    func=flaky_api,
                    fallback=fallback
                )
                print(f"Call {i+1}: {result} (fallback={is_fallback})")
            except Exception as e:
                print(f"Call {i+1}: Error - {e}")

            metrics = circuit.get_metrics()
            print(f"   State: {metrics.state}")

        print("\nFinal metrics:")
        print(asdict(circuit.get_metrics()))

    asyncio.run(test_circuit_breaker())
