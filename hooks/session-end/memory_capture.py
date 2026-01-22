#!/usr/bin/env python3
"""
Session-end hook: Capture learnings from Claude Code sessions.
Extracts decisions, patterns, and learnings from session transcript.

Receives hook event data via stdin:
{
  "session_id": "abc123",
  "transcript_path": "~/.claude/projects/.../session.jsonl",
  "cwd": "/path/to/project",
  "reason": "exit"
}

Extracts and stores:
- Decisions made (architecture, design choices)
- Bugs fixed (what went wrong, how it was solved)
- Patterns discovered (reusable approaches)
"""
import sys
import json
import re
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

# Suppress output to avoid hook framework errors
# Save original stderr for logging
_original_stderr = sys.stderr
sys.stdout = open(os.devnull, 'w')
sys.stderr = open(os.devnull, 'w')

# Add Thanos to path
THANOS_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(THANOS_ROOT))

# Set up logging to file instead of stderr
import logging
LOG_DIR = THANOS_ROOT / 'logs'
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    filename=str(LOG_DIR / 'memory_capture.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Learning extraction patterns
DECISION_PATTERNS = [
    r"(?:decided to|chose to|going with|will use|opted for|selected)\s+(.{20,200})",
    r"(?:the approach is|solution is|best option is|implemented)\s+(.{20,200})",
    r"(?:architecture|design):?\s*(.{20,200})",
]

BUG_FIX_PATTERNS = [
    r"(?:fixed|resolved|solved|patched)\s+(?:the\s+)?(?:bug|issue|problem|error)\s*(?:by|with|:)?\s*(.{20,200})",
    r"(?:the issue was|problem was|root cause was|caused by)\s+(.{20,200})",
    r"(?:bug|error|issue):\s*(.{20,200})",
]

PATTERN_PATTERNS = [
    r"(?:pattern|approach|technique|method):\s*(.{20,200})",
    r"(?:always|never|should)\s+(.{20,200})",
    r"(?:lesson learned|takeaway|insight):\s*(.{20,200})",
    r"(?:this works because|key insight is|remember that)\s+(.{20,200})",
]


def extract_project_context(cwd: str) -> dict:
    """
    Extract client/project info from working directory.

    Patterns:
    - /Projects/ClientName/project-name
    - /clients/ClientName/project
    - /work/client-project
    """
    context = {
        "project": None,
        "client": None,
    }

    if not cwd:
        return context

    path = Path(cwd)
    parts = path.parts

    # Look for known directory patterns
    for i, part in enumerate(parts):
        if part.lower() in ('projects', 'clients', 'work'):
            if i + 1 < len(parts):
                context["client"] = parts[i + 1]
            if i + 2 < len(parts):
                context["project"] = parts[i + 2]
            break

    # Fallback: use last directory component as project
    if not context["project"] and len(parts) > 1:
        context["project"] = parts[-1]

    return context


def read_transcript(transcript_path: str) -> list:
    """
    Read JSONL transcript file and return messages.

    Each line is a JSON object representing a conversation turn.
    """
    messages = []

    try:
        # Expand ~ in path
        path = Path(transcript_path).expanduser()

        if not path.exists():
            logger.warning(f"Transcript not found: {path}")
            return messages

        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        msg = json.loads(line)
                        messages.append(msg)
                    except json.JSONDecodeError:
                        continue

    except Exception as e:
        logger.error(f"Error reading transcript: {e}")

    return messages


def extract_text_content(messages: list) -> str:
    """
    Extract text content from transcript messages.

    Handles various message formats from Claude Code.
    """
    text_parts = []

    for msg in messages:
        # Handle different message structures
        if isinstance(msg, dict):
            # Direct content field
            if 'content' in msg:
                content = msg['content']
                if isinstance(content, str):
                    text_parts.append(content)
                elif isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and 'text' in item:
                            text_parts.append(item['text'])
                        elif isinstance(item, str):
                            text_parts.append(item)

            # Message with message field (nested)
            if 'message' in msg:
                inner = msg['message']
                if isinstance(inner, dict) and 'content' in inner:
                    if isinstance(inner['content'], str):
                        text_parts.append(inner['content'])

    return '\n\n'.join(text_parts)


def extract_learnings(content: str) -> list:
    """
    Extract key learnings from session content.

    Returns list of dicts with:
    - type: "decision" | "bug_fix" | "pattern"
    - content: The extracted learning
    - confidence: How confident we are this is a real learning
    """
    learnings = []
    seen = set()  # Dedupe

    # Extract decisions
    for pattern in DECISION_PATTERNS:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            text = match.group(1).strip()
            if text and text not in seen and len(text) > 30:
                learnings.append({
                    "type": "decision",
                    "content": _clean_learning(text),
                    "confidence": 0.7
                })
                seen.add(text)

    # Extract bug fixes
    for pattern in BUG_FIX_PATTERNS:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            text = match.group(1).strip()
            if text and text not in seen and len(text) > 30:
                learnings.append({
                    "type": "bug_fix",
                    "content": _clean_learning(text),
                    "confidence": 0.8
                })
                seen.add(text)

    # Extract patterns
    for pattern in PATTERN_PATTERNS:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            text = match.group(1).strip()
            if text and text not in seen and len(text) > 30:
                learnings.append({
                    "type": "pattern",
                    "content": _clean_learning(text),
                    "confidence": 0.6
                })
                seen.add(text)

    # Limit to top learnings by confidence
    learnings.sort(key=lambda x: x['confidence'], reverse=True)
    return learnings[:10]


def _clean_learning(text: str) -> str:
    """Clean up extracted learning text."""
    # Remove trailing punctuation artifacts
    text = re.sub(r'[.,:;]+$', '', text)
    # Collapse whitespace
    text = ' '.join(text.split())
    # Capitalize first letter
    if text:
        text = text[0].upper() + text[1:]
    return text


def store_learnings(learnings: list, context: dict, session_id: str) -> int:
    """
    Store extracted learnings in Memory V2.

    Returns number of learnings stored.
    """
    stored = 0

    try:
        from Tools.memory_v2.service import get_memory_service
        service = get_memory_service()

        for learning in learnings:
            # Skip low confidence learnings
            if learning['confidence'] < 0.5:
                continue

            # Map type to memory_type
            memory_type = {
                'decision': 'decision',
                'bug_fix': 'learning',
                'pattern': 'pattern',
            }.get(learning['type'], 'learning')

            # Build metadata
            metadata = {
                "source": "claude_code",
                "memory_type": memory_type,
                "session_id": session_id,
                "extracted_at": datetime.now().isoformat(),
                "confidence": learning['confidence'],
            }

            if context.get('client'):
                metadata['client'] = context['client']
            if context.get('project'):
                metadata['project'] = context['project']

            # Format content
            content = f"[{memory_type.upper()}] {learning['content']}"

            try:
                service.add(content, metadata)
                stored += 1
                logger.info(f"Stored learning: {content[:100]}...")
            except Exception as e:
                logger.error(f"Failed to store learning: {e}")

    except ImportError as e:
        logger.error(f"Memory V2 not available: {e}")
    except Exception as e:
        logger.error(f"Error storing learnings: {e}")

    return stored


def main():
    """Main entry point - process session transcript and extract learnings."""
    logger.info("Memory capture hook started")

    try:
        # Read hook event data from stdin
        if sys.stdin.isatty():
            logger.warning("No stdin data - running in test mode")
            return

        # Restore stdin temporarily
        stdin_data = ""
        try:
            import select
            # Check if there's data on stdin
            if select.select([sys.__stdin__], [], [], 0.1)[0]:
                stdin_data = sys.__stdin__.read()
        except:
            pass

        if not stdin_data:
            logger.warning("No hook event data received")
            return

        try:
            event_data = json.loads(stdin_data)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid hook event JSON: {e}")
            return

        session_id = event_data.get('session_id', 'unknown')
        transcript_path = event_data.get('transcript_path')
        cwd = event_data.get('cwd', '')
        reason = event_data.get('reason', 'unknown')

        logger.info(f"Processing session {session_id}, reason: {reason}")

        if not transcript_path:
            logger.warning("No transcript_path in event data")
            return

        # Extract project context
        context = extract_project_context(cwd)
        logger.info(f"Project context: {context}")

        # Read transcript
        messages = read_transcript(transcript_path)
        if not messages:
            logger.warning("No messages in transcript")
            return

        logger.info(f"Read {len(messages)} messages from transcript")

        # Extract text content
        content = extract_text_content(messages)
        if not content:
            logger.warning("No text content extracted")
            return

        # Extract learnings
        learnings = extract_learnings(content)
        logger.info(f"Extracted {len(learnings)} learnings")

        if not learnings:
            logger.info("No learnings to store")
            return

        # Store learnings
        stored = store_learnings(learnings, context, session_id)
        logger.info(f"Stored {stored} learnings in Memory V2")

    except Exception as e:
        logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
