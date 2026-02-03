#!/usr/bin/env python3
"""
Unit tests for commands/pa/process.py

Tests the LLM categorization function with various brain dump entries,
including mocked responses, edge cases, and error handling.
"""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from commands.pa.process import (
    analyze_brain_dump_entry,
    CATEGORIZATION_SYSTEM_PROMPT,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_litellm_client():
    """Mock LiteLLM client for testing."""
    mock_client = Mock()
    mock_client.chat = Mock()
    return mock_client


@pytest.fixture
def sample_brain_dump_entries():
    """Sample brain dump entries for testing categorization."""
    return {
        "clear_task": "Email John about the Q4 budget proposal by Friday",
        "vague_thought": "I wonder what the weather will be like tomorrow",
        "creative_idea": "Maybe we could build a mobile app for tracking daily habits",
        "worry": "I'm concerned about missing the project deadline next month",
        "long_task": "Need to prepare comprehensive documentation for the API, including setup instructions, authentication flows, endpoint descriptions, code examples in multiple languages, error handling guides, and deployment best practices. Also need to create video tutorials and update the developer portal.",
        "empty": "",
        "short": "Buy milk",
        "multi_sentence": "The project is going well. We should celebrate. Maybe Friday?",
        "question": "Should we switch to microservices architecture?",
        "note": "Meeting notes: discussed timeline, budget concerns raised, need follow-up",
    }


# =============================================================================
# Test analyze_brain_dump_entry - Basic Categorization
# =============================================================================


class TestAnalyzeBrainDumpEntry:
    """Test the LLM categorization function."""

    @pytest.mark.asyncio
    async def test_categorize_as_task(self, mock_litellm_client, sample_brain_dump_entries):
        """Test categorization of clear actionable task."""
        # Mock LLM response for a clear task
        llm_response = json.dumps({
            "category": "task",
            "should_convert_to_task": True,
            "task_title": "Email John about Q4 budget proposal",
            "task_description": sample_brain_dump_entries["clear_task"],
            "task_category": "work",
            "reasoning": "Clear action item with specific recipient and deadline"
        })
        mock_litellm_client.chat.return_value = llm_response

        with patch("commands.pa.process.get_client", return_value=mock_litellm_client):
            result = await analyze_brain_dump_entry(sample_brain_dump_entries["clear_task"])

        # Verify the result
        assert result["category"] == "task"
        assert result["should_convert_to_task"] is True
        assert result["task_title"] == "Email John about Q4 budget proposal"
        assert result["task_category"] == "work"
        assert "reasoning" in result

        # Verify client was called correctly
        mock_litellm_client.chat.assert_called_once()
        call_args = mock_litellm_client.chat.call_args
        assert call_args[1]["model"] == "anthropic/claude-3-5-haiku-20241022"
        assert call_args[1]["temperature"] == 0.3
        assert call_args[1]["system_prompt"] == CATEGORIZATION_SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_categorize_as_thought(self, mock_litellm_client, sample_brain_dump_entries):
        """Test categorization of random thought."""
        llm_response = json.dumps({
            "category": "thought",
            "should_convert_to_task": False,
            "reasoning": "Random musing without actionable component"
        })
        mock_litellm_client.chat.return_value = llm_response

        with patch("commands.pa.process.get_client", return_value=mock_litellm_client):
            result = await analyze_brain_dump_entry(sample_brain_dump_entries["vague_thought"])

        assert result["category"] == "thought"
        assert result["should_convert_to_task"] is False
        assert "reasoning" in result

    @pytest.mark.asyncio
    async def test_categorize_as_idea(self, mock_litellm_client, sample_brain_dump_entries):
        """Test categorization of creative idea."""
        llm_response = json.dumps({
            "category": "idea",
            "should_convert_to_task": False,
            "reasoning": "Creative concept that needs more refinement before becoming actionable"
        })
        mock_litellm_client.chat.return_value = llm_response

        with patch("commands.pa.process.get_client", return_value=mock_litellm_client):
            result = await analyze_brain_dump_entry(sample_brain_dump_entries["creative_idea"])

        assert result["category"] == "idea"
        assert result["should_convert_to_task"] is False

    @pytest.mark.asyncio
    async def test_categorize_as_worry(self, mock_litellm_client, sample_brain_dump_entries):
        """Test categorization of worry/concern."""
        llm_response = json.dumps({
            "category": "worry",
            "should_convert_to_task": False,
            "reasoning": "Expressed concern without clear action item"
        })
        mock_litellm_client.chat.return_value = llm_response

        with patch("commands.pa.process.get_client", return_value=mock_litellm_client):
            result = await analyze_brain_dump_entry(sample_brain_dump_entries["worry"])

        assert result["category"] == "worry"
        assert result["should_convert_to_task"] is False

    @pytest.mark.asyncio
    async def test_task_with_personal_category(self, mock_litellm_client, sample_brain_dump_entries):
        """Test task categorized as personal."""
        llm_response = json.dumps({
            "category": "task",
            "should_convert_to_task": True,
            "task_title": "Buy milk",
            "task_description": "Buy milk",
            "task_category": "personal",
            "reasoning": "Simple personal errand"
        })
        mock_litellm_client.chat.return_value = llm_response

        with patch("commands.pa.process.get_client", return_value=mock_litellm_client):
            result = await analyze_brain_dump_entry(sample_brain_dump_entries["short"])

        assert result["category"] == "task"
        assert result["task_category"] == "personal"


# =============================================================================
# Test JSON Parsing Edge Cases
# =============================================================================


class TestJsonParsing:
    """Test JSON parsing from various LLM response formats."""

    @pytest.mark.asyncio
    async def test_parse_json_with_markdown_code_blocks(self, mock_litellm_client):
        """Test parsing JSON wrapped in markdown code blocks."""
        # LLM sometimes wraps JSON in ```json ... ```
        llm_response = """```json
{
    "category": "task",
    "should_convert_to_task": true,
    "task_title": "Test task",
    "task_description": "Test description",
    "task_category": "work",
    "reasoning": "Test reasoning"
}
```"""
        mock_litellm_client.chat.return_value = llm_response

        with patch("commands.pa.process.get_client", return_value=mock_litellm_client):
            result = await analyze_brain_dump_entry("Test entry")

        assert result["category"] == "task"
        assert result["should_convert_to_task"] is True

    @pytest.mark.asyncio
    async def test_parse_json_with_generic_code_blocks(self, mock_litellm_client):
        """Test parsing JSON wrapped in generic code blocks."""
        llm_response = """```
{
    "category": "thought",
    "should_convert_to_task": false,
    "reasoning": "Just a thought"
}
```"""
        mock_litellm_client.chat.return_value = llm_response

        with patch("commands.pa.process.get_client", return_value=mock_litellm_client):
            result = await analyze_brain_dump_entry("Random thought")

        assert result["category"] == "thought"
        assert result["should_convert_to_task"] is False

    @pytest.mark.asyncio
    async def test_parse_plain_json(self, mock_litellm_client):
        """Test parsing plain JSON without code blocks."""
        llm_response = json.dumps({
            "category": "idea",
            "should_convert_to_task": False,
            "reasoning": "Creative idea"
        })
        mock_litellm_client.chat.return_value = llm_response

        with patch("commands.pa.process.get_client", return_value=mock_litellm_client):
            result = await analyze_brain_dump_entry("Cool idea")

        assert result["category"] == "idea"


# =============================================================================
# Test Error Handling
# =============================================================================


class TestErrorHandling:
    """Test error handling in categorization."""

    @pytest.mark.asyncio
    async def test_invalid_json_fallback(self, mock_litellm_client):
        """Test fallback when LLM returns invalid JSON."""
        mock_litellm_client.chat.return_value = "This is not valid JSON"

        with patch("commands.pa.process.get_client", return_value=mock_litellm_client):
            result = await analyze_brain_dump_entry("Test entry")

        # Should fallback to thought/archive
        assert result["category"] == "thought"
        assert result["should_convert_to_task"] is False
        assert "Failed to parse LLM response" in result["reasoning"]

    @pytest.mark.asyncio
    async def test_missing_required_fields(self, mock_litellm_client):
        """Test handling of response missing required fields."""
        llm_response = json.dumps({
            "reasoning": "Some reasoning but missing category and should_convert_to_task"
        })
        mock_litellm_client.chat.return_value = llm_response

        with patch("commands.pa.process.get_client", return_value=mock_litellm_client):
            result = await analyze_brain_dump_entry("Test entry")

        # Should fallback to thought/archive
        assert result["category"] == "thought"
        assert result["should_convert_to_task"] is False
        assert "Error during categorization" in result["reasoning"]

    @pytest.mark.asyncio
    async def test_invalid_category_value(self, mock_litellm_client):
        """Test handling of invalid category value."""
        llm_response = json.dumps({
            "category": "invalid_category",
            "should_convert_to_task": False,
            "reasoning": "Test"
        })
        mock_litellm_client.chat.return_value = llm_response

        with patch("commands.pa.process.get_client", return_value=mock_litellm_client):
            result = await analyze_brain_dump_entry("Test entry")

        # Should fallback to thought/archive
        assert result["category"] == "thought"
        assert result["should_convert_to_task"] is False

    @pytest.mark.asyncio
    async def test_missing_task_fields_when_converting(self, mock_litellm_client):
        """Test handling when should_convert_to_task=true but task fields missing."""
        llm_response = json.dumps({
            "category": "task",
            "should_convert_to_task": True,
            # Missing task_title and task_category
            "reasoning": "Should be a task"
        })
        mock_litellm_client.chat.return_value = llm_response

        with patch("commands.pa.process.get_client", return_value=mock_litellm_client):
            result = await analyze_brain_dump_entry("Test entry")

        # Should fallback to thought/archive due to validation error
        assert result["category"] == "thought"
        assert result["should_convert_to_task"] is False

    @pytest.mark.asyncio
    async def test_invalid_task_category_defaults_to_personal(self, mock_litellm_client):
        """Test that invalid task_category defaults to personal."""
        llm_response = json.dumps({
            "category": "task",
            "should_convert_to_task": True,
            "task_title": "Test task",
            "task_description": "Test description",
            "task_category": "invalid_category",  # Invalid
            "reasoning": "Test"
        })
        mock_litellm_client.chat.return_value = llm_response

        with patch("commands.pa.process.get_client", return_value=mock_litellm_client):
            result = await analyze_brain_dump_entry("Test entry")

        # Should default task_category to personal
        assert result["task_category"] == "personal"

    @pytest.mark.asyncio
    async def test_missing_task_description_uses_original_content(self, mock_litellm_client):
        """Test that missing task_description uses original content."""
        content = "Original brain dump content"
        llm_response = json.dumps({
            "category": "task",
            "should_convert_to_task": True,
            "task_title": "Test task",
            # Missing task_description
            "task_category": "work",
            "reasoning": "Test"
        })
        mock_litellm_client.chat.return_value = llm_response

        with patch("commands.pa.process.get_client", return_value=mock_litellm_client):
            result = await analyze_brain_dump_entry(content)

        # Should use original content as task_description
        assert result["task_description"] == content

    @pytest.mark.asyncio
    async def test_client_exception_fallback(self, mock_litellm_client):
        """Test fallback when client raises exception."""
        mock_litellm_client.chat.side_effect = Exception("API connection error")

        with patch("commands.pa.process.get_client", return_value=mock_litellm_client):
            result = await analyze_brain_dump_entry("Test entry")

        # Should fallback to thought/archive
        assert result["category"] == "thought"
        assert result["should_convert_to_task"] is False
        assert "Error during categorization" in result["reasoning"]


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases in brain dump processing."""

    @pytest.mark.asyncio
    async def test_empty_entry(self, mock_litellm_client):
        """Test processing empty brain dump entry."""
        llm_response = json.dumps({
            "category": "thought",
            "should_convert_to_task": False,
            "reasoning": "Empty entry, nothing to process"
        })
        mock_litellm_client.chat.return_value = llm_response

        with patch("commands.pa.process.get_client", return_value=mock_litellm_client):
            result = await analyze_brain_dump_entry("")

        assert result["category"] == "thought"
        assert result["should_convert_to_task"] is False

    @pytest.mark.asyncio
    async def test_very_long_entry(self, mock_litellm_client):
        """Test processing very long brain dump entry."""
        # Create a very long entry (> 1000 characters)
        long_entry = "This is a very long brain dump entry. " * 50

        llm_response = json.dumps({
            "category": "task",
            "should_convert_to_task": True,
            "task_title": "Process the long documentation request",
            "task_description": long_entry,
            "task_category": "work",
            "reasoning": "Clear task despite length"
        })
        mock_litellm_client.chat.return_value = llm_response

        with patch("commands.pa.process.get_client", return_value=mock_litellm_client):
            result = await analyze_brain_dump_entry(long_entry)

        assert result["category"] == "task"
        assert result["should_convert_to_task"] is True
        # Verify client received the full content
        call_args = mock_litellm_client.chat.call_args
        assert long_entry in call_args[1]["prompt"]

    @pytest.mark.asyncio
    async def test_special_characters_in_entry(self, mock_litellm_client):
        """Test processing entry with special characters."""
        entry_with_special_chars = "Test with émojis 🎉 and spëcial çhars & symbols: @#$%"

        llm_response = json.dumps({
            "category": "thought",
            "should_convert_to_task": False,
            "reasoning": "Just a test entry"
        })
        mock_litellm_client.chat.return_value = llm_response

        with patch("commands.pa.process.get_client", return_value=mock_litellm_client):
            result = await analyze_brain_dump_entry(entry_with_special_chars)

        assert result["category"] == "thought"
        # Should handle special characters without error

    @pytest.mark.asyncio
    async def test_multiline_entry(self, mock_litellm_client):
        """Test processing multiline brain dump entry."""
        multiline_entry = """This is a multiline entry.

        It has multiple paragraphs.

        And should be processed correctly."""

        llm_response = json.dumps({
            "category": "idea",
            "should_convert_to_task": False,
            "reasoning": "Multiline thought"
        })
        mock_litellm_client.chat.return_value = llm_response

        with patch("commands.pa.process.get_client", return_value=mock_litellm_client):
            result = await analyze_brain_dump_entry(multiline_entry)

        assert result["category"] == "idea"
        # Verify multiline content was sent to client
        call_args = mock_litellm_client.chat.call_args
        assert multiline_entry in call_args[1]["prompt"]


# =============================================================================
# Test Categorization Consistency
# =============================================================================


class TestCategorizationConsistency:
    """Test that categorization follows expected patterns."""

    @pytest.mark.asyncio
    async def test_system_prompt_is_used(self, mock_litellm_client):
        """Test that the categorization system prompt is used."""
        llm_response = json.dumps({
            "category": "task",
            "should_convert_to_task": True,
            "task_title": "Test",
            "task_description": "Test",
            "task_category": "work",
            "reasoning": "Test"
        })
        mock_litellm_client.chat.return_value = llm_response

        with patch("commands.pa.process.get_client", return_value=mock_litellm_client):
            await analyze_brain_dump_entry("Test task")

        # Verify system prompt was used
        call_args = mock_litellm_client.chat.call_args
        assert call_args[1]["system_prompt"] == CATEGORIZATION_SYSTEM_PROMPT
        assert "CONSERVATIVE" in CATEGORIZATION_SYSTEM_PROMPT.upper()
        assert "thought" in CATEGORIZATION_SYSTEM_PROMPT
        assert "task" in CATEGORIZATION_SYSTEM_PROMPT
        assert "idea" in CATEGORIZATION_SYSTEM_PROMPT
        assert "worry" in CATEGORIZATION_SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_temperature_is_low_for_consistency(self, mock_litellm_client):
        """Test that temperature is set low for consistent categorization."""
        llm_response = json.dumps({
            "category": "thought",
            "should_convert_to_task": False,
            "reasoning": "Test"
        })
        mock_litellm_client.chat.return_value = llm_response

        with patch("commands.pa.process.get_client", return_value=mock_litellm_client):
            await analyze_brain_dump_entry("Test")

        # Verify low temperature for consistency
        call_args = mock_litellm_client.chat.call_args
        assert call_args[1]["temperature"] == 0.3

    @pytest.mark.asyncio
    async def test_uses_haiku_model(self, mock_litellm_client):
        """Test that Haiku model is used for fast categorization."""
        llm_response = json.dumps({
            "category": "thought",
            "should_convert_to_task": False,
            "reasoning": "Test"
        })
        mock_litellm_client.chat.return_value = llm_response

        with patch("commands.pa.process.get_client", return_value=mock_litellm_client):
            await analyze_brain_dump_entry("Test")

        # Verify Haiku model is used
        call_args = mock_litellm_client.chat.call_args
        assert call_args[1]["model"] == "anthropic/claude-3-5-haiku-20241022"

    @pytest.mark.asyncio
    async def test_max_tokens_is_reasonable(self, mock_litellm_client):
        """Test that max_tokens is set to reasonable value for categorization."""
        llm_response = json.dumps({
            "category": "thought",
            "should_convert_to_task": False,
            "reasoning": "Test"
        })
        mock_litellm_client.chat.return_value = llm_response

        with patch("commands.pa.process.get_client", return_value=mock_litellm_client):
            await analyze_brain_dump_entry("Test")

        # Verify max_tokens is set (categorization doesn't need many tokens)
        call_args = mock_litellm_client.chat.call_args
        assert call_args[1]["max_tokens"] == 500
