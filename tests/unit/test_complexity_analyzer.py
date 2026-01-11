"""
Unit tests for the ComplexityAnalyzer class.
Tests prompt complexity analysis and model tier routing.
"""
import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from Tools.litellm import ComplexityAnalyzer


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
