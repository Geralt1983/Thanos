#!/usr/bin/env python3
"""
Impact Scoring Engine for Personal Tasks.

Categorizes personal tasks by their potential impact across four dimensions:
- Health: Physical and mental wellbeing
- Stress: Anxiety and cognitive load reduction
- Financial: Money, wealth, security
- Relationships: Family, friends, connections
"""

import re
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

# Handle both CLI and module imports
try:
    from .models import (
        ImpactScore,
        ImpactDimension,
        IMPACT_KEYWORDS,
        TaskDomain,
    )
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from models import (
        ImpactScore,
        ImpactDimension,
        IMPACT_KEYWORDS,
        TaskDomain,
    )


class ImpactScorer:
    """
    Scores personal tasks by their impact across four dimensions.

    The scorer uses keyword matching, context analysis, and deadline
    proximity to calculate impact scores.
    """

    def __init__(self):
        """Initialize the impact scorer."""
        # Compile regex patterns for efficiency
        self.keyword_patterns: Dict[ImpactDimension, re.Pattern] = {}
        for dimension, keywords in IMPACT_KEYWORDS.items():
            pattern = r'\b(' + '|'.join(re.escape(k) for k in keywords) + r')\b'
            self.keyword_patterns[dimension] = re.compile(pattern, re.IGNORECASE)

    def score(
        self,
        content: str,
        deadline_days: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ImpactScore:
        """
        Calculate impact score for content.

        Args:
            content: The text content to analyze.
            deadline_days: Days until deadline (if known).
            context: Additional context for scoring.

        Returns:
            ImpactScore with dimensions filled.
        """
        content_lower = content.lower()
        context = context or {}

        # Calculate base scores from keyword matching
        scores = {}
        for dimension, pattern in self.keyword_patterns.items():
            matches = pattern.findall(content_lower)
            # Base score from match count (capped at 7)
            base_score = min(len(matches) * 2, 7)
            scores[dimension] = base_score

        # Apply deadline urgency boost
        if deadline_days is not None:
            urgency_boost = self._calculate_urgency_boost(deadline_days)
            scores[ImpactDimension.STRESS] = min(
                scores.get(ImpactDimension.STRESS, 0) + urgency_boost,
                10
            )

        # Apply context-specific adjustments
        scores = self._apply_context_adjustments(scores, context)

        # Ensure minimum score of 1 for detected items
        for dim in scores:
            if scores[dim] > 0:
                scores[dim] = max(scores[dim], 1)

        return ImpactScore(
            health=scores.get(ImpactDimension.HEALTH, 0),
            stress=scores.get(ImpactDimension.STRESS, 0),
            financial=scores.get(ImpactDimension.FINANCIAL, 0),
            relationship=scores.get(ImpactDimension.RELATIONSHIP, 0),
        )

    def _calculate_urgency_boost(self, deadline_days: int) -> float:
        """
        Calculate stress boost based on deadline proximity.

        Args:
            deadline_days: Days until deadline.

        Returns:
            Boost value (0-5).
        """
        if deadline_days < 0:
            # Overdue: maximum stress
            return 5
        elif deadline_days == 0:
            # Due today
            return 4
        elif deadline_days <= 2:
            # Due within 2 days
            return 3
        elif deadline_days <= 7:
            # Due within a week
            return 2
        elif deadline_days <= 14:
            # Due within 2 weeks
            return 1
        return 0

    def _apply_context_adjustments(
        self,
        scores: Dict[ImpactDimension, float],
        context: Dict[str, Any]
    ) -> Dict[ImpactDimension, float]:
        """
        Apply context-specific adjustments to scores.

        Args:
            scores: Current dimension scores.
            context: Additional context.

        Returns:
            Adjusted scores.
        """
        # Recurring items are more impactful
        if context.get('is_recurring'):
            for dim in scores:
                scores[dim] = scores.get(dim, 0) * 1.2

        # High cognitive load affects stress
        if context.get('cognitive_load') == 'high':
            scores[ImpactDimension.STRESS] = min(
                scores.get(ImpactDimension.STRESS, 0) + 2,
                10
            )

        # Money amounts boost financial score
        if context.get('amount'):
            amount = context['amount']
            if amount >= 1000:
                scores[ImpactDimension.FINANCIAL] = min(
                    scores.get(ImpactDimension.FINANCIAL, 0) + 4,
                    10
                )
            elif amount >= 100:
                scores[ImpactDimension.FINANCIAL] = min(
                    scores.get(ImpactDimension.FINANCIAL, 0) + 2,
                    10
                )

        # Named people boost relationship score
        if context.get('mentioned_people'):
            people_count = len(context['mentioned_people'])
            scores[ImpactDimension.RELATIONSHIP] = min(
                scores.get(ImpactDimension.RELATIONSHIP, 0) + people_count,
                10
            )

        return scores

    def explain(
        self,
        content: str,
        score: ImpactScore
    ) -> str:
        """
        Generate human-readable explanation of score.

        Args:
            content: The original content.
            score: The calculated score.

        Returns:
            Explanation string.
        """
        parts = []

        if score.health > 0:
            parts.append(f"Health impact: {score.health:.1f}/10")
        if score.stress > 0:
            parts.append(f"Stress impact: {score.stress:.1f}/10")
        if score.financial > 0:
            parts.append(f"Financial impact: {score.financial:.1f}/10")
        if score.relationship > 0:
            parts.append(f"Relationship impact: {score.relationship:.1f}/10")

        if not parts:
            return "No significant impact detected."

        primary = score.primary_dimension
        parts.append(f"Primary dimension: {primary.value.title()}")
        parts.append(f"Composite score: {score.composite:.1f}/10")

        return " | ".join(parts)

    def batch_score(
        self,
        items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Score multiple items at once.

        Args:
            items: List of dicts with 'content' and optional 'deadline_days', 'context'.

        Returns:
            List of items with 'impact_score' added.
        """
        results = []
        for item in items:
            score = self.score(
                content=item.get('content', ''),
                deadline_days=item.get('deadline_days'),
                context=item.get('context', {})
            )
            item['impact_score'] = score
            results.append(item)
        return results


def score_task(content: str, deadline_days: Optional[int] = None) -> ImpactScore:
    """
    Convenience function to score a single task.

    Args:
        content: Task content to analyze.
        deadline_days: Days until deadline.

    Returns:
        ImpactScore instance.
    """
    scorer = ImpactScorer()
    return scorer.score(content, deadline_days)


# CLI interface
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Impact Scoring Engine')
    parser.add_argument('content', nargs='?', help='Content to score')
    parser.add_argument('--deadline', '-d', type=int, help='Days until deadline')
    parser.add_argument('--explain', '-e', action='store_true', help='Show explanation')
    args = parser.parse_args()

    if args.content:
        scorer = ImpactScorer()
        score = scorer.score(args.content, args.deadline)

        print(f"\nImpact Score for: {args.content[:50]}...")
        print(f"  Health:       {score.health:.1f}/10")
        print(f"  Stress:       {score.stress:.1f}/10")
        print(f"  Financial:    {score.financial:.1f}/10")
        print(f"  Relationship: {score.relationship:.1f}/10")
        print(f"  ---")
        print(f"  Composite:    {score.composite:.1f}/10")
        print(f"  Primary:      {score.primary_dimension.value.title()}")

        if args.explain:
            print(f"\n{scorer.explain(args.content, score)}")
    else:
        # Demo mode
        print("Impact Scoring Engine - Demo")
        print("=" * 50)

        test_cases = [
            "Call mom for her birthday tomorrow",
            "Pay the electricity bill - overdue!",
            "Schedule annual physical with doctor",
            "Review quarterly budget and savings plan",
            "Exercise more this week",
            "Send thank you note to Sarah for the gift",
        ]

        scorer = ImpactScorer()
        for content in test_cases:
            score = scorer.score(content)
            print(f"\n{content}")
            print(f"  → {score.primary_dimension.value.title()}: {score.composite:.1f}/10")
