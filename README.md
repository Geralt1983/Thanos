# Thanos

Thanos is an AI-powered orchestration system that enables seamless integration with external services and APIs through a unified adapter framework.

## Features

- **Unified Adapter Framework**: Consistent interface for integrating with external services
- **Direct Adapters**: Native Python adapters for WorkOS, Oura, Neo4j, ChromaDB, and more
- **Full MCP SDK Integration**: Connect to any MCP-compatible server for maximum flexibility
- **Intelligent Orchestration**: Smart routing and execution of commands across adapters
- **Advanced Features**: Connection pooling, health monitoring, caching, load balancing
- **Type-Safe Configuration**: Pydantic-based configuration with validation

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/thanos.git
cd thanos

# Install dependencies (including MCP SDK)
pip install -r requirements.txt
```

### Basic Usage

```python
from Tools.adapters import get_default_manager

# Initialize adapter manager with MCP support
manager = get_default_manager(enable_mcp=True)

# Discover and register MCP servers from ~/.claude.json
await manager.discover_and_register_mcp_servers()

# List all available tools (both direct adapters and MCP servers)
tools = await manager.list_tools()

# Call a tool (automatically routed to correct adapter)
result = await manager.call_tool("tool_name", {"arg": "value"})
```

## Model Context Protocol (MCP) Integration

Thanos includes **full MCP SDK integration**, enabling connection to any MCP-compatible server. This opens up the entire MCP ecosystem to Thanos.

### What is MCP?

The Model Context Protocol (MCP) is an open standard for connecting AI systems to external data sources and tools. It enables:

- **Third-Party Server Integration**: Connect to any MCP-compatible server
- **Ecosystem Expansion**: Access to growing MCP ecosystem (filesystem, databases, APIs, etc.)
- **Custom Server Development**: Build your own MCP servers for specific needs
- **Protocol Compliance**: Full support for MCP specification

### Key MCP Capabilities

✅ **Full Protocol Support**
- Complete MCP SDK protocol compliance
- Capability negotiation with servers
- Support for stdio, SSE, and HTTP transports
- Session management and lifecycle control

✅ **Advanced Features**
- **Connection Pooling**: Efficient long-lived session management
- **Health Monitoring**: Automatic server health checks with performance metrics
- **Intelligent Caching**: TTL-based result caching with multiple invalidation strategies
- **Load Balancing**: Multiple strategies (round-robin, least-connections, health-aware)
- **Error Handling**: Comprehensive retry logic with exponential backoff and circuit breaker

✅ **Third-Party Server Support**
Pre-configured bridges for popular MCP servers:
- **Context7**: Documentation search and code context
- **Sequential Thinking**: Advanced reasoning with structured thinking
- **Filesystem**: File operations with access control
- **Playwright**: Browser automation and web scraping
- **Fetch**: Web content fetching and parsing

### Quick MCP Setup

1. **Install MCP SDK** (if not already installed):
   ```bash
   pip install mcp>=1.0.0
   ```

2. **Configure MCP Servers** (create `.mcp.json` in your project or `~/.claude.json`):
   ```json
   {
     "mcpServers": {
       "filesystem": {
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"],
         "enabled": true
       },
       "context7": {
         "url": "https://context7.example.com/mcp",
         "transport": "sse",
         "headers": {
           "Authorization": "Bearer ${CONTEXT7_API_KEY}"
         },
         "enabled": true
       }
     }
   }
   ```

3. **Use MCP Servers**:
   ```python
   from Tools.adapters import get_default_manager

   # Enable MCP support
   manager = get_default_manager(enable_mcp=True)

   # Auto-discover from config files
   await manager.discover_and_register_mcp_servers()

   # Use tools from MCP servers
   result = await manager.call_tool("read_file", {"path": "/path/to/file.txt"})
   ```

### Documentation

#### Core Documentation
- **[Agent Routing Algorithm](docs/agent-routing.md)**: Comprehensive guide to the intelligent agent routing system
  - Routing algorithm and scoring system
  - Complete keyword reference (92 keywords)
  - Performance optimization details
  - Developer guides for customization
  - Troubleshooting and FAQ

#### MCP Documentation
- **[MCP Integration Guide](docs/mcp-integration-guide.md)**: Complete guide for using MCP in Thanos
- **[Custom MCP Server Guide](docs/custom-mcp-server-guide.md)**: Build your own MCP servers
- **[MCP Server Development](docs/mcp-server-development.md)**: Advanced MCP server development
- **[Third-Party MCP Servers](docs/third-party-mcp-servers.md)**: Pre-configured third-party servers
- **[MCP Implementation Details](MCP.md)**: Technical implementation overview

#### System Architecture
- **[Architecture Documentation](docs/architecture.md)**: System architecture with MCP

## Architecture

Thanos uses a modular architecture with:

- **Adapter Layer**: Unified interface for all integrations (direct + MCP)
- **Orchestration Layer**: Smart routing and execution
- **MCP Bridge Layer**: Protocol-compliant MCP client implementation
- **Transport Layer**: Support for stdio, SSE, and HTTP
- **Advanced Features**: Pooling, caching, monitoring, load balancing

See [Architecture Documentation](docs/architecture.md) for detailed diagrams and explanations.

## Direct Adapters

Thanos includes native Python adapters for:

- **WorkOS**: Task management and productivity
- **Oura**: Health and fitness data
- **Neo4j**: Graph database operations
- **ChromaDB**: Vector database operations

These adapters work alongside MCP bridges, providing flexibility in integration approach.

## Development

### Running Tests

```bash
# Unit tests
python -m pytest tests/

# Integration tests (requires MCP servers)
python -m pytest tests/integration/ -v

# With coverage
python -m pytest tests/ --cov=Tools/adapters --cov-report=html
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes (follow existing patterns)
4. Add tests
5. Submit a pull request

## Configuration

Thanos supports multiple configuration sources:

1. **Global Config**: `~/.claude.json` for user-wide MCP servers
2. **Project Config**: `.mcp.json` in project root for project-specific servers
3. **Environment Variables**: For credentials and runtime configuration

See [MCP Integration Guide](docs/mcp-integration-guide.md) for detailed configuration options.

## Migration from Direct Adapters

If you're using direct adapters and want to migrate to MCP:

1. Review the [Migration Guide](docs/mcp-integration-guide.md#migration-from-direct-adapters)
2. Use [Migration Utilities](docs/mcp-integration-guide.md#migration-utilities) to compare adapters
3. Test both approaches in parallel
4. Gradually migrate with fallback options

## Support

- **Documentation**: See `docs/` directory for comprehensive guides
- **Issues**: Report bugs via GitHub issues
- **Examples**: See `examples/` directory for sample implementations

## License

[Your License Here]

## Acknowledgments

Built with:
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) - Model Context Protocol implementation
- Anthropic's Claude - For MCP specification and tooling
