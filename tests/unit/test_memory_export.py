#!/usr/bin/env python3
"""
Unit Tests for Memory Export/Backup/Restore System.

Tests cover:
- MemoryExporter initialization
- Export methods (memories, relationships, all)
- Format support (JSON, CSV, Markdown)
- Checksum generation and validation
- Export verification
- Restore functionality (dry-run and actual)
- Conflict handling (skip vs update modes)
- Error handling

All tests use mocked database connections for CI/CD compatibility.
"""

from pathlib import Path
import sys
import json
import tempfile
import hashlib
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ========================================================================
# Test Fixtures
# ========================================================================


@pytest.fixture
def mock_psycopg2():
    """Mock psycopg2 module to avoid database dependency."""
    with patch("Tools.memory_export.psycopg2") as mock_pg:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pg.connect.return_value = mock_conn

        # Provide RealDictCursor
        mock_pg.extras.RealDictCursor = Mock

        yield {"module": mock_pg, "conn": mock_conn, "cursor": mock_cursor}


@pytest.fixture
def sample_memories():
    """Provide sample memory data for testing."""
    return [
        {
            "id": "mem_001",
            "user_id": "jeremy",
            "memory": "Orlando project meeting about API design",
            "hash": "abc123",
            "created_at": "2026-01-20T10:00:00Z",
            "updated_at": "2026-01-20T10:00:00Z",
            "metadata": {
                "client": "Orlando",
                "domain": "work",
                "heat": 0.85,
                "importance": 1.0
            },
            "embedding": [0.1] * 1536  # Mock 1536-dim vector
        },
        {
            "id": "mem_002",
            "user_id": "jeremy",
            "memory": "Raleigh project update on database migration",
            "hash": "def456",
            "created_at": "2026-01-21T14:30:00Z",
            "updated_at": "2026-01-21T14:30:00Z",
            "metadata": {
                "client": "Raleigh",
                "domain": "work",
                "heat": 0.65,
                "importance": 0.8
            },
            "embedding": [0.2] * 1536
        },
        {
            "id": "mem_003",
            "user_id": "jeremy",
            "memory": "Personal: Ashley's birthday next week",
            "hash": "ghi789",
            "created_at": "2026-01-22T09:15:00Z",
            "updated_at": "2026-01-22T09:15:00Z",
            "metadata": {
                "domain": "personal",
                "heat": 0.25,
                "importance": 0.9
            },
            "embedding": [0.3] * 1536
        }
    ]


@pytest.fixture
def sample_relationships():
    """Provide sample relationship data for testing."""
    return [
        {
            "source_id": "mem_001",
            "target_id": "mem_002",
            "rel_type": "relates_to",
            "strength": 0.75,
            "metadata": {"context": "both about work projects"},
            "created_at": "2026-01-22T10:00:00Z",
            "last_accessed": "2026-01-22T10:00:00Z"
        },
        {
            "source_id": "mem_002",
            "target_id": "mem_003",
            "rel_type": "followed_by",
            "strength": 0.50,
            "metadata": {},
            "created_at": "2026-01-22T14:00:00Z",
            "last_accessed": "2026-01-22T14:00:00Z"
        }
    ]


@pytest.fixture
def temp_export_dir():
    """Create temporary directory for test exports."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def create_test_export(temp_export_dir, sample_memories, sample_relationships):
    """Helper to create valid test export."""
    def _create(format="json", include_checksums=True):
        export_data = {
            "metadata": {
                "version": "1.0",
                "timestamp": datetime.now().isoformat(),
                "user_id": "jeremy",
                "memory_count": len(sample_memories),
                "relationship_count": len(sample_relationships),
                "format": format,
                "includes_vectors": True
            },
            "memories": sample_memories,
            "relationships": sample_relationships
        }

        export_path = temp_export_dir / f"test_export_{format}"
        export_path.mkdir(exist_ok=True)

        if format == "json":
            json_path = export_path / "memory_export.json"
            with open(json_path, "w") as f:
                json.dump(export_data, f, indent=2)

            if include_checksums:
                checksum = hashlib.sha256(json_path.read_bytes()).hexdigest()
                metadata_path = export_path / "metadata.json"
                with open(metadata_path, "w") as f:
                    json.dump({**export_data["metadata"], "checksum": checksum}, f)

        return export_path

    return _create


# ========================================================================
# Test MemoryExporter Initialization
# ========================================================================


class TestMemoryExporterInitialization:
    """Test MemoryExporter initialization with various configurations."""

    @patch("Tools.memory_export.psycopg2", None)
    def test_initialization_without_psycopg2_raises_error(self):
        """Test that ImportError is raised when psycopg2 is not available."""
        from Tools.memory_export import MemoryExporter

        with pytest.raises(ImportError, match="psycopg2 not installed"):
            MemoryExporter()

    @patch("Tools.memory_export.psycopg2")
    @patch("Tools.memory_export.NEON_DATABASE_URL", "postgresql://test:test@localhost/thanos")
    def test_initialization_with_default_params(self, mock_pg):
        """Test MemoryExporter initialization with default parameters."""
        from Tools.memory_export import MemoryExporter

        exporter = MemoryExporter()

        assert exporter.database_url == "postgresql://test:test@localhost/thanos"
        assert exporter.user_id == "jeremy"

    @patch("Tools.memory_export.psycopg2")
    def test_initialization_with_custom_database_url(self, mock_pg):
        """Test MemoryExporter initialization with custom database URL."""
        from Tools.memory_export import MemoryExporter

        custom_url = "postgresql://custom:custom@localhost/custom_db"
        exporter = MemoryExporter(database_url=custom_url)

        assert exporter.database_url == custom_url

    @patch("Tools.memory_export.psycopg2")
    def test_initialization_with_custom_user_id(self, mock_pg):
        """Test MemoryExporter initialization with custom user ID."""
        from Tools.memory_export import MemoryExporter

        exporter = MemoryExporter(user_id="test_user")

        assert exporter.user_id == "test_user"


# ========================================================================
# Test Export Methods
# ========================================================================


class TestExportMemories:
    """Test memory export functionality."""

    @patch("Tools.memory_export.psycopg2")
    def test_export_memories_json(self, mock_pg, temp_export_dir, sample_memories):
        """Test exporting memories to JSON format."""
        from Tools.memory_export import MemoryExporter

        # Setup mock database response
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = sample_memories
        mock_cursor.description = [(col,) for col in sample_memories[0].keys()]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pg.connect.return_value = mock_conn

        exporter = MemoryExporter()
        result = exporter.export_memories(
            output_path=str(temp_export_dir),
            format="json"
        )

        assert result["success"] is True
        assert result["memory_count"] == 3
        assert "file_path" in result

        # Verify JSON file was created
        json_path = Path(result["file_path"])
        assert json_path.exists()

        # Verify JSON content
        with open(json_path, "r") as f:
            data = json.load(f)

        assert "memories" in data
        assert len(data["memories"]) == 3
        assert data["memories"][0]["id"] == "mem_001"

    @patch("Tools.memory_export.psycopg2")
    def test_export_memories_csv(self, mock_pg, temp_export_dir, sample_memories):
        """Test exporting memories to CSV format."""
        from Tools.memory_export import MemoryExporter

        # Setup mock
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = sample_memories
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pg.connect.return_value = mock_conn

        exporter = MemoryExporter()
        result = exporter.export_memories(
            output_path=str(temp_export_dir),
            format="csv"
        )

        assert result["success"] is True
        assert result["memory_count"] == 3

        # Verify CSV file was created
        csv_path = Path(result["file_path"])
        assert csv_path.exists()
        assert csv_path.suffix == ".csv"

        # Verify CSV has content
        content = csv_path.read_text()
        assert "mem_001" in content
        assert "Orlando project" in content

    @patch("Tools.memory_export.psycopg2")
    def test_export_memories_markdown(self, mock_pg, temp_export_dir, sample_memories):
        """Test exporting memories to Markdown format."""
        from Tools.memory_export import MemoryExporter

        # Setup mock
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = sample_memories
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pg.connect.return_value = mock_conn

        exporter = MemoryExporter()
        result = exporter.export_memories(
            output_path=str(temp_export_dir),
            format="markdown"
        )

        assert result["success"] is True

        # Verify markdown file was created
        md_path = Path(result["file_path"])
        assert md_path.exists()
        assert md_path.suffix == ".md"

        # Verify markdown content has heat indicators
        content = md_path.read_text()
        assert "🔥" in content or "•" in content or "❄️" in content
        assert "Orlando project" in content

    @patch("Tools.memory_export.psycopg2")
    def test_export_no_vectors(self, mock_pg, temp_export_dir, sample_memories):
        """Test exporting memories without vector embeddings."""
        from Tools.memory_export import MemoryExporter

        # Setup mock
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = sample_memories
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pg.connect.return_value = mock_conn

        exporter = MemoryExporter()
        result = exporter.export_memories(
            output_path=str(temp_export_dir),
            format="json",
            include_vectors=False
        )

        assert result["success"] is True

        # Verify JSON doesn't include vectors
        with open(result["file_path"], "r") as f:
            data = json.load(f)

        # Check that embedding field is excluded
        for memory in data["memories"]:
            assert "embedding" not in memory or memory["embedding"] is None


class TestExportRelationships:
    """Test relationship export functionality."""

    @patch("Tools.memory_export.psycopg2")
    @patch("Tools.memory_export.get_relationship_store")
    def test_export_relationships(self, mock_get_store, mock_pg, sample_relationships):
        """Test exporting relationships from SQLite."""
        from Tools.memory_export import MemoryExporter

        # Mock relationship store
        mock_store = MagicMock()
        mock_store.get_all_relationships.return_value = sample_relationships
        mock_get_store.return_value = mock_store

        exporter = MemoryExporter()
        result = exporter.export_relationships()

        assert "relationships" in result
        assert len(result["relationships"]) == 2
        assert result["relationships"][0]["source_id"] == "mem_001"
        assert result["relationship_count"] == 2


class TestExportAll:
    """Test unified export combining memories and relationships."""

    @patch("Tools.memory_export.psycopg2")
    @patch("Tools.memory_export.get_relationship_store")
    def test_export_all_json(self, mock_get_store, mock_pg, temp_export_dir,
                              sample_memories, sample_relationships):
        """Test export_all with JSON format."""
        from Tools.memory_export import MemoryExporter

        # Setup mocks
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = sample_memories
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pg.connect.return_value = mock_conn

        mock_store = MagicMock()
        mock_store.get_all_relationships.return_value = sample_relationships
        mock_get_store.return_value = mock_store

        exporter = MemoryExporter()
        result = exporter.export_all(
            output_path=str(temp_export_dir),
            format="json"
        )

        assert result["success"] is True
        assert result["memory_count"] == 3
        assert result["relationship_count"] == 2
        assert "checksums" in result

        # Verify combined export
        with open(result["file_path"], "r") as f:
            data = json.load(f)

        assert "metadata" in data
        assert "memories" in data
        assert "relationships" in data
        assert data["metadata"]["memory_count"] == 3
        assert data["metadata"]["relationship_count"] == 2


# ========================================================================
# Test Checksum Generation and Verification
# ========================================================================


class TestChecksumOperations:
    """Test checksum generation and validation."""

    @patch("Tools.memory_export.psycopg2")
    @patch("Tools.memory_export.get_relationship_store")
    def test_checksum_generation(self, mock_get_store, mock_pg, temp_export_dir,
                                  sample_memories, sample_relationships):
        """Test that checksums are generated for exported files."""
        from Tools.memory_export import MemoryExporter

        # Setup mocks
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = sample_memories
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pg.connect.return_value = mock_conn

        mock_store = MagicMock()
        mock_store.get_all_relationships.return_value = sample_relationships
        mock_get_store.return_value = mock_store

        exporter = MemoryExporter()
        result = exporter.export_all(output_path=str(temp_export_dir), format="json")

        assert "checksums" in result
        assert isinstance(result["checksums"], dict)
        assert len(result["checksums"]) > 0

    @patch("Tools.memory_export.psycopg2")
    def test_checksum_consistency(self, mock_pg, temp_export_dir):
        """Test that same file produces same checksum."""
        from Tools.memory_export import MemoryExporter

        # Create a test file
        test_file = temp_export_dir / "test.json"
        test_data = {"test": "data"}
        with open(test_file, "w") as f:
            json.dump(test_data, f)

        exporter = MemoryExporter()
        checksum1 = exporter._calculate_checksum(test_file)
        checksum2 = exporter._calculate_checksum(test_file)

        assert checksum1 == checksum2
        assert len(checksum1) == 64  # SHA-256 produces 64 hex chars


class TestExportVerification:
    """Test export verification functionality."""

    @patch("Tools.memory_export.psycopg2")
    def test_verify_export_valid(self, mock_pg, create_test_export):
        """Test verification of a valid export."""
        from Tools.memory_export import MemoryExporter

        export_path = create_test_export(format="json", include_checksums=True)

        exporter = MemoryExporter()
        is_valid = exporter.verify_export(str(export_path))

        assert is_valid is True

    @patch("Tools.memory_export.psycopg2")
    def test_verify_export_invalid_checksum(self, mock_pg, create_test_export):
        """Test verification fails when file is corrupted."""
        from Tools.memory_export import MemoryExporter

        export_path = create_test_export(format="json", include_checksums=True)

        # Corrupt the export file
        json_file = export_path / "memory_export.json"
        with open(json_file, "a") as f:
            f.write("CORRUPTED DATA")

        exporter = MemoryExporter()
        is_valid = exporter.verify_export(str(export_path))

        # Should fail due to checksum mismatch
        assert is_valid is False

    @patch("Tools.memory_export.psycopg2")
    def test_verify_export_missing_file(self, mock_pg, temp_export_dir):
        """Test verification fails when export directory is missing files."""
        from Tools.memory_export import MemoryExporter

        # Create incomplete export (missing files)
        incomplete_path = temp_export_dir / "incomplete_export"
        incomplete_path.mkdir()

        exporter = MemoryExporter()
        is_valid = exporter.verify_export(str(incomplete_path))

        assert is_valid is False


# ========================================================================
# Test Restore Functionality
# ========================================================================


class TestRestoreFunctionality:
    """Test restore/import functionality."""

    @patch("Tools.memory_export.psycopg2")
    @patch("Tools.memory_export.get_relationship_store")
    def test_restore_dry_run(self, mock_get_store, mock_pg, create_test_export):
        """Test dry-run restore mode shows preview without making changes."""
        from Tools.memory_export import MemoryExporter

        export_path = create_test_export(format="json")

        # Setup mocks
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []  # Existing DB is empty
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pg.connect.return_value = mock_conn

        mock_store = MagicMock()
        mock_get_store.return_value = mock_store

        exporter = MemoryExporter()
        result = exporter.restore_from_backup(str(export_path), dry_run=True)

        assert result["dry_run"] is True
        assert "would_restore" in result
        assert result["would_restore"] > 0

        # Verify no database writes occurred
        mock_conn.commit.assert_not_called()

    @patch("Tools.memory_export.psycopg2")
    @patch("Tools.memory_export.get_relationship_store")
    def test_restore_conflict_mode_skip(self, mock_get_store, mock_pg,
                                        create_test_export, sample_memories):
        """Test restore with conflict_mode='skip' doesn't overwrite existing."""
        from Tools.memory_export import MemoryExporter

        export_path = create_test_export(format="json")

        # Setup mocks - existing database has one overlapping memory
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [sample_memories[0]]  # mem_001 exists
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pg.connect.return_value = mock_conn

        mock_store = MagicMock()
        mock_get_store.return_value = mock_store

        exporter = MemoryExporter()
        result = exporter.restore_from_backup(
            str(export_path),
            dry_run=True,  # Use dry-run to test logic without actual DB
            conflict_mode="skip"
        )

        assert "conflicts" in result
        # Should detect conflict with mem_001
        assert result["conflicts"] >= 1

    @patch("Tools.memory_export.psycopg2")
    @patch("Tools.memory_export.get_relationship_store")
    def test_restore_conflict_mode_update(self, mock_get_store, mock_pg,
                                          create_test_export, sample_memories):
        """Test restore with conflict_mode='update' overwrites existing."""
        from Tools.memory_export import MemoryExporter

        export_path = create_test_export(format="json")

        # Setup mocks
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [sample_memories[0]]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pg.connect.return_value = mock_conn

        mock_store = MagicMock()
        mock_get_store.return_value = mock_store

        exporter = MemoryExporter()
        result = exporter.restore_from_backup(
            str(export_path),
            dry_run=True,
            conflict_mode="update"
        )

        # In update mode, conflicts should be marked for update
        assert "would_update" in result


# ========================================================================
# Test Error Handling
# ========================================================================


class TestErrorHandling:
    """Test error handling in various scenarios."""

    @patch("Tools.memory_export.psycopg2")
    def test_database_connection_error(self, mock_pg, temp_export_dir):
        """Test error handling when database connection fails."""
        from Tools.memory_export import MemoryExporter
        import psycopg2

        # Mock connection failure
        mock_pg.connect.side_effect = Exception("Connection refused")

        exporter = MemoryExporter()

        with pytest.raises(Exception, match="Connection refused"):
            exporter.export_memories(output_path=str(temp_export_dir))

    @patch("Tools.memory_export.psycopg2")
    def test_invalid_export_path(self, mock_pg):
        """Test error handling for invalid export path."""
        from Tools.memory_export import MemoryExporter

        exporter = MemoryExporter()

        # Attempt to export to invalid path
        with pytest.raises(Exception):
            exporter.export_memories(output_path="/invalid/path/that/does/not/exist")


# ========================================================================
# Run Tests
# ========================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=Tools.memory_export", "--cov-report=term"])
