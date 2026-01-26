"""
Memory: Data Export Command

Exports memories and relationships from Memory V2 (pgvector) and Relationship Store (SQLite)
to JSON, CSV, or Markdown format for analysis and backup.

Usage:
    python -m commands.memory.export [--format FORMAT] [--output DIR] [--verify]

Arguments:
    --format    Output format: json, csv, or markdown (default: json)
    --output    Output directory (default: History/Exports/memory)
    --verify    Verify export integrity after completion
    --no-vectors    Exclude vector embeddings from export (smaller file size)
    --user      User ID to export memories for (default: jeremy)

Examples:
    python -m commands.memory.export --format json
    python -m commands.memory.export --format csv --output ./my-backup
    python -m commands.memory.export --format markdown --verify
    python -m commands.memory.export --no-vectors --output ./lightweight-export

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
SYSTEM_PROMPT = """You are Jeremy's memory export assistant.

Your role:
- Export memory data for analysis and backup
- Present data in clear, structured formats
- Ensure data integrity and completeness
- Provide helpful summaries of exported data

Context:
- Data comes from Memory V2 (Neon pgvector) and Relationship Store (SQLite)
- Includes memories with embeddings, relationships, and metadata
- Used for backup, analysis, and portability
"""


# =============================================================================
# EXPORT COMMAND
# =============================================================================


def export_memories(
    format: str = "json",
    output: str = "./History/Exports/memory",
    verify: bool = False,
    no_vectors: bool = False,
    user: str = "jeremy"
) -> dict:
    """
    Export memories and relationships from Memory V2.

    Args:
        format: Output format (json|csv|markdown)
        output: Output directory path
        verify: Whether to verify export integrity after completion
        no_vectors: Whether to exclude vector embeddings
        user: User ID to export memories for

    Returns:
        Dictionary with export results including:
        - output_path: Path to exported data
        - memory_count: Number of memories exported
        - relationship_count: Number of relationships exported
        - files: List of created files
        - checksums: Checksums for verification
        - verified: Whether export was verified (if verify=True)

    Raises:
        Exception: If export fails
    """
    print(f"\n🔍 Exporting memories...")
    print(f"   Format: {format}")
    print(f"   Output: {output}")
    print(f"   User: {user}")
    if no_vectors:
        print(f"   Mode: Lightweight (no vectors)")

    # Initialize exporter
    exporter = MemoryExporter(user_id=user)

    # Perform export
    result = exporter.export_all(
        output_path=output,
        format=format,
        include_vectors=not no_vectors
    )

    # Display results
    print(f"\n✓ Export complete")
    print(f"  Output: {result['output_path']}")
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

    # Verify export if requested
    if verify:
        print(f"\n🔍 Verifying export integrity...")
        is_valid = exporter.verify_export(result['output_path'])

        if is_valid:
            print(f"✓ Export verified successfully")
            result['verified'] = True
        else:
            print(f"✗ Export verification failed")
            result['verified'] = False
            sys.exit(1)

    return result


# =============================================================================
# CLI ENTRY POINT
# =============================================================================


def main():
    """CLI entry point for memory export command."""
    parser = argparse.ArgumentParser(
        description="Export Thanos Memory V2 data to portable formats",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m commands.memory.export --format json
  python -m commands.memory.export --format csv --output ./my-backup
  python -m commands.memory.export --format markdown --verify
  python -m commands.memory.export --no-vectors --output ./lightweight-export

Output formats:
  json     - Complete data with all fields, embeddings, and relationships
  csv      - Flattened data in separate CSV files (memories.csv, relationships.csv)
  markdown - Human-readable format with heat indicators and relationship graph

Verification:
  Use --verify to automatically validate export integrity after completion.
  Checks checksums, record counts, and data structure.
        """
    )

    parser.add_argument(
        "--format",
        choices=["json", "csv", "markdown"],
        default="json",
        help="Output format (default: json)"
    )

    parser.add_argument(
        "--output",
        default="./History/Exports/memory",
        help="Output directory (default: ./History/Exports/memory)"
    )

    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify export integrity after completion"
    )

    parser.add_argument(
        "--no-vectors",
        action="store_true",
        help="Exclude vector embeddings from export (smaller file size)"
    )

    parser.add_argument(
        "--user",
        default="jeremy",
        help="User ID to export memories for (default: jeremy)"
    )

    args = parser.parse_args()

    try:
        export_memories(
            format=args.format,
            output=args.output,
            verify=args.verify,
            no_vectors=args.no_vectors,
            user=args.user
        )

        print("\n✓ Memory export complete")
        sys.exit(0)

    except Exception as e:
        print(f"\n✗ Export failed: {e}")
        import logging
        logging.error(f"Export failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
