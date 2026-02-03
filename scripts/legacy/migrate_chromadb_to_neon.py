#!/usr/bin/env python3
"""
Migrate ChromaDB memories to Neon pgvector database.

This script reads memories from the ChromaDB database used by claude-mem
and inserts them into the new Neon pgvector database for Thanos Memory V2.

Usage:
    python scripts/migrate_chromadb_to_neon.py [--dry-run] [--batch-size N] [--limit N]

Options:
    --dry-run       Show what would be migrated without making changes
    --batch-size N  Number of records to insert per batch (default: 100)
    --limit N       Limit number of records to migrate (useful for testing)
"""

import os
import sys
import json
import sqlite3
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from contextlib import contextmanager

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_batch, RealDictCursor

# Load environment variables
load_dotenv(Path(__file__).parent.parent / '.env')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ChromaDB location
CHROMADB_PATH = Path.home() / '.claude-mem' / 'vector-db' / 'chroma.sqlite3'

# Neon database URL
NEON_DATABASE_URL = os.getenv('THANOS_MEMORY_DATABASE_URL')

# Map ChromaDB doc_type to Neon memory_type
DOC_TYPE_MAPPING = {
    'observation': 'pattern',
    'discovery': 'pattern',
    'decision': 'professional',
    'reflection': 'personal',
    'learning': 'pattern',
    'task': 'goal',
    'commitment': 'goal',
    'fact': 'fact',
    'insight': 'pattern',
}


class ChromaDBReader:
    """Read data from ChromaDB SQLite database."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        if not db_path.exists():
            raise FileNotFoundError(f"ChromaDB not found at {db_path}")

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def count_embeddings(self) -> int:
        """Count total embeddings in ChromaDB."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM embeddings")
            return cursor.fetchone()[0]

    def fetch_all_embeddings(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch all embeddings with their metadata.

        Returns list of dicts with:
        - embedding_id: Original ChromaDB ID
        - document: The text content
        - metadata: Dict of all metadata fields
        """
        with self._get_connection() as conn:
            # Query to get embeddings with all metadata
            query = """
                SELECT
                    e.id as internal_id,
                    e.embedding_id,
                    GROUP_CONCAT(
                        em.key || '=' || COALESCE(em.string_value,
                            CAST(em.int_value AS TEXT),
                            CAST(em.float_value AS TEXT),
                            CASE WHEN em.bool_value = 1 THEN 'true' ELSE 'false' END),
                        '||'
                    ) as metadata_str
                FROM embeddings e
                LEFT JOIN embedding_metadata em ON e.id = em.id
                GROUP BY e.id
            """

            if limit:
                query += f" LIMIT {limit}"

            cursor = conn.execute(query)

            results = []
            for row in cursor:
                record = {
                    'internal_id': row['internal_id'],
                    'embedding_id': row['embedding_id'],
                    'metadata': {}
                }

                # Parse metadata string
                if row['metadata_str']:
                    for item in row['metadata_str'].split('||'):
                        if '=' in item:
                            key, value = item.split('=', 1)
                            record['metadata'][key] = value

                # Extract document content
                record['document'] = record['metadata'].pop('chroma:document', '')

                results.append(record)

            return results


class NeonMigrator:
    """Migrate data to Neon pgvector database."""

    def __init__(self, database_url: str, dry_run: bool = False):
        self.database_url = database_url
        self.dry_run = dry_run
        self.user_id = 'jeremy'  # Default user

    @contextmanager
    def _get_connection(self):
        conn = psycopg2.connect(self.database_url)
        try:
            yield conn
            if not self.dry_run:
                conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def check_connection(self) -> bool:
        """Verify database connection and schema."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM memories")
                    count = cur.fetchone()[0]
                    logger.info(f"Connected to Neon. Existing memories: {count}")
                    return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False

    def get_existing_ids(self) -> set:
        """Get set of already migrated embedding IDs."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Check if we have a source_file field we can use to track migrations
                cur.execute("""
                    SELECT DISTINCT source_file
                    FROM memory_metadata
                    WHERE source = 'chromadb_migration'
                """)
                return {row[0] for row in cur.fetchall() if row[0]}

    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform ChromaDB record to Neon format."""
        metadata = record.get('metadata', {})

        # Extract fields
        doc_type = metadata.get('doc_type', 'observation')
        memory_type = DOC_TYPE_MAPPING.get(doc_type, 'pattern')

        # Parse timestamp
        created_at_epoch = metadata.get('created_at_epoch')
        if created_at_epoch:
            try:
                created_at = datetime.fromtimestamp(int(created_at_epoch) / 1000)
            except (ValueError, TypeError):
                created_at = datetime.now()
        else:
            created_at = datetime.now()

        # Build tags from concepts and type
        tags = []
        if metadata.get('concepts'):
            tags.extend(metadata['concepts'].split(','))
        if metadata.get('type'):
            tags.append(metadata['type'])
        if metadata.get('field_type'):
            tags.append(metadata['field_type'])

        # Clean tags
        tags = [t.strip() for t in tags if t.strip()]

        return {
            'user_id': self.user_id,
            'content': record.get('document', ''),
            'memory_type': memory_type,
            'created_at': created_at,
            'source': 'chromadb_migration',
            'source_file': record.get('embedding_id'),  # Store original ID for dedup
            'original_timestamp': created_at,
            'project': metadata.get('project'),
            'tags': tags if tags else None,
            # ChromaDB doesn't have client concept, so leave null
            'client': None,
            # Heat data - start fresh
            'heat': 1.0,
            'importance': 1.0,
        }

    def migrate_batch(self, records: List[Dict[str, Any]]) -> int:
        """Insert a batch of records into Neon."""
        if self.dry_run:
            return len(records)

        transformed = [self.transform_record(r) for r in records]

        # Filter out empty content
        transformed = [t for t in transformed if t['content'].strip()]

        if not transformed:
            return 0

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Insert into memories table
                memories_query = """
                    INSERT INTO memories (user_id, content, memory_type, created_at)
                    VALUES (%(user_id)s, %(content)s, %(memory_type)s, %(created_at)s)
                    RETURNING id
                """

                metadata_query = """
                    INSERT INTO memory_metadata (
                        memory_id, source, source_file, original_timestamp,
                        project, tags, heat, importance, created_at
                    )
                    VALUES (
                        %(memory_id)s, %(source)s, %(source_file)s, %(original_timestamp)s,
                        %(project)s, %(tags)s, %(heat)s, %(importance)s, NOW()
                    )
                    ON CONFLICT (memory_id) DO NOTHING
                """

                inserted = 0
                for record in transformed:
                    try:
                        # Insert memory
                        cur.execute(memories_query, {
                            'user_id': record['user_id'],
                            'content': record['content'],
                            'memory_type': record['memory_type'],
                            'created_at': record['created_at'],
                        })

                        memory_id = cur.fetchone()[0]

                        # Insert metadata
                        cur.execute(metadata_query, {
                            'memory_id': memory_id,
                            'source': record['source'],
                            'source_file': record['source_file'],
                            'original_timestamp': record['original_timestamp'],
                            'project': record['project'],
                            'tags': record['tags'],
                            'heat': record['heat'],
                            'importance': record['importance'],
                        })

                        inserted += 1
                    except Exception as e:
                        logger.warning(f"Failed to insert record: {e}")
                        continue

                return inserted


def main():
    parser = argparse.ArgumentParser(description='Migrate ChromaDB to Neon pgvector')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be migrated')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for inserts')
    parser.add_argument('--limit', type=int, default=None, help='Limit records to migrate')
    args = parser.parse_args()

    # Check prerequisites
    if not CHROMADB_PATH.exists():
        logger.error(f"ChromaDB not found at {CHROMADB_PATH}")
        sys.exit(1)

    if not NEON_DATABASE_URL:
        logger.error("THANOS_MEMORY_DATABASE_URL not set in .env")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("ChromaDB to Neon pgvector Migration")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")

    # Initialize readers/writers
    reader = ChromaDBReader(CHROMADB_PATH)
    migrator = NeonMigrator(NEON_DATABASE_URL, dry_run=args.dry_run)

    # Check connections
    if not migrator.check_connection():
        sys.exit(1)

    # Count source records
    total_count = reader.count_embeddings()
    logger.info(f"ChromaDB contains {total_count} embeddings")

    if args.limit:
        logger.info(f"Limiting migration to {args.limit} records")

    # Get existing migrated IDs to avoid duplicates
    existing_ids = migrator.get_existing_ids()
    logger.info(f"Already migrated: {len(existing_ids)} records")

    # Fetch all records
    logger.info("Fetching records from ChromaDB...")
    records = reader.fetch_all_embeddings(limit=args.limit)
    logger.info(f"Fetched {len(records)} records")

    # Filter out already migrated
    new_records = [r for r in records if r['embedding_id'] not in existing_ids]
    logger.info(f"New records to migrate: {len(new_records)}")

    if not new_records:
        logger.info("No new records to migrate. Done!")
        return

    # Migrate in batches
    total_migrated = 0
    for i in range(0, len(new_records), args.batch_size):
        batch = new_records[i:i + args.batch_size]
        migrated = migrator.migrate_batch(batch)
        total_migrated += migrated

        progress = min(i + args.batch_size, len(new_records))
        logger.info(f"Progress: {progress}/{len(new_records)} ({total_migrated} migrated)")

    logger.info("=" * 60)
    logger.info(f"Migration complete! Migrated {total_migrated} records")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
