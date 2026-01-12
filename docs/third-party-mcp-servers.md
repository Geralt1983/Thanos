# Third-Party MCP Server Integration

This guide covers how to integrate third-party MCP servers with Thanos, including configuration, setup, and usage examples for popular MCP servers.

## Table of Contents

- [Overview](#overview)
- [Supported Servers](#supported-servers)
- [Quick Start](#quick-start)
- [Server-Specific Guides](#server-specific-guides)
  - [Context7 - Documentation Search](#context7---documentation-search)
  - [Sequential Thinking - Advanced Reasoning](#sequential-thinking---advanced-reasoning)
  - [Filesystem - File Operations](#filesystem---file-operations)
  - [Playwright - Browser Automation](#playwright---browser-automation)
  - [Fetch - Web Content](#fetch---web-content)
- [Configuration Files](#configuration-files)
- [Troubleshooting](#troubleshooting)
- [Adding New Servers](#adding-new-servers)

---

## Overview

Thanos supports integration with third-party MCP servers through the MCP SDK. These servers provide specialized capabilities such as documentation search, browser automation, file operations, and more.

### Benefits

- **Extensibility**: Add new capabilities without modifying core code
- **Ecosystem**: Leverage the growing MCP server ecosystem
- **Standardization**: All servers use the same MCP protocol
- **Isolation**: Each server runs in its own process

### Architecture

```
Thanos AdapterManager
    ↓
MCPBridge (per server)
    ↓
Transport Layer (stdio/SSE/HTTP)
    ↓
Third-Party MCP Server
```

---

## Supported Servers

| Server | Transport | Use Case | Installation |
|--------|-----------|----------|--------------|
| **Context7** | SSE (HTTPS) | Documentation search, code context | API key required |
| **Sequential Thinking** | stdio | Advanced reasoning, structured thinking | npm package |
| **Filesystem** | stdio | File operations with access control | npm package |
| **Playwright** | stdio | Browser automation, web scraping | npm package |
| **Fetch** | stdio | Web content fetching, parsing | npm package |

---

## Quick Start

### 1. Install Prerequisites

For stdio-based servers (Sequential Thinking, Filesystem, Playwright, Fetch):
```bash
# Install Node.js if not already installed
# https://nodejs.org/

# Servers will be installed automatically via npx
# Or install globally:
npm install -g @modelcontextprotocol/server-sequential-thinking
npm install -g @modelcontextprotocol/server-filesystem
npm install -g @modelcontextprotocol/server-playwright
npm install -g @modelcontextprotocol/server-fetch
```

For SSE-based servers (Context7):
```bash
# Sign up for API key at https://context7.ai
export CONTEXT7_API_KEY="your-api-key"
```

### 2. Create Configuration

Create `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "context7": {
      "name": "context7",
      "type": "sse",
      "url": "https://api.context7.ai/mcp",
      "api_key": "${CONTEXT7_API_KEY}",
      "tags": ["documentation", "search"],
      "enabled": true
    },
    "sequential-thinking": {
      "name": "sequential-thinking",
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
      "tags": ["reasoning", "analysis"],
      "enabled": true
    },
    "filesystem": {
      "name": "filesystem",
      "type": "stdio",
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/you/Documents",
        "/Users/you/Projects"
      ],
      "tags": ["files", "storage"],
      "enabled": true
    }
  }
}
```

### 3. Use in Code

```python
from Tools.adapters.third_party_bridges import (
    create_context7_bridge,
    create_sequential_thinking_bridge,
    create_filesystem_bridge
)

# Create bridges
context7 = await create_context7_bridge()
sequential = await create_sequential_thinking_bridge()
filesystem = await create_filesystem_bridge(
    allowed_directories=["/Users/you/Documents"]
)

# Use the tools
# Context7 - Search documentation
result = await context7.call_tool("query-docs", {
    "libraryId": "/vercel/next.js",
    "query": "How to set up API routes"
})

# Sequential Thinking - Analyze problem
result = await sequential.call_tool("sequentialThinking", {
    "question": "What are the pros and cons of microservices?",
    "steps": 5
})

# Filesystem - List files
result = await filesystem.call_tool("list_directory", {
    "path": "/Users/you/Documents"
})
```

### 4. Or Use AdapterManager

```python
from Tools.adapters import get_default_manager

# Enable MCP support and auto-discover servers
manager = await get_default_manager(enable_mcp=True)

# Servers from .mcp.json are automatically registered
# Call tools directly
result = await manager.call_tool("query-docs", {
    "libraryId": "/vercel/next.js",
    "query": "authentication"
})
```

---

## Server-Specific Guides

### Context7 - Documentation Search

**Purpose**: Search documentation and get code context for popular libraries and frameworks.

**Transport**: SSE (Server-Sent Events) over HTTPS

**Setup**:
1. Sign up at https://context7.ai
2. Get your API key
3. Set environment variable: `export CONTEXT7_API_KEY="your-key"`

**Configuration**:
```python
from Tools.adapters.third_party_bridges import create_context7_config, create_context7_bridge

# Create config
config = create_context7_config(
    api_key="your-api-key",  # Or use env var
    tags=["documentation", "search"],
    enabled=True
)

# Create bridge
bridge = await create_context7_bridge(config)
```

**Available Tools**:
- `resolve-library-id`: Resolve library name to Context7 library ID
- `query-docs`: Search documentation for a library

**Example Usage**:
```python
# Resolve library
result = await bridge.call_tool("resolve-library-id", {
    "libraryName": "next.js",
    "query": "React framework for production"
})

# Query documentation
result = await bridge.call_tool("query-docs", {
    "libraryId": "/vercel/next.js",
    "query": "How to set up authentication with NextAuth.js"
})

print(result.data)  # Documentation snippets and examples
```

**Server-Specific Quirks**:
- Requires active internet connection
- API key must be valid and not expired
- Rate limiting may apply based on your plan
- Results are cached on Context7 side for common queries

**Troubleshooting**:
- **401 Unauthorized**: Check API key is correct and set in environment
- **429 Too Many Requests**: You've hit rate limits, wait before retrying
- **Connection Timeout**: Check internet connection and firewall settings

---

### Sequential Thinking - Advanced Reasoning

**Purpose**: Perform structured, step-by-step reasoning on complex questions.

**Transport**: stdio (subprocess)

**Setup**:
```bash
# No installation needed if using npx
# Or install globally:
npm install -g @modelcontextprotocol/server-sequential-thinking
```

**Configuration**:
```python
from Tools.adapters.third_party_bridges import create_sequential_thinking_bridge

# Create bridge (uses npx by default)
bridge = await create_sequential_thinking_bridge()

# Or with custom server path
bridge = await create_sequential_thinking_bridge(
    server_path="/path/to/sequential-thinking-server"
)
```

**Available Tools**:
- `sequentialThinking`: Perform multi-step reasoning on a question

**Example Usage**:
```python
# Analyze a complex question
result = await bridge.call_tool("sequentialThinking", {
    "question": "Should our company adopt microservices architecture?",
    "steps": 5  # Number of reasoning steps
})

print(result.data)
# Output: Step-by-step analysis with pros, cons, and recommendation
```

**Server-Specific Quirks**:
- Each call spawns a new thinking session
- More steps = more detailed analysis but slower response
- Results are deterministic for same inputs
- Process cleanup happens automatically

**Troubleshooting**:
- **Command not found**: Ensure Node.js and npm are installed
- **Slow responses**: Reduce number of steps or check system resources
- **Process hangs**: Set timeout in bridge configuration

---

### Filesystem - File Operations

**Purpose**: Read, write, and manage files with access control.

**Transport**: stdio (subprocess)

**Setup**:
```bash
# No installation needed if using npx
# Or install globally:
npm install -g @modelcontextprotocol/server-filesystem
```

**Configuration**:
```python
from Tools.adapters.third_party_bridges import create_filesystem_bridge

# Create bridge with allowed directories
bridge = await create_filesystem_bridge(
    allowed_directories=[
        "/Users/you/Documents",
        "/Users/you/Projects"
    ]
)

# Or use environment variable
# export FILESYSTEM_ALLOWED_DIRS="/path1,/path2"
bridge = await create_filesystem_bridge()
```

**Available Tools**:
- `read_file`: Read file contents
- `write_file`: Write or update file
- `list_directory`: List files in directory
- `create_directory`: Create new directory
- `move_file`: Move or rename file
- `search_files`: Search for files by pattern

**Example Usage**:
```python
# List files
result = await bridge.call_tool("list_directory", {
    "path": "/Users/you/Documents"
})

# Read file
result = await bridge.call_tool("read_file", {
    "path": "/Users/you/Documents/notes.txt"
})

# Write file
result = await bridge.call_tool("write_file", {
    "path": "/Users/you/Documents/output.txt",
    "content": "Hello, MCP!"
})

# Search files
result = await bridge.call_tool("search_files", {
    "path": "/Users/you/Projects",
    "pattern": "*.py",
    "recursive": True
})
```

**Server-Specific Quirks**:
- **Security**: Only allowed directories are accessible
- Attempts to access outside directories will fail
- Symlinks are followed (can escape allowed directories!)
- File operations are synchronous
- Large file reads may timeout

**Troubleshooting**:
- **Permission denied**: Check directory is in allowed list
- **Path not found**: Ensure path exists and is absolute
- **Operation timeout**: Increase timeout for large files
- **Symlink escape**: Be careful with symlinks pointing outside allowed dirs

---

### Playwright - Browser Automation

**Purpose**: Automate browser interactions for web scraping and testing.

**Transport**: stdio (subprocess)

**Setup**:
```bash
# Install globally
npm install -g @modelcontextprotocol/server-playwright

# Install browser binaries
npx playwright install
```

**Configuration**:
```python
from Tools.adapters.third_party_bridges import create_playwright_bridge

# Create bridge (headless by default)
bridge = await create_playwright_bridge(headless=True)

# Or with UI
bridge = await create_playwright_bridge(headless=False)
```

**Available Tools**:
- `playwright_navigate`: Navigate to URL
- `playwright_screenshot`: Take screenshot
- `playwright_click`: Click element
- `playwright_fill`: Fill form field
- `playwright_evaluate`: Execute JavaScript

**Example Usage**:
```python
# Navigate to page
result = await bridge.call_tool("playwright_navigate", {
    "url": "https://example.com"
})

# Take screenshot
result = await bridge.call_tool("playwright_screenshot", {
    "name": "example",
    "fullPage": True
})

# Click button
result = await bridge.call_tool("playwright_click", {
    "selector": "#submit-button"
})

# Fill form
result = await bridge.call_tool("playwright_fill", {
    "selector": "#email",
    "value": "test@example.com"
})

# Execute JavaScript
result = await bridge.call_tool("playwright_evaluate", {
    "script": "document.title"
})
```

**Server-Specific Quirks**:
- Browser state persists across calls within same session
- Headless mode is faster but can't debug visually
- Screenshots are base64 encoded
- Browser binaries must be installed via `playwright install`
- Timeouts are configurable but default to 30s

**Troubleshooting**:
- **Browser not found**: Run `npx playwright install`
- **Timeout on navigation**: Increase timeout or check network
- **Element not found**: Wait for element or check selector
- **Screenshot too large**: Use viewport size instead of fullPage

---

### Fetch - Web Content

**Purpose**: Fetch and parse web content.

**Transport**: stdio (subprocess)

**Setup**:
```bash
# No installation needed if using npx
# Or install globally:
npm install -g @modelcontextprotocol/server-fetch
```

**Configuration**:
```python
from Tools.adapters.third_party_bridges import create_fetch_bridge

# Create bridge
bridge = await create_fetch_bridge()

# Or with custom user agent
bridge = await create_fetch_bridge(
    user_agent="MyBot/1.0 (+https://example.com)"
)
```

**Available Tools**:
- `fetch`: Fetch URL and convert to markdown or text

**Example Usage**:
```python
# Fetch as markdown
result = await bridge.call_tool("fetch", {
    "url": "https://example.com",
    "format": "markdown"
})

# Fetch as text
result = await bridge.call_tool("fetch", {
    "url": "https://example.com/api/data",
    "format": "text"
})

print(result.data)  # Parsed content
```

**Server-Specific Quirks**:
- HTML is automatically converted to markdown
- JavaScript is not executed (use Playwright for that)
- Respects robots.txt by default
- User agent can be customized
- Large pages may timeout

**Troubleshooting**:
- **Blocked by server**: Set appropriate user agent
- **Timeout**: Increase timeout for slow sites
- **Malformed markdown**: Some HTML doesn't convert well
- **Redirect loops**: Check URL and server configuration

---

## Configuration Files

### .mcp.json Format

```json
{
  "mcpServers": {
    "server-name": {
      "name": "server-name",
      "type": "stdio|sse|http",
      "command": "command",
      "args": ["arg1", "arg2"],
      "env": {
        "VAR": "value"
      },
      "tags": ["tag1", "tag2"],
      "enabled": true
    }
  }
}
```

### ~/.claude.json Format (Claude Code)

```json
{
  "mcpServers": {
    "server-name": {
      "command": "command",
      "args": ["arg1"],
      "env": {
        "VAR": "value"
      }
    }
  }
}
```

### Generate Configuration Automatically

```python
from Tools.adapters.third_party_bridges import generate_third_party_mcp_json
from pathlib import Path

# Generate for all servers
config = generate_third_party_mcp_json(Path(".mcp.json"))

# Generate for specific servers only
config = generate_third_party_mcp_json(
    Path(".mcp.json"),
    enabled_servers=["context7", "filesystem", "playwright"]
)
```

---

## Troubleshooting

### Common Issues

#### 1. Server Won't Start

**Symptoms**: Bridge creation fails, timeout errors

**Solutions**:
- Check command path is correct
- Verify Node.js is installed: `node --version`
- Try running command manually: `npx -y @modelcontextprotocol/server-X`
- Check environment variables are set
- Look at logs for specific error messages

#### 2. Tools Not Available

**Symptoms**: Empty tool list, tools not found

**Solutions**:
- Ensure server started successfully
- Check capability negotiation completed
- Verify server supports expected tools
- Try refreshing tools: `await bridge.refresh_tools()`

#### 3. Authentication Failures

**Symptoms**: 401, 403 errors for SSE servers

**Solutions**:
- Verify API key is correct
- Check environment variable is set: `echo $API_KEY`
- Ensure key hasn't expired
- Check network/firewall allows HTTPS to server

#### 4. Performance Issues

**Symptoms**: Slow tool calls, timeouts

**Solutions**:
- Enable connection pooling for repeated calls
- Increase timeout in bridge configuration
- Use caching for repeated queries
- Check system resources (CPU, memory)
- Consider load balancing across multiple instances

#### 5. Permission Errors

**Symptoms**: Access denied, file not found

**Solutions**:
- Check allowed directories for filesystem server
- Verify file paths are absolute
- Ensure user has read/write permissions
- Check for symlinks escaping allowed paths

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now create bridges - you'll see detailed logs
bridge = await create_filesystem_bridge()
```

### Health Checks

Monitor server health:

```python
from Tools.adapters.mcp_health import HealthMonitor, HealthCheckConfig

# Create health monitor
monitor = HealthMonitor(
    server_config,
    health_config=HealthCheckConfig(
        check_interval=30.0,
        unhealthy_threshold=3
    )
)

await monitor.start()

# Check status
status = await monitor.get_health_status()
print(f"Server is {status.status.value}")
print(f"Success rate: {status.metrics.success_rate:.2%}")
```

---

## Adding New Servers

### Steps to Add a Third-Party Server

1. **Create Configuration Function**

```python
def create_myserver_config(
    option1: str,
    option2: Optional[str] = None,
    tags: Optional[List[str]] = None,
    enabled: bool = True
) -> MCPServerConfig:
    """Create configuration for MyServer MCP server."""
    return MCPServerConfig(
        name="myserver",
        description="What this server does",
        transport_type="stdio",  # or "sse"
        stdio=StdioConfig(
            command="npx",
            args=["-y", "@org/server-myserver"],
            env={"OPTION": option1}
        ),
        tags=tags or ["category1", "category2"],
        enabled=enabled
    )
```

2. **Create Bridge Factory Function**

```python
async def create_myserver_bridge(
    config: Optional[MCPServerConfig] = None,
    option1: Optional[str] = None
) -> Optional[MCPBridge]:
    """Create MCPBridge for MyServer."""
    if config is None:
        config = create_myserver_config(option1=option1)

    if not config or not config.enabled:
        return None

    try:
        bridge = MCPBridge(config)
        return bridge
    except Exception as e:
        logger.error(f"Failed to create MyServer bridge: {e}")
        return None
```

3. **Add to third_party_bridges.py**

4. **Document in this file** with:
   - Purpose and use cases
   - Installation instructions
   - Configuration examples
   - Available tools
   - Server-specific quirks
   - Troubleshooting tips

5. **Test the integration**

```python
# Test bridge creation
bridge = await create_myserver_bridge()
assert bridge is not None

# Test tool listing
tools = await bridge.list_tools()
assert len(tools) > 0

# Test tool calling
result = await bridge.call_tool("tool_name", {"arg": "value"})
assert result.success
```

### Server Discovery

Once added to `third_party_bridges.py`, the server can be discovered automatically:

```python
from Tools.adapters import get_default_manager

manager = await get_default_manager(enable_mcp=True)
# Your server will be auto-discovered from .mcp.json
```

---

## Best Practices

1. **Use environment variables** for sensitive data (API keys, tokens)
2. **Enable only needed servers** to reduce resource usage
3. **Set appropriate timeouts** based on expected response times
4. **Monitor health** for production servers
5. **Cache results** for frequently called tools
6. **Handle errors gracefully** with fallback strategies
7. **Document quirks** for your team in this file
8. **Test before deploying** to production
9. **Use connection pooling** for high-traffic scenarios
10. **Keep servers updated** to latest versions

---

## Resources

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Official MCP Servers](https://github.com/modelcontextprotocol/servers)
- [Context7 Documentation](https://context7.ai/docs)
- [Thanos MCP Integration Guide](./mcp-integration-guide.md)

---

## Support

For issues with:
- **Thanos integration**: Open issue on Thanos repository
- **Specific MCP server**: Check server's repository for issues
- **MCP SDK**: Check MCP Python SDK repository
- **This guide**: Submit PR with corrections/additions

---

**Last Updated**: 2026-01-11
**Version**: 1.0.0
