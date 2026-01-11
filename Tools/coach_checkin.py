#!/usr/bin/env python3
"""
Coach Check-In Tool - Enables Coach to conduct accountability check-ins.

This tool provides Coach with comprehensive access to commitment history and
patterns for empathetic, data-driven accountability conversations. It formats
commitment data specifically for Coach persona interactions.

Usage:
    # Check-in on a specific commitment
    python coach_checkin.py <commitment_id>

    # Check-in on all commitments needing Coach attention
    python coach_checkin.py --all

    # List commitments needing Coach intervention
    python coach_checkin.py --list

    # Output as JSON for integration
    python coach_checkin.py <commitment_id> --json

As a module:
    from Tools.coach_checkin import CoachCheckin

    checkin = CoachCheckin()
    context = checkin.get_checkin_context(commitment_id)
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# Import our commitment modules
try:
    from commitment_tracker import CommitmentTracker, Commitment
except ImportError:
    # Try relative import if run as module
    from .commitment_tracker import CommitmentTracker, Commitment


@dataclass
class CoachCheckinContext:
    """
    Comprehensive context for Coach accountability check-in.

    Contains all the information Coach needs for empathetic,
    data-driven accountability conversations.
    """
    commitment_id: str
    commitment_title: str
    commitment_type: str
    recurrence_pattern: str

    # Current status
    status: str
    consecutive_misses: int
    should_trigger_coach: bool
    escalation_level: str
    escalation_reason: str

    # Pattern analysis
    total_misses: int
    total_completions: int
    miss_rate: float
    miss_by_weekday: Dict[str, int]
    completion_by_weekday: Dict[str, int]

    # Streak information
    current_streak: int
    longest_streak: int
    completion_rate: float

    # Context
    domain: str
    priority: int
    notes: str
    tags: List[str]
    created_date: str
    due_date: Optional[str]

    # Coach suggestion
    coach_suggestion: str
    suggested_approach: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class CoachCheckin:
    """
    Manages Coach accountability check-ins with commitment data access.

    Provides Coach persona with comprehensive commitment history, pattern
    analysis, and contextual information for accountability conversations.
    """

    # Coach approach messages based on escalation level
    COACH_APPROACHES = {
        'celebrate_or_encourage': {
            'tone': 'Celebratory and encouraging',
            'focus': 'Acknowledge success, ask what made it possible',
            'example': "You did it! What made you show up today?",
        },
        'gentle_curiosity': {
            'tone': 'Warm and curious, no pressure',
            'focus': 'Understand what got in the way, offer support',
            'example': "I noticed [commitment] didn't happen. What got in the way?",
        },
        'pattern_acknowledgment': {
            'tone': 'Direct but kind, pattern-focused',
            'focus': 'Point out emerging pattern, check if commitment still fits',
            'example': "This is the second time this week. What's up? Is this still serving you?",
        },
        'direct_confrontation': {
            'tone': 'Honest and direct, reality check',
            'focus': 'Call out the pattern clearly, collaborative problem-solving',
            'example': "Real talk: [commitment] hasn't happened in a week. Let's be honest about the blocker.",
        },
        'commitment_redesign': {
            'tone': 'Supportive but firm, solution-oriented',
            'focus': 'Challenge the commitment itself, offer to redesign or let go',
            'example': "This commitment doesn't fit your life right now. Let's redesign or release it.",
        },
        'values_alignment_check': {
            'tone': 'Deep and reflective, values-focused',
            'focus': 'Connect to deeper values, explore what\'s really important',
            'example': "Let's talk about why this matters to you—or if it still does.",
        },
    }

    def __init__(self, state_dir: Optional[Path] = None):
        """
        Initialize the Coach check-in tool.

        Args:
            state_dir: Path to State directory (defaults to ../State)
        """
        if state_dir is None:
            state_dir = Path(__file__).parent.parent / "State"

        self.state_dir = Path(state_dir)
        self.tracker = CommitmentTracker(state_dir=state_dir)

    def get_checkin_context(self, commitment_id: str) -> Optional[CoachCheckinContext]:
        """
        Get comprehensive check-in context for a specific commitment.

        Args:
            commitment_id: Commitment ID

        Returns:
            CoachCheckinContext if commitment found, None otherwise
        """
        # Get comprehensive context from tracker
        coach_data = self.tracker.get_coach_context(commitment_id)

        if 'error' in coach_data:
            return None

        # Get the commitment object for additional details
        commitment = self.tracker.get_commitment(commitment_id)
        if not commitment:
            return None

        # Extract and structure data for Coach
        context = CoachCheckinContext(
            commitment_id=commitment.id,
            commitment_title=commitment.title,
            commitment_type=commitment.type,
            recurrence_pattern=commitment.recurrence_pattern,

            # Current status
            status=commitment.status,
            consecutive_misses=coach_data['consecutive_misses'],
            should_trigger_coach=coach_data['should_trigger_coach'],
            escalation_level=coach_data['escalation_level'],
            escalation_reason=coach_data['escalation_reason'],

            # Pattern analysis
            total_misses=coach_data['pattern_analysis']['total_misses'],
            total_completions=coach_data['pattern_analysis']['total_completions'],
            miss_rate=coach_data['pattern_analysis']['miss_rate'],
            miss_by_weekday=coach_data['pattern_analysis']['miss_by_weekday'],
            completion_by_weekday=coach_data['pattern_analysis']['completion_by_weekday'],

            # Streak information
            current_streak=coach_data['streak_history']['current_streak'],
            longest_streak=coach_data['streak_history']['longest_streak'],
            completion_rate=coach_data['streak_history']['completion_rate'],

            # Context
            domain=commitment.domain,
            priority=commitment.priority,
            notes=commitment.notes,
            tags=commitment.tags,
            created_date=commitment.created_date,
            due_date=commitment.due_date,

            # Coach suggestion
            coach_suggestion=coach_data['coach_suggestion'],
            suggested_approach=self._get_approach_description(coach_data['coach_suggestion'])
        )

        return context

    def _get_approach_description(self, suggestion: str) -> str:
        """
        Get the approach description for a coach suggestion.

        Args:
            suggestion: Coach suggestion key

        Returns:
            Formatted approach description
        """
        approach = self.COACH_APPROACHES.get(suggestion, {})

        if not approach:
            return "Standard check-in"

        return (
            f"Tone: {approach['tone']}\n"
            f"Focus: {approach['focus']}\n"
            f"Example: \"{approach['example']}\""
        )

    def get_commitments_needing_coach(self) -> List[CoachCheckinContext]:
        """
        Get all commitments that need Coach intervention.

        Returns:
            List of CoachCheckinContext for commitments needing attention
        """
        all_commitments = self.tracker.get_all_commitments()
        needing_coach = []

        for commitment in all_commitments:
            # Skip completed and cancelled
            if commitment.status in ['completed', 'cancelled']:
                continue

            # Check if Coach should be triggered
            trigger_info = self.tracker.should_trigger_coach(commitment.id)

            if trigger_info['should_trigger']:
                context = self.get_checkin_context(commitment.id)
                if context:
                    needing_coach.append(context)

        # Sort by escalation urgency and consecutive misses
        escalation_order = {
            'chronic_pattern': 0,
            'third_miss': 1,
            'second_miss': 2,
            'first_miss': 3,
            'none': 4
        }

        needing_coach.sort(
            key=lambda x: (
                escalation_order.get(x.escalation_level, 4),
                -x.consecutive_misses
            )
        )

        return needing_coach

    def format_checkin_brief(self, context: CoachCheckinContext) -> str:
        """
        Format a brief check-in summary for Coach.

        Args:
            context: CoachCheckinContext

        Returns:
            Brief formatted summary
        """
        lines = []

        # Header
        emoji = self._get_status_emoji(context)
        lines.append(f"{emoji} {context.commitment_title}")
        lines.append("─" * 60)

        # Status
        if context.consecutive_misses > 0:
            lines.append(f"Status: {context.consecutive_misses} consecutive miss{'es' if context.consecutive_misses > 1 else ''}")
            lines.append(f"Escalation: {context.escalation_level.replace('_', ' ').title()}")
        else:
            lines.append(f"Status: Active (Streak: {context.current_streak} days)")

        # Key metrics
        lines.append(f"Type: {context.commitment_type.title()} | Domain: {context.domain.title()}")

        if context.recurrence_pattern != 'none':
            lines.append(f"Completion Rate: {context.completion_rate:.0f}%")
            if context.longest_streak > 0:
                lines.append(f"Best Streak: {context.longest_streak} days")

        # Pattern insights
        if context.total_misses > 0 or context.total_completions > 0:
            lines.append("")
            lines.append("Pattern Insights:")
            lines.append(f"  Completions: {context.total_completions} | Misses: {context.total_misses}")

            if context.miss_by_weekday:
                problem_days = sorted(
                    context.miss_by_weekday.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:2]
                days_str = ", ".join(f"{day} ({count})" for day, count in problem_days)
                lines.append(f"  Struggle days: {days_str}")

        # Notes
        if context.notes:
            lines.append("")
            lines.append(f"Notes: {context.notes[:100]}")

        return "\n".join(lines)

    def format_checkin_detailed(self, context: CoachCheckinContext) -> str:
        """
        Format a detailed check-in report for Coach.

        Args:
            context: CoachCheckinContext

        Returns:
            Detailed formatted report
        """
        lines = []

        # Header
        lines.append("=" * 70)
        emoji = self._get_status_emoji(context)
        lines.append(f"{emoji} COACH CHECK-IN: {context.commitment_title}")
        lines.append("=" * 70)
        lines.append("")

        # Current Status Section
        lines.append("📊 CURRENT STATUS")
        lines.append("─" * 70)
        lines.append(f"Type: {context.commitment_type.title()}")
        lines.append(f"Recurrence: {context.recurrence_pattern.replace('_', ' ').title()}")
        lines.append(f"Status: {context.status.title()}")
        lines.append(f"Domain: {context.domain.title()} | Priority: {context.priority}/5")

        if context.due_date:
            lines.append(f"Due Date: {context.due_date}")

        if context.tags:
            lines.append(f"Tags: {', '.join(context.tags)}")
        lines.append("")

        # Miss Pattern Section
        if context.consecutive_misses > 0:
            lines.append("⚠️  MISS PATTERN")
            lines.append("─" * 70)
            lines.append(f"Consecutive misses: {context.consecutive_misses}")
            lines.append(f"Escalation level: {context.escalation_level.replace('_', ' ').title()}")
            lines.append(f"Reason: {context.escalation_reason}")
            lines.append("")

        # Streak Section
        if context.recurrence_pattern != 'none':
            lines.append("🔥 STREAK & PERFORMANCE")
            lines.append("─" * 70)
            lines.append(f"Current streak: {context.current_streak} days")
            lines.append(f"Longest streak: {context.longest_streak} days")
            lines.append(f"Completion rate: {context.completion_rate:.1f}%")
            lines.append(f"Total completions: {context.total_completions}")
            lines.append(f"Total misses: {context.total_misses}")

            if context.miss_rate > 0:
                lines.append(f"Miss rate: {context.miss_rate:.1f}%")
            lines.append("")

        # Pattern Analysis Section
        if context.miss_by_weekday or context.completion_by_weekday:
            lines.append("📈 TEMPORAL PATTERNS")
            lines.append("─" * 70)

            if context.completion_by_weekday:
                lines.append("Success days:")
                for day, count in sorted(
                    context.completion_by_weekday.items(),
                    key=lambda x: x[1],
                    reverse=True
                ):
                    lines.append(f"  ✅ {day}: {count} completions")

            if context.miss_by_weekday:
                lines.append("Struggle days:")
                for day, count in sorted(
                    context.miss_by_weekday.items(),
                    key=lambda x: x[1],
                    reverse=True
                ):
                    lines.append(f"  ❌ {day}: {count} misses")
            lines.append("")

        # Coach Approach Section
        lines.append("🎯 RECOMMENDED COACH APPROACH")
        lines.append("─" * 70)
        lines.append(f"Suggestion: {context.coach_suggestion.replace('_', ' ').title()}")
        lines.append("")
        lines.append(context.suggested_approach)
        lines.append("")

        # Context Notes
        if context.notes:
            lines.append("📝 CONTEXT NOTES")
            lines.append("─" * 70)
            lines.append(context.notes)
            lines.append("")

        # Footer
        lines.append("─" * 70)
        lines.append(f"Created: {context.created_date}")
        lines.append(f"Check-in generated: {datetime.now().isoformat()}")
        lines.append("=" * 70)

        return "\n".join(lines)

    def _get_status_emoji(self, context: CoachCheckinContext) -> str:
        """Get appropriate emoji based on commitment status."""
        if context.consecutive_misses >= 8:
            return "🚨"
        elif context.consecutive_misses >= 5:
            return "⚠️"
        elif context.consecutive_misses >= 3:
            return "⏰"
        elif context.consecutive_misses > 0:
            return "💭"
        elif context.current_streak >= 30:
            return "💎"
        elif context.current_streak >= 14:
            return "⭐"
        elif context.current_streak >= 7:
            return "🔥"
        else:
            return "✅"

    def format_coach_prompt(self, context: CoachCheckinContext) -> str:
        """
        Format a natural language prompt for Coach to use.

        Args:
            context: CoachCheckinContext

        Returns:
            Natural language prompt for Coach
        """
        approach = self.COACH_APPROACHES.get(context.coach_suggestion, {})

        lines = []
        lines.append(f"Coach Check-In for: {context.commitment_title}")
        lines.append("")

        # Suggested opening based on escalation
        if context.consecutive_misses == 0:
            if context.current_streak > 0:
                lines.append(f"Opening: Celebrate their {context.current_streak}-day streak!")
                lines.append(f"Ask: What made this week work? Capture the conditions.")
            else:
                lines.append("Opening: Check in on how the commitment is going.")
        elif context.consecutive_misses <= 2:
            lines.append(f"Opening: \"I see {context.commitment_title} didn't happen. You good?\"")
            lines.append("Tone: Gentle curiosity, no pressure")
        elif context.consecutive_misses <= 4:
            lines.append(f"Opening: \"This is the second time this week. What's up?\"")
            lines.append("Check: Is this commitment still serving them?")
        elif context.consecutive_misses <= 7:
            lines.append(f"Opening: \"Real talk: {context.commitment_title} hasn't happened in a week.\"")
            lines.append("Ask: What's blocking them? Be direct but kind.")
        else:
            lines.append(f"Opening: \"We need to discuss {context.commitment_title}.\"")
            lines.append(f"Data: {context.total_completions} completions out of {context.total_completions + context.total_misses} attempts.")
            lines.append("Offer: Redesign completely or let it go. Which feels right?")

        lines.append("")
        lines.append("Key Data Points:")
        lines.append(f"- Type: {context.commitment_type} | Domain: {context.domain}")

        if context.recurrence_pattern != 'none':
            lines.append(f"- Completion rate: {context.completion_rate:.0f}%")
            lines.append(f"- Current/Longest streak: {context.current_streak}/{context.longest_streak}")

        if context.miss_by_weekday:
            problem_days = sorted(context.miss_by_weekday.items(), key=lambda x: x[1], reverse=True)
            lines.append(f"- Pattern: Struggles on {problem_days[0][0]}")

        if approach:
            lines.append("")
            lines.append(f"Approach: {approach['focus']}")

        return "\n".join(lines)

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of commitments needing Coach attention.

        Returns:
            Dictionary with summary statistics
        """
        needing_coach = self.get_commitments_needing_coach()

        # Count by escalation level
        escalation_counts = {}
        for context in needing_coach:
            level = context.escalation_level
            escalation_counts[level] = escalation_counts.get(level, 0) + 1

        return {
            'total_needing_coach': len(needing_coach),
            'by_escalation': escalation_counts,
            'most_urgent': needing_coach[0].to_dict() if needing_coach else None,
            'timestamp': datetime.now().isoformat()
        }


def main():
    """Command-line interface for Coach check-ins."""
    parser = argparse.ArgumentParser(
        description="Coach accountability check-in tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s abc123                      # Check-in on specific commitment
  %(prog)s abc123 --detailed           # Detailed check-in report
  %(prog)s --list                      # List commitments needing Coach
  %(prog)s --all                       # Check-in on all needing attention
  %(prog)s abc123 --json               # Output as JSON
  %(prog)s --summary                   # Quick summary
        """
    )

    parser.add_argument(
        'commitment_id',
        nargs='?',
        help='Commitment ID to check in on'
    )
    parser.add_argument(
        '-l', '--list',
        action='store_true',
        help='List all commitments needing Coach attention'
    )
    parser.add_argument(
        '-a', '--all',
        action='store_true',
        help='Check-in on all commitments needing attention'
    )
    parser.add_argument(
        '-d', '--detailed',
        action='store_true',
        help='Show detailed check-in report'
    )
    parser.add_argument(
        '-p', '--prompt',
        action='store_true',
        help='Generate Coach prompt format'
    )
    parser.add_argument(
        '-j', '--json',
        action='store_true',
        help='Output as JSON'
    )
    parser.add_argument(
        '-s', '--summary',
        action='store_true',
        help='Show summary of commitments needing Coach'
    )
    parser.add_argument(
        '--state-dir',
        type=Path,
        help='Path to State directory (defaults to ../State)'
    )

    args = parser.parse_args()

    # Initialize Coach check-in
    try:
        checkin = CoachCheckin(state_dir=args.state_dir)
    except Exception as e:
        print(f"❌ Error initializing Coach check-in: {e}", file=sys.stderr)
        sys.exit(1)

    # Handle summary mode
    if args.summary:
        summary = checkin.get_summary()
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print("📊 Coach Check-In Summary")
            print("=" * 60)
            print(f"Commitments needing Coach: {summary['total_needing_coach']}")

            if summary['by_escalation']:
                print("\nBy escalation level:")
                for level, count in summary['by_escalation'].items():
                    print(f"  {level.replace('_', ' ').title()}: {count}")

            if summary['most_urgent']:
                print(f"\nMost urgent: {summary['most_urgent']['commitment_title']}")
                print(f"  Escalation: {summary['most_urgent']['escalation_level']}")
        return

    # Handle list mode
    if args.list:
        needing_coach = checkin.get_commitments_needing_coach()

        if args.json:
            output = [ctx.to_dict() for ctx in needing_coach]
            print(json.dumps(output, indent=2))
        else:
            print("📋 Commitments Needing Coach Attention")
            print("=" * 60)

            if not needing_coach:
                print("✅ No commitments need Coach intervention right now!")
            else:
                for context in needing_coach:
                    print(f"\n{checkin.format_checkin_brief(context)}")
                    print("")
        return

    # Handle all mode
    if args.all:
        needing_coach = checkin.get_commitments_needing_coach()

        if args.json:
            output = [ctx.to_dict() for ctx in needing_coach]
            print(json.dumps(output, indent=2))
        else:
            for context in needing_coach:
                if args.detailed:
                    print(checkin.format_checkin_detailed(context))
                elif args.prompt:
                    print(checkin.format_coach_prompt(context))
                else:
                    print(checkin.format_checkin_brief(context))
                print("\n")
        return

    # Handle specific commitment check-in
    if not args.commitment_id:
        parser.print_help()
        sys.exit(1)

    try:
        context = checkin.get_checkin_context(args.commitment_id)
    except Exception as e:
        print(f"❌ Error getting check-in context: {e}", file=sys.stderr)
        sys.exit(1)

    if not context:
        print(f"❌ Commitment not found: {args.commitment_id}", file=sys.stderr)
        sys.exit(1)

    # Output check-in
    if args.json:
        print(json.dumps(context.to_dict(), indent=2))
    elif args.prompt:
        print(checkin.format_coach_prompt(context))
    elif args.detailed:
        print(checkin.format_checkin_detailed(context))
    else:
        print(checkin.format_checkin_brief(context))


if __name__ == "__main__":
    main()
