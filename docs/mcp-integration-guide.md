# MCP Integration Guide

Comprehensive guide for using and configuring Model Context Protocol (MCP) servers in Thanos.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Common Use Cases](#common-use-cases)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Overview

### What is MCP?

The Model Context Protocol (MCP) is an open standard for connecting AI assistants to external data sources and tools. It enables:

- **Standardized Integration**: Unified interface for connecting to diverse services
- **Ecosystem Access**: Access to growing ecosystem of third-party MCP servers
- **Flexibility**: Support for both direct adapters and MCP bridges
- **Extensibility**: Easy to add new integrations without modifying core code

### MCP in Thanos

Thanos uses a **hybrid approach** combining two types of adapters:

1. **Direct Adapters**: Native Python implementations for core services (WorkOS, Oura, Neo4j, ChromaDB)
   - Better performance (no protocol overhead)
   - Tighter integration with Thanos systems
   - Full control over implementation

2. **MCP Bridges**: Protocol-based connections to MCP servers
   - Access to third-party ecosystem
   - Standardized interface
   - Easy to add new integrations
   - Language-agnostic (servers can be in any language)

The `AdapterManager` provides a **unified interface** that seamlessly routes requests to either adapter type.

## Architecture

### Component Layers

```
┌─────────────────────────────────────┐
│   Thanos Application Layer          │
│   (CommandRouter, CLI, etc.)        │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│      AdapterManager                 │
│  (Unified Tool Routing)             │
└─────┬──────────────────┬────────────┘
      │                  │
      │                  │
┌─────▼────────┐  ┌──────▼────────────┐
│ Direct       │  │  MCP Bridge       │
│ Adapters     │  │  Layer            │
│              │  │                   │
│ • WorkOS     │  │  • MCPBridge      │
│ • Oura       │  │  • Transport      │
│ • Neo4j      │  │  • Discovery      │
│ • ChromaDB   │  │  • Load Balance   │
└──────────────┘  └───────┬───────────┘
                          │
                    ┌─────▼──────────┐
                    │  MCP Servers   │
                    │                │
                    │ • Context7     │
                    │ • Sequential   │
                    │ • Magic        │
                    │ • Playwright   │
                    │ • Custom       │
                    └────────────────┘
```

### Key Components

#### MCPBridge

Core bridge implementation connecting to MCP servers:

```python
class MCPBridge(BaseAdapter):
    """
    Bridge to external MCP servers using official MCP SDK.

    Implements BaseAdapter interface for unified tool access.
    """
```

**Responsibilities**:
- Initialize MCP client with server configuration
- Establish stdio/SSE transport connection
- Negotiate capabilities with server
- Route tool calls through MCP protocol
- Handle errors and retries with circuit breaker
- Maintain connection pool for performance

#### MCPServerConfig

Configuration schema for MCP servers:

```python
@dataclass
class MCPServerConfig:
    name: str              # Unique server identifier
    command: str           # Command to start server (e.g., "npx", "python")
    args: List[str]        # Command arguments
    env: Dict[str, str]    # Environment variables
    transport: str         # "stdio" or "sse"
    description: str       # Human-readable description
```

#### Server Discovery

Automatic discovery and loading of MCP servers from configuration:

```python
async def discover_servers(
    config_path: Optional[str] = None
) -> List[MCPServerConfig]:
    """
    Discover MCP servers from configuration file.

    Default locations:
    1. config/mcp_servers.json
    2. ~/.config/thanos/mcp_servers.json
    3. /etc/thanos/mcp_servers.json
    """
```

## Quick Start

### Basic Usage

```python
from Tools.adapters import get_default_manager

# Get manager with MCP bridges enabled
manager = await get_default_manager(enable_mcp_bridges=True)

# Call tool (automatically routes to correct adapter)
result = await manager.call_tool("workos_get_today_metrics")

# Call with prefixed name for clarity
result = await manager.call_tool("workos.get_today_metrics")

# Cleanup
await manager.close_all()
```

### Using Specific Bridge

```python
from Tools.adapters.workos_mcp_bridge import WorkOSMCPBridge

# Create WorkOS bridge directly
bridge = WorkOSMCPBridge()
await bridge.connect()

# Call convenience methods
metrics = await bridge.get_today_metrics()
tasks = await bridge.get_tasks(status="active")

# Get performance stats
bridge.print_performance_report()

await bridge.close()
```

### Third-Party Servers

```python
from Tools.adapters.third_party_bridges import (
    Context7Bridge,
    MagicBridge,
    create_third_party_bridges,
    close_all_bridges
)

# Method 1: Individual bridges
context7 = Context7Bridge(api_key="your-key")
await context7.connect()

result = await context7.resolve_library_id("react")
await context7.close()

# Method 2: Create multiple bridges
bridges = await create_third_party_bridges(
    context7_key="your-key",
    magic_key="your-key"
)

try:
    # Use bridges
    result = await bridges["context7"].get_library_docs(...)
finally:
    await close_all_bridges(bridges)
```

## Configuration

### MCP Servers Configuration File

Create `config/mcp_servers.json`:

```json
{
  "mcpServers": {
    "workos": {
      "command": "uvx",
      "args": ["mcp-server-workos"],
      "env": {
        "DATABASE_URL": "postgresql://user:pass@localhost/workos"
      },
      "transport": "stdio",
      "description": "WorkOS personal assistant MCP server"
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@21st-dev/mcp-context7"],
      "env": {
        "CONTEXT7_API_KEY": "${CONTEXT7_API_KEY}"
      },
      "transport": "stdio",
      "description": "Context7 documentation search"
    },
    "sequential": {
      "command": "npx",
      "args": ["-y", "@sequentialread/mcp-sequential"],
      "env": {},
      "transport": "stdio",
      "description": "Sequential thinking and reasoning"
    }
  }
}
```

### Environment Variables

Use environment variables for sensitive configuration:

```bash
# .env file
DATABASE_URL=postgresql://user:pass@localhost/workos
CONTEXT7_API_KEY=your-context7-api-key
MAGIC_API_KEY=your-magic-api-key
```

Load in Python:

```python
from dotenv import load_dotenv
load_dotenv()

# Configuration will use environment variables
manager = await get_default_manager(enable_mcp_bridges=True)
```

### Transport Options

#### Stdio Transport (Default)

Standard input/output communication:

```json
{
  "transport": "stdio",
  "command": "npx",
  "args": ["-y", "@21st-dev/mcp-context7"]
}
```

**Pros**:
- Simple and reliable
- Works with any language
- No network configuration needed

**Cons**:
- One process per server
- No remote servers

#### SSE Transport

Server-Sent Events for HTTP-based communication:

```json
{
  "transport": "sse",
  "url": "http://localhost:3000/mcp",
  "headers": {
    "Authorization": "Bearer ${API_TOKEN}"
  }
}
```

**Pros**:
- Remote servers supported
- Multiple clients per server
- Better for long-running services

**Cons**:
- Requires HTTP server setup
- More complex configuration

## Common Use Cases

### Use Case 1: WorkOS Integration

Access WorkOS personal assistant data:

```python
manager = await get_default_manager(enable_mcp_bridges=True)

# Get today's metrics
metrics = await manager.call_tool("workos.get_today_metrics")
print(f"Points today: {metrics.data['pointsEarned']}")
print(f"Target: {metrics.data['dailyTarget']}")

# Get active tasks
tasks = await manager.call_tool("workos.get_tasks", {"status": "active"})
for task in tasks.data:
    print(f"- {task['title']} ({task['valueTier']})")

# Create new task
await manager.call_tool("workos.create_task", {
    "title": "Complete MCP integration",
    "category": "work",
    "clientId": 1,
    "valueTier": "deliverable"
})
```

### Use Case 2: Documentation Research

Look up official library documentation:

```python
from Tools.adapters.third_party_bridges import Context7Bridge

context7 = Context7Bridge(api_key="your-key")
await context7.connect()

# Find library
result = await context7.resolve_library_id("express")
library_id = result.data["id"]

# Get middleware documentation
docs = await context7.get_library_docs(
    library_id,
    topic="middleware"
)

print(docs.data)  # Official Express middleware docs

await context7.close()
```

### Use Case 3: UI Component Generation

Generate UI components with Magic:

```python
from Tools.adapters.third_party_bridges import MagicBridge

magic = MagicBridge(api_key="your-key")
await magic.connect()

# Generate button component
result = await magic.generate_component(
    description="Primary button with loading state and icon support",
    framework="react",
    design_system="tailwind"
)

# Save component code
component_code = result.data["code"]
with open("components/Button.tsx", "w") as f:
    f.write(component_code)

await magic.close()
```

### Use Case 4: Complex Problem Analysis

Use Sequential Thinking for structured reasoning:

```python
from Tools.adapters.third_party_bridges import SequentialThinkingBridge

sequential = SequentialThinkingBridge()
await sequential.connect()

# Analyze complex issue
result = await sequential.analyze_problem(
    problem="Users reporting intermittent 500 errors on login endpoint",
    context="Node.js API with PostgreSQL, deployed on Kubernetes"
)

# Get step-by-step analysis
analysis = result.data
print(analysis["hypothesis"])
print(analysis["investigation_steps"])
print(analysis["recommended_actions"])

await sequential.close()
```

### Use Case 5: Migration from Direct Adapter

Validate migration to MCP bridge:

```python
from Tools.adapters.mcp_migration import MigrationValidator
from Tools.adapters.workos import WorkOSAdapter
from Tools.adapters.workos_mcp_bridge import WorkOSMCPBridge

# Create both adapters
direct = WorkOSAdapter()
mcp = WorkOSMCPBridge()
await mcp.connect()

# Validate migration
validator = MigrationValidator()
report = await validator.validate_migration(
    direct_adapter=direct,
    mcp_bridge=mcp.bridge,
    test_cases={
        "get_today_metrics": {},
        "get_tasks": {"status": "active"},
        "get_clients": {}
    }
)

# Check if migration is safe
if report["migration_ready"]:
    print("✅ Migration validated. Safe to switch to MCP bridge.")
else:
    print("⚠️ Migration not ready:")
    for recommendation in report["recommendations"]:
        print(f"  {recommendation}")

await mcp.close()
await direct.close()
```

## API Reference

### AdapterManager

Main interface for unified adapter access.

#### Methods

**`register(adapter: BaseAdapter) -> None`**

Register an adapter (direct or MCP bridge).

```python
manager = AdapterManager()
manager.register(WorkOSAdapter())
manager.register(MCPBridge(config))
```

**`list_adapters() -> List[str]`**

Get list of registered adapter names.

**`get_adapter(name: str) -> Optional[BaseAdapter]`**

Get specific adapter by name.

**`list_all_tools() -> Dict[str, List[Dict[str, Any]]]`**

List all tools grouped by adapter.

**`list_tools_flat() -> List[Dict[str, Any]]`**

List all tools as flat list with adapter info.

**`async call_tool(tool_name: str, arguments: Optional[Dict] = None) -> ToolResult`**

Call a tool by name. Supports prefixed names (e.g., "workos.get_tasks") or short names if unique.

**`async call_multiple(calls: List[Dict]) -> List[ToolResult]`**

Execute multiple tool calls.

**`async health_check_all() -> Dict[str, ToolResult]`**

Run health checks on all adapters.

**`async close_all() -> None`**

Close all adapter connections.

### MCPBridge

Bridge to MCP servers.

#### Methods

**`__init__(config: MCPServerConfig)`**

Initialize bridge with server configuration.

**`async connect() -> None`**

Establish connection to MCP server.

**`async close() -> None`**

Close connection to MCP server.

**`list_tools() -> List[Dict[str, Any]]`**

List available tools from MCP server.

**`async call_tool(name: str, arguments: Optional[Dict] = None) -> ToolResult`**

Call tool on MCP server.

**`async health_check() -> ToolResult`**

Check connection health.

### Helper Functions

**`async get_default_manager(enable_mcp_bridges: bool = False) -> AdapterManager`**

Get or create default adapter manager. Registers all available adapters.

**`async discover_servers(config_path: Optional[str] = None) -> List[MCPServerConfig]`**

Discover MCP servers from configuration file.

**`async create_third_party_bridges(...) -> Dict[str, Any]`**

Create and connect multiple third-party bridges at once.

## Troubleshooting

### Server Won't Connect

**Symptom**: `ConnectionError` when calling `connect()`

**Common Causes**:
1. Server command not found in PATH
2. Missing Node.js/npm for npx-based servers
3. Invalid server configuration
4. Network issues (for SSE transport)

**Solutions**:

```bash
# Check if command exists
which npx
which uvx

# Test server manually
npx -y @21st-dev/mcp-context7

# Verify Node.js version
node --version  # Should be v18+

# Check configuration
python -c "from Tools.adapters.mcp_discovery import discover_servers; import asyncio; print(asyncio.run(discover_servers()))"
```

### Tool Calls Fail

**Symptom**: `ToolResult` with `success=False`

**Debug Steps**:

1. Check tool name is correct:
```python
tools = bridge.list_tools()
print([t["name"] for t in tools])
```

2. Verify arguments schema:
```python
tool = next(t for t in tools if t["name"] == "target-tool")
print(tool["inputSchema"])
```

3. Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

4. Test with minimal arguments:
```python
result = await bridge.call_tool("tool-name", {})
print(result.error)
```

### Performance Issues

**Symptom**: Slow tool calls (>2 seconds)

**Diagnostic Steps**:

```python
import time

start = time.time()
result = await bridge.call_tool("tool-name", args)
elapsed = time.time() - start

print(f"Call took {elapsed:.2f}s")
```

**Common Fixes**:

1. Use connection pooling (already enabled by default)
2. Enable caching for repeated calls
3. Batch multiple calls together
4. Consider using direct adapter for critical path

**Benchmark Comparison**:

```python
from Tools.adapters.mcp_migration import AdapterComparison
from Tools.adapters.workos import WorkOSAdapter
from Tools.adapters.workos_mcp_bridge import WorkOSMCPBridge

direct = WorkOSAdapter()
mcp = WorkOSMCPBridge()
await mcp.connect()

comparison = AdapterComparison(direct, mcp.bridge)

# Compare performance
for i in range(10):
    await comparison.validate_tool_parity("get_today_metrics")

# View timing stats
# Direct adapter: ~50ms
# MCP bridge: ~100ms (acceptable 2x overhead)
```

### Memory Leaks

**Symptom**: Memory usage grows over time

**Prevention**:

```python
# Always close connections
try:
    manager = await get_default_manager(enable_mcp_bridges=True)
    # Use manager
finally:
    await manager.close_all()  # Critical!

# Use context managers if available
async with create_bridge_context() as bridges:
    # Use bridges
    pass  # Automatic cleanup
```

### Configuration Not Found

**Symptom**: `FileNotFoundError` when discovering servers

**Solutions**:

1. Create configuration file:
```bash
mkdir -p config
cat > config/mcp_servers.json << 'EOF'
{
  "mcpServers": {}
}
EOF
```

2. Specify custom path:
```python
servers = await discover_servers(config_path="/custom/path/mcp_servers.json")
```

3. Disable auto-discovery and register manually:
```python
manager = AdapterManager()
manager.register(MCPBridge(manual_config))
```

## Best Practices

### 1. Connection Management

**Do:**
- Create bridges once, reuse for multiple calls
- Always close connections in finally blocks
- Use connection pooling (enabled by default)

**Don't:**
- Create new bridge for each call
- Leave connections open indefinitely
- Ignore connection errors

### 2. Error Handling

**Do:**
- Check `ToolResult.success` before using data
- Log errors with context
- Implement retries for transient failures
- Have fallback strategies

**Don't:**
- Assume calls always succeed
- Silently ignore errors
- Retry indefinitely without backoff

### 3. Performance

**Do:**
- Batch related operations
- Use caching for repeated queries
- Monitor performance metrics
- Benchmark critical paths

**Don't:**
- Make unnecessary tool calls
- Ignore slow operations
- Skip performance testing

### 4. Security

**Do:**
- Store API keys in environment variables
- Use minimal permissions for API keys
- Rotate API keys regularly
- Validate input before passing to tools

**Don't:**
- Commit API keys to source control
- Share API keys between environments
- Use root/admin API keys
- Trust user input without validation

### 5. Testing

**Do:**
- Test with real servers in development
- Use mocks for unit tests
- Validate tool schemas
- Monitor third-party server health

**Don't:**
- Skip integration tests
- Assume third-party servers are always available
- Test only happy paths
- Ignore edge cases

## Next Steps

- [Custom MCP Server Development Guide](./mcp-server-development.md)
- [Third-Party MCP Servers](./third-party-mcp-servers.md)
- [Migration Guide](./mcp-migration-checklist.md)
- [API Reference](./api-reference.md)
