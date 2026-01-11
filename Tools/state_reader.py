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
from datetime import datetime
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

        Returns:
            datetime of last interaction, or None if not found/unavailable
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
        except Exception:
            return None

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
