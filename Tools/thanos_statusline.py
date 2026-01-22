#!/usr/bin/env python3
"""
Thanos Statusline - Dynamic single-line status generator.

Generates a compact, real-time status line showing:
- Energy level (based on Oura readiness)
- Readiness and sleep scores
- Points progress (current/target)
- Streak status
- Active task count
- Time-of-day context with work mode hints

Usage:
    python thanos_statusline.py              # Default formatted output
    python thanos_statusline.py --json       # JSON output for integration
    python thanos_statusline.py --compact    # Minimal output
    python thanos_statusline.py --no-color   # Plain text (no ANSI)

Example output:
    HIGH 78 | 85 | 12/18 | 5 | 3 tasks | deep work window
"""

import argparse
import asyncio
import json
import os
import sqlite3
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Tuple

# Optional: PostgreSQL support for WorkOS
HAS_ASYNCPG = False
try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    pass


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class OuraMetrics:
    """Health metrics from Oura cache."""
    readiness_score: Optional[int] = None
    sleep_score: Optional[int] = None
    hrv: Optional[int] = None
    rhr: Optional[int] = None
    available: bool = False


@dataclass
class WorkOSMetrics:
    """Productivity metrics from WorkOS."""
    active_tasks: int = 0
    points_earned: int = 0
    target_points: int = 18
    current_streak: int = 0
    readiness_score: Optional[int] = None  # From daily_goals if Oura unavailable
    energy_level: Optional[str] = None  # From daily_goals if available
    inbox_count: int = 0  # Unprocessed brain dumps
    available: bool = False


@dataclass
class StatusData:
    """Combined status data."""
    oura: OuraMetrics
    workos: WorkOSMetrics
    energy_level: str  # "high", "medium", "low", "unknown"
    time_of_day: str  # "morning", "afternoon", "evening", "night"
    mode_hint: str  # "deep work", "maintenance", "recovery", "wind down"
    timestamp: str


# =============================================================================
# OURA DATA FETCHING
# =============================================================================

def get_oura_metrics() -> OuraMetrics:
    """
    Fetch health metrics from Oura cache database.

    Database: ~/.oura-cache/oura-health.db
    """
    metrics = OuraMetrics()
    oura_db = Path.home() / ".oura-cache" / "oura-health.db"

    if not oura_db.exists():
        return metrics

    try:
        conn = sqlite3.connect(str(oura_db), timeout=5)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get most recent readiness data
        cursor.execute(
            "SELECT data FROM readiness_data ORDER BY day DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            try:
                data = json.loads(row["data"])
                metrics.readiness_score = data.get("score")
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

        # Get most recent sleep data
        cursor.execute(
            "SELECT data FROM sleep_data ORDER BY day DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            try:
                data = json.loads(row["data"])
                metrics.sleep_score = data.get("score")
                metrics.hrv = data.get("average_hrv")
                metrics.rhr = data.get("average_heart_rate")
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

        conn.close()
        metrics.available = (
            metrics.readiness_score is not None or
            metrics.sleep_score is not None
        )

    except (sqlite3.Error, OSError):
        pass

    return metrics


# =============================================================================
# WORKOS DATA FETCHING
# =============================================================================

def get_workos_metrics_local() -> WorkOSMetrics:
    """
    Try to fetch WorkOS metrics from local Thanos database.

    Falls back to PostgreSQL if local data is stale/unavailable.
    """
    metrics = WorkOSMetrics()
    thanos_db = Path("/Users/jeremy/Projects/Thanos/State/thanos.db")

    if not thanos_db.exists():
        return metrics

    try:
        conn = sqlite3.connect(str(thanos_db), timeout=5)
        cursor = conn.cursor()

        # Count active tasks
        cursor.execute(
            "SELECT COUNT(*) FROM tasks WHERE status = 'active'"
        )
        result = cursor.fetchone()
        metrics.active_tasks = result[0] if result else 0

        # Also count queued tasks as "actionable"
        cursor.execute(
            "SELECT COUNT(*) FROM tasks WHERE status IN ('active', 'queued')"
        )
        result = cursor.fetchone()
        if result and result[0] > metrics.active_tasks:
            metrics.active_tasks = result[0]

        # Try to get habits streak info
        cursor.execute(
            "SELECT MAX(current_streak) FROM habits WHERE is_active = 1"
        )
        result = cursor.fetchone()
        if result and result[0]:
            metrics.current_streak = result[0]

        conn.close()
        metrics.available = True

    except (sqlite3.Error, OSError):
        pass

    return metrics


async def get_workos_metrics_remote() -> WorkOSMetrics:
    """
    Fetch WorkOS metrics from PostgreSQL (Neon).
    """
    metrics = WorkOSMetrics()

    database_url = os.environ.get("WORKOS_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not database_url or not HAS_ASYNCPG:
        return metrics

    try:
        conn = await asyncpg.connect(database_url, timeout=5)
        today = date.today()

        # Get active task count
        result = await conn.fetchval(
            "SELECT COUNT(*) FROM tasks WHERE status = 'active'"
        )
        metrics.active_tasks = result or 0

        # Get today's daily goal data
        row = await conn.fetchrow(
            """
            SELECT target_points, earned_points, current_streak, adjusted_target_points,
                   readiness_score, energy_level
            FROM daily_goals
            WHERE date = $1
            LIMIT 1
            """,
            today
        )

        if row:
            target = row["adjusted_target_points"] or row["target_points"] or 18
            metrics.target_points = target
            metrics.points_earned = row["earned_points"] or 0
            metrics.current_streak = row["current_streak"] or 0
            metrics.readiness_score = row["readiness_score"]
            metrics.energy_level = row["energy_level"]

        await conn.close()
        metrics.available = True

    except Exception:
        pass

    return metrics


def get_workos_metrics() -> WorkOSMetrics:
    """
    Fetch WorkOS metrics, preferring local then remote.
    """
    # Try local first
    metrics = get_workos_metrics_local()

    # If we have remote access and local data is limited, try remote
    if HAS_ASYNCPG and (not metrics.available or metrics.points_earned == 0):
        remote_metrics = asyncio.run(get_workos_metrics_remote())
        if remote_metrics.available:
            # Merge: prefer remote for points/streak, local for task count
            if metrics.active_tasks == 0:
                metrics.active_tasks = remote_metrics.active_tasks
            metrics.points_earned = remote_metrics.points_earned
            metrics.target_points = remote_metrics.target_points
            metrics.current_streak = remote_metrics.current_streak
            metrics.readiness_score = remote_metrics.readiness_score
            metrics.energy_level = remote_metrics.energy_level
            metrics.available = True

    return metrics


# =============================================================================
# INBOX (BRAIN DUMP) COUNTING
# =============================================================================

def get_inbox_count() -> int:
    """
    Count unprocessed brain dumps from State/brain_dumps.json.

    Items are in inbox if: processed=false OR needs_review=true
    """
    brain_dump_path = Path("/Users/jeremy/Projects/Thanos/State/brain_dumps.json")

    if not brain_dump_path.exists():
        return 0

    try:
        with open(brain_dump_path, 'r') as f:
            dumps = json.load(f)

        count = 0
        for dump in dumps:
            if not dump.get("processed", False) or dump.get("needs_review", False):
                count += 1

        return count
    except (json.JSONDecodeError, OSError, TypeError):
        return 0


# =============================================================================
# INTELLIGENCE LAYER
# =============================================================================

def determine_energy_level(oura: OuraMetrics, workos: WorkOSMetrics) -> str:
    """
    Determine energy level from Oura metrics, with WorkOS fallback.

    Priority: oura.readiness > oura.sleep > workos.energy_level > workos.readiness
    """
    # First try Oura direct scores
    score = oura.readiness_score or oura.sleep_score

    if score is not None:
        if score >= 85:
            return "high"
        elif score >= 70:
            return "medium"
        else:
            return "low"

    # Fallback to WorkOS energy_level if available
    if workos.energy_level:
        return workos.energy_level.lower()

    # Fallback to WorkOS readiness_score
    if workos.readiness_score is not None:
        if workos.readiness_score >= 85:
            return "high"
        elif workos.readiness_score >= 70:
            return "medium"
        else:
            return "low"

    return "unknown"


def get_time_of_day() -> Tuple[str, int]:
    """
    Get current time of day category and hour.

    Returns: (category, hour)
    """
    hour = datetime.now().hour

    if 5 <= hour < 12:
        return "morning", hour
    elif 12 <= hour < 17:
        return "afternoon", hour
    elif 17 <= hour < 21:
        return "evening", hour
    else:
        return "night", hour


def determine_mode_hint(energy: str, time_of_day: str, workos: WorkOSMetrics) -> str:
    """
    Generate contextual work mode hint based on energy and time.
    """
    # Progress check
    progress = workos.points_earned / workos.target_points if workos.target_points > 0 else 0

    # Low energy always suggests recovery/light work
    if energy == "low":
        if time_of_day in ("morning", "afternoon"):
            return "recovery mode"
        return "wind down"

    # Unknown energy - give neutral advice
    if energy == "unknown":
        if time_of_day == "morning":
            return "check in first"
        elif time_of_day == "afternoon":
            return "maintain pace"
        elif time_of_day == "evening":
            return "light tasks"
        return "rest"

    # Morning with high/medium energy
    if time_of_day == "morning":
        if energy == "high":
            return "deep work window"
        return "build momentum"

    # Afternoon
    if time_of_day == "afternoon":
        if progress >= 1.0:
            return "bonus round"
        elif progress >= 0.7:
            return "finish strong"
        elif energy == "high":
            return "deep work"
        return "maintain pace"

    # Evening
    if time_of_day == "evening":
        if progress >= 1.0:
            return "celebrate wins"
        elif progress >= 0.8:
            return "quick wins"
        return "wind down"

    # Night
    return "rest"


# =============================================================================
# STATUS LINE FORMATTING
# =============================================================================

ENERGY_EMOJI = {
    "high": "\U0001F7E2",      # Green circle
    "medium": "\U0001F7E1",    # Yellow circle
    "low": "\U0001F534",       # Red circle
    "unknown": "\U00002754",   # Question mark
}

TIME_EMOJI = {
    "morning": "\U0001F305",   # Sunrise
    "afternoon": "\U00002600\uFE0F",  # Sun
    "evening": "\U0001F319",   # Crescent moon
    "night": "\U0001F303",     # Night with stars
}


def format_statusline(data: StatusData, compact: bool = False, no_color: bool = False) -> str:
    """
    Format the status line for terminal display.

    Full format (~80-100 chars):
        HIGH 78 | 85 | 12/18 | 5 | 3 tasks | deep work window

    Compact format (~60 chars):
        HIGH 78|85 12/18 3t
    """
    parts = []

    # Energy indicator
    energy_emoji = ENERGY_EMOJI.get(data.energy_level, "?")
    energy_label = data.energy_level.upper()[:3] if data.energy_level != "unknown" else "???"

    # Readiness score
    readiness = data.oura.readiness_score if data.oura.readiness_score else "?"

    # Sleep score
    sleep = data.oura.sleep_score if data.oura.sleep_score else "?"

    # Points progress
    points_str = f"{data.workos.points_earned}/{data.workos.target_points}"

    # Streak (only if > 0)
    streak = data.workos.current_streak

    # Task count
    tasks = data.workos.active_tasks

    # Inbox count
    inbox = data.workos.inbox_count

    # Time indicator
    time_emoji = TIME_EMOJI.get(data.time_of_day, "")

    if compact:
        # Compact: minimal separators
        parts = [
            f"{energy_emoji}{energy_label}",
            str(readiness),
            f"\U0001F634{sleep}" if sleep != "?" else "",  # Sleep face
            f"\U0001F4E5{inbox}" if inbox > 0 else "",  # Inbox tray
            f"\u2B50{points_str}",  # Star
            f"\U0001F525{streak}" if streak > 0 else "",  # Fire
            f"\U0001F4CB{tasks}t",  # Clipboard
        ]
        line = " ".join(p for p in parts if p)
    else:
        # Full format with separators
        parts = [
            f"{energy_emoji} {energy_label} {readiness}",
            f"\U0001F634 {sleep}",  # Sleep face
        ]

        if inbox > 0:
            parts.append(f"\U0001F4E5 {inbox}")  # Inbox tray

        parts.append(f"\u2B50 {points_str}")  # Star

        if streak > 0:
            parts.append(f"\U0001F525{streak}")  # Fire

        parts.append(f"\U0001F4CB {tasks} tasks")  # Clipboard
        parts.append(f"{time_emoji} {data.mode_hint}")

        line = " | ".join(parts)

    return line


def format_json(data: StatusData) -> str:
    """Format status data as JSON."""
    output = {
        "timestamp": data.timestamp,
        "energy_level": data.energy_level,
        "time_of_day": data.time_of_day,
        "mode_hint": data.mode_hint,
        "oura": {
            "readiness": data.oura.readiness_score,
            "sleep": data.oura.sleep_score,
            "hrv": data.oura.hrv,
            "rhr": data.oura.rhr,
            "available": data.oura.available,
        },
        "workos": {
            "active_tasks": data.workos.active_tasks,
            "points_earned": data.workos.points_earned,
            "target_points": data.workos.target_points,
            "current_streak": data.workos.current_streak,
            "inbox_count": data.workos.inbox_count,
            "available": data.workos.available,
        },
        "formatted": format_statusline(data, compact=False, no_color=True),
        "formatted_compact": format_statusline(data, compact=True, no_color=True),
    }
    return json.dumps(output, indent=2)


# =============================================================================
# MAIN
# =============================================================================

def fetch_status_data() -> StatusData:
    """Fetch all status data from sources."""
    oura = get_oura_metrics()
    workos = get_workos_metrics()

    # Get inbox count (unprocessed brain dumps)
    workos.inbox_count = get_inbox_count()

    # If Oura readiness is missing, use WorkOS readiness as fallback
    if oura.readiness_score is None and workos.readiness_score is not None:
        oura.readiness_score = workos.readiness_score

    energy = determine_energy_level(oura, workos)
    time_of_day, _ = get_time_of_day()
    mode_hint = determine_mode_hint(energy, time_of_day, workos)

    return StatusData(
        oura=oura,
        workos=workos,
        energy_level=energy,
        time_of_day=time_of_day,
        mode_hint=mode_hint,
        timestamp=datetime.now().isoformat(),
    )


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Thanos Statusline - Dynamic single-line status generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  thanos_statusline.py              # Full formatted output
  thanos_statusline.py --compact    # Minimal output
  thanos_statusline.py --json       # JSON for integration
  thanos_statusline.py --no-color   # Plain text

Output format:
  HIGH 78 | 85 | 12/18 | 5 | 3 tasks | deep work window
        """
    )

    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output as JSON for integration"
    )
    parser.add_argument(
        "--compact", "-c",
        action="store_true",
        help="Minimal compact output"
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Plain text without ANSI colors"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show debug information about data sources"
    )

    args = parser.parse_args()

    data = fetch_status_data()

    if args.debug:
        print(f"[DEBUG] Oura available: {data.oura.available}", file=sys.stderr)
        print(f"[DEBUG] WorkOS available: {data.workos.available}", file=sys.stderr)
        print(f"[DEBUG] Energy: {data.energy_level}", file=sys.stderr)
        print(f"[DEBUG] Time: {data.time_of_day}", file=sys.stderr)
        print(f"[DEBUG] Mode: {data.mode_hint}", file=sys.stderr)
        print("---", file=sys.stderr)

    if args.json:
        print(format_json(data))
    else:
        print(format_statusline(data, compact=args.compact, no_color=args.no_color))


if __name__ == "__main__":
    main()
