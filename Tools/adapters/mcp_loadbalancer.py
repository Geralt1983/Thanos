"""
MCP Server Load Balancing.

Provides intelligent load balancing across multiple instances of the same server type
with support for multiple strategies including round-robin, least-connections,
health-aware routing, and automatic failover.

This module enables efficient distribution of tool calls across server instances,
improving performance and reliability through intelligent routing and failover.
"""

import asyncio
import logging
import random
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, List, Optional

from .mcp_config import MCPServerConfig
from .mcp_errors import (
    MCPError,
    MCPServerUnavailableError,
    log_error_with_context,
)
from .mcp_health import (
    HealthMonitor,
    HealthStatus,
    get_global_health_monitor_registry,
)

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(str, Enum):
    """
    Available load balancing strategies.

    - ROUND_ROBIN: Distribute requests evenly across all healthy servers
    - LEAST_CONNECTIONS: Route to server with fewest active connections
    - HEALTH_AWARE: Route to healthiest server based on metrics
    - WEIGHTED: Route based on configured weights
    - RANDOM: Randomly select from healthy servers
    """

    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    HEALTH_AWARE = "health_aware"
    WEIGHTED = "weighted"
    RANDOM = "random"


class LoadBalancerError(MCPError):
    """
    Error raised during load balancing operations.

    Includes context about the load balancing operation that failed.
    """

    def __init__(
        self,
        message: str,
        strategy: Optional[str] = None,
        available_servers: Optional[int] = None,
        context: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize load balancer error.

        Args:
            message: Error description
            strategy: Load balancing strategy being used
            available_servers: Number of available servers
            context: Additional error context
        """
        context = context or {}
        if strategy:
            context["strategy"] = strategy
        if available_servers is not None:
            context["available_servers"] = available_servers

        super().__init__(
            message=message,
            context=context,
            retryable=True,
        )
        self.strategy = strategy
        self.available_servers = available_servers


@dataclass
class LoadBalancerConfig:
    """
    Configuration for load balancer behavior.

    Defines strategy, health checking, failover behavior, and weights.
    """

    strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN
    """Load balancing strategy to use"""

    enable_health_checks: bool = True
    """Whether to consider server health when routing"""

    failover_on_error: bool = True
    """Whether to automatically failover to another server on error"""

    max_failover_attempts: int = 3
    """Maximum number of failover attempts before giving up"""

    weights: dict[str, float] = field(default_factory=dict)
    """Server weights for weighted strategy (server_name -> weight)"""

    exclude_degraded: bool = False
    """Whether to exclude degraded servers from routing"""

    connection_timeout: float = 30.0
    """Timeout for server connections (seconds)"""

    min_healthy_servers: int = 1
    """Minimum number of healthy servers required"""


@dataclass
class ServerInstance:
    """
    A server instance tracked by the load balancer.

    Tracks connection counts, health status, and usage statistics.
    """

    config: MCPServerConfig
    """Server configuration"""

    active_connections: int = 0
    """Current number of active connections"""

    total_requests: int = 0
    """Total requests routed to this server"""

    last_used: Optional[datetime] = None
    """When this server was last used"""

    weight: float = 1.0
    """Server weight for weighted load balancing"""

    health_status: HealthStatus = HealthStatus.UNKNOWN
    """Current health status"""

    enabled: bool = True
    """Whether this server is enabled for routing"""

    @property
    def name(self) -> str:
        """Get server name."""
        return self.config.name

    def increment_connections(self) -> None:
        """Increment active connection count."""
        self.active_connections += 1
        self.total_requests += 1
        self.last_used = datetime.now()

    def decrement_connections(self) -> None:
        """Decrement active connection count."""
        self.active_connections = max(0, self.active_connections - 1)

    def is_available(self, exclude_degraded: bool = False) -> bool:
        """
        Check if server is available for routing.

        Args:
            exclude_degraded: Whether to exclude degraded servers

        Returns:
            True if server is available for routing
        """
        if not self.enabled:
            return False

        if self.health_status == HealthStatus.UNHEALTHY:
            return False

        if exclude_degraded and self.health_status == HealthStatus.DEGRADED:
            return False

        return True


class LoadBalancer:
    """
    Load balancer for distributing requests across multiple server instances.

    Supports multiple load balancing strategies, health-aware routing,
    and automatic failover to backup servers.
    """

    def __init__(
        self,
        server_type: str,
        servers: List[MCPServerConfig],
        config: Optional[LoadBalancerConfig] = None,
    ):
        """
        Initialize load balancer.

        Args:
            server_type: Type of servers being load balanced (for grouping)
            servers: List of server configurations to load balance
            config: Load balancing configuration
        """
        self.server_type = server_type
        self.config = config or LoadBalancerConfig()
        self._servers: dict[str, ServerInstance] = {}
        self._round_robin_index = 0
        self._lock = asyncio.Lock()
        self._health_registry = get_global_health_monitor_registry()

        # Initialize server instances
        for server_config in servers:
            weight = self.config.weights.get(server_config.name, 1.0)
            self._servers[server_config.name] = ServerInstance(
                config=server_config,
                weight=weight,
            )

        logger.info(
            f"Initialized load balancer for '{server_type}' with {len(servers)} servers "
            f"using {self.config.strategy.value} strategy"
        )

    async def select_server(
        self,
        exclude: Optional[List[str]] = None,
    ) -> ServerInstance:
        """
        Select a server instance based on the configured strategy.

        Args:
            exclude: List of server names to exclude from selection

        Returns:
            Selected server instance

        Raises:
            LoadBalancerError: If no available servers found
        """
        async with self._lock:
            # Update health status for all servers
            if self.config.enable_health_checks:
                await self._update_health_status()

            # Get available servers
            exclude = exclude or []
            available = [
                server
                for server in self._servers.values()
                if server.name not in exclude
                and server.is_available(self.config.exclude_degraded)
            ]

            if not available:
                raise LoadBalancerError(
                    f"No available servers for '{self.server_type}'",
                    strategy=self.config.strategy.value,
                    available_servers=0,
                )

            # Check minimum healthy servers requirement
            if len(available) < self.config.min_healthy_servers:
                logger.warning(
                    f"Only {len(available)} healthy servers available for '{self.server_type}', "
                    f"minimum is {self.config.min_healthy_servers}"
                )

            # Select server based on strategy
            if self.config.strategy == LoadBalancingStrategy.ROUND_ROBIN:
                server = self._select_round_robin(available)
            elif self.config.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
                server = self._select_least_connections(available)
            elif self.config.strategy == LoadBalancingStrategy.HEALTH_AWARE:
                server = self._select_health_aware(available)
            elif self.config.strategy == LoadBalancingStrategy.WEIGHTED:
                server = self._select_weighted(available)
            elif self.config.strategy == LoadBalancingStrategy.RANDOM:
                server = self._select_random(available)
            else:
                # Default to round-robin
                server = self._select_round_robin(available)

            logger.debug(
                f"Selected server '{server.name}' using {self.config.strategy.value} strategy "
                f"(active_connections={server.active_connections}, "
                f"health={server.health_status.value})"
            )

            return server

    def _select_round_robin(self, available: List[ServerInstance]) -> ServerInstance:
        """Select server using round-robin strategy."""
        server = available[self._round_robin_index % len(available)]
        self._round_robin_index += 1
        return server

    def _select_least_connections(
        self, available: List[ServerInstance]
    ) -> ServerInstance:
        """Select server with least active connections."""
        return min(available, key=lambda s: s.active_connections)

    def _select_health_aware(self, available: List[ServerInstance]) -> ServerInstance:
        """
        Select healthiest server based on health status and metrics.

        Priority: HEALTHY > DEGRADED > UNKNOWN
        Within same health level, prefer lower connection count.
        """
        # Sort by health status (HEALTHY=0, DEGRADED=1, UNKNOWN=2, UNHEALTHY=3)
        health_priority = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.DEGRADED: 1,
            HealthStatus.UNKNOWN: 2,
            HealthStatus.UNHEALTHY: 3,
        }

        return min(
            available,
            key=lambda s: (
                health_priority.get(s.health_status, 99),
                s.active_connections,
            ),
        )

    def _select_weighted(self, available: List[ServerInstance]) -> ServerInstance:
        """
        Select server using weighted random selection.

        Servers with higher weights have higher probability of selection.
        """
        if not available:
            raise LoadBalancerError(
                "No available servers for weighted selection",
                strategy=self.config.strategy.value,
            )

        # Calculate total weight
        total_weight = sum(s.weight for s in available)
        if total_weight <= 0:
            # Fallback to random if all weights are 0
            return random.choice(available)

        # Weighted random selection
        rand_value = random.uniform(0, total_weight)
        cumulative_weight = 0.0

        for server in available:
            cumulative_weight += server.weight
            if rand_value <= cumulative_weight:
                return server

        # Fallback to last server (should not reach here)
        return available[-1]

    def _select_random(self, available: List[ServerInstance]) -> ServerInstance:
        """Select server randomly."""
        return random.choice(available)

    async def _update_health_status(self) -> None:
        """Update health status for all servers from health monitor."""
        try:
            # Get health status from registry
            health_statuses = await self._health_registry.get_all_health_status()

            for server_name, health_result in health_statuses.items():
                if server_name in self._servers:
                    self._servers[server_name].health_status = health_result.status
        except Exception as e:
            logger.warning(
                f"Failed to update health status for '{self.server_type}': {e}"
            )

    @asynccontextmanager
    async def get_connection(
        self, exclude: Optional[List[str]] = None
    ) -> ServerInstance:
        """
        Get a connection to a server with automatic cleanup.

        Args:
            exclude: List of server names to exclude from selection

        Yields:
            Selected server instance

        Raises:
            LoadBalancerError: If no available servers found
        """
        server = await self.select_server(exclude=exclude)
        server.increment_connections()

        try:
            yield server
        finally:
            server.decrement_connections()

    async def execute_with_failover(
        self,
        func: Callable[[ServerInstance], Any],
        max_attempts: Optional[int] = None,
    ) -> Any:
        """
        Execute a function with automatic failover on error.

        Args:
            func: Async function to execute with server instance
            max_attempts: Maximum failover attempts (uses config if not specified)

        Returns:
            Result from successful function execution

        Raises:
            LoadBalancerError: If all failover attempts exhausted
        """
        max_attempts = max_attempts or self.config.max_failover_attempts
        exclude: List[str] = []
        last_error = None

        for attempt in range(max_attempts):
            try:
                async with self.get_connection(exclude=exclude) as server:
                    logger.debug(
                        f"Executing on server '{server.name}' "
                        f"(attempt {attempt + 1}/{max_attempts})"
                    )
                    result = await func(server)
                    return result
            except Exception as e:
                last_error = e
                if hasattr(e, "server_name"):
                    exclude.append(e.server_name)
                logger.warning(
                    f"Failover attempt {attempt + 1}/{max_attempts} failed for "
                    f"'{self.server_type}': {e}"
                )

                # Don't retry if failover is disabled
                if not self.config.failover_on_error:
                    raise

                # Check if we should continue retrying
                if attempt < max_attempts - 1:
                    continue
                else:
                    break

        # All attempts exhausted
        raise LoadBalancerError(
            f"All failover attempts exhausted for '{self.server_type}' after "
            f"{max_attempts} attempts: {last_error}",
            strategy=self.config.strategy.value,
            context={"last_error": str(last_error), "excluded_servers": exclude},
        )

    def get_server_by_name(self, name: str) -> Optional[ServerInstance]:
        """
        Get server instance by name.

        Args:
            name: Server name

        Returns:
            Server instance or None if not found
        """
        return self._servers.get(name)

    def add_server(self, config: MCPServerConfig, weight: float = 1.0) -> None:
        """
        Add a new server to the load balancer.

        Args:
            config: Server configuration
            weight: Server weight for weighted strategy
        """
        if config.name in self._servers:
            logger.warning(f"Server '{config.name}' already exists, updating")

        self._servers[config.name] = ServerInstance(
            config=config,
            weight=weight,
        )
        logger.info(f"Added server '{config.name}' to load balancer '{self.server_type}'")

    def remove_server(self, name: str) -> bool:
        """
        Remove a server from the load balancer.

        Args:
            name: Server name to remove

        Returns:
            True if server was removed, False if not found
        """
        if name in self._servers:
            del self._servers[name]
            logger.info(f"Removed server '{name}' from load balancer '{self.server_type}'")
            return True
        return False

    def enable_server(self, name: str) -> bool:
        """
        Enable a server for routing.

        Args:
            name: Server name

        Returns:
            True if server was enabled, False if not found
        """
        server = self._servers.get(name)
        if server:
            server.enabled = True
            logger.info(f"Enabled server '{name}'")
            return True
        return False

    def disable_server(self, name: str) -> bool:
        """
        Disable a server from routing.

        Args:
            name: Server name

        Returns:
            True if server was disabled, False if not found
        """
        server = self._servers.get(name)
        if server:
            server.enabled = False
            logger.info(f"Disabled server '{name}'")
            return True
        return False

    def get_stats(self) -> dict[str, Any]:
        """
        Get load balancer statistics.

        Returns:
            Dictionary with load balancing statistics
        """
        total_requests = sum(s.total_requests for s in self._servers.values())
        active_connections = sum(s.active_connections for s in self._servers.values())
        available_servers = sum(
            1
            for s in self._servers.values()
            if s.is_available(self.config.exclude_degraded)
        )

        server_stats = {
            name: {
                "active_connections": server.active_connections,
                "total_requests": server.total_requests,
                "health_status": server.health_status.value,
                "enabled": server.enabled,
                "weight": server.weight,
                "last_used": (
                    server.last_used.isoformat() if server.last_used else None
                ),
            }
            for name, server in self._servers.items()
        }

        return {
            "server_type": self.server_type,
            "strategy": self.config.strategy.value,
            "total_servers": len(self._servers),
            "available_servers": available_servers,
            "total_requests": total_requests,
            "active_connections": active_connections,
            "servers": server_stats,
        }

    def get_available_servers(self) -> List[str]:
        """
        Get list of available server names.

        Returns:
            List of available server names
        """
        return [
            name
            for name, server in self._servers.items()
            if server.is_available(self.config.exclude_degraded)
        ]

    def get_all_servers(self) -> List[str]:
        """
        Get list of all server names.

        Returns:
            List of all server names
        """
        return list(self._servers.keys())


class LoadBalancerRegistry:
    """
    Registry for managing multiple load balancers.

    Provides centralized management of load balancers for different server types.
    """

    def __init__(self):
        """Initialize load balancer registry."""
        self._load_balancers: dict[str, LoadBalancer] = {}
        self._lock = asyncio.Lock()
        logger.debug("Initialized load balancer registry")

    async def register_load_balancer(
        self,
        server_type: str,
        servers: List[MCPServerConfig],
        config: Optional[LoadBalancerConfig] = None,
    ) -> LoadBalancer:
        """
        Register a load balancer for a server type.

        Args:
            server_type: Type of servers being load balanced
            servers: List of server configurations
            config: Load balancing configuration

        Returns:
            Created load balancer instance
        """
        async with self._lock:
            if server_type in self._load_balancers:
                logger.warning(
                    f"Load balancer for '{server_type}' already exists, replacing"
                )

            load_balancer = LoadBalancer(server_type, servers, config)
            self._load_balancers[server_type] = load_balancer

            logger.info(
                f"Registered load balancer for '{server_type}' with {len(servers)} servers"
            )
            return load_balancer

    async def unregister_load_balancer(self, server_type: str) -> bool:
        """
        Unregister a load balancer.

        Args:
            server_type: Type of servers being load balanced

        Returns:
            True if load balancer was removed, False if not found
        """
        async with self._lock:
            if server_type in self._load_balancers:
                del self._load_balancers[server_type]
                logger.info(f"Unregistered load balancer for '{server_type}'")
                return True
            return False

    def get_load_balancer(self, server_type: str) -> Optional[LoadBalancer]:
        """
        Get load balancer for a server type.

        Args:
            server_type: Type of servers being load balanced

        Returns:
            Load balancer instance or None if not found
        """
        return self._load_balancers.get(server_type)

    def get_all_load_balancers(self) -> dict[str, LoadBalancer]:
        """
        Get all registered load balancers.

        Returns:
            Dictionary of server type to load balancer
        """
        return self._load_balancers.copy()

    async def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """
        Get statistics for all load balancers.

        Returns:
            Dictionary of server type to statistics
        """
        stats = {}
        for server_type, lb in self._load_balancers.items():
            stats[server_type] = lb.get_stats()
        return stats

    async def select_server(
        self,
        server_type: str,
        exclude: Optional[List[str]] = None,
    ) -> ServerInstance:
        """
        Select a server from a load balancer.

        Args:
            server_type: Type of servers being load balanced
            exclude: List of server names to exclude from selection

        Returns:
            Selected server instance

        Raises:
            LoadBalancerError: If load balancer not found or no servers available
        """
        load_balancer = self.get_load_balancer(server_type)
        if not load_balancer:
            raise LoadBalancerError(
                f"No load balancer registered for '{server_type}'",
                context={"server_type": server_type},
            )

        return await load_balancer.select_server(exclude=exclude)

    @asynccontextmanager
    async def get_connection(
        self,
        server_type: str,
        exclude: Optional[List[str]] = None,
    ) -> ServerInstance:
        """
        Get a connection to a server with automatic cleanup.

        Args:
            server_type: Type of servers being load balanced
            exclude: List of server names to exclude from selection

        Yields:
            Selected server instance

        Raises:
            LoadBalancerError: If load balancer not found or no servers available
        """
        load_balancer = self.get_load_balancer(server_type)
        if not load_balancer:
            raise LoadBalancerError(
                f"No load balancer registered for '{server_type}'",
                context={"server_type": server_type},
            )

        async with load_balancer.get_connection(exclude=exclude) as server:
            yield server

    async def close(self) -> None:
        """Close all load balancers and cleanup resources."""
        async with self._lock:
            count = len(self._load_balancers)
            self._load_balancers.clear()
            logger.info(f"Closed {count} load balancers")


# Global registry singleton
_global_registry: Optional[LoadBalancerRegistry] = None


def get_global_load_balancer_registry() -> LoadBalancerRegistry:
    """
    Get the global load balancer registry singleton.

    Returns:
        Global load balancer registry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = LoadBalancerRegistry()
    return _global_registry


# Convenience functions


def create_load_balancer(
    server_type: str,
    servers: List[MCPServerConfig],
    strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
    enable_health_checks: bool = True,
    failover_on_error: bool = True,
    weights: Optional[dict[str, float]] = None,
) -> LoadBalancer:
    """
    Create a load balancer with common configuration.

    Args:
        server_type: Type of servers being load balanced
        servers: List of server configurations
        strategy: Load balancing strategy
        enable_health_checks: Whether to enable health checks
        failover_on_error: Whether to enable automatic failover
        weights: Server weights for weighted strategy

    Returns:
        Configured load balancer instance
    """
    config = LoadBalancerConfig(
        strategy=strategy,
        enable_health_checks=enable_health_checks,
        failover_on_error=failover_on_error,
        weights=weights or {},
    )
    return LoadBalancer(server_type, servers, config)


async def select_server_with_lb(
    server_type: str,
    servers: List[MCPServerConfig],
    strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
) -> ServerInstance:
    """
    Quick helper to select a server using load balancing.

    Args:
        server_type: Type of servers being load balanced
        servers: List of server configurations
        strategy: Load balancing strategy

    Returns:
        Selected server instance
    """
    lb = create_load_balancer(server_type, servers, strategy)
    return await lb.select_server()
