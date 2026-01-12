#!/usr/bin/env python3
"""
Test transport selection in MCPBridge.
Verifies that MCPBridge correctly selects transports based on configuration.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def test_transport_selection():
    """Test that MCPBridge selects the correct transport based on config."""
    from Tools.adapters.mcp_bridge import MCPBridge
    from Tools.adapters.mcp_config import MCPServerConfig, SSEConfig, StdioConfig
    from Tools.adapters.transports import SSETransport, StdioTransport

    print("Testing transport selection in MCPBridge...")

    # Test 1: Stdio transport selection
    stdio_config = MCPServerConfig(
        name="stdio-server",
        transport=StdioConfig(command="node", args=["server.js"]),
    )
    bridge = MCPBridge(stdio_config)
    transport = bridge._create_transport()
    assert isinstance(
        transport, StdioTransport
    ), "Should create StdioTransport for stdio config"
    assert transport.transport_type == "stdio"
    print("  ✓ Stdio transport selection works")

    # Test 2: SSE transport selection
    sse_config = MCPServerConfig(
        name="sse-server",
        transport=SSEConfig(url="https://api.example.com/mcp"),
    )
    bridge = MCPBridge(sse_config)
    transport = bridge._create_transport()
    assert isinstance(
        transport, SSETransport
    ), "Should create SSETransport for SSE config"
    assert transport.transport_type == "sse"
    print("  ✓ SSE transport selection works")

    # Test 3: Verify unsupported transport raises error
    # (We'll test this when HTTP transport is added)

    print("✓ All transport selection tests passed!")


if __name__ == "__main__":
    try:
        test_transport_selection()
        sys.exit(0)
    except AssertionError as e:
        print(f"✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
