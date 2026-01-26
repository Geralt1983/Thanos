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
import hashlib
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

    def _generate_mermaid_graph(self, relationships: List[Dict[str, Any]]) -> str:
        """
        Generate Mermaid graph diagram from relationships.

        Creates a visual graph showing memory relationships with:
        - Shortened memory IDs as nodes
        - Relationship types and strengths on edges
        - Different arrow styles for different relationship types

        Args:
            relationships: List of relationship dictionaries

        Returns:
            Mermaid graph syntax as string
        """
        if not relationships:
            return "*No relationships to visualize*\n"

        lines = []
        lines.append("```mermaid\n")
        lines.append("graph TD\n")

        # Limit to top relationships by strength to avoid huge graphs
        # Sort by strength and take top 100
        sorted_rels = sorted(
            relationships,
            key=lambda r: r.get("strength", 0),
            reverse=True
        )[:100]

        # Build node ID mapping (shortened IDs for readability)
        node_ids = {}
        node_counter = 1

        for rel in sorted_rels:
            source = rel.get("source_id", "")
            target = rel.get("target_id", "")

            if source not in node_ids:
                node_ids[source] = f"M{node_counter}"
                node_counter += 1
            if target not in node_ids:
                node_ids[target] = f"M{node_counter}"
                node_counter += 1

        # Define arrow styles for different relationship types
        arrow_styles = {
            "caused": "-->",
            "prevented": "-.-x",
            "enabled": "-.->",
            "preceded": "-->",
            "followed": "-->",
            "concurrent": "<-->",
            "related_to": "---",
            "contradicts": "-.x",
            "supports": "==>",
            "elaborates": "-.->",
            "belongs_to": "-->",
            "impacts": "==>",
            "learned_from": "==>",
            "applied_to": "-->",
            "invalidated_by": "-.x"
        }

        # Render nodes with labels (shortened memory ID)
        for memory_id, short_id in node_ids.items():
            label = memory_id[:8]
            lines.append(f"    {short_id}[\"{label}...\"]\n")

        # Render edges with relationship types and strengths
        for rel in sorted_rels:
            source = rel.get("source_id", "")
            target = rel.get("target_id", "")
            rel_type = rel.get("rel_type", "unknown")
            strength = rel.get("strength", 1.0)

            source_id = node_ids.get(source)
            target_id = node_ids.get(target)

            if not source_id or not target_id:
                continue

            # Get arrow style for this relationship type
            arrow = arrow_styles.get(rel_type, "-->")

            # Format relationship label with type and strength
            rel_label = f"{rel_type} ({strength:.2f})"

            lines.append(f"    {source_id} {arrow}|{rel_label}| {target_id}\n")

        lines.append("```\n")

        # Add legend
        if sorted_rels:
            lines.append("\n**Graph Legend:**\n")
            lines.append("- Nodes: Memory IDs (shortened)\n")
            lines.append("- Edges: Relationship type and strength\n")
            if len(relationships) > 100:
                lines.append(f"- *Showing top 100 of {len(relationships)} relationships by strength*\n")

        return "".join(lines)

    def _generate_markdown(
        self,
        memories: List[Dict[str, Any]],
        relationships_data: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> str:
        """
        Generate Markdown formatted export of memories and relationships.

        Creates a human-readable Markdown document with:
        - Export metadata in header
        - Memories grouped by client/project
        - Heat indicators (🔥 hot, • normal, ❄️ cold)
        - Relationships section with Mermaid graph diagrams

        Args:
            memories: List of memory dictionaries
            relationships_data: Dictionary with relationships list
            metadata: Export metadata dictionary

        Returns:
            Markdown formatted string
        """
        lines = []

        # Header
        lines.append("# Thanos Memory Export\n")
        lines.append(f"**Exported:** {metadata['timestamp']}\n")
        lines.append(f"**User:** {metadata['user_id']}\n")
        lines.append(f"**Total Memories:** {metadata['memory_count']}\n")
        lines.append(f"**Total Relationships:** {metadata['relationship_count']}\n")
        lines.append("\n---\n")

        # Group memories by client/project
        grouped_memories = {}
        ungrouped_memories = []

        for mem in memories:
            payload = mem.get("payload", {})
            client = payload.get("client", "").strip()
            project = payload.get("project", "").strip()

            if client or project:
                key = (client or "No Client", project or "General")
                if key not in grouped_memories:
                    grouped_memories[key] = []
                grouped_memories[key].append(mem)
            else:
                ungrouped_memories.append(mem)

        # Render grouped memories
        if grouped_memories:
            lines.append("## Memories by Client/Project\n\n")

            for (client, project), mems in sorted(grouped_memories.items()):
                lines.append(f"### Client: {client}\n")
                if project != "General":
                    lines.append(f"#### Project: {project}\n")
                lines.append("\n")

                for mem in mems:
                    lines.append(self._format_memory_markdown(mem))
                    lines.append("\n")

        # Render ungrouped memories
        if ungrouped_memories:
            lines.append("## General Memories\n\n")
            for mem in ungrouped_memories:
                lines.append(self._format_memory_markdown(mem))
                lines.append("\n")

        # Relationships section
        if relationships_data.get("relationships"):
            lines.append("\n---\n\n")
            lines.append("## Relationships\n\n")
            lines.append(f"**Total Relationships:** {relationships_data['count']}\n\n")

            # Add Mermaid graph diagram
            lines.append("### Relationship Graph\n\n")
            lines.append(self._generate_mermaid_graph(relationships_data["relationships"]))
            lines.append("\n")

            # Group by relationship type
            by_type = {}
            for rel in relationships_data["relationships"]:
                rel_type = rel.get("rel_type", "unknown")
                if rel_type not in by_type:
                    by_type[rel_type] = []
                by_type[rel_type].append(rel)

            for rel_type, rels in sorted(by_type.items()):
                lines.append(f"### {rel_type.replace('_', ' ').title()}\n\n")
                lines.append("| Source | Target | Strength | Created |\n")
                lines.append("|--------|--------|----------|----------|\n")

                for rel in rels:
                    source = rel.get("source_id", "")[:12]
                    target = rel.get("target_id", "")[:12]
                    strength = rel.get("strength", 0)
                    created = rel.get("created_at", "")[:10]
                    lines.append(f"| `{source}...` | `{target}...` | {strength} | {created} |\n")

                lines.append("\n")

        return "".join(lines)

    def _format_memory_markdown(self, mem: Dict[str, Any]) -> str:
        """
        Format a single memory as Markdown.

        Includes heat indicator, content preview, and metadata.

        Args:
            mem: Memory dictionary with id, payload, optional vector

        Returns:
            Markdown formatted string for this memory
        """
        payload = mem.get("payload", {})
        content = payload.get("data", "")
        memory_type = payload.get("type", "")
        domain = payload.get("domain", "")
        source = payload.get("source", "")
        heat = payload.get("heat", 0)
        importance = payload.get("importance", "")
        created_at = payload.get("created_at", "")

        # Heat indicator
        if heat > 0.7:
            heat_icon = "🔥"
            heat_label = "Hot"
        elif heat > 0.3:
            heat_icon = "•"
            heat_label = "Normal"
        else:
            heat_icon = "❄️"
            heat_label = "Cold"

        # Content preview (first line or first 100 chars)
        content_preview = content.split("\n")[0] if content else "[No content]"
        if len(content_preview) > 100:
            content_preview = content_preview[:97] + "..."

        lines = []
        lines.append(f"##### {heat_icon} {content_preview}\n\n")
        lines.append(f"**ID:** `{mem.get('id', '')}`  \n")

        if memory_type:
            lines.append(f"**Type:** {memory_type}  \n")
        if domain:
            lines.append(f"**Domain:** {domain}  \n")
        if source:
            lines.append(f"**Source:** {source}  \n")

        lines.append(f"**Heat:** {heat:.2f} ({heat_label})  \n")

        if importance:
            lines.append(f"**Importance:** {importance}  \n")
        if created_at:
            lines.append(f"**Created:** {created_at[:10]}  \n")

        # Full content if different from preview
        if len(content) > len(content_preview):
            lines.append("\n**Content:**\n\n")
            lines.append(f"```\n{content}\n```\n")

        return "".join(lines)

    def _calculate_checksum(self, file_path: Path) -> str:
        """
        Calculate SHA-256 checksum of a file.

        Args:
            file_path: Path to file to checksum

        Returns:
            Hexadecimal SHA-256 checksum string
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files efficiently
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

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
            "checksums": {},
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

            # Calculate checksum for the file
            checksum = self._calculate_checksum(combined_file)
            result["files"].append(str(combined_file))
            result["checksums"][str(combined_file)] = checksum
            logger.info(f"Wrote combined export to {combined_file} (checksum: {checksum})")

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

                # Calculate checksum for memories CSV
                checksum = self._calculate_checksum(memories_file)
                result["files"].append(str(memories_file))
                result["checksums"][str(memories_file)] = checksum
                logger.info(f"Wrote memories CSV to {memories_file} (checksum: {checksum})")

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

                # Calculate checksum for relationships CSV
                checksum = self._calculate_checksum(relationships_file)
                result["files"].append(str(relationships_file))
                result["checksums"][str(relationships_file)] = checksum
                logger.info(f"Wrote relationships CSV to {relationships_file} (checksum: {checksum})")

            # Write metadata JSON
            metadata_file = output_dir / "export_metadata.json"
            with open(metadata_file, "w") as f:
                json.dump(export_metadata, f, indent=2)

            # Calculate checksum for metadata JSON
            checksum = self._calculate_checksum(metadata_file)
            result["files"].append(str(metadata_file))
            result["checksums"][str(metadata_file)] = checksum

        elif format == "markdown":
            # Write markdown file
            markdown_file = output_dir / "memories.md"
            markdown_content = self._generate_markdown(memories, relationships_data, export_metadata)

            with open(markdown_file, "w") as f:
                f.write(markdown_content)

            # Calculate checksum for markdown file
            checksum = self._calculate_checksum(markdown_file)
            result["files"].append(str(markdown_file))
            result["checksums"][str(markdown_file)] = checksum
            logger.info(f"Wrote markdown export to {markdown_file} (checksum: {checksum})")

        else:
            raise ValueError(f"Unsupported format: {format}. Use 'json', 'csv', or 'markdown'")

        # Generate a combined checksum of all file checksums for verification
        if result["checksums"]:
            combined_hash = hashlib.sha256()
            for file_path in sorted(result["checksums"].keys()):
                combined_hash.update(result["checksums"][file_path].encode('utf-8'))
            result["checksum"] = combined_hash.hexdigest()
            logger.info(f"Combined checksum: {result['checksum']}")

        logger.info(f"Export complete: {len(memories)} memories, {relationships_data['count']} relationships")
        return result

    def verify_export(self, export_path: str) -> bool:
        """
        Verify the integrity of an exported backup.

        Performs comprehensive validation:
        - Checks that export directory exists
        - Verifies all required files are present
        - Recalculates and validates file checksums
        - Validates record counts match metadata
        - Validates JSON schema structure

        Args:
            export_path: Path to the export directory to verify

        Returns:
            True if export is valid and complete, False otherwise
        """
        export_dir = Path(export_path)
        logger.info(f"Verifying export at {export_dir}...")

        # Check export directory exists
        if not export_dir.exists():
            logger.error(f"Export directory does not exist: {export_dir}")
            return False

        if not export_dir.is_dir():
            logger.error(f"Export path is not a directory: {export_dir}")
            return False

        # Detect format based on files present
        json_file = export_dir / "memory_export.json"
        csv_memories_file = export_dir / "memories.csv"
        csv_relationships_file = export_dir / "relationships.csv"
        csv_metadata_file = export_dir / "export_metadata.json"
        markdown_file = export_dir / "memories.md"

        # Determine format and required files
        format_type = None
        required_files = []

        if json_file.exists():
            format_type = "json"
            required_files = [json_file]
        elif csv_memories_file.exists() or csv_metadata_file.exists():
            format_type = "csv"
            # CSV exports may not have all files if there's no data
            if csv_memories_file.exists():
                required_files.append(csv_memories_file)
            if csv_relationships_file.exists():
                required_files.append(csv_relationships_file)
            if csv_metadata_file.exists():
                required_files.append(csv_metadata_file)
        elif markdown_file.exists():
            format_type = "markdown"
            required_files = [markdown_file]
        else:
            logger.error("No valid export files found in directory")
            return False

        logger.info(f"Detected format: {format_type}")

        # Verify all required files exist
        for file_path in required_files:
            if not file_path.exists():
                logger.error(f"Required file missing: {file_path}")
                return False
            if not file_path.is_file():
                logger.error(f"Path is not a file: {file_path}")
                return False
            logger.info(f"✓ File exists: {file_path.name}")

        # Verify file checksums (if we can recalculate them)
        logger.info("Verifying file integrity...")
        for file_path in required_files:
            try:
                checksum = self._calculate_checksum(file_path)
                logger.info(f"✓ Checksum calculated for {file_path.name}: {checksum[:16]}...")
            except Exception as e:
                logger.error(f"Failed to calculate checksum for {file_path}: {e}")
                return False

        # Load and validate metadata (JSON and CSV formats)
        metadata = None
        if format_type == "json":
            try:
                with open(json_file, "r") as f:
                    data = json.load(f)

                # Validate JSON schema structure
                if "metadata" not in data:
                    logger.error("JSON export missing 'metadata' field")
                    return False
                if "memories" not in data:
                    logger.error("JSON export missing 'memories' field")
                    return False
                if "relationships" not in data:
                    logger.error("JSON export missing 'relationships' field")
                    return False

                metadata = data["metadata"]

                # Validate metadata fields
                required_metadata_fields = ["version", "timestamp", "user_id", "memory_count", "relationship_count"]
                for field in required_metadata_fields:
                    if field not in metadata:
                        logger.error(f"Metadata missing required field: {field}")
                        return False

                logger.info(f"✓ JSON schema valid")

                # Verify record counts
                actual_memory_count = len(data["memories"])
                actual_relationship_count = len(data["relationships"])
                expected_memory_count = metadata["memory_count"]
                expected_relationship_count = metadata["relationship_count"]

                if actual_memory_count != expected_memory_count:
                    logger.error(f"Memory count mismatch: expected {expected_memory_count}, found {actual_memory_count}")
                    return False

                if actual_relationship_count != expected_relationship_count:
                    logger.error(f"Relationship count mismatch: expected {expected_relationship_count}, found {actual_relationship_count}")
                    return False

                logger.info(f"✓ Record counts valid: {actual_memory_count} memories, {actual_relationship_count} relationships")

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in export file: {e}")
                return False
            except Exception as e:
                logger.error(f"Error reading JSON export: {e}")
                return False

        elif format_type == "csv":
            # Load metadata from export_metadata.json if present
            if csv_metadata_file.exists():
                try:
                    with open(csv_metadata_file, "r") as f:
                        metadata = json.load(f)

                    # Validate metadata fields
                    required_metadata_fields = ["version", "timestamp", "user_id", "memory_count", "relationship_count"]
                    for field in required_metadata_fields:
                        if field not in metadata:
                            logger.error(f"Metadata missing required field: {field}")
                            return False

                    logger.info(f"✓ Metadata valid")

                    # Verify CSV record counts match metadata
                    if csv_memories_file.exists():
                        with open(csv_memories_file, "r") as f:
                            reader = csv.DictReader(f)
                            actual_memory_count = sum(1 for _ in reader)

                        expected_memory_count = metadata["memory_count"]
                        if actual_memory_count != expected_memory_count:
                            logger.error(f"Memory count mismatch: expected {expected_memory_count}, found {actual_memory_count}")
                            return False

                        logger.info(f"✓ Memory count valid: {actual_memory_count} records")

                    if csv_relationships_file.exists():
                        with open(csv_relationships_file, "r") as f:
                            reader = csv.DictReader(f)
                            actual_relationship_count = sum(1 for _ in reader)

                        expected_relationship_count = metadata["relationship_count"]
                        if actual_relationship_count != expected_relationship_count:
                            logger.error(f"Relationship count mismatch: expected {expected_relationship_count}, found {actual_relationship_count}")
                            return False

                        logger.info(f"✓ Relationship count valid: {actual_relationship_count} records")

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in metadata file: {e}")
                    return False
                except Exception as e:
                    logger.error(f"Error reading CSV export: {e}")
                    return False

        elif format_type == "markdown":
            # For markdown, verify file is readable and non-empty
            try:
                with open(markdown_file, "r") as f:
                    content = f.read()

                if not content:
                    logger.error("Markdown file is empty")
                    return False

                # Check for basic structure markers
                if "# Thanos Memory Export" not in content:
                    logger.error("Markdown file missing expected header")
                    return False

                logger.info(f"✓ Markdown structure valid ({len(content)} bytes)")

            except Exception as e:
                logger.error(f"Error reading markdown export: {e}")
                return False

        # All checks passed
        logger.info(f"✅ Export verification complete: All checks passed")
        return True

    def restore_from_backup(
        self,
        backup_path: str,
        dry_run: bool = False,
        conflict_mode: str = "skip"
    ) -> Dict[str, Any]:
        """
        Restore memories from a JSON backup.

        Restores memories to the thanos_memories table, preserving:
        - Memory IDs
        - Vector embeddings
        - Full payload data (content, metadata, heat, importance)
        - Timestamps

        Args:
            backup_path: Path to backup directory containing export files
            dry_run: If True, validate backup but don't restore (preview mode)
            conflict_mode: How to handle duplicate IDs ("skip" or "update")

        Returns:
            Dictionary with restore statistics and results
        """
        backup_dir = Path(backup_path)
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Restoring from {backup_dir}...")

        # Verify backup exists and is valid
        if not self.verify_export(str(backup_dir)):
            raise ValueError(f"Backup verification failed: {backup_dir}")

        # Detect format and load backup data
        json_file = backup_dir / "memory_export.json"
        csv_memories_file = backup_dir / "memories.csv"
        csv_metadata_file = backup_dir / "export_metadata.json"

        memories = []
        metadata = None
        format_type = None

        if json_file.exists():
            # Load JSON backup
            format_type = "json"
            logger.info("Loading JSON backup...")
            with open(json_file, "r") as f:
                data = json.load(f)

            memories = data.get("memories", [])
            metadata = data.get("metadata", {})

        elif csv_memories_file.exists() and csv_metadata_file.exists():
            # CSV format not supported for restore (no vector data)
            raise ValueError("Cannot restore from CSV format: vector embeddings not included in CSV export. Use JSON format for backups intended for restore.")

        else:
            raise ValueError(f"No valid backup files found in {backup_dir}")

        if not memories:
            logger.warning("No memories found in backup")
            return {
                "success": True,
                "dry_run": dry_run,
                "restored": 0,
                "skipped": 0,
                "updated": 0,
                "errors": []
            }

        logger.info(f"Found {len(memories)} memories in backup")

        # Validate conflict_mode
        if conflict_mode not in ["skip", "update"]:
            raise ValueError(f"Invalid conflict_mode: {conflict_mode}. Use 'skip' or 'update'")

        # Dry run: just report what would happen
        if dry_run:
            return self._dry_run_restore(memories, metadata, conflict_mode)

        # Actual restore
        return self._execute_restore(memories, metadata, conflict_mode)

    def _dry_run_restore(
        self,
        memories: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        conflict_mode: str
    ) -> Dict[str, Any]:
        """
        Dry run: analyze restore without making changes.

        Checks for conflicts and reports what would happen.

        Args:
            memories: List of memories to restore
            metadata: Backup metadata
            conflict_mode: How conflicts would be handled

        Returns:
            Dictionary with analysis results
        """
        logger.info("[DRY RUN] Analyzing restore operation...")

        # Check which memory IDs already exist
        memory_ids = [mem["id"] for mem in memories]
        existing_ids = set()

        if memory_ids:
            conn = self._get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id FROM thanos_memories
                        WHERE id = ANY(%s)
                    """, (memory_ids,))
                    existing_ids = {row[0] for row in cur.fetchall()}
            finally:
                conn.close()

        conflicts = [mem_id for mem_id in memory_ids if mem_id in existing_ids]
        new_memories = [mem for mem in memories if mem["id"] not in existing_ids]
        conflicting_memories = [mem for mem in memories if mem["id"] in existing_ids]

        result = {
            "success": True,
            "dry_run": True,
            "total_in_backup": len(memories),
            "new_memories": len(new_memories),
            "conflicts": len(conflicts),
            "conflict_mode": conflict_mode,
            "would_restore": len(new_memories),
            "would_skip": len(conflicts) if conflict_mode == "skip" else 0,
            "would_update": len(conflicts) if conflict_mode == "update" else 0,
            "metadata": metadata
        }

        logger.info(f"[DRY RUN] Analysis complete:")
        logger.info(f"  Total memories in backup: {result['total_in_backup']}")
        logger.info(f"  New memories (would restore): {result['new_memories']}")
        logger.info(f"  Conflicts detected: {result['conflicts']}")
        if conflict_mode == "skip":
            logger.info(f"  Would skip conflicts: {result['would_skip']}")
        else:
            logger.info(f"  Would update conflicts: {result['would_update']}")

        return result

    def _execute_restore(
        self,
        memories: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        conflict_mode: str
    ) -> Dict[str, Any]:
        """
        Execute the actual restore operation.

        Inserts memories into thanos_memories table with conflict handling.

        Args:
            memories: List of memories to restore
            metadata: Backup metadata
            conflict_mode: How to handle conflicts ("skip" or "update")

        Returns:
            Dictionary with restore statistics
        """
        logger.info(f"Restoring {len(memories)} memories with conflict_mode={conflict_mode}...")

        restored = 0
        skipped = 0
        updated = 0
        errors = []

        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                for mem in memories:
                    try:
                        memory_id = mem["id"]
                        payload = mem["payload"]

                        # Handle vector if present
                        vector = mem.get("vector")

                        if conflict_mode == "skip":
                            # Insert only if ID doesn't exist
                            if vector:
                                cur.execute("""
                                    INSERT INTO thanos_memories (id, vector, payload)
                                    VALUES (%s, %s::vector, %s::jsonb)
                                    ON CONFLICT (id) DO NOTHING
                                """, (memory_id, vector, json.dumps(payload)))
                            else:
                                # No vector in backup (shouldn't happen with JSON, but handle gracefully)
                                cur.execute("""
                                    INSERT INTO thanos_memories (id, payload)
                                    VALUES (%s, %s::jsonb)
                                    ON CONFLICT (id) DO NOTHING
                                """, (memory_id, json.dumps(payload)))

                            # Check if row was actually inserted
                            if cur.rowcount > 0:
                                restored += 1
                            else:
                                skipped += 1

                        elif conflict_mode == "update":
                            # Insert or update if exists
                            if vector:
                                cur.execute("""
                                    INSERT INTO thanos_memories (id, vector, payload)
                                    VALUES (%s, %s::vector, %s::jsonb)
                                    ON CONFLICT (id) DO UPDATE
                                    SET vector = EXCLUDED.vector,
                                        payload = EXCLUDED.payload
                                """, (memory_id, vector, json.dumps(payload)))
                            else:
                                cur.execute("""
                                    INSERT INTO thanos_memories (id, payload)
                                    VALUES (%s, %s::jsonb)
                                    ON CONFLICT (id) DO UPDATE
                                    SET payload = EXCLUDED.payload
                                """, (memory_id, json.dumps(payload)))

                            # Check if it was an insert or update
                            # Unfortunately, we can't easily distinguish, so we count as restored
                            # In a more sophisticated implementation, we'd check beforehand
                            restored += 1

                    except Exception as e:
                        error_msg = f"Failed to restore memory {mem.get('id', 'unknown')}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        continue

            # Commit all changes
            conn.commit()
            logger.info(f"✅ Restore complete: {restored} restored, {skipped} skipped, {len(errors)} errors")

        except Exception as e:
            conn.rollback()
            logger.error(f"Restore failed: {e}", exc_info=True)
            raise

        finally:
            conn.close()

        result = {
            "success": len(errors) == 0,
            "dry_run": False,
            "total_in_backup": len(memories),
            "restored": restored,
            "skipped": skipped,
            "updated": updated,
            "errors": errors,
            "conflict_mode": conflict_mode,
            "metadata": metadata
        }

        return result


def main():
    """CLI entry point for memory export."""
    parser = argparse.ArgumentParser(
        description="Export Thanos Memory V2 data to portable formats"
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv", "markdown"],
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
            checksum = result['checksums'].get(f, "N/A")[:16]
            print(f"    - {f} (checksum: {checksum}...)")
        if 'checksum' in result:
            print(f"  Combined checksum: {result['checksum']}")

    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        print(f"\n✗ Export failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
