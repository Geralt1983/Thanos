#!/usr/bin/env python3
"""
Hot Memory Loader - Loads high-heat memories into session context.

Part of the tiered memory architecture:
- Hot (0ms): This loader, for session start or periodic refresh
- Warm (~0.5s): On-demand search with cached embeddings
- Cold (~1s): Full corpus deep search

For long-running sessions:
- Use load_if_stale() to only refresh when needed
- Default refresh interval: 1 hour
- Tracks last load time in State/hot_memory_cache.json
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

from Tools.memory_v2.service import MemoryService

CACHE_FILE = Path(__file__).parent.parent / "State" / "hot_memory_cache.json"
DEFAULT_REFRESH_HOURS = 1


def _get_cache() -> dict:
    """Load cache state."""
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_cache(data: dict):
    """Save cache state."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(data, default=str))


def load_hot_memories(limit: int = 10) -> str:
    """Load high-heat memories for session context injection."""
    try:
        ms = MemoryService()

        # Get top memories by heat
        hot = ms.whats_hot(limit=limit)

        if not hot:
            return ""

        lines = ["## Hot Memory Context", ""]
        for mem in hot[:limit]:
            heat_indicator = "🔥" if mem.get('heat', 0) > 0.8 else "•" if mem.get('heat', 0) > 0.5 else "❄️"
            memory_text = mem.get('memory', '')[:150]
            client = mem.get('client')

            line = f"{heat_indicator} {memory_text}"
            if client:
                line += f" [{client}]"
            lines.append(line)

        # Update cache with load time
        _save_cache({
            "last_loaded": datetime.now().isoformat(),
            "memory_count": len(hot)
        })

        return "\n".join(lines)

    except Exception as e:
        # Silent fail - don't break session
        return f"<!-- Hot memory load failed: {e} -->"


def load_if_stale(hours: float = DEFAULT_REFRESH_HOURS, limit: int = 10) -> str:
    """
    Load hot memories only if cache is stale.

    For long-running sessions, call this periodically.
    Returns empty string if cache is fresh.

    Args:
        hours: Refresh interval in hours (default: 1)
        limit: Maximum memories to load

    Returns:
        Hot memory context string, or empty if cache is fresh
    """
    cache = _get_cache()
    last_loaded = cache.get("last_loaded")

    if last_loaded:
        try:
            last_time = datetime.fromisoformat(last_loaded)
            if datetime.now() - last_time < timedelta(hours=hours):
                return ""  # Cache is fresh
        except Exception:
            pass

    # Cache is stale or missing, reload
    return load_hot_memories(limit)


def get_heat_summary() -> str:
    """Get a quick summary of memory heat distribution."""
    try:
        from Tools.memory_v2.heat import HeatService
        hs = HeatService()
        stats = hs.get_heat_stats()

        return (
            f"📊 Memory: {stats['total_memories']} total | "
            f"🔥 {stats['hot_count']} hot | "
            f"❄️ {stats['cold_count']} cold | "
            f"Avg heat: {stats['avg_heat']}"
        )
    except Exception as e:
        return f"<!-- Heat summary failed: {e} -->"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--stale", type=float, help="Only load if stale (hours)")
    parser.add_argument("--summary", action="store_true", help="Show heat summary")
    parser.add_argument("--limit", type=int, default=10, help="Memory limit")
    args = parser.parse_args()

    if args.summary:
        print(get_heat_summary())
    elif args.stale:
        result = load_if_stale(args.stale, args.limit)
        if result:
            print(result)
        else:
            print("<!-- Cache is fresh -->")
    else:
        print(load_hot_memories(args.limit))
