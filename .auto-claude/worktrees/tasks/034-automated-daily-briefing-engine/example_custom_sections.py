"""
Example script demonstrating custom section functionality in BriefingEngine.

This shows how to:
1. Enable/disable sections
2. Reorder sections
3. Add custom sections with data providers
4. Use conditional sections (day-specific, briefing-type-specific)
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Tools.briefing_engine import BriefingEngine


def example_1_basic_section_control():
    """Example 1: Basic enable/disable and reordering of sections."""
    print("=" * 80)
    print("Example 1: Basic Section Control")
    print("=" * 80)

    # Configure to only show priorities and commitments, in reverse order
    config = {
        "content": {
            "sections": {
                "enabled": ["priorities", "commitments"],
                "order": ["commitments", "priorities"]
            }
        }
    }

    engine = BriefingEngine(config=config)
    enabled_sections = engine.get_enabled_sections("morning")

    print("\nEnabled sections (in order):")
    for i, section_id in enumerate(enabled_sections, 1):
        print(f"  {i}. {section_id}")

    print("\n" + "=" * 80 + "\n")


def example_2_custom_section_provider():
    """Example 2: Register a custom section provider programmatically."""
    print("=" * 80)
    print("Example 2: Custom Section Provider")
    print("=" * 80)

    def weather_provider(context, briefing_type, **kwargs):
        """Custom provider for weather section."""
        # In a real implementation, this would fetch actual weather data
        return {
            "title": "🌤️ Weather Forecast",
            "data": {
                "temperature": "72°F",
                "conditions": "Partly Cloudy",
                "recommendation": "Great day for outdoor tasks!"
            }
        }

    # Create engine and register custom provider
    engine = BriefingEngine()
    engine.register_section_provider("weather", weather_provider)

    # Get weather section data
    context = engine.gather_context()
    weather_data = engine.get_section_data("weather", context, "morning")

    print("\nWeather Section Data:")
    print(json.dumps(weather_data, indent=2))

    print("\n" + "=" * 80 + "\n")


def example_3_custom_section_via_config():
    """Example 3: Define custom section in configuration."""
    print("=" * 80)
    print("Example 3: Custom Section via Config")
    print("=" * 80)

    config = {
        "content": {
            "sections": {
                "enabled": ["priorities", "daily_quote", "commitments"],
                "order": ["daily_quote", "priorities", "commitments"],
                "custom": [
                    {
                        "id": "daily_quote",
                        "title": "💭 Daily Inspiration",
                        "enabled_by_default": True
                    }
                ]
            }
        }
    }

    engine = BriefingEngine(config=config)
    context = engine.gather_context()

    # Get custom section
    quote_section = engine.get_section_data("daily_quote", context, "morning")

    print("\nDaily Quote Section:")
    print(json.dumps(quote_section, indent=2))

    print("\n" + "=" * 80 + "\n")


def example_4_conditional_sections():
    """Example 4: Sections that only appear on certain days."""
    print("=" * 80)
    print("Example 4: Conditional Sections (Day-Specific)")
    print("=" * 80)

    config = {
        "content": {
            "sections": {
                "enabled": ["priorities", "weekly_review", "weekend_plans"],
                "order": ["weekly_review", "priorities", "weekend_plans"],
                "custom": [
                    {
                        "id": "weekly_review",
                        "title": "📊 Weekly Review",
                        "conditions": {
                            "days": ["sunday", "monday"]
                        }
                    },
                    {
                        "id": "weekend_plans",
                        "title": "🌴 Weekend Plans",
                        "conditions": {
                            "days": ["friday", "saturday"]
                        }
                    }
                ]
            }
        }
    }

    engine = BriefingEngine(config=config)
    context = engine.gather_context()

    print(f"\nToday is: {context['day_of_week']}")

    # Check which conditional sections appear
    weekly_review = engine.get_section_data("weekly_review", context, "morning")
    weekend_plans = engine.get_section_data("weekend_plans", context, "morning")

    print("\nWeekly Review section:")
    if weekly_review:
        print(f"  ✓ Appears (configured for Sunday/Monday)")
    else:
        print(f"  ✗ Hidden (only appears on Sunday/Monday)")

    print("\nWeekend Plans section:")
    if weekend_plans:
        print(f"  ✓ Appears (configured for Friday/Saturday)")
    else:
        print(f"  ✗ Hidden (only appears on Friday/Saturday)")

    print("\n" + "=" * 80 + "\n")


def example_5_briefing_type_conditions():
    """Example 5: Sections specific to morning or evening briefings."""
    print("=" * 80)
    print("Example 5: Briefing Type-Specific Sections")
    print("=" * 80)

    config = {
        "content": {
            "sections": {
                "enabled": ["priorities", "morning_motivation", "evening_reflection"],
                "order": ["morning_motivation", "priorities", "evening_reflection"],
                "custom": [
                    {
                        "id": "morning_motivation",
                        "title": "☀️ Morning Motivation",
                        "conditions": {
                            "briefing_types": ["morning"]
                        }
                    },
                    {
                        "id": "evening_reflection",
                        "title": "🌙 Evening Reflection",
                        "conditions": {
                            "briefing_types": ["evening"]
                        }
                    }
                ]
            }
        }
    }

    engine = BriefingEngine(config=config)
    context = engine.gather_context()

    # Morning briefing
    print("\nMorning Briefing Sections:")
    sections_data = engine.prepare_sections_data(context, "morning")
    for section in sections_data:
        print(f"  - {section['title']}")

    # Evening briefing
    print("\nEvening Briefing Sections:")
    sections_data = engine.prepare_sections_data(context, "evening")
    for section in sections_data:
        print(f"  - {section['title']}")

    print("\n" + "=" * 80 + "\n")


def example_6_full_workflow():
    """Example 6: Complete workflow with custom sections."""
    print("=" * 80)
    print("Example 6: Full Workflow with Custom Sections")
    print("=" * 80)

    # Define a custom data provider for habit tracking
    def habits_provider(context, briefing_type, **kwargs):
        """Provider for daily habits section."""
        # In real use, this would read from a habits tracking file
        return {
            "title": "✅ Daily Habits",
            "data": {
                "habits": [
                    {"name": "Morning meditation", "completed": False},
                    {"name": "Exercise", "completed": False},
                    {"name": "Read 30 min", "completed": False},
                ]
            }
        }

    # Configuration with multiple custom sections
    config = {
        "content": {
            "sections": {
                "enabled": [
                    "health",
                    "priorities",
                    "habits",
                    "commitments",
                    "tasks",
                    "quick_wins"
                ],
                "order": [
                    "health",
                    "habits",
                    "priorities",
                    "commitments",
                    "tasks",
                    "quick_wins"
                ],
                "custom": [
                    {
                        "id": "habits",
                        "title": "✅ Daily Habits",
                        "enabled_by_default": True
                    }
                ]
            }
        }
    }

    # Create engine and register provider
    engine = BriefingEngine(config=config)
    engine.register_section_provider("habits", habits_provider)

    # Gather context and prepare sections
    context = engine.gather_context()
    sections_data = engine.prepare_sections_data(
        context,
        "morning",
        health_state={"energy_level": 7, "sleep_hours": 7.5}
    )

    print("\nMorning Briefing Structure:")
    print(f"Total sections: {len(sections_data)}\n")

    for i, section in enumerate(sections_data, 1):
        print(f"{i}. {section['title']} (id: {section['id']})")
        # Show sample data
        data_keys = list(section['data'].keys())
        if data_keys:
            print(f"   Data keys: {', '.join(data_keys)}")

    print("\n" + "=" * 80 + "\n")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("Custom Sections Feature Examples")
    print("=" * 80 + "\n")

    try:
        example_1_basic_section_control()
        example_2_custom_section_provider()
        example_3_custom_section_via_config()
        example_4_conditional_sections()
        example_5_briefing_type_conditions()
        example_6_full_workflow()

        print("=" * 80)
        print("All examples completed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
