"""
Thanos MCP Bridge Adapters

Provides unified access to external services (WorkOS, Oura, Calendar) that are
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

        # Call Calendar tools (unified interface)
        result = await manager.call_tool("calendar.get_today_events", {
            "calendar_id": "primary"
        })

        # Cleanup
        await manager.close_all()
"""

import logging
from typing import Any, Optional, TYPE_CHECKING

# Lightweight imports - no external dependencies
from .base import BaseAdapter, ToolResult

# TYPE_CHECKING imports for type hints (not evaluated at runtime)
if TYPE_CHECKING:
    from .workos import WorkOSAdapter
    from .oura import OuraAdapter
    from .neo4j_adapter import Neo4jAdapter
    from .chroma_adapter import ChromaAdapter
    from .google_calendar import GoogleCalendarAdapter
    from .calendar_adapter import CalendarAdapter

# Availability flags - checked lazily when needed
_WORKOS_AVAILABLE: Optional[bool] = None
_OURA_AVAILABLE: Optional[bool] = None
_NEO4J_AVAILABLE: Optional[bool] = None
_CHROMADB_AVAILABLE: Optional[bool] = None
_GOOGLE_CALENDAR_AVAILABLE: Optional[bool] = None
_CALENDAR_AVAILABLE: Optional[bool] = None


def _check_workos_available() -> bool:
    """Check if WorkOS adapter dependencies are available."""
    global _WORKOS_AVAILABLE
    if _WORKOS_AVAILABLE is None:
        try:
            import asyncpg  # noqa: F401
            _WORKOS_AVAILABLE = True
        except ImportError:
            _WORKOS_AVAILABLE = False
    return _WORKOS_AVAILABLE


def _check_oura_available() -> bool:
    """Check if Oura adapter dependencies are available."""
    global _OURA_AVAILABLE
    if _OURA_AVAILABLE is None:
        try:
            import httpx  # noqa: F401
            _OURA_AVAILABLE = True
        except ImportError:
            _OURA_AVAILABLE = False
    return _OURA_AVAILABLE


def _check_neo4j_available() -> bool:
    """Check if Neo4j adapter dependencies are available."""
    global _NEO4J_AVAILABLE
    if _NEO4J_AVAILABLE is None:
        try:
            from .neo4j_adapter import Neo4jAdapter  # noqa: F401
            _NEO4J_AVAILABLE = True
        except ImportError:
            _NEO4J_AVAILABLE = False
    return _NEO4J_AVAILABLE


def _check_chromadb_available() -> bool:
    """Check if ChromaDB adapter dependencies are available."""
    global _CHROMADB_AVAILABLE
    if _CHROMADB_AVAILABLE is None:
        try:
            from .chroma_adapter import ChromaAdapter  # noqa: F401
            _CHROMADB_AVAILABLE = True
        except ImportError:
            _CHROMADB_AVAILABLE = False
    return _CHROMADB_AVAILABLE


def _check_google_calendar_available() -> bool:
    """Check if Google Calendar adapter dependencies are available."""
    global _GOOGLE_CALENDAR_AVAILABLE
    if _GOOGLE_CALENDAR_AVAILABLE is None:
        try:
            from .google_calendar import GoogleCalendarAdapter  # noqa: F401
            _GOOGLE_CALENDAR_AVAILABLE = True
        except ImportError:
            _GOOGLE_CALENDAR_AVAILABLE = False
    return _GOOGLE_CALENDAR_AVAILABLE


def _check_calendar_available() -> bool:
    """Check if Calendar adapter dependencies are available."""
    global _CALENDAR_AVAILABLE
    if _CALENDAR_AVAILABLE is None:
        try:
            from .calendar_adapter import CalendarAdapter  # noqa: F401
            _CALENDAR_AVAILABLE = True
        except ImportError:
            _CALENDAR_AVAILABLE = False
    return _CALENDAR_AVAILABLE


# For backward compatibility, we use a module-level __getattr__ to lazily evaluate availability
# These are accessed as module attributes (e.g., adapters.NEO4J_AVAILABLE)
def __getattr__(name: str):
    """Lazy attribute access for availability flags and adapter classes."""
    if name == "NEO4J_AVAILABLE":
        return _check_neo4j_available()
    elif name == "CHROMADB_AVAILABLE":
        return _check_chromadb_available()
    elif name == "GOOGLE_CALENDAR_AVAILABLE":
        return _check_google_calendar_available()
    elif name == "CALENDAR_AVAILABLE":
        return _check_calendar_available()
    elif name == "WORKOS_AVAILABLE":
        return _check_workos_available()
    elif name == "OURA_AVAILABLE":
        return _check_oura_available()
    # Lazy class imports for backward compatibility
    elif name == "WorkOSAdapter":
        return get_workos_adapter_class()
    elif name == "OuraAdapter":
        return get_oura_adapter_class()
    elif name == "Neo4jAdapter":
        if _check_neo4j_available():
            return get_neo4j_adapter_class()
        return None
    elif name == "ChromaAdapter":
        if _check_chromadb_available():
            return get_chromadb_adapter_class()
        return None
    elif name == "GoogleCalendarAdapter":
        if _check_google_calendar_available():
            return get_google_calendar_adapter_class()
        return None
    elif name == "CalendarAdapter":
        if _check_calendar_available():
            return get_calendar_adapter_class()
        return None
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Lazy import functions for adapters
def get_workos_adapter_class():
    """Lazily import and return WorkOSAdapter class."""
    if not _check_workos_available():
        raise ImportError("WorkOS adapter requires asyncpg package")
    from .workos import WorkOSAdapter
    return WorkOSAdapter


def get_oura_adapter_class():
    """Lazily import and return OuraAdapter class."""
    if not _check_oura_available():
        raise ImportError("Oura adapter requires httpx package")
    from .oura import OuraAdapter
    return OuraAdapter


def get_neo4j_adapter_class():
    """Lazily import and return Neo4jAdapter class."""
    if not _check_neo4j_available():
        raise ImportError("Neo4j adapter requires neo4j package")
    from .neo4j_adapter import Neo4jAdapter
    return Neo4jAdapter


def get_chromadb_adapter_class():
    """Lazily import and return ChromaAdapter class."""
    if not _check_chromadb_available():
        raise ImportError("ChromaDB adapter requires chromadb package")
    from .chroma_adapter import ChromaAdapter
    return ChromaAdapter


def get_google_calendar_adapter_class():
    """Lazily import and return GoogleCalendarAdapter class."""
    if not _check_google_calendar_available():
        raise ImportError("Google Calendar adapter requires google-auth packages")
    from .google_calendar import GoogleCalendarAdapter
    return GoogleCalendarAdapter


def get_calendar_adapter_class():
    """Lazily import and return CalendarAdapter class."""
    if not _check_calendar_available():
        raise ImportError("Calendar adapter requires GoogleCalendarAdapter")
    from .calendar_adapter import CalendarAdapter
    return CalendarAdapter


# WorkOS Memory Bridge - lazy import wrapper
def _get_workos_memory_bridge():
    """Lazily import workos_memory_bridge module."""
    from . import workos_memory_bridge
    return workos_memory_bridge


def store_task_completion(*args, **kwargs):
    """Store task completion in memory (lazy import)."""
    return _get_workos_memory_bridge().store_task_completion(*args, **kwargs)


def store_decision(*args, **kwargs):
    """Store decision in memory (lazy import)."""
    return _get_workos_memory_bridge().store_decision(*args, **kwargs)


def write_to_queue(*args, **kwargs):
    """Write to memory queue (lazy import)."""
    return _get_workos_memory_bridge().write_to_queue(*args, **kwargs)


def process_queue(*args, **kwargs):
    """Process memory queue (lazy import)."""
    return _get_workos_memory_bridge().process_queue(*args, **kwargs)


# Calendar Memory Bridge - lazy import wrapper
def _get_calendar_memory_bridge():
    """Lazily import calendar_memory_bridge module."""
    from . import calendar_memory_bridge
    return calendar_memory_bridge


def extract_entities_from_event(*args, **kwargs):
    """Extract entities from calendar event (lazy import)."""
    return _get_calendar_memory_bridge().extract_entities_from_event(*args, **kwargs)


def prime_for_meeting(*args, **kwargs):
    """Prime memory for meeting (lazy import)."""
    return _get_calendar_memory_bridge().prime_for_meeting(*args, **kwargs)


def get_meeting_context(*args, **kwargs):
    """Get meeting context (lazy import)."""
    return _get_calendar_memory_bridge().get_meeting_context(*args, **kwargs)


def prime_upcoming_meetings(*args, **kwargs):
    """Prime upcoming meetings (lazy import)."""
    return _get_calendar_memory_bridge().prime_upcoming_meetings(*args, **kwargs)

__all__ = [
    # Base classes (always available)
    "BaseAdapter",
    "ToolResult",
    # Adapter classes (lazy-loaded via __getattr__)
    "WorkOSAdapter",
    "OuraAdapter",
    "Neo4jAdapter",
    "ChromaAdapter",
    "GoogleCalendarAdapter",
    "CalendarAdapter",
    # Manager
    "AdapterManager",
    "get_default_manager",
    "reset_default_manager",
    # Availability flags (lazy-evaluated via __getattr__)
    "WORKOS_AVAILABLE",
    "OURA_AVAILABLE",
    "NEO4J_AVAILABLE",
    "CHROMADB_AVAILABLE",
    "GOOGLE_CALENDAR_AVAILABLE",
    "CALENDAR_AVAILABLE",
    # Lazy import functions (explicit way to get adapter classes)
    "get_workos_adapter_class",
    "get_oura_adapter_class",
    "get_neo4j_adapter_class",
    "get_chromadb_adapter_class",
    "get_google_calendar_adapter_class",
    "get_calendar_adapter_class",
    # WorkOS Memory Bridge
    "store_task_completion",
    "store_decision",
    "write_to_queue",
    "process_queue",
    # Calendar Memory Bridge
    "extract_entities_from_event",
    "prime_for_meeting",
    "get_meeting_context",
    "prime_upcoming_meetings",
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


async def get_default_manager() -> AdapterManager:
    """
    Get or create the default adapter manager.

    This is the primary entry point for using the adapter system.
    Registers WorkOS and Oura adapters by default (if their dependencies are available).

    Returns:
        Configured AdapterManager instance
    """
    global _default_manager

    if _default_manager is None:
        _default_manager = AdapterManager()

        # Register WorkOS adapter if asyncpg is available
        if _check_workos_available():
            try:
                WorkOSAdapter = get_workos_adapter_class()
                _default_manager.register(WorkOSAdapter())
                logger.info("Registered WorkOS adapter")
            except Exception as e:
                logger.warning(f"Failed to register WorkOS adapter: {e}")
        else:
            logger.debug("WorkOS adapter not available (asyncpg not installed)")

        # Register Oura adapter if httpx is available
        if _check_oura_available():
            try:
                OuraAdapter = get_oura_adapter_class()
                _default_manager.register(OuraAdapter())
                logger.info("Registered Oura adapter")
            except Exception as e:
                logger.warning(f"Failed to register Oura adapter: {e}")
        else:
            logger.debug("Oura adapter not available (httpx not installed)")

        # Register Neo4j adapter if available and configured
        if _check_neo4j_available():
            try:
                Neo4jAdapter = get_neo4j_adapter_class()
                _default_manager.register(Neo4jAdapter())
                logger.info("Registered Neo4j adapter")
            except Exception as e:
                logger.warning(f"Failed to register Neo4j adapter: {e}")

        # Register ChromaDB adapter if available
        if _check_chromadb_available():
            try:
                ChromaAdapter = get_chromadb_adapter_class()
                _default_manager.register(ChromaAdapter())
                logger.info("Registered ChromaDB adapter")
            except Exception as e:
                logger.warning(f"Failed to register ChromaDB adapter: {e}")

        # Register Google Calendar adapter if available
        if _check_google_calendar_available():
            try:
                GoogleCalendarAdapter = get_google_calendar_adapter_class()
                _default_manager.register(GoogleCalendarAdapter())
                logger.info("Registered Google Calendar adapter")
            except Exception as e:
                logger.warning(f"Failed to register Google Calendar adapter: {e}")

        # Register unified Calendar adapter if available
        if _check_calendar_available():
            try:
                CalendarAdapter = get_calendar_adapter_class()
                _default_manager.register(CalendarAdapter())
                logger.info("Registered Calendar adapter")
            except Exception as e:
                logger.warning(f"Failed to register Calendar adapter: {e}")

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
