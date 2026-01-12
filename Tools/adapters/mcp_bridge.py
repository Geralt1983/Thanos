"""
MCP Bridge Adapter for Thanos.

Provides a bridge between Thanos and MCP (Model Context Protocol) servers,
enabling communication with third-party MCP tools via the official Python SDK.

This adapter supports multiple transport types (stdio, SSE, HTTP) and handles
the full MCP protocol lifecycle:
    initialize → list_tools → call_tool → shutdown
"""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Optional

from mcp import ClientSession
from mcp.types import Implementation, InitializeResult

from .base import BaseAdapter, ToolResult
from .mcp_capabilities import CapabilityManager, create_capability_manager
from .mcp_config import MCPServerConfig, SSEConfig, StdioConfig
from .mcp_observability import MCPLogger, get_metrics
from .transports import SSETransport, StdioTransport, Transport

logger = logging.getLogger(__name__)


class MCPBridge(BaseAdapter):
    """
    Bridge adapter that connects to MCP servers via multiple transport types.

    This adapter implements the BaseAdapter interface, making MCP servers
    accessible through the standard Thanos adapter system. It supports:
    - stdio: Subprocess-based servers (local)
    - SSE: Server-Sent Events (remote)
    - HTTP: Future support for REST-style MCP servers

    Lifecycle:
        1. Initialize: Connect via transport and negotiate capabilities
        2. List Tools: Query available tools from server
        3. Call Tool: Execute tools with arguments
        4. Shutdown: Clean up transport and connections

    Example:
        >>> from mcp_config import MCPServerConfig, StdioConfig
        >>> config = MCPServerConfig(
        ...     name="workos-mcp",
        ...     transport=StdioConfig(
        ...         command="node",
        ...         args=["./dist/index.js"],
        ...         env={"DATABASE_URL": "postgresql://..."}
        ...     )
        ... )
        >>> bridge = MCPBridge(config)
        >>> tools = bridge.list_tools()
        >>> result = await bridge.call_tool("get_tasks", {"status": "active"})
    """

    def __init__(self, server_config: MCPServerConfig):
        """
        Initialize the MCP bridge with a server configuration.

        Args:
            server_config: Configuration for the MCP server to bridge
        """
        self.config = server_config
        self._tools_cache: Optional[list[dict[str, Any]]] = None
        self._session_lock = asyncio.Lock()
        self._capability_manager = create_capability_manager()
        self._initialized = False
        self._transport: Optional[Transport] = None

        # Observability infrastructure
        self._mcp_logger = MCPLogger(server_config.name)
        self._metrics = get_metrics(server_config.name)

    @property
    def name(self) -> str:
        """Return the adapter/server name."""
        return self.config.name

    def _create_transport(self) -> Transport:
        """
        Create appropriate transport based on server configuration.

        Returns:
            Transport instance for the configured transport type

        Raises:
            ValueError: If transport type is not supported
        """
        if isinstance(self.config.transport, StdioConfig):
            return StdioTransport(self.config.transport)
        elif isinstance(self.config.transport, SSEConfig):
            return SSETransport(self.config.transport)
        else:
            # Future: Add HTTPConfig support
            raise ValueError(
                f"Unsupported transport type: {self.config.transport.type}"
            )

    @asynccontextmanager
    async def _get_session(self):
        """
        Create a new session with the MCP server.

        Establishes connection via the configured transport (stdio, SSE, etc.)
        and initializes the session with capability negotiation.

        Yields:
            ClientSession: Active MCP client session

        Raises:
            ValueError: If transport type is not supported
            RuntimeError: If session initialization fails
        """
        # Create transport instance
        transport = self._create_transport()

        # Log connection attempt
        transport_config = {
            "command": getattr(self.config.transport, "command", None),
            "transport": transport.transport_type,
        }
        self._mcp_logger.log_connection_attempt(transport_config)

        start_time = time.time()

        logger.debug(
            f"Connecting to MCP server '{self.name}' via {transport.transport_type}"
        )

        try:
            # Establish connection via transport
            async with transport.connect() as (read, write):
                # Create and initialize session with client info
                async with ClientSession(
                    read,
                    write,
                    client_info=Implementation(name="thanos", version="1.0.0"),
                ) as session:
                    # Initialize the session (capability negotiation)
                    result: InitializeResult = await session.initialize()

                    # Store server capabilities for feature detection
                    self._capability_manager.set_server_capabilities(result.capabilities)
                    self._initialized = True

                    # Calculate connection duration
                    duration = time.time() - start_time

                    # Record successful connection
                    self._metrics.record_connection_attempt(success=True)

                    # Count tools for logging
                    try:
                        tools_result = await session.list_tools()
                        tools_count = len(tools_result.tools)
                    except:
                        tools_count = 0

                    # Log successful connection
                    self._mcp_logger.log_connection_success(duration, tools_count)

                    logger.info(
                        f"MCP session initialized for '{self.name}' - "
                        f"Transport: {transport.transport_type}, "
                        f"Protocol version: {result.protocolVersion}"
                    )

                    # Log server info if available
                    if result.serverInfo:
                        logger.debug(
                            f"Server info: {result.serverInfo.name} "
                            f"v{result.serverInfo.version}"
                        )

                    # Log capabilities summary
                    cap_summary = self._capability_manager.get_capability_summary()
                    logger.debug(f"Capabilities for '{self.name}': {cap_summary}")

                    # Warn about missing capabilities
                    self._capability_manager.warn_if_no_tool_list_changed()

                    yield session

        except Exception as e:
            # Record failed connection
            duration = time.time() - start_time
            self._metrics.record_connection_attempt(success=False)
            self._mcp_logger.log_connection_failure(str(e), duration)
            self._metrics.record_error("server")

            logger.error(f"Failed to create MCP session for '{self.name}': {e}", exc_info=True)
            raise RuntimeError(f"MCP session creation failed: {e}") from e

    def list_tools(self) -> list[dict[str, Any]]:
        """
        Return list of available tools from the MCP server.

        This is a synchronous method that returns cached tools if available.
        Call refresh_tools() to update the cache from the server.

        Returns:
            List of tool definitions with name, description, and parameter schemas

        Note:
            If tools haven't been cached yet, this will run refresh_tools()
            synchronously using the current event loop.
        """
        if self._tools_cache is None:
            # Need to fetch tools - run async operation
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're already in an async context, we can't use run_until_complete
                    # Return empty list and log warning
                    logger.warning(
                        f"Tools not cached for '{self.name}' and cannot fetch "
                        "synchronously in running event loop. Call refresh_tools() first."
                    )
                    return []
                else:
                    loop.run_until_complete(self.refresh_tools())
            except RuntimeError:
                # No event loop available
                logger.warning(
                    f"Tools not cached for '{self.name}' and no event loop available. "
                    "Call refresh_tools() first."
                )
                return []

        return self._tools_cache or []

    async def refresh_tools(self) -> list[dict[str, Any]]:
        """
        Fetch and cache the tools list from the MCP server.

        Creates a new session, queries available tools, converts them to
        Thanos tool format, and caches the result.

        Returns:
            List of tool definitions

        Raises:
            RuntimeError: If tool fetching fails or tools not supported
        """
        async with self._session_lock:
            try:
                async with self._get_session() as session:
                    # Check if server supports tools
                    if self._initialized and not self._capability_manager.supports_tools():
                        logger.warning(
                            f"Server '{self.name}' does not advertise tools capability, "
                            "but attempting to list tools anyway"
                        )

                    logger.debug(f"Fetching tools from MCP server '{self.name}'")
                    result = await session.list_tools()

                    # Convert MCP tool format to Thanos tool format
                    self._tools_cache = [
                        {
                            "name": tool.name,
                            "description": tool.description or "",
                            "parameters": tool.inputSchema or {},
                        }
                        for tool in result.tools
                    ]

                    logger.info(
                        f"Cached {len(self._tools_cache)} tools from MCP server '{self.name}'"
                    )
                    return self._tools_cache

            except Exception as e:
                logger.error(
                    f"Failed to fetch tools from MCP server '{self.name}': {e}", exc_info=True
                )
                raise RuntimeError(f"Tool fetching failed: {e}") from e

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        """
        Execute a tool on the MCP server.

        Creates a new session, calls the specified tool with arguments,
        and returns the result in Thanos ToolResult format.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool parameters as dictionary

        Returns:
            ToolResult with success status and data/error

        Note:
            Each tool call creates a new session. For better performance with
            multiple calls, consider implementing connection pooling.
        """
        start_time = time.time()
        success = False

        try:
            # Check if server supports tools
            if self._initialized and not self._capability_manager.supports_tools():
                duration = time.time() - start_time
                self._metrics.record_tool_call(tool_name, success=False, duration=duration)
                self._mcp_logger.log_tool_call(tool_name, arguments, duration, success=False)

                return ToolResult.fail(
                    f"Server '{self.name}' does not support tools capability",
                    server=self.name,
                    tool=tool_name,
                )

            logger.debug(
                f"Calling tool '{tool_name}' on MCP server '{self.name}' "
                f"with arguments: {arguments}"
            )

            async with self._get_session() as session:
                # Call the tool on the MCP server
                result = await session.call_tool(tool_name, arguments or {})

                # Parse the result content
                if result.content and len(result.content) > 0:
                    # Extract content from first content item
                    content_item = result.content[0]

                    if hasattr(content_item, "text"):
                        # Text content - try to parse as JSON
                        text = content_item.text
                        try:
                            data = json.loads(text)
                        except json.JSONDecodeError:
                            # Not JSON, return as plain text
                            data = text
                    else:
                        # Other content types - convert to string
                        data = str(content_item)

                    # Check if result indicates an error
                    if result.isError:
                        duration = time.time() - start_time
                        self._metrics.record_tool_call(tool_name, success=False, duration=duration)
                        self._mcp_logger.log_tool_call(tool_name, arguments, duration, success=False)

                        return ToolResult.fail(
                            str(data),
                            server=self.name,
                            tool=tool_name,
                        )

                    # Success
                    success = True
                    duration = time.time() - start_time
                    self._metrics.record_tool_call(tool_name, success=True, duration=duration)
                    self._mcp_logger.log_tool_call(tool_name, arguments, duration, success=True)

                    return ToolResult.ok(
                        data,
                        server=self.name,
                        tool=tool_name,
                    )

                # No content returned
                duration = time.time() - start_time

                if result.isError:
                    self._metrics.record_tool_call(tool_name, success=False, duration=duration)
                    self._mcp_logger.log_tool_call(tool_name, arguments, duration, success=False)

                    return ToolResult.fail(
                        "Tool execution failed with no error message",
                        server=self.name,
                        tool=tool_name,
                    )

                # Success with no content
                success = True
                self._metrics.record_tool_call(tool_name, success=True, duration=duration)
                self._mcp_logger.log_tool_call(tool_name, arguments, duration, success=True)

                return ToolResult.ok(
                    None,
                    server=self.name,
                    tool=tool_name,
                )

        except Exception as e:
            duration = time.time() - start_time
            self._metrics.record_tool_call(tool_name, success=False, duration=duration)
            self._mcp_logger.log_tool_call(tool_name, arguments, duration, success=False)
            self._mcp_logger.log_error("tool_execution", str(e), {"tool": tool_name, "arguments": arguments})
            self._metrics.record_error("server")

            logger.error(
                f"Error calling tool '{tool_name}' on MCP server '{self.name}': {e}",
                exc_info=True,
            )
            return ToolResult.fail(
                f"Tool execution error: {e}",
                server=self.name,
                tool=tool_name,
            )

    def get_capabilities(self) -> dict[str, Any]:
        """
        Get capability information for this server.

        Returns:
            Dictionary with capability status and details

        Example:
            >>> capabilities = bridge.get_capabilities()
            >>> if capabilities["capabilities"]["tools"]["supported"]:
            ...     # Server supports tools
            ...     pass
        """
        return self._capability_manager.get_capability_summary()

    def supports_tools(self) -> bool:
        """
        Check if server supports tools.

        Returns:
            True if server advertised tools capability during initialization
        """
        return self._capability_manager.supports_tools()

    def supports_prompts(self) -> bool:
        """
        Check if server supports prompts.

        Returns:
            True if server advertised prompts capability during initialization
        """
        return self._capability_manager.supports_prompts()

    def supports_resources(self) -> bool:
        """
        Check if server supports resources.

        Returns:
            True if server advertised resources capability during initialization
        """
        return self._capability_manager.supports_resources()

    def is_initialized(self) -> bool:
        """
        Check if bridge has completed initialization.

        Returns:
            True if initialization and capability negotiation completed
        """
        return self._initialized

    async def close(self):
        """
        Close the adapter and clean up resources.

        Note:
            Each session is automatically closed after use via context managers,
            so this method primarily clears the tool cache and logs shutdown.
        """
        logger.info(f"Closing MCP bridge adapter '{self.name}'")
        self._metrics.record_connection_close()
        self._tools_cache = None
        self._initialized = False

    async def health_check(self) -> ToolResult:
        """
        Check adapter health by testing server connectivity.

        Creates a session and verifies that the MCP server responds to
        a list_tools request. Also includes capability information and metrics.

        Returns:
            ToolResult indicating health status with performance metrics
        """
        try:
            # Try to fetch tools as a health check
            async with self._get_session() as session:
                result = await session.list_tools()
                tool_count = len(result.tools)

                # Get performance metrics
                metrics_summary = self._metrics.get_summary()

                # Determine health status based on metrics
                error_rate = (
                    metrics_summary["tool_calls"]["failed"] / metrics_summary["tool_calls"]["total"]
                    if metrics_summary["tool_calls"]["total"] > 0
                    else 0.0
                )

                status = "healthy"
                if error_rate > 0.5:
                    status = "unhealthy"
                elif error_rate > 0.1:
                    status = "degraded"

                health_details = {
                    "status": status,
                    "adapter": self.name,
                    "transport": self.config.transport.type,
                    "tool_count": tool_count,
                    "initialized": self._initialized,
                    "capabilities": self._capability_manager.get_capability_summary(),
                    "metrics": metrics_summary,
                }

                self._mcp_logger.log_health_check(status, health_details)

                return ToolResult.ok(health_details)

        except Exception as e:
            self._mcp_logger.log_health_check("unhealthy", {"error": str(e)})
            return ToolResult.fail(
                f"Health check failed: {e}",
                adapter=self.name,
            )

    def get_performance_metrics(self) -> dict[str, Any]:
        """
        Get performance metrics for this MCP bridge.

        Returns:
            Dictionary with connection, tool call, and performance metrics

        Example:
            >>> metrics = bridge.get_performance_metrics()
            >>> print(f"Success rate: {metrics['tool_calls']['success_rate']:.1%}")
            >>> print(f"Avg call time: {metrics['performance']['avg_call_times']}")
        """
        return self._metrics.get_summary()


def create_mcp_bridge_from_config(config: MCPServerConfig) -> MCPBridge:
    """
    Factory function to create an MCPBridge from a server configuration.

    Args:
        config: MCP server configuration

    Returns:
        MCPBridge instance

    Example:
        >>> from mcp_discovery import get_server_config
        >>> config = get_server_config("workos-mcp")
        >>> if config:
        ...     bridge = create_mcp_bridge_from_config(config)
    """
    return MCPBridge(config)


async def create_bridges_from_discovery(
    project_root: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> dict[str, MCPBridge]:
    """
    Discover MCP servers and create bridge adapters for all enabled servers.

    Args:
        project_root: Root directory for project-specific config search
        tags: Optional tags to filter servers

    Returns:
        Dictionary mapping server names to MCPBridge instances

    Example:
        >>> bridges = await create_bridges_from_discovery()
        >>> for name, bridge in bridges.items():
        ...     print(f"Created bridge for: {name}")
        ...     tools = await bridge.refresh_tools()
    """
    from pathlib import Path

    from .mcp_discovery import discover_servers

    # Discover servers
    servers = discover_servers(
        project_root=Path(project_root) if project_root else None,
        tags=tags,
    )

    # Create bridges for all discovered servers
    bridges = {}
    for name, config in servers.items():
        try:
            bridge = create_mcp_bridge_from_config(config)
            bridges[name] = bridge
            logger.info(f"Created MCP bridge for server: {name}")
        except Exception as e:
            logger.warning(f"Failed to create bridge for server '{name}': {e}")

    return bridges
