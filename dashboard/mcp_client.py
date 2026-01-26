"""
MCP Client for Dashboard API.

Provides async MCP client for WorkOS and Oura MCP server communication.
Wraps MCPBridge infrastructure for simplified dashboard integration.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Initialize logger first
logger = logging.getLogger(__name__)

# Lazy imports to handle missing dependencies gracefully
try:
    from Tools.adapters.mcp_bridge import MCPBridge
    from Tools.adapters.mcp_config import MCPServerConfig, StdioConfig
    from Tools.adapters.base import ToolResult
    MCP_AVAILABLE = True
except ImportError as e:
    logger.warning(f"MCP dependencies not available: {e}")
    MCP_AVAILABLE = False
    MCPBridge = None
    MCPServerConfig = None
    StdioConfig = None
    ToolResult = None

from dashboard.config import config


class MCPClient:
    """
    Async MCP client for dashboard API endpoints.

    Provides simplified interface to WorkOS and Oura MCP servers for
    fetching tasks, energy, health, and correlation data.

    The client creates sessions per-call (no persistent connection) for
    reliability and simplicity.
    """

    def __init__(self):
        """Initialize MCP client with server configurations."""
        self._workos_bridge: Optional[MCPBridge] = None
        self._oura_bridge: Optional[MCPBridge] = None
        self._lock = asyncio.Lock()
        self._init_bridges()

    def _init_bridges(self):
        """Initialize MCPBridge instances for WorkOS and Oura."""
        if not MCP_AVAILABLE:
            logger.warning("MCP dependencies not available, bridges will not be initialized")
            return

        try:
            # Initialize WorkOS MCP bridge
            if config.mcp_paths.workos_mcp.exists():
                workos_config = MCPServerConfig(
                    name="workos-mcp",
                    transport=StdioConfig(
                        command="bun",
                        args=["run", str(config.mcp_paths.workos_mcp)],
                        env={}
                    ),
                    description="WorkOS productivity database MCP server"
                )
                self._workos_bridge = MCPBridge(workos_config)
                logger.info(f"WorkOS MCP bridge initialized: {config.mcp_paths.workos_mcp}")
            else:
                logger.warning(f"WorkOS MCP server not found at {config.mcp_paths.workos_mcp}")

            # Initialize Oura MCP bridge if path is configured
            if config.mcp_paths.oura_mcp and config.mcp_paths.oura_mcp.exists():
                oura_config = MCPServerConfig(
                    name="oura-mcp",
                    transport=StdioConfig(
                        command="node",
                        args=[str(config.mcp_paths.oura_mcp)],
                        env={}
                    ),
                    description="Oura Ring health metrics MCP server"
                )
                self._oura_bridge = MCPBridge(oura_config)
                logger.info(f"Oura MCP bridge initialized: {config.mcp_paths.oura_mcp}")
            else:
                logger.warning(f"Oura MCP server not found or not configured")

        except Exception as e:
            logger.error(f"Failed to initialize MCP bridges: {e}", exc_info=True)

    async def get_tasks(self, status: str = "active") -> Optional[List[Dict[str, Any]]]:
        """
        Get tasks from WorkOS MCP.

        Args:
            status: Task status filter ('active', 'completed', or 'all')

        Returns:
            List of task dictionaries or None on failure
        """
        if not self._workos_bridge:
            logger.error("WorkOS MCP bridge not initialized")
            return None

        try:
            result: ToolResult = await self._workos_bridge.call_tool(
                "workos_get_tasks",
                {"status": status}
            )

            if result.success and result.data:
                return result.data

            logger.warning(f"Failed to get tasks: {result.error}")
            return []

        except Exception as e:
            logger.error(f"Error getting tasks: {e}", exc_info=True)
            return None

    async def get_energy_logs(self, days: int = 7) -> Optional[List[Dict[str, Any]]]:
        """
        Get energy logs from WorkOS MCP.

        Args:
            days: Number of days to retrieve (default: 7)

        Returns:
            List of energy log dictionaries or None on failure
        """
        if not self._workos_bridge:
            logger.error("WorkOS MCP bridge not initialized")
            return None

        try:
            result: ToolResult = await self._workos_bridge.call_tool(
                "workos_get_energy_logs",
                {"days": days}
            )

            if result.success and result.data:
                return result.data

            logger.warning(f"Failed to get energy logs: {result.error}")
            return []

        except Exception as e:
            logger.error(f"Error getting energy logs: {e}", exc_info=True)
            return None

    async def get_today_metrics(self) -> Optional[Dict[str, Any]]:
        """
        Get today's productivity metrics from WorkOS MCP.

        Returns:
            Dictionary with today's metrics (points, target, streak) or None on failure
        """
        if not self._workos_bridge:
            logger.error("WorkOS MCP bridge not initialized")
            return None

        try:
            result: ToolResult = await self._workos_bridge.call_tool(
                "workos_get_today_metrics",
                {}
            )

            if result.success and result.data:
                return result.data

            logger.warning(f"Failed to get today metrics: {result.error}")
            return None

        except Exception as e:
            logger.error(f"Error getting today metrics: {e}", exc_info=True)
            return None

    async def get_readiness(self, days: int = 7) -> Optional[List[Dict[str, Any]]]:
        """
        Get readiness data from Oura MCP.

        Args:
            days: Number of days to retrieve (default: 7)

        Returns:
            List of readiness dictionaries or None on failure
        """
        if not self._oura_bridge:
            logger.warning("Oura MCP bridge not initialized")
            return None

        try:
            result: ToolResult = await self._oura_bridge.call_tool(
                "oura__get_daily_readiness",
                {"days": days}
            )

            if result.success and result.data:
                return result.data

            logger.warning(f"Failed to get readiness data: {result.error}")
            return []

        except Exception as e:
            logger.error(f"Error getting readiness data: {e}", exc_info=True)
            return None

    async def get_sleep(self, days: int = 7) -> Optional[List[Dict[str, Any]]]:
        """
        Get sleep data from Oura MCP.

        Args:
            days: Number of days to retrieve (default: 7)

        Returns:
            List of sleep dictionaries or None on failure
        """
        if not self._oura_bridge:
            logger.warning("Oura MCP bridge not initialized")
            return None

        try:
            result: ToolResult = await self._oura_bridge.call_tool(
                "oura__get_daily_sleep",
                {"days": days}
            )

            if result.success and result.data:
                return result.data

            logger.warning(f"Failed to get sleep data: {result.error}")
            return []

        except Exception as e:
            logger.error(f"Error getting sleep data: {e}", exc_info=True)
            return None

    async def get_habits(self, time_of_day: str = "all") -> Optional[List[Dict[str, Any]]]:
        """
        Get habits from WorkOS MCP.

        Args:
            time_of_day: Filter by time ('morning', 'evening', 'all')

        Returns:
            List of habit dictionaries or None on failure
        """
        if not self._workos_bridge:
            logger.error("WorkOS MCP bridge not initialized")
            return None

        try:
            result: ToolResult = await self._workos_bridge.call_tool(
                "life_habit_checkin",
                {"timeOfDay": time_of_day}
            )

            if result.success and result.data:
                return result.data

            logger.warning(f"Failed to get habits: {result.error}")
            return []

        except Exception as e:
            logger.error(f"Error getting habits: {e}", exc_info=True)
            return None

    async def get_correlations(self, days: int = 7) -> Optional[Dict[str, Any]]:
        """
        Get productivity correlations combining tasks, energy, and readiness data.

        Correlates task completion with energy levels and Oura readiness scores
        to identify patterns between physical state and productivity.

        Args:
            days: Number of days to analyze (default: 7)

        Returns:
            Dictionary with correlation data or None on failure
        """
        try:
            # Fetch data from multiple sources in parallel
            logger.info(f"Fetching correlation data for {days} days")

            # Get completed tasks
            tasks = await self.get_tasks(status="done")

            # Get energy logs
            energy_logs = await self.get_energy_logs(days=days)

            # Get readiness data
            readiness_data = await self.get_readiness(days=days)

            # Handle partial failures gracefully
            if tasks is None:
                tasks = []
            if energy_logs is None:
                energy_logs = []
            if readiness_data is None:
                readiness_data = []

            # Build correlation dataset
            # Group by date and compute aggregates
            from collections import defaultdict
            from datetime import datetime

            daily_data = defaultdict(lambda: {
                "date": None,
                "tasks_completed": 0,
                "points_earned": 0,
                "energy_level": None,
                "readiness_score": None
            })

            # Process completed tasks
            for task in tasks:
                if task.get("completedAt"):
                    # Extract date from timestamp
                    completed_date = task["completedAt"][:10]  # YYYY-MM-DD
                    daily_data[completed_date]["date"] = completed_date
                    daily_data[completed_date]["tasks_completed"] += 1
                    daily_data[completed_date]["points_earned"] += task.get("points", 0)

            # Process energy logs
            for log in energy_logs:
                log_date = log.get("date", log.get("timestamp", ""))[:10]
                if log_date:
                    daily_data[log_date]["date"] = log_date
                    # Map energy level to numeric value (high=3, medium=2, low=1)
                    energy_map = {"high": 3, "medium": 2, "low": 1}
                    daily_data[log_date]["energy_level"] = energy_map.get(
                        log.get("level", "medium"),
                        2
                    )

            # Process readiness data
            for item in readiness_data:
                ready_date = item.get("day", item.get("date", ""))[:10]
                if ready_date:
                    daily_data[ready_date]["date"] = ready_date
                    daily_data[ready_date]["readiness_score"] = item.get("score", 0)

            # Convert to sorted list
            correlation_data = sorted(
                [v for v in daily_data.values() if v["date"]],
                key=lambda x: x["date"]
            )

            # Compute simple correlation coefficients if we have enough data
            correlation_stats = {}
            if len(correlation_data) >= 3:
                # Energy vs Tasks
                energy_task_pairs = [
                    (d["energy_level"], d["tasks_completed"])
                    for d in correlation_data
                    if d["energy_level"] is not None
                ]

                # Readiness vs Points
                readiness_points_pairs = [
                    (d["readiness_score"], d["points_earned"])
                    for d in correlation_data
                    if d["readiness_score"] is not None
                ]

                correlation_stats = {
                    "energy_task_correlation": len(energy_task_pairs),
                    "readiness_points_correlation": len(readiness_points_pairs)
                }

            return {
                "daily_data": correlation_data,
                "stats": correlation_stats,
                "days_analyzed": days
            }

        except Exception as e:
            logger.error(f"Error getting correlations: {e}", exc_info=True)
            return None

    async def close(self):
        """
        Close MCP connections.

        Note: MCPBridge uses session-per-call pattern, so minimal cleanup needed.
        """
        async with self._lock:
            if self._workos_bridge:
                try:
                    await self._workos_bridge.close()
                    logger.debug("WorkOS MCP bridge closed")
                except Exception as e:
                    logger.error(f"Error closing WorkOS bridge: {e}")
                finally:
                    self._workos_bridge = None

            if self._oura_bridge:
                try:
                    await self._oura_bridge.close()
                    logger.debug("Oura MCP bridge closed")
                except Exception as e:
                    logger.error(f"Error closing Oura bridge: {e}")
                finally:
                    self._oura_bridge = None


# Global client instance (singleton)
_client: Optional[MCPClient] = None


def get_client() -> MCPClient:
    """
    Get the global MCP client instance.

    Returns:
        MCPClient singleton instance
    """
    global _client
    if _client is None:
        _client = MCPClient()
    return _client


async def close_client():
    """Close the global MCP client instance."""
    global _client
    if _client:
        await _client.close()
        _client = None
