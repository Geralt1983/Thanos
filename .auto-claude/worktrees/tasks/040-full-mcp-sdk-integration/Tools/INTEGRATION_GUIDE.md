# MCP Integration Guide for Thanos Orchestrator and Command Router

This guide provides the necessary changes to integrate MCP SDK support into `thanos_orchestrator.py` and `command_router.py`.

## Overview

The integration enables:
1. **Automatic MCP server initialization** on orchestrator startup
2. **Transparent MCP tool access** through the command router
3. **Graceful shutdown** of MCP connections
4. **Backward compatibility** with existing workflows
5. **Error handling** integrated with existing systems

## 1. Thanos Orchestrator Integration

### Changes to `Tools/thanos_orchestrator.py`

Add MCP/AdapterManager support to the `ThanosOrchestrator` class:

```python
# Add to imports at top of file
import os
from typing import Optional

# Conditional AdapterManager import (after other conditional imports)
try:
    from Tools.adapters import AdapterManager, get_default_manager
    ADAPTER_MANAGER_AVAILABLE = True
except ImportError:
    AdapterManager = None
    get_default_manager = None
    ADAPTER_MANAGER_AVAILABLE = False
```

### Modify `__init__` method

```python
def __init__(
    self,
    base_dir: str = None,
    api_client: "LiteLLMClient" = None,
    matcher_strategy: str = "regex",
    enable_mcp: bool = None,  # NEW: Add MCP parameter
):
    """Initialize the Thanos orchestrator.

    Args:
        base_dir: Base directory for Thanos files (defaults to project root)
        api_client: Optional LiteLLM client instance
        matcher_strategy: Strategy for keyword matching ('regex' or 'trie')
        enable_mcp: Enable MCP bridge support. If None, reads from MCP_ENABLED env var.
    """
    self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent.parent
    self.api_client = api_client
    self.matcher_strategy = matcher_strategy

    # NEW: MCP integration support
    self._enable_mcp = enable_mcp if enable_mcp is not None else (
        os.environ.get("MCP_ENABLED", "false").lower() == "true"
    )
    self._adapter_manager: Optional[AdapterManager] = None
    self._adapter_manager_initialized = False

    # Load components (existing code)
    self.agents: dict[str, Agent] = {}
    self.commands: dict[str, Command] = {}
    self.context: dict[str, str] = {}

    self._load_agents()
    self._load_commands()
    self._load_context()

    # Initialize intent matcher with pre-compiled patterns (lazy initialization)
    self._intent_matcher: Optional[Union[KeywordMatcher, TrieKeywordMatcher]] = None

    # NEW: Initialize MCP if enabled
    if self._enable_mcp:
        self._initialize_mcp()
```

### Add MCP initialization method

```python
def _initialize_mcp(self):
    """Initialize MCP adapter manager if available and enabled."""
    if not ADAPTER_MANAGER_AVAILABLE:
        print("⚠ MCP support requested but AdapterManager not available")
        return

    try:
        import asyncio

        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Initialize adapter manager with MCP support
        if loop.is_running():
            # If loop is already running, we can't use run_until_complete
            # MCP will be initialized lazily on first use
            print("ℹ MCP adapter manager will be initialized on first use")
        else:
            # Initialize now
            self._adapter_manager = loop.run_until_complete(
                get_default_manager(enable_mcp=True)
            )
            self._adapter_manager_initialized = True

            # Log initialization success
            if self._adapter_manager:
                stats = self._adapter_manager.get_stats()
                total = stats['total_adapters']
                mcp_count = stats['mcp_bridges']
                if total > 0:
                    print(f"✓ Initialized {total} adapter(s) ({mcp_count} MCP bridge(s))")

    except Exception as e:
        print(f"⚠ Failed to initialize MCP: {e}")
        # Continue without MCP - graceful degradation
```

### Add MCP accessor method

```python
def _get_adapter_manager(self) -> Optional[AdapterManager]:
    """Get adapter manager instance, initializing if needed (lazy initialization)."""
    if not ADAPTER_MANAGER_AVAILABLE:
        return None

    if not self._adapter_manager_initialized:
        try:
            import asyncio
            loop = asyncio.get_event_loop()

            if loop.is_running():
                # Can't initialize in running loop
                return None

            self._adapter_manager = loop.run_until_complete(
                get_default_manager(enable_mcp=self._enable_mcp)
            )
            self._adapter_manager_initialized = True

        except Exception:
            self._adapter_manager = None

    return self._adapter_manager
```

### Add graceful shutdown method

```python
def shutdown(self):
    """Gracefully shutdown the orchestrator and close all connections.

    This method should be called when the orchestrator is no longer needed
    to ensure proper cleanup of MCP connections and other resources.
    """
    if self._adapter_manager_initialized and self._adapter_manager:
        try:
            import asyncio
            loop = asyncio.get_event_loop()

            if not loop.is_running():
                # Close all adapter connections
                loop.run_until_complete(self._adapter_manager.close_all())
                print("✓ Closed all adapter connections")
        except Exception as e:
            print(f"⚠ Error during shutdown: {e}")
        finally:
            self._adapter_manager = None
            self._adapter_manager_initialized = False
```

### Add context manager support

```python
def __enter__(self):
    """Context manager entry."""
    return self

def __exit__(self, exc_type, exc_val, exc_tb):
    """Context manager exit with automatic cleanup."""
    self.shutdown()
    return False  # Don't suppress exceptions
```

### Update `get_thanos` function for MCP support

```python
def get_thanos(base_dir: str = None, enable_mcp: bool = None) -> ThanosOrchestrator:
    """Get or create the singleton orchestrator instance.

    Args:
        base_dir: Base directory for Thanos files
        enable_mcp: Enable MCP bridge support. If None, reads from MCP_ENABLED env var.
    """
    global _thanos_instance
    if _thanos_instance is None:
        _thanos_instance = ThanosOrchestrator(base_dir, enable_mcp=enable_mcp)
    return _thanos_instance
```

## 2. Command Router Integration

The command router (`Tools/command_router.py`) already has MCP integration in place via the `_get_adapter_manager()` method and MCP commands (`/mcp`, `/mcp:list`, etc.).

### Verify Error Handling

The existing implementation already includes proper error handling:

1. **Graceful degradation** when MCP is unavailable (lines 248-286)
2. **Try-except blocks** around adapter operations (lines 280-283)
3. **User-friendly error messages** (lines 282, 1174, 1235, etc.)

### Add Shutdown Support

Update the `CommandRouter` to support graceful shutdown:

```python
def shutdown(self):
    """Gracefully shutdown the command router and close all adapter connections."""
    if self._adapter_manager_initialized and self._adapter_manager:
        try:
            self._run_async(self._adapter_manager.close_all())
            print(f"{Colors.DIM}✓ Closed all adapter connections{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.DIM}⚠ Error closing adapters: {e}{Colors.RESET}")
        finally:
            self._adapter_manager = None
            self._adapter_manager_initialized = False
```

Add to `_cmd_quit` method:

```python
def _cmd_quit(self, args: str) -> CommandResult:
    """Exit interactive mode."""
    # NEW: Shutdown adapters before quitting
    self.shutdown()
    return CommandResult(action=CommandAction.QUIT)
```

## 3. Environment Configuration

Add to `.env` or system environment:

```bash
# Enable MCP bridge support
MCP_ENABLED=true

# Optional: MCP server configurations
# (Alternatively, use ~/.claude.json or .mcp.json files)
```

## 4. Usage Examples

### Example 1: Using Thanos Orchestrator with MCP

```python
from Tools.thanos_orchestrator import ThanosOrchestrator

# Method 1: Context manager (recommended - automatic cleanup)
with ThanosOrchestrator(enable_mcp=True) as thanos:
    response = thanos.route("What should I do today?")
    print(response)
# MCP connections automatically closed on exit

# Method 2: Manual cleanup
thanos = ThanosOrchestrator(enable_mcp=True)
try:
    response = thanos.chat("I'm feeling overwhelmed", agent="coach")
    print(response)
finally:
    thanos.shutdown()  # Explicit cleanup
```

### Example 2: Using MCP Commands in Interactive Mode

```python
# In thanos_interactive.py or similar
from Tools.command_router import CommandRouter

# The router will automatically initialize MCP if MCP_ENABLED=true
router = CommandRouter(orchestrator, session, context_mgr, state_reader, thanos_dir)

# Users can now use MCP commands:
# /mcp              - Show MCP status
# /mcp:list         - List available MCP servers and tools
# /mcp:test workos  - Test WorkOS MCP server connection
# /mcp:metrics      - Show performance metrics
# /mcp:refresh      - Refresh all MCP connections
```

### Example 3: Direct Tool Calls via AdapterManager

```python
from Tools.adapters import get_default_manager
import asyncio

async def main():
    # Get manager with MCP support
    manager = await get_default_manager(enable_mcp=True)

    # Call a direct adapter tool
    result = await manager.call_tool("get_today_metrics")
    print(result.data)

    # Call an MCP bridge tool (if configured)
    result = await manager.call_tool("context7.query-docs", {
        "libraryId": "/vercel/next.js",
        "query": "authentication patterns"
    })
    print(result.data)

    # Cleanup
    await manager.close_all()

asyncio.run(main())
```

## 5. Error Handling

The integration includes comprehensive error handling:

### MCP Unavailable

```python
# If MCP SDK not installed
if not MCP_AVAILABLE:
    logger.warning("MCP SDK not available. Install with: pip install mcp>=1.0.0")
    # Continue with direct adapters only - graceful degradation
```

### Connection Failures

```python
# Individual server failures don't break the whole system
try:
    await manager.register_mcp_server(server_config)
except Exception as e:
    logger.error(f"Failed to register MCP server: {e}")
    # Continue with other servers
```

### Tool Call Failures

```python
# Tool calls return ToolResult with success/error status
result = await manager.call_tool("some_tool")
if not result.success:
    print(f"Tool failed: {result.error}")
    # Handle gracefully - don't crash the application
```

## 6. Backward Compatibility

The integration maintains 100% backward compatibility:

1. **MCP is opt-in**: Default behavior unchanged unless `enable_mcp=True` or `MCP_ENABLED=true`
2. **Direct adapters work unchanged**: WorkOS, Oura, Neo4j, ChromaDB continue to function
3. **Existing commands unchanged**: All existing `/run`, `/agent`, etc. commands work as before
4. **No breaking changes**: API remains the same, MCP features are additive

## 7. Testing

### Manual Testing Checklist

- [ ] Orchestrator initializes without MCP (`enable_mcp=False`)
- [ ] Orchestrator initializes with MCP (`enable_mcp=True`)
- [ ] MCP commands work in interactive mode (`/mcp`, `/mcp:list`)
- [ ] Direct adapter tools still work (e.g., `get_today_metrics`)
- [ ] MCP bridge tools work (if servers configured)
- [ ] Graceful shutdown closes all connections
- [ ] Context manager cleanup works correctly
- [ ] Error handling for missing MCP SDK
- [ ] Error handling for failed server connections
- [ ] Backward compatibility verified

### Integration Test Example

```python
# tests/integration/test_mcp_integration.py
import pytest
from Tools.thanos_orchestrator import ThanosOrchestrator

def test_orchestrator_without_mcp():
    """Test orchestrator works without MCP (backward compatibility)."""
    thanos = ThanosOrchestrator(enable_mcp=False)
    assert thanos is not None
    assert thanos._enable_mcp is False
    thanos.shutdown()

def test_orchestrator_with_mcp():
    """Test orchestrator initializes with MCP support."""
    thanos = ThanosOrchestrator(enable_mcp=True)
    assert thanos is not None
    assert thanos._enable_mcp is True
    thanos.shutdown()

def test_context_manager():
    """Test context manager cleanup."""
    with ThanosOrchestrator(enable_mcp=True) as thanos:
        assert thanos is not None
    # Verify connections closed (no exceptions)
```

## 8. Production Deployment

### Deployment Steps

1. **Update environment variables**:
   ```bash
   export MCP_ENABLED=true
   ```

2. **Configure MCP servers** (optional):
   Create `~/.claude.json` or `.mcp.json` with server configurations

3. **Test in staging**: Verify MCP servers connect correctly

4. **Monitor startup**: Check logs for MCP initialization messages

5. **Monitor performance**: Use `/mcp:metrics` to track server health

### Rollback Plan

If issues occur:

1. Set `MCP_ENABLED=false` to disable MCP bridges
2. Restart application - will use direct adapters only
3. All existing functionality continues to work

## 9. Monitoring and Observability

### Health Checks

```python
# Check all adapter health
manager = await get_default_manager(enable_mcp=True)
health_results = await manager.health_check_all()

for adapter_name, result in health_results.items():
    if result.success:
        print(f"✓ {adapter_name}: healthy")
    else:
        print(f"✗ {adapter_name}: {result.error}")
```

### Statistics

```python
# Get adapter statistics
stats = manager.get_stats()
print(f"Total adapters: {stats['total_adapters']}")
print(f"Direct adapters: {stats['direct_adapters']}")
print(f"MCP bridges: {stats['mcp_bridges']}")
print(f"Total tools: {stats['total_tools']}")
```

### Metrics via Commands

Users can monitor MCP health via interactive commands:
- `/mcp` - Overview and status
- `/mcp:metrics` - Detailed performance metrics
- `/mcp:test <server>` - Test specific server connection

## 10. Troubleshooting

### Issue: MCP servers not connecting

**Check:**
1. `MCP_ENABLED=true` is set
2. MCP SDK installed: `pip install mcp>=1.0.0`
3. Server configuration exists in `~/.claude.json` or `.mcp.json`
4. Server process can start (check `command` path in config)

**Debug:**
```bash
# Test server configuration
/mcp:test <server_name>

# Check logs
# Look for initialization messages in orchestrator output
```

### Issue: "AdapterManager not available"

**Solution:**
```bash
# Ensure AdapterManager is importable
python3 -c "from Tools.adapters import AdapterManager; print('OK')"

# If fails, check Tools/adapters/__init__.py exists and is correct
```

### Issue: Slow startup with MCP

**Solution:**
Set `mcp_auto_discover=False` to disable automatic server discovery:

```python
manager = await get_default_manager(
    enable_mcp=True,
    mcp_auto_discover=False  # Manual registration only
)
```

## Summary

This integration provides:

✅ **Seamless MCP integration** into Thanos orchestrator and command router
✅ **Backward compatibility** - existing functionality unchanged
✅ **Graceful error handling** - failures don't break the system
✅ **Easy configuration** - single environment variable to enable
✅ **Production-ready** - proper shutdown, monitoring, and observability
✅ **User-friendly** - interactive commands for MCP management

The changes are minimal, focused, and maintain the existing architecture while adding powerful MCP capabilities.
