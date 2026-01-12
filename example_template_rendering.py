#!/usr/bin/env python3
"""
Example script demonstrating BriefingEngine template rendering.

This script shows how to:
1. Render morning briefings
2. Render evening briefings
3. Add custom sections to briefings
4. Use different energy levels for task recommendations
"""

import sys
import os

# Add Tools to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from Tools.briefing_engine import BriefingEngine, JINJA2_AVAILABLE


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def example_morning_briefing():
    """Example 1: Basic morning briefing."""
    print_section("Example 1: Morning Briefing")

    if not JINJA2_AVAILABLE:
        print("⚠️  Jinja2 not available. Install with: pip install jinja2")
        return

    engine = BriefingEngine()

    try:
        briefing = engine.render_briefing(briefing_type="morning")
        print(briefing)
    except Exception as e:
        print(f"Error: {e}")


def example_morning_with_energy():
    """Example 2: Morning briefing with energy level."""
    print_section("Example 2: Morning Briefing with Energy Level (Low Energy)")

    if not JINJA2_AVAILABLE:
        print("⚠️  Jinja2 not available. Install with: pip install jinja2")
        return

    engine = BriefingEngine()

    try:
        # Simulate low energy morning (4/10)
        briefing = engine.render_briefing(
            briefing_type="morning",
            energy_level=4
        )
        print(briefing)
    except Exception as e:
        print(f"Error: {e}")


def example_evening_briefing():
    """Example 3: Evening briefing with reflection data."""
    print_section("Example 3: Evening Briefing with Reflection")

    if not JINJA2_AVAILABLE:
        print("⚠️  Jinja2 not available. Install with: pip install jinja2")
        return

    engine = BriefingEngine()

    try:
        briefing = engine.render_briefing(
            briefing_type="evening",
            accomplishments=[
                "Completed priority ranking implementation",
                "Wrote comprehensive unit tests",
                "Updated documentation"
            ],
            energy_data={
                "morning_energy": 7,
                "evening_energy": 5,
                "trend": "Decreased (expected after productive day)"
            },
            reflection_notes={
                "went_well": "Good focus in the morning, tackled complex tasks early",
                "could_improve": "Got distracted after lunch, could use better break timing",
                "learned": "Morning hours are best for deep work on this project"
            },
            prep_checklist=[
                "Review tomorrow's calendar",
                "Prepare materials for morning meeting",
                "Set out gym clothes for morning workout"
            ]
        )
        print(briefing)
    except Exception as e:
        print(f"Error: {e}")


def example_custom_sections():
    """Example 4: Morning briefing with custom sections."""
    print_section("Example 4: Morning Briefing with Custom Sections")

    if not JINJA2_AVAILABLE:
        print("⚠️  Jinja2 not available. Install with: pip install jinja2")
        return

    engine = BriefingEngine()

    try:
        custom_sections = [
            {
                "title": "🏋️ Health Goals",
                "content": "- 30 min morning workout\n- Drink 8 glasses of water\n- Take vitamins"
            },
            {
                "title": "📚 Learning Focus",
                "content": "Continue Python testing best practices course (Module 3)"
            }
        ]

        briefing = engine.render_briefing(
            briefing_type="morning",
            custom_sections=custom_sections,
            energy_level=8  # High energy morning
        )
        print(briefing)
    except Exception as e:
        print(f"Error: {e}")


def example_weekend_briefing():
    """Example 5: Weekend briefing (different content priorities)."""
    print_section("Example 5: Weekend Morning Briefing")

    if not JINJA2_AVAILABLE:
        print("⚠️  Jinja2 not available. Install with: pip install jinja2")
        return

    engine = BriefingEngine()

    try:
        context = engine.gather_context()

        # Display what day it is
        print(f"Today is {context['day_of_week']}")
        print(f"Is weekend: {context['is_weekend']}\n")

        briefing = engine.render_briefing(
            briefing_type="morning",
            context=context,
            energy_level=6
        )
        print(briefing)
    except Exception as e:
        print(f"Error: {e}")


def main():
    """Run all examples."""
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "BRIEFING TEMPLATE RENDERING EXAMPLES" + " " * 22 + "║")
    print("╚" + "=" * 78 + "╝")

    # Run examples
    example_morning_briefing()
    example_morning_with_energy()
    example_evening_briefing()
    example_custom_sections()
    example_weekend_briefing()

    # Summary
    print_section("Summary")
    print("✅ Demonstrated morning briefing rendering")
    print("✅ Demonstrated evening briefing rendering")
    print("✅ Showed energy level impact on recommendations")
    print("✅ Showed custom section injection")
    print("✅ Showed weekend vs weekday adaptation")
    print("\nTemplates are fully customizable in the Templates/ directory!")
    print("Edit briefing_morning.md or briefing_evening.md to customize output.\n")


if __name__ == "__main__":
    main()
