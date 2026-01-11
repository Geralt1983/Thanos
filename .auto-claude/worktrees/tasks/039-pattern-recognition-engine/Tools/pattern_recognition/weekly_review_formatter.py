"""Weekly review formatting templates for pattern recognition insights.

This module provides comprehensive formatting templates for presenting insights
in weekly review format with concise summaries, evidence, actions, and confidence indicators.
"""

from typing import List, Optional
from datetime import datetime

from .models import Insight, InsightCategory


def format_insight_for_weekly_review(
    insight: Insight,
    include_evidence: bool = True,
    max_evidence: int = 3
) -> str:
    """Format a single insight for weekly review presentation.

    Presents insight with:
    - Concise summary (1-2 sentences)
    - Confidence level indicator
    - Supporting evidence (data points)
    - Suggested action (specific recommendation)

    Args:
        insight: Insight to format
        include_evidence: Whether to include supporting evidence
        max_evidence: Maximum number of evidence items to show

    Returns:
        str: Formatted insight string ready for weekly review

    Example output:
        💡 Most productive 9-11am (avg 8.2 tasks) [●●●●○ 82% confidence]

        📊 Evidence:
           • Analyzed 45 days from 2024-11-15 to 2024-12-30
           • Peak productivity window: 9-11am (40% above average)
           • Consistent pattern across 85% of workdays

        🎯 Action: Schedule important tasks during 9-11am to capitalize on high productivity windows
    """
    lines = []

    # Header with emoji and confidence indicator
    category_emoji = _get_category_emoji(insight.category)
    confidence_bar = _format_confidence_indicator(insight.confidence_score)

    lines.append(f"{category_emoji} {insight.summary}")
    lines.append(f"   {confidence_bar}")
    lines.append("")

    # Supporting evidence section
    if include_evidence and insight.supporting_evidence:
        lines.append("   📊 Evidence:")
        evidence_items = insight.supporting_evidence[:max_evidence]
        for evidence in evidence_items:
            lines.append(f"      • {evidence}")

        if len(insight.supporting_evidence) > max_evidence:
            remaining = len(insight.supporting_evidence) - max_evidence
            lines.append(f"      ... and {remaining} more")
        lines.append("")

    # Action section
    lines.append(f"   🎯 Action: {insight.suggested_action}")

    return "\n".join(lines)


def format_insights_for_weekly_review(
    insights: List[Insight],
    title: str = "📈 Pattern Insights",
    include_evidence: bool = True,
    max_evidence_per_insight: int = 3
) -> str:
    """Format multiple insights as a complete weekly review section.

    Args:
        insights: List of insights to format
        title: Section title
        include_evidence: Whether to include supporting evidence
        max_evidence_per_insight: Maximum evidence items per insight

    Returns:
        str: Complete formatted section for weekly review

    Example output:
        ═══════════════════════════════════════════════════════════════
        📈 Pattern Insights (3 insights discovered)
        ═══════════════════════════════════════════════════════════════

        1. 💡 Most productive 9-11am (avg 8.2 tasks) [●●●●○ 82% confidence]
           ...

        2. 🏃 Exercise habit: 12-day streak broken [●●●○○ 68% confidence]
           ...

        3. 📈 Tasks per day improving (7.2 → 9.4) [●●●●○ 75% confidence]
           ...
    """
    if not insights:
        return f"{title}\nNo significant patterns detected this period."

    lines = []

    # Header with decorative separator
    separator = "═" * 63
    lines.append(separator)
    lines.append(f"{title} ({len(insights)} insight{'s' if len(insights) != 1 else ''} discovered)")
    lines.append(separator)
    lines.append("")

    # Format each insight with numbering
    for idx, insight in enumerate(insights, 1):
        insight_text = format_insight_for_weekly_review(
            insight,
            include_evidence=include_evidence,
            max_evidence=max_evidence_per_insight
        )

        # Add numbering to first line
        insight_lines = insight_text.split("\n")
        if insight_lines:
            insight_lines[0] = f"{idx}. {insight_lines[0]}"

        lines.extend(insight_lines)

        # Add spacing between insights (except after last one)
        if idx < len(insights):
            lines.append("")
            lines.append("   " + "─" * 60)
            lines.append("")

    return "\n".join(lines)


def format_insight_compact(insight: Insight) -> str:
    """Format insight in compact single-line format.

    Useful for CLI displays or when space is limited.

    Args:
        insight: Insight to format

    Returns:
        str: Compact one-line summary

    Example:
        💡 Most productive 9-11am (avg 8.2 tasks) [82%] → Schedule important tasks during 9-11am
    """
    emoji = _get_category_emoji(insight.category)
    confidence = f"{insight.confidence_score:.0%}"

    return f"{emoji} {insight.summary} [{confidence}] → {insight.suggested_action}"


def format_insight_detailed(insight: Insight) -> str:
    """Format insight with full details including all metadata.

    Provides comprehensive view with all scores, evidence, and metadata.
    Useful for debugging or detailed analysis.

    Args:
        insight: Insight to format

    Returns:
        str: Detailed formatted insight
    """
    lines = []

    # Header
    emoji = _get_category_emoji(insight.category)
    lines.append(f"{emoji} {insight.summary}")
    lines.append("=" * 70)
    lines.append("")

    # Category and date range
    lines.append(f"Category: {insight.category.value.replace('_', ' ').title()}")
    if insight.date_range_start and insight.date_range_end:
        date_range = (
            f"{insight.date_range_start.strftime('%Y-%m-%d')} to "
            f"{insight.date_range_end.strftime('%Y-%m-%d')}"
        )
        lines.append(f"Date Range: {date_range}")
    lines.append("")

    # Detailed description
    lines.append("Description:")
    lines.append(f"  {insight.detailed_description}")
    lines.append("")

    # Scores
    lines.append("Scores:")
    lines.append(f"  Overall:        {insight.get_overall_score():.1%} {_format_score_bar(insight.get_overall_score())}")
    lines.append(f"  Confidence:     {insight.confidence_score:.1%} {_format_score_bar(insight.confidence_score)}")
    lines.append(f"  Significance:   {insight.significance_score:.1%} {_format_score_bar(insight.significance_score)}")
    lines.append(f"  Actionability:  {insight.actionability_score:.1%} {_format_score_bar(insight.actionability_score)}")
    lines.append(f"  Impact:         {insight.impact_score:.1%} {_format_score_bar(insight.impact_score)}")
    lines.append(f"  Recency:        {insight.recency_score:.1%} {_format_score_bar(insight.recency_score)}")
    lines.append(f"  Novelty:        {insight.novelty_score:.1%} {_format_score_bar(insight.novelty_score)}")
    lines.append("")

    # Evidence
    if insight.supporting_evidence:
        lines.append("Supporting Evidence:")
        for i, evidence in enumerate(insight.supporting_evidence, 1):
            lines.append(f"  {i}. {evidence}")
        lines.append("")

    # Action
    lines.append("Suggested Action:")
    lines.append(f"  {insight.suggested_action}")
    lines.append("")

    # Metadata
    if insight.metadata:
        lines.append("Metadata:")
        for key, value in insight.metadata.items():
            lines.append(f"  {key}: {value}")

    return "\n".join(lines)


def format_insight_markdown(insight: Insight, level: int = 2) -> str:
    """Format insight as markdown for documentation or reports.

    Args:
        insight: Insight to format
        level: Header level for the insight (2-6)

    Returns:
        str: Markdown formatted insight

    Example:
        ## 💡 Most productive 9-11am (avg 8.2 tasks)

        **Confidence:** 82% ████░

        ### Evidence
        - Analyzed 45 days from 2024-11-15 to 2024-12-30
        - Peak productivity window: 9-11am (40% above average)

        ### Action
        Schedule important tasks during 9-11am to capitalize on high productivity windows
    """
    lines = []

    # Header
    emoji = _get_category_emoji(insight.category)
    header_prefix = "#" * min(max(level, 2), 6)
    lines.append(f"{header_prefix} {emoji} {insight.summary}")
    lines.append("")

    # Confidence and impact
    confidence_bar = _format_score_bar(insight.confidence_score)
    impact_bar = _format_score_bar(insight.impact_score)
    lines.append(f"**Confidence:** {insight.confidence_score:.0%} {confidence_bar}")
    lines.append(f"**Impact:** {insight.impact_score:.0%} {impact_bar}")
    lines.append("")

    # Detailed description
    lines.append(insight.detailed_description)
    lines.append("")

    # Evidence
    if insight.supporting_evidence:
        lines.append(f"{header_prefix}# Evidence")
        lines.append("")
        for evidence in insight.supporting_evidence:
            lines.append(f"- {evidence}")
        lines.append("")

    # Action
    lines.append(f"{header_prefix}# Action")
    lines.append("")
    lines.append(insight.suggested_action)

    return "\n".join(lines)


def _get_category_emoji(category: InsightCategory) -> str:
    """Get emoji representation for insight category.

    Args:
        category: InsightCategory enum value

    Returns:
        str: Emoji for the category
    """
    emoji_map = {
        InsightCategory.TASK_COMPLETION: "💡",
        InsightCategory.HEALTH_CORRELATION: "🏥",
        InsightCategory.HABIT: "🔄",
        InsightCategory.TREND: "📈",
        InsightCategory.BEHAVIORAL: "🧠",
    }
    return emoji_map.get(category, "📊")


def _format_confidence_indicator(confidence: float) -> str:
    """Format confidence score as visual indicator.

    Args:
        confidence: Confidence score (0.0 to 1.0)

    Returns:
        str: Visual confidence indicator

    Examples:
        0.90 → [●●●●● 90% confidence - Very High]
        0.75 → [●●●●○ 75% confidence - High]
        0.60 → [●●●○○ 60% confidence - Moderate]
        0.40 → [●●○○○ 40% confidence - Low]
    """
    # Calculate number of filled circles (out of 5)
    filled = int(confidence * 5)
    empty = 5 - filled

    bar = "●" * filled + "○" * empty
    percentage = f"{confidence:.0%}"

    # Determine confidence level label
    if confidence >= 0.80:
        level = "Very High"
    elif confidence >= 0.70:
        level = "High"
    elif confidence >= 0.60:
        level = "Moderate"
    elif confidence >= 0.40:
        level = "Low"
    else:
        level = "Very Low"

    return f"[{bar} {percentage} confidence - {level}]"


def _format_score_bar(score: float, width: int = 10) -> str:
    """Format a score as a horizontal bar.

    Args:
        score: Score value (0.0 to 1.0)
        width: Width of the bar in characters

    Returns:
        str: Bar representation

    Example:
        0.75 → ████████░░ (8 filled, 2 empty)
    """
    filled = int(score * width)
    empty = width - filled

    return "█" * filled + "░" * empty


def generate_weekly_insights_summary(
    insights: List[Insight],
    period_start: datetime,
    period_end: datetime
) -> str:
    """Generate a complete weekly insights summary with statistics.

    Provides overview of insights by category, confidence distribution,
    and actionability summary.

    Args:
        insights: List of insights for the week
        period_start: Start of the analysis period
        period_end: End of the analysis period

    Returns:
        str: Complete weekly summary with insights and statistics
    """
    if not insights:
        return "No significant patterns detected this week."

    lines = []

    # Header
    lines.append("╔═══════════════════════════════════════════════════════════════╗")
    lines.append("║         WEEKLY PATTERN INSIGHTS SUMMARY                      ║")
    lines.append("╚═══════════════════════════════════════════════════════════════╝")
    lines.append("")
    lines.append(f"Period: {period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}")
    lines.append(f"Total Insights: {len(insights)}")
    lines.append("")

    # Category breakdown
    category_counts = {}
    for insight in insights:
        category = insight.category.value.replace("_", " ").title()
        category_counts[category] = category_counts.get(category, 0) + 1

    lines.append("Insights by Category:")
    for category, count in sorted(category_counts.items()):
        lines.append(f"  • {category}: {count}")
    lines.append("")

    # Confidence distribution
    high_confidence = sum(1 for i in insights if i.confidence_score >= 0.75)
    medium_confidence = sum(1 for i in insights if 0.60 <= i.confidence_score < 0.75)
    low_confidence = sum(1 for i in insights if i.confidence_score < 0.60)

    lines.append("Confidence Distribution:")
    lines.append(f"  • High (≥75%):    {high_confidence}")
    lines.append(f"  • Medium (60-75%): {medium_confidence}")
    lines.append(f"  • Low (<60%):     {low_confidence}")
    lines.append("")

    # Top insights
    lines.append(format_insights_for_weekly_review(
        insights,
        title="📈 Top Insights This Week",
        include_evidence=True,
        max_evidence_per_insight=3
    ))

    return "\n".join(lines)


def format_insights_for_cli_display(
    insights: List[Insight],
    compact: bool = False
) -> str:
    """Format insights for CLI display with color and formatting.

    Args:
        insights: List of insights to display
        compact: If True, use compact single-line format

    Returns:
        str: Formatted insights for terminal display
    """
    if not insights:
        return "No insights to display."

    if compact:
        lines = []
        for i, insight in enumerate(insights, 1):
            lines.append(f"{i}. {format_insight_compact(insight)}")
        return "\n".join(lines)
    else:
        return format_insights_for_weekly_review(insights)


def export_insights_to_markdown_file(
    insights: List[Insight],
    filepath: str,
    title: str = "Pattern Recognition Insights",
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None
) -> None:
    """Export insights to a markdown file for documentation.

    Args:
        insights: List of insights to export
        filepath: Path to write markdown file
        title: Document title
        period_start: Optional start date
        period_end: Optional end date
    """
    lines = []

    # Header
    lines.append(f"# {title}")
    lines.append("")

    if period_start and period_end:
        lines.append(f"**Period:** {period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}")
        lines.append("")

    lines.append(f"**Total Insights:** {len(insights)}")
    lines.append("")

    # Table of contents
    lines.append("## Table of Contents")
    lines.append("")
    for i, insight in enumerate(insights, 1):
        # Create anchor-friendly title
        anchor = insight.summary.lower().replace(" ", "-")
        anchor = "".join(c for c in anchor if c.isalnum() or c == "-")
        lines.append(f"{i}. [{insight.summary}](#{anchor})")
    lines.append("")

    # Insights
    lines.append("## Insights")
    lines.append("")

    for i, insight in enumerate(insights, 1):
        lines.append(f"### {i}. {format_insight_markdown(insight, level=3)}")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Write to file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
