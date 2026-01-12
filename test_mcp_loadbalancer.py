"""
Tests for MCP Server Load Balancing.

Tests load balancing strategies, failover behavior, and health-aware routing.
"""

import asyncio
import pytest
from datetime import datetime

from Tools.adapters.mcp_loadbalancer import (
    LoadBalancer,
    LoadBalancerConfig,
    LoadBalancerError,
    LoadBalancerRegistry,
    LoadBalancingStrategy,
    ServerInstance,
    create_load_balancer,
    get_global_load_balancer_registry,
    select_server_with_lb,
)
from Tools.adapters.mcp_config import MCPServerConfig, StdioConfig
from Tools.adapters.mcp_health import HealthStatus


# Test Fixtures


def create_test_config(name: str) -> MCPServerConfig:
    """Create a test server configuration."""
    return MCPServerConfig(
        name=name,
        transport=StdioConfig(
            command="node",
            args=[f"/path/to/{name}/index.js"],
        ),
        enabled=True,
    )


def create_test_servers(count: int = 3) -> list[MCPServerConfig]:
    """Create multiple test server configurations."""
    return [create_test_config(f"server-{i}") for i in range(count)]


# Test Load Balancing Strategy Enum


def test_load_balancing_strategy_values():
    """Test that all load balancing strategies are defined."""
    assert LoadBalancingStrategy.ROUND_ROBIN.value == "round_robin"
    assert LoadBalancingStrategy.LEAST_CONNECTIONS.value == "least_connections"
    assert LoadBalancingStrategy.HEALTH_AWARE.value == "health_aware"
    assert LoadBalancingStrategy.WEIGHTED.value == "weighted"
    assert LoadBalancingStrategy.RANDOM.value == "random"


# Test LoadBalancerConfig


def test_load_balancer_config_defaults():
    """Test default load balancer configuration."""
    config = LoadBalancerConfig()
    assert config.strategy == LoadBalancingStrategy.ROUND_ROBIN
    assert config.enable_health_checks is True
    assert config.failover_on_error is True
    assert config.max_failover_attempts == 3
    assert config.weights == {}
    assert config.exclude_degraded is False
    assert config.connection_timeout == 30.0
    assert config.min_healthy_servers == 1


def test_load_balancer_config_custom():
    """Test custom load balancer configuration."""
    config = LoadBalancerConfig(
        strategy=LoadBalancingStrategy.LEAST_CONNECTIONS,
        enable_health_checks=False,
        failover_on_error=False,
        max_failover_attempts=5,
        weights={"server-1": 2.0, "server-2": 1.0},
        exclude_degraded=True,
        connection_timeout=60.0,
        min_healthy_servers=2,
    )
    assert config.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS
    assert config.enable_health_checks is False
    assert config.failover_on_error is False
    assert config.max_failover_attempts == 5
    assert config.weights == {"server-1": 2.0, "server-2": 1.0}
    assert config.exclude_degraded is True
    assert config.connection_timeout == 60.0
    assert config.min_healthy_servers == 2


# Test ServerInstance


def test_server_instance_initialization():
    """Test server instance initialization."""
    config = create_test_config("test-server")
    instance = ServerInstance(config=config, weight=2.0)

    assert instance.config.name == "test-server"
    assert instance.name == "test-server"
    assert instance.active_connections == 0
    assert instance.total_requests == 0
    assert instance.last_used is None
    assert instance.weight == 2.0
    assert instance.health_status == HealthStatus.UNKNOWN
    assert instance.enabled is True


def test_server_instance_connection_tracking():
    """Test connection count tracking."""
    config = create_test_config("test-server")
    instance = ServerInstance(config=config)

    # Increment connections
    instance.increment_connections()
    assert instance.active_connections == 1
    assert instance.total_requests == 1
    assert instance.last_used is not None

    instance.increment_connections()
    assert instance.active_connections == 2
    assert instance.total_requests == 2

    # Decrement connections
    instance.decrement_connections()
    assert instance.active_connections == 1
    assert instance.total_requests == 2  # Total doesn't decrease

    instance.decrement_connections()
    assert instance.active_connections == 0

    # Can't go negative
    instance.decrement_connections()
    assert instance.active_connections == 0


def test_server_instance_availability():
    """Test server availability logic."""
    config = create_test_config("test-server")
    instance = ServerInstance(config=config)

    # Healthy and enabled
    instance.health_status = HealthStatus.HEALTHY
    instance.enabled = True
    assert instance.is_available() is True
    assert instance.is_available(exclude_degraded=True) is True

    # Degraded
    instance.health_status = HealthStatus.DEGRADED
    assert instance.is_available() is True
    assert instance.is_available(exclude_degraded=True) is False

    # Unhealthy
    instance.health_status = HealthStatus.UNHEALTHY
    assert instance.is_available() is False
    assert instance.is_available(exclude_degraded=True) is False

    # Disabled
    instance.health_status = HealthStatus.HEALTHY
    instance.enabled = False
    assert instance.is_available() is False


# Test LoadBalancer


@pytest.mark.asyncio
async def test_load_balancer_initialization():
    """Test load balancer initialization."""
    servers = create_test_servers(3)
    config = LoadBalancerConfig(strategy=LoadBalancingStrategy.ROUND_ROBIN)
    lb = LoadBalancer("test-type", servers, config)

    assert lb.server_type == "test-type"
    assert lb.config.strategy == LoadBalancingStrategy.ROUND_ROBIN
    assert len(lb._servers) == 3
    assert "server-0" in lb._servers
    assert "server-1" in lb._servers
    assert "server-2" in lb._servers


@pytest.mark.asyncio
async def test_round_robin_selection():
    """Test round-robin server selection."""
    servers = create_test_servers(3)
    config = LoadBalancerConfig(strategy=LoadBalancingStrategy.ROUND_ROBIN)
    lb = LoadBalancer("test-type", servers, config)

    # Mark all servers as healthy (since health checks are enabled by default)
    for server in lb._servers.values():
        server.health_status = HealthStatus.HEALTHY

    # Should cycle through servers
    server1 = await lb.select_server()
    server2 = await lb.select_server()
    server3 = await lb.select_server()
    server4 = await lb.select_server()

    assert server1.name == "server-0"
    assert server2.name == "server-1"
    assert server3.name == "server-2"
    assert server4.name == "server-0"  # Back to first


@pytest.mark.asyncio
async def test_least_connections_selection():
    """Test least-connections server selection."""
    servers = create_test_servers(3)
    config = LoadBalancerConfig(strategy=LoadBalancingStrategy.LEAST_CONNECTIONS)
    lb = LoadBalancer("test-type", servers, config)

    # Mark all servers as healthy
    for server in lb._servers.values():
        server.health_status = HealthStatus.HEALTHY

    # Set different connection counts
    lb._servers["server-0"].active_connections = 5
    lb._servers["server-1"].active_connections = 2
    lb._servers["server-2"].active_connections = 8

    # Should select server with least connections
    server = await lb.select_server()
    assert server.name == "server-1"

    # Increase its connections
    lb._servers["server-1"].active_connections = 10

    # Should now select server-0
    server = await lb.select_server()
    assert server.name == "server-0"


@pytest.mark.asyncio
async def test_health_aware_selection():
    """Test health-aware server selection."""
    servers = create_test_servers(3)
    config = LoadBalancerConfig(strategy=LoadBalancingStrategy.HEALTH_AWARE)
    lb = LoadBalancer("test-type", servers, config)

    # Set different health statuses
    lb._servers["server-0"].health_status = HealthStatus.DEGRADED
    lb._servers["server-0"].active_connections = 1
    lb._servers["server-1"].health_status = HealthStatus.HEALTHY
    lb._servers["server-1"].active_connections = 5
    lb._servers["server-2"].health_status = HealthStatus.HEALTHY
    lb._servers["server-2"].active_connections = 2

    # Should prefer healthy servers over degraded
    server = await lb.select_server()
    assert server.name in ["server-1", "server-2"]
    assert server.health_status == HealthStatus.HEALTHY

    # Among healthy servers, prefer lower connections
    server = await lb.select_server()
    assert server.name == "server-2"


@pytest.mark.asyncio
async def test_weighted_selection():
    """Test weighted server selection."""
    servers = create_test_servers(3)
    config = LoadBalancerConfig(
        strategy=LoadBalancingStrategy.WEIGHTED,
        weights={
            "server-0": 5.0,
            "server-1": 1.0,
            "server-2": 1.0,
        },
    )
    lb = LoadBalancer("test-type", servers, config)

    # Mark all servers as healthy
    for server in lb._servers.values():
        server.health_status = HealthStatus.HEALTHY

    # Select multiple times and count
    selections = {}
    for _ in range(100):
        server = await lb.select_server()
        selections[server.name] = selections.get(server.name, 0) + 1

    # server-0 with weight 5 should be selected much more often
    # This is probabilistic, so we use a loose threshold
    assert selections["server-0"] > 40  # Should be around 71%


@pytest.mark.asyncio
async def test_random_selection():
    """Test random server selection."""
    servers = create_test_servers(3)
    config = LoadBalancerConfig(strategy=LoadBalancingStrategy.RANDOM)
    lb = LoadBalancer("test-type", servers, config)

    # Mark all servers as healthy
    for server in lb._servers.values():
        server.health_status = HealthStatus.HEALTHY

    # Select multiple times
    selected_names = set()
    for _ in range(20):
        server = await lb.select_server()
        selected_names.add(server.name)

    # Should have selected from all servers at least once (probabilistic)
    assert len(selected_names) >= 2  # At least 2 different servers


@pytest.mark.asyncio
async def test_exclude_servers():
    """Test excluding servers from selection."""
    servers = create_test_servers(3)
    config = LoadBalancerConfig(strategy=LoadBalancingStrategy.ROUND_ROBIN)
    lb = LoadBalancer("test-type", servers, config)

    # Mark all servers as healthy
    for server in lb._servers.values():
        server.health_status = HealthStatus.HEALTHY

    # Exclude two servers
    server = await lb.select_server(exclude=["server-0", "server-1"])
    assert server.name == "server-2"


@pytest.mark.asyncio
async def test_no_available_servers():
    """Test error when no servers available."""
    servers = create_test_servers(3)
    lb = LoadBalancer("test-type", servers)

    # Mark all servers as unhealthy
    for server in lb._servers.values():
        server.health_status = HealthStatus.UNHEALTHY

    # Should raise error
    with pytest.raises(LoadBalancerError) as exc_info:
        await lb.select_server()

    assert "No available servers" in str(exc_info.value)
    assert exc_info.value.available_servers == 0


@pytest.mark.asyncio
async def test_exclude_degraded_servers():
    """Test excluding degraded servers."""
    servers = create_test_servers(3)
    config = LoadBalancerConfig(
        strategy=LoadBalancingStrategy.ROUND_ROBIN,
        exclude_degraded=True,
    )
    lb = LoadBalancer("test-type", servers, config)

    # Mark servers with different health statuses
    lb._servers["server-0"].health_status = HealthStatus.HEALTHY
    lb._servers["server-1"].health_status = HealthStatus.DEGRADED
    lb._servers["server-2"].health_status = HealthStatus.DEGRADED

    # Should only select healthy server
    server = await lb.select_server()
    assert server.name == "server-0"


@pytest.mark.asyncio
async def test_connection_context_manager():
    """Test connection context manager."""
    servers = create_test_servers(1)
    lb = LoadBalancer("test-type", servers)
    lb._servers["server-0"].health_status = HealthStatus.HEALTHY

    # Check initial state
    assert lb._servers["server-0"].active_connections == 0

    # Use context manager
    async with lb.get_connection() as server:
        assert server.name == "server-0"
        assert server.active_connections == 1

    # Should be decremented after exit
    assert lb._servers["server-0"].active_connections == 0


@pytest.mark.asyncio
async def test_execute_with_failover_success():
    """Test successful execution without failover."""
    servers = create_test_servers(2)
    lb = LoadBalancer("test-type", servers)

    # Mark servers as healthy
    for server in lb._servers.values():
        server.health_status = HealthStatus.HEALTHY

    async def mock_func(server: ServerInstance) -> str:
        return f"result from {server.name}"

    result = await lb.execute_with_failover(mock_func)
    assert "result from" in result


@pytest.mark.asyncio
async def test_execute_with_failover():
    """Test automatic failover on error."""
    servers = create_test_servers(3)
    config = LoadBalancerConfig(
        strategy=LoadBalancingStrategy.ROUND_ROBIN,
        failover_on_error=True,
        max_failover_attempts=3,
    )
    lb = LoadBalancer("test-type", servers, config)

    # Mark all servers as healthy
    for server in lb._servers.values():
        server.health_status = HealthStatus.HEALTHY

    call_count = 0

    async def mock_func(server: ServerInstance) -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception(f"Error on {server.name}")
        return f"success from {server.name}"

    result = await lb.execute_with_failover(mock_func)
    assert "success from" in result
    assert call_count == 3


@pytest.mark.asyncio
async def test_execute_with_failover_exhausted():
    """Test all failover attempts exhausted."""
    servers = create_test_servers(2)
    config = LoadBalancerConfig(
        strategy=LoadBalancingStrategy.ROUND_ROBIN,
        failover_on_error=True,
        max_failover_attempts=2,
    )
    lb = LoadBalancer("test-type", servers, config)

    # Mark servers as healthy
    for server in lb._servers.values():
        server.health_status = HealthStatus.HEALTHY

    async def mock_func(server: ServerInstance) -> str:
        raise Exception(f"Error on {server.name}")

    with pytest.raises(LoadBalancerError) as exc_info:
        await lb.execute_with_failover(mock_func)

    assert "All failover attempts exhausted" in str(exc_info.value)


@pytest.mark.asyncio
async def test_server_management():
    """Test adding, removing, enabling, and disabling servers."""
    servers = create_test_servers(2)
    lb = LoadBalancer("test-type", servers)

    # Add server
    new_config = create_test_config("server-new")
    lb.add_server(new_config, weight=2.0)
    assert "server-new" in lb._servers
    assert lb._servers["server-new"].weight == 2.0

    # Get server by name
    server = lb.get_server_by_name("server-new")
    assert server is not None
    assert server.name == "server-new"

    # Disable server
    assert lb.disable_server("server-new") is True
    assert lb._servers["server-new"].enabled is False

    # Enable server
    assert lb.enable_server("server-new") is True
    assert lb._servers["server-new"].enabled is True

    # Remove server
    assert lb.remove_server("server-new") is True
    assert "server-new" not in lb._servers

    # Remove non-existent server
    assert lb.remove_server("non-existent") is False


@pytest.mark.asyncio
async def test_load_balancer_stats():
    """Test load balancer statistics."""
    servers = create_test_servers(2)
    lb = LoadBalancer("test-type", servers)

    # Set some data
    lb._servers["server-0"].active_connections = 3
    lb._servers["server-0"].total_requests = 10
    lb._servers["server-0"].health_status = HealthStatus.HEALTHY

    lb._servers["server-1"].active_connections = 1
    lb._servers["server-1"].total_requests = 5
    lb._servers["server-1"].health_status = HealthStatus.DEGRADED

    stats = lb.get_stats()

    assert stats["server_type"] == "test-type"
    assert stats["total_servers"] == 2
    assert stats["total_requests"] == 15
    assert stats["active_connections"] == 4
    assert "server-0" in stats["servers"]
    assert stats["servers"]["server-0"]["active_connections"] == 3
    assert stats["servers"]["server-0"]["health_status"] == "healthy"


@pytest.mark.asyncio
async def test_get_available_servers():
    """Test getting list of available servers."""
    servers = create_test_servers(3)
    lb = LoadBalancer("test-type", servers)

    # Set different health statuses
    lb._servers["server-0"].health_status = HealthStatus.HEALTHY
    lb._servers["server-1"].health_status = HealthStatus.UNHEALTHY
    lb._servers["server-2"].health_status = HealthStatus.DEGRADED

    available = lb.get_available_servers()
    assert "server-0" in available
    assert "server-2" in available
    assert "server-1" not in available

    all_servers = lb.get_all_servers()
    assert len(all_servers) == 3


# Test LoadBalancerRegistry


@pytest.mark.asyncio
async def test_registry_initialization():
    """Test registry initialization."""
    registry = LoadBalancerRegistry()
    assert len(registry._load_balancers) == 0


@pytest.mark.asyncio
async def test_registry_register_load_balancer():
    """Test registering a load balancer."""
    registry = LoadBalancerRegistry()
    servers = create_test_servers(2)
    config = LoadBalancerConfig(strategy=LoadBalancingStrategy.ROUND_ROBIN)

    lb = await registry.register_load_balancer("test-type", servers, config)
    assert lb.server_type == "test-type"
    assert registry.get_load_balancer("test-type") is not None


@pytest.mark.asyncio
async def test_registry_unregister_load_balancer():
    """Test unregistering a load balancer."""
    registry = LoadBalancerRegistry()
    servers = create_test_servers(2)

    await registry.register_load_balancer("test-type", servers)
    assert await registry.unregister_load_balancer("test-type") is True
    assert registry.get_load_balancer("test-type") is None

    # Unregister non-existent
    assert await registry.unregister_load_balancer("non-existent") is False


@pytest.mark.asyncio
async def test_registry_get_all_load_balancers():
    """Test getting all load balancers."""
    registry = LoadBalancerRegistry()
    servers1 = create_test_servers(2)
    servers2 = create_test_servers(2)

    await registry.register_load_balancer("type-1", servers1)
    await registry.register_load_balancer("type-2", servers2)

    all_lbs = registry.get_all_load_balancers()
    assert len(all_lbs) == 2
    assert "type-1" in all_lbs
    assert "type-2" in all_lbs


@pytest.mark.asyncio
async def test_registry_select_server():
    """Test selecting server through registry."""
    registry = LoadBalancerRegistry()
    servers = create_test_servers(2)
    await registry.register_load_balancer("test-type", servers)

    # Mark servers as healthy
    lb = registry.get_load_balancer("test-type")
    for server in lb._servers.values():
        server.health_status = HealthStatus.HEALTHY

    server = await registry.select_server("test-type")
    assert server.name in ["server-0", "server-1"]

    # Non-existent load balancer
    with pytest.raises(LoadBalancerError):
        await registry.select_server("non-existent")


@pytest.mark.asyncio
async def test_registry_get_connection():
    """Test getting connection through registry."""
    registry = LoadBalancerRegistry()
    servers = create_test_servers(1)
    await registry.register_load_balancer("test-type", servers)

    # Mark server as healthy
    lb = registry.get_load_balancer("test-type")
    lb._servers["server-0"].health_status = HealthStatus.HEALTHY

    async with registry.get_connection("test-type") as server:
        assert server.name == "server-0"
        assert server.active_connections == 1

    # Connection should be released
    assert lb._servers["server-0"].active_connections == 0


@pytest.mark.asyncio
async def test_registry_get_all_stats():
    """Test getting stats for all load balancers."""
    registry = LoadBalancerRegistry()
    servers1 = create_test_servers(2)
    servers2 = create_test_servers(1)

    await registry.register_load_balancer("type-1", servers1)
    await registry.register_load_balancer("type-2", servers2)

    stats = await registry.get_all_stats()
    assert "type-1" in stats
    assert "type-2" in stats
    assert stats["type-1"]["total_servers"] == 2
    assert stats["type-2"]["total_servers"] == 1


@pytest.mark.asyncio
async def test_registry_close():
    """Test closing registry."""
    registry = LoadBalancerRegistry()
    servers = create_test_servers(2)

    await registry.register_load_balancer("type-1", servers)
    await registry.register_load_balancer("type-2", servers)

    await registry.close()
    assert len(registry._load_balancers) == 0


# Test Global Registry


def test_global_registry_singleton():
    """Test global registry is singleton."""
    registry1 = get_global_load_balancer_registry()
    registry2 = get_global_load_balancer_registry()
    assert registry1 is registry2


# Test Convenience Functions


def test_create_load_balancer_convenience():
    """Test convenience function for creating load balancer."""
    servers = create_test_servers(2)
    lb = create_load_balancer(
        "test-type",
        servers,
        strategy=LoadBalancingStrategy.LEAST_CONNECTIONS,
        enable_health_checks=False,
        failover_on_error=False,
        weights={"server-0": 2.0},
    )

    assert lb.server_type == "test-type"
    assert lb.config.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS
    assert lb.config.enable_health_checks is False
    assert lb.config.failover_on_error is False
    assert lb.config.weights == {"server-0": 2.0}


@pytest.mark.asyncio
async def test_select_server_with_lb_convenience():
    """Test convenience function for selecting server."""
    servers = create_test_servers(2)

    # Mark servers as healthy (need to get LB instance first)
    lb = create_load_balancer("test-type", servers)
    for server in lb._servers.values():
        server.health_status = HealthStatus.HEALTHY

    server = await lb.select_server()
    assert server.name in ["server-0", "server-1"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
