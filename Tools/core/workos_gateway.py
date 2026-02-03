#!/usr/bin/env python3
"""
WorkOS Gateway - Single entrypoint for WorkOS data access.

MCP-first with graceful fallbacks:
1) WorkOS MCP server via MCPBridge
2) Direct WorkOSAdapter (Postgres)
3) Read-only SQLite cache (for snapshot use)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from Tools.adapters.base import ToolResult
from Tools.adapters.mcp_bridge import MCPBridge
from Tools.adapters.mcp_config import MCPServerConfig, StdioConfig, load_claude_json_config
from Tools.adapters.mcp_discovery import MCPServerDiscovery

logger = logging.getLogger(__name__)


@dataclass
class WorkOSMetrics:
    points: int
    target: int
    minimum: int
    streak: int
    completed_count: int
    active_count: int
    queued_count: int
    pace_status: Optional[str]
    raw: dict[str, Any]


class WorkOSGateway:
    """MCP-first gateway for WorkOS access with fallbacks."""

    CACHE_TTL = 300  # seconds

    def __init__(self, project_root: Optional[Path] = None, prefer_mcp: bool = True):
        self.project_root = (
            Path(project_root).resolve()
            if project_root
            else Path(__file__).parent.parent.parent.resolve()
        )
        self.prefer_mcp = prefer_mcp
        self._mcp_bridge: Optional[MCPBridge] = None
        self._direct_adapter = None
        self._cache: dict[str, Any] = {}
        self._cache_time: dict[str, datetime] = {}

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------

    def _cache_get(self, key: str) -> Optional[Any]:
        ts = self._cache_time.get(key)
        if not ts:
            return None
        if (datetime.now() - ts).seconds >= self.CACHE_TTL:
            return None
        return self._cache.get(key)

    def _cache_set(self, key: str, value: Any) -> None:
        self._cache[key] = value
        self._cache_time[key] = datetime.now()

    def _get_mcp_bridge(self) -> Optional[MCPBridge]:
        if self._mcp_bridge is not None:
            return self._mcp_bridge

        config = self._load_workos_mcp_config()
        if not config or not config.enabled:
            return None

        self._mcp_bridge = MCPBridge(config)
        return self._mcp_bridge

    def _get_direct_adapter(self):
        if self._direct_adapter is not None:
            return self._direct_adapter
        try:
            from Tools.adapters.workos import WorkOSAdapter

            self._direct_adapter = WorkOSAdapter()
            return self._direct_adapter
        except Exception as exc:
            logger.warning("WorkOSAdapter unavailable: %s", exc)
            return None

    def _load_workos_mcp_config(self) -> Optional[MCPServerConfig]:
        # Primary path: discovery (supports project + global config)
        try:
            discovery = MCPServerDiscovery(project_root=self.project_root)
            servers = discovery.discover_servers()
            config = servers.get("workos") or servers.get("workos-mcp")
            if config:
                return config
        except Exception as exc:
            logger.debug("MCP discovery failed: %s", exc)

        # Fallback: Claude-format .mcp.json in project root
        try:
            claude_servers = load_claude_json_config(
                claude_json_path=self.project_root / ".mcp.json",
                project_path=str(self.project_root),
            )
            config = claude_servers.get("workos") or claude_servers.get("workos-mcp")
            if config:
                return config
        except Exception as exc:
            logger.debug("Claude-format MCP config load failed: %s", exc)

        # Final fallback: local stdio command
        return MCPServerConfig(
            name="workos",
            description="WorkOS MCP server (local fallback)",
            transport=StdioConfig(
                command="npx",
                args=["tsx", "mcp-servers/workos-mcp/src/index.ts"],
                env={},
                cwd=str(self.project_root),
            ),
            enabled=True,
            tags=["productivity", "tasks", "workos"],
        )

    async def _call_mcp(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        bridge = self._get_mcp_bridge()
        if bridge is None:
            return ToolResult.fail("WorkOS MCP not configured")
        try:
            return await bridge.call_tool(tool_name, arguments)
        except Exception as exc:
            return ToolResult.fail(str(exc))

    async def _call_adapter(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        adapter = self._get_direct_adapter()
        if adapter is None:
            return ToolResult.fail("WorkOS adapter unavailable")
        try:
            return await adapter.call_tool(tool_name, arguments)
        except Exception as exc:
            return ToolResult.fail(str(exc))

    @staticmethod
    def _effort_to_value_tier(effort_estimate: Optional[int]) -> Optional[str]:
        if effort_estimate is None:
            return None
        if effort_estimate <= 1:
            return "checkbox"
        if effort_estimate <= 3:
            return "progress"
        if effort_estimate == 4:
            return "deliverable"
        return "milestone"

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------

    async def get_daily_summary(self, force_refresh: bool = False) -> Optional[dict[str, Any]]:
        cache_key = "daily_summary"
        if not force_refresh:
            cached = self._cache_get(cache_key)
            if cached is not None:
                return cached

        # MCP-first
        result = await self._call_mcp("workos_daily_summary", {})
        if result.success and isinstance(result.data, dict):
            self._cache_set(cache_key, result.data)
            return result.data

        # Fallback: direct adapter
        result = await self._call_adapter("daily_summary", {})
        if result.success and isinstance(result.data, dict):
            self._cache_set(cache_key, result.data)
            return result.data

        return None

    async def get_today_metrics(self, raw: bool = False) -> Optional[dict[str, Any]]:
        result = await self._call_mcp("workos_get_today_metrics", {})
        data = result.data if result.success else None

        if data is None:
            adapter_result = await self._call_adapter("get_today_metrics", {})
            data = adapter_result.data if adapter_result.success else None

        if not isinstance(data, dict):
            return None

        if raw:
            return data

        metrics = self._normalize_metrics(data)
        return metrics.__dict__

    async def get_tasks(
        self,
        status: Optional[str] = None,
        client_id: Optional[int] = None,
        limit: Optional[int] = None,
        client_name: Optional[str] = None,
        apply_energy_filter: Optional[bool] = None,
        raw: bool = False,
    ) -> Optional[list[dict[str, Any]] | dict[str, Any]]:
        args: dict[str, Any] = {}
        if status:
            args["status"] = status
        if client_id is not None:
            args["clientId"] = client_id
        if client_name:
            args["clientName"] = client_name
        if limit is not None:
            args["limit"] = limit
        if apply_energy_filter is not None:
            args["applyEnergyFilter"] = apply_energy_filter

        result = await self._call_mcp("workos_get_tasks", args)
        data = result.data if result.success else None

        if data is None:
            # Adapter supports status + limit only
            adapter_args: dict[str, Any] = {}
            if status:
                adapter_args["status"] = status
            if limit is not None:
                adapter_args["limit"] = limit
            adapter_result = await self._call_adapter("get_tasks", adapter_args)
            data = adapter_result.data if adapter_result.success else None

        if raw:
            return data

        return self._normalize_tasks(data)

    async def create_task(
        self,
        title: str,
        description: Optional[str] = None,
        status: Optional[str] = None,
        client_id: Optional[int] = None,
        category: Optional[str] = None,
        value_tier: Optional[str] = None,
        drain_type: Optional[str] = None,
        effort_estimate: Optional[int] = None,
    ) -> ToolResult:
        value_tier = value_tier or self._effort_to_value_tier(effort_estimate)
        args: dict[str, Any] = {"title": title}
        if description:
            args["description"] = description
        if status:
            args["status"] = status
        if client_id is not None:
            args["clientId"] = client_id
        if category:
            args["category"] = category
        if value_tier:
            args["valueTier"] = value_tier
        if drain_type:
            args["drainType"] = drain_type

        result = await self._call_mcp("workos_create_task", args)
        if result.success:
            return result

        # Fallback to direct adapter (supports effort_estimate)
        adapter_args: dict[str, Any] = {
            "title": title,
            "description": description,
            "status": status or "backlog",
            "client_id": client_id,
            "effort_estimate": effort_estimate,
        }
        return await self._call_adapter("create_task", adapter_args)

    async def complete_task(self, task_id: int) -> ToolResult:
        result = await self._call_mcp("workos_complete_task", {"taskId": task_id})
        if result.success:
            return result
        return await self._call_adapter("complete_task", {"task_id": task_id})

    async def get_state_snapshot(self) -> dict[str, Any]:
        """
        Minimal WorkOS snapshot for UI/state use.
        Returns a consistent dict matching StateManager expectations.
        """
        tasks = await self.get_tasks(status="active", limit=3)
        metrics = await self.get_today_metrics()

        top_tasks = []
        if isinstance(tasks, list):
            for task in tasks:
                title = task.get("title") or task.get("name") or "Untitled"
                top_tasks.append(title)

        points = 0
        target = 18
        if isinstance(metrics, dict):
            points = int(metrics.get("points", 0) or 0)
            target = int(metrics.get("target", 18) or 18)

        available = bool(top_tasks or metrics)
        return {
            "available": available,
            "top_tasks": top_tasks,
            "active_count": len(top_tasks),
            "today_focus": top_tasks[0] if top_tasks else None,
            "points_earned": points,
            "target_points": target,
        }

    # ------------------------------------------------------------------
    # Normalizers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_tasks(data: Any) -> list[dict[str, Any]]:
        if data is None:
            return []
        if isinstance(data, dict):
            tasks = data.get("tasks")
            if isinstance(tasks, list):
                return tasks
            if isinstance(data.get("data"), list):
                return data["data"]
            return []
        if isinstance(data, list):
            return data
        return []

    @staticmethod
    def _normalize_metrics(data: dict[str, Any]) -> WorkOSMetrics:
        earned = (
            data.get("earnedPoints")
            or data.get("earned_points")
            or data.get("points")
            or 0
        )
        target = (
            data.get("targetPoints")
            or data.get("target_points")
            or data.get("target")
            or 18
        )
        minimum = (
            data.get("minimumPoints")
            or data.get("minimum_points")
            or data.get("minimum")
            or 12
        )
        streak = data.get("streak") or 0
        completed = data.get("completedCount") or data.get("completed_count") or 0
        active = data.get("active_count") or data.get("activeCount") or 0
        queued = data.get("queued_count") or data.get("queuedCount") or 0
        pace_status = data.get("paceStatus") or data.get("pace_status")

        return WorkOSMetrics(
            points=int(earned),
            target=int(target),
            minimum=int(minimum),
            streak=int(streak),
            completed_count=int(completed),
            active_count=int(active),
            queued_count=int(queued),
            pace_status=pace_status,
            raw=data,
        )

    async def close(self) -> None:
        if self._direct_adapter is not None:
            try:
                await self._direct_adapter.close()
            except Exception:
                pass
