"""
Thanos MCP Bridge Adapters

Provides unified access to external services (WorkOS, Oura) via both:
1. Direct adapters - Direct Python implementations (better performance)
2. MCP bridges - Full MCP protocol support (better ecosystem integration)

The AdapterManager seamlessly supports both approaches with automatic routing.

Usage:
    from Tools.adapters import get_default_manager

    async def main():
        # Get manager with both direct adapters and MCP bridges
        manager = await get_default_manager(enable_mcp_bridges=True)

        # Call WorkOS tools (routes to best available adapter)
        result = await manager.call_tool("get_today_metrics")

        # Call Oura tools (with prefix for clarity)
        result = await manager.call_tool("oura.get_daily_readiness", {
            "start_date": "2026-01-08"
        })

        # Cleanup (closes both adapters and bridges)
        await manager.close_all()
"""

import logging
from typing import Any, List, Optional

from .base import BaseAdapter, ToolResult

# MCP bridge imports (conditional)
try:
    from .mcp_bridge import MCPBridge
    from .mcp_discovery import discover_servers, get_server_config
    from .mcp_config import MCPServerConfig

    MCP_BRIDGE_AVAILABLE = True
except ImportError:
    MCPBridge = None
    MCP_BRIDGE_AVAILABLE = False

# Conditional Oura import (requires httpx package)
try:
    from .oura import OuraAdapter

    OURA_AVAILABLE = True
except ImportError:
    OuraAdapter = None
    OURA_AVAILABLE = False

# Conditional WorkOS import (requires asyncpg package)
try:
    from .workos import WorkOSAdapter

    WORKOS_AVAILABLE = True
except ImportError:
    WorkOSAdapter = None
    WORKOS_AVAILABLE = False

# Conditional Neo4j import (requires neo4j package)
try:
    from .neo4j_adapter import Neo4jAdapter

    NEO4J_AVAILABLE = True
except ImportError:
    Neo4jAdapter = None
    NEO4J_AVAILABLE = False

# Conditional ChromaDB import (requires chromadb package)
try:
    from .chroma_adapter import ChromaAdapter

    CHROMADB_AVAILABLE = True
except ImportError:
    ChromaAdapter = None
    CHROMADB_AVAILABLE = False

__all__ = [
    "BaseAdapter",
    "ToolResult",
    "WorkOSAdapter",
    "OuraAdapter",
    "Neo4jAdapter",
    "ChromaAdapter",
    "MCPBridge",
    "AdapterManager",
    "get_default_manager",
    "WORKOS_AVAILABLE",
    "OURA_AVAILABLE",
    "NEO4J_AVAILABLE",
    "CHROMADB_AVAILABLE",
    "MCP_BRIDGE_AVAILABLE",
]

logger = logging.getLogger(__name__)


class AdapterManager:
    """
    Unified interface for all Thanos adapters.
    Routes tool calls to appropriate adapters based on tool name.
    """

    def __init__(self):
        self._adapters: dict[str, BaseAdapter] = {}
        self._tool_map: dict[str, str] = {}  # tool_name -> adapter_name
        self._initialized = False

    def register(self, adapter: BaseAdapter) -> None:
        """
        Register an adapter and index its tools.

        Args:
            adapter: Adapter instance to register
        """
        self._adapters[adapter.name] = adapter

        for tool in adapter.list_tools():
            tool_name = tool["name"]

            # Always register with adapter prefix (e.g., "workos.get_tasks")
            full_name = f"{adapter.name}.{tool_name}"
            self._tool_map[full_name] = adapter.name

            # Also allow short names if unique (no collision)
            if tool_name in self._tool_map:
                # Collision - remove the short name mapping
                # Force users to use prefixed names
                if self._tool_map[tool_name] != adapter.name:
                    logger.warning(
                        f"Tool name collision: {tool_name} exists in multiple adapters. "
                        f"Use prefixed names like '{full_name}'"
                    )
                    # Keep the first registration but log the conflict
            else:
                self._tool_map[tool_name] = adapter.name

        logger.debug(f"Registered adapter '{adapter.name}' with {len(adapter.list_tools())} tools")

    def list_adapters(self) -> list[str]:
        """Return list of registered adapter names."""
        return list(self._adapters.keys())

    def get_adapter(self, name: str) -> Optional[BaseAdapter]:
        """Get a specific adapter by name."""
        return self._adapters.get(name)

    def list_all_tools(self) -> dict[str, list[dict[str, Any]]]:
        """
        List all available tools grouped by adapter.

        Returns:
            Dict mapping adapter name to list of tool schemas
        """
        return {name: adapter.list_tools() for name, adapter in self._adapters.items()}

    def list_tools_flat(self) -> list[dict[str, Any]]:
        """
        List all tools as a flat list with adapter prefixes.

        Returns:
            List of tool schemas with 'adapter' field added
        """
        tools = []
        for name, adapter in self._adapters.items():
            for tool in adapter.list_tools():
                tool_copy = tool.copy()
                tool_copy["adapter"] = name
                tool_copy["full_name"] = f"{name}.{tool['name']}"
                tools.append(tool_copy)
        return tools

    async def call_tool(
        self, tool_name: str, arguments: Optional[dict[str, Any]] = None
    ) -> ToolResult:
        """
        Route a tool call to the appropriate adapter.

        Args:
            tool_name: Tool name (e.g., "get_tasks" or "workos.get_tasks")
            arguments: Tool parameters

        Returns:
            ToolResult from the adapter
        """
        arguments = arguments or {}

        # Handle prefixed tool names (e.g., "workos.get_tasks")
        if "." in tool_name:
            adapter_name, short_name = tool_name.split(".", 1)
            if adapter_name in self._adapters:
                adapter = self._adapters[adapter_name]
                logger.debug(f"Calling {adapter_name}.{short_name} with {arguments}")
                return await adapter.call_tool(short_name, arguments)
            else:
                return ToolResult.fail(
                    f"Unknown adapter: {adapter_name}. Available: {list(self._adapters.keys())}"
                )

        # Try to find adapter for unprefixed tool name
        if tool_name in self._tool_map:
            adapter_name = self._tool_map[tool_name]
            adapter = self._adapters[adapter_name]
            logger.debug(f"Calling {adapter_name}.{tool_name} with {arguments}")
            return await adapter.call_tool(tool_name, arguments)

        # Tool not found
        available_tools = list(self._tool_map.keys())
        return ToolResult.fail(
            f"Unknown tool: {tool_name}. "
            f"Available tools: {available_tools[:10]}... ({len(available_tools)} total)"
        )

    async def call_multiple(self, calls: list[dict[str, Any]]) -> list[ToolResult]:
        """
        Execute multiple tool calls.

        Args:
            calls: List of dicts with 'tool' and optional 'arguments' keys

        Returns:
            List of ToolResults in same order as calls
        """
        results = []
        for call in calls:
            tool_name = call.get("tool")
            arguments = call.get("arguments", {})
            result = await self.call_tool(tool_name, arguments)
            results.append(result)
        return results

    async def health_check_all(self) -> dict[str, ToolResult]:
        """
        Run health checks on all adapters.

        Returns:
            Dict mapping adapter name to health check result
        """
        results = {}
        for name, adapter in self._adapters.items():
            try:
                results[name] = await adapter.health_check()
            except Exception as e:
                results[name] = ToolResult.fail(f"Health check error: {e}")
        return results

    async def close_all(self) -> None:
        """Close all adapter connections."""
        for adapter in self._adapters.values():
            try:
                await adapter.close()
            except Exception as e:
                logger.warning(f"Error closing adapter {adapter.name}: {e}")
        self._initialized = False


# Singleton manager instance
_default_manager: Optional[AdapterManager] = None


async def get_default_manager(enable_mcp_bridges: bool = False) -> AdapterManager:
    """
    Get or create the default adapter manager.

    This is the primary entry point for using the adapter system.
    Registers WorkOS and Oura adapters by default.

    Args:
        enable_mcp_bridges: If True, discover and register MCP servers as bridges.
                          Provides access to third-party MCP ecosystem.

    Returns:
        Configured AdapterManager instance with direct adapters and optionally MCP bridges
    """
    global _default_manager

    if _default_manager is None:
        _default_manager = AdapterManager()

        # Register direct adapters first (better performance for built-in services)

        # Register WorkOS adapter if available
        if WORKOS_AVAILABLE:
            try:
                _default_manager.register(WorkOSAdapter())
                logger.info("Registered WorkOS adapter")
            except Exception as e:
                logger.warning(f"Failed to register WorkOS adapter: {e}")

        # Register Oura adapter if available
        if OURA_AVAILABLE:
            try:
                _default_manager.register(OuraAdapter())
                logger.info("Registered Oura adapter")
            except Exception as e:
                logger.warning(f"Failed to register Oura adapter: {e}")

        # Register Neo4j adapter if available and configured
        if NEO4J_AVAILABLE:
            try:
                _default_manager.register(Neo4jAdapter())
                logger.info("Registered Neo4j adapter")
            except Exception as e:
                logger.warning(f"Failed to register Neo4j adapter: {e}")

        # Register ChromaDB adapter if available
        if CHROMADB_AVAILABLE:
            try:
                _default_manager.register(ChromaAdapter())
                logger.info("Registered ChromaDB adapter")
            except Exception as e:
                logger.warning(f"Failed to register ChromaDB adapter: {e}")

        # Register MCP bridges if enabled
        if enable_mcp_bridges and MCP_BRIDGE_AVAILABLE:
            try:
                # Discover available MCP servers from configuration
                servers = await discover_servers()
                logger.info(f"Discovered {len(servers)} MCP servers")

                # Create and register a bridge for each discovered server
                for server_config in servers:
                    try:
                        bridge = MCPBridge(server_config)
                        await bridge.connect()  # Initialize connection
                        _default_manager.register(bridge)
                        logger.info(f"Registered MCP bridge for '{server_config.name}'")
                    except Exception as e:
                        logger.warning(
                            f"Failed to register MCP bridge for '{server_config.name}': {e}"
                        )
            except Exception as e:
                logger.warning(f"Failed to discover/register MCP bridges: {e}")

        _default_manager._initialized = True

    return _default_manager


async def reset_default_manager() -> None:
    """
    Close and reset the default manager.

    Useful for testing or when you need to reinitialize with different config.
    """
    global _default_manager
    if _default_manager is not None:
        await _default_manager.close_all()
        _default_manager = None
