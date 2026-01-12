"""
Personal Assistant: Calendar Management Command

Manages calendar events, syncs data from Google Calendar, and checks availability.

Usage:
    python -m commands.pa.calendar [action] [options]

Actions:
    view      - View calendar events (default)
    sync      - Sync calendar data from Google Calendar
    find      - Find available time slots
    available - Check availability for specific time

Options:
    --today   - Focus on today's events (default)
    --week    - Show week view
    --sync    - Force sync before viewing

Model: gpt-4o-mini (simple task - cost effective)
"""

import asyncio
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.litellm_client import get_client


# System prompt for calendar assistant persona
SYSTEM_PROMPT = """You are Jeremy's calendar and scheduling assistant.

Your role:
- Manage calendar events and availability
- Help find optimal meeting times
- Sync calendar data from Google Calendar
- Provide clear, actionable calendar insights

Jeremy's context:
- Epic consultant - 15-20 billable hours/week target
- Has ADHD - needs clear, organized schedule views
- Partner Ashley, baby Sullivan (9 months)
- Best focus: mornings (8-11am when Vyvanse peaks)
- Values stoic philosophy and building systems

Calendar principles:
- Be direct and scannable (ADHD-friendly)
- Show time in 12-hour format with AM/PM
- Group events by day clearly
- Highlight conflicts or back-to-back meetings
- Suggest optimal focus blocks between meetings
"""


def sync_calendar(scope: str = "today", timezone: str = "America/New_York") -> dict:
    """
    Sync calendar data using Tools/calendar_sync.py.

    Args:
        scope: "today", "week", or "all"
        timezone: Timezone for date calculations

    Returns:
        dict with success status and message
    """
    project_root = Path(__file__).parent.parent.parent
    sync_script = project_root / "Tools" / "calendar_sync.py"

    if not sync_script.exists():
        return {
            "success": False,
            "message": "Calendar sync script not found"
        }

    try:
        # Build command
        cmd = [sys.executable, str(sync_script)]

        if scope == "today":
            cmd.append("--today")
        elif scope == "week":
            cmd.append("--week")
        elif scope == "all":
            cmd.append("--all")

        cmd.extend(["--timezone", timezone])

        # Run sync
        print(f"🔄 Syncing {scope} calendar data...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            return {
                "success": True,
                "message": f"✅ Calendar synced successfully ({scope})"
            }
        else:
            return {
                "success": False,
                "message": f"❌ Sync failed: {result.stderr}"
            }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "❌ Sync timeout (>30s)"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Sync error: {str(e)}"
        }


def load_calendar_data(scope: str = "today") -> dict:
    """
    Load calendar data from State directory.

    Args:
        scope: "today" or "week"

    Returns:
        dict with calendar data or empty structure
    """
    project_root = Path(__file__).parent.parent.parent
    state_dir = project_root / "State"

    filename = "calendar_today.json" if scope == "today" else "calendar_week.json"
    calendar_file = state_dir / filename

    if not calendar_file.exists():
        return {
            "success": False,
            "message": f"No {scope} calendar data found. Run sync first.",
            "events": []
        }

    try:
        with open(calendar_file) as f:
            data = json.load(f)

        return {
            "success": True,
            "data": data,
            "events": data.get("events", []),
            "synced_at": data.get("synced_at", "unknown")
        }

    except json.JSONDecodeError as e:
        return {
            "success": False,
            "message": f"Invalid JSON in {filename}: {str(e)}",
            "events": []
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error loading {filename}: {str(e)}",
            "events": []
        }


def format_calendar_for_display(calendar_data: dict, scope: str = "today") -> str:
    """
    Format calendar data for LLM context.

    Args:
        calendar_data: Calendar data from load_calendar_data
        scope: "today" or "week"

    Returns:
        Formatted string for LLM
    """
    if not calendar_data.get("success"):
        return calendar_data.get("message", "No calendar data available")

    data = calendar_data.get("data", {})
    events = calendar_data.get("events", [])
    synced_at = calendar_data.get("synced_at", "unknown")

    output = []
    output.append(f"## Calendar - {scope.title()}")
    output.append(f"Last synced: {synced_at}")
    output.append(f"Total events: {len(events)}")
    output.append("")

    if scope == "today":
        date = data.get("date", "unknown")
        output.append(f"### {date}")
    elif scope == "week":
        start = data.get("week_start", "unknown")
        end = data.get("week_end", "unknown")
        output.append(f"### Week: {start} to {end}")

    output.append("")

    if not events:
        output.append("No events scheduled")
    else:
        # Format events
        for event in events:
            summary = event.get("summary", "Untitled Event")
            start = event.get("start", {})
            end = event.get("end", {})

            start_time = start.get("dateTime") or start.get("date", "")
            end_time = end.get("dateTime") or end.get("date", "")

            # Format times
            if start_time and "T" in start_time:
                # Has time component
                start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                time_str = f"{start_dt.strftime('%I:%M %p')} - {end_dt.strftime('%I:%M %p')}"
            else:
                # All-day event
                time_str = "All day"

            output.append(f"- **{summary}**")
            output.append(f"  {time_str}")

            # Add location if present
            if event.get("location"):
                output.append(f"  📍 {event['location']}")

            # Add attendees count if present
            attendees = event.get("attendees", [])
            if attendees:
                output.append(f"  👥 {len(attendees)} attendees")

            output.append("")

    return "\n".join(output)


def save_to_history(action: str, response: str):
    """Save calendar action to History."""
    project_root = Path(__file__).parent.parent.parent
    history_dir = project_root / "History" / "Calendar"
    history_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now()
    filename = f"calendar_{action}_{timestamp.strftime('%Y-%m-%d_%H%M')}.md"

    with open(history_dir / filename, "w") as f:
        f.write(f"# Calendar {action.title()} - {timestamp.strftime('%B %d, %Y %I:%M %p')}\n\n")
        f.write(response)


def execute(args: Optional[str] = None) -> str:
    """
    Execute calendar command.

    Args:
        args: Action and options (e.g., "view --week" or "sync --today")

    Returns:
        The generated response
    """
    # Parse action and options
    action = "view"  # default
    scope = "today"  # default
    force_sync = False
    details = ""

    if args:
        parts = args.split()
        if parts:
            # First word is action if it's a known action
            if parts[0].lower() in ["view", "sync", "find", "available"]:
                action = parts[0].lower()
                parts = parts[1:]

        # Parse flags
        for i, part in enumerate(parts):
            if part == "--week":
                scope = "week"
            elif part == "--today":
                scope = "today"
            elif part == "--sync":
                force_sync = True
            elif not part.startswith("--"):
                # Collect non-flag words as details
                details += part + " "

        details = details.strip()

    # Execute action
    client = get_client()
    today = datetime.now().strftime("%A, %B %d, %Y")
    model = "gpt-4o-mini"

    print(f"📅 Calendar Assistant - {action.title()}")
    print(f"📡 Using {model}\n")
    print("-" * 50)

    response_parts = []

    # Handle sync action
    if action == "sync":
        sync_result = sync_calendar(scope="all" if scope == "week" else "today")
        print(sync_result["message"])
        print("-" * 50)

        # Load and display synced data
        calendar_data = load_calendar_data(scope)
        context = format_calendar_for_display(calendar_data, scope)

        prompt = f"""Today is {today}.

{context}

Calendar data has been synced. Provide a brief summary:
1. Number of events
2. Any notable meetings or time blocks
3. Overall schedule density (light, moderate, heavy)
"""

        for chunk in client.chat_stream(
            prompt=prompt, model=model, system_prompt=SYSTEM_PROMPT, temperature=0.7
        ):
            print(chunk, end="", flush=True)
            response_parts.append(chunk)

        print("\n" + "-" * 50)
        response = "".join(response_parts)

    # Handle view action
    elif action == "view":
        # Sync if requested
        if force_sync:
            sync_result = sync_calendar(scope="all" if scope == "week" else "today")
            print(sync_result["message"])

        # Load calendar data
        calendar_data = load_calendar_data(scope)
        context = format_calendar_for_display(calendar_data, scope)

        prompt = f"""Today is {today}.

{context}

Review my {scope} calendar and provide:
1. Events in chronological order with clear time formatting
2. Any scheduling conflicts or back-to-back meetings
3. Available focus time blocks
4. Any preparation needed for important meetings

{f"Additional context: {details}" if details else ""}

Be concise and ADHD-friendly - use bullets and clear formatting.
"""

        for chunk in client.chat_stream(
            prompt=prompt, model=model, system_prompt=SYSTEM_PROMPT, temperature=0.7
        ):
            print(chunk, end="", flush=True)
            response_parts.append(chunk)

        print("\n" + "-" * 50)
        response = "".join(response_parts)

    # Handle find action
    elif action == "find":
        # Load calendar data
        calendar_data = load_calendar_data("week")
        context = format_calendar_for_display(calendar_data, "week")

        prompt = f"""Today is {today}.

{context}

Find available time for:
{details if details else "a meeting or focus block"}

Requirements:
- Look for gaps between existing meetings
- Prefer mornings (8-11am) for focus work
- Prefer afternoons for meetings
- Need at least 30-min buffer between meetings
- Suggest 2-3 specific time slot options with day/time
"""

        for chunk in client.chat_stream(
            prompt=prompt, model=model, system_prompt=SYSTEM_PROMPT, temperature=0.7
        ):
            print(chunk, end="", flush=True)
            response_parts.append(chunk)

        print("\n" + "-" * 50)
        response = "".join(response_parts)

    # Handle available action
    elif action == "available":
        # Load calendar data
        calendar_data = load_calendar_data(scope)
        context = format_calendar_for_display(calendar_data, scope)

        prompt = f"""Today is {today}.

{context}

Check availability for:
{details if details else "the requested time"}

Analyze:
1. Is the time slot free?
2. Any conflicts or adjacent meetings?
3. Quality of the slot (good focus time, between meetings, etc.)
4. Alternative suggestions if not ideal
"""

        for chunk in client.chat_stream(
            prompt=prompt, model=model, system_prompt=SYSTEM_PROMPT, temperature=0.7
        ):
            print(chunk, end="", flush=True)
            response_parts.append(chunk)

        print("\n" + "-" * 50)
        response = "".join(response_parts)

    else:
        response = f"Unknown action: {action}"
        print(response)
        print("-" * 50)

    # Save to history
    save_to_history(action, response)

    return response


def main():
    """CLI entry point."""
    args = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    execute(args)


if __name__ == "__main__":
    main()
