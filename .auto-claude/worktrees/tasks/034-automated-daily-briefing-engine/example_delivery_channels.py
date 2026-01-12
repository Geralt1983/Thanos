"""
Example usage of DeliveryChannels for briefing delivery.

This script demonstrates how to use the various delivery channels
(CLI, File, Notification) to deliver briefing content.

Run this script to test the delivery channel implementations:
    python example_delivery_channels.py
"""

import sys
import os
from pathlib import Path

# Add Tools to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from Tools.delivery_channels import (
    CLIChannel,
    FileChannel,
    NotificationChannel,
    create_delivery_channel,
    deliver_to_channels
)


def example_1_cli_channel():
    """Example 1: Using CLIChannel to print briefing to terminal."""
    print("\n" + "="*80)
    print("EXAMPLE 1: CLI Channel with Color")
    print("="*80)

    content = """# Morning Briefing

## Top Priorities
1. Complete project architecture design
2. Review pull requests from team
3. Update documentation

## Quick Wins
- Respond to urgent emails
- Schedule weekly team meeting

## Energy Assessment
Current energy: 7/10
Recommendation: Good time for deep work
"""

    cli_channel = CLIChannel(config={'color': True})
    success = cli_channel.deliver(content, "morning")

    print(f"\nDelivery status: {'✓ SUCCESS' if success else '✗ FAILED'}")


def example_2_file_channel():
    """Example 2: Using FileChannel to save briefing to disk."""
    print("\n" + "="*80)
    print("EXAMPLE 2: File Channel")
    print("="*80)

    content = """# Evening Briefing

## Today's Accomplishments
- ✓ Completed 3 high-priority tasks
- ✓ Attended 2 important meetings
- ✓ Responded to all critical emails

## Tomorrow's Focus
1. Morning: Deep work on feature implementation
2. Afternoon: Team collaboration session

## Energy Reflection
Morning energy: 8/10
Evening energy: 5/10
Overall: Productive day!
"""

    file_channel = FileChannel(config={
        'output_dir': 'History/DailyBriefings',
        'filename_pattern': '{date}_{type}_briefing.md'
    })

    metadata = {'date': '2026-01-11'}
    success = file_channel.deliver(content, "evening", metadata)

    print(f"Delivery status: {'✓ SUCCESS' if success else '✗ FAILED'}")

    if success:
        expected_file = Path('History/DailyBriefings/2026-01-11_evening_briefing.md')
        print(f"File saved to: {expected_file}")
        if expected_file.exists():
            print(f"File size: {expected_file.stat().st_size} bytes")


def example_3_notification_channel():
    """Example 3: Using NotificationChannel for desktop notifications."""
    print("\n" + "="*80)
    print("EXAMPLE 3: Notification Channel")
    print("="*80)

    content = """# Morning Briefing

Top priorities for today:
1. Design review meeting at 10am
2. Complete urgent bug fix
3. Prepare presentation for stakeholders
"""

    notification_channel = NotificationChannel(config={'summary_only': True})

    print(f"Notification system available: {notification_channel.notification_available}")

    metadata = {
        'priorities': [
            {'title': 'Design review meeting at 10am'},
            {'title': 'Complete urgent bug fix'},
            {'title': 'Prepare presentation for stakeholders'}
        ]
    }

    success = notification_channel.deliver(content, "morning", metadata)

    print(f"Delivery status: {'✓ SUCCESS' if success else '✗ FAILED'}")

    if not notification_channel.notification_available:
        print("\nNote: Notifications not available on this system.")
        print("Install terminal-notifier (macOS) or notify-send (Linux) to enable.")


def example_4_factory_function():
    """Example 4: Using factory function to create channels."""
    print("\n" + "="*80)
    print("EXAMPLE 4: Channel Factory Function")
    print("="*80)

    content = "# Test Briefing\n\nThis is a test briefing created using the factory function."

    # Create channels using factory
    channels = {
        'cli': create_delivery_channel('cli', {'color': False}),
        'file': create_delivery_channel('file', {
            'output_dir': 'History/DailyBriefings',
            'filename_pattern': 'test_{type}_briefing.md'
        })
    }

    print("\nCreated channels:")
    for name, channel in channels.items():
        print(f"  - {name}: {channel.__class__.__name__}")

    # Deliver to CLI channel only
    if channels['cli']:
        success = channels['cli'].deliver(content, "test")
        print(f"\nCLI delivery: {'✓ SUCCESS' if success else '✗ FAILED'}")


def example_5_multi_channel_delivery():
    """Example 5: Deliver to multiple channels simultaneously."""
    print("\n" + "="*80)
    print("EXAMPLE 5: Multi-Channel Delivery")
    print("="*80)

    content = """# Multi-Channel Test Briefing

## Status
This briefing is being delivered through multiple channels simultaneously:
- CLI (terminal output)
- File (saved to History/DailyBriefings)
- Notification (desktop notification, if available)

## Test Results
All channels should receive this content.
"""

    channels_config = {
        'cli': {
            'enabled': True,
            'color': False  # Disable color for clearer test output
        },
        'file': {
            'enabled': True,
            'output_dir': 'History/DailyBriefings',
            'filename_pattern': '{date}_{type}_multi_channel.md'
        },
        'notification': {
            'enabled': True,
            'summary_only': True
        }
    }

    metadata = {
        'date': '2026-01-11',
        'priorities': [
            {'title': 'Multi-channel delivery test'},
            {'title': 'Verify all channels working'},
            {'title': 'Check delivery results'}
        ]
    }

    results = deliver_to_channels(content, "test", channels_config, metadata)

    print("\nDelivery Results:")
    for channel, success in results.items():
        status = '✓ SUCCESS' if success else '✗ FAILED'
        print(f"  {channel}: {status}")


def example_6_custom_configuration():
    """Example 6: Custom channel configuration from briefing_schedule.json."""
    print("\n" + "="*80)
    print("EXAMPLE 6: Configuration from briefing_schedule.json")
    print("="*80)

    # Load configuration from briefing_schedule.json
    import json

    config_path = Path('config/briefing_schedule.json')

    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        print("Using default configuration instead.")
        delivery_config = {
            'cli': {'enabled': True, 'color': True},
            'file': {'enabled': True, 'output_dir': 'History/DailyBriefings'}
        }
    else:
        with open(config_path, 'r') as f:
            schedule_config = json.load(f)

        delivery_config = schedule_config.get('delivery', {})
        print(f"Loaded configuration from: {config_path}")

    content = """# Configuration Test Briefing

This briefing uses delivery channel settings from briefing_schedule.json.

## Configured Channels
The enabled channels are determined by the configuration file.
"""

    # Filter to only enabled channels
    enabled_channels = {
        channel_type: config
        for channel_type, config in delivery_config.items()
        if config.get('enabled', False)
    }

    print(f"\nEnabled channels: {', '.join(enabled_channels.keys())}")

    results = deliver_to_channels(
        content,
        "config_test",
        enabled_channels,
        metadata={'date': '2026-01-11'}
    )

    print("\nDelivery Results:")
    for channel, success in results.items():
        status = '✓ SUCCESS' if success else '✗ FAILED'
        print(f"  {channel}: {status}")


def main():
    """Run all examples."""
    print("\n" + "="*80)
    print("DELIVERY CHANNELS DEMONSTRATION")
    print("="*80)
    print("\nThis script demonstrates the DeliveryChannel abstraction and implementations.")
    print("Each example shows a different aspect of the delivery system.\n")

    examples = [
        ("CLI Channel with Color", example_1_cli_channel),
        ("File Channel", example_2_file_channel),
        ("Notification Channel", example_3_notification_channel),
        ("Factory Function", example_4_factory_function),
        ("Multi-Channel Delivery", example_5_multi_channel_delivery),
        ("Custom Configuration", example_6_custom_configuration),
    ]

    for i, (title, example_func) in enumerate(examples, 1):
        try:
            example_func()
        except Exception as e:
            print(f"\n✗ Example {i} failed with error: {e}")
            import traceback
            traceback.print_exc()

        print()  # Add spacing between examples

    print("="*80)
    print("DEMONSTRATION COMPLETE")
    print("="*80)
    print("\nCheck the following locations:")
    print("  - Terminal output above for CLI deliveries")
    print("  - History/DailyBriefings/ for saved files")
    print("  - Desktop notifications (if system supports them)")


if __name__ == '__main__':
    main()
