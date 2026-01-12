#!/usr/bin/env python3
"""
Example script demonstrating weekly pattern summary functionality.

This script shows how the BriefingEngine generates weekly pattern insights
for Sunday evening briefings, including:
- Most productive days and times
- Category breakdown
- Pattern changes from historical data
- Optimization suggestions for next week
"""

import os
import sys
import json
from datetime import datetime, date, timedelta
from pathlib import Path

# Add parent directory to path to import BriefingEngine
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Tools.briefing_engine import BriefingEngine
from Tools.pattern_analyzer import PatternAnalyzer


def create_sample_pattern_data():
    """Create sample pattern data for demonstration."""
    print("📝 Creating sample pattern data for the past 4 weeks...")

    pattern_analyzer = PatternAnalyzer()

    # Get date range for the past 4 weeks
    today = date.today()
    days_since_sunday = (today.weekday() + 1) % 7
    week_start = today - timedelta(days=days_since_sunday + 21)  # Go back 3 more weeks

    # Create realistic task completion patterns
    patterns = {
        "Monday": ["work", "meetings", "planning"],
        "Tuesday": ["work", "deep_work", "development"],
        "Wednesday": ["work", "deep_work", "development"],
        "Thursday": ["work", "admin", "meetings"],
        "Friday": ["work", "admin", "review"],
        "Saturday": ["personal", "household", "health"],
        "Sunday": ["personal", "learning", "planning"]
    }

    time_patterns = {
        "morning": 0.4,     # 40% of tasks in morning
        "afternoon": 0.35,  # 35% in afternoon
        "evening": 0.25     # 25% in evening
    }

    tasks_created = 0
    for day_offset in range(28):  # 4 weeks
        task_date = week_start + timedelta(days=day_offset)
        day_name = task_date.strftime("%A")

        # Number of tasks varies by day (more on weekdays)
        if day_name in ["Saturday", "Sunday"]:
            num_tasks = 2
        else:
            num_tasks = 4

        # Categories for this day
        day_categories = patterns.get(day_name, ["general"])

        for i in range(num_tasks):
            # Pick category
            category = day_categories[i % len(day_categories)]

            # Pick time of day based on probabilities
            import random
            rand = random.random()
            if rand < time_patterns["morning"]:
                time_period = "morning"
                hour = random.randint(8, 11)
            elif rand < time_patterns["morning"] + time_patterns["afternoon"]:
                time_period = "afternoon"
                hour = random.randint(12, 16)
            else:
                time_period = "evening"
                hour = random.randint(17, 20)

            task_titles = {
                "work": ["Review pull request", "Attend standup", "Deploy feature", "Code review"],
                "meetings": ["Team sync", "1-on-1 meeting", "Planning session", "Retrospective"],
                "planning": ["Weekly planning", "Sprint planning", "Roadmap review", "Set priorities"],
                "deep_work": ["Implement feature", "Design system", "Refactor code", "Write documentation"],
                "development": ["Fix bug", "Add tests", "Update API", "Optimize query"],
                "admin": ["Expense report", "Timesheet", "Email cleanup", "Calendar review"],
                "review": ["Code review", "Week review", "Performance review", "Project status"],
                "personal": ["Exercise", "Read book", "Call friend", "Meal prep"],
                "household": ["Groceries", "Cleaning", "Laundry", "Bills"],
                "health": ["Workout", "Meditation", "Doctor appointment", "Meal planning"],
                "learning": ["Online course", "Read article", "Practice skill", "Watch tutorial"]
            }

            title = random.choice(task_titles.get(category, ["General task"]))

            # Record completion
            pattern_analyzer.record_task_completion(
                task_title=title,
                task_category=category,
                completion_time=datetime(task_date.year, task_date.month, task_date.day, hour, 0),
                completion_date=task_date
            )
            tasks_created += 1

    print(f"✅ Created {tasks_created} task completions over 4 weeks\n")


def example_1_basic_weekly_summary():
    """Example 1: Basic weekly pattern summary."""
    print("=" * 80)
    print("EXAMPLE 1: Basic Weekly Pattern Summary")
    print("=" * 80)
    print()

    config = {
        "patterns": {
            "enabled": True,
            "weekly_review": {
                "enabled": True,
                "comparison_weeks": 2
            }
        }
    }

    engine = BriefingEngine(config=config)

    # Get weekly summary
    summary = engine.get_weekly_pattern_summary()

    if summary["has_data"]:
        print(f"📊 Weekly Summary for {summary['week_start']} to {summary['week_end']}")
        print(f"   Total completions: {summary['total_completions']}")
        print()

        if summary.get("most_productive_day"):
            print(f"🌟 Most productive day: {summary['most_productive_day']['day']} "
                  f"({summary['most_productive_day']['count']} tasks)")

        if summary.get("most_productive_time"):
            print(f"⏰ Most productive time: {summary['most_productive_time']['time']} "
                  f"({summary['most_productive_time']['count']} tasks)")

        print()
        print("💡 Insights:")
        for insight in summary.get("insights", []):
            print(f"   - {insight}")

        print()
        print("🚀 Optimizations:")
        for opt in summary.get("optimizations", []):
            print(f"   - {opt['suggestion']}")
    else:
        print(f"ℹ️  {summary.get('reason', 'No data available')}")

    print()


def example_2_category_breakdown():
    """Example 2: Detailed category breakdown."""
    print("=" * 80)
    print("EXAMPLE 2: Category Breakdown Analysis")
    print("=" * 80)
    print()

    config = {"patterns": {"enabled": True}}
    engine = BriefingEngine(config=config)

    summary = engine.get_weekly_pattern_summary()

    if summary["has_data"] and summary.get("category_breakdown"):
        print("🎯 Task Category Distribution:")
        print()

        for category, data in summary["category_breakdown"].items():
            bar_length = int(data["percentage"] / 2)  # Scale to fit console
            bar = "█" * bar_length
            print(f"   {category:15s} {bar} {data['percentage']:5.1f}% ({data['count']} tasks)")

        print()
    else:
        print("ℹ️  No category data available")

    print()


def example_3_pattern_changes():
    """Example 3: Identifying pattern changes."""
    print("=" * 80)
    print("EXAMPLE 3: Pattern Changes Detection")
    print("=" * 80)
    print()

    config = {"patterns": {"enabled": True}}
    engine = BriefingEngine(config=config)

    summary = engine.get_weekly_pattern_summary()

    if summary["has_data"]:
        pattern_changes = summary.get("pattern_changes", [])

        if pattern_changes:
            print("🔄 Pattern Changes Detected:")
            print()

            for change in pattern_changes:
                print(f"   Type: {change['type']}")
                print(f"   Description: {change['description']}")
                print()
        else:
            print("✅ No significant pattern changes - your productivity patterns are consistent")
            print()
    else:
        print("ℹ️  Insufficient data for pattern change detection")
        print()


def example_4_sunday_evening_briefing():
    """Example 4: Sunday evening briefing with weekly review."""
    print("=" * 80)
    print("EXAMPLE 4: Sunday Evening Briefing with Weekly Review")
    print("=" * 80)
    print()

    # Check if we have Jinja2 for rendering
    try:
        import jinja2
        has_jinja = True
    except ImportError:
        has_jinja = False
        print("⚠️  Jinja2 not available - showing data structure instead of rendered template")
        print()

    config = {
        "patterns": {
            "enabled": True,
            "weekly_review": {
                "enabled": True,
                "comparison_weeks": 2
            }
        }
    }

    engine = BriefingEngine(config=config)

    # Get context and force it to be Sunday
    context = engine.gather_context()
    context["day_of_week"] = "Sunday"
    context["is_weekend"] = True

    if has_jinja:
        try:
            # Render Sunday evening briefing (will include weekly review)
            briefing = engine.render_briefing(
                briefing_type="evening",
                context=context
            )

            print("📋 Rendered Sunday Evening Briefing:")
            print()
            print(briefing)
        except Exception as e:
            print(f"❌ Error rendering briefing: {e}")
            print()
            # Fall back to showing template data
            template_data = engine._prepare_template_data(context, "evening")
            if "weekly_review" in template_data:
                print("📊 Weekly Review Data:")
                print(json.dumps(template_data["weekly_review"], indent=2))
    else:
        # Show template data structure
        template_data = engine._prepare_template_data(context, "evening")

        if "weekly_review" in template_data:
            print("📊 Weekly Review Data Structure:")
            print()
            print(json.dumps(template_data["weekly_review"], indent=2, default=str))
            print()
        else:
            print("ℹ️  Weekly review not included in template data")

    print()


def example_5_config_control():
    """Example 5: Controlling weekly review via config."""
    print("=" * 80)
    print("EXAMPLE 5: Config Control of Weekly Review")
    print("=" * 80)
    print()

    # Scenario 1: Weekly review enabled
    print("Scenario 1: Weekly review ENABLED")
    config_enabled = {
        "patterns": {
            "enabled": True,
            "weekly_review": {
                "enabled": True
            }
        }
    }

    engine = BriefingEngine(config=config_enabled)
    context = engine.gather_context()
    context["day_of_week"] = "Sunday"

    template_data = engine._prepare_template_data(context, "evening")
    has_weekly_review = "weekly_review" in template_data and template_data["weekly_review"]

    print(f"   Weekly review in template: {has_weekly_review}")
    print()

    # Scenario 2: Weekly review disabled
    print("Scenario 2: Weekly review DISABLED")
    config_disabled = {
        "patterns": {
            "enabled": True,
            "weekly_review": {
                "enabled": False
            }
        }
    }

    engine = BriefingEngine(config=config_disabled)
    context = engine.gather_context()
    context["day_of_week"] = "Sunday"

    template_data = engine._prepare_template_data(context, "evening")
    has_weekly_review = "weekly_review" in template_data and template_data["weekly_review"]

    print(f"   Weekly review in template: {has_weekly_review}")
    print()

    # Scenario 3: Non-Sunday evening
    print("Scenario 3: Monday evening (non-Sunday)")
    engine = BriefingEngine(config=config_enabled)
    context = engine.gather_context()
    context["day_of_week"] = "Monday"

    template_data = engine._prepare_template_data(context, "evening")
    has_weekly_review = "weekly_review" in template_data and template_data["weekly_review"]

    print(f"   Weekly review in template: {has_weekly_review}")
    print()


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + " " * 20 + "WEEKLY PATTERN SUMMARY EXAMPLES" + " " * 26 + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "═" * 78 + "╝")
    print("\n")

    # Create sample data first
    create_sample_pattern_data()

    # Run examples
    example_1_basic_weekly_summary()
    example_2_category_breakdown()
    example_3_pattern_changes()
    example_4_sunday_evening_briefing()
    example_5_config_control()

    print("=" * 80)
    print("✅ All examples completed!")
    print("=" * 80)
    print()
    print("💡 Tip: Weekly reviews help you understand your productivity patterns")
    print("   and optimize your workflow for the upcoming week.")
    print()


if __name__ == "__main__":
    main()
