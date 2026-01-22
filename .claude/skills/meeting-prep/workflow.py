#!/usr/bin/env python3
"""
Meeting Prep Workflow: Prime memories and gather context before meetings.

This script is invoked by the meeting-prep skill to:
1. Extract entities from meeting information
2. Search for relevant memories
3. Boost heat on related memories
4. Format context for the meeting

Usage:
    python workflow.py --title "Orlando Sprint Review" --description "Q1 milestones"
    python workflow.py --upcoming  # Prime all meetings in next 4 hours
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add Tools to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


async def get_meeting_context_with_tasks(
    event: dict,
    include_tasks: bool = True,
    limit: int = 10
) -> dict:
    """
    Get comprehensive meeting context including memories and tasks.

    Args:
        event: Calendar event with title, description, etc.
        include_tasks: Whether to fetch related tasks
        limit: Max memories to return

    Returns:
        Dict with memories, tasks, entities, and formatted context
    """
    from Tools.adapters.calendar_memory_bridge import (
        extract_entities_from_event,
        prime_for_meeting,
        get_meeting_context
    )

    # Extract entities
    entities = extract_entities_from_event(event)

    # Prime memories (boost heat)
    prime_result = await prime_for_meeting(event)

    # Get formatted context
    context = await get_meeting_context(event, limit=limit)

    result = {
        "entities": entities,
        "prime_result": prime_result,
        "memory_context": context,
        "tasks": []
    }

    # Optionally get related tasks
    if include_tasks and entities["clients"]:
        try:
            # Try to get tasks via local cache or direct call
            tasks = await _get_client_tasks(entities["clients"])
            result["tasks"] = tasks
        except Exception as e:
            result["tasks_error"] = str(e)

    return result


async def _get_client_tasks(clients: list) -> list:
    """Get tasks for the given clients."""
    import os
    import sqlite3

    tasks = []

    # Try SQLite cache first
    cache_path = os.path.expanduser("~/.workos-cache/cache.db")
    if os.path.exists(cache_path):
        try:
            conn = sqlite3.connect(cache_path)
            conn.row_factory = sqlite3.Row

            for client in clients:
                cursor = conn.execute("""
                    SELECT t.id, t.title, t.status, c.name as client_name
                    FROM cached_tasks t
                    LEFT JOIN cached_clients c ON t.client_id = c.id
                    WHERE c.name LIKE ? AND t.status IN ('active', 'queued')
                    ORDER BY t.status, t.created_at DESC
                    LIMIT 10
                """, (f"%{client}%",))

                for row in cursor:
                    tasks.append(dict(row))

            conn.close()
        except Exception:
            pass

    return tasks


def format_output(result: dict, json_output: bool = False) -> str:
    """Format the result for display."""
    if json_output:
        return json.dumps(result, indent=2, default=str)

    lines = []

    # Title
    title = result.get("prime_result", {}).get("meeting_title", "Meeting")
    lines.append(f"### DESTINY // Meeting Prep: {title}")
    lines.append("")

    # Entities
    entities = result.get("entities", {})
    if entities.get("clients"):
        lines.append(f"**Clients:** {', '.join(entities['clients'])}")
    if entities.get("projects"):
        lines.append(f"**Projects:** {', '.join(entities['projects'])}")
    if entities.get("people"):
        lines.append(f"**People:** {', '.join(entities['people'][:5])}")
    lines.append("")

    # Boost stats
    prime = result.get("prime_result", {})
    if prime.get("total_boosted", 0) > 0:
        lines.append(f"**Memories Boosted:** {prime['total_boosted']}")
        if prime.get("boosted_counts"):
            for entity, count in prime["boosted_counts"].items():
                lines.append(f"  - {entity}: {count}")
        lines.append("")

    # Memory context
    context = result.get("memory_context", "")
    if context:
        lines.append(context)
        lines.append("")

    # Tasks
    tasks = result.get("tasks", [])
    if tasks:
        lines.append("### Active Tasks")
        lines.append("")
        for task in tasks:
            status_icon = "◉" if task.get("status") == "active" else "○"
            lines.append(f"  {status_icon} {task.get('title', 'Unknown')}")
        lines.append("")

    lines.append("---")
    lines.append("The stones recall. You are prepared.")

    return "\n".join(lines)


async def main():
    parser = argparse.ArgumentParser(
        description="Prime memories for upcoming meetings"
    )

    parser.add_argument(
        "--title",
        help="Meeting title"
    )
    parser.add_argument(
        "--description",
        help="Meeting description",
        default=""
    )
    parser.add_argument(
        "--attendees",
        help="Comma-separated attendee names/emails",
        default=""
    )
    parser.add_argument(
        "--upcoming",
        action="store_true",
        help="Prime all upcoming meetings"
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=4,
        help="Hours ahead for --upcoming (default: 4)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Max memories to return"
    )

    args = parser.parse_args()

    if args.upcoming:
        from Tools.adapters.calendar_memory_bridge import prime_upcoming_meetings
        result = await prime_upcoming_meetings(hours_ahead=args.hours)

        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"\n### DESTINY // Upcoming Meetings Primed")
            print(f"\nMeetings processed: {result['meetings_processed']}")
            print(f"Total memories boosted: {result['total_memories_boosted']}")
            print("")

            for r in result.get("results", []):
                status = "✓" if r.get("total_boosted", 0) > 0 else "○"
                print(f"  {status} {r.get('meeting_title', 'Unknown')}: {r.get('total_boosted', 0)} memories")

            print("\nThe universe is prepared.")

    elif args.title:
        # Parse attendees
        attendees = []
        if args.attendees:
            attendees = [a.strip() for a in args.attendees.split(",")]

        event = {
            "title": args.title,
            "description": args.description,
            "attendees": attendees
        }

        result = await get_meeting_context_with_tasks(event, limit=args.limit)
        print(format_output(result, json_output=args.json))

    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
