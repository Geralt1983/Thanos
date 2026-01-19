#!/usr/bin/env python3
"""
Thanos Dashboard - Compact status bar showing health + productivity metrics.

Usage:
  python dashboard.py           # One-shot display
  python dashboard.py --watch   # Live updating (every 30s)
  python dashboard.py --json    # JSON output for integration
"""

import argparse
import asyncio
import json
import os
import sqlite3
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional

# PostgreSQL driver support (try multiple options)
HAS_PSYCOPG2 = False
HAS_ASYNCPG = False

try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    pass

try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    pass

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.live import Live
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class HealthMetrics:
    """Health metrics from Oura."""
    energy_level: Optional[str] = None  # high, medium, low
    readiness_score: Optional[int] = None
    sleep_score: Optional[int] = None
    available: bool = False


@dataclass
class ProductivityMetrics:
    """Productivity metrics from WorkOS."""
    active_tasks: int = 0
    points_earned: int = 0
    target_points: int = 18
    current_streak: int = 0
    available: bool = False


@dataclass
class DashboardData:
    """Combined dashboard data."""
    health: HealthMetrics
    productivity: ProductivityMetrics
    timestamp: datetime


# =============================================================================
# OURA DATA (SQLite)
# =============================================================================

def get_oura_data() -> HealthMetrics:
    """
    Read health metrics from Oura cache database.

    Database location: ~/.oura-cache/oura-health.db

    Fetches most recent data available (today or most recent if today unavailable).
    """
    metrics = HealthMetrics()

    oura_db_path = Path.home() / ".oura-cache" / "oura-health.db"

    if not oura_db_path.exists():
        return metrics

    try:
        conn = sqlite3.connect(str(oura_db_path), timeout=5)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get most recent readiness data
        readiness_score = None
        cursor.execute(
            "SELECT data FROM readiness_data ORDER BY day DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            try:
                data = json.loads(row["data"])
                readiness_score = data.get("score")
            except (json.JSONDecodeError, KeyError):
                pass

        # Get most recent sleep data
        sleep_score = None
        cursor.execute(
            "SELECT data FROM sleep_data ORDER BY day DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            try:
                data = json.loads(row["data"])
                sleep_score = data.get("score")
            except (json.JSONDecodeError, KeyError):
                pass

        conn.close()

        # Determine energy level from readiness score (preferred) or sleep score (fallback)
        energy_level = None
        primary_score = readiness_score if readiness_score is not None else sleep_score
        if primary_score is not None:
            if primary_score >= 85:
                energy_level = "high"
            elif primary_score >= 70:
                energy_level = "medium"
            else:
                energy_level = "low"

        metrics.readiness_score = readiness_score
        metrics.sleep_score = sleep_score
        metrics.energy_level = energy_level
        metrics.available = readiness_score is not None or sleep_score is not None

    except (sqlite3.Error, OSError):
        # Database unavailable or locked
        pass

    return metrics


# =============================================================================
# WORKOS DATA (PostgreSQL via Neon)
# =============================================================================

async def _get_workos_data_asyncpg() -> ProductivityMetrics:
    """Fetch WorkOS data using asyncpg driver."""
    metrics = ProductivityMetrics()

    database_url = os.environ.get("WORKOS_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not database_url:
        return metrics

    try:
        conn = await asyncpg.connect(database_url, timeout=5)

        today = date.today()  # asyncpg expects date object, not string

        # Get active task count
        result = await conn.fetchval(
            "SELECT COUNT(*) FROM tasks WHERE status = 'active'"
        )
        active_tasks = result or 0

        # Get today's daily goal data
        row = await conn.fetchrow(
            """
            SELECT target_points, earned_points, current_streak, adjusted_target_points
            FROM daily_goals
            WHERE date = $1
            LIMIT 1
            """,
            today
        )

        if row:
            target_points = row["adjusted_target_points"] if row["adjusted_target_points"] else row["target_points"]
            earned_points = row["earned_points"] or 0
            current_streak = row["current_streak"] or 0
        else:
            target_points = 18
            earned_points = 0
            current_streak = 0

        await conn.close()

        metrics.active_tasks = active_tasks
        metrics.points_earned = earned_points
        metrics.target_points = target_points or 18
        metrics.current_streak = current_streak
        metrics.available = True

    except Exception:
        pass

    return metrics


def _get_workos_data_psycopg2() -> ProductivityMetrics:
    """Fetch WorkOS data using psycopg2 driver."""
    metrics = ProductivityMetrics()

    database_url = os.environ.get("WORKOS_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not database_url:
        return metrics

    try:
        conn = psycopg2.connect(database_url, connect_timeout=5)
        cursor = conn.cursor()

        today = date.today().isoformat()

        # Get active task count (status = 'active')
        cursor.execute(
            "SELECT COUNT(*) FROM tasks WHERE status = 'active'"
        )
        result = cursor.fetchone()
        active_tasks = result[0] if result else 0

        # Get today's daily goal data
        cursor.execute(
            """
            SELECT target_points, earned_points, current_streak, adjusted_target_points
            FROM daily_goals
            WHERE date = %s
            LIMIT 1
            """,
            (today,)
        )
        row = cursor.fetchone()

        if row:
            target_points = row[3] if row[3] else row[0]  # Use adjusted if available
            earned_points = row[1] or 0
            current_streak = row[2] or 0
        else:
            target_points = 18
            earned_points = 0
            current_streak = 0

        conn.close()

        metrics.active_tasks = active_tasks
        metrics.points_earned = earned_points
        metrics.target_points = target_points or 18
        metrics.current_streak = current_streak
        metrics.available = True

    except Exception:
        pass

    return metrics


def get_workos_data() -> ProductivityMetrics:
    """
    Read productivity metrics from WorkOS PostgreSQL database.

    Connection string from: WORKOS_DATABASE_URL environment variable

    Supports both asyncpg and psycopg2 drivers.
    """
    database_url = os.environ.get("WORKOS_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not database_url:
        return ProductivityMetrics()

    if not HAS_ASYNCPG and not HAS_PSYCOPG2:
        return ProductivityMetrics()

    # Prefer asyncpg (already installed)
    if HAS_ASYNCPG:
        return asyncio.run(_get_workos_data_asyncpg())
    elif HAS_PSYCOPG2:
        return _get_workos_data_psycopg2()

    return ProductivityMetrics()


# =============================================================================
# DASHBOARD RENDERING
# =============================================================================

def get_energy_indicator(level: Optional[str]) -> str:
    """Get colored energy indicator."""
    if level == "high":
        return "[green]HIGH[/green]"
    elif level == "medium":
        return "[yellow]MEDIUM[/yellow]"
    elif level == "low":
        return "[red]LOW[/red]"
    return "[dim]?[/dim]"


def get_energy_emoji(level: Optional[str]) -> str:
    """Get energy level emoji."""
    if level == "high":
        return "\U0001F7E2"  # Green circle
    elif level == "medium":
        return "\U0001F7E1"  # Yellow circle
    elif level == "low":
        return "\U0001F534"  # Red circle
    return "\u2754"  # Question mark


def format_score(score: Optional[int], emoji: str = "") -> str:
    """Format a score with optional emoji."""
    if score is None:
        return f"{emoji} ?" if emoji else "?"
    return f"{emoji} {score}" if emoji else str(score)


def render_dashboard_rich(data: DashboardData) -> Panel:
    """Render dashboard using rich library."""
    console = Console()

    # Build the status line
    parts = []

    # Energy level
    energy_emoji = get_energy_emoji(data.health.energy_level)
    energy_text = data.health.energy_level.upper() if data.health.energy_level else "?"
    parts.append(f"{energy_emoji} {energy_text}")

    # Sleep score
    sleep_display = format_score(data.health.sleep_score, "\U0001F634")  # Sleeping face
    parts.append(sleep_display)

    # Readiness score
    readiness_display = format_score(data.health.readiness_score, "\U0001F3AF")  # Target
    parts.append(readiness_display)

    # Active tasks
    tasks_display = f"\u2705 {data.productivity.active_tasks} tasks"  # Check mark
    parts.append(tasks_display)

    # Points earned
    points_display = f"\u2B50 {data.productivity.points_earned}/{data.productivity.target_points} pts"  # Star
    parts.append(points_display)

    # Streak (if > 0)
    if data.productivity.current_streak > 0:
        streak_display = f"\U0001F525 {data.productivity.current_streak}"  # Fire
        parts.append(streak_display)

    # Join with separator
    status_line = " | ".join(parts)

    # Create panel
    panel = Panel(
        Text(status_line, justify="center"),
        title="THANOS",
        border_style="cyan",
        padding=(0, 1),
    )

    return panel


def render_dashboard_plain(data: DashboardData) -> str:
    """Render dashboard as plain text (no rich library)."""
    lines = []

    # Header
    lines.append("+-- THANOS " + "-" * 45 + "+")

    # Build status parts
    parts = []

    # Energy level
    energy_emoji = get_energy_emoji(data.health.energy_level)
    energy_text = data.health.energy_level.upper() if data.health.energy_level else "?"
    parts.append(f"{energy_emoji} {energy_text}")

    # Sleep score
    sleep_val = data.health.sleep_score if data.health.sleep_score else "?"
    parts.append(f"\U0001F634 {sleep_val}")

    # Readiness score
    readiness_val = data.health.readiness_score if data.health.readiness_score else "?"
    parts.append(f"\U0001F3AF {readiness_val}")

    # Active tasks
    parts.append(f"\u2705 {data.productivity.active_tasks} tasks")

    # Points
    parts.append(f"\u2B50 {data.productivity.points_earned} pts")

    # Streak
    if data.productivity.current_streak > 0:
        parts.append(f"\U0001F525 {data.productivity.current_streak}")

    status_line = " | ".join(parts)

    # Pad to fit in box
    content = f"| {status_line} |"
    lines.append(content)

    # Footer
    lines.append("+" + "-" * 56 + "+")

    return "\n".join(lines)


def render_dashboard_json(data: DashboardData) -> str:
    """Render dashboard as JSON."""
    return json.dumps({
        "timestamp": data.timestamp.isoformat(),
        "health": {
            "energy_level": data.health.energy_level,
            "readiness_score": data.health.readiness_score,
            "sleep_score": data.health.sleep_score,
            "available": data.health.available,
        },
        "productivity": {
            "active_tasks": data.productivity.active_tasks,
            "points_earned": data.productivity.points_earned,
            "target_points": data.productivity.target_points,
            "current_streak": data.productivity.current_streak,
            "available": data.productivity.available,
        },
    }, indent=2)


# =============================================================================
# MAIN FUNCTIONS
# =============================================================================

def fetch_dashboard_data() -> DashboardData:
    """Fetch all dashboard data from sources."""
    return DashboardData(
        health=get_oura_data(),
        productivity=get_workos_data(),
        timestamp=datetime.now(),
    )


def display_dashboard(output_json: bool = False) -> None:
    """Display the dashboard once."""
    data = fetch_dashboard_data()

    if output_json:
        print(render_dashboard_json(data))
    elif HAS_RICH:
        console = Console()
        console.print(render_dashboard_rich(data))
    else:
        print(render_dashboard_plain(data))


def watch_dashboard(interval: int = 30) -> None:
    """Display dashboard with live updates."""
    if not HAS_RICH:
        print("Watch mode requires 'rich' library. Install with: pip install rich")
        print("Falling back to single display...")
        display_dashboard()
        return

    console = Console()

    try:
        with Live(render_dashboard_rich(fetch_dashboard_data()),
                  console=console,
                  refresh_per_second=0.1,
                  transient=False) as live:
            while True:
                time.sleep(interval)
                data = fetch_dashboard_data()
                live.update(render_dashboard_rich(data))
    except KeyboardInterrupt:
        console.print("\n[dim]Dashboard stopped.[/dim]")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Thanos Dashboard - Compact health + productivity HUD"
    )
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Live updating mode (refreshes every 30s)"
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=30,
        help="Update interval in seconds for watch mode (default: 30)"
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output as JSON for integration"
    )

    args = parser.parse_args()

    if args.watch:
        watch_dashboard(interval=args.interval)
    else:
        display_dashboard(output_json=args.json)


if __name__ == "__main__":
    main()
