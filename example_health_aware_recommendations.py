"""
Example: Health-Aware Task Recommendations

Demonstrates how the BriefingEngine uses health state to recommend
appropriate tasks based on energy levels, medication timing, and patterns.
"""

import sys
import os
from datetime import datetime, date

# Add Tools to path
sys.path.insert(0, os.path.dirname(__file__))

from Tools.briefing_engine import BriefingEngine

def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")

def print_recommendations(recommendations, title):
    """Print recommendations in a readable format."""
    print_section(title)

    # Energy level and reasoning
    energy = recommendations.get("energy_level")
    if energy:
        print(f"Energy Level: {energy}/10\n")

    print("Reasoning:")
    for reason in recommendations.get("reasoning", []):
        print(f"  • {reason}")

    # Peak focus window
    peak_focus = recommendations.get("peak_focus_window")
    if peak_focus:
        print(f"\n⏰ Peak Focus Window: {peak_focus['peak_start_str']} - {peak_focus['peak_end_str']}")
        if peak_focus.get("is_peak_now"):
            print("   ✨ You're in your peak focus time right now!")

    # Recommended tasks
    print("\n📋 Recommended Tasks:")
    for i, task in enumerate(recommendations.get("recommended_tasks", [])[:5], 1):
        urgency = task.get("urgency_level", "medium")
        task_type = task.get("task_type", "general")
        urgency_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(urgency, "⚪")
        type_icon = {"deep_work": "🧠", "admin": "📝", "general": "✅"}.get(task_type, "✅")
        print(f"  {i}. {urgency_icon} {type_icon} {task['title']}")
        print(f"     └─ {task.get('priority_reason', '')}")

    # Reschedule recommendations
    if recommendations.get("reschedule_recommendations"):
        print("\n⏰ Consider Rescheduling:")
        for item in recommendations["reschedule_recommendations"][:3]:
            task = item["task"]
            print(f"  • {task['title']}")
            print(f"    └─ {item['reason']}")

    # Task breakdown
    print("\n📊 Task Classification:")
    print(f"  • Deep Work: {len(recommendations.get('deep_work_tasks', []))} tasks")
    print(f"  • Admin/Light: {len(recommendations.get('admin_tasks', []))} tasks")
    print(f"  • General: {len(recommendations.get('general_tasks', []))} tasks")


def main():
    """Run examples demonstrating health-aware recommendations."""
    print("\n" + "=" * 80)
    print("  Health-Aware Task Recommendations - Examples")
    print("=" * 80)

    # Initialize engine
    engine = BriefingEngine()

    # Example 1: High Energy (8+) - Ideal for Deep Work
    print_section("Example 1: High Energy Morning (9/10)")
    print("Scenario: Well-rested, took Vyvanse at 8:00 AM, feeling energized")

    health_state_high = {
        "has_todays_data": True,
        "current_energy": 9,
        "current_sleep": 8.0,
        "vyvanse_time": "08:00",
        "patterns": None
    }

    recommendations = engine.get_health_aware_recommendations(health_state=health_state_high)
    print_recommendations(recommendations, "Recommendations")

    print("\n💡 Insight: High energy detected! Perfect time for complex problem-solving,")
    print("   deep coding work, or architectural planning.")

    # Example 2: Moderate Energy (5/10) - Light Tasks
    print_section("Example 2: Moderate Energy Afternoon (5/10)")
    print("Scenario: Decent sleep but energy declining, no medication")

    health_state_moderate = {
        "has_todays_data": True,
        "current_energy": 5,
        "current_sleep": 7.0,
        "vyvanse_time": None,
        "patterns": None
    }

    recommendations = engine.get_health_aware_recommendations(health_state=health_state_moderate)
    print_recommendations(recommendations, "Recommendations")

    print("\n💡 Insight: Moderate energy suggests focusing on lighter tasks like admin work,")
    print("   meetings, code reviews, or organizing. Save deep work for better timing.")

    # Example 3: Low Energy (3/10) - Admin Only
    print_section("Example 3: Low Energy Day (3/10)")
    print("Scenario: Poor sleep, low energy, no medication")

    health_state_low = {
        "has_todays_data": True,
        "current_energy": 3,
        "current_sleep": 5.0,
        "vyvanse_time": None,
        "patterns": None
    }

    recommendations = engine.get_health_aware_recommendations(health_state=health_state_low)
    print_recommendations(recommendations, "Recommendations")

    print("\n💡 Insight: Low energy day - be kind to yourself! Focus on simple tasks,")
    print("   reschedule complex work, and prioritize rest when possible.")

    # Example 4: Good Energy with Peak Focus Window
    print_section("Example 4: Good Energy with Medication (7/10)")
    print("Scenario: Good energy, took Vyvanse at 8:00 AM, currently in peak window")

    health_state_peak = {
        "has_todays_data": True,
        "current_energy": 7,
        "current_sleep": 7.5,
        "vyvanse_time": "08:00",
        "patterns": None
    }

    recommendations = engine.get_health_aware_recommendations(health_state=health_state_peak)
    print_recommendations(recommendations, "Recommendations")

    print("\n💡 Insight: Good energy plus medication peak = excellent time for important work!")
    print("   Tackle your highest-priority deep work tasks during this window.")

    # Example 5: With Pattern Insights
    print_section("Example 5: With Historical Patterns")
    print("Scenario: Good energy, but historical data shows Mondays are typically low")

    health_state_patterns = {
        "has_todays_data": True,
        "current_energy": 6,
        "current_sleep": 7.0,
        "vyvanse_time": None,
        "patterns": {
            "has_sufficient_data": True,
            "worst_energy_day": "Monday",
            "best_energy_day": "Wednesday",
            "sleep_energy_correlation": "strong"
        }
    }

    # Mock it's Monday
    recommendations = engine.get_health_aware_recommendations(health_state=health_state_patterns)
    print_recommendations(recommendations, "Recommendations")

    print("\n💡 Insight: Historical patterns help calibrate expectations and provide")
    print("   personalized guidance based on your unique energy rhythms.")

    # Summary
    print_section("Summary: Task Type Classification")
    print("""
The BriefingEngine classifies tasks into three categories:

🧠 Deep Work (Requires high cognitive load)
   Keywords: design, architect, plan, research, analyze, write, develop,
            implement, refactor, debug, solve, create, strategy, complex

📝 Admin/Light (Lower cognitive load)
   Keywords: send, email, call, schedule, update, review, respond,
            organize, file, expense, timesheet, report, meeting

✅ General (Standard tasks)
   Everything else that doesn't fit above categories

Energy Level Recommendations:
• 8-10 (High): Focus on deep work and complex problem-solving
• 6-7 (Good): Mix of deep work and general tasks
• 4-5 (Moderate): Lighter tasks and admin work
• 1-3 (Low): Simple admin tasks only, reschedule complex work

The system also considers:
• Deadline urgency (overdue > due today > this week)
• Medication timing (peak focus window 2-4 hours post-dose)
• Historical patterns (best/worst energy days)
• Day of week context (weekday vs weekend)
""")

    print("\n" + "=" * 80)
    print("  For more information, see docs/HEALTH_STATE_TRACKER.md")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
