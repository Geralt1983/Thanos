#!/usr/bin/env python3
"""
Example usage of BriefingEngine.

This demonstrates how to use the BriefingEngine to gather context
from State files and generate briefing data.
"""

from Tools.briefing_engine import BriefingEngine
import json


def main():
    """Demonstrate BriefingEngine usage."""

    # Initialize engine (uses ./State by default)
    engine = BriefingEngine()

    # Gather all context
    context = engine.gather_context()

    # Display the gathered context
    print("=" * 60)
    print("DAILY BRIEFING CONTEXT")
    print("=" * 60)
    print(f"\nDate: {context['today_date']}")
    print(f"Day: {context['day_of_week']}")
    print(f"Weekend: {context['is_weekend']}")

    # Show commitments
    print(f"\n--- Commitments ({len(context['commitments'])} total) ---")
    for commitment in context['commitments'][:5]:  # Show first 5
        status = "✓" if commitment['is_complete'] else " "
        deadline = f" (due: {commitment['deadline']})" if commitment['deadline'] else ""
        print(f"  [{status}] {commitment['title']}{deadline}")
        print(f"      Category: {commitment['category']}")

    # Show active commitments only
    active = engine.get_active_commitments(context)
    print(f"\n--- Active Commitments ({len(active)} pending) ---")
    for commitment in active[:3]:  # Show first 3
        deadline = f" (due: {commitment['deadline']})" if commitment['deadline'] else ""
        print(f"  • {commitment['title']}{deadline}")

    # Show this week's tasks
    this_week = context['this_week']
    print(f"\n--- This Week's Goals ({len(this_week['goals'])} total) ---")
    for goal in this_week['goals'][:3]:  # Show first 3
        status = "✓" if goal['is_complete'] else " "
        print(f"  [{status}] {goal['text']}")

    pending_tasks = engine.get_pending_tasks(context)
    print(f"\n--- Pending Tasks ({len(pending_tasks)} remaining) ---")
    for task in pending_tasks[:3]:  # Show first 3
        print(f"  • {task['text']}")

    # Show current focus
    focus = context['current_focus']
    print(f"\n--- Current Focus Areas ---")
    for area in focus['focus_areas'][:3]:  # Show first 3
        print(f"  • {area}")

    print(f"\n--- Top Priorities ---")
    for priority in focus['priorities'][:3]:  # Show first 3
        print(f"  • {priority}")

    # Show metadata
    print(f"\n--- Metadata ---")
    print(f"Generated at: {context['metadata']['generated_at']}")
    print(f"State directory: {context['metadata']['state_dir']}")

    print("\n" + "=" * 60)

    # Optionally output full JSON
    # print("\nFull JSON context:")
    # print(json.dumps(context, indent=2))


if __name__ == "__main__":
    main()
