#!/usr/bin/env python3
"""
Session-end hook: Capture learnings from Claude Code sessions.
Extracts decisions, patterns, and learnings from session transcript.

Also integrates with the checkpoint system for crash-resilient memory capture.

Receives hook event data via stdin:
{
  "session_id": "abc123",
  "transcript_path": "~/.claude/projects/.../session.jsonl",
  "cwd": "/path/to/project",
  "reason": "exit"
}

Extracts and stores:
- Checkpoint data (accumulated during session)
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
    context = {"project": None, "client": None}
    if not cwd:
        return context
    path = Path(cwd)
    parts = path.parts
    for i, part in enumerate(parts):
        if part.lower() in ('projects', 'clients', 'work'):
            if i + 1 < len(parts):
                context["client"] = parts[i + 1]
            if i + 2 < len(parts):
                context["project"] = parts[i + 2]
            break
    if not context["project"] and len(parts) > 1:
        context["project"] = parts[-1]
    return context


def read_transcript(transcript_path: str) -> list:
    messages = []
    try:
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
    text_parts = []
    for msg in messages:
        if isinstance(msg, dict):
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
            if 'message' in msg:
                inner = msg['message']
                if isinstance(inner, dict) and 'content' in inner:
                    if isinstance(inner['content'], str):
                        text_parts.append(inner['content'])
    return '\n\n'.join(text_parts)


def extract_learnings(content: str) -> list:
    learnings = []
    seen = set()
    for pattern in DECISION_PATTERNS:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            text = match.group(1).strip()
            if text and text not in seen and len(text) > 30:
                learnings.append({"type": "decision", "content": _clean_learning(text), "confidence": 0.7})
                seen.add(text)
    for pattern in BUG_FIX_PATTERNS:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            text = match.group(1).strip()
            if text and text not in seen and len(text) > 30:
                learnings.append({"type": "bug_fix", "content": _clean_learning(text), "confidence": 0.8})
                seen.add(text)
    for pattern in PATTERN_PATTERNS:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            text = match.group(1).strip()
            if text and text not in seen and len(text) > 30:
                learnings.append({"type": "pattern", "content": _clean_learning(text), "confidence": 0.6})
                seen.add(text)
    learnings.sort(key=lambda x: x['confidence'], reverse=True)
    return learnings[:10]


def _clean_learning(text: str) -> str:
    text = re.sub(r'[.,:;]+$', '', text)
    text = ' '.join(text.split())
    if text:
        text = text[0].upper() + text[1:]
    return text


def store_learnings(learnings: list, context: dict, session_id: str) -> int:
    stored = 0
    try:
        from Tools.memory_v2.service import MemoryService
        service = MemoryService()
        for learning in learnings:
            if learning['confidence'] < 0.5:
                continue
            memory_type = {'decision': 'decision', 'bug_fix': 'learning', 'pattern': 'pattern'}.get(learning['type'], 'learning')
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


def finalize_checkpoint(session_id: str) -> Optional[dict]:
    """Finalize session checkpoint if it exists."""
    try:
        from Tools.memory_checkpoint import finalize_session_checkpoint
        extraction = finalize_session_checkpoint(session_id)
        if extraction:
            logger.info(f"Finalized checkpoint: {extraction.get('prompt_count', 0)} prompts, "
                       f"{extraction.get('duration_minutes', 0)}min")
        return extraction
    except ImportError:
        logger.warning("Checkpoint system not available")
        return None
    except Exception as e:
        logger.error(f"Failed to finalize checkpoint: {e}")
        return None


def store_checkpoint_to_memory(extraction: dict) -> bool:
    """Store checkpoint extraction data to Memory V2."""
    try:
        from Tools.memory_v2.service import MemoryService
        service = MemoryService()
        session_id = extraction["session_id"]
        duration = extraction.get("duration_minutes", 0)
        prompt_count = extraction.get("prompt_count", 0)
        project = extraction.get("project", "unknown")
        client = extraction.get("client")
        summary = extraction.get("cumulative_summary", "")
        facts = extraction.get("all_facts", [])
        files = extraction.get("all_files_modified", [])
        content_parts = [
            f"Session {session_id}: {duration}min, {prompt_count} prompts",
            f"Project: {project}" + (f" (Client: {client})" if client else ""),
        ]
        if summary:
            content_parts.append(f"\nSummary:\n{summary}")
        if facts:
            content_parts.append(f"\nKey facts:\n- " + "\n- ".join(facts[:10]))
        if files:
            content_parts.append(f"\nFiles:\n- " + "\n- ".join(files[:10]))
        content = "\n".join(content_parts)
        result = service.add(
            content=content,
            metadata={
                "type": "session_summary",
                "session_id": session_id,
                "project": project,
                "client": client,
                "duration_minutes": duration,
                "prompt_count": prompt_count,
                "source": "session_end_hook",
                "extracted_at": datetime.now().isoformat()
            }
        )
        logger.info(f"Stored checkpoint to Memory V2: {result}")
        return True
    except Exception as e:
        logger.error(f"Failed to store checkpoint to Memory V2: {e}")
        return False


def main():
    """Main entry point - process session and extract learnings."""
    logger.info("Memory capture hook started")
    try:
        if sys.stdin.isatty():
            logger.warning("No stdin data - running in test mode")
            return
        stdin_data = ""
        try:
            import select
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

        # FIRST: Try checkpoint-based capture (crash-resilient path)
        checkpoint_extraction = finalize_checkpoint(session_id)
        if checkpoint_extraction:
            if store_checkpoint_to_memory(checkpoint_extraction):
                logger.info("Successfully stored checkpoint-based memory")

        # THEN: Continue with transcript extraction for additional learnings
        if not transcript_path:
            logger.warning("No transcript_path in event data")
            return
        context = extract_project_context(cwd)
        logger.info(f"Project context: {context}")
        messages = read_transcript(transcript_path)
        if not messages:
            logger.warning("No messages in transcript")
            return
        logger.info(f"Read {len(messages)} messages from transcript")
        content = extract_text_content(messages)
        if not content:
            logger.warning("No text content extracted")
            return
        learnings = extract_learnings(content)
        logger.info(f"Extracted {len(learnings)} learnings")
        if not learnings:
            logger.info("No learnings to store")
            return
        stored = store_learnings(learnings, context, session_id)
        logger.info(f"Stored {stored} learnings in Memory V2")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
