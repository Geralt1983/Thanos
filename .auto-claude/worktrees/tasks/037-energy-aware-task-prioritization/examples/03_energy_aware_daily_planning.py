#!/usr/bin/env python3
"""
Energy-Aware Daily Planning Example

This script demonstrates a complete daily planning workflow that adapts to your
energy levels throughout the day. Perfect for ADHD users who experience variable
energy and need flexible planning.

Workflow:
1. Morning: Check energy and plan the day
2. Mid-day: Reassess energy and adjust tasks
3. Evening: Override energy if needed (medication, deadline pressure)
4. End of day: Provide feedback on task-energy matches

Usage:
    python 03_energy_aware_daily_planning.py

Requirements:
    - Thanos MCP server running
    - Oura Ring data synced (or manual energy logs)
"""

import json
from datetime import datetime, time


def print_header(title: str, timestamp: str = None) -> None:
    """Print a formatted section header with optional timestamp."""
    print(f"\n{'=' * 70}")
    if timestamp:
        print(f"  {title} - {timestamp}")
    else:
        print(f"  {title}")
    print(f"{'=' * 70}\n")


def print_time_separator(time_str: str, emoji: str) -> None:
    """Print a time separator for different parts of the day."""
    print(f"\n\n{'~' * 70}")
    print(f"{emoji} {time_str}".center(70))
    print(f"{'~' * 70}\n")


def morning_planning() -> dict:
    """
    Phase 1: Morning Planning (8:00 AM)

    Start the day by checking energy and setting up daily plan.
    """
    print_time_separator("MORNING PLANNING - 8:00 AM", "🌅")
    print_header("Phase 1: Morning Energy Check & Planning")

    # Step 1: Get energy context
    print("🔍 Checking energy context...\n")

    energy_context = {
        "energyLevel": "medium",
        "readinessScore": 76,
        "sleepScore": 73,
        "source": "oura",
        "timestamp": "2026-01-12T08:00:00"
    }

    print(f"✅ Energy Context:")
    print(f"   🔋 Energy Level: {energy_context['energyLevel'].upper()}")
    print(f"   📊 Readiness: {energy_context['readinessScore']}/100")
    print(f"   😴 Sleep: {energy_context['sleepScore']}/100")
    print(f"   💭 Not your best sleep, but you're functional")

    # Step 2: Adjust daily goal
    print(f"\n📏 Adjusting daily goal based on readiness...")

    goal = {
        "originalTarget": 18,
        "adjustedTarget": 18,  # 76 is in 70-84 range = 0% adjustment
        "adjustmentPercent": 0,
        "reasoning": "Your readiness (76) is in the healthy baseline range. Aim for standard daily target."
    }

    print(f"\n🎯 Daily Goal: {goal['adjustedTarget']} points (no adjustment needed)")

    # Step 3: Get task recommendations
    print(f"\n🧠 Getting energy-matched task recommendations...\n")

    tasks = [
        {
            "id": 42,
            "title": "Review and merge 3 pull requests",
            "cognitiveLoad": "medium",
            "estimatedHours": 2.0,
            "points": 5,
            "energyScore": 125
        },
        {
            "id": 51,
            "title": "Write unit tests for auth service",
            "cognitiveLoad": "medium",
            "estimatedHours": 3.0,
            "points": 6,
            "energyScore": 120
        },
        {
            "id": 38,
            "title": "Update deployment documentation",
            "cognitiveLoad": "medium",
            "estimatedHours": 2.0,
            "points": 4,
            "energyScore": 115
        },
        {
            "id": 29,
            "title": "Respond to team slack messages",
            "cognitiveLoad": "low",
            "estimatedHours": 1.0,
            "points": 2,
            "energyScore": 65
        }
    ]

    print("✅ Top tasks for MEDIUM energy:\n")
    for i, task in enumerate(tasks[:3], 1):
        print(f"   {i}. [{task['cognitiveLoad'].upper()}] {task['title']}")
        print(f"      ~{task['estimatedHours']}h | {task['points']} points | Score: {task['energyScore']}/165")

    # Step 4: Plan morning block
    print(f"\n📋 Morning Plan (8:00 AM - 12:00 PM):")
    print(f"   • 8:00-10:00: Review and merge pull requests (2h)")
    print(f"   • 10:00-12:00: Write unit tests for auth service (2h)")
    print(f"   • Progress toward goal: 11 points / 18 target")

    return {
        "energyContext": energy_context,
        "goal": goal,
        "tasks": tasks,
        "completedTasks": []
    }


def midday_adjustment(morning_state: dict) -> dict:
    """
    Phase 2: Mid-day Check-in (1:00 PM)

    Energy has dipped after lunch. Reassess and adjust afternoon plan.
    """
    print_time_separator("MID-DAY CHECK-IN - 1:00 PM", "☀️")
    print_header("Phase 2: Energy Shift Detection & Adjustment")

    # Completed morning tasks
    completed = [42, 51]  # Completed both morning tasks
    points_earned = 11

    print(f"✅ Morning Progress:")
    print(f"   ✓ Reviewed and merged pull requests (5 points)")
    print(f"   ✓ Wrote unit tests for auth service (6 points)")
    print(f"   📊 Total: {points_earned}/18 points")

    # Energy check at lunch
    print(f"\n🔍 Checking current energy (post-lunch dip)...\n")

    energy_context = {
        "energyLevel": "low",
        "readinessScore": 76,  # Same readiness, but post-lunch energy dip
        "sleepScore": 73,
        "source": "manual_override",  # User noticed they're dragging
        "timestamp": "2026-01-12T13:00:00"
    }

    print(f"⚠️  Energy Update:")
    print(f"   🔋 Energy Level: {energy_context['energyLevel'].upper()} (was: MEDIUM)")
    print(f"   💭 Post-lunch energy dip detected")
    print(f"   🎯 Adjusting task recommendations...")

    # Get new recommendations for low energy
    print(f"\n🧠 Updated recommendations for LOW energy:\n")

    afternoon_tasks = [
        {
            "id": 29,
            "title": "Respond to team slack messages",
            "cognitiveLoad": "low",
            "estimatedHours": 1.0,
            "points": 2,
            "energyScore": 140
        },
        {
            "id": 67,
            "title": "Update JIRA tickets with progress notes",
            "cognitiveLoad": "low",
            "estimatedHours": 0.5,
            "points": 1,
            "energyScore": 135
        },
        {
            "id": 72,
            "title": "Review and approve expense reports",
            "cognitiveLoad": "low",
            "estimatedHours": 0.5,
            "points": 1,
            "energyScore": 130
        },
        {
            "id": 38,
            "title": "Update deployment documentation",
            "cognitiveLoad": "medium",
            "estimatedHours": 2.0,
            "points": 4,
            "energyScore": 50
        }
    ]

    print("✅ Top tasks for LOW energy (admin work):\n")
    for i, task in enumerate(afternoon_tasks[:3], 1):
        print(f"   {i}. [{task['cognitiveLoad'].upper()}] {task['title']}")
        print(f"      ~{task['estimatedHours']}h | {task['points']} points | Score: {task['energyScore']}/165")

    print(f"\n💡 Coach Says:")
    print(f"   'You're at 11/18 points with afternoon ahead. Your energy dipped")
    print(f"   post-lunch - totally normal! Let's knock out some quick admin wins")
    print(f"   to build momentum. Save the documentation for tomorrow when you're fresh.'")

    print(f"\n📋 Afternoon Plan (1:00 PM - 5:00 PM):")
    print(f"   • 1:00-2:00: Respond to slack messages + update JIRA (1h)")
    print(f"   • 2:00-2:30: Review expense reports (0.5h)")
    print(f"   • 2:30-3:30: Walk/break (energy recovery)")
    print(f"   • 3:30-5:00: Light admin work or early finish")
    print(f"   • Target: 14-15 points (adjusted for energy)")

    return {
        "energyContext": energy_context,
        "afternoonTasks": afternoon_tasks,
        "pointsEarned": points_earned
    }


def medication_override(midday_state: dict) -> dict:
    """
    Phase 3: Energy Override (3:00 PM)

    ADHD medication kicks in, user feels energy boost. Override the system
    to take advantage of this window.
    """
    print_time_separator("MEDICATION WINDOW - 3:00 PM", "💊")
    print_header("Phase 3: User Override (Medication Boost)")

    points_earned = 15  # Completed afternoon admin tasks

    print(f"✅ Afternoon Progress:")
    print(f"   ✓ Responded to slack messages (2 points)")
    print(f"   ✓ Updated JIRA tickets (1 point)")
    print(f"   ✓ Reviewed expense reports (1 point)")
    print(f"   📊 Total: {points_earned}/18 points")

    # User notices medication effect
    print(f"\n💊 User Input: 'I took my ADHD medication and it just kicked in.'")
    print(f"               'I feel focused and ready to tackle something more complex!'\n")

    # Override energy level
    print(f"🔧 Overriding energy detection...\n")

    # Simulate MCP tool call: workos_override_energy_suggestion
    mcp_request = {
        "tool": "workos_override_energy_suggestion",
        "args": {
            "energyLevel": "high",
            "reason": "ADHD medication kicked in, feeling focused and energized",
            "adjustDailyGoal": False  # Keep current goal, just rerank tasks
        }
    }

    energy_context = {
        "energyLevel": "high",
        "readinessScore": 76,  # Oura still says 76, but user knows better
        "source": "user_override",
        "overrideReason": "ADHD medication kicked in, feeling focused and energized",
        "timestamp": "2026-01-12T15:00:00"
    }

    print(f"✅ Energy Override Applied:")
    print(f"   🔋 New Energy Level: {energy_context['energyLevel'].upper()}")
    print(f"   📊 Oura Readiness: {energy_context['readinessScore']} (unchanged)")
    print(f"   💡 Source: USER OVERRIDE (you know your body best!)")

    # Get high-energy task recommendations
    print(f"\n🧠 Updated recommendations for HIGH energy:\n")

    high_energy_tasks = [
        {
            "id": 85,
            "title": "Architect database indexing strategy",
            "cognitiveLoad": "high",
            "estimatedHours": 2.0,
            "points": 8,
            "energyScore": 145
        },
        {
            "id": 91,
            "title": "Debug performance bottleneck in API",
            "cognitiveLoad": "high",
            "estimatedHours": 2.0,
            "points": 7,
            "energyScore": 140
        },
        {
            "id": 38,
            "title": "Update deployment documentation",
            "cognitiveLoad": "medium",
            "estimatedHours": 2.0,
            "points": 4,
            "energyScore": 70
        }
    ]

    print("✅ Top tasks for HIGH energy:\n")
    for i, task in enumerate(high_energy_tasks[:2], 1):
        print(f"   {i}. [{task['cognitiveLoad'].upper()}] {task['title']}")
        print(f"      ~{task['estimatedHours']}h | {task['points']} points | Score: {task['energyScore']}/165")

    print(f"\n💡 Coach Says:")
    print(f"   'Perfect! Take advantage of this medication window. You have 2 hours")
    print(f"   of high focus available. Tackle that database indexing work - it's")
    print(f"   exactly the right task for your current state.'")

    print(f"\n📋 Medication Window Plan (3:00 PM - 5:00 PM):")
    print(f"   • 3:00-5:00: Architect database indexing strategy (2h)")
    print(f"   • This gets you to 23 points - exceeding your 18 point target!")
    print(f"   • 🎉 Bonus: High-value work completed on medium readiness day")

    return {
        "energyContext": energy_context,
        "highEnergyTasks": high_energy_tasks,
        "pointsEarned": points_earned
    }


def end_of_day_feedback(daily_state: dict) -> None:
    """
    Phase 4: End of Day Feedback (6:00 PM)

    Provide feedback on energy-task matches to improve future recommendations.
    """
    print_time_separator("END OF DAY REVIEW - 6:00 PM", "🌙")
    print_header("Phase 4: Provide Feedback for Learning")

    final_points = 23
    target_points = 18

    print(f"🎉 Daily Summary:")
    print(f"   📊 Points Earned: {final_points}/{target_points} ({final_points - target_points:+d})")
    print(f"   ✅ Tasks Completed: 6")
    print(f"   🎯 Target: EXCEEDED")

    print(f"\n📝 Providing feedback on energy-task matches...\n")

    # Feedback example 1: Good match
    print("📊 Feedback #1:")
    print("   Task: Review and merge pull requests")
    print("   Suggested Energy: MEDIUM | Actual Energy: MEDIUM")
    print("   Result: ✅ COMPLETED SUCCESSFULLY")
    print("   Feedback: 'Perfect match! Task was exactly right for morning energy.'")

    # Simulate MCP tool call
    feedback1 = {
        "tool": "workos_provide_energy_feedback",
        "args": {
            "taskId": 42,
            "suggestedEnergyLevel": "medium",
            "actualEnergyLevel": "medium",
            "completedSuccessfully": True,
            "userFeedback": "Perfect match! Task was exactly right for morning energy."
        }
    }

    # Feedback example 2: Good match (low energy)
    print("\n📊 Feedback #2:")
    print("   Task: Respond to team slack messages")
    print("   Suggested Energy: LOW | Actual Energy: LOW")
    print("   Result: ✅ COMPLETED SUCCESSFULLY")
    print("   Feedback: 'Great suggestion. Easy admin work was all I could handle.'")

    feedback2 = {
        "tool": "workos_provide_energy_feedback",
        "args": {
            "taskId": 29,
            "suggestedEnergyLevel": "low",
            "actualEnergyLevel": "low",
            "completedSuccessfully": True,
            "userFeedback": "Great suggestion. Easy admin work was all I could handle."
        }
    }

    # Feedback example 3: User override success
    print("\n📊 Feedback #3:")
    print("   Task: Architect database indexing strategy")
    print("   Suggested Energy: LOW (auto) | Actual Energy: HIGH (override)")
    print("   Result: ✅ COMPLETED SUCCESSFULLY")
    print("   Feedback: 'Override worked perfectly. Medication window was productive!'")

    feedback3 = {
        "tool": "workos_provide_energy_feedback",
        "args": {
            "taskId": 85,
            "suggestedEnergyLevel": "low",  # System suggested low based on afternoon time
            "actualEnergyLevel": "high",  # User overrode to high
            "completedSuccessfully": True,
            "userFeedback": "Override worked perfectly. Medication window was productive!"
        }
    }

    print(f"\n✅ Feedback recorded for 3 tasks")
    print(f"   This data helps improve future energy-task matching!")

    print(f"\n💡 Coach Insights:")
    print(f"   • Your morning (8-12) is solid for medium cognitive work")
    print(f"   • Post-lunch dip (1-3) is consistent - plan admin work")
    print(f"   • Medication window (3-5) is your high-energy time")
    print(f"   • Consider scheduling deep work for 3-5 PM going forward")

    print(f"\n🎯 Tomorrow's Recommendations:")
    print(f"   • Check readiness score in morning")
    print(f"   • If readiness is similar (70-84), use this schedule:")
    print(f"     - Morning: Medium cognitive work")
    print(f"     - Lunch: Energy dip incoming, plan admin")
    print(f"     - 3 PM: Take medication if needed")
    print(f"     - 3-5 PM: High cognitive work (medication window)")


def main():
    """Run the complete daily planning workflow."""
    print("\n" + "📅 ENERGY-AWARE DAILY PLANNING".center(70))
    print("Adaptive task planning that responds to your energy throughout the day\n")

    print("This example simulates a full day with energy shifts and user overrides.")
    print("Watch how the system adapts recommendations based on real-world conditions.\n")

    try:
        input("Press Enter to start the day...")

        # Phase 1: Morning planning
        morning_state = morning_planning()

        input("\n⏰ Fast forward to lunch time... (Press Enter)")

        # Phase 2: Mid-day adjustment
        midday_state = midday_adjustment(morning_state)

        input("\n⏰ Fast forward to medication time... (Press Enter)")

        # Phase 3: Medication override
        override_state = medication_override(midday_state)

        input("\n⏰ Fast forward to end of day... (Press Enter)")

        # Phase 4: End of day feedback
        end_of_day_feedback(override_state)

        print_header("✨ Daily Planning Example Complete!")

        print("🎯 Key Learnings:")
        print("   1. Check energy multiple times per day, not just once")
        print("   2. Adjust plans when energy shifts (post-lunch dip is common)")
        print("   3. Override auto-detection when you know better (medication, urgency)")
        print("   4. Provide feedback to improve future recommendations")
        print("   5. The system learns YOUR patterns over time\n")

        print("💡 ADHD-Specific Benefits:")
        print("   • Flexible planning that adapts to variable energy")
        print("   • Medication timing is respected and utilized")
        print("   • Quick wins on low energy days (momentum building)")
        print("   • User agency to override when needed")
        print("   • Feedback loop prevents algorithmic rigidity\n")

        print("🚀 Next Steps:")
        print("   1. Try this workflow with your actual tasks")
        print("   2. Set cognitive load on all tasks for better matching")
        print("   3. Check energy 2-3 times per day (morning, lunch, afternoon)")
        print("   4. Override when you know your energy better than metrics")
        print("   5. Provide feedback after completing tasks\n")

    except KeyboardInterrupt:
        print("\n\n👋 Exiting...\n")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Make sure the Thanos MCP server is running.\n")


if __name__ == "__main__":
    main()
