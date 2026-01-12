#!/usr/bin/env python3
"""
Test suite for MCP connection pooling.

Verifies pool configuration, connection lifecycle, health checks,
and reconnection logic.
"""

import asyncio
import sys
from pathlib import Path

# Add Tools directory to path
sys.path.insert(0, str(Path(__file__).parent))

from Tools.adapters.mcp_pool import (
    ConnectionState,
    MCPConnectionPool,
    MCPConnectionPoolRegistry,
    PoolConfig,
    PooledConnection,
    get_global_pool_registry,
)


def test_pool_config():
    """Test pool configuration dataclass."""
    print("\n=== Test: Pool Configuration ===")

    # Default config
    config = PoolConfig()
    assert config.min_connections == 1
    assert config.max_connections == 10
    assert config.enable_health_checks is True
    assert config.enable_auto_reconnect is True
    print("✓ Default pool configuration")

    # Custom config
    custom = PoolConfig(
        min_connections=2,
        max_connections=20,
        connection_timeout=60.0,
        idle_timeout=600.0,
        enable_health_checks=False,
    )
    assert custom.min_connections == 2
    assert custom.max_connections == 20
    assert custom.connection_timeout == 60.0
    assert custom.enable_health_checks is False
    print("✓ Custom pool configuration")

    print("✓ Pool configuration tests passed")


def test_connection_state():
    """Test connection state enum."""
    print("\n=== Test: Connection State ===")

    assert ConnectionState.IDLE.value == "idle"
    assert ConnectionState.ACTIVE.value == "active"
    assert ConnectionState.UNHEALTHY.value == "unhealthy"
    assert ConnectionState.CLOSED.value == "closed"

    print("✓ Connection state enum tests passed")


def test_pooled_connection():
    """Test pooled connection dataclass and methods."""
    print("\n=== Test: Pooled Connection ===")

    # Create mock session (we won't actually use it)
    mock_session = None

    # Create pooled connection
    conn = PooledConnection(
        connection_id="test-conn-1",
        session=mock_session,
        state=ConnectionState.IDLE,
    )

    assert conn.connection_id == "test-conn-1"
    assert conn.state == ConnectionState.IDLE
    assert conn.use_count == 0
    assert conn.error_count == 0
    print("✓ Pooled connection creation")

    # Test mark_used
    conn.mark_used()
    assert conn.use_count == 1
    print("✓ Mark connection used")

    # Test mark_error
    conn.mark_error()
    assert conn.error_count == 1
    conn.mark_error()
    assert conn.error_count == 2
    assert conn.state == ConnectionState.IDLE
    conn.mark_error()
    assert conn.error_count == 3
    assert conn.state == ConnectionState.UNHEALTHY
    print("✓ Mark connection error (unhealthy after 3 errors)")

    # Test is_healthy
    config = PoolConfig(
        max_lifetime=3600.0,
        idle_timeout=300.0,
    )

    healthy_conn = PooledConnection(
        connection_id="healthy-conn",
        session=mock_session,
        state=ConnectionState.IDLE,
    )
    assert healthy_conn.is_healthy(config) is True
    print("✓ Healthy connection check")

    unhealthy_conn = PooledConnection(
        connection_id="unhealthy-conn",
        session=mock_session,
        state=ConnectionState.UNHEALTHY,
    )
    assert unhealthy_conn.is_healthy(config) is False
    print("✓ Unhealthy connection check")

    print("✓ Pooled connection tests passed")


def test_pool_instantiation():
    """Test connection pool instantiation."""
    print("\n=== Test: Pool Instantiation ===")

    # Import config for testing
    from Tools.adapters.mcp_config import MCPServerConfig, StdioConfig

    # Create mock server config
    server_config = MCPServerConfig(
        name="test-server",
        transport=StdioConfig(
            command="node",
            args=["test.js"],
        ),
    )

    # Create pool with default config
    pool = MCPConnectionPool(server_config)
    assert pool.server_config.name == "test-server"
    assert pool.pool_config.min_connections == 1
    assert pool.pool_config.max_connections == 10
    assert pool._initialized is False
    assert pool._closed is False
    print("✓ Pool instantiation with default config")

    # Create pool with custom config
    custom_config = PoolConfig(min_connections=2, max_connections=5)
    pool2 = MCPConnectionPool(server_config, custom_config)
    assert pool2.pool_config.min_connections == 2
    assert pool2.pool_config.max_connections == 5
    print("✓ Pool instantiation with custom config")

    # Check initial stats
    stats = pool.get_stats()
    assert stats["server_name"] == "test-server"
    assert stats["pool_state"]["initialized"] is False
    assert stats["pool_state"]["closed"] is False
    assert stats["pool_state"]["active_connections"] == 0
    print("✓ Pool statistics")

    print("✓ Pool instantiation tests passed")


def test_pool_registry():
    """Test connection pool registry."""
    print("\n=== Test: Pool Registry ===")

    # Create registry
    registry = MCPConnectionPoolRegistry()
    assert registry.get_pool_count() == 0
    print("✓ Registry instantiation")

    # Test global registry
    global_registry = get_global_pool_registry()
    assert global_registry is not None
    assert isinstance(global_registry, MCPConnectionPoolRegistry)

    # Calling again should return same instance
    global_registry2 = get_global_pool_registry()
    assert global_registry is global_registry2
    print("✓ Global registry singleton")

    # Test stats on empty registry
    stats = registry.get_all_stats()
    assert len(stats) == 0
    print("✓ Empty registry stats")

    print("✓ Pool registry tests passed")


def test_pool_health_check():
    """Test pool health check."""
    print("\n=== Test: Pool Health Check ===")

    from Tools.adapters.mcp_config import MCPServerConfig, StdioConfig

    server_config = MCPServerConfig(
        name="test-server",
        transport=StdioConfig(command="node", args=["test.js"]),
    )

    pool = MCPConnectionPool(server_config)

    # Pool not initialized yet
    assert pool.is_healthy() is False
    print("✓ Uninitialized pool is unhealthy")

    # Note: We can't test initialized pool without actual MCP server
    # That would require integration tests

    print("✓ Pool health check tests passed")


def run_all_tests():
    """Run all synchronous tests."""
    print("=" * 70)
    print("MCP Connection Pooling Test Suite")
    print("=" * 70)

    try:
        test_pool_config()
        test_connection_state()
        test_pooled_connection()
        test_pool_instantiation()
        test_pool_registry()
        test_pool_health_check()

        print("\n" + "=" * 70)
        print("✓ All tests passed!")
        print("=" * 70)
        return True

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
