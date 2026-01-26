"""
Memory: Restore Command

Restores memories and relationships from a backup directory.
Includes safety checks and verification before restore.

Usage:
    python -m commands.memory.restore --source DIR [--dry-run] [--force] [--conflict-mode MODE]

Arguments:
    --source         Path to backup directory (required)
    --dry-run        Preview restore without making changes
    --force          Skip confirmation prompt (use with caution)
    --conflict-mode  How to handle duplicate IDs: skip or update (default: skip)

Examples:
    # Preview what would be restored
    python -m commands.memory.restore --source ./backups/memory_20240126_120000 --dry-run

    # Restore with confirmation
    python -m commands.memory.restore --source ./backups/memory_20240126_120000

    # Restore without confirmation (automated restore)
    python -m commands.memory.restore --source ./backups/memory_20240126_120000 --force

    # Restore and update conflicts
    python -m commands.memory.restore --source ./backups/memory_20240126_120000 --conflict-mode update

Model: Direct data restore (no LLM required)
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.memory_export import MemoryExporter


# System prompt for potential LLM-based summary generation
SYSTEM_PROMPT = """You are Jeremy's memory restore assistant.

Your role:
- Restore memories and relationships from backup safely
- Verify backup integrity before restore
- Warn about potential data conflicts
- Ensure no data loss during restore operations

Context:
- Data is restored to Memory V2 (Neon pgvector) and Relationship Store (SQLite)
- Backups include memories with embeddings, relationships, and metadata
- Used for disaster recovery and data migration
"""


# =============================================================================
# RESTORE COMMAND
# =============================================================================


def restore_memories(
    source: str,
    dry_run: bool = False,
    conflict_mode: str = "skip",
    force: bool = False
) -> dict:
    """
    Restore memories and relationships from a backup directory.

    Args:
        source: Path to backup directory
        dry_run: Preview restore without making changes
        conflict_mode: How to handle duplicate IDs ("skip" or "update")
        force: Skip confirmation prompt

    Returns:
        Dictionary with restore results including:
        - memories_restored: Number of memories restored
        - memories_skipped: Number of memories skipped (conflicts)
        - memories_updated: Number of memories updated (if mode=update)
        - relationships_restored: Number of relationships restored
        - relationships_skipped: Number of relationships skipped
        - dry_run: Whether this was a dry run

    Raises:
        Exception: If restore fails
        ValueError: If backup is invalid or source doesn't exist
    """
    source_path = Path(source)

    # Validate source exists
    if not source_path.exists():
        raise ValueError(f"Backup source not found: {source}")

    if not source_path.is_dir():
        raise ValueError(f"Backup source is not a directory: {source}")

    print(f"\n{'🔍 [DRY RUN] ' if dry_run else '📥 '}Restoring memory from backup...")
    print(f"   Source: {source_path}")
    print(f"   Conflict mode: {conflict_mode}")

    # Initialize exporter
    exporter = MemoryExporter(user_id="jeremy")

    # Verify backup before restore
    print(f"\n🔍 Verifying backup integrity...")
    is_valid = exporter.verify_export(str(source_path))

    if not is_valid:
        print(f"✗ Backup verification failed")
        raise ValueError(f"Invalid or corrupted backup: {source}")

    print(f"✓ Backup verified successfully")

    # For actual restore (not dry-run), show warning and get confirmation
    if not dry_run and not force:
        print(f"\n⚠️  WARNING: This will restore data to your memory store")
        print(f"   Conflict mode: {conflict_mode}")

        if conflict_mode == "update":
            print(f"   Existing memories with matching IDs will be UPDATED")
        else:
            print(f"   Existing memories with matching IDs will be SKIPPED")

        print(f"\n   Use --dry-run to preview changes without restoring")

        response = input(f"\n   Continue with restore? (yes/no): ").strip().lower()

        if response not in ["yes", "y"]:
            print(f"\n✗ Restore cancelled by user")
            sys.exit(0)

    # Perform restore
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Restoring data...")

    result = exporter.restore_from_backup(
        backup_path=str(source_path),
        dry_run=dry_run,
        conflict_mode=conflict_mode
    )

    # Display results
    print(f"\n{'[DRY RUN COMPLETE] ' if dry_run else '✓ '}Restore {'preview' if dry_run else 'complete'}")

    # Memory stats
    memories_restored = result.get('memories_restored', 0)
    memories_skipped = result.get('memories_skipped', 0)
    memories_updated = result.get('memories_updated', 0)

    print(f"\n  Memories:")
    if conflict_mode == "update":
        print(f"    Restored: {memories_restored:,}")
        print(f"    Updated: {memories_updated:,}")
        print(f"    Skipped: {memories_skipped:,}")
    else:
        print(f"    Restored: {memories_restored:,}")
        print(f"    Skipped: {memories_skipped:,} (duplicates)")

    # Relationship stats
    relationships_restored = result.get('relationships_restored', 0)
    relationships_skipped = result.get('relationships_skipped', 0)
    relationships_updated = result.get('relationships_updated', 0)

    print(f"\n  Relationships:")
    if conflict_mode == "update":
        print(f"    Restored: {relationships_restored:,}")
        print(f"    Updated: {relationships_updated:,}")
        print(f"    Skipped: {relationships_skipped:,}")
    else:
        print(f"    Restored: {relationships_restored:,}")
        print(f"    Skipped: {relationships_skipped:,} (duplicates)")

    if dry_run:
        print(f"\n💡 This was a preview. Use without --dry-run to perform actual restore.")

    return result


# =============================================================================
# CLI ENTRY POINT
# =============================================================================


def main():
    """CLI entry point for memory restore command."""
    parser = argparse.ArgumentParser(
        description="Restore Thanos Memory V2 data from backup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview restore (recommended first step)
  python -m commands.memory.restore --source ./backups/memory_20240126_120000 --dry-run

  # Restore with confirmation prompt
  python -m commands.memory.restore --source ./backups/memory_20240126_120000

  # Automated restore without confirmation
  python -m commands.memory.restore --source ./backups/memory_20240126_120000 --force

  # Restore and update conflicts
  python -m commands.memory.restore --source ./backups/memory_20240126_120000 --conflict-mode update

Safety:
  - Always run with --dry-run first to preview changes
  - Backup is verified before restore begins
  - Confirmation prompt shown before actual restore (unless --force)
  - Duplicate IDs are handled according to --conflict-mode

Conflict Modes:
  skip   - Skip memories/relationships with duplicate IDs (default, safest)
  update - Update existing memories/relationships with backup data (overwrites)
        """
    )

    parser.add_argument(
        "--source",
        required=True,
        help="Path to backup directory to restore from"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview restore without making changes"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt (use with caution)"
    )

    parser.add_argument(
        "--conflict-mode",
        choices=["skip", "update"],
        default="skip",
        help="How to handle duplicate IDs: skip (default) or update"
    )

    args = parser.parse_args()

    try:
        restore_memories(
            source=args.source,
            dry_run=args.dry_run,
            conflict_mode=args.conflict_mode,
            force=args.force
        )

        if not args.dry_run:
            print("\n✓ Memory restore complete")

        sys.exit(0)

    except ValueError as e:
        print(f"\n✗ Invalid backup: {e}")
        sys.exit(1)

    except Exception as e:
        print(f"\n✗ Restore failed: {e}")
        import logging
        logging.error(f"Restore failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
