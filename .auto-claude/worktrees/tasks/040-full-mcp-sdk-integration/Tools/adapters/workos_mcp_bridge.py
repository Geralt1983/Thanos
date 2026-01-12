"""
WorkOS MCP Bridge - Reference Implementation

This module provides a reference implementation for bridging to the WorkOS MCP server.
It demonstrates how to create an MCPBridge instance for an existing MCP server and
provides convenient factory functions for integration with Thanos.

The WorkOS MCP server provides task management, habit tracking, and productivity
metrics from the Life OS database via the MCP protocol.

Usage:
    # Create bridge from environment configuration
    >>> bridge = await create_workos_mcp_bridge()
    >>> tools = bridge.list_tools()
    >>> result = await bridge.call_tool("get_tasks", {"status": "active"})

    # Create bridge with custom configuration
    >>> config = create_workos_mcp_config(
    ...     server_path="/custom/path/to/workos-mcp",
    ...     database_url="postgresql://..."
    ... )
    >>> bridge = MCPBridge(config)

    # Use with AdapterManager for automatic discovery
    >>> from Tools.adapters import get_default_manager
    >>> manager = await get_default_manager(enable_mcp=True)
    >>> # WorkOS MCP bridge automatically discovered from ~/.claude.json
    >>> result = await manager.call_tool("get_today_metrics")
"""

import logging
import os
from pathlib import Path
from typing import Optional

from .mcp_bridge import MCPBridge
from .mcp_config import MCPServerConfig, StdioConfig

logger = logging.getLogger(__name__)


# Default configuration constants
DEFAULT_SERVER_NAME = "workos-mcp"
DEFAULT_SERVER_DESCRIPTION = "WorkOS productivity database MCP server"
DEFAULT_SERVER_TAGS = ["productivity", "database", "workos", "tasks", "habits"]
DEFAULT_PRIORITY = 10


def get_default_server_path() -> str:
    """
    Get the default path to the WorkOS MCP server.

    Looks for the server in common locations:
    1. ${WORKOS_MCP_PATH} environment variable
    2. ${HOME}/Projects/Thanos/mcp-servers/workos-mcp/dist/index.js
    3. ./mcp-servers/workos-mcp/dist/index.js (relative to project root)

    Returns:
        Path to the WorkOS MCP server entry point

    Raises:
        ValueError: If server path cannot be determined
    """
    # 1. Check environment variable
    env_path = os.environ.get("WORKOS_MCP_PATH")
    if env_path:
        path = Path(env_path).expanduser().resolve()
        if path.exists():
            return str(path)
        logger.warning(f"WORKOS_MCP_PATH points to non-existent file: {path}")

    # 2. Check standard location (~/Projects/Thanos/mcp-servers/workos-mcp)
    home = Path.home()
    standard_path = home / "Projects" / "Thanos" / "mcp-servers" / "workos-mcp" / "dist" / "index.js"
    if standard_path.exists():
        return str(standard_path)

    # 3. Check relative to project root
    project_root = Path(__file__).parent.parent.parent
    relative_path = project_root / "mcp-servers" / "workos-mcp" / "dist" / "index.js"
    if relative_path.exists():
        return str(relative_path)

    # If not found, return the standard path with environment variable interpolation
    # This allows the configuration to work if the path is created later
    return "${HOME}/Projects/Thanos/mcp-servers/workos-mcp/dist/index.js"


def get_database_url() -> str:
    """
    Get the WorkOS database URL from environment variables.

    Checks in order:
    1. WORKOS_DATABASE_URL
    2. DATABASE_URL

    Returns:
        Database URL (may be unexpanded environment variable reference)

    Note:
        Returns "${WORKOS_DATABASE_URL}" if not found, allowing
        environment variable interpolation at runtime.
    """
    # Check for explicit WorkOS database URL
    if "WORKOS_DATABASE_URL" in os.environ:
        return os.environ["WORKOS_DATABASE_URL"]

    # Fall back to generic DATABASE_URL
    if "DATABASE_URL" in os.environ:
        return os.environ["DATABASE_URL"]

    # Return environment variable reference for later interpolation
    return "${WORKOS_DATABASE_URL}"


def create_workos_mcp_config(
    server_path: Optional[str] = None,
    database_url: Optional[str] = None,
    name: str = DEFAULT_SERVER_NAME,
    description: str = DEFAULT_SERVER_DESCRIPTION,
    tags: Optional[list[str]] = None,
    priority: int = DEFAULT_PRIORITY,
    enabled: bool = True,
) -> MCPServerConfig:
    """
    Create an MCPServerConfig for the WorkOS MCP server.

    Args:
        server_path: Path to workos-mcp/dist/index.js. If None, uses default location
        database_url: PostgreSQL connection string. If None, uses environment variables
        name: Server name (default: "workos-mcp")
        description: Server description
        tags: List of tags for filtering (default: ["productivity", "database", "workos", "tasks", "habits"])
        priority: Server priority for routing (default: 10)
        enabled: Whether server is enabled (default: True)

    Returns:
        Configured MCPServerConfig ready for MCPBridge instantiation

    Example:
        >>> config = create_workos_mcp_config()
        >>> bridge = MCPBridge(config)
    """
    # Use defaults if not provided
    if server_path is None:
        server_path = get_default_server_path()

    if database_url is None:
        database_url = get_database_url()

    if tags is None:
        tags = DEFAULT_SERVER_TAGS.copy()

    # Create stdio transport configuration
    transport = StdioConfig(
        type="stdio",
        command="node",
        args=[server_path],
        env={
            "WORKOS_DATABASE_URL": database_url,
            # Add NODE_ENV for better error messages in development
            "NODE_ENV": os.environ.get("NODE_ENV", "production"),
        },
    )

    # Create full server configuration
    config = MCPServerConfig(
        name=name,
        description=description,
        transport=transport,
        enabled=enabled,
        priority=priority,
        tags=tags,
    )

    logger.debug(
        f"Created WorkOS MCP config: name={name}, server_path={server_path}, "
        f"enabled={enabled}, tags={tags}"
    )

    return config


async def create_workos_mcp_bridge(
    config: Optional[MCPServerConfig] = None,
) -> MCPBridge:
    """
    Create and initialize a WorkOS MCP bridge.

    This is the recommended way to create a WorkOS MCP bridge instance.
    It creates the configuration if not provided and returns a ready-to-use bridge.

    Args:
        config: Optional pre-configured MCPServerConfig. If None, creates default config

    Returns:
        Initialized MCPBridge instance ready for tool calling

    Example:
        >>> bridge = await create_workos_mcp_bridge()
        >>> await bridge.refresh_tools()  # Optional: pre-fetch tools
        >>> result = await bridge.call_tool("get_tasks", {"status": "active"})
        >>> await bridge.close()

    Note:
        Remember to call bridge.close() when done, or use as async context manager:
        >>> async with await create_workos_mcp_bridge() as bridge:
        ...     result = await bridge.call_tool("get_tasks", {"status": "active"})
    """
    if config is None:
        config = create_workos_mcp_config()

    bridge = MCPBridge(config)

    logger.info(
        f"Created WorkOS MCP bridge: {bridge.name} "
        f"(transport: {config.transport.type})"
    )

    return bridge


def create_workos_mcp_bridge_sync(
    config: Optional[MCPServerConfig] = None,
) -> MCPBridge:
    """
    Create a WorkOS MCP bridge (synchronous factory).

    This is a synchronous version of create_workos_mcp_bridge() for use
    in non-async contexts. The bridge is created but not initialized.

    Args:
        config: Optional pre-configured MCPServerConfig. If None, creates default config

    Returns:
        MCPBridge instance (not yet initialized - call refresh_tools() before use)

    Example:
        >>> bridge = create_workos_mcp_bridge_sync()
        >>> # In async context:
        >>> await bridge.refresh_tools()
        >>> result = await bridge.call_tool("get_tasks", {"status": "active"})
    """
    if config is None:
        config = create_workos_mcp_config()

    bridge = MCPBridge(config)

    logger.info(
        f"Created WorkOS MCP bridge (sync): {bridge.name} "
        f"(transport: {config.transport.type})"
    )

    return bridge


# Convenience alias
create_bridge = create_workos_mcp_bridge_sync


__all__ = [
    "create_workos_mcp_config",
    "create_workos_mcp_bridge",
    "create_workos_mcp_bridge_sync",
    "create_bridge",
    "get_default_server_path",
    "get_database_url",
    "DEFAULT_SERVER_NAME",
    "DEFAULT_SERVER_DESCRIPTION",
    "DEFAULT_SERVER_TAGS",
    "DEFAULT_PRIORITY",
]
