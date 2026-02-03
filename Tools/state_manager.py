#!/usr/bin/env python3
"""
State Manager for PAI v2.0

Manages and refreshes the current_state.md file with real data from:
- Oura MCP for readiness scores and health metrics
- WorkOS gateway (MCP-first) for tasks and productivity metrics

Usage:
    python tools/state_manager.py refresh          # Update current_state.md
    python tools/state_manager.py show             # Display current state
    python tools/state_manager.py --help           # Show help
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Try to import the adapters - fall back gracefully
try:
    from Tools.adapters.oura import OuraAdapter
    HAS_OURA_ADAPTER = True
except ImportError:
    HAS_OURA_ADAPTER = False

# Try direct database access for WorkOS as fallback
try:
    import sqlite3
    HAS_SQLITE = True
except ImportError:
    HAS_SQLITE = False


class StateManager:
    """Manages PAI state by aggregating data from various MCP sources."""

    def __init__(self, context_dir: Optional[Path] = None):
        """
        Initialize the state manager.

        Args:
            context_dir: Path to Context directory. Defaults to PROJECT_ROOT/Context
        """
        self.context_dir = context_dir or (PROJECT_ROOT / "Context")
        self.state_file = self.context_dir / "current_state.md"
        self.context_dir.mkdir(parents=True, exist_ok=True)

    async def get_oura_data(self) -> dict[str, Any]:
        """
        Fetch readiness and health data from Oura.

        Returns:
            Dict with readiness_score, energy_level, and recommendations
        """
        default_data = {
            "available": False,
            "readiness_score": None,
            "sleep_score": None,
            "energy_level": None,
            "recommendation": "Oura data unavailable",
        }

        if not HAS_OURA_ADAPTER:
            return default_data

        try:
            adapter = OuraAdapter()
            result = await adapter.call_tool("get_today_health", {})

            if not result.success:
                return default_data

            data = result.data
            summary = data.get("summary", {})
            readiness = data.get("readiness", {})

            readiness_score = summary.get("readiness_score") or readiness.get("score")
            sleep_score = summary.get("sleep_score")

            # Determine energy level based on readiness
            energy_level = "medium"
            recommendation = "Normal day - balance work and rest"

            if readiness_score:
                if readiness_score >= 85:
                    energy_level = "high"
                    recommendation = "Great day for challenging tasks"
                elif readiness_score >= 70:
                    energy_level = "medium"
                    recommendation = "Good for steady productivity"
                elif readiness_score >= 55:
                    energy_level = "low"
                    recommendation = "Take it easy - focus on lighter tasks"
                else:
                    energy_level = "low"
                    recommendation = "Recovery day - minimal cognitive load"

            await adapter.close()

            return {
                "available": True,
                "readiness_score": readiness_score,
                "sleep_score": sleep_score,
                "energy_level": energy_level,
                "recommendation": recommendation,
            }

        except Exception as e:
            print(f"[StateManager] Oura error: {e}", file=sys.stderr)
            return default_data

    async def get_workos_data(self) -> dict[str, Any]:
        """
        Fetch task and productivity data from WorkOS.
        Uses WorkOS gateway (MCP-first) with cache fallback.

        Returns:
            Dict with top_tasks, active_count, today_metrics
        """
        default_data = {
            "available": False,
            "top_tasks": [],
            "active_count": 0,
            "today_focus": None,
            "points_earned": 0,
            "target_points": 18,
        }

        try:
            from Tools.core.workos_gateway import WorkOSGateway

            gateway = WorkOSGateway(project_root=PROJECT_ROOT)
            snapshot = await gateway.get_state_snapshot()
            if snapshot.get("available"):
                return snapshot
            return default_data
        except Exception as e:
            print(f"[StateManager] WorkOS gateway error: {e}", file=sys.stderr)
            return default_data

    def format_state_markdown(
        self,
        oura_data: dict[str, Any],
        workos_data: dict[str, Any],
    ) -> str:
        """
        Format the current state as markdown.

        Args:
            oura_data: Health data from Oura
            workos_data: Task data from WorkOS

        Returns:
            Formatted markdown string
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Format readiness section
        if oura_data.get("available") and oura_data.get("readiness_score"):
            readiness_score = oura_data["readiness_score"]
            energy_level = oura_data.get("energy_level", "unknown")
            recommendation = oura_data.get("recommendation", "")
        else:
            readiness_score = "N/A"
            energy_level = "unknown"
            recommendation = "Connect Oura for health insights"

        # Format tasks section
        if workos_data.get("available") and workos_data.get("top_tasks"):
            tasks = workos_data["top_tasks"]
            task_lines = "\n".join(
                f"{i}. {task}" for i, task in enumerate(tasks, 1)
            )
            if len(tasks) < 3:
                # Pad to 3 items
                for i in range(len(tasks) + 1, 4):
                    task_lines += f"\n{i}. [No more active tasks]"
        else:
            task_lines = "1. [No active tasks]\n2. [No active tasks]\n3. [No active tasks]"

        # Format focus
        today_focus = workos_data.get("today_focus") or "[Set your focus for today]"

        # Format progress
        points = workos_data.get("points_earned", 0)
        target = workos_data.get("target_points", 18)
        progress_pct = int((points / target) * 100) if target > 0 else 0

        # Build the markdown
        content = f"""# Current State
*Auto-updated by state_manager.py*

## Last Updated
{timestamp}

## Readiness
- Score: {readiness_score}
- Mode: {energy_level}
- Recommendation: {recommendation}

## Pending Tasks (Top 3)
{task_lines}

## Active Alerts
- [None]

## Today's Focus
{today_focus}

## Progress
- Points: {points}/{target} ({progress_pct}%)
"""
        return content

    async def refresh(self) -> str:
        """
        Refresh the current state from all sources.

        Returns:
            Path to the updated state file
        """
        print("[StateManager] Fetching Oura data...")
        oura_data = await self.get_oura_data()

        print("[StateManager] Fetching WorkOS data...")
        workos_data = await self.get_workos_data()

        print("[StateManager] Formatting state...")
        content = self.format_state_markdown(oura_data, workos_data)

        print(f"[StateManager] Writing to {self.state_file}...")
        self.state_file.write_text(content)

        return str(self.state_file)

    def show(self) -> str:
        """
        Read and return the current state.

        Returns:
            Content of current_state.md or error message
        """
        if not self.state_file.exists():
            return "No state file found. Run 'refresh' first."
        return self.state_file.read_text()

    def get_state_dict(self) -> dict[str, Any]:
        """
        Parse current state into a dictionary.

        Returns:
            Parsed state data
        """
        if not self.state_file.exists():
            return {"error": "No state file found"}

        content = self.state_file.read_text()

        # Parse basic info from markdown
        state = {
            "last_updated": None,
            "readiness": {},
            "tasks": [],
            "focus": None,
        }

        lines = content.split("\n")
        current_section = None

        for line in lines:
            if line.startswith("## "):
                current_section = line[3:].strip().lower()
            elif current_section == "last updated" and line.strip():
                state["last_updated"] = line.strip()
            elif current_section == "readiness" and line.startswith("- "):
                key, _, value = line[2:].partition(":")
                state["readiness"][key.strip().lower()] = value.strip()
            elif current_section == "pending tasks" and line.strip() and line[0].isdigit():
                # Extract task from "1. Task name"
                parts = line.split(".", 1)
                if len(parts) == 2:
                    task = parts[1].strip()
                    if task and not task.startswith("["):
                        state["tasks"].append(task)
            elif current_section == "today's focus" and line.strip():
                state["focus"] = line.strip()

        return state


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PAI v2.0 State Manager - Manages current_state.md",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python tools/state_manager.py refresh     # Update state from MCP sources
    python tools/state_manager.py show        # Display current state
    python tools/state_manager.py --json      # Output state as JSON
        """,
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="show",
        choices=["refresh", "show", "json"],
        help="Command to run (default: show)",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of markdown",
    )

    parser.add_argument(
        "--context-dir",
        type=Path,
        default=None,
        help="Path to Context directory",
    )

    args = parser.parse_args()

    manager = StateManager(context_dir=args.context_dir)

    if args.command == "refresh":
        result = asyncio.run(manager.refresh())
        print(f"[StateManager] State refreshed: {result}")

    elif args.command == "show":
        if args.json:
            state = manager.get_state_dict()
            print(json.dumps(state, indent=2))
        else:
            print(manager.show())

    elif args.command == "json":
        state = manager.get_state_dict()
        print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
