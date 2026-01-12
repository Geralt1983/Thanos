"""
Example usage of PatternAnalyzer for tracking task completion patterns.

This script demonstrates how to:
1. Record task completions
2. Retrieve completion history
3. Identify patterns (requires 14+ days of data)
4. Get recommendations based on context
"""

import sys
import os
from datetime import datetime, date, timedelta

# Add Tools to path
sys.path.insert(0, os.path.dirname(__file__))

from Tools.pattern_analyzer import PatternAnalyzer


def print_section(title):
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)


def example_1_basic_usage():
    """Example 1: Basic task completion recording."""
    print_section("Example 1: Basic Task Completion Recording")

    analyzer = PatternAnalyzer()

    # Record some task completions
    tasks = [
        ("Review PR for authentication system", "admin"),
        ("Design new API architecture", "deep_work"),
        ("Send weekly status report", "admin"),
        ("Call mom about weekend plans", "personal"),
        ("Implement user dashboard", "deep_work")
    ]

    print("\nRecording task completions...")
    for task_title, category in tasks:
        result = analyzer.record_task_completion(task_title, category)
        if result:
            print(f"✓ Recorded: {task_title} ({category})")

    print(f"\nTotal completions recorded: {len(analyzer.patterns_data['task_completions'])}")


def example_2_category_inference():
    """Example 2: Automatic category inference."""
    print_section("Example 2: Automatic Category Inference")

    analyzer = PatternAnalyzer()

    # Record tasks without specifying category
    tasks = [
        "Design database schema for new feature",
        "Schedule team standup meeting",
        "Pay utility bills",
        "Implement caching layer",
        "Send expense report"
    ]

    print("\nRecording tasks with automatic category inference...")
    for task_title in tasks:
        result = analyzer.record_task_completion(task_title)
        if result:
            # Get the last recorded completion
            completion = analyzer.patterns_data["task_completions"][0]
            inferred_category = completion["task_category"]
            print(f"✓ '{task_title}'")
            print(f"  → Inferred category: {inferred_category}")


def example_3_historical_data():
    """Example 3: Creating historical data with patterns."""
    print_section("Example 3: Creating Historical Data with Patterns")

    analyzer = PatternAnalyzer()

    print("\nCreating 4 weeks of task completion history...")
    print("Pattern: Admin tasks on Fridays, Deep work Mon-Thu, Personal on weekends")

    tasks_created = 0
    for day_offset in range(28):  # 4 weeks
        completion_date = analyzer.today - timedelta(days=day_offset)
        day_name = completion_date.strftime("%A")

        # Different patterns for different days
        if day_name == "Friday":
            # Admin tasks on Friday
            hour = 14  # Afternoon
            analyzer.record_task_completion(
                f"Weekly status report {day_offset}",
                "admin",
                completion_time=datetime.combine(completion_date, datetime.min.time().replace(hour=hour)),
                completion_date=completion_date
            )
            tasks_created += 1

        elif day_name in ["Saturday", "Sunday"]:
            # Personal tasks on weekends
            hour = 10  # Morning
            analyzer.record_task_completion(
                f"Personal errands {day_offset}",
                "personal",
                completion_time=datetime.combine(completion_date, datetime.min.time().replace(hour=hour)),
                completion_date=completion_date
            )
            tasks_created += 1

        else:
            # Deep work Mon-Thu
            hour = 9  # Morning
            analyzer.record_task_completion(
                f"Feature implementation {day_offset}",
                "deep_work",
                completion_time=datetime.combine(completion_date, datetime.min.time().replace(hour=hour)),
                completion_date=completion_date
            )
            tasks_created += 1

    print(f"✓ Created {tasks_created} task completions over 4 weeks")


def example_4_retrieving_completions():
    """Example 4: Retrieving completion history."""
    print_section("Example 4: Retrieving Completion History")

    analyzer = PatternAnalyzer()

    # Create some sample data
    for i in range(5):
        analyzer.record_task_completion(f"Task {i}", "admin" if i % 2 == 0 else "deep_work")

    # Get all recent completions
    print("\nAll completions (last 30 days):")
    completions = analyzer.get_completions(days=30)
    for i, completion in enumerate(completions[:5], 1):  # Show first 5
        print(f"  {i}. {completion['task_title']}")
        print(f"     Category: {completion['task_category']}")
        print(f"     Day: {completion['day_of_week']}, Time: {completion['time_of_day']}")

    # Filter by category
    print("\nAdmin tasks only:")
    admin_completions = analyzer.get_completions(days=30, category="admin")
    for i, completion in enumerate(admin_completions, 1):
        print(f"  {i}. {completion['task_title']}")


def example_5_pattern_identification():
    """Example 5: Pattern identification (requires 14+ days)."""
    print_section("Example 5: Pattern Identification")

    analyzer = PatternAnalyzer()

    # Create 21 days of data with clear patterns
    print("\nCreating 3 weeks of data with clear patterns...")

    for day_offset in range(21):
        completion_date = analyzer.today - timedelta(days=day_offset)
        day_name = completion_date.strftime("%A")

        if day_name == "Friday":
            # 80% admin tasks on Friday
            analyzer.record_task_completion(
                f"Admin task {day_offset}",
                "admin",
                completion_time=datetime.combine(completion_date, datetime.min.time().replace(hour=14)),
                completion_date=completion_date
            )
        else:
            # Deep work on other weekdays
            analyzer.record_task_completion(
                f"Deep work task {day_offset}",
                "deep_work",
                completion_time=datetime.combine(completion_date, datetime.min.time().replace(hour=9)),
                completion_date=completion_date
            )

    # Identify patterns
    print("\nIdentifying patterns...")
    patterns = analyzer.identify_patterns(min_days=14)

    if patterns["has_sufficient_data"]:
        print(f"\n✓ Sufficient data: {patterns['sample_size']} days, {patterns['total_completions']} completions")

        # Day of week patterns
        print("\nDay of Week Patterns:")
        for day, data in patterns["day_of_week_patterns"].items():
            print(f"  {day}: {data['total_completions']} completions")
            if data["dominant_category"]:
                print(f"    → Dominant: {data['dominant_category']} ({data['dominant_percentage']:.0f}%)")

        # Time of day patterns
        print("\nTime of Day Patterns:")
        for time_period, data in patterns["time_of_day_patterns"].items():
            print(f"  {time_period}: {data['total_completions']} completions")
            if data["dominant_category"]:
                print(f"    → Dominant: {data['dominant_category']} ({data['dominant_percentage']:.0f}%)")

        # Category patterns
        print("\nCategory Patterns:")
        for category, data in patterns["category_patterns"].items():
            print(f"  {category}: {data['total_completions']} completions ({data['percentage_of_total']}%)")
            if data["preferred_time_of_day"]:
                print(f"    → Preferred time: {data['preferred_time_of_day']}")

        # Insights
        print("\nInsights:")
        for insight in patterns["insights"]:
            print(f"  • {insight}")

    else:
        print(f"\n⚠ {patterns['message']}")


def example_6_recommendations():
    """Example 6: Getting recommendations based on context."""
    print_section("Example 6: Context-Based Recommendations")

    analyzer = PatternAnalyzer()

    # Create strong Friday admin pattern
    print("\nCreating data with Friday admin pattern...")
    for week in range(4):
        # Friday admin tasks
        friday = analyzer.today - timedelta(days=analyzer.today.weekday() - 4 + 7 * week)
        if friday <= analyzer.today:
            for hour in [9, 14, 16]:
                analyzer.record_task_completion(
                    f"Admin task week {week} hour {hour}",
                    "admin",
                    completion_time=datetime.combine(friday, datetime.min.time().replace(hour=hour)),
                    completion_date=friday
                )

    # Fill in other days with deep work
    for day_offset in range(1, 28):
        completion_date = analyzer.today - timedelta(days=day_offset)
        if completion_date.strftime("%A") != "Friday":
            analyzer.record_task_completion(
                f"Deep work task {day_offset}",
                "deep_work",
                completion_time=datetime.combine(completion_date, datetime.min.time().replace(hour=10)),
                completion_date=completion_date
            )

    # Get recommendations for Friday
    print("\nGetting recommendations for Friday afternoon...")
    recommendations = analyzer.get_recommendations_for_context(
        current_day="Friday",
        current_time_of_day="afternoon"
    )

    if recommendations["has_recommendations"]:
        print(f"\n✓ Found {len(recommendations['recommendations'])} recommendations")
        print(f"Context: {recommendations['current_context']['day']}, {recommendations['current_context']['time_of_day']}")
        print("\nRecommendations:")
        for rec in recommendations["recommendations"]:
            print(f"  • {rec['reason']}")
            print(f"    Suggested category: {rec['category']}")
            print(f"    Confidence: {rec['confidence']:.0f}%")
    else:
        print(f"\n⚠ {recommendations['reason']}")

    # Try Monday morning
    print("\nGetting recommendations for Monday morning...")
    recommendations = analyzer.get_recommendations_for_context(
        current_day="Monday",
        current_time_of_day="morning"
    )

    if recommendations["has_recommendations"]:
        print(f"\n✓ Found {len(recommendations['recommendations'])} recommendations")
        for rec in recommendations["recommendations"]:
            print(f"  • {rec['reason']}")
    else:
        print(f"\n⚠ No specific recommendations for this context")


def example_7_data_persistence():
    """Example 7: Data persistence across sessions."""
    print_section("Example 7: Data Persistence")

    # First analyzer instance
    analyzer1 = PatternAnalyzer()
    initial_count = len(analyzer1.patterns_data["task_completions"])
    print(f"\nInitial task completions: {initial_count}")

    # Record a task
    print("\nRecording a new task...")
    analyzer1.record_task_completion("Test persistence task", "admin")
    print(f"Completions after recording: {len(analyzer1.patterns_data['task_completions'])}")

    # Create new analyzer instance (simulating new session)
    print("\nCreating new analyzer instance (simulating new session)...")
    analyzer2 = PatternAnalyzer()
    loaded_count = len(analyzer2.patterns_data["task_completions"])
    print(f"Loaded completions: {loaded_count}")

    if loaded_count > initial_count:
        print("✓ Data persisted successfully!")
        print(f"\nMost recent task: {analyzer2.patterns_data['task_completions'][0]['task_title']}")
    else:
        print("⚠ No new data found")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("  PatternAnalyzer - Task Completion Pattern Tracking")
    print("=" * 70)

    examples = [
        ("Basic Usage", example_1_basic_usage),
        ("Category Inference", example_2_category_inference),
        ("Historical Data", example_3_historical_data),
        ("Retrieving Completions", example_4_retrieving_completions),
        ("Pattern Identification", example_5_pattern_identification),
        ("Recommendations", example_6_recommendations),
        ("Data Persistence", example_7_data_persistence)
    ]

    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")

    print("\nRunning all examples...\n")

    for name, example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\n❌ Error in {name}: {e}")

    print("\n" + "=" * 70)
    print("  All examples completed!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
