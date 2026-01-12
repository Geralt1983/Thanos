"""
MCP Server Discovery Mechanism.

Discovers and loads MCP server configurations from various sources:
- Global ~/.claude.json configuration
- Project-specific .mcp.json files
- Environment-based overrides

Handles configuration merging and validation gracefully.
"""

import logging
from pathlib import Path
from typing import Any, Optional

from .mcp_config import (
    MCPConfigFile,
    MCPServerConfig,
    load_claude_json_config,
    load_mcp_json_config,
    merge_configs,
)

logger = logging.getLogger(__name__)


class MCPServerDiscovery:
    """
    Discovers and manages MCP server configurations from multiple sources.

    Discovery order (later sources override earlier ones):
    1. Global ~/.claude.json configuration
    2. Project-specific .mcp.json in parent directories (walking up)
    3. Local .mcp.json in current directory
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        global_config_path: Optional[Path] = None,
    ):
        """
        Initialize server discovery.

        Args:
            project_root: Root directory for project-specific config search.
                         Defaults to current working directory.
            global_config_path: Path to global configuration file.
                               Defaults to ~/.claude.json
        """
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self.global_config_path = Path(
            global_config_path or Path.home() / ".claude.json"
        )
        self._discovered_servers: dict[str, MCPServerConfig] = {}
        self._config_sources: list[Path] = []

    def discover_servers(
        self,
        include_disabled: bool = False,
        tags: Optional[list[str]] = None,
    ) -> dict[str, MCPServerConfig]:
        """
        Discover all MCP servers from configured sources.

        Args:
            include_disabled: If True, include servers marked as disabled
            tags: If provided, only return servers with at least one matching tag

        Returns:
            Dictionary mapping server names to their configurations
        """
        self._discovered_servers = {}
        self._config_sources = []

        # 1. Load global ~/.claude.json configuration
        self._load_global_config()

        # 2. Load project-specific configurations (walk up directory tree)
        self._load_project_configs()

        # Filter servers based on criteria
        filtered_servers = self._filter_servers(
            self._discovered_servers,
            include_disabled=include_disabled,
            tags=tags,
        )

        logger.info(
            f"Discovered {len(filtered_servers)} MCP servers from {len(self._config_sources)} sources"
        )

        return filtered_servers

    def _load_global_config(self) -> None:
        """Load global configuration from ~/.claude.json."""
        try:
            if not self.global_config_path.exists():
                logger.debug(
                    f"Global config not found at {self.global_config_path}, skipping"
                )
                return

            # Load servers from Claude's config format
            servers = load_claude_json_config(
                claude_json_path=self.global_config_path,
                project_path=str(self.project_root),
            )

            if servers:
                self._discovered_servers.update(servers)
                self._config_sources.append(self.global_config_path)
                logger.debug(
                    f"Loaded {len(servers)} servers from global config: {self.global_config_path}"
                )
            else:
                logger.debug(f"No servers found in global config: {self.global_config_path}")

        except Exception as e:
            logger.warning(
                f"Failed to load global config from {self.global_config_path}: {e}",
                exc_info=True,
            )

    def _load_project_configs(self) -> None:
        """
        Load project-specific .mcp.json files.

        Walks up the directory tree from project_root to find .mcp.json files.
        Closer files override settings from parent directories.
        """
        # Collect all .mcp.json files from current directory up to root
        config_files = self._find_project_configs()

        # Load in order from root to current (so closer configs override)
        for config_file in config_files:
            try:
                config = load_mcp_json_config(config_file)

                if config.servers:
                    # Project configs override global
                    self._discovered_servers.update(config.servers)
                    self._config_sources.append(config_file)
                    logger.debug(
                        f"Loaded {len(config.servers)} servers from project config: {config_file}"
                    )
                else:
                    logger.debug(f"No servers found in project config: {config_file}")

            except Exception as e:
                logger.warning(
                    f"Failed to load project config from {config_file}: {e}",
                    exc_info=True,
                )

    def _find_project_configs(self) -> list[Path]:
        """
        Find all .mcp.json files from project root up to filesystem root.

        Returns:
            List of config file paths, ordered from root to current directory
        """
        config_files = []
        current = self.project_root

        # Walk up directory tree
        max_depth = 10  # Prevent infinite loops
        depth = 0

        while depth < max_depth:
            config_file = current / ".mcp.json"
            if config_file.exists() and config_file.is_file():
                config_files.append(config_file)

            # Stop at filesystem root or home directory
            parent = current.parent
            if parent == current or current == Path.home().parent:
                break

            current = parent
            depth += 1

        # Reverse so configs closer to project root come last (and override)
        return list(reversed(config_files))

    def _filter_servers(
        self,
        servers: dict[str, MCPServerConfig],
        include_disabled: bool = False,
        tags: Optional[list[str]] = None,
    ) -> dict[str, MCPServerConfig]:
        """
        Filter servers based on criteria.

        Args:
            servers: Server configurations to filter
            include_disabled: If True, include disabled servers
            tags: If provided, only include servers with at least one matching tag

        Returns:
            Filtered server configurations
        """
        filtered = {}

        for name, config in servers.items():
            # Skip disabled servers unless explicitly included
            if not config.enabled and not include_disabled:
                logger.debug(f"Skipping disabled server: {name}")
                continue

            # Filter by tags if specified
            if tags:
                if not any(tag in config.tags for tag in tags):
                    logger.debug(
                        f"Skipping server {name}: tags {config.tags} don't match {tags}"
                    )
                    continue

            filtered[name] = config

        return filtered

    def get_server(self, name: str) -> Optional[MCPServerConfig]:
        """
        Get a specific server configuration by name.

        Args:
            name: Server name to look up

        Returns:
            Server configuration if found, None otherwise
        """
        return self._discovered_servers.get(name)

    def get_servers_by_tag(self, tag: str) -> dict[str, MCPServerConfig]:
        """
        Get all servers with a specific tag.

        Args:
            tag: Tag to filter by

        Returns:
            Dictionary of servers with the specified tag
        """
        return {
            name: config
            for name, config in self._discovered_servers.items()
            if tag in config.tags
        }

    def get_config_sources(self) -> list[Path]:
        """
        Get list of configuration file paths that were loaded.

        Returns:
            List of Path objects for loaded configuration files
        """
        return list(self._config_sources)

    def reload(self) -> dict[str, MCPServerConfig]:
        """
        Reload all server configurations from sources.

        Returns:
            Updated dictionary of server configurations
        """
        logger.info("Reloading MCP server configurations")
        return self.discover_servers()


def discover_servers(
    project_root: Optional[Path] = None,
    global_config_path: Optional[Path] = None,
    include_disabled: bool = False,
    tags: Optional[list[str]] = None,
) -> dict[str, MCPServerConfig]:
    """
    Convenience function to discover MCP servers.

    Args:
        project_root: Root directory for project-specific config search
        global_config_path: Path to global configuration file
        include_disabled: If True, include disabled servers
        tags: If provided, only return servers with at least one matching tag

    Returns:
        Dictionary mapping server names to their configurations

    Example:
        >>> servers = discover_servers(tags=["productivity"])
        >>> for name, config in servers.items():
        ...     print(f"Found server: {name}")
    """
    discovery = MCPServerDiscovery(
        project_root=project_root,
        global_config_path=global_config_path,
    )
    return discovery.discover_servers(include_disabled=include_disabled, tags=tags)


def get_server_config(
    server_name: str,
    project_root: Optional[Path] = None,
    global_config_path: Optional[Path] = None,
) -> Optional[MCPServerConfig]:
    """
    Get configuration for a specific MCP server.

    Args:
        server_name: Name of the server to look up
        project_root: Root directory for project-specific config search
        global_config_path: Path to global configuration file

    Returns:
        Server configuration if found, None otherwise

    Example:
        >>> config = get_server_config("workos-mcp")
        >>> if config:
        ...     print(f"Command: {config.transport.command}")
    """
    discovery = MCPServerDiscovery(
        project_root=project_root,
        global_config_path=global_config_path,
    )
    discovery.discover_servers(include_disabled=True)  # Include all for lookup
    return discovery.get_server(server_name)
