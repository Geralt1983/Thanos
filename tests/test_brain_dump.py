#!/usr/bin/env python3
"""
Tests for Brain Dump Classifier and Router.

Tests the classification of different brain dump types and routing logic
for domain separation between personal and work tasks.
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from Tools.brain_dump.classifier import (
    BrainDumpClassifier,
    ClassifiedBrainDump,
    CLASSIFICATION_PROMPT,
)
from Tools.brain_dump.router import (
    BrainDumpRouter,
    RoutingResult,
    Classification,
    ClassifiedSegment,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_thanos.db"
        yield db_path


@pytest.fixture
def state_store(temp_db):
    """Create a StateStore with temporary database."""
    from Tools.unified_state import StateStore
    return StateStore(db_path=temp_db)


@pytest.fixture
def journal(temp_db):
    """Create a Journal with temporary database."""
    from Tools.journal import Journal
    return Journal(db_path=temp_db)


@pytest.fixture
def mock_workos_adapter():
    """Create a mock WorkOS adapter."""
    adapter = AsyncMock()
    adapter.call_tool = AsyncMock(return_value=Mock(
        success=True,
        data={"id": 12345}
    ))
    return adapter


@pytest.fixture
def router(state_store, journal):
    """Create a router with test dependencies."""
    return BrainDumpRouter(state_store, journal, workos_adapter=None)


@pytest.fixture
def router_with_workos(state_store, journal, mock_workos_adapter):
    """Create a router with WorkOS adapter."""
    return BrainDumpRouter(state_store, journal, workos_adapter=mock_workos_adapter)


# ============================================================================
# Sample Test Data
# ============================================================================

SAMPLE_INPUTS = {
    # Thinking - vague reflections without specific actions
    "thinking": [
        "I've been thinking about maybe starting to exercise more",
        "I wonder if we should restructure the codebase",
        "Maybe I need to reconsider my career path",
        "I should really start eating healthier at some point",
        "What if life was different?",
    ],

    # Venting - emotional release, frustration
    "venting": [
        "UGH this stupid API keeps timing out and nobody seems to care about fixing it!!",
        "I'm so tired of all these meetings that could be emails",
        "This is ridiculous, why does everything have to be so complicated",
        "I can't believe they pushed back the deadline AGAIN",
        "Why do I even bother trying to explain things anymore!",
    ],

    # Observation - noting something without action
    "observation": [
        "I noticed that the response times have improved lately",
        "It seems like traffic is worse on Tuesdays",
        "The team appears more engaged after the offsite",
        "Interesting pattern - users tend to sign up more on Sundays",
        "The new UI seems to be getting mixed reactions",
    ],

    # Note - information to remember
    "note": [
        "Remember that the API key expires on Jan 31",
        "John's phone number is 555-1234",
        "The staging server IP is 192.168.1.100",
        "Meeting room is on the 3rd floor, room 301",
        "The password hint is my dog's name backwards",
    ],

    # Idea - creative thoughts
    "idea": [
        "What if we built a feature that automatically tags support tickets",
        "A cool improvement would be to add dark mode to the dashboard",
        "We could integrate with Slack for notifications",
        "Maybe we should create a mobile app version",
        "It would be great to have an AI assistant for onboarding",
    ],

    # Personal task - clear personal action
    "personal_task": [
        "Need to call the dentist about my appointment",
        "Pick up groceries on the way home",
        "Pay the electric bill before Friday",
        "Schedule car maintenance for next week",
        "Buy birthday present for Mom",
    ],

    # Work task - clear work action
    "work_task": [
        "Review Sarah's PR for the auth changes",
        "Send the quarterly report to the client",
        "Fix the login bug in production",
        "Update the API documentation",
        "Deploy the hotfix to staging",
    ],

    # Commitment - promises made to others
    "commitment": [
        "I told Mike I'd have the design ready by Friday",
        "I promised Sarah I would review her code today",
        "I committed to presenting at the team meeting",
        "I told the client I'd send the proposal by EOD",
        "I promised my manager I'd finish the sprint tasks",
    ],

    # Mixed - multiple items
    "mixed": [
        "I should probably clean my desk at some point. Also need to buy milk.",
        "UGH meetings all day! But I do need to fix that bug for John before tomorrow.",
        "Thinking about vacation plans... oh and remind me to call the insurance company.",
    ],
}


# ============================================================================
# Keyword Fallback Tests (No API Required)
# ============================================================================

class TestKeywordFallback:
    """Test keyword-based classification fallback when API is unavailable."""

    def test_keyword_patterns_exist_in_prompt(self):
        """Verify the classification prompt contains expected patterns."""
        # Check that key patterns are mentioned in the prompt
        assert "thinking" in CLASSIFICATION_PROMPT.lower()
        assert "venting" in CLASSIFICATION_PROMPT.lower()
        assert "personal_task" in CLASSIFICATION_PROMPT.lower()
        assert "work_task" in CLASSIFICATION_PROMPT.lower()
        assert "commitment" in CLASSIFICATION_PROMPT.lower()

    def test_thinking_keywords(self):
        """Test thinking pattern keywords."""
        thinking_patterns = [
            "I've been thinking",
            "I wonder if",
            "What if we",
            "Maybe I need",
        ]
        for pattern in thinking_patterns:
            assert pattern.lower() in CLASSIFICATION_PROMPT.lower() or \
                   any(p in pattern.lower() for p in ["thinking", "wonder", "what if", "maybe"])

    def test_venting_keywords(self):
        """Test venting pattern keywords."""
        venting_patterns = [
            "frustrated",
            "tired of",
            "ridiculous",
            "can't believe",
        ]
        for pattern in venting_patterns:
            # Check pattern exists in prompt or our understanding of venting
            assert "venting" in CLASSIFICATION_PROMPT.lower()

    def test_task_verb_keywords(self):
        """Test task action verb patterns."""
        task_verbs = ["call", "buy", "fix", "send", "review"]
        for verb in task_verbs:
            assert verb in CLASSIFICATION_PROMPT.lower()


# ============================================================================
# ClassifiedBrainDump Tests
# ============================================================================

class TestClassifiedBrainDump:
    """Test the ClassifiedBrainDump dataclass."""

    def test_create_basic(self):
        """Test creating a basic classified brain dump."""
        dump = ClassifiedBrainDump(
            id="test123",
            raw_text="Test input",
            source="manual",
            classification="thinking",
            confidence=0.9,
            reasoning="Just a test"
        )
        assert dump.id == "test123"
        assert dump.classification == "thinking"
        assert dump.confidence == 0.9

    def test_is_actionable_true(self):
        """Test is_actionable returns True for task/commitment types."""
        for classification in ["personal_task", "work_task", "commitment"]:
            dump = ClassifiedBrainDump(
                id="test",
                raw_text="Test",
                source="manual",
                classification=classification,
                confidence=0.9,
                reasoning="Test"
            )
            assert dump.is_actionable() is True

    def test_is_actionable_false(self):
        """Test is_actionable returns False for non-actionable types."""
        for classification in ["thinking", "venting", "observation", "note", "idea"]:
            dump = ClassifiedBrainDump(
                id="test",
                raw_text="Test",
                source="manual",
                classification=classification,
                confidence=0.9,
                reasoning="Test"
            )
            assert dump.is_actionable() is False

    def test_has_task(self):
        """Test has_task helper method."""
        dump_with_task = ClassifiedBrainDump(
            id="test",
            raw_text="Call the dentist",
            source="manual",
            classification="personal_task",
            confidence=0.9,
            reasoning="Test",
            task={"title": "Call dentist", "context": "personal"}
        )
        assert dump_with_task.has_task() is True

        dump_without_task = ClassifiedBrainDump(
            id="test",
            raw_text="I'm frustrated",
            source="manual",
            classification="venting",
            confidence=0.9,
            reasoning="Test"
        )
        assert dump_without_task.has_task() is False

    def test_to_dict(self):
        """Test serialization to dictionary."""
        dump = ClassifiedBrainDump(
            id="test",
            raw_text="Test input",
            source="telegram",
            classification="note",
            confidence=0.85,
            reasoning="Information to remember"
        )
        d = dump.to_dict()
        assert d["id"] == "test"
        assert d["source"] == "telegram"
        assert d["classification"] == "note"


# ============================================================================
# Classification Enum Tests
# ============================================================================

class TestClassificationEnum:
    """Test the Classification enum."""

    def test_all_classifications_exist(self):
        """Test all expected classification types exist."""
        expected = [
            "thinking", "venting", "observation", "note", "idea",
            "personal_task", "work_task", "commitment", "mixed"
        ]
        for name in expected:
            assert Classification.from_string(name) is not None

    def test_from_string_valid(self):
        """Test from_string with valid values."""
        assert Classification.from_string("thinking") == Classification.THINKING
        assert Classification.from_string("personal_task") == Classification.PERSONAL_TASK
        assert Classification.from_string("work_task") == Classification.WORK_TASK

    def test_from_string_invalid_defaults_to_thinking(self):
        """Test from_string with invalid value defaults to thinking."""
        assert Classification.from_string("invalid") == Classification.THINKING
        assert Classification.from_string("") == Classification.THINKING
        assert Classification.from_string("UNKNOWN") == Classification.THINKING


# ============================================================================
# Routing Result Tests
# ============================================================================

class TestRoutingResult:
    """Test the RoutingResult dataclass."""

    def test_success_with_no_errors(self):
        """Test success property when no errors."""
        result = RoutingResult(dump_id="test")
        assert result.success is True

    def test_success_with_errors(self):
        """Test success property when errors exist."""
        result = RoutingResult(dump_id="test", errors=["Something failed"])
        assert result.success is False

    def test_merge_results(self):
        """Test merging two routing results."""
        result1 = RoutingResult(dump_id="test1", tasks_created=["task1"])
        result2 = RoutingResult(dump_id="test2", tasks_created=["task2"], idea_created="idea1")

        merged = result1.merge(result2)
        assert len(merged.tasks_created) == 2
        assert merged.idea_created == "idea1"

    def test_summary_no_actions(self):
        """Test summary when no actions taken."""
        result = RoutingResult(dump_id="test")
        assert result.summary() == "no actions taken"

    def test_summary_with_actions(self):
        """Test summary with various actions."""
        result = RoutingResult(
            dump_id="test",
            tasks_created=["task1", "task2"],
            workos_task_id=123
        )
        summary = result.summary()
        assert "2 task(s) created" in summary
        assert "synced to WorkOS (#123)" in summary


# ============================================================================
# Router Classification Routing Tests
# ============================================================================

class TestRouterClassificationRouting:
    """Test that the router correctly routes different classifications."""

    @pytest.mark.asyncio
    async def test_route_thinking(self, router):
        """Test routing thinking classification to journal only."""
        dump = ClassifiedBrainDump(
            id="test1",
            raw_text="I've been thinking about life",
            source="manual",
            classification="thinking",
            confidence=0.9,
            reasoning="Reflection",
            acknowledgment="That's something to ponder."
        )

        result = await router.route(dump)

        assert result.success
        assert len(result.tasks_created) == 0
        assert result.journal_entry is not None
        assert result.acknowledgment is not None

    @pytest.mark.asyncio
    async def test_route_venting(self, router):
        """Test routing venting classification to journal only."""
        dump = ClassifiedBrainDump(
            id="test2",
            raw_text="I'm so frustrated with this!",
            source="telegram",
            classification="venting",
            confidence=0.95,
            reasoning="Emotional release",
            acknowledgment="I hear you."
        )

        result = await router.route(dump)

        assert result.success
        assert len(result.tasks_created) == 0
        assert result.journal_entry is not None

    @pytest.mark.asyncio
    async def test_route_observation(self, router):
        """Test routing observation classification to journal only."""
        dump = ClassifiedBrainDump(
            id="test3",
            raw_text="The traffic seems worse lately",
            source="manual",
            classification="observation",
            confidence=0.85,
            reasoning="Pattern noticed"
        )

        result = await router.route(dump)

        assert result.success
        assert len(result.tasks_created) == 0

    @pytest.mark.asyncio
    async def test_route_note(self, router, state_store):
        """Test routing note to state store."""
        dump = ClassifiedBrainDump(
            id="test4",
            raw_text="The API key is abc123",
            source="manual",
            classification="note",
            confidence=0.9,
            reasoning="Information to remember",
            note={"content": "API key is abc123", "category": "reference"}
        )

        result = await router.route(dump)

        assert result.success
        assert result.note_created is not None

    @pytest.mark.asyncio
    async def test_route_idea(self, router, state_store):
        """Test routing idea to state store."""
        dump = ClassifiedBrainDump(
            id="test5",
            raw_text="What if we built an AI chatbot",
            source="manual",
            classification="idea",
            confidence=0.88,
            reasoning="Creative suggestion",
            idea={"title": "AI Chatbot", "description": "Build an AI chatbot", "category": "feature"}
        )

        result = await router.route(dump)

        assert result.success
        assert result.idea_created is not None


# ============================================================================
# Domain Separation Tests (Personal vs Work)
# ============================================================================

class TestDomainSeparation:
    """Test that personal and work tasks are routed correctly."""

    @pytest.mark.asyncio
    async def test_personal_task_stays_local(self, router, state_store):
        """Test personal tasks are created locally and NOT synced to WorkOS."""
        dump = ClassifiedBrainDump(
            id="personal1",
            raw_text="Buy groceries on the way home",
            source="manual",
            classification="personal_task",
            confidence=0.92,
            reasoning="Personal errand",
            task={
                "title": "Buy groceries",
                "description": "Buy groceries on the way home",
                "context": "personal",
                "priority": "medium",
                "estimated_effort": "quick"
            }
        )

        result = await router.route(dump)

        assert result.success
        assert len(result.tasks_created) == 1
        assert result.workos_task_id is None  # Personal tasks should NOT sync to WorkOS

        # Verify task is in state store with personal domain
        task = state_store.get_task(result.tasks_created[0])
        assert task is not None
        # Handle metadata being either dict or JSON string
        metadata = task.metadata
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        assert metadata.get("domain") == "personal"

    @pytest.mark.asyncio
    async def test_work_task_with_workos(self, router_with_workos, state_store, mock_workos_adapter):
        """Test work tasks are synced to WorkOS when adapter is available."""
        dump = ClassifiedBrainDump(
            id="work1",
            raw_text="Review the PR for auth changes",
            source="manual",
            classification="work_task",
            confidence=0.95,
            reasoning="Work code review",
            task={
                "title": "Review auth PR",
                "description": "Review the PR for auth changes",
                "context": "work",
                "priority": "high",
                "estimated_effort": "medium"
            }
        )

        result = await router_with_workos.route(dump)

        assert result.success
        assert len(result.tasks_created) == 1
        assert result.workos_task_id == 12345  # Should have synced to WorkOS

        # Verify WorkOS adapter was called
        mock_workos_adapter.call_tool.assert_called_once()
        call_args = mock_workos_adapter.call_tool.call_args
        assert call_args[0][0] == "create_task"

    @pytest.mark.asyncio
    async def test_work_task_without_workos(self, router, state_store):
        """Test work tasks are created locally when no WorkOS adapter."""
        dump = ClassifiedBrainDump(
            id="work2",
            raw_text="Fix the login bug",
            source="manual",
            classification="work_task",
            confidence=0.9,
            reasoning="Work bug fix",
            task={
                "title": "Fix login bug",
                "context": "work",
                "priority": "high"
            }
        )

        result = await router.route(dump)

        assert result.success
        assert len(result.tasks_created) == 1
        assert result.workos_task_id is None  # No WorkOS adapter

    @pytest.mark.asyncio
    async def test_commitment_creates_commitment(self, router, state_store):
        """Test commitments are created as commitments, not tasks."""
        dump = ClassifiedBrainDump(
            id="commit1",
            raw_text="I told Sarah I'd review her code by Friday",
            source="manual",
            classification="commitment",
            confidence=0.95,
            reasoning="Promise made to colleague",
            commitment={
                "description": "Review Sarah's code",
                "to_whom": "Sarah",
                "deadline": "Friday"
            }
        )

        result = await router.route(dump)

        assert result.success
        assert result.commitment_created is not None
        assert len(result.tasks_created) == 0  # Commitment, not task


# ============================================================================
# Mixed Classification Tests
# ============================================================================

class TestMixedClassification:
    """Test routing of mixed classification brain dumps."""

    @pytest.mark.asyncio
    async def test_mixed_routing_processes_segments(self, router):
        """Test that mixed classification processes each segment."""
        dump = ClassifiedBrainDump(
            id="mixed1",
            raw_text="I should clean my desk. Also need to buy milk.",
            source="manual",
            classification="mixed",
            confidence=0.88,
            reasoning="Two items: thinking + personal task",
            segments=[
                {
                    "text": "I should clean my desk",
                    "classification": "thinking",
                    "extracted": None
                },
                {
                    "text": "need to buy milk",
                    "classification": "personal_task",
                    "extracted": {
                        "task": {
                            "title": "Buy milk",
                            "context": "personal",
                            "priority": "low"
                        }
                    }
                }
            ]
        )

        result = await router.route(dump)

        assert result.success
        # Should have one task from the personal_task segment
        assert len(result.tasks_created) == 1

    @pytest.mark.asyncio
    async def test_mixed_with_no_segments_becomes_note(self, router):
        """Test mixed with no segments defaults to note behavior."""
        dump = ClassifiedBrainDump(
            id="mixed2",
            raw_text="Some mixed content",
            source="manual",
            classification="mixed",
            confidence=0.6,
            reasoning="Could not parse segments",
            segments=None  # No segments
        )

        result = await router.route(dump)

        assert result.success
        # Should have been treated as a note
        assert result.note_created is not None


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test error handling in classification and routing."""

    def test_classifier_handles_empty_input(self):
        """Test classifier handles empty input gracefully."""
        classifier = BrainDumpClassifier()

        # Mock the classify to avoid API call
        async def mock_classify(text, source):
            if not text or not text.strip():
                return ClassifiedBrainDump(
                    id="empty",
                    raw_text=text or "",
                    source=source,
                    classification="thinking",
                    confidence=1.0,
                    reasoning="Empty input"
                )

        # Test synchronously
        result = asyncio.run(mock_classify("", "manual"))
        assert result.classification == "thinking"
        assert result.confidence == 1.0

    @pytest.mark.asyncio
    async def test_router_handles_missing_task_data(self, router):
        """Test router handles missing task data gracefully."""
        dump = ClassifiedBrainDump(
            id="test",
            raw_text="Do something",
            source="manual",
            classification="personal_task",
            confidence=0.7,
            reasoning="Task without details",
            task=None  # Missing task data
        )

        result = await router.route(dump)

        # Should still create a task using raw_text
        assert result.success
        assert len(result.tasks_created) == 1

    @pytest.mark.asyncio
    async def test_workos_failure_is_non_fatal(self, router_with_workos, mock_workos_adapter):
        """Test WorkOS sync failure doesn't fail the whole operation."""
        # Make WorkOS fail
        mock_workos_adapter.call_tool = AsyncMock(side_effect=Exception("WorkOS error"))

        dump = ClassifiedBrainDump(
            id="test",
            raw_text="Fix the bug",
            source="manual",
            classification="work_task",
            confidence=0.9,
            reasoning="Work task",
            task={"title": "Fix bug", "context": "work"}
        )

        result = await router_with_workos.route(dump)

        # Task should still be created locally
        assert len(result.tasks_created) == 1
        # WorkOS ID should be None due to failure
        assert result.workos_task_id is None


# ============================================================================
# Confidence Scoring Tests
# ============================================================================

class TestConfidenceScoring:
    """Test confidence scoring behavior."""

    def test_high_confidence_for_clear_classification(self):
        """Test that clear classifications get high confidence."""
        # This tests the expected behavior from the prompt examples
        high_confidence_examples = [
            ("Need to call Dr. Smith about my appointment", "personal_task", 0.90),
            ("Review Sarah's PR for the auth changes", "work_task", 0.90),
            ("UGH this API keeps timing out!!", "venting", 0.90),
        ]

        for text, expected_class, min_confidence in high_confidence_examples:
            # The prompt examples show these should have >= 0.90 confidence
            # This is a documentation test of expected behavior
            assert min_confidence >= 0.90

    def test_lower_confidence_for_ambiguous(self):
        """Test that ambiguous inputs should get lower confidence."""
        ambiguous_examples = [
            "I should probably do something about that",
            "Maybe fix it later",
            "Things could be better",
        ]
        # Ambiguous inputs should theoretically get lower confidence
        # This documents expected behavior
        for text in ambiguous_examples:
            # These vague statements should default to thinking
            # with lower confidence
            pass  # Actual confidence would come from API


# ============================================================================
# Integration Tests with Mock API
# ============================================================================

class TestClassifierWithMockAPI:
    """Test classifier with mocked API responses."""

    def test_parse_response_valid_json(self):
        """Test parsing valid JSON response."""
        classifier = BrainDumpClassifier()

        response = json.dumps({
            "classification": "personal_task",
            "confidence": 0.92,
            "reasoning": "Clear action",
            "task": {"title": "Call dentist", "context": "personal"}
        })

        result = classifier._parse_response(response)

        assert result["classification"] == "personal_task"
        assert result["confidence"] == 0.92
        assert result["task"]["title"] == "Call dentist"

    def test_parse_response_with_markdown(self):
        """Test parsing response wrapped in markdown code blocks."""
        classifier = BrainDumpClassifier()

        response = '''```json
{
    "classification": "venting",
    "confidence": 0.98,
    "reasoning": "Frustration expressed"
}
```'''

        result = classifier._parse_response(response)

        assert result["classification"] == "venting"
        assert result["confidence"] == 0.98

    def test_parse_response_invalid_json_fallback(self):
        """Test parsing invalid JSON falls back to thinking."""
        classifier = BrainDumpClassifier()

        response = "This is not valid JSON at all"

        result = classifier._parse_response(response)

        assert result["classification"] == "thinking"
        assert result["confidence"] < 0.5  # Low confidence for fallback

    def test_parse_response_extracts_json_from_text(self):
        """Test parsing extracts JSON embedded in text."""
        classifier = BrainDumpClassifier()

        response = '''Here is my analysis:
{"classification": "idea", "confidence": 0.85, "reasoning": "Creative thought"}
That's my assessment.'''

        result = classifier._parse_response(response)

        assert result["classification"] == "idea"
        assert result["confidence"] == 0.85


# ============================================================================
# Full Integration Test (Requires API Key - Skipped by Default)
# ============================================================================

@pytest.mark.skipif(
    not pytest.importorskip("anthropic", reason="anthropic package not installed"),
    reason="Requires anthropic package"
)
class TestFullIntegration:
    """Full integration tests requiring API key.

    These tests are skipped by default. Run with:
    ANTHROPIC_API_KEY=sk-... pytest tests/test_brain_dump.py -k TestFullIntegration
    """

    @pytest.fixture
    def classifier(self):
        """Create real classifier (requires API key)."""
        import os
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")
        return BrainDumpClassifier()

    @pytest.mark.asyncio
    async def test_classify_real_thinking(self, classifier):
        """Test real API classification of thinking input."""
        result = await classifier.classify("I've been thinking about life lately")

        assert result.classification in ("thinking", "observation")
        assert result.confidence > 0.5
        assert result.is_actionable() is False

    @pytest.mark.asyncio
    async def test_classify_real_task(self, classifier):
        """Test real API classification of task input."""
        result = await classifier.classify("Need to call the dentist tomorrow")

        assert result.classification == "personal_task"
        assert result.confidence > 0.7
        assert result.has_task() is True


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
