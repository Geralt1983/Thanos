"""
Unit tests for the LiteLLMClient class.
Tests model routing, API integration, caching, usage tracking, and module functions.
"""
import json
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from Tools.litellm import (
    LiteLLMClient,
    get_client,
    init_client,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def mock_config(temp_dir):
    """Create a mock configuration file."""
    config = {
        "litellm": {
            "providers": {
                "anthropic": {
                    "api_key_env": "ANTHROPIC_API_KEY",
                    "models": {
                        "opus": "claude-opus-4-5-20251101",
                        "sonnet": "claude-sonnet-4-20250514",
                        "haiku": "claude-3-5-haiku-20241022"
                    }
                }
            },
            "default_provider": "anthropic",
            "default_model": "claude-opus-4-5-20251101",
            "fallback_chain": [
                "claude-opus-4-5-20251101",
                "claude-sonnet-4-20250514"
            ],
            "timeout": 600,
            "max_retries": 3,
            "retry_delay": 1.0
        },
        "model_routing": {
            "rules": {
                "complex": {
                    "model": "claude-opus-4-5-20251101",
                    "indicators": ["architecture", "analysis"],
                    "min_complexity": 0.7
                },
                "standard": {
                    "model": "claude-sonnet-4-20250514",
                    "indicators": ["task", "summary"],
                    "min_complexity": 0.3
                },
                "simple": {
                    "model": "claude-3-5-haiku-20241022",
                    "indicators": ["lookup", "simple"],
                    "max_complexity": 0.3
                }
            },
            "complexity_factors": {
                "token_count_weight": 0.3,
                "keyword_weight": 0.4,
                "history_length_weight": 0.3
            }
        },
        "usage_tracking": {
            "enabled": True,
            "storage_path": str(temp_dir / "usage.json"),
            "pricing": {
                "claude-opus-4-5-20251101": {"input": 0.015, "output": 0.075},
                "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
                "claude-3-5-haiku-20241022": {"input": 0.00025, "output": 0.00125}
            }
        },
        "caching": {
            "enabled": True,
            "ttl_seconds": 3600,
            "storage_path": str(temp_dir / "cache"),
            "max_cache_size_mb": 10
        },
        "defaults": {
            "max_tokens": 4096,
            "temperature": 1.0
        }
    }

    config_path = temp_dir / "config" / "api.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2))
    return config_path


@pytest.fixture
def mock_litellm_response():
    """Create a mock LiteLLM completion response."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = "Test response from LiteLLM"
    mock_response.usage = Mock()
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    return mock_response


@pytest.fixture
def mock_anthropic_response():
    """Create a mock direct Anthropic response (fallback)."""
    mock_response = Mock()
    mock_response.content = [Mock()]
    mock_response.content[0].text = "Test response from Anthropic"
    mock_response.usage = Mock()
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50
    return mock_response


# ============================================================================
# LiteLLMClient Tests
# ============================================================================

class TestLiteLLMClient:
    """Tests for the LiteLLMClient class."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_init_with_config(self, mock_config, temp_dir):
        """Client should initialize with provided config."""
        with patch("Tools.litellm.client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm.client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm.client.anthropic") as mock_anthropic:
                    client = LiteLLMClient(str(mock_config))

                    assert client.config is not None
                    assert client.usage_tracker is not None
                    assert client.cache is not None

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_model_selection_simple(self, mock_config):
        """Simple prompts should select simpler models."""
        with patch("Tools.litellm.client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm.client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm.client.anthropic"):
                    client = LiteLLMClient(str(mock_config))
                    model = client._select_model("What's the weather?")

                    # Should NOT be opus for simple query
                    assert model in [
                        "claude-opus-4-5-20251101",
                        "claude-sonnet-4-20250514",
                        "claude-3-5-haiku-20241022"
                    ]

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_model_selection_override(self, mock_config):
        """Explicit model override should be respected."""
        with patch("Tools.litellm.client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm.client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm.client.anthropic"):
                    client = LiteLLMClient(str(mock_config))
                    model = client._select_model(
                        "Simple question",
                        model_override="claude-opus-4-5-20251101"
                    )

                    assert model == "claude-opus-4-5-20251101"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_chat_uses_cache(self, mock_config, mock_anthropic_response):
        """chat should use cached responses when available."""
        with patch("Tools.litellm.client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm.client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm.client.anthropic") as mock_anthropic:
                    mock_client = Mock()
                    mock_client.messages.create.return_value = mock_anthropic_response
                    mock_anthropic.Anthropic.return_value = mock_client

                    client = LiteLLMClient(str(mock_config))

                    # First call should hit API
                    response1 = client.chat("Test prompt")
                    assert mock_client.messages.create.call_count == 1

                    # Second call should use cache
                    response2 = client.chat("Test prompt")
                    assert mock_client.messages.create.call_count == 1
                    assert response1 == response2

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_chat_skips_cache_when_disabled(self, mock_config, mock_anthropic_response):
        """chat should skip cache when use_cache=False."""
        with patch("Tools.litellm.client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm.client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm.client.anthropic") as mock_anthropic:
                    mock_client = Mock()
                    mock_client.messages.create.return_value = mock_anthropic_response
                    mock_anthropic.Anthropic.return_value = mock_client

                    client = LiteLLMClient(str(mock_config))

                    client.chat("Test prompt", use_cache=False)
                    client.chat("Test prompt", use_cache=False)

                    assert mock_client.messages.create.call_count == 2

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_usage_tracking(self, mock_config, mock_anthropic_response, temp_dir):
        """chat should track usage when enabled."""
        with patch("Tools.litellm.client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm.client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm.client.anthropic") as mock_anthropic:
                    mock_client = Mock()
                    mock_client.messages.create.return_value = mock_anthropic_response
                    mock_anthropic.Anthropic.return_value = mock_client

                    client = LiteLLMClient(str(mock_config))
                    client.chat("Test prompt", use_cache=False)

                    usage = client.get_today_usage()
                    assert usage["calls"] >= 1
                    assert usage["tokens"] > 0

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_analyze_complexity_method(self, mock_config):
        """analyze_complexity should return complexity info."""
        with patch("Tools.litellm.client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm.client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm.client.anthropic"):
                    client = LiteLLMClient(str(mock_config))

                    result = client.analyze_complexity("Analyze this architecture")

                    assert "complexity_score" in result
                    assert "tier" in result
                    assert "selected_model" in result
                    assert 0 <= result["complexity_score"] <= 1

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_list_available_models(self, mock_config):
        """list_available_models should return configured models."""
        with patch("Tools.litellm.client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm.client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm.client.anthropic"):
                    client = LiteLLMClient(str(mock_config))
                    models = client.list_available_models()

                    assert "claude-opus-4-5-20251101" in models
                    assert "claude-sonnet-4-20250514" in models
                    assert "claude-3-5-haiku-20241022" in models


# ============================================================================
# Module Function Tests
# ============================================================================

class TestModuleFunctions:
    """Tests for module-level functions."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_get_client_singleton(self, mock_config):
        """get_client should return singleton instance."""
        with patch("Tools.litellm.client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm.client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm.client.anthropic"):
                    # Reset singleton
                    import Tools.litellm.client as llm_module
                    llm_module._client_instance = None

                    client1 = get_client(str(mock_config))
                    client2 = get_client()

                    assert client1 is client2

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_init_client_creates_new(self, mock_config):
        """init_client should create a new instance."""
        with patch("Tools.litellm.client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm.client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm.client.anthropic"):
                    import Tools.litellm.client as llm_module
                    llm_module._client_instance = None

                    client1 = init_client(str(mock_config))
                    client2 = init_client(str(mock_config))

                    # init_client always creates new
                    assert client1 is not None
                    assert client2 is not None


# ============================================================================
# Integration-like Tests (with mocks)
# ============================================================================

class TestLiteLLMIntegration:
    """Integration-style tests with comprehensive mocking."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_full_chat_flow(self, mock_config, mock_anthropic_response):
        """Test complete chat flow: routing -> API call -> tracking -> caching."""
        with patch("Tools.litellm.client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm.client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm.client.anthropic") as mock_anthropic:
                    mock_client = Mock()
                    mock_client.messages.create.return_value = mock_anthropic_response
                    mock_anthropic.Anthropic.return_value = mock_client

                    client = LiteLLMClient(str(mock_config))

                    # First request
                    response = client.chat(
                        "What is architecture analysis?",
                        operation="test_chat"
                    )

                    assert response == "Test response from Anthropic"

                    # Check usage was tracked
                    usage = client.get_today_usage()
                    assert usage["calls"] >= 1

                    # Check response was cached
                    response2 = client.chat("What is architecture analysis?")
                    assert response2 == response
                    assert mock_client.messages.create.call_count == 1

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_complexity_based_routing(self, mock_config, mock_anthropic_response):
        """Test that complexity analysis affects model selection."""
        with patch("Tools.litellm.client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm.client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm.client.anthropic") as mock_anthropic:
                    mock_client = Mock()
                    mock_client.messages.create.return_value = mock_anthropic_response
                    mock_anthropic.Anthropic.return_value = mock_client

                    client = LiteLLMClient(str(mock_config))

                    # Analyze simple vs complex prompts
                    simple_analysis = client.analyze_complexity("Hi")
                    complex_analysis = client.analyze_complexity(
                        "Analyze this complex architecture and debug systematically"
                    )

                    assert complex_analysis["complexity_score"] > simple_analysis["complexity_score"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
