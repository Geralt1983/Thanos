"""
WorkOS/Neon Database adapter for Thanos.

Provides direct PostgreSQL access to the WorkOS productivity database,
bypassing the MCP server for better performance and control.
"""

from datetime import datetime
import os
from typing import Any, Optional
from zoneinfo import ZoneInfo

import asyncpg

from .base import BaseAdapter, ToolResult


class WorkOSAdapter(BaseAdapter):
    """Direct adapter for WorkOS/Neon database operations."""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize the WorkOS adapter.

        Args:
            database_url: PostgreSQL connection string. Falls back to
                         WORKOS_DATABASE_URL or DATABASE_URL env vars.
        """
        self.database_url = database_url or os.environ.get(
            "WORKOS_DATABASE_URL", os.environ.get("DATABASE_URL")
        )
        self._pool: Optional[asyncpg.Pool] = None

    @property
    def name(self) -> str:
        return "workos"

    async def _get_pool(self) -> asyncpg.Pool:
        """Get or create the connection pool."""
        if self._pool is None:
            if not self.database_url:
                raise ValueError(
                    "No database URL configured. Set WORKOS_DATABASE_URL or DATABASE_URL."
                )
            self._pool = await asyncpg.create_pool(
                self.database_url, min_size=1, max_size=5, command_timeout=30
            )
        return self._pool

    def list_tools(self) -> list[dict[str, Any]]:
        """Return list of available WorkOS tools."""
        return [
            {
                "name": "get_tasks",
                "description": "Get tasks by status",
                "parameters": {
                    "status": {
                        "type": "string",
                        "enum": ["active", "queued", "backlog", "done"],
                        "description": "Filter by task status",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 50,
                        "description": "Maximum number of tasks to return",
                    },
                },
            },
            {
                "name": "get_today_metrics",
                "description": "Get today's work progress metrics (points earned, streak, etc.)",
                "parameters": {},
            },
            {
                "name": "complete_task",
                "description": "Mark a task as complete",
                "parameters": {
                    "task_id": {
                        "type": "integer",
                        "required": True,
                        "description": "ID of the task to complete",
                    }
                },
            },
            {
                "name": "create_task",
                "description": "Create a new task",
                "parameters": {
                    "title": {"type": "string", "required": True, "description": "Task title"},
                    "description": {"type": "string", "description": "Task description"},
                    "status": {
                        "type": "string",
                        "default": "backlog",
                        "enum": ["active", "queued", "backlog"],
                        "description": "Initial task status",
                    },
                    "client_id": {"type": "integer", "description": "Associated client ID"},
                    "effort_estimate": {
                        "type": "integer",
                        "description": "Estimated effort points (1-5)",
                    },
                },
            },
            {
                "name": "update_task",
                "description": "Update an existing task",
                "parameters": {
                    "task_id": {
                        "type": "integer",
                        "required": True,
                        "description": "ID of the task to update",
                    },
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "status": {"type": "string", "enum": ["active", "queued", "backlog", "done"]},
                    "sort_order": {"type": "integer"},
                },
            },
            {"name": "get_habits", "description": "Get all active habits", "parameters": {}},
            {
                "name": "complete_habit",
                "description": "Mark a habit as complete for today",
                "parameters": {
                    "habit_id": {
                        "type": "integer",
                        "required": True,
                        "description": "ID of the habit to complete",
                    }
                },
            },
            {
                "name": "get_clients",
                "description": "Get all clients",
                "parameters": {
                    "active_only": {
                        "type": "boolean",
                        "default": True,
                        "description": "Only return active clients",
                    }
                },
            },
            {
                "name": "daily_summary",
                "description": "Get comprehensive daily summary with tasks, habits, and metrics",
                "parameters": {},
            },
            {
                "name": "search_tasks",
                "description": "Search tasks by title or description",
                "parameters": {
                    "query": {"type": "string", "required": True, "description": "Search query"},
                    "limit": {"type": "integer", "default": 20},
                },
            },
        ]

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        """Execute a WorkOS tool."""
        try:
            pool = await self._get_pool()

            tool_methods = {
                "get_tasks": self._get_tasks,
                "get_today_metrics": self._get_today_metrics,
                "complete_task": self._complete_task,
                "create_task": self._create_task,
                "update_task": self._update_task,
                "get_habits": self._get_habits,
                "complete_habit": self._complete_habit,
                "get_clients": self._get_clients,
                "daily_summary": self._daily_summary,
                "search_tasks": self._search_tasks,
            }

            if tool_name not in tool_methods:
                return ToolResult.fail(f"Unknown tool: {tool_name}")

            return await tool_methods[tool_name](pool, **arguments)

        except asyncpg.PostgresError as e:
            return ToolResult.fail(f"Database error: {e}")
        except Exception as e:
            return ToolResult.fail(f"Error: {e}")

    async def _get_tasks(
        self, pool: asyncpg.Pool, status: Optional[str] = None, limit: int = 50
    ) -> ToolResult:
        """Get tasks, optionally filtered by status."""
        async with pool.acquire() as conn:
            if status:
                rows = await conn.fetch(
                    """
                    SELECT t.*, c.name as client_name
                    FROM tasks t
                    LEFT JOIN clients c ON t.client_id = c.id
                    WHERE t.status = $1
                    ORDER BY t.sort_order ASC NULLS LAST, t.created_at DESC
                    LIMIT $2
                    """,
                    status,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT t.*, c.name as client_name
                    FROM tasks t
                    LEFT JOIN clients c ON t.client_id = c.id
                    ORDER BY
                        CASE t.status
                            WHEN 'active' THEN 1
                            WHEN 'queued' THEN 2
                            WHEN 'backlog' THEN 3
                            WHEN 'done' THEN 4
                        END,
                        t.sort_order ASC NULLS LAST,
                        t.created_at DESC
                    LIMIT $1
                    """,
                    limit,
                )
            return ToolResult.ok([self._row_to_dict(r) for r in rows])

    async def _get_today_metrics(self, pool: asyncpg.Pool) -> ToolResult:
        """Get today's work progress metrics."""
        async with pool.acquire() as conn:
            today_start = self._get_est_today_start()

            # Get completed tasks today
            completed = await conn.fetch(
                """
                SELECT * FROM tasks
                WHERE status = 'done' AND completed_at >= $1
                """,
                today_start,
            )

            # Calculate earned points
            earned_points = sum(
                r.get("points_final") or r.get("points_ai_guess") or r.get("effort_estimate") or 2
                for r in completed
            )

            # Get active and queued counts
            active_count = await conn.fetchval("SELECT COUNT(*) FROM tasks WHERE status = 'active'")
            queued_count = await conn.fetchval("SELECT COUNT(*) FROM tasks WHERE status = 'queued'")

            # Get streak from daily_goals
            streak_row = await conn.fetchrow(
                "SELECT current_streak FROM daily_goals ORDER BY date DESC LIMIT 1"
            )

            # Calculate progress percentage
            target_points = 18
            minimum_points = 12
            progress_pct = min(100, round((earned_points / target_points) * 100))

            return ToolResult.ok(
                {
                    "completed_count": len(completed),
                    "earned_points": earned_points,
                    "target_points": target_points,
                    "minimum_points": minimum_points,
                    "progress_percentage": progress_pct,
                    "streak": streak_row["current_streak"] if streak_row else 0,
                    "active_count": active_count,
                    "queued_count": queued_count,
                    "goal_met": earned_points >= minimum_points,
                    "target_met": earned_points >= target_points,
                }
            )

    async def _complete_task(self, pool: asyncpg.Pool, task_id: int) -> ToolResult:
        """Mark a task as complete."""
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE tasks
                SET status = 'done',
                    completed_at = NOW(),
                    updated_at = NOW()
                WHERE id = $1
                RETURNING *
                """,
                task_id,
            )
            if row:
                return ToolResult.ok(self._row_to_dict(row))
            return ToolResult.fail(f"Task {task_id} not found")

    async def _create_task(
        self,
        pool: asyncpg.Pool,
        title: str,
        description: Optional[str] = None,
        status: str = "backlog",
        client_id: Optional[int] = None,
        effort_estimate: Optional[int] = None,
    ) -> ToolResult:
        """Create a new task."""
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO tasks (
                    title, description, status, client_id, effort_estimate, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, NOW())
                RETURNING *
                """,
                title,
                description,
                status,
                client_id,
                effort_estimate,
            )
            return ToolResult.ok(self._row_to_dict(row))

    async def _update_task(self, pool: asyncpg.Pool, task_id: int, **updates) -> ToolResult:
        """Update an existing task."""
        # Build dynamic update query
        allowed_fields = {
            "title",
            "description",
            "status",
            "sort_order",
            "effort_estimate",
            "client_id",
        }
        update_fields = {k: v for k, v in updates.items() if k in allowed_fields and v is not None}

        if not update_fields:
            return ToolResult.fail("No valid fields to update")

        # Build SET clause
        set_parts = [f"{field} = ${i + 2}" for i, field in enumerate(update_fields.keys())]
        set_parts.append("updated_at = NOW()")

        # Handle status change to 'done'
        if update_fields.get("status") == "done":
            set_parts.append("completed_at = NOW()")

        query = f"""
            UPDATE tasks
            SET {", ".join(set_parts)}
            WHERE id = $1
            RETURNING *
        """

        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, task_id, *update_fields.values())
            if row:
                return ToolResult.ok(self._row_to_dict(row))
            return ToolResult.fail(f"Task {task_id} not found")

    async def _get_habits(self, pool: asyncpg.Pool) -> ToolResult:
        """Get all active habits."""
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT h.*,
                       (SELECT MAX(completed_at) FROM habit_completions
                        WHERE habit_id = h.id) as last_completion
                FROM habits h
                WHERE h.is_active = true OR h.is_active = 1
                ORDER BY h.sort_order ASC NULLS LAST
                """
            )
            return ToolResult.ok([self._row_to_dict(r) for r in rows])

    async def _complete_habit(self, pool: asyncpg.Pool, habit_id: int) -> ToolResult:
        """Mark a habit as complete for today."""
        today_str = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")

        async with pool.acquire() as conn:
            # Check if already completed today
            existing = await conn.fetchrow(
                """
                SELECT * FROM habit_completions
                WHERE habit_id = $1 AND DATE(completed_at) = $2
                """,
                habit_id,
                today_str,
            )

            if existing:
                return ToolResult.fail(f"Habit {habit_id} already completed today")

            # Insert completion
            await conn.execute(
                "INSERT INTO habit_completions (habit_id, completed_at) VALUES ($1, NOW())",
                habit_id,
            )

            # Update habit streak
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
                today_str,
                habit_id,
            )

            if row:
                return ToolResult.ok(self._row_to_dict(row))
            return ToolResult.fail(f"Habit {habit_id} not found")

    async def _get_clients(self, pool: asyncpg.Pool, active_only: bool = True) -> ToolResult:
        """Get all clients."""
        async with pool.acquire() as conn:
            if active_only:
                rows = await conn.fetch(
                    """
                    SELECT c.*,
                           (SELECT COUNT(*) FROM tasks
                            WHERE client_id = c.id AND status != 'done') as open_tasks
                    FROM clients c
                    WHERE c.is_active = true OR c.is_active = 1
                    ORDER BY c.name
                    """
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT c.*,
                           (SELECT COUNT(*) FROM tasks
                            WHERE client_id = c.id AND status != 'done') as open_tasks
                    FROM clients c
                    ORDER BY c.name
                    """
                )
            return ToolResult.ok([self._row_to_dict(r) for r in rows])

    async def _daily_summary(self, pool: asyncpg.Pool) -> ToolResult:
        """Get comprehensive daily summary."""
        metrics = await self._get_today_metrics(pool)
        active = await self._get_tasks(pool, status="active")
        queued = await self._get_tasks(pool, status="queued", limit=5)
        habits = await self._get_habits(pool)

        return ToolResult.ok(
            {
                "progress": metrics.data if metrics.success else None,
                "active_tasks": active.data if active.success else [],
                "queued_tasks": queued.data if queued.success else [],
                "habits": habits.data if habits.success else [],
                "generated_at": datetime.now(ZoneInfo("America/New_York")).isoformat(),
            }
        )

    async def _search_tasks(self, pool: asyncpg.Pool, query: str, limit: int = 20) -> ToolResult:
        """Search tasks by title or description."""
        search_pattern = f"%{query}%"
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT t.*, c.name as client_name
                FROM tasks t
                LEFT JOIN clients c ON t.client_id = c.id
                WHERE t.title ILIKE $1 OR t.description ILIKE $1
                ORDER BY
                    CASE t.status
                        WHEN 'active' THEN 1
                        WHEN 'queued' THEN 2
                        WHEN 'backlog' THEN 3
                        WHEN 'done' THEN 4
                    END,
                    t.updated_at DESC
                LIMIT $2
                """,
                search_pattern,
                limit,
            )
            return ToolResult.ok([self._row_to_dict(r) for r in rows])

    def _get_est_today_start(self) -> datetime:
        """Get UTC timestamp for midnight EST today."""
        est = ZoneInfo("America/New_York")
        now_est = datetime.now(est)
        midnight_est = now_est.replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight_est.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

    def _row_to_dict(self, row: asyncpg.Record) -> dict[str, Any]:
        """Convert asyncpg Record to dict, handling datetime serialization."""
        result = dict(row)
        for key, value in result.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
        return result

    async def close(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def health_check(self) -> ToolResult:
        """Check database connectivity."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                return ToolResult.ok(
                    {
                        "status": "ok",
                        "adapter": self.name,
                        "database": "connected",
                        "version": version[:50] if version else None,
                    }
                )
        except Exception as e:
            return ToolResult.fail(f"Health check failed: {e}")
