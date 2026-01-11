#!/usr/bin/env python3
"""
AnalyticsHandler - Handles conversation analytics and pattern analysis

Analyzes session history to provide insights into usage patterns, agent preferences,
activity hours, and session characteristics. Provides data-driven insights to help
users understand their interaction patterns with Thanos.

Commands:
    /patterns    - Analyze conversation patterns and usage analytics
"""

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from Tools.command_handlers.base import BaseHandler, CommandResult, Colors


class AnalyticsHandler(BaseHandler):
    """
    Handler for analytics and pattern analysis commands.

    Provides functionality for:
    - Analyzing session history for patterns
    - Tracking agent usage statistics
    - Identifying peak activity hours
    - Categorizing session types (deep vs quick)
    - Displaying usage trends and insights
    """

    def __init__(
        self,
        orchestrator,
        session_manager,
        context_manager,
        state_reader,
        thanos_dir,
        current_agent_getter=None,
    ):
        """
        Initialize AnalyticsHandler with dependencies.

        Args:
            orchestrator: ThanosOrchestrator for agent info
            session_manager: SessionManager for session operations
            context_manager: ContextManager for context operations
            state_reader: StateReader for state operations
            thanos_dir: Path to Thanos root directory
            current_agent_getter: Optional callable to get current agent name
        """
        super().__init__(
            orchestrator,
            session_manager,
            context_manager,
            state_reader,
            thanos_dir,
            current_agent_getter,
        )

    def handle_patterns(self, args: str) -> CommandResult:
        """
        Handle /patterns command - Analyze conversation patterns from session history.

        Analyzes all saved session files to extract and display:
        - Session overview (total sessions, total messages, average messages/session)
        - Agent usage distribution (which agents are used most frequently)
        - Peak activity hours (when the user is most active)
        - Session types (deep sessions vs quick sessions)

        Visualization includes:
        - Horizontal bar charts for agent usage percentages
        - Categorized session statistics
        - Human-readable peak hours (12-hour format)

        Args:
            args: Optional arguments (currently unused)

        Returns:
            CommandResult with action and success status
        """
        history_dir = self.thanos_dir / "History" / "Sessions"
        if not history_dir.exists():
            print(f"{Colors.DIM}No session history to analyze.{Colors.RESET}")
            return CommandResult()

        # Collect session data
        sessions_data = []
        json_files = list(history_dir.glob("*.json"))

        if not json_files:
            print(f"{Colors.DIM}No saved sessions found.{Colors.RESET}")
            return CommandResult()

        for json_file in json_files:
            try:
                data = json.loads(json_file.read_text())
                sessions_data.append(data)
            except (json.JSONDecodeError, KeyError):
                continue

        if not sessions_data:
            print(f"{Colors.DIM}No valid session data to analyze.{Colors.RESET}")
            return CommandResult()

        # Analyze patterns
        agent_usage = Counter()
        hour_usage = Counter()
        session_lengths = []
        total_messages = 0

        for session in sessions_data:
            # Agent usage
            agent = session.get("agent", "unknown")
            agent_usage[agent] += 1

            # Time of day
            started = session.get("started_at", "")
            if started:
                try:
                    dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                    hour_usage[dt.hour] += 1
                except ValueError:
                    pass

            # Session length (messages)
            msg_count = len(session.get("history", []))
            if msg_count > 0:
                session_lengths.append(msg_count)
                total_messages += msg_count

        # Calculate statistics
        total_sessions = len(sessions_data)
        avg_messages = total_messages / total_sessions if total_sessions > 0 else 0

        # Find peak hours
        peak_hours = hour_usage.most_common(3)
        peak_hour_strs = []
        for hour, _ in peak_hours:
            if hour < 12:
                peak_hour_strs.append(f"{hour}am" if hour > 0 else "12am")
            else:
                h = hour - 12 if hour > 12 else 12
                peak_hour_strs.append(f"{h}pm")

        # Display patterns
        print(f"\n{Colors.CYAN}Conversation Patterns:{Colors.RESET}\n")
        print(f"  {Colors.BOLD}Session Overview:{Colors.RESET}")
        print(f"    Total sessions: {total_sessions}")
        print(f"    Total messages: {total_messages}")
        print(f"    Avg messages/session: {avg_messages:.1f}")

        print(f"\n  {Colors.BOLD}Agent Usage:{Colors.RESET}")
        for agent, count in agent_usage.most_common():
            pct = (count / total_sessions) * 100
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            print(f"    {agent:12} {bar} {pct:.0f}%")

        if peak_hour_strs:
            print(f"\n  {Colors.BOLD}Peak Activity Hours:{Colors.RESET}")
            print(f"    Most active: {', '.join(peak_hour_strs)}")

        # Productivity insight based on session sizes
        if session_lengths:
            long_sessions = sum(1 for s in session_lengths if s > 10)
            short_sessions = sum(1 for s in session_lengths if s <= 5)
            print(f"\n  {Colors.BOLD}Session Types:{Colors.RESET}")
            print(f"    Deep sessions (>10 msgs): {long_sessions}")
            print(f"    Quick sessions (≤5 msgs): {short_sessions}")

        print(f"\n{Colors.DIM}Based on {total_sessions} saved sessions{Colors.RESET}\n")
        return CommandResult()
