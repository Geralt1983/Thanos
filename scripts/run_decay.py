#!/usr/bin/env python3
"""
Apply heat decay to memories.

Run daily via cron:
0 3 * * * cd ~/Projects/Thanos && .venv/bin/python scripts/run_decay.py

Or manually:
python scripts/run_decay.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from Tools.memory_v2.heat import get_heat_service


def main():
    """Run decay on all memories."""
    print(f"Running memory decay at {datetime.now()}")

    try:
        heat_service = get_heat_service()
        count = heat_service.apply_decay()
        print(f"✓ Decayed {count} memories")

        # Print stats
        stats = heat_service.get_heat_stats()
        print(f"\nStats:")
        print(f"  Total: {stats.get('total_memories', 0)}")
        print(f"  Avg Heat: {stats.get('avg_heat', 0):.2f}")
        print(f"  Hot: {stats.get('hot_count', 0)}")
        print(f"  Cold: {stats.get('cold_count', 0)}")
        print(f"  Pinned: {stats.get('pinned_count', 0)}")

        return 0

    except Exception as e:
        print(f"✗ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
