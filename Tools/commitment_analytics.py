#!/usr/bin/env python3
"""
Commitment Analytics - Calculate commitment performance metrics and trends.

This module provides analytics capabilities for commitment tracking, including
completion rates, streak statistics, trend analysis, and performance comparisons
across time periods. Supports insights generation for weekly reviews.

Usage:
    # Generate analytics for current week
    python commitment_analytics.py

    # Compare weeks
    python commitment_analytics.py --compare-weeks 4

    # Output as JSON
    python commitment_analytics.py --json

As a module:
    from Tools.commitment_analytics import CommitmentAnalytics

    analytics = CommitmentAnalytics()
    weekly_stats = analytics.get_weekly_stats()
"""

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

# Import our commitment modules
try:
    from commitment_tracker import CommitmentTracker, Commitment, CommitmentType
except ImportError:
    # Try relative import if run as module
    from .commitment_tracker import CommitmentTracker, Commitment, CommitmentType


@dataclass
class WeeklyStats:
    """Statistics for a single week."""
    week_start: str  # ISO date
    week_end: str  # ISO date
    total_commitments: int
    completed_count: int
    missed_count: int
    completion_rate: float  # Percentage (0-100)
    by_type: Dict[str, Dict[str, Any]]  # Stats broken down by commitment type
    streak_milestones: List[Dict[str, Any]]  # Streaks achieved this week
    average_completion_time: Optional[float] = None  # Average days to complete

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class TrendAnalysis:
    """Trend analysis comparing multiple weeks."""
    current_week: WeeklyStats
    previous_weeks: List[WeeklyStats]
    trend_direction: str  # 'improving', 'stable', 'declining'
    completion_rate_change: float  # Percentage point change
    streak_trends: Dict[str, Any]
    insights: List[str]  # Actionable insights

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class CommitmentInsight:
    """Individual insight about commitment performance."""
    type: str  # 'success', 'warning', 'pattern', 'suggestion'
    category: str  # 'completion', 'streak', 'overdue', 'performance'
    message: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class CommitmentAnalytics:
    """
    Analyzes commitment performance metrics and trends.

    Provides comprehensive analytics including completion rates, streak
    statistics, trend analysis, and actionable insights for improvement.
    """

    def __init__(self, state_dir: Optional[Path] = None):
        """
        Initialize the commitment analytics engine.

        Args:
            state_dir: Path to State directory (defaults to ../State)
        """
        if state_dir is None:
            state_dir = Path(__file__).parent.parent / "State"

        self.state_dir = Path(state_dir)
        self.tracker = CommitmentTracker(state_dir=state_dir)

    def get_weekly_stats(
        self,
        week_start: Optional[date] = None,
        week_end: Optional[date] = None
    ) -> WeeklyStats:
        """
        Calculate statistics for a specific week.

        Args:
            week_start: Start date of week (defaults to start of current week)
            week_end: End date of week (defaults to end of current week)

        Returns:
            WeeklyStats for the specified week
        """
        # Default to current week (Monday to Sunday)
        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())  # Monday

        if week_end is None:
            week_end = week_start + timedelta(days=6)  # Sunday

        # Get all commitments
        all_commitments = self.tracker.get_all_commitments()

        # Filter completions within this week
        completed_this_week = []
        missed_this_week = []
        by_type: Dict[str, Dict[str, Any]] = {}
        streak_milestones = []

        # Track stats by type
        type_stats = {
            'habit': {'total': 0, 'completed': 0, 'missed': 0, 'expected': 0},
            'goal': {'total': 0, 'completed': 0, 'missed': 0, 'expected': 0},
            'task': {'total': 0, 'completed': 0, 'missed': 0, 'expected': 0}
        }

        for commitment in all_commitments:
            c_type = commitment.type

            # Count completions and misses in this week
            week_completions = 0
            week_misses = 0

            for record in commitment.completion_history:
                try:
                    record_date = datetime.fromisoformat(record.timestamp).date()
                    if week_start <= record_date <= week_end:
                        if record.status == 'completed':
                            week_completions += 1
                            completed_this_week.append(commitment.id)
                        elif record.status == 'missed':
                            week_misses += 1
                            missed_this_week.append(commitment.id)
                except (ValueError, TypeError):
                    continue

            # For recurring commitments, calculate expected occurrences
            expected_this_week = 0
            if commitment.is_recurring():
                expected_dates = self.tracker._get_expected_dates(
                    commitment,
                    datetime.combine(week_start, datetime.min.time()),
                    datetime.combine(week_end, datetime.max.time())
                )
                expected_this_week = len(expected_dates)

            # For non-recurring, check if due this week
            elif commitment.due_date:
                try:
                    due = datetime.fromisoformat(commitment.due_date).date()
                    if week_start <= due <= week_end:
                        expected_this_week = 1
                except (ValueError, TypeError):
                    pass

            # Update type stats
            if c_type in type_stats:
                if expected_this_week > 0 or week_completions > 0 or week_misses > 0:
                    type_stats[c_type]['total'] += 1
                    type_stats[c_type]['expected'] += expected_this_week
                    type_stats[c_type]['completed'] += week_completions
                    type_stats[c_type]['missed'] += week_misses

            # Check for streak milestones achieved this week
            if commitment.is_recurring() and commitment.streak_count > 0:
                # Milestone thresholds
                milestones = [3, 7, 14, 21, 30, 60, 90, 100]
                for milestone in milestones:
                    if commitment.streak_count >= milestone:
                        # Check if milestone was reached this week
                        # (crude check - see if streak would be less than milestone without this week)
                        if commitment.streak_count - 7 < milestone <= commitment.streak_count:
                            streak_milestones.append({
                                'commitment_id': commitment.id,
                                'commitment_title': commitment.title,
                                'milestone': milestone,
                                'current_streak': commitment.streak_count
                            })
                            break  # Only report the most recent milestone

        # Calculate overall stats
        total_expected = sum(type_stats[t]['expected'] for t in type_stats)
        total_completed = sum(type_stats[t]['completed'] for t in type_stats)
        total_missed = sum(type_stats[t]['missed'] for t in type_stats)

        completion_rate = 0.0
        if total_expected > 0:
            completion_rate = (total_completed / total_expected) * 100.0

        # Build by_type stats
        for c_type in type_stats:
            stats = type_stats[c_type]
            if stats['expected'] > 0:
                type_completion_rate = (stats['completed'] / stats['expected']) * 100.0
            else:
                type_completion_rate = 0.0

            by_type[c_type] = {
                'total_commitments': stats['total'],
                'expected_completions': stats['expected'],
                'completed': stats['completed'],
                'missed': stats['missed'],
                'completion_rate': round(type_completion_rate, 1)
            }

        return WeeklyStats(
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
            total_commitments=sum(type_stats[t]['total'] for t in type_stats),
            completed_count=total_completed,
            missed_count=total_missed,
            completion_rate=round(completion_rate, 1),
            by_type=by_type,
            streak_milestones=streak_milestones
        )

    def get_trend_analysis(
        self,
        weeks_to_compare: int = 4
    ) -> TrendAnalysis:
        """
        Analyze trends over multiple weeks.

        Args:
            weeks_to_compare: Number of weeks to analyze (including current)

        Returns:
            TrendAnalysis with trend information and insights
        """
        today = date.today()
        current_week_start = today - timedelta(days=today.weekday())

        # Get stats for each week
        weekly_stats = []
        for week_offset in range(weeks_to_compare):
            week_start = current_week_start - timedelta(weeks=week_offset)
            week_end = week_start + timedelta(days=6)
            stats = self.get_weekly_stats(week_start, week_end)
            weekly_stats.append(stats)

        current_week = weekly_stats[0]
        previous_weeks = weekly_stats[1:]

        # Determine trend direction
        trend_direction, completion_rate_change = self._calculate_trend_direction(
            current_week,
            previous_weeks
        )

        # Analyze streak trends
        streak_trends = self._analyze_streak_trends(weeks_to_compare)

        # Generate insights
        insights = self._generate_insights(
            current_week,
            previous_weeks,
            trend_direction,
            streak_trends
        )

        return TrendAnalysis(
            current_week=current_week,
            previous_weeks=previous_weeks,
            trend_direction=trend_direction,
            completion_rate_change=round(completion_rate_change, 1),
            streak_trends=streak_trends,
            insights=insights
        )

    def _calculate_trend_direction(
        self,
        current_week: WeeklyStats,
        previous_weeks: List[WeeklyStats]
    ) -> Tuple[str, float]:
        """
        Calculate trend direction based on completion rates.

        Args:
            current_week: Current week stats
            previous_weeks: Previous weeks stats

        Returns:
            Tuple of (trend_direction, rate_change)
        """
        if not previous_weeks:
            return 'stable', 0.0

        # Calculate average completion rate of previous weeks
        prev_rates = [w.completion_rate for w in previous_weeks]
        avg_prev_rate = sum(prev_rates) / len(prev_rates)

        # Calculate change
        rate_change = current_week.completion_rate - avg_prev_rate

        # Determine direction
        if rate_change >= 10:
            return 'improving', rate_change
        elif rate_change <= -10:
            return 'declining', rate_change
        else:
            return 'stable', rate_change

    def _analyze_streak_trends(self, weeks: int) -> Dict[str, Any]:
        """
        Analyze streak trends over time.

        Args:
            weeks: Number of weeks to analyze

        Returns:
            Dictionary with streak trend data
        """
        all_commitments = self.tracker.get_all_commitments()
        recurring = [c for c in all_commitments if c.is_recurring()]

        active_streaks = [c for c in recurring if c.streak_count > 0]
        total_streaks = len(active_streaks)

        # Calculate average streak length
        avg_streak = 0.0
        if active_streaks:
            avg_streak = sum(c.streak_count for c in active_streaks) / len(active_streaks)

        # Find longest current streak
        longest_streak = max((c.streak_count for c in active_streaks), default=0)
        longest_streak_commitment = None
        if longest_streak > 0:
            for c in active_streaks:
                if c.streak_count == longest_streak:
                    longest_streak_commitment = {
                        'id': c.id,
                        'title': c.title,
                        'streak': c.streak_count
                    }
                    break

        # Count personal records
        personal_records = [
            c for c in recurring
            if c.streak_count > 0 and c.streak_count == c.longest_streak
        ]

        return {
            'total_active_streaks': total_streaks,
            'average_streak_length': round(avg_streak, 1),
            'longest_current_streak': longest_streak,
            'longest_streak_commitment': longest_streak_commitment,
            'personal_records_count': len(personal_records),
            'personal_records': [
                {'id': c.id, 'title': c.title, 'streak': c.streak_count}
                for c in personal_records[:5]  # Top 5
            ]
        }

    def _generate_insights(
        self,
        current_week: WeeklyStats,
        previous_weeks: List[WeeklyStats],
        trend_direction: str,
        streak_trends: Dict[str, Any]
    ) -> List[str]:
        """
        Generate actionable insights based on analytics.

        Args:
            current_week: Current week stats
            previous_weeks: Previous weeks stats
            trend_direction: Trend direction
            streak_trends: Streak trend data

        Returns:
            List of insight messages
        """
        insights = []

        # Completion rate insights
        if current_week.completion_rate >= 80:
            insights.append(f"🎯 Excellent completion rate of {current_week.completion_rate:.0f}%! You're crushing your commitments.")
        elif current_week.completion_rate >= 60:
            insights.append(f"✅ Good completion rate of {current_week.completion_rate:.0f}%. Keep up the momentum!")
        elif current_week.completion_rate >= 40:
            insights.append(f"⚠️  Completion rate of {current_week.completion_rate:.0f}% - there's room for improvement.")
        else:
            insights.append(f"🚨 Completion rate of {current_week.completion_rate:.0f}% is concerning. Let's reassess your commitments.")

        # Trend insights
        if trend_direction == 'improving':
            insights.append("📈 Your completion rate is improving! The consistency is paying off.")
        elif trend_direction == 'declining':
            insights.append("📉 Your completion rate is declining. Time to course-correct before it becomes a pattern.")

        # Type-specific insights
        for c_type, stats in current_week.by_type.items():
            if stats['total_commitments'] > 0:
                rate = stats['completion_rate']
                if rate < 50 and stats['total_commitments'] >= 2:
                    insights.append(f"🔍 Your {c_type}s are struggling ({rate:.0f}% completion). Consider reducing load or adjusting frequency.")
                elif rate >= 90:
                    insights.append(f"⭐ Your {c_type}s are on fire! {rate:.0f}% completion rate.")

        # Streak insights
        if streak_trends['total_active_streaks'] >= 3:
            insights.append(f"🔥 You're maintaining {streak_trends['total_active_streaks']} active streaks! That's powerful momentum.")
        elif streak_trends['total_active_streaks'] == 0:
            insights.append("💭 No active streaks right now. Start small - even a 3-day streak builds motivation.")

        if streak_trends['longest_current_streak'] >= 30:
            longest = streak_trends['longest_streak_commitment']
            if longest:
                insights.append(f"💎 Your '{longest['title']}' streak of {longest['streak']} days is exceptional!")

        # Personal records
        if streak_trends['personal_records_count'] > 0:
            insights.append(f"🎉 You're hitting {streak_trends['personal_records_count']} personal record{'s' if streak_trends['personal_records_count'] > 1 else ''}!")

        # Milestone insights
        if current_week.streak_milestones:
            milestone_titles = [m['commitment_title'] for m in current_week.streak_milestones[:3]]
            if len(milestone_titles) == 1:
                insights.append(f"🏆 Milestone achieved: '{milestone_titles[0]}' hit a streak milestone!")
            else:
                insights.append(f"🏆 Multiple milestones achieved this week! {', '.join(milestone_titles)}")

        # Compare to previous weeks
        if previous_weeks:
            avg_prev_completed = sum(w.completed_count for w in previous_weeks) / len(previous_weeks)
            if current_week.completed_count > avg_prev_completed * 1.2:
                insights.append(f"🚀 You completed {current_week.completed_count} items this week, up from your recent average of {avg_prev_completed:.0f}!")

        # Overload detection
        total_expected = sum(stats['expected_completions'] for stats in current_week.by_type.values())
        if total_expected > 50:
            insights.append(f"⚡ You had {total_expected} expected completions this week. That's a heavy load - consider if all are necessary.")

        return insights

    def get_commitment_performance(
        self,
        commitment_id: str,
        weeks: int = 4
    ) -> Dict[str, Any]:
        """
        Get detailed performance analysis for a specific commitment.

        Args:
            commitment_id: Commitment ID
            weeks: Number of weeks to analyze

        Returns:
            Dictionary with performance metrics
        """
        commitment = self.tracker.get_commitment(commitment_id)
        if not commitment:
            return {'error': 'Commitment not found'}

        # Get completion history for last N weeks
        today = date.today()
        cutoff_date = today - timedelta(weeks=weeks)

        recent_completions = []
        recent_misses = []

        for record in commitment.completion_history:
            try:
                record_date = datetime.fromisoformat(record.timestamp).date()
                if record_date >= cutoff_date:
                    if record.status == 'completed':
                        recent_completions.append(record_date)
                    elif record.status == 'missed':
                        recent_misses.append(record_date)
            except (ValueError, TypeError):
                continue

        # Calculate weekly breakdown
        weekly_breakdown = []
        for week_offset in range(weeks):
            week_start = today - timedelta(days=today.weekday()) - timedelta(weeks=week_offset)
            week_end = week_start + timedelta(days=6)

            week_completions = len([d for d in recent_completions if week_start <= d <= week_end])
            week_misses = len([d for d in recent_misses if week_start <= d <= week_end])

            # Calculate expected for recurring
            expected = 0
            if commitment.is_recurring():
                expected_dates = self.tracker._get_expected_dates(
                    commitment,
                    datetime.combine(week_start, datetime.min.time()),
                    datetime.combine(week_end, datetime.max.time())
                )
                expected = len(expected_dates)

            weekly_breakdown.append({
                'week_start': week_start.isoformat(),
                'week_end': week_end.isoformat(),
                'expected': expected,
                'completed': week_completions,
                'missed': week_misses,
                'rate': (week_completions / expected * 100.0) if expected > 0 else 0.0
            })

        return {
            'commitment_id': commitment.id,
            'commitment_title': commitment.title,
            'commitment_type': commitment.type,
            'current_streak': commitment.streak_count,
            'longest_streak': commitment.longest_streak,
            'overall_completion_rate': commitment.completion_rate,
            'recent_completions': len(recent_completions),
            'recent_misses': len(recent_misses),
            'weeks_analyzed': weeks,
            'weekly_breakdown': list(reversed(weekly_breakdown))  # Oldest to newest
        }

    def get_insights(self, weeks: int = 4) -> List[CommitmentInsight]:
        """
        Generate comprehensive insights about commitment performance.

        Args:
            weeks: Number of weeks to analyze

        Returns:
            List of CommitmentInsight objects
        """
        insights: List[CommitmentInsight] = []

        # Get trend analysis
        trend = self.get_trend_analysis(weeks_to_compare=weeks)

        # Success insights
        if trend.current_week.completion_rate >= 80:
            insights.append(CommitmentInsight(
                type='success',
                category='completion',
                message=f"Outstanding {trend.current_week.completion_rate:.0f}% completion rate this week!",
                data={'rate': trend.current_week.completion_rate}
            ))

        # Warning insights
        if trend.current_week.completion_rate < 50:
            insights.append(CommitmentInsight(
                type='warning',
                category='completion',
                message=f"Completion rate of {trend.current_week.completion_rate:.0f}% is below target. Consider reducing commitment load.",
                data={'rate': trend.current_week.completion_rate}
            ))

        # Trend insights
        if trend.trend_direction == 'improving':
            insights.append(CommitmentInsight(
                type='success',
                category='performance',
                message=f"Performance improving by {trend.completion_rate_change:.1f} percentage points!",
                data={'change': trend.completion_rate_change}
            ))
        elif trend.trend_direction == 'declining':
            insights.append(CommitmentInsight(
                type='warning',
                category='performance',
                message=f"Performance declining by {abs(trend.completion_rate_change):.1f} percentage points.",
                data={'change': trend.completion_rate_change}
            ))

        # Streak insights
        streak_trends = trend.streak_trends
        if streak_trends['total_active_streaks'] >= 3:
            insights.append(CommitmentInsight(
                type='success',
                category='streak',
                message=f"Maintaining {streak_trends['total_active_streaks']} active streaks!",
                data={'count': streak_trends['total_active_streaks']}
            ))

        if streak_trends['longest_current_streak'] >= 21:
            longest = streak_trends['longest_streak_commitment']
            insights.append(CommitmentInsight(
                type='success',
                category='streak',
                message=f"Exceptional {longest['streak']}-day streak on '{longest['title']}'!",
                data=longest
            ))

        # Pattern insights - check for struggling commitment types
        for c_type, stats in trend.current_week.by_type.items():
            if stats['total_commitments'] > 0 and stats['completion_rate'] < 50:
                insights.append(CommitmentInsight(
                    type='pattern',
                    category='performance',
                    message=f"Your {c_type}s are at {stats['completion_rate']:.0f}% completion - consider adjustment.",
                    data={'type': c_type, 'stats': stats}
                ))

        # Suggestion insights
        all_commitments = self.tracker.get_all_commitments()
        overdue_count = len(self.tracker.get_overdue())
        if overdue_count > 5:
            insights.append(CommitmentInsight(
                type='suggestion',
                category='overdue',
                message=f"You have {overdue_count} overdue items. Focus on clearing these first.",
                data={'count': overdue_count}
            ))

        return insights

    def export_analytics(
        self,
        filepath: Optional[Path] = None,
        weeks: int = 4
    ) -> str:
        """
        Export complete analytics to JSON.

        Args:
            filepath: Optional file path to save to
            weeks: Number of weeks to analyze

        Returns:
            JSON string of analytics data
        """
        trend = self.get_trend_analysis(weeks_to_compare=weeks)
        insights = self.get_insights(weeks=weeks)

        data = {
            'version': '1.0',
            'generated_at': datetime.now().isoformat(),
            'weeks_analyzed': weeks,
            'trend_analysis': trend.to_dict(),
            'insights': [i.to_dict() for i in insights]
        }

        json_str = json.dumps(data, indent=2)

        if filepath:
            Path(filepath).write_text(json_str)

        return json_str


def main():
    """Command-line interface for commitment analytics."""
    parser = argparse.ArgumentParser(
        description="Analyze commitment performance and trends",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                         # Show current week stats
  %(prog)s --trend                 # Show trend analysis
  %(prog)s --compare-weeks 8       # Compare last 8 weeks
  %(prog)s --insights              # Show actionable insights
  %(prog)s --json                  # Output as JSON
        """
    )

    parser.add_argument(
        '-t', '--trend',
        action='store_true',
        help='Show trend analysis across multiple weeks'
    )
    parser.add_argument(
        '-w', '--compare-weeks',
        type=int,
        default=4,
        help='Number of weeks to compare (default: 4)'
    )
    parser.add_argument(
        '-i', '--insights',
        action='store_true',
        help='Show actionable insights'
    )
    parser.add_argument(
        '-c', '--commitment',
        type=str,
        help='Analyze specific commitment by ID'
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

    # Initialize analytics
    try:
        analytics = CommitmentAnalytics(state_dir=args.state_dir)
    except Exception as e:
        print(f"❌ Error initializing analytics: {e}", file=sys.stderr)
        sys.exit(1)

    # Handle specific commitment analysis
    if args.commitment:
        try:
            perf = analytics.get_commitment_performance(args.commitment, weeks=args.compare_weeks)
            if args.json:
                print(json.dumps(perf, indent=2))
            else:
                if 'error' in perf:
                    print(f"❌ {perf['error']}")
                else:
                    print(f"\n📊 Performance Analysis: {perf['commitment_title']}")
                    print("=" * 70)
                    print(f"Type: {perf['commitment_type']}")
                    print(f"Current Streak: {perf['current_streak']} days")
                    print(f"Longest Streak: {perf['longest_streak']} days")
                    print(f"Overall Completion Rate: {perf['overall_completion_rate']:.1f}%")
                    print(f"\nLast {args.compare_weeks} Weeks:")
                    for week in perf['weekly_breakdown']:
                        print(f"  Week of {week['week_start']}: {week['completed']}/{week['expected']} ({week['rate']:.0f}%)")
        except Exception as e:
            print(f"❌ Error analyzing commitment: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Handle insights
    if args.insights:
        try:
            insights = analytics.get_insights(weeks=args.compare_weeks)
            if args.json:
                print(json.dumps([i.to_dict() for i in insights], indent=2))
            else:
                print("\n💡 COMMITMENT INSIGHTS")
                print("=" * 70)
                for insight in insights:
                    emoji = {'success': '✅', 'warning': '⚠️ ', 'pattern': '🔍', 'suggestion': '💭'}.get(insight.type, '•')
                    print(f"\n{emoji} {insight.message}")
                print("\n" + "=" * 70)
        except Exception as e:
            print(f"❌ Error generating insights: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Handle trend analysis
    if args.trend:
        try:
            trend = analytics.get_trend_analysis(weeks_to_compare=args.compare_weeks)
            if args.json:
                print(json.dumps(trend.to_dict(), indent=2))
            else:
                print("\n📈 TREND ANALYSIS")
                print("=" * 70)
                print(f"Analyzing {args.compare_weeks} weeks of data\n")

                # Current week
                cw = trend.current_week
                print(f"Current Week ({cw.week_start} to {cw.week_end}):")
                print(f"  Completion Rate: {cw.completion_rate:.1f}%")
                print(f"  Completed: {cw.completed_count}")
                print(f"  Missed: {cw.missed_count}")
                print(f"  Active Commitments: {cw.total_commitments}")

                # Trend
                print(f"\nTrend: {trend.trend_direction.upper()}")
                if trend.completion_rate_change >= 0:
                    print(f"  +{trend.completion_rate_change:.1f} percentage points")
                else:
                    print(f"  {trend.completion_rate_change:.1f} percentage points")

                # Streak trends
                st = trend.streak_trends
                print(f"\nStreak Statistics:")
                print(f"  Active Streaks: {st['total_active_streaks']}")
                print(f"  Average Length: {st['average_streak_length']:.1f} days")
                print(f"  Longest Current: {st['longest_current_streak']} days")
                if st['longest_streak_commitment']:
                    print(f"    ({st['longest_streak_commitment']['title']})")

                # Insights
                print(f"\nKey Insights:")
                for insight in trend.insights[:5]:  # Top 5
                    print(f"  • {insight}")

                print("\n" + "=" * 70)
        except Exception as e:
            print(f"❌ Error generating trend analysis: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Default: show current week stats
    try:
        stats = analytics.get_weekly_stats()
        if args.json:
            print(json.dumps(stats.to_dict(), indent=2))
        else:
            print("\n📊 WEEKLY STATISTICS")
            print("=" * 70)
            print(f"Week: {stats.week_start} to {stats.week_end}")
            print(f"\nOverall:")
            print(f"  Active Commitments: {stats.total_commitments}")
            print(f"  Completion Rate: {stats.completion_rate:.1f}%")
            print(f"  Completed: {stats.completed_count}")
            print(f"  Missed: {stats.missed_count}")

            print(f"\nBy Type:")
            for c_type, type_stats in stats.by_type.items():
                print(f"  {c_type.capitalize()}:")
                print(f"    Commitments: {type_stats['total_commitments']}")
                print(f"    Expected: {type_stats['expected_completions']}")
                print(f"    Completed: {type_stats['completed']}")
                print(f"    Rate: {type_stats['completion_rate']:.1f}%")

            if stats.streak_milestones:
                print(f"\n🏆 Streak Milestones Achieved:")
                for milestone in stats.streak_milestones:
                    print(f"  • {milestone['commitment_title']}: {milestone['milestone']}-day milestone!")

            print("\n" + "=" * 70)
    except Exception as e:
        print(f"❌ Error generating weekly stats: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
