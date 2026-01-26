#!/usr/bin/env python3
"""
Context Injector - Build comprehensive session context at startup

Returns: temporal context, energy level, hot memories, relationship status, emotional continuity

Part of enhanced session continuity (task-047):
- Automatically loads yesterday's emotional markers
- Surfaces active projects and commitments
- Includes recent relationship mentions
- Provides temporal context and energy awareness
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables if available
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / '.env')
except ImportError:
    pass


def get_yesterday_session() -> Optional[Dict]:
    """Load yesterday's session JSON file.

    Searches the History/Sessions directory for JSON session files from
    yesterday and returns the most recent one (by filename timestamp).

    Returns:
        Dictionary containing session data if found, None otherwise.
        Session data includes: id, started_at, agent, history, memory_snapshot.

    Example:
        >>> session = get_yesterday_session()
        >>> if session:
        ...     markers = session.get("memory_snapshot", {}).get("emotional_markers", {})
        ...     print(f"Yesterday's frustration level: {markers.get('frustration', 0)}")
    """
    try:
        # Calculate yesterday's date
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_str = yesterday.strftime("%Y-%m-%d")

        # Find History/Sessions directory relative to this file
        sessions_dir = Path(__file__).parent.parent / "History" / "Sessions"

        if not sessions_dir.exists():
            return None

        # Find all JSON files matching yesterday's date pattern
        pattern = f"{yesterday_str}-*.json"
        matching_files = list(sessions_dir.glob(pattern))

        if not matching_files:
            return None

        # Sort by filename (which includes timestamp) and get the most recent
        most_recent = sorted(matching_files)[-1]

        # Load and return the JSON data
        with open(most_recent, 'r', encoding='utf-8') as f:
            return json.load(f)

    except Exception:
        # Silently return None on any error (file read, JSON parse, etc.)
        return None


def build_temporal_context() -> str:
    """Build temporal context with current time and time-of-day awareness.

    Returns:
        Formatted temporal context string
    """
    try:
        # Load timezone from critical_facts.json if available
        timezone_name = "America/New_York"  # Default
        try:
            facts_file = Path(__file__).parent.parent / "State" / "critical_facts.json"
            if facts_file.exists():
                with open(facts_file, 'r', encoding='utf-8') as f:
                    facts = json.load(f)
                    timezone_name = facts.get("personal", {}).get("timezone", timezone_name)
        except Exception:
            pass  # Use default timezone if loading fails

        # Get current time with timezone awareness
        try:
            tz = ZoneInfo(timezone_name)
            now = datetime.now(tz)
        except Exception:
            # Fallback to naive datetime if timezone fails
            now = datetime.now()
            timezone_name = "local"

        hour = now.hour

        # Time of day context
        if 5 <= hour < 12:
            period = "Morning (5am-12pm): The day begins..."
        elif 12 <= hour < 17:
            period = "Afternoon (12pm-5pm): Midday execution..."
        elif 17 <= hour < 21:
            period = "Evening (5pm-9pm): The day draws to close..."
        else:
            period = "Night (9pm-5am): The universe rests. Should you?"

        # Build temporal context string
        parts = [f"## Temporal Context"]
        parts.append(f"Current time: {now.strftime('%Y-%m-%d %H:%M')} ({timezone_name})")
        parts.append(period)

        return "\n".join(parts)
    except Exception as e:
        return f"<!-- Temporal context failed: {e} -->"


def build_energy_context() -> str:
    """Build energy context from Oura or WorkOS.

    Returns:
        Formatted energy context string
    """
    try:
        # TODO: Integrate with Oura MCP or WorkOS energy tracking
        # For now, return placeholder
        return "## Energy Context\n<!-- Energy integration pending -->"
    except Exception as e:
        return f"<!-- Energy context failed: {e} -->"


def build_hot_memory_context(limit: int = 10) -> str:
    """Load hot memories from memory service.

    Args:
        limit: Maximum number of hot memories to load (default: 10)

    Returns:
        Formatted hot memory context string
    """
    try:
        # Try to use the dedicated hot_memory_loader first
        from Tools.hot_memory_loader import load_hot_memories
        result = load_hot_memories(limit=limit)

        # If empty or error comment, return header with placeholder
        if not result or result.startswith("<!--"):
            return "## Hot Memory Context\n<!-- No hot memories available -->"

        return result
    except ImportError:
        # If hot_memory_loader not available, implement inline
        try:
            from Tools.memory_v2.service import MemoryService
            ms = MemoryService()

            # Get top memories by heat
            hot = ms.whats_hot(limit=limit)

            if not hot:
                return "## Hot Memory Context\n<!-- No hot memories available -->"

            lines = ["## Hot Memory Context", ""]
            for mem in hot[:limit]:
                heat_indicator = "🔥" if mem.get('heat', 0) > 0.8 else "•" if mem.get('heat', 0) > 0.5 else "❄️"
                memory_text = mem.get('memory', '')[:150]
                client = mem.get('client')

                line = f"{heat_indicator} {memory_text}"
                if client:
                    line += f" [{client}]"
                lines.append(line)

            return "\n".join(lines)
        except Exception as e:
            # Return header with error note
            return "## Hot Memory Context\n<!-- Memory service unavailable -->"
    except Exception as e:
        # Return header with error note for any other errors
        return "## Hot Memory Context\n<!-- Memory service unavailable -->"


def active_projects_context() -> str:
    """Load active projects context from Memory V2.

    Searches memory for client/project mentions from critical_facts.json.

    Returns:
        Formatted active projects context string
    """
    try:
        # Load client names from critical_facts.json
        facts_file = Path(__file__).parent.parent / "State" / "critical_facts.json"
        if not facts_file.exists():
            return "## Active Projects Context\n<!-- critical_facts.json not found -->"

        with open(facts_file, 'r', encoding='utf-8') as f:
            facts = json.load(f)

        # Get active clients and primary projects
        active_clients = facts.get("work", {}).get("active_clients", [])
        primary_projects = facts.get("work", {}).get("primary_projects", [])

        if not active_clients and not primary_projects:
            return "## Active Projects Context\n<!-- No active clients or projects in critical_facts -->"

        # Search Memory V2 for client/project mentions
        from Tools.memory_v2.service import MemoryService
        ms = MemoryService()

        # Collect memories for each client/project
        project_memories = {}
        all_entities = list(active_clients) + list(primary_projects)

        for entity in all_entities:
            results = ms.search(entity, limit=3)
            # Only include high-quality results (effective_score > 0.3)
            relevant = [r for r in results if r.get('effective_score', 0) > 0.3]
            if relevant:
                project_memories[entity] = relevant

        # Format output
        if not project_memories:
            return "## Active Projects Context\n<!-- No recent memory found for active clients/projects -->"

        lines = ["## Active Projects Context", ""]
        for entity, memories in project_memories.items():
            # Determine if this is a client or project
            entity_type = "Client" if entity in active_clients else "Project"
            lines.append(f"**{entity}** ({entity_type}):")

            for mem in memories[:2]:  # Limit to 2 memories per entity
                memory_text = mem.get('memory', '')[:120]  # Truncate to 120 chars
                heat = mem.get('heat', 0)
                heat_indicator = "🔥" if heat > 0.8 else "•" if heat > 0.5 else "❄️"
                lines.append(f"  {heat_indicator} {memory_text}")

            lines.append("")  # Blank line between entities

        return "\n".join(lines).rstrip()

    except ImportError:
        # Memory V2 not available
        return "## Active Projects Context\n<!-- Memory V2 service unavailable -->"
    except Exception as e:
        # Silent error handling - don't break session startup
        return "## Active Projects Context\n<!-- Memory service error -->"


def relationship_context() -> str:
    """Search Memory V2 for personal domain entries from past 7 days.

    Searches for memories with domain='personal' to surface recent
    relationship mentions, family interactions, and personal commitments.

    Returns:
        Formatted relationship context string
    """
    try:
        from Tools.memory_v2.service import MemoryService
        ms = MemoryService()

        # Calculate date 7 days ago
        seven_days_ago = datetime.now() - timedelta(days=7)
        seven_days_ago_str = seven_days_ago.strftime("%Y-%m-%d")

        # Search for personal domain memories
        # Note: Memory V2 search doesn't support date filtering directly,
        # so we'll search broadly and filter results by date
        results = ms.search("domain:personal", limit=20)

        # Filter results to only include entries from past 7 days
        recent_memories = []
        for mem in results:
            # Check if memory has a timestamp we can use
            created_at = mem.get('created_at') or mem.get('timestamp')
            if created_at:
                try:
                    # Parse the timestamp (handle ISO format)
                    if isinstance(created_at, str):
                        mem_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        mem_date = created_at

                    # Check if within past 7 days
                    if mem_date >= seven_days_ago:
                        recent_memories.append(mem)
                except Exception:
                    # If date parsing fails, include it anyway
                    recent_memories.append(mem)
            else:
                # No timestamp - include it anyway
                recent_memories.append(mem)

        # Also check metadata for domain='personal'
        personal_memories = [m for m in recent_memories if m.get('domain') == 'personal']

        # If we didn't find any with domain filter, fall back to broader search
        if not personal_memories:
            # Try searching for common relationship terms
            relationship_queries = ["Ashley", "Sullivan", "family", "wife", "son"]
            for query in relationship_queries:
                query_results = ms.search(query, limit=3)
                for mem in query_results:
                    if mem.get('effective_score', 0) > 0.3:
                        # Check date constraint
                        created_at = mem.get('created_at') or mem.get('timestamp')
                        if created_at:
                            try:
                                if isinstance(created_at, str):
                                    mem_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                                else:
                                    mem_date = created_at
                                if mem_date >= seven_days_ago:
                                    personal_memories.append(mem)
                            except Exception:
                                personal_memories.append(mem)
                        else:
                            personal_memories.append(mem)

        # Remove duplicates (by memory id)
        seen_ids = set()
        unique_memories = []
        for mem in personal_memories:
            mem_id = mem.get('id')
            if mem_id and mem_id not in seen_ids:
                seen_ids.add(mem_id)
                unique_memories.append(mem)
            elif not mem_id:
                unique_memories.append(mem)

        # Format output
        if not unique_memories:
            return "## Relationship Context\n<!-- No personal memories found in past 7 days -->"

        lines = ["## Relationship Context (Past 7 Days)", ""]

        for mem in unique_memories[:5]:  # Limit to 5 most relevant
            memory_text = mem.get('memory', '')[:120]
            heat = mem.get('heat', 0)
            heat_indicator = "🔥" if heat > 0.8 else "•" if heat > 0.5 else "❄️"

            # Add date if available
            created_at = mem.get('created_at') or mem.get('timestamp')
            date_str = ""
            if created_at:
                try:
                    if isinstance(created_at, str):
                        mem_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        mem_date = created_at
                    date_str = f" ({mem_date.strftime('%b %d')})"
                except Exception:
                    pass

            lines.append(f"{heat_indicator} {memory_text}{date_str}")

        return "\n".join(lines)

    except ImportError:
        return "## Relationship Context\n<!-- Memory V2 service unavailable -->"
    except Exception as e:
        # Silent error handling - don't break session startup
        return "## Relationship Context\n<!-- Memory service error -->"


def build_relationship_context() -> str:
    """Build relationship context from recent memory.

    Returns:
        Formatted relationship context string
    """
    try:
        # Use the new relationship_context() function
        return relationship_context()
    except Exception as e:
        return f"<!-- Relationship context failed: {e} -->"


def build_emotional_context() -> str:
    """Build emotional continuity from yesterday's session.

    Extracts emotional markers (frustration, excitement, urgency) from
    yesterday's session memory_snapshot and formats them as context.

    Returns:
        Formatted emotional context string with yesterday's emotional state
    """
    try:
        # Load yesterday's session data
        yesterday = get_yesterday_session()

        if not yesterday:
            return "## Emotional Continuity\n<!-- No session data from yesterday -->"

        # Extract emotional markers from memory_snapshot
        markers = yesterday.get("memory_snapshot", {}).get("emotional_markers", {})

        if not markers:
            return "## Emotional Continuity\n<!-- No emotional markers recorded yesterday -->"

        # Extract individual marker counts
        frustration = markers.get("frustration", 0)
        excitement = markers.get("excitement", 0)
        urgency = markers.get("urgency", 0)

        # Build contextual summary based on detected emotions
        parts = ["## Emotional Continuity", ""]

        # Format concise emotional state summary (max 2-3 sentences)
        # Determine dominant emotional tone
        dominant_emotion = None
        max_count = 0

        if frustration > max_count:
            dominant_emotion = "frustration"
            max_count = frustration
        if excitement > max_count:
            dominant_emotion = "excitement"
            max_count = excitement
        if urgency > max_count:
            dominant_emotion = "urgency"
            max_count = urgency

        # Generate concise, contextual summary
        if dominant_emotion == "frustration" and frustration >= 3:
            parts.append("The stones sensed resistance yesterday. Frustration marked the path.")
            if urgency > 0:
                parts.append("Urgency compounds the pressure.")
        elif dominant_emotion == "excitement" and excitement >= 2:
            parts.append("Yesterday's energy carried momentum. The balance shifts toward possibility.")
        elif dominant_emotion == "urgency" and urgency >= 2:
            parts.append("Urgency drove yesterday's choices. The clock commands attention.")
        elif frustration > 0 or excitement > 0 or urgency > 0:
            # Mixed state - list concisely
            states = []
            if frustration > 0:
                states.append(f"frustration ({frustration}x)")
            if excitement > 0:
                states.append(f"excitement ({excitement}x)")
            if urgency > 0:
                states.append(f"urgency ({urgency}x)")
            parts.append(f"Yesterday: {', '.join(states)}.")
        else:
            parts.append("Yesterday: steady state, neutral ground.")

        return "\n".join(parts)
    except Exception as e:
        return f"<!-- Emotional context failed: {e} -->"


def build_session_context() -> str:
    """Build comprehensive session context for startup.

    Aggregates:
    - Temporal context (current time, time-of-day awareness)
    - Energy level (from Oura or WorkOS)
    - Hot memories (high-heat items from Memory V2)
    - Relationship status (recent family/friend mentions)
    - Emotional continuity (yesterday's markers)

    Returns:
        Complete session context string for injection into Claude prompt
    """
    parts = []

    # Add each context section
    parts.append(build_temporal_context())
    parts.append(build_energy_context())
    parts.append(build_hot_memory_context())
    parts.append(build_relationship_context())
    parts.append(build_emotional_context())

    # Filter out empty sections
    parts = [p for p in parts if p and not p.startswith("<!--")]

    return "\n\n".join(parts)


if __name__ == "__main__":
    # Allow running as standalone script for testing
    context = build_session_context()
    print(context)
