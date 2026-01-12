#!/usr/bin/env python3
"""
Example demonstrating StateSyncChannel for updating State/Today.md with briefing content.

This example shows how the StateSyncChannel:
1. Creates State/Today.md if it doesn't exist
2. Updates specific sections (Morning Brief, Evening Brief)
3. Preserves existing content in other sections
4. Adds timestamps to track updates
"""

import sys
import os
from pathlib import Path

# Add Tools to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from Tools.delivery_channels import StateSyncChannel, deliver_to_channels


def example_1_create_new_file():
    """Example 1: Create new Today.md with morning briefing."""
    print("=" * 80)
    print("Example 1: Create new Today.md with morning briefing")
    print("=" * 80)

    # Configure channel
    channel = StateSyncChannel(config={'state_file': 'State/Today.md'})

    # Morning briefing content
    morning_content = """**Top 3 Priorities:**
1. Fix critical security bug (due today!)
2. Complete briefing engine implementation
3. Review PR for authentication system

**Quick Wins:**
- Send weekly status update
- Schedule 1-on-1 meetings

**Energy Level:** 7/10 - Good for most tasks
**Peak Focus Time:** 10:00 AM - 12:00 PM (post-medication)
"""

    # Deliver to State/Today.md
    success = channel.deliver(morning_content, 'morning')

    print(f"\nDelivery {'successful' if success else 'failed'}!")
    print(f"Check State/Today.md for the morning briefing.\n")


def example_2_update_existing_section():
    """Example 2: Update existing morning brief section."""
    print("=" * 80)
    print("Example 2: Update existing morning brief (preserves other content)")
    print("=" * 80)

    # Configure channel
    channel = StateSyncChannel(config={'state_file': 'State/Today.md'})

    # Updated morning briefing
    updated_morning = """**Top 3 Priorities:**
1. ✅ Fixed critical security bug (COMPLETED!)
2. Deploy database migration (due tomorrow)
3. Complete briefing engine implementation

**Progress Update:**
- Security bug resolved in commit abc123
- All tests passing
- Ready for deployment

**Energy Level:** 6/10 - Moderate energy, good for admin tasks
"""

    # Update the morning brief section
    success = channel.deliver(updated_morning, 'morning')

    print(f"\nDelivery {'successful' if success else 'failed'}!")
    print(f"Morning brief updated. Other sections preserved.\n")


def example_3_add_evening_brief():
    """Example 3: Add evening brief while preserving morning brief."""
    print("=" * 80)
    print("Example 3: Add evening brief to existing file")
    print("=" * 80)

    # Configure channel
    channel = StateSyncChannel(config={'state_file': 'State/Today.md'})

    # Evening reflection content
    evening_content = """**Today's Accomplishments:**
✅ Fixed critical security bug
✅ Completed briefing engine State sync feature
✅ Reviewed 3 PRs
✅ Attended team standup

**Energy & Productivity:**
- Morning energy: 7/10 → Evening energy: 5/10 (↘️ decrease)
- Significant energy drain after lunch - consider shorter work blocks

**What Went Well:**
- Morning deep work session was very productive
- Clear priorities helped maintain focus
- Medication timing was optimal

**Improvements for Tomorrow:**
- Take a proper lunch break
- Schedule breaks between meetings
- Don't skip afternoon walk

**Tomorrow's Preview:**
1. Deploy database migration (morning)
2. Team retrospective (2pm)
3. Start API architecture design
"""

    # Add evening brief
    success = channel.deliver(evening_content, 'evening')

    print(f"\nDelivery {'successful' if success else 'failed'}!")
    print(f"Evening brief added. Morning brief still intact.\n")


def example_4_multi_channel_delivery():
    """Example 4: Deliver to multiple channels including state sync."""
    print("=" * 80)
    print("Example 4: Multi-channel delivery (CLI + File + State)")
    print("=" * 80)

    # Briefing content
    briefing_content = """**Top 3 Priorities:**
1. Launch automated briefing engine (due Friday!)
2. Complete all code reviews
3. Write comprehensive tests

**Focus Areas:**
- Testing and edge cases
- ADHD-friendly UX improvements
- Documentation updates

**Energy Level:** 8/10 - High energy, ideal for deep work
"""

    # Configure multiple channels
    channels_config = {
        'cli': {
            'enabled': True,
            'color': True
        },
        'state_sync': {
            'enabled': True,
            'state_file': 'State/Today.md'
        },
        'file': {
            'enabled': True,
            'output_dir': 'History/DailyBriefings',
            'filename_pattern': '{date}_{type}_briefing.md'
        }
    }

    # Metadata for the briefing
    metadata = {
        'date': '2026-01-11',
        'priorities': [
            {'title': 'Launch automated briefing engine', 'urgency': 'high'},
            {'title': 'Complete all code reviews', 'urgency': 'medium'},
            {'title': 'Write comprehensive tests', 'urgency': 'medium'}
        ]
    }

    # Deliver to all channels
    results = deliver_to_channels(
        briefing_content,
        'morning',
        channels_config,
        metadata
    )

    print(f"\nDelivery results:")
    for channel, success in results.items():
        status = "✓ Success" if success else "✗ Failed"
        print(f"  {channel}: {status}")
    print()


def example_5_custom_state_file():
    """Example 5: Use custom state file path."""
    print("=" * 80)
    print("Example 5: Custom state file path")
    print("=" * 80)

    # Configure channel with custom path
    channel = StateSyncChannel(config={'state_file': 'State/WorkLog.md'})

    # Work log content
    work_log = """**Development Progress:**
- Implemented StateSyncChannel class
- Added comprehensive test suite (14 tests)
- Updated factory function for channel creation
- All tests passing

**Technical Notes:**
- Section parsing preserves existing content
- Timestamps added automatically
- Maintains consistent section order
- Graceful handling of missing files

**Next Steps:**
- Update documentation
- Create example scripts
- Commit changes
"""

    # Deliver to custom state file
    success = channel.deliver(work_log, 'development')

    print(f"\nDelivery {'successful' if success else 'failed'}!")
    print(f"Check State/WorkLog.md for the work log.\n")


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "StateSyncChannel Examples" + " " * 33 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    try:
        example_1_create_new_file()
        input("Press Enter to continue to Example 2...")

        example_2_update_existing_section()
        input("Press Enter to continue to Example 3...")

        example_3_add_evening_brief()
        input("Press Enter to continue to Example 4...")

        example_4_multi_channel_delivery()
        input("Press Enter to continue to Example 5...")

        example_5_custom_state_file()

        print("=" * 80)
        print("All examples completed!")
        print("=" * 80)
        print("\nKey Features Demonstrated:")
        print("✓ Creates State/Today.md if it doesn't exist")
        print("✓ Updates specific sections (Morning Brief, Evening Brief)")
        print("✓ Preserves existing content in other sections")
        print("✓ Adds timestamps to track when sections were updated")
        print("✓ Maintains consistent section order")
        print("✓ Works with multi-channel delivery")
        print("✓ Supports custom state file paths")
        print()

    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user.")
    except Exception as e:
        print(f"\n\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
