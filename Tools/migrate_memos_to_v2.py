#!/usr/bin/env python3
"""
MemOS to Memory V2 Migration Script

Migrates data from MemOS (ChromaDB + Neo4j) to Memory V2 (Neon PostgreSQL).

Usage:
    python Tools/migrate_memos_to_v2.py --dry-run          # Preview what would be migrated
    python Tools/migrate_memos_to_v2.py --limit 10         # Migrate first 10 items
    python Tools/migrate_memos_to_v2.py --confirm          # Full migration

Data sources:
    - ChromaDB collections (observations, commitments, decisions, patterns, etc.)
    - Neo4j graph relationships (if available)
    - SQLite RelationshipStore (if available)

Output:
    - Migrated memories in Memory V2 with preserved metadata
    - Relationships stored via RelationshipStore
    - Migration log with statistics
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Conditional imports with graceful fallbacks
try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    print("⚠️  chromadb not installed. Run: pip install chromadb")

try:
    from Tools.memory_v2.service import MemoryService
    MEMORY_V2_AVAILABLE = True
except ImportError as e:
    MEMORY_V2_AVAILABLE = False
    MemoryService = None
    # Don't exit here - we'll check later if actually needed

try:
    from Tools.relationships import RelationshipStore, get_relationship_store
    RELATIONSHIPS_AVAILABLE = True
except ImportError:
    RELATIONSHIPS_AVAILABLE = False
    print("⚠️  RelationshipStore not available")


# Collection to domain mapping
COLLECTION_TO_DOMAIN = {
    "observations": "general",
    "commitments": "work",
    "decisions": "personal",
    "patterns": "pattern",
    "conversations": "relationship",
    "entities": "general",
    "memory_activities": "personal",
    "memory_struggles": "health",
    "memory_values": "personal",
}


class MigrationStats:
    """Track migration statistics."""

    def __init__(self):
        self.total_items = 0
        self.migrated = 0
        self.skipped = 0
        self.errors = 0
        self.errors_detail = []
        self.collections = {}

    def add_collection(self, name: str, count: int):
        """Record collection count."""
        self.collections[name] = count
        self.total_items += count

    def record_success(self, collection: str):
        """Record successful migration."""
        self.migrated += 1

    def record_skip(self, reason: str):
        """Record skipped item."""
        self.skipped += 1

    def record_error(self, error: str, item: Dict = None):
        """Record migration error."""
        self.errors += 1
        self.errors_detail.append({
            "error": error,
            "item": item.get("id") if item and "id" in item else "unknown",
            "timestamp": datetime.now().isoformat()
        })

    def summary(self) -> str:
        """Generate summary report."""
        lines = [
            "\n" + "=" * 60,
            "MIGRATION SUMMARY",
            "=" * 60,
            f"Total items found: {self.total_items}",
            f"Successfully migrated: {self.migrated}",
            f"Skipped: {self.skipped}",
            f"Errors: {self.errors}",
            "",
            "Collections:",
        ]

        for name, count in self.collections.items():
            lines.append(f"  - {name}: {count} items")

        if self.errors_detail:
            lines.append("\nErrors:")
            for err in self.errors_detail[:5]:  # Show first 5
                lines.append(f"  - {err['error']} (item: {err['item']})")
            if len(self.errors_detail) > 5:
                lines.append(f"  ... and {len(self.errors_detail) - 5} more")

        lines.append("=" * 60)
        return "\n".join(lines)


class MemOSMigrator:
    """Migrate data from MemOS to Memory V2."""

    def __init__(self, dry_run: bool = False, limit: Optional[int] = None):
        """
        Initialize migrator.

        Args:
            dry_run: If True, preview migration without writing to Memory V2
            limit: Maximum number of items to migrate (None = all)
        """
        self.dry_run = dry_run
        self.limit = limit
        self.stats = MigrationStats()
        self.memory_v2 = None
        self.chroma_client = None
        self.relationships = None

        # Initialize Memory V2
        if not dry_run:
            if not MEMORY_V2_AVAILABLE:
                print("❌ Memory V2 not available (missing dependencies)")
                print("   Install: pip install psycopg2-binary mem0ai")
                raise RuntimeError("Memory V2 required for live migration")
            try:
                self.memory_v2 = MemoryService()
                print("✓ Memory V2 initialized")
            except Exception as e:
                print(f"❌ Failed to initialize Memory V2: {e}")
                raise
        else:
            # Dry run mode - Memory V2 not needed
            print("🔍 Dry-run mode: Memory V2 not required")

        # Initialize ChromaDB
        if CHROMA_AVAILABLE:
            self._init_chromadb()

        # Initialize RelationshipStore
        if RELATIONSHIPS_AVAILABLE and not dry_run:
            try:
                self.relationships = get_relationship_store()
                print("✓ RelationshipStore initialized")
            except Exception as e:
                print(f"⚠️  RelationshipStore init failed: {e}")

    def _init_chromadb(self):
        """Initialize ChromaDB client."""
        try:
            # Try server first
            self.chroma_client = chromadb.HttpClient(host='localhost', port=8000)
            self.chroma_client.heartbeat()
            print("✓ Connected to ChromaDB server")
        except Exception:
            # Fallback to local persistent storage
            chroma_path = Path.home() / ".claude" / "Memory" / "vectors"
            if not chroma_path.exists():
                print(f"❌ ChromaDB storage not found at {chroma_path}")
                self.chroma_client = None
                return

            try:
                # Use PersistentClient for ChromaDB 1.4+
                self.chroma_client = chromadb.PersistentClient(path=str(chroma_path))
                print(f"✓ Connected to ChromaDB at {chroma_path}")
            except Exception as e:
                print(f"❌ Failed to connect to ChromaDB: {e}")
                self.chroma_client = None

    def migrate_chromadb_collection(self, collection_name: str) -> int:
        """
        Migrate a single ChromaDB collection.

        Args:
            collection_name: Name of the collection to migrate

        Returns:
            Number of items migrated from this collection
        """
        if not self.chroma_client:
            print(f"⚠️  ChromaDB not available, skipping {collection_name}")
            return 0

        try:
            collection = self.chroma_client.get_collection(name=collection_name)
        except Exception as e:
            print(f"⚠️  Collection '{collection_name}' not found: {e}")
            return 0

        # Get all documents from collection
        try:
            # ChromaDB's get() returns all documents if no filters provided
            results = collection.get(include=['documents', 'metadatas', 'embeddings'])
        except Exception as e:
            print(f"❌ Failed to read collection '{collection_name}': {e}")
            self.stats.record_error(f"Failed to read collection: {e}")
            return 0

        if not results or not results.get('documents'):
            print(f"  Collection '{collection_name}' is empty")
            return 0

        count = len(results['documents'])
        self.stats.add_collection(collection_name, count)
        print(f"\n📦 Processing collection '{collection_name}': {count} items")

        migrated = 0
        items_to_process = results['documents']
        if self.limit:
            # Account for items already migrated globally across all collections
            remaining = self.limit - self.stats.migrated
            items_to_process = items_to_process[:remaining]

        for i, doc in enumerate(items_to_process):
            # Extract metadata
            metadata = results['metadatas'][i] if results.get('metadatas') else {}
            item_id = results['ids'][i] if results.get('ids') else f"{collection_name}_{i}"

            # Build Memory V2 metadata
            v2_metadata = {
                "source": metadata.get("source", "memos_migration"),
                "domain": metadata.get("domain") or COLLECTION_TO_DOMAIN.get(collection_name, "general"),
                "migrated_from": "MemOS",
                "original_collection": collection_name,
                "original_id": item_id,
                "migration_timestamp": datetime.now().isoformat(),
            }

            # Preserve additional metadata fields
            for key in ["client", "project", "entities", "timestamp", "priority", "tags"]:
                if key in metadata:
                    v2_metadata[key] = metadata[key]

            # Migration preview
            if self.dry_run:
                print(f"  [{i+1}/{len(items_to_process)}] Would migrate:")
                print(f"    ID: {item_id}")
                print(f"    Content: {doc[:80]}..." if len(doc) > 80 else f"    Content: {doc}")
                print(f"    Metadata: {json.dumps(v2_metadata, indent=6)}")
                self.stats.record_success(collection_name)  # Track dry-run items in global counter
                migrated += 1
                continue

            # Actually migrate to Memory V2
            try:
                result = self.memory_v2.add(content=doc, metadata=v2_metadata)
                if result:
                    self.stats.record_success(collection_name)
                    migrated += 1
                    print(f"  ✓ [{i+1}/{len(items_to_process)}] Migrated: {doc[:60]}...")
                else:
                    self.stats.record_error(f"Memory V2 add() returned None", {"id": item_id})
                    print(f"  ✗ [{i+1}/{len(items_to_process)}] Failed: add() returned None")
            except Exception as e:
                self.stats.record_error(str(e), {"id": item_id, "content": doc[:50]})
                print(f"  ✗ [{i+1}/{len(items_to_process)}] Error: {e}")

            # Check limit
            if self.limit and self.stats.migrated >= self.limit:
                print(f"\n⚠️  Reached limit of {self.limit} items")
                break

        return migrated

    def migrate_all_collections(self) -> None:
        """Migrate all ChromaDB collections."""
        if not self.chroma_client:
            print("❌ ChromaDB not available. Cannot migrate.")

            # Check if ChromaDB database exists
            chroma_path = Path.home() / ".claude" / "Memory" / "vectors" / "chroma.sqlite3"
            if chroma_path.exists():
                size_mb = chroma_path.stat().st_size / (1024 * 1024)
                print(f"   Note: ChromaDB database found at {chroma_path}")
                print(f"   Size: {size_mb:.2f} MB")
                print(f"   Install chromadb to read: pip install chromadb")
            else:
                print(f"   No ChromaDB database found at {chroma_path}")

            return

        print("\n" + "=" * 60)
        print("CHROMADB MIGRATION")
        print("=" * 60)

        # Get all collections
        try:
            collections = self.chroma_client.list_collections()
            collection_names = [c.name for c in collections]
            print(f"Found {len(collection_names)} collections: {', '.join(collection_names)}")
        except Exception as e:
            print(f"❌ Failed to list collections: {e}")
            return

        # Migrate each collection
        for collection_name in collection_names:
            if self.limit and self.stats.migrated >= self.limit:
                print(f"\n⚠️  Reached migration limit of {self.limit}")
                break

            self.migrate_chromadb_collection(collection_name)

    def run(self) -> MigrationStats:
        """
        Execute full migration.

        Returns:
            Migration statistics
        """
        mode = "DRY RUN" if self.dry_run else "LIVE MIGRATION"
        limit_str = f" (limit: {self.limit})" if self.limit else ""

        print(f"\n{'=' * 60}")
        print(f"MemOS → Memory V2 Migration - {mode}{limit_str}")
        print(f"{'=' * 60}")
        print(f"Started at: {datetime.now().isoformat()}\n")

        if self.dry_run:
            print("🔍 DRY RUN MODE - No data will be written")
            print("   Run with --confirm to execute migration\n")

        # Migrate ChromaDB collections
        self.migrate_all_collections()

        # TODO: Migrate Neo4j data if available
        # For now, Neo4j package is not installed, so we skip

        # Print summary
        print(self.stats.summary())

        return self.stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate MemOS data to Memory V2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview migration (no changes)
  python Tools/migrate_memos_to_v2.py --dry-run

  # Migrate first 10 items for testing
  python Tools/migrate_memos_to_v2.py --limit 10

  # Full migration (requires --confirm flag)
  python Tools/migrate_memos_to_v2.py --confirm

  # Combine flags: test with limit in dry-run mode
  python Tools/migrate_memos_to_v2.py --dry-run --limit 5
        """
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without writing to Memory V2"
    )

    parser.add_argument(
        "--limit",
        type=int,
        metavar="N",
        help="Migrate only first N items (for testing)"
    )

    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm full migration (required for live migration)"
    )

    args = parser.parse_args()

    # Validation: require --dry-run or --confirm
    if not args.dry_run and not args.confirm:
        print("❌ Error: Must specify either --dry-run or --confirm")
        print("   Use --dry-run to preview migration")
        print("   Use --confirm to execute migration")
        sys.exit(1)

    # Run migration
    try:
        migrator = MemOSMigrator(dry_run=args.dry_run, limit=args.limit)
        stats = migrator.run()

        # Exit with error code if there were errors
        if stats.errors > 0:
            print(f"\n⚠️  Migration completed with {stats.errors} errors")
            sys.exit(1)
        else:
            print(f"\n✓ Migration completed successfully")
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Migration failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
