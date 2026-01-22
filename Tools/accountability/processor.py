#!/usr/bin/env python3
"""
Brain Dump Processing Pipeline.

Transforms raw brain dumps into actionable items through:
1. Classification (thought/project/task/worry)
2. Domain routing (work/personal)
3. Impact scoring (personal tasks)
4. Work prioritization (work tasks)
5. Task creation
"""

import re
import json
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

# Handle both CLI and module imports
try:
    from .models import (
        BrainDumpCategory,
        TaskDomain,
        ClassifiedBrainDump,
        CATEGORY_KEYWORDS,
        ImpactScore,
    )
    from .impact_scorer import ImpactScorer
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from models import (
        BrainDumpCategory,
        TaskDomain,
        ClassifiedBrainDump,
        CATEGORY_KEYWORDS,
        ImpactScore,
    )
    from impact_scorer import ImpactScorer

logger = logging.getLogger('brain_dump_processor')


class BrainDumpProcessor:
    """
    Processes brain dumps through the accountability pipeline.

    Flow:
    1. Classify - Determine category (thought/project/task/worry)
    2. Extract - Pull entities, deadlines, blockers
    3. Route - Work vs Personal
    4. Score - Impact (personal) or Priority (work)
    5. Create - Generate tasks/store thoughts
    """

    def __init__(self):
        """Initialize the processor."""
        self.impact_scorer = ImpactScorer()

        # Compile classification patterns
        self.category_patterns: Dict[BrainDumpCategory, re.Pattern] = {}
        for category, keywords in CATEGORY_KEYWORDS.items():
            pattern = r'\b(' + '|'.join(re.escape(k) for k in keywords) + r')\b'
            self.category_patterns[category] = re.compile(pattern, re.IGNORECASE)

        # Domain indicators
        self.work_indicators = [
            'client', 'project', 'meeting', 'deadline', 'deliverable',
            'invoice', 'contract', 'stakeholder', 'sprint', 'ticket',
            'jira', 'github', 'pr', 'merge', 'deploy', 'release',
            # Client names (would be populated from WorkOS)
        ]
        self.personal_indicators = [
            'family', 'home', 'personal', 'doctor', 'appointment',
            'gym', 'exercise', 'kids', 'wife', 'husband', 'birthday',
            'groceries', 'house', 'car', 'insurance', 'health',
            # Family names (Jeremy-specific)
            'ashley', 'sullivan', 'baby', 'nanny', 'childcare', 'support',
            'pregnant', 'pregnancy', 'cushion', 'savings',
        ]

    def process(
        self,
        content: str,
        source: str = "direct",
        context: Optional[Dict[str, Any]] = None
    ) -> ClassifiedBrainDump:
        """
        Process a single brain dump.

        Args:
            content: Raw brain dump content.
            source: Source of the dump (telegram, voice, direct).
            context: Additional context.

        Returns:
            ClassifiedBrainDump with all extracted info.
        """
        context = context or {}
        start_time = datetime.now()
        review_reasons = []

        # Step 1: Classify with confidence
        category, cat_confidence, cat_review = self._classify(content)
        if cat_review:
            review_reasons.append(f"Category: {cat_review}")

        # Step 2: Extract metadata
        title = self._extract_title(content)
        entities = self._extract_entities(content)
        deadline = self._extract_deadline(content)
        energy_hint = self._extract_energy_hint(content)
        blockers = self._extract_blockers(content)

        # Step 3: Determine domain (for tasks) with confidence
        domain = None
        domain_confidence = 1.0
        if category in [BrainDumpCategory.TASK, BrainDumpCategory.PROJECT]:
            domain, domain_confidence, domain_review = self._determine_domain(content)
            if domain_review:
                review_reasons.append(f"Domain: {domain_review}")

        # Step 4: Score impact (for personal items)
        impact_score = None
        if domain == TaskDomain.PERSONAL:
            deadline_days = None
            if deadline:
                deadline_days = (deadline - date.today()).days
            impact_score = self.impact_scorer.score(
                content,
                deadline_days=deadline_days,
                context={'mentioned_people': [e for e in entities if self._is_person(e)]}
            )

        # Calculate overall confidence (minimum of category and domain confidence)
        overall_confidence = min(cat_confidence, domain_confidence) if domain else cat_confidence

        # Flag for review if low confidence
        REVIEW_THRESHOLD = 0.6
        needs_review = overall_confidence < REVIEW_THRESHOLD or len(review_reasons) > 0
        review_reason = "; ".join(review_reasons) if review_reasons else None

        # Create result
        result = ClassifiedBrainDump(
            id=context.get('id', 0),
            raw_content=content,
            category=category,
            domain=domain,
            impact_score=impact_score,
            title=title,
            entities=entities,
            deadline=deadline,
            energy_hint=energy_hint,
            blockers=blockers,
            processed_at=datetime.now(),
            source=source,
            confidence=overall_confidence,
            needs_review=needs_review,
            review_reason=review_reason,
        )

        processing_time = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Processed brain dump: category={category.value}, "
            f"domain={domain.value if domain else 'N/A'}, "
            f"confidence={overall_confidence:.2f}, "
            f"needs_review={needs_review}, "
            f"time={processing_time:.2f}s"
        )

        return result

    def _classify(self, content: str) -> tuple[BrainDumpCategory, float, str | None]:
        """
        Classify content into a category with confidence score.

        Uses keyword matching with priority ordering.

        Returns:
            Tuple of (category, confidence, review_reason)
        """
        content_lower = content.lower()
        scores = {}

        for category, pattern in self.category_patterns.items():
            matches = pattern.findall(content_lower)
            scores[category] = len(matches)

        # Priority order for ties: task > project > worry > idea > thought > observation
        priority = [
            BrainDumpCategory.TASK,
            BrainDumpCategory.PROJECT,
            BrainDumpCategory.WORRY,
            BrainDumpCategory.IDEA,
            BrainDumpCategory.THOUGHT,
            BrainDumpCategory.OBSERVATION,
        ]

        # Find highest scoring with priority tiebreaker
        max_score = max(scores.values()) if scores else 0
        total_matches = sum(scores.values())

        # Calculate confidence based on match clarity
        review_reason = None
        if max_score == 0:
            # No keywords matched - low confidence default
            confidence = 0.3
            review_reason = "No category keywords matched"
            if len(content) < 50:
                return BrainDumpCategory.TASK, confidence, review_reason
            return BrainDumpCategory.THOUGHT, confidence, review_reason

        # Count categories with high scores (competing classifications)
        high_scorers = sum(1 for s in scores.values() if s >= max_score * 0.7 and s > 0)

        if high_scorers > 2:
            # Multiple competing categories
            confidence = 0.4
            review_reason = f"Mixed signals: {high_scorers} competing categories"
        elif high_scorers == 2:
            confidence = 0.6
            review_reason = "Two possible categories"
        elif max_score == 1:
            confidence = 0.7
            review_reason = None  # Single weak match, but clear
        else:
            # Strong, clear match
            confidence = min(0.95, 0.7 + (max_score * 0.05))

        for cat in priority:
            if scores.get(cat, 0) == max_score:
                return cat, confidence, review_reason

        return BrainDumpCategory.THOUGHT, 0.5, "Fallback classification"

    def _determine_domain(self, content: str) -> tuple[TaskDomain, float, str | None]:
        """
        Determine if content is work or personal with confidence.

        Returns:
            Tuple of (domain, confidence, review_reason)
        """
        content_lower = content.lower()

        work_score = sum(1 for w in self.work_indicators if w in content_lower)
        personal_score = sum(1 for p in self.personal_indicators if p in content_lower)

        # Check for explicit markers - high confidence
        if 'work:' in content_lower or '[work]' in content_lower:
            return TaskDomain.WORK, 0.95, None
        if 'personal:' in content_lower or '[personal]' in content_lower:
            return TaskDomain.PERSONAL, 0.95, None

        # Calculate confidence based on score difference
        total_score = work_score + personal_score
        if total_score == 0:
            # No indicators - low confidence default to personal
            return TaskDomain.PERSONAL, 0.4, "No domain indicators found"

        # Check for mixed signals (both work AND personal indicators)
        if work_score > 0 and personal_score > 0:
            diff = abs(work_score - personal_score)
            if diff <= 1:
                # Very close - needs review
                confidence = 0.45
                review_reason = f"Mixed signals: {work_score} work vs {personal_score} personal indicators"
            else:
                # Slight preference
                confidence = 0.6
                review_reason = f"Competing indicators: work={work_score}, personal={personal_score}"
        else:
            # Clear signal
            confidence = min(0.9, 0.6 + (max(work_score, personal_score) * 0.1))
            review_reason = None

        if work_score > personal_score:
            return TaskDomain.WORK, confidence, review_reason
        elif personal_score > work_score:
            return TaskDomain.PERSONAL, confidence, review_reason

        # Default to personal for safety
        return TaskDomain.PERSONAL, 0.5, "Tie broken toward personal"

    def _extract_title(self, content: str) -> str:
        """Extract a title from content."""
        # First line or first sentence
        lines = content.strip().split('\n')
        first_line = lines[0].strip()

        # Truncate if too long
        if len(first_line) > 100:
            # Find sentence end
            for punct in ['.', '!', '?', '-']:
                idx = first_line.find(punct)
                if 0 < idx < 100:
                    return first_line[:idx + 1]
            return first_line[:97] + '...'

        return first_line

    def _extract_entities(self, content: str) -> List[str]:
        """Extract named entities from content."""
        entities = []

        # Find capitalized words that might be names/proper nouns
        words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', content)
        entities.extend(words)

        # Find @mentions
        mentions = re.findall(r'@(\w+)', content)
        entities.extend(mentions)

        # Find #tags
        tags = re.findall(r'#(\w+)', content)
        entities.extend(tags)

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for e in entities:
            if e.lower() not in seen:
                seen.add(e.lower())
                unique.append(e)

        return unique[:10]  # Limit to 10 entities

    def _extract_deadline(self, content: str) -> Optional[date]:
        """Extract deadline date from content."""
        content_lower = content.lower()
        today = date.today()

        # Relative dates
        if 'today' in content_lower:
            return today
        if 'tomorrow' in content_lower:
            return today + timedelta(days=1)
        if 'next week' in content_lower:
            return today + timedelta(days=7)
        if 'this week' in content_lower:
            # Friday of this week
            days_until_friday = (4 - today.weekday()) % 7
            return today + timedelta(days=days_until_friday)

        # Day names
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for i, day in enumerate(days):
            if day in content_lower:
                # Next occurrence of this day
                days_ahead = (i - today.weekday()) % 7
                if days_ahead == 0:
                    days_ahead = 7  # If today, assume next week
                return today + timedelta(days=days_ahead)

        # Date patterns (MM/DD, MM-DD, Month Day)
        # ISO format
        iso_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', content)
        if iso_match:
            try:
                return date.fromisoformat(iso_match.group(1))
            except ValueError:
                pass

        # US format (1/15, 01/15)
        us_match = re.search(r'\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b', content)
        if us_match:
            month, day = int(us_match.group(1)), int(us_match.group(2))
            year = int(us_match.group(3)) if us_match.group(3) else today.year
            if year < 100:
                year += 2000
            try:
                return date(year, month, day)
            except ValueError:
                pass

        return None

    def _extract_energy_hint(self, content: str) -> Optional[str]:
        """Extract energy level hint from content."""
        content_lower = content.lower()

        high_indicators = ['complex', 'difficult', 'important', 'critical', 'deep work', 'focus']
        low_indicators = ['easy', 'simple', 'quick', 'admin', 'routine', 'mindless']
        medium_indicators = ['normal', 'regular', 'standard']

        high_count = sum(1 for h in high_indicators if h in content_lower)
        low_count = sum(1 for l in low_indicators if l in content_lower)
        medium_count = sum(1 for m in medium_indicators if m in content_lower)

        if high_count > low_count and high_count > medium_count:
            return 'high'
        if low_count > high_count and low_count > medium_count:
            return 'low'
        if medium_count > 0:
            return 'medium'

        return None

    def _extract_blockers(self, content: str) -> List[str]:
        """Extract blockers or dependencies."""
        blockers = []
        content_lower = content.lower()

        # Common blocker patterns
        patterns = [
            r'blocked by[:\s]+([^.!?\n]+)',
            r'waiting (?:on|for)[:\s]+([^.!?\n]+)',
            r'depends on[:\s]+([^.!?\n]+)',
            r'need[s]?[:\s]+([^.!?\n]+)(?:first|before)',
            r'after[:\s]+([^.!?\n]+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content_lower)
            blockers.extend(m.strip() for m in matches)

        return blockers[:5]  # Limit to 5 blockers

    def _is_person(self, entity: str) -> bool:
        """Check if entity is likely a person name."""
        # Simple heuristic: capitalized, not a common noun
        common_nouns = {'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday',
                       'Saturday', 'Sunday', 'January', 'February', 'March',
                       'April', 'May', 'June', 'July', 'August', 'September',
                       'October', 'November', 'December', 'Project', 'Task'}
        return entity not in common_nouns and entity[0].isupper()

    async def process_queue(self, limit: int = 10) -> List[ClassifiedBrainDump]:
        """
        Process unprocessed brain dumps from queue.

        Args:
            limit: Maximum number to process.

        Returns:
            List of processed brain dumps.
        """
        # Get unprocessed brain dumps from WorkOS
        try:
            import os
            import httpx

            # This would integrate with workos_get_brain_dump
            # For now, return empty
            logger.info("Queue processing not yet integrated with WorkOS MCP")
            return []

        except Exception as e:
            logger.error(f"Failed to process queue: {e}")
            return []


class BrainDumpRouter:
    """
    Routes processed brain dumps to appropriate handlers.
    """

    def __init__(self):
        self.processor = BrainDumpProcessor()

    async def route(self, brain_dump: ClassifiedBrainDump) -> Dict[str, Any]:
        """
        Route a processed brain dump to appropriate action.

        Args:
            brain_dump: The classified brain dump.

        Returns:
            Result of routing action.
        """
        category = brain_dump.category

        if category == BrainDumpCategory.THOUGHT:
            return await self._store_thought(brain_dump)

        elif category == BrainDumpCategory.PROJECT:
            return await self._create_project(brain_dump)

        elif category == BrainDumpCategory.TASK:
            return await self._create_task(brain_dump)

        elif category == BrainDumpCategory.WORRY:
            return await self._convert_worry(brain_dump)

        elif category == BrainDumpCategory.IDEA:
            return await self._store_idea(brain_dump)

        elif category == BrainDumpCategory.OBSERVATION:
            return await self._log_observation(brain_dump)

        return {'action': 'unknown', 'success': False}

    async def _store_thought(self, bd: ClassifiedBrainDump) -> Dict[str, Any]:
        """Store thought for pattern discovery."""
        # Would integrate with MemOS/ChromaDB for vector storage
        return {
            'action': 'store_thought',
            'success': True,
            'message': f"Thought stored for pattern discovery: {bd.title[:50]}..."
        }

    async def _create_project(self, bd: ClassifiedBrainDump) -> Dict[str, Any]:
        """Create project and decompose into tasks."""
        # Would integrate with WorkOS to create project
        return {
            'action': 'create_project',
            'success': True,
            'message': f"Project created: {bd.title}. Needs decomposition into tasks."
        }

    async def _create_task(self, bd: ClassifiedBrainDump) -> Dict[str, Any]:
        """Create task in appropriate domain."""
        # Would call workos_create_task
        domain = bd.domain.value if bd.domain else 'personal'

        task_data = {
            'title': bd.title,
            'description': bd.raw_content,
            'category': domain,
            'cognitiveLoad': bd.energy_hint or 'medium',
        }

        if bd.deadline:
            task_data['dueDate'] = bd.deadline.isoformat()

        if bd.impact_score:
            task_data['metadata'] = {
                'impact_score': bd.impact_score.to_dict()
            }

        return {
            'action': 'create_task',
            'success': True,
            'domain': domain,
            'task_data': task_data,
            'message': f"Task created ({domain}): {bd.title}"
        }

    async def _convert_worry(self, bd: ClassifiedBrainDump) -> Dict[str, Any]:
        """Convert worry into actionable task."""
        # Worries become tasks with concrete next actions
        title = f"Address: {bd.title}"
        if 'what if' in bd.raw_content.lower():
            title = f"Prepare for: {bd.title}"

        return {
            'action': 'convert_worry',
            'success': True,
            'original_worry': bd.raw_content,
            'converted_task': title,
            'message': f"Worry converted to task: {title}"
        }

    async def _store_idea(self, bd: ClassifiedBrainDump) -> Dict[str, Any]:
        """Store idea for later exploration."""
        return {
            'action': 'store_idea',
            'success': True,
            'message': f"Idea stored: {bd.title}"
        }

    async def _log_observation(self, bd: ClassifiedBrainDump) -> Dict[str, Any]:
        """Log observation for reference."""
        return {
            'action': 'log_observation',
            'success': True,
            'message': f"Observation logged: {bd.title}"
        }


# Convenience function
def process_brain_dump(content: str, source: str = "direct") -> Dict[str, Any]:
    """
    Process a brain dump and return structured result.

    Args:
        content: Raw brain dump content.
        source: Source of the dump.

    Returns:
        Processing result dict.
    """
    processor = BrainDumpProcessor()
    result = processor.process(content, source)
    return result.to_dict()


# CLI interface
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Brain Dump Processor')
    parser.add_argument('content', nargs='?', help='Content to process')
    parser.add_argument('--source', '-s', default='direct', help='Source of dump')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    if args.content:
        result = process_brain_dump(args.content, args.source)

        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"\n=== Brain Dump Processed ===")
            print(f"Category: {result['category']}")
            print(f"Domain: {result['domain'] or 'N/A'}")
            print(f"Title: {result['title']}")

            if result['deadline']:
                print(f"Deadline: {result['deadline']}")
            if result['entities']:
                print(f"Entities: {', '.join(result['entities'][:5])}")
            if result['energy_hint']:
                print(f"Energy: {result['energy_hint']}")
            if result['impact_score']:
                score = result['impact_score']
                print(f"Impact: {score['primary']} ({score['composite']:.1f}/10)")
    else:
        # Demo mode
        print("Brain Dump Processor - Demo")
        print("=" * 50)

        test_cases = [
            "Call mom tomorrow for her birthday",
            "Need to fix the bug in the login page for client Memphis - deadline Friday",
            "I'm worried about the quarterly review next week",
            "Idea: what if we built an AI assistant for task management?",
            "Need to schedule dentist appointment",
            "Project: Migrate database to PostgreSQL",
        ]

        processor = BrainDumpProcessor()
        for content in test_cases:
            result = processor.process(content)
            print(f"\n\"{content[:50]}...\"")
            print(f"  → {result.category.value} | {result.domain.value if result.domain else 'N/A'}")
            if result.impact_score:
                print(f"  → Impact: {result.impact_score.primary_dimension.value} "
                      f"({result.impact_score.composite:.1f}/10)")
