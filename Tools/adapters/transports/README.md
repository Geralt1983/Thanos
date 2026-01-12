# MCP Transport Layer

The transport layer provides abstraction for communicating with MCP servers via different protocols. This enables Thanos to connect to both local subprocess-based servers and remote network-based servers.

## Overview

The transport layer consists of:

- **Base Transport**: Abstract interface that all transports implement
- **Stdio Transport**: For subprocess-based local MCP servers (primary)
- **SSE Transport**: For remote MCP servers using Server-Sent Events
- **HTTP Transport**: (Future) For REST-style MCP servers

## Architecture

```
┌─────────────────┐
│   MCPBridge     │  ← High-level adapter interface
└────────┬────────┘
         │
         │ uses
         ▼
┌─────────────────┐
│   Transport     │  ← Abstract base class
│   (ABC)         │
└────────┬────────┘
         │
         ├─────────────────┐
         │                 │
         ▼                 ▼
┌─────────────────┐ ┌─────────────────┐
│ StdioTransport  │ │  SSETransport   │
│ (subprocess)    │ │  (HTTP/SSE)     │
└─────────────────┘ └─────────────────┘
```

## Transport Interface

All transports implement the `Transport` abstract base class:

```python
class Transport(ABC):
    @abstractmethod
    async def connect(self) -> AsyncIterator[tuple[Any, Any]]:
        """Establish connection and yield (read, write) streams"""
        pass

    @abstractmethod
    async def close(self):
        """Close connection and cleanup resources"""
        pass

    @property
    @abstractmethod
    def transport_type(self) -> str:
        """Return transport type identifier"""
        pass
```

## Stdio Transport

The stdio transport spawns MCP servers as subprocesses and communicates via stdin/stdout using JSON-RPC.

### Use Cases

- Local MCP servers (Node.js, Python, etc.)
- Development and testing
- Servers that don't require network access

### Configuration

```python
from mcp_config import StdioConfig

config = StdioConfig(
    command="node",              # Executable to run
    args=["./dist/index.js"],    # Command arguments
    env={                         # Environment variables
        "API_KEY": "secret",
        "DATABASE_URL": "postgresql://..."
    },
    cwd="/path/to/server"        # Working directory (optional)
)
```

### Example Usage

```python
from transports import StdioTransport
from mcp import ClientSession

transport = StdioTransport(config)

async with transport.connect() as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
```

### Implementation Details

- Uses `mcp.client.stdio.stdio_client` from MCP SDK
- Automatically merges environment variables with parent process
- Handles subprocess lifecycle (spawn and termination)
- Supports cross-platform (Windows, macOS, Linux)

## SSE Transport

The SSE transport connects to remote MCP servers via Server-Sent Events over HTTP/HTTPS.

### Use Cases

- Remote MCP servers hosted on the cloud
- Third-party MCP services
- Servers behind authentication/authorization

### Configuration

```python
from mcp_config import SSEConfig

config = SSEConfig(
    url="https://api.example.com/mcp",  # SSE endpoint
    headers={                            # HTTP headers
        "Authorization": "Bearer token",
        "X-Custom-Header": "value"
    },
    timeout=30,                          # Connection timeout (seconds)
    reconnect_interval=5                 # Reconnection interval (seconds)
)
```

### Example Usage

```python
from transports import SSETransport
from mcp import ClientSession

transport = SSETransport(config)

async with transport.connect() as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
```

### Implementation Details

- Uses `mcp.client.sse.sse_client` from MCP SDK
- Supports HTTPS with optional SSL verification
- Automatic reconnection on disconnect
- Custom header support for authentication

### Status

⚠️ **Scaffolded for Future Use**: The SSE transport is implemented and tested but awaiting real-world validation with remote MCP servers. Full integration testing will occur when remote servers become available.

## HTTP Transport

The HTTP transport will support REST-style MCP servers (future implementation).

### Status

📋 **Planned**: This transport is planned for a future phase when the MCP specification includes HTTP/REST support.

## Usage in MCPBridge

The MCPBridge automatically selects the appropriate transport based on configuration:

```python
from mcp_bridge import MCPBridge
from mcp_config import MCPServerConfig, StdioConfig

config = MCPServerConfig(
    name="my-server",
    transport=StdioConfig(command="node", args=["server.js"])
)

bridge = MCPBridge(config)
# Bridge automatically creates StdioTransport
```

The bridge handles:

- Transport creation via `_create_transport()`
- Connection establishment via `transport.connect()`
- Session management
- Error handling and logging

## Error Handling

All transports raise `TransportError` for transport-specific failures:

```python
from transports import TransportError

try:
    async with transport.connect() as (read, write):
        # Use connection
        pass
except TransportError as e:
    print(f"Transport failed: {e}")
```

Transport errors include:

- Connection failures
- Subprocess spawn errors
- Network timeouts
- Authentication failures (SSE/HTTP)

## Testing

Run the transport test suite:

```bash
python3 test_transports.py
```

This tests:

- ✓ Transport instantiation
- ✓ Configuration validation
- ✓ Health checks
- ✓ MCPBridge integration

## Adding New Transports

To add a new transport:

1. **Create transport class** inheriting from `Transport`
2. **Implement required methods**:
   - `transport_type` property
   - `connect()` context manager
   - `close()` method
3. **Add configuration model** in `mcp_config.py`
4. **Update MCPBridge** `_create_transport()` method
5. **Add to exports** in `__init__.py`
6. **Write tests** and documentation

Example skeleton:

```python
from .base import Transport, TransportError

class CustomTransport(Transport):
    def __init__(self, config: CustomConfig):
        super().__init__(config)
        self.config = config

    @property
    def transport_type(self) -> str:
        return "custom"

    @asynccontextmanager
    async def connect(self):
        # Establish connection
        try:
            read, write = await self._establish_connection()
            yield read, write
        finally:
            await self._cleanup()

    async def close(self):
        # Cleanup resources
        pass
```

## Best Practices

1. **Use context managers**: Always use `async with transport.connect()`
2. **Handle errors gracefully**: Catch `TransportError` and log appropriately
3. **Verify configuration**: Use Pydantic models for type safety
4. **Log connections**: Use debug logging for connection lifecycle
5. **Clean up resources**: Ensure proper cleanup in `close()`

## Future Enhancements

- [ ] Connection pooling for long-lived sessions
- [ ] Automatic reconnection with exponential backoff
- [ ] Transport middleware for logging/metrics
- [ ] WebSocket transport
- [ ] HTTP/REST transport
- [ ] Unix socket transport

## References

- [MCP Specification](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- `mcp_config.py` - Configuration schemas
- `mcp_bridge.py` - Bridge implementation
