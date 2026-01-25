#!/usr/bin/env python3
"""
Thanos Statusline Generator for Claude Code

Generates a compact statusline showing:
- Work metrics (points, streak, pace)
- Health readiness from Oura
- Active tasks count
- Git branch
- Session info

Output format is designed for Claude Code's statusline hook.
"""

import json
import os
import sys
import sqlite3
from datetime import datetime, date
from pathlib import Path

# Color codes for terminal output
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground colors
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright variants
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"


def get_thanos_root() -> Path:
    """Get Thanos project root directory."""
    # Check environment variable first
    if "THANOS_ROOT" in os.environ:
        return Path(os.environ["THANOS_ROOT"])

    # Fall back to script location
    script_dir = Path(__file__).parent
    return script_dir.parent.parent


def get_git_branch(cwd: str = None) -> str:
    """Get current git branch name."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=cwd or get_thanos_root(),
            capture_output=True,
            text=True,
            timeout=2
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def get_work_metrics() -> dict:
    """
    Get work metrics from WorkOS MCP database.

    Returns dict with:
    - points_earned: int
    - target_points: int
    - streak: int
    - pace: str (ahead/on_track/behind)
    - active_tasks: int
    """
    metrics = {
        "points_earned": 0,
        "target_points": 18,
        "streak": 0,
        "pace": "unknown",
        "active_tasks": 0
    }

    thanos_root = get_thanos_root()

    # Try unified DB first
    db_paths = [
        thanos_root / "State" / "thanos_unified.db",
        thanos_root / "State" / "thanos.db",
        thanos_root / "mcp-servers" / "workos-mcp" / "workos.db",
    ]

    for db_path in db_paths:
        if db_path.exists():
            try:
                conn = sqlite3.connect(str(db_path), timeout=1)
                cursor = conn.cursor()

                # Get today's date
                today = date.today().isoformat()

                # Try to get daily metrics
                try:
                    cursor.execute("""
                        SELECT points_earned, target_points, streak_days
                        FROM daily_metrics
                        WHERE date = ?
                    """, (today,))
                    row = cursor.fetchone()
                    if row:
                        metrics["points_earned"] = row[0] or 0
                        metrics["target_points"] = row[1] or 18
                        metrics["streak"] = row[2] or 0
                except sqlite3.OperationalError:
                    pass

                # Get active tasks count
                try:
                    cursor.execute("""
                        SELECT COUNT(*) FROM tasks
                        WHERE status = 'active'
                    """)
                    row = cursor.fetchone()
                    if row:
                        metrics["active_tasks"] = row[0] or 0
                except sqlite3.OperationalError:
                    pass

                conn.close()

                # Calculate pace
                if metrics["target_points"] > 0:
                    progress = metrics["points_earned"] / metrics["target_points"]
                    hour = datetime.now().hour
                    expected = hour / 16  # Assuming 16-hour workday (6am-10pm)

                    if progress >= expected + 0.15:
                        metrics["pace"] = "ahead"
                    elif progress >= expected - 0.15:
                        metrics["pace"] = "on_track"
                    else:
                        metrics["pace"] = "behind"

                break  # Found working database

            except Exception:
                continue

    return metrics


def get_oura_readiness() -> int:
    """
    Get Oura readiness score from cache.

    Returns readiness score (0-100) or -1 if unavailable.
    """
    thanos_root = get_thanos_root()
    cache_path = thanos_root / "State" / "OuraCache.json"

    if not cache_path.exists():
        return -1

    try:
        with open(cache_path, 'r') as f:
            cache = json.load(f)

        # Look for today's readiness
        today = date.today().isoformat()

        # Check readiness data
        if "readiness" in cache:
            readiness_data = cache["readiness"]
            if isinstance(readiness_data, list):
                for entry in readiness_data:
                    if entry.get("day") == today:
                        return entry.get("score", -1)
            elif isinstance(readiness_data, dict):
                if readiness_data.get("day") == today:
                    return readiness_data.get("score", -1)

        # Check daily_readiness
        if "daily_readiness" in cache:
            for entry in cache["daily_readiness"]:
                if entry.get("day") == today:
                    return entry.get("score", -1)

        return -1

    except Exception:
        return -1


def get_interaction_count() -> int:
    """Get today's interaction count from TimeState."""
    thanos_root = get_thanos_root()
    state_path = thanos_root / "State" / "TimeState.json"

    if not state_path.exists():
        return 0

    try:
        with open(state_path, 'r') as f:
            state = json.load(f)
        return state.get("interaction_count_today", 0)
    except Exception:
        return 0


def get_daemon_status() -> str:
    """
    Check Thanos daemon status via launchctl.

    Returns:
        🟢 = Running with PID
        🟡 = Loaded but no PID
        🔴 = Not running
    """
    try:
        import subprocess
        result = subprocess.run(
            ["launchctl", "list"],
            capture_output=True,
            text=True,
            timeout=2
        )
        for line in result.stdout.split('\n'):
            if 'com.thanos.daemon' in line:
                parts = line.split()
                if parts and parts[0].isdigit():
                    return "🟢"  # Running with PID
                return "🟡"  # Loaded but no PID
        return "🔴"  # Not found
    except Exception:
        return "🔴"


def get_model_from_context(context: dict) -> str:
    """Extract model name from Claude Code context."""
    model = context.get("model", {})
    if isinstance(model, dict):
        display_name = model.get("display_name", "")
        if display_name:
            return display_name
        model_id = model.get("id", "")
    else:
        model_id = str(model) if model else ""

    # Shorten model names
    if "opus" in model_id.lower():
        return "Opus 4.5"
    elif "sonnet" in model_id.lower():
        return "Sonnet 4"
    elif "haiku" in model_id.lower():
        return "Haiku 3.5"

    return model_id.replace("claude-", "").split("-")[0].title() if model_id else "Claude"


def format_pace_indicator(pace: str, points: int, target: int) -> str:
    """Format pace indicator with color coding."""
    progress_pct = int((points / target) * 100) if target > 0 else 0

    if pace == "ahead":
        color = Colors.BRIGHT_GREEN
        icon = "+"
    elif pace == "on_track":
        color = Colors.BRIGHT_YELLOW
        icon = "="
    elif pace == "behind":
        color = Colors.BRIGHT_RED
        icon = "-"
    else:
        color = Colors.DIM
        icon = "?"

    return f"{color}{points}/{target}pt {icon}{Colors.RESET}"


def format_readiness(score: int) -> str:
    """Format Oura readiness with color coding."""
    if score < 0:
        return ""

    if score >= 85:
        color = Colors.BRIGHT_GREEN
    elif score >= 70:
        color = Colors.BRIGHT_YELLOW
    else:
        color = Colors.BRIGHT_RED

    return f"{color}{score}r{Colors.RESET}"


def format_streak(streak: int) -> str:
    """Format streak with fire emoji if active."""
    if streak <= 0:
        return ""
    return f"{Colors.BRIGHT_RED}{streak}d{Colors.RESET}"


def generate_statusline(context: dict = None) -> str:
    """
    Generate the Thanos statusline.

    Format:
    Thanos | Opus 4.5 | main | 12/18pt + | 85r | 5d | 3 active

    Components:
    - Project name (Thanos)
    - Model name
    - Git branch
    - Work points/target with pace indicator
    - Oura readiness score
    - Streak days
    - Active tasks count
    """
    context = context or {}
    parts = []

    # Daemon status (first - most important health indicator)
    daemon = get_daemon_status()
    parts.append(f"{daemon}")

    # Project identifier
    parts.append(f"{Colors.BOLD}{Colors.MAGENTA}Thanos{Colors.RESET}")

    # Model name
    model = get_model_from_context(context)
    if model:
        parts.append(f"{Colors.CYAN}{model}{Colors.RESET}")

    # Git branch
    cwd = context.get("workspace", {}).get("current_dir") or context.get("cwd")
    branch = get_git_branch(cwd)
    if branch:
        parts.append(f"{Colors.YELLOW}{branch}{Colors.RESET}")

    # Work metrics section
    metrics = get_work_metrics()

    # Points and pace
    pace_str = format_pace_indicator(
        metrics["pace"],
        metrics["points_earned"],
        metrics["target_points"]
    )
    if pace_str:
        parts.append(pace_str)

    # Oura readiness
    readiness = get_oura_readiness()
    readiness_str = format_readiness(readiness)
    if readiness_str:
        parts.append(readiness_str)

    # Streak
    streak_str = format_streak(metrics["streak"])
    if streak_str:
        parts.append(streak_str)

    # Active tasks
    if metrics["active_tasks"] > 0:
        parts.append(f"{Colors.BLUE}{metrics['active_tasks']} active{Colors.RESET}")

    # Interaction count (subtle)
    interactions = get_interaction_count()
    if interactions > 0:
        parts.append(f"{Colors.DIM}#{interactions}{Colors.RESET}")

    return " | ".join(parts)


def main():
    """Main entry point - reads context from stdin if available."""
    context = {}

    # Try to read JSON context from stdin
    if not sys.stdin.isatty():
        try:
            input_data = sys.stdin.read()
            if input_data.strip():
                context = json.loads(input_data)
        except (json.JSONDecodeError, Exception):
            pass

    # Generate and print statusline
    statusline = generate_statusline(context)
    print(statusline)


if __name__ == "__main__":
    main()
