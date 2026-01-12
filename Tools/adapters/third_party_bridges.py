"""
Third-party MCP Server Bridge Integration

This module provides factory functions and configuration helpers for integrating
popular third-party MCP servers with Thanos. It demonstrates how to create bridges
for various server types and handles server-specific quirks gracefully.

Supported Third-Party Servers:
- Context7: Documentation search and code context
- Sequential Thinking: Advanced reasoning and analysis
- Filesystem: File system operations
- Playwright: Browser automation
- Fetch: Web scraping and content fetching

Each server has its own factory function and configuration helper that
encapsulates server-specific setup requirements.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

# Import MCP infrastructure (graceful degradation if not available)
try:
    from Tools.adapters.mcp_bridge import MCPBridge
    from Tools.adapters.mcp_config import MCPServerConfig, StdioConfig, SSEConfig
    from Tools.adapters.mcp_discovery import MCPServerDiscovery
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

logger = logging.getLogger(__name__)


# ============================================================================
# Context7 MCP Server - Documentation Search
# ============================================================================

def create_context7_config(
    api_key: Optional[str] = None,
    tags: Optional[List[str]] = None,
    enabled: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Create configuration for Context7 MCP server.

    Context7 provides documentation search and code context for popular libraries.
    It's typically available via SSE transport over HTTPS.

    Args:
        api_key: Context7 API key (defaults to CONTEXT7_API_KEY env var)
        tags: Optional tags for server categorization
        enabled: Whether server is enabled (default: True)

    Returns:
        MCPServerConfig or dict if MCP infrastructure not available

    Environment Variables:
        CONTEXT7_API_KEY: API key for Context7 service
    """
    if not MCP_AVAILABLE:
        logger.warning("MCP infrastructure not available, returning config dict")
        return {
            "name": "context7",
            "type": "sse",
            "url": "https://api.context7.ai/mcp",
            "api_key": api_key or os.getenv("CONTEXT7_API_KEY", ""),
            "tags": tags or ["documentation", "search", "context"],
            "enabled": enabled
        }

    api_key = api_key or os.getenv("CONTEXT7_API_KEY")
    if not api_key:
        logger.warning("Context7 API key not provided. Set CONTEXT7_API_KEY environment variable.")

    return MCPServerConfig(
        name="context7",
        description="Documentation search and code context",
        transport_type="sse",
        sse=SSEConfig(
            url="https://api.context7.ai/mcp",
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {}
        ),
        tags=tags or ["documentation", "search", "context"],
        enabled=enabled and bool(api_key),
        metadata={
            "provider": "Context7",
            "website": "https://context7.ai",
            "tools": [
                "resolve-library-id",
                "query-docs"
            ]
        }
    )


async def create_context7_bridge(
    config: Optional[MCPServerConfig] = None,
    api_key: Optional[str] = None
) -> Optional['MCPBridge']:
    """
    Create an MCPBridge for Context7 server.

    Args:
        config: Optional pre-configured MCPServerConfig
        api_key: Context7 API key (if config not provided)

    Returns:
        MCPBridge instance or None if creation fails

    Example:
        ```python
        # With API key
        bridge = await create_context7_bridge(api_key="your-api-key")

        # With custom config
        config = create_context7_config(api_key="your-api-key")
        bridge = await create_context7_bridge(config)

        # Use the bridge
        result = await bridge.call_tool("query-docs", {
            "libraryId": "/vercel/next.js",
            "query": "How to set up API routes"
        })
        ```
    """
    if not MCP_AVAILABLE:
        logger.error("MCP infrastructure not available")
        return None

    if config is None:
        config = create_context7_config(api_key=api_key)

    if not config or not config.enabled:
        logger.warning("Context7 bridge not enabled or config invalid")
        return None

    try:
        bridge = MCPBridge(config)
        logger.info(f"Created Context7 bridge: {bridge.name}")
        return bridge
    except Exception as e:
        logger.error(f"Failed to create Context7 bridge: {e}")
        return None


# ============================================================================
# Sequential Thinking MCP Server - Advanced Reasoning
# ============================================================================

def create_sequential_thinking_config(
    server_path: Optional[str] = None,
    tags: Optional[List[str]] = None,
    enabled: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Create configuration for Sequential Thinking MCP server.

    Sequential Thinking provides advanced reasoning capabilities through
    structured thought processes.

    Args:
        server_path: Path to server executable (defaults to npx sequential-thinking)
        tags: Optional tags for server categorization
        enabled: Whether server is enabled (default: True)

    Returns:
        MCPServerConfig or dict if MCP infrastructure not available

    Environment Variables:
        SEQUENTIAL_THINKING_PATH: Custom path to server executable
    """
    if not MCP_AVAILABLE:
        logger.warning("MCP infrastructure not available, returning config dict")
        return {
            "name": "sequential-thinking",
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
            "tags": tags or ["reasoning", "analysis", "thinking"],
            "enabled": enabled
        }

    server_path = server_path or os.getenv("SEQUENTIAL_THINKING_PATH")

    # Default to npx for easy installation
    if server_path:
        command = server_path
        args = []
    else:
        command = "npx"
        args = ["-y", "@modelcontextprotocol/server-sequential-thinking"]

    return MCPServerConfig(
        name="sequential-thinking",
        description="Advanced reasoning and analysis with structured thinking",
        transport_type="stdio",
        stdio=StdioConfig(
            command=command,
            args=args,
            env={}
        ),
        tags=tags or ["reasoning", "analysis", "thinking"],
        enabled=enabled,
        metadata={
            "provider": "Model Context Protocol",
            "package": "@modelcontextprotocol/server-sequential-thinking",
            "install": "npm install -g @modelcontextprotocol/server-sequential-thinking",
            "tools": [
                "sequentialThinking"
            ]
        }
    )


async def create_sequential_thinking_bridge(
    config: Optional[MCPServerConfig] = None,
    server_path: Optional[str] = None
) -> Optional['MCPBridge']:
    """
    Create an MCPBridge for Sequential Thinking server.

    Args:
        config: Optional pre-configured MCPServerConfig
        server_path: Path to server executable (if config not provided)

    Returns:
        MCPBridge instance or None if creation fails

    Example:
        ```python
        # Default configuration
        bridge = await create_sequential_thinking_bridge()

        # Use the bridge
        result = await bridge.call_tool("sequentialThinking", {
            "question": "What are the pros and cons of microservices?",
            "steps": 5
        })
        ```
    """
    if not MCP_AVAILABLE:
        logger.error("MCP infrastructure not available")
        return None

    if config is None:
        config = create_sequential_thinking_config(server_path=server_path)

    if not config or not config.enabled:
        logger.warning("Sequential Thinking bridge not enabled or config invalid")
        return None

    try:
        bridge = MCPBridge(config)
        logger.info(f"Created Sequential Thinking bridge: {bridge.name}")
        return bridge
    except Exception as e:
        logger.error(f"Failed to create Sequential Thinking bridge: {e}")
        return None


# ============================================================================
# Filesystem MCP Server - File Operations
# ============================================================================

def create_filesystem_config(
    allowed_directories: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    enabled: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Create configuration for Filesystem MCP server.

    Provides file system operations with configurable directory access.

    Args:
        allowed_directories: List of directories to allow access (defaults to current dir)
        tags: Optional tags for server categorization
        enabled: Whether server is enabled (default: True)

    Returns:
        MCPServerConfig or dict if MCP infrastructure not available

    Environment Variables:
        FILESYSTEM_ALLOWED_DIRS: Comma-separated list of allowed directories
    """
    if not MCP_AVAILABLE:
        logger.warning("MCP infrastructure not available, returning config dict")
        allowed_dirs = allowed_directories or os.getenv("FILESYSTEM_ALLOWED_DIRS", os.getcwd()).split(",")
        return {
            "name": "filesystem",
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem"] + allowed_dirs,
            "tags": tags or ["files", "filesystem", "storage"],
            "enabled": enabled
        }

    # Get allowed directories
    if allowed_directories is None:
        env_dirs = os.getenv("FILESYSTEM_ALLOWED_DIRS")
        if env_dirs:
            allowed_directories = [d.strip() for d in env_dirs.split(",")]
        else:
            allowed_directories = [os.getcwd()]

    return MCPServerConfig(
        name="filesystem",
        description="File system operations with directory access control",
        transport_type="stdio",
        stdio=StdioConfig(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem"] + allowed_directories,
            env={}
        ),
        tags=tags or ["files", "filesystem", "storage"],
        enabled=enabled,
        metadata={
            "provider": "Model Context Protocol",
            "package": "@modelcontextprotocol/server-filesystem",
            "install": "npm install -g @modelcontextprotocol/server-filesystem",
            "allowed_directories": allowed_directories,
            "tools": [
                "read_file",
                "write_file",
                "list_directory",
                "create_directory",
                "move_file",
                "search_files"
            ]
        }
    )


async def create_filesystem_bridge(
    config: Optional[MCPServerConfig] = None,
    allowed_directories: Optional[List[str]] = None
) -> Optional['MCPBridge']:
    """
    Create an MCPBridge for Filesystem server.

    Args:
        config: Optional pre-configured MCPServerConfig
        allowed_directories: Directories to allow access (if config not provided)

    Returns:
        MCPBridge instance or None if creation fails

    Example:
        ```python
        # With allowed directories
        bridge = await create_filesystem_bridge(
            allowed_directories=["/Users/me/Documents", "/Users/me/Projects"]
        )

        # Use the bridge
        result = await bridge.call_tool("list_directory", {
            "path": "/Users/me/Documents"
        })
        ```
    """
    if not MCP_AVAILABLE:
        logger.error("MCP infrastructure not available")
        return None

    if config is None:
        config = create_filesystem_config(allowed_directories=allowed_directories)

    if not config or not config.enabled:
        logger.warning("Filesystem bridge not enabled or config invalid")
        return None

    try:
        bridge = MCPBridge(config)
        logger.info(f"Created Filesystem bridge: {bridge.name}")
        return bridge
    except Exception as e:
        logger.error(f"Failed to create Filesystem bridge: {e}")
        return None


# ============================================================================
# Playwright MCP Server - Browser Automation
# ============================================================================

def create_playwright_config(
    headless: bool = True,
    tags: Optional[List[str]] = None,
    enabled: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Create configuration for Playwright MCP server.

    Provides browser automation capabilities for web scraping and testing.

    Args:
        headless: Run browser in headless mode (default: True)
        tags: Optional tags for server categorization
        enabled: Whether server is enabled (default: True)

    Returns:
        MCPServerConfig or dict if MCP infrastructure not available

    Environment Variables:
        PLAYWRIGHT_HEADLESS: Set to "false" to run with UI
    """
    if not MCP_AVAILABLE:
        logger.warning("MCP infrastructure not available, returning config dict")
        return {
            "name": "playwright",
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-playwright"],
            "env": {"PLAYWRIGHT_HEADLESS": str(headless).lower()},
            "tags": tags or ["browser", "automation", "scraping"],
            "enabled": enabled
        }

    # Check environment variable
    if os.getenv("PLAYWRIGHT_HEADLESS", "").lower() == "false":
        headless = False

    return MCPServerConfig(
        name="playwright",
        description="Browser automation and web scraping",
        transport_type="stdio",
        stdio=StdioConfig(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-playwright"],
            env={"PLAYWRIGHT_HEADLESS": str(headless).lower()}
        ),
        tags=tags or ["browser", "automation", "scraping"],
        enabled=enabled,
        metadata={
            "provider": "Model Context Protocol",
            "package": "@modelcontextprotocol/server-playwright",
            "install": "npm install -g @modelcontextprotocol/server-playwright",
            "tools": [
                "playwright_navigate",
                "playwright_screenshot",
                "playwright_click",
                "playwright_fill",
                "playwright_evaluate"
            ]
        }
    )


async def create_playwright_bridge(
    config: Optional[MCPServerConfig] = None,
    headless: bool = True
) -> Optional['MCPBridge']:
    """
    Create an MCPBridge for Playwright server.

    Args:
        config: Optional pre-configured MCPServerConfig
        headless: Run in headless mode (if config not provided)

    Returns:
        MCPBridge instance or None if creation fails

    Example:
        ```python
        # Create bridge
        bridge = await create_playwright_bridge()

        # Navigate and screenshot
        await bridge.call_tool("playwright_navigate", {"url": "https://example.com"})
        result = await bridge.call_tool("playwright_screenshot", {"name": "example"})
        ```
    """
    if not MCP_AVAILABLE:
        logger.error("MCP infrastructure not available")
        return None

    if config is None:
        config = create_playwright_config(headless=headless)

    if not config or not config.enabled:
        logger.warning("Playwright bridge not enabled or config invalid")
        return None

    try:
        bridge = MCPBridge(config)
        logger.info(f"Created Playwright bridge: {bridge.name}")
        return bridge
    except Exception as e:
        logger.error(f"Failed to create Playwright bridge: {e}")
        return None


# ============================================================================
# Fetch MCP Server - Web Content Fetching
# ============================================================================

def create_fetch_config(
    user_agent: Optional[str] = None,
    tags: Optional[List[str]] = None,
    enabled: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Create configuration for Fetch MCP server.

    Provides web content fetching and parsing capabilities.

    Args:
        user_agent: Custom user agent string (optional)
        tags: Optional tags for server categorization
        enabled: Whether server is enabled (default: True)

    Returns:
        MCPServerConfig or dict if MCP infrastructure not available

    Environment Variables:
        FETCH_USER_AGENT: Custom user agent for requests
    """
    if not MCP_AVAILABLE:
        logger.warning("MCP infrastructure not available, returning config dict")
        ua = user_agent or os.getenv("FETCH_USER_AGENT", "")
        env = {"USER_AGENT": ua} if ua else {}
        return {
            "name": "fetch",
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-fetch"],
            "env": env,
            "tags": tags or ["web", "fetch", "scraping"],
            "enabled": enabled
        }

    user_agent = user_agent or os.getenv("FETCH_USER_AGENT")
    env = {"USER_AGENT": user_agent} if user_agent else {}

    return MCPServerConfig(
        name="fetch",
        description="Web content fetching and parsing",
        transport_type="stdio",
        stdio=StdioConfig(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-fetch"],
            env=env
        ),
        tags=tags or ["web", "fetch", "scraping"],
        enabled=enabled,
        metadata={
            "provider": "Model Context Protocol",
            "package": "@modelcontextprotocol/server-fetch",
            "install": "npm install -g @modelcontextprotocol/server-fetch",
            "tools": [
                "fetch"
            ]
        }
    )


async def create_fetch_bridge(
    config: Optional[MCPServerConfig] = None,
    user_agent: Optional[str] = None
) -> Optional['MCPBridge']:
    """
    Create an MCPBridge for Fetch server.

    Args:
        config: Optional pre-configured MCPServerConfig
        user_agent: Custom user agent (if config not provided)

    Returns:
        MCPBridge instance or None if creation fails

    Example:
        ```python
        # Create bridge
        bridge = await create_fetch_bridge()

        # Fetch web content
        result = await bridge.call_tool("fetch", {
            "url": "https://example.com",
            "format": "markdown"
        })
        ```
    """
    if not MCP_AVAILABLE:
        logger.error("MCP infrastructure not available")
        return None

    if config is None:
        config = create_fetch_config(user_agent=user_agent)

    if not config or not config.enabled:
        logger.warning("Fetch bridge not enabled or config invalid")
        return None

    try:
        bridge = MCPBridge(config)
        logger.info(f"Created Fetch bridge: {bridge.name}")
        return bridge
    except Exception as e:
        logger.error(f"Failed to create Fetch bridge: {e}")
        return None


# ============================================================================
# Multi-Server Management
# ============================================================================

def get_all_third_party_configs() -> Dict[str, Dict[str, Any]]:
    """
    Get configurations for all supported third-party MCP servers.

    Returns:
        Dictionary mapping server name to configuration

    Example:
        ```python
        configs = get_all_third_party_configs()
        for name, config in configs.items():
            print(f"Server: {name}")
            print(f"  Enabled: {config.get('enabled', False)}")
        ```
    """
    return {
        "context7": create_context7_config(),
        "sequential-thinking": create_sequential_thinking_config(),
        "filesystem": create_filesystem_config(),
        "playwright": create_playwright_config(),
        "fetch": create_fetch_config()
    }


async def create_all_third_party_bridges(
    enabled_only: bool = True
) -> Dict[str, Optional['MCPBridge']]:
    """
    Create bridges for all supported third-party MCP servers.

    Args:
        enabled_only: Only create bridges for enabled servers (default: True)

    Returns:
        Dictionary mapping server name to MCPBridge instance

    Example:
        ```python
        bridges = await create_all_third_party_bridges()
        for name, bridge in bridges.items():
            if bridge:
                tools = await bridge.list_tools()
                print(f"{name}: {len(tools)} tools available")
        ```
    """
    if not MCP_AVAILABLE:
        logger.error("MCP infrastructure not available")
        return {}

    configs = get_all_third_party_configs()
    bridges = {}

    for name, config in configs.items():
        if enabled_only and not config.get("enabled", False):
            logger.debug(f"Skipping disabled server: {name}")
            bridges[name] = None
            continue

        try:
            if name == "context7":
                bridges[name] = await create_context7_bridge(config)
            elif name == "sequential-thinking":
                bridges[name] = await create_sequential_thinking_bridge(config)
            elif name == "filesystem":
                bridges[name] = await create_filesystem_bridge(config)
            elif name == "playwright":
                bridges[name] = await create_playwright_bridge(config)
            elif name == "fetch":
                bridges[name] = await create_fetch_bridge(config)
        except Exception as e:
            logger.error(f"Failed to create bridge for {name}: {e}")
            bridges[name] = None

    return bridges


def generate_third_party_mcp_json(
    output_path: Optional[Path] = None,
    enabled_servers: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Generate .mcp.json configuration file for third-party servers.

    Args:
        output_path: Optional path to save the configuration
        enabled_servers: List of server names to enable (None = all)

    Returns:
        Dictionary containing the full configuration

    Example:
        ```python
        # Generate for all servers
        config = generate_third_party_mcp_json(Path(".mcp.json"))

        # Generate for specific servers only
        config = generate_third_party_mcp_json(
            Path(".mcp.json"),
            enabled_servers=["context7", "filesystem"]
        )
        ```
    """
    configs = get_all_third_party_configs()

    # Filter by enabled servers if specified
    if enabled_servers:
        configs = {
            name: config for name, config in configs.items()
            if name in enabled_servers
        }

    mcp_config = {
        "mcpServers": configs,
        "description": "Third-party MCP server configurations for Thanos"
    }

    # Save to file if path provided
    if output_path:
        import json
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(mcp_config, f, indent=2)
        logger.info(f"Saved third-party MCP configuration to {output_path}")

    return mcp_config


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Context7
    'create_context7_config',
    'create_context7_bridge',

    # Sequential Thinking
    'create_sequential_thinking_config',
    'create_sequential_thinking_bridge',

    # Filesystem
    'create_filesystem_config',
    'create_filesystem_bridge',

    # Playwright
    'create_playwright_config',
    'create_playwright_bridge',

    # Fetch
    'create_fetch_config',
    'create_fetch_bridge',

    # Multi-server
    'get_all_third_party_configs',
    'create_all_third_party_bridges',
    'generate_third_party_mcp_json',
]
