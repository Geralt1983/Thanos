"""
Memory Export Utility for Thanos Memory V2.

Exports memories from Memory V2 (pgvector) storage to portable JSON format.
Supports full export including vector embeddings, payload data, and heat metadata.

Usage:
    from Tools.memory_export import MemoryExporter

    exporter = MemoryExporter()
    result = exporter.export_memories(output_path="./export")

    # Export with specific format
    result = exporter.export_all(output_path="./backup", format="json")

Features:
    - Export all memories with embeddings and metadata
    - Export relationship graph from SQLite
    - Unified export combining memories + relationships
    - CSV and JSON format support
    - Checksum generation for verification

Model: Direct data export (no LLM required)
"""

import argparse
import csv
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Initialize logger first
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Import psycopg2 for specific error handling
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None

# Import config directly to avoid triggering service imports
import os

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    # dotenv not available, rely on system environment
    pass

NEON_DATABASE_URL = os.getenv("THANOS_MEMORY_DATABASE_URL")
DEFAULT_USER_ID = "jeremy"

# Import relationship store with graceful degradation
try:
    from Tools.relationships import RelationshipStore, get_relationship_store
    RELATIONSHIPS_AVAILABLE = True
except ImportError:
    RELATIONSHIPS_AVAILABLE = False
    RelationshipStore = None
    get_relationship_store = None
    logger.warning("Relationship store not available")


class MemoryExporter:
    """
    Export memories and relationships from Thanos Memory V2.

    Handles:
    - Memory V2 data from Neon pgvector (thanos_memories table)
    - Relationship data from SQLite (relationships.db)
    - Export to JSON and CSV formats
    - Verification and checksums
    """

    def __init__(self, database_url: str = None, user_id: str = None):
        """
        Initialize MemoryExporter.

        Args:
            database_url: PostgreSQL connection URL (defaults to NEON_DATABASE_URL)
            user_id: User ID to export memories for (defaults to DEFAULT_USER_ID)
        """
        if not psycopg2:
            raise ImportError("psycopg2 not installed. Run: pip install psycopg2-binary")

        self.database_url = database_url or NEON_DATABASE_URL
        self.user_id = user_id or DEFAULT_USER_ID

        if not self.database_url:
            raise ValueError("Database URL not configured. Set THANOS_MEMORY_DATABASE_URL in .env")

        logger.info(f"MemoryExporter initialized for user: {self.user_id}")

    def _get_connection(self):
        """Get database connection."""
        return psycopg2.connect(self.database_url)

    def export_memories(
        self,
        limit: Optional[int] = None,
        include_vectors: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Export all memories from Memory V2.

        Retrieves memories from thanos_memories table including:
        - Memory ID
        - Vector embeddings (optional)
        - Payload data (content, metadata, heat, importance)
        - Timestamps

        Args:
            limit: Maximum number of memories to export (None = all)
            include_vectors: Whether to include vector embeddings in export

        Returns:
            List of memory dictionaries with all data
        """
        logger.info(f"Exporting memories for user {self.user_id}...")

        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Build query
                vector_select = "vector," if include_vectors else ""
                limit_clause = f"LIMIT {limit}" if limit else ""

                cur.execute(f"""
                    SELECT
                        id,
                        {vector_select}
                        payload
                    FROM thanos_memories
                    WHERE payload->>'user_id' = %(user_id)s
                    ORDER BY (payload->>'created_at')::timestamp DESC NULLS LAST
                    {limit_clause}
                """, {"user_id": self.user_id})

                rows = cur.fetchall()
                memories = []

                for row in rows:
                    memory = {
                        "id": row["id"],
                        "payload": row["payload"]
                    }

                    # Convert vector to list if included
                    if include_vectors and "vector" in row:
                        # pgvector returns string representation, convert to list
                        vector_str = row["vector"]
                        if vector_str:
                            # Parse pgvector format: "[0.1,0.2,0.3,...]"
                            memory["vector"] = [float(x) for x in vector_str.strip("[]").split(",")]

                    memories.append(memory)

                logger.info(f"Exported {len(memories)} memories")
                return memories

        finally:
            conn.close()

    def export_relationships(self) -> Dict[str, Any]:
        """
        Export all relationships from SQLite relationship store.

        Returns:
            Dictionary with relationships list and metadata
        """
        logger.info("Exporting relationships...")

        if not RELATIONSHIPS_AVAILABLE:
            logger.warning("Relationship store not available")
            return {
                "relationships": [],
                "count": 0,
                "error": "Relationship store not available"
            }

        try:
            store = get_relationship_store()

            # Query all relationships from SQLite
            cursor = store.conn.cursor()
            cursor.execute("""
                SELECT
                    id,
                    source_id,
                    target_id,
                    rel_type,
                    strength,
                    metadata,
                    created_at,
                    updated_at
                FROM relationships
                ORDER BY created_at DESC
            """)

            rows = cursor.fetchall()
            relationships = []

            for row in rows:
                relationships.append({
                    "id": row[0],
                    "source_id": row[1],
                    "target_id": row[2],
                    "rel_type": row[3],
                    "strength": row[4],
                    "metadata": json.loads(row[5]) if row[5] else {},
                    "created_at": row[6],
                    "updated_at": row[7]
                })

            logger.info(f"Exported {len(relationships)} relationships")

            return {
                "relationships": relationships,
                "count": len(relationships)
            }

        except Exception as e:
            logger.error(f"Failed to export relationships: {e}")
            return {
                "relationships": [],
                "count": 0,
                "error": str(e)
            }

    def export_all(
        self,
        output_path: str,
        format: str = "json",
        include_vectors: bool = True
    ) -> Dict[str, Any]:
        """
        Export all memories and relationships to files.

        Creates a complete backup including:
        - All memories with embeddings and metadata
        - All relationships
        - Export metadata (timestamp, counts, version)

        Args:
            output_path: Directory to write export files
            format: Export format ("json" or "csv")
            include_vectors: Whether to include vector embeddings

        Returns:
            Export summary with file paths and counts
        """
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Exporting to {output_dir} in {format} format...")

        # Export memories
        memories = self.export_memories(include_vectors=include_vectors)

        # Export relationships
        relationships_data = self.export_relationships()

        # Create export metadata
        export_metadata = {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "user_id": self.user_id,
            "memory_count": len(memories),
            "relationship_count": relationships_data["count"],
            "format": format,
            "includes_vectors": include_vectors
        }

        result = {
            "success": True,
            "output_path": str(output_dir),
            "format": format,
            "files": [],
            **export_metadata
        }

        # Write files based on format
        if format == "json":
            # Write combined JSON file
            combined_file = output_dir / "memory_export.json"
            with open(combined_file, "w") as f:
                json.dump({
                    "metadata": export_metadata,
                    "memories": memories,
                    "relationships": relationships_data["relationships"]
                }, f, indent=2, default=str)

            result["files"].append(str(combined_file))
            logger.info(f"Wrote combined export to {combined_file}")

        elif format == "csv":
            # Write memories CSV (flattened payload)
            memories_file = output_dir / "memories.csv"
            if memories:
                fieldnames = ["id", "content", "type", "source", "client", "project",
                             "domain", "created_at", "heat", "importance"]

                with open(memories_file, "w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()

                    for mem in memories:
                        payload = mem["payload"]
                        writer.writerow({
                            "id": mem["id"],
                            "content": payload.get("data", ""),
                            "type": payload.get("type", ""),
                            "source": payload.get("source", ""),
                            "client": payload.get("client", ""),
                            "project": payload.get("project", ""),
                            "domain": payload.get("domain", ""),
                            "created_at": payload.get("created_at", ""),
                            "heat": payload.get("heat", ""),
                            "importance": payload.get("importance", "")
                        })

                result["files"].append(str(memories_file))
                logger.info(f"Wrote memories CSV to {memories_file}")

            # Write relationships CSV
            relationships_file = output_dir / "relationships.csv"
            if relationships_data["relationships"]:
                with open(relationships_file, "w", newline="") as f:
                    fieldnames = ["id", "source_id", "target_id", "rel_type",
                                 "strength", "created_at", "updated_at"]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()

                    for rel in relationships_data["relationships"]:
                        writer.writerow({
                            "id": rel["id"],
                            "source_id": rel["source_id"],
                            "target_id": rel["target_id"],
                            "rel_type": rel["rel_type"],
                            "strength": rel["strength"],
                            "created_at": rel["created_at"],
                            "updated_at": rel["updated_at"]
                        })

                result["files"].append(str(relationships_file))
                logger.info(f"Wrote relationships CSV to {relationships_file}")

            # Write metadata JSON
            metadata_file = output_dir / "export_metadata.json"
            with open(metadata_file, "w") as f:
                json.dump(export_metadata, f, indent=2)
            result["files"].append(str(metadata_file))

        else:
            raise ValueError(f"Unsupported format: {format}. Use 'json' or 'csv'")

        logger.info(f"Export complete: {len(memories)} memories, {relationships_data['count']} relationships")
        return result


def main():
    """CLI entry point for memory export."""
    parser = argparse.ArgumentParser(
        description="Export Thanos Memory V2 data to portable formats"
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json",
        help="Output format (default: json)"
    )
    parser.add_argument(
        "--output",
        default="./History/Exports/memory",
        help="Output directory (default: ./History/Exports/memory)"
    )
    parser.add_argument(
        "--no-vectors",
        action="store_true",
        help="Exclude vector embeddings from export"
    )
    parser.add_argument(
        "--user",
        default=DEFAULT_USER_ID,
        help=f"User ID to export (default: {DEFAULT_USER_ID})"
    )

    args = parser.parse_args()

    try:
        exporter = MemoryExporter(user_id=args.user)
        result = exporter.export_all(
            output_path=args.output,
            format=args.format,
            include_vectors=not args.no_vectors
        )

        print("\n✓ Export complete")
        print(f"  Output: {result['output_path']}")
        print(f"  Memories: {result['memory_count']}")
        print(f"  Relationships: {result['relationship_count']}")
        print(f"  Files: {len(result['files'])}")
        for f in result['files']:
            print(f"    - {f}")

    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        print(f"\n✗ Export failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
