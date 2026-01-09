# MCP Bridge Design Document

## Overview

This document outlines the architecture for enabling the Thanos Python orchestrator to call MCP tools (WorkOS, Oura) that are currently only accessible through Claude Code's MCP integration.

## Current MCP Architecture

### How MCP Works in Claude Code

```
┌─────────────────────────────────────────────────────────────────┐
│                        Claude Code                               │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │   User       │────▶│   Claude     │────▶│  MCP Client  │    │
│  │   Prompt     │     │   LLM        │     │  (internal)  │    │
│  └──────────────┘     └──────────────┘     └──────┬───────┘    │
└──────────────────────────────────────────────────┬──────────────┘
                                                   │
                    ┌──────────────────────────────┼──────────────────┐
                    │                              │                   │
           ┌────────▼────────┐           ┌────────▼────────┐         │
           │  WorkOS MCP     │           │   Oura MCP      │         │
           │  (Node.js)      │           │   (Node.js)     │         │
           │                 │           │                 │         │
           │  stdin ◀──▶ stdout        │  stdin ◀──▶ stdout        │
           └────────┬────────┘           └────────┬────────┘         │
                    │                              │                   │
           ┌────────▼────────┐           ┌────────▼────────┐         │
           │  Neon Database  │           │   Oura API      │         │
           │  (PostgreSQL)   │           │   (REST)        │         │
           └─────────────────┘           └─────────────────┘         │
```

### MCP Protocol Basics

MCP (Model Context Protocol) uses JSON-RPC 2.0 over stdio:
- **Transport**: stdin/stdout (subprocess communication)
- **Protocol**: JSON-RPC 2.0 with specific method names
- **Lifecycle**: initialize → list_tools → call_tool → shutdown

### Current MCP Server Configurations

From `~/.claude.json`, the Thanos project has these MCP servers:

```json
{
  "workos-mcp": {
    "type": "stdio",
    "command": "node",
    "args": ["/Users/jeremy/Projects/Thanos/mcp-servers/workos-mcp/dist/index.js"],
    "env": {
      "WORKOS_DATABASE_URL": "postgresql://..."
    }
  },
  "oura": {
    "type": "stdio",
    "command": "node",
    "args": ["/Users/jeremy/mcp-servers/oura-mcp/build/index.js"],
    "env": {
      "OURA_PERSONAL_ACCESS_TOKEN": "..."
    }
  }
}
```

## Design Options

### Option 1: Direct Database/API Access (Recommended for v1)

**Approach**: Bypass MCP entirely and connect directly to the underlying data sources.

```
┌─────────────────────────────────────────────────────────────────┐
│                      Thanos Orchestrator                         │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │  Scheduler   │────▶│   Router     │────▶│  Adapters    │    │
│  └──────────────┘     └──────────────┘     └──────┬───────┘    │
└──────────────────────────────────────────────────┬──────────────┘
                                                   │
                    ┌──────────────────────────────┼──────────────────┐
                    │                              │                   │
           ┌────────▼────────┐           ┌────────▼────────┐         │
           │  NeonAdapter    │           │   OuraAdapter   │         │
           │  (psycopg2)     │           │   (requests)    │         │
           └────────┬────────┘           └────────┬────────┘         │
                    │                              │                   │
           ┌────────▼────────┐           ┌────────▼────────┐         │
           │  Neon Database  │           │   Oura API      │         │
           └─────────────────┘           └─────────────────┘         │
```

**Pros**:
- Simplest implementation
- No subprocess overhead
- Full control over queries
- No MCP protocol complexity

**Cons**:
- Duplicates logic from MCP servers
- Must maintain two implementations
- Loses MCP abstraction benefits

### Option 2: Python MCP Client (Recommended for v2)

**Approach**: Use the official Python MCP SDK to spawn and communicate with MCP servers.

```
┌─────────────────────────────────────────────────────────────────┐
│                      Thanos Orchestrator                         │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │  Scheduler   │────▶│   MCPBridge  │────▶│  MCPClient   │    │
│  └──────────────┘     └──────────────┘     └──────┬───────┘    │
└──────────────────────────────────────────────────┬──────────────┘
                                                   │ (JSON-RPC over stdio)
                    ┌──────────────────────────────┼──────────────────┐
                    │                              │                   │
           ┌────────▼────────┐           ┌────────▼────────┐         │
           │  WorkOS MCP     │           │   Oura MCP      │         │
           │  (subprocess)   │           │   (subprocess)  │         │
           └────────┬────────┘           └────────┬────────┘         │
                    │                              │                   │
           ┌────────▼────────┐           ┌────────▼────────┐         │
           │  Neon Database  │           │   Oura API      │         │
           └─────────────────┘           └─────────────────┘         │
```

**Pros**:
- Reuses existing MCP server code
- Single source of truth for tool logic
- Works with any MCP server
- Future-proof for adding more servers

**Cons**:
- Subprocess overhead per call
- Async complexity
- Dependency on MCP Python SDK

### Option 3: HTTP/REST Bridge (Future Consideration)

**Approach**: Add HTTP endpoints to MCP servers for direct REST access.

Not recommended for now - adds complexity without clear benefit.

## Recommended Implementation: Hybrid Approach

**Phase 1 (v1)**: Direct database/API adapters for critical paths
**Phase 2 (v2)**: MCP Python client for full tool access

This gives us:
- Fast, reliable v1 implementation
- Clean path to full MCP integration
- Flexibility to choose per-tool

## Implementation Details

### Phase 1: Direct Adapters

#### Directory Structure

```
/Users/jeremy/Projects/Thanos/
├── Tools/
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py           # Abstract base adapter
│   │   ├── workos.py         # WorkOS/Neon adapter
│   │   ├── oura.py           # Oura API adapter
│   │   └── mcp_bridge.py     # Future MCP bridge
│   ├── thanos_orchestrator.py
│   └── claude_api_client.py
```

#### Base Adapter Interface

```python
# /Users/jeremy/Projects/Thanos/Tools/adapters/base.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ToolResult:
    """Standard result from any adapter tool call."""
    success: bool
    data: Any
    error: Optional[str] = None

class BaseAdapter(ABC):
    """Abstract base class for all Thanos adapters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Adapter identifier."""
        pass

    @abstractmethod
    def list_tools(self) -> List[Dict[str, Any]]:
        """Return list of available tools with their schemas."""
        pass

    @abstractmethod
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Execute a tool and return the result."""
        pass

    def validate_arguments(self, tool_name: str, arguments: Dict[str, Any]) -> bool:
        """Validate arguments against tool schema."""
        # Default implementation - can be overridden
        tools = {t['name']: t for t in self.list_tools()}
        if tool_name not in tools:
            return False
        # TODO: JSON Schema validation
        return True
```

#### WorkOS Adapter

```python
# /Users/jeremy/Projects/Thanos/Tools/adapters/workos.py

import os
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import asyncpg
from .base import BaseAdapter, ToolResult

class WorkOSAdapter(BaseAdapter):
    """Direct adapter for WorkOS/Neon database operations."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.environ.get(
            'WORKOS_DATABASE_URL',
            os.environ.get('DATABASE_URL')
        )
        self._pool: Optional[asyncpg.Pool] = None

    @property
    def name(self) -> str:
        return "workos"

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=5
            )
        return self._pool

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "get_tasks",
                "description": "Get tasks by status",
                "parameters": {
                    "status": {"type": "string", "enum": ["active", "queued", "backlog", "done"]},
                    "limit": {"type": "integer", "default": 50}
                }
            },
            {
                "name": "get_today_metrics",
                "description": "Get today's work progress metrics",
                "parameters": {}
            },
            {
                "name": "complete_task",
                "description": "Mark a task as complete",
                "parameters": {
                    "task_id": {"type": "integer", "required": True}
                }
            },
            {
                "name": "create_task",
                "description": "Create a new task",
                "parameters": {
                    "title": {"type": "string", "required": True},
                    "description": {"type": "string"},
                    "status": {"type": "string", "default": "backlog"},
                    "client_id": {"type": "integer"}
                }
            },
            {
                "name": "get_habits",
                "description": "Get all active habits",
                "parameters": {}
            },
            {
                "name": "complete_habit",
                "description": "Mark a habit as complete for today",
                "parameters": {
                    "habit_id": {"type": "integer", "required": True}
                }
            },
            {
                "name": "daily_summary",
                "description": "Get comprehensive daily summary",
                "parameters": {}
            }
        ]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        try:
            pool = await self._get_pool()

            if tool_name == "get_tasks":
                return await self._get_tasks(pool, **arguments)
            elif tool_name == "get_today_metrics":
                return await self._get_today_metrics(pool)
            elif tool_name == "complete_task":
                return await self._complete_task(pool, **arguments)
            elif tool_name == "create_task":
                return await self._create_task(pool, **arguments)
            elif tool_name == "get_habits":
                return await self._get_habits(pool)
            elif tool_name == "complete_habit":
                return await self._complete_habit(pool, **arguments)
            elif tool_name == "daily_summary":
                return await self._daily_summary(pool)
            else:
                return ToolResult(success=False, data=None, error=f"Unknown tool: {tool_name}")

        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

    async def _get_tasks(self, pool: asyncpg.Pool, status: str = None, limit: int = 50) -> ToolResult:
        async with pool.acquire() as conn:
            if status:
                rows = await conn.fetch(
                    """
                    SELECT t.*, c.name as client_name
                    FROM tasks t
                    LEFT JOIN clients c ON t.client_id = c.id
                    WHERE t.status = $1
                    ORDER BY t.sort_order ASC, t.created_at DESC
                    LIMIT $2
                    """,
                    status, limit
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT t.*, c.name as client_name
                    FROM tasks t
                    LEFT JOIN clients c ON t.client_id = c.id
                    ORDER BY t.sort_order ASC, t.created_at DESC
                    LIMIT $1
                    """,
                    limit
                )
            return ToolResult(success=True, data=[dict(r) for r in rows])

    async def _get_today_metrics(self, pool: asyncpg.Pool) -> ToolResult:
        async with pool.acquire() as conn:
            # Get EST midnight
            today_start = self._get_est_today_start()

            # Get completed tasks today
            completed = await conn.fetch(
                """
                SELECT * FROM tasks
                WHERE status = 'done' AND completed_at >= $1
                """,
                today_start
            )

            earned_points = sum(
                r.get('points_final') or r.get('points_ai_guess') or r.get('effort_estimate') or 2
                for r in completed
            )

            # Get streak
            streak_row = await conn.fetchrow(
                "SELECT current_streak FROM daily_goals ORDER BY date DESC LIMIT 1"
            )

            return ToolResult(success=True, data={
                "completed_count": len(completed),
                "earned_points": earned_points,
                "target_points": 18,
                "minimum_points": 12,
                "streak": streak_row['current_streak'] if streak_row else 0
            })

    async def _complete_task(self, pool: asyncpg.Pool, task_id: int) -> ToolResult:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE tasks
                SET status = 'done', completed_at = NOW(), updated_at = NOW()
                WHERE id = $1
                RETURNING *
                """,
                task_id
            )
            if row:
                return ToolResult(success=True, data=dict(row))
            return ToolResult(success=False, data=None, error=f"Task {task_id} not found")

    async def _create_task(self, pool: asyncpg.Pool, title: str,
                          description: str = None, status: str = "backlog",
                          client_id: int = None) -> ToolResult:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO tasks (title, description, status, client_id, updated_at)
                VALUES ($1, $2, $3, $4, NOW())
                RETURNING *
                """,
                title, description, status, client_id
            )
            return ToolResult(success=True, data=dict(row))

    async def _get_habits(self, pool: asyncpg.Pool) -> ToolResult:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM habits WHERE is_active = 1 ORDER BY sort_order"
            )
            return ToolResult(success=True, data=[dict(r) for r in rows])

    async def _complete_habit(self, pool: asyncpg.Pool, habit_id: int) -> ToolResult:
        async with pool.acquire() as conn:
            # Insert completion
            await conn.execute(
                "INSERT INTO habit_completions (habit_id) VALUES ($1)",
                habit_id
            )
            # Update habit streak
            today_str = datetime.now().strftime('%Y-%m-%d')
            row = await conn.fetchrow(
                """
                UPDATE habits
                SET current_streak = current_streak + 1,
                    longest_streak = GREATEST(longest_streak, current_streak + 1),
                    last_completed_date = $1,
                    updated_at = NOW()
                WHERE id = $2
                RETURNING *
                """,
                today_str, habit_id
            )
            return ToolResult(success=True, data=dict(row) if row else None)

    async def _daily_summary(self, pool: asyncpg.Pool) -> ToolResult:
        metrics = await self._get_today_metrics(pool)
        active = await self._get_tasks(pool, status="active")
        queued = await self._get_tasks(pool, status="queued", limit=5)
        habits = await self._get_habits(pool)

        return ToolResult(success=True, data={
            "progress": metrics.data,
            "active_tasks": active.data,
            "queued_tasks": queued.data,
            "habits": habits.data
        })

    def _get_est_today_start(self) -> datetime:
        """Get UTC timestamp for midnight EST today."""
        from zoneinfo import ZoneInfo
        est = ZoneInfo('America/New_York')
        now_est = datetime.now(est)
        midnight_est = now_est.replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight_est.astimezone(ZoneInfo('UTC')).replace(tzinfo=None)

    async def close(self):
        if self._pool:
            await self._pool.close()
```

#### Oura Adapter

```python
# /Users/jeremy/Projects/Thanos/Tools/adapters/oura.py

import os
import httpx
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from .base import BaseAdapter, ToolResult

class OuraAdapter(BaseAdapter):
    """Direct adapter for Oura Ring API."""

    BASE_URL = "https://api.ouraring.com/v2"

    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or os.environ.get('OURA_PERSONAL_ACCESS_TOKEN')
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def name(self) -> str:
        return "oura"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=30.0
            )
        return self._client

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "get_daily_readiness",
                "description": "Get daily readiness scores",
                "parameters": {
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"}
                }
            },
            {
                "name": "get_daily_sleep",
                "description": "Get daily sleep scores",
                "parameters": {
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"}
                }
            },
            {
                "name": "get_sleep",
                "description": "Get detailed sleep sessions",
                "parameters": {
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"}
                }
            },
            {
                "name": "get_daily_activity",
                "description": "Get daily activity data",
                "parameters": {
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"}
                }
            },
            {
                "name": "get_daily_stress",
                "description": "Get daily stress data",
                "parameters": {
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"}
                }
            },
            {
                "name": "get_workout",
                "description": "Get workout sessions",
                "parameters": {
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"}
                }
            }
        ]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        try:
            client = await self._get_client()

            # Default date range: today
            today = datetime.now().strftime('%Y-%m-%d')
            start_date = arguments.get('start_date', today)
            end_date = arguments.get('end_date', today)

            endpoint_map = {
                "get_daily_readiness": "/usercollection/daily_readiness",
                "get_daily_sleep": "/usercollection/daily_sleep",
                "get_sleep": "/usercollection/sleep",
                "get_daily_activity": "/usercollection/daily_activity",
                "get_daily_stress": "/usercollection/daily_stress",
                "get_workout": "/usercollection/workout"
            }

            if tool_name not in endpoint_map:
                return ToolResult(success=False, data=None, error=f"Unknown tool: {tool_name}")

            response = await client.get(
                endpoint_map[tool_name],
                params={"start_date": start_date, "end_date": end_date}
            )
            response.raise_for_status()
            data = response.json()

            return ToolResult(success=True, data=data.get('data', data))

        except httpx.HTTPStatusError as e:
            return ToolResult(success=False, data=None, error=f"HTTP {e.response.status_code}: {e.response.text}")
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

    async def close(self):
        if self._client:
            await self._client.aclose()
```

### Phase 2: MCP Python Client Bridge

For full MCP protocol support, use the official Python SDK:

```python
# /Users/jeremy/Projects/Thanos/Tools/adapters/mcp_bridge.py

import asyncio
import json
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager
from .base import BaseAdapter, ToolResult

# Requires: pip install mcp
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPServerConfig:
    """Configuration for an MCP server."""
    def __init__(self, name: str, command: str, args: List[str], env: Dict[str, str] = None):
        self.name = name
        self.command = command
        self.args = args
        self.env = env or {}

class MCPBridge(BaseAdapter):
    """
    Bridge adapter that spawns MCP servers as subprocesses
    and communicates via JSON-RPC over stdio.
    """

    def __init__(self, server_config: MCPServerConfig):
        self.config = server_config
        self._session: Optional[ClientSession] = None
        self._tools_cache: Optional[List[Dict[str, Any]]] = None

    @property
    def name(self) -> str:
        return self.config.name

    @asynccontextmanager
    async def _get_session(self):
        """Create a session with the MCP server."""
        import os

        # Merge environment variables
        env = {**os.environ, **self.config.env}

        server_params = StdioServerParameters(
            command=self.config.command,
            args=self.config.args,
            env=env
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return cached tools list. Call refresh_tools() to update."""
        if self._tools_cache is None:
            # Run async in sync context
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.refresh_tools())
        return self._tools_cache or []

    async def refresh_tools(self) -> List[Dict[str, Any]]:
        """Fetch and cache the tools list from the MCP server."""
        async with self._get_session() as session:
            result = await session.list_tools()
            self._tools_cache = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
                for tool in result.tools
            ]
            return self._tools_cache

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Call a tool on the MCP server."""
        try:
            async with self._get_session() as session:
                result = await session.call_tool(tool_name, arguments)

                # Parse result content
                if result.content and len(result.content) > 0:
                    content = result.content[0]
                    if hasattr(content, 'text'):
                        try:
                            data = json.loads(content.text)
                        except json.JSONDecodeError:
                            data = content.text
                    else:
                        data = str(content)

                    return ToolResult(
                        success=not result.isError,
                        data=data,
                        error=None if not result.isError else str(data)
                    )

                return ToolResult(success=True, data=None)

        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))


# Factory function to create MCP bridges from claude.json config
def create_mcp_bridges_from_config(config_path: str = "~/.claude.json") -> Dict[str, MCPBridge]:
    """
    Parse Claude's MCP configuration and create bridge adapters.

    Returns:
        Dict mapping server name to MCPBridge instance
    """
    import os
    import json

    config_path = os.path.expanduser(config_path)

    with open(config_path) as f:
        config = json.load(f)

    bridges = {}

    # Get project-specific servers
    project_path = os.getcwd()
    project_config = config.get('projects', {}).get(project_path, {})
    servers = project_config.get('mcpServers', {})

    # Also check global servers
    global_servers = config.get('mcpServers', {})
    servers = {**global_servers, **servers}

    for name, server_config in servers.items():
        if server_config.get('type') == 'stdio':
            bridge = MCPBridge(MCPServerConfig(
                name=name,
                command=server_config['command'],
                args=server_config.get('args', []),
                env=server_config.get('env', {})
            ))
            bridges[name] = bridge

    return bridges
```

### Unified Adapter Manager

```python
# /Users/jeremy/Projects/Thanos/Tools/adapters/__init__.py

from typing import Dict, Any, Optional
from .base import BaseAdapter, ToolResult
from .workos import WorkOSAdapter
from .oura import OuraAdapter

class AdapterManager:
    """
    Unified interface for all Thanos adapters.
    Routes tool calls to appropriate adapters.
    """

    def __init__(self):
        self._adapters: Dict[str, BaseAdapter] = {}
        self._tool_map: Dict[str, str] = {}  # tool_name -> adapter_name

    def register(self, adapter: BaseAdapter):
        """Register an adapter and index its tools."""
        self._adapters[adapter.name] = adapter
        for tool in adapter.list_tools():
            # Prefix with adapter name to avoid conflicts
            full_name = f"{adapter.name}.{tool['name']}"
            self._tool_map[full_name] = adapter.name
            # Also allow short names if unique
            if tool['name'] not in self._tool_map:
                self._tool_map[tool['name']] = adapter.name

    def list_all_tools(self) -> Dict[str, list]:
        """List all available tools grouped by adapter."""
        return {
            name: adapter.list_tools()
            for name, adapter in self._adapters.items()
        }

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> ToolResult:
        """Route a tool call to the appropriate adapter."""
        arguments = arguments or {}

        # Handle prefixed tool names (e.g., "workos.get_tasks")
        if '.' in tool_name:
            adapter_name, short_name = tool_name.split('.', 1)
            if adapter_name in self._adapters:
                return await self._adapters[adapter_name].call_tool(short_name, arguments)

        # Try to find adapter for unprefixed tool name
        if tool_name in self._tool_map:
            adapter_name = self._tool_map[tool_name]
            return await self._adapters[adapter_name].call_tool(tool_name, arguments)

        return ToolResult(
            success=False,
            data=None,
            error=f"Unknown tool: {tool_name}. Available: {list(self._tool_map.keys())}"
        )

    async def close_all(self):
        """Close all adapter connections."""
        for adapter in self._adapters.values():
            if hasattr(adapter, 'close'):
                await adapter.close()


# Default manager instance
_default_manager: Optional[AdapterManager] = None

async def get_default_manager() -> AdapterManager:
    """Get or create the default adapter manager."""
    global _default_manager

    if _default_manager is None:
        _default_manager = AdapterManager()

        # Register adapters
        _default_manager.register(WorkOSAdapter())
        _default_manager.register(OuraAdapter())

    return _default_manager
```

## Usage Examples

### Basic Tool Call

```python
import asyncio
from Tools.adapters import get_default_manager

async def main():
    manager = await get_default_manager()

    # Get today's metrics
    result = await manager.call_tool("get_today_metrics")
    if result.success:
        print(f"Points earned: {result.data['earned_points']}")

    # Get Oura readiness
    result = await manager.call_tool("oura.get_daily_readiness", {
        "start_date": "2026-01-08",
        "end_date": "2026-01-08"
    })
    if result.success:
        print(f"Readiness: {result.data}")

    await manager.close_all()

asyncio.run(main())
```

### Integration with Orchestrator

```python
# In thanos_orchestrator.py

class ThanosOrchestrator:
    def __init__(self):
        self.adapter_manager = None

    async def initialize(self):
        from Tools.adapters import get_default_manager
        self.adapter_manager = await get_default_manager()

    async def get_daily_context(self) -> dict:
        """Gather all context for daily briefing."""

        # Get WorkOS data
        summary = await self.adapter_manager.call_tool("daily_summary")

        # Get Oura data
        today = datetime.now().strftime('%Y-%m-%d')
        readiness = await self.adapter_manager.call_tool("oura.get_daily_readiness", {
            "start_date": today,
            "end_date": today
        })
        sleep = await self.adapter_manager.call_tool("oura.get_daily_sleep", {
            "start_date": today,
            "end_date": today
        })

        return {
            "workos": summary.data if summary.success else None,
            "oura": {
                "readiness": readiness.data if readiness.success else None,
                "sleep": sleep.data if sleep.success else None
            }
        }
```

## Dependencies

### Python Requirements

```
# requirements.txt
asyncpg>=0.29.0        # PostgreSQL async driver
httpx>=0.27.0          # Async HTTP client
mcp>=1.0.0             # MCP SDK (Phase 2)
```

### Environment Variables

```bash
# WorkOS/Neon
WORKOS_DATABASE_URL=postgresql://...

# Oura
OURA_PERSONAL_ACCESS_TOKEN=...
```

## Security Considerations

1. **Credentials**: Store in environment variables, never in code
2. **Database**: Use connection pooling, parameterized queries
3. **API Tokens**: Rotate periodically, use least-privilege access
4. **MCP Bridge**: Validate tool names and arguments before execution

## Future Enhancements

1. **Caching Layer**: Add Redis/SQLite caching for frequent queries
2. **Rate Limiting**: Respect API rate limits (especially Oura)
3. **Retry Logic**: Automatic retries with exponential backoff
4. **Metrics**: Track tool call latency and success rates
5. **More Adapters**: Calendar, email, notes integration

## References

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Specification](https://modelcontextprotocol.info/)
- [Oura API v2 Documentation](https://cloud.ouraring.com/docs/)
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/)
