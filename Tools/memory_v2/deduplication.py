"""
Auto-Deduplication for Thanos Memory V2.

Finds and merges duplicate or highly similar memories to reduce clutter
and improve search quality.

Features:
- Cosine similarity detection (configurable threshold, default 0.95)
- Smart merge strategy: keep most recent, combine metadata
- Batch processing for efficiency
- Dry-run mode for safety
- Detailed logging of merges

Usage:
    from Tools.memory_v2.deduplication import deduplicate_memories
    
    # Dry run (no changes)
    results = deduplicate_memories(dry_run=True)
    
    # Execute deduplication
    results = deduplicate_memories(similarity_threshold=0.95)
    
    # Run as maintenance task
    python Tools/memory_v2/deduplication.py --threshold 0.95
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np

from .config import NEON_DATABASE_URL

logger = logging.getLogger(__name__)


class MemoryDeduplicator:
    """
    Finds and merges duplicate memories based on vector similarity.
    """
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or NEON_DATABASE_URL
        
        if not self.database_url:
            raise ValueError("Database URL not configured")
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager."""
        conn = psycopg2.connect(self.database_url)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def find_duplicates(
        self,
        similarity_threshold: float = 0.95,
        min_created_days_apart: int = 0,
        limit: Optional[int] = None,
        recent_days: Optional[int] = None,
        recent_limit: Optional[int] = None
    ) -> List[Tuple[Dict[str, Any], Dict[str, Any], float]]:
        """
        Find pairs of highly similar memories.
        
        Args:
            similarity_threshold: Cosine similarity threshold (0.95 = 95% similar)
            min_created_days_apart: Only consider memories created this many days apart
                                   (0 = any time difference)
            limit: Maximum duplicate pairs to return
        
        Returns:
            List of (memory1, memory2, similarity) tuples sorted by similarity
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Find pairs with high cosine similarity
                # Using cosine distance: 1 - cosine_distance = cosine_similarity
                # Threshold: if similarity >= threshold, then distance <= (1 - threshold)
                
                distance_threshold = 1 - similarity_threshold
                
                # Build time filter
                time_filter = ""
                if min_created_days_apart > 0:
                    time_filter = f"""
                        AND ABS(EXTRACT(EPOCH FROM (
                            COALESCE((m1.payload->>'created_at')::timestamp, NOW()) - 
                            COALESCE((m2.payload->>'created_at')::timestamp, NOW())
                        )) / 86400) >= {min_created_days_apart}
                    """
                
                m1_filter = ""
                m1_limit = ""
                params = {"distance_threshold": distance_threshold}
                if recent_days is not None:
                    m1_filter = """
                        WHERE COALESCE((payload->>'created_at')::timestamp, NOW())
                              >= NOW() - (%(recent_days)s || ' days')::interval
                    """
                    params["recent_days"] = recent_days
                if recent_limit:
                    m1_limit = "LIMIT %(recent_limit)s"
                    params["recent_limit"] = recent_limit

                m1_source = f"""
                    (SELECT * FROM thanos_memories
                     {m1_filter}
                     ORDER BY COALESCE((payload->>'created_at')::timestamp, NOW()) DESC
                     {m1_limit}) m1
                """

                query = f"""
                    SELECT
                        m1.id as id1,
                        m1.payload->>'data' as content1,
                        COALESCE((m1.payload->>'created_at')::timestamp, NOW()) as created1,
                        COALESCE((m1.payload->>'heat')::float, 0.5) as heat1,
                        COALESCE((m1.payload->>'access_count')::int, 0) as access_count1,
                        m1.payload->>'client' as client1,
                        m1.payload->>'project' as project1,
                        m1.payload->>'source' as source1,
                        
                        m2.id as id2,
                        m2.payload->>'data' as content2,
                        COALESCE((m2.payload->>'created_at')::timestamp, NOW()) as created2,
                        COALESCE((m2.payload->>'heat')::float, 0.5) as heat2,
                        COALESCE((m2.payload->>'access_count')::int, 0) as access_count2,
                        m2.payload->>'client' as client2,
                        m2.payload->>'project' as project2,
                        m2.payload->>'source' as source2,
                        
                        (m1.vector <=> m2.vector) as distance,
                        (1 - (m1.vector <=> m2.vector)) as similarity
                    FROM {m1_source}
                    CROSS JOIN thanos_memories m2
                    WHERE m1.id < m2.id  -- Avoid duplicates and self-comparisons
                      AND (m1.vector <=> m2.vector) <= %(distance_threshold)s
                      {time_filter}
                    ORDER BY similarity DESC
                    {'LIMIT %(limit)s' if limit else ''}
                """

                if limit:
                    params["limit"] = limit
                
                cur.execute(query, params)
                
                results = []
                for row in cur.fetchall():
                    mem1 = {
                        "id": row["id1"],
                        "content": row["content1"],
                        "created_at": row["created1"],
                        "heat": row["heat1"],
                        "access_count": row["access_count1"],
                        "client": row["client1"],
                        "project": row["project1"],
                        "source": row["source1"]
                    }
                    mem2 = {
                        "id": row["id2"],
                        "content": row["content2"],
                        "created_at": row["created2"],
                        "heat": row["heat2"],
                        "access_count": row["access_count2"],
                        "client": row["client2"],
                        "project": row["project2"],
                        "source": row["source2"]
                    }
                    results.append((mem1, mem2, row["similarity"]))
                
                logger.info(f"Found {len(results)} duplicate pairs above {similarity_threshold} similarity")
                return results
    
    def merge_memories(
        self,
        keep_id: str,
        remove_id: str,
        merged_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Merge two memories: keep one, delete the other, combine metadata.
        
        Args:
            keep_id: ID of memory to keep
            remove_id: ID of memory to remove
            merged_metadata: Combined metadata (if None, will auto-merge)
        
        Returns:
            Success status
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get both memories
                cur.execute("""
                    SELECT id, payload, vector
                    FROM thanos_memories
                    WHERE id IN (%(keep_id)s, %(remove_id)s)
                """, {"keep_id": keep_id, "remove_id": remove_id})
                
                memories = {row["id"]: row for row in cur.fetchall()}
                
                if len(memories) != 2:
                    logger.warning(f"Could not find both memories for merge: {keep_id}, {remove_id}")
                    return False
                
                keep_mem = memories[keep_id]
                remove_mem = memories[remove_id]
                
                # Auto-merge metadata if not provided
                if merged_metadata is None:
                    merged_metadata = self._merge_metadata(keep_mem["payload"], remove_mem["payload"])
                
                # Update the kept memory with merged metadata
                cur.execute("""
                    UPDATE thanos_memories
                    SET payload = %(merged_payload)s
                    WHERE id = %(keep_id)s
                """, {
                    "keep_id": keep_id,
                    "merged_payload": psycopg2.extras.Json(merged_metadata)
                })
                
                # Delete the removed memory
                cur.execute("""
                    DELETE FROM thanos_memories
                    WHERE id = %(remove_id)s
                    RETURNING id
                """, {"remove_id": remove_id})
                
                if cur.fetchone():
                    logger.info(f"Merged memories: kept {keep_id}, removed {remove_id}")
                    return True
                else:
                    logger.warning(f"Failed to delete memory {remove_id}")
                    return False
    
    def _merge_metadata(self, payload1: dict, payload2: dict) -> dict:
        """
        Intelligently merge metadata from two memories.
        
        Strategy:
        - Keep data from the more recent memory
        - Combine access_count (sum)
        - Take maximum heat
        - Combine tags, sources (union)
        - Keep highest importance
        """
        import json
        
        # Parse payloads if they're JSON strings
        if isinstance(payload1, str):
            payload1 = json.loads(payload1)
        if isinstance(payload2, str):
            payload2 = json.loads(payload2)
        
        # Determine which is more recent
        created1 = payload1.get("created_at")
        created2 = payload2.get("created_at")
        
        if created1 and created2:
            if created1 >= created2:
                base = payload1.copy()
                other = payload2
            else:
                base = payload2.copy()
                other = payload1
        else:
            # If timestamps missing, prefer first
            base = payload1.copy()
            other = payload2
        
        # Merge numeric fields (take max or sum)
        base["heat"] = max(
            payload1.get("heat", 0.5),
            payload2.get("heat", 0.5)
        )
        base["access_count"] = (
            payload1.get("access_count", 0) +
            payload2.get("access_count", 0)
        )
        base["importance"] = max(
            payload1.get("importance", 1.0),
            payload2.get("importance", 1.0)
        )
        
        # Merge array fields (union)
        for field in ["tags", "entities", "sources"]:
            val1 = payload1.get(field, [])
            val2 = payload2.get(field, [])
            if isinstance(val1, list) and isinstance(val2, list):
                base[field] = list(set(val1 + val2))
        
        # Merge text fields (combine if different)
        for field in ["source", "client", "project"]:
            val1 = payload1.get(field, "")
            val2 = payload2.get(field, "")
            if val1 and val2 and val1 != val2:
                base[field] = f"{val1}, {val2}"
            elif val2 and not val1:
                base[field] = val2
        
        # Track merge history
        base["merged_from"] = base.get("merged_from", [])
        base["merged_from"].append({
            "id": other.get("id"),
            "created_at": other.get("created_at"),
            "merged_at": datetime.now().isoformat()
        })
        
        return base
    
    def deduplicate(
        self,
        similarity_threshold: float = 0.95,
        dry_run: bool = False,
        limit: Optional[int] = None,
        recent_days: Optional[int] = None,
        recent_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Find and merge duplicate memories.
        
        Args:
            similarity_threshold: Cosine similarity threshold (0.95 = 95% similar)
            dry_run: If True, find duplicates but don't merge
            limit: Maximum pairs to process
        
        Returns:
            Summary of deduplication results
        """
        duplicates = self.find_duplicates(
            similarity_threshold=similarity_threshold,
            limit=limit,
            recent_days=recent_days,
            recent_limit=recent_limit
        )
        
        if not duplicates:
            logger.info("No duplicates found")
            return {
                "duplicates_found": 0,
                "duplicates_merged": 0,
                "dry_run": dry_run
            }
        
        merged_count = 0
        merge_log = []
        
        for mem1, mem2, similarity in duplicates:
            # Decide which to keep: more recent, or higher heat if same age
            if mem1["created_at"] > mem2["created_at"]:
                keep, remove = mem1, mem2
            elif mem1["created_at"] < mem2["created_at"]:
                keep, remove = mem2, mem1
            else:
                # Same creation time, prefer higher heat
                if mem1["heat"] >= mem2["heat"]:
                    keep, remove = mem1, mem2
                else:
                    keep, remove = mem2, mem1
            
            merge_info = {
                "keep_id": keep["id"],
                "remove_id": remove["id"],
                "similarity": similarity,
                "keep_content": keep["content"][:100],
                "remove_content": remove["content"][:100]
            }
            
            if not dry_run:
                success = self.merge_memories(keep["id"], remove["id"])
                if success:
                    merged_count += 1
                merge_info["merged"] = success
            else:
                merge_info["merged"] = "dry_run"
            
            merge_log.append(merge_info)
            
            logger.info(
                f"{'[DRY RUN] ' if dry_run else ''}Duplicate (similarity={similarity:.3f}): "
                f"keep {keep['id']}, remove {remove['id']}"
            )
        
        return {
            "duplicates_found": len(duplicates),
            "duplicates_merged": merged_count,
            "dry_run": dry_run,
            "merge_log": merge_log
        }


# Singleton instance
_deduplicator: Optional[MemoryDeduplicator] = None


def get_deduplicator() -> MemoryDeduplicator:
    """Get or create the singleton MemoryDeduplicator instance."""
    global _deduplicator
    if _deduplicator is None:
        _deduplicator = MemoryDeduplicator()
    return _deduplicator


def deduplicate_memories(
    similarity_threshold: float = 0.95,
    dry_run: bool = False,
    limit: Optional[int] = None,
    recent_days: Optional[int] = None,
    recent_limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Convenience function to deduplicate memories.
    
    Args:
        similarity_threshold: Cosine similarity threshold (0.95 = 95% similar)
        dry_run: If True, find duplicates but don't merge
        limit: Maximum pairs to process
        recent_days: Only compare memories created within last N days
        recent_limit: Cap recent memory set size (when recent_days is set)
    
    Returns:
        Summary of deduplication results
    
    Examples:
        # Dry run to see what would be merged
        results = deduplicate_memories(dry_run=True)
        
        # Execute deduplication
        results = deduplicate_memories(similarity_threshold=0.95)
        
        # Process only top 10 most similar pairs
        results = deduplicate_memories(limit=10)
    """
    dedup = get_deduplicator()
    return dedup.deduplicate(
        similarity_threshold=similarity_threshold,
        dry_run=dry_run,
        limit=limit,
        recent_days=recent_days,
        recent_limit=recent_limit
    )


if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Deduplicate Thanos memories")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.95,
        help="Similarity threshold (0-1, default 0.95)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Find duplicates but don't merge"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum pairs to process"
    )
    parser.add_argument(
        "--recent-days",
        type=int,
        help="Only compare memories created within the last N days"
    )
    parser.add_argument(
        "--recent-limit",
        type=int,
        help="Cap the recent memory set size (when --recent-days is used)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed merge log"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    print(f"Deduplication Settings:")
    print(f"  Threshold: {args.threshold}")
    print(f"  Dry Run: {args.dry_run}")
    print(f"  Limit: {args.limit or 'None'}")
    print()
    
    results = deduplicate_memories(
        similarity_threshold=args.threshold,
        dry_run=args.dry_run,
        limit=args.limit,
        recent_days=args.recent_days,
        recent_limit=args.recent_limit
    )
    
    print("Results:")
    print("=" * 40)
    print(f"Duplicates Found: {results['duplicates_found']}")
    print(f"Duplicates Merged: {results['duplicates_merged']}")
    print(f"Dry Run: {results['dry_run']}")
    
    if args.verbose and results.get("merge_log"):
        print("\nMerge Log:")
        print(json.dumps(results["merge_log"], indent=2))
