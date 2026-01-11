#!/usr/bin/env python3
"""
Example script demonstrating the priority ranking functionality.

This script shows how the BriefingEngine ranks tasks based on multiple factors:
- Deadline urgency
- Day of week (weekend vs weekday)
- Task category (work vs personal)
- Energy levels
"""

import sys
import os
from datetime import date, timedelta

# Add Tools to path
sys.path.insert(0, os.path.dirname(__file__))

from Tools.briefing_engine import BriefingEngine


def print_separator():
    """Print a visual separator."""
    print("\n" + "="*80 + "\n")


def display_ranked_priorities(ranked_items, title="Ranked Priorities"):
    """Display ranked items in a formatted way."""
    print(f"\n{title}")
    print("-" * 80)

    if not ranked_items:
        print("No items to prioritize.")
        return

    for i, item in enumerate(ranked_items, 1):
        print(f"\n{i}. [{item['urgency_level'].upper()}] {item['title']}")
        print(f"   Type: {item['type']} | Category: {item['category']}")
        print(f"   Score: {item['priority_score']:.1f}")
        print(f"   Reason: {item['priority_reason']}")


def example_1_deadline_based_ranking():
    """Example 1: Ranking based on deadlines."""
    print_separator()
    print("EXAMPLE 1: Deadline-Based Priority Ranking")
    print_separator()

    engine = BriefingEngine(state_dir="./State")

    # Get current context and ranked priorities
    context = engine.gather_context()
    ranked = engine.rank_priorities(context)

    print(f"Today: {context['today_date']} ({context['day_of_week']})")
    print(f"Weekend: {context['is_weekend']}")

    display_ranked_priorities(ranked)


def example_2_weekend_vs_weekday():
    """Example 2: How weekend vs weekday affects ranking."""
    print_separator()
    print("EXAMPLE 2: Weekend vs Weekday Context")
    print_separator()

    engine = BriefingEngine(state_dir="./State")
    context = engine.gather_context()

    print(f"Current day: {context['day_of_week']}")
    print(f"Is weekend: {context['is_weekend']}")

    ranked = engine.rank_priorities(context)

    # Show how work vs personal tasks are prioritized
    print("\nHow tasks are prioritized based on day of week:")
    for item in ranked[:5]:  # Top 5
        category_type = "Work" if any(k in item['category'].lower()
                                      for k in ['work', 'project', 'team']) else "Personal"
        print(f"  {category_type}: {item['title']}")
        print(f"    Score: {item['priority_score']:.1f} - {item['priority_reason']}")


def example_3_energy_level_recommendations():
    """Example 3: Energy level affects task recommendations."""
    print_separator()
    print("EXAMPLE 3: Energy Level Impact on Task Recommendations")
    print_separator()

    engine = BriefingEngine(state_dir="./State")

    # High energy scenario
    print("\n🚀 HIGH ENERGY (8/10) - Complex work recommended:")
    ranked_high = engine.rank_priorities(energy_level=8)
    display_ranked_priorities(ranked_high[:5], "Top 5 with High Energy")

    # Low energy scenario
    print("\n😴 LOW ENERGY (3/10) - Simple tasks recommended:")
    ranked_low = engine.rank_priorities(energy_level=3)
    display_ranked_priorities(ranked_low[:5], "Top 5 with Low Energy")

    # Compare the differences
    print("\n📊 COMPARISON:")
    print("Tasks that rank higher with HIGH energy:")
    high_scores = {item['title']: item['priority_score'] for item in ranked_high}
    low_scores = {item['title']: item['priority_score'] for item in ranked_low}

    for title in high_scores:
        if title in low_scores:
            diff = high_scores[title] - low_scores[title]
            if diff > 5:
                print(f"  + {title}: +{diff:.1f} points with high energy")


def example_4_top_3_priorities():
    """Example 4: Get top 3 priorities for the day."""
    print_separator()
    print("EXAMPLE 4: Today's Top 3 Priorities")
    print_separator()

    engine = BriefingEngine(state_dir="./State")
    context = engine.gather_context()

    print(f"📅 {context['day_of_week']}, {context['today_date']}\n")

    # Get top 3 priorities
    top_3 = engine.get_top_priorities(limit=3)

    if top_3:
        print("Your top 3 priorities today are:\n")
        for i, item in enumerate(top_3, 1):
            urgency_emoji = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '🟢'
            }.get(item['urgency_level'], '⚪')

            print(f"{urgency_emoji} {i}. {item['title']}")
            print(f"     {item['priority_reason']}\n")
    else:
        print("✅ No pending tasks found. Great job!")


def example_5_all_sources():
    """Example 5: Show ranking includes all sources."""
    print_separator()
    print("EXAMPLE 5: Priority Ranking from All Sources")
    print_separator()

    engine = BriefingEngine(state_dir="./State")
    ranked = engine.rank_priorities()

    # Group by type
    by_type = {}
    for item in ranked:
        item_type = item['type']
        if item_type not in by_type:
            by_type[item_type] = []
        by_type[item_type].append(item)

    print("Items by source type:\n")
    for item_type, items in by_type.items():
        print(f"📋 {item_type.upper()}: {len(items)} items")
        for item in items[:3]:  # Show top 3 from each type
            print(f"   - {item['title']} (score: {item['priority_score']:.1f})")
        if len(items) > 3:
            print(f"   ... and {len(items) - 3} more")
        print()


def main():
    """Run all examples."""
    print("\n" + "="*80)
    print(" " * 20 + "BRIEFING ENGINE - PRIORITY RANKING DEMO")
    print("="*80)

    try:
        # Run examples
        example_1_deadline_based_ranking()
        example_2_weekend_vs_weekday()
        example_3_energy_level_recommendations()
        example_4_top_3_priorities()
        example_5_all_sources()

        print_separator()
        print("✅ All examples completed successfully!")
        print_separator()

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
