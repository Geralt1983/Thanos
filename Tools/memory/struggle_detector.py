"""
Struggle Detection for Thanos Memory System.

Detects user difficulties, frustrations, and blockers through
linguistic analysis, behavioral patterns, and contextual signals.
"""

import os
import json
import uuid
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class StruggleDetectionResult:
    """Result of struggle detection analysis."""
    struggle_detected: bool
    struggle_type: Optional[str]
    confidence: float
    severity: str  # low, medium, high
    reasoning: str
    suggested_response: Optional[str]
    trigger_patterns: Optional[List[str]] = None


# Linguistic patterns that indicate struggles
STRUGGLE_PATTERNS = {
    "confusion": {
        "patterns": [
            r"\b(don'?t|doesn'?t|can'?t) (understand|get|know)\b",
            r"\b(confused|confusing|unclear)\b",
            r"\bwhat (does|is|are) .+ mean\b",
            r"\bhow (do|does|can) I\b",
            r"\bi'?m (lost|stuck)\b",
            r"\bmakes? no sense\b",
        ],
        "weight": 0.8
    },
    "frustration": {
        "patterns": [
            r"\b(ugh+|argh+|grr+)\b",
            r"!{2,}",
            r"\b(frustrated|annoying|annoyed|irritating|irritated)\b",
            r"\b(stupid|dumb|idiotic)\b",
            r"\b(hate|hating)\b",
            r"\bwhy (won'?t|doesn'?t|can'?t)\b",
            r"\bthis is (ridiculous|insane|crazy)\b",
        ],
        "weight": 0.85
    },
    "blocked": {
        "patterns": [
            r"\bwaiting (for|on)\b",
            r"\bcan'?t (proceed|continue|move forward)\b",
            r"\b(blocked|blocking|blocker)\b",
            r"\bdependent on\b",
            r"\bneed .+ (first|before)\b",
            r"\bstuck (on|at|with)\b",
        ],
        "weight": 0.75
    },
    "overwhelmed": {
        "patterns": [
            r"\b(so much|too much|overwhelming)\b",
            r"\beverything\b",
            r"\b(drowning|buried|swamped)\b",
            r"\bno idea where to (start|begin)\b",
            r"\b(can'?t handle|can'?t cope)\b",
            r"\blist of .+ things\b",
        ],
        "weight": 0.8
    },
    "procrastination": {
        "patterns": [
            r"\bi (should|need to|have to|gotta) (really )?.+\.\.\.",
            r"\bmaybe (later|tomorrow|next week)\b",
            r"\bi'?ll (do it|get to it) (later|soon|eventually)\b",
            r"\bjust (one more|another)\b",
            r"\b(putting off|avoiding)\b",
        ],
        "weight": 0.65
    },
    "decision_paralysis": {
        "patterns": [
            r"\bshould I .+ or .+\?",
            r"\bcan'?t (decide|choose)\b",
            r"\b(option|choice) (a|1) or (option|choice) (b|2)\b",
            r"\bpros and cons\b",
            r"\b(weighing|considering) (options|choices)\b",
            r"\bnot sure (which|what|if)\b",
        ],
        "weight": 0.7
    },
    "energy_low": {
        "patterns": [
            r"\b(tired|exhausted|drained|wiped)\b",
            r"\b(need|needs|want) (a )?break\b",
            r"\b(burnt? out|burned out)\b",
            r"\b(no energy|low energy)\b",
            r"\bcan'?t (focus|concentrate)\b",
            r"\bbrain (fog|fried|dead)\b",
        ],
        "weight": 0.75
    },
    "deadline_pressure": {
        "patterns": [
            r"\b(deadline|due|overdue)\b",
            r"\brunning out of time\b",
            r"\bnot enough time\b",
            r"\b(tomorrow|today) .+ (due|deadline)\b",
            r"\bcrunch (time|mode)\b",
            r"\b(behind|late|delayed)\b",
        ],
        "weight": 0.7
    },
    "technical": {
        "patterns": [
            r"\b(bug|error|exception|crash)\b",
            r"\b(not working|broken|failing)\b",
            r"\b(timeout|timed out)\b",
            r"\bdoesn'?t (work|compile|run|build)\b",
            r"\b(500|404|error code)\b",
        ],
        "weight": 0.7
    }
}

# Explicit struggle phrases (very high confidence)
EXPLICIT_STRUGGLE_PHRASES = [
    (r"\bi'?m struggling (with|to)\b", "explicit", 0.95),
    (r"\bthis is (hard|difficult|tough)\b", "explicit", 0.85),
    (r"\bi need help\b", "explicit", 0.9),
    (r"\bhelp me\b", "explicit", 0.85),
    (r"\bi'?m having (trouble|problems|issues)\b", "explicit", 0.9),
]

# Severity modifiers
SEVERITY_AMPLIFIERS = [
    r"!{3,}",           # Multiple exclamation marks
    r"\b(very|really|so|extremely|incredibly)\b",
    r"\bALL CAPS\b",    # Will check separately
    r"\b(always|never|constantly)\b",
]

SEVERITY_DAMPENERS = [
    r"\b(kind of|sort of|a bit|slightly|somewhat)\b",
    r"\bmaybe\b",
    r"\bjust\b",
]


class StruggleDetector:
    """
    Detects struggles in user input through linguistic and behavioral analysis.

    Uses a combination of:
    - Pattern matching for linguistic signals
    - AI-powered analysis for nuanced detection
    - Behavioral pattern tracking over time
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
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
    ) -> StruggleDetectionResult:
        """
        Detect struggles in user input.

        Args:
            text: The user input to analyze.
            context: Optional context (recent activities, current task, etc.)
            use_ai: Whether to use AI for nuanced analysis.

        Returns:
            StruggleDetectionResult with detection findings.
        """
        if not text or not text.strip():
            return StruggleDetectionResult(
                struggle_detected=False,
                struggle_type=None,
                confidence=0.0,
                severity="none",
                reasoning="Empty input"
            )

        # Step 1: Pattern-based detection
        pattern_result = self._detect_by_patterns(text)

        # Step 2: Check explicit phrases
        explicit_result = self._check_explicit_phrases(text)

        # Step 3: Merge pattern and explicit results
        if explicit_result and explicit_result.confidence > pattern_result.confidence:
            merged_result = explicit_result
        else:
            merged_result = pattern_result

        # Step 4: Adjust severity based on modifiers
        severity = self._calculate_severity(text, merged_result.confidence)
        merged_result.severity = severity

        # Step 5: AI analysis for edge cases (if enabled and confidence is moderate)
        if use_ai and self.client and 0.3 <= merged_result.confidence <= 0.7:
            ai_result = self._ai_detect(text, context)
            if ai_result:
                # AI can override pattern detection
                if ai_result.confidence > merged_result.confidence:
                    return ai_result

        return merged_result

    def _detect_by_patterns(self, text: str) -> StruggleDetectionResult:
        """Detect struggles using pattern matching."""
        text_lower = text.lower()
        detected_types: List[Tuple[str, float, List[str]]] = []

        for struggle_type, config in STRUGGLE_PATTERNS.items():
            matched_patterns = []
            for pattern in config["patterns"]:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    matched_patterns.append(pattern)

            if matched_patterns:
                # Calculate confidence based on number of matches and weight
                match_score = min(len(matched_patterns) * 0.3, 1.0)
                confidence = config["weight"] * match_score
                detected_types.append((struggle_type, confidence, matched_patterns))

        if not detected_types:
            return StruggleDetectionResult(
                struggle_detected=False,
                struggle_type=None,
                confidence=0.0,
                severity="none",
                reasoning="No struggle patterns detected",
                suggested_response=None
            )

        # Get the highest confidence struggle type
        detected_types.sort(key=lambda x: x[1], reverse=True)
        best_match = detected_types[0]

        return StruggleDetectionResult(
            struggle_detected=True,
            struggle_type=best_match[0],
            confidence=best_match[1],
            severity="medium",  # Will be adjusted later
            reasoning=f"Detected {best_match[0]} signals",
            suggested_response=self._get_suggested_response(best_match[0]),
            trigger_patterns=best_match[2]
        )

    def _check_explicit_phrases(self, text: str) -> Optional[StruggleDetectionResult]:
        """Check for explicit struggle statements."""
        text_lower = text.lower()

        for pattern, label, confidence in EXPLICIT_STRUGGLE_PHRASES:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return StruggleDetectionResult(
                    struggle_detected=True,
                    struggle_type="explicit",
                    confidence=confidence,
                    severity="medium",
                    reasoning=f"Explicit struggle statement detected",
                    suggested_response="I hear you. What specifically can I help with?",
                    trigger_patterns=[pattern]
                )

        return None

    def _calculate_severity(self, text: str, base_confidence: float) -> str:
        """Calculate severity based on text modifiers."""
        severity_score = base_confidence

        # Check for amplifiers
        for pattern in SEVERITY_AMPLIFIERS:
            if pattern == r"\bALL CAPS\b":
                # Check for all caps words
                caps_words = len(re.findall(r'\b[A-Z]{3,}\b', text))
                if caps_words >= 2:
                    severity_score += 0.15
            elif re.search(pattern, text, re.IGNORECASE):
                severity_score += 0.1

        # Check for dampeners
        for pattern in SEVERITY_DAMPENERS:
            if re.search(pattern, text, re.IGNORECASE):
                severity_score -= 0.1

        # Clamp and categorize
        severity_score = max(0, min(1, severity_score))

        if severity_score < 0.4:
            return "low"
        elif severity_score < 0.7:
            return "medium"
        else:
            return "high"

    def _get_suggested_response(self, struggle_type: str) -> str:
        """Get an empathetic suggested response for the struggle type."""
        responses = {
            "confusion": "That can be confusing. Would it help if I explained it differently?",
            "frustration": "That sounds frustrating. Let's see if we can find a way forward.",
            "blocked": "Being blocked is tough. Is there anything I can help unblock?",
            "overwhelmed": "That's a lot. Let's break it down into smaller pieces.",
            "procrastination": "Sometimes getting started is the hardest part. What's the smallest first step?",
            "decision_paralysis": "Decisions can be tough. What matters most to you here?",
            "energy_low": "Sounds like you could use a break. Rest is productive too.",
            "deadline_pressure": "Tight timelines are stressful. What's the most critical thing right now?",
            "technical": "Technical issues are frustrating. Let's debug this together.",
        }
        return responses.get(struggle_type, "I'm here to help. What do you need?")

    def _ai_detect(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[StruggleDetectionResult]:
        """Use AI for nuanced struggle detection."""
        if not self.client:
            return None

        prompt = f"""Analyze this user input for signs of struggle. Consider:

1. Confusion - Not understanding something
2. Frustration - Emotional difficulty
3. Blocked - External dependency stopping progress
4. Overwhelmed - Too much to handle
5. Procrastination - Avoiding something
6. Decision paralysis - Can't decide
7. Energy low - Depleted
8. Deadline pressure - Time stress
9. Technical - Technical problem

User input: "{text}"

{f'Context: {json.dumps(context)}' if context else ''}

Return JSON only:
{{"struggle_detected": true/false, "struggle_type": "type or null", "confidence": 0.0-1.0, "severity": "low/medium/high", "reasoning": "brief explanation", "suggested_response": "empathetic response"}}
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
                # Try to extract JSON from response
                start = result_text.find('{')
                end = result_text.rfind('}')
                if start != -1 and end != -1:
                    result = json.loads(result_text[start:end + 1])
                else:
                    return None

            return StruggleDetectionResult(
                struggle_detected=result.get('struggle_detected', False),
                struggle_type=result.get('struggle_type'),
                confidence=result.get('confidence', 0.5),
                severity=result.get('severity', 'medium'),
                reasoning=result.get('reasoning', 'AI analysis'),
                suggested_response=result.get('suggested_response')
            )

        except Exception as e:
            logger.error(f"AI struggle detection failed: {e}")
            return None

    def analyze_patterns(
        self,
        struggles: List[Dict[str, Any]],
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze struggle patterns over time.

        Args:
            struggles: List of struggle records from database.
            days: Number of days to analyze.

        Returns:
            Pattern analysis results.
        """
        if not struggles:
            return {
                "total_struggles": 0,
                "patterns": [],
                "recommendations": []
            }

        # Count by type
        type_counts = {}
        time_counts = {"morning": 0, "afternoon": 0, "evening": 0, "night": 0}
        day_counts = {i: 0 for i in range(7)}
        project_counts = {}

        for s in struggles:
            # Type frequency
            stype = s.get('struggle_type', 'unknown')
            type_counts[stype] = type_counts.get(stype, 0) + 1

            # Time of day
            tod = s.get('time_of_day', 'unknown')
            if tod in time_counts:
                time_counts[tod] += 1

            # Day of week
            dow = s.get('day_of_week')
            if dow is not None and dow in day_counts:
                day_counts[dow] += 1

            # Project
            project = s.get('project')
            if project:
                project_counts[project] = project_counts.get(project, 0) + 1

        # Find patterns
        patterns = []

        # Most common struggle type
        if type_counts:
            most_common = max(type_counts, key=type_counts.get)
            patterns.append({
                "pattern": f"Most common struggle: {most_common}",
                "count": type_counts[most_common],
                "percentage": type_counts[most_common] / len(struggles) * 100
            })

        # Peak struggle time
        if time_counts:
            peak_time = max(time_counts, key=time_counts.get)
            if time_counts[peak_time] > 0:
                patterns.append({
                    "pattern": f"Struggles peak in the {peak_time}",
                    "count": time_counts[peak_time]
                })

        # Problem project
        if project_counts:
            problem_project = max(project_counts, key=project_counts.get)
            patterns.append({
                "pattern": f"Most struggles related to: {problem_project}",
                "count": project_counts[problem_project]
            })

        # Generate recommendations
        recommendations = self._generate_recommendations(
            type_counts, time_counts, project_counts
        )

        return {
            "total_struggles": len(struggles),
            "by_type": type_counts,
            "by_time": time_counts,
            "by_day": day_counts,
            "by_project": project_counts,
            "patterns": patterns,
            "recommendations": recommendations
        }

    def _generate_recommendations(
        self,
        type_counts: Dict[str, int],
        time_counts: Dict[str, int],
        project_counts: Dict[str, int]
    ) -> List[str]:
        """Generate recommendations based on struggle patterns."""
        recommendations = []

        # Type-based recommendations
        if type_counts.get("energy_low", 0) >= 3:
            recommendations.append(
                "Consider scheduling demanding tasks earlier when energy is higher"
            )

        if type_counts.get("overwhelmed", 0) >= 3:
            recommendations.append(
                "Try breaking large tasks into smaller, manageable chunks"
            )

        if type_counts.get("frustration", 0) >= 5:
            recommendations.append(
                "High frustration detected. Consider taking short breaks when frustration builds"
            )

        # Time-based recommendations
        if time_counts.get("afternoon", 0) > time_counts.get("morning", 0) * 2:
            recommendations.append(
                "Afternoon slump detected. Try scheduling complex work in the morning"
            )

        if time_counts.get("night", 0) >= 3:
            recommendations.append(
                "Late-night struggles suggest overwork. Consider ending work earlier"
            )

        return recommendations


# Convenience function
def detect_struggle(
    text: str,
    context: Optional[Dict[str, Any]] = None
) -> StruggleDetectionResult:
    """
    Convenience function to detect struggles in text.

    Args:
        text: User input to analyze.
        context: Optional context.

    Returns:
        StruggleDetectionResult.
    """
    detector = StruggleDetector()
    return detector.detect(text, context)


if __name__ == "__main__":
    # Test the detector
    test_cases = [
        "UGH this stupid API keeps timing out!!",
        "I've been thinking about maybe starting to exercise more",
        "Can't decide whether to use REST or GraphQL",
        "I'm so tired, been at this all day",
        "What does this error message mean?",
        "Waiting for the client to respond before I can proceed",
        "I have like 50 things to do and no idea where to start",
        "Just need to review the PR quickly",
    ]

    detector = StruggleDetector()

    for text in test_cases:
        result = detector.detect(text, use_ai=False)
        print(f"\n{'='*60}")
        print(f"Input: {text}")
        print(f"Detected: {result.struggle_detected}")
        if result.struggle_detected:
            print(f"Type: {result.struggle_type}")
            print(f"Confidence: {result.confidence:.2f}")
            print(f"Severity: {result.severity}")
            print(f"Reasoning: {result.reasoning}")
            print(f"Suggested: {result.suggested_response}")
