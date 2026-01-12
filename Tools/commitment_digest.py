#!/usr/bin/env python3
"""
Commitment Digest - Generates a daily morning digest of commitments.

This tool creates a comprehensive morning summary of commitments for the day,
including what's due, current streaks, overdue items, and encouraging messages
to help users start their day with clarity and motivation.

Usage:
    # Generate today's digest
    python commitment_digest.py

    # Output as JSON for integration
    python commitment_digest.py --json

    # Show full details
    python commitment_digest.py --detailed

As a module:
    from Tools.commitment_digest import CommitmentDigest

    digest = CommitmentDigest()
    summary = digest.generate_digest()
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, date
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
class DigestData:
    """Data structure for the daily digest."""
    date: str
    day_of_week: str
    overdue_items: List[Dict[str, Any]]
    due_today_items: List[Dict[str, Any]]
    habits_for_today: List[Dict[str, Any]]
    active_streaks: List[Dict[str, Any]]
    total_active_commitments: int
    completion_trend: str  # 'improving', 'stable', 'declining'
    encouragement_message: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class CommitmentDigest:
    """
    Generates a daily morning digest of commitments.

    Provides a comprehensive overview of the day ahead, including overdue
    items, today's commitments, active streaks, and motivational messaging.
    """

    # Encouragement messages based on different scenarios
    MESSAGES = {
        'all_clear': [
            "✨ You're all caught up! Great work staying on top of your commitments.",
            "🎯 No overdue items - you're crushing it! Let's keep the momentum going.",
            "💪 Starting fresh with a clean slate. You've got this!",
        ],
        'some_overdue': [
            "⚡ You've got some items needing attention. Tackle them first to clear your mind.",
            "🔥 A few things backed up - that's okay! Let's get them sorted today.",
            "💫 Time to catch up on a few things. One step at a time!",
        ],
        'very_overdue': [
            "🚨 Several items need attention, but don't get overwhelmed. Pick one to start.",
            "💪 Today's the day to tackle those backed-up items. Start with just one.",
            "🎯 It's normal to fall behind sometimes. Let's make progress today.",
        ],
        'strong_streaks': [
            "🔥 Your streaks are on fire! Keep that momentum going.",
            "⭐ You're building amazing habits. Stay consistent!",
            "💎 Those streaks represent real progress. Protect them!",
        ],
        'new_week': [
            "☀️ New week, new opportunities! Let's make it count.",
            "🎯 Fresh start to the week. Set the tone with today's commitments.",
            "💫 Monday energy! Use it to build momentum for the week.",
        ],
        'weekend': [
            "🌟 Weekend vibes! Don't forget your habits that keep you feeling great.",
            "😌 Take it easy, but stay consistent with what matters.",
            "🎨 Weekend is for recharging. Keep up with habits that energize you.",
        ]
    }

    def __init__(
        self,
        state_dir: Optional[Path] = None,
        quiet_hours: Optional[Dict] = None
    ):
        """
        Initialize the commitment digest generator.

        Args:
            state_dir: Path to State directory (defaults to ../State)
            quiet_hours: Quiet hours configuration dict
        """
        if state_dir is None:
            state_dir = Path(__file__).parent.parent / "State"

        self.state_dir = Path(state_dir)
        self.tracker = CommitmentTracker(state_dir=state_dir)
        self.scheduler = CommitmentScheduler(state_dir=state_dir, quiet_hours=quiet_hours)

    def generate_digest(self, for_date: Optional[date] = None) -> DigestData:
        """
        Generate the daily digest for a given date.

        Args:
            for_date: Date to generate digest for (defaults to today)

        Returns:
            DigestData with all digest information
        """
        if for_date is None:
            for_date = date.today()

        now = datetime.now()

        # Get all active commitments
        all_commitments = self.tracker.get_all_commitments()
        active_commitments = [
            c for c in all_commitments
            if c.status not in ['completed', 'cancelled']
        ]

        # Get overdue items
        overdue_items = self._get_overdue_items(active_commitments, for_date)

        # Get items due today
        due_today_items = self._get_due_today_items(active_commitments, for_date)

        # Get habits for today
        habits_today = self._get_habits_for_today(active_commitments, for_date)

        # Get active streaks
        active_streaks = self._get_active_streaks(all_commitments)

        # Calculate completion trend
        completion_trend = self._calculate_trend(all_commitments)

        # Generate encouragement message
        encouragement = self._generate_encouragement(
            overdue_count=len(overdue_items),
            streak_count=len(active_streaks),
            day_of_week=for_date.strftime('%A')
        )

        digest = DigestData(
            date=for_date.isoformat(),
            day_of_week=for_date.strftime('%A'),
            overdue_items=overdue_items,
            due_today_items=due_today_items,
            habits_for_today=habits_today,
            active_streaks=active_streaks,
            total_active_commitments=len(active_commitments),
            completion_trend=completion_trend,
            encouragement_message=encouragement
        )

        return digest

    def _get_overdue_items(
        self,
        commitments: List[Commitment],
        ref_date: date
    ) -> List[Dict[str, Any]]:
        """Get overdue commitments."""
        overdue = []

        for c in commitments:
            if c.due_date:
                try:
                    due_date = datetime.fromisoformat(c.due_date).date()
                    if due_date < ref_date:
                        days_overdue = (ref_date - due_date).days
                        overdue.append({
                            'id': c.id,
                            'title': c.title,
                            'type': c.type,
                            'due_date': c.due_date,
                            'days_overdue': days_overdue,
                            'priority': c.priority,
                            'notes': c.notes
                        })
                except (ValueError, TypeError):
                    pass

        # Sort by days overdue (most overdue first)
        overdue.sort(key=lambda x: x['days_overdue'], reverse=True)

        return overdue

    def _get_due_today_items(
        self,
        commitments: List[Commitment],
        ref_date: date
    ) -> List[Dict[str, Any]]:
        """Get commitments due today."""
        due_today = []

        for c in commitments:
            if c.due_date:
                try:
                    due_date = datetime.fromisoformat(c.due_date).date()
                    if due_date == ref_date:
                        due_today.append({
                            'id': c.id,
                            'title': c.title,
                            'type': c.type,
                            'due_date': c.due_date,
                            'priority': c.priority,
                            'notes': c.notes
                        })
                except (ValueError, TypeError):
                    pass

        # Sort by priority
        due_today.sort(key=lambda x: x.get('priority', 3))

        return due_today

    def _get_habits_for_today(
        self,
        commitments: List[Commitment],
        ref_date: date
    ) -> List[Dict[str, Any]]:
        """Get habits that should be done today."""
        habits = []

        for c in commitments:
            # Only include recurring commitments (habits)
            if c.recurrence_pattern == 'none':
                continue

            # Check if already completed today
            completed_today = any(
                datetime.fromisoformat(record.timestamp).date() == ref_date
                and record.status == 'completed'
                for record in c.completion_history
                if record.timestamp
            )

            if not completed_today:
                habits.append({
                    'id': c.id,
                    'title': c.title,
                    'type': c.type,
                    'recurrence_pattern': c.recurrence_pattern,
                    'streak_count': c.streak_count,
                    'completion_rate': c.completion_rate,
                    'notes': c.notes
                })

        # Sort by streak count (highest first - don't break the streak!)
        habits.sort(key=lambda x: x.get('streak_count', 0), reverse=True)

        return habits

    def _get_active_streaks(
        self,
        commitments: List[Commitment]
    ) -> List[Dict[str, Any]]:
        """Get commitments with active streaks."""
        streaks = []

        for c in commitments:
            if c.streak_count > 0:
                streaks.append({
                    'id': c.id,
                    'title': c.title,
                    'streak_count': c.streak_count,
                    'longest_streak': c.longest_streak,
                    'completion_rate': c.completion_rate
                })

        # Sort by current streak (highest first)
        streaks.sort(key=lambda x: x['streak_count'], reverse=True)

        return streaks

    def _calculate_trend(self, commitments: List[Commitment]) -> str:
        """
        Calculate the overall completion trend.

        Analyzes recent completion rates to determine if improving/stable/declining.
        """
        # Simple heuristic based on average completion rate
        rates = [c.completion_rate for c in commitments if c.recurrence_pattern != 'none']

        if not rates:
            return 'stable'

        avg_rate = sum(rates) / len(rates)

        if avg_rate >= 80:
            return 'improving'
        elif avg_rate >= 60:
            return 'stable'
        else:
            return 'declining'

    def _generate_encouragement(
        self,
        overdue_count: int,
        streak_count: int,
        day_of_week: str
    ) -> str:
        """Generate an encouraging message based on current status."""
        import random

        messages = []

        # Choose primary message based on overdue status
        if overdue_count == 0:
            messages.extend(self.MESSAGES['all_clear'])
        elif overdue_count <= 2:
            messages.extend(self.MESSAGES['some_overdue'])
        else:
            messages.extend(self.MESSAGES['very_overdue'])

        # Add streak encouragement if applicable
        if streak_count >= 3:
            messages.extend(self.MESSAGES['strong_streaks'])

        # Add day-specific encouragement
        if day_of_week == 'Monday':
            messages.extend(self.MESSAGES['new_week'])
        elif day_of_week in ['Saturday', 'Sunday']:
            messages.extend(self.MESSAGES['weekend'])

        return random.choice(messages)

    def format_digest(
        self,
        digest: DigestData,
        detailed: bool = False
    ) -> str:
        """
        Format the digest as human-readable text.

        Args:
            digest: DigestData to format
            detailed: Whether to show full details

        Returns:
            Formatted text output
        """
        lines = []

        # Header
        lines.append("=" * 70)
        lines.append(f"🌅 GOOD MORNING! Your Commitment Digest for {digest.day_of_week}")
        lines.append(f"📅 {digest.date}")
        lines.append("=" * 70)
        lines.append("")

        # Encouragement message
        lines.append(f"💭 {digest.encouragement_message}")
        lines.append("")

        # Overview
        lines.append("📊 OVERVIEW")
        lines.append("─" * 70)
        lines.append(f"  Active commitments: {digest.total_active_commitments}")
        lines.append(f"  Overdue items: {len(digest.overdue_items)}")
        lines.append(f"  Due today: {len(digest.due_today_items)}")
        lines.append(f"  Habits for today: {len(digest.habits_for_today)}")
        lines.append(f"  Active streaks: {len(digest.active_streaks)}")
        lines.append(f"  Trend: {digest.completion_trend.upper()}")
        lines.append("")

        # Overdue items (always show if present)
        if digest.overdue_items:
            lines.append("🚨 OVERDUE - NEEDS ATTENTION")
            lines.append("─" * 70)
            for item in digest.overdue_items[:5]:  # Show top 5
                emoji = "🔴" if item['days_overdue'] > 7 else "⚠️"
                lines.append(f"  {emoji} {item['title']}")
                lines.append(f"     {item['days_overdue']} day{'s' if item['days_overdue'] > 1 else ''} overdue")
                if detailed and item.get('notes'):
                    lines.append(f"     💭 {item['notes'][:80]}")
                lines.append("")

            if len(digest.overdue_items) > 5:
                lines.append(f"  ... and {len(digest.overdue_items) - 5} more overdue items")
                lines.append("")

        # Due today
        if digest.due_today_items:
            lines.append("📅 DUE TODAY")
            lines.append("─" * 70)
            for item in digest.due_today_items:
                priority_emoji = "🔥" if item.get('priority', 3) <= 2 else "📌"
                lines.append(f"  {priority_emoji} {item['title']}")
                if detailed and item.get('notes'):
                    lines.append(f"     💭 {item['notes'][:80]}")
                lines.append("")

        # Habits for today
        if digest.habits_for_today:
            lines.append("🔄 TODAY'S HABITS")
            lines.append("─" * 70)
            for item in digest.habits_for_today[:8]:  # Show top 8
                if item.get('streak_count', 0) > 0:
                    streak_emoji = "🔥" if item['streak_count'] >= 7 else "✨"
                    lines.append(f"  {streak_emoji} {item['title']} - {item['streak_count']}-day streak!")
                else:
                    lines.append(f"  ⭕ {item['title']}")

                if detailed:
                    rate = item.get('completion_rate', 0)
                    lines.append(f"     Completion rate: {rate:.0f}%")
                lines.append("")

            if len(digest.habits_for_today) > 8:
                lines.append(f"  ... and {len(digest.habits_for_today) - 8} more habits")
                lines.append("")

        # Active streaks highlight
        if digest.active_streaks:
            lines.append("🔥 ACTIVE STREAKS - KEEP THEM ALIVE!")
            lines.append("─" * 70)
            for item in digest.active_streaks[:5]:  # Show top 5
                streak = item['streak_count']
                longest = item['longest_streak']

                # Special emoji for different milestones
                if streak >= 30:
                    emoji = "💎"
                elif streak >= 14:
                    emoji = "⭐"
                elif streak >= 7:
                    emoji = "🔥"
                else:
                    emoji = "✨"

                lines.append(f"  {emoji} {item['title']}: {streak} days")

                if detailed:
                    if streak == longest:
                        lines.append(f"     🎯 Personal record!")
                    else:
                        lines.append(f"     Best: {longest} days")
                    lines.append(f"     Rate: {item['completion_rate']:.0f}%")
                lines.append("")

        # Footer
        lines.append("─" * 70)

        # Action items
        if digest.overdue_items:
            lines.append("⚡ ACTION: Focus on overdue items first to clear your mind")
        elif digest.due_today_items:
            lines.append("🎯 ACTION: Tackle today's commitments to stay on track")
        else:
            lines.append("✅ You're all caught up! Maintain your habits and you're golden")

        lines.append("")
        lines.append("💪 You've got this! One step at a time.")
        lines.append("=" * 70)

        return "\n".join(lines)


def main():
    """Command-line interface for commitment digest."""
    parser = argparse.ArgumentParser(
        description="Generate daily commitment digest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Generate today's digest
  %(prog)s --detailed         # Show full details
  %(prog)s --json             # Output as JSON
        """
    )

    parser.add_argument(
        '-d', '--detailed',
        action='store_true',
        help='Show detailed information'
    )
    parser.add_argument(
        '-j', '--json',
        action='store_true',
        help='Output results as JSON'
    )
    parser.add_argument(
        '--state-dir',
        type=Path,
        help='Path to State directory (defaults to ../State)'
    )

    args = parser.parse_args()

    # Initialize digest generator
    try:
        digest_gen = CommitmentDigest(state_dir=args.state_dir)
    except Exception as e:
        print(f"❌ Error initializing commitment digest: {e}", file=sys.stderr)
        sys.exit(1)

    # Generate digest
    try:
        digest = digest_gen.generate_digest()
    except Exception as e:
        print(f"❌ Error generating digest: {e}", file=sys.stderr)
        sys.exit(1)

    # Output results
    if args.json:
        print(json.dumps(digest.to_dict(), indent=2))
    else:
        output = digest_gen.format_digest(digest, detailed=args.detailed)
        print(output)


if __name__ == "__main__":
    main()
