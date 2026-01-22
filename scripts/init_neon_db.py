#!/usr/bin/env python3
"""
Initialize Neon database schema for Thanos Memory V2.

Run: python scripts/init_neon_db.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / '.env')


def init_schema():
    """Initialize the Neon database schema."""
    url = os.getenv('THANOS_MEMORY_DATABASE_URL')

    if not url:
        print("ERROR: THANOS_MEMORY_DATABASE_URL not set")
        return False

    print("Connecting to Neon...")

    conn = psycopg2.connect(url)
    conn.autocommit = True  # Each statement in its own transaction
    cur = conn.cursor()

    statements = [
        # Enable pgvector extension
        "CREATE EXTENSION IF NOT EXISTS vector",

        # Core memories table
        """
        CREATE TABLE IF NOT EXISTS memories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id VARCHAR(255) NOT NULL,
            content TEXT NOT NULL,
            embedding VECTOR(1536),
            memory_type VARCHAR(50),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """,

        # Extended metadata with heat decay
        """
        CREATE TABLE IF NOT EXISTS memory_metadata (
            memory_id UUID PRIMARY KEY,
            source VARCHAR(50),
            source_file VARCHAR(255),
            original_timestamp TIMESTAMP,
            client VARCHAR(100),
            project VARCHAR(100),
            tags TEXT[],
            heat FLOAT DEFAULT 1.0,
            last_accessed TIMESTAMP DEFAULT NOW(),
            access_count INT DEFAULT 0,
            importance FLOAT DEFAULT 1.0,
            pinned BOOLEAN DEFAULT FALSE,
            neo4j_node_id VARCHAR(255),
            created_at TIMESTAMP DEFAULT NOW()
        )
        """,

        # Indexes
        "CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)",
        "CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_metadata_heat ON memory_metadata(heat DESC)",
        "CREATE INDEX IF NOT EXISTS idx_metadata_last_accessed ON memory_metadata(last_accessed)",
        "CREATE INDEX IF NOT EXISTS idx_metadata_client ON memory_metadata(client)",
        "CREATE INDEX IF NOT EXISTS idx_metadata_source ON memory_metadata(source)",

        # View for easy querying
        """
        CREATE OR REPLACE VIEW memories_with_heat AS
        SELECT
            m.id,
            m.user_id,
            m.content,
            m.memory_type,
            m.created_at,
            m.updated_at,
            COALESCE(mm.heat, 1.0) as heat,
            COALESCE(mm.importance, 1.0) as importance,
            COALESCE(mm.access_count, 0) as access_count,
            mm.last_accessed,
            mm.pinned,
            mm.source,
            mm.client,
            mm.project,
            mm.tags
        FROM memories m
        LEFT JOIN memory_metadata mm ON m.id = mm.memory_id
        """,
    ]

    success = 0
    for i, stmt in enumerate(statements, 1):
        try:
            cur.execute(stmt)
            print(f"✓ Statement {i}/{len(statements)} executed")
            success += 1
        except Exception as e:
            if 'already exists' in str(e).lower():
                print(f"• Statement {i}/{len(statements)} (already exists)")
                success += 1
            else:
                print(f"✗ Statement {i}: {e}")

    cur.close()
    conn.close()

    print(f"\n{'='*40}")
    print(f"Schema initialized: {success}/{len(statements)} statements")

    # Verify tables
    verify_schema()

    return success == len(statements)


def verify_schema():
    """Verify the schema was created correctly."""
    url = os.getenv('THANOS_MEMORY_DATABASE_URL')

    conn = psycopg2.connect(url)
    cur = conn.cursor()

    print("\nVerifying schema...")

    # Check tables
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
    """)
    tables = [row[0] for row in cur.fetchall()]

    print(f"Tables: {', '.join(tables)}")

    # Check views
    cur.execute("""
        SELECT table_name FROM information_schema.views
        WHERE table_schema = 'public'
    """)
    views = [row[0] for row in cur.fetchall()]

    print(f"Views: {', '.join(views)}")

    # Check extensions
    cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
    has_vector = cur.fetchone() is not None
    print(f"pgvector extension: {'✓' if has_vector else '✗'}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    init_schema()
