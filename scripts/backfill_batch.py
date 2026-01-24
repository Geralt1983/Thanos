#!/usr/bin/env python3
"""
Fast batch backfill - bypasses mem0 for 100x speedup.

Batches:
- OpenAI embeddings (100 texts per API call)
- PostgreSQL inserts (100 rows per INSERT)
"""

import os
import sys
import time
import hashlib
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
import openai

# Config
BATCH_SIZE = 100  # OpenAI supports up to 2048, but 100 is safe
DATABASE_URL = os.getenv("THANOS_MEMORY_DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = openai.OpenAI(api_key=OPENAI_API_KEY)


def get_already_migrated(conn):
    """Get set of content hashes already in thanos_memories."""
    with conn.cursor() as cur:
        cur.execute("SELECT payload->>'hash' FROM thanos_memories WHERE payload->>'hash' IS NOT NULL")
        return {row[0] for row in cur.fetchall()}


def get_legacy_batch(conn, offset, limit):
    """Fetch batch of legacy memories."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
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
            LIMIT %(limit)s
        """, {"offset": offset, "limit": limit})
        return cur.fetchall()


def batch_embed(texts):
    """Get embeddings for multiple texts in one API call."""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    return [item.embedding for item in response.data]


def batch_insert(conn, records):
    """Insert multiple records in one query."""
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO thanos_memories (id, vector, payload)
            VALUES %s
            ON CONFLICT (id) DO NOTHING
            """,
            records,
            template="(%(id)s, %(vector)s::vector, %(payload)s::jsonb)"
        )
    conn.commit()


def main():
    print("=" * 60)
    print("FAST BATCH BACKFILL")
    print("=" * 60)

    conn = psycopg2.connect(DATABASE_URL)

    # Get counts
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM memories WHERE user_id = 'jeremy'")
        total_legacy = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM thanos_memories")
        already_done = cur.fetchone()[0]

    print(f"Legacy records: {total_legacy:,}")
    print(f"Already migrated: {already_done:,}")
    print(f"Remaining: ~{total_legacy - already_done:,}")
    print()

    # Get already migrated hashes to skip duplicates
    print("Loading migrated hashes...")
    migrated_hashes = get_already_migrated(conn)
    print(f"Found {len(migrated_hashes):,} existing hashes")
    print()

    # Process in batches
    offset = 0
    total_migrated = 0
    total_skipped = 0
    total_errors = 0
    start_time = time.time()

    while True:
        batch = get_legacy_batch(conn, offset, BATCH_SIZE)
        if not batch:
            break

        # Filter out already migrated
        to_migrate = []
        for record in batch:
            content_hash = hashlib.md5(record['content'].encode()).hexdigest()
            if content_hash not in migrated_hashes:
                to_migrate.append((record, content_hash))
            else:
                total_skipped += 1

        if to_migrate:
            try:
                # Batch embed
                texts = [r[0]['content'] for r in to_migrate]
                embeddings = batch_embed(texts)

                # Prepare records for insert
                insert_records = []
                for (record, content_hash), embedding in zip(to_migrate, embeddings):
                    import uuid
                    payload = {
                        "data": record['content'],
                        "hash": content_hash,
                        "type": record.get('memory_type') or 'note',
                        "source": record.get('source') or 'migration',
                        "user_id": record.get('user_id', 'jeremy'),
                        "created_at": record['created_at'].isoformat() if record.get('created_at') else datetime.now().isoformat(),
                        "migrated_from": str(record['id']),
                    }
                    if record.get('client'):
                        payload['client'] = record['client']
                    if record.get('project'):
                        payload['project'] = record['project']

                    insert_records.append({
                        "id": str(uuid.uuid4()),
                        "vector": embedding,
                        "payload": psycopg2.extras.Json(payload)
                    })

                # Batch insert
                batch_insert(conn, insert_records)
                total_migrated += len(insert_records)

                # Track hashes
                for _, content_hash in to_migrate:
                    migrated_hashes.add(content_hash)

            except Exception as e:
                print(f"  Error in batch at offset {offset}: {e}")
                total_errors += len(to_migrate)

        offset += BATCH_SIZE

        # Progress
        elapsed = time.time() - start_time
        rate = (total_migrated + total_skipped) / elapsed if elapsed > 0 else 0
        eta = (total_legacy - offset) / rate if rate > 0 else 0

        print(f"Progress: {offset:,}/{total_legacy:,} | Migrated: {total_migrated:,} | Skipped: {total_skipped:,} | {rate:.0f}/sec | ETA: {eta/60:.1f}min")

    conn.close()

    elapsed = time.time() - start_time
    print()
    print("=" * 60)
    print("COMPLETE")
    print("=" * 60)
    print(f"Migrated: {total_migrated:,}")
    print(f"Skipped (dupes): {total_skipped:,}")
    print(f"Errors: {total_errors:,}")
    print(f"Time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    print(f"Rate: {total_migrated/elapsed:.0f} records/second")


if __name__ == "__main__":
    main()
