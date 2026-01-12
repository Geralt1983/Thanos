"""
Example usage of HealthStateTracker module.

Demonstrates how to:
1. Log health entries (energy, sleep, medication)
2. Retrieve entries and calculate averages
3. Identify patterns in health data
4. Get current state assessments with recommendations
"""

import sys
import os
from datetime import date, timedelta

# Add Tools to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from Tools.health_state_tracker import HealthStateTracker


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def example_1_log_basic_entry():
    """Example 1: Log a basic health entry."""
    print_section("Example 1: Log Basic Health Entry")

    tracker = HealthStateTracker()

    # Log today's health state
    result = tracker.log_entry(
        energy_level=7,
        sleep_hours=8.0,
        vyvanse_time="08:30",
        notes="Feeling productive today"
    )

    if result:
        print("✓ Successfully logged health entry")
        entry = tracker.get_entry()
        print(f"  Energy Level: {entry['energy_level']}/10")
        print(f"  Sleep Hours: {entry['sleep_hours']}")
        print(f"  Vyvanse Time: {entry['vyvanse_time']}")
        print(f"  Notes: {entry['notes']}")
    else:
        print("✗ Failed to log entry")


def example_2_log_historical_data():
    """Example 2: Log historical data for pattern analysis."""
    print_section("Example 2: Log Historical Data (Past 3 Weeks)")

    tracker = HealthStateTracker()

    # Simulate 3 weeks of data with patterns:
    # - Mondays typically low energy
    # - Better sleep = better energy
    # - Morning medication timing better than late
    print("Logging entries...")

    for i in range(21):
        entry_date = tracker.today - timedelta(days=i)
        day_name = entry_date.strftime("%A")

        # Pattern: Mondays are tough
        if day_name == "Monday":
            energy = 4
            sleep = 6.5
        # Pattern: Fridays are good
        elif day_name == "Friday":
            energy = 8
            sleep = 7.5
        # Other days vary
        else:
            energy = 6 + (i % 3)
            sleep = 7.0 + (i % 2) * 0.5

        # Medication timing varies
        if i % 3 == 0:
            vyvanse = "08:00"
        elif i % 3 == 1:
            vyvanse = "08:30"
        else:
            vyvanse = "09:00"

        tracker.log_entry(
            energy_level=energy,
            sleep_hours=sleep,
            vyvanse_time=vyvanse,
            entry_date=entry_date
        )

    print(f"✓ Logged {len(tracker.health_log['entries'])} entries")


def example_3_calculate_averages():
    """Example 3: Calculate 7-day averages."""
    print_section("Example 3: Calculate 7-Day Averages")

    tracker = HealthStateTracker()

    # Need data first - log some entries
    for i in range(10):
        entry_date = tracker.today - timedelta(days=i)
        tracker.log_entry(
            energy_level=6 + (i % 4),
            sleep_hours=7.0 + (i % 3) * 0.5,
            entry_date=entry_date
        )

    # Calculate averages
    averages = tracker.calculate_averages(days=7)

    print(f"Last 7 days averages:")
    print(f"  Average Energy: {averages['avg_energy_level']}/10")
    print(f"  Average Sleep: {averages['avg_sleep_hours']} hours")
    print(f"  Sample Size: {averages['sample_size']} days")


def example_4_identify_patterns():
    """Example 4: Identify patterns in health data."""
    print_section("Example 4: Identify Patterns (Requires 14+ Days)")

    tracker = HealthStateTracker()

    # Create 4 weeks of data with clear patterns
    print("Creating 28 days of data with patterns...")

    for week in range(4):
        for day in range(7):
            entry_date = tracker.today - timedelta(days=week * 7 + day)
            day_name = entry_date.strftime("%A")

            # Pattern: Monday blues
            if day_name == "Monday":
                energy = 4
                sleep = 6.0
            # Pattern: Wednesday hump day
            elif day_name == "Wednesday":
                energy = 5
                sleep = 6.5
            # Pattern: Friday energy
            elif day_name == "Friday":
                energy = 9
                sleep = 8.0
            # Weekend
            elif day_name in ["Saturday", "Sunday"]:
                energy = 7
                sleep = 8.5
            else:
                energy = 6
                sleep = 7.0

            # Vary medication timing
            vyvanse = "08:00" if energy >= 7 else "09:00"

            tracker.log_entry(
                energy_level=energy,
                sleep_hours=sleep,
                vyvanse_time=vyvanse,
                entry_date=entry_date
            )

    # Analyze patterns
    patterns = tracker.identify_patterns(min_days=14)

    if patterns["has_sufficient_data"]:
        print(f"✓ Pattern analysis (based on {patterns['sample_size']} days)\n")

        print("Day of Week Patterns:")
        for day, stats in patterns["day_of_week_patterns"].items():
            print(f"  {day:10} - Energy: {stats['avg_energy']}/10, Sleep: {stats['avg_sleep']} hrs")

        print(f"\n📊 Best Energy Day: {patterns['best_energy_day']}")
        print(f"📉 Worst Energy Day: {patterns['worst_energy_day']}")

        print("\n💡 Insights:")
        for insight in patterns["insights"]:
            print(f"  • {insight}")

        # Sleep-energy correlation
        corr = patterns["sleep_energy_correlation"]
        print(f"\n😴 Sleep-Energy Correlation: {corr['correlation']}")
        print(f"  {corr['relationship']}")

        # Vyvanse timing
        vyvanse = patterns["vyvanse_timing"]
        if vyvanse["has_data"]:
            print(f"\n💊 Vyvanse Timing Analysis:")
            print(f"  {vyvanse['message']}")
    else:
        print(f"⚠ Insufficient data: {patterns['message']}")


def example_5_current_state_assessment():
    """Example 5: Get current state assessment with recommendations."""
    print_section("Example 5: Current State Assessment & Recommendations")

    tracker = HealthStateTracker()

    # Log today's entry with high energy
    tracker.log_entry(
        energy_level=8,
        sleep_hours=8.5,
        vyvanse_time="08:00",
        notes="Great sleep, feeling motivated"
    )

    # Add some historical context
    for i in range(1, 10):
        entry_date = tracker.today - timedelta(days=i)
        tracker.log_entry(
            energy_level=6,
            sleep_hours=7.0,
            entry_date=entry_date
        )

    # Get assessment
    assessment = tracker.get_current_state_assessment()

    print(f"Date: {assessment['date']} ({assessment['day_of_week']})")
    print()

    if assessment["has_todays_data"]:
        print("Current State:")
        print(f"  Energy Level: {assessment['current_energy']}/10")
        print(f"  Sleep Last Night: {assessment['current_sleep']} hours")
        if assessment['vyvanse_time']:
            print(f"  Medication Taken: {assessment['vyvanse_time']}")

        print(f"\n7-Day Averages:")
        avg = assessment['seven_day_avg']
        print(f"  Avg Energy: {avg['avg_energy_level']}/10")
        print(f"  Avg Sleep: {avg['avg_sleep_hours']} hours")

        print(f"\n💡 Recommendations:")
        for rec in assessment['recommendations']:
            print(f"  • {rec}")
    else:
        print("⚠ No data logged for today yet")


def example_6_low_energy_recommendations():
    """Example 6: Recommendations for low energy day."""
    print_section("Example 6: Low Energy Day Recommendations")

    tracker = HealthStateTracker()

    # Log today with low energy
    tracker.log_entry(
        energy_level=3,
        sleep_hours=5.5,
        notes="Didn't sleep well, feeling drained"
    )

    assessment = tracker.get_current_state_assessment()

    print(f"Current Energy: {assessment['current_energy']}/10")
    print(f"Sleep: {assessment['current_sleep']} hours")
    print()
    print("💡 Recommendations for today:")
    for rec in assessment['recommendations']:
        print(f"  • {rec}")


def example_7_retrieve_historical_entries():
    """Example 7: Retrieve and display historical entries."""
    print_section("Example 7: Review Recent History")

    tracker = HealthStateTracker()

    # Create some historical data
    for i in range(5):
        entry_date = tracker.today - timedelta(days=i)
        tracker.log_entry(
            energy_level=5 + i,
            sleep_hours=6.5 + (i * 0.3),
            vyvanse_time="08:30",
            entry_date=entry_date
        )

    # Retrieve recent entries
    recent = tracker.get_recent_entries(days=5)

    print(f"Last 5 days of health data:\n")
    for entry in recent:
        entry_date = date.fromisoformat(entry['date'])
        print(f"{entry_date.strftime('%Y-%m-%d')} ({entry['day_of_week']}):")
        print(f"  Energy: {entry['energy_level']}/10")
        print(f"  Sleep: {entry['sleep_hours']} hours")
        if entry.get('vyvanse_time'):
            print(f"  Vyvanse: {entry['vyvanse_time']}")
        print()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("  HealthStateTracker - Example Usage")
    print("=" * 60)

    try:
        example_1_log_basic_entry()
        example_2_log_historical_data()
        example_3_calculate_averages()
        example_4_identify_patterns()
        example_5_current_state_assessment()
        example_6_low_energy_recommendations()
        example_7_retrieve_historical_entries()

        print("\n" + "=" * 60)
        print("  All examples completed successfully!")
        print("=" * 60)
        print("\n💾 Health data saved to: State/HealthLog.json")
        print()

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
