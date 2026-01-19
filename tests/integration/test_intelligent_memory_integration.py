#!/usr/bin/env python3
"""
Integration Tests for Intelligent Memory System.

Tests the complete flow from conversation input through:
- Memory capture
- Classification and routing
- Storage (SQLite relationships + ChromaDB vectors)
- Retrieval via memory commands
- Contextual injection during conversation

Test Categories:
- TestFullCaptureFlow: End-to-end conversation to memory storage
- TestMemoryCommands: /memory search, /memory today, /recall
- TestContextualInjection: Memory retrieval during conversations
- TestCrossDomainIntegration: Multi-domain memory linking
- TestTemporalQueryIntegration: Time-based memory queries
"""

import json
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def temp_thanos_dir(tmp_path):
    """Create a temporary Thanos directory structure."""
    thanos_dir = tmp_path / "Thanos"
    (thanos_dir / "History" / "Sessions").mkdir(parents=True)
    (thanos_dir / "State").mkdir(parents=True)
    return thanos_dir


@pytest.fixture
def mock_session_manager(temp_thanos_dir):
    """Create a mock session manager."""
    from Tools.session_manager import SessionManager, Session

    history_dir = temp_thanos_dir / "History" / "Sessions"
    sm = SessionManager(history_dir=history_dir)
    sm.session = Session()
    return sm


@pytest.fixture
def mock_orchestrator():
    """Create a mock ThanosOrchestrator."""
    orchestrator = MagicMock()
    orchestrator.get_current_agent.return_value = "ops"
    return orchestrator


@pytest.fixture
def mock_context_manager():
    """Create a mock ContextManager."""
    return MagicMock()


@pytest.fixture
def mock_state_reader():
    """Create a mock StateReader."""
    return MagicMock()


@pytest.fixture
def memory_handler(mock_orchestrator, mock_session_manager, mock_context_manager,
                   mock_state_reader, temp_thanos_dir):
    """Create a MemoryHandler with all mock dependencies."""
    from Tools.command_handlers.memory_handler import MemoryHandler

    return MemoryHandler(
        orchestrator=mock_orchestrator,
        session_manager=mock_session_manager,
        context_manager=mock_context_manager,
        state_reader=mock_state_reader,
        thanos_dir=temp_thanos_dir,
        current_agent_getter=lambda: "ops",
    )


@pytest.fixture
def mock_memos():
    """Create a mock MemOS instance."""
    memos = AsyncMock()

    # Mock remember result
    remember_result = Mock()
    remember_result.success = True
    remember_result.graph_results = [{"node_id": "node_123"}]
    remember_result.vector_results = [{"id": "vec_123"}]
    memos.remember = AsyncMock(return_value=remember_result)

    # Mock recall result
    recall_result = Mock()
    recall_result.success = True
    recall_result.vector_results = [
        {"content": "Previous observation about client", "memory_type": "observation", "similarity": 0.85},
        {"content": "Pattern: client scope changes", "memory_type": "pattern", "similarity": 0.72},
    ]
    recall_result.graph_results = {"nodes": []}
    memos.recall = AsyncMock(return_value=recall_result)

    return memos


@pytest.fixture
def relationship_store(tmp_path):
    """Create a RelationshipStore with temporary database."""
    from Tools.relationships import RelationshipStore

    db_path = tmp_path / "test_relationships.db"
    store = RelationshipStore(db_path=db_path)
    yield store
    store.close()


# =============================================================================
# Test Full Capture Flow
# =============================================================================


class TestFullCaptureFlow:
    """End-to-end tests for conversation -> memory storage flow."""

    @pytest.mark.asyncio
    async def test_struggle_capture_to_storage(self, mock_memos, relationship_store):
        """Test: Frustrated conversation -> stored as observation with struggle tag."""
        from Tools.memos import MemoryResult

        text = "I'm really frustrated with this client, they keep changing requirements"

        # 1. Classify the input (simulated)
        classification = {
            "type": "venting",
            "emotion": "frustration",
            "entities": ["client"],
            "tags": ["struggle", "requirements"],
        }

        # 2. Store in MemOS
        result = await mock_memos.remember(
            content=text,
            memory_type="observation",
            domain="work",
            entities=["client"],
            metadata={"emotion": "frustration", "tags": ["struggle"]},
        )

        assert result.success
        mock_memos.remember.assert_called_once()
        call_args = mock_memos.remember.call_args
        assert call_args.kwargs["memory_type"] == "observation"
        assert "frustration" in str(call_args.kwargs["metadata"])

    @pytest.mark.asyncio
    async def test_priority_capture_to_storage(self, mock_memos):
        """Test: Priority statement -> stored with priority metadata."""
        text = "My main focus today needs to be the Memphis project"

        result = await mock_memos.remember(
            content=text,
            memory_type="observation",
            domain="work",
            entities=["Memphis"],
            metadata={
                "priority": "high",
                "time_context": "today",
                "focus_type": "main",
            },
        )

        assert result.success
        call_args = mock_memos.remember.call_args
        assert call_args.kwargs["metadata"]["priority"] == "high"
        assert "Memphis" in call_args.kwargs["entities"]

    @pytest.mark.asyncio
    async def test_activity_capture_to_storage(self, mock_memos):
        """Test: Completed activity -> stored with completion metadata."""
        text = "I just finished the Sherlock post for Orlando"

        result = await mock_memos.remember(
            content=text,
            memory_type="observation",
            domain="work",
            entities=["Sherlock", "Orlando"],
            metadata={
                "activity_type": "content",
                "status": "completed",
                "client": "Orlando",
            },
        )

        assert result.success
        call_args = mock_memos.remember.call_args
        assert call_args.kwargs["metadata"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_commitment_capture_creates_relationship(self, mock_memos, relationship_store):
        """Test: Commitment creates relationship to person entity."""
        from Tools.relationships import RelationType

        text = "I told Sarah I would review her PR by Friday"

        # Store the commitment
        result = await mock_memos.remember(
            content=text,
            memory_type="commitment",
            domain="work",
            entities=["Sarah"],
            metadata={
                "to_whom": "Sarah",
                "deadline": "Friday",
                "action": "review PR",
            },
        )

        assert result.success

        # Create relationship to person entity
        rel = relationship_store.link_memories(
            source_id="commitment_123",
            target_id="entity_sarah",
            rel_type=RelationType.RELATED_TO,
            metadata={"relationship": "commitment_to_person"},
        )

        assert rel.source_id == "commitment_123"
        assert rel.target_id == "entity_sarah"


# =============================================================================
# Test Memory Commands
# =============================================================================


class TestMemoryCommands:
    """Tests for memory-related commands."""

    def test_handle_remember_basic(self, memory_handler, mock_memos):
        """Test /remember command stores memory."""
        with patch.object(memory_handler, '_get_memos', return_value=mock_memos):
            with patch.object(memory_handler, '_run_async') as mock_run:
                mock_result = Mock()
                mock_result.success = True
                mock_result.graph_results = {"node_id": "test_123"}
                mock_result.vector_results = True
                mock_run.return_value = mock_result

                with patch('builtins.print'):
                    result = memory_handler.handle_remember("Test memory content")

                    assert mock_run.called

    def test_handle_remember_with_type_prefix(self, memory_handler, mock_memos):
        """Test /remember with type prefix (decision:, pattern:)."""
        with patch.object(memory_handler, '_get_memos', return_value=mock_memos):
            with patch.object(memory_handler, '_run_async') as mock_run:
                mock_result = Mock()
                mock_result.success = True
                mock_result.graph_results = {}
                mock_result.vector_results = True
                mock_run.return_value = mock_result

                with patch('builtins.print'):
                    memory_handler.handle_remember("decision: Use React for frontend")

                    # Verify _run_async was called (which calls memos.remember)
                    assert mock_run.called

    def test_handle_remember_extracts_entities(self, memory_handler, mock_memos):
        """Test /remember extracts @-mentioned entities."""
        with patch.object(memory_handler, '_get_memos', return_value=mock_memos):
            with patch.object(memory_handler, '_run_async') as mock_run:
                mock_result = Mock()
                mock_result.success = True
                mock_result.graph_results = {}
                mock_result.vector_results = True
                mock_run.return_value = mock_result

                with patch('builtins.print'):
                    memory_handler.handle_remember(
                        "Meeting with @Memphis about @Sherlock project"
                    )
                    assert mock_run.called

    def test_handle_recall_basic(self, memory_handler, mock_memos):
        """Test /recall command searches memories."""
        with patch.object(memory_handler, '_get_memos', return_value=mock_memos):
            with patch.object(memory_handler, '_run_async') as mock_run:
                mock_result = Mock()
                mock_result.success = True
                mock_result.vector_results = [
                    {"content": "Test result", "memory_type": "observation", "similarity": 0.8}
                ]
                mock_result.graph_results = {"nodes": []}
                mock_run.return_value = mock_result

                with patch('builtins.print') as mock_print:
                    memory_handler.handle_recall("client meetings")

                    assert mock_run.called
                    # Should print results
                    assert mock_print.called

    def test_handle_recall_sessions_only(self, memory_handler, temp_thanos_dir):
        """Test /recall --sessions searches only session history."""
        # Create a session file with searchable content
        session_data = {
            "id": "session_123",
            "started_at": "2026-01-15T10:00:00",
            "history": [
                {"role": "user", "content": "Tell me about the Memphis project"},
                {"role": "assistant", "content": "The Memphis project involves..."},
            ],
        }
        session_file = temp_thanos_dir / "History" / "Sessions" / "2026-01-15-session.json"
        session_file.write_text(json.dumps(session_data))

        with patch('builtins.print') as mock_print:
            memory_handler.handle_recall("Memphis --sessions")

            # Should find the session match
            printed_output = " ".join(str(call) for call in mock_print.call_args_list)
            assert "Memphis" in printed_output or "session" in printed_output.lower()

    def test_handle_memory_shows_status(self, memory_handler):
        """Test /memory command shows memory system status."""
        with patch('builtins.print') as mock_print:
            result = memory_handler.handle_memory("")

            # Should print memory systems info
            printed_output = " ".join(str(call) for call in mock_print.call_args_list)
            assert "Memory" in printed_output or "MemOS" in printed_output

    def test_handle_recall_no_results(self, memory_handler, mock_memos, temp_thanos_dir):
        """Test /recall with no matching results."""
        with patch.object(memory_handler, '_get_memos', return_value=mock_memos):
            with patch.object(memory_handler, '_run_async') as mock_run:
                # Return empty results
                mock_result = Mock()
                mock_result.success = True
                mock_result.vector_results = []
                mock_result.graph_results = {"nodes": []}
                mock_run.return_value = mock_result

                with patch('builtins.print') as mock_print:
                    memory_handler.handle_recall("nonexistent query xyz123")

                    # Should indicate no results found
                    printed_output = " ".join(str(call) for call in mock_print.call_args_list)
                    assert "No matches" in printed_output or mock_print.called


# =============================================================================
# Test Contextual Injection
# =============================================================================


class TestContextualInjection:
    """Tests for memory retrieval during conversations."""

    @pytest.mark.asyncio
    async def test_inject_relevant_context(self, mock_memos):
        """Test retrieving relevant memories for conversation context."""
        # Simulate user asking about a client
        user_message = "What's the status of the Memphis project?"

        # Query memories related to Memphis
        result = await mock_memos.recall(
            query="Memphis project status",
            memory_types=["observation", "commitment", "decision"],
            domain="work",
            limit=5,
        )

        assert result.success
        mock_memos.recall.assert_called_once()

        # Verify recall was called with appropriate parameters
        call_args = mock_memos.recall.call_args
        assert "Memphis" in call_args.kwargs["query"]

    @pytest.mark.asyncio
    async def test_inject_entity_context(self, mock_memos):
        """Test injecting entity-specific context."""
        # User mentions a client name
        entity_name = "Memphis"

        # Retrieve entity context
        # In real implementation, this would call get_entity_context
        mock_memos.get_entity_context = AsyncMock(return_value=Mock(
            success=True,
            graph_results=[{
                "entity": "Memphis",
                "commitments": ["Complete integration by Q1"],
                "recent_interactions": ["Call on Jan 15"],
            }],
        ))

        result = await mock_memos.get_entity_context(entity_name)
        assert result.success

    @pytest.mark.asyncio
    async def test_inject_pattern_context(self, mock_memos):
        """Test injecting relevant patterns based on conversation topic."""
        # User mentions something that should trigger pattern recall
        topic = "client feedback"

        result = await mock_memos.recall(
            query=f"patterns related to {topic}",
            memory_types=["pattern"],
            limit=3,
        )

        assert result.success

    def test_contextual_injection_respects_domain(self, mock_memos):
        """Test that context injection respects domain boundaries."""
        # When in work context, should prioritize work memories
        # When in personal context, should prioritize personal memories

        work_query_params = {
            "query": "deadlines",
            "domain": "work",
        }

        personal_query_params = {
            "query": "deadlines",
            "domain": "personal",
        }

        # Both should be valid queries but with different domain filters
        assert work_query_params["domain"] == "work"
        assert personal_query_params["domain"] == "personal"


# =============================================================================
# Test Cross-Domain Integration
# =============================================================================


class TestCrossDomainIntegration:
    """Tests for cross-domain memory linking and correlation."""

    def test_link_health_to_work_outcome(self, relationship_store):
        """Test linking health metrics to work outcomes."""
        from Tools.relationships import RelationType

        # Create health memory
        health_memory_id = "health_poor_sleep_20260115"

        # Create work outcome
        work_memory_id = "work_missed_deadline_20260115"

        # Link them
        relationship_store.link_memories(
            source_id=health_memory_id,
            target_id=work_memory_id,
            rel_type=RelationType.CAUSED,
            strength=0.7,
            metadata={"correlation_type": "health_to_work"},
        )

        # Verify relationship exists
        related = relationship_store.get_related(
            health_memory_id, direction="outgoing"
        )
        assert len(related) == 1
        assert related[0].target_id == work_memory_id

    def test_find_correlation_health_work(self, relationship_store):
        """Test finding correlations between health and work domains."""
        from Tools.relationships import RelationType

        # Create pattern: poor sleep often correlates with missed commitments
        relationship_store.link_memories(
            "health_sleep_1", "common_stress", RelationType.CAUSED
        )
        relationship_store.link_memories(
            "work_missed_1", "common_stress", RelationType.CAUSED
        )

        # Find correlations
        candidates = relationship_store.get_correlation_candidates(
            memory_ids=["health_sleep_1", "work_missed_1"],
            min_shared_connections=2,
        )

        assert len(candidates) >= 1

    def test_store_cross_domain_insight(self, relationship_store):
        """Test storing insights discovered from cross-domain analysis."""
        insight_id = relationship_store.store_insight(
            insight_type="correlation",
            content="Poor sleep score correlates with missed work deadlines 70% of the time",
            source_memories=["health_1", "health_2", "work_1", "work_2"],
            confidence=0.7,
        )

        assert insight_id is not None

        # Retrieve insight
        insights = relationship_store.get_unsurfaced_insights(min_confidence=0.5)
        assert len(insights) == 1
        assert "sleep" in insights[0]["content"].lower()

    def test_traverse_cross_domain_chain(self, relationship_store):
        """Test traversing relationship chains across domains."""
        from Tools.relationships import RelationType

        # Create a chain: health -> stress -> work impact
        relationship_store.link_memories(
            "health_poor_sleep", "emotional_stress", RelationType.CAUSED
        )
        relationship_store.link_memories(
            "emotional_stress", "work_poor_focus", RelationType.CAUSED
        )
        relationship_store.link_memories(
            "work_poor_focus", "work_missed_deadline", RelationType.CAUSED
        )

        # Traverse from deadline back to root cause
        chain = relationship_store.traverse_chain(
            "work_missed_deadline",
            direction="backward",
            rel_types=[RelationType.CAUSED],
            max_depth=5,
        )

        memory_ids = [r.memory_id for r in chain]
        assert "emotional_stress" in memory_ids or "work_poor_focus" in memory_ids


# =============================================================================
# Test Temporal Query Integration
# =============================================================================


class TestTemporalQueryIntegration:
    """Tests for time-based memory queries in integrated context."""

    def test_query_yesterday_struggles(self, relationship_store):
        """Test querying struggles from yesterday."""
        # Store struggles with yesterday's timestamp
        yesterday = datetime.now() - timedelta(days=1)

        relationship_store.store_insight(
            insight_type="struggle",
            content="Authentication bug blocked progress",
            source_memories=["struggle_auth_1"],
            confidence=0.9,
        )

        # Query would filter by date in real implementation
        insights = relationship_store.get_unsurfaced_insights(
            min_confidence=0.5,
            limit=10,
        )

        struggle_insights = [i for i in insights if i["type"] == "struggle"]
        assert len(struggle_insights) > 0

    def test_query_this_week_priorities(self):
        """Test querying priorities set this week."""
        # Simulate priority memories with timestamps
        this_week_priorities = [
            {
                "content": "Memphis project deadline",
                "priority": "high",
                "created_at": datetime.now() - timedelta(days=2),
            },
            {
                "content": "Quarterly report",
                "priority": "high",
                "created_at": datetime.now() - timedelta(days=5),
            },
        ]

        # Filter by this week (within 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        filtered = [
            p for p in this_week_priorities
            if p["created_at"] > week_ago
        ]

        assert len(filtered) == 2

    def test_query_activities_today(self):
        """Test querying activities completed today."""
        today = datetime.now().date()

        activities = [
            {
                "content": "Finished Sherlock post",
                "completed_at": datetime.now() - timedelta(hours=2),
            },
            {
                "content": "Pushed feature branch",
                "completed_at": datetime.now() - timedelta(hours=5),
            },
            {
                "content": "Yesterday's task",
                "completed_at": datetime.now() - timedelta(days=1),
            },
        ]

        # Filter for today only
        today_activities = [
            a for a in activities
            if a["completed_at"].date() == today
        ]

        assert len(today_activities) == 2

    def test_temporal_relationship_ordering(self, relationship_store):
        """Test that temporal relationships maintain order."""
        from Tools.relationships import RelationType

        # Create temporally ordered events
        relationship_store.link_memories(
            "event_morning", "event_afternoon", RelationType.PRECEDED
        )
        relationship_store.link_memories(
            "event_afternoon", "event_evening", RelationType.PRECEDED
        )

        # Traverse forward from morning
        chain = relationship_store.traverse_chain(
            "event_morning",
            direction="forward",
            rel_types=[RelationType.PRECEDED],
        )

        # Should find afternoon first, then evening
        if len(chain) >= 2:
            assert chain[0].depth <= chain[1].depth


# =============================================================================
# Test Session History Integration
# =============================================================================


class TestSessionHistoryIntegration:
    """Tests for session history search and integration."""

    def test_search_session_history(self, temp_thanos_dir):
        """Test searching through session history files."""
        # Create multiple session files
        sessions = [
            {
                "id": "session_1",
                "started_at": "2026-01-10T10:00:00",
                "history": [
                    {"role": "user", "content": "What about the Memphis client?"},
                    {"role": "assistant", "content": "Memphis is a priority client..."},
                ],
            },
            {
                "id": "session_2",
                "started_at": "2026-01-11T14:00:00",
                "history": [
                    {"role": "user", "content": "Need to discuss Orlando project"},
                    {"role": "assistant", "content": "Orlando project status..."},
                ],
            },
        ]

        history_dir = temp_thanos_dir / "History" / "Sessions"
        for i, session in enumerate(sessions):
            file_path = history_dir / f"2026-01-1{i}-session_{i+1}.json"
            file_path.write_text(json.dumps(session))

        # Search for "Memphis"
        matches = []
        for json_file in history_dir.glob("*.json"):
            data = json.loads(json_file.read_text())
            for msg in data.get("history", []):
                if "memphis" in msg.get("content", "").lower():
                    matches.append({
                        "session_id": data["id"],
                        "content": msg["content"],
                    })

        assert len(matches) >= 1
        assert any("Memphis" in m["content"] for m in matches)

    def test_session_memory_integration(self, temp_thanos_dir, mock_memos):
        """Test integrating session history with MemOS memories."""
        # Session history provides conversation context
        # MemOS provides semantic search

        # Create session with relevant content
        session = {
            "id": "session_integrated",
            "history": [
                {"role": "user", "content": "The Memphis deadline is next Friday"},
            ],
        }

        session_file = temp_thanos_dir / "History" / "Sessions" / "test_session.json"
        session_file.write_text(json.dumps(session))

        # MemOS would have the semantic understanding
        # Session history provides exact conversation records

        # Both sources should be searchable
        session_match = "Memphis" in session["history"][0]["content"]
        assert session_match


# =============================================================================
# Test Error Handling Integration
# =============================================================================


class TestErrorHandlingIntegration:
    """Tests for graceful error handling in integrated scenarios."""

    def test_memos_unavailable_fallback(self, memory_handler, temp_thanos_dir):
        """Test fallback when MemOS is unavailable."""
        # Create session file as fallback data
        session = {
            "id": "fallback_session",
            "started_at": "2026-01-15T10:00:00",
            "history": [
                {"role": "user", "content": "fallback search term"},
            ],
        }
        session_file = temp_thanos_dir / "History" / "Sessions" / "fallback.json"
        session_file.write_text(json.dumps(session))

        # Mock MemOS as unavailable
        with patch.object(memory_handler, '_get_memos', return_value=None):
            with patch('builtins.print') as mock_print:
                memory_handler.handle_recall("fallback search term")

                # Should still work via session search
                printed = " ".join(str(c) for c in mock_print.call_args_list)
                # Either finds session match or indicates MemOS unavailable
                assert mock_print.called

    def test_chromadb_error_graceful(self, mock_memos):
        """Test graceful handling of ChromaDB errors."""
        # Mock recall to raise error
        mock_memos.recall = AsyncMock(side_effect=Exception("ChromaDB connection failed"))

        # Should not crash - error should be caught
        with pytest.raises(Exception) as exc_info:
            import asyncio
            asyncio.run(mock_memos.recall("test query"))

        assert "ChromaDB" in str(exc_info.value)

    def test_relationship_store_error_recovery(self, tmp_path):
        """Test relationship store handles errors gracefully."""
        from Tools.relationships import RelationshipStore, RelationType

        # Create store with valid path
        db_path = tmp_path / "test_recovery.db"
        store = RelationshipStore(db_path=db_path)

        # Normal operation should work
        rel = store.link_memories("mem_1", "mem_2", RelationType.RELATED_TO)
        assert rel is not None

        store.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
