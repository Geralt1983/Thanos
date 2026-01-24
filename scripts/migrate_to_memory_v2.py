#!/usr/bin/env python3
"""
Memory Migration Utility: Legacy -> Memory V2

Migrates memories from legacy backends (ChromaDB, MemOS) into Memory V2
(mem0 + Neon pgvector + heat decay).

Usage:
    python scripts/migrate_to_memory_v2.py --dry-run     # Preview without changes
    python scripts/migrate_to_memory_v2.py --migrate     # Execute migration
    python scripts/migrate_to_memory_v2.py --status      # Check migration status

Migration Sources:
    1. MemOS (memory/services/memory_service.py)
    2. Legacy ChromaDB (Tools/memory/service.py)
    3. Session history files (History/Sessions/*.json)
    4. Brain dump files (State/brain_dumps.json)

Preservation:
    - Original timestamps are preserved as 'original_timestamp'
    - Source is tagged as 'legacy_migration'
    - Original source file is recorded for traceability
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import Memory V2
try:
    from Tools.memory_v2.service import get_memory_service, MemoryService
    MEMORY_V2_AVAILABLE = True
except ImportError as e:
    logger.error(f"Memory V2 not available: {e}")
    MEMORY_V2_AVAILABLE = False


class MemoryMigrator:
    """Migrates memories from legacy systems to Memory V2."""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.stats = {
            "memos": {"found": 0, "migrated": 0, "skipped": 0, "errors": 0},
            "chroma": {"found": 0, "migrated": 0, "skipped": 0, "errors": 0},
            "sessions": {"found": 0, "migrated": 0, "skipped": 0, "errors": 0},
            "brain_dumps": {"found": 0, "migrated": 0, "skipped": 0, "errors": 0},
        }

        if MEMORY_V2_AVAILABLE and not dry_run:
            self.v2_service = get_memory_service()
        else:
            self.v2_service = None

    def migrate_all(self) -> Dict[str, Any]:
        """Run full migration from all sources."""
        logger.info(f"Starting migration {'(DRY RUN)' if self.dry_run else '(LIVE)'}")

        # Migrate from each source
        self._migrate_memos()
        self._migrate_chroma()
        self._migrate_sessions()
        self._migrate_brain_dumps()

        return self._get_summary()

    def _migrate_memos(self):
        """Migrate from MemOS hybrid system."""
        logger.info("Scanning MemOS memories...")

        try:
            from memory.services.memory_service import memory_service
            memories = memory_service.get_all(limit=1000)

            self.stats["memos"]["found"] = len(memories)
            logger.info(f"Found {len(memories)} MemOS memories")

            for mem in memories:
                self._migrate_memory(mem, "memos")

        except ImportError:
            logger.warning("MemOS not available, skipping")
        except Exception as e:
            logger.error(f"MemOS migration error: {e}")
            self.stats["memos"]["errors"] += 1

    def _migrate_chroma(self):
        """Migrate from legacy ChromaDB + SQLite system."""
        logger.info("Scanning ChromaDB memories...")

        try:
            from Tools.memory.service import get_memory_service as get_legacy_service
            legacy_service = get_legacy_service()

            # Get all activities from SQLite
            if hasattr(legacy_service, 'store'):
                activities = asyncio.run(
                    legacy_service.store.get_activities_by_range(
                        datetime(2020, 1, 1).date(),
                        datetime.now().date(),
                        limit=1000
                    )
                )

                self.stats["chroma"]["found"] = len(activities)
                logger.info(f"Found {len(activities)} ChromaDB activities")

                for activity in activities:
                    self._migrate_activity(activity, "chroma")

        except ImportError:
            logger.warning("Legacy ChromaDB service not available, skipping")
        except Exception as e:
            logger.error(f"ChromaDB migration error: {e}")
            self.stats["chroma"]["errors"] += 1

    def _migrate_sessions(self):
        """Migrate significant conversation turns from session history."""
        logger.info("Scanning session history...")

        sessions_dir = PROJECT_ROOT / "History" / "Sessions"
        if not sessions_dir.exists():
            logger.warning("Sessions directory not found, skipping")
            return

        session_files = list(sessions_dir.glob("*.json"))
        logger.info(f"Found {len(session_files)} session files")

        for session_file in session_files:
            try:
                with open(session_file) as f:
                    data = json.load(f)

                history = data.get("history", [])
                session_id = data.get("id", session_file.stem)

                # Extract significant turns (those with decisions, blockers, etc.)
                for msg in history:
                    content = msg.get("content", "")
                    if self._is_significant(content):
                        self.stats["sessions"]["found"] += 1
                        self._migrate_session_message(msg, session_id, session_file.name)

            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Error parsing {session_file.name}: {e}")
                self.stats["sessions"]["errors"] += 1

    def _migrate_brain_dumps(self):
        """Migrate unprocessed brain dumps."""
        logger.info("Scanning brain dumps...")

        brain_dumps_file = PROJECT_ROOT / "State" / "brain_dumps.json"
        if not brain_dumps_file.exists():
            logger.warning("Brain dumps file not found, skipping")
            return

        try:
            with open(brain_dumps_file) as f:
                data = json.load(f)

            entries = data.get("entries", [])
            self.stats["brain_dumps"]["found"] = len(entries)
            logger.info(f"Found {len(entries)} brain dump entries")

            for entry in entries:
                self._migrate_brain_dump(entry)

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Brain dumps file error: {e}")
            self.stats["brain_dumps"]["errors"] += 1

    def _migrate_memory(self, mem: Dict, source_type: str):
        """Migrate a single memory from MemOS."""
        try:
            content = mem.get("memory", mem.get("content", ""))
            if not content:
                self.stats[source_type]["skipped"] += 1
                return

            metadata = {
                "source": "legacy_migration",
                "original_source": source_type,
                "original_id": mem.get("id"),
                "original_timestamp": mem.get("created_at"),
                "client": mem.get("metadata", {}).get("client"),
                "memory_type": mem.get("metadata", {}).get("memory_type"),
            }

            if self.dry_run:
                logger.debug(f"Would migrate: {content[:50]}...")
                self.stats[source_type]["migrated"] += 1
            else:
                result = self.v2_service.add(content, metadata=metadata)
                if result:
                    self.stats[source_type]["migrated"] += 1
                else:
                    self.stats[source_type]["errors"] += 1

        except Exception as e:
            logger.warning(f"Error migrating memory: {e}")
            self.stats[source_type]["errors"] += 1

    def _migrate_activity(self, activity, source_type: str):
        """Migrate a single activity from ChromaDB."""
        try:
            content = activity.content or activity.title
            if not content:
                self.stats[source_type]["skipped"] += 1
                return

            metadata = {
                "source": "legacy_migration",
                "original_source": source_type,
                "original_id": activity.id,
                "original_timestamp": str(activity.timestamp) if activity.timestamp else None,
                "project": activity.project,
                "activity_type": activity.activity_type,
            }

            if self.dry_run:
                logger.debug(f"Would migrate activity: {content[:50]}...")
                self.stats[source_type]["migrated"] += 1
            else:
                result = self.v2_service.add(content, metadata=metadata)
                if result:
                    self.stats[source_type]["migrated"] += 1
                else:
                    self.stats[source_type]["errors"] += 1

        except Exception as e:
            logger.warning(f"Error migrating activity: {e}")
            self.stats[source_type]["errors"] += 1

    def _migrate_session_message(self, msg: Dict, session_id: str, source_file: str):
        """Migrate a significant session message."""
        try:
            content = msg.get("content", "")
            if not content:
                self.stats["sessions"]["skipped"] += 1
                return

            metadata = {
                "source": "legacy_migration",
                "original_source": "session_history",
                "source_file": source_file,
                "session_id": session_id,
                "role": msg.get("role"),
                "original_timestamp": msg.get("timestamp"),
                "type": "session_log",
            }

            if self.dry_run:
                logger.debug(f"Would migrate session msg: {content[:50]}...")
                self.stats["sessions"]["migrated"] += 1
            else:
                result = self.v2_service.add(content, metadata=metadata)
                if result:
                    self.stats["sessions"]["migrated"] += 1
                else:
                    self.stats["sessions"]["errors"] += 1

        except Exception as e:
            logger.warning(f"Error migrating session message: {e}")
            self.stats["sessions"]["errors"] += 1

    def _migrate_brain_dump(self, entry: Dict):
        """Migrate a brain dump entry."""
        try:
            content = entry.get("content", "")
            if not content:
                self.stats["brain_dumps"]["skipped"] += 1
                return

            metadata = {
                "source": "legacy_migration",
                "original_source": "brain_dump",
                "category": entry.get("category"),
                "original_timestamp": entry.get("timestamp"),
                "processed": entry.get("processed", False),
                "type": "brain_dump",
            }

            if self.dry_run:
                logger.debug(f"Would migrate brain dump: {content[:50]}...")
                self.stats["brain_dumps"]["migrated"] += 1
            else:
                result = self.v2_service.add(content, metadata=metadata)
                if result:
                    self.stats["brain_dumps"]["migrated"] += 1
                else:
                    self.stats["brain_dumps"]["errors"] += 1

        except Exception as e:
            logger.warning(f"Error migrating brain dump: {e}")
            self.stats["brain_dumps"]["errors"] += 1

    def _is_significant(self, content: str) -> bool:
        """Check if a message is significant enough to migrate."""
        if len(content) < 50:
            return False

        significance_markers = [
            "decided", "decision", "blocked", "blocker", "stuck",
            "completed", "finished", "solved", "fixed",
            "important", "critical", "urgent",
            "learned", "realized", "discovered",
            "error", "bug", "issue",
            "pattern", "approach", "strategy",
        ]

        content_lower = content.lower()
        return any(marker in content_lower for marker in significance_markers)

    def _get_summary(self) -> Dict[str, Any]:
        """Get migration summary."""
        total_found = sum(s["found"] for s in self.stats.values())
        total_migrated = sum(s["migrated"] for s in self.stats.values())
        total_errors = sum(s["errors"] for s in self.stats.values())

        return {
            "dry_run": self.dry_run,
            "sources": self.stats,
            "totals": {
                "found": total_found,
                "migrated": total_migrated,
                "errors": total_errors,
            }
        }


def get_migration_status() -> Dict[str, Any]:
    """Check current migration status."""
    status = {
        "memory_v2_available": MEMORY_V2_AVAILABLE,
        "memory_v2_stats": None,
        "legacy_sources": {},
    }

    # Check Memory V2
    if MEMORY_V2_AVAILABLE:
        try:
            service = get_memory_service()
            status["memory_v2_stats"] = service.stats()
        except Exception as e:
            status["memory_v2_error"] = str(e)

    # Check MemOS
    try:
        from memory.services.memory_service import memory_service
        memos_count = len(memory_service.get_all(limit=1))
        status["legacy_sources"]["memos"] = {"available": True, "count": memos_count}
    except Exception:
        status["legacy_sources"]["memos"] = {"available": False}

    # Check ChromaDB
    try:
        from Tools.memory.service import get_memory_service as get_legacy_service
        status["legacy_sources"]["chroma"] = {"available": True}
    except Exception:
        status["legacy_sources"]["chroma"] = {"available": False}

    # Check session history
    sessions_dir = PROJECT_ROOT / "History" / "Sessions"
    if sessions_dir.exists():
        count = len(list(sessions_dir.glob("*.json")))
        status["legacy_sources"]["sessions"] = {"available": True, "count": count}
    else:
        status["legacy_sources"]["sessions"] = {"available": False}

    # Check brain dumps
    brain_dumps_file = PROJECT_ROOT / "State" / "brain_dumps.json"
    if brain_dumps_file.exists():
        try:
            with open(brain_dumps_file) as f:
                data = json.load(f)
            count = len(data.get("entries", []))
            status["legacy_sources"]["brain_dumps"] = {"available": True, "count": count}
        except Exception:
            status["legacy_sources"]["brain_dumps"] = {"available": True, "count": "unknown"}
    else:
        status["legacy_sources"]["brain_dumps"] = {"available": False}

    return status


def main():
    parser = argparse.ArgumentParser(
        description="Migrate memories from legacy systems to Memory V2"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without making changes"
    )
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Execute the migration"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Check migration status"
    )

    args = parser.parse_args()

    if args.status:
        status = get_migration_status()
        print("\n=== Memory Migration Status ===\n")
        print(f"Memory V2 Available: {status['memory_v2_available']}")
        if status.get("memory_v2_stats"):
            stats = status["memory_v2_stats"]
            print(f"Memory V2 Total: {stats.get('total', 0)} memories")
            print(f"Memory V2 Hot: {stats.get('hot_count', 0)}")
            print(f"Memory V2 Cold: {stats.get('cold_count', 0)}")

        print("\nLegacy Sources:")
        for source, info in status.get("legacy_sources", {}).items():
            if info.get("available"):
                count = info.get("count", "yes")
                print(f"  ✓ {source}: {count}")
            else:
                print(f"  ✗ {source}: not available")

        return

    if args.migrate:
        if not MEMORY_V2_AVAILABLE:
            logger.error("Memory V2 not available. Cannot proceed with migration.")
            sys.exit(1)

        print("\n⚠️  This will migrate all legacy memories to Memory V2.")
        confirm = input("Type 'yes' to proceed: ")
        if confirm.lower() != 'yes':
            print("Migration cancelled.")
            return

        migrator = MemoryMigrator(dry_run=False)
    elif args.dry_run:
        migrator = MemoryMigrator(dry_run=True)
    else:
        parser.print_help()
        return

    summary = migrator.migrate_all()

    print("\n=== Migration Summary ===\n")
    print(f"Mode: {'DRY RUN' if summary['dry_run'] else 'LIVE MIGRATION'}")
    print()

    for source, stats in summary["sources"].items():
        print(f"{source}:")
        print(f"  Found: {stats['found']}")
        print(f"  Migrated: {stats['migrated']}")
        print(f"  Skipped: {stats['skipped']}")
        print(f"  Errors: {stats['errors']}")
        print()

    totals = summary["totals"]
    print("TOTALS:")
    print(f"  Found: {totals['found']}")
    print(f"  Migrated: {totals['migrated']}")
    print(f"  Errors: {totals['errors']}")

    if summary["dry_run"]:
        print("\n💡 Run with --migrate to execute the migration")


if __name__ == "__main__":
    main()
