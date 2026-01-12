"""
MCP Server Configuration Schema.

Provides Pydantic models for validating and managing MCP server configurations,
supporting multiple transport types and environment variable interpolation.
"""

import os
import re
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class TransportType(str, Enum):
    """Supported MCP transport types."""

    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"
    HTTPS = "https"


class StdioConfig(BaseModel):
    """Configuration for stdio transport (subprocess communication)."""

    type: Literal["stdio"] = Field(
        default="stdio", description="Transport type identifier"
    )
    command: str = Field(..., description="Command to execute (e.g., 'node', 'python3')")
    args: list[str] = Field(
        default_factory=list, description="Command line arguments"
    )
    env: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables for the subprocess",
    )
    cwd: Optional[str] = Field(
        None, description="Working directory for the subprocess"
    )

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: str) -> str:
        """Validate that command is not empty."""
        if not v or not v.strip():
            raise ValueError("Command cannot be empty")
        return v.strip()

    @field_validator("env")
    @classmethod
    def interpolate_env_vars(cls, v: dict[str, str]) -> dict[str, str]:
        """Interpolate environment variables in values."""
        return {key: _interpolate_env(value) for key, value in v.items()}

    @field_validator("cwd")
    @classmethod
    def expand_cwd(cls, v: Optional[str]) -> Optional[str]:
        """Expand ~ and environment variables in working directory path."""
        if v:
            return str(Path(_interpolate_env(v)).expanduser().resolve())
        return v


class SSEConfig(BaseModel):
    """Configuration for Server-Sent Events transport."""

    type: Literal["sse"] = Field(
        default="sse", description="Transport type identifier"
    )
    url: str = Field(..., description="SSE endpoint URL")
    headers: dict[str, str] = Field(
        default_factory=dict, description="HTTP headers for the connection"
    )
    timeout: int = Field(
        default=30, ge=1, le=300, description="Connection timeout in seconds"
    )
    reconnect_interval: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Reconnection interval in seconds on disconnect",
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v or not v.strip():
            raise ValueError("URL cannot be empty")
        v = v.strip()
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("headers")
    @classmethod
    def interpolate_headers(cls, v: dict[str, str]) -> dict[str, str]:
        """Interpolate environment variables in header values."""
        return {key: _interpolate_env(value) for key, value in v.items()}


class HTTPConfig(BaseModel):
    """Configuration for HTTP/HTTPS transport."""

    type: Literal["http", "https"] = Field(
        ..., description="Transport type identifier (http or https)"
    )
    url: str = Field(..., description="Base URL for the MCP HTTP endpoint")
    headers: dict[str, str] = Field(
        default_factory=dict, description="HTTP headers to include in requests"
    )
    timeout: int = Field(
        default=30, ge=1, le=300, description="Request timeout in seconds"
    )
    verify_ssl: bool = Field(
        default=True, description="Whether to verify SSL certificates"
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format and normalize."""
        if not v or not v.strip():
            raise ValueError("URL cannot be empty")
        v = v.strip()
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return v.rstrip("/")  # Remove trailing slash for consistency

    @field_validator("headers")
    @classmethod
    def interpolate_headers(cls, v: dict[str, str]) -> dict[str, str]:
        """Interpolate environment variables in header values."""
        return {key: _interpolate_env(value) for key, value in v.items()}

    @model_validator(mode="after")
    def validate_ssl_config(self) -> "HTTPConfig":
        """Warn if SSL verification is disabled for HTTPS."""
        if self.url.startswith("https://") and not self.verify_ssl:
            # Note: In production, we should log a warning here
            pass
        return self


# Union type for all transport configurations
TransportConfig = Union[StdioConfig, SSEConfig, HTTPConfig]


class MCPServerConfig(BaseModel):
    """Complete configuration for an MCP server."""

    name: str = Field(..., description="Unique identifier for this server")
    description: Optional[str] = Field(
        None, description="Human-readable description of the server"
    )
    transport: TransportConfig = Field(
        ..., description="Transport configuration", discriminator="type"
    )
    enabled: bool = Field(default=True, description="Whether this server is enabled")
    priority: int = Field(
        default=0,
        ge=0,
        description="Server priority for load balancing (higher = higher priority)",
    )
    tags: list[str] = Field(
        default_factory=list, description="Tags for categorizing servers"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate server name format."""
        if not v or not v.strip():
            raise ValueError("Server name cannot be empty")
        # Ensure name is safe for use as identifier
        if not re.match(r"^[a-z0-9][a-z0-9_-]*$", v.strip(), re.IGNORECASE):
            raise ValueError(
                "Server name must start with alphanumeric and contain only "
                "alphanumeric, underscore, or hyphen characters"
            )
        return v.strip()

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class MCPConfigFile(BaseModel):
    """Root configuration file structure for MCP servers."""

    servers: dict[str, MCPServerConfig] = Field(
        default_factory=dict, description="Map of server name to configuration"
    )
    version: str = Field(default="1.0", description="Configuration schema version")
    defaults: dict[str, Any] = Field(
        default_factory=dict, description="Default settings applied to all servers"
    )

    @model_validator(mode="after")
    def sync_server_names(self) -> "MCPConfigFile":
        """Ensure server names in dict keys match the name field."""
        for key, server_config in self.servers.items():
            if server_config.name != key:
                # Use the dict key as the canonical name
                server_config.name = key
        return self


def _interpolate_env(value: str) -> str:
    """
    Interpolate environment variables in a string.

    Supports both ${VAR} and $VAR syntax.
    Falls back to empty string if variable is not set.

    Examples:
        "${HOME}/path" -> "/Users/username/path"
        "$USER-data" -> "username-data"
    """
    if not isinstance(value, str):
        return value

    # Replace ${VAR} style
    def replace_braces(match: re.Match) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, "")

    value = re.sub(r"\$\{([^}]+)\}", replace_braces, value)

    # Replace $VAR style (word boundaries to avoid partial matches)
    def replace_bare(match: re.Match) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, "")

    value = re.sub(r"\$([A-Z_][A-Z0-9_]*)", replace_bare, value, flags=re.IGNORECASE)

    return value


def load_claude_json_config(
    claude_json_path: Union[str, Path] = "~/.claude.json",
    project_path: Optional[Union[str, Path]] = None,
) -> dict[str, MCPServerConfig]:
    """
    Load MCP server configurations from Claude's .claude.json file.

    Args:
        claude_json_path: Path to the .claude.json file
        project_path: Optional project path to load project-specific servers

    Returns:
        Dictionary mapping server names to MCPServerConfig objects

    Note:
        This function requires the actual .claude.json file to be present.
        It will return an empty dict if the file doesn't exist or is malformed.
    """
    import json

    claude_json_path = Path(claude_json_path).expanduser()

    if not claude_json_path.exists():
        return {}

    try:
        with open(claude_json_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

    servers = {}

    # Load project-specific servers if project path provided
    if project_path:
        project_path_str = str(Path(project_path).resolve())
        project_config = data.get("projects", {}).get(project_path_str, {})
        project_servers = project_config.get("mcpServers", {})

        for name, config in project_servers.items():
            servers[name] = _parse_claude_server_config(name, config)

    # Also load global servers (lower priority)
    global_servers = data.get("mcpServers", {})
    for name, config in global_servers.items():
        if name not in servers:  # Project servers take precedence
            servers[name] = _parse_claude_server_config(name, config)

    return servers


def _parse_claude_server_config(name: str, config: dict[str, Any]) -> MCPServerConfig:
    """
    Parse a server configuration from Claude's .claude.json format.

    Args:
        name: Server name
        config: Configuration dictionary from .claude.json

    Returns:
        MCPServerConfig object
    """
    transport_type = config.get("type", "stdio").lower()

    if transport_type == "stdio":
        transport = StdioConfig(
            command=config.get("command", ""),
            args=config.get("args", []),
            env=config.get("env", {}),
            cwd=config.get("cwd"),
        )
    elif transport_type in ("sse", "http", "https"):
        transport = HTTPConfig(
            type=transport_type,
            url=config.get("url", ""),
            headers=config.get("headers", {}),
            timeout=config.get("timeout", 30),
            verify_ssl=config.get("verify_ssl", True),
        )
    else:
        # Default to stdio for unknown types
        transport = StdioConfig(
            command=config.get("command", ""),
            args=config.get("args", []),
            env=config.get("env", {}),
        )

    return MCPServerConfig(
        name=name,
        description=config.get("description"),
        transport=transport,
        enabled=config.get("enabled", True),
        priority=config.get("priority", 0),
        tags=config.get("tags", []),
        metadata=config.get("metadata", {}),
    )


def load_mcp_json_config(config_path: Union[str, Path] = ".mcp.json") -> MCPConfigFile:
    """
    Load MCP configuration from a project-specific .mcp.json file.

    Args:
        config_path: Path to the .mcp.json file

    Returns:
        MCPConfigFile object with all server configurations

    Note:
        Returns empty configuration if file doesn't exist or is malformed.
    """
    import json

    config_path = Path(config_path)

    if not config_path.exists():
        return MCPConfigFile()

    try:
        with open(config_path) as f:
            data = json.load(f)
        return MCPConfigFile.model_validate(data)
    except (json.JSONDecodeError, IOError, ValueError):
        return MCPConfigFile()


def merge_configs(
    base_config: MCPConfigFile, override_config: MCPConfigFile
) -> MCPConfigFile:
    """
    Merge two MCP configurations, with override_config taking precedence.

    Args:
        base_config: Base configuration (e.g., global settings)
        override_config: Override configuration (e.g., project-specific)

    Returns:
        Merged MCPConfigFile
    """
    merged_servers = dict(base_config.servers)
    merged_servers.update(override_config.servers)

    merged_defaults = dict(base_config.defaults)
    merged_defaults.update(override_config.defaults)

    return MCPConfigFile(
        servers=merged_servers,
        version=override_config.version or base_config.version,
        defaults=merged_defaults,
    )
