#!/usr/bin/env python3
"""
Commitment Check Tool - Checks commitments and generates prompts.

This tool integrates with the commitment accountability system to check for
due/overdue commitments and generate natural language prompts for user
accountability. Can be invoked by hooks, scheduled tasks, or run manually.

Usage:
    # Check and show commitments needing attention
    python commitment_check.py

    # Show all active commitments
    python commitment_check.py --all

    # Show only overdue commitments
    python commitment_check.py --overdue

    # Dry-run mode (don't update reminder timestamps)
    python commitment_check.py --dry-run

    # Output as JSON for integration
    python commitment_check.py --json

    # Respect quiet hours
    python commitment_check.py --quiet-hours

As a module:
    from Tools.commitment_check import CommitmentChecker

    checker = CommitmentChecker()
    results = checker.check_commitments()
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Import our commitment modules
try:
    from commitment_tracker import CommitmentTracker, Commitment
    from commitment_scheduler import CommitmentScheduler, ScheduledPrompt
except ImportError:
    # Try relative import if run as module
    from .commitment_tracker import CommitmentTracker, Commitment
    from .commitment_scheduler import CommitmentScheduler, ScheduledPrompt


@dataclass
class CheckResult:
    """Result of a commitment check operation."""
    prompts: List[ScheduledPrompt]
    total_active: int
    overdue_count: int
    due_today_count: int
    habit_reminder_count: int
    in_quiet_hours: bool
    check_timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'prompts': [p.to_dict() for p in self.prompts],
            'total_active': self.total_active,
            'overdue_count': self.overdue_count,
            'due_today_count': self.due_today_count,
            'habit_reminder_count': self.habit_reminder_count,
            'in_quiet_hours': self.in_quiet_hours,
            'check_timestamp': self.check_timestamp
        }


class CommitmentChecker:
    """
    Checks commitments and generates natural language prompts.

    Integrates with CommitmentTracker and CommitmentScheduler to identify
    commitments needing attention and generate appropriate user prompts.
    """

    def __init__(
        self,
        state_dir: Optional[Path] = None,
        quiet_hours: Optional[Dict] = None
    ):
        """
        Initialize the commitment checker.

        Args:
            state_dir: Path to State directory (defaults to ../State)
            quiet_hours: Quiet hours configuration dict
        """
        if state_dir is None:
            state_dir = Path(__file__).parent.parent / "State"

        self.state_dir = Path(state_dir)
        self.tracker = CommitmentTracker(state_dir=state_dir)
        self.scheduler = CommitmentScheduler(state_dir=state_dir, quiet_hours=quiet_hours)

    def check_commitments(
        self,
        respect_quiet_hours: bool = False,
        dry_run: bool = False
    ) -> CheckResult:
        """
        Check commitments and return results.

        Args:
            respect_quiet_hours: Whether to skip checks during quiet hours
            dry_run: If True, don't update reminder timestamps

        Returns:
            CheckResult with prompts and statistics
        """
        now = datetime.now()

        # Get prompts from scheduler
        prompts = self.scheduler.get_commitments_needing_prompt(
            now=now,
            respect_quiet_hours=respect_quiet_hours
        )

        # Count by reason
        overdue_count = sum(1 for p in prompts if p.reason == 'overdue')
        due_today_count = sum(1 for p in prompts if p.reason == 'due_today')
        habit_reminder_count = sum(1 for p in prompts if p.reason == 'habit_reminder')

        # Get total active commitments
        all_commitments = self.tracker.get_all_commitments()
        active_commitments = [
            c for c in all_commitments
            if c.status not in ['completed', 'cancelled']
        ]

        # Mark prompts as sent (unless dry-run)
        if not dry_run:
            for prompt in prompts:
                self.scheduler.mark_prompted(prompt.commitment_id, now=now)

        result = CheckResult(
            prompts=prompts,
            total_active=len(active_commitments),
            overdue_count=overdue_count,
            due_today_count=due_today_count,
            habit_reminder_count=habit_reminder_count,
            in_quiet_hours=self.scheduler.is_quiet_hours(now),
            check_timestamp=now.isoformat()
        )

        return result

    def generate_prompt_text(
        self,
        prompt: ScheduledPrompt,
        commitment: Optional[Commitment] = None
    ) -> str:
        """
        Generate natural language prompt for a commitment.

        Args:
            prompt: ScheduledPrompt object
            commitment: Optional full Commitment object for additional context

        Returns:
            Natural language prompt string
        """
        if commitment is None:
            commitment = self.tracker.get_commitment(prompt.commitment_id)

        if commitment is None:
            return f"• {prompt.commitment_title} needs attention"

        # Build prompt based on reason
        if prompt.reason == 'overdue':
            days_msg = f"{prompt.days_overdue} day{'s' if prompt.days_overdue > 1 else ''}"
            emoji = "🚨" if prompt.days_overdue > 7 else "⚠️"
            text = f"{emoji} **{commitment.title}** is {days_msg} overdue"

        elif prompt.reason == 'due_today':
            emoji = "📅"
            text = f"{emoji} **{commitment.title}** is due today"

        elif prompt.reason == 'habit_reminder':
            emoji = "🔄"
            if prompt.streak_count and prompt.streak_count > 0:
                text = f"{emoji} **{commitment.title}** - Keep your {prompt.streak_count}-day streak going!"
            else:
                text = f"{emoji} Time for **{commitment.title}**"

        else:
            text = f"• **{commitment.title}** needs attention"

        # Add context if available
        if commitment.notes:
            # Truncate notes if too long
            notes = commitment.notes[:100]
            if len(commitment.notes) > 100:
                notes += "..."
            text += f"\n  💭 _{notes}_"

        return text

    def format_output(
        self,
        result: CheckResult,
        show_all: bool = False,
        show_overdue_only: bool = False
    ) -> str:
        """
        Format check results as human-readable text.

        Args:
            result: CheckResult to format
            show_all: Whether to show all details
            show_overdue_only: Whether to show only overdue items

        Returns:
            Formatted text output
        """
        lines = ["📋 Commitment Check", "=" * 60, ""]

        # Check if in quiet hours
        if result.in_quiet_hours:
            lines.append("🌙 Currently in quiet hours - prompts suppressed")
            lines.append("")

        # No prompts needed
        if not result.prompts:
            if result.total_active == 0:
                lines.append("✅ No active commitments")
            else:
                lines.append(f"✅ All caught up! ({result.total_active} active commitment{'s' if result.total_active != 1 else ''})")
            return "\n".join(lines)

        # Show prompts by category
        overdue_prompts = [p for p in result.prompts if p.reason == 'overdue']
        due_today_prompts = [p for p in result.prompts if p.reason == 'due_today']
        habit_prompts = [p for p in result.prompts if p.reason == 'habit_reminder']

        # Overdue (always show if present)
        if overdue_prompts:
            lines.append("🚨 OVERDUE:")
            lines.append("")
            for prompt in overdue_prompts:
                commitment = self.tracker.get_commitment(prompt.commitment_id)
                text = self.generate_prompt_text(prompt, commitment)
                lines.append(f"  {text}")
                lines.append("")

        # Due today (skip if showing only overdue)
        if not show_overdue_only and due_today_prompts:
            lines.append("📅 DUE TODAY:")
            lines.append("")
            for prompt in due_today_prompts:
                commitment = self.tracker.get_commitment(prompt.commitment_id)
                text = self.generate_prompt_text(prompt, commitment)
                lines.append(f"  {text}")
                lines.append("")

        # Habit reminders (skip if showing only overdue, show if --all)
        if not show_overdue_only and (show_all or not overdue_prompts) and habit_prompts:
            lines.append("🔄 HABIT REMINDERS:")
            lines.append("")
            for prompt in habit_prompts:
                commitment = self.tracker.get_commitment(prompt.commitment_id)
                text = self.generate_prompt_text(prompt, commitment)
                lines.append(f"  {text}")
                lines.append("")

        # Summary
        lines.append("─" * 60)
        lines.append(f"Total active commitments: {result.total_active}")
        if result.overdue_count > 0:
            lines.append(f"  🚨 Overdue: {result.overdue_count}")
        if result.due_today_count > 0:
            lines.append(f"  📅 Due today: {result.due_today_count}")
        if result.habit_reminder_count > 0:
            lines.append(f"  🔄 Habit reminders: {result.habit_reminder_count}")

        # Action prompt
        if result.overdue_count > 0:
            lines.append("")
            lines.append("⚠️  You have overdue commitments. Address these first!")
        elif result.due_today_count > 0:
            lines.append("")
            lines.append("💪 Focus on today's commitments to stay on track!")

        return "\n".join(lines)

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a quick summary of commitment status.

        Returns:
            Dictionary with summary statistics
        """
        schedule_summary = self.scheduler.get_schedule_summary()

        all_commitments = self.tracker.get_all_commitments()
        active_streaks = self.tracker.get_active_streaks()

        return {
            'total_commitments': len(all_commitments),
            'active_commitments': schedule_summary['total_active_commitments'],
            'prompts_needed': schedule_summary['prompts_needed_now'],
            'active_streaks': len(active_streaks),
            'longest_streak': max((c.streak_count for c in active_streaks), default=0),
            'in_quiet_hours': schedule_summary['in_quiet_hours'],
            'next_prompt_time': schedule_summary['next_prompt_time']
        }


def main():
    """Command-line interface for commitment checking."""
    parser = argparse.ArgumentParser(
        description="Check commitments and generate prompts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Check and show commitments needing attention
  %(prog)s --all              # Show all details including habit reminders
  %(prog)s --overdue          # Show only overdue commitments
  %(prog)s --dry-run          # Don't update reminder timestamps
  %(prog)s --json             # Output as JSON
  %(prog)s --quiet-hours      # Respect quiet hours configuration
  %(prog)s --summary          # Show quick summary only
        """
    )

    parser.add_argument(
        '-a', '--all',
        action='store_true',
        help='Show all prompts including habit reminders'
    )
    parser.add_argument(
        '-o', '--overdue',
        action='store_true',
        help='Show only overdue commitments'
    )
    parser.add_argument(
        '-d', '--dry-run',
        action='store_true',
        help="Don't update reminder timestamps (for testing)"
    )
    parser.add_argument(
        '-j', '--json',
        action='store_true',
        help='Output results as JSON'
    )
    parser.add_argument(
        '-q', '--quiet-hours',
        action='store_true',
        help='Respect quiet hours configuration'
    )
    parser.add_argument(
        '-s', '--summary',
        action='store_true',
        help='Show quick summary only'
    )
    parser.add_argument(
        '--state-dir',
        type=Path,
        help='Path to State directory (defaults to ../State)'
    )

    args = parser.parse_args()

    # Initialize checker
    try:
        checker = CommitmentChecker(state_dir=args.state_dir)
    except Exception as e:
        print(f"❌ Error initializing commitment checker: {e}", file=sys.stderr)
        sys.exit(1)

    # Handle summary mode
    if args.summary:
        summary = checker.get_summary()
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print("📊 Commitment Summary")
            print("=" * 60)
            print(f"Total commitments: {summary['total_commitments']}")
            print(f"Active commitments: {summary['active_commitments']}")
            print(f"Prompts needed now: {summary['prompts_needed']}")
            print(f"Active streaks: {summary['active_streaks']}")
            if summary['longest_streak'] > 0:
                print(f"Longest streak: {summary['longest_streak']} days")
            print(f"In quiet hours: {summary['in_quiet_hours']}")
            if summary['next_prompt_time']:
                print(f"Next prompt: {summary['next_prompt_time']}")
        return

    # Check commitments
    try:
        result = checker.check_commitments(
            respect_quiet_hours=args.quiet_hours,
            dry_run=args.dry_run
        )
    except Exception as e:
        print(f"❌ Error checking commitments: {e}", file=sys.stderr)
        sys.exit(1)

    # Output results
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        output = checker.format_output(
            result,
            show_all=args.all,
            show_overdue_only=args.overdue
        )
        print(output)

    # Exit code: 0 if no overdue, 1 if overdue items
    sys.exit(1 if result.overdue_count > 0 else 0)


if __name__ == "__main__":
    main()
