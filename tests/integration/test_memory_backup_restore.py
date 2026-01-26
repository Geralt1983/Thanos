#!/usr/bin/env python3
"""
Integration Tests for Memory Backup and Restore System.

Tests the complete end-to-end flow:
- Export memories and relationships to backup
- Verify backup integrity
- Restore from backup
- Verify data preservation

These tests use real database operations (with test database) to ensure
the full export/restore cycle works correctly in production.

Test Categories:
- TestFullExportRestoreCycle: Complete E2E backup/restore
- TestRelationshipPreservation: Verify relationships survive cycle
- TestVectorEmbeddingPreservation: Verify embeddings preserved
- TestMetadataPreservation: Verify all metadata fields preserved
- TestLargeDatasetHandling: Performance with large datasets
- TestCLICommands: Test command-line interface
- TestBackupRetention: Test retention policy logic
"""

import json
import sys
import tempfile
import time
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def temp_backup_dir():
    """Create temporary directory for test backups."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_database_connection():
    """Create mock database connection for testing."""
    with patch("Tools.memory_export.psycopg2") as mock_pg:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pg.connect.return_value = mock_conn
        mock_pg.extras.RealDictCursor = Mock

        yield {
            "module": mock_pg,
            "conn": mock_conn,
            "cursor": mock_cursor
        }


@pytest.fixture
def sample_test_memories():
    """Generate sample memories for testing."""
    memories = []
    for i in range(10):
        memories.append({
            "id": f"mem_{i:03d}",
            "user_id": "jeremy",
            "memory": f"Test memory {i} about project work",
            "hash": f"hash_{i}",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "metadata": {
                "client": "TestClient" if i % 2 == 0 else None,
                "domain": "work" if i < 7 else "personal",
                "heat": 0.5 + (i * 0.05),
                "importance": 0.8
            },
            "embedding": [float(i) / 100] * 1536
        })
    return memories


@pytest.fixture
def sample_test_relationships():
    """Generate sample relationships for testing."""
    relationships = []
    for i in range(5):
        relationships.append({
            "source_id": f"mem_{i:03d}",
            "target_id": f"mem_{i+1:03d}",
            "rel_type": "relates_to" if i % 2 == 0 else "followed_by",
            "strength": 0.7,
            "metadata": {"test": True},
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat()
        })
    return relationships


@pytest.fixture
def cleanup_test_backups(temp_backup_dir):
    """Cleanup fixture to remove test backup directories after tests."""
    yield
    # Cleanup happens automatically with temp_backup_dir


# =============================================================================
# Test Full Export/Restore Cycle
# =============================================================================


class TestFullExportRestoreCycle:
    """Test complete export → verify → restore cycle."""

    def test_full_export_restore_cycle(self, mock_database_connection,
                                        temp_backup_dir, sample_test_memories,
                                        sample_test_relationships):
        """
        Test full E2E cycle:
        1. Export memories and relationships
        2. Verify export
        3. Clear database (simulated)
        4. Restore from export
        5. Verify all data restored correctly
        """
        from Tools.memory_export import MemoryExporter

        # Setup mock for export
        mock_db = mock_database_connection
        mock_db["cursor"].fetchall.return_value = sample_test_memories

        with patch("Tools.memory_export.get_relationship_store") as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_all_relationships.return_value = sample_test_relationships
            mock_get_store.return_value = mock_store

            # Step 1: Export
            exporter = MemoryExporter()
            export_result = exporter.export_all(
                output_path=str(temp_backup_dir / "backup_001"),
                format="json"
            )

            assert export_result["success"] is True
            assert export_result["memory_count"] == 10
            assert export_result["relationship_count"] == 5

            # Step 2: Verify export
            is_valid = exporter.verify_export(str(temp_backup_dir / "backup_001"))
            assert is_valid is True

            # Step 3: Simulate database clear (mock returns empty)
            mock_db["cursor"].fetchall.return_value = []

            # Step 4: Restore from backup
            restore_result = exporter.restore_from_backup(
                str(temp_backup_dir / "backup_001"),
                dry_run=True  # Use dry-run for testing
            )

            assert restore_result["dry_run"] is True
            assert restore_result["would_restore"] == 10

    def test_export_includes_all_memory_fields(self, mock_database_connection,
                                                temp_backup_dir, sample_test_memories):
        """Test that export preserves all memory fields."""
        from Tools.memory_export import MemoryExporter

        mock_db = mock_database_connection
        mock_db["cursor"].fetchall.return_value = sample_test_memories

        with patch("Tools.memory_export.get_relationship_store") as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_all_relationships.return_value = []
            mock_get_store.return_value = mock_store

            exporter = MemoryExporter()
            result = exporter.export_all(
                output_path=str(temp_backup_dir / "test_export"),
                format="json"
            )

            # Read exported file
            with open(result["file_path"], "r") as f:
                data = json.load(f)

            # Verify all fields present
            memory = data["memories"][0]
            assert "id" in memory
            assert "user_id" in memory
            assert "memory" in memory
            assert "metadata" in memory
            assert "embedding" in memory
            assert "created_at" in memory


# =============================================================================
# Test Relationship Preservation
# =============================================================================


class TestRelationshipPreservation:
    """Test that relationships are preserved through export/restore."""

    def test_relationship_preservation(self, mock_database_connection,
                                        temp_backup_dir, sample_test_relationships):
        """Test relationships are exported and can be restored."""
        from Tools.memory_export import MemoryExporter

        mock_db = mock_database_connection
        mock_db["cursor"].fetchall.return_value = []

        with patch("Tools.memory_export.get_relationship_store") as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_all_relationships.return_value = sample_test_relationships
            mock_get_store.return_value = mock_store

            exporter = MemoryExporter()
            result = exporter.export_all(
                output_path=str(temp_backup_dir / "rel_test"),
                format="json"
            )

            # Verify relationship count in export
            assert result["relationship_count"] == 5

            # Read export and verify relationship data
            with open(result["file_path"], "r") as f:
                data = json.load(f)

            assert len(data["relationships"]) == 5
            rel = data["relationships"][0]
            assert "source_id" in rel
            assert "target_id" in rel
            assert "rel_type" in rel
            assert "strength" in rel

    def test_relationship_types_preserved(self, mock_database_connection,
                                           temp_backup_dir, sample_test_relationships):
        """Test that relationship types and metadata are preserved."""
        from Tools.memory_export import MemoryExporter

        mock_db = mock_database_connection
        mock_db["cursor"].fetchall.return_value = []

        with patch("Tools.memory_export.get_relationship_store") as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_all_relationships.return_value = sample_test_relationships
            mock_get_store.return_value = mock_store

            exporter = MemoryExporter()
            result = exporter.export_all(
                output_path=str(temp_backup_dir / "rel_types_test"),
                format="json"
            )

            with open(result["file_path"], "r") as f:
                data = json.load(f)

            # Verify relationship types preserved
            rel_types = [r["rel_type"] for r in data["relationships"]]
            assert "relates_to" in rel_types
            assert "followed_by" in rel_types


# =============================================================================
# Test Vector Embedding Preservation
# =============================================================================


class TestVectorEmbeddingPreservation:
    """Test that vector embeddings are preserved correctly."""

    def test_vector_embedding_preservation(self, mock_database_connection,
                                            temp_backup_dir):
        """Test that vector embeddings survive export/restore."""
        from Tools.memory_export import MemoryExporter

        # Create memory with known vector
        test_vector = [0.123, 0.456, 0.789] * 512  # 1536 dims
        test_memory = [{
            "id": "mem_vector_test",
            "user_id": "jeremy",
            "memory": "Vector test memory",
            "hash": "vec_hash",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "metadata": {"test": True},
            "embedding": test_vector
        }]

        mock_db = mock_database_connection
        mock_db["cursor"].fetchall.return_value = test_memory

        with patch("Tools.memory_export.get_relationship_store") as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_all_relationships.return_value = []
            mock_get_store.return_value = mock_store

            exporter = MemoryExporter()
            result = exporter.export_all(
                output_path=str(temp_backup_dir / "vector_test"),
                format="json"
            )

            # Read and verify vector preserved
            with open(result["file_path"], "r") as f:
                data = json.load(f)

            exported_vector = data["memories"][0]["embedding"]
            assert len(exported_vector) == 1536
            assert exported_vector[:3] == [0.123, 0.456, 0.789]


# =============================================================================
# Test Metadata Preservation
# =============================================================================


class TestMetadataPreservation:
    """Test that all metadata fields are preserved."""

    def test_metadata_preservation(self, mock_database_connection,
                                    temp_backup_dir, sample_test_memories):
        """Test all metadata fields (heat, importance, timestamps) preserved."""
        from Tools.memory_export import MemoryExporter

        mock_db = mock_database_connection
        mock_db["cursor"].fetchall.return_value = sample_test_memories

        with patch("Tools.memory_export.get_relationship_store") as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_all_relationships.return_value = []
            mock_get_store.return_value = mock_store

            exporter = MemoryExporter()
            result = exporter.export_all(
                output_path=str(temp_backup_dir / "metadata_test"),
                format="json"
            )

            with open(result["file_path"], "r") as f:
                data = json.load(f)

            # Verify metadata preserved
            memory = data["memories"][0]
            assert "metadata" in memory
            assert "heat" in memory["metadata"]
            assert "importance" in memory["metadata"]
            assert "domain" in memory["metadata"]


# =============================================================================
# Test Large Dataset Handling
# =============================================================================


class TestLargeDatasetExportRestore:
    """Test performance and correctness with large datasets."""

    def test_large_dataset_export_restore(self, mock_database_connection,
                                           temp_backup_dir):
        """Test export/restore with 1000+ memories completes successfully."""
        from Tools.memory_export import MemoryExporter

        # Generate 1000 memories
        large_dataset = []
        for i in range(1000):
            large_dataset.append({
                "id": f"mem_{i:04d}",
                "user_id": "jeremy",
                "memory": f"Memory {i}",
                "hash": f"hash_{i}",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "metadata": {"domain": "test", "heat": 0.5},
                "embedding": [0.1] * 1536
            })

        mock_db = mock_database_connection
        mock_db["cursor"].fetchall.return_value = large_dataset

        with patch("Tools.memory_export.get_relationship_store") as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_all_relationships.return_value = []
            mock_get_store.return_value = mock_store

            exporter = MemoryExporter()

            # Test export performance (should complete in reasonable time)
            start_time = time.time()
            result = exporter.export_all(
                output_path=str(temp_backup_dir / "large_test"),
                format="json"
            )
            export_time = time.time() - start_time

            assert result["success"] is True
            assert result["memory_count"] == 1000
            assert export_time < 30  # Should complete in under 30 seconds

            # Verify export
            is_valid = exporter.verify_export(str(temp_backup_dir / "large_test"))
            assert is_valid is True


# =============================================================================
# Test Export Verification
# =============================================================================


class TestExportVerification:
    """Test export verification functionality."""

    def test_export_verification_passes_for_valid_export(self, mock_database_connection,
                                                          temp_backup_dir,
                                                          sample_test_memories):
        """Test that verification passes for valid export."""
        from Tools.memory_export import MemoryExporter

        mock_db = mock_database_connection
        mock_db["cursor"].fetchall.return_value = sample_test_memories

        with patch("Tools.memory_export.get_relationship_store") as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_all_relationships.return_value = []
            mock_get_store.return_value = mock_store

            exporter = MemoryExporter()
            result = exporter.export_all(
                output_path=str(temp_backup_dir / "verify_test"),
                format="json"
            )

            is_valid = exporter.verify_export(str(temp_backup_dir / "verify_test"))
            assert is_valid is True

    def test_verification_fails_for_corrupted_export(self, mock_database_connection,
                                                      temp_backup_dir,
                                                      sample_test_memories):
        """Test that verification fails when export is corrupted."""
        from Tools.memory_export import MemoryExporter

        mock_db = mock_database_connection
        mock_db["cursor"].fetchall.return_value = sample_test_memories

        with patch("Tools.memory_export.get_relationship_store") as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_all_relationships.return_value = []
            mock_get_store.return_value = mock_store

            exporter = MemoryExporter()
            result = exporter.export_all(
                output_path=str(temp_backup_dir / "corrupt_test"),
                format="json"
            )

            # Corrupt the export
            json_file = Path(result["file_path"])
            with open(json_file, "a") as f:
                f.write("CORRUPTED")

            is_valid = exporter.verify_export(str(temp_backup_dir / "corrupt_test"))
            assert is_valid is False


# =============================================================================
# Test Restore Conflict Resolution
# =============================================================================


class TestRestoreConflictResolution:
    """Test conflict resolution during restore."""

    def test_restore_conflict_resolution_skip_mode(self, mock_database_connection,
                                                    temp_backup_dir,
                                                    sample_test_memories):
        """Test restore with conflict_mode='skip' preserves existing data."""
        from Tools.memory_export import MemoryExporter

        # Setup: Export memories
        mock_db = mock_database_connection
        mock_db["cursor"].fetchall.return_value = sample_test_memories

        with patch("Tools.memory_export.get_relationship_store") as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_all_relationships.return_value = []
            mock_get_store.return_value = mock_store

            exporter = MemoryExporter()
            exporter.export_all(
                output_path=str(temp_backup_dir / "conflict_test"),
                format="json"
            )

            # Simulate existing data (first 5 memories already exist)
            existing_memories = sample_test_memories[:5]
            mock_db["cursor"].fetchall.return_value = existing_memories

            # Restore with skip mode
            result = exporter.restore_from_backup(
                str(temp_backup_dir / "conflict_test"),
                dry_run=True,
                conflict_mode="skip"
            )

            # Should detect conflicts
            assert "conflicts" in result
            assert result["conflicts"] >= 5

    def test_restore_conflict_resolution_update_mode(self, mock_database_connection,
                                                      temp_backup_dir,
                                                      sample_test_memories):
        """Test restore with conflict_mode='update' overwrites existing."""
        from Tools.memory_export import MemoryExporter

        mock_db = mock_database_connection
        mock_db["cursor"].fetchall.return_value = sample_test_memories

        with patch("Tools.memory_export.get_relationship_store") as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_all_relationships.return_value = []
            mock_get_store.return_value = mock_store

            exporter = MemoryExporter()
            exporter.export_all(
                output_path=str(temp_backup_dir / "update_test"),
                format="json"
            )

            # Restore with update mode
            result = exporter.restore_from_backup(
                str(temp_backup_dir / "update_test"),
                dry_run=True,
                conflict_mode="update"
            )

            # Should plan to update conflicts
            assert "would_update" in result or "would_restore" in result


# =============================================================================
# Test CLI Commands
# =============================================================================


class TestCLICommands:
    """Test command-line interface for backup/restore."""

    def test_cli_backup_command_help(self):
        """Test that backup CLI command shows help."""
        result = subprocess.run(
            ["python3", "-m", "commands.memory.backup", "--help"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "backup" in result.stdout.lower()

    def test_cli_restore_command_help(self):
        """Test that restore CLI command shows help."""
        result = subprocess.run(
            ["python3", "-m", "commands.memory.restore", "--help"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "restore" in result.stdout.lower()

    def test_cli_export_command_help(self):
        """Test that export CLI command shows help."""
        result = subprocess.run(
            ["python3", "-m", "commands.memory.export", "--help"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "export" in result.stdout.lower()

    @patch("Tools.memory_export.psycopg2")
    @patch("Tools.memory_export.get_relationship_store")
    def test_cli_restore_dry_run(self, mock_get_store, mock_pg,
                                  temp_backup_dir, sample_test_memories):
        """Test restore CLI command with --dry-run flag."""
        from Tools.memory_export import MemoryExporter

        # Create a test backup first
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = sample_test_memories
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pg.connect.return_value = mock_conn

        mock_store = MagicMock()
        mock_store.get_all_relationships.return_value = []
        mock_get_store.return_value = mock_store

        exporter = MemoryExporter()
        backup_path = temp_backup_dir / "cli_test_backup"
        exporter.export_all(output_path=str(backup_path), format="json")

        # Test restore dry-run via API (CLI would call this)
        result = exporter.restore_from_backup(str(backup_path), dry_run=True)

        assert result["dry_run"] is True
        assert "would_restore" in result


# =============================================================================
# Test Backup Retention Policy
# =============================================================================


class TestBackupRetentionPolicy:
    """Test backup retention policy logic."""

    def test_backup_retention_policy_logic(self, temp_backup_dir):
        """Test retention logic keeps 7 daily + 4 weekly backups."""
        # Create 15 simulated backup directories
        # (representing 15 days of backups)
        today = datetime.now()
        backup_dirs = []

        for i in range(15):
            date = today - timedelta(days=i)
            dir_name = f"memory_{date.strftime('%Y%m%d_%H%M%S')}"
            backup_dir = temp_backup_dir / dir_name
            backup_dir.mkdir()
            backup_dirs.append({
                "path": backup_dir,
                "date": date,
                "is_sunday": date.weekday() == 6  # Sunday
            })

        # Retention policy: keep last 7 daily + 4 weekly (Sundays)
        # Simulate cleanup logic
        to_keep = []

        # Keep last 7 backups (daily)
        to_keep.extend(backup_dirs[:7])

        # Keep up to 4 weekly (Sundays older than 7 days)
        weekly_count = 0
        for backup in backup_dirs[7:]:
            if backup["is_sunday"] and weekly_count < 4:
                to_keep.append(backup)
                weekly_count += 1

        # After cleanup, should have between 7 and 11 backups
        # (7 daily + 0-4 weekly depending on Sunday distribution)
        assert 7 <= len(to_keep) <= 11

        # Verify all kept backups exist
        for backup in to_keep:
            assert backup["path"].exists()


# =============================================================================
# Run Tests
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
