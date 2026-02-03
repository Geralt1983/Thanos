"""
Value Detection for Thanos Memory System.

Detects user values, priorities, and important relationships through
linguistic analysis and behavioral patterns.
"""

import os
import json
import uuid
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ValueDetectionResult:
    """Result of value detection analysis."""
    value_detected: bool
    value_type: Optional[str]
    title: Optional[str]
    description: Optional[str]
    emotional_weight: float  # 0-1 based on emphasis
    explicit: bool  # Was explicitly stated as important
    domain: Optional[str]
    related_entity: Optional[str]
    evidence_quote: Optional[str]
    confidence: float


@dataclass
class EntityMention:
    """A detected mention of a person or entity."""
    name: str
    entity_type: str  # client, colleague, family, friend, etc.
    context: str  # The surrounding context
    sentiment: Optional[str]
    commitment_detected: bool
    commitment_text: Optional[str]


# Value detection patterns
VALUE_PATTERNS = {
    "priority": {
        "patterns": [
            r"\b(this is|that'?s) (really )?(important|critical|crucial|vital)\b",
            r"\b(top|#1|number one|highest) priority\b",
            r"\b(must|need to|have to) (make sure|ensure)\b",
            r"\b(focus|focusing) on\b",
            r"\bcan'?t (miss|forget|skip)\b",
        ],
        "weight": 0.8
    },
    "boundary": {
        "patterns": [
            r"\bi (don'?t|won'?t|never) .+ on (weekends?|sundays?|saturdays?)\b",
            r"\b(non-?negotiable|off-?limits|sacred)\b",
            r"\bi always\b",
            r"\bi never\b",
            r"\bno matter what\b",
            r"\bline in the sand\b",
        ],
        "weight": 0.85
    },
    "relationship": {
        "patterns": [
            r"\bmy (most important|best|key|main) (client|customer)\b",
            r"\b(love|adore|appreciate) working with\b",
            r"\b(great|amazing|awesome) (relationship|partnership) with\b",
            r"\bcan'?t (let down|disappoint)\b",
        ],
        "weight": 0.75
    },
    "commitment_value": {
        "patterns": [
            r"\bi promised\b",
            r"\bi gave my word\b",
            r"\bi committed to\b",
            r"\bi said i would\b",
            r"\bmy word is\b",
        ],
        "weight": 0.8
    },
    "principle": {
        "patterns": [
            r"\bi (always|never) .+ (code|work|write)\b",
            r"\b(quality|clean code|testing) (matters|is important)\b",
            r"\bi believe (in|that)\b",
            r"\bthe (right|proper|correct) way\b",
        ],
        "weight": 0.7
    },
    "goal": {
        "patterns": [
            r"\b(want|need|hope) to (achieve|accomplish|reach)\b",
            r"\bmy goal is\b",
            r"\bworking (toward|towards)\b",
            r"\baiming (for|to)\b",
            r"\bby (end of|the end of) (year|quarter|month)\b",
        ],
        "weight": 0.75
    }
}

# Emotional emphasis indicators
EMPHASIS_PATTERNS = [
    (r"!{2,}", 0.15),           # Multiple exclamation marks
    (r"\b(really|very|so|extremely|incredibly)\b", 0.1),
    (r"\b(love|care about|value)\b", 0.15),
    (r"\b(crucial|critical|vital|essential)\b", 0.2),
    (r"\bABSOLUTELY\b", 0.2),   # All caps emphasis
]

# Entity type detection
ENTITY_TYPE_PATTERNS = {
    "client": [r"\bclient\b", r"\bcustomer\b", r"\bthe .+ (project|account)\b"],
    "colleague": [r"\bcolleague\b", r"\bcoworker\b", r"\bteammate\b", r"\bon my team\b"],
    "family": [r"\b(wife|husband|spouse|partner)\b", r"\b(mom|dad|mother|father)\b",
               r"\b(son|daughter|kids?|children)\b", r"\b(brother|sister)\b"],
    "friend": [r"\bfriend\b", r"\bbuddy\b", r"\bpal\b"],
    "stakeholder": [r"\bstakeholder\b", r"\bexecutive\b", r"\bboss\b", r"\bmanager\b"],
    "vendor": [r"\bvendor\b", r"\bsupplier\b", r"\bcontractor\b"],
}


class ValueDetector:
    """
    Detects user values and priorities through analysis of their inputs.

    Values are recognized through:
    - Explicit priority statements
    - Emotional emphasis
    - Protective language (boundaries)
    - Repeated mentions
    - Commitment patterns
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "anthropic/claude-sonnet-4-5"):
        """
        Initialize the detector.

        Args:
            api_key: Anthropic API key for AI-powered detection.
            model: Claude model for complex analysis.
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.model = model
        self._client = None

    @property
    def client(self):
        """Lazy-load Anthropic client."""
        if self._client is None and self.api_key:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                logger.warning("anthropic package not installed")
        return self._client

    def detect(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        use_ai: bool = True
    ) -> Optional[ValueDetectionResult]:
        """
        Detect values in user input.

        Args:
            text: The user input to analyze.
            context: Optional context (recent activities, etc.)
            use_ai: Whether to use AI for nuanced analysis.

        Returns:
            ValueDetectionResult if value detected, None otherwise.
        """
        if not text or not text.strip():
            return None

        # Step 1: Pattern-based detection
        pattern_result = self._detect_by_patterns(text)

        # Step 2: Calculate emotional weight
        emotional_weight = self._calculate_emotional_weight(text)

        # Step 3: AI analysis for nuanced detection
        if use_ai and self.client and (not pattern_result or pattern_result.confidence < 0.7):
            ai_result = self._ai_detect(text, context)
            if ai_result:
                # Merge results, preferring higher confidence
                if not pattern_result or ai_result.confidence > pattern_result.confidence:
                    ai_result.emotional_weight = max(
                        ai_result.emotional_weight,
                        emotional_weight
                    )
                    return ai_result

        if pattern_result:
            pattern_result.emotional_weight = max(
                pattern_result.emotional_weight,
                emotional_weight
            )

        return pattern_result

    def _detect_by_patterns(self, text: str) -> Optional[ValueDetectionResult]:
        """Detect values using pattern matching."""
        text_lower = text.lower()
        detected_values: List[Tuple[str, float, str]] = []

        for value_type, config in VALUE_PATTERNS.items():
            for pattern in config["patterns"]:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    detected_values.append((
                        value_type,
                        config["weight"],
                        match.group(0)
                    ))
                    break  # One match per type is enough

        if not detected_values:
            return None

        # Get the highest confidence value
        detected_values.sort(key=lambda x: x[1], reverse=True)
        best_match = detected_values[0]

        # Extract title from the text
        title = self._extract_value_title(text, best_match[0])

        return ValueDetectionResult(
            value_detected=True,
            value_type=best_match[0],
            title=title,
            description=text[:200],
            emotional_weight=0.5,
            explicit=best_match[0] == "priority",
            domain=self._infer_domain(text),
            related_entity=self._extract_entity_name(text),
            evidence_quote=best_match[2],
            confidence=best_match[1]
        )

    def _calculate_emotional_weight(self, text: str) -> float:
        """Calculate emotional emphasis in the text."""
        weight = 0.5  # Base weight

        for pattern, boost in EMPHASIS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                weight += boost

        # Check for all-caps words (emphasis)
        caps_words = len(re.findall(r'\b[A-Z]{3,}\b', text))
        if caps_words >= 2:
            weight += 0.1

        return min(1.0, weight)

    def _extract_value_title(self, text: str, value_type: str) -> str:
        """Extract a concise title for the detected value."""
        # Try to extract the core subject
        # This is a simplified extraction - AI does better

        # For boundaries, extract what's protected
        if value_type == "boundary":
            match = re.search(r"(weekends?|sundays?|saturdays?|family time|personal time)", text, re.I)
            if match:
                return f"Protected: {match.group(1).title()}"

        # For priorities, extract what's important
        if value_type == "priority":
            match = re.search(r"(focus(?:ing)? on|priority[:\s]+)(.{10,50})", text, re.I)
            if match:
                return match.group(2).strip()[:50]

        # Default: use first 50 chars
        return text[:50].strip() + ("..." if len(text) > 50 else "")

    def _infer_domain(self, text: str) -> Optional[str]:
        """Infer the domain (work/personal) from text."""
        work_signals = [
            r"\b(client|customer|project|deadline|meeting|report|pr|code)\b",
            r"\b(team|colleague|boss|manager)\b",
            r"\b(work|office|job)\b",
        ]

        personal_signals = [
            r"\b(family|home|personal|weekend)\b",
            r"\b(wife|husband|kids|children)\b",
            r"\b(health|exercise|gym|doctor)\b",
        ]

        work_score = sum(1 for p in work_signals if re.search(p, text, re.I))
        personal_score = sum(1 for p in personal_signals if re.search(p, text, re.I))

        if work_score > personal_score:
            return "work"
        elif personal_score > work_score:
            return "personal"
        return None

    def _extract_entity_name(self, text: str) -> Optional[str]:
        """Extract a person or entity name from text."""
        # Look for names (capitalized words not at sentence start)
        # This is simplified - a proper NER would be better

        # Pattern for names: "with Mike", "to Sarah", etc.
        match = re.search(
            r"\b(with|to|for|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
            text
        )
        if match:
            return match.group(2)

        # Pattern for possessive: "Mike's", "Sarah's"
        match = re.search(r"\b([A-Z][a-z]+)'s\b", text)
        if match:
            return match.group(1)

        return None

    def detect_entities(self, text: str) -> List[EntityMention]:
        """
        Detect mentions of people and entities in text.

        Args:
            text: The text to analyze.

        Returns:
            List of detected entity mentions.
        """
        entities = []

        # Extract potential names
        names = self._extract_potential_names(text)

        for name in names:
            entity_type = self._classify_entity(text, name)
            sentiment = self._infer_entity_sentiment(text, name)

            # Check for commitment
            commitment_detected = False
            commitment_text = None
            commitment_match = re.search(
                rf"\b(promised|committed|said i would|told)\s+{re.escape(name)}\b",
                text, re.I
            )
            if commitment_match:
                commitment_detected = True
                commitment_text = text[commitment_match.start():commitment_match.end() + 50]

            entities.append(EntityMention(
                name=name,
                entity_type=entity_type,
                context=self._get_name_context(text, name),
                sentiment=sentiment,
                commitment_detected=commitment_detected,
                commitment_text=commitment_text
            ))

        return entities

    def _extract_potential_names(self, text: str) -> List[str]:
        """Extract potential person names from text."""
        names = set()

        # Pattern 1: Capitalized words after prepositions
        matches = re.findall(
            r"\b(?:with|to|for|from|told|asked)\s+([A-Z][a-z]+)",
            text
        )
        names.update(matches)

        # Pattern 2: Possessive names
        matches = re.findall(r"\b([A-Z][a-z]+)'s\b", text)
        names.update(matches)

        # Pattern 3: Names with roles
        matches = re.findall(
            r"\b([A-Z][a-z]+)\s+(?:said|asked|wants|needs)\b",
            text
        )
        names.update(matches)

        # Filter out common words that might be capitalized
        common_words = {'The', 'This', 'That', 'What', 'When', 'Where', 'How', 'Why',
                       'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday',
                       'Saturday', 'Sunday', 'January', 'February', 'March',
                       'April', 'May', 'June', 'July', 'August', 'September',
                       'October', 'November', 'December'}

        return [n for n in names if n not in common_words]

    def _classify_entity(self, text: str, name: str) -> str:
        """Classify the type of entity based on context."""
        text_lower = text.lower()

        for entity_type, patterns in ENTITY_TYPE_PATTERNS.items():
            for pattern in patterns:
                # Check if pattern appears near the name
                if re.search(f"{pattern}.*{name}|{name}.*{pattern}", text_lower, re.I):
                    return entity_type

        return "other"

    def _infer_entity_sentiment(self, text: str, name: str) -> Optional[str]:
        """Infer sentiment toward the mentioned entity."""
        # Get context around the name
        context = self._get_name_context(text, name).lower()

        positive = ['love', 'great', 'amazing', 'awesome', 'appreciate', 'thank']
        negative = ['frustrated', 'annoyed', 'disappointed', 'let down', 'angry']

        for word in positive:
            if word in context:
                return "positive"

        for word in negative:
            if word in context:
                return "negative"

        return "neutral"

    def _get_name_context(self, text: str, name: str) -> str:
        """Get the context surrounding a name mention."""
        match = re.search(rf'\b{re.escape(name)}\b', text)
        if match:
            start = max(0, match.start() - 30)
            end = min(len(text), match.end() + 30)
            return text[start:end]
        return ""

    def _ai_detect(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[ValueDetectionResult]:
        """Use AI for nuanced value detection."""
        if not self.client:
            return None

        prompt = f"""Analyze this user input for signals of what matters to them (values):

1. Priority - Something explicitly important
2. Boundary - Something they protect or won't compromise
3. Relationship - Someone who matters to them
4. Commitment - Keeping promises matters
5. Principle - How they prefer to work
6. Goal - Something they're working toward
7. Preference - How they like things done

User input: "{text}"

{f'Context: {json.dumps(context)}' if context else ''}

Return JSON only:
{{"value_detected": true/false, "value_type": "type or null", "title": "short title", "description": "what this value represents", "emotional_weight": 0.0-1.0, "explicit": true/false, "domain": "work/personal/null", "related_entity": "person/project name or null", "evidence_quote": "the text that revealed this", "confidence": 0.0-1.0}}
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            result_text = response.content[0].text.strip()

            # Parse JSON
            if result_text.startswith('{'):
                result = json.loads(result_text)
            else:
                start = result_text.find('{')
                end = result_text.rfind('}')
                if start != -1 and end != -1:
                    result = json.loads(result_text[start:end + 1])
                else:
                    return None

            if not result.get('value_detected'):
                return None

            return ValueDetectionResult(
                value_detected=True,
                value_type=result.get('value_type'),
                title=result.get('title'),
                description=result.get('description'),
                emotional_weight=result.get('emotional_weight', 0.5),
                explicit=result.get('explicit', False),
                domain=result.get('domain'),
                related_entity=result.get('related_entity'),
                evidence_quote=result.get('evidence_quote'),
                confidence=result.get('confidence', 0.5)
            )

        except Exception as e:
            logger.error(f"AI value detection failed: {e}")
            return None


# Convenience function
def detect_value(
    text: str,
    context: Optional[Dict[str, Any]] = None
) -> Optional[ValueDetectionResult]:
    """
    Convenience function to detect values in text.

    Args:
        text: User input to analyze.
        context: Optional context.

    Returns:
        ValueDetectionResult if value detected, None otherwise.
    """
    detector = ValueDetector()
    return detector.detect(text, context)


if __name__ == "__main__":
    # Test the detector
    test_cases = [
        "Mike is my most important client right now",
        "Family dinner on Sundays is non-negotiable",
        "I promised Sarah I'd have the design ready by Friday",
        "Quality code matters more than speed",
        "Need to focus on the Memphis project this week",
        "Just need to review the PR quickly",
        "I REALLY care about getting this launch right",
    ]

    detector = ValueDetector()

    for text in test_cases:
        result = detector.detect(text, use_ai=False)
        print(f"\n{'='*60}")
        print(f"Input: {text}")
        if result:
            print(f"Value Type: {result.value_type}")
            print(f"Title: {result.title}")
            print(f"Emotional Weight: {result.emotional_weight:.2f}")
            print(f"Explicit: {result.explicit}")
            print(f"Domain: {result.domain}")
            print(f"Entity: {result.related_entity}")
            print(f"Confidence: {result.confidence:.2f}")
        else:
            print("No value detected")

        # Also test entity detection
        entities = detector.detect_entities(text)
        if entities:
            print(f"Entities found: {[e.name for e in entities]}")
