"""
Unit tests for the LiteLLM client module.
Tests model routing, caching, usage tracking, and API integration.
"""
import json
import os
from pathlib import Path
import sys
from unittest.mock import Mock, patch

import pytest


# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from Tools.litellm_client import (
    ComplexityAnalyzer,
    LiteLLMClient,
    ModelResponse,
    ResponseCache,
    UsageTracker,
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
# UsageTracker Tests
# ============================================================================

class TestUsageTracker:
    """Tests for the UsageTracker class."""

    def test_init_creates_storage_file(self, temp_dir):
        """UsageTracker should create storage file on initialization."""
        storage_path = temp_dir / "usage.json"
        pricing = {"claude-opus-4-5-20251101": {"input": 0.015, "output": 0.075}}

        tracker = UsageTracker(str(storage_path), pricing)

        assert storage_path.exists()
        data = json.loads(storage_path.read_text())
        assert "sessions" in data
        assert "daily_totals" in data

    def test_calculate_cost(self, temp_dir):
        """calculate_cost should compute correct costs based on pricing."""
        storage_path = temp_dir / "usage.json"
        pricing = {
            "claude-opus-4-5-20251101": {"input": 0.015, "output": 0.075}
        }
        tracker = UsageTracker(str(storage_path), pricing)

        # 1000 input tokens = $0.015, 1000 output tokens = $0.075
        cost = tracker.calculate_cost("claude-opus-4-5-20251101", 1000, 1000)
        assert cost == pytest.approx(0.09)

    def test_record_updates_storage(self, temp_dir):
        """record should update storage with usage data."""
        storage_path = temp_dir / "usage.json"
        pricing = {"claude-opus-4-5-20251101": {"input": 0.015, "output": 0.075}}
        tracker = UsageTracker(str(storage_path), pricing)

        tracker.record(
            model="claude-opus-4-5-20251101",
            input_tokens=500,
            output_tokens=200,
            cost_usd=0.0225,
            latency_ms=1500,
            operation="test"
        )

        data = json.loads(storage_path.read_text())
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["input_tokens"] == 500
        assert data["sessions"][0]["output_tokens"] == 200

    def test_get_today_returns_daily_stats(self, temp_dir):
        """get_today should return today's usage statistics."""
        storage_path = temp_dir / "usage.json"
        pricing = {"claude-opus-4-5-20251101": {"input": 0.015, "output": 0.075}}
        tracker = UsageTracker(str(storage_path), pricing)

        tracker.record("claude-opus-4-5-20251101", 100, 50, 0.01, 1000)
        tracker.record("claude-opus-4-5-20251101", 200, 100, 0.02, 1200)

        today = tracker.get_today()
        assert today["tokens"] == 450  # (100+50) + (200+100)
        assert today["calls"] == 2

    def test_get_summary_aggregates_correctly(self, temp_dir):
        """get_summary should aggregate usage over the specified period."""
        storage_path = temp_dir / "usage.json"
        pricing = {"claude-opus-4-5-20251101": {"input": 0.015, "output": 0.075}}
        tracker = UsageTracker(str(storage_path), pricing)

        # Record some usage
        tracker.record("claude-opus-4-5-20251101", 1000, 500, 0.05, 1500)

        summary = tracker.get_summary(30)
        assert summary["total_tokens"] == 1500
        assert summary["total_calls"] == 1
        assert "projected_monthly_cost" in summary

    def test_provider_detection(self, temp_dir):
        """_get_provider should correctly identify providers from model names."""
        storage_path = temp_dir / "usage.json"
        pricing = {}
        tracker = UsageTracker(str(storage_path), pricing)

        assert tracker._get_provider("claude-opus-4-5-20251101") == "anthropic"
        assert tracker._get_provider("gpt-4o") == "openai"
        assert tracker._get_provider("gemini-pro") == "google"
        assert tracker._get_provider("unknown-model") == "unknown"


# ============================================================================
# ComplexityAnalyzer Tests
# ============================================================================

class TestComplexityAnalyzer:
    """Tests for the ComplexityAnalyzer class."""

    def test_simple_prompt_low_complexity(self):
        """Simple prompts should have low complexity scores."""
        config = {
            "complexity_factors": {
                "token_count_weight": 0.3,
                "keyword_weight": 0.4,
                "history_length_weight": 0.3
            }
        }
        analyzer = ComplexityAnalyzer(config)

        complexity, tier = analyzer.analyze("What's 2+2?")

        assert complexity < 0.5
        assert tier in ["simple", "standard"]

    def test_complex_prompt_high_complexity(self):
        """Complex prompts with analysis keywords should have high complexity."""
        config = {
            "complexity_factors": {
                "token_count_weight": 0.3,
                "keyword_weight": 0.4,
                "history_length_weight": 0.3
            }
        }
        analyzer = ComplexityAnalyzer(config)

        complexity, tier = analyzer.analyze(
            "Analyze the architecture of this complex system and provide "
            "a comprehensive strategy for optimization and refactoring. "
            "Debug any issues and explain the reasoning step by step."
        )

        # Complexity should be moderate-to-high (above default 0.35 baseline)
        assert complexity > 0.35
        assert tier in ["standard", "complex"]

    def test_history_increases_complexity(self):
        """Long conversation history should increase complexity."""
        config = {
            "complexity_factors": {
                "token_count_weight": 0.3,
                "keyword_weight": 0.4,
                "history_length_weight": 0.3
            }
        }
        analyzer = ComplexityAnalyzer(config)

        # Short history
        complexity_short, _ = analyzer.analyze("Continue", [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"}
        ])

        # Long history
        history = [{"role": "user" if i % 2 == 0 else "assistant",
                    "content": f"Message {i}"} for i in range(20)]
        complexity_long, _ = analyzer.analyze("Continue", history)

        assert complexity_long > complexity_short

    def test_simple_keywords_reduce_complexity(self):
        """Simple keywords should reduce complexity score."""
        config = {
            "complexity_factors": {
                "token_count_weight": 0.3,
                "keyword_weight": 0.4,
                "history_length_weight": 0.3
            }
        }
        analyzer = ComplexityAnalyzer(config)

        complexity, tier = analyzer.analyze("Just give me a quick, simple one sentence summary")

        assert complexity < 0.5


# ============================================================================
# ResponseCache Tests
# ============================================================================

class TestResponseCache:
    """Tests for the ResponseCache class."""

    def test_set_and_get(self, temp_dir):
        """Cache should store and retrieve responses."""
        cache = ResponseCache(str(temp_dir / "cache"), ttl_seconds=3600)

        cache.set("test prompt", "claude-opus-4-5-20251101", {}, "cached response")
        result = cache.get("test prompt", "claude-opus-4-5-20251101", {})

        assert result == "cached response"

    def test_cache_miss(self, temp_dir):
        """Cache should return None for missing entries."""
        cache = ResponseCache(str(temp_dir / "cache"), ttl_seconds=3600)

        result = cache.get("nonexistent", "model", {})

        assert result is None

    def test_cache_expiration(self, temp_dir):
        """Expired cache entries should return None."""
        cache = ResponseCache(str(temp_dir / "cache"), ttl_seconds=1)

        cache.set("test", "model", {}, "response")

        # Manually expire the cache
        import time
        time.sleep(1.1)

        result = cache.get("test", "model", {})
        assert result is None

    def test_different_models_different_cache(self, temp_dir):
        """Same prompt with different models should have different cache entries."""
        cache = ResponseCache(str(temp_dir / "cache"), ttl_seconds=3600)

        cache.set("test prompt", "model-a", {}, "response from A")
        cache.set("test prompt", "model-b", {}, "response from B")

        assert cache.get("test prompt", "model-a", {}) == "response from A"
        assert cache.get("test prompt", "model-b", {}) == "response from B"

    def test_clear_expired(self, temp_dir):
        """clear_expired should remove old cache entries."""
        cache = ResponseCache(str(temp_dir / "cache"), ttl_seconds=1)
        cache_dir = Path(temp_dir / "cache")

        cache.set("test1", "model", {}, "response1")
        cache.set("test2", "model", {}, "response2")

        import time
        time.sleep(1.1)

        cache.clear_expired()

        # All cache files should be removed
        cache_files = list(cache_dir.glob("*.json"))
        assert len(cache_files) == 0


# ============================================================================
# LiteLLMClient Tests
# ============================================================================

class TestLiteLLMClient:
    """Tests for the LiteLLMClient class."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_init_with_config(self, mock_config, temp_dir):
        """Client should initialize with provided config."""
        with patch("Tools.litellm_client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm_client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm_client.anthropic") as mock_anthropic:
                    client = LiteLLMClient(str(mock_config))

                    assert client.config is not None
                    assert client.usage_tracker is not None
                    assert client.cache is not None

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_model_selection_simple(self, mock_config):
        """Simple prompts should select simpler models."""
        with patch("Tools.litellm_client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm_client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm_client.anthropic"):
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
        with patch("Tools.litellm_client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm_client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm_client.anthropic"):
                    client = LiteLLMClient(str(mock_config))
                    model = client._select_model(
                        "Simple question",
                        model_override="claude-opus-4-5-20251101"
                    )

                    assert model == "claude-opus-4-5-20251101"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_chat_uses_cache(self, mock_config, mock_anthropic_response):
        """chat should use cached responses when available."""
        with patch("Tools.litellm_client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm_client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm_client.anthropic") as mock_anthropic:
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
        with patch("Tools.litellm_client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm_client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm_client.anthropic") as mock_anthropic:
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
        with patch("Tools.litellm_client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm_client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm_client.anthropic") as mock_anthropic:
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
        with patch("Tools.litellm_client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm_client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm_client.anthropic"):
                    client = LiteLLMClient(str(mock_config))

                    result = client.analyze_complexity("Analyze this architecture")

                    assert "complexity_score" in result
                    assert "tier" in result
                    assert "selected_model" in result
                    assert 0 <= result["complexity_score"] <= 1

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_list_available_models(self, mock_config):
        """list_available_models should return configured models."""
        with patch("Tools.litellm_client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm_client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm_client.anthropic"):
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
        with patch("Tools.litellm_client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm_client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm_client.anthropic"):
                    # Reset singleton
                    import Tools.litellm_client as llm_module
                    llm_module._client_instance = None

                    client1 = get_client(str(mock_config))
                    client2 = get_client()

                    assert client1 is client2

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_init_client_creates_new(self, mock_config):
        """init_client should create a new instance."""
        with patch("Tools.litellm_client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm_client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm_client.anthropic"):
                    import Tools.litellm_client as llm_module
                    llm_module._client_instance = None

                    client1 = init_client(str(mock_config))
                    client2 = init_client(str(mock_config))

                    # init_client always creates new
                    assert client1 is not None
                    assert client2 is not None


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


# ============================================================================
# Integration-like Tests (with mocks)
# ============================================================================

class TestLiteLLMIntegration:
    """Integration-style tests with comprehensive mocking."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_full_chat_flow(self, mock_config, mock_anthropic_response):
        """Test complete chat flow: routing -> API call -> tracking -> caching."""
        with patch("Tools.litellm_client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm_client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm_client.anthropic") as mock_anthropic:
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
        with patch("Tools.litellm_client.LITELLM_AVAILABLE", False):
            with patch("Tools.litellm_client.ANTHROPIC_AVAILABLE", True):
                with patch("Tools.litellm_client.anthropic") as mock_anthropic:
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
