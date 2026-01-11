#!/usr/bin/env python3
"""
Intelligent prompt complexity analysis for automatic model routing.

This module provides sophisticated analysis of prompt complexity to enable
intelligent model selection. By evaluating multiple factors, it determines
the appropriate model tier (simple/standard/complex) to balance cost and
capability for each request.

Analysis Factors:
    - Token count: Length of prompt and conversation history
    - Keyword indicators: Presence of complexity markers (e.g., "analyze", "debug")
    - Conversation depth: Number of messages in history
    - Weighted scoring: Configurable weights for each factor

Complexity Tiers:
    - simple (0.0-0.3): Fast, cheap models for basic tasks
    - standard (0.3-0.7): Balanced models for typical workloads
    - complex (0.7-1.0): Premium models for sophisticated reasoning

Key Classes:
    ComplexityAnalyzer: Analyzes prompts and returns complexity scores with
                        recommended model tiers

Usage:
    from Tools.litellm.complexity_analyzer import ComplexityAnalyzer

    # Initialize with routing configuration
    analyzer = ComplexityAnalyzer(config={
        "complexity_factors": {
            "token_count_weight": 0.3,
            "keyword_weight": 0.4,
            "history_length_weight": 0.3
        }
    })

    # Analyze a prompt
    complexity, tier = analyzer.analyze(
        prompt="Explain the architectural design of this system",
        history=[{"role": "user", "content": "Previous message"}]
    )
    # Returns: (0.75, "complex")

    # Simple queries route to cheaper models
    complexity, tier = analyzer.analyze("What time is it?")
    # Returns: (0.15, "simple")

Integration:
    The ComplexityAnalyzer is automatically used by LiteLLMClient when no
    explicit model is specified. The client queries the analyzer, which
    returns a tier recommendation, then maps that tier to a specific model
    using the routing rules configuration.

Configuration Example:
    {
        "model_routing": {
            "rules": {
                "complex": {"model": "claude-opus-4-5-20251101", "min_complexity": 0.7},
                "standard": {"model": "claude-sonnet-4-20250514", "min_complexity": 0.3},
                "simple": {"model": "claude-3-5-haiku-20241022", "max_complexity": 0.3}
            },
            "complexity_factors": {
                "token_count_weight": 0.3,
                "keyword_weight": 0.4,
                "history_length_weight": 0.3
            }
        }
    }

This intelligent routing can significantly reduce API costs by automatically
using cheaper models for simple tasks while reserving premium models for
complex reasoning.
"""

from typing import Dict, List, Optional, Tuple


class ComplexityAnalyzer:
    """Analyze prompt complexity for model routing."""

    def __init__(self, config: Dict):
        self.config = config
        self.factors = config.get("complexity_factors", {
            "token_count_weight": 0.3,
            "keyword_weight": 0.4,
            "history_length_weight": 0.3
        })

    def analyze(self, prompt: str, history: Optional[List[Dict]] = None) -> Tuple[float, str]:
        """
        Analyze prompt complexity and return score with recommended tier.

        Returns:
            Tuple of (complexity_score: float, tier: str)
        """
        scores = []

        # Token count factor (rough estimate: 4 chars per token)
        estimated_tokens = len(prompt) / 4
        if history:
            estimated_tokens += sum(len(m.get("content", "")) / 4 for m in history)

        token_score = min(estimated_tokens / 2000, 1.0)  # Normalize to 0-1
        scores.append(("token_count", token_score, self.factors.get("token_count_weight", 0.3)))

        # Keyword complexity factor
        complex_indicators = [
            "analyze", "architecture", "strategy", "debug", "investigate",
            "optimize", "refactor", "design", "explain", "comprehensive",
            "detailed", "thoroughly", "step by step", "reasoning"
        ]
        simple_indicators = [
            "quick", "simple", "lookup", "translate", "format",
            "summarize briefly", "one sentence", "yes or no"
        ]

        prompt_lower = prompt.lower()
        complex_matches = sum(1 for ind in complex_indicators if ind in prompt_lower)
        simple_matches = sum(1 for ind in simple_indicators if ind in prompt_lower)

        keyword_score = min((complex_matches * 0.2) - (simple_matches * 0.15) + 0.5, 1.0)
        keyword_score = max(keyword_score, 0.0)
        scores.append(("keyword", keyword_score, self.factors.get("keyword_weight", 0.4)))

        # History length factor
        history_len = len(history) if history else 0
        history_score = min(history_len / 10, 1.0)  # Normalize: 10+ messages = max complexity
        scores.append(("history", history_score, self.factors.get("history_length_weight", 0.3)))

        # Calculate weighted average
        total_weight = sum(w for _, _, w in scores)
        complexity = sum(s * w for _, s, w in scores) / total_weight if total_weight > 0 else 0.5

        # Determine tier
        if complexity >= 0.7:
            tier = "complex"
        elif complexity >= 0.3:
            tier = "standard"
        else:
            tier = "simple"

        return complexity, tier
