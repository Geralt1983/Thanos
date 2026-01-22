#!/usr/bin/env python3
"""
Orphan Checkpoint Processor

Cron script to process orphaned session checkpoints and
extract memories to Memory V2.

Run via cron every 30 minutes:
*/30 * * * * /Users/jeremy/Projects/Thanos/.venv/bin/python3 /Users/jeremy/Projects/Thanos/scripts/process_orphan_checkpoints.py

Or called by the Operator daemon watchdog.
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from Tools.memory_checkpoint import process_orphans, get_checkpoint_manager

# Try to import Memory V2
try:
    from Tools.memory_v2.service import MemoryService
    MEMORY_V2_AVAILABLE = True
except ImportError:
    MEMORY_V2_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PROJECT_ROOT / "logs" / "orphan_processor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def extract_to_memory_v2(extraction_data: dict) -> bool:
    """
    Extract session data to Memory V2.

    Creates a comprehensive memory entry from the session checkpoint.
    """
    if not MEMORY_V2_AVAILABLE:
        logger.warning("Memory V2 not available, skipping extraction")
        return False

    try:
        service = MemoryService()

        # Build memory content
        session_id = extraction_data["session_id"]
        duration = extraction_data.get("duration_minutes", 0)
        prompt_count = extraction_data.get("prompt_count", 0)
        project = extraction_data.get("project", "unknown")
        client = extraction_data.get("client")
        summary = extraction_data.get("cumulative_summary", "")
        facts = extraction_data.get("all_facts", [])
        files = extraction_data.get("all_files_modified", [])
        orphaned = extraction_data.get("orphaned", False)

        # Format content
        content_parts = [
            f"Session: {session_id}",
            f"Duration: {duration} minutes, {prompt_count} prompts",
            f"Project: {project}" + (f" (Client: {client})" if client else ""),
        ]

        if summary:
            content_parts.append(f"\nActivity:\n{summary}")

        if facts:
            content_parts.append(f"\nKey Facts:\n- " + "\n- ".join(facts[:10]))

        if files:
            content_parts.append(f"\nFiles Modified:\n- " + "\n- ".join(files[:15]))

        if orphaned:
            content_parts.append("\n[Session was orphaned/crashed - extracted from checkpoint]")

        content = "\n".join(content_parts)

        # Store in Memory V2
        result = service.add(
            content=content,
            metadata={
                "type": "session_summary",
                "session_id": session_id,
                "project": project,
                "client": client,
                "duration_minutes": duration,
                "prompt_count": prompt_count,
                "orphaned": orphaned,
                "extracted_at": datetime.now().isoformat(),
                "source": "checkpoint_processor"
            }
        )

        logger.info(f"Stored session {session_id} in Memory V2: {result}")
        return True

    except Exception as e:
        logger.error(f"Failed to extract to Memory V2: {e}", exc_info=True)
        return False


def fallback_storage(extraction_data: dict) -> bool:
    """
    Fallback: store extraction data to JSON file if Memory V2 unavailable.
    """
    try:
        fallback_dir = PROJECT_ROOT / "State" / "session_checkpoints" / "extracted"
        fallback_dir.mkdir(parents=True, exist_ok=True)

        session_id = extraction_data["session_id"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fallback_path = fallback_dir / f"{session_id}_{timestamp}.json"

        fallback_path.write_text(json.dumps(extraction_data, indent=2))
        logger.info(f"Stored extraction to fallback: {fallback_path}")
        return True

    except Exception as e:
        logger.error(f"Fallback storage failed: {e}")
        return False


def main():
    """Process all orphaned checkpoints."""
    logger.info("Starting orphan checkpoint processing...")

    # Get orphaned sessions
    extractions = process_orphans()

    if not extractions:
        logger.info("No orphaned sessions found")
        return

    logger.info(f"Found {len(extractions)} orphaned sessions")

    # Process each extraction
    success_count = 0
    for extraction in extractions:
        session_id = extraction["session_id"]
        logger.info(f"Processing session {session_id}...")

        # Try Memory V2 first
        if extract_to_memory_v2(extraction):
            success_count += 1
        else:
            # Fallback to JSON storage
            if fallback_storage(extraction):
                success_count += 1

    logger.info(f"Processed {success_count}/{len(extractions)} sessions successfully")

    # Report results
    print(json.dumps({
        "processed": len(extractions),
        "successful": success_count,
        "timestamp": datetime.now().isoformat()
    }))


if __name__ == "__main__":
    main()
