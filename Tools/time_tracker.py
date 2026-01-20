#!/usr/bin/env python3
"""
Thanos Time Tracker - Vigilance Daemon Component

Tracks session time and provides elapsed time context.
Designed to run on every UserPromptSubmit hook.

Usage:
    python3 time_tracker.py              # Update and output elapsed time
    python3 time_tracker.py --reset      # Reset session start
    python3 time_tracker.py --status     # Show current time state
    python3 time_tracker.py --json       # Output JSON for hook injection
"""

import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any


# Configuration
STATE_DIR = Path(__file__).parent.parent / "State"
TIME_STATE_FILE = STATE_DIR / "TimeState.json"

# Time thresholds for warnings (in minutes)
TIME_THRESHOLDS = {
    30: "Half hour in. Pace yourself.",
    60: "One hour. How's your focus?",
    90: "90 minutes. Consider a break.",
    120: "Two hours deep. The mind requires rest to maintain balance.",
    180: "Three hours. The universe demands you pause.",
}


def get_local_tz():
    """Get local timezone."""
    return datetime.now().astimezone().tzinfo


def now_iso() -> str:
    """Get current time in ISO format with timezone."""
    return datetime.now(get_local_tz()).isoformat()


def load_time_state() -> Dict[str, Any]:
    """Load current time state from file."""
    if TIME_STATE_FILE.exists():
        try:
            with open(TIME_STATE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "last_interaction": None,
        "session_started": None,
        "interaction_count_today": 0,
    }


def save_time_state(state: Dict[str, Any]) -> None:
    """Save time state to file."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(TIME_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def calculate_elapsed(start_time: str) -> Dict[str, Any]:
    """Calculate elapsed time since session start."""
    try:
        start = datetime.fromisoformat(start_time)
        now = datetime.now(get_local_tz())

        # Handle naive datetime
        if start.tzinfo is None:
            start = start.replace(tzinfo=get_local_tz())

        elapsed = now - start
        total_minutes = int(elapsed.total_seconds() / 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60

        return {
            "total_minutes": total_minutes,
            "hours": hours,
            "minutes": minutes,
            "formatted": f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m",
            "seconds": int(elapsed.total_seconds()),
        }
    except Exception:
        return {
            "total_minutes": 0,
            "hours": 0,
            "minutes": 0,
            "formatted": "0m",
            "seconds": 0,
        }


def get_time_warning(elapsed_minutes: int) -> Optional[str]:
    """Get appropriate time warning based on elapsed time."""
    warning = None
    for threshold, message in sorted(TIME_THRESHOLDS.items()):
        if elapsed_minutes >= threshold:
            warning = message
    return warning


def get_time_of_day_context() -> Dict[str, str]:
    """Get time of day context for Thanos personality."""
    hour = datetime.now().hour

    if 5 <= hour < 12:
        return {
            "period": "morning",
            "greeting": "The day begins...",
            "mode": "full_capacity"
        }
    elif 12 <= hour < 17:
        return {
            "period": "afternoon",
            "greeting": "Midday execution...",
            "mode": "full_capacity"
        }
    elif 17 <= hour < 21:
        return {
            "period": "evening",
            "greeting": "The day draws to close...",
            "mode": "wrap_up"
        }
    else:
        return {
            "period": "night",
            "greeting": "The universe rests. Should you?",
            "mode": "discourage_complex"
        }


def update_and_track() -> Dict[str, Any]:
    """Update time state and return tracking info."""
    state = load_time_state()
    now = now_iso()
    today = datetime.now().strftime("%Y-%m-%d")

    # Check if we need to start a new session
    session_started = state.get("session_started")

    if not session_started:
        # New session
        session_started = now
        state["session_started"] = session_started
        state["interaction_count_today"] = 1
    else:
        # Check if session is from a different day (reset daily)
        try:
            session_date = datetime.fromisoformat(session_started).strftime("%Y-%m-%d")
            if session_date != today:
                # New day, new session
                session_started = now
                state["session_started"] = session_started
                state["interaction_count_today"] = 1
            else:
                state["interaction_count_today"] = state.get("interaction_count_today", 0) + 1
        except:
            session_started = now
            state["session_started"] = session_started
            state["interaction_count_today"] = 1

    # Update last interaction
    state["last_interaction"] = {
        "timestamp": now,
        "type": "user_prompt",
        "agent": "thanos"
    }

    # Calculate elapsed time
    elapsed = calculate_elapsed(session_started)

    # Get time warning if applicable
    warning = get_time_warning(elapsed["total_minutes"])

    # Get time of day context
    tod = get_time_of_day_context()

    # Save state
    save_time_state(state)

    return {
        "current_time": datetime.now().strftime("%I:%M %p"),
        "current_time_24h": datetime.now().strftime("%H:%M"),
        "session_started": session_started,
        "elapsed": elapsed,
        "warning": warning,
        "time_of_day": tod,
        "interaction_count": state["interaction_count_today"],
    }


def reset_session() -> Dict[str, Any]:
    """Reset session start time."""
    state = load_time_state()
    state["session_started"] = now_iso()
    state["interaction_count_today"] = 0
    save_time_state(state)
    return {"status": "reset", "session_started": state["session_started"]}


def format_status_output(info: Dict[str, Any]) -> str:
    """Format time info for human-readable output."""
    lines = [
        f"Time: {info['current_time']}",
        f"Session: {info['elapsed']['formatted']}",
        f"Interactions: {info['interaction_count']}",
    ]

    if info.get("warning"):
        lines.append(f"Warning: {info['warning']}")

    lines.append(f"Mode: {info['time_of_day']['mode']}")

    return " | ".join(lines)


def format_context_injection(info: Dict[str, Any]) -> str:
    """Format time info for context injection into Claude."""
    parts = [
        f"[{info['current_time']}]",
        f"[Session: {info['elapsed']['formatted']}]",
    ]

    if info.get("warning"):
        parts.append(f"[{info['warning']}]")

    if info["time_of_day"]["mode"] == "discourage_complex":
        parts.append("[Late hour - avoid complex work]")
    elif info["time_of_day"]["mode"] == "wrap_up":
        parts.append("[Evening - wrap-up mode]")

    return " ".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Thanos Time Tracker")
    parser.add_argument("--reset", action="store_true", help="Reset session start time")
    parser.add_argument("--status", action="store_true", help="Show current time state")
    parser.add_argument("--json", action="store_true", help="Output JSON for hook injection")
    parser.add_argument("--context", action="store_true", help="Output context injection string")
    args = parser.parse_args()

    if args.reset:
        result = reset_session()
        print(json.dumps(result, indent=2))
        return

    info = update_and_track()

    if args.json:
        print(json.dumps(info, indent=2))
    elif args.context:
        print(format_context_injection(info))
    elif args.status:
        print(format_status_output(info))
    else:
        # Default: output context injection string
        print(format_context_injection(info))


if __name__ == "__main__":
    main()
