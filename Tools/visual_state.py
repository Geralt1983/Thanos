#!/usr/bin/env python3
"""
Thanos Visual State Controller

Controls Kitty terminal wallpaper based on workflow state:
- CHAOS: nebula_storm.png - Morning/Unsorted
- FOCUS: infinity_gauntlet_fist.png - Deep Work
- BALANCE: farm_sunrise.png - Daily goals achieved

Usage:
    python visual_state.py chaos   # Enter chaos state
    python visual_state.py focus   # Enter focus state
    python visual_state.py balance # Enter balance state
    python visual_state.py auto    # Auto-detect state from metrics
    python visual_state.py status  # Show current state
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

WALLPAPER_DIR = Path.home() / ".thanos" / "wallpapers"
STATE_FILE = Path.home() / "Projects" / "Thanos" / "State" / "visual_state.json"

STATES = {
    "chaos": {
        "wallpaper": "nebula_storm.png",
        "description": "Morning/Unsorted - tasks in disarray",
        "color": "\033[35m",  # Magenta
    },
    "focus": {
        "wallpaper": "infinity_gauntlet_fist.png",
        "description": "Deep Work - engaged and executing",
        "color": "\033[33m",  # Yellow/Gold
    },
    "balance": {
        "wallpaper": "farm_sunrise.png",
        "description": "End of Day/Done - The Garden achieved",
        "color": "\033[32m",  # Green
    },
}

RESET = "\033[0m"


def set_kitty_wallpaper(wallpaper_name: str) -> bool:
    """Set Kitty terminal wallpaper."""
    wallpaper_path = WALLPAPER_DIR / wallpaper_name

    if not wallpaper_path.exists():
        # Create a placeholder message if wallpaper doesn't exist
        print(f"Note: Wallpaper {wallpaper_path} not found")
        print(f"Place your wallpaper at: {wallpaper_path}")
        return False

    try:
        subprocess.run(
            ["kitty", "@", "set-background-image", str(wallpaper_path)],
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError:
        # Kitty remote control might not be enabled
        return False
    except FileNotFoundError:
        # Kitty not found
        return False


def save_state(state: str) -> None:
    """Save current visual state to file."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "state": state,
        "timestamp": datetime.now().isoformat(),
        "wallpaper": STATES[state]["wallpaper"],
    }
    STATE_FILE.write_text(json.dumps(data, indent=2))


def load_state() -> dict:
    """Load current visual state from file."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return {"state": "unknown", "timestamp": None, "wallpaper": None}


def auto_detect_state() -> str:
    """Auto-detect state based on current metrics."""
    # Try to load TimeState for context
    time_state_path = Path.home() / "Projects" / "Thanos" / "State" / "TimeState.json"
    thanos_db_path = Path.home() / "Projects" / "Thanos" / "State" / "thanos_unified.db"

    # Default to chaos at start
    hour = datetime.now().hour

    # Morning = chaos (inbox processing time)
    if 5 <= hour < 10:
        return "chaos"

    # Check if daily goal is met (would indicate balance)
    if thanos_db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(str(thanos_db_path))
            cursor = conn.cursor()

            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("""
                SELECT SUM(points_final)
                FROM tasks
                WHERE status = 'done'
                AND date(completed_at) = ?
            """, (today,))

            result = cursor.fetchone()
            points_today = result[0] or 0
            conn.close()

            # Assume 18 point target
            if points_today >= 18:
                return "balance"
        except Exception:
            pass

    # Default to focus during work hours
    if 10 <= hour < 18:
        return "focus"

    # Evening/night
    return "balance"


def transition_state(target_state: str, quiet: bool = False) -> None:
    """Transition to a new visual state."""
    if target_state not in STATES:
        print(f"Unknown state: {target_state}")
        print(f"Valid states: {', '.join(STATES.keys())}")
        sys.exit(1)

    state_info = STATES[target_state]
    color = state_info["color"]

    # Set wallpaper
    wallpaper_set = set_kitty_wallpaper(state_info["wallpaper"])

    # Save state
    save_state(target_state)

    if not quiet:
        print(f"{color}{'=' * 40}{RESET}")
        print(f"{color}STATE: {target_state.upper()}{RESET}")
        print(f"{color}{state_info['description']}{RESET}")
        print(f"{color}{'=' * 40}{RESET}")

        if not wallpaper_set:
            print(f"\nWallpaper not set (kitty remote control may not be enabled)")
            print(f"Enable with: kitty @ ls")


def show_status() -> None:
    """Show current visual state."""
    current = load_state()
    state = current.get("state", "unknown")

    if state in STATES:
        info = STATES[state]
        color = info["color"]
        print(f"{color}Current State: {state.upper()}{RESET}")
        print(f"{color}{info['description']}{RESET}")
        print(f"Since: {current.get('timestamp', 'unknown')}")
    else:
        print(f"Current State: UNKNOWN")
        print("Use 'visual_state.py auto' to auto-detect")


def main():
    parser = argparse.ArgumentParser(
        description="Thanos Visual State Controller",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "state",
        nargs="?",
        choices=["chaos", "focus", "balance", "auto", "status"],
        default="status",
        help="Target state or 'auto' to detect, 'status' to show current"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress output"
    )

    args = parser.parse_args()

    if args.state == "status":
        show_status()
    elif args.state == "auto":
        detected = auto_detect_state()
        if not args.quiet:
            print(f"Auto-detected state: {detected}")
        transition_state(detected, args.quiet)
    else:
        transition_state(args.state, args.quiet)


if __name__ == "__main__":
    main()
