#!/usr/bin/env python3
"""
Brain Dump Classifier for Thanos.

AI-powered classification of brain dumps to distinguish thinking/venting
from actual actionable items. Defaults to NOT creating tasks unless
there's clear actionable content.
"""

import os
import json
import uuid
import logging
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Any
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('brain_dump_classifier')


@dataclass
class ClassifiedBrainDump:
    """A classified brain dump with extracted structured data."""
    id: str
    raw_text: str
    source: str
    classification: str  # thinking, venting, observation, note, personal_task, work_task, idea, commitment, mixed
    confidence: float
    reasoning: str
    acknowledgment: Optional[str] = None
    task: Optional[Dict[str, Any]] = None
    commitment: Optional[Dict[str, Any]] = None
    idea: Optional[Dict[str, Any]] = None
    note: Optional[Dict[str, Any]] = None
    segments: Optional[List[Dict[str, Any]]] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def is_actionable(self) -> bool:
        """Check if this brain dump contains actionable content."""
        return self.classification in ('personal_task', 'work_task', 'commitment')

    def has_task(self) -> bool:
        """Check if a task was extracted."""
        return self.task is not None

    def has_commitment(self) -> bool:
        """Check if a commitment was extracted."""
        return self.commitment is not None


# The full classification prompt - embedded directly in the code
CLASSIFICATION_PROMPT = '''You are a brain dump classifier for a personal productivity system. Your job is to analyze incoming text and classify it appropriately.

CRITICAL PRINCIPLE: Default to NOT creating tasks. Most brain dumps are just thoughts, reflections, or venting - not actionable items. Only classify something as a task if there's a CLEAR, SPECIFIC action to take.

## Classifications

1. **thinking** - Internal reflection, musing, pondering
   - "I've been thinking about..."
   - "I wonder if..."
   - "What if we..."
   - "I should really..." (vague, no specific action)
   - "Maybe I need to..."

2. **venting** - Emotional release, frustration, stress
   - Contains frustration, anger, or stress
   - "I'm so tired of..."
   - "This is ridiculous..."
   - "I can't believe..."
   - Complaints without solutions

3. **observation** - Noting something without action needed
   - "I noticed that..."
   - "It seems like..."
   - Factual observations
   - Pattern recognition

4. **note** - Information to remember, not to act on
   - "Remember that the API is..."
   - "The meeting is at..."
   - "John's phone number is..."
   - Facts, references, information

5. **personal_task** - Clear, specific personal action
   - "Need to call the dentist"
   - "Pick up groceries"
   - "Pay the electric bill"
   - Must have SPECIFIC action + context

6. **work_task** - Clear, specific work action
   - "Review the PR"
   - "Send report to client"
   - "Fix the login bug"
   - Work-related with SPECIFIC action

7. **idea** - Creative thought worth capturing
   - "What if we built..."
   - "A cool feature would be..."
   - Innovation, invention, improvement ideas

8. **commitment** - Promise made to someone
   - "I told Sarah I would..."
   - "I promised to..."
   - "I committed to..."
   - Must involve another person + promise

9. **mixed** - Contains multiple distinct items
   - When text contains 2+ clearly separate items
   - Return segments array with each classified separately

## Classification Rules

1. **When in doubt, classify as thinking** - It's better to not create a task than to create unnecessary ones

2. **"Should" and "need to" are usually thinking** unless:
   - There's a specific action (verb + object)
   - There's urgency or deadline
   - There's a clear context (who, what, when)

3. **Work vs Personal detection**:
   - Work: mentions clients, projects, PRs, code, meetings, team members, reports
   - Personal: mentions family, home, health, errands, personal appointments

4. **Venting detection**:
   - Emotional language (frustrated, angry, tired, annoyed)
   - Complaints without proposed solutions
   - Rhetorical questions expressing frustration
   - Multiple exclamation points or strong language

5. **Task requirements** (ALL must be present):
   - Specific verb (call, buy, fix, send, review, etc.)
   - Clear object/target (the dentist, groceries, the bug, etc.)
   - Implicit or explicit timeline feasibility

## Response Format

Return a JSON object with:
```json
{
  "classification": "one of the 9 types",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of classification choice",
  "acknowledgment": "A brief, empathetic response to show the input was heard (for thinking/venting)",
  "task": {
    "title": "Short task title",
    "description": "Full description",
    "context": "work|personal",
    "priority": "low|medium|high",
    "estimated_effort": "quick|medium|long"
  },
  "commitment": {
    "description": "What was committed",
    "to_whom": "Person name",
    "deadline": "If mentioned, otherwise null"
  },
  "idea": {
    "title": "Idea title",
    "description": "Full idea description",
    "category": "feature|improvement|creative|other"
  },
  "note": {
    "content": "The information to remember",
    "category": "reference|fact|contact|other"
  },
  "segments": [
    {
      "text": "Original text portion",
      "classification": "type",
      "extracted": { ... }
    }
  ]
}
```

Only include the relevant fields. For thinking/venting/observation, only return classification, confidence, reasoning, and acknowledgment.

## Examples

Input: "I've been thinking about maybe starting to exercise more"
Output: {"classification": "thinking", "confidence": 0.95, "reasoning": "Vague reflection about a potential future action, no specific commitment or plan", "acknowledgment": "That's a good thing to consider. When you're ready to make it concrete, let me know."}

Input: "UGH this stupid API keeps timing out and nobody seems to care about fixing it!!"
Output: {"classification": "venting", "confidence": 0.98, "reasoning": "Frustration expressed with emotional language, exclamation points, no specific action requested", "acknowledgment": "That sounds really frustrating. Unreliable APIs are the worst."}

Input: "Need to call Dr. Smith about my appointment"
Output: {"classification": "personal_task", "confidence": 0.92, "reasoning": "Clear action (call) + specific target (Dr. Smith) + context (appointment)", "task": {"title": "Call Dr. Smith about appointment", "description": "Need to call Dr. Smith about my appointment", "context": "personal", "priority": "medium", "estimated_effort": "quick"}}

Input: "Review Sarah's PR for the auth changes"
Output: {"classification": "work_task", "confidence": 0.95, "reasoning": "Clear work action (review PR) + specific target (Sarah's auth changes)", "task": {"title": "Review Sarah's auth PR", "description": "Review Sarah's PR for the auth changes", "context": "work", "priority": "medium", "estimated_effort": "medium"}}

Input: "Remember that the staging API key expires on Jan 31"
Output: {"classification": "note", "confidence": 0.93, "reasoning": "Information to remember, not an immediate action", "note": {"content": "Staging API key expires on Jan 31", "category": "reference"}}

Input: "I told Mike I'd have the design ready by Friday"
Output: {"classification": "commitment", "confidence": 0.96, "reasoning": "Promise made to specific person with deadline", "commitment": {"description": "Have the design ready", "to_whom": "Mike", "deadline": "Friday"}}

Input: "I should probably clean my desk at some point. Also need to buy milk."
Output: {"classification": "mixed", "confidence": 0.88, "reasoning": "Contains two separate items: vague thought about desk + specific task about milk", "segments": [{"text": "I should probably clean my desk at some point", "classification": "thinking", "extracted": null}, {"text": "need to buy milk", "classification": "personal_task", "extracted": {"task": {"title": "Buy milk", "context": "personal", "priority": "low", "estimated_effort": "quick"}}}]}

Now classify the following brain dump:
'''


class BrainDumpClassifier:
    """
    AI-powered brain dump classifier.

    Uses Claude to intelligently classify brain dumps and extract
    structured data when appropriate. Defaults to NOT creating tasks.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize the classifier.

        Args:
            api_key: Anthropic API key. Defaults to ANTHROPIC_API_KEY env var.
            model: Claude model to use for classification.
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.model = model
        self._client = None

        if not self.api_key:
            logger.warning("No ANTHROPIC_API_KEY found - classification will fail")

    @property
    def client(self):
        """Lazy-load the Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package not installed. Install with: pip install anthropic")
        return self._client

    async def classify(self, text: str, source: str = "manual") -> ClassifiedBrainDump:
        """
        Classify a brain dump using Claude.

        Args:
            text: The raw brain dump text to classify.
            source: Source of the brain dump (telegram, manual, voice, etc.)

        Returns:
            ClassifiedBrainDump with classification and extracted data.
        """
        entry_id = str(uuid.uuid4())[:8]

        # Handle empty or whitespace-only input
        if not text or not text.strip():
            return ClassifiedBrainDump(
                id=entry_id,
                raw_text=text or "",
                source=source,
                classification="thinking",
                confidence=1.0,
                reasoning="Empty input",
                acknowledgment="I didn't catch anything there. What's on your mind?"
            )

        try:
            # Call Claude for classification
            response = await self._call_claude(text)

            # Parse the response
            result = self._parse_response(response)

            return ClassifiedBrainDump(
                id=entry_id,
                raw_text=text,
                source=source,
                classification=result.get('classification', 'thinking'),
                confidence=result.get('confidence', 0.5),
                reasoning=result.get('reasoning', 'Unable to determine reasoning'),
                acknowledgment=result.get('acknowledgment'),
                task=result.get('task'),
                commitment=result.get('commitment'),
                idea=result.get('idea'),
                note=result.get('note'),
                segments=result.get('segments')
            )

        except Exception as e:
            logger.error(f"Classification failed: {e}")
            # Return a safe fallback - default to thinking
            return ClassifiedBrainDump(
                id=entry_id,
                raw_text=text,
                source=source,
                classification="thinking",
                confidence=0.3,
                reasoning=f"Classification failed: {str(e)}",
                acknowledgment="I've noted that down. Let me know if there's anything specific you need help with."
            )

    async def _call_claude(self, text: str) -> str:
        """
        Call Claude API for classification.

        Args:
            text: The brain dump text to classify.

        Returns:
            Raw response text from Claude.
        """
        import asyncio

        # Use sync client in async context via executor
        def sync_call():
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": f"{CLASSIFICATION_PROMPT}\n\n{text}"
                    }
                ]
            )
            return response.content[0].text

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_call)

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse Claude's response into structured data.

        Args:
            response: Raw response text from Claude.

        Returns:
            Parsed dictionary with classification data.
        """
        # Try to extract JSON from the response
        response = response.strip()

        # Handle responses wrapped in markdown code blocks
        if response.startswith('```'):
            # Remove markdown code block
            lines = response.split('\n')
            json_lines = []
            in_block = False
            for line in lines:
                if line.startswith('```') and not in_block:
                    in_block = True
                    continue
                elif line.startswith('```') and in_block:
                    break
                elif in_block:
                    json_lines.append(line)
            response = '\n'.join(json_lines)

        # Try to find JSON object in response
        try:
            # First, try direct parse
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try to find JSON object with { ... }
        start = response.find('{')
        end = response.rfind('}')

        if start != -1 and end != -1 and end > start:
            try:
                json_str = response[start:end + 1]
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # If all parsing fails, return default
        logger.warning(f"Could not parse JSON from response: {response[:200]}")
        return {
            'classification': 'thinking',
            'confidence': 0.4,
            'reasoning': 'Could not parse classifier response',
            'acknowledgment': "I've noted that. Let me know if you need anything specific."
        }

    def classify_sync(self, text: str, source: str = "manual") -> ClassifiedBrainDump:
        """
        Synchronous wrapper for classify().

        Args:
            text: The raw brain dump text to classify.
            source: Source of the brain dump.

        Returns:
            ClassifiedBrainDump with classification and extracted data.
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, create a new task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.classify(text, source)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(self.classify(text, source))
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self.classify(text, source))


# Convenience functions for quick classification
async def classify_brain_dump(text: str, source: str = "manual") -> ClassifiedBrainDump:
    """
    Convenience function to classify a brain dump.

    Args:
        text: The brain dump text.
        source: Source of the brain dump.

    Returns:
        ClassifiedBrainDump instance.
    """
    classifier = BrainDumpClassifier()
    return await classifier.classify(text, source)


def classify_brain_dump_sync(text: str, source: str = "manual") -> ClassifiedBrainDump:
    """
    Synchronous convenience function to classify a brain dump.

    Args:
        text: The brain dump text.
        source: Source of the brain dump.

    Returns:
        ClassifiedBrainDump instance.
    """
    classifier = BrainDumpClassifier()
    return classifier.classify_sync(text, source)


# CLI for testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python classifier.py 'your brain dump text'")
        print("\nExamples:")
        print("  python classifier.py 'I should really start exercising'")
        print("  python classifier.py 'Need to call the dentist tomorrow'")
        print("  python classifier.py 'Review the PR for the auth changes'")
        sys.exit(1)

    text = ' '.join(sys.argv[1:])
    print(f"\nClassifying: {text}\n")

    result = classify_brain_dump_sync(text)

    print(f"Classification: {result.classification}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Reasoning: {result.reasoning}")

    if result.acknowledgment:
        print(f"\nAcknowledgment: {result.acknowledgment}")

    if result.task:
        print(f"\nExtracted Task:")
        print(f"  Title: {result.task.get('title')}")
        print(f"  Context: {result.task.get('context')}")
        print(f"  Priority: {result.task.get('priority')}")

    if result.commitment:
        print(f"\nExtracted Commitment:")
        print(f"  Description: {result.commitment.get('description')}")
        print(f"  To: {result.commitment.get('to_whom')}")
        print(f"  Deadline: {result.commitment.get('deadline')}")

    if result.idea:
        print(f"\nExtracted Idea:")
        print(f"  Title: {result.idea.get('title')}")
        print(f"  Category: {result.idea.get('category')}")

    if result.note:
        print(f"\nExtracted Note:")
        print(f"  Content: {result.note.get('content')}")
        print(f"  Category: {result.note.get('category')}")

    if result.segments:
        print(f"\nSegments ({len(result.segments)}):")
        for i, seg in enumerate(result.segments, 1):
            print(f"  {i}. [{seg.get('classification')}] {seg.get('text')}")

    print("\n" + "="*50)
    print("Full JSON:")
    print(json.dumps(result.to_dict(), indent=2))
