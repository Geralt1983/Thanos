"""
Thanos MCP Bridge Adapters

Provides unified access to external services (WorkOS, Oura) that are
typically accessed via MCP servers. These adapters bypass MCP for
better performance and direct control while maintaining a compatible
interface for future MCP integration.

Usage:
    from Tools.adapters import get_default_manager

    async def main():
        manager = await get_default_manager()

        # Call WorkOS tools
        result = await manager.call_tool("get_today_metrics")

        # Call Oura tools (with prefix for clarity)
        result = await manager.call_tool("oura.get_daily_readiness", {
            "start_date": "2026-01-08"
        })

        # Cleanup
        await manager.close_all()
"""

from typing import Dict, Any, List, Optional
import logging

from .base import BaseAdapter, ToolResult
from .workos import WorkOSAdapter
from .oura import OuraAdapter

__all__ = [
    'BaseAdapter',
    'ToolResult',
    'WorkOSAdapter',
    'OuraAdapter',
    'AdapterManager',
    'get_default_manager',
]

logger = logging.getLogger(__name__)


class AdapterManager:
    """
    Unified interface for all Thanos adapters.
    Routes tool calls to appropriate adapters based on tool name.
    """

    def __init__(self):
        self._adapters: Dict[str, BaseAdapter] = {}
        self._tool_map: Dict[str, str] = {}  # tool_name -> adapter_name
        self._initialized = False

    def register(self, adapter: BaseAdapter) -> None:
        """
        Register an adapter and index its tools.

        Args:
            adapter: Adapter instance to register
        """
        self._adapters[adapter.name] = adapter

        for tool in adapter.list_tools():
            tool_name = tool['name']

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

    def list_adapters(self) -> List[str]:
        """Return list of registered adapter names."""
        return list(self._adapters.keys())

    def get_adapter(self, name: str) -> Optional[BaseAdapter]:
        """Get a specific adapter by name."""
        return self._adapters.get(name)

    def list_all_tools(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        List all available tools grouped by adapter.

        Returns:
            Dict mapping adapter name to list of tool schemas
        """
        return {
            name: adapter.list_tools()
            for name, adapter in self._adapters.items()
        }

    def list_tools_flat(self) -> List[Dict[str, Any]]:
        """
        List all tools as a flat list with adapter prefixes.

        Returns:
            List of tool schemas with 'adapter' field added
        """
        tools = []
        for name, adapter in self._adapters.items():
            for tool in adapter.list_tools():
                tool_copy = tool.copy()
                tool_copy['adapter'] = name
                tool_copy['full_name'] = f"{name}.{tool['name']}"
                tools.append(tool_copy)
        return tools

    async def call_tool(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None
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
        if '.' in tool_name:
            adapter_name, short_name = tool_name.split('.', 1)
            if adapter_name in self._adapters:
                adapter = self._adapters[adapter_name]
                logger.debug(f"Calling {adapter_name}.{short_name} with {arguments}")
                return await adapter.call_tool(short_name, arguments)
            else:
                return ToolResult.fail(
                    f"Unknown adapter: {adapter_name}. "
                    f"Available: {list(self._adapters.keys())}"
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

    async def call_multiple(
        self,
        calls: List[Dict[str, Any]]
    ) -> List[ToolResult]:
        """
        Execute multiple tool calls.

        Args:
            calls: List of dicts with 'tool' and optional 'arguments' keys

        Returns:
            List of ToolResults in same order as calls
        """
        results = []
        for call in calls:
            tool_name = call.get('tool')
            arguments = call.get('arguments', {})
            result = await self.call_tool(tool_name, arguments)
            results.append(result)
        return results

    async def health_check_all(self) -> Dict[str, ToolResult]:
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


async def get_default_manager() -> AdapterManager:
    """
    Get or create the default adapter manager.

    This is the primary entry point for using the adapter system.
    Registers WorkOS and Oura adapters by default.

    Returns:
        Configured AdapterManager instance
    """
    global _default_manager

    if _default_manager is None:
        _default_manager = AdapterManager()

        # Register default adapters
        try:
            _default_manager.register(WorkOSAdapter())
            logger.info("Registered WorkOS adapter")
        except Exception as e:
            logger.warning(f"Failed to register WorkOS adapter: {e}")

        try:
            _default_manager.register(OuraAdapter())
            logger.info("Registered Oura adapter")
        except Exception as e:
            logger.warning(f"Failed to register Oura adapter: {e}")

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
