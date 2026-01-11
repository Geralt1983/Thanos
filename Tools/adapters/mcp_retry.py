"""
MCP Retry Logic and Circuit Breaker.

Provides exponential backoff retry logic and circuit breaker pattern
for resilient MCP server communication.
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

from .mcp_errors import (
    MCPCircuitBreakerError,
    MCPError,
    is_retryable_error,
    log_error_with_context,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RetryConfig:
    """
    Configuration for retry behavior.

    Defines retry parameters including backoff strategy, max attempts,
    and timing constraints.
    """

    max_attempts: int = 3
    """Maximum number of retry attempts"""

    initial_delay: float = 1.0
    """Initial delay in seconds before first retry"""

    max_delay: float = 60.0
    """Maximum delay between retries"""

    exponential_base: float = 2.0
    """Base for exponential backoff calculation"""

    jitter: bool = True
    """Add random jitter to prevent thundering herd"""

    jitter_factor: float = 0.1
    """Jitter randomness factor (0.0 to 1.0)"""

    timeout: Optional[float] = None
    """Optional overall timeout for all attempts"""


@dataclass
class CircuitBreakerConfig:
    """
    Configuration for circuit breaker pattern.

    The circuit breaker prevents cascading failures by temporarily
    blocking requests to failing servers.
    """

    failure_threshold: int = 5
    """Number of consecutive failures before opening circuit"""

    success_threshold: int = 2
    """Number of consecutive successes to close circuit"""

    timeout: float = 60.0
    """Seconds to wait before attempting half-open state"""

    half_open_max_calls: int = 1
    """Max concurrent calls in half-open state"""


class CircuitState(Enum):
    """
    Circuit breaker states.

    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests are blocked
    - HALF_OPEN: Testing if service has recovered
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerStats:
    """Statistics tracked by the circuit breaker."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    half_open_calls: int = 0


class RetryPolicy:
    """
    Implements retry logic with exponential backoff and jitter.

    Handles transient failures by retrying operations with
    progressively longer delays between attempts.

    Example:
        >>> policy = RetryPolicy(max_attempts=3, initial_delay=1.0)
        >>> result = await policy.execute_async(async_function, arg1, arg2)
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Initialize retry policy.

        Args:
            config: Retry configuration, uses defaults if None
        """
        self.config = config or RetryConfig()

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay before next retry attempt.

        Uses exponential backoff with optional jitter:
            delay = min(initial_delay * (base ^ attempt), max_delay)

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds before next retry
        """
        # Exponential backoff
        delay = self.config.initial_delay * (self.config.exponential_base**attempt)

        # Apply max delay cap
        delay = min(delay, self.config.max_delay)

        # Add jitter if enabled
        if self.config.jitter:
            jitter_range = delay * self.config.jitter_factor
            jitter = random.uniform(-jitter_range, jitter_range)
            delay = max(0.1, delay + jitter)  # Ensure delay is always positive

        return delay

    async def execute_async(
        self,
        func: Callable[..., Any],
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute an async function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Result from successful function execution

        Raises:
            Exception: Last exception if all retries exhausted
        """
        start_time = time.time()
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                # Check overall timeout
                if self.config.timeout:
                    elapsed = time.time() - start_time
                    if elapsed >= self.config.timeout:
                        logger.warning(
                            f"Overall timeout ({self.config.timeout}s) exceeded after {attempt} attempts"
                        )
                        raise TimeoutError(
                            f"Operation timed out after {elapsed:.2f}s and {attempt} attempts"
                        )

                # Execute the function
                if attempt > 0:
                    logger.debug(
                        f"Retry attempt {attempt + 1}/{self.config.max_attempts} for {func.__name__}"
                    )

                result = await func(*args, **kwargs)

                # Success!
                if attempt > 0:
                    logger.info(f"Operation succeeded on attempt {attempt + 1}")

                return result

            except Exception as e:
                last_exception = e

                # Log the error with context
                log_error_with_context(
                    e,
                    component="retry_policy",
                    additional_context={
                        "attempt": attempt + 1,
                        "max_attempts": self.config.max_attempts,
                        "function": func.__name__,
                    },
                )

                # Check if we should retry
                if attempt + 1 >= self.config.max_attempts:
                    logger.error(
                        f"All {self.config.max_attempts} retry attempts exhausted for {func.__name__}"
                    )
                    break

                if not is_retryable_error(e):
                    logger.info(f"Error is not retryable, aborting retry: {e}")
                    break

                # Calculate delay and wait
                delay = self.calculate_delay(attempt)
                logger.info(
                    f"Retrying {func.__name__} in {delay:.2f}s (attempt {attempt + 1}/{self.config.max_attempts})"
                )
                await asyncio.sleep(delay)

        # All retries exhausted
        raise last_exception

    def execute(
        self,
        func: Callable[..., T],
        *args,
        **kwargs,
    ) -> T:
        """
        Execute a synchronous function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Result from successful function execution

        Raises:
            Exception: Last exception if all retries exhausted
        """
        start_time = time.time()
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                # Check overall timeout
                if self.config.timeout:
                    elapsed = time.time() - start_time
                    if elapsed >= self.config.timeout:
                        logger.warning(
                            f"Overall timeout ({self.config.timeout}s) exceeded after {attempt} attempts"
                        )
                        raise TimeoutError(
                            f"Operation timed out after {elapsed:.2f}s and {attempt} attempts"
                        )

                # Execute the function
                if attempt > 0:
                    logger.debug(
                        f"Retry attempt {attempt + 1}/{self.config.max_attempts} for {func.__name__}"
                    )

                result = func(*args, **kwargs)

                # Success!
                if attempt > 0:
                    logger.info(f"Operation succeeded on attempt {attempt + 1}")

                return result

            except Exception as e:
                last_exception = e

                # Log the error with context
                log_error_with_context(
                    e,
                    component="retry_policy",
                    additional_context={
                        "attempt": attempt + 1,
                        "max_attempts": self.config.max_attempts,
                        "function": func.__name__,
                    },
                )

                # Check if we should retry
                if attempt + 1 >= self.config.max_attempts:
                    logger.error(
                        f"All {self.config.max_attempts} retry attempts exhausted for {func.__name__}"
                    )
                    break

                if not is_retryable_error(e):
                    logger.info(f"Error is not retryable, aborting retry: {e}")
                    break

                # Calculate delay and wait
                delay = self.calculate_delay(attempt)
                logger.info(
                    f"Retrying {func.__name__} in {delay:.2f}s (attempt {attempt + 1}/{self.config.max_attempts})"
                )
                time.sleep(delay)

        # All retries exhausted
        raise last_exception


class CircuitBreaker:
    """
    Implements circuit breaker pattern for fault tolerance.

    Prevents cascading failures by temporarily blocking requests
    to failing services. Transitions between states based on
    success/failure patterns.

    States:
        - CLOSED: Normal operation
        - OPEN: Blocking requests (service is failing)
        - HALF_OPEN: Testing service recovery

    Example:
        >>> breaker = CircuitBreaker(server_name="workos-mcp")
        >>> async with breaker.protect():
        ...     result = await call_mcp_server()
    """

    def __init__(
        self,
        server_name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ):
        """
        Initialize circuit breaker.

        Args:
            server_name: Name of server being protected
            config: Circuit breaker configuration
        """
        self.server_name = server_name
        self.config = config or CircuitBreakerConfig()
        self.stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self.stats.state

    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)."""
        return self.stats.state == CircuitState.OPEN

    def is_closed(self) -> bool:
        """Check if circuit is closed (allowing requests)."""
        return self.stats.state == CircuitState.CLOSED

    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)."""
        return self.stats.state == CircuitState.HALF_OPEN

    async def _check_state(self) -> None:
        """
        Check and update circuit state based on time and stats.

        Transitions from OPEN to HALF_OPEN after timeout period.
        """
        if self.stats.state == CircuitState.OPEN:
            if self.stats.opened_at:
                elapsed = (datetime.now() - self.stats.opened_at).total_seconds()
                if elapsed >= self.config.timeout:
                    logger.info(
                        f"Circuit breaker for '{self.server_name}' transitioning to HALF_OPEN "
                        f"after {elapsed:.1f}s timeout"
                    )
                    self.stats.state = CircuitState.HALF_OPEN
                    self.stats.half_open_calls = 0

    async def _record_success(self) -> None:
        """Record successful operation."""
        async with self._lock:
            self.stats.success_count += 1
            self.stats.failure_count = 0
            self.stats.last_success_time = datetime.now()

            if self.stats.state == CircuitState.HALF_OPEN:
                # Check if we can close the circuit
                if self.stats.success_count >= self.config.success_threshold:
                    logger.info(
                        f"Circuit breaker for '{self.server_name}' closing after "
                        f"{self.stats.success_count} consecutive successes"
                    )
                    self.stats.state = CircuitState.CLOSED
                    self.stats.failure_count = 0
                    self.stats.success_count = 0

    async def _record_failure(self, error: Exception) -> None:
        """Record failed operation."""
        async with self._lock:
            self.stats.failure_count += 1
            self.stats.success_count = 0
            self.stats.last_failure_time = datetime.now()

            if self.stats.state == CircuitState.CLOSED:
                # Check if we should open the circuit
                if self.stats.failure_count >= self.config.failure_threshold:
                    logger.warning(
                        f"Circuit breaker for '{self.server_name}' opening after "
                        f"{self.stats.failure_count} consecutive failures"
                    )
                    self.stats.state = CircuitState.OPEN
                    self.stats.opened_at = datetime.now()

            elif self.stats.state == CircuitState.HALF_OPEN:
                # Failed during test - reopen circuit
                logger.warning(
                    f"Circuit breaker for '{self.server_name}' reopening after failure "
                    "in HALF_OPEN state"
                )
                self.stats.state = CircuitState.OPEN
                self.stats.opened_at = datetime.now()

    async def call(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            MCPCircuitBreakerError: If circuit is open
            Exception: Original exception from function
        """
        # Check if we can make the call
        await self._check_state()

        if self.stats.state == CircuitState.OPEN:
            timeout_remaining = 0.0
            if self.stats.opened_at:
                elapsed = (datetime.now() - self.stats.opened_at).total_seconds()
                timeout_remaining = max(0, self.config.timeout - elapsed)

            raise MCPCircuitBreakerError(
                server_name=self.server_name,
                failure_count=self.stats.failure_count,
                timeout_seconds=timeout_remaining,
            )

        if self.stats.state == CircuitState.HALF_OPEN:
            # Limit concurrent calls in half-open state
            if self.stats.half_open_calls >= self.config.half_open_max_calls:
                raise MCPCircuitBreakerError(
                    server_name=self.server_name,
                    failure_count=self.stats.failure_count,
                    timeout_seconds=0.0,
                    context={"reason": "half_open_concurrent_limit"},
                )

        # Track half-open calls
        if self.stats.state == CircuitState.HALF_OPEN:
            self.stats.half_open_calls += 1

        try:
            # Execute the function
            result = await func(*args, **kwargs)
            await self._record_success()
            return result

        except Exception as e:
            await self._record_failure(e)
            raise

        finally:
            # Decrement half-open call counter
            if self.stats.state == CircuitState.HALF_OPEN:
                self.stats.half_open_calls = max(0, self.stats.half_open_calls - 1)

    def get_stats(self) -> dict[str, Any]:
        """
        Get circuit breaker statistics.

        Returns:
            Dictionary with current stats and state
        """
        return {
            "server_name": self.server_name,
            "state": self.stats.state.value,
            "failure_count": self.stats.failure_count,
            "success_count": self.stats.success_count,
            "last_failure_time": (
                self.stats.last_failure_time.isoformat()
                if self.stats.last_failure_time
                else None
            ),
            "last_success_time": (
                self.stats.last_success_time.isoformat()
                if self.stats.last_success_time
                else None
            ),
            "opened_at": (
                self.stats.opened_at.isoformat() if self.stats.opened_at else None
            ),
        }

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        logger.info(f"Resetting circuit breaker for '{self.server_name}'")
        self.stats = CircuitBreakerStats()


class CircuitBreakerRegistry:
    """
    Registry for managing circuit breakers across multiple servers.

    Maintains a circuit breaker instance per server, allowing
    centralized monitoring and control.

    Example:
        >>> registry = CircuitBreakerRegistry()
        >>> breaker = registry.get_breaker("workos-mcp")
        >>> async with breaker.protect():
        ...     result = await call_server()
    """

    def __init__(self, default_config: Optional[CircuitBreakerConfig] = None):
        """
        Initialize registry.

        Args:
            default_config: Default config for new circuit breakers
        """
        self.default_config = default_config or CircuitBreakerConfig()
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def get_breaker(
        self,
        server_name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> CircuitBreaker:
        """
        Get or create circuit breaker for a server.

        Args:
            server_name: Server identifier
            config: Optional config (uses default if None)

        Returns:
            CircuitBreaker instance for the server
        """
        async with self._lock:
            if server_name not in self._breakers:
                breaker_config = config or self.default_config
                self._breakers[server_name] = CircuitBreaker(
                    server_name=server_name,
                    config=breaker_config,
                )
                logger.debug(f"Created circuit breaker for server: {server_name}")

            return self._breakers[server_name]

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """
        Get statistics for all circuit breakers.

        Returns:
            Dictionary mapping server names to their stats
        """
        return {name: breaker.get_stats() for name, breaker in self._breakers.items()}

    def reset_breaker(self, server_name: str) -> None:
        """
        Reset a specific circuit breaker.

        Args:
            server_name: Server identifier
        """
        if server_name in self._breakers:
            self._breakers[server_name].reset()

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.reset()


# Global circuit breaker registry instance
_global_registry: Optional[CircuitBreakerRegistry] = None


def get_global_registry() -> CircuitBreakerRegistry:
    """
    Get global circuit breaker registry instance.

    Returns:
        Singleton CircuitBreakerRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = CircuitBreakerRegistry()
    return _global_registry


async def with_retry_and_circuit_breaker(
    func: Callable[..., Any],
    server_name: str,
    retry_config: Optional[RetryConfig] = None,
    circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    *args,
    **kwargs,
) -> Any:
    """
    Execute function with both retry logic and circuit breaker protection.

    Combines exponential backoff retry with circuit breaker pattern
    for maximum resilience.

    Args:
        func: Async function to execute
        server_name: Server identifier for circuit breaker
        retry_config: Retry configuration
        circuit_breaker_config: Circuit breaker configuration
        *args: Positional arguments for function
        **kwargs: Keyword arguments for function

    Returns:
        Function result

    Raises:
        MCPCircuitBreakerError: If circuit is open
        Exception: Last exception if all retries exhausted

    Example:
        >>> result = await with_retry_and_circuit_breaker(
        ...     call_mcp_tool,
        ...     "workos-mcp",
        ...     retry_config=RetryConfig(max_attempts=3),
        ...     tool_name="get_tasks",
        ...     arguments={"status": "active"}
        ... )
    """
    # Get circuit breaker for this server
    registry = get_global_registry()
    breaker = await registry.get_breaker(server_name, circuit_breaker_config)

    # Create retry policy
    retry_policy = RetryPolicy(retry_config)

    # Wrap function with circuit breaker
    async def protected_call():
        return await breaker.call(func, *args, **kwargs)

    # Execute with retry logic
    return await retry_policy.execute_async(protected_call)
