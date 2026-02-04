"""
Wrapper for Memory V2 heat decay with deterministic output.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Tools.memory_v2.heat import apply_decay


def main() -> int:
    try:
        count = apply_decay()
        line = f"{datetime.now(timezone.utc).isoformat()} DECAY_OK {count}"
        with open("/tmp/memory_heat_decay.last", "w", encoding="utf-8") as handle:
            handle.write(line + "\n")
        print(line)
        return 0
    except Exception as exc:
        line = f"{datetime.now(timezone.utc).isoformat()} DECAY_ERROR {type(exc).__name__}: {exc}"
        with open("/tmp/memory_heat_decay.last", "w", encoding="utf-8") as handle:
            handle.write(line + "\n")
        print(line)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
