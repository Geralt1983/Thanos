#!/usr/bin/env python3
"""
Backfill heat values for legacy memories.

Calculates heat based on recency and sets initial values for memories
that don't have heat tracked yet. Run once to migrate legacy data.

Usage:
    python scripts/backfill_heat.py          # Dry run
    python scripts/backfill_heat.py --apply  # Apply changes
"""

import argparse
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Tools.memory_v2.config import NEON_DATABASE_URL


def calculate_initial_heat(created_at: datetime) -> float:
    """Calculate heat based on memory age."""
    now = datetime.now(created_at.tzinfo) if created_at.tzinfo else datetime.now()
    age = now - created_at
    
    if age < timedelta(hours=6):
        return 1.0
    elif age < timedelta(hours=24):
        return 0.85
    elif age < timedelta(hours=48):
        return 0.7
    elif age < timedelta(days=7):
        return 0.5
    elif age < timedelta(days=14):
        return 0.3
    elif age < timedelta(days=30):
        return 0.15
    else:
        return 0.05  # Floor


def backfill_heat(apply: bool = False):
    """Backfill heat values for memories without them."""
    conn = psycopg2.connect(NEON_DATABASE_URL)
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Find memories without heat in payload
            cur.execute("""
                SELECT id, payload->>'created_at' as created_at
                FROM thanos_memories
                WHERE payload->>'heat' IS NULL
                ORDER BY (payload->>'created_at')::timestamp DESC
            """)
            
            memories = cur.fetchall()
            print(f"Found {len(memories)} memories without heat values")
            
            if not memories:
                print("Nothing to backfill!")
                return
            
            updates = []
            for mem in memories:
                created_at_str = mem['created_at']
                if created_at_str:
                    try:
                        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    except:
                        created_at = datetime.now() - timedelta(days=30)  # Default to old
                else:
                    created_at = datetime.now() - timedelta(days=30)
                
                heat = calculate_initial_heat(created_at)
                updates.append((mem['id'], heat, created_at_str or 'unknown'))
            
            # Show sample
            print("\nSample updates (first 10):")
            for id, heat, created in updates[:10]:
                print(f"  {id[:8]}... | heat={heat:.2f} | created={created[:19] if created != 'unknown' else created}")
            
            if not apply:
                print(f"\n[DRY RUN] Would update {len(updates)} memories")
                print("Run with --apply to execute")
                return
            
            # Apply updates in batches using a single UPDATE with CASE
            print(f"\nApplying {len(updates)} updates in batches...")
            batch_size = 1000
            total_updated = 0
            
            for i in range(0, len(updates), batch_size):
                batch = updates[i:i + batch_size]
                ids = [u[0] for u in batch]
                
                # Build CASE statement for heat values
                case_parts = []
                params = {}
                for j, (id, heat, _) in enumerate(batch):
                    param_id = f"id_{j}"
                    param_heat = f"heat_{j}"
                    case_parts.append(f"WHEN id = %({param_id})s THEN %({param_heat})s")
                    params[param_id] = id
                    params[param_heat] = heat
                
                case_sql = " ".join(case_parts)
                params["ids"] = ids
                
                cur.execute(f"""
                    UPDATE thanos_memories
                    SET payload = payload || jsonb_build_object(
                        'heat', CASE {case_sql} END,
                        'last_accessed', NOW()::text
                    )
                    WHERE id = ANY(%(ids)s::uuid[])
                """, params)
                
                total_updated += len(batch)
                print(f"  Progress: {total_updated}/{len(updates)}")
            
            conn.commit()
            print(f"✓ Backfilled {total_updated} memories with heat values")
            
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill heat values for legacy memories")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default: dry run)")
    args = parser.parse_args()
    
    backfill_heat(apply=args.apply)
