"""
Memory: Quick Backup Command

Creates a timestamped backup of all memories and relationships to the backups/ directory.
Automatically verifies backup integrity after creation.

Usage:
    python -m commands.memory.backup [--output DIR] [--no-verify]

Arguments:
    --output    Backup directory (default: ./backups)
    --no-verify Skip verification after backup

Examples:
    python -m commands.memory.backup
    python -m commands.memory.backup --output ./custom-backups
    python -m commands.memory.backup --no-verify

Model: Direct data export (no LLM required)
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.memory_export import MemoryExporter


# System prompt for potential LLM-based summary generation
SYSTEM_PROMPT = """You are Jeremy's memory backup assistant.

Your role:
- Create reliable backups of all memory data
- Ensure data integrity through verification
- Provide clear backup status and location
- Safeguard against data loss

Context:
- Data comes from Memory V2 (Neon pgvector) and Relationship Store (SQLite)
- Backups include memories with embeddings, relationships, and metadata
- Used for disaster recovery and data safety
"""


# =============================================================================
# BACKUP COMMAND
# =============================================================================


def backup_memories(
    output: str = "./backups",
    verify: bool = True
) -> dict:
    """
    Create a timestamped backup of all memories and relationships.

    Args:
        output: Base backup directory path
        verify: Whether to verify backup integrity after creation

    Returns:
        Dictionary with backup results including:
        - output_path: Path to backup directory
        - memory_count: Number of memories backed up
        - relationship_count: Number of relationships backed up
        - files: List of created files
        - checksums: Checksums for verification
        - verified: Whether backup was verified

    Raises:
        Exception: If backup fails
    """
    # Create timestamped backup directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{output}/memory_{timestamp}"

    print(f"\n💾 Creating memory backup...")
    print(f"   Destination: {backup_path}")
    print(f"   Timestamp: {timestamp}")

    # Initialize exporter
    exporter = MemoryExporter(user_id="jeremy")

    # Perform backup (always use JSON for complete backup)
    result = exporter.export_all(
        output_path=backup_path,
        format="json",
        include_vectors=True  # Always include vectors in backups
    )

    # Display results
    print(f"\n✓ Backup complete")
    print(f"  Location: {result['output_path']}")
    print(f"  Memories: {result['memory_count']:,}")
    print(f"  Relationships: {result['relationship_count']:,}")
    print(f"  Files: {len(result['files'])}")

    for file_path in result['files']:
        checksum = result['checksums'].get(file_path, "N/A")
        # Display abbreviated checksum for readability
        short_checksum = checksum[:16] if len(checksum) > 16 else checksum
        print(f"    - {Path(file_path).name} (checksum: {short_checksum}...)")

    if 'checksum' in result:
        print(f"  Combined checksum: {result['checksum'][:32]}...")

    # Verify backup if requested
    if verify:
        print(f"\n🔍 Verifying backup integrity...")
        is_valid = exporter.verify_export(result['output_path'])

        if is_valid:
            print(f"✓ Backup verified successfully")
            result['verified'] = True
        else:
            print(f"✗ Backup verification failed")
            result['verified'] = False
            sys.exit(1)

    return result


# =============================================================================
# CLI ENTRY POINT
# =============================================================================


def main():
    """CLI entry point for memory backup command."""
    parser = argparse.ArgumentParser(
        description="Create timestamped backup of Thanos Memory V2 data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m commands.memory.backup
  python -m commands.memory.backup --output ./custom-backups
  python -m commands.memory.backup --no-verify

Backup Format:
  Backups are created in timestamped directories (memory_YYYYMMDD_HHMMSS)
  in JSON format with full vector embeddings and relationship data.
  Each backup is automatically verified for integrity.

Retention:
  Use scripts/schedule_memory_backup.sh to set up automated daily backups
  with retention policy (7 daily + 4 weekly backups).
        """
    )

    parser.add_argument(
        "--output",
        default="./backups",
        help="Backup directory (default: ./backups)"
    )

    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip verification after backup"
    )

    args = parser.parse_args()

    try:
        backup_memories(
            output=args.output,
            verify=not args.no_verify
        )

        print("\n✓ Memory backup complete")
        sys.exit(0)

    except Exception as e:
        print(f"\n✗ Backup failed: {e}")
        import logging
        logging.error(f"Backup failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
