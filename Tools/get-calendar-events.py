#!/usr/bin/env python3
"""
Calendar Events CLI Wrapper
Fetch today's calendar events for use in daily brief and other tools
"""

import asyncio
import json
import logging
import sys
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# Suppress OAuth-related warnings and noisy Google logs BEFORE importing
warnings.filterwarnings('ignore', message='.*oauth.*', category=Warning)
warnings.filterwarnings('ignore', message='.*Oauth.*', category=Warning)
logging.getLogger('googleapiclient').setLevel(logging.ERROR)
logging.getLogger('google').setLevel(logging.ERROR)
logging.getLogger('oauth2client').setLevel(logging.ERROR)
logging.getLogger('google_auth_oauthlib').setLevel(logging.ERROR)

# Add Tools directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from Tools.adapters import get_default_manager, GOOGLE_CALENDAR_AVAILABLE


async def get_calendar_events():
    """Fetch today's calendar events and format for daily brief."""
    try:
        if not GOOGLE_CALENDAR_AVAILABLE:
            return {
                "success": False,
                "error": "Google Calendar adapter not available",
                "events": [],
            }

        manager = await get_default_manager()

        # Call get_today_events tool
        result = await manager.call_tool("google_calendar.get_today_events")

        if not result.success:
            # Calendar not authenticated or other error - return empty gracefully
            return {
                "success": False,
                "error": result.error or "Calendar not available",
                "events": [],
            }

        # Extract event data
        events = result.data.get("events", [])
        summary = result.data.get("summary", {})

        # Get current time to identify upcoming events (within 2 hours)
        now = datetime.now(ZoneInfo("UTC"))
        two_hours_later = now + timedelta(hours=2)

        # Process events
        processed_events = []
        upcoming_events = []
        focus_blocks = []

        for event in events:
            # Parse event times
            start_str = event.get("start")
            end_str = event.get("end")

            # Determine if this is an all-day event
            is_all_day = event.get("is_all_day", False)

            # Build event info
            event_info = {
                "summary": event.get("summary", "Untitled Event"),
                "start": start_str,
                "end": end_str,
                "is_all_day": is_all_day,
                "location": event.get("location", ""),
                "attendees_count": len(event.get("attendees", [])),
            }

            processed_events.append(event_info)

            # Check if upcoming (only for timed events)
            if not is_all_day and start_str:
                try:
                    event_start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    if now <= event_start <= two_hours_later:
                        upcoming_events.append(event_info)
                except (ValueError, AttributeError):
                    pass

            # Identify focus blocks (events with keywords like "focus", "deep work", "block")
            summary_lower = event_info["summary"].lower()
            focus_keywords = ["focus", "deep work", "block", "concentration", "heads down"]
            if any(keyword in summary_lower for keyword in focus_keywords):
                focus_blocks.append(event_info)

        # Build response
        return {
            "success": True,
            "events": processed_events,
            "upcoming": upcoming_events,
            "focus_blocks": focus_blocks,
            "summary": summary,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "events": [],
        }
    finally:
        try:
            await manager.close_all()
        except Exception:
            pass


def main():
    """Run the async function and output JSON."""
    try:
        result = asyncio.run(get_calendar_events())
        print(json.dumps(result, indent=2))
    except Exception as e:
        error_result = {
            "success": False,
            "error": f"Failed to fetch calendar events: {str(e)}",
            "events": [],
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
