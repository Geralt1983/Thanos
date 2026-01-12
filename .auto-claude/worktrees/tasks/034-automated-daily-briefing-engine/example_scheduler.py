#!/usr/bin/env python3
"""
Example: BriefingScheduler Usage

Demonstrates how to use the BriefingScheduler daemon for automated briefings.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from Tools.briefing_scheduler import BriefingScheduler


def example_run_once():
    """Example: Run a single check cycle (for cron)."""
    print("="*80)
    print("Example 1: Single Check Cycle (Cron Mode)")
    print("="*80)

    scheduler = BriefingScheduler(
        config_path="config/briefing_schedule.json",
        state_dir="State",
        templates_dir="Templates"
    )

    print("\nRunning single check cycle...")
    scheduler.run_once()
    print("✓ Check complete\n")


def example_check_status():
    """Example: Check scheduler configuration and status."""
    print("="*80)
    print("Example 2: Check Scheduler Configuration")
    print("="*80)

    scheduler = BriefingScheduler(
        config_path="config/briefing_schedule.json",
        state_dir="State",
        templates_dir="Templates"
    )

    print("\nScheduler Configuration:")
    print(f"  Config: {scheduler.config_path}")
    print(f"  State: {scheduler.state_dir}")
    print(f"  Templates: {scheduler.templates_dir}")
    print(f"  Log: {scheduler.config.get('scheduler', {}).get('log_file')}")

    print("\nConfigured Briefings:")
    briefings = scheduler.config.get("briefings", {})
    for briefing_type, config in briefings.items():
        enabled = "✓" if config.get("enabled") else "✗"
        time = config.get("time", "N/A")
        print(f"  [{enabled}] {briefing_type.capitalize()}: {time}")

    print("\nRun State (Today):")
    for briefing_type in briefings.keys():
        has_run = scheduler._has_run_today(briefing_type)
        status = "Already run" if has_run else "Not run yet"
        print(f"  {briefing_type.capitalize()}: {status}")

    print()


def example_manual_briefing():
    """Example: Manually trigger a briefing."""
    print("="*80)
    print("Example 3: Manual Briefing Trigger")
    print("="*80)

    scheduler = BriefingScheduler(
        config_path="config/briefing_schedule.json",
        state_dir="State",
        templates_dir="Templates"
    )

    print("\nManually triggering morning briefing...")

    briefing_config = scheduler.config.get("briefings", {}).get("morning", {})
    if briefing_config:
        scheduler._run_briefing("morning", briefing_config)
        print("✓ Briefing generated\n")
    else:
        print("✗ Morning briefing not configured\n")


def example_daemon_mode_info():
    """Example: Information about daemon mode."""
    print("="*80)
    print("Example 4: Daemon Mode Information")
    print("="*80)

    print("""
Daemon mode runs continuously and checks for scheduled briefings every minute.

To start the daemon:
    python -m Tools.briefing_scheduler --mode daemon

To stop the daemon:
    Press Ctrl+C or send SIGTERM signal

The daemon will:
  • Check the schedule every minute (configurable)
  • Trigger briefings at configured times
  • Prevent duplicate runs on the same day
  • Log all activity to logs/briefing_scheduler.log
  • Gracefully shutdown on SIGTERM/SIGINT

For production use, consider:
  • Running as a systemd service (Linux)
  • Using launchd (macOS)
  • Running via cron with --mode once (all platforms)

See scripts/ directory for installation helpers (coming in subtask 2.3).
""")


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "BRIEFING SCHEDULER EXAMPLES" + " "*31 + "║")
    print("╚" + "="*78 + "╝")
    print()

    examples = [
        ("Check Configuration", example_check_status),
        ("Single Check Cycle", example_run_once),
        ("Manual Briefing", example_manual_briefing),
        ("Daemon Mode Info", example_daemon_mode_info),
    ]

    for i, (name, func) in enumerate(examples, 1):
        try:
            func()
        except Exception as e:
            print(f"✗ Error in example {i}: {e}\n")

        if i < len(examples):
            input("Press Enter to continue to next example...")
            print("\n")

    print("="*80)
    print("Examples complete!")
    print("="*80)
    print()


if __name__ == "__main__":
    main()
