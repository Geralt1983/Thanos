#!/usr/bin/env python3
"""
Memory Checkpoint Hook - UserPromptSubmit

Records prompt interactions and writes periodic checkpoints
for crash-resilient memory capture.

Runs on every UserPromptSubmit event but only writes to disk
when thresholds are met (every 10 prompts or 30 minutes).
"""

import sys
import os
import json
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from Tools.memory_checkpoint import checkpoint_prompt

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PROJECT_ROOT / "logs" / "memory_checkpoint.log"),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)


def extract_context_from_event(event_data: dict) -> dict:
    """Extract relevant context from hook event data."""
    context = {
        "prompt_summary": "",
        "key_facts": [],
        "files_modified": [],
        "tools_used": []
    }

    # Extract from conversation if available
    conversation = event_data.get("conversation", [])
    if conversation:
        last_msg = conversation[-1] if conversation else {}
        content = last_msg.get("content", "")

        # Simple extraction - could be enhanced with LLM
        if isinstance(content, str):
            # Truncate for summary
            context["prompt_summary"] = content[:200] + "..." if len(content) > 200 else content

    # Extract tool usage from event
    tool_calls = event_data.get("tool_calls", [])
    if tool_calls:
        context["tools_used"] = [t.get("name", "unknown") for t in tool_calls]

    # Extract file modifications (if tracked)
    files = event_data.get("files_modified", [])
    if files:
        context["files_modified"] = files

    return context


def infer_project_from_cwd(cwd: str) -> tuple:
    """Infer project and client from working directory."""
    project = None
    client = None

    cwd_lower = cwd.lower()

    # Known project patterns
    if "thanos" in cwd_lower:
        project = "thanos"
    elif "versacare" in cwd_lower or "kentucky" in cwd_lower:
        project = "versacare"
        client = "kentucky"
    elif "orlando" in cwd_lower:
        client = "orlando"
    elif "memphis" in cwd_lower:
        client = "memphis"
    elif "raleigh" in cwd_lower:
        client = "raleigh"

    return project, client


def main():
    """Main hook entry point."""
    try:
        # Read event data from stdin
        if sys.stdin.isatty():
            logger.warning("No stdin data provided")
            return

        event_data = json.load(sys.stdin)

        # Extract session info
        session_id = event_data.get("session_id")
        if not session_id:
            logger.warning("No session_id in event data")
            return

        # Get process info
        claude_pid = event_data.get("claude_pid") or os.getppid()
        cwd = event_data.get("cwd") or os.getcwd()

        # Infer project/client
        project, client = infer_project_from_cwd(cwd)

        # Extract context
        context = extract_context_from_event(event_data)

        # Record checkpoint
        wrote_checkpoint = checkpoint_prompt(
            session_id=session_id,
            claude_pid=claude_pid,
            working_directory=cwd,
            prompt_summary=context["prompt_summary"],
            key_facts=context["key_facts"],
            files_modified=context["files_modified"],
            tools_used=context["tools_used"],
            project=project,
            client=client
        )

        if wrote_checkpoint:
            logger.info(f"Wrote checkpoint for session {session_id}")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse event data: {e}")
    except Exception as e:
        logger.error(f"Checkpoint hook error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
