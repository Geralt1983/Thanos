# MCP Orchestrator Integration Guide

Integration guide for connecting MCP bridges to the Thanos orchestrator and command router.

## Overview

This guide covers integrating MCP bridges into the Thanos orchestrator system:
- CommandRouter integration for slash commands
- Agent routing with MCP awareness
- State management and coordination
- Interactive mode support

## Architecture Integration

### System Components

```
┌─────────────────────────────────────────────────────┐
│              CommandRouter                          │
│  • Parse slash commands                            │
│  • Route to agents or adapters                     │
│  • Handle /adapter and /mcp commands               │
└──────────────────┬──────────────────────────────────┘
                   │
                   ├──────────┐
                   │          │
         ┌─────────▼────┐   ┌▼──────────────────┐
         │ Orchestrator │   │  AdapterManager   │
         │  • Agents    │   │  • Direct adapters│
         │  • Routing   │   │  • MCP bridges    │
         └──────────────┘   └────────┬──────────┘
                                     │
                      ┌──────────────┴──────────────┐
                      │                             │
            ┌─────────▼─────────┐      ┌───────────▼────────┐
            │  Direct Adapters  │      │    MCP Bridges     │
            │  • WorkOS (native)│      │  • WorkOS (MCP)    │
            │  • Oura           │      │  • Context7        │
            │  • Neo4j          │      │  • Magic           │
            │  • ChromaDB       │      │  • Playwright      │
            └───────────────────┘      └────────────────────┘
```

## CommandRouter Integration

### Step 1: Enable MCP Bridges in AdapterManager

Update the `_get_adapter_manager()` lazy initialization method:

```python
# Tools/command_router.py

async def _get_adapter_manager(self) -> Optional[AdapterManager]:
    """
    Get or initialize the adapter manager (lazy initialization).

    Returns:
        AdapterManager instance or None if unavailable
    """
    if not ADAPTER_MANAGER_AVAILABLE:
        return None

    if not self._adapter_manager_initialized:
        try:
            # Enable MCP bridges in production
            enable_mcp = os.environ.get("MCP_ENABLED", "false").lower() == "true"

            self._adapter_manager = await get_default_manager(
                enable_mcp_bridges=enable_mcp
            )
            self._adapter_manager_initialized = True

            # Log initialization
            adapters = self._adapter_manager.list_adapters()
            print(f"{Colors.DIM}✓ Initialized AdapterManager with {len(adapters)} adapters{Colors.RESET}")

            # If MCP enabled, log discovered servers
            if enable_mcp:
                mcp_servers = [a for a in adapters if ".mcp" in a or a.startswith("mcp_")]
                if mcp_servers:
                    print(f"{Colors.DIM}  MCP servers: {', '.join(mcp_servers)}{Colors.RESET}")

        except Exception as e:
            print(f"{Colors.DIM}⚠ Could not initialize AdapterManager: {e}{Colors.RESET}")
            self._adapter_manager = None
            self._adapter_manager_initialized = True

    return self._adapter_manager
```

### Step 2: Add MCP-Specific Commands

Register MCP management commands in `_register_commands()`:

```python
def _register_commands(self):
    """Register all slash commands with their handlers."""
    # Existing commands...

    # MCP-specific commands
    self._commands["/mcp"] = (self._cmd_mcp_status, "Show MCP server status", [])
    self._commands["/mcp:list"] = (self._cmd_mcp_list, "List available MCP servers", [])
    self._commands["/mcp:test"] = (self._cmd_mcp_test, "Test MCP server connection", ["server"])
    self._commands["/mcp:metrics"] = (self._cmd_mcp_metrics, "Show MCP performance metrics", [])
    self._commands["/mcp:refresh"] = (self._cmd_mcp_refresh, "Refresh MCP server discovery", [])
```

### Step 3: Implement MCP Command Handlers

```python
async def _cmd_mcp_status(self) -> CommandResult:
    """Show MCP bridge status."""
    manager = await self._get_adapter_manager()
    if not manager:
        return CommandResult(
            success=False,
            message="AdapterManager not available"
        )

    from Tools.adapters.mcp_observability import get_all_metrics

    # Get all MCP servers
    adapters = manager.list_adapters()
    mcp_servers = [a for a in adapters if ".mcp" in a or a.startswith("mcp_")]

    if not mcp_servers:
        return CommandResult(
            message="No MCP servers registered"
        )

    # Get metrics for each server
    output = [f"\n{Colors.BOLD}MCP Server Status:{Colors.RESET}\n"]
    all_metrics = get_all_metrics()

    for server in mcp_servers:
        # Extract server name (remove .mcp suffix if present)
        server_name = server.replace(".mcp", "")

        if server_name in all_metrics:
            metrics = all_metrics[server_name]
            conn_metrics = metrics.get("connections", {})
            tool_metrics = metrics.get("tool_calls", {})

            status_color = Colors.CYAN if conn_metrics.get("active", 0) > 0 else Colors.DIM

            output.append(f"{status_color}• {server}:{Colors.RESET}")
            output.append(f"  Connections: {conn_metrics.get('successful', 0)}/{conn_metrics.get('total', 0)}")
            output.append(f"  Tool calls: {tool_metrics.get('successful', 0)}/{tool_metrics.get('total', 0)}")
            output.append(f"  Success rate: {tool_metrics.get('success_rate', 0):.1%}")
        else:
            output.append(f"{Colors.DIM}• {server}: No metrics available{Colors.RESET}")

    return CommandResult(message="\n".join(output))


async def _cmd_mcp_list(self) -> CommandResult:
    """List available MCP servers."""
    manager = await self._get_adapter_manager()
    if not manager:
        return CommandResult(
            success=False,
            message="AdapterManager not available"
        )

    # Get all adapters
    adapters = manager.list_adapters()

    # Separate direct adapters from MCP bridges
    direct = []
    mcp_bridges = []

    for adapter_name in adapters:
        if ".mcp" in adapter_name or adapter_name.startswith("mcp_"):
            mcp_bridges.append(adapter_name)
        else:
            direct.append(adapter_name)

    output = [f"\n{Colors.BOLD}Adapter Inventory:{Colors.RESET}\n"]

    if direct:
        output.append(f"{Colors.CYAN}Direct Adapters:{Colors.RESET}")
        for name in sorted(direct):
            output.append(f"  • {name}")

    if mcp_bridges:
        output.append(f"\n{Colors.PURPLE}MCP Bridges:{Colors.RESET}")
        for name in sorted(mcp_bridges):
            # Get tools for this bridge
            try:
                adapter = await manager.get_adapter(name)
                tools = adapter.list_tools()
                output.append(f"  • {name} ({len(tools)} tools)")
            except:
                output.append(f"  • {name}")
    else:
        output.append(f"\n{Colors.DIM}No MCP bridges registered{Colors.RESET}")
        output.append(f"{Colors.DIM}Set MCP_ENABLED=true to enable MCP bridges{Colors.RESET}")

    return CommandResult(message="\n".join(output))


async def _cmd_mcp_test(self, server: str) -> CommandResult:
    """Test MCP server connection."""
    manager = await self._get_adapter_manager()
    if not manager:
        return CommandResult(
            success=False,
            message="AdapterManager not available"
        )

    # Test health check
    try:
        adapter = await manager.get_adapter(server)
        result = await adapter.health_check()

        if result.success:
            output = [
                f"\n{Colors.CYAN}✓ {server} is healthy{Colors.RESET}",
                f"\nDetails:"
            ]

            # Add health check details if available
            if isinstance(result.data, dict):
                for key, value in result.data.items():
                    if key == "metrics":
                        continue  # Skip metrics, too verbose
                    output.append(f"  {key}: {value}")

            return CommandResult(message="\n".join(output))
        else:
            return CommandResult(
                success=False,
                message=f"Health check failed: {result.error}"
            )

    except Exception as e:
        return CommandResult(
            success=False,
            message=f"Error testing server: {e}"
        )


async def _cmd_mcp_metrics(self) -> CommandResult:
    """Show MCP performance metrics."""
    from Tools.adapters.mcp_observability import get_all_metrics

    metrics = get_all_metrics()

    if not metrics:
        return CommandResult(
            message="No MCP metrics available"
        )

    output = [f"\n{Colors.BOLD}MCP Performance Metrics:{Colors.RESET}\n"]

    for server_name, server_metrics in metrics.items():
        output.append(f"{Colors.CYAN}{server_name}:{Colors.RESET}")

        # Connection metrics
        conn = server_metrics.get("connections", {})
        output.append(f"  Connections:")
        output.append(f"    Total: {conn.get('total', 0)}")
        output.append(f"    Success rate: {conn.get('success_rate', 0):.1%}")
        output.append(f"    Active: {conn.get('active', 0)}")

        # Tool call metrics
        tools = server_metrics.get("tool_calls", {})
        output.append(f"  Tool Calls:")
        output.append(f"    Total: {tools.get('total', 0)}")
        output.append(f"    Success rate: {tools.get('success_rate', 0):.1%}")

        # Performance metrics
        perf = server_metrics.get("performance", {})
        if perf.get("avg_call_times"):
            output.append(f"  Performance:")
            for tool_name, avg_time in perf["avg_call_times"].items():
                output.append(f"    {tool_name}: {avg_time*1000:.0f}ms")

        # Cache metrics
        cache_hit_rate = perf.get("cache_hit_rate", 0)
        if cache_hit_rate > 0:
            output.append(f"  Cache hit rate: {cache_hit_rate:.1%}")

        output.append("")  # Blank line between servers

    return CommandResult(message="\n".join(output))


async def _cmd_mcp_refresh(self) -> CommandResult:
    """Refresh MCP server discovery."""
    try:
        from Tools.adapters.mcp_discovery import discover_servers
        from Tools.adapters.mcp_bridge import MCPBridge

        # Discover servers
        servers = await discover_servers()

        if not servers:
            return CommandResult(
                message="No MCP servers found in configuration"
            )

        # Re-register with manager
        manager = await self._get_adapter_manager()
        if not manager:
            return CommandResult(
                success=False,
                message="AdapterManager not available"
            )

        registered = []
        failed = []

        for server_config in servers:
            try:
                bridge = MCPBridge(server_config)
                await bridge.connect()
                manager.register(bridge)
                registered.append(server_config.name)
            except Exception as e:
                failed.append(f"{server_config.name}: {e}")

        output = [f"\n{Colors.BOLD}MCP Discovery Refresh:{Colors.RESET}\n"]

        if registered:
            output.append(f"{Colors.CYAN}Registered:{Colors.RESET}")
            for name in registered:
                output.append(f"  ✓ {name}")

        if failed:
            output.append(f"\n{Colors.DIM}Failed:{Colors.RESET}")
            for error in failed:
                output.append(f"  ✗ {error}")

        return CommandResult(message="\n".join(output))

    except Exception as e:
        return CommandResult(
            success=False,
            message=f"Discovery failed: {e}"
        )
```

## Environment Configuration

### Enable MCP in Production

```bash
# .env.production
MCP_ENABLED=true
MCP_CONFIG_PATH=/etc/thanos/mcp_servers.json
```

### Enable MCP in Development

```bash
# .env.development
MCP_ENABLED=true
MCP_CONFIG_PATH=config/mcp_servers.json
```

## Interactive Mode Usage

### Example Session

```
🧠 thanos> /mcp:list

Adapter Inventory:

Direct Adapters:
  • workos
  • oura
  • neo4j
  • chroma

MCP Bridges:
  • workos.mcp (8 tools)
  • context7.mcp (4 tools)
  • magic.mcp (6 tools)
  • playwright.mcp (12 tools)

🧠 thanos> /mcp:test workos.mcp

✓ workos.mcp is healthy

Details:
  status: ok
  adapter: workos
  transport: stdio
  tool_count: 8
  initialized: True

🧠 thanos> /mcp:metrics

MCP Performance Metrics:

workos:
  Connections:
    Total: 45
    Success rate: 97.8%
    Active: 2
  Tool Calls:
    Total: 234
    Success rate: 98.7%
  Performance:
    get_tasks: 87ms
    get_today_metrics: 45ms
    complete_task: 123ms
  Cache hit rate: 67.3%

context7:
  Connections:
    Total: 12
    Success rate: 100.0%
    Active: 1
  Tool Calls:
    Total: 34
    Success rate: 100.0%
  Performance:
    resolve_library_id: 245ms
    get_library_docs: 567ms
```

## Agent Routing with MCP Awareness

### Enhanced Agent Routing

Update agent trigger patterns to include MCP-aware routing:

```python
# In agent configuration
{
    "epic_agent": {
        "triggers": [
            "epic", "consultant", "consulting", "client",
            # MCP-aware triggers
            "workos tasks", "calendar", "productivity"
        ]
    },
    "research_agent": {
        "triggers": [
            "research", "documentation", "library",
            # MCP-aware triggers
            "context7", "search docs", "api reference"
        ]
    },
    "ui_agent": {
        "triggers": [
            "component", "ui", "interface", "frontend",
            # MCP-aware triggers
            "magic", "generate component", "react"
        ]
    }
}
```

### Dynamic Tool Discovery

Agents can discover available MCP tools dynamically:

```python
# In agent prompt or initialization
async def get_available_tools(self, manager: AdapterManager) -> dict:
    """Get tools from both direct adapters and MCP bridges."""
    all_tools = {}

    for adapter_name in manager.list_adapters():
        adapter = await manager.get_adapter(adapter_name)
        tools = adapter.list_tools()

        for tool in tools:
            tool_key = f"{adapter_name}.{tool['name']}"
            all_tools[tool_key] = tool

    return all_tools
```

## State Management

### Persisting MCP Configuration

Store MCP server preferences in State/ directory:

```yaml
# State/mcp_config.yaml
enabled_servers:
  - workos
  - context7
  - magic

preferred_mode:
  workos: mcp  # Use MCP bridge instead of direct adapter

cache_config:
  enabled: true
  ttl: 1800

connection_pool:
  enabled: true
  max_connections: 10
```

### Session Tracking

Track MCP usage in session history:

```python
# During session
{
    "session_id": "...",
    "timestamp": "2026-01-11T12:00:00",
    "mcp_stats": {
        "total_calls": 45,
        "servers_used": ["workos.mcp", "context7.mcp"],
        "avg_latency_ms": 123,
        "cache_hit_rate": 0.67
    }
}
```

## Testing Integration

### Integration Test

```python
# tests/integration/test_mcp_orchestrator.py
import pytest
from Tools.command_router import CommandRouter
from Tools.adapters import get_default_manager


@pytest.mark.asyncio
async def test_mcp_orchestrator_integration():
    """Test MCP bridge integration with orchestrator."""
    # Initialize with MCP enabled
    manager = await get_default_manager(enable_mcp_bridges=True)

    # Verify MCP servers registered
    adapters = manager.list_adapters()
    mcp_servers = [a for a in adapters if ".mcp" in a]
    assert len(mcp_servers) > 0

    # Test tool call through manager
    result = await manager.call_tool("workos.mcp.get_today_metrics")
    assert result.success


@pytest.mark.asyncio
async def test_command_router_mcp_commands(mock_orchestrator):
    """Test MCP-specific commands in CommandRouter."""
    router = CommandRouter(mock_orchestrator, ...)

    # Test /mcp:list
    result = await router.route_command("/mcp:list")
    assert result.success
    assert "MCP Bridges" in result.message

    # Test /mcp:status
    result = await router.route_command("/mcp:status")
    assert result.success
```

## Migration Strategy

### Gradual Migration Path

1. **Phase 1**: Run MCP bridges alongside direct adapters
2. **Phase 2**: Switch traffic gradually using feature flags
3. **Phase 3**: Deprecate direct adapters when stable
4. **Phase 4**: Remove legacy code

### Feature Flag Configuration

```python
# config/feature_flags.py
MCP_ROLLOUT = {
    "workos": {
        "enabled": True,
        "traffic_percentage": 10,  # 10% of requests use MCP bridge
        "fallback_to_direct": True  # Fall back to direct adapter on error
    },
    "oura": {
        "enabled": False,  # Keep using direct adapter
        "traffic_percentage": 0,
        "fallback_to_direct": True
    }
}
```

## Monitoring and Observability

### Integration with Monitoring Stack

```python
# Export metrics for Prometheus
from Tools.adapters.mcp_observability import get_all_metrics

@app.get("/metrics")
def prometheus_metrics():
    """Export MCP metrics in Prometheus format."""
    metrics = get_all_metrics()

    lines = []
    for server, data in metrics.items():
        # Connection metrics
        lines.append(f'mcp_connections_total{{server="{server}"}} {data["connections"]["total"]}')
        lines.append(f'mcp_connections_success_rate{{server="{server}"}} {data["connections"]["success_rate"]}')

        # Tool call metrics
        lines.append(f'mcp_tool_calls_total{{server="{server}"}} {data["tool_calls"]["total"]}')
        lines.append(f'mcp_tool_calls_success_rate{{server="{server}"}} {data["tool_calls"]["success_rate"]}')

    return "\n".join(lines)
```

## Summary

### Integration Checklist

- [ ] Enable MCP bridges in AdapterManager initialization
- [ ] Add MCP-specific commands to CommandRouter
- [ ] Update agent trigger patterns for MCP awareness
- [ ] Configure environment variables (MCP_ENABLED, MCP_CONFIG_PATH)
- [ ] Test integration in interactive mode
- [ ] Set up monitoring and metrics export
- [ ] Document usage for team

### Key Benefits

- **Hybrid Architecture**: Use direct adapters OR MCP bridges
- **Seamless Integration**: MCP bridges work like native adapters
- **Performance Monitoring**: Built-in metrics and observability
- **Easy Testing**: New /mcp:* commands for debugging
- **Gradual Migration**: Run both systems in parallel
