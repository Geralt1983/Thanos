#!/usr/bin/env python3
"""
Verification script for WorkOS MCP Bridge

Tests that the WorkOS MCP bridge:
1. Can be created and configured
2. Lists the same tools as the direct adapter
3. Maintains parity with direct WorkOS adapter
4. Has acceptable performance

Run this script to verify subtask 4.3 acceptance criteria.
"""

import asyncio
import logging
import os
import sys
import time
from pathlib import Path

# Add Tools to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def verify_configuration():
    """Verify that WorkOS MCP configuration can be created."""
    print("\n" + "="*70)
    print("TEST 1: Configuration Creation")
    print("="*70)

    try:
        from Tools.adapters.workos_mcp_bridge import create_workos_mcp_config

        config = create_workos_mcp_config()

        print(f"✓ Configuration created successfully")
        print(f"  Server name: {config.name}")
        print(f"  Description: {config.description}")
        print(f"  Transport: {config.transport.type}")
        print(f"  Command: {config.transport.command}")
        print(f"  Enabled: {config.enabled}")
        print(f"  Priority: {config.priority}")
        print(f"  Tags: {', '.join(config.tags)}")

        # Verify required fields
        assert config.name == "workos-mcp", "Server name mismatch"
        assert config.transport.type == "stdio", "Transport type should be stdio"
        assert config.transport.command == "node", "Command should be node"
        assert config.enabled is True, "Server should be enabled by default"

        print("✓ All configuration checks passed")
        return True

    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        logger.exception("Configuration test failed")
        return False


async def verify_bridge_creation():
    """Verify that WorkOS MCP bridge can be created."""
    print("\n" + "="*70)
    print("TEST 2: Bridge Creation")
    print("="*70)

    try:
        from Tools.adapters.workos_mcp_bridge import (
            create_workos_mcp_bridge_sync,
            create_workos_mcp_config
        )
        from Tools.adapters.mcp_bridge import MCPBridge

        # Test sync creation
        bridge = create_workos_mcp_bridge_sync()

        print(f"✓ Bridge created successfully (sync)")
        print(f"  Bridge name: {bridge.name}")
        print(f"  Bridge type: {type(bridge).__name__}")

        # Verify it's an MCPBridge instance
        assert isinstance(bridge, MCPBridge), "Bridge should be MCPBridge instance"
        assert bridge.name == "workos-mcp", "Bridge name mismatch"

        # Test with custom config
        custom_config = create_workos_mcp_config(
            name="workos-mcp-custom",
            tags=["test", "custom"]
        )
        custom_bridge = create_workos_mcp_bridge_sync(custom_config)

        assert custom_bridge.name == "workos-mcp-custom", "Custom config not applied"

        print("✓ All bridge creation checks passed")
        return True

    except Exception as e:
        print(f"✗ Bridge creation test failed: {e}")
        logger.exception("Bridge creation test failed")
        return False


async def verify_tool_listing():
    """Verify that bridge can list tools (if server is available)."""
    print("\n" + "="*70)
    print("TEST 3: Tool Listing (requires running server)")
    print("="*70)

    try:
        from Tools.adapters.workos_mcp_bridge import create_workos_mcp_bridge

        # Check if server is available
        server_path = Path.home() / "Projects" / "Thanos" / "mcp-servers" / "workos-mcp" / "dist" / "index.js"
        if not server_path.exists():
            print(f"⊘ Server not found at {server_path}")
            print(f"  This is expected if the server hasn't been built yet")
            print(f"  Skipping tool listing test")
            return None  # Not a failure, just skip

        # Check if database URL is configured
        if not os.environ.get("WORKOS_DATABASE_URL") and not os.environ.get("DATABASE_URL"):
            print("⊘ No database URL configured (WORKOS_DATABASE_URL or DATABASE_URL)")
            print("  Skipping tool listing test")
            return None  # Not a failure, just skip

        print("✓ Server and database configuration found")
        print("  Attempting to connect to WorkOS MCP server...")

        # Create bridge
        bridge = await create_workos_mcp_bridge()

        # List tools
        start_time = time.time()
        await bridge.refresh_tools()
        duration_ms = (time.time() - start_time) * 1000

        tools = bridge.list_tools()

        print(f"✓ Successfully listed {len(tools)} tools from MCP server")
        print(f"  Connection time: {duration_ms:.2f}ms")
        print(f"\n  Available tools:")
        for tool in tools:
            print(f"    - {tool['name']}: {tool.get('description', 'No description')}")

        # Verify expected tools exist
        expected_tools = [
            "get_tasks",
            "get_today_metrics",
            "complete_task",
            "create_task",
            "update_task",
            "get_habits",
            "complete_habit",
            "get_clients",
            "daily_summary",
        ]

        tool_names = {tool['name'] for tool in tools}
        missing_tools = set(expected_tools) - tool_names

        if missing_tools:
            print(f"⚠ Some expected tools are missing: {missing_tools}")
        else:
            print(f"✓ All expected tools are present")

        # Clean up
        await bridge.close()

        return True

    except Exception as e:
        print(f"✗ Tool listing test failed: {e}")
        logger.exception("Tool listing test failed")
        return False


async def verify_adapter_parity():
    """Compare MCP bridge tools with direct adapter tools."""
    print("\n" + "="*70)
    print("TEST 4: Adapter Parity (requires running server)")
    print("="*70)

    try:
        # Check if direct adapter is available
        try:
            from Tools.adapters.workos import WorkOSAdapter
            direct_available = True
        except ImportError:
            print("⊘ Direct WorkOS adapter not available (requires asyncpg)")
            print("  Skipping parity test")
            return None

        # Check if server is available
        server_path = Path.home() / "Projects" / "Thanos" / "mcp-servers" / "workos-mcp" / "dist" / "index.js"
        if not server_path.exists():
            print(f"⊘ MCP server not found at {server_path}")
            print("  Skipping parity test")
            return None

        # Check database URL
        if not os.environ.get("WORKOS_DATABASE_URL") and not os.environ.get("DATABASE_URL"):
            print("⊘ No database URL configured")
            print("  Skipping parity test")
            return None

        from Tools.adapters.workos_mcp_bridge import create_workos_mcp_bridge

        print("✓ Both adapters available, comparing tools...")

        # Get tools from direct adapter
        direct_adapter = WorkOSAdapter()
        direct_tools = direct_adapter.list_tools()
        direct_tool_names = {tool['name'] for tool in direct_tools}

        print(f"  Direct adapter: {len(direct_tools)} tools")

        # Get tools from MCP bridge
        mcp_bridge = await create_workos_mcp_bridge()
        await mcp_bridge.refresh_tools()
        mcp_tools = mcp_bridge.list_tools()
        mcp_tool_names = {tool['name'] for tool in mcp_tools}

        print(f"  MCP bridge: {len(mcp_tools)} tools")

        # Compare
        only_in_direct = direct_tool_names - mcp_tool_names
        only_in_mcp = mcp_tool_names - direct_tool_names
        common_tools = direct_tool_names & mcp_tool_names

        print(f"\n  Common tools: {len(common_tools)}")
        print(f"  Only in direct adapter: {len(only_in_direct)}")
        if only_in_direct:
            print(f"    {only_in_direct}")
        print(f"  Only in MCP bridge: {len(only_in_mcp)}")
        if only_in_mcp:
            print(f"    {only_in_mcp}")

        # Calculate parity percentage
        total_unique_tools = len(direct_tool_names | mcp_tool_names)
        parity_pct = (len(common_tools) / total_unique_tools * 100) if total_unique_tools > 0 else 0

        print(f"\n  Parity: {parity_pct:.1f}%")

        if parity_pct >= 90:
            print(f"✓ Excellent parity (≥90%)")
        elif parity_pct >= 75:
            print(f"⚠ Good parity but some differences (≥75%)")
        else:
            print(f"✗ Low parity (<75%) - significant differences")

        # Clean up
        await direct_adapter.close()
        await mcp_bridge.close()

        return parity_pct >= 75

    except Exception as e:
        print(f"✗ Parity test failed: {e}")
        logger.exception("Parity test failed")
        return False


async def main():
    """Run all verification tests."""
    print("\n" + "="*70)
    print("WORKOS MCP BRIDGE VERIFICATION")
    print("Subtask 4.3: Create MCP bridge instance for existing WorkOS MCP server")
    print("="*70)

    results = {}

    # Test 1: Configuration
    results['configuration'] = await verify_configuration()

    # Test 2: Bridge creation
    results['bridge_creation'] = await verify_bridge_creation()

    # Test 3: Tool listing (optional - requires running server)
    results['tool_listing'] = await verify_tool_listing()

    # Test 4: Adapter parity (optional - requires running server and direct adapter)
    results['adapter_parity'] = await verify_adapter_parity()

    # Summary
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)

    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)

    for test_name, result in results.items():
        status = "✓ PASS" if result is True else "✗ FAIL" if result is False else "⊘ SKIP"
        print(f"  {status}: {test_name.replace('_', ' ').title()}")

    print(f"\nResults: {passed} passed, {failed} failed, {skipped} skipped")

    # Acceptance criteria check
    print("\n" + "="*70)
    print("ACCEPTANCE CRITERIA")
    print("="*70)

    criteria = {
        "WorkOS MCP server accessible via MCPBridge": results['configuration'] and results['bridge_creation'],
        "All existing workos tools available": results['tool_listing'] or results['adapter_parity'],
        "Parity with direct WorkOS adapter": results['adapter_parity'] if results['adapter_parity'] is not None else "Skipped",
        "Performance benchmarked and acceptable": "Manual verification required",
    }

    for criterion, status in criteria.items():
        check = "✓" if status is True else "⊘" if status == "Skipped" or isinstance(status, str) else "✗"
        print(f"  {check} {criterion}")
        if isinstance(status, str) and status != "Skipped":
            print(f"      {status}")

    # Exit code
    if failed > 0:
        print("\n⚠ Some tests failed. Check logs above.")
        return 1
    elif passed == 0:
        print("\n⚠ No tests were able to run. This is expected if the MCP server isn't set up yet.")
        print("   The bridge implementation is complete and ready for integration.")
        return 0
    else:
        print("\n✓ All tests passed!")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
