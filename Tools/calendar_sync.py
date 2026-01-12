#!/usr/bin/env python3
"""
Calendar Sync Utility

Syncs Google Calendar events to State/ directory for use in daily briefings
and schedule management.

Outputs:
    - State/calendar_today.json: Today's calendar events
    - State/calendar_week.json: This week's calendar events

Usage:
    python Tools/calendar_sync.py [--today] [--week] [--all]

    --today: Sync today's events only (default)
    --week: Sync this week's events only
    --all: Sync both today and week
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from Tools.adapters import get_default_manager, GOOGLE_CALENDAR_AVAILABLE


async def sync_today_events(manager, timezone: str = "America/New_York") -> dict:
    """
    Fetch and save today's calendar events.

    Args:
        manager: AdapterManager instance
        timezone: Timezone for date calculations

    Returns:
        dict with success status and event data
    """
    try:
        # Call get_today_events tool
        result = await manager.call_tool(
            "google_calendar.get_today_events",
            arguments={"timezone": timezone}
        )

        if not result.success:
            return {
                "success": False,
                "error": result.error or "Failed to fetch today's events",
                "events": []
            }

        # Extract event data
        events = result.data.get("events", [])
        summary = result.data.get("summary", {})

        # Build output data
        output_data = {
            "synced_at": datetime.now(ZoneInfo(timezone)).isoformat(),
            "date": datetime.now(ZoneInfo(timezone)).strftime("%Y-%m-%d"),
            "timezone": timezone,
            "events": events,
            "summary": summary
        }

        # Save to State/calendar_today.json
        project_root = Path(__file__).parent.parent
        state_dir = project_root / "State"
        state_dir.mkdir(parents=True, exist_ok=True)

        output_file = state_dir / "calendar_today.json"
        with open(output_file, "w") as f:
            json.dump(output_data, f, indent=2)

        return {
            "success": True,
            "file": str(output_file),
            "event_count": len(events),
            "data": output_data
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "events": []
        }


async def sync_week_events(manager, timezone: str = "America/New_York") -> dict:
    """
    Fetch and save this week's calendar events.

    Args:
        manager: AdapterManager instance
        timezone: Timezone for date calculations

    Returns:
        dict with success status and event data
    """
    try:
        # Calculate week date range (Monday to Sunday)
        now = datetime.now(ZoneInfo(timezone))

        # Get Monday of current week
        days_since_monday = now.weekday()  # Monday is 0, Sunday is 6
        week_start = now - timedelta(days=days_since_monday)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        # Get Sunday of current week
        days_until_sunday = 6 - now.weekday()
        week_end = now + timedelta(days=days_until_sunday)
        week_end = week_end.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Format dates for API call
        start_date = week_start.strftime("%Y-%m-%d")
        end_date = week_end.strftime("%Y-%m-%d")

        # Call get_events tool for the week
        result = await manager.call_tool(
            "google_calendar.get_events",
            arguments={
                "start_date": start_date,
                "end_date": end_date,
                "calendar_id": "primary",
                "single_events": True,
                "include_cancelled": False
            }
        )

        if not result.success:
            return {
                "success": False,
                "error": result.error or "Failed to fetch week's events",
                "events": []
            }

        # Extract event data
        events = result.data.get("events", [])

        # Build output data
        output_data = {
            "synced_at": datetime.now(ZoneInfo(timezone)).isoformat(),
            "week_start": start_date,
            "week_end": end_date,
            "timezone": timezone,
            "events": events,
            "event_count": len(events)
        }

        # Save to State/calendar_week.json
        project_root = Path(__file__).parent.parent
        state_dir = project_root / "State"
        state_dir.mkdir(parents=True, exist_ok=True)

        output_file = state_dir / "calendar_week.json"
        with open(output_file, "w") as f:
            json.dump(output_data, f, indent=2)

        return {
            "success": True,
            "file": str(output_file),
            "event_count": len(events),
            "data": output_data
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "events": []
        }


async def sync_calendar(
    sync_today: bool = True,
    sync_week: bool = False,
    timezone: str = "America/New_York"
) -> dict:
    """
    Main sync function.

    Args:
        sync_today: Whether to sync today's events
        sync_week: Whether to sync week's events
        timezone: Timezone for date calculations

    Returns:
        dict with results for each sync operation
    """
    results = {
        "success": True,
        "operations": {}
    }

    try:
        # Check if Google Calendar adapter is available
        if not GOOGLE_CALENDAR_AVAILABLE:
            return {
                "success": False,
                "error": "Google Calendar adapter not available. Please ensure google-api-python-client is installed.",
                "operations": {}
            }

        # Get adapter manager
        manager = await get_default_manager()

        # Sync today's events
        if sync_today:
            print("📅 Syncing today's calendar events...")
            today_result = await sync_today_events(manager, timezone)
            results["operations"]["today"] = today_result

            if today_result["success"]:
                print(f"✅ Saved {today_result['event_count']} events to {today_result['file']}")
            else:
                print(f"❌ Failed to sync today's events: {today_result.get('error', 'Unknown error')}")
                results["success"] = False

        # Sync week's events
        if sync_week:
            print("📅 Syncing this week's calendar events...")
            week_result = await sync_week_events(manager, timezone)
            results["operations"]["week"] = week_result

            if week_result["success"]:
                print(f"✅ Saved {week_result['event_count']} events to {week_result['file']}")
            else:
                print(f"❌ Failed to sync week's events: {week_result.get('error', 'Unknown error')}")
                results["success"] = False

        return results

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "operations": {}
        }
    finally:
        try:
            await manager.close_all()
        except Exception:
            pass


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Sync Google Calendar events to State/ directory"
    )
    parser.add_argument(
        "--today",
        action="store_true",
        help="Sync today's events (default if no flags specified)"
    )
    parser.add_argument(
        "--week",
        action="store_true",
        help="Sync this week's events"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Sync both today and week"
    )
    parser.add_argument(
        "--timezone",
        type=str,
        default="America/New_York",
        help="Timezone for date calculations (default: America/New_York)"
    )

    args = parser.parse_args()

    # Determine what to sync
    sync_today = args.today or args.all or (not args.today and not args.week and not args.all)
    sync_week = args.week or args.all

    try:
        print("🔄 Starting calendar sync...")
        result = asyncio.run(sync_calendar(
            sync_today=sync_today,
            sync_week=sync_week,
            timezone=args.timezone
        ))

        if result["success"]:
            print("\n✅ Calendar sync completed successfully")
            sys.exit(0)
        else:
            print(f"\n❌ Calendar sync failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️  Sync cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
