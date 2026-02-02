#!/usr/bin/env python3
"""
Epic Expert Learning - Daily Review & Progress Tracking

Synthesizes day's learnings, updates domain strengths, identifies gaps,
and generates progress summaries.

Usage:
    python daily_review.py
    python daily_review.py --domain orderset_builds
    python daily_review.py --weekly
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

# Paths
SKILL_DIR = Path(__file__).parent.parent
STATE_FILE = SKILL_DIR / "references" / "learning-state.json"


class DailyReviewer:
    """Handles daily/weekly learning reviews and progress tracking."""

    def __init__(self):
        self.state = self.load_state()

    def load_state(self) -> Dict:
        """Load current learning state."""
        if STATE_FILE.exists():
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        return {}

    def save_state(self):
        """Save updated learning state."""
        with open(STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    def get_todays_learnings(self) -> List[Dict]:
        """Get all learnings from today."""
        today = datetime.now(timezone.utc).date().isoformat()
        recent = self.state.get("recent_learnings", [])

        return [
            learning for learning in recent
            if learning.get("date", "").startswith(today)
        ]

    def get_learnings_since(self, days_ago: int) -> List[Dict]:
        """Get learnings from the past N days."""
        cutoff = datetime.now(timezone.utc).date() - timedelta(days=days_ago)
        cutoff_str = cutoff.isoformat()
        recent = self.state.get("recent_learnings", [])

        return [
            learning for learning in recent
            if learning.get("date", "") >= cutoff_str
        ]

    def summarize_learnings(self, learnings: List[Dict]) -> Dict:
        """
        Summarize a set of learnings by domain, source, confidence.
        
        Returns summary dict with counts and breakdowns.
        """
        summary = {
            "total_count": len(learnings),
            "by_domain": defaultdict(int),
            "by_source": defaultdict(int),
            "by_confidence": defaultdict(int),
            "concepts": []
        }

        for learning in learnings:
            summary["by_domain"][learning.get("domain", "unknown")] += 1
            summary["by_source"][learning.get("source", "unknown")] += 1
            summary["by_confidence"][learning.get("confidence", "unknown")] += 1
            summary["concepts"].append({
                "domain": learning.get("domain"),
                "concept": learning.get("concept"),
                "confidence": learning.get("confidence")
            })

        return summary

    def calculate_domain_progress(self) -> List[Dict]:
        """
        Calculate progress for each domain.
        
        Returns list of domain progress objects with:
        - domain name
        - strength level
        - concepts learned
        - strength change (if any)
        """
        domains = self.state.get("domains", {})
        progress = []

        for domain_name, domain_data in domains.items():
            progress.append({
                "domain": domain_name,
                "strength": domain_data.get("strength", "novice"),
                "strength_level": domain_data.get("strength_level", 0),
                "concepts_learned": domain_data.get("concepts_learned", 0),
                "solutions_captured": domain_data.get("solutions_captured", 0),
                "questions_asked": domain_data.get("questions_asked", 0),
                "knowledge_gaps": len(domain_data.get("knowledge_gaps", []))
            })

        # Sort by concepts learned (descending)
        progress.sort(key=lambda x: x["concepts_learned"], reverse=True)

        return progress

    def identify_knowledge_gaps(self) -> List[Dict]:
        """
        Identify and prioritize current knowledge gaps across all domains.
        
        Returns sorted list of gaps by priority.
        """
        gaps = self.state.get("knowledge_gaps", [])

        # Sort by priority (high → medium → low)
        priority_order = {"high": 0, "medium": 1, "low": 2}
        gaps.sort(key=lambda g: priority_order.get(g.get("priority", "low"), 3))

        return gaps

    def suggest_next_learning_targets(self) -> List[str]:
        """
        Suggest specific learning targets based on:
        1. High-priority knowledge gaps
        2. Domains with low concept count but high activity
        3. Priority domains from settings
        """
        suggestions = []

        # Get priority domains
        priority_domains = self.state.get("settings", {}).get("priority_domains", [])

        # Get high-priority gaps
        gaps = self.identify_knowledge_gaps()
        for gap in gaps[:3]:  # Top 3 gaps
            if gap.get("priority") == "high":
                suggestions.append(
                    f"Ask about '{gap.get('gap')}' when working on {gap.get('domain')}"
                )

        # Identify domains with activity but low concepts (learning opportunities)
        domains = self.state.get("domains", {})
        for domain_name in priority_domains:
            if domain_name in domains:
                domain_data = domains[domain_name]
                concepts = domain_data.get("concepts_learned", 0)
                solutions = domain_data.get("solutions_captured", 0)

                if concepts < 15 and solutions > 0:  # Active but still beginner
                    suggestions.append(
                        f"Focus on {domain_name} - active work but still learning"
                    )

        return suggestions[:5]  # Max 5 suggestions

    def generate_daily_summary(self) -> str:
        """Generate formatted daily learning summary."""
        today = datetime.now(timezone.utc).date().isoformat()
        learnings = self.get_todays_learnings()
        summary = self.summarize_learnings(learnings)
        progress = self.calculate_domain_progress()
        gaps = self.identify_knowledge_gaps()
        suggestions = self.suggest_next_learning_targets()

        # Build summary text
        lines = [
            f"📊 Epic Learning Summary - {today}",
            "",
            f"✅ Solutions captured: {summary['by_source'].get('solution_capture', 0)}",
        ]

        # List solutions by domain
        if summary['by_source'].get('solution_capture', 0) > 0:
            for concept in summary['concepts']:
                if 'solution' in concept.get('concept', '').lower():
                    domain_display = concept['domain'].replace('_', ' ').title()
                    lines.append(f"   - {concept['concept']} ({domain_display})")

        lines.append("")
        lines.append(f"💡 Concepts learned: {summary['total_count']}")

        # List concepts by source
        for concept in summary['concepts'][:5]:  # Top 5
            lines.append(f"   - {concept['concept']}")

        lines.append("")
        lines.append("📈 Domain progress:")

        # Show top 3 domains by activity
        for domain_data in progress[:3]:
            domain_display = domain_data['domain'].replace('_', ' ').title()
            strength = domain_data['strength'].capitalize()
            concepts = domain_data['concepts_learned']
            lines.append(f"   - {domain_display}: {strength} ({concepts} concepts)")

        if gaps:
            lines.append("")
            lines.append(f"🎯 Knowledge gaps identified: {len(gaps)}")
            for gap in gaps[:3]:  # Top 3 gaps
                lines.append(f"   - {gap.get('gap')}")

        if suggestions:
            lines.append("")
            lines.append("💭 Suggested next learning:")
            for suggestion in suggestions:
                lines.append(f"   - {suggestion}")

        return "\n".join(lines)

    def generate_weekly_summary(self) -> str:
        """Generate formatted weekly learning summary."""
        week_start = datetime.now(timezone.utc).date() - timedelta(days=7)
        learnings = self.get_learnings_since(7)
        summary = self.summarize_learnings(learnings)
        progress = self.calculate_domain_progress()

        lines = [
            f"📊 Epic Learning Weekly Summary",
            f"   {week_start} to {datetime.now(timezone.utc).date()}",
            "",
            f"📚 Total concepts learned this week: {summary['total_count']}",
            "",
            "📈 Domain breakdown:"
        ]

        for domain, count in summary['by_domain'].items():
            domain_display = domain.replace('_', ' ').title()
            lines.append(f"   - {domain_display}: {count} concepts")

        lines.append("")
        lines.append("🏆 Current expertise levels:")

        for domain_data in progress:
            domain_display = domain_data['domain'].replace('_', ' ').title()
            strength = domain_data['strength'].capitalize()
            concepts = domain_data['concepts_learned']
            lines.append(f"   - {domain_display}: {strength} ({concepts} concepts)")

        # Calculate learning velocity
        global_stats = self.state.get("global_stats", {})
        days_active = global_stats.get("days_active", 1)
        avg_per_day = global_stats.get("avg_concepts_per_day", 0)

        lines.append("")
        lines.append(f"⚡ Learning velocity: {avg_per_day:.1f} concepts/day over {days_active} days")

        # Projection to expert level
        if avg_per_day > 0:
            # Assume "expert" = 150 total concepts across domains
            total_concepts = global_stats.get("total_concepts_learned", 0)
            expert_target = 150
            remaining = max(0, expert_target - total_concepts)
            days_to_expert = remaining / avg_per_day

            lines.append(f"🎯 Projected to expert level in ~{int(days_to_expert)} days at current pace")

        return "\n".join(lines)

    def update_review_timestamp(self):
        """Update last review timestamp in session history."""
        if "session_history" not in self.state:
            self.state["session_history"] = {}

        self.state["session_history"]["last_review_timestamp"] = \
            datetime.now(timezone.utc).isoformat()

        self.save_state()


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Epic Daily Review")
    parser.add_argument("--weekly", "-w", action="store_true",
                       help="Generate weekly summary instead of daily")
    parser.add_argument("--domain", "-d", type=str,
                       help="Show progress for specific domain")

    args = parser.parse_args()

    reviewer = DailyReviewer()

    if args.domain:
        # Domain-specific progress
        domain_data = reviewer.state.get("domains", {}).get(args.domain)
        if not domain_data:
            print(f"❌ Domain not found: {args.domain}")
            return

        domain_display = args.domain.replace('_', ' ').title()
        print(f"\n📊 {domain_display} Progress\n")
        print(f"Strength: {domain_data.get('strength', 'novice').capitalize()}")
        print(f"Concepts learned: {domain_data.get('concepts_learned', 0)}")
        print(f"Solutions captured: {domain_data.get('solutions_captured', 0)}")
        print(f"Questions asked: {domain_data.get('questions_asked', 0)}")

        print("\nRecent concepts:")
        for concept in domain_data.get("recent_concepts", [])[:5]:
            print(f"  - {concept.get('concept')} ({concept.get('learned_date')})")

        gaps = domain_data.get("knowledge_gaps", [])
        if gaps:
            print(f"\nKnowledge gaps ({len(gaps)}):")
            for gap in gaps:
                print(f"  - {gap}")

    elif args.weekly:
        summary = reviewer.generate_weekly_summary()
        print("\n" + summary + "\n")
        reviewer.update_review_timestamp()

    else:
        summary = reviewer.generate_daily_summary()
        print("\n" + summary + "\n")
        reviewer.update_review_timestamp()


if __name__ == "__main__":
    main()
