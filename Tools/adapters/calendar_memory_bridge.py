#!/usr/bin/env python3
"""
Calendar Memory Bridge: Prime memories before calendar events.

Boosts relevant memories before meetings to ensure contextual awareness.
Uses Memory V2's heat service to bring related memories to the surface.

Usage:
    # Programmatic usage
    from Tools.adapters.calendar_memory_bridge import prime_for_meeting, get_meeting_context

    event = {"title": "Orlando Sprint Review", "description": "Discuss Q1 milestones"}
    result = await prime_for_meeting(event)
    context = await get_meeting_context(event)

    # CLI usage
    python -m Tools.adapters.calendar_memory_bridge --event-title "Orlando Sprint Review"
"""

import re
import logging
from typing import Optional, Dict, Any, List, Set
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Known client names for fuzzy matching (loaded from WorkOS cache)
_CLIENT_NAMES_CACHE: Optional[List[str]] = None

# Common meeting keywords to filter out of entity extraction
MEETING_NOISE_WORDS = {
    "meeting", "call", "sync", "standup", "stand-up", "review", "planning",
    "retro", "retrospective", "demo", "weekly", "daily", "monthly", "quarterly",
    "1:1", "one-on-one", "check-in", "checkin", "catchup", "catch-up",
    "discussion", "session", "workshop", "brainstorm", "kickoff", "kick-off"
}

# Project keywords that often appear in calendar events
PROJECT_PATTERNS = [
    r"(?:project|phase)\s*[:=]?\s*(\w+)",
    r"(\w+)\s*(?:project|phase)",
    r"\b(Q[1-4])\b",  # Q1, Q2, Q3, Q4 quarters
]


def _get_client_names() -> List[str]:
    """
    Get list of known client names from WorkOS cache.

    Returns cached list to avoid repeated MCP calls.
    """
    global _CLIENT_NAMES_CACHE

    if _CLIENT_NAMES_CACHE is not None:
        return _CLIENT_NAMES_CACHE

    try:
        # Try to import WorkOS cache for client names
        import sys
        import os

        # Add path for bun-based cache if needed
        workos_cache_path = os.path.expanduser("~/.workos-cache/clients.json")
        if os.path.exists(workos_cache_path):
            import json
            with open(workos_cache_path, "r") as f:
                clients = json.load(f)
                _CLIENT_NAMES_CACHE = [c.get("name", "") for c in clients if c.get("name")]
                logger.debug(f"Loaded {len(_CLIENT_NAMES_CACHE)} clients from WorkOS cache")
                return _CLIENT_NAMES_CACHE

        # Fallback: try SQLite cache
        thanos_cache_path = os.path.expanduser("~/.thanos-cache/workos.db")
        if os.path.exists(thanos_cache_path):
            import sqlite3
            conn = sqlite3.connect(thanos_cache_path)
            cursor = conn.execute("SELECT name FROM cached_clients WHERE is_active = 1")
            _CLIENT_NAMES_CACHE = [row[0] for row in cursor.fetchall()]
            conn.close()
            logger.debug(f"Loaded {len(_CLIENT_NAMES_CACHE)} clients from SQLite cache")
            return _CLIENT_NAMES_CACHE

        # No cache available - return empty list
        _CLIENT_NAMES_CACHE = []
        logger.warning("No client cache available - entity extraction may be limited")
        return _CLIENT_NAMES_CACHE

    except Exception as e:
        logger.warning(f"Could not load client names: {e}")
        _CLIENT_NAMES_CACHE = []
        return _CLIENT_NAMES_CACHE


def extract_entities_from_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract client/project entities from calendar event.

    Parses event title, description, and attendees to identify:
    - Client names (matched against known clients)
    - Project names (extracted via patterns)
    - People (from attendees list)
    - Keywords (significant terms for memory search)

    Args:
        event: Calendar event dict with keys:
            - title/summary: Event title
            - description: Event description (optional)
            - attendees: List of attendee emails/names (optional)
            - location: Event location (optional)

    Returns:
        Dict with extracted entities:
            - clients: List of matched client names
            - projects: List of extracted project names
            - people: List of attendee names/emails
            - keywords: List of significant search terms
            - raw_text: Combined text used for extraction
    """
    # Gather all text from event
    title = event.get("title") or event.get("summary") or ""
    description = event.get("description") or ""
    location = event.get("location") or ""

    # Extract attendees
    attendees = event.get("attendees") or []
    attendee_names = []
    attendee_emails = []

    for attendee in attendees:
        if isinstance(attendee, str):
            if "@" in attendee:
                attendee_emails.append(attendee)
                # Extract name part before @
                name_part = attendee.split("@")[0].replace(".", " ").replace("_", " ")
                attendee_names.append(name_part.title())
            else:
                attendee_names.append(attendee)
        elif isinstance(attendee, dict):
            if attendee.get("displayName"):
                attendee_names.append(attendee["displayName"])
            if attendee.get("email"):
                attendee_emails.append(attendee["email"])

    # Combine all text for analysis
    raw_text = f"{title} {description} {location}"
    text_lower = raw_text.lower()

    # Extract clients (match against known client names)
    known_clients = _get_client_names()
    matched_clients: Set[str] = set()

    for client in known_clients:
        if client.lower() in text_lower:
            matched_clients.add(client)

    # Also check attendee emails for client domains
    for email in attendee_emails:
        domain = email.split("@")[-1].split(".")[0]
        for client in known_clients:
            if domain.lower() == client.lower():
                matched_clients.add(client)

    # Extract projects via patterns
    projects: Set[str] = set()
    for pattern in PROJECT_PATTERNS:
        matches = re.findall(pattern, raw_text, re.IGNORECASE)
        for match in matches:
            match_lower = match.lower()
            # Skip noise words and matched clients (avoid duplication)
            # Allow Q1-Q4 (2 chars) but require 3+ for other patterns
            is_quarter = match.upper() in ("Q1", "Q2", "Q3", "Q4")
            if (match_lower not in MEETING_NOISE_WORDS
                    and match_lower not in {c.lower() for c in matched_clients}
                    and (is_quarter or len(match) > 2)):
                projects.add(match.upper() if is_quarter else match.title())

    # Extract keywords (significant words not in noise list)
    words = re.findall(r"\b[A-Za-z]{3,}\b", raw_text)
    keywords = [
        w for w in words
        if w.lower() not in MEETING_NOISE_WORDS
        and len(w) > 3
    ]

    # Deduplicate while preserving order
    seen = set()
    unique_keywords = []
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower not in seen:
            seen.add(kw_lower)
            unique_keywords.append(kw)

    return {
        "clients": list(matched_clients),
        "projects": list(projects),
        "people": attendee_names,
        "emails": attendee_emails,
        "keywords": unique_keywords[:20],  # Limit to top 20
        "raw_text": raw_text.strip()
    }


async def prime_for_meeting(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Boost memories related to upcoming meeting.

    Extracts entities from the event and boosts related memories
    using Memory V2's heat service. This brings relevant context
    to the surface before the meeting starts.

    Args:
        event: Calendar event dict (see extract_entities_from_event)

    Returns:
        Dict with:
            - entities: Extracted entities
            - boosted_counts: Number of memories boosted per entity
            - total_boosted: Total memories boosted
            - meeting_title: Event title for reference
    """
    # Extract entities
    entities = extract_entities_from_event(event)

    boosted_counts: Dict[str, int] = {}
    total_boosted = 0

    try:
        # Import heat service
        from Tools.memory_v2.heat import get_heat_service
        heat_service = get_heat_service()

        # Boost memories for each client
        for client in entities["clients"]:
            count = heat_service.boost_related(client, "mention")
            boosted_counts[f"client:{client}"] = count
            total_boosted += count
            logger.info(f"Boosted {count} memories for client '{client}'")

        # Boost memories for each project
        for project in entities["projects"]:
            count = heat_service.boost_related(project, "mention")
            boosted_counts[f"project:{project}"] = count
            total_boosted += count
            logger.info(f"Boosted {count} memories for project '{project}'")

        # Boost by top keywords if no clients/projects found
        if not entities["clients"] and not entities["projects"]:
            for keyword in entities["keywords"][:5]:  # Top 5 keywords
                count = heat_service.boost_related(keyword, "mention")
                if count > 0:
                    boosted_counts[f"keyword:{keyword}"] = count
                    total_boosted += count

    except ImportError as e:
        logger.warning(f"Memory V2 not available: {e}")
    except Exception as e:
        logger.error(f"Error boosting memories: {e}")

    return {
        "entities": entities,
        "boosted_counts": boosted_counts,
        "total_boosted": total_boosted,
        "meeting_title": event.get("title") or event.get("summary") or "Unknown",
        "primed_at": datetime.now().isoformat()
    }


async def get_meeting_context(event: Dict[str, Any], limit: int = 10) -> str:
    """
    Get formatted memory context for a meeting.

    Searches memories related to the meeting entities and
    formats them for easy review before the meeting.

    Args:
        event: Calendar event dict
        limit: Maximum memories to include

    Returns:
        Formatted string with relevant memories and context
    """
    entities = extract_entities_from_event(event)
    title = event.get("title") or event.get("summary") or "Meeting"

    lines = []
    lines.append(f"## Meeting Context: {title}")
    lines.append("")

    # Show extracted entities
    if entities["clients"]:
        lines.append(f"**Clients:** {', '.join(entities['clients'])}")
    if entities["projects"]:
        lines.append(f"**Projects:** {', '.join(entities['projects'])}")
    if entities["people"]:
        lines.append(f"**People:** {', '.join(entities['people'][:5])}")
    lines.append("")

    try:
        # Search for relevant memories
        from Tools.memory_v2.service import get_memory_service
        memory_service = get_memory_service()

        # Build search query from entities
        search_terms = []
        search_terms.extend(entities["clients"])
        search_terms.extend(entities["projects"])
        search_terms.extend(entities["keywords"][:5])

        if search_terms:
            query = " ".join(search_terms)
            memories = memory_service.search(query, limit=limit)

            if memories:
                lines.append("### Relevant Memories")
                lines.append("")

                for mem in memories:
                    heat = mem.get("heat", 1.0)
                    heat_icon = "🔥" if heat > 0.7 else "•" if heat > 0.3 else "❄️"

                    content = mem.get("memory", mem.get("content", ""))
                    # Truncate long content
                    if len(content) > 150:
                        content = content[:147] + "..."

                    score = mem.get("effective_score", 0)
                    client = mem.get("client", "")
                    client_tag = f" [{client}]" if client else ""

                    lines.append(f"{heat_icon} {content}{client_tag}")
                    lines.append(f"   _Relevance: {score:.2f}_")
                    lines.append("")
            else:
                lines.append("_No relevant memories found._")
        else:
            lines.append("_No searchable terms extracted from event._")

    except ImportError as e:
        lines.append(f"_Memory service unavailable: {e}_")
    except Exception as e:
        lines.append(f"_Error retrieving memories: {e}_")

    return "\n".join(lines)


async def prime_upcoming_meetings(
    hours_ahead: int = 24,
    calendar_events: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Prime memories for all meetings in the next N hours.

    Can be called as a scheduled job or hook to prepare
    context before the day's meetings.

    Args:
        hours_ahead: Hours to look ahead (default 24)
        calendar_events: Optional pre-fetched events. If not provided,
                        will attempt to fetch from Google Calendar.

    Returns:
        Summary of all priming operations
    """
    if calendar_events is None:
        try:
            # Try to fetch from Google Calendar adapter
            from Tools.adapters.calendar_adapter import CalendarAdapter
            adapter = CalendarAdapter()

            # Get events for the time window
            now = datetime.now()
            end = now + timedelta(hours=hours_ahead)

            result = await adapter.call_tool("list_events", {
                "time_min": now.isoformat(),
                "time_max": end.isoformat()
            })

            if result.success:
                calendar_events = result.data.get("items", [])
            else:
                logger.warning(f"Could not fetch calendar events: {result.error}")
                calendar_events = []

        except Exception as e:
            logger.warning(f"Calendar adapter unavailable: {e}")
            calendar_events = []

    results = []
    total_boosted = 0

    for event in calendar_events:
        try:
            result = await prime_for_meeting(event)
            results.append(result)
            total_boosted += result.get("total_boosted", 0)
        except Exception as e:
            logger.error(f"Error priming for event: {e}")
            results.append({
                "meeting_title": event.get("title", "Unknown"),
                "error": str(e)
            })

    return {
        "meetings_processed": len(results),
        "total_memories_boosted": total_boosted,
        "results": results,
        "primed_at": datetime.now().isoformat()
    }


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """CLI entry point for calendar memory bridge."""
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(
        description="Prime memories before calendar events",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Prime for a specific meeting
    python -m Tools.adapters.calendar_memory_bridge --event-title "Orlando Sprint Review"

    # Get context for a meeting
    python -m Tools.adapters.calendar_memory_bridge --event-title "VersaCare Demo" --context

    # Prime all meetings in next 4 hours
    python -m Tools.adapters.calendar_memory_bridge --upcoming --hours 4
        """
    )

    parser.add_argument(
        "--event-title",
        help="Event title to prime for"
    )
    parser.add_argument(
        "--event-description",
        help="Event description for additional context",
        default=""
    )
    parser.add_argument(
        "--context",
        action="store_true",
        help="Get formatted context instead of priming"
    )
    parser.add_argument(
        "--upcoming",
        action="store_true",
        help="Prime all upcoming meetings"
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Hours to look ahead for --upcoming (default: 24)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )

    args = parser.parse_args()

    async def run():
        import json as json_module

        if args.upcoming:
            result = await prime_upcoming_meetings(hours_ahead=args.hours)
            if args.json:
                print(json_module.dumps(result, indent=2))
            else:
                print(f"\n🗓️  Primed {result['meetings_processed']} meetings")
                print(f"🔥 Boosted {result['total_memories_boosted']} memories total\n")
                for r in result['results']:
                    status = "✓" if r.get("total_boosted", 0) > 0 else "○"
                    print(f"  {status} {r.get('meeting_title', 'Unknown')}: {r.get('total_boosted', 0)} memories")

        elif args.event_title:
            event = {
                "title": args.event_title,
                "description": args.event_description
            }

            if args.context:
                context = await get_meeting_context(event)
                if args.json:
                    print(json_module.dumps({"context": context}))
                else:
                    print(context)
            else:
                result = await prime_for_meeting(event)
                if args.json:
                    print(json_module.dumps(result, indent=2))
                else:
                    print(f"\n🎯 Primed for: {result['meeting_title']}")
                    print(f"🔥 Boosted {result['total_boosted']} memories\n")

                    if result['entities']['clients']:
                        print(f"  Clients: {', '.join(result['entities']['clients'])}")
                    if result['entities']['projects']:
                        print(f"  Projects: {', '.join(result['entities']['projects'])}")

                    if result['boosted_counts']:
                        print("\n  Breakdown:")
                        for entity, count in result['boosted_counts'].items():
                            print(f"    {entity}: {count}")
        else:
            parser.print_help()

    asyncio.run(run())


if __name__ == "__main__":
    main()
