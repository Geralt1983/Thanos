#!/usr/bin/env python3
"""
Energy-Aware Morning Routine Example

This script demonstrates a typical morning workflow using the energy-aware
task prioritization system. Perfect for ADHD users who want to start the day
aligned with their energy levels.

Workflow:
1. Check current energy context (Oura readiness + sleep score)
2. Adjust daily goal based on readiness
3. Get energy-matched task recommendations
4. Review and plan the day

Usage:
    python 01_morning_routine.py

Requirements:
    - Thanos MCP server running
    - Oura Ring data synced (or manual energy logs)
"""

import json
from datetime import datetime


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def check_energy_context() -> dict:
    """
    Step 1: Check current energy context

    Uses workos_get_energy_aware_tasks (with limit=0) to get energy context
    without fetching tasks yet.

    Returns:
        dict: Energy context with readiness, sleep scores, and energy level
    """
    print_header("STEP 1: Check Your Energy Context")

    # Simulate MCP tool call: workos_get_energy_aware_tasks
    # In real usage, this would be called through the MCP protocol
    mcp_request = {
        "tool": "workos_get_energy_aware_tasks",
        "args": {
            "limit": 0  # Just get energy context
        }
    }

    print("🔍 Checking Oura Ring data and energy logs...\n")

    # Simulated response - in real usage this comes from MCP server
    energy_context = {
        "energyLevel": "medium",
        "readinessScore": 77,
        "sleepScore": 75,
        "source": "oura",
        "timestamp": datetime.now().isoformat()
    }

    print(f"✅ Energy Context Retrieved:")
    print(f"   🔋 Energy Level: {energy_context['energyLevel'].upper()}")
    print(f"   📊 Readiness Score: {energy_context['readinessScore']}/100")
    print(f"   😴 Sleep Score: {energy_context['sleepScore']}/100")
    print(f"   📡 Source: {energy_context['source']}")

    return energy_context


def adjust_daily_goal(energy_context: dict) -> dict:
    """
    Step 2: Adjust daily goal based on readiness

    Uses workos_adjust_daily_goal to automatically calculate the appropriate
    target for today based on your readiness score.

    Args:
        energy_context: Current energy context from step 1

    Returns:
        dict: Goal adjustment details
    """
    print_header("STEP 2: Adjust Your Daily Goal")

    base_target = 18  # Standard daily target

    # Simulate MCP tool call: workos_adjust_daily_goal
    mcp_request = {
        "tool": "workos_adjust_daily_goal",
        "args": {
            "baseTarget": base_target
        }
    }

    print(f"📏 Calculating optimal target for readiness {energy_context['readinessScore']}...\n")

    # Simulated response based on algorithm
    # Readiness 70-84 = 0% adjustment
    adjustment = {
        "originalTarget": base_target,
        "adjustedTarget": base_target,  # 77 is in 70-84 range
        "adjustmentPercent": 0,
        "reasoning": "Your readiness (77) is in the healthy baseline range. Maintaining standard daily target.",
        "energyContext": energy_context
    }

    print(f"✅ Daily Goal Adjusted:")
    print(f"   🎯 Original Target: {adjustment['originalTarget']} points")
    print(f"   🎯 Adjusted Target: {adjustment['adjustedTarget']} points")
    print(f"   📈 Adjustment: {adjustment['adjustmentPercent']:+d}%")
    print(f"\n   💡 Coach Says:")
    print(f"   \"{adjustment['reasoning']}\"")

    return adjustment


def get_task_recommendations(energy_context: dict, limit: int = 8) -> list:
    """
    Step 3: Get energy-matched task recommendations

    Uses workos_get_energy_aware_tasks to get tasks ranked by how well
    they match your current energy level.

    Args:
        energy_context: Current energy context
        limit: Maximum number of tasks to return

    Returns:
        list: Ranked tasks with energy scores and match reasoning
    """
    print_header("STEP 3: Get Energy-Matched Task Recommendations")

    # Simulate MCP tool call: workos_get_energy_aware_tasks
    mcp_request = {
        "tool": "workos_get_energy_aware_tasks",
        "args": {
            "limit": limit
        }
    }

    print(f"🧠 Finding tasks that match your {energy_context['energyLevel']} energy...\n")

    # Simulated response - medium energy scenario
    tasks = [
        {
            "id": 42,
            "title": "Update API documentation",
            "cognitiveLoad": "medium",
            "valueTier": "progress",
            "estimatedHours": 3.0,
            "energyScore": 125,
            "matchReason": "Perfect match: Medium cognitive load for medium energy. Bonus: Progress tasks ideal for medium energy (+20)."
        },
        {
            "id": 38,
            "title": "Review pull request #247",
            "cognitiveLoad": "medium",
            "valueTier": "progress",
            "estimatedHours": 1.5,
            "energyScore": 120,
            "matchReason": "Perfect match: Medium cognitive load for medium energy. Bonus: Quick win for building momentum (+15)."
        },
        {
            "id": 55,
            "title": "Refactor authentication module",
            "cognitiveLoad": "high",
            "valueTier": "deliverable",
            "estimatedHours": 6.0,
            "energyScore": 70,
            "matchReason": "Acceptable match: High cognitive load tasks doable on medium energy. Best saved for high-energy days."
        },
        {
            "id": 29,
            "title": "Respond to client emails",
            "cognitiveLoad": "low",
            "valueTier": "checkbox",
            "estimatedHours": 1.0,
            "energyScore": 65,
            "matchReason": "Acceptable match: Low cognitive load tasks okay on medium energy. Great for afternoon energy dip."
        },
        {
            "id": 51,
            "title": "Write unit tests for payment service",
            "cognitiveLoad": "medium",
            "valueTier": "progress",
            "estimatedHours": 4.0,
            "energyScore": 105,
            "matchReason": "Perfect match: Medium cognitive load for medium energy."
        }
    ]

    print(f"✅ Found {len(tasks)} tasks ranked by energy match:\n")

    for i, task in enumerate(tasks[:5], 1):
        print(f"{i}. [{task['cognitiveLoad'].upper()}] {task['title']}")
        print(f"   Score: {task['energyScore']}/165 | ~{task['estimatedHours']}h | {task['valueTier']}")
        print(f"   💡 {task['matchReason']}")
        print()

    return tasks


def plan_your_day(tasks: list, goal_adjustment: dict) -> None:
    """
    Step 4: Review and plan your day

    Provides recommendations and next steps based on energy context
    and available tasks.

    Args:
        tasks: Energy-matched task recommendations
        goal_adjustment: Daily goal adjustment details
    """
    print_header("STEP 4: Plan Your Day")

    energy_level = goal_adjustment['energyContext']['energyLevel']
    target = goal_adjustment['adjustedTarget']

    print(f"📋 Your Energy-Aware Plan:\n")

    # Energy-specific recommendations
    if energy_level == "high":
        print("🚀 HIGH ENERGY DAY:")
        print("   • Tackle complex, high-cognitive load tasks first")
        print("   • This is your time for deep work and milestone progress")
        print("   • Schedule important meetings or creative work")
        print("   • Push for deliverables and difficult problems")
    elif energy_level == "medium":
        print("⚡ MEDIUM ENERGY DAY:")
        print("   • Focus on steady progress tasks")
        print("   • Mix of cognitive work and lighter tasks")
        print("   • Good day for documentation, reviews, and refactoring")
        print("   • Save complex problems for high-energy days")
    else:
        print("🌱 LOW ENERGY DAY:")
        print("   • Prioritize quick wins and low cognitive load tasks")
        print("   • Admin work, emails, simple bug fixes")
        print("   • Build momentum with small completions")
        print("   • Be gentle with yourself - recovery is productive")

    print(f"\n🎯 Target for Today: {target} points")
    print(f"\n💪 Recommended Focus:")
    print(f"   1. Start with: {tasks[0]['title']}")
    print(f"   2. Then try: {tasks[1]['title']}")
    print(f"   3. If energy shifts, check: {tasks[2]['title']}")

    print(f"\n📌 Pro Tips:")
    print(f"   • Take breaks every 45-90 minutes")
    print(f"   • If energy changes, run this script again for fresh recommendations")
    print(f"   • Override with workos_override_energy_suggestion if meds kick in")
    print(f"   • Provide feedback after completing tasks to improve future suggestions")


def main():
    """Run the complete morning routine workflow."""
    print("\n" + "🌅 ENERGY-AWARE MORNING ROUTINE".center(70))
    print("Optimize your day based on your current energy level\n")

    try:
        # Step 1: Check energy context
        energy_context = check_energy_context()

        # Step 2: Adjust daily goal
        goal_adjustment = adjust_daily_goal(energy_context)

        # Step 3: Get task recommendations
        tasks = get_task_recommendations(energy_context)

        # Step 4: Plan your day
        plan_your_day(tasks, goal_adjustment)

        print_header("✨ Morning Routine Complete!")
        print("💡 Next Steps:")
        print("   1. Start working on your top-ranked task")
        print("   2. Check in mid-day if energy shifts")
        print("   3. Run daily summary tonight to track progress")
        print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Make sure the Thanos MCP server is running and Oura data is synced.\n")


if __name__ == "__main__":
    main()
