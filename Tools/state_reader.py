#!/usr/bin/env python3
"""
Fast state file reader for hooks - no API calls.

This module provides quick access to Thanos state files for use in
Claude Code lifecycle hooks. It's designed to be fast and reliable,
reading only local files without any external API calls.

Usage:
    from Tools.state_reader import StateReader

    reader = StateReader(Path("/Users/jeremy/Projects/Thanos/State"))
    context = reader.get_quick_context()
"""

from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
import re


class StateReader:
    """Read Thanos state files quickly for hook context."""

    def __init__(self, state_dir: Path):
        """Initialize with the State directory path.

        Args:
            state_dir: Path to the Thanos State directory
        """
        self.state_dir = Path(state_dir)

    def get_current_focus(self) -> Optional[str]:
        """Extract current focus from CurrentFocus.md.

        Returns:
            The primary focus string, or None if not found
        """
        path = self.state_dir / "CurrentFocus.md"
        if not path.exists():
            return None

        try:
            content = path.read_text()
            # Match **Primary focus**: value pattern
            match = re.search(r'\*\*Primary focus\*\*:\s*(.+)', content)
            return match.group(1).strip() if match else None
        except Exception:
            return None

    def get_pending_commitments(self) -> int:
        """Count pending commitments.

        Returns:
            Number of unchecked items in Commitments.md
        """
        path = self.state_dir / "Commitments.md"
        if not path.exists():
            return 0

        try:
            content = path.read_text()
            return content.count("- [ ]")
        except Exception:
            return 0

    def get_todays_top3(self) -> List[str]:
        """Extract today's top 3 priorities.

        Looks in Today.md first, then falls back to CurrentFocus.md.

        Returns:
            List of up to 3 priority items
        """
        # Try Today.md first
        path = self.state_dir / "Today.md"
        if not path.exists():
            path = self.state_dir / "CurrentFocus.md"
        if not path.exists():
            return []

        try:
            content = path.read_text()
            items = []
            in_top3 = False

            for line in content.split('\n'):
                # Look for Top 3 or Priorities section
                if 'Top 3' in line or 'Priorities' in line:
                    in_top3 = True
                    continue
                if in_top3:
                    # Stop at next section header
                    if line.startswith('#'):
                        break
                    # Match checkbox items with various formats:
                    # 1. [ ] item, - [ ] item, * [ ] item
                    # Also handles: 1. [x] item (completed)
                    match = re.match(r'^[\d]+\.\s*\[[ x]\]\s*(.+)', line)
                    if not match:
                        match = re.match(r'^[\-\*]\s*\[[ x]\]\s*(.+)', line)
                    if match:
                        # Extract just the item text (before any | or deadline info)
                        item_text = match.group(1).split('|')[0].strip()
                        items.append(item_text)
                        if len(items) >= 3:
                            break

            return items
        except Exception:
            return []

    def get_energy_state(self) -> Optional[str]:
        """Extract current energy state if logged.

        Returns:
            Energy description string, or None if not found
        """
        path = self.state_dir / "CurrentFocus.md"
        if not path.exists():
            return None

        try:
            content = path.read_text()
            # Look for energy rating
            match = re.search(r'\*\*Current energy\*\*:\s*(.+)', content)
            if match:
                value = match.group(1).strip()
                # Skip placeholder values
                if '[' not in value and value:
                    return value
            return None
        except Exception:
            return None

    def get_week_theme(self) -> Optional[str]:
        """Extract this week's theme.

        Returns:
            Week theme string, or None if not found
        """
        path = self.state_dir / "CurrentFocus.md"
        if not path.exists():
            path = self.state_dir / "ThisWeek.md"
        if not path.exists():
            return None

        try:
            content = path.read_text()
            # Look in Week's Theme section
            in_theme = False
            for line in content.split('\n'):
                if "Week's Theme" in line or "This Week" in line:
                    in_theme = True
                    continue
                if in_theme and line.strip() and not line.startswith('#'):
                    return line.strip()
            return None
        except Exception:
            return None

    def get_blockers(self) -> List[str]:
        """Extract any current blockers.

        Returns:
            List of blocker descriptions
        """
        path = self.state_dir / "CurrentFocus.md"
        if not path.exists():
            return []

        try:
            content = path.read_text()
            match = re.search(r'\*\*Blockers\*\*:\s*(.+)', content)
            if match:
                value = match.group(1).strip()
                if value.lower() not in ['none', 'none currently', 'n/a', '']:
                    return [value]
            return []
        except Exception:
            return []

    def get_waiting_for(self) -> List[str]:
        """Extract items waiting on others.

        Returns:
            List of waiting-for items
        """
        path = self.state_dir / "WaitingFor.md"
        if not path.exists():
            return []

        try:
            content = path.read_text()
            items = []
            for line in content.split('\n'):
                # Match checkbox items that are not completed
                match = re.match(r'^[\-\*]\s*\[ \]\s*(.+)', line)
                if match:
                    items.append(match.group(1).strip())
            return items[:5]  # Limit to 5
        except Exception:
            return []

    def get_last_interaction_time(self) -> Optional[datetime]:
        """Get the timestamp of the last user interaction.

        Reads the TimeState.json file and extracts the last interaction
        timestamp for calculating elapsed time between interactions.

        Handles corrupted TimeState.json files gracefully by returning None,
        allowing the system to treat it as a first interaction.

        Returns:
            datetime of last interaction, or None if not found/unavailable/corrupted
        """
        path = self.state_dir / "TimeState.json"
        if not path.exists():
            return None

        try:
            content = path.read_text()
            data = json.loads(content)
            timestamp_str = data.get("last_interaction", {}).get("timestamp")
            if timestamp_str:
                return datetime.fromisoformat(timestamp_str)
            return None
        except (json.JSONDecodeError, OSError, ValueError, TypeError, AttributeError):
            # Handle corrupted/unreadable files or invalid data gracefully:
            # - JSONDecodeError: corrupted JSON syntax
            # - OSError: file read errors
            # - ValueError: invalid datetime format
            # - TypeError/AttributeError: unexpected data structure
            return None

    def calculate_elapsed_time(self) -> Optional[timedelta]:
        """Calculate elapsed time since the last user interaction.

        Uses get_last_interaction_time() to retrieve the last interaction
        timestamp and calculates the difference from the current time.

        Returns:
            timedelta representing elapsed time since last interaction,
            or None if no previous interaction recorded (first interaction)
        """
        last_time = self.get_last_interaction_time()
        if last_time is None:
            return None

        try:
            now = datetime.now().astimezone()
            # Ensure last_time is timezone-aware for comparison
            if last_time.tzinfo is None:
                # Assume local timezone if not specified
                last_time = last_time.astimezone()
            elapsed = now - last_time
            # Ensure we don't return negative timedelta (clock skew, etc.)
            return elapsed if elapsed > timedelta(0) else timedelta(0)
        except Exception:
            return None

    def format_elapsed_time(self, elapsed: Optional[timedelta],
                            reference_time: Optional[datetime] = None) -> str:
        """Format a timedelta as human-readable elapsed time string.

        Converts a timedelta to a natural language string showing the most
        significant time units (up to two), with " ago" suffix.

        For very long gaps (>7 days), includes the actual date for clarity.

        Args:
            elapsed: The timedelta to format, or None for first interaction
            reference_time: Optional reference time (defaults to now) for
                           calculating the actual date for long gaps

        Returns:
            Human-readable string like "5 minutes ago", "2 hours and 30 minutes ago",
            "1 day and 3 hours ago", "10 days ago (on Mon, Dec 30)",
            or "This is our first interaction" if elapsed is None
        """
        if elapsed is None:
            return "This is our first interaction"

        total_seconds = int(elapsed.total_seconds())

        if total_seconds < 60:
            return "just now"

        # Calculate time components
        days = total_seconds // 86400
        remaining = total_seconds % 86400
        hours = remaining // 3600
        remaining = remaining % 3600
        minutes = remaining // 60

        # Build human-readable parts
        parts = []

        if days > 0:
            parts.append(f"{days} day" + ("s" if days != 1 else ""))
        if hours > 0:
            parts.append(f"{hours} hour" + ("s" if hours != 1 else ""))
        if minutes > 0 and days == 0:  # Only show minutes if no days
            parts.append(f"{minutes} minute" + ("s" if minutes != 1 else ""))

        # Take up to 2 most significant parts
        parts = parts[:2]

        if not parts:
            return "just now"

        if len(parts) == 1:
            time_str = f"{parts[0]} ago"
        else:
            time_str = f"{parts[0]} and {parts[1]} ago"

        # For very long gaps (>7 days), include the actual date for clarity
        if days > 7:
            try:
                if reference_time is None:
                    reference_time = datetime.now()
                last_date = reference_time - elapsed
                # Format as "Mon, Dec 30" for readability
                date_str = last_date.strftime("%a, %b %d").replace(" 0", " ")
                return f"{time_str} (on {date_str})"
            except Exception:
                # Fall back to just the time string if date calculation fails
                pass

        return time_str

    def update_last_interaction(self, interaction_type: str = "chat",
                                 agent: Optional[str] = None) -> bool:
        """Update the last interaction timestamp in TimeState.json.

        Records the current timestamp and interaction metadata to persist
        time awareness across sessions. Creates TimeState.json if it doesn't
        exist, or updates existing data preserving session information.

        Args:
            interaction_type: Type of interaction (e.g., 'chat', 'command', 'route')
            agent: Optional agent name that handled the interaction

        Returns:
            True if update succeeded, False on error
        """
        path = self.state_dir / "TimeState.json"
        now = datetime.now().astimezone()

        # Load existing data or create new structure
        data = {}
        if path.exists():
            try:
                content = path.read_text()
                data = json.loads(content)
            except (json.JSONDecodeError, OSError):
                # Corrupted or unreadable file, start fresh
                data = {}

        # Check if this is a new day to reset interaction count
        today = now.date().isoformat()
        last_date = None
        if "last_interaction" in data:
            try:
                last_ts = data["last_interaction"].get("timestamp")
                if last_ts:
                    last_date = datetime.fromisoformat(last_ts).date().isoformat()
            except (ValueError, TypeError):
                pass

        # Initialize or update session data
        if "session_started" not in data:
            data["session_started"] = now.isoformat()

        # Reset or increment interaction count
        if last_date != today:
            data["interaction_count_today"] = 1
        else:
            data["interaction_count_today"] = data.get("interaction_count_today", 0) + 1

        # Update last interaction
        data["last_interaction"] = {
            "timestamp": now.isoformat(),
            "type": interaction_type
        }
        if agent:
            data["last_interaction"]["agent"] = agent

        # Write atomically by writing to temp file first
        try:
            # Ensure state directory exists
            self.state_dir.mkdir(parents=True, exist_ok=True)

            # Write the file
            path.write_text(json.dumps(data, indent=2))
            return True
        except Exception:
            return False

    def is_morning(self) -> bool:
        """Check if current time is morning (5am-12pm).

        Returns:
            True if current hour is between 5 and 12
        """
        hour = datetime.now().hour
        return 5 <= hour < 12

    def get_quick_context(self) -> Dict:
        """Get quick context summary for hooks.

        Returns a dictionary with all available context that can be
        quickly assembled for hook output.

        Returns:
            Dictionary containing:
            - focus: Current primary focus
            - pending_commitments: Count of pending items
            - top3: List of top 3 priorities
            - energy: Current energy state (if logged)
            - week_theme: This week's theme
            - blockers: List of current blockers
            - is_morning: Whether it's morning
        """
        return {
            "focus": self.get_current_focus(),
            "pending_commitments": self.get_pending_commitments(),
            "top3": self.get_todays_top3(),
            "energy": self.get_energy_state(),
            "week_theme": self.get_week_theme(),
            "blockers": self.get_blockers(),
            "is_morning": self.is_morning()
        }

    def format_for_hook(self) -> str:
        """Format context for Claude hook additionalContext.

        Returns:
            Formatted string suitable for hook output
        """
        ctx = self.get_quick_context()
        parts = []

        if ctx["focus"]:
            parts.append(f"FOCUS: {ctx['focus']}")

        if ctx["top3"]:
            # Show first 2 items abbreviated
            items = ctx["top3"][:2]
            if len(items) == 1:
                parts.append(f"TOP: {items[0]}")
            else:
                parts.append(f"TOP: {items[0]} / {items[1]}...")

        if ctx["pending_commitments"] > 0:
            parts.append(f"PENDING: {ctx['pending_commitments']} commitments")

        if ctx["blockers"]:
            parts.append(f"BLOCKED: {ctx['blockers'][0]}")

        if ctx["energy"]:
            parts.append(f"ENERGY: {ctx['energy']}")

        if not parts:
            return ""

        return "[THANOS] " + " | ".join(parts)


def main():
    """Test the state reader."""
    import sys

    # Default to Thanos State directory
    if len(sys.argv) > 1:
        state_dir = Path(sys.argv[1])
    else:
        state_dir = Path(__file__).parent.parent / "State"

    reader = StateReader(state_dir)

    print("State Reader Test")
    print("=" * 40)
    print(f"State directory: {state_dir}")
    print(f"Directory exists: {state_dir.exists()}")
    print()

    ctx = reader.get_quick_context()
    for key, value in ctx.items():
        print(f"{key}: {value}")

    print()
    print("Hook output:")
    print(reader.format_for_hook())


if __name__ == "__main__":
    main()
