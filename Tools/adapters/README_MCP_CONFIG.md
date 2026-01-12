# MCP Configuration Schema

This document describes the MCP server configuration schema implemented in `mcp_config.py`.

## Overview

The MCP configuration system provides a flexible, validated way to configure MCP (Model Context Protocol) servers with support for:

- **Multiple transport types**: stdio (subprocess), SSE (Server-Sent Events), HTTP/HTTPS
- **Environment variable interpolation**: Automatic substitution of `${VAR}` and `$VAR` patterns
- **Pydantic validation**: Strong type checking and validation of all configuration values
- **Multiple configuration sources**: Load from `.claude.json`, `.mcp.json`, or programmatically

## Transport Types

### Stdio Transport

For MCP servers that run as subprocesses and communicate via stdin/stdout:

```python
from Tools.adapters.mcp_config import StdioConfig

config = StdioConfig(
    command="node",
    args=["/path/to/server.js"],
    env={"API_KEY": "${API_KEY}"},  # Environment variables interpolated
    cwd="/path/to/working/dir"
)
```

**Fields:**
- `type`: Always `"stdio"`
- `command`: Executable to run (e.g., `"node"`, `"python3"`, `"npx"`)
- `args`: List of command-line arguments
- `env`: Dictionary of environment variables (with interpolation support)
- `cwd`: Optional working directory (paths expanded automatically)

### SSE Transport

For MCP servers accessible via Server-Sent Events:

```python
from Tools.adapters.mcp_config import SSEConfig

config = SSEConfig(
    url="https://example.com/mcp/events",
    headers={"Authorization": "Bearer ${TOKEN}"},
    timeout=30,
    reconnect_interval=5
)
```

**Fields:**
- `type`: Always `"sse"`
- `url`: SSE endpoint URL (must start with `http://` or `https://`)
- `headers`: HTTP headers for the connection
- `timeout`: Connection timeout in seconds (1-300)
- `reconnect_interval`: Seconds to wait before reconnecting (1-60)

### HTTP Transport

For MCP servers accessible via HTTP/HTTPS:

```python
from Tools.adapters.mcp_config import HTTPConfig

config = HTTPConfig(
    type="http",  # or "https"
    url="https://example.com/mcp",
    headers={"X-API-Key": "${API_KEY}"},
    timeout=30,
    verify_ssl=True
)
```

**Fields:**
- `type`: Either `"http"` or `"https"`
- `url`: Base URL for the MCP endpoint
- `headers`: HTTP headers to include in requests
- `timeout`: Request timeout in seconds (1-300)
- `verify_ssl`: Whether to verify SSL certificates (default: `True`)

## Server Configuration

Complete MCP server configuration:

```python
from Tools.adapters.mcp_config import MCPServerConfig, StdioConfig

server = MCPServerConfig(
    name="my-server",
    description="My custom MCP server",
    transport=StdioConfig(command="node", args=["server.js"]),
    enabled=True,
    priority=10,
    tags=["custom", "production"],
    metadata={"version": "1.0.0"}
)
```

**Fields:**
- `name`: Unique server identifier (alphanumeric, underscore, hyphen only)
- `description`: Optional human-readable description
- `transport`: Transport configuration (StdioConfig, SSEConfig, or HTTPConfig)
- `enabled`: Whether the server is enabled (default: `True`)
- `priority`: Priority for load balancing, higher = higher priority (default: 0)
- `tags`: List of tags for categorization
- `metadata`: Additional arbitrary metadata

## Configuration Files

### .mcp.json Format

Project-specific configuration file:

```json
{
  "version": "1.0",
  "defaults": {
    "timeout": 30,
    "enabled": true
  },
  "servers": {
    "my-server": {
      "name": "my-server",
      "description": "Example server",
      "transport": {
        "type": "stdio",
        "command": "node",
        "args": ["server.js"],
        "env": {
          "API_KEY": "${API_KEY}"
        }
      },
      "enabled": true,
      "priority": 10,
      "tags": ["example"]
    }
  }
}
```

Load with:

```python
from Tools.adapters.mcp_config import load_mcp_json_config

config = load_mcp_json_config(".mcp.json")
servers = config.servers  # Dict of server name -> MCPServerConfig
```

### .claude.json Format

Load from Claude Code's global configuration:

```python
from Tools.adapters.mcp_config import load_claude_json_config

# Load global servers
servers = load_claude_json_config("~/.claude.json")

# Load project-specific servers
servers = load_claude_json_config(
    "~/.claude.json",
    project_path="/path/to/project"
)
```

The function automatically parses Claude's format and converts to `MCPServerConfig` objects.

## Environment Variable Interpolation

The configuration system automatically interpolates environment variables:

**Supported formats:**
- `${VAR}` - Braced format (recommended)
- `$VAR` - Bare format (word boundaries respected)

**Examples:**
```python
# Input:  "postgresql://${DB_USER}:${DB_PASS}@localhost/db"
# Output: "postgresql://admin:secret123@localhost/db"

# Input:  "$HOME/path/to/file"
# Output: "/Users/username/path/to/file"

# Input:  "prefix_${VALUE}_suffix"
# Output: "prefix_test_suffix"
```

**Note:** Undefined variables are replaced with empty strings.

## Merging Configurations

Combine multiple configuration sources:

```python
from Tools.adapters.mcp_config import merge_configs, load_mcp_json_config

# Load global and project configs
global_config = load_mcp_json_config(".mcp.json")
project_config = load_mcp_json_config(".mcp.local.json")

# Merge (project overrides global)
merged = merge_configs(global_config, project_config)
```

## Validation

All configurations are validated using Pydantic:

```python
from pydantic import ValidationError
from Tools.adapters.mcp_config import StdioConfig

try:
    config = StdioConfig(
        command="",  # Invalid: empty command
        args=[]
    )
except ValidationError as e:
    print(e.errors())
```

**Common validation errors:**
- Empty command for stdio transport
- Invalid URL format for HTTP/SSE
- Invalid server name (must be alphanumeric with hyphens/underscores)
- Timeout out of range (1-300 seconds)

## Complete Example

```python
from Tools.adapters.mcp_config import (
    MCPServerConfig,
    StdioConfig,
    load_claude_json_config,
    load_mcp_json_config,
    merge_configs
)

# Load from multiple sources
claude_servers = load_claude_json_config(
    "~/.claude.json",
    project_path="/Users/jeremy/Projects/Thanos"
)

project_config = load_mcp_json_config(".mcp.json")

# Create custom server
custom_server = MCPServerConfig(
    name="custom-server",
    transport=StdioConfig(
        command="python3",
        args=["server.py"],
        env={"API_KEY": "${MY_API_KEY}"}
    ),
    priority=15,
    tags=["custom"]
)

# Combine all sources
all_servers = {
    **claude_servers,
    **project_config.servers,
    "custom-server": custom_server
}

# Use the servers
for name, server in all_servers.items():
    if server.enabled:
        print(f"Server {name}: {server.transport.type}")
```

## Schema Reference

See `.mcp.json.example` for a complete example configuration file with all supported transport types.

## Testing

Run the configuration tests:

```bash
python3 test_mcp_config.py
```

This validates all features:
- Transport configuration (stdio, SSE, HTTP)
- Environment variable interpolation
- Configuration file loading
- Validation errors
- Configuration merging
