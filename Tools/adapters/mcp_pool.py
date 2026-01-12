"""
MCP Connection Pooling and Session Management.

Provides connection pooling for long-lived MCP sessions with automatic
reconnection, health checks, and proper resource cleanup.

This module implements a connection pool that maintains multiple MCP sessions,
reducing the overhead of repeated session creation and improving performance
for high-frequency tool calls.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from mcp import ClientSession

from .mcp_config import MCPServerConfig
from .mcp_errors import MCPConnectionError, MCPResourceError, log_error_with_context
from .mcp_retry import CircuitBreaker, CircuitBreakerConfig, RetryConfig, RetryPolicy

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection state in the pool."""

    IDLE = "idle"
    ACTIVE = "active"
    UNHEALTHY = "unhealthy"
    CLOSED = "closed"


@dataclass
class PoolConfig:
    """
    Configuration for connection pool.

    Defines pool size limits, timeouts, and health check settings.
    """

    min_connections: int = 1
    """Minimum number of connections to maintain in pool"""

    max_connections: int = 10
    """Maximum number of connections allowed in pool"""

    connection_timeout: float = 30.0
    """Timeout for establishing new connections (seconds)"""

    idle_timeout: float = 300.0
    """Timeout before closing idle connections (seconds)"""

    max_lifetime: float = 3600.0
    """Maximum connection lifetime before forced refresh (seconds)"""

    health_check_interval: float = 60.0
    """Interval between health checks on idle connections (seconds)"""

    acquire_timeout: float = 30.0
    """Timeout when acquiring connection from pool (seconds)"""

    enable_health_checks: bool = True
    """Whether to perform periodic health checks"""

    enable_auto_reconnect: bool = True
    """Whether to automatically reconnect on connection loss"""

    max_reconnect_attempts: int = 3
    """Maximum number of reconnection attempts"""


@dataclass
class PooledConnection:
    """
    A pooled MCP connection with metadata.

    Tracks connection state, usage statistics, and health information.
    """

    connection_id: str
    """Unique identifier for this connection"""

    session: ClientSession
    """The MCP client session"""

    state: ConnectionState = ConnectionState.IDLE
    """Current connection state"""

    created_at: datetime = field(default_factory=datetime.now)
    """When this connection was created"""

    last_used: datetime = field(default_factory=datetime.now)
    """When this connection was last used"""

    last_health_check: Optional[datetime] = None
    """When last health check was performed"""

    use_count: int = 0
    """Number of times this connection has been used"""

    error_count: int = 0
    """Number of errors encountered by this connection"""

    cleanup_callback: Optional[Any] = None
    """Callback to clean up transport resources"""

    def is_healthy(self, config: PoolConfig) -> bool:
        """
        Check if connection is healthy based on configuration.

        Args:
            config: Pool configuration with health check settings

        Returns:
            True if connection is healthy and usable
        """
        # Check state
        if self.state in (ConnectionState.UNHEALTHY, ConnectionState.CLOSED):
            return False

        # Check lifetime
        age = (datetime.now() - self.created_at).total_seconds()
        if age > config.max_lifetime:
            logger.debug(
                f"Connection {self.connection_id} exceeded max lifetime "
                f"({age:.1f}s > {config.max_lifetime}s)"
            )
            return False

        # Check idle timeout
        idle_time = (datetime.now() - self.last_used).total_seconds()
        if idle_time > config.idle_timeout:
            logger.debug(
                f"Connection {self.connection_id} exceeded idle timeout "
                f"({idle_time:.1f}s > {config.idle_timeout}s)"
            )
            return False

        return True

    def mark_used(self):
        """Mark connection as used, updating statistics."""
        self.last_used = datetime.now()
        self.use_count += 1

    def mark_error(self):
        """Mark connection as having encountered an error."""
        self.error_count += 1
        if self.error_count >= 3:
            self.state = ConnectionState.UNHEALTHY
            logger.warning(
                f"Connection {self.connection_id} marked unhealthy after "
                f"{self.error_count} errors"
            )


class MCPConnectionPool:
    """
    Connection pool for MCP sessions.

    Manages a pool of long-lived MCP sessions with automatic reconnection,
    health checks, and resource cleanup.

    Features:
    - Configurable min/max pool size
    - Automatic reconnection on connection loss
    - Periodic health checks for idle connections
    - Connection lifecycle management
    - Statistics tracking and monitoring
    - Graceful shutdown with cleanup

    Example:
        >>> config = MCPServerConfig(name="workos-mcp", ...)
        >>> pool_config = PoolConfig(min_connections=2, max_connections=10)
        >>> pool = MCPConnectionPool(config, pool_config)
        >>> await pool.initialize()
        >>>
        >>> async with pool.acquire() as session:
        ...     result = await session.call_tool("get_tasks", {})
        >>>
        >>> await pool.close()
    """

    def __init__(
        self,
        server_config: MCPServerConfig,
        pool_config: Optional[PoolConfig] = None,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    ):
        """
        Initialize connection pool.

        Args:
            server_config: MCP server configuration
            pool_config: Pool configuration (uses defaults if None)
            retry_config: Retry configuration for reconnection
            circuit_breaker_config: Circuit breaker configuration
        """
        self.server_config = server_config
        self.pool_config = pool_config or PoolConfig()
        self.retry_config = retry_config or RetryConfig(max_attempts=3, initial_delay=1.0)
        self.circuit_breaker = CircuitBreaker(
            server_name=server_config.name,
            config=circuit_breaker_config or CircuitBreakerConfig(),
        )

        # Pool state
        self._connections: dict[str, PooledConnection] = {}
        self._available: asyncio.Queue = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._next_connection_id = 0
        self._initialized = False
        self._closed = False

        # Background tasks
        self._health_check_task: Optional[asyncio.Task] = None

        # Statistics
        self._stats = {
            "total_created": 0,
            "total_closed": 0,
            "total_acquisitions": 0,
            "total_releases": 0,
            "total_reconnections": 0,
            "total_health_checks": 0,
            "total_errors": 0,
        }

    async def initialize(self):
        """
        Initialize the connection pool.

        Creates minimum number of connections and starts background tasks.

        Raises:
            MCPConnectionError: If unable to create minimum connections
        """
        if self._initialized:
            logger.warning(f"Connection pool for '{self.server_config.name}' already initialized")
            return

        logger.info(
            f"Initializing connection pool for '{self.server_config.name}' "
            f"(min={self.pool_config.min_connections}, max={self.pool_config.max_connections})"
        )

        # Create minimum connections
        for _ in range(self.pool_config.min_connections):
            try:
                await self._create_connection()
            except Exception as e:
                logger.error(
                    f"Failed to create initial connection for pool '{self.server_config.name}': {e}"
                )
                # Clean up any connections we did create
                await self.close()
                raise MCPConnectionError(
                    f"Failed to initialize connection pool: {e}",
                    server_name=self.server_config.name,
                )

        # Start background health checks if enabled
        if self.pool_config.enable_health_checks:
            self._health_check_task = asyncio.create_task(self._health_check_loop())

        self._initialized = True
        logger.info(
            f"Connection pool initialized for '{self.server_config.name}' "
            f"with {len(self._connections)} connections"
        )

    async def _create_connection(self) -> PooledConnection:
        """
        Create a new connection and add it to the pool.

        Returns:
            PooledConnection instance

        Raises:
            MCPConnectionError: If connection creation fails
        """
        connection_id = f"{self.server_config.name}-{self._next_connection_id}"
        self._next_connection_id += 1

        logger.debug(f"Creating new connection: {connection_id}")

        try:
            # Import here to avoid circular dependency
            from .mcp_bridge import MCPBridge

            # Create a bridge instance
            bridge = MCPBridge(self.server_config)

            # Get a session (this connects to the server)
            # We need to keep the context manager alive for the connection lifetime
            # So we manually enter the context and store the exit callback
            session_context = bridge._get_session()
            session = await session_context.__aenter__()

            # Create pooled connection
            pooled_conn = PooledConnection(
                connection_id=connection_id,
                session=session,
                state=ConnectionState.IDLE,
                cleanup_callback=session_context.__aexit__,
            )

            # Add to pool
            async with self._lock:
                self._connections[connection_id] = pooled_conn
                await self._available.put(connection_id)
                self._stats["total_created"] += 1

            logger.info(f"Created connection: {connection_id}")
            return pooled_conn

        except Exception as e:
            log_error_with_context(
                e,
                component="mcp_pool",
                additional_context={
                    "connection_id": connection_id,
                    "server": self.server_config.name,
                },
            )
            raise MCPConnectionError(
                f"Failed to create connection: {e}",
                server_name=self.server_config.name,
            )

    async def _close_connection(self, connection_id: str):
        """
        Close a connection and remove it from the pool.

        Args:
            connection_id: ID of connection to close
        """
        async with self._lock:
            pooled_conn = self._connections.get(connection_id)
            if not pooled_conn:
                return

            logger.debug(f"Closing connection: {connection_id}")

            # Mark as closed
            pooled_conn.state = ConnectionState.CLOSED

            # Call cleanup callback to exit the context manager
            if pooled_conn.cleanup_callback:
                try:
                    await pooled_conn.cleanup_callback(None, None, None)
                except Exception as e:
                    logger.warning(f"Error during connection cleanup: {e}")

            # Remove from pool
            del self._connections[connection_id]
            self._stats["total_closed"] += 1

            logger.debug(f"Closed connection: {connection_id}")

    @asynccontextmanager
    async def acquire(self, timeout: Optional[float] = None):
        """
        Acquire a connection from the pool.

        This is a context manager that automatically returns the connection
        to the pool when done.

        Args:
            timeout: Timeout for acquiring connection (uses pool config if None)

        Yields:
            ClientSession instance

        Raises:
            MCPResourceError: If unable to acquire connection within timeout
            RuntimeError: If pool is not initialized or closed

        Example:
            >>> async with pool.acquire() as session:
            ...     result = await session.call_tool("get_tasks", {})
        """
        if not self._initialized:
            raise RuntimeError("Connection pool not initialized. Call initialize() first.")

        if self._closed:
            raise RuntimeError("Connection pool is closed")

        timeout = timeout or self.pool_config.acquire_timeout
        connection_id = None
        pooled_conn = None

        try:
            # Try to get an available connection
            try:
                connection_id = await asyncio.wait_for(
                    self._available.get(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                # No available connections within timeout
                # Try to create a new one if under max limit
                async with self._lock:
                    if len(self._connections) < self.pool_config.max_connections:
                        pooled_conn = await self._create_connection()
                        connection_id = pooled_conn.connection_id
                    else:
                        raise MCPResourceError(
                            f"Connection pool exhausted for '{self.server_config.name}' "
                            f"(max={self.pool_config.max_connections})",
                            resource_type="connection_pool",
                            server_name=self.server_config.name,
                        )

            # Get the connection
            if pooled_conn is None:
                async with self._lock:
                    pooled_conn = self._connections.get(connection_id)
                    if not pooled_conn:
                        raise MCPConnectionError(
                            f"Connection {connection_id} not found in pool",
                            server_name=self.server_config.name,
                        )

            # Check if connection is healthy
            if not pooled_conn.is_healthy(self.pool_config):
                logger.info(f"Connection {connection_id} is unhealthy, reconnecting...")
                await self._reconnect_connection(connection_id)
                async with self._lock:
                    pooled_conn = self._connections.get(connection_id)

            # Mark as active
            pooled_conn.state = ConnectionState.ACTIVE
            pooled_conn.mark_used()
            self._stats["total_acquisitions"] += 1

            logger.debug(
                f"Acquired connection: {connection_id} "
                f"(use_count={pooled_conn.use_count})"
            )

            # Yield the session
            yield pooled_conn.session

        except Exception as e:
            log_error_with_context(
                e,
                component="mcp_pool",
                additional_context={
                    "connection_id": connection_id,
                    "server": self.server_config.name,
                    "operation": "acquire",
                },
            )
            if pooled_conn:
                pooled_conn.mark_error()
            self._stats["total_errors"] += 1
            raise

        finally:
            # Return connection to pool
            if pooled_conn and connection_id:
                pooled_conn.state = ConnectionState.IDLE
                await self._available.put(connection_id)
                self._stats["total_releases"] += 1
                logger.debug(f"Released connection: {connection_id}")

    async def _reconnect_connection(self, connection_id: str):
        """
        Reconnect a connection that has failed or become unhealthy.

        Args:
            connection_id: ID of connection to reconnect

        Raises:
            MCPConnectionError: If reconnection fails
        """
        if not self.pool_config.enable_auto_reconnect:
            raise MCPConnectionError(
                "Auto-reconnect disabled",
                server_name=self.server_config.name,
            )

        logger.info(f"Attempting to reconnect connection: {connection_id}")

        # Close the old connection
        await self._close_connection(connection_id)

        # Create a new connection with retry logic
        retry_policy = RetryPolicy(self.retry_config)

        try:
            new_conn = await retry_policy.execute_async(self._create_connection)
            self._stats["total_reconnections"] += 1
            logger.info(f"Successfully reconnected: {connection_id} -> {new_conn.connection_id}")
            return new_conn

        except Exception as e:
            log_error_with_context(
                e,
                component="mcp_pool",
                additional_context={
                    "connection_id": connection_id,
                    "server": self.server_config.name,
                    "operation": "reconnect",
                },
            )
            raise MCPConnectionError(
                f"Failed to reconnect after {self.retry_config.max_attempts} attempts: {e}",
                server_name=self.server_config.name,
            )

    async def _health_check_loop(self):
        """
        Background task that performs periodic health checks on idle connections.

        This task runs continuously until the pool is closed, checking
        idle connections and removing unhealthy ones.
        """
        logger.info(
            f"Starting health check loop for '{self.server_config.name}' "
            f"(interval={self.pool_config.health_check_interval}s)"
        )

        while not self._closed:
            try:
                await asyncio.sleep(self.pool_config.health_check_interval)

                async with self._lock:
                    for connection_id, pooled_conn in list(self._connections.items()):
                        # Only check idle connections
                        if pooled_conn.state != ConnectionState.IDLE:
                            continue

                        # Check if connection is healthy
                        if not pooled_conn.is_healthy(self.pool_config):
                            logger.info(
                                f"Health check failed for connection {connection_id}, "
                                "closing..."
                            )
                            await self._close_connection(connection_id)

                            # Maintain minimum connections
                            if len(self._connections) < self.pool_config.min_connections:
                                try:
                                    await self._create_connection()
                                except Exception as e:
                                    logger.error(
                                        f"Failed to create replacement connection: {e}"
                                    )

                        pooled_conn.last_health_check = datetime.now()
                        self._stats["total_health_checks"] += 1

            except asyncio.CancelledError:
                logger.info("Health check loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}", exc_info=True)
                # Continue running despite errors
                await asyncio.sleep(5)  # Brief pause before retry

    async def close(self):
        """
        Close the connection pool and clean up all resources.

        This method:
        - Stops background tasks
        - Closes all connections
        - Cleans up resources
        """
        if self._closed:
            logger.warning(f"Connection pool for '{self.server_config.name}' already closed")
            return

        logger.info(f"Closing connection pool for '{self.server_config.name}'")

        self._closed = True

        # Stop health check task
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Close all connections
        async with self._lock:
            for connection_id in list(self._connections.keys()):
                await self._close_connection(connection_id)

        logger.info(
            f"Connection pool closed for '{self.server_config.name}'. "
            f"Stats: {self.get_stats()}"
        )

    def get_stats(self) -> dict[str, Any]:
        """
        Get connection pool statistics.

        Returns:
            Dictionary with pool statistics and metrics
        """
        return {
            "server_name": self.server_config.name,
            "pool_config": {
                "min_connections": self.pool_config.min_connections,
                "max_connections": self.pool_config.max_connections,
                "health_checks_enabled": self.pool_config.enable_health_checks,
                "auto_reconnect_enabled": self.pool_config.enable_auto_reconnect,
            },
            "pool_state": {
                "initialized": self._initialized,
                "closed": self._closed,
                "active_connections": len(self._connections),
                "available_connections": self._available.qsize(),
            },
            "connection_details": [
                {
                    "connection_id": conn.connection_id,
                    "state": conn.state.value,
                    "age_seconds": (datetime.now() - conn.created_at).total_seconds(),
                    "idle_seconds": (datetime.now() - conn.last_used).total_seconds(),
                    "use_count": conn.use_count,
                    "error_count": conn.error_count,
                }
                for conn in self._connections.values()
            ],
            "statistics": self._stats,
            "circuit_breaker": self.circuit_breaker.get_stats(),
        }

    def get_connection_count(self) -> int:
        """
        Get current number of connections in pool.

        Returns:
            Number of active connections
        """
        return len(self._connections)

    def is_healthy(self) -> bool:
        """
        Check if pool is healthy and operational.

        Returns:
            True if pool is initialized, not closed, and has connections
        """
        return (
            self._initialized
            and not self._closed
            and len(self._connections) >= self.pool_config.min_connections
            and not self.circuit_breaker.is_open()
        )


class MCPConnectionPoolRegistry:
    """
    Registry for managing connection pools across multiple MCP servers.

    Maintains a pool instance per server, allowing centralized pool
    management and monitoring.

    Example:
        >>> registry = MCPConnectionPoolRegistry()
        >>> pool = await registry.get_pool(server_config)
        >>> async with pool.acquire() as session:
        ...     result = await session.call_tool("get_tasks", {})
    """

    def __init__(self, default_pool_config: Optional[PoolConfig] = None):
        """
        Initialize pool registry.

        Args:
            default_pool_config: Default config for new pools
        """
        self.default_pool_config = default_pool_config or PoolConfig()
        self._pools: dict[str, MCPConnectionPool] = {}
        self._lock = asyncio.Lock()

    async def get_pool(
        self,
        server_config: MCPServerConfig,
        pool_config: Optional[PoolConfig] = None,
    ) -> MCPConnectionPool:
        """
        Get or create connection pool for a server.

        Args:
            server_config: MCP server configuration
            pool_config: Optional pool config (uses default if None)

        Returns:
            MCPConnectionPool instance for the server
        """
        server_name = server_config.name

        async with self._lock:
            if server_name not in self._pools:
                logger.info(f"Creating connection pool for server: {server_name}")
                pool = MCPConnectionPool(
                    server_config=server_config,
                    pool_config=pool_config or self.default_pool_config,
                )
                await pool.initialize()
                self._pools[server_name] = pool
            else:
                logger.debug(f"Reusing existing pool for server: {server_name}")

            return self._pools[server_name]

    async def close_pool(self, server_name: str):
        """
        Close and remove a specific pool.

        Args:
            server_name: Name of server whose pool to close
        """
        async with self._lock:
            if server_name in self._pools:
                pool = self._pools[server_name]
                await pool.close()
                del self._pools[server_name]
                logger.info(f"Closed pool for server: {server_name}")

    async def close_all(self):
        """Close all connection pools."""
        async with self._lock:
            for server_name, pool in self._pools.items():
                logger.info(f"Closing pool for server: {server_name}")
                await pool.close()
            self._pools.clear()

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """
        Get statistics for all connection pools.

        Returns:
            Dictionary mapping server names to their pool stats
        """
        return {name: pool.get_stats() for name, pool in self._pools.items()}

    def get_pool_count(self) -> int:
        """
        Get number of pools in registry.

        Returns:
            Number of active pools
        """
        return len(self._pools)


# Global pool registry instance
_global_registry: Optional[MCPConnectionPoolRegistry] = None


def get_global_pool_registry() -> MCPConnectionPoolRegistry:
    """
    Get global connection pool registry instance.

    Returns:
        Singleton MCPConnectionPoolRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = MCPConnectionPoolRegistry()
    return _global_registry
