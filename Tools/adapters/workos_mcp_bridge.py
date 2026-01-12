"""
WorkOS MCP Bridge

Reference implementation showing how to use MCPBridge with WorkOS MCP server.
Demonstrates best practices for MCP bridge integration.
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional

from .mcp_bridge import MCPBridge
from .mcp_config import MCPServerConfig
from .base import ToolResult

logger = logging.getLogger(__name__)


class WorkOSMCPBridge:
    """
    WorkOS MCP Bridge wrapper with convenience methods.

    This is a reference implementation showing how to:
    1. Configure an MCP server for WorkOS
    2. Initialize and connect the bridge
    3. Call tools through the MCP protocol
    4. Handle errors and retries
    5. Monitor performance

    Usage:
        bridge = WorkOSMCPBridge()
        await bridge.connect()
        result = await bridge.get_today_metrics()
        await bridge.close()
    """

    def __init__(self, server_command: Optional[str] = None):
        """
        Initialize WorkOS MCP bridge.

        Args:
            server_command: Optional custom server command.
                          Defaults to "uvx mcp-server-workos"
        """
        # Create MCP server configuration for WorkOS
        self.config = MCPServerConfig(
            name="workos",
            command=server_command or "uvx",
            args=["mcp-server-workos"],
            env={
                # WorkOS MCP server uses environment variables for config
                # These are typically set in the system environment
            },
            transport="stdio",
            description="WorkOS personal assistant MCP server"
        )

        # Create MCPBridge instance
        self.bridge = MCPBridge(self.config)

        # Performance tracking
        self._call_times: Dict[str, list[float]] = {}
        self._call_counts: Dict[str, int] = {}

    async def connect(self) -> None:
        """Initialize connection to WorkOS MCP server."""
        await self.bridge.connect()
        logger.info("WorkOS MCP bridge connected")

    async def close(self) -> None:
        """Close connection to WorkOS MCP server."""
        await self.bridge.close()
        logger.info("WorkOS MCP bridge closed")

    async def _call_with_timing(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """
        Call tool and track performance metrics.

        Args:
            tool_name: Tool to call
            arguments: Tool parameters

        Returns:
            ToolResult from the MCP server
        """
        start_time = time.time()

        try:
            result = await self.bridge.call_tool(tool_name, arguments)
        finally:
            elapsed = time.time() - start_time

            # Track timing
            if tool_name not in self._call_times:
                self._call_times[tool_name] = []
                self._call_counts[tool_name] = 0

            self._call_times[tool_name].append(elapsed)
            self._call_counts[tool_name] += 1

            # Log slow calls (>1s)
            if elapsed > 1.0:
                logger.warning(f"Slow MCP call: {tool_name} took {elapsed:.2f}s")

        return result

    # Convenience methods for common WorkOS operations
    # These mirror the direct WorkOS adapter API for compatibility

    async def get_today_metrics(self) -> ToolResult:
        """Get today's work progress metrics."""
        return await self._call_with_timing("workos_get_today_metrics")

    async def get_tasks(
        self,
        status: Optional[str] = None,
        client_id: Optional[int] = None,
        limit: Optional[int] = None
    ) -> ToolResult:
        """
        Get tasks from WorkOS.

        Args:
            status: Filter by status (active, queued, backlog, done)
            client_id: Filter by client ID
            limit: Maximum tasks to return

        Returns:
            ToolResult with tasks list
        """
        args = {}
        if status:
            args["status"] = status
        if client_id:
            args["clientId"] = client_id
        if limit:
            args["limit"] = limit

        return await self._call_with_timing("workos_get_tasks", args)

    async def get_clients(self) -> ToolResult:
        """Get all active clients."""
        return await self._call_with_timing("workos_get_clients")

    async def create_task(
        self,
        title: str,
        category: Optional[str] = None,
        client_id: Optional[int] = None,
        description: Optional[str] = None,
        drain_type: Optional[str] = None,
        value_tier: Optional[str] = None,
        status: Optional[str] = None
    ) -> ToolResult:
        """
        Create a new task in WorkOS.

        Args:
            title: Task title (required)
            category: work or personal
            client_id: Client ID to associate with
            description: Task description
            drain_type: Energy drain type (deep, shallow, admin)
            value_tier: Value tier (checkbox, progress, deliverable, milestone)
            status: Initial status (default: backlog)

        Returns:
            ToolResult with created task
        """
        args = {"title": title}
        if category:
            args["category"] = category
        if client_id:
            args["clientId"] = client_id
        if description:
            args["description"] = description
        if drain_type:
            args["drainType"] = drain_type
        if value_tier:
            args["valueTier"] = value_tier
        if status:
            args["status"] = status

        return await self._call_with_timing("workos_create_task", args)

    async def complete_task(self, task_id: int) -> ToolResult:
        """Mark a task as completed."""
        return await self._call_with_timing("workos_complete_task", {"taskId": task_id})

    async def promote_task(self, task_id: int) -> ToolResult:
        """Promote a task to 'active' (today) status."""
        return await self._call_with_timing("workos_promote_task", {"taskId": task_id})

    async def update_task(
        self,
        task_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        client_id: Optional[int] = None,
        value_tier: Optional[str] = None,
        drain_type: Optional[str] = None
    ) -> ToolResult:
        """Update a task's properties."""
        args = {"taskId": task_id}
        if title:
            args["title"] = title
        if description:
            args["description"] = description
        if status:
            args["status"] = status
        if client_id is not None:  # Allow null to unassign
            args["clientId"] = client_id
        if value_tier:
            args["valueTier"] = value_tier
        if drain_type:
            args["drainType"] = drain_type

        return await self._call_with_timing("workos_update_task", args)

    async def delete_task(self, task_id: int) -> ToolResult:
        """Permanently delete a task."""
        return await self._call_with_timing("workos_delete_task", {"taskId": task_id})

    async def get_streak(self) -> ToolResult:
        """Get current streak information."""
        return await self._call_with_timing("workos_get_streak")

    async def get_client_memory(self, client_name: str) -> ToolResult:
        """Get AI-generated notes for a client."""
        return await self._call_with_timing(
            "workos_get_client_memory",
            {"clientName": client_name}
        )

    async def daily_summary(self) -> ToolResult:
        """Get comprehensive daily summary."""
        return await self._call_with_timing("workos_daily_summary")

    async def get_habits(self) -> ToolResult:
        """Get all active habits with streaks."""
        return await self._call_with_timing("workos_get_habits")

    async def create_habit(
        self,
        name: str,
        frequency: Optional[str] = None,
        time_of_day: Optional[str] = None,
        category: Optional[str] = None,
        emoji: Optional[str] = None,
        description: Optional[str] = None,
        target_count: Optional[int] = None
    ) -> ToolResult:
        """Create a new habit to track."""
        args = {"name": name}
        if frequency:
            args["frequency"] = frequency
        if time_of_day:
            args["timeOfDay"] = time_of_day
        if category:
            args["category"] = category
        if emoji:
            args["emoji"] = emoji
        if description:
            args["description"] = description
        if target_count:
            args["targetCount"] = target_count

        return await self._call_with_timing("workos_create_habit", args)

    async def complete_habit(self, habit_id: int, note: Optional[str] = None) -> ToolResult:
        """Mark a habit as completed for today."""
        args = {"habitId": habit_id}
        if note:
            args["note"] = note

        return await self._call_with_timing("workos_complete_habit", args)

    async def brain_dump(self, content: str, category: Optional[str] = None) -> ToolResult:
        """Quick capture a thought, idea, or worry."""
        args = {"content": content}
        if category:
            args["category"] = category

        return await self._call_with_timing("workos_brain_dump", args)

    async def get_brain_dump(
        self,
        include_processed: bool = False,
        limit: Optional[int] = None
    ) -> ToolResult:
        """Get unprocessed brain dump entries."""
        args = {}
        if include_processed:
            args["includeProcessed"] = include_processed
        if limit:
            args["limit"] = limit

        return await self._call_with_timing("workos_get_brain_dump", args)

    # Performance analysis methods

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for all tool calls.

        Returns:
            Dict with per-tool timing statistics
        """
        stats = {}

        for tool_name, times in self._call_times.items():
            if times:
                stats[tool_name] = {
                    "calls": self._call_counts[tool_name],
                    "avg_time": sum(times) / len(times),
                    "min_time": min(times),
                    "max_time": max(times),
                    "total_time": sum(times)
                }

        return stats

    def print_performance_report(self) -> None:
        """Print formatted performance report to console."""
        stats = self.get_performance_stats()

        if not stats:
            print("No performance data collected yet.")
            return

        print("\n=== WorkOS MCP Bridge Performance Report ===\n")
        print(f"{'Tool':<30} {'Calls':>8} {'Avg (ms)':>10} {'Min (ms)':>10} {'Max (ms)':>10}")
        print("-" * 70)

        for tool_name, data in sorted(stats.items()):
            print(
                f"{tool_name:<30} {data['calls']:>8} "
                f"{data['avg_time']*1000:>10.1f} "
                f"{data['min_time']*1000:>10.1f} "
                f"{data['max_time']*1000:>10.1f}"
            )

        total_calls = sum(d["calls"] for d in stats.values())
        total_time = sum(d["total_time"] for d in stats.values())

        print("-" * 70)
        print(f"{'TOTAL':<30} {total_calls:>8} {total_time*1000:>10.1f} ms")
        print()


# Factory function for easy creation
async def create_workos_bridge() -> WorkOSMCPBridge:
    """
    Create and connect WorkOS MCP bridge.

    Returns:
        Connected WorkOSMCPBridge instance
    """
    bridge = WorkOSMCPBridge()
    await bridge.connect()
    return bridge
