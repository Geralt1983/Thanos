#!/usr/bin/env python3
"""
Example demonstrating pattern-based priority ranking in BriefingEngine.

This example shows how the BriefingEngine uses learned patterns from task
completions to intelligently boost priority scores for tasks that are typically
completed on certain days or times.
"""

import os
import sys
import json
from datetime import datetime, timedelta, date
from pathlib import Path

# Add Tools to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from Tools.briefing_engine import BriefingEngine
from Tools.pattern_analyzer import PatternAnalyzer


def setup_test_environment():
    """Create test State directory with sample data."""
    state_dir = Path("./State_pattern_example")
    state_dir.mkdir(exist_ok=True)

    # Create Commitments.md
    commitments_content = """# Commitments

## Active
- [ ] Complete weekly expense reports (deadline: 2026-01-17)
- [ ] Design new authentication feature (deadline: 2026-01-13)
- [ ] Team meeting prep (deadline: 2026-01-12)
- [ ] Code review for PR #234 (deadline: 2026-01-14)
- [ ] Update project documentation (deadline: 2026-01-15)
"""
    (state_dir / "Commitments.md").write_text(commitments_content)

    # Create ThisWeek.md
    this_week_content = """# This Week

## Goals
- Finish authentication feature
- Clear expense backlog
- Update all documentation

## Tasks
- [ ] Review and submit expense reports
- [ ] Update API documentation
- [ ] Organize email inbox
- [ ] Weekly team sync
"""
    (state_dir / "ThisWeek.md").write_text(this_week_content)

    # Create CurrentFocus.md
    current_focus_content = """# Current Focus

## Priorities
- Authentication feature design
- Clear administrative backlog

## Notes
Working on authentication system this week.
"""
    (state_dir / "CurrentFocus.md").write_text(current_focus_content)

    # Create realistic pattern data (20 days of completions)
    create_pattern_data(state_dir)

    return state_dir


def create_pattern_data(state_dir: Path):
    """Create realistic pattern data showing day-of-week and category patterns."""
    completions = []
    base_date = datetime.now() - timedelta(days=25)

    for i in range(25):
        current_date = base_date + timedelta(days=i)
        day_of_week = current_date.strftime("%A")

        # Friday admin pattern (strong)
        if day_of_week == "Friday":
            completions.extend([
                {
                    "task_title": "Weekly expense report",
                    "task_category": "admin",
                    "completion_time": "14:30",
                    "completion_date": current_date.strftime("%Y-%m-%d"),
                    "day_of_week": day_of_week,
                    "time_of_day": "afternoon"
                },
                {
                    "task_title": "Update timesheet",
                    "task_category": "admin",
                    "completion_time": "15:00",
                    "completion_date": current_date.strftime("%Y-%m-%d"),
                    "day_of_week": day_of_week,
                    "time_of_day": "afternoon"
                },
                {
                    "task_title": "Organize files",
                    "task_category": "admin",
                    "completion_time": "16:00",
                    "completion_date": current_date.strftime("%Y-%m-%d"),
                    "day_of_week": day_of_week,
                    "time_of_day": "afternoon"
                }
            ])

        # Monday lighter tasks pattern
        if day_of_week == "Monday":
            completions.extend([
                {
                    "task_title": "Organize inbox",
                    "task_category": "admin",
                    "completion_time": "09:30",
                    "completion_date": current_date.strftime("%Y-%m-%d"),
                    "day_of_week": day_of_week,
                    "time_of_day": "morning"
                },
                {
                    "task_title": "Review calendar",
                    "task_category": "admin",
                    "completion_time": "10:00",
                    "completion_date": current_date.strftime("%Y-%m-%d"),
                    "day_of_week": day_of_week,
                    "time_of_day": "morning"
                }
            ])

        # Tuesday-Thursday work tasks (deep work)
        if day_of_week in ["Tuesday", "Wednesday", "Thursday"]:
            completions.extend([
                {
                    "task_title": "Code review",
                    "task_category": "work",
                    "completion_time": "10:00",
                    "completion_date": current_date.strftime("%Y-%m-%d"),
                    "day_of_week": day_of_week,
                    "time_of_day": "morning"
                },
                {
                    "task_title": "Design feature",
                    "task_category": "work",
                    "completion_time": "14:00",
                    "completion_date": current_date.strftime("%Y-%m-%d"),
                    "day_of_week": day_of_week,
                    "time_of_day": "afternoon"
                }
            ])

    patterns_data = {
        "task_completions": completions,
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "version": "1.0"
        }
    }

    (state_dir / "BriefingPatterns.json").write_text(json.dumps(patterns_data, indent=2))


def print_section_header(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def print_priorities(priorities: list, title: str = "Top Priorities"):
    """Print prioritized tasks in a formatted way."""
    print(f"\n{title}:")
    print("-" * 80)
    for i, item in enumerate(priorities, 1):
        print(f"{i}. {item['title']}")
        print(f"   Priority Score: {item['priority_score']:.1f}")
        print(f"   Urgency: {item['urgency_level'].upper()}")
        print(f"   Reason: {item['priority_reason']}")
        print()


def example_1_patterns_disabled():
    """Example 1: Priority ranking WITHOUT pattern learning (baseline)."""
    print_section_header("Example 1: Priority Ranking WITHOUT Pattern Learning (Baseline)")

    state_dir = setup_test_environment()

    # Create engine with patterns DISABLED
    config = {
        "patterns": {
            "enabled": False
        }
    }
    engine = BriefingEngine(state_dir=str(state_dir), config=config)

    # Mock today as Friday
    engine.today = date(2026, 1, 16)  # Friday

    print(f"Today: Friday, January 16, 2026")
    print(f"Pattern Learning: DISABLED\n")

    # Get top priorities
    top_priorities = engine.get_top_priorities(limit=5)

    print_priorities(top_priorities)

    # Clean up
    import shutil
    shutil.rmtree(state_dir)


def example_2_patterns_enabled_friday():
    """Example 2: Friday briefing WITH pattern learning (admin tasks boosted)."""
    print_section_header("Example 2: Friday Briefing WITH Pattern Learning (Admin Tasks Boosted)")

    state_dir = setup_test_environment()

    # Create engine with patterns ENABLED
    config = {
        "patterns": {
            "enabled": True,
            "influence_level": "medium"
        }
    }
    engine = BriefingEngine(state_dir=str(state_dir), config=config)

    # Mock today as Friday
    engine.today = date(2026, 1, 16)  # Friday

    print(f"Today: Friday, January 16, 2026")
    print(f"Pattern Learning: ENABLED (influence_level: medium)\n")

    # Show identified patterns first
    patterns = engine.pattern_analyzer.identify_patterns()
    if patterns.get("has_sufficient_data"):
        print("Identified Patterns:")
        for insight in patterns.get("insights", [])[:3]:
            print(f"  • {insight}")
        print()

    # Get top priorities
    top_priorities = engine.get_top_priorities(limit=5)

    print_priorities(top_priorities)

    print("📊 Observation:")
    print("   Admin tasks like 'expense reports' get a pattern boost on Fridays")
    print("   because historical data shows you typically complete admin work on Fridays.")

    # Clean up
    import shutil
    shutil.rmtree(state_dir)


def example_3_patterns_enabled_monday():
    """Example 3: Monday briefing WITH pattern learning (lighter tasks)."""
    print_section_header("Example 3: Monday Briefing WITH Pattern Learning (Lighter Tasks)")

    state_dir = setup_test_environment()

    # Create engine with patterns ENABLED
    config = {
        "patterns": {
            "enabled": True,
            "influence_level": "medium"
        }
    }
    engine = BriefingEngine(state_dir=str(state_dir), config=config)

    # Mock today as Monday
    engine.today = date(2026, 1, 12)  # Monday

    print(f"Today: Monday, January 12, 2026")
    print(f"Pattern Learning: ENABLED (influence_level: medium)\n")

    # Get top priorities
    top_priorities = engine.get_top_priorities(limit=5)

    print_priorities(top_priorities)

    print("📊 Observation:")
    print("   On Mondays, pattern learning accounts for typical energy dips.")
    print("   Admin tasks may get a small boost if patterns show you typically")
    print("   ease into the week with lighter tasks.")

    # Clean up
    import shutil
    shutil.rmtree(state_dir)


def example_4_influence_levels():
    """Example 4: Comparing different pattern influence levels."""
    print_section_header("Example 4: Comparing Pattern Influence Levels")

    state_dir = setup_test_environment()

    influence_levels = ["low", "medium", "high"]

    for level in influence_levels:
        print(f"\n--- Influence Level: {level.upper()} ---\n")

        config = {
            "patterns": {
                "enabled": True,
                "influence_level": level
            }
        }
        engine = BriefingEngine(state_dir=str(state_dir), config=config)
        engine.today = date(2026, 1, 16)  # Friday

        # Get just admin task for comparison
        all_priorities = engine.rank_priorities()
        admin_task = next((p for p in all_priorities if "expense" in p["title"].lower()), None)

        if admin_task:
            print(f"Task: {admin_task['title']}")
            print(f"Priority Score: {admin_task['priority_score']:.1f}")
            print(f"Reason: {admin_task['priority_reason']}\n")

    print("📊 Observation:")
    print("   - Low influence: Pattern boost ≤ 5 points (subtle)")
    print("   - Medium influence: Pattern boost ≤ 10 points (balanced)")
    print("   - High influence: Pattern boost ≤ 15 points (stronger)")
    print("   Even with high influence, deadline urgency still takes priority!")

    # Clean up
    import shutil
    shutil.rmtree(state_dir)


def example_5_pattern_doesnt_override_urgency():
    """Example 5: Patterns are subtle - they don't override deadline urgency."""
    print_section_header("Example 5: Pattern Influence is Subtle, Not Override")

    state_dir = setup_test_environment()

    config = {
        "patterns": {
            "enabled": True,
            "influence_level": "high"  # Even with HIGH influence
        }
    }
    engine = BriefingEngine(state_dir=str(state_dir), config=config)
    engine.today = date(2026, 1, 16)  # Friday

    print(f"Today: Friday, January 16, 2026")
    print(f"Pattern Learning: ENABLED (influence_level: HIGH)\n")

    # Get all priorities
    all_priorities = engine.rank_priorities()

    # Find urgent task and pattern-boosted task
    design_task = next((p for p in all_priorities if "Design" in p["title"]), None)
    expense_task = next((p for p in all_priorities if "expense" in p["title"].lower()), None)

    print("Comparing two tasks:\n")
    print(f"1. {design_task['title']}")
    print(f"   Deadline: {design_task.get('deadline', 'None')}")
    print(f"   Priority Score: {design_task['priority_score']:.1f}")
    print(f"   Urgency: {design_task['urgency_level']}")
    print(f"   Reason: {design_task['priority_reason']}\n")

    print(f"2. {expense_task['title']}")
    print(f"   Deadline: {expense_task.get('deadline', 'None')}")
    print(f"   Priority Score: {expense_task['priority_score']:.1f}")
    print(f"   Urgency: {expense_task['urgency_level']}")
    print(f"   Reason: {expense_task['priority_reason']}\n")

    print("📊 Observation:")
    print("   Even though it's Friday (admin task pattern day) and influence is HIGH,")
    print("   the urgent design task (due Monday) still scores higher than the")
    print("   expense report (due later). Patterns provide subtle boosts, not overrides!")

    # Clean up
    import shutil
    shutil.rmtree(state_dir)


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("  PATTERN-BASED PRIORITY RANKING EXAMPLES")
    print("  Demonstrating how BriefingEngine uses learned patterns")
    print("=" * 80)

    try:
        example_1_patterns_disabled()
        example_2_patterns_enabled_friday()
        example_3_patterns_enabled_monday()
        example_4_influence_levels()
        example_5_pattern_doesnt_override_urgency()

        print("\n" + "=" * 80)
        print("  All Examples Complete!")
        print("=" * 80)
        print("\nKey Takeaways:")
        print("  1. Pattern learning requires 14+ days of completion data")
        print("  2. Friday admin tasks get boosted based on historical patterns")
        print("  3. Monday briefings account for typical energy patterns")
        print("  4. Pattern influence is configurable (low/medium/high)")
        print("  5. Patterns provide subtle boosts - they NEVER override deadline urgency")
        print("  6. Patterns can be completely disabled in config")
        print()

    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user.")
    except Exception as e:
        print(f"\n\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
