#!/usr/bin/env python3
"""
Backfill embeddings for legacy memories.

Migrates records from `memories` table (no embeddings) to `thanos_memories`
table (with proper OpenAI embeddings via mem0).

Usage:
    python scripts/backfill_embeddings.py --dry-run     # Preview only
    python scripts/backfill_embeddings.py --batch 100   # Process 100 at a time
    python scripts/backfill_embeddings.py               # Full migration
"""

import os
import sys
import argparse
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor

from mem0 import Memory
from Tools.memory_v2.config import MEM0_CONFIG, NEON_DATABASE_URL


def get_legacy_memories(conn, limit=None, offset=0):
    """Fetch memories from legacy table that need migration."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        query = """
            SELECT
                m.id,
                m.content,
                m.memory_type,
                m.user_id,
                m.created_at,
                mm.source,
                mm.client,
                mm.project,
                mm.importance
            FROM memories m
            LEFT JOIN memory_metadata mm ON m.id = mm.memory_id
            WHERE m.user_id = 'jeremy'
            ORDER BY m.created_at DESC
            OFFSET %(offset)s
        """
        if limit:
            query += " LIMIT %(limit)s"

        cur.execute(query, {"limit": limit, "offset": offset})
        return cur.fetchall()


def check_already_migrated(conn, content_hash):
    """Check if content already exists in thanos_memories."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) FROM thanos_memories
            WHERE payload->>'hash' = %(hash)s
        """, {"hash": content_hash})
        return cur.fetchone()[0] > 0


def migrate_memory(memory_client, record):
    """Migrate a single memory record to mem0."""
    content = record['content']

    # Build metadata
    metadata = {
        'source': record.get('source') or 'migration',
        'type': record.get('memory_type') or 'note',
        'migrated_from': str(record['id']),
        'original_created_at': record['created_at'].isoformat() if record.get('created_at') else None,
    }

    if record.get('client'):
        metadata['client'] = record['client']
    if record.get('project'):
        metadata['project'] = record['project']
    if record.get('importance'):
        metadata['importance'] = record['importance']

    # Add via mem0 (generates embedding)
    result = memory_client.add(
        messages=[{"role": "user", "content": content}],
        user_id=record.get('user_id', 'jeremy'),
        metadata=metadata
    )

    return result


def main():
    parser = argparse.ArgumentParser(description='Backfill embeddings for legacy memories')
    parser.add_argument('--dry-run', action='store_true', help='Preview without making changes')
    parser.add_argument('--batch', type=int, default=50, help='Batch size (default: 50)')
    parser.add_argument('--limit', type=int, help='Max records to process')
    parser.add_argument('--offset', type=int, default=0, help='Start offset')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between batches (seconds)')
    args = parser.parse_args()

    print("=" * 60)
    print("Memory Embedding Backfill")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"Batch size: {args.batch}")
    print(f"Limit: {args.limit or 'No limit'}")
    print(f"Offset: {args.offset}")
    print()

    # Connect to database
    conn = psycopg2.connect(NEON_DATABASE_URL)

    # Get counts
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM memories WHERE user_id = 'jeremy'")
        total_legacy = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM thanos_memories")
        total_new = cur.fetchone()[0]

    print(f"Legacy memories (memories table): {total_legacy:,}")
    print(f"New memories (thanos_memories): {total_new:,}")
    print()

    if args.dry_run:
        # Preview mode
        records = get_legacy_memories(conn, limit=10, offset=args.offset)
        print(f"Preview of first 10 records to migrate:")
        print("-" * 60)
        for r in records:
            print(f"ID: {r['id']}")
            print(f"Content: {r['content'][:100]}...")
            print(f"Type: {r['memory_type']}, Source: {r.get('source')}")
            print()
        conn.close()
        return

    # Initialize mem0
    print("Initializing mem0...")
    memory = Memory.from_config(MEM0_CONFIG)
    print("✓ mem0 ready")
    print()

    # Process in batches
    processed = 0
    migrated = 0
    skipped = 0
    errors = 0
    start_time = time.time()

    offset = args.offset
    limit = args.limit

    while True:
        batch_limit = min(args.batch, limit - processed) if limit else args.batch
        if batch_limit <= 0:
            break

        records = get_legacy_memories(conn, limit=batch_limit, offset=offset)

        if not records:
            break

        print(f"Processing batch: offset={offset}, count={len(records)}")

        for record in records:
            processed += 1

            try:
                result = migrate_memory(memory, record)

                if result and result.get('results'):
                    migrated += 1
                    if processed % 10 == 0:
                        elapsed = time.time() - start_time
                        rate = processed / elapsed if elapsed > 0 else 0
                        print(f"  Progress: {processed:,} processed, {migrated:,} migrated, {rate:.1f}/sec")
                else:
                    skipped += 1

            except Exception as e:
                errors += 1
                print(f"  Error migrating {record['id']}: {e}")

        offset += len(records)

        # Rate limiting
        if args.delay > 0:
            time.sleep(args.delay)

    conn.close()

    elapsed = time.time() - start_time

    print()
    print("=" * 60)
    print("Migration Complete")
    print("=" * 60)
    print(f"Processed: {processed:,}")
    print(f"Migrated:  {migrated:,}")
    print(f"Skipped:   {skipped:,}")
    print(f"Errors:    {errors:,}")
    print(f"Time:      {elapsed:.1f} seconds")
    print(f"Rate:      {processed/elapsed:.1f} records/second")


if __name__ == "__main__":
    main()
