"""
Unit tests for the ModelResponse dataclass.
Tests dataclass creation and metadata handling.
"""
import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from Tools.litellm import ModelResponse


# ============================================================================
# ModelResponse Dataclass Tests
# ============================================================================

class TestModelResponse:
    """Tests for the ModelResponse dataclass."""

    def test_model_response_creation(self):
        """ModelResponse should be properly initialized."""
        response = ModelResponse(
            content="Test content",
            model="claude-opus-4-5-20251101",
            provider="anthropic",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cost_usd=0.05,
            latency_ms=1500.0,
            cached=False
        )

        assert response.content == "Test content"
        assert response.model == "claude-opus-4-5-20251101"
        assert response.total_tokens == 150
        assert response.cached is False

    def test_model_response_with_metadata(self):
        """ModelResponse should support metadata."""
        response = ModelResponse(
            content="Test",
            model="test-model",
            provider="test",
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            cost_usd=0.01,
            latency_ms=100.0,
            metadata={"operation": "test", "agent": "ops"}
        )

        assert response.metadata["operation"] == "test"
        assert response.metadata["agent"] == "ops"
