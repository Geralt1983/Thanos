#!/usr/bin/env python3
"""
Task Creation with Cognitive Load Example

This script demonstrates how to create tasks with appropriate cognitive load
labels, enabling the energy-aware prioritization system to match them to your
energy levels.

Workflow:
1. Create a high cognitive load task (complex work)
2. Create a medium cognitive load task (moderate work)
3. Create a low cognitive load task (admin work)
4. Update an existing task's cognitive load
5. Query energy-aware recommendations

Usage:
    python 02_task_creation_with_cognitive_load.py

Requirements:
    - Thanos MCP server running
"""

import json
from datetime import datetime


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def print_cognitive_load_guide() -> None:
    """Display the cognitive load selection guide."""
    print_header("COGNITIVE LOAD GUIDE")

    print("How to choose cognitive load for your tasks:\n")

    print("🔴 HIGH COGNITIVE LOAD:")
    print("   • Deep thinking, complex problem-solving")
    print("   • Architecture decisions, system design")
    print("   • Learning new concepts or technologies")
    print("   • Creative work requiring focus")
    print("   • Writing complex code from scratch")
    print("   Examples: 'Architect microservice', 'Debug memory leak', 'Design API'\n")

    print("🟡 MEDIUM COGNITIVE LOAD:")
    print("   • Moderate focus required")
    print("   • Following established patterns")
    print("   • Code reviews, documentation")
    print("   • Refactoring with clear goals")
    print("   • Testing and debugging known issues")
    print("   Examples: 'Write tests', 'Update docs', 'Refactor module'\n")

    print("🟢 LOW COGNITIVE LOAD:")
    print("   • Routine, repetitive tasks")
    print("   • Administrative work")
    print("   • Simple updates or fixes")
    print("   • Communication tasks")
    print("   • Organizational work")
    print("   Examples: 'Respond to emails', 'Update dependencies', 'File tickets'\n")


def create_high_cognitive_task() -> dict:
    """
    Example 1: Create a high cognitive load task

    This type of task requires deep focus and is best suited for high-energy days.
    """
    print_header("EXAMPLE 1: High Cognitive Load Task")

    task_data = {
        "title": "Architect real-time notification system",
        "description": "Design and implement a scalable WebSocket-based notification system with Redis pub/sub for multi-server support. Need to consider connection management, reconnection logic, and message queuing.",
        "cognitiveLoad": "high",
        "valueTier": "milestone",
        "drainType": "deep",
        "estimatedHours": 8.0,
        "category": "work"
    }

    # Simulate MCP tool call: workos_create_task
    mcp_request = {
        "tool": "workos_create_task",
        "args": task_data
    }

    print("Creating task with HIGH cognitive load...\n")
    print(f"📝 Task: {task_data['title']}")
    print(f"🔴 Cognitive Load: {task_data['cognitiveLoad']}")
    print(f"💎 Value Tier: {task_data['valueTier']}")
    print(f"⏱️  Estimated: {task_data['estimatedHours']} hours")
    print(f"🧠 Drain Type: {task_data['drainType']}")

    # Simulated response
    created_task = {
        "id": 101,
        **task_data,
        "status": "ready",
        "createdAt": datetime.now().isoformat()
    }

    print(f"\n✅ Task created with ID: {created_task['id']}")
    print(f"\n💡 Best scheduled for: HIGH energy days (readiness >= 85)")
    print(f"   This task will score highest when you're at peak performance.")

    return created_task


def create_medium_cognitive_task() -> dict:
    """
    Example 2: Create a medium cognitive load task

    This type of task requires moderate focus and works well on medium-energy days.
    """
    print_header("EXAMPLE 2: Medium Cognitive Load Task")

    task_data = {
        "title": "Write integration tests for payment API",
        "description": "Add comprehensive integration tests for the payment processing endpoints. Cover happy path, error cases, and edge cases. Follow existing test patterns in tests/integration/.",
        "cognitiveLoad": "medium",
        "valueTier": "progress",
        "drainType": "shallow",
        "estimatedHours": 3.0,
        "category": "work"
    }

    # Simulate MCP tool call: workos_create_task
    mcp_request = {
        "tool": "workos_create_task",
        "args": task_data
    }

    print("Creating task with MEDIUM cognitive load...\n")
    print(f"📝 Task: {task_data['title']}")
    print(f"🟡 Cognitive Load: {task_data['cognitiveLoad']}")
    print(f"💎 Value Tier: {task_data['valueTier']}")
    print(f"⏱️  Estimated: {task_data['estimatedHours']} hours")
    print(f"🧠 Drain Type: {task_data['drainType']}")

    # Simulated response
    created_task = {
        "id": 102,
        **task_data,
        "status": "ready",
        "createdAt": datetime.now().isoformat()
    }

    print(f"\n✅ Task created with ID: {created_task['id']}")
    print(f"\n💡 Best scheduled for: MEDIUM energy days (readiness 70-84)")
    print(f"   Solid progress work that doesn't require peak performance.")

    return created_task


def create_low_cognitive_task() -> dict:
    """
    Example 3: Create a low cognitive load task

    This type of task is routine/admin work, perfect for low-energy days.
    """
    print_header("EXAMPLE 3: Low Cognitive Load Task")

    task_data = {
        "title": "Update project dependencies",
        "description": "Run npm audit and update all dependencies to latest stable versions. Test locally to ensure nothing breaks. Update changelog with dependency versions.",
        "cognitiveLoad": "low",
        "valueTier": "checkbox",
        "drainType": "admin",
        "estimatedHours": 1.0,
        "category": "work"
    }

    # Simulate MCP tool call: workos_create_task
    mcp_request = {
        "tool": "workos_create_task",
        "args": task_data
    }

    print("Creating task with LOW cognitive load...\n")
    print(f"📝 Task: {task_data['title']}")
    print(f"🟢 Cognitive Load: {task_data['cognitiveLoad']}")
    print(f"💎 Value Tier: {task_data['valueTier']}")
    print(f"⏱️  Estimated: {task_data['estimatedHours']} hour")
    print(f"🧠 Drain Type: {task_data['drainType']}")

    # Simulated response
    created_task = {
        "id": 103,
        **task_data,
        "status": "ready",
        "createdAt": datetime.now().isoformat()
    }

    print(f"\n✅ Task created with ID: {created_task['id']}")
    print(f"\n💡 Best scheduled for: LOW energy days (readiness < 70)")
    print(f"   Perfect for recovery days or afternoon energy dips.")
    print(f"   Quick win to build momentum!")

    return created_task


def update_task_cognitive_load(task_id: int, old_load: str, new_load: str) -> dict:
    """
    Example 4: Update cognitive load on existing task

    Sometimes you realize a task is more or less complex than initially thought.
    """
    print_header("EXAMPLE 4: Update Existing Task Cognitive Load")

    print(f"Updating task #{task_id} cognitive load...")
    print(f"   From: {old_load.upper()} → To: {new_load.upper()}\n")

    # Simulate MCP tool call: workos_update_task
    mcp_request = {
        "tool": "workos_update_task",
        "args": {
            "taskId": task_id,
            "cognitiveLoad": new_load
        }
    }

    print(f"💡 Reason: After breaking down the requirements, this task is")
    print(f"   actually {new_load} cognitive load, not {old_load}.")

    # Simulated response
    updated_task = {
        "id": task_id,
        "cognitiveLoad": new_load,
        "updatedAt": datetime.now().isoformat()
    }

    print(f"\n✅ Task #{task_id} updated successfully")
    print(f"   New cognitive load: {new_load.upper()}")
    print(f"\n📊 This will affect when the task appears in energy-aware recommendations.")

    return updated_task


def query_energy_aware_recommendations() -> None:
    """
    Example 5: See how cognitive load affects recommendations

    Query energy-aware tasks to see how the system prioritizes based on
    the cognitive load labels we just set.
    """
    print_header("EXAMPLE 5: Energy-Aware Recommendations")

    print("Simulating different energy scenarios to show task prioritization...\n")

    # Scenario 1: High Energy
    print("🚀 SCENARIO 1: High Energy Day (Readiness 90)")
    print("-" * 70)
    print("Top recommendations:")
    print("  1. [HIGH] Architect real-time notification system (Score: 138)")
    print("     → Perfect match + Milestone bonus")
    print("  2. [MEDIUM] Write integration tests for payment API (Score: 70)")
    print("     → Acceptable match for high energy")
    print("  3. [LOW] Update project dependencies (Score: 15)")
    print("     → Poor match, save for low energy day")

    # Scenario 2: Medium Energy
    print("\n⚡ SCENARIO 2: Medium Energy Day (Readiness 77)")
    print("-" * 70)
    print("Top recommendations:")
    print("  1. [MEDIUM] Write integration tests for payment API (Score: 125)")
    print("     → Perfect match + Progress bonus")
    print("  2. [HIGH] Architect real-time notification system (Score: 70)")
    print("     → Acceptable match, doable but not optimal")
    print("  3. [LOW] Update project dependencies (Score: 65)")
    print("     → Acceptable match, good for afternoon")

    # Scenario 3: Low Energy
    print("\n🌱 SCENARIO 3: Low Energy Day (Readiness 62)")
    print("-" * 70)
    print("Top recommendations:")
    print("  1. [LOW] Update project dependencies (Score: 140)")
    print("     → Perfect match + Checkbox bonus + Quick win bonus")
    print("  2. [MEDIUM] Write integration tests for payment API (Score: 50)")
    print("     → Acceptable match if you're feeling okay")
    print("  3. [HIGH] Architect real-time notification system (Score: 0)")
    print("     → Poor match, definitely save for high energy")

    print("\n" + "=" * 70)
    print("💡 Notice how the same tasks are prioritized differently based on")
    print("   your energy level. The system helps you work WITH your brain!")


def main():
    """Run the complete task creation workflow."""
    print("\n" + "📝 TASK CREATION WITH COGNITIVE LOAD".center(70))
    print("Label tasks appropriately for energy-aware prioritization\n")

    try:
        # Show cognitive load guide
        print_cognitive_load_guide()

        input("\nPress Enter to continue with examples...")

        # Example 1: High cognitive load
        high_task = create_high_cognitive_task()

        input("\nPress Enter to continue...")

        # Example 2: Medium cognitive load
        medium_task = create_medium_cognitive_task()

        input("\nPress Enter to continue...")

        # Example 3: Low cognitive load
        low_task = create_low_cognitive_task()

        input("\nPress Enter to continue...")

        # Example 4: Update cognitive load
        update_task_cognitive_load(medium_task['id'], "medium", "low")

        input("\nPress Enter to see energy-aware recommendations...")

        # Example 5: Query recommendations
        query_energy_aware_recommendations()

        print_header("✨ Task Creation Examples Complete!")
        print("🎯 Key Takeaways:")
        print("   1. Always set cognitive load when creating tasks")
        print("   2. High = Deep work, Medium = Steady progress, Low = Admin/routine")
        print("   3. You can update cognitive load if you misjudge initially")
        print("   4. The system uses these labels to match tasks to your energy")
        print("   5. Better labeling = better recommendations!\n")

        print("💡 Pro Tips:")
        print("   • When in doubt, start with 'medium' and adjust after attempting")
        print("   • Break large high-cognitive tasks into medium chunks")
        print("   • Keep a list of low-cognitive tasks for energy dips")
        print("   • Use drainType and valueTier for even better matching\n")

    except KeyboardInterrupt:
        print("\n\n👋 Exiting...\n")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Make sure the Thanos MCP server is running.\n")


if __name__ == "__main__":
    main()
