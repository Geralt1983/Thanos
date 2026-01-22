#!/usr/bin/env python3
"""
Example: How to integrate ThanosVisualState into Thanos workflows.

This demonstrates how to call visual state management from:
- Startup scripts
- Task completion handlers
- Energy level changes
- Time-based transitions
"""

from visuals import ThanosVisualState
from datetime import datetime


def on_session_start():
    """Call this when Thanos session starts."""
    hour = datetime.now().hour

    # Determine context
    context = {
        "time_of_day": "morning" if 5 <= hour < 12 else "afternoon" if 12 <= hour < 17 else "evening",
        "inbox": 0,  # Get from WorkOS
        "tasks_active": 0,  # Get from WorkOS
        "energy_level": "medium",  # Get from Oura
    }

    # Auto-transition to appropriate state
    state = ThanosVisualState.auto_transition(context)
    print(f"Session started in {state} state")


def on_task_completed(task):
    """Call this when a task is completed."""
    # Check if daily goal achieved
    daily_goal_achieved = False  # Check WorkOS metrics

    if daily_goal_achieved:
        ThanosVisualState.set_state("BALANCE")
        print("Daily goal achieved - The Snap is complete")


def on_deep_work_start():
    """Call this when entering deep work/focus mode."""
    ThanosVisualState.set_state("FOCUS")
    print("Entering deep work mode")


def on_brain_dump():
    """Call this during brain dump / inbox processing."""
    ThanosVisualState.set_state("CHAOS")
    print("Processing inbox - embracing the chaos")


def on_energy_change(new_level: str, tasks_active: int):
    """Call this when energy level changes significantly."""
    context = {
        "energy_level": new_level,
        "tasks_active": tasks_active,
        "time_of_day": "afternoon",
    }

    state = ThanosVisualState.auto_transition(context)
    print(f"Energy level changed to {new_level}, state: {state}")


# Example usage in a main script
if __name__ == "__main__":
    print("=== Visual State Integration Examples ===\n")

    # Example 1: Session start
    print("1. Session Start")
    on_session_start()
    print()

    # Example 2: Deep work
    print("2. Starting Deep Work")
    on_deep_work_start()
    print()

    # Example 3: Brain dump
    print("3. Brain Dump Mode")
    on_brain_dump()
    print()

    # Example 4: Task completion
    print("4. Task Completed")
    on_task_completed({"id": 1, "title": "Example Task"})
    print()

    # Example 5: View history
    print("5. State History")
    history = ThanosVisualState.get_state_history(5)
    for entry in history[-5:]:
        ts = datetime.fromisoformat(entry['timestamp'])
        print(f"  {ts.strftime('%H:%M:%S')} → {entry['state']}")
