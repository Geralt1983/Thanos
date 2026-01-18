#!/usr/bin/env python3
"""
Comprehensive tests for StateStore and schema implementation.

Tests cover:
- Database initialization and schema creation
- CRUD operations for all entity types
- Health metrics storage and retrieval
- Schema versioning
- Edge cases: empty queries, duplicate IDs, null handling
"""

import json
import sqlite3
import tempfile
import uuid
from datetime import date, timedelta
from pathlib import Path

import pytest

# Import the StateStore and related models
from Tools.state_store.store import (
    StateStore,
    Task,
    Commitment,
    Idea,
    Note,
    BrainDump,
    HealthMetric,
    FocusArea,
    get_store,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test_state.db"


@pytest.fixture
def store(temp_db_path):
    """Create a StateStore instance with a temporary database."""
    return StateStore(db_path=temp_db_path)


@pytest.fixture
def populated_store(store):
    """Create a store with sample data for testing queries."""
    # Add tasks
    store.create_task(title="Work task 1", domain="work", priority="p0")
    store.create_task(title="Work task 2", domain="work", priority="p1")
    store.create_task(title="Personal task 1", domain="personal", priority="p2")
    store.create_task(
        title="Due task",
        domain="work",
        due_date=date.today() - timedelta(days=1),  # Overdue
    )

    # Add commitments
    store.create_commitment(
        title="Client deliverable",
        stakeholder="Client A",
        deadline=date.today() + timedelta(days=3),
        domain="work",
    )
    store.create_commitment(
        title="Friend meetup",
        stakeholder="John",
        deadline=date.today() + timedelta(days=7),
        domain="personal",
    )

    # Add ideas
    store.create_idea(content="Build a feature for X", domain="work", category="feature")
    store.create_idea(content="Learn new skill Y", domain="personal", category="learning")

    # Add brain dumps
    store.create_brain_dump(content="Random thought", context="work", category="thought")
    store.create_brain_dump(content="Task to do later", context="personal", category="task")

    # Add health metrics
    store.log_health_metric("sleep_score", 85.0, metric_date=date.today())
    store.log_health_metric("hrv", 45.5, metric_date=date.today())
    store.log_health_metric("readiness", 72.0, metric_date=date.today())

    return store


# ============================================================================
# Database Initialization Tests
# ============================================================================


class TestDatabaseInitialization:
    """Tests for database initialization and table creation."""

    def test_database_file_created(self, temp_db_path, store):
        """Test that database file is created."""
        assert temp_db_path.exists()

    def test_all_tables_created(self, store):
        """Test that all required tables are created."""
        expected_tables = [
            "schema_version",
            "tasks",
            "commitments",
            "ideas",
            "notes",
            "focus_areas",
            "health_metrics",
            "brain_dumps",
        ]

        with store._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [row[0] for row in cursor.fetchall()]

        for expected in expected_tables:
            assert expected in tables, f"Table {expected} should exist"

    def test_indexes_created(self, store):
        """Test that indexes are created for performance."""
        with store._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )
            indexes = [row[0] for row in cursor.fetchall()]

        # Check for key indexes
        assert any("tasks" in idx for idx in indexes), "Tasks table should have indexes"
        assert any("health" in idx for idx in indexes), "Health metrics should have indexes"

    def test_schema_version_recorded(self, store):
        """Test that schema version is recorded."""
        with store._get_connection() as conn:
            cursor = conn.execute("SELECT version FROM schema_version")
            version = cursor.fetchone()[0]

        assert version == store.SCHEMA_VERSION

    def test_multiple_init_idempotent(self, temp_db_path):
        """Test that initializing multiple times doesn't cause issues."""
        store1 = StateStore(db_path=temp_db_path)
        store1.create_task(title="Test task", domain="work")

        # Create another instance pointing to same DB
        store2 = StateStore(db_path=temp_db_path)
        tasks = store2.get_tasks()

        assert len(tasks) == 1
        assert tasks[0].title == "Test task"


# ============================================================================
# Task CRUD Tests
# ============================================================================


class TestTaskOperations:
    """Tests for task CRUD operations."""

    def test_create_task_minimal(self, store):
        """Test creating a task with minimal fields."""
        task_id = store.create_task(title="Simple task", domain="work")

        assert task_id is not None
        assert len(task_id) == 36  # UUID format

        task = store.get_task(task_id)
        assert task is not None
        assert task.title == "Simple task"
        assert task.domain == "work"
        assert task.status == "pending"

    def test_create_task_all_fields(self, store):
        """Test creating a task with all fields."""
        task_id = store.create_task(
            title="Full task",
            description="A complete task with all fields",
            priority="p0",
            due_date=date.today() + timedelta(days=7),
            domain="personal",
            source="brain_dump",
            source_id="bd_123",
            tags=["urgent", "home"],
            metadata={"estimated_time": 120},
        )

        task = store.get_task(task_id)
        assert task.title == "Full task"
        assert task.description == "A complete task with all fields"
        assert task.priority == "p0"
        assert task.domain == "personal"
        assert task.source == "brain_dump"
        assert task.source_id == "bd_123"
        assert task.tags == ["urgent", "home"]
        assert task.metadata == {"estimated_time": 120}

    def test_get_task_not_found(self, store):
        """Test getting a non-existent task returns None."""
        task = store.get_task("nonexistent-id")
        assert task is None

    def test_get_tasks_by_domain(self, populated_store):
        """Test filtering tasks by domain."""
        work_tasks = populated_store.get_tasks(domain="work")
        personal_tasks = populated_store.get_tasks(domain="personal")

        assert len(work_tasks) >= 2
        assert len(personal_tasks) >= 1
        assert all(t.domain == "work" for t in work_tasks)
        assert all(t.domain == "personal" for t in personal_tasks)

    def test_get_tasks_by_status(self, store):
        """Test filtering tasks by status."""
        store.create_task(title="Pending task", domain="work")
        task_id = store.create_task(title="Completed task", domain="work")
        store.complete_task(task_id)

        pending_tasks = store.get_tasks(status="pending")
        completed_tasks = store.get_tasks(status="completed", include_completed=True)

        assert len(pending_tasks) >= 1
        assert all(t.status == "pending" for t in pending_tasks)
        assert len(completed_tasks) >= 1

    def test_get_tasks_by_priority(self, populated_store):
        """Test filtering tasks by priority."""
        p0_tasks = populated_store.get_tasks(priority="p0")

        assert len(p0_tasks) >= 1
        assert all(t.priority == "p0" for t in p0_tasks)

    def test_update_task(self, store):
        """Test updating task fields."""
        task_id = store.create_task(title="Original", domain="work")

        result = store.update_task(
            task_id,
            title="Updated",
            priority="p1",
            description="New description",
        )

        assert result is True

        task = store.get_task(task_id)
        assert task.title == "Updated"
        assert task.priority == "p1"
        assert task.description == "New description"

    def test_update_task_not_found(self, store):
        """Test updating non-existent task."""
        result = store.update_task("nonexistent-id", title="New")
        assert result is False

    def test_complete_task(self, store):
        """Test completing a task sets status and completed_at."""
        task_id = store.create_task(title="To complete", domain="work")

        result = store.complete_task(task_id)
        assert result is True

        task = store.get_task(task_id)
        assert task.status == "completed"
        assert task.completed_at is not None

    def test_count_tasks(self, populated_store):
        """Test counting tasks with various filters."""
        total = populated_store.count_tasks()
        work_count = populated_store.count_tasks(domain="work")
        personal_count = populated_store.count_tasks(domain="personal")
        overdue_count = populated_store.count_tasks(overdue=True)

        assert total >= 4
        assert work_count >= 2
        assert personal_count >= 1
        assert overdue_count >= 1

    def test_exclude_completed_by_default(self, store):
        """Test that completed tasks are excluded by default."""
        store.create_task(title="Active", domain="work")
        completed_id = store.create_task(title="Done", domain="work")
        store.complete_task(completed_id)

        tasks = store.get_tasks()
        assert len(tasks) == 1
        assert tasks[0].title == "Active"

        all_tasks = store.get_tasks(include_completed=True)
        assert len(all_tasks) == 2


# ============================================================================
# Commitment CRUD Tests
# ============================================================================


class TestCommitmentOperations:
    """Tests for commitment CRUD operations."""

    def test_create_commitment(self, store):
        """Test creating a commitment."""
        commitment_id = store.create_commitment(
            title="Deliver report",
            stakeholder="Manager",
            deadline=date.today() + timedelta(days=5),
            priority="p1",
            domain="work",
        )

        assert commitment_id is not None

        commitments = store.get_commitments()
        assert len(commitments) == 1
        assert commitments[0].title == "Deliver report"
        assert commitments[0].stakeholder == "Manager"

    def test_get_commitments_by_stakeholder(self, populated_store):
        """Test filtering commitments by stakeholder."""
        commitments = populated_store.get_commitments(stakeholder="Client A")

        assert len(commitments) >= 1
        assert all(c.stakeholder == "Client A" for c in commitments)

    def test_get_commitments_due_within_days(self, populated_store):
        """Test filtering commitments by due date."""
        due_soon = populated_store.get_commitments(due_within_days=5)

        assert len(due_soon) >= 1
        for c in due_soon:
            if c.deadline:
                deadline_date = date.fromisoformat(c.deadline)
                assert deadline_date <= date.today() + timedelta(days=5)

    def test_complete_commitment(self, store):
        """Test completing a commitment."""
        commitment_id = store.create_commitment(
            title="Test commitment",
            stakeholder="Test",
            domain="work",
        )

        result = store.complete_commitment(commitment_id)
        assert result is True

        # Should not appear in active commitments
        active = store.get_commitments(status="active")
        assert all(c.id != commitment_id for c in active)

    def test_count_commitments(self, populated_store):
        """Test counting commitments."""
        total = populated_store.count_commitments()
        work = populated_store.count_commitments(domain="work")

        assert total >= 2
        assert work >= 1


# ============================================================================
# Idea CRUD Tests
# ============================================================================


class TestIdeaOperations:
    """Tests for idea CRUD operations."""

    def test_create_idea(self, store):
        """Test creating an idea."""
        idea_id = store.create_idea(
            content="Build a mobile app",
            category="feature",
            domain="work",
        )

        assert idea_id is not None

        ideas = store.get_ideas()
        assert len(ideas) == 1
        assert ideas[0].content == "Build a mobile app"

    def test_get_ideas_by_category(self, populated_store):
        """Test filtering ideas by category."""
        feature_ideas = populated_store.get_ideas(category="feature")

        assert len(feature_ideas) >= 1
        assert all(i.category == "feature" for i in feature_ideas)

    def test_promote_idea_to_task(self, store):
        """Test promoting an idea to a task."""
        idea_id = store.create_idea(
            content="Implement new feature",
            domain="work",
        )

        task_id = store.promote_idea_to_task(
            idea_id,
            title="Feature Implementation",
            priority="p1",
        )

        assert task_id is not None

        # Check idea is marked as promoted
        ideas = store.get_ideas(status="promoted")
        assert len(ideas) == 1
        assert ideas[0].promoted_to_task_id == task_id

        # Check task was created
        task = store.get_task(task_id)
        assert task is not None
        assert task.title == "Feature Implementation"

    def test_promote_nonexistent_idea(self, store):
        """Test promoting a non-existent idea returns None."""
        result = store.promote_idea_to_task("nonexistent-id")
        assert result is None


# ============================================================================
# Brain Dump CRUD Tests
# ============================================================================


class TestBrainDumpOperations:
    """Tests for brain dump CRUD operations."""

    def test_create_brain_dump(self, store):
        """Test creating a brain dump."""
        dump_id = store.create_brain_dump(
            content="Quick thought I had",
            category="thought",
            context="work",
            source="telegram",
        )

        assert dump_id is not None

        dumps = store.get_brain_dumps()
        assert len(dumps) == 1
        assert dumps[0].content == "Quick thought I had"
        assert dumps[0].processed is False

    def test_get_unprocessed_brain_dumps(self, store):
        """Test getting unprocessed brain dumps."""
        store.create_brain_dump(content="Unprocessed 1", context="work")
        store.create_brain_dump(content="Unprocessed 2", context="personal")
        dump_id = store.create_brain_dump(content="To archive", context="work")
        store.archive_brain_dump(dump_id)

        unprocessed = store.get_brain_dumps(processed=False)
        assert len(unprocessed) == 2

    def test_archive_brain_dump(self, store):
        """Test archiving a brain dump."""
        dump_id = store.create_brain_dump(content="Archive me", context="work")

        result = store.archive_brain_dump(dump_id)
        assert result is True

        # Should not appear in non-archived query
        dumps = store.get_brain_dumps(archived=False)
        assert all(d.id != dump_id for d in dumps)

    def test_filter_brain_dumps_by_context(self, populated_store):
        """Test filtering brain dumps by context."""
        work_dumps = populated_store.get_brain_dumps(context="work")

        assert len(work_dumps) >= 1
        assert all(d.context == "work" for d in work_dumps)

    def test_count_brain_dumps(self, populated_store):
        """Test counting brain dumps."""
        unprocessed = populated_store.count_brain_dumps(processed=False)
        total = populated_store.count_brain_dumps(archived=True)

        assert unprocessed >= 2
        assert total >= 2


# ============================================================================
# Health Metrics Tests
# ============================================================================


class TestHealthMetricOperations:
    """Tests for health metric operations."""

    def test_log_health_metric(self, store):
        """Test logging a health metric."""
        metric_id = store.log_health_metric(
            metric_type="sleep_score",
            value=85.0,
            metric_date=date.today(),
            source="oura",
        )

        assert metric_id is not None

        metrics = store.get_health_metrics(metric_date=date.today())
        assert len(metrics) == 1
        assert metrics[0].metric_type == "sleep_score"
        assert metrics[0].value == 85.0

    def test_log_metric_with_metadata(self, store):
        """Test logging metric with metadata."""
        store.log_health_metric(
            metric_type="hrv",
            value=42.5,
            metadata={"rmssd": 42.5, "sdnn": 65.2},
        )

        metrics = store.get_health_metrics(metric_type="hrv")
        assert len(metrics) == 1
        assert metrics[0].metadata["rmssd"] == 42.5

    def test_get_metrics_by_type(self, populated_store):
        """Test filtering metrics by type."""
        sleep_metrics = populated_store.get_health_metrics(metric_type="sleep_score")

        assert len(sleep_metrics) >= 1
        assert all(m.metric_type == "sleep_score" for m in sleep_metrics)

    def test_get_metrics_by_date_range(self, store):
        """Test filtering metrics by date range."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)

        store.log_health_metric("sleep_score", 80.0, metric_date=yesterday)
        store.log_health_metric("sleep_score", 85.0, metric_date=today)

        recent = store.get_health_metrics(start_date=week_ago, end_date=today)
        assert len(recent) >= 2

    def test_upsert_metric_same_date_type(self, store):
        """Test that logging same metric type for same date updates existing."""
        today = date.today()

        store.log_health_metric("sleep_score", 80.0, metric_date=today)
        store.log_health_metric("sleep_score", 85.0, metric_date=today)  # Update

        metrics = store.get_health_metrics(metric_date=today, metric_type="sleep_score")
        assert len(metrics) == 1
        assert metrics[0].value == 85.0


# ============================================================================
# Focus Area Tests
# ============================================================================


class TestFocusAreaOperations:
    """Tests for focus area operations."""

    def test_set_focus(self, store):
        """Test setting a focus area."""
        focus_id = store.set_focus(
            title="Q1 Goals",
            description="Focus on key deliverables",
            domain="work",
        )

        assert focus_id is not None

        active = store.get_active_focus()
        assert len(active) == 1
        assert active[0].title == "Q1 Goals"
        assert active[0].is_active is True

    def test_setting_focus_deactivates_previous(self, store):
        """Test that setting new focus deactivates previous in same domain."""
        focus1_id = store.set_focus(title="First focus", domain="work")
        focus2_id = store.set_focus(title="Second focus", domain="work")

        active = store.get_active_focus(domain="work")
        assert len(active) == 1
        assert active[0].id == focus2_id
        assert active[0].title == "Second focus"

    def test_separate_focus_per_domain(self, store):
        """Test that different domains can have separate focus areas."""
        store.set_focus(title="Work focus", domain="work")
        store.set_focus(title="Personal focus", domain="personal")

        all_active = store.get_active_focus()
        work_active = store.get_active_focus(domain="work")
        personal_active = store.get_active_focus(domain="personal")

        assert len(all_active) == 2
        assert len(work_active) == 1
        assert len(personal_active) == 1


# ============================================================================
# Note Operations Tests
# ============================================================================


class TestNoteOperations:
    """Tests for note CRUD operations."""

    def test_create_note(self, store):
        """Test creating a note."""
        note_id = store.create_note(
            content="Meeting notes from standup",
            title="Daily Standup",
            category="meeting",
            domain="work",
            tags=["team", "daily"],
        )

        assert note_id is not None

    def test_search_notes(self, store):
        """Test searching notes."""
        store.create_note(content="Python programming tips", title="Python Notes")
        store.create_note(content="JavaScript best practices", title="JS Notes")

        results = store.search_notes("Python")
        assert len(results) == 1
        assert "Python" in results[0].title or "Python" in results[0].content

    def test_search_notes_empty_query(self, store):
        """Test searching notes with empty result."""
        store.create_note(content="Some content", title="Test")

        results = store.search_notes("nonexistent_xyz")
        assert len(results) == 0


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_database_queries(self, store):
        """Test queries on empty database return empty lists."""
        assert store.get_tasks() == []
        assert store.get_commitments() == []
        assert store.get_ideas() == []
        assert store.get_brain_dumps() == []
        assert store.get_health_metrics() == []
        assert store.get_active_focus() == []

    def test_count_on_empty_database(self, store):
        """Test counts on empty database return zero."""
        assert store.count_tasks() == 0
        assert store.count_commitments() == 0
        assert store.count_brain_dumps() == 0

    def test_null_optional_fields(self, store):
        """Test that null optional fields are handled correctly."""
        task_id = store.create_task(
            title="Minimal task",
            domain="work",
            # All other fields default to None/null
        )

        task = store.get_task(task_id)
        assert task.description is None
        assert task.priority is None
        assert task.due_date is None
        assert task.tags is None
        assert task.metadata is None

    def test_empty_string_content(self, store):
        """Test handling of empty string content."""
        # This should still work - empty string is valid
        dump_id = store.create_brain_dump(content="", context="work")

        dumps = store.get_brain_dumps()
        assert len(dumps) == 1
        assert dumps[0].content == ""

    def test_unicode_content(self, store):
        """Test handling of unicode content."""
        task_id = store.create_task(
            title="Task with unicode - cafe",
            description="Some emojis here",
            domain="work",
        )

        task = store.get_task(task_id)
        assert task.title == "Task with unicode - cafe"

    def test_json_metadata_complex(self, store):
        """Test complex JSON metadata storage."""
        metadata = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "mixed": {"items": ["a", "b"], "count": 2},
        }

        task_id = store.create_task(
            title="Complex metadata",
            domain="work",
            metadata=metadata,
        )

        task = store.get_task(task_id)
        assert task.metadata == metadata

    def test_large_limit_query(self, store):
        """Test query with very large limit."""
        # Should not cause issues
        tasks = store.get_tasks(limit=10000)
        assert tasks == []

    def test_zero_limit_query(self, store):
        """Test query with zero limit."""
        store.create_task(title="Test", domain="work")
        tasks = store.get_tasks(limit=0)
        assert len(tasks) == 0

    def test_concurrent_db_access(self, temp_db_path):
        """Test that multiple store instances can access same database."""
        store1 = StateStore(db_path=temp_db_path)
        store2 = StateStore(db_path=temp_db_path)

        task_id = store1.create_task(title="From store 1", domain="work")

        # Store 2 should see the task
        task = store2.get_task(task_id)
        assert task is not None
        assert task.title == "From store 1"

    def test_special_characters_in_text(self, store):
        """Test special characters don't cause SQL issues."""
        task_id = store.create_task(
            title="Task with 'quotes' and \"double quotes\"",
            description="Also has; semicolons and -- dashes",
            domain="work",
        )

        task = store.get_task(task_id)
        assert "quotes" in task.title
        assert "semicolons" in task.description

    def test_update_with_no_valid_fields(self, store):
        """Test update with only invalid field names."""
        task_id = store.create_task(title="Test", domain="work")

        # These fields don't exist, should return False
        result = store.update_task(task_id, invalid_field="value", another_invalid="x")
        assert result is False

    def test_very_long_content(self, store):
        """Test handling of very long content."""
        long_content = "A" * 10000

        note_id = store.create_note(content=long_content, title="Long note")

        results = store.search_notes("A" * 100)  # Search substring
        assert len(results) == 1


# ============================================================================
# Export and Summary Tests
# ============================================================================


class TestExportSummary:
    """Tests for export and summary functionality."""

    def test_export_summary_empty(self, store):
        """Test export summary on empty database."""
        summary = store.export_summary()

        assert "exported_at" in summary
        assert summary["tasks"]["total"] == 0
        assert summary["commitments"]["active"] == 0
        assert summary["brain_dumps"]["unprocessed"] == 0
        assert summary["focus_areas"] == []

    def test_export_summary_populated(self, populated_store):
        """Test export summary with data."""
        summary = populated_store.export_summary()

        assert summary["tasks"]["total"] >= 4
        assert summary["tasks"]["work"] >= 2
        assert summary["tasks"]["personal"] >= 1
        assert summary["commitments"]["active"] >= 2
        assert summary["brain_dumps"]["unprocessed"] >= 2


# ============================================================================
# Singleton Pattern Tests
# ============================================================================


class TestSingletonPattern:
    """Tests for the module-level singleton pattern."""

    def test_get_store_singleton(self, temp_db_path):
        """Test that get_store returns same instance."""
        # Reset the module-level instance
        import Tools.state_store.store as store_module
        store_module._store_instance = None

        store1 = get_store(temp_db_path)
        store2 = get_store()  # Should return same instance

        assert store1 is store2

    def test_get_store_new_path_creates_new(self, tmp_path):
        """Test that specifying new path creates new instance."""
        import Tools.state_store.store as store_module
        store_module._store_instance = None

        path1 = tmp_path / "db1.db"
        path2 = tmp_path / "db2.db"

        store1 = get_store(path1)
        store2 = get_store(path2)  # Different path, new instance

        assert store1 is not store2


# ============================================================================
# Schema Versioning Tests
# ============================================================================


class TestSchemaVersioning:
    """Tests for schema versioning."""

    def test_schema_version_constant(self, store):
        """Test that SCHEMA_VERSION constant is set."""
        assert hasattr(store, "SCHEMA_VERSION")
        assert store.SCHEMA_VERSION == 2

    def test_schema_version_in_database(self, store):
        """Test that schema version is recorded in database."""
        with store._get_connection() as conn:
            cursor = conn.execute(
                "SELECT version, applied_at FROM schema_version ORDER BY version DESC LIMIT 1"
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == store.SCHEMA_VERSION
        assert row[1] is not None  # applied_at timestamp


# ============================================================================
# Data Model Tests
# ============================================================================


class TestDataModels:
    """Tests for data model classes."""

    def test_task_dataclass_defaults(self):
        """Test Task dataclass has correct defaults."""
        task = Task(id="test-id", title="Test")

        assert task.status == "pending"
        assert task.domain == "work"
        assert task.source == "manual"

    def test_commitment_dataclass_defaults(self):
        """Test Commitment dataclass has correct defaults."""
        commitment = Commitment(id="test-id", title="Test")

        assert commitment.status == "active"
        assert commitment.domain == "work"

    def test_brain_dump_dataclass_defaults(self):
        """Test BrainDump dataclass has correct defaults."""
        dump = BrainDump(id="test-id", content="Test")

        assert dump.content_type == "text"
        assert dump.source == "manual"
        assert dump.processed is False
        assert dump.archived is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
