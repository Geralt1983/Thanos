#!/usr/bin/env python3
"""
Re-embed Memory V2 entries into a Voyage-compatible table.

Creates a new table `thanos_memories_voyage` with vector(1024) and
re-embeds content from `thanos_memories` using Voyage AI.

Usage:
  python Tools/memory_v2/migrate_embeddings.py --dry-run
  python Tools/memory_v2/migrate_embeddings.py --confirm
  python Tools/memory_v2/migrate_embeddings.py --confirm --limit 1000
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Iterable, List, Tuple

import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv


DEFAULT_SOURCE_TABLE = "thanos_memories"
DEFAULT_TARGET_TABLE = "thanos_memories_voyage"


def load_env() -> None:
    """Load .env from repo root."""
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)


def get_db_url() -> str:
    url = os.getenv("THANOS_MEMORY_DATABASE_URL")
    if not url:
        raise ValueError("THANOS_MEMORY_DATABASE_URL not set in .env")
    return url


def get_voyage_key() -> str:
    key = os.getenv("VOYAGE_API_KEY")
    if not key:
        raise ValueError("VOYAGE_API_KEY not set in .env")
    return key


def ensure_target_table(conn, table_name: str) -> None:
    """Create target table if missing."""
    with conn.cursor() as cur:
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id TEXT PRIMARY KEY,
                vector vector(1024),
                payload JSONB
            )
            """
        )
        cur.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{table_name}_vector
            ON {table_name} USING ivfflat (vector vector_cosine_ops)
            """
        )


def iter_source_rows(conn, table_name: str) -> Iterable[Tuple[str, dict]]:
    """Stream source rows to avoid loading all rows in memory."""
    with conn.cursor(name="memories_cursor") as cur:
        cur.itersize = 500
        cur.execute(f"SELECT id, payload FROM {table_name}")
        for row in cur:
            yield row[0], row[1]


def extract_content(payload: dict) -> str | None:
    if not payload:
        return None
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return None
    return payload.get("data") or payload.get("content") or payload.get("text")


def embed_batch(client, texts: List[str]) -> List[List[float]]:
    result = client.embed(texts=texts, model="voyage-3", input_type="document")
    return result.embeddings


def migrate(
    conn,
    source_table: str,
    target_table: str,
    dry_run: bool,
    limit: int | None,
    batch_size: int,
) -> None:
    import voyageai

    client = voyageai.Client(api_key=get_voyage_key())
    total = 0
    migrated = 0
    skipped = 0

    batch: List[Tuple[str, dict, str]] = []

    for mem_id, payload in iter_source_rows(conn, source_table):
        total += 1
        if limit and total > limit:
            break

        content = extract_content(payload)
        if not content:
            skipped += 1
            continue

        batch.append((mem_id, payload, content))
        if len(batch) >= batch_size:
            migrated += process_batch(conn, batch, target_table, client, dry_run)
            batch = []

    if batch:
        migrated += process_batch(conn, batch, target_table, client, dry_run)

    print("\nMigration Summary")
    print("=" * 40)
    print(f"Source table: {source_table}")
    print(f"Target table: {target_table}")
    print(f"Total scanned: {total}")
    print(f"Migrated: {migrated}")
    print(f"Skipped (no content): {skipped}")


def process_batch(
    conn,
    batch: List[Tuple[str, dict, str]],
    target_table: str,
    client,
    dry_run: bool,
) -> int:
    ids = [row[0] for row in batch]
    payloads = [row[1] for row in batch]
    texts = [row[2] for row in batch]

    embeddings = embed_batch(client, texts)
    rows = list(zip(ids, embeddings, payloads))

    if dry_run:
        return len(rows)

    with conn.cursor() as cur:
        execute_batch(
            cur,
            f"""
            INSERT INTO {target_table} (id, vector, payload)
            VALUES (%s, %s, %s)
            ON CONFLICT (id) DO UPDATE
            SET vector = EXCLUDED.vector,
                payload = EXCLUDED.payload
            """,
            rows,
        )
    conn.commit()
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-embed Memory V2 with Voyage")
    parser.add_argument("--dry-run", action="store_true", help="No writes, just count")
    parser.add_argument("--confirm", action="store_true", help="Execute migration")
    parser.add_argument("--limit", type=int, help="Limit number of rows")
    parser.add_argument("--batch-size", type=int, default=100, help="Embedding batch size")
    parser.add_argument("--source-table", default=DEFAULT_SOURCE_TABLE)
    parser.add_argument("--target-table", default=DEFAULT_TARGET_TABLE)
    args = parser.parse_args()

    if not args.dry_run and not args.confirm:
        raise SystemExit("Specify --dry-run or --confirm")

    load_env()
    db_url = get_db_url()

    with psycopg2.connect(db_url) as conn:
        if not args.dry_run:
            ensure_target_table(conn, args.target_table)
        migrate(
            conn,
            args.source_table,
            args.target_table,
            args.dry_run,
            args.limit,
            args.batch_size,
        )


if __name__ == "__main__":
    main()
