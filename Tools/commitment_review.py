#!/usr/bin/env python3
"""
Commitment Review - Generates weekly commitment performance review.

This tool creates a comprehensive weekly review of commitment performance,
combining analytics with Coach-style reflection prompts to help users
understand their patterns and improve their commitment follow-through.

Usage:
    # Generate weekly review
    python commitment_review.py

    # Review specific week
    python commitment_review.py --week-offset 1  # Last week

    # Output as JSON
    python commitment_review.py --json

    # Save to file
    python commitment_review.py --output review.md

As a module:
    from Tools.commitment_review import CommitmentReview

    review = CommitmentReview()
    report = review.generate_review()
"""

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, List, Optional, Any
import random

# Import our commitment modules
try:
    from commitment_analytics import CommitmentAnalytics, WeeklyStats, TrendAnalysis, CommitmentInsight
    from commitment_tracker import CommitmentTracker, Commitment
except ImportError:
    # Try relative import if run as module
    from .commitment_analytics import CommitmentAnalytics, WeeklyStats, TrendAnalysis, CommitmentInsight
    from .commitment_tracker import CommitmentTracker, Commitment


@dataclass
class ReflectionPrompt:
    """A Coach-style reflection prompt."""
    category: str  # 'wins', 'struggles', 'patterns', 'redesign'
    question: str
    context: str  # Why this question matters
    priority: int = 3  # 1 = highest, 5 = lowest

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class WeeklyReview:
    """Comprehensive weekly commitment review."""
    week_start: str
    week_end: str
    generated_at: str

    # Analytics data
    weekly_stats: Dict[str, Any]
    trend_analysis: Dict[str, Any]
    insights: List[Dict[str, Any]]

    # Highlights
    wins: List[str]
    struggles: List[str]
    streak_milestones: List[Dict[str, Any]]

    # Reflection prompts
    reflection_prompts: List[Dict[str, Any]]

    # Summary
    summary_message: str
    completion_grade: str  # A+, A, B+, B, C, D, F

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class CommitmentReview:
    """
    Generates comprehensive weekly commitment reviews.

    Combines analytics data with Coach-style reflection prompts to help
    users understand their commitment patterns and make improvements.
    """

    # Coach-style reflection questions by category
    REFLECTION_QUESTIONS = {
        'wins': [
            ("What made your successful commitments work this week?",
             "Understanding success conditions helps replicate them."),
            ("Which commitment felt easiest to keep? Why?",
             "Ease often signals alignment with your natural rhythms."),
            ("What conditions supported your streaks this week?",
             "Environment matters more than willpower."),
            ("When did you feel most proud of following through?",
             "Pride is data about what matters to you."),
            ("What surprised you about what you accomplished?",
             "Surprises reveal untapped capabilities."),
        ],
        'struggles': [
            ("What got in the way of your commitments this week?",
             "Obstacles are information, not failures."),
            ("Which commitment felt hardest? What made it hard?",
             "Friction points signal misalignment or poor design."),
            ("When did you notice yourself avoiding a commitment?",
             "Avoidance is always trying to tell you something."),
            ("What excuse showed up most often this week?",
             "Recurring excuses often mask deeper blockers."),
            ("What commitment are you considering dropping? Why?",
             "Sometimes letting go is the right move."),
        ],
        'patterns': [
            ("What day of the week is hardest for keeping commitments?",
             "Temporal patterns reveal energy and schedule realities."),
            ("Do you see any connection between missed commitments?",
             "Patterns across failures point to systemic issues."),
            ("When do you have the most follow-through energy?",
             "Align your important commitments with your peak times."),
            ("What type of commitment (habit/goal/task) works best for you?",
             "Different commitment types suit different personalities."),
            ("Are you overcommitted? What feels like too much?",
             "Overload is the enemy of consistency."),
        ],
        'redesign': [
            ("Which commitment needs to be redesigned, not just retried?",
             "Repetition without adjustment is insanity."),
            ("What would make [struggling commitment] feel easier?",
             "Small tweaks can remove significant friction."),
            ("Is there a commitment that no longer serves you?",
             "What mattered last month might not matter now."),
            ("What commitment would you make if you weren't afraid of failing?",
             "Fear-based avoidance limits growth."),
            ("What's one commitment you could drop to create space?",
             "Less can be more when it comes to consistency."),
        ],
        'values': [
            ("Which commitments align most with who you want to be?",
             "Values alignment creates intrinsic motivation."),
            ("What commitment are you keeping out of 'should' vs. genuine want?",
             "Should-based commitments rarely stick."),
            ("If you could only keep 3 commitments, which would they be?",
             "Priority clarity reduces decision fatigue."),
            ("What would someone who truly valued [domain] do consistently?",
             "Identity-based habits are stronger than goal-based ones."),
            ("Are your commitments reflecting your current values or past ones?",
             "We grow and change; commitments should too."),
        ]
    }

    # Grading thresholds
    GRADE_THRESHOLDS = {
        'A+': 95,
        'A': 90,
        'A-': 85,
        'B+': 80,
        'B': 75,
        'B-': 70,
        'C+': 65,
        'C': 60,
        'C-': 55,
        'D': 50,
        'F': 0
    }

    def __init__(self, state_dir: Optional[Path] = None):
        """
        Initialize the commitment review generator.

        Args:
            state_dir: Path to State directory (defaults to ../State)
        """
        if state_dir is None:
            state_dir = Path(__file__).parent.parent / "State"

        self.state_dir = Path(state_dir)
        self.analytics = CommitmentAnalytics(state_dir=state_dir)
        self.tracker = CommitmentTracker(state_dir=state_dir)

    def generate_review(
        self,
        week_offset: int = 0,
        weeks_to_compare: int = 4
    ) -> WeeklyReview:
        """
        Generate a comprehensive weekly review.

        Args:
            week_offset: Weeks back from current week (0 = this week, 1 = last week)
            weeks_to_compare: Number of weeks to include in trend analysis

        Returns:
            WeeklyReview with complete analysis and reflection prompts
        """
        # Calculate week dates
        today = date.today()
        current_week_start = today - timedelta(days=today.weekday())
        week_start = current_week_start - timedelta(weeks=week_offset)
        week_end = week_start + timedelta(days=6)

        # Get analytics data
        weekly_stats = self.analytics.get_weekly_stats(week_start, week_end)
        trend_analysis = self.analytics.get_trend_analysis(weeks_to_compare=weeks_to_compare)
        insights = self.analytics.get_insights(weeks=weeks_to_compare)

        # Extract highlights
        wins = self._extract_wins(weekly_stats, trend_analysis, insights)
        struggles = self._extract_struggles(weekly_stats, trend_analysis, insights)
        streak_milestones = weekly_stats.streak_milestones

        # Generate reflection prompts
        reflection_prompts = self._generate_reflection_prompts(
            weekly_stats,
            trend_analysis,
            insights
        )

        # Create summary message
        summary_message = self._create_summary_message(
            weekly_stats,
            trend_analysis,
            wins,
            struggles
        )

        # Calculate grade
        completion_grade = self._calculate_grade(weekly_stats.completion_rate)

        review = WeeklyReview(
            week_start=weekly_stats.week_start,
            week_end=weekly_stats.week_end,
            generated_at=datetime.now().isoformat(),
            weekly_stats=weekly_stats.to_dict(),
            trend_analysis=trend_analysis.to_dict(),
            insights=[i.to_dict() for i in insights],
            wins=wins,
            struggles=struggles,
            streak_milestones=streak_milestones,
            reflection_prompts=[p.to_dict() for p in reflection_prompts],
            summary_message=summary_message,
            completion_grade=completion_grade
        )

        return review

    def _extract_wins(
        self,
        stats: WeeklyStats,
        trend: TrendAnalysis,
        insights: List[CommitmentInsight]
    ) -> List[str]:
        """Extract wins and positive highlights from the week."""
        wins = []

        # Completion rate wins
        if stats.completion_rate >= 80:
            wins.append(f"🎯 {stats.completion_rate:.0f}% completion rate - exceptional consistency!")
        elif stats.completion_rate >= 70:
            wins.append(f"✅ {stats.completion_rate:.0f}% completion rate - solid week!")

        # Improvement wins
        if trend.trend_direction == 'improving':
            wins.append(f"📈 Performance improving by {trend.completion_rate_change:.1f} percentage points!")

        # Streak wins
        if stats.streak_milestones:
            for milestone in stats.streak_milestones[:3]:  # Top 3
                wins.append(f"🏆 {milestone['commitment_title']} hit {milestone['milestone']}-day milestone!")

        # Type-specific wins
        for c_type, type_stats in stats.by_type.items():
            if type_stats['total_commitments'] > 0 and type_stats['completion_rate'] >= 90:
                wins.append(f"⭐ {c_type.capitalize()}s crushing it at {type_stats['completion_rate']:.0f}%!")

        # Personal records
        if trend.streak_trends['personal_records_count'] > 0:
            wins.append(f"🎉 {trend.streak_trends['personal_records_count']} personal record{'s' if trend.streak_trends['personal_records_count'] > 1 else ''} active!")

        # High volume completion
        if stats.completed_count >= 20:
            wins.append(f"💪 Completed {stats.completed_count} commitments this week - impressive volume!")

        return wins

    def _extract_struggles(
        self,
        stats: WeeklyStats,
        trend: TrendAnalysis,
        insights: List[CommitmentInsight]
    ) -> List[str]:
        """Extract struggles and areas for improvement."""
        struggles = []

        # Low completion rate
        if stats.completion_rate < 60:
            struggles.append(f"⚠️  {stats.completion_rate:.0f}% completion rate - below target")

        # Declining trend
        if trend.trend_direction == 'declining':
            struggles.append(f"📉 Performance declining by {abs(trend.completion_rate_change):.1f} percentage points")

        # High miss count
        if stats.missed_count >= 5:
            struggles.append(f"🚨 {stats.missed_count} missed commitments this week")

        # Type-specific struggles
        for c_type, type_stats in stats.by_type.items():
            if type_stats['total_commitments'] > 0 and type_stats['completion_rate'] < 50:
                struggles.append(f"🔍 {c_type.capitalize()}s struggling at {type_stats['completion_rate']:.0f}% - may need adjustment")

        # No active streaks
        if trend.streak_trends['total_active_streaks'] == 0:
            struggles.append("💭 No active streaks - consider starting small to build momentum")

        # Extract warning insights
        for insight in insights:
            if insight.type == 'warning':
                struggles.append(f"⚠️  {insight.message}")

        return struggles

    def _generate_reflection_prompts(
        self,
        stats: WeeklyStats,
        trend: TrendAnalysis,
        insights: List[CommitmentInsight]
    ) -> List[ReflectionPrompt]:
        """Generate Coach-style reflection prompts based on the week's data."""
        prompts = []

        # Always include at least one from each major category
        # Wins prompts (if there are wins)
        if stats.completion_rate >= 60 or stats.streak_milestones:
            q, c = random.choice(self.REFLECTION_QUESTIONS['wins'])
            prompts.append(ReflectionPrompt(
                category='wins',
                question=q,
                context=c,
                priority=1 if stats.completion_rate >= 80 else 2
            ))

        # Struggles prompts (if there are struggles)
        if stats.completion_rate < 70 or stats.missed_count > 0:
            q, c = random.choice(self.REFLECTION_QUESTIONS['struggles'])
            prompts.append(ReflectionPrompt(
                category='struggles',
                question=q,
                context=c,
                priority=1 if stats.completion_rate < 50 else 2
            ))

        # Pattern prompts (always valuable)
        q, c = random.choice(self.REFLECTION_QUESTIONS['patterns'])
        prompts.append(ReflectionPrompt(
            category='patterns',
            question=q,
            context=c,
            priority=2
        ))

        # Redesign prompts (if struggling with specific types)
        needs_redesign = False
        for c_type, type_stats in stats.by_type.items():
            if type_stats['total_commitments'] > 0 and type_stats['completion_rate'] < 60:
                needs_redesign = True
                break

        if needs_redesign or trend.trend_direction == 'declining':
            q, c = random.choice(self.REFLECTION_QUESTIONS['redesign'])
            prompts.append(ReflectionPrompt(
                category='redesign',
                question=q,
                context=c,
                priority=1 if stats.completion_rate < 50 else 3
            ))

        # Values prompts (periodic check-in)
        q, c = random.choice(self.REFLECTION_QUESTIONS['values'])
        prompts.append(ReflectionPrompt(
            category='values',
            question=q,
            context=c,
            priority=3
        ))

        # Sort by priority
        prompts.sort(key=lambda p: p.priority)

        return prompts[:5]  # Top 5 most relevant

    def _create_summary_message(
        self,
        stats: WeeklyStats,
        trend: TrendAnalysis,
        wins: List[str],
        struggles: List[str]
    ) -> str:
        """Create a Coach-style summary message."""
        messages = []

        # Opening based on performance
        if stats.completion_rate >= 85:
            openings = [
                "Exceptional week. You showed up consistently and it shows.",
                "This is what consistency looks like. Well done.",
                "You crushed it this week. That's the standard you're setting.",
            ]
        elif stats.completion_rate >= 70:
            openings = [
                "Solid week. You maintained good momentum.",
                "Good follow-through this week. Keep building on this.",
                "You stayed consistent where it mattered. That's progress.",
            ]
        elif stats.completion_rate >= 50:
            openings = [
                "Mixed week, but you kept some things going. That matters.",
                "Not your strongest week, but you didn't give up. That's something.",
                "Some wins, some misses. The question is: what's the pattern?",
            ]
        else:
            openings = [
                "Tough week. Let's be honest about what's not working.",
                "This week was a struggle. Time to reassess and redesign.",
                "Real talk: something needs to change. Let's figure out what.",
            ]

        messages.append(random.choice(openings))

        # Trend commentary
        if trend.trend_direction == 'improving':
            messages.append("You're on an upward trajectory. The consistency is paying off.")
        elif trend.trend_direction == 'declining':
            messages.append("You're sliding. Catch it now before it becomes a pattern.")

        # Actionable next step
        if len(struggles) > len(wins):
            messages.append("Focus on the reflection questions. They'll help you see what needs adjusting.")
        elif stats.streak_milestones:
            messages.append("Protect those streaks. They represent real progress.")
        else:
            messages.append("Keep showing up. Consistency compounds.")

        return " ".join(messages)

    def _calculate_grade(self, completion_rate: float) -> str:
        """Calculate a letter grade based on completion rate."""
        for grade, threshold in self.GRADE_THRESHOLDS.items():
            if completion_rate >= threshold:
                return grade
        return 'F'

    def format_review(
        self,
        review: WeeklyReview,
        detailed: bool = False
    ) -> str:
        """
        Format the review as human-readable text.

        Args:
            review: WeeklyReview to format
            detailed: Whether to show full details

        Returns:
            Formatted text output
        """
        lines = []

        # Header
        lines.append("=" * 70)
        lines.append("📊 WEEKLY COMMITMENT REVIEW")
        lines.append(f"Week of {review.week_start} to {review.week_end}")
        lines.append("=" * 70)
        lines.append("")

        # Grade and summary
        grade_emoji = self._get_grade_emoji(review.completion_grade)
        lines.append(f"{grade_emoji} OVERALL GRADE: {review.completion_grade}")
        lines.append(f"Completion Rate: {review.weekly_stats['completion_rate']:.1f}%")
        lines.append("")
        lines.append(f"💭 {review.summary_message}")
        lines.append("")

        # Wins section
        if review.wins:
            lines.append("🏆 WINS & HIGHLIGHTS")
            lines.append("─" * 70)
            for win in review.wins:
                lines.append(f"  {win}")
            lines.append("")

        # Struggles section
        if review.struggles:
            lines.append("🔍 AREAS FOR IMPROVEMENT")
            lines.append("─" * 70)
            for struggle in review.struggles:
                lines.append(f"  {struggle}")
            lines.append("")

        # Statistics section
        lines.append("📈 WEEKLY STATISTICS")
        lines.append("─" * 70)
        ws = review.weekly_stats
        lines.append(f"  Active commitments: {ws['total_commitments']}")
        lines.append(f"  Completed: {ws['completed_count']}")
        lines.append(f"  Missed: {ws['missed_count']}")
        lines.append(f"  Completion rate: {ws['completion_rate']:.1f}%")
        lines.append("")

        # By type
        if detailed:
            lines.append("  By Type:")
            for c_type, stats in ws['by_type'].items():
                if stats['total_commitments'] > 0:
                    lines.append(f"    {c_type.capitalize()}:")
                    lines.append(f"      Commitments: {stats['total_commitments']}")
                    lines.append(f"      Expected: {stats['expected_completions']}")
                    lines.append(f"      Completed: {stats['completed']}")
                    lines.append(f"      Rate: {stats['completion_rate']:.1f}%")
            lines.append("")

        # Trend section
        trend = review.trend_analysis
        lines.append("📊 TREND ANALYSIS")
        lines.append("─" * 70)
        trend_emoji = "📈" if trend['trend_direction'] == 'improving' else "📉" if trend['trend_direction'] == 'declining' else "➡️"
        lines.append(f"  {trend_emoji} Direction: {trend['trend_direction'].upper()}")

        change = trend['completion_rate_change']
        if change >= 0:
            lines.append(f"  Change: +{change:.1f} percentage points")
        else:
            lines.append(f"  Change: {change:.1f} percentage points")

        # Streak trends
        st = trend['streak_trends']
        lines.append(f"  Active streaks: {st['total_active_streaks']}")
        if st['longest_current_streak'] > 0:
            lines.append(f"  Longest streak: {st['longest_current_streak']} days")
            if st['longest_streak_commitment']:
                lines.append(f"    ({st['longest_streak_commitment']['title']})")
        lines.append("")

        # Streak milestones
        if review.streak_milestones:
            lines.append("🎯 STREAK MILESTONES ACHIEVED")
            lines.append("─" * 70)
            for milestone in review.streak_milestones:
                milestone_emoji = self._get_milestone_emoji(milestone['milestone'])
                lines.append(f"  {milestone_emoji} {milestone['commitment_title']}")
                lines.append(f"     Reached {milestone['milestone']}-day milestone! (Current: {milestone['current_streak']} days)")
            lines.append("")

        # Reflection prompts
        lines.append("🧠 REFLECTION PROMPTS")
        lines.append("─" * 70)
        lines.append("Take time to reflect on these questions:")
        lines.append("")

        for i, prompt in enumerate(review.reflection_prompts, 1):
            lines.append(f"{i}. {prompt['question']}")
            if detailed:
                lines.append(f"   💭 {prompt['context']}")
            lines.append("")

        # Key insights
        if review.insights:
            lines.append("💡 KEY INSIGHTS")
            lines.append("─" * 70)
            for insight in review.insights[:5]:  # Top 5
                emoji = {
                    'success': '✅',
                    'warning': '⚠️ ',
                    'pattern': '🔍',
                    'suggestion': '💭'
                }.get(insight['type'], '•')
                lines.append(f"  {emoji} {insight['message']}")
            lines.append("")

        # Footer
        lines.append("─" * 70)
        lines.append("🎯 Next Steps:")
        lines.append("  1. Review your reflection questions honestly")
        lines.append("  2. Identify one commitment to improve or redesign")
        lines.append("  3. Celebrate your wins - progress compounds")
        lines.append("")
        lines.append("Generated: " + review.generated_at)
        lines.append("=" * 70)

        return "\n".join(lines)

    def _get_grade_emoji(self, grade: str) -> str:
        """Get emoji for grade."""
        if grade.startswith('A'):
            return "🌟"
        elif grade.startswith('B'):
            return "✅"
        elif grade.startswith('C'):
            return "⚠️"
        elif grade.startswith('D'):
            return "🚨"
        else:
            return "❌"

    def _get_milestone_emoji(self, milestone: int) -> str:
        """Get emoji for milestone."""
        if milestone >= 100:
            return "💎"
        elif milestone >= 30:
            return "🏆"
        elif milestone >= 14:
            return "⭐"
        elif milestone >= 7:
            return "🔥"
        else:
            return "✨"

    def save_review(
        self,
        review: WeeklyReview,
        filepath: Path,
        detailed: bool = False
    ):
        """
        Save review to a file.

        Args:
            review: WeeklyReview to save
            filepath: Path to save to
            detailed: Whether to include detailed statistics
        """
        if filepath.suffix == '.json':
            # Save as JSON
            filepath.write_text(json.dumps(review.to_dict(), indent=2))
        else:
            # Save as formatted text (markdown)
            content = self.format_review(review, detailed=detailed)
            filepath.write_text(content)


def main():
    """Command-line interface for weekly commitment review."""
    parser = argparse.ArgumentParser(
        description="Generate weekly commitment review with reflection prompts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                         # This week's review
  %(prog)s --week-offset 1         # Last week's review
  %(prog)s --detailed              # Include detailed statistics
  %(prog)s --json                  # Output as JSON
  %(prog)s --output review.md      # Save to file
        """
    )

    parser.add_argument(
        '-w', '--week-offset',
        type=int,
        default=0,
        help='Weeks back from current week (0 = this week, 1 = last week)'
    )
    parser.add_argument(
        '-c', '--compare-weeks',
        type=int,
        default=4,
        help='Number of weeks to compare in trend analysis (default: 4)'
    )
    parser.add_argument(
        '-d', '--detailed',
        action='store_true',
        help='Show detailed statistics'
    )
    parser.add_argument(
        '-j', '--json',
        action='store_true',
        help='Output as JSON'
    )
    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Save review to file (supports .md or .json)'
    )
    parser.add_argument(
        '--state-dir',
        type=Path,
        help='Path to State directory (defaults to ../State)'
    )

    args = parser.parse_args()

    # Initialize review generator
    try:
        review_gen = CommitmentReview(state_dir=args.state_dir)
    except Exception as e:
        print(f"❌ Error initializing commitment review: {e}", file=sys.stderr)
        sys.exit(1)

    # Generate review
    try:
        review = review_gen.generate_review(
            week_offset=args.week_offset,
            weeks_to_compare=args.compare_weeks
        )
    except Exception as e:
        print(f"❌ Error generating review: {e}", file=sys.stderr)
        sys.exit(1)

    # Output or save results
    if args.output:
        try:
            review_gen.save_review(review, args.output, detailed=args.detailed)
            print(f"✅ Review saved to {args.output}")
        except Exception as e:
            print(f"❌ Error saving review: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.json:
        print(json.dumps(review.to_dict(), indent=2))
    else:
        output = review_gen.format_review(review, detailed=args.detailed)
        print(output)


if __name__ == "__main__":
    main()
