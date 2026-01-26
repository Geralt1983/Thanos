#!/usr/bin/env python3
"""
PatternAnalyzer - Proactive insight discovery for second brain capabilities.

Analyzes memories and relationships to:
- Discover recurring patterns
- Identify cross-domain correlations
- Generate proactive insights
- Surface warnings and opportunities

Designed to run periodically or on-demand to enhance MemOS with
intelligent pattern recognition and proactive surfacing.

Key Classes:
    PatternAnalyzer: Core pattern analysis engine
    AnalysisResult: Container for analysis results

Usage:
    from Tools.pattern_analyzer import PatternAnalyzer

    analyzer = PatternAnalyzer()

    # Run full analysis
    results = await analyzer.analyze_all()

    # Check for specific patterns
    correlations = analyzer.find_domain_correlations(
        domains=["health", "work"],
        timeframe_days=30
    )
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional
from pathlib import Path

try:
    from .memory_router import search_memory, add_memory
    from .relationships import RelationshipStore, RelationType, get_relationship_store
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False


@dataclass
class AnalysisResult:
    """Container for pattern analysis results."""

    patterns_found: list[dict[str, Any]] = field(default_factory=list)
    correlations_found: list[dict[str, Any]] = field(default_factory=list)
    insights_generated: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    opportunities: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_findings(self) -> int:
        return (
            len(self.patterns_found)
            + len(self.correlations_found)
            + len(self.insights_generated)
            + len(self.warnings)
            + len(self.opportunities)
        )


class PatternAnalyzer:
    """
    Intelligent pattern analysis for second brain capabilities.

    Analyzes memories across domains to discover patterns, correlations,
    and insights that should be proactively surfaced to the user.

    Attributes:
        relationships: RelationshipStore for relationship traversal
    """

    def __init__(
        self,
        relationships: Optional[RelationshipStore] = None,
    ):
        """
        Initialize PatternAnalyzer.

        Args:
            relationships: RelationshipStore instance (uses singleton if not provided)
        """
        if not DEPS_AVAILABLE:
            raise ImportError("Required dependencies not available")

        self.relationships = relationships or get_relationship_store()

    async def analyze_all(
        self,
        timeframe_days: int = 30,
        domains: Optional[list[str]] = None,
    ) -> AnalysisResult:
        """
        Run comprehensive pattern analysis.

        Args:
            timeframe_days: How far back to analyze
            domains: Specific domains to focus on (None = all)

        Returns:
            AnalysisResult with all findings
        """
        domains = domains or ["work", "health", "personal", "relationship"]

        result = AnalysisResult(
            metadata={
                "analyzed_at": datetime.now().isoformat(),
                "timeframe_days": timeframe_days,
                "domains": domains,
            }
        )

        # Find domain correlations
        correlations = await self._analyze_domain_correlations(domains, timeframe_days)
        result.correlations_found.extend(correlations)

        # Find recurring patterns
        patterns = await self._find_recurring_patterns(timeframe_days)
        result.patterns_found.extend(patterns)

        # Check for warnings (broken commitments, negative patterns)
        warnings = await self._check_for_warnings(timeframe_days)
        result.warnings.extend(warnings)

        # Check for opportunities
        opportunities = await self._find_opportunities(timeframe_days)
        result.opportunities.extend(opportunities)

        # Generate insights from findings
        insights = self._synthesize_insights(result)
        result.insights_generated.extend(insights)

        # Store high-confidence insights for proactive surfacing
        for insight in insights:
            if insight.get("confidence", 0) >= 0.6:
                add_memory(
                    content=insight.get("content", ""),
                    metadata={
                        "memory_type": "insight",
                        "insight_type": insight.get("type", "pattern"),
                        "source_memories": insight.get("source_memories", []),
                        "confidence": insight.get("confidence", 0.5),
                        "source": "pattern_analyzer",
                    }
                )

        return result

    async def _analyze_domain_correlations(
        self,
        domains: list[str],
        timeframe_days: int,
    ) -> list[dict[str, Any]]:
        """Find correlations between different domains."""
        correlations = []

        # Get recent memories from each domain
        domain_memories: dict[str, list[str]] = {}

        for domain in domains:
            try:
                results = search_memory(
                    query=f"recent {domain} events and observations",
                    limit=20,
                    filters={"domain": domain}
                )
                memory_ids = []
                for item in results:
                    mem_id = item.get("id")
                    if mem_id:
                        memory_ids.append(str(mem_id))
                domain_memories[domain] = memory_ids
            except Exception:
                pass

        # Find memories that connect multiple domains
        all_memories = []
        for memories in domain_memories.values():
            all_memories.extend(memories)

        if len(all_memories) >= 2:
            correlation_candidates = self.relationships.get_correlation_candidates(
                memory_ids=all_memories,
                min_shared_connections=2,
            )

            for candidate in correlation_candidates:
                # Determine which domains this memory connects
                connected_domains = []
                for domain, memories in domain_memories.items():
                    if any(
                        rel.source_id in memories or rel.target_id in memories
                        for rel in self.relationships.get_related(
                            candidate["memory_id"], direction="both"
                        )
                    ):
                        connected_domains.append(domain)

                if len(connected_domains) >= 2:
                    correlations.append({
                        "memory_id": candidate["memory_id"],
                        "connects_domains": connected_domains,
                        "connection_count": candidate["connection_count"],
                        "relationship_types": candidate["relationship_types"],
                    })

        return correlations

    async def _find_recurring_patterns(
        self,
        timeframe_days: int,
    ) -> list[dict[str, Any]]:
        """Find recurring behavioral patterns."""
        patterns = []

        # Look for patterns in relationship chains
        try:
            # Get recent relationship activity
            stats = self.relationships.get_stats()

            # Group relationships by type to find patterns
            for rel_type, count in stats.get("by_type", {}).items():
                if count >= 3:  # Recurring pattern threshold
                    patterns.append({
                        "type": "relationship_pattern",
                        "relationship_type": rel_type,
                        "occurrence_count": count,
                        "confidence": min(0.9, 0.5 + (count * 0.1)),
                    })

        except Exception:
            pass

        # Query for behavior patterns via semantic search
        try:
            results = search_memory(
                query="recurring patterns behaviors habits",
                limit=20,
                filters={"memory_type": "pattern,observation"}
            )

            # Group similar patterns by content similarity
            seen_topics = set()
            for item in results:
                content = item.get("memory", item.get("content", ""))
                # Simple deduplication by first 50 chars
                topic = content[:50].lower()
                if topic not in seen_topics:
                    seen_topics.add(topic)
                    metadata = item.get("metadata", {})
                    patterns.append({
                        "type": "semantic_pattern",
                        "content": content,
                        "domain": metadata.get("domain"),
                        "source": metadata.get("source", "unknown"),
                    })

        except Exception:
            pass

        return patterns

    async def _check_for_warnings(
        self,
        timeframe_days: int,
    ) -> list[dict[str, Any]]:
        """Check for warning signs that should be surfaced."""
        warnings = []

        # Check for negative patterns
        try:
            results = search_memory(
                query="missed deadline failed broken commitment struggle difficulty",
                limit=10,
                filters={"memory_type": "commitment,observation"}
            )

            if len(results) >= 3:
                warnings.append({
                    "type": "negative_pattern",
                    "content": "Multiple missed commitments or difficulties detected",
                    "count": len(results),
                    "severity": "medium" if len(results) < 5 else "high",
                    "recommendation": "Consider reviewing commitments and priorities",
                })

        except Exception:
            pass

        # Check for relationship chains ending in negative outcomes
        try:
            # Look for PREVENTED relationships (things that blocked progress)
            prevented_rels = self.relationships.get_related(
                memory_id="",  # Get all
                rel_type=RelationType.PREVENTED if RelationType else None,
                direction="both",
            )

            if len(prevented_rels) >= 2:
                warnings.append({
                    "type": "blockers_detected",
                    "content": f"Found {len(prevented_rels)} blocking relationships",
                    "count": len(prevented_rels),
                    "severity": "low",
                    "recommendation": "Review blockers and consider workarounds",
                })

        except Exception:
            pass

        return warnings

    async def _find_opportunities(
        self,
        timeframe_days: int,
    ) -> list[dict[str, Any]]:
        """Find opportunities for improvement or action."""
        opportunities = []

        # Look for positive patterns that could be expanded
        try:
            results = search_memory(
                query="success improvement progress achievement completed",
                limit=10,
                filters={"memory_type": "observation,decision"}
            )

            if len(results) >= 2:
                opportunities.append({
                    "type": "positive_momentum",
                    "content": "Recent successes detected - good momentum to build on",
                    "count": len(results),
                    "recommendation": "Consider expanding successful approaches to other areas",
                })

        except Exception:
            pass

        # Check for unlinked memories that might benefit from connections
        try:
            stats = self.relationships.get_stats()
            if stats.get("total_relationships", 0) < 10:
                opportunities.append({
                    "type": "connection_opportunity",
                    "content": "Few explicit memory relationships exist",
                    "recommendation": "Consider linking related memories for better pattern recognition",
                })

        except Exception:
            pass

        return opportunities

    def _synthesize_insights(
        self,
        result: AnalysisResult,
    ) -> list[dict[str, Any]]:
        """Synthesize insights from analysis findings."""
        insights = []

        # Cross-domain correlation insights
        if result.correlations_found:
            for corr in result.correlations_found[:3]:  # Top 3
                domains = corr.get("connects_domains", [])
                if len(domains) >= 2:
                    insights.append({
                        "type": "correlation",
                        "content": f"Found connection between {' and '.join(domains)} domains",
                        "source_memories": [corr.get("memory_id")],
                        "confidence": min(0.8, 0.4 + (corr.get("connection_count", 0) * 0.1)),
                    })

        # Pattern-based insights
        if len(result.patterns_found) >= 3:
            insights.append({
                "type": "pattern_cluster",
                "content": f"Detected {len(result.patterns_found)} recurring patterns - review for optimization opportunities",
                "source_memories": [
                    p.get("memory_id") or p.get("content", "")[:30]
                    for p in result.patterns_found[:5]
                ],
                "confidence": 0.7,
            })

        # Warning-based insights
        for warning in result.warnings:
            if warning.get("severity") in ("medium", "high"):
                insights.append({
                    "type": "warning",
                    "content": warning.get("content", ""),
                    "source_memories": [],
                    "confidence": 0.8 if warning.get("severity") == "high" else 0.6,
                    "action_required": True,
                })

        # Opportunity-based insights
        for opp in result.opportunities:
            insights.append({
                "type": "opportunity",
                "content": opp.get("recommendation", opp.get("content", "")),
                "source_memories": [],
                "confidence": 0.5,
            })

        return insights

    async def quick_check(self) -> dict[str, Any]:
        """
        Run a quick health check on memory patterns.

        Returns status and any urgent insights.
        """
        status = {
            "healthy": True,
            "urgent_insights": [],
            "relationship_count": 0,
            "pending_insights": 0,
        }

        try:
            # Check relationship store health
            stats = self.relationships.get_stats()
            status["relationship_count"] = stats.get("total_relationships", 0)
            status["pending_insights"] = stats.get("pending_insights", 0)

            # Get any pending high-priority insights
            pending = search_memory(
                query="insights patterns warnings",
                limit=3,
                filters={"memory_type": "insight", "confidence": ">=0.7"}
            )
            status["urgent_insights"] = pending

            if status["pending_insights"] > 5:
                status["healthy"] = False
                status["message"] = "Many unsurfaced insights - review recommended"

        except Exception as e:
            status["healthy"] = False
            status["error"] = str(e)

        return status


# Convenience function for quick analysis
async def run_pattern_analysis(
    timeframe_days: int = 30,
    domains: Optional[list[str]] = None,
) -> AnalysisResult:
    """
    Run pattern analysis with default settings.

    Args:
        timeframe_days: How far back to analyze
        domains: Specific domains to focus on

    Returns:
        AnalysisResult with all findings
    """
    analyzer = PatternAnalyzer()
    return await analyzer.analyze_all(
        timeframe_days=timeframe_days,
        domains=domains,
    )
