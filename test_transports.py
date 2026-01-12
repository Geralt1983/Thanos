#!/usr/bin/env python3
"""
Test script for transport layer implementation.
Verifies that all transports can be imported and instantiated correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add Tools directory to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_stdio_transport():
    """Test stdio transport instantiation and configuration."""
    from Tools.adapters.mcp_config import StdioConfig
    from Tools.adapters.transports import StdioTransport

    print("Testing StdioTransport...")

    # Create config
    config = StdioConfig(
        command="node",
        args=["./dist/index.js"],
        env={"TEST_VAR": "test_value"},
    )

    # Create transport
    transport = StdioTransport(config)

    # Verify properties
    assert transport.transport_type == "stdio", "Transport type should be 'stdio'"
    assert transport.config == config, "Config should be stored"

    # Test health check
    health = await transport.health_check()
    assert health["status"] == "configured", "Should be configured"
    assert health["transport_type"] == "stdio", "Type should be stdio"
    assert health["command"] == "node", "Command should match"

    print("✓ StdioTransport tests passed")


async def test_sse_transport():
    """Test SSE transport instantiation and configuration."""
    from Tools.adapters.mcp_config import SSEConfig
    from Tools.adapters.transports import SSETransport

    print("Testing SSETransport...")

    # Create config
    config = SSEConfig(
        url="https://api.example.com/mcp",
        headers={"Authorization": "Bearer token"},
        timeout=30,
        reconnect_interval=5,
    )

    # Create transport
    transport = SSETransport(config)

    # Verify properties
    assert transport.transport_type == "sse", "Transport type should be 'sse'"
    assert transport.config == config, "Config should be stored"

    # Test health check
    health = await transport.health_check()
    assert health["status"] == "configured", "Should be configured"
    assert health["transport_type"] == "sse", "Type should be sse"
    assert health["url"] == "https://api.example.com/mcp", "URL should match"

    print("✓ SSETransport tests passed")


async def test_transport_abstraction():
    """Test transport base class and abstraction."""
    from Tools.adapters.transports import Transport, TransportError

    print("Testing Transport abstraction...")

    # Verify exception can be raised
    try:
        raise TransportError("Test error")
    except TransportError as e:
        assert str(e) == "Test error", "Exception message should match"

    # Verify Transport is abstract
    try:
        # This should fail because Transport is abstract
        Transport(None)
        assert False, "Should not be able to instantiate abstract Transport"
    except TypeError as e:
        assert "abstract" in str(e).lower(), "Should complain about abstract class"

    print("✓ Transport abstraction tests passed")


async def test_mcp_bridge_integration():
    """Test MCPBridge integration with transport layer."""
    from Tools.adapters.mcp_bridge import MCPBridge
    from Tools.adapters.mcp_config import MCPServerConfig, StdioConfig

    print("Testing MCPBridge transport integration...")

    # Create server config with stdio transport
    config = MCPServerConfig(
        name="test-server",
        transport=StdioConfig(
            command="echo",
            args=["test"],
        ),
    )

    # Create bridge
    bridge = MCPBridge(config)

    # Verify transport creation
    transport = bridge._create_transport()
    assert transport.transport_type == "stdio", "Should create stdio transport"

    print("✓ MCPBridge integration tests passed")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Transport Layer Test Suite")
    print("=" * 60)
    print()

    try:
        await test_stdio_transport()
        print()
        await test_sse_transport()
        print()
        await test_transport_abstraction()
        print()
        await test_mcp_bridge_integration()
        print()
        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
