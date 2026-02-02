#!/usr/bin/env python3
"""
Graphiti Daily Digest
Reads today's memory notes and feeds key events to the knowledge graph.
Run via cron at end of day.
"""

import os
import sys
import json
import tempfile
import subprocess
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path("/Users/jeremy/Projects/Thanos")
MEMORY_DIR = WORKSPACE / "memory"


def get_today_notes() -> str:
    """Read today's memory file."""
    today = datetime.now().strftime("%Y-%m-%d")
    memory_file = MEMORY_DIR / f"{today}.md"
    
    if not memory_file.exists():
        # Try to find any recent files
        files = sorted(MEMORY_DIR.glob("*.md"), reverse=True)
        if files:
            memory_file = files[0]
            print(f"No file for today, using {memory_file.name}")
        else:
            return ""
    
    return memory_file.read_text()


def summarize_for_graph(notes: str) -> str:
    """
    Format notes for Graphiti ingestion.
    Focuses on: decisions, relationships, events, outcomes.
    """
    if not notes.strip():
        return ""
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    digest = f"""Daily digest for {today}:

{notes}

Key focus: Extract people, projects, decisions, dependencies, and outcomes.
"""
    return digest


def feed_to_graphiti_docker(content: str) -> bool:
    """Feed content to Graphiti via docker exec using stdin."""
    
    payload = json.dumps({
        "content": content,
        "name": f"daily_digest_{datetime.now().strftime('%Y%m%d')}",
        "source": "Thanos Daily Digest"
    })
    
    # Run ingestion script inside container, passing JSON via stdin
    ingest_script = '''
import asyncio
import json
import sys
from datetime import datetime, timezone
from graphiti_core import Graphiti
import os

async def ingest():
    data = json.loads(sys.stdin.read())
    
    client = Graphiti(
        uri="bolt://neo4j:7687",
        user="neo4j",
        password=os.environ.get("NEO4J_PASSWORD", "graphiti_thanos_2026")
    )
    
    await client.add_episode(
        name=data["name"],
        episode_body=data["content"],
        source_description=data["source"],
        reference_time=datetime.now(timezone.utc)
    )
    print("Daily digest ingested to Graphiti")
    await client.close()

asyncio.run(ingest())
'''
    
    result = subprocess.run(
        ["docker", "exec", "-i", "mcp-root", "python3", "-c", ingest_script],
        input=payload,
        capture_output=True, text=True
    )
    
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    
    print(result.stdout)
    return True


def main():
    print(f"=== Graphiti Daily Digest ===")
    print(f"Time: {datetime.now()}")
    
    # Get today's notes
    notes = get_today_notes()
    if not notes:
        print("No notes found for today. Skipping.")
        return
    
    print(f"Found {len(notes)} chars of notes")
    
    # Prepare digest
    digest = summarize_for_graph(notes)
    if not digest:
        print("Nothing to digest. Skipping.")
        return
    
    print(f"Digest prepared ({len(digest)} chars)")
    
    # Feed to Graphiti
    print("Feeding to Graphiti...")
    success = feed_to_graphiti_docker(digest)
    
    if success:
        print("✓ Daily digest complete")
    else:
        print("✗ Failed to ingest digest")
        sys.exit(1)


if __name__ == "__main__":
    main()
