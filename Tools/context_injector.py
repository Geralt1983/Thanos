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
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables if available
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / '.env')
except ImportError:
    pass


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


def build_hot_memory_context() -> str:
    """Load hot memories from memory service.

    Returns:
        Formatted hot memory context string
    """
    try:
        from Tools.hot_memory_loader import load_hot_memories
        return load_hot_memories(limit=10)
    except Exception as e:
        return f"<!-- Hot memory context failed: {e} -->"


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

    Returns:
        Formatted emotional context string
    """
    try:
        # TODO: Load yesterday's emotional markers from memory
        # For now, return placeholder
        return "## Emotional Continuity\n<!-- Emotional tracking pending -->"
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
