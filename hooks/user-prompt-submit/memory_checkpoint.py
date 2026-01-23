#!/usr/bin/env python3
"""
Memory Checkpoint Hook - UserPromptSubmit

Records prompt interactions and writes periodic checkpoints
for crash-resilient memory capture.

Uses filesystem-based session discovery (workaround for passStdin issues).
"""

import sys
import os
import logging
from pathlib import Path

# Suppress stdout to avoid hook framework issues
_original_stdout = sys.stdout
sys.stdout = open(os.devnull, 'w')

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set up logging ONLY to file (not stderr - causes hook issues)
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "memory_checkpoint.log")
    ]
)
logger = logging.getLogger(__name__)

# Import after path setup
from Tools.session_discovery import discover_session_context, infer_project_client
from Tools.memory_checkpoint import checkpoint_prompt


def main():
    """Main hook entry point."""
    try:
        logger.info("Memory checkpoint hook invoked")

        # Use filesystem-based discovery (stdin is unreliable)
        context = discover_session_context(prefer_stdin=True, max_age_seconds=120)

        session_id = context.get('session_id')
        if not session_id:
            logger.warning("Could not discover session_id")
            return

        logger.info(f"Discovered session: {session_id} (source: {context.get('_discovery_source')})")

        # Get process info
        claude_pid = os.getppid()
        cwd = context.get('cwd') or os.getcwd()

        # Infer project/client
        project, client = infer_project_client(cwd)

        # Record checkpoint (prompt_summary will be empty but that's ok -
        # the checkpoint tracks session activity, not individual prompt content)
        wrote_checkpoint = checkpoint_prompt(
            session_id=session_id,
            claude_pid=claude_pid,
            working_directory=cwd,
            prompt_summary="",  # Not available without stdin
            key_facts=[],
            files_modified=[],
            tools_used=[],
            project=project,
            client=client
        )

        if wrote_checkpoint:
            logger.info(f"Wrote checkpoint for session {session_id}")
        else:
            logger.debug(f"Checkpoint recorded (no write yet) for session {session_id}")

    except Exception as e:
        logger.error(f"Checkpoint hook error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
