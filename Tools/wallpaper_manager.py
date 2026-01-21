#!/usr/bin/env python3
"""
Kitty Terminal Visual State Manager for Thanos

Manages terminal wallpaper based on workflow state:
- CHAOS: Morning disorder, unsorted tasks (nebula_storm.png)
- FOCUS: Deep work engaged (infinity_gauntlet_fist.png)
- BALANCE: Daily goals achieved (farm_sunrise.png)
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Literal

StateType = Literal["chaos", "focus", "balance"]

# Wallpaper paths
THANOS_ROOT = Path.home() / "Projects" / "Thanos"
WALLPAPER_DIR = Path.home() / ".thanos" / "wallpapers"

WALLPAPERS = {
    "chaos": WALLPAPER_DIR / "nebula_storm.png",
    "focus": WALLPAPER_DIR / "infinity_gauntlet_fist.png",
    "balance": WALLPAPER_DIR / "farm_sunrise.png"
}


class WallpaperManager:
    """Manages Kitty terminal wallpaper based on workflow state."""

    def __init__(self):
        """Initialize wallpaper manager."""
        self.thanos_root = THANOS_ROOT
        self.wallpaper_dir = WALLPAPER_DIR
        self.time_state_file = self.thanos_root / "State" / "TimeState.json"

    def is_kitty_running(self) -> bool:
        """Check if running inside Kitty terminal."""
        return "KITTY_PID" in subprocess.os.environ

    def set_wallpaper(self, state: StateType) -> bool:
        """
        Set Kitty wallpaper for given state.

        Args:
            state: One of "chaos", "focus", "balance"

        Returns:
            True if successful, False otherwise
        """
        if not self.is_kitty_running():
            return False

        wallpaper_path = WALLPAPERS.get(state)
        if not wallpaper_path or not wallpaper_path.exists():
            print(f"Warning: Wallpaper not found: {wallpaper_path}", file=sys.stderr)
            return False

        try:
            # Find the actual Kitty socket
            import os
            import glob

            # Look for any kitty socket
            sockets = glob.glob("/tmp/kitty-*")
            if not sockets:
                print("No Kitty socket found", file=sys.stderr)
                return False

            # Use the first socket found (usually only one)
            socket_path = f"unix:{sockets[0]}"

            # Use scaled layout with resized images
            result = subprocess.run(
                ["kitty", "@", "--to", socket_path, "set-background-image",
                 "--layout", "scaled", str(wallpaper_path)],
                capture_output=True,
                text=True,
                timeout=15  # Increased timeout for large images
            )
            if result.returncode != 0:
                # Print actual error from kitty command
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                print(f"Kitty command failed: {error_msg}", file=sys.stderr)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"Error setting wallpaper: {e}", file=sys.stderr)
            return False

    def load_time_state(self) -> Optional[Dict]:
        """Load TimeState.json if available."""
        if not self.time_state_file.exists():
            return None

        try:
            with open(self.time_state_file, 'r') as f:
                return json.load(f)
        except Exception:
            return None

    def get_workos_metrics(self) -> Optional[Dict]:
        """Get current WorkOS metrics via MCP."""
        try:
            # Import MCP adapter
            sys.path.insert(0, str(self.thanos_root / "Tools"))
            from adapters.mcp_adapter import get_mcp_client

            client = get_mcp_client()
            result = client.call_tool("workos_get_today_metrics", {})
            return result if isinstance(result, dict) else None
        except Exception:
            return None

    def detect_state(self) -> StateType:
        """
        Auto-detect current workflow state.

        Returns:
            "chaos", "focus", or "balance"
        """
        hour = datetime.now().hour

        # Check for BALANCE state (daily goal achieved)
        workos_metrics = self.get_workos_metrics()
        if workos_metrics:
            points = workos_metrics.get('points', 0)
            target = workos_metrics.get('target', 18)
            if points >= target:
                return "balance"

        # Check for FOCUS state (deep work indicators)
        time_state = self.load_time_state()
        if time_state:
            # If session has been running > 30 min, likely in focus
            duration_ms = time_state.get('duration_ms', 0)
            if duration_ms > 30 * 60 * 1000:  # 30 minutes
                return "focus"

        # Default to CHAOS (morning, unsorted, or starting state)
        # Morning hours (5am-12pm) or fresh session
        if 5 <= hour < 12:
            return "chaos"

        # If we have active tasks, still in CHAOS
        if workos_metrics:
            active_count = workos_metrics.get('active_tasks', 0)
            if active_count > 3:
                return "chaos"

        # Default: FOCUS (afternoon/evening work state)
        return "focus"

    def apply_state(self, state: StateType) -> bool:
        """Apply wallpaper for given state."""
        return self.set_wallpaper(state)

    def auto_apply(self) -> Optional[StateType]:
        """Auto-detect and apply appropriate state."""
        state = self.detect_state()
        success = self.apply_state(state)
        return state if success else None


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Manage Kitty terminal wallpaper based on workflow state"
    )
    parser.add_argument(
        "--state",
        choices=["chaos", "focus", "balance"],
        help="Manually set specific state"
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto-detect and apply state"
    )
    parser.add_argument(
        "--detect",
        action="store_true",
        help="Detect current state without applying"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if Kitty is running"
    )

    args = parser.parse_args()
    manager = WallpaperManager()

    if args.check:
        if manager.is_kitty_running():
            print("Kitty terminal detected")
            sys.exit(0)
        else:
            print("Not running in Kitty terminal")
            sys.exit(1)

    if args.detect:
        state = manager.detect_state()
        print(state)
        sys.exit(0)

    if args.state:
        success = manager.apply_state(args.state)
        if success:
            print(f"Applied {args.state.upper()} state")
            sys.exit(0)
        else:
            print(f"Failed to apply {args.state} state", file=sys.stderr)
            sys.exit(1)

    if args.auto:
        state = manager.auto_apply()
        if state:
            print(f"Auto-applied {state.upper()} state")
            sys.exit(0)
        else:
            print("Failed to auto-apply state", file=sys.stderr)
            sys.exit(1)

    # Default: auto-apply
    state = manager.auto_apply()
    if state:
        print(f"{state.upper()} state active")
    else:
        print("Not running in Kitty terminal", file=sys.stderr)


if __name__ == "__main__":
    main()
