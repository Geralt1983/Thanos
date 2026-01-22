#!/usr/bin/env python3
"""
Thanos Visual State Management

Controls terminal wallpaper via Kitty image protocol.
Visual representation of CHAOS, FOCUS, BALANCE.
"""

import os
import sys
import json
from pathlib import Path
from typing import Literal, Optional, Dict, Any, List
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("thanos.visuals")

# Wallpaper directory
WALLPAPER_DIR = Path.home() / ".thanos" / "wallpapers"
WALLPAPER_DIR.mkdir(parents=True, exist_ok=True)

# State file location (as per requirements)
STATE_FILE = Path(__file__).parent.parent.parent / "State" / "visual_state.json"

# State definitions
VisualState = Literal["CHAOS", "FOCUS", "BALANCE"]


class ThanosVisualState:
    """Manage Thanos visual state in Kitty terminal."""

    STATES = {
        "CHAOS": WALLPAPER_DIR / "nebula_storm.png",
        "FOCUS": WALLPAPER_DIR / "infinity_gauntlet_fist.png",
        "BALANCE": WALLPAPER_DIR / "farm_sunrise.png",
    }

    STATE_DESCRIPTIONS = {
        "CHAOS": "Morning/Unsorted - Tasks in disarray, inbox awaits",
        "FOCUS": "Deep Work - Engaged and executing with power",
        "BALANCE": "End of Day/Complete - The Garden achieved",
    }

    @classmethod
    def set_state(cls, state: VisualState, force: bool = False) -> bool:
        """
        Set visual state by changing terminal wallpaper.

        Args:
            state: CHAOS|FOCUS|BALANCE
            force: Set even if wallpaper doesn't exist

        Returns:
            bool: True if successful
        """
        if state not in cls.STATES:
            logger.error(f"Invalid state: {state}")
            return False

        wallpaper = cls.STATES[state]

        if not wallpaper.exists() and not force:
            logger.warning(f"Wallpaper not found: {wallpaper}")
            logger.info("Run 'python3 visuals.py download' to get wallpapers")
            return False

        # Check if running in Kitty
        if not cls.is_kitty_terminal():
            logger.warning("Not running in Kitty terminal - visual state tracking only")
            # Still save state for tracking purposes
            cls._save_state(state)
            return True  # Consider it successful for tracking purposes

        # Use Kitty remote control to set background
        try:
            cmd = f"kitty @ set-background-image '{wallpaper}'"
            result = os.system(cmd)

            if result == 0:
                logger.info(f"Visual state: {state} - {cls.STATE_DESCRIPTIONS[state]}")
                cls._save_state(state)  # Save state on successful transition
                return True
            else:
                logger.error(f"Failed to set wallpaper (exit code: {result})")
                return False

        except Exception as e:
            logger.error(f"Error setting wallpaper: {e}")
            return False

    @classmethod
    def is_kitty_terminal(cls) -> bool:
        """Check if running in Kitty terminal."""
        return os.getenv("TERM") == "xterm-kitty" or "kitty" in os.getenv("TERM_PROGRAM", "").lower()

    @classmethod
    def auto_transition(cls, context: dict) -> Optional[VisualState]:
        """
        Automatically determine and set visual state based on context.

        Args:
            context: {
                'time_of_day': 'morning'|'afternoon'|'evening'|'night',
                'inbox': int,  # Number of inbox items
                'cognitive_load': 'low'|'medium'|'high',
                'energy_level': 'low'|'medium'|'high',
                'daily_goal_achieved': bool,
                'tasks_active': int
            }

        Returns:
            VisualState that was set, or None if no change
        """
        hour = datetime.now().hour
        time_of_day = context.get("time_of_day")

        # Infer time of day if not provided
        if not time_of_day:
            if 5 <= hour < 12:
                time_of_day = "morning"
            elif 12 <= hour < 17:
                time_of_day = "afternoon"
            elif 17 <= hour < 21:
                time_of_day = "evening"
            else:
                time_of_day = "night"

        # Decision logic for state transitions
        inbox = context.get("inbox", 0)
        cognitive_load = context.get("cognitive_load", "medium")
        energy_level = context.get("energy_level", "medium")
        daily_goal_achieved = context.get("daily_goal_achieved", False)
        tasks_active = context.get("tasks_active", 0)

        # BALANCE: Daily goal achieved or evening with clear inbox
        if daily_goal_achieved:
            cls.set_state("BALANCE")
            return "BALANCE"

        if time_of_day == "evening" and inbox == 0:
            cls.set_state("BALANCE")
            return "BALANCE"

        # CHAOS: Morning with unsorted inbox or low energy with many tasks
        if time_of_day == "morning" and inbox > 0:
            cls.set_state("CHAOS")
            return "CHAOS"

        if energy_level == "low" and tasks_active > 5:
            cls.set_state("CHAOS")
            return "CHAOS"

        # FOCUS: High cognitive load or high energy with work
        if cognitive_load == "high":
            cls.set_state("FOCUS")
            return "FOCUS"

        if energy_level == "high" and tasks_active > 0:
            cls.set_state("FOCUS")
            return "FOCUS"

        # Default: FOCUS (working state)
        cls.set_state("FOCUS")
        return "FOCUS"

    @classmethod
    def get_current_state(cls) -> Optional[VisualState]:
        """
        Get current visual state from persistent storage.

        Returns:
            Current state or None if unable to determine
        """
        state_data = cls._load_state()
        return state_data.get("current_state")

    @classmethod
    def get_state_history(cls, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent state transition history.

        Args:
            limit: Maximum number of history entries to return

        Returns:
            List of state transitions with timestamps
        """
        state_data = cls._load_state()
        history = state_data.get("history", [])
        return history[-limit:]

    @classmethod
    def _load_state(cls) -> Dict[str, Any]:
        """
        Load state data from persistent storage.

        Returns:
            State data dict with current_state and history
        """
        if not STATE_FILE.exists():
            return {"current_state": None, "history": []}

        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load state file: {e}")
            return {"current_state": None, "history": []}

    @classmethod
    def _save_state(cls, state: VisualState) -> None:
        """
        Save current state and append to history.

        Args:
            state: Visual state to save
        """
        # Ensure State directory exists
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Load existing state data
        state_data = cls._load_state()

        # Update current state
        state_data["current_state"] = state

        # Append to history
        if "history" not in state_data:
            state_data["history"] = []

        state_data["history"].append({
            "state": state,
            "timestamp": datetime.now().isoformat(),
            "description": cls.STATE_DESCRIPTIONS[state]
        })

        # Keep only last 100 history entries
        if len(state_data["history"]) > 100:
            state_data["history"] = state_data["history"][-100:]

        # Write to file
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(state_data, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save state file: {e}")

    @classmethod
    def _save_current_state(cls, state: VisualState) -> None:
        """Alias for _save_state for backwards compatibility."""
        cls._save_state(state)

    @classmethod
    def download_wallpapers(cls) -> None:
        """
        Download or create default wallpapers.

        For now, creates placeholder files.
        In production, would download from URL or generate.
        """
        logger.info("Creating placeholder wallpapers...")

        for state, path in cls.STATES.items():
            if not path.exists():
                # Create a minimal PNG (1x1 pixel) as placeholder
                # In production, use actual images
                logger.info(f"Creating placeholder: {path}")
                path.write_bytes(
                    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01"
                    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
                )

        logger.info("Wallpapers ready (placeholders created)")
        logger.info(f"Location: {WALLPAPER_DIR}")
        logger.info("\nTo use custom images:")
        logger.info("1. Create/download 3 images (1920x1080 recommended)")
        logger.info("2. Save as:")
        for state, path in cls.STATES.items():
            logger.info(f"   - {state}: {path}")


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python3 visuals.py <command> [args]")
        print("\nCommands:")
        print("  set <state>        - Set visual state (CHAOS|FOCUS|BALANCE)")
        print("  auto               - Auto-detect and set state")
        print("  get                - Get current state")
        print("  history [limit]    - Show state transition history (default: 10)")
        print("  download           - Download/create wallpapers")
        print("  check              - Check if Kitty terminal")
        sys.exit(1)

    command = sys.argv[1]

    if command == "set":
        if len(sys.argv) < 3:
            print("Error: Missing state argument")
            print("Usage: python3 visuals.py set <CHAOS|FOCUS|BALANCE>")
            sys.exit(1)

        state = sys.argv[2].upper()
        if state not in ThanosVisualState.STATES:
            print(f"Error: Invalid state '{state}'")
            print("Valid states: CHAOS, FOCUS, BALANCE")
            sys.exit(1)

        success = ThanosVisualState.set_state(state)  # type: ignore
        if success:
            print(f"✓ Visual state: {state}")
        else:
            print("✗ Failed to set visual state")
            sys.exit(1)

    elif command == "auto":
        # Example context
        context = {
            "time_of_day": "evening",
            "inbox": 0,
            "cognitive_load": "medium",
            "energy_level": "medium",
            "daily_goal_achieved": False,
            "tasks_active": 3,
        }

        state = ThanosVisualState.auto_transition(context)
        print(f"✓ Auto-transitioned to: {state}")

    elif command == "get":
        state = ThanosVisualState.get_current_state()
        if state:
            print(f"Current state: {state}")
            print(f"Description: {ThanosVisualState.STATE_DESCRIPTIONS[state]}")
        else:
            print("No state set")

    elif command == "history":
        limit = 10
        if len(sys.argv) > 2:
            try:
                limit = int(sys.argv[2])
            except ValueError:
                print("Error: Invalid limit value")
                sys.exit(1)

        history = ThanosVisualState.get_state_history(limit)
        if not history:
            print("No state history")
        else:
            print(f"\n=== State Transition History (last {len(history)} entries) ===\n")
            for entry in history:
                timestamp = datetime.fromisoformat(entry['timestamp'])
                state = entry['state']
                desc = entry['description']
                print(f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} → {state}")
                print(f"  {desc}\n")

    elif command == "download":
        ThanosVisualState.download_wallpapers()

    elif command == "check":
        if ThanosVisualState.is_kitty_terminal():
            print("✓ Running in Kitty terminal")
        else:
            print("✗ Not running in Kitty terminal")
            print(f"TERM: {os.getenv('TERM')}")
            print(f"TERM_PROGRAM: {os.getenv('TERM_PROGRAM')}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
