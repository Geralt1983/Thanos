#!/usr/bin/env python3
"""
MCP Client for Operator Monitors

Provides async MCP client for WorkOS and Oura integrations.
Uses the MCPBridge infrastructure with circuit breaker resilience.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from Tools.adapters.mcp_bridge import MCPBridge
from Tools.adapters.mcp_config import MCPServerConfig, StdioConfig
from Tools.adapters.base import ToolResult
from Tools.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class OperatorMCPClient:
    """
    Async MCP client for Operator daemon monitors.

    Uses MCPBridge for WorkOS integration with circuit breaker protection.
    MCPBridge uses session-per-call pattern (no persistent connection).
    """

    def __init__(self, circuit: CircuitBreaker):
        """
        Initialize MCP client with circuit breaker.

        Args:
            circuit: Circuit breaker for resilient MCP calls
        """
        self.circuit = circuit
        self._bridge: Optional[MCPBridge] = None
        self._init_bridge()

    def _init_bridge(self):
        """Initialize MCPBridge instance."""
        try:
            # Find local WorkOS MCP server
            project_root = Path(__file__).parent.parent
            workos_server = project_root / "mcp-servers" / "workos-mcp" / "dist" / "index.js"

            # Create WorkOS MCP configuration using Bun (has built-in SQLite)
            config = MCPServerConfig(
                name="workos",
                transport=StdioConfig(
                    command="bun",
                    args=["run", str(workos_server)],
                    env={}
                ),
                description="WorkOS personal assistant MCP server"
            )

            self._bridge = MCPBridge(config)
            logger.debug(f"MCPBridge initialized for WorkOS (local: {workos_server})")
        except Exception as e:
            logger.error(f"Failed to initialize MCPBridge: {e}")
            self._bridge = None

    async def get_active_tasks(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get active tasks from WorkOS.

        Returns:
            List of task dictionaries or None on failure
        """
        if not self._bridge:
            logger.error("MCPBridge not initialized")
            return None

        try:
            # Use circuit breaker to call MCP tool
            async def call_mcp():
                result: ToolResult = await self._bridge.call_tool(
                    "workos_get_tasks",
                    {"status": "active"}
                )
                return result

            # Circuit breaker returns (result, metadata) tuple
            result, metadata = await self.circuit.call(
                func=call_mcp,
                fallback=lambda: ToolResult(success=False, data=None)
            )

            if result and result.success and result.data:
                return result.data
            return []

        except Exception as e:
            logger.error(f"Failed to get active tasks: {e}", exc_info=True)
            return None

    async def get_today_metrics(self) -> Optional[Dict[str, Any]]:
        """
        Get today's WorkOS metrics (points, target, streak).

        Returns:
            Metrics dictionary or None on failure
        """
        if not self._bridge:
            logger.error("MCPBridge not initialized")
            return None

        try:
            async def call_mcp():
                result: ToolResult = await self._bridge.call_tool(
                    "workos_get_today_metrics",
                    {}
                )
                return result

            # Circuit breaker returns (result, metadata) tuple
            result, metadata = await self.circuit.call(
                func=call_mcp,
                fallback=lambda: ToolResult(success=False, data=None)
            )

            if result and result.success and result.data:
                return result.data
            return None

        except Exception as e:
            logger.error(f"Failed to get today metrics: {e}", exc_info=True)
            return None

    async def get_habits_due(self, time_of_day: str = "all") -> Optional[List[Dict[str, Any]]]:
        """
        Get habits due for check-in.

        Args:
            time_of_day: Filter by time ('morning', 'evening', 'all')

        Returns:
            List of habit dictionaries or None on failure
        """
        if not self._bridge:
            logger.error("MCPBridge not initialized")
            return None

        try:
            async def call_mcp():
                result: ToolResult = await self._bridge.call_tool(
                    "life_habit_checkin",
                    {"timeOfDay": time_of_day}
                )
                return result

            # Circuit breaker returns (result, metadata) tuple
            result, metadata = await self.circuit.call(
                func=call_mcp,
                fallback=lambda: ToolResult(success=False, data=None)
            )

            if result and result.success and result.data:
                return result.data
            return []

        except Exception as e:
            logger.error(f"Failed to get habits: {e}", exc_info=True)
            return None

    async def close(self):
        """
        Close MCP connection.

        Note: MCPBridge creates sessions per-call, so minimal cleanup needed.
        """
        if self._bridge:
            try:
                await self._bridge.close()
                logger.debug("MCPBridge closed")
            except Exception as e:
                logger.error(f"Error closing MCPBridge: {e}")
            finally:
                self._bridge = None
