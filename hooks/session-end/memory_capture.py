#!/usr/bin/env python3
"""
Session-end hook: Unified memory capture for Claude Code sessions.

Routes learnings to:
- Memory V2 + Graphiti (via unified capture)
- ByteRover (technical knowledge)

Also integrates with checkpoint system for crash-resilient capture.
"""
import sys
import json
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
    """Store checkpoint extraction data via unified capture router."""
    try:
        from Tools.memory_capture_router import capture_checkpoint_extraction
        return capture_checkpoint_extraction(extraction, source="session_end_hook")
    except Exception as e:
        logger.error(f"Failed to store checkpoint to Memory V2: {e}")
        return False


def main():
    """Main entry point - process session and extract learnings."""
    logger.info("Memory capture hook started")
    try:
        # Import session discovery (workaround for passStdin issues)
        from Tools.session_discovery import discover_session_context

        # Use filesystem-based discovery (stdin is unreliable)
        context = discover_session_context(prefer_stdin=True, max_age_seconds=300)

        session_id = context.get('session_id', 'unknown')
        transcript_path = context.get('transcript_path')
        cwd = context.get('cwd', '')
        reason = 'session_end'

        logger.info(f"Discovered session: {session_id} (source: {context.get('_discovery_source')})")
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
        allow_llm = os.environ.get("MEMORY_CAPTURE_LLM", "1").lower() in ("1", "true", "yes")
        try:
            from Tools.memory_capture_router import capture_from_transcript
            results = capture_from_transcript(
                transcript_path=transcript_path,
                context=context,
                session_id=session_id,
                source="claude_code",
                allow_llm=allow_llm
            )
            logger.info(f"Captured learnings: {results}")
        except Exception as e:
            logger.error(f"Unified capture failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
