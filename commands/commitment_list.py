#!/usr/bin/env python3
"""
Commitment List Command - View commitments with filtering and sorting.

This command allows users to view commitments with flexible filtering and sorting options.
Supports multiple output formats including table, list, and JSON.

Usage:
    python commitment_list.py [options]
    python commitment_list.py --type habit --status pending
    python commitment_list.py --overdue
    python commitment_list.py --sort-by due --format table

Examples:
    # List all commitments
    python commitment_list.py

    # List only habits
    python commitment_list.py --type habit

    # List pending tasks
    python commitment_list.py --type task --status pending

    # Show overdue commitments
    python commitment_list.py --overdue

    # Show active streaks
    python commitment_list.py --streaks

    # Sort by priority
    python commitment_list.py --sort-by priority

    # Output as JSON
    python commitment_list.py --format json

    # Filter by domain and tags
    python commitment_list.py --domain work --tags urgent,review
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from Tools.commitment_tracker import (
        CommitmentTracker,
        CommitmentType,
        CommitmentStatus,
        RecurrencePattern,
        Commitment
    )
except ImportError:
    print("❌ Error: Could not import CommitmentTracker. Please ensure Tools/commitment_tracker.py exists.")
    sys.exit(1)


def format_due_date(commitment: Commitment) -> str:
    """
    Format due date with visual indicators.

    Args:
        commitment: Commitment to format

    Returns:
        Formatted due date string with emoji indicators
    """
    if not commitment.due_date:
        return "N/A"

    try:
        due_date = datetime.fromisoformat(commitment.due_date).date()
        today = datetime.now().date()
        days_diff = (due_date - today).days

        if days_diff < 0:
            return f"🚨 {due_date.isoformat()} (overdue)"
        elif days_diff == 0:
            return f"📅 {due_date.isoformat()} (today)"
        elif days_diff == 1:
            return f"⏰ {due_date.isoformat()} (tomorrow)"
        elif days_diff <= 3:
            return f"⚠️  {due_date.isoformat()} ({days_diff}d)"
        else:
            return due_date.isoformat()
    except (ValueError, TypeError):
        return commitment.due_date


def format_streak(commitment: Commitment) -> str:
    """
    Format streak information with visual indicators.

    Args:
        commitment: Commitment to format

    Returns:
        Formatted streak string
    """
    if not commitment.is_recurring():
        return "N/A"

    if commitment.streak_count == 0:
        return "0 days"

    streak_emoji = "🔥"
    if commitment.streak_count >= 100:
        streak_emoji = "💯"
    elif commitment.streak_count >= 30:
        streak_emoji = "🌟"
    elif commitment.streak_count >= 7:
        streak_emoji = "⭐"

    return f"{streak_emoji} {commitment.streak_count} days"


def format_priority(priority: int) -> str:
    """
    Format priority with visual indicators.

    Args:
        priority: Priority level (1-5)

    Returns:
        Formatted priority string
    """
    if priority == 1:
        return "⚡ P1"
    elif priority == 2:
        return "🔴 P2"
    elif priority == 3:
        return "🟡 P3"
    elif priority == 4:
        return "🟢 P4"
    else:
        return "⚪ P5"


def format_recurrence(commitment: Commitment) -> str:
    """
    Format recurrence pattern.

    Args:
        commitment: Commitment to format

    Returns:
        Formatted recurrence string
    """
    if not commitment.is_recurring():
        return "One-time"

    recurrence_map = {
        RecurrencePattern.DAILY: "🔄 Daily",
        RecurrencePattern.WEEKLY: "📅 Weekly",
        RecurrencePattern.WEEKDAYS: "💼 Weekdays",
        RecurrencePattern.WEEKENDS: "🌴 Weekends",
        RecurrencePattern.CUSTOM: "🔁 Custom",
    }

    return recurrence_map.get(commitment.recurrence_pattern, "Recurring")


def format_status(status: str) -> str:
    """
    Format status with visual indicators.

    Args:
        status: Status string

    Returns:
        Formatted status string
    """
    status_map = {
        CommitmentStatus.PENDING: "⏳ Pending",
        CommitmentStatus.IN_PROGRESS: "🔄 In Progress",
        CommitmentStatus.COMPLETED: "✅ Completed",
        CommitmentStatus.MISSED: "❌ Missed",
        CommitmentStatus.CANCELLED: "🚫 Cancelled",
    }

    return status_map.get(status, status)


def format_list_view(commitments: List[Commitment], show_details: bool = False) -> str:
    """
    Format commitments as a simple list.

    Args:
        commitments: List of commitments to display
        show_details: Whether to show detailed information

    Returns:
        Formatted string
    """
    if not commitments:
        return "No commitments found."

    lines = []
    for commitment in commitments:
        # Basic line
        checkbox = "✅" if commitment.status == CommitmentStatus.COMPLETED else "⬜"
        title = commitment.title

        # Priority indicator
        priority_str = ""
        if commitment.priority <= 2:
            priority_str = f" {format_priority(commitment.priority)}"

        # Due date
        due_str = ""
        if commitment.due_date and commitment.status not in [CommitmentStatus.COMPLETED, CommitmentStatus.CANCELLED]:
            due_str = f" [{format_due_date(commitment)}]"

        # Streak
        streak_str = ""
        if commitment.is_recurring() and commitment.streak_count > 0:
            streak_str = f" {format_streak(commitment)}"

        # Build line
        line = f"{checkbox} {title}{priority_str}{due_str}{streak_str}"
        lines.append(line)

        # Details
        if show_details:
            lines.append(f"   ID: {commitment.id}")
            lines.append(f"   Type: {commitment.type} | Domain: {commitment.domain} | Status: {format_status(commitment.status)}")
            if commitment.is_recurring():
                lines.append(f"   Recurrence: {format_recurrence(commitment)} | Completion: {commitment.completion_rate:.1f}%")
            if commitment.tags:
                lines.append(f"   Tags: {', '.join(commitment.tags)}")
            if commitment.notes:
                lines.append(f"   Notes: {commitment.notes}")
            lines.append("")  # Blank line between items

    return "\n".join(lines)


def format_table_view(commitments: List[Commitment]) -> str:
    """
    Format commitments as a table.

    Args:
        commitments: List of commitments to display

    Returns:
        Formatted table string
    """
    if not commitments:
        return "No commitments found."

    # Build table header
    lines = []
    lines.append("=" * 120)
    lines.append(f"{'ID':<12} {'Title':<30} {'Type':<8} {'Status':<15} {'Due Date':<25} {'Streak':<15} {'Priority':<10}")
    lines.append("=" * 120)

    # Build table rows
    for commitment in commitments:
        row_id = commitment.id[:10] + ".." if len(commitment.id) > 12 else commitment.id
        row_title = (commitment.title[:27] + "...") if len(commitment.title) > 30 else commitment.title
        row_type = commitment.type
        row_status = format_status(commitment.status)
        row_due = format_due_date(commitment)
        row_streak = format_streak(commitment)
        row_priority = format_priority(commitment.priority)

        lines.append(f"{row_id:<12} {row_title:<30} {row_type:<8} {row_status:<15} {row_due:<25} {row_streak:<15} {row_priority:<10}")

    lines.append("=" * 120)
    lines.append(f"Total: {len(commitments)} commitment(s)")

    return "\n".join(lines)


def format_json_view(commitments: List[Commitment]) -> str:
    """
    Format commitments as JSON.

    Args:
        commitments: List of commitments to display

    Returns:
        JSON string
    """
    data = {
        "count": len(commitments),
        "commitments": [c.to_dict() for c in commitments]
    }

    return json.dumps(data, indent=2)


def sort_commitments(
    commitments: List[Commitment],
    sort_by: str,
    reverse: bool = False
) -> List[Commitment]:
    """
    Sort commitments by specified criteria.

    Args:
        commitments: List of commitments to sort
        sort_by: Sort criteria (due, priority, streak, created, title)
        reverse: Whether to reverse sort order

    Returns:
        Sorted list of commitments
    """
    if sort_by == "due":
        # Sort by due date, with None values at the end
        def due_key(c):
            if c.due_date:
                try:
                    return datetime.fromisoformat(c.due_date)
                except (ValueError, TypeError):
                    return datetime.max
            return datetime.max

        return sorted(commitments, key=due_key, reverse=reverse)

    elif sort_by == "priority":
        return sorted(commitments, key=lambda c: c.priority, reverse=reverse)

    elif sort_by == "streak":
        return sorted(commitments, key=lambda c: c.streak_count, reverse=not reverse)  # Higher streaks first by default

    elif sort_by == "created":
        return sorted(commitments, key=lambda c: c.created_date, reverse=reverse)

    elif sort_by == "title":
        return sorted(commitments, key=lambda c: c.title.lower(), reverse=reverse)

    else:
        return commitments


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="List commitments with filtering and sorting options",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # List all commitments
  %(prog)s --type habit                       # List only habits
  %(prog)s --status pending                   # List pending commitments
  %(prog)s --overdue                          # Show overdue commitments
  %(prog)s --streaks                          # Show active streaks
  %(prog)s --domain work                      # Filter by domain
  %(prog)s --tags urgent,review               # Filter by tags
  %(prog)s --sort-by due                      # Sort by due date
  %(prog)s --sort-by priority --reverse       # Sort by priority (descending)
  %(prog)s --format table                     # Display as table
  %(prog)s --format json                      # Output as JSON
  %(prog)s --details                          # Show detailed information

Sort options:
  - due: Sort by due date (earliest first)
  - priority: Sort by priority (highest first)
  - streak: Sort by streak count (longest first)
  - created: Sort by creation date
  - title: Sort alphabetically by title
        """
    )

    # Filters
    parser.add_argument(
        "--type", "-t",
        type=str,
        choices=["habit", "goal", "task"],
        help="Filter by commitment type"
    )

    parser.add_argument(
        "--status", "-s",
        type=str,
        choices=["pending", "in_progress", "completed", "missed", "cancelled"],
        help="Filter by status"
    )

    parser.add_argument(
        "--domain", "-d",
        type=str,
        help="Filter by domain (work, personal, health, learning, general)"
    )

    parser.add_argument(
        "--tags",
        type=str,
        help="Filter by tags (comma-separated, must have all tags)"
    )

    parser.add_argument(
        "--priority", "-p",
        type=int,
        choices=[1, 2, 3, 4, 5],
        help="Filter by priority level"
    )

    # Special filters
    parser.add_argument(
        "--overdue",
        action="store_true",
        help="Show only overdue commitments"
    )

    parser.add_argument(
        "--due-today",
        action="store_true",
        help="Show only commitments due today"
    )

    parser.add_argument(
        "--streaks",
        action="store_true",
        help="Show only commitments with active streaks"
    )

    # Sorting
    parser.add_argument(
        "--sort-by",
        type=str,
        choices=["due", "priority", "streak", "created", "title"],
        default="created",
        help="Sort criteria (default: created)"
    )

    parser.add_argument(
        "--reverse", "-r",
        action="store_true",
        help="Reverse sort order"
    )

    # Output format
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["list", "table", "json"],
        default="list",
        help="Output format (default: list)"
    )

    parser.add_argument(
        "--details",
        action="store_true",
        help="Show detailed information (for list format)"
    )

    parser.add_argument(
        "--state-dir",
        type=str,
        help="Custom state directory path"
    )

    args = parser.parse_args()

    # Determine state directory
    if args.state_dir:
        state_dir = Path(args.state_dir)
    else:
        state_dir = Path(__file__).parent.parent / "State"

    # Initialize tracker
    try:
        tracker = CommitmentTracker(state_dir=state_dir)
    except Exception as e:
        print(f"❌ Error initializing CommitmentTracker: {e}")
        return 1

    # Get commitments with filters
    try:
        # Special filters
        if args.overdue:
            commitments = tracker.get_overdue()
        elif args.due_today:
            commitments = tracker.get_due_today()
        elif args.streaks:
            commitments = tracker.get_active_streaks()
        else:
            # Standard filters
            tags = [tag.strip() for tag in args.tags.split(",")] if args.tags else None

            commitments = tracker.get_all_commitments(
                commitment_type=args.type,
                status=args.status,
                domain=args.domain,
                tags=tags
            )

            # Additional priority filter
            if args.priority:
                commitments = [c for c in commitments if c.priority == args.priority]

        # Sort commitments
        commitments = sort_commitments(commitments, args.sort_by, args.reverse)

        # Format and display
        if args.format == "json":
            output = format_json_view(commitments)
        elif args.format == "table":
            output = format_table_view(commitments)
        else:  # list
            output = format_list_view(commitments, show_details=args.details)

        print(output)

        return 0

    except Exception as e:
        print(f"❌ Error listing commitments: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
