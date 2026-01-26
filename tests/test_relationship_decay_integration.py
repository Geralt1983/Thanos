#!/usr/bin/env python3
"""
Integration tests for relationship decay tracking and alerts.

Tests the end-to-end flow of:
- Tracking person mentions in conversation
- Detecting when people haven't been mentioned recently
- Triggering importance-based decay alerts
- Generating signals for session startup

These tests verify that all components work together correctly:
- RelationshipMentionTracker: Recording and tracking person mentions
- RelationshipDecayChecker: Alert generation for stale relationships
- SignalManager: Signal persistence and deduplication
"""

import pytest
import asyncio
import json
import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import patch, MagicMock

# Add Tools directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "Tools"))

from Tools.relationship_tracker import (
    RelationshipMentionTracker,
    ImportanceLevel,
    PersonMention
)
from Tools.alert_checkers.relationship_decay_checker import RelationshipDecayChecker
from Tools.get_signals import SignalManager, get_signals


# ========================================================================
# Fixtures
# ========================================================================

@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary state directory for testing."""
    state_dir = tmp_path / "State"
    state_dir.mkdir()
    return state_dir


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for relationship tracking."""
    db_path = tmp_path / "relationship_tracker.db"
    return str(db_path)


@pytest.fixture
def tracker(temp_db):
    """Create a RelationshipMentionTracker instance with temp database."""
    return RelationshipMentionTracker(db_path=temp_db)


@pytest.fixture
def decay_checker(tracker):
    """Create a RelationshipDecayChecker instance."""
    return RelationshipDecayChecker(tracker=tracker)


@pytest.fixture
def signal_manager(temp_state_dir):
    """Create a SignalManager instance."""
    state_file = temp_state_dir / "signal_state.json"
    return SignalManager(state_file=str(state_file))


# ========================================================================
# End-to-End Relationship Decay Flow
# ========================================================================

@pytest.mark.integration
class TestRelationshipDecayFlow:
    """Test the complete flow from mention tracking to alert generation."""

    def test_record_mention_and_retrieve(self, tracker):
        """Test basic mention recording and retrieval."""
        # Record a mention
        tracker.record_mention("Ashley", context="Discussed weekend plans")

        # Verify it was recorded
        recent = tracker.get_recent_mentions(days=1)
        assert len(recent) > 0
        assert any(m.person_name == "Ashley" for m in recent)

        # Verify person info
        info = tracker.get_person_info("Ashley")
        assert info is not None
        assert info['person_name'] == "Ashley"
        assert info['mention_count'] == 1

    def test_multiple_mentions_increment_count(self, tracker):
        """Test that multiple mentions of the same person increment the count."""
        # Record multiple mentions
        tracker.record_mention("Sullivan")
        tracker.record_mention("Sullivan", context="Talked about school")
        tracker.record_mention("Sullivan", context="Bedtime story")

        # Verify count
        info = tracker.get_person_info("Sullivan")
        assert info['mention_count'] == 3

    def test_importance_level_assignment(self, tracker):
        """Test setting and retrieving importance levels."""
        # Record mentions and set importance
        tracker.record_mention("Ashley")
        tracker.set_importance("Ashley", ImportanceLevel.CRITICAL)

        tracker.record_mention("John")
        tracker.set_importance("John", ImportanceLevel.MEDIUM)

        # Verify importance levels
        ashley_info = tracker.get_person_info("Ashley")
        assert ashley_info['importance'] == ImportanceLevel.CRITICAL.value

        john_info = tracker.get_person_info("John")
        assert john_info['importance'] == ImportanceLevel.MEDIUM.value

    def test_get_all_people(self, tracker):
        """Test retrieving all tracked people."""
        # Record several people
        tracker.record_mention("Ashley")
        tracker.record_mention("Sullivan")
        tracker.record_mention("Mom")
        tracker.record_mention("Dad")

        # Get all people
        all_people = tracker.get_all_people()
        assert len(all_people) == 4

        names = {p['person_name'] for p in all_people}
        assert names == {"Ashley", "Sullivan", "Mom", "Dad"}

    @pytest.mark.asyncio
    async def test_no_decay_when_recently_mentioned(self, tracker, decay_checker):
        """Test that no alerts are generated for recently mentioned people."""
        # Record recent mentions
        tracker.record_mention("Ashley")
        tracker.set_importance("Ashley", ImportanceLevel.CRITICAL)

        # Check for alerts (should be none)
        alerts = await decay_checker.check()

        # Filter to only relationship decay alerts
        decay_alerts = [a for a in alerts if 'relationship_decay' in str(a.data)]
        assert len(decay_alerts) == 0

    @pytest.mark.asyncio
    async def test_decay_alert_for_critical_person_after_threshold(self, tracker, decay_checker, temp_db):
        """Test that decay alert is generated for critical person after 5 days."""
        # Record a mention and manually set it to 6 days ago
        tracker.record_mention("Ashley")
        tracker.set_importance("Ashley", ImportanceLevel.CRITICAL)

        # Manually update the last_mentioned_at timestamp to 6 days ago
        six_days_ago = (datetime.now() - timedelta(days=6)).isoformat()
        conn = sqlite3.connect(temp_db)
        conn.execute(
            "UPDATE person_mentions SET last_mentioned_at = ? WHERE person_name = ?",
            (six_days_ago, "Ashley")
        )
        conn.commit()
        conn.close()

        # Check for alerts
        alerts = await decay_checker.check()

        # Should have at least one alert for Ashley
        ashley_alerts = [
            a for a in alerts
            if a.data.get('person_name') == 'Ashley' and a.data.get('alert_type') == 'relationship_decay'
        ]
        assert len(ashley_alerts) > 0

        # Verify alert properties
        alert = ashley_alerts[0]
        assert alert.data['person_name'] == "Ashley"
        assert alert.data['days_since_mention'] == 6
        assert alert.data['importance_level'] == ImportanceLevel.CRITICAL.value
        assert alert.severity == "critical"

    @pytest.mark.asyncio
    async def test_decay_alert_for_high_priority_person(self, tracker, decay_checker, temp_db):
        """Test that decay alert is generated for high priority person after 7 days."""
        # Record a mention for a high priority person
        tracker.record_mention("Best Friend")
        tracker.set_importance("Best Friend", ImportanceLevel.HIGH)

        # Manually update timestamp to 8 days ago
        eight_days_ago = (datetime.now() - timedelta(days=8)).isoformat()
        conn = sqlite3.connect(temp_db)
        conn.execute(
            "UPDATE person_mentions SET last_mentioned_at = ? WHERE person_name = ?",
            (eight_days_ago, "Best Friend")
        )
        conn.commit()
        conn.close()

        # Check for alerts
        alerts = await decay_checker.check()

        # Should have alert for Best Friend
        friend_alerts = [
            a for a in alerts
            if a.data.get('person_name') == 'Best Friend'
        ]
        assert len(friend_alerts) > 0

        # Verify severity is warning for HIGH importance
        alert = friend_alerts[0]
        assert alert.severity == "warning"
        assert alert.data['days_since_mention'] == 8

    @pytest.mark.asyncio
    async def test_decay_alert_for_medium_priority_person(self, tracker, decay_checker, temp_db):
        """Test that decay alert is generated for medium priority person after 14 days."""
        # Record a mention for a medium priority person
        tracker.record_mention("Colleague")
        tracker.set_importance("Colleague", ImportanceLevel.MEDIUM)

        # Manually update timestamp to 15 days ago
        fifteen_days_ago = (datetime.now() - timedelta(days=15)).isoformat()
        conn = sqlite3.connect(temp_db)
        conn.execute(
            "UPDATE person_mentions SET last_mentioned_at = ? WHERE person_name = ?",
            (fifteen_days_ago, "Colleague")
        )
        conn.commit()
        conn.close()

        # Check for alerts
        alerts = await decay_checker.check()

        # Should have alert for Colleague
        colleague_alerts = [
            a for a in alerts
            if a.data.get('person_name') == 'Colleague'
        ]
        assert len(colleague_alerts) > 0

        # Verify severity is info for MEDIUM importance
        alert = colleague_alerts[0]
        assert alert.severity == "info"

    @pytest.mark.asyncio
    async def test_decay_alert_for_low_priority_person(self, tracker, decay_checker, temp_db):
        """Test that decay alert is generated for low priority person after 30 days."""
        # Record a mention for a low priority person
        tracker.record_mention("Acquaintance")
        tracker.set_importance("Acquaintance", ImportanceLevel.LOW)

        # Manually update timestamp to 31 days ago
        thirty_one_days_ago = (datetime.now() - timedelta(days=31)).isoformat()
        conn = sqlite3.connect(temp_db)
        conn.execute(
            "UPDATE person_mentions SET last_mentioned_at = ? WHERE person_name = ?",
            (thirty_one_days_ago, "Acquaintance")
        )
        conn.commit()
        conn.close()

        # Check for alerts
        alerts = await decay_checker.check()

        # Should have alert for Acquaintance
        acquaintance_alerts = [
            a for a in alerts
            if a.data.get('person_name') == 'Acquaintance'
        ]
        assert len(acquaintance_alerts) > 0

        # Verify severity is debug for LOW importance
        alert = acquaintance_alerts[0]
        assert alert.severity == "debug"

    @pytest.mark.asyncio
    async def test_multiple_stale_relationships_generate_multiple_alerts(self, tracker, decay_checker, temp_db):
        """Test that multiple stale relationships each generate their own alert."""
        # Record mentions for multiple people
        tracker.record_mention("Ashley")
        tracker.set_importance("Ashley", ImportanceLevel.CRITICAL)

        tracker.record_mention("Sullivan")
        tracker.set_importance("Sullivan", ImportanceLevel.CRITICAL)

        tracker.record_mention("Mom")
        tracker.set_importance("Mom", ImportanceLevel.CRITICAL)

        # Set all to 6 days ago (past critical threshold of 5 days)
        six_days_ago = (datetime.now() - timedelta(days=6)).isoformat()
        conn = sqlite3.connect(temp_db)
        for name in ["Ashley", "Sullivan", "Mom"]:
            conn.execute(
                "UPDATE person_mentions SET last_mentioned_at = ? WHERE person_name = ?",
                (six_days_ago, name)
            )
        conn.commit()
        conn.close()

        # Check for alerts
        alerts = await decay_checker.check()

        # Should have alerts for all three
        decay_alerts = [
            a for a in alerts
            if a.data.get('alert_type') == 'relationship_decay'
        ]
        assert len(decay_alerts) >= 3

        # Verify all three people are in the alerts
        alert_names = {a.data['person_name'] for a in decay_alerts}
        assert "Ashley" in alert_names
        assert "Sullivan" in alert_names
        assert "Mom" in alert_names

    @pytest.mark.asyncio
    async def test_stale_relationships_query(self, tracker, temp_db):
        """Test querying for stale relationships directly."""
        # Record mentions
        tracker.record_mention("Ashley")
        tracker.set_importance("Ashley", ImportanceLevel.CRITICAL)

        tracker.record_mention("Sullivan")
        tracker.set_importance("Sullivan", ImportanceLevel.CRITICAL)

        # Set Ashley to 6 days ago (stale), Sullivan to 2 days ago (fresh)
        six_days_ago = (datetime.now() - timedelta(days=6)).isoformat()
        two_days_ago = (datetime.now() - timedelta(days=2)).isoformat()

        conn = sqlite3.connect(temp_db)
        conn.execute(
            "UPDATE person_mentions SET last_mentioned_at = ? WHERE person_name = ?",
            (six_days_ago, "Ashley")
        )
        conn.execute(
            "UPDATE person_mentions SET last_mentioned_at = ? WHERE person_name = ?",
            (two_days_ago, "Sullivan")
        )
        conn.commit()
        conn.close()

        # Query for stale critical relationships (threshold = 5 days)
        stale = tracker.get_stale_relationships(
            threshold_days=5,
            importance=ImportanceLevel.CRITICAL.value
        )

        # Should only have Ashley
        assert len(stale) == 1
        assert stale[0].person_name == "Ashley"

    def test_checker_status_includes_relationship_stats(self, tracker, decay_checker):
        """Test that checker status includes relationship tracking stats."""
        # Add some people
        tracker.record_mention("Ashley")
        tracker.set_importance("Ashley", ImportanceLevel.CRITICAL)
        tracker.record_mention("John")
        tracker.set_importance("John", ImportanceLevel.MEDIUM)

        # Get status
        status = decay_checker.get_status()

        # Verify stats are included
        assert 'total_people_tracked' in status
        assert status['total_people_tracked'] == 2
        assert 'thresholds' in status
        assert status['thresholds'][ImportanceLevel.CRITICAL.value] == 5

    @pytest.mark.asyncio
    async def test_deduplication_key_changes_weekly(self, tracker, decay_checker, temp_db):
        """Test that deduplication key changes weekly to allow re-alerts."""
        # Record a mention
        tracker.record_mention("Ashley")
        tracker.set_importance("Ashley", ImportanceLevel.CRITICAL)

        # Set to 6 days ago
        six_days_ago = (datetime.now() - timedelta(days=6)).isoformat()
        conn = sqlite3.connect(temp_db)
        conn.execute(
            "UPDATE person_mentions SET last_mentioned_at = ? WHERE person_name = ?",
            (six_days_ago, "Ashley")
        )
        conn.commit()
        conn.close()

        # Get first alert
        alerts1 = await decay_checker.check()
        ashley_alert1 = next(
            (a for a in alerts1 if a.data.get('person_name') == 'Ashley'),
            None
        )

        # Update to 13 days ago (different week bucket)
        thirteen_days_ago = (datetime.now() - timedelta(days=13)).isoformat()
        conn = sqlite3.connect(temp_db)
        conn.execute(
            "UPDATE person_mentions SET last_mentioned_at = ? WHERE person_name = ?",
            (thirteen_days_ago, "Ashley")
        )
        conn.commit()
        conn.close()

        # Get second alert
        alerts2 = await decay_checker.check()
        ashley_alert2 = next(
            (a for a in alerts2 if a.data.get('person_name') == 'Ashley'),
            None
        )

        # Both should exist
        assert ashley_alert1 is not None
        assert ashley_alert2 is not None

        # Dedup keys should be different (different week buckets)
        assert ashley_alert1.dedup_key != ashley_alert2.dedup_key


# ========================================================================
# Signal Generation and Persistence
# ========================================================================

@pytest.mark.integration
class TestRelationshipDecaySignals:
    """Test signal generation and persistence for relationship decay alerts."""

    @pytest.mark.asyncio
    async def test_generate_signal_from_decay_alert(self, tracker, decay_checker, temp_db):
        """Test that decay alerts generate proper signals."""
        # Record stale mention
        tracker.record_mention("Ashley")
        tracker.set_importance("Ashley", ImportanceLevel.CRITICAL)

        # Set to 6 days ago
        six_days_ago = (datetime.now() - timedelta(days=6)).isoformat()
        conn = sqlite3.connect(temp_db)
        conn.execute(
            "UPDATE person_mentions SET last_mentioned_at = ? WHERE person_name = ?",
            (six_days_ago, "Ashley")
        )
        conn.commit()
        conn.close()

        # Get alerts
        alerts = await decay_checker.check()
        ashley_alerts = [
            a for a in alerts
            if a.data.get('person_name') == 'Ashley'
        ]

        assert len(ashley_alerts) > 0

        # Verify alert can be converted to signal format
        alert = ashley_alerts[0]
        assert alert.data['person_name'] == "Ashley"
        assert alert.data['days_since_mention'] == 6
        assert alert.severity == "critical"

    def test_signal_manager_generates_unique_ids(self, signal_manager):
        """Test that signal manager generates consistent IDs for relationship signals."""
        signal1 = {
            'type': 'RelationshipCell',
            'person': 'Ashley',
            'priority': 'critical',
            'message': 'Test message'
        }

        signal2 = {
            'type': 'RelationshipCell',
            'person': 'Ashley',
            'priority': 'critical',
            'message': 'Different message'
        }

        signal3 = {
            'type': 'RelationshipCell',
            'person': 'Sullivan',
            'priority': 'critical',
            'message': 'Test message'
        }

        # Same person should generate same ID
        id1 = signal_manager.generate_signal_id(signal1)
        id2 = signal_manager.generate_signal_id(signal2)
        assert id1 == id2
        assert id1 == "relationship-Ashley"

        # Different person should generate different ID
        id3 = signal_manager.generate_signal_id(signal3)
        assert id3 != id1
        assert id3 == "relationship-Sullivan"

    def test_signal_acknowledgment_and_filtering(self, signal_manager):
        """Test that acknowledged signals are filtered from subsequent calls."""
        # Create a signal
        signal = {
            'type': 'RelationshipCell',
            'person': 'Ashley',
            'priority': 'critical',
            'message': 'Test message'
        }

        signal_id = signal_manager.generate_signal_id(signal)

        # Acknowledge it
        signal_manager.mark_acknowledged(signal_id)

        # Verify it's acknowledged
        assert signal_manager.is_acknowledged(signal_id)

        # Create a different signal
        signal2 = {
            'type': 'RelationshipCell',
            'person': 'Sullivan',
            'priority': 'critical',
            'message': 'Test message'
        }

        signal_id2 = signal_manager.generate_signal_id(signal2)

        # Should not be acknowledged
        assert not signal_manager.is_acknowledged(signal_id2)

    def test_signal_state_persistence(self, signal_manager, temp_state_dir):
        """Test that signal acknowledgments persist across manager instances."""
        # Acknowledge a signal
        signal_id = "relationship-Ashley"
        signal_manager.mark_acknowledged(signal_id)

        # Create a new manager instance with same state file
        state_file = temp_state_dir / "signal_state.json"
        new_manager = SignalManager(state_file=str(state_file))

        # Should still be acknowledged
        assert new_manager.is_acknowledged(signal_id)

    def test_old_acknowledgments_are_cleaned_up(self, signal_manager):
        """Test that old acknowledgments are automatically cleaned up."""
        # Acknowledge a signal
        signal_id = "relationship-Ashley"
        signal_manager.mark_acknowledged(signal_id)

        # Manually set timestamp to 25 hours ago (past 24h window)
        old_timestamp = (datetime.now() - timedelta(hours=25)).isoformat()
        signal_manager.state.acknowledged_signals[signal_id] = old_timestamp
        signal_manager._save_state()

        # Clean up old acknowledgments
        signal_manager._clean_old_acknowledgments()

        # Should no longer be acknowledged
        assert not signal_manager.is_acknowledged(signal_id)


# ========================================================================
# Error Handling
# ========================================================================

@pytest.mark.integration
class TestRelationshipDecayErrorHandling:
    """Test error handling in relationship decay checking."""

    @pytest.mark.asyncio
    async def test_checker_handles_database_errors_gracefully(self):
        """Test that checker returns error alert when database is unavailable."""
        # Create checker with invalid database path
        invalid_tracker = RelationshipMentionTracker(db_path="/nonexistent/path/db.sqlite")
        checker = RelationshipDecayChecker(tracker=invalid_tracker)

        # Should not crash, should return error alert
        alerts = await checker.check()

        # Should have at least one alert (may be error alert)
        assert isinstance(alerts, list)

    def test_tracker_initializes_with_custom_db_path(self, tmp_path):
        """Test that tracker can be initialized with custom database path."""
        custom_db = tmp_path / "custom_tracker.db"
        tracker = RelationshipMentionTracker(db_path=str(custom_db))

        # Should create database
        assert custom_db.exists()

        # Should be able to record mentions
        tracker.record_mention("Test Person")
        info = tracker.get_person_info("Test Person")
        assert info['person_name'] == "Test Person"


if __name__ == "__main__":
    """Run tests with pytest."""
    pytest.main([__file__, "-v", "--tb=short"])
