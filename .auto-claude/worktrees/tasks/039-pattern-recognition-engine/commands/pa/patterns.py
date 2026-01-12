"""
Personal Assistant: Pattern Recognition Command

View, analyze, export, and visualize behavioral patterns and insights.

Usage:
    python -m commands.pa.patterns [mode] [options]

Modes:
    show      - Display all current patterns (default)
    analyze   - Run on-demand pattern analysis (no waiting for weekly review)
    export    - Export patterns to markdown file
    visualize - Show trend visualizations (text-based charts)
    list      - List patterns by category
    search    - Search patterns by topic/keyword

Options:
    --days=N        - Number of days to analyze (default: 30)
    --category=TYPE - Filter by category (task/health/habit/trend/insight)
    --confidence=N  - Minimum confidence threshold (0.0-1.0, default: 0.6)
    --compact       - Use compact display format
    --output=FILE   - Output file for export mode (default: patterns_export.md)

Examples:
    python -m commands.pa.patterns show
    python -m commands.pa.patterns analyze --days=60
    python -m commands.pa.patterns export --output=my_patterns.md
    python -m commands.pa.patterns visualize
    python -m commands.pa.patterns list --category=habit
    python -m commands.pa.patterns search sleep
"""

from datetime import datetime, timedelta
from pathlib import Path
import sys
import asyncio
from typing import Optional, List, Dict, Any, Tuple


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def parse_args(args: Optional[str] = None) -> Dict[str, Any]:
    """Parse command line arguments.

    Args:
        args: Space-separated argument string

    Returns:
        Dict with parsed arguments
    """
    parsed = {
        "mode": "show",
        "days": 30,
        "category": None,
        "confidence": 0.6,
        "compact": False,
        "output": "patterns_export.md",
        "search_term": None,
    }

    if not args:
        return parsed

    parts = args.strip().split()
    if not parts:
        return parsed

    # First argument is mode (if it's not an option)
    if parts[0] and not parts[0].startswith("--"):
        mode = parts[0].lower()
        if mode in ["show", "analyze", "export", "visualize", "list", "search"]:
            parsed["mode"] = mode
            parts = parts[1:]

    # Parse remaining options
    for part in parts:
        if part.startswith("--"):
            if "=" in part:
                key, value = part[2:].split("=", 1)
                if key == "days":
                    try:
                        parsed["days"] = int(value)
                    except ValueError:
                        pass
                elif key == "category":
                    parsed["category"] = value.lower()
                elif key == "confidence":
                    try:
                        parsed["confidence"] = float(value)
                    except ValueError:
                        pass
                elif key == "output":
                    parsed["output"] = value
            elif part == "--compact":
                parsed["compact"] = True
        elif parsed["mode"] == "search" and not part.startswith("--"):
            # For search mode, remaining args are search terms
            parsed["search_term"] = part

    return parsed


async def run_pattern_analysis(days_back: int = 30) -> Tuple[List, List, List, List, Dict]:
    """Run comprehensive pattern analysis.

    Args:
        days_back: Number of days to analyze

    Returns:
        Tuple of (task_patterns, health_correlations, habit_streaks, trends, all_insights_dict)
    """
    from Tools.pattern_recognition.data_aggregator import DataAggregator
    from Tools.pattern_recognition.time_series import (
        TaskCompletionRecord,
        HealthMetricRecord,
        ProductivityRecord,
    )
    from Tools.pattern_recognition.analyzers.task_patterns import get_all_task_patterns
    from Tools.pattern_recognition.analyzers.health_correlation import (
        analyze_sleep_duration_with_tasks,
        analyze_readiness_with_productivity,
        analyze_deep_sleep_with_focus,
        analyze_sleep_timing_with_morning_energy,
    )
    from Tools.pattern_recognition.analyzers.habit_streaks import get_all_habit_streaks
    from Tools.pattern_recognition.analyzers.trend_detector import get_all_trends
    from Tools.pattern_recognition.insight_generator import (
        generate_insights_from_all_patterns,
    )

    # Aggregate historical data
    aggregator = DataAggregator()
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days_back)

    print(f"🔍 Analyzing patterns from {start_date} to {end_date}...")

    aggregated_data = await aggregator.aggregate_data(
        start_date=start_date,
        end_date=end_date,
        days_back=days_back
    )

    # Build time series data structures
    task_records = []
    health_records = []
    productivity_records = []

    # Process task completions by day
    tasks_by_day = {}
    for task in aggregated_data.task_completions:
        day = task.completed_date
        if day not in tasks_by_day:
            tasks_by_day[day] = []
        tasks_by_day[day].append(task)

    # Create task completion time series
    for day, tasks in tasks_by_day.items():
        hourly_dist = {}  # Would need actual hour data
        task_records.append(
            TaskCompletionRecord(
                date=day,
                tasks_completed=len(tasks),
                hourly_distribution=hourly_dist,
                task_types={"work": len([t for t in tasks if t.domain == "work"])},
            )
        )

    # Create health metrics time series
    for health in aggregated_data.health_metrics:
        health_records.append(
            HealthMetricRecord(
                date=health.date,
                sleep_duration=health.total_sleep_duration,
                readiness_score=health.readiness_score,
                deep_sleep_duration=health.deep_sleep_duration,
                hrv=health.hrv_average,
                steps=health.steps,
            )
        )

    # Create productivity scores
    for task_rec in task_records:
        health = next(
            (h for h in health_records if h.date == task_rec.date),
            None
        )
        readiness = health.readiness_score if health else 70
        energy = readiness / 100.0 if readiness else 0.7
        focus = 0.8  # Default

        productivity_records.append(
            ProductivityRecord(
                date=task_rec.date,
                tasks_completed=task_rec.tasks_completed,
                focus_score=focus,
                energy_level=energy,
            )
        )

    # Run all analyzers
    print("📊 Running task pattern analysis...")
    task_patterns = get_all_task_patterns(task_records) if task_records else {}

    print("🏥 Running health correlation analysis...")
    health_correlations = []
    if task_records and health_records:
        try:
            sleep_corr = analyze_sleep_duration_with_tasks(task_records, health_records)
            if sleep_corr:
                health_correlations.append(sleep_corr)
        except Exception:
            pass

        try:
            readiness_corr = analyze_readiness_with_productivity(productivity_records, health_records)
            if readiness_corr:
                health_correlations.append(readiness_corr)
        except Exception:
            pass

    print("🔄 Running habit streak analysis...")
    habit_streaks = get_all_habit_streaks(task_records) if task_records else []

    print("📈 Running trend detection...")
    all_trends = get_all_trends(
        task_records=task_records,
        health_records=health_records,
        productivity_records=productivity_records
    )

    # Generate insights
    print("💡 Generating insights...")
    all_insights = generate_insights_from_all_patterns(
        task_patterns=list(task_patterns.values()) if isinstance(task_patterns, dict) else [],
        health_correlations=health_correlations,
        habit_streaks=habit_streaks,
        trends=all_trends if isinstance(all_trends, list) else list(all_trends.values()),
    )

    print("✅ Pattern analysis complete!\n")

    return (
        list(task_patterns.values()) if isinstance(task_patterns, dict) else [],
        health_correlations,
        habit_streaks,
        all_trends if isinstance(all_trends, list) else list(all_trends.values()),
        all_insights
    )


async def get_stored_patterns(category: Optional[str] = None, days_back: int = 30) -> Tuple[List, str]:
    """Retrieve patterns from Neo4j storage.

    Args:
        category: Filter by category (task/health/habit/trend/insight)
        days_back: Look for patterns from last N days

    Returns:
        Tuple of (patterns_list, status_message)
    """
    try:
        from Tools.pattern_recognition.pattern_queries import (
            get_patterns_by_category,
            get_recent_insights,
        )
        from Adapters.neo4j_adapter import get_adapter

        adapter = get_adapter()

        # Map category aliases
        category_map = {
            "task": "task_completion",
            "health": "health_correlation",
            "habit": "habit",
            "trend": "trend",
            "insight": "insight",
        }

        neo4j_category = category_map.get(category, category) if category else None

        if neo4j_category:
            patterns = await get_patterns_by_category(neo4j_category, adapter)
            return patterns, f"Retrieved {len(patterns)} {category} patterns from knowledge graph"
        else:
            # Get recent insights (all categories)
            patterns = await get_recent_insights(adapter, limit=20, days_back=days_back)
            return patterns, f"Retrieved {len(patterns)} recent patterns from knowledge graph"

    except ImportError:
        return [], "⚠️  Neo4j adapter not available"
    except Exception as e:
        return [], f"⚠️  Failed to retrieve patterns: {str(e)}"


def display_patterns(patterns: List, insights: List, compact: bool = False):
    """Display patterns and insights to console.

    Args:
        patterns: List of pattern objects
        insights: List of Insight objects
        compact: Use compact display format
    """
    from Tools.pattern_recognition.weekly_review_formatter import (
        format_insights_for_cli_display,
        format_insight_compact,
    )

    if not patterns and not insights:
        print("📭 No patterns found. Try running analysis first with 'analyze' mode.")
        return

    if insights:
        print("\n" + "=" * 60)
        print("💡 INSIGHTS")
        print("=" * 60 + "\n")

        if compact:
            for i, insight in enumerate(insights, 1):
                print(format_insight_compact(insight))
        else:
            formatted = format_insights_for_cli_display(insights, mode="full")
            print(formatted)

    if patterns:
        print("\n" + "=" * 60)
        print("📊 PATTERNS")
        print("=" * 60 + "\n")

        for i, pattern in enumerate(patterns, 1):
            # Display pattern based on type
            if hasattr(pattern, "summary"):
                # It's an Insight
                continue  # Already displayed above
            elif hasattr(pattern, "description"):
                # TaskCompletionPattern or similar
                conf = getattr(pattern, "confidence_score", 0.0)
                print(f"{i}. {pattern.description}")
                print(f"   Confidence: {conf:.0%}")
                if hasattr(pattern, "evidence") and pattern.evidence:
                    print(f"   Evidence: {pattern.evidence[0]}")
                print()


def visualize_trends(trends: List):
    """Visualize trends with text-based charts.

    Args:
        trends: List of Trend objects
    """
    if not trends:
        print("📭 No trends found to visualize.")
        return

    print("\n" + "=" * 60)
    print("📈 TREND VISUALIZATIONS")
    print("=" * 60 + "\n")

    for i, trend in enumerate(trends, 1):
        metric = getattr(trend, "metric_name", "Unknown Metric")
        direction = getattr(trend, "trend_direction", None)
        start_val = getattr(trend, "start_value", 0)
        end_val = getattr(trend, "end_value", 0)
        change_pct = getattr(trend, "change_percentage", 0)
        description = getattr(trend, "trend_description", "")

        print(f"{i}. {metric}")
        print(f"   {description}")
        print()

        # Create simple text chart
        chart_width = 40

        # Determine scale
        min_val = min(start_val, end_val)
        max_val = max(start_val, end_val)
        value_range = max_val - min_val if max_val > min_val else 1

        # Normalize to chart width
        start_pos = int(((start_val - min_val) / value_range) * chart_width) if value_range > 0 else 0
        end_pos = int(((end_val - min_val) / value_range) * chart_width) if value_range > 0 else 0

        # Draw chart
        print(f"   Start: {start_val:.1f}")
        print(f"   │" + "─" * start_pos + "●")

        # Draw trend line
        if end_pos > start_pos:
            # Improving trend
            print(f"   │" + " " * start_pos + "╱" + "─" * (end_pos - start_pos - 1) + "●  ({change_pct:+.1f}%)")
        elif end_pos < start_pos:
            # Declining trend
            print(f"   │" + " " * end_pos + "●" + "─" * (start_pos - end_pos - 1) + "╲  ({change_pct:+.1f}%)")
        else:
            # Plateau
            print(f"   │" + " " * start_pos + "─●  (no change)")

        print(f"   End:   {end_val:.1f}")

        # Direction indicator
        direction_emoji = {
            "improving": "📈",
            "declining": "📉",
            "plateau": "➡️",
            "volatile": "📊"
        }.get(str(direction).lower() if direction else "", "")

        if direction_emoji:
            print(f"   {direction_emoji} {str(direction).upper() if direction else 'UNKNOWN'}")

        print()


async def export_patterns_to_markdown(
    patterns: List,
    insights: List,
    output_file: str = "patterns_export.md"
):
    """Export patterns to markdown file.

    Args:
        patterns: List of pattern objects
        insights: List of Insight objects
        output_file: Output filename
    """
    from Tools.pattern_recognition.weekly_review_formatter import (
        export_insights_to_markdown_file,
    )

    project_root = Path(__file__).parent.parent.parent
    output_path = project_root / "History" / output_file

    # Ensure History directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if insights:
        # Use built-in markdown export
        export_insights_to_markdown_file(
            insights,
            str(output_path),
            title="Pattern Recognition Export",
            include_toc=True,
            include_metadata=True
        )
        print(f"✅ Exported {len(insights)} insights to {output_path}")
    else:
        # Manual export for patterns
        with open(output_path, "w") as f:
            f.write("# Pattern Recognition Export\n\n")
            f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")
            f.write("---\n\n")

            if patterns:
                f.write("## Detected Patterns\n\n")
                for i, pattern in enumerate(patterns, 1):
                    if hasattr(pattern, "description"):
                        f.write(f"### {i}. {pattern.description}\n\n")
                        conf = getattr(pattern, "confidence_score", 0.0)
                        f.write(f"- **Confidence:** {conf:.0%}\n")
                        if hasattr(pattern, "evidence") and pattern.evidence:
                            f.write(f"- **Evidence:**\n")
                            for evidence in pattern.evidence[:3]:
                                f.write(f"  - {evidence}\n")
                        f.write("\n")
            else:
                f.write("No patterns found.\n\n")

        print(f"✅ Exported patterns to {output_path}")


def list_patterns_by_category(
    task_patterns: List,
    health_correlations: List,
    habit_streaks: List,
    trends: List,
    category_filter: Optional[str] = None
):
    """List patterns organized by category.

    Args:
        task_patterns: List of TaskCompletionPattern objects
        health_correlations: List of HealthCorrelation objects
        habit_streaks: List of HabitStreak objects
        trends: List of Trend objects
        category_filter: Optional category to filter by
    """
    categories = {
        "task": (task_patterns, "💡 Task Completion Patterns"),
        "health": (health_correlations, "🏥 Health Correlations"),
        "habit": (habit_streaks, "🔄 Habit Streaks"),
        "trend": (trends, "📈 Trends"),
    }

    if category_filter and category_filter in categories:
        categories = {category_filter: categories[category_filter]}

    print("\n" + "=" * 60)
    print("📋 PATTERNS BY CATEGORY")
    print("=" * 60 + "\n")

    for cat_key, (patterns, title) in categories.items():
        if not patterns:
            continue

        print(f"\n{title} ({len(patterns)})")
        print("-" * 60)

        for i, pattern in enumerate(patterns, 1):
            if hasattr(pattern, "description"):
                desc = pattern.description
            elif hasattr(pattern, "correlation_description"):
                desc = pattern.correlation_description
            elif hasattr(pattern, "habit_name"):
                desc = f"{pattern.habit_name}: {pattern.streak_length}-day streak"
            elif hasattr(pattern, "trend_description"):
                desc = pattern.trend_description
            else:
                desc = str(pattern)

            conf = getattr(pattern, "confidence_score", 0.0)
            print(f"{i}. {desc} ({conf:.0%} confidence)")

        print()


async def search_patterns(
    search_term: str,
    patterns: List,
    insights: List
) -> Tuple[List, List]:
    """Search patterns by keyword/topic.

    Args:
        search_term: Search keyword
        patterns: List of pattern objects
        insights: List of Insight objects

    Returns:
        Tuple of (matching_patterns, matching_insights)
    """
    search_lower = search_term.lower()

    matching_patterns = []
    matching_insights = []

    # Search insights
    for insight in insights:
        if (search_lower in insight.summary.lower() or
            search_lower in insight.detailed_description.lower() or
            any(search_lower in ev.lower() for ev in insight.supporting_evidence)):
            matching_insights.append(insight)

    # Search patterns
    for pattern in patterns:
        # Check various description fields
        desc_fields = ["description", "correlation_description", "trend_description", "habit_name"]
        for field in desc_fields:
            if hasattr(pattern, field):
                value = getattr(pattern, field)
                if value and search_lower in str(value).lower():
                    matching_patterns.append(pattern)
                    break

    return matching_patterns, matching_insights


def execute(args: Optional[str] = None) -> str:
    """Execute patterns command.

    Args:
        args: Command arguments

    Returns:
        Status message
    """
    parsed = parse_args(args)
    mode = parsed["mode"]

    print(f"\n{'=' * 60}")
    print(f"📊 Pattern Recognition - {mode.upper()} mode")
    print("=" * 60 + "\n")

    try:
        if mode == "show":
            # Try to get stored patterns first, then analyze if needed
            stored_patterns, status_msg = asyncio.run(
                get_stored_patterns(
                    category=parsed["category"],
                    days_back=parsed["days"]
                )
            )

            if stored_patterns:
                print(status_msg + "\n")
                display_patterns(stored_patterns, stored_patterns, compact=parsed["compact"])
            else:
                print("No stored patterns found. Running fresh analysis...\n")
                task_p, health_c, habit_s, trends, insights = asyncio.run(
                    run_pattern_analysis(parsed["days"])
                )
                display_patterns(
                    task_p + health_c + habit_s + trends,
                    insights,
                    compact=parsed["compact"]
                )

        elif mode == "analyze":
            # Run fresh analysis
            task_p, health_c, habit_s, trends, insights = asyncio.run(
                run_pattern_analysis(parsed["days"])
            )

            # Filter by confidence
            if parsed["confidence"] > 0:
                from Tools.pattern_recognition.insight_generator import filter_insights_by_confidence
                insights = filter_insights_by_confidence(insights, parsed["confidence"])

            display_patterns(
                task_p + health_c + habit_s + trends,
                insights,
                compact=parsed["compact"]
            )

        elif mode == "export":
            # Run analysis and export
            task_p, health_c, habit_s, trends, insights = asyncio.run(
                run_pattern_analysis(parsed["days"])
            )

            asyncio.run(export_patterns_to_markdown(
                task_p + health_c + habit_s + trends,
                insights,
                parsed["output"]
            ))

        elif mode == "visualize":
            # Run analysis and visualize trends
            task_p, health_c, habit_s, trends, insights = asyncio.run(
                run_pattern_analysis(parsed["days"])
            )

            visualize_trends(trends)

        elif mode == "list":
            # Run analysis and list by category
            task_p, health_c, habit_s, trends, insights = asyncio.run(
                run_pattern_analysis(parsed["days"])
            )

            list_patterns_by_category(
                task_p, health_c, habit_s, trends,
                category_filter=parsed["category"]
            )

        elif mode == "search":
            if not parsed["search_term"]:
                print("❌ Search mode requires a search term")
                print("Usage: python -m commands.pa.patterns search <term>")
                return "Error: missing search term"

            # Run analysis and search
            task_p, health_c, habit_s, trends, insights = asyncio.run(
                run_pattern_analysis(parsed["days"])
            )

            matching_p, matching_i = asyncio.run(search_patterns(
                parsed["search_term"],
                task_p + health_c + habit_s + trends,
                insights
            ))

            print(f"🔍 Search results for '{parsed['search_term']}':\n")
            print(f"Found {len(matching_p)} patterns and {len(matching_i)} insights\n")

            display_patterns(matching_p, matching_i, compact=parsed["compact"])

        print("\n" + "=" * 60)
        print("✅ Done!")
        print("=" * 60)

        return f"Pattern recognition {mode} completed"

    except ImportError as e:
        error_msg = f"⚠️  Required modules not available: {e}"
        print(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return error_msg


def main():
    """CLI entry point."""
    args = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    execute(args)


if __name__ == "__main__":
    main()
