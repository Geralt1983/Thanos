"""
Example: Adaptive Briefing Content Based on Recent Activity

This script demonstrates how the BriefingEngine adapts briefing content based on:
1. Inactivity (3+ days without activity) → gentle reentry
2. High activity (15+ activities in 7 days) → concise briefing
3. Many overdue tasks (5+ tasks) → catch-up focus
4. Normal activity → standard briefing

The adaptive content includes:
- Mode detection (reentry/concise/catchup/normal)
- Activity metrics (days inactive, recent activities, overdue tasks)
- Human-readable reasoning
- Contextual recommendations
"""

import sys
import os
import tempfile
import shutil
import json
from pathlib import Path
from datetime import datetime, date, timedelta

# Add Tools to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from Tools.briefing_engine import BriefingEngine


def setup_test_environment():
    """Create a temporary test environment."""
    temp_dir = tempfile.mkdtemp()
    state_dir = Path(temp_dir) / "State"
    state_dir.mkdir(parents=True, exist_ok=True)

    # Create basic State files
    (state_dir / "Commitments.md").write_text("# Commitments\n")
    (state_dir / "ThisWeek.md").write_text("# This Week\n")
    (state_dir / "CurrentFocus.md").write_text("# Current Focus\n")

    return temp_dir, state_dir


def cleanup_test_environment(temp_dir):
    """Clean up the test environment."""
    shutil.rmtree(temp_dir)


def example_1_normal_mode():
    """Example 1: Normal mode - regular activity pattern."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Normal Mode (Regular Activity)")
    print("=" * 80)

    temp_dir, state_dir = setup_test_environment()

    try:
        # Initialize engine with patterns enabled
        config = {"patterns": {"enabled": True}}
        engine = BriefingEngine(state_dir=str(state_dir), config=config)

        # Track a recent briefing (today)
        engine._track_briefing_activity("morning")

        # Get adaptive mode
        context = engine.gather_context()
        result = engine.get_adaptive_briefing_mode(context)

        print("\n📊 Adaptive Mode Analysis:")
        print(f"  Mode: {result['mode']}")
        print(f"  Days Inactive: {result['days_inactive']}")
        print(f"  Recent Activities: {result['recent_activities']}")
        print(f"  Overdue Tasks: {result['overdue_tasks']}")
        print(f"\n💡 Reasoning: {result['reasoning']}")

        if result['recommendations']:
            print("\n✨ Recommendations:")
            for rec in result['recommendations']:
                print(f"  - {rec}")

        print("\n🎯 Observation:")
        print("  Normal mode provides standard briefing content with all sections.")
        print("  No special adaptations or warnings.")

    finally:
        cleanup_test_environment(temp_dir)


def example_2_reentry_mode():
    """Example 2: Reentry mode - inactive for 5 days."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Reentry Mode (Inactive for 5 Days)")
    print("=" * 80)

    temp_dir, state_dir = setup_test_environment()

    try:
        # Initialize engine
        config = {"patterns": {"enabled": True}}
        engine = BriefingEngine(state_dir=str(state_dir), config=config)

        # Create old activity (5 days ago)
        activity_file = state_dir / ".briefing_activity.json"
        old_date = (engine.today - timedelta(days=5)).isoformat()
        activity_data = {
            "briefings": [{
                "date": old_date,
                "type": "morning",
                "timestamp": datetime.now().isoformat()
            }],
            "metadata": {"last_updated": datetime.now().isoformat()}
        }
        with open(activity_file, 'w') as f:
            json.dump(activity_data, f, indent=2)

        # Get adaptive mode
        context = engine.gather_context()
        result = engine.get_adaptive_briefing_mode(context)

        print("\n📊 Adaptive Mode Analysis:")
        print(f"  Mode: {result['mode']}")
        print(f"  Days Inactive: {result['days_inactive']}")
        print(f"  Recent Activities: {result['recent_activities']}")
        print(f"  Overdue Tasks: {result['overdue_tasks']}")
        print(f"\n💡 Reasoning: {result['reasoning']}")

        if result['recommendations']:
            print("\n✨ Recommendations:")
            for rec in result['recommendations']:
                print(f"  - {rec}")

        print("\n🎯 Observation:")
        print("  Reentry mode provides gentle welcome-back messaging.")
        print("  Encourages starting with quick wins and not overwhelming.")
        print("  Focus on understanding current state before diving into tasks.")

    finally:
        cleanup_test_environment(temp_dir)


def example_3_catchup_mode():
    """Example 3: Catch-up mode - many overdue tasks."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Catch-up Mode (Many Overdue Tasks)")
    print("=" * 80)

    temp_dir, state_dir = setup_test_environment()

    try:
        # Initialize engine
        config = {"patterns": {"enabled": True}}
        engine = BriefingEngine(state_dir=str(state_dir), config=config)

        # Create many overdue tasks
        past_date = (engine.today - timedelta(days=5)).isoformat()
        content = f"""# Commitments

## Work
- [ ] Overdue task 1 (due: {past_date})
- [ ] Overdue task 2 (due: {past_date})
- [ ] Overdue task 3 (due: {past_date})
- [ ] Overdue task 4 (due: {past_date})
- [ ] Overdue task 5 (due: {past_date})
- [ ] Overdue task 6 (due: {past_date})
- [ ] Overdue task 7 (due: {past_date})

## Personal
- [ ] Overdue personal task (due: {past_date})
"""
        (state_dir / "Commitments.md").write_text(content)

        # Track recent activity to avoid reentry mode
        engine._track_briefing_activity("morning")

        # Get adaptive mode
        context = engine.gather_context()
        result = engine.get_adaptive_briefing_mode(context)

        print("\n📊 Adaptive Mode Analysis:")
        print(f"  Mode: {result['mode']}")
        print(f"  Days Inactive: {result['days_inactive']}")
        print(f"  Recent Activities: {result['recent_activities']}")
        print(f"  Overdue Tasks: {result['overdue_tasks']}")
        print(f"\n💡 Reasoning: {result['reasoning']}")

        if result['recommendations']:
            print("\n✨ Recommendations:")
            for rec in result['recommendations']:
                print(f"  - {rec}")

        print("\n🎯 Observation:")
        print("  Catch-up mode focuses on helping user address overdue items.")
        print("  Provides practical advice for managing overwhelm.")
        print("  Suggests breaking tasks down and setting realistic goals.")
        print("  Encourages prioritization and rescheduling less urgent items.")

    finally:
        cleanup_test_environment(temp_dir)


def example_4_concise_mode():
    """Example 4: Concise mode - high activity."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Concise Mode (High Activity)")
    print("=" * 80)

    temp_dir, state_dir = setup_test_environment()

    try:
        # Initialize engine
        config = {"patterns": {"enabled": True}}
        engine = BriefingEngine(state_dir=str(state_dir), config=config)

        # Create many recent activities
        if engine.pattern_analyzer:
            for i in range(20):
                days_ago = i % 7  # Spread across last 7 days
                completion_date = engine.today - timedelta(days=days_ago)
                engine.pattern_analyzer.record_task_completion(
                    f"Completed task {i}",
                    task_category="work",
                    completion_date=completion_date
                )

        # Get adaptive mode
        context = engine.gather_context()
        result = engine.get_adaptive_briefing_mode(context)

        print("\n📊 Adaptive Mode Analysis:")
        print(f"  Mode: {result['mode']}")
        print(f"  Days Inactive: {result['days_inactive']}")
        print(f"  Recent Activities: {result['recent_activities']}")
        print(f"  Overdue Tasks: {result['overdue_tasks']}")
        print(f"\n💡 Reasoning: {result['reasoning']}")

        if result['recommendations']:
            print("\n✨ Recommendations:")
            for rec in result['recommendations']:
                print(f"  - {rec}")

        print("\n🎯 Observation:")
        print("  Concise mode recognizes user is in productive flow.")
        print("  Provides quick, streamlined briefing to maintain momentum.")
        print("  Reminds user to balance productivity with rest.")
        print("  Watches for signs of burnout.")

    finally:
        cleanup_test_environment(temp_dir)


def example_5_priority_order():
    """Example 5: Mode priority order - inactivity takes precedence."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Mode Priority Order (Inactivity > Catchup > Concise)")
    print("=" * 80)

    temp_dir, state_dir = setup_test_environment()

    try:
        # Initialize engine
        config = {"patterns": {"enabled": True}}
        engine = BriefingEngine(state_dir=str(state_dir), config=config)

        # Create conditions for ALL modes:
        # 1. Old activity (for reentry)
        activity_file = state_dir / ".briefing_activity.json"
        old_date = (engine.today - timedelta(days=5)).isoformat()
        activity_data = {
            "briefings": [{
                "date": old_date,
                "type": "morning",
                "timestamp": datetime.now().isoformat()
            }],
            "metadata": {"last_updated": datetime.now().isoformat()}
        }
        with open(activity_file, 'w') as f:
            json.dump(activity_data, f, indent=2)

        # 2. Overdue tasks (for catchup)
        past_date = (engine.today - timedelta(days=3)).isoformat()
        content = f"""# Commitments

## Work
- [ ] Overdue 1 (due: {past_date})
- [ ] Overdue 2 (due: {past_date})
- [ ] Overdue 3 (due: {past_date})
- [ ] Overdue 4 (due: {past_date})
- [ ] Overdue 5 (due: {past_date})
- [ ] Overdue 6 (due: {past_date})
"""
        (state_dir / "Commitments.md").write_text(content)

        # Get adaptive mode
        context = engine.gather_context()
        result = engine.get_adaptive_briefing_mode(context)

        print("\n📊 Conditions Present:")
        print(f"  ✓ Inactivity: {result['days_inactive']} days (triggers reentry)")
        print(f"  ✓ Overdue Tasks: {result['overdue_tasks']} tasks (would trigger catchup)")
        print()
        print(f"🎯 Selected Mode: {result['mode']}")
        print(f"\n💡 Reasoning: {result['reasoning']}")

        print("\n🎯 Observation:")
        print("  When multiple conditions are present, priority order is:")
        print("  1. Inactivity (reentry) - most important for returning users")
        print("  2. Overdue tasks (catchup) - helps with overwhelm")
        print("  3. High activity (concise) - optimizes for productivity")
        print("  4. Normal - default mode")

    finally:
        cleanup_test_environment(temp_dir)


def example_6_template_integration():
    """Example 6: Adaptive mode integration in templates."""
    print("\n" + "=" * 80)
    print("EXAMPLE 6: Template Integration (Adaptive Mode in Briefing)")
    print("=" * 80)

    temp_dir, state_dir = setup_test_environment()

    try:
        # Initialize engine
        config = {"patterns": {"enabled": True}}
        engine = BriefingEngine(state_dir=str(state_dir), config=config)

        # Create old activity for reentry mode
        activity_file = state_dir / ".briefing_activity.json"
        old_date = (engine.today - timedelta(days=4)).isoformat()
        activity_data = {
            "briefings": [{
                "date": old_date,
                "type": "morning",
                "timestamp": datetime.now().isoformat()
            }],
            "metadata": {"last_updated": datetime.now().isoformat()}
        }
        with open(activity_file, 'w') as f:
            json.dump(activity_data, f, indent=2)

        # Get template data (includes adaptive mode automatically)
        context = engine.gather_context()
        template_data = engine._prepare_template_data(context, "morning")

        print("\n📊 Template Data Includes Adaptive Mode:")
        print(f"  adaptive_mode present: {'adaptive_mode' in template_data}")
        print(f"  Mode: {template_data['adaptive_mode']['mode']}")
        print(f"  Reasoning: {template_data['adaptive_mode']['reasoning']}")

        print("\n📝 Template Usage Example:")
        print("  In Templates/briefing_morning.md:")
        print("  {% if adaptive_mode %}")
        print("  ## 🔄 Briefing Adaptation")
        print("  **{{ adaptive_mode.reasoning }}**")
        print("  {% if adaptive_mode.recommendations %}")
        print("  **Recommendations:**")
        print("  {% for rec in adaptive_mode.recommendations %}")
        print("  - {{ rec }}")
        print("  {% endfor %}")
        print("  {% endif %}")
        print("  {% endif %}")

        print("\n🎯 Observation:")
        print("  Adaptive mode is automatically included in template data.")
        print("  Templates can conditionally display adaptive content.")
        print("  No manual intervention required - it's seamlessly integrated.")

    finally:
        cleanup_test_environment(temp_dir)


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("ADAPTIVE BRIEFING CONTENT EXAMPLES")
    print("Demonstrating intelligent briefing adaptation based on activity patterns")
    print("=" * 80)

    example_1_normal_mode()
    example_2_reentry_mode()
    example_3_catchup_mode()
    example_4_concise_mode()
    example_5_priority_order()
    example_6_template_integration()

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("""
The adaptive briefing system provides:

1. **Inactivity Detection (Reentry Mode)**
   - Triggers after 3+ days without activity
   - Gentle welcome-back messaging
   - Encourages starting with quick wins
   - Focus on understanding current state

2. **Overdue Task Detection (Catch-up Mode)**
   - Triggers with 5+ overdue tasks
   - Helps manage overwhelm
   - Suggests prioritization and rescheduling
   - Breaks down large tasks

3. **High Activity Detection (Concise Mode)**
   - Triggers with 15+ activities in 7 days
   - Streamlined, concise briefing
   - Maintains productivity momentum
   - Reminds about rest and balance

4. **Normal Mode**
   - Standard briefing for regular activity
   - All sections included
   - No special adaptations

The system automatically tracks activity and adapts briefings without
any manual configuration. It's designed to be helpful, not intrusive,
with ADHD-friendly messaging that reduces cognitive load.
""")


if __name__ == "__main__":
    main()
