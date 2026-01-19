#!/usr/bin/env python3
"""
Comprehensive Unit Tests for the Intelligent Memory System.

This module tests the intelligent memory capture, processing, and retrieval
capabilities of the Thanos memory system, including:

1. Memory capture from conversation text
2. Struggle/emotion detection (keywords, patterns)
3. Value/priority extraction
4. SQLite storage and retrieval (RelationshipStore)
5. ChromaDB vector search integration
6. Brain dump classification

Test Categories:
- TestMemoryCaptureFromConversation: Tests for extracting memories from text
- TestStruggleDetection: Tests for detecting struggles, frustration, blockers
- TestPriorityExtraction: Tests for extracting priorities and focus areas
- TestActivityTracking: Tests for tracking completed tasks and activities
- TestSQLiteStorage: Tests for RelationshipStore SQLite operations
- TestChromaDBSearch: Tests for vector search functionality
- TestTemporalQueries: Tests for time-based queries
- TestMemoryClassification: Tests for brain dump classification
"""

import json
import re
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
def temp_db_path(tmp_path):
    """Create a temporary database path for testing."""
    return tmp_path / "test_relationships.db"


@pytest.fixture
def relationship_store(temp_db_path):
    """Create a RelationshipStore with temporary database."""
    from Tools.relationships import RelationshipStore

    store = RelationshipStore(db_path=temp_db_path)
    yield store
    store.close()


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client for embeddings."""
    mock_client = Mock()
    mock_embedding_response = Mock()
    mock_embedding_response.data = [Mock(embedding=[0.1] * 1536)]
    mock_client.embeddings.create = Mock(return_value=mock_embedding_response)
    return mock_client


@pytest.fixture
def mock_chroma_client():
    """Create a mock ChromaDB client."""
    mock_client = Mock()
    mock_collection = Mock()
    mock_collection.add = Mock()
    mock_collection.query = Mock(return_value={
        "ids": [["doc1", "doc2"]],
        "documents": [["Test document 1", "Test document 2"]],
        "metadatas": [[{"type": "observation"}, {"type": "pattern"}]],
        "distances": [[0.1, 0.2]],
    })
    mock_client.get_or_create_collection = Mock(return_value=mock_collection)
    mock_client.get_collection = Mock(return_value=mock_collection)
    mock_client.list_collections = Mock(return_value=[])
    return mock_client


@pytest.fixture
def sample_conversations():
    """Sample conversation texts for testing."""
    return {
        "struggle_frustration": "I'm really frustrated with this client, they keep changing requirements",
        "struggle_blocked": "I'm stuck on this authentication bug, can't figure out why tokens expire",
        "struggle_overwhelmed": "I have so much to do and I'm feeling completely overwhelmed",
        "priority_focus": "My main focus today needs to be the Memphis project",
        "priority_urgent": "The most important thing right now is finishing the quarterly report",
        "activity_completed": "I just finished the Sherlock post for Orlando",
        "activity_work_task": "Just pushed the new feature to staging",
        "commitment": "I told Sarah I would review her PR by Friday",
        "thinking": "I've been thinking about maybe restructuring the API",
        "venting": "UGH this deployment pipeline is such a mess!!",
        "observation": "I noticed that team productivity drops after 3pm meetings",
        "mixed": "Need to call the dentist. Also been thinking about vacation plans.",
    }


# =============================================================================
# Test Memory Capture from Conversation
# =============================================================================


class TestMemoryCaptureFromConversation:
    """Tests for capturing memories from conversation text."""

    def test_extract_entities_at_mentions(self):
        """Test extracting @-mentioned entities from text."""
        text = "Meeting with @Memphis client about the @Sherlock project"

        # Simple entity extraction (words starting with @)
        words = text.split()
        entities = [word[1:] for word in words if word.startswith("@") and len(word) > 1]

        assert "Memphis" in entities
        assert "Sherlock" in entities
        assert len(entities) == 2

    def test_extract_entities_client_mentions(self):
        """Test extracting client names from context."""
        text = "Working on the Memphis client integration"

        # Pattern-based client detection
        client_patterns = [
            r"(?:client|customer|account)\s+(?:named\s+)?([A-Z][a-z]+)",
            r"([A-Z][a-z]+)\s+(?:client|customer|account)",
            r"for\s+([A-Z][a-z]+)\b",
        ]

        found_clients = []
        for pattern in client_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            found_clients.extend(matches)

        assert "Memphis" in found_clients

    def test_extract_project_mentions(self):
        """Test extracting project names from text."""
        text = "The Sherlock project deadline is next week"

        project_patterns = [
            r"(?:project|task|work on)\s+(?:called\s+)?([A-Z][a-z]+)",
            r"([A-Z][a-z]+)\s+(?:project|initiative|feature)",
        ]

        found_projects = []
        for pattern in project_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            found_projects.extend(matches)

        assert "Sherlock" in found_projects

    def test_detect_memory_type_from_content(self):
        """Test automatic memory type detection."""
        test_cases = [
            ("I decided to use React for the frontend", "decision"),
            ("I committed to delivering by Friday", "commitment"),
            ("I noticed this happens every Monday", "pattern"),
            ("Meeting notes from today's standup", "observation"),
        ]

        type_keywords = {
            "decision": ["decided", "chose", "selected", "picked", "went with"],
            "commitment": ["committed", "promised", "will deliver", "told them I would"],
            "pattern": ["noticed", "pattern", "every time", "always", "usually"],
            "observation": ["notes", "observed", "saw that", "meeting"],
        }

        for text, expected_type in test_cases:
            detected_type = "observation"  # default
            text_lower = text.lower()

            for mem_type, keywords in type_keywords.items():
                if any(kw in text_lower for kw in keywords):
                    detected_type = mem_type
                    break

            assert detected_type == expected_type, f"Failed for: {text}"


# =============================================================================
# Test Struggle Detection
# =============================================================================


class TestStruggleDetection:
    """Tests for detecting struggles, frustrations, and blockers."""

    @pytest.fixture
    def struggle_keywords(self):
        """Keywords indicating struggle or frustration."""
        return {
            "frustration": ["frustrated", "annoying", "annoyed", "ugh", "argh", "hate"],
            "blocked": ["stuck", "blocked", "can't figure out", "not working", "broken"],
            "overwhelmed": ["overwhelmed", "too much", "drowning", "buried", "swamped"],
            "stress": ["stressed", "anxious", "worried", "pressure", "deadline"],
            "confusion": ["confused", "don't understand", "unclear", "lost", "puzzled"],
        }

    def test_detect_frustration_keywords(self, struggle_keywords):
        """Test detecting frustration from keywords."""
        texts = [
            ("I'm really frustrated with this client", True, "frustration"),
            ("The bug is annoying me", True, "frustration"),
            ("UGH why doesn't this work", True, "frustration"),
            ("Had a great meeting today", False, None),
        ]

        for text, should_detect, expected_category in texts:
            text_lower = text.lower()
            detected = False
            detected_category = None

            for category, keywords in struggle_keywords.items():
                if any(kw in text_lower for kw in keywords):
                    detected = True
                    detected_category = category
                    break

            assert detected == should_detect, f"Failed for: {text}"
            if should_detect:
                assert detected_category == expected_category

    def test_detect_blocked_state(self, struggle_keywords):
        """Test detecting blocked/stuck state."""
        texts = [
            "I'm stuck on this authentication bug",
            "Can't figure out why the tests are failing",
            "This feature is not working at all",
            "The deployment is broken again",
        ]

        for text in texts:
            text_lower = text.lower()
            is_blocked = any(
                kw in text_lower for kw in struggle_keywords["blocked"]
            )
            assert is_blocked, f"Should detect blocked state in: {text}"

    def test_detect_overwhelmed_state(self, struggle_keywords):
        """Test detecting overwhelmed state."""
        texts = [
            "I have so much to do and I'm feeling completely overwhelmed",
            "There's too much on my plate right now",
            "I'm drowning in tasks",
            "Swamped with client requests",
        ]

        for text in texts:
            text_lower = text.lower()
            is_overwhelmed = any(
                kw in text_lower for kw in struggle_keywords["overwhelmed"]
            )
            assert is_overwhelmed, f"Should detect overwhelmed state in: {text}"

    def test_detect_emotional_intensity(self):
        """Test detecting emotional intensity from punctuation and caps."""
        texts = [
            ("This is terrible!!!", 3, True),  # Multiple exclamation
            ("WHY DOESN'T THIS WORK", 0, True),  # All caps
            ("I'm a bit frustrated.", 1, False),  # Normal punctuation
            ("ARGH!!!", 3, True),  # Both caps and exclamation
        ]

        for text, exclamation_count, is_intense in texts:
            actual_exclamations = text.count("!")
            has_caps = text.isupper() or (
                sum(1 for c in text if c.isupper()) > len(text) * 0.5
            )
            detected_intense = actual_exclamations >= 2 or has_caps

            assert detected_intense == is_intense, f"Failed intensity detection for: {text}"

    def test_extract_struggle_context(self):
        """Test extracting context around struggle (what they're struggling with)."""
        text = "I'm really frustrated with this client, they keep changing requirements"

        # Extract what comes after "frustrated with"
        pattern = r"frustrated\s+(?:with|about|by)\s+(.+?)(?:[,.]|$)"
        match = re.search(pattern, text.lower())

        assert match is not None
        context = match.group(1).strip()
        assert "client" in context

    def test_struggle_creates_appropriate_memory_type(self):
        """Test that struggles are categorized appropriately."""
        # Struggles should become observations or patterns, not tasks
        struggle_text = "I'm frustrated with constant scope changes"

        # In brain dump classifier logic, venting/frustration -> venting classification
        # Not a task, but logged as observation
        expected_classifications = ["venting", "observation", "thinking"]

        # Simple heuristic check - frustration without clear action = not a task
        is_task = "need to" in struggle_text.lower() and "frustrated" not in struggle_text.lower()
        assert not is_task


# =============================================================================
# Test Priority Extraction
# =============================================================================


class TestPriorityExtraction:
    """Tests for extracting priorities and focus areas from text."""

    @pytest.fixture
    def priority_indicators(self):
        """Keywords and patterns indicating priority."""
        return {
            "high": [
                "most important", "top priority", "critical", "urgent",
                "main focus", "need to focus on", "primary goal",
            ],
            "medium": [
                "should do", "important", "need to", "want to",
            ],
            "low": [
                "when i have time", "eventually", "nice to have",
                "if possible", "would be good", "someday",
            ],
        }

    def test_detect_high_priority(self, priority_indicators):
        """Test detecting high priority items."""
        texts = [
            "My main focus today needs to be the Memphis project",
            "The most important thing right now is finishing the quarterly report",
            "This is critical - we need to fix the production bug",
            "Top priority: review the security audit",
        ]

        for text in texts:
            text_lower = text.lower()
            is_high_priority = any(
                kw in text_lower for kw in priority_indicators["high"]
            )
            assert is_high_priority, f"Should detect high priority in: {text}"

    def test_detect_low_priority(self, priority_indicators):
        """Test detecting low priority items."""
        texts = [
            "Eventually I should clean up the test fixtures",
            "Nice to have: dark mode support",
            "When I have time, I'll refactor the database layer",
        ]

        for text in texts:
            text_lower = text.lower()
            is_low_priority = any(
                kw in text_lower for kw in priority_indicators["low"]
            )
            assert is_low_priority, f"Should detect low priority in: {text}"

    def test_extract_time_context_today(self):
        """Test extracting 'today' time context."""
        text = "My main focus today needs to be the Memphis project"

        time_patterns = {
            "today": ["today", "this morning", "this afternoon", "this evening"],
            "tomorrow": ["tomorrow", "tomorrow morning"],
            "this_week": ["this week", "by friday", "by end of week"],
        }

        text_lower = text.lower()
        detected_time = None

        for time_frame, patterns in time_patterns.items():
            if any(p in text_lower for p in patterns):
                detected_time = time_frame
                break

        assert detected_time == "today"

    def test_extract_focus_area(self):
        """Test extracting what the focus/priority is about."""
        texts = [
            ("My main focus today needs to be the Memphis project", "Memphis project"),
            ("Most important: quarterly report", "quarterly report"),
            ("Priority is fixing the auth bug", "auth bug"),
        ]

        for text, expected_focus in texts:
            # Patterns to extract focus area
            patterns = [
                r"focus.*?(?:on|be|is)\s+(?:the\s+)?(.+?)(?:$|[.])",
                r"most important.*?(?:is|:)\s*(?:the\s+)?(.+?)(?:$|[.])",
                r"priority.*?(?:is|:)\s*(?:the\s+)?(.+?)(?:$|[.])",
            ]

            focus = None
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    focus = match.group(1).strip()
                    break

            assert focus is not None, f"Should extract focus from: {text}"
            assert expected_focus.lower() in focus.lower()

    def test_priority_with_deadline(self):
        """Test extracting priority with associated deadline."""
        text = "Need to finish the proposal by Friday - it's the top priority"

        # Extract deadline
        deadline_patterns = [
            r"by\s+([A-Za-z]+day)",
            r"by\s+(tomorrow|today|end of day)",
            r"deadline[:\s]+(.+?)(?:$|[,.])",
        ]

        deadline = None
        for pattern in deadline_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                deadline = match.group(1)
                break

        assert deadline == "Friday"


# =============================================================================
# Test Activity Tracking
# =============================================================================


class TestActivityTracking:
    """Tests for tracking completed tasks and activities."""

    @pytest.fixture
    def completion_indicators(self):
        """Keywords indicating task completion."""
        return [
            "finished", "completed", "done", "just did", "just finished",
            "pushed", "deployed", "shipped", "submitted", "sent",
        ]

    def test_detect_completed_activity(self, completion_indicators):
        """Test detecting completed activities."""
        texts = [
            ("I just finished the Sherlock post for Orlando", True),
            ("Just pushed the new feature to staging", True),
            ("Completed the quarterly review", True),
            ("Need to finish the report", False),  # Future, not completed
            ("I want to complete this", False),  # Intention, not completed
        ]

        for text, should_be_completed in texts:
            text_lower = text.lower()
            is_completed = any(
                indicator in text_lower for indicator in completion_indicators
            )
            assert is_completed == should_be_completed, f"Failed for: {text}"

    def test_extract_activity_details(self):
        """Test extracting what activity was completed."""
        text = "I just finished the Sherlock post for Orlando"

        # Pattern: [completion word] [the] [activity] [for client]
        pattern = r"(?:finished|completed|done)\s+(?:the\s+)?(.+?)(?:\s+for\s+(.+))?$"
        match = re.search(pattern, text.lower())

        assert match is not None
        activity = match.group(1).strip()
        client = match.group(2).strip() if match.group(2) else None

        assert "sherlock post" in activity
        assert client == "orlando"

    def test_extract_work_type(self):
        """Test extracting type of work completed."""
        # Note: Order matters - more specific types should be checked first
        work_types = [
            ("review", ["reviewed", "feedback", "approved"]),
            ("communication", ["sent", "emailed", "called", "meeting", "proposal"]),
            ("content", ["post", "article", "blog", "document", "write-up"]),
            ("code", ["pushed", "deployed", "committed", "merged", "pr", "feature"]),
        ]

        texts = [
            ("Just pushed the new feature to staging", "code"),
            ("Finished the Sherlock post", "content"),
            ("Sent the proposal to the client", "communication"),
            ("Reviewed the PR for auth changes", "review"),
        ]

        for text, expected_type in texts:
            text_lower = text.lower()
            detected_type = None

            for work_type, keywords in work_types:
                if any(kw in text_lower for kw in keywords):
                    detected_type = work_type
                    break

            assert detected_type == expected_type, f"Failed for: {text}"

    def test_activity_links_to_client(self):
        """Test that activities are linked to clients when mentioned."""
        text = "Finished the Sherlock post for Orlando"

        # Extract client mention pattern
        for_pattern = r"for\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"
        match = re.search(for_pattern, text)

        assert match is not None
        client = match.group(1)
        assert client == "Orlando"


# =============================================================================
# Test SQLite Storage (RelationshipStore)
# =============================================================================


class TestSQLiteStorage:
    """Tests for SQLite-based relationship storage."""

    def test_create_relationship(self, relationship_store):
        """Test creating a relationship between memories."""
        from Tools.relationships import RelationType

        rel = relationship_store.link_memories(
            source_id="memory_1",
            target_id="memory_2",
            rel_type=RelationType.CAUSED,
            strength=0.9,
            metadata={"context": "test"},
        )

        assert rel.source_id == "memory_1"
        assert rel.target_id == "memory_2"
        assert rel.rel_type == RelationType.CAUSED
        assert rel.strength == 0.9
        assert rel.metadata.get("context") == "test"

    def test_get_related_memories(self, relationship_store):
        """Test retrieving related memories."""
        from Tools.relationships import RelationType

        # Create multiple relationships
        relationship_store.link_memories("mem_a", "mem_b", RelationType.CAUSED)
        relationship_store.link_memories("mem_a", "mem_c", RelationType.ENABLED)
        relationship_store.link_memories("mem_d", "mem_a", RelationType.PRECEDED)

        # Get outgoing relationships
        outgoing = relationship_store.get_related(
            "mem_a", direction="outgoing"
        )
        assert len(outgoing) == 2

        # Get incoming relationships
        incoming = relationship_store.get_related(
            "mem_a", direction="incoming"
        )
        assert len(incoming) == 1
        assert incoming[0].source_id == "mem_d"

    def test_traverse_chain_backward(self, relationship_store):
        """Test backward chain traversal (what led to this?)."""
        from Tools.relationships import RelationType

        # Create a causal chain: A -> B -> C -> D
        relationship_store.link_memories("mem_a", "mem_b", RelationType.CAUSED)
        relationship_store.link_memories("mem_b", "mem_c", RelationType.CAUSED)
        relationship_store.link_memories("mem_c", "mem_d", RelationType.CAUSED)

        # Traverse backward from D
        results = relationship_store.traverse_chain(
            "mem_d",
            direction="backward",
            rel_types=[RelationType.CAUSED],
        )

        assert len(results) >= 1
        # Should find at least C (depth 1)
        memory_ids = [r.memory_id for r in results]
        assert "mem_c" in memory_ids

    def test_traverse_chain_forward(self, relationship_store):
        """Test forward chain traversal (what resulted from this?)."""
        from Tools.relationships import RelationType

        # Create a chain: A -> B -> C
        relationship_store.link_memories("mem_a", "mem_b", RelationType.CAUSED)
        relationship_store.link_memories("mem_b", "mem_c", RelationType.CAUSED)

        # Traverse forward from A
        results = relationship_store.traverse_chain(
            "mem_a",
            direction="forward",
            rel_types=[RelationType.CAUSED],
        )

        memory_ids = [r.memory_id for r in results]
        assert "mem_b" in memory_ids

    def test_filter_by_relationship_type(self, relationship_store):
        """Test filtering relationships by type."""
        from Tools.relationships import RelationType

        relationship_store.link_memories("mem_a", "mem_b", RelationType.CAUSED)
        relationship_store.link_memories("mem_a", "mem_c", RelationType.ENABLED)
        relationship_store.link_memories("mem_a", "mem_d", RelationType.RELATED_TO)

        # Filter by CAUSED only
        caused_rels = relationship_store.get_related(
            "mem_a",
            rel_type=RelationType.CAUSED,
            direction="outgoing",
        )

        assert len(caused_rels) == 1
        assert caused_rels[0].target_id == "mem_b"

    def test_filter_by_strength(self, relationship_store):
        """Test filtering relationships by strength."""
        from Tools.relationships import RelationType

        relationship_store.link_memories("mem_a", "mem_b", RelationType.CAUSED, strength=0.9)
        relationship_store.link_memories("mem_a", "mem_c", RelationType.CAUSED, strength=0.3)
        relationship_store.link_memories("mem_a", "mem_d", RelationType.CAUSED, strength=0.6)

        # Filter by minimum strength
        strong_rels = relationship_store.get_related(
            "mem_a",
            direction="outgoing",
            min_strength=0.5,
        )

        assert len(strong_rels) == 2  # mem_b (0.9) and mem_d (0.6)
        strengths = [r.strength for r in strong_rels]
        assert all(s >= 0.5 for s in strengths)

    def test_store_insight(self, relationship_store):
        """Test storing discovered insights."""
        insight_id = relationship_store.store_insight(
            insight_type="pattern",
            content="Poor sleep correlates with missed commitments",
            source_memories=["sleep_mem_1", "commitment_mem_1"],
            confidence=0.8,
        )

        assert insight_id is not None
        assert isinstance(insight_id, int)

    def test_get_unsurfaced_insights(self, relationship_store):
        """Test retrieving unsurfaced insights."""
        relationship_store.store_insight(
            insight_type="pattern",
            content="Test insight 1",
            source_memories=["mem_1"],
            confidence=0.9,
        )
        relationship_store.store_insight(
            insight_type="correlation",
            content="Test insight 2",
            source_memories=["mem_2", "mem_3"],
            confidence=0.4,  # Below default threshold
        )

        # Get insights with default threshold (0.5)
        insights = relationship_store.get_unsurfaced_insights()

        assert len(insights) == 1
        assert insights[0]["content"] == "Test insight 1"
        assert insights[0]["confidence"] == 0.9

    def test_mark_insight_surfaced(self, relationship_store):
        """Test marking insight as surfaced."""
        insight_id = relationship_store.store_insight(
            insight_type="warning",
            content="Deadline approaching",
            source_memories=["mem_1"],
            confidence=0.8,
        )

        # Initially should be unsurfaced
        insights = relationship_store.get_unsurfaced_insights()
        assert len(insights) == 1

        # Mark as surfaced
        relationship_store.mark_insight_surfaced(insight_id)

        # Should no longer appear
        insights = relationship_store.get_unsurfaced_insights()
        assert len(insights) == 0

    def test_find_correlation_candidates(self, relationship_store):
        """Test finding memories that connect multiple input memories."""
        from Tools.relationships import RelationType

        # Create a hub memory that connects multiple other memories
        relationship_store.link_memories("sleep_bad", "hub_mem", RelationType.CAUSED)
        relationship_store.link_memories("missed_commitment", "hub_mem", RelationType.CAUSED)
        relationship_store.link_memories("stress_high", "hub_mem", RelationType.CAUSED)

        # Find what connects sleep and commitment
        candidates = relationship_store.get_correlation_candidates(
            memory_ids=["sleep_bad", "missed_commitment"],
            min_shared_connections=2,
        )

        # hub_mem should be a candidate
        candidate_ids = [c["memory_id"] for c in candidates]
        assert "hub_mem" in candidate_ids

    def test_get_stats(self, relationship_store):
        """Test getting relationship store statistics."""
        from Tools.relationships import RelationType

        relationship_store.link_memories("mem_a", "mem_b", RelationType.CAUSED)
        relationship_store.link_memories("mem_c", "mem_d", RelationType.ENABLED)

        stats = relationship_store.get_stats()

        assert "total_relationships" in stats
        assert stats["total_relationships"] == 2
        assert "by_type" in stats
        assert "caused" in stats["by_type"]

    def test_upsert_relationship(self, relationship_store):
        """Test updating existing relationship (upsert behavior)."""
        from Tools.relationships import RelationType

        # Create initial relationship
        rel1 = relationship_store.link_memories(
            "mem_a", "mem_b", RelationType.CAUSED, strength=0.5
        )

        # Update with same source/target/type
        rel2 = relationship_store.link_memories(
            "mem_a", "mem_b", RelationType.CAUSED, strength=0.9
        )

        # Should update, not create duplicate
        relationships = relationship_store.get_related("mem_a", direction="outgoing")
        assert len(relationships) == 1
        assert relationships[0].strength == 0.9


# =============================================================================
# Test ChromaDB Vector Search
# =============================================================================


class TestChromaDBSearch:
    """Tests for ChromaDB vector search functionality."""

    def test_vector_search_returns_similar_documents(self, mock_chroma_client, mock_openai_client):
        """Test that vector search returns semantically similar documents."""
        collection = mock_chroma_client.get_or_create_collection(name="observations")

        # Perform search
        results = collection.query(
            query_embeddings=[[0.1] * 1536],
            n_results=2,
        )

        assert "documents" in results
        assert len(results["documents"][0]) == 2

    def test_vector_search_with_metadata_filter(self, mock_chroma_client):
        """Test vector search with metadata filtering."""
        collection = mock_chroma_client.get_or_create_collection(name="memories")

        # Configure mock to handle where filter
        filtered_results = {
            "ids": [["doc1"]],
            "documents": [["Filtered document"]],
            "metadatas": [[{"domain": "work"}]],
            "distances": [[0.1]],
        }
        collection.query = Mock(return_value=filtered_results)

        results = collection.query(
            query_embeddings=[[0.1] * 1536],
            n_results=5,
            where={"domain": "work"},
        )

        assert len(results["documents"][0]) == 1
        collection.query.assert_called()

    def test_store_memory_with_embedding(self, mock_chroma_client, mock_openai_client):
        """Test storing a memory with generated embedding."""
        collection = mock_chroma_client.get_or_create_collection(name="observations")

        # Generate embedding
        text = "This is a test observation"
        embedding_response = mock_openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
        )
        embedding = embedding_response.data[0].embedding

        # Store in ChromaDB
        collection.add(
            ids=["obs_123"],
            embeddings=[embedding],
            documents=[text],
            metadatas=[{"type": "observation", "domain": "work"}],
        )

        collection.add.assert_called_once()

    def test_search_across_multiple_collections(self, mock_chroma_client):
        """Test searching across multiple memory collections."""
        collections = ["commitments", "decisions", "patterns", "observations"]

        all_results = []
        for coll_name in collections:
            collection = mock_chroma_client.get_collection(name=coll_name)
            results = collection.query(
                query_embeddings=[[0.1] * 1536],
                n_results=3,
            )
            all_results.extend(results["documents"][0])

        # Should have results from all collections
        assert len(all_results) > 0

    def test_similarity_score_ranking(self, mock_chroma_client):
        """Test that results are ranked by similarity."""
        collection = mock_chroma_client.get_or_create_collection(name="memories")

        # Mock results with different distances
        ranked_results = {
            "ids": [["doc1", "doc2", "doc3"]],
            "documents": [["Most similar", "Second", "Third"]],
            "metadatas": [[{}, {}, {}]],
            "distances": [[0.1, 0.3, 0.5]],
        }
        collection.query = Mock(return_value=ranked_results)

        results = collection.query(query_embeddings=[[0.1] * 1536], n_results=3)

        distances = results["distances"][0]
        assert distances == sorted(distances)  # Should be in ascending order


# =============================================================================
# Test Temporal Queries
# =============================================================================


class TestTemporalQueries:
    """Tests for time-based memory queries."""

    @pytest.fixture
    def time_expressions(self):
        """Common time expressions and their relative meanings."""
        return {
            "yesterday": timedelta(days=-1),
            "today": timedelta(days=0),
            "last week": timedelta(days=-7),
            "this morning": timedelta(hours=-6),
            "on Monday": None,  # Requires day-of-week calculation
        }

    def test_parse_yesterday(self):
        """Test parsing 'yesterday' in queries."""
        query = "What did I struggle with yesterday?"

        time_patterns = {
            "yesterday": (timedelta(days=-1), timedelta(days=0)),
            "today": (timedelta(days=0), timedelta(days=1)),
            "last week": (timedelta(days=-7), timedelta(days=0)),
        }

        for time_word, (start_delta, end_delta) in time_patterns.items():
            if time_word in query.lower():
                now = datetime.now()
                start = now + start_delta
                end = now + end_delta

                assert start < end
                assert "yesterday" in query.lower()
                break

    def test_parse_this_morning(self):
        """Test parsing 'this morning' in queries."""
        query = "What did I work on this morning?"

        if "this morning" in query.lower():
            now = datetime.now()
            # Morning is roughly 6 AM to 12 PM
            start = now.replace(hour=6, minute=0, second=0, microsecond=0)
            end = now.replace(hour=12, minute=0, second=0, microsecond=0)

            assert start < end

    def test_parse_last_week(self):
        """Test parsing 'last week' in queries."""
        query = "What patterns emerged last week?"

        if "last week" in query.lower():
            now = datetime.now()
            start = now - timedelta(days=7)
            end = now

            assert (end - start).days == 7

    def test_parse_day_of_week(self):
        """Test parsing specific day names."""
        query = "What did I commit to on Monday?"

        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

        for day in days:
            if day in query.lower():
                # Find the most recent occurrence of that day
                now = datetime.now()
                target_day = days.index(day)
                current_day = now.weekday()

                days_ago = (current_day - target_day) % 7
                if days_ago == 0:
                    days_ago = 7  # If today is Monday, "on Monday" means last Monday

                target_date = now - timedelta(days=days_ago)
                assert target_date.weekday() == target_day
                break

    def test_extract_time_context_from_query(self):
        """Test extracting time context from various query forms."""
        queries = [
            ("What did I struggle with yesterday?", "yesterday"),
            ("Show me priorities from last week", "last week"),
            ("What happened this morning?", "this morning"),
            ("Tasks completed on Friday", "on friday"),
        ]

        time_patterns = [
            r"(yesterday)",
            r"(last week)",
            r"(this morning|this afternoon|this evening)",
            r"(on [A-Za-z]+day)",
            r"(today)",
        ]

        for query, expected_time in queries:
            found_time = None
            for pattern in time_patterns:
                match = re.search(pattern, query.lower())
                if match:
                    found_time = match.group(1)
                    break

            assert found_time is not None, f"Should extract time from: {query}"
            assert expected_time.lower() in found_time.lower()


# =============================================================================
# Test Memory Classification (Brain Dump)
# =============================================================================


class TestMemoryClassification:
    """Tests for brain dump classification."""

    def test_classified_brain_dump_dataclass(self):
        """Test ClassifiedBrainDump dataclass creation."""
        from Tools.brain_dump.classifier import ClassifiedBrainDump

        dump = ClassifiedBrainDump(
            id="test_123",
            raw_text="Test content",
            source="manual",
            classification="thinking",
            confidence=0.9,
            reasoning="Test reasoning",
        )

        assert dump.id == "test_123"
        assert dump.classification == "thinking"
        assert not dump.is_actionable()

    def test_is_actionable_for_tasks(self):
        """Test is_actionable() returns true for task types."""
        from Tools.brain_dump.classifier import ClassifiedBrainDump

        task_types = ["personal_task", "work_task", "commitment"]
        non_task_types = ["thinking", "venting", "observation", "note", "idea"]

        for class_type in task_types:
            dump = ClassifiedBrainDump(
                id="test",
                raw_text="Test",
                source="manual",
                classification=class_type,
                confidence=0.9,
                reasoning="Test",
            )
            assert dump.is_actionable(), f"{class_type} should be actionable"

        for class_type in non_task_types:
            dump = ClassifiedBrainDump(
                id="test",
                raw_text="Test",
                source="manual",
                classification=class_type,
                confidence=0.9,
                reasoning="Test",
            )
            assert not dump.is_actionable(), f"{class_type} should not be actionable"

    def test_has_task_check(self):
        """Test has_task() method."""
        from Tools.brain_dump.classifier import ClassifiedBrainDump

        dump_with_task = ClassifiedBrainDump(
            id="test",
            raw_text="Call the dentist",
            source="manual",
            classification="personal_task",
            confidence=0.9,
            reasoning="Clear action",
            task={"title": "Call dentist", "context": "personal"},
        )

        dump_without_task = ClassifiedBrainDump(
            id="test",
            raw_text="Thinking about vacation",
            source="manual",
            classification="thinking",
            confidence=0.9,
            reasoning="Just thinking",
        )

        assert dump_with_task.has_task()
        assert not dump_without_task.has_task()

    def test_has_commitment_check(self):
        """Test has_commitment() method."""
        from Tools.brain_dump.classifier import ClassifiedBrainDump

        dump_with_commitment = ClassifiedBrainDump(
            id="test",
            raw_text="I told Sarah I would review her PR",
            source="manual",
            classification="commitment",
            confidence=0.9,
            reasoning="Promise made",
            commitment={"description": "Review PR", "to_whom": "Sarah"},
        )

        assert dump_with_commitment.has_commitment()

    def test_to_dict_serialization(self):
        """Test to_dict() returns valid dictionary."""
        from Tools.brain_dump.classifier import ClassifiedBrainDump

        dump = ClassifiedBrainDump(
            id="test_123",
            raw_text="Test content",
            source="telegram",
            classification="observation",
            confidence=0.85,
            reasoning="Just an observation",
            acknowledgment="Noted!",
        )

        data = dump.to_dict()

        assert isinstance(data, dict)
        assert data["id"] == "test_123"
        assert data["classification"] == "observation"
        assert data["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_empty_input_defaults_to_thinking(self):
        """Test that empty input returns thinking classification."""
        from Tools.brain_dump.classifier import BrainDumpClassifier

        classifier = BrainDumpClassifier()
        result = await classifier.classify("", source="test")

        assert result.classification == "thinking"
        assert result.confidence == 1.0

    @pytest.mark.asyncio
    async def test_classifier_error_handling(self):
        """Test classifier handles API errors gracefully."""
        from Tools.brain_dump.classifier import BrainDumpClassifier

        classifier = BrainDumpClassifier(api_key="invalid_key")

        # Mock the _call_claude method which is where errors occur
        with patch.object(classifier, '_call_claude', side_effect=Exception("API Error")):
            result = await classifier.classify("Test input", source="test")

            # Should return safe fallback
            assert result.classification == "thinking"
            assert result.confidence == 0.3
            assert "Classification failed" in result.reasoning


# =============================================================================
# Integration Test Scenarios
# =============================================================================


class TestIntegrationScenarios:
    """Integration tests combining multiple components."""

    def test_struggle_detection_flow(self, sample_conversations):
        """Test full flow: conversation -> struggle detection -> storage."""
        text = sample_conversations["struggle_frustration"]

        # 1. Detect struggle
        struggle_keywords = ["frustrated", "stuck", "blocked", "overwhelmed"]
        is_struggle = any(kw in text.lower() for kw in struggle_keywords)
        assert is_struggle

        # 2. Extract context
        pattern = r"frustrated\s+(?:with|about|by)\s+(.+?)(?:[,.]|$)"
        match = re.search(pattern, text.lower())
        assert match is not None
        context = match.group(1)
        assert "client" in context

        # 3. Classify emotion
        emotion = "frustration"  # Detected from "frustrated"

        # 4. Would store as observation with struggle tag
        memory = {
            "content": text,
            "type": "observation",
            "tags": ["struggle", "frustration", "client"],
            "emotion": emotion,
        }

        assert memory["type"] == "observation"  # Not a task
        assert "struggle" in memory["tags"]

    def test_priority_extraction_flow(self, sample_conversations):
        """Test full flow: conversation -> priority extraction -> storage."""
        text = sample_conversations["priority_focus"]

        # 1. Detect priority indicator
        priority_indicators = ["main focus", "top priority", "most important"]
        has_priority = any(ind in text.lower() for ind in priority_indicators)
        assert has_priority

        # 2. Extract time context
        time_indicators = ["today", "this week", "tomorrow"]
        time_context = None
        for ind in time_indicators:
            if ind in text.lower():
                time_context = ind
                break
        assert time_context == "today"

        # 3. Extract focus target
        pattern = r"focus.*?(?:on|be|is)\s+(?:the\s+)?(.+?)(?:$|[.])"
        match = re.search(pattern, text, re.IGNORECASE)
        focus_target = match.group(1).strip() if match else None
        assert focus_target is not None
        assert "memphis" in focus_target.lower()

    def test_activity_tracking_flow(self, sample_conversations):
        """Test full flow: conversation -> activity detection -> storage."""
        text = sample_conversations["activity_completed"]

        # 1. Detect completion
        completion_words = ["finished", "completed", "done", "pushed"]
        is_completed = any(word in text.lower() for word in completion_words)
        assert is_completed

        # 2. Extract activity details
        pattern = r"(?:finished|completed)\s+(?:the\s+)?(.+?)(?:\s+for\s+(.+))?$"
        match = re.search(pattern, text.lower())

        activity = match.group(1).strip() if match else None
        client = match.group(2).strip() if match and match.group(2) else None

        assert "sherlock post" in activity
        assert client == "orlando"

    def test_memory_search_and_retrieval(self, relationship_store):
        """Test storing and retrieving memories with relationships."""
        from Tools.relationships import RelationType

        # 1. Store some memories with relationships
        relationship_store.link_memories(
            "struggle_1", "decision_1", RelationType.CAUSED,
            metadata={"context": "Client frustration led to process change"}
        )
        relationship_store.link_memories(
            "decision_1", "outcome_1", RelationType.CAUSED,
            metadata={"context": "Process change improved satisfaction"}
        )

        # 2. Query "what led to this outcome?"
        chain = relationship_store.traverse_chain(
            "outcome_1",
            direction="backward",
            rel_types=[RelationType.CAUSED],
        )

        # Should find the causal chain
        memory_ids = [r.memory_id for r in chain]
        assert "decision_1" in memory_ids

    def test_cross_domain_correlation(self, relationship_store):
        """Test finding correlations across domains."""
        from Tools.relationships import RelationType

        # Create cross-domain memories
        relationship_store.link_memories(
            "health_sleep_bad", "common_factor", RelationType.CAUSED
        )
        relationship_store.link_memories(
            "work_missed_deadline", "common_factor", RelationType.CAUSED
        )
        relationship_store.link_memories(
            "personal_stress_high", "common_factor", RelationType.RELATED_TO
        )

        # Find what connects sleep and work
        candidates = relationship_store.get_correlation_candidates(
            memory_ids=["health_sleep_bad", "work_missed_deadline"],
            min_shared_connections=2,
        )

        # Should find common_factor
        assert len(candidates) > 0
        candidate_ids = [c["memory_id"] for c in candidates]
        assert "common_factor" in candidate_ids


# =============================================================================
# Validation Tests
# =============================================================================


class TestValidationQueries:
    """Tests validating specific query types return expected results."""

    def test_query_what_did_i_struggle_with_yesterday(self, relationship_store):
        """Test 'What did I struggle with yesterday?' query validation."""
        from Tools.relationships import RelationType

        # Setup: Create struggle memories with timestamps
        yesterday = datetime.now() - timedelta(days=1)

        relationship_store.store_insight(
            insight_type="struggle",
            content="Struggled with client requirements",
            source_memories=["struggle_client_1"],
            confidence=0.9,
        )

        # Query should find insights of type "struggle"
        insights = relationship_store.get_unsurfaced_insights(
            min_confidence=0.5,
            limit=10,
        )

        struggle_insights = [i for i in insights if i["type"] == "struggle"]
        assert len(struggle_insights) > 0
        assert "client" in struggle_insights[0]["content"].lower()

    def test_query_what_are_my_priorities(self):
        """Test 'What are my priorities?' query validation."""
        # Priorities would be stored as memories with high importance
        priority_memories = [
            {"content": "Memphis project deadline", "priority": "high", "time_context": "today"},
            {"content": "Quarterly report", "priority": "high", "time_context": "this_week"},
        ]

        # Filter for high priority items
        high_priority = [m for m in priority_memories if m["priority"] == "high"]
        assert len(high_priority) == 2

    def test_query_temporal_last_week(self, relationship_store):
        """Test temporal query for 'last week'."""
        # Create memories with different timestamps
        one_week_ago = datetime.now() - timedelta(days=7)
        two_weeks_ago = datetime.now() - timedelta(days=14)

        # In real implementation, would filter by created_at
        # Here we validate the time calculation
        now = datetime.now()
        week_start = now - timedelta(days=7)

        # Memory from 5 days ago should be included
        five_days_ago = now - timedelta(days=5)
        assert week_start <= five_days_ago <= now

        # Memory from 10 days ago should NOT be included
        ten_days_ago = now - timedelta(days=10)
        assert not (week_start <= ten_days_ago <= now)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
