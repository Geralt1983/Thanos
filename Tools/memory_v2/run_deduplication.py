"""Wrapper for Memory V2 deduplication with deterministic output."""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Tools.memory_v2.deduplication import deduplicate_memories


def _env_bool(key: str, default: str = "false") -> bool:
    return os.getenv(key, default).strip().lower() in {"1", "true", "yes", "y"}


def main() -> int:
    try:
        threshold = float(os.getenv("MEMORY_DEDUP_THRESHOLD", "0.95"))
        recent_days = int(os.getenv("MEMORY_DEDUP_RECENT_DAYS", "7"))
        recent_limit = int(os.getenv("MEMORY_DEDUP_RECENT_LIMIT", "500"))
        dry_run = _env_bool("MEMORY_DEDUP_DRY_RUN", "false")

        results = deduplicate_memories(
            similarity_threshold=threshold,
            dry_run=dry_run,
            recent_days=recent_days,
            recent_limit=recent_limit,
        )

        line = (
            f"{datetime.now(timezone.utc).isoformat()} "
            "DEDUP_OK "
            f"found={results.get('duplicates_found', 0)} "
            f"merged={results.get('duplicates_merged', 0)} "
            f"dry_run={results.get('dry_run', False)}"
        )
        with open("/tmp/memory_dedup.last", "w", encoding="utf-8") as handle:
            handle.write(line + "\n")
        print(line)
        return 0
    except Exception as exc:
        line = f"{datetime.now(timezone.utc).isoformat()} DEDUP_ERROR {type(exc).__name__}: {exc}"
        with open("/tmp/memory_dedup.last", "w", encoding="utf-8") as handle:
            handle.write(line + "\n")
        print(line)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
