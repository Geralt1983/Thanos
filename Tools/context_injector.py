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


def build_relationship_context() -> str:
    """Build relationship context from recent memory.

    Returns:
        Formatted relationship context string
    """
    try:
        # TODO: Query memory for recent family/relationship mentions
        # For now, return placeholder
        return "## Relationship Context\n<!-- Relationship tracking pending -->"
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

        # Create concise emotional state summary (max 2-3 sentences)
        states = []
        if frustration > 0:
            states.append(f"frustration detected ({frustration}x)")
        if excitement > 0:
            states.append(f"excitement noted ({excitement}x)")
        if urgency > 0:
            states.append(f"urgency sensed ({urgency}x)")

        if states:
            parts.append(f"Yesterday: {', '.join(states)}.")
        else:
            parts.append("Yesterday: neutral emotional state.")

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
