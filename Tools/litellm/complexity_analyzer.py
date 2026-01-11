#!/usr/bin/env python3
"""
Complexity analysis for prompt routing in LiteLLM client.

This module analyzes prompt complexity to determine the appropriate model tier
for handling requests. Uses multiple factors including token count, keyword
indicators, and conversation history to calculate a complexity score.
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
