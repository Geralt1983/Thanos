# Thanos Architecture Documentation

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Core Layers](#core-layers)
- [MCP Integration](#mcp-integration)
- [Component Details](#component-details)
- [Data Flow](#data-flow)
- [Integration Points](#integration-points)
- [Scalability & Performance](#scalability--performance)
- [Security](#security)
- [Future Architecture](#future-architecture)

## Overview

Thanos is built on a **modular, layered architecture** that enables flexible integration with external services through two primary approaches:

1. **Direct Adapters**: Native Python implementations for tight integration
2. **MCP Bridges**: Protocol-based integration via Model Context Protocol

This hybrid approach provides the best of both worlds: native performance where needed and ecosystem flexibility through MCP.

## System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        User / Client Layer                           │
│  - CLI Interface                                                     │
│  - API Endpoints                                                     │
│  - Configuration Files                                               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Orchestration Layer                              │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              Thanos Orchestrator                              │  │
│  │  - Command Parsing                                            │  │
│  │  - Execution Planning                                         │  │
│  │  - Result Aggregation                                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              Command Router                                   │  │
│  │  - Tool Selection                                             │  │
│  │  - Parameter Validation                                       │  │
│  │  - Response Formatting                                        │  │
│  └──────────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Adapter Layer                                   │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                   Adapter Manager                             │  │
│  │  - Adapter Registration & Discovery                           │  │
│  │  - Unified Tool Interface                                     │  │
│  │  - Routing (Direct vs MCP)                                    │  │
│  │  - Lifecycle Management                                       │  │
│  │  - Health Checking                                            │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌────────────────────────┐        ┌──────────────────────────┐   │
│  │   Direct Adapters      │        │     MCP Bridges          │   │
│  │                        │        │                          │   │
│  │  ┌──────────────────┐ │        │  ┌────────────────────┐ │   │
│  │  │ WorkOS Adapter   │ │        │  │ WorkOS MCP Bridge  │ │   │
│  │  │ - Native Python  │ │        │  │ - Via Protocol     │ │   │
│  │  └──────────────────┘ │        │  └────────────────────┘ │   │
│  │                        │        │                          │   │
│  │  ┌──────────────────┐ │        │  ┌────────────────────┐ │   │
│  │  │ Oura Adapter     │ │        │  │ Context7 Bridge    │ │   │
│  │  │ - Native Python  │ │        │  │ - Remote SSE       │ │   │
│  │  └──────────────────┘ │        │  └────────────────────┘ │   │
│  │                        │        │                          │   │
│  │  ┌──────────────────┐ │        │  │ Sequential Bridge  │ │   │
│  │  │ Neo4j Adapter    │ │        │  │ - Local stdio      │ │   │
│  │  │ - Graph DB       │ │        │  └────────────────────┘ │   │
│  │  └──────────────────┘ │        │                          │   │
│  │                        │        │  ┌────────────────────┐ │   │
│  │  ┌──────────────────┐ │        │  │ Filesystem Bridge  │ │   │
│  │  │ ChromaDB Adapter │ │        │  │ - Local stdio      │ │   │
│  │  │ - Vector DB      │ │        │  └────────────────────┘ │   │
│  │  └──────────────────┘ │        │                          │   │
│  │                        │        │  ┌────────────────────┐ │   │
│  └────────────────────────┘        │  │ Custom Bridges     │ │   │
│       BaseAdapter                  │  │ - User-defined     │ │   │
│       Interface                    │  └────────────────────┘ │   │
│                                    └──────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      MCP Bridge Layer                                │
│  (Only for MCP Bridges)                                             │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │   Discovery      │  │  Configuration   │  │  Capabilities   │  │
│  │  - Global        │  │  - Validation    │  │  - Negotiation  │  │
│  │  - Project       │  │  - Env vars      │  │  - Feature det. │  │
│  │  - Filtering     │  │  - Merging       │  │  - Versioning   │  │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘  │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │   Transport      │  │   Connection     │  │   Health        │  │
│  │  - stdio         │  │   Pooling        │  │   Monitoring    │  │
│  │  - SSE           │  │  - Lifecycle     │  │  - Metrics      │  │
│  │  - HTTP (ready)  │  │  - Reuse         │  │  - Status       │  │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘  │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │   Caching        │  │   Load           │  │   Error         │  │
│  │  - TTL           │  │   Balancing      │  │   Handling      │  │
│  │  - LRU/LFU       │  │  - Strategies    │  │  - Retry        │  │
│  │  - Disk/Memory   │  │  - Failover      │  │  - Circuit      │  │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              MCPBridge Core                                   │  │
│  │  - Session Management                                         │  │
│  │  - Protocol Lifecycle                                         │  │
│  │  - Tool Caching                                               │  │
│  │  - BaseAdapter Implementation                                 │  │
│  └──────────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  MCP Protocol (JSON-RPC 2.0)                         │
│  - initialize                                                        │
│  - tools/list                                                        │
│  - tools/call                                                        │
│  - completion                                                        │
│  - resources/* (future)                                             │
│  - prompts/* (future)                                               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      External Services                               │
│                                                                      │
│  ┌────────────────────────┐        ┌──────────────────────────┐    │
│  │   Direct Services      │        │     MCP Servers          │    │
│  │                        │        │                          │    │
│  │  - WorkOS API          │        │  - WorkOS MCP Server     │    │
│  │  - Oura API            │        │  - Context7 (Remote)     │    │
│  │  - Neo4j Database      │        │  - Sequential Thinking   │    │
│  │  - ChromaDB            │        │  - Filesystem Server     │    │
│  └────────────────────────┘        │  - Playwright Server     │    │
│                                    │  - Fetch Server          │    │
│                                    │  - Custom Servers        │    │
│                                    └──────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

## Core Layers

### 1. User / Client Layer

**Responsibility**: User interaction and configuration

**Components**:
- CLI interface for command-line interactions
- API endpoints for programmatic access
- Configuration files (`.mcp.json`, `~/.claude.json`, `.env`)

**Key Files**:
- Configuration files in project root
- Environment variables

### 2. Orchestration Layer

**Responsibility**: High-level command orchestration and execution

**Components**:

#### Thanos Orchestrator (`Tools/thanos_orchestrator.py`)
- Parses user commands
- Plans execution strategy
- Coordinates multi-step operations
- Aggregates results

#### Command Router (`Tools/command_router.py`)
- Routes commands to appropriate adapters
- Validates parameters
- Formats responses
- Handles errors

**Integration Points**:
- Initializes AdapterManager on startup
- Calls adapter methods for tool execution
- Manages adapter lifecycle

### 3. Adapter Layer

**Responsibility**: Unified interface to all external services

**Core Component**: AdapterManager (`Tools/adapters/__init__.py`)

**Features**:
- **Unified Interface**: Single API for all adapters (direct + MCP)
- **Discovery**: Automatic MCP server discovery from config files
- **Registration**: Both manual and automatic adapter registration
- **Routing**: Transparent routing to direct adapters or MCP bridges
- **Lifecycle**: Health checking, initialization, shutdown
- **Statistics**: Usage tracking and performance monitoring

**Key Methods**:
```python
class AdapterManager:
    async def list_tools() -> List[Dict]
    async def call_tool(name: str, args: Dict) -> ToolResult
    async def register_adapter(name: str, adapter: BaseAdapter)
    async def register_mcp_server(config: MCPServerConfig)
    async def discover_and_register_mcp_servers(...)
    async def health_check_all() -> Dict
```

**Adapter Types**:

#### Direct Adapters
Native Python implementations extending `BaseAdapter`:
- **WorkOS Adapter**: Task management
- **Oura Adapter**: Health data
- **Neo4j Adapter**: Graph database
- **ChromaDB Adapter**: Vector database

**Advantages**:
- Native Python performance
- Direct API integration
- Tighter error handling
- Simpler debugging

#### MCP Bridges
Protocol-based implementations extending `BaseAdapter`:
- **WorkOS MCP Bridge**: Via WorkOS MCP server
- **Context7 Bridge**: Documentation search (remote)
- **Sequential Thinking Bridge**: Advanced reasoning
- **Filesystem Bridge**: File operations
- **Playwright Bridge**: Browser automation
- **Fetch Bridge**: Web scraping
- **Custom Bridges**: User-defined servers

**Advantages**:
- Ecosystem access
- Language-agnostic
- Standardized protocol
- Community servers

### 4. MCP Bridge Layer

**Responsibility**: MCP protocol implementation and advanced features

**Only active for MCP bridges** - Direct adapters bypass this layer.

#### Core Components:

**MCPBridge** (`Tools/adapters/mcp_bridge.py`)
- Implements `BaseAdapter` interface
- Manages MCP protocol lifecycle
- Handles sessions and cleanup
- Caches tool listings
- Provides health checks

**Server Discovery** (`Tools/adapters/mcp_discovery.py`)
- Discovers servers from `~/.claude.json`
- Discovers project-specific `.mcp.json`
- Walks directory tree for configs
- Merges configurations with precedence
- Filters by enabled status and tags

**Configuration** (`Tools/adapters/mcp_config.py`)
- Pydantic-based validation
- Environment variable interpolation
- Support for stdio, SSE, HTTP transports
- Per-server settings (timeouts, retries, etc.)

**Capabilities** (`Tools/adapters/mcp_capabilities.py`)
- Client capability declaration
- Server capability parsing
- Feature detection and matching
- Graceful degradation

**Transport Layer** (`Tools/adapters/transports/`)
- **Base Transport**: Abstract interface
- **StdioTransport**: Local subprocess via stdin/stdout
- **SSETransport**: Remote servers via server-sent events
- **HTTPTransport**: (Ready for implementation)

#### Advanced Features:

**Connection Pooling** (`Tools/adapters/mcp_pool.py`)
- Min/max connection limits
- Connection lifecycle tracking
- Automatic reconnection
- Background health checks
- Graceful shutdown

**Health Monitoring** (`Tools/adapters/mcp_health.py`)
- Periodic health checks
- Performance metrics (latency, success rate)
- Health status tracking (HEALTHY/DEGRADED/UNHEALTHY)
- Automatic status updates
- Multi-server registry

**Result Caching** (`Tools/adapters/mcp_cache.py`)
- TTL-based expiration
- Multiple strategies (LRU, LFU, MANUAL)
- Memory and disk backends
- Cache statistics
- Per-tool cache keys

**Load Balancing** (`Tools/adapters/mcp_loadbalancer.py`)
- Multiple strategies (round-robin, least-connections, health-aware)
- Automatic failover
- Connection tracking
- Health-aware routing
- Multi-server registry

**Error Handling** (`Tools/adapters/mcp_errors.py`, `mcp_retry.py`)
- Custom exception hierarchy (11 types)
- Exponential backoff with jitter
- Circuit breaker pattern
- Detailed error logging
- Fallback strategies

**Validation** (`Tools/adapters/mcp_validation.py`)
- JSON Schema validation
- Argument validation
- Response validation
- Strict and lenient modes
- Type coercion

### 5. Protocol Layer

**MCP Protocol** (JSON-RPC 2.0 over stdio/SSE/HTTP)

**Messages**:
- `initialize`: Handshake with capability negotiation
- `tools/list`: Retrieve available tools
- `tools/call`: Execute a tool with arguments
- `completion`: Graceful shutdown

**Future Messages** (MCP spec extensions):
- `resources/*`: Access to contextual resources
- `prompts/*`: Prompt templates
- `sampling/*`: LLM sampling requests

### 6. External Services Layer

**Direct Services**: Native APIs accessed directly
- WorkOS REST API
- Oura REST API
- Neo4j database protocol
- ChromaDB API

**MCP Servers**: Protocol-compliant servers
- WorkOS MCP Server (Node.js, local stdio)
- Context7 (Remote HTTPS/SSE)
- @modelcontextprotocol/* (NPM packages, local stdio)
- Custom servers (Any language, any transport)

## MCP Integration

### Integration Architecture

MCP integration follows a **bridge pattern** where:

1. **MCPBridge** implements the same `BaseAdapter` interface as direct adapters
2. **AdapterManager** treats both types identically
3. **Orchestrator** remains unaware of adapter implementation details

This enables:
- Transparent routing
- Zero orchestrator changes
- Backward compatibility
- Easy migration

### Integration Flow

```
User Command
    │
    ▼
Orchestrator
    │
    ▼
Command Router
    │
    ▼
Adapter Manager ──┬──> Direct Adapter ──> External API
                  │
                  └──> MCP Bridge ──> Transport ──> MCP Server ──> Service
```

### Configuration Discovery

```
Adapter Manager
    │
    ▼
MCPServerDiscovery
    │
    ├──> Load ~/.claude.json (global)
    │
    ├──> Walk directory tree for .mcp.json (project-specific)
    │
    ├──> Merge configurations (project > global)
    │
    ├──> Filter by enabled status and tags
    │
    └──> Return list of MCPServerConfig
         │
         ▼
    Create MCPBridge instances
         │
         ▼
    Register with AdapterManager
```

### Session Lifecycle

```
1. Discovery Phase
   - Scan config files
   - Parse and validate configurations
   - Create MCPServerConfig objects

2. Registration Phase
   - Create MCPBridge instances (lazy)
   - Register with AdapterManager
   - Store in adapter registry

3. Initialization Phase (Lazy)
   - First tool call triggers initialization
   - Create transport (stdio/SSE)
   - Send initialize request
   - Negotiate capabilities
   - Cache tool list

4. Operation Phase
   - List tools (from cache or fresh)
   - Call tools (via protocol)
   - Handle errors (retry, circuit breaker)
   - Cache results (if enabled)
   - Monitor health (if enabled)

5. Shutdown Phase
   - Send completion request
   - Close transport
   - Cleanup resources
   - Close connection pool (if used)
   - Stop health monitor (if running)
```

## Component Details

### BaseAdapter Interface

All adapters (direct and MCP) implement this interface:

```python
class BaseAdapter(ABC):
    @abstractmethod
    async def list_tools(self) -> List[Dict]:
        """List available tools"""

    @abstractmethod
    async def call_tool(self, name: str, arguments: Dict) -> ToolResult:
        """Execute a tool with arguments"""

    @abstractmethod
    async def health_check(self) -> bool:
        """Check adapter health"""

    @abstractmethod
    async def close(self):
        """Cleanup and shutdown"""
```

This unified interface enables:
- Transparent routing in AdapterManager
- Consistent error handling
- Uniform health checking
- Common lifecycle management

### Tool Result Format

Both adapter types return the same `ToolResult`:

```python
@dataclass
class ToolResult:
    success: bool
    result: Optional[Any]
    error: Optional[str]
    metadata: Optional[Dict]
```

### Configuration Schema

MCP servers are configured via JSON:

```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "package-name"],
      "env": {
        "VAR": "value",
        "SECRET": "${ENV_VAR}"
      },
      "transport": "stdio",
      "enabled": true,
      "tags": ["tag1", "tag2"],
      "settings": {
        "timeout": 30000,
        "retries": 3
      }
    }
  }
}
```

## Data Flow

### Tool Call Flow (MCP Bridge)

```
1. User → Orchestrator
   Command: "Get task list"

2. Orchestrator → Command Router
   Parse and extract intent

3. Command Router → Adapter Manager
   call_tool("task_list", {})

4. Adapter Manager
   - Lookup tool in registry
   - Find MCPBridge for "task_list"
   - Route to bridge

5. MCPBridge
   - Check if initialized (if not, initialize)
   - Check cache (if enabled)
   - Check circuit breaker status

6. MCPBridge → Transport
   Send JSON-RPC request:
   {
     "jsonrpc": "2.0",
     "method": "tools/call",
     "params": {
       "name": "task_list",
       "arguments": {}
     }
   }

7. Transport → MCP Server
   - Stdio: Write to process stdin
   - SSE: POST to HTTPS endpoint

8. MCP Server
   - Process request
   - Execute tool logic
   - Return result

9. MCP Server → Transport
   JSON-RPC response:
   {
     "jsonrpc": "2.0",
     "result": {
       "content": [...]
     }
   }

10. Transport → MCPBridge
    Parse response

11. MCPBridge
    - Cache result (if enabled)
    - Record metrics (if monitoring enabled)
    - Convert to ToolResult

12. MCPBridge → Adapter Manager
    Return ToolResult

13. Adapter Manager → Command Router
    Forward result

14. Command Router → Orchestrator
    Format response

15. Orchestrator → User
    Present result
```

### Error Flow

```
Error in MCP Server
    │
    ▼
Transport detects error
    │
    ▼
MCPBridge catches exception
    │
    ▼
Retry Logic (if transient error)
    │
    ├──> Success → Return result
    │
    └──> Failure → Circuit Breaker
         │
         ├──> Open Circuit → Return error immediately
         │
         └──> Closed Circuit → Try alternative server (load balancer)
              │
              ├──> Success → Return result
              │
              └──> All failed → Return ToolResult with error
                   │
                   ▼
              Adapter Manager
                   │
                   ▼
              Command Router (format error)
                   │
                   ▼
              Orchestrator (handle error)
                   │
                   ▼
              User (error message)
```

## Integration Points

### 1. Orchestrator Integration

**Current State**: Orchestrator is MCP-ready but not yet enabled

**Integration Points**:
```python
# Tools/thanos_orchestrator.py

class ThanosOrchestrator:
    def __init__(self, enable_mcp: bool = False):
        self.adapter_manager = get_default_manager(enable_mcp=enable_mcp)

    async def initialize(self):
        if self.enable_mcp:
            await self.adapter_manager.discover_and_register_mcp_servers()
```

**Future Work** (Subtask 6.5):
- Enable MCP by default (or via config)
- Auto-discover on startup
- Graceful shutdown of MCP connections
- Error handling integration

### 2. Command Router Integration

**Current State**: Routes transparently to any adapter

**Integration Points**:
```python
# Tools/command_router.py

class CommandRouter:
    async def route_command(self, command: str, args: Dict):
        # Works identically for direct adapters and MCP bridges
        tools = await self.adapter_manager.list_tools()
        tool = self.select_tool(tools, command)
        result = await self.adapter_manager.call_tool(tool['name'], args)
        return self.format_response(result)
```

**No changes needed** - already works with both adapter types.

### 3. Configuration Integration

**Configuration Sources** (in precedence order):
1. Project-specific `.mcp.json` (highest precedence)
2. Parent directory `.mcp.json` (walks up tree)
3. Global `~/.claude.json`
4. Environment variables (for credentials)

**Merging Strategy**:
- Project configs override global configs
- Same server name → project config wins
- Different server names → both included
- Disabled servers → excluded from final list

### 4. Logging Integration

**Current State**: Uses Python logging module

**Integration Points**:
```python
import logging

logger = logging.getLogger(__name__)

# In MCPBridge
logger.debug(f"Sending MCP request: {request}")
logger.info(f"Tool '{tool_name}' executed successfully")
logger.warning(f"Retry attempt {attempt}/{max_attempts}")
logger.error(f"Tool execution failed: {error}")
```

**Future Work** (Subtask 6.1):
- Structured logging with context
- Log sanitization for sensitive data
- Configurable log levels per component
- Log aggregation for production

### 5. Metrics Integration

**Current State**: Basic metrics in health monitoring

**Future Work** (Subtask 6.2):
- Prometheus/StatsD export
- Grafana dashboards
- Real-time monitoring
- Alerting on failures

## Scalability & Performance

### Horizontal Scaling

**Load Balancing** enables scaling across multiple server instances:

```python
# Create multiple instances of same server
bridges = [
    await create_mcp_bridge(config1),
    await create_mcp_bridge(config2),
    await create_mcp_bridge(config3)
]

# Load balance across instances
lb = LoadBalancer("server-name", bridges, LoadBalancingStrategy.HEALTH_AWARE)

# Automatic distribution
result = await lb.execute_tool("tool_name", args)
```

**Strategies**:
- **Round-robin**: Distribute evenly
- **Least-connections**: Use least busy server
- **Health-aware**: Prioritize healthy servers

### Vertical Scaling

**Connection Pooling** enables efficient resource usage:

```python
# Single bridge with connection pool
bridge = await create_mcp_bridge(config)
pool = MCPConnectionPool(bridge, PoolConfig(
    min_connections=2,
    max_connections=20
))

# Reuse connections
async with pool.acquire() as conn:
    result = await conn.call_tool("tool", args)
```

**Benefits**:
- Reduce initialization overhead
- Reuse existing sessions
- Background health checks
- Automatic reconnection

### Caching Strategy

**Result Caching** reduces load on MCP servers:

```python
cache = create_cache(CacheConfig(
    backend="MEMORY",
    invalidation_strategy=InvalidationStrategy.LRU,
    default_ttl=300,
    max_size=1000
))

# Cache tool results
result = await cache.cache_tool_call(bridge, "tool", args, ttl=600)
```

**Strategies**:
- **TTL**: Time-based expiration
- **LRU**: Least recently used eviction
- **LFU**: Least frequently used eviction
- **MANUAL**: Explicit invalidation

### Performance Characteristics

| Component | Overhead | Mitigation |
|-----------|----------|------------|
| MCP Protocol | ~10ms | Acceptable for most use cases |
| Subprocess | ~5-10ms | Use connection pooling |
| Initialization | ~200ms | Lazy initialization, pooling |
| Cache lookup | <1ms | In-memory cache |
| Health check | <5ms | Background checks |

**Optimization Tips**:
1. Enable connection pooling for long-running operations
2. Use caching for frequently accessed data
3. Use health-aware load balancing
4. Tune TTL based on data freshness needs
5. Monitor metrics to identify bottlenecks

## Security

### Configuration Security

**Sensitive Data Protection**:
- Store credentials in environment variables
- Use `.env` files (never commit to git)
- Reference via `${VAR}` syntax in configs
- Validate all configurations

**Example**:
```json
{
  "mcpServers": {
    "secure-server": {
      "command": "node",
      "args": ["server.js"],
      "env": {
        "API_KEY": "${SECURE_API_KEY}",
        "DATABASE_URL": "${DATABASE_URL}"
      }
    }
  }
}
```

### Transport Security

**Stdio Transport**:
- Local subprocess communication only
- No network exposure
- Process isolation

**SSE Transport**:
- HTTPS for encryption
- Bearer token authentication
- Header-based credentials

**Future HTTP Transport**:
- HTTPS only
- OAuth2/JWT support
- Certificate validation

### Input Validation

**Tool Arguments**:
- JSON Schema validation
- Type checking
- Range validation
- Required field checking

**Configuration**:
- Pydantic validation
- Type safety
- Default values
- Constraint enforcement

### Access Control

**MCP Server Access Control**:
- Servers define allowed directories (filesystem server)
- API keys for authentication (Context7, custom servers)
- Read-only by default (filesystem server requires ALLOW_WRITE)

**Thanos Access Control**:
- Per-server enabled/disabled flag
- Tag-based filtering
- Environment-specific configs (dev vs prod)

### Audit Logging

**Current**:
- All tool calls logged
- Error context captured
- Performance metrics recorded

**Future** (Subtask 6.1):
- Structured audit logs
- User attribution
- Request/response logging
- Compliance reporting

## Future Architecture

### Planned Enhancements (Phase 6)

#### 6.1: Comprehensive Logging
- Structured logging with JSON output
- Log levels per component
- Sensitive data sanitization
- Centralized log aggregation

#### 6.2: Metrics & Observability
- Prometheus metrics export
- StatsD integration
- Grafana dashboards
- Real-time alerting

#### 6.3: Deployment Configuration
- Docker support
- Kubernetes manifests
- Helm charts
- CI/CD pipelines

#### 6.4: Performance Optimization
- Profile and optimize hot paths
- Memory usage optimization
- Subprocess spawning optimization
- Benchmark suite

#### 6.5: Full Orchestrator Integration
- MCP enabled by default
- Graceful shutdown
- Error handling integration
- Backward compatibility testing

### Future MCP Features

**Resources** (MCP Spec):
- Access to contextual resources
- File contents, API responses, etc.
- URI-based resource access

**Prompts** (MCP Spec):
- Reusable prompt templates
- Dynamic prompt generation
- Prompt parameter injection

**Sampling** (MCP Spec):
- LLM sampling requests from servers
- Server-initiated reasoning
- Agentic workflows

### Extensibility

**Adding New Direct Adapters**:
1. Extend `BaseAdapter`
2. Implement required methods
3. Register with `AdapterManager`

**Adding New MCP Bridges**:
1. Create server configuration
2. Add to `.mcp.json` or `~/.claude.json`
3. Auto-discovered on next startup

**Custom Advanced Features**:
- Custom cache backends
- Custom load balancing strategies
- Custom health check logic
- Custom retry policies

## Conclusion

The Thanos architecture provides:

- ✅ **Unified Interface**: Single API for all integrations
- ✅ **Flexibility**: Support for both direct and protocol-based adapters
- ✅ **Scalability**: Connection pooling, load balancing, caching
- ✅ **Reliability**: Error handling, retry logic, circuit breakers
- ✅ **Observability**: Health monitoring, metrics, logging
- ✅ **Security**: Input validation, access control, credential management
- ✅ **Extensibility**: Easy to add new adapters and servers
- ✅ **Performance**: Optimized for production workloads

This positions Thanos as a robust, production-ready orchestration platform capable of integrating with any external service through native adapters or the growing MCP ecosystem.
