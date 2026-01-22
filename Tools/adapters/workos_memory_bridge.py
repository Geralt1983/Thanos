"""
WorkOS Memory Bridge - Task Completion to Memory V2 Integration.

Automatically captures task completion context and stores it in Memory V2
for semantic search and ADHD-friendly memory surfacing.

This bridge:
1. Reads task completion events from a queue file (written by WorkOS MCP)
2. Extracts context: task title, client, project, decisions made
3. Stores in Memory V2 with proper metadata and heat boosting

Usage:
    # As a daemon:
    python -m Tools.adapters.workos_memory_bridge --daemon

    # One-time processing:
    python -m Tools.adapters.workos_memory_bridge --process

    # Direct call from Python:
    from Tools.adapters.workos_memory_bridge import store_task_completion
    store_task_completion(task_data)
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Queue file location (shared with WorkOS MCP TypeScript code)
QUEUE_DIR = Path(os.getenv("THANOS_STATE_DIR", "/Users/jeremy/Projects/Thanos/State"))
QUEUE_FILE = QUEUE_DIR / "workos_memory_queue.jsonl"
PROCESSED_DIR = QUEUE_DIR / "processed"

# Memory V2 import with graceful fallback
try:
    from Tools.memory_v2 import get_memory_service, get_heat_service
    MEMORY_V2_AVAILABLE = True
except ImportError:
    MEMORY_V2_AVAILABLE = False
    logger.warning("Memory V2 not available. Task completions will not be stored.")


def store_task_completion(
    task_data: Dict[str, Any],
    context: Optional[str] = None,
    decisions: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Store task completion context in Memory V2.

    This is the main entry point for capturing task completion context.
    Can be called directly or via the queue processor.

    Args:
        task_data: Task object from WorkOS with:
            - id: Task ID
            - title: Task title
            - description: Task description (optional)
            - clientId: Client ID (optional)
            - clientName: Client name (optional, resolved)
            - valueTier: checkbox/progress/deliverable/milestone
            - drainType: deep/shallow/admin
            - pointsFinal: Points earned
            - completedAt: Completion timestamp
        context: Additional context about what was done (optional)
        decisions: List of decisions made during the task (optional)

    Returns:
        Result of memory storage operation
    """
    if not MEMORY_V2_AVAILABLE:
        return {
            "success": False,
            "error": "Memory V2 not available",
            "task_id": task_data.get("id")
        }

    try:
        memory_service = get_memory_service()
        heat_service = get_heat_service()

        # Build content for the memory
        task_title = task_data.get("title", "Unknown task")
        task_description = task_data.get("description", "")
        client_name = task_data.get("clientName")
        value_tier = task_data.get("valueTier", "progress")
        points = task_data.get("pointsFinal", 0)

        # Construct a rich memory content
        content_parts = [
            f"Completed task: {task_title}",
        ]

        if task_description:
            content_parts.append(f"Description: {task_description}")

        if client_name:
            content_parts.append(f"Client: {client_name}")

        if context:
            content_parts.append(f"Context: {context}")

        if decisions:
            content_parts.append(f"Decisions made: {', '.join(decisions)}")

        content_parts.append(f"Value: {value_tier} ({points} points)")

        content = ". ".join(content_parts)

        # Build metadata
        metadata = {
            "source": "workos",
            "type": "task_completion",
            "task_id": str(task_data.get("id")),
            "value_tier": value_tier,
            "points": points,
            "original_timestamp": task_data.get("completedAt", datetime.now().isoformat()),
        }

        if client_name:
            metadata["client"] = client_name

        # Extract project from task if available
        project = task_data.get("project") or _extract_project_from_title(task_title)
        if project:
            metadata["project"] = project

        # Calculate importance based on value tier
        importance_map = {
            "checkbox": 0.5,
            "progress": 1.0,
            "deliverable": 1.5,
            "milestone": 2.0,
        }
        metadata["importance"] = importance_map.get(value_tier, 1.0)

        # Store in Memory V2
        result = memory_service.add(content, metadata=metadata)

        # Boost heat for related client/project
        if client_name:
            heat_service.boost_related(client_name, "completion")
            logger.info(f"Boosted heat for client: {client_name}")

        if project:
            heat_service.boost_related(project, "completion")
            logger.info(f"Boosted heat for project: {project}")

        logger.info(f"Stored task completion in memory: {task_title}")

        return {
            "success": True,
            "memory_id": result.get("id"),
            "task_id": task_data.get("id"),
            "content_preview": content[:100] + "..." if len(content) > 100 else content
        }

    except Exception as e:
        logger.error(f"Failed to store task completion: {e}")
        return {
            "success": False,
            "error": str(e),
            "task_id": task_data.get("id")
        }


def store_decision(
    decision: str,
    task_id: Optional[int] = None,
    client_name: Optional[str] = None,
    alternatives_considered: Optional[List[str]] = None,
    rationale: Optional[str] = None
) -> Dict[str, Any]:
    """
    Store a decision made during task execution.

    Decisions are stored with higher importance and special memory type
    for later retrieval when similar situations arise.

    Args:
        decision: The decision that was made
        task_id: Related task ID (optional)
        client_name: Related client (optional)
        alternatives_considered: Other options that were considered (optional)
        rationale: Why this decision was made (optional)

    Returns:
        Result of memory storage operation
    """
    if not MEMORY_V2_AVAILABLE:
        return {
            "success": False,
            "error": "Memory V2 not available"
        }

    try:
        memory_service = get_memory_service()
        heat_service = get_heat_service()

        # Build decision content
        content_parts = [f"Decision: {decision}"]

        if rationale:
            content_parts.append(f"Rationale: {rationale}")

        if alternatives_considered:
            content_parts.append(f"Alternatives considered: {', '.join(alternatives_considered)}")

        if client_name:
            content_parts.append(f"Client context: {client_name}")

        content = ". ".join(content_parts)

        # Build metadata
        metadata = {
            "source": "workos",
            "type": "decision",
            "importance": 1.5,  # Decisions are important
            "original_timestamp": datetime.now().isoformat(),
        }

        if task_id:
            metadata["task_id"] = str(task_id)

        if client_name:
            metadata["client"] = client_name

        if alternatives_considered:
            metadata["alternatives_count"] = len(alternatives_considered)

        # Store in Memory V2
        result = memory_service.add(content, metadata=metadata)

        # Boost heat for related client
        if client_name:
            heat_service.boost_related(client_name, "decision")

        logger.info(f"Stored decision in memory: {decision[:50]}...")

        return {
            "success": True,
            "memory_id": result.get("id"),
            "content_preview": content[:100] + "..." if len(content) > 100 else content
        }

    except Exception as e:
        logger.error(f"Failed to store decision: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def _extract_project_from_title(title: str) -> Optional[str]:
    """
    Extract project name from task title if present.

    Looks for common patterns like:
    - [ProjectName] Task description
    - ProjectName: Task description
    - ProjectName - Task description

    Args:
        title: Task title to parse

    Returns:
        Project name if found, None otherwise
    """
    import re

    # Pattern: [Project] description
    bracket_match = re.match(r'\[([^\]]+)\]', title)
    if bracket_match:
        return bracket_match.group(1)

    # Pattern: Project: description
    colon_match = re.match(r'^([^:]+):', title)
    if colon_match:
        potential_project = colon_match.group(1).strip()
        # Only consider short-ish strings as projects
        if len(potential_project) <= 30 and ' ' not in potential_project:
            return potential_project

    return None


# =============================================================================
# Queue Processing
# =============================================================================

def write_to_queue(event_type: str, data: Dict[str, Any]) -> bool:
    """
    Write an event to the queue file.

    Called by external systems (like WorkOS MCP via shell/HTTP) to queue
    events for processing.

    Args:
        event_type: Type of event (task_completion, decision)
        data: Event data

    Returns:
        True if successfully written
    """
    try:
        QUEUE_DIR.mkdir(parents=True, exist_ok=True)

        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

        with open(QUEUE_FILE, "a") as f:
            f.write(json.dumps(event) + "\n")

        logger.debug(f"Queued event: {event_type}")
        return True

    except Exception as e:
        logger.error(f"Failed to write to queue: {e}")
        return False


def process_queue() -> Dict[str, Any]:
    """
    Process all pending events in the queue.

    Reads the queue file, processes each event, and moves processed
    entries to the processed directory.

    Returns:
        Summary of processing results
    """
    if not QUEUE_FILE.exists():
        return {"processed": 0, "errors": 0, "message": "No queue file"}

    results = {
        "processed": 0,
        "errors": 0,
        "events": []
    }

    # Read all events
    events = []
    with open(QUEUE_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in queue: {e}")
                    results["errors"] += 1

    if not events:
        return {"processed": 0, "errors": 0, "message": "Queue empty"}

    # Process each event
    for event in events:
        event_type = event.get("type")
        data = event.get("data", {})

        try:
            if event_type == "task_completion":
                result = store_task_completion(data)
            elif event_type == "decision":
                result = store_decision(
                    decision=data.get("decision", ""),
                    task_id=data.get("task_id"),
                    client_name=data.get("client_name"),
                    alternatives_considered=data.get("alternatives"),
                    rationale=data.get("rationale")
                )
            else:
                logger.warning(f"Unknown event type: {event_type}")
                results["errors"] += 1
                continue

            if result.get("success"):
                results["processed"] += 1
            else:
                results["errors"] += 1

            results["events"].append({
                "type": event_type,
                "success": result.get("success"),
                "error": result.get("error")
            })

        except Exception as e:
            logger.error(f"Error processing event: {e}")
            results["errors"] += 1

    # Archive processed queue
    if results["processed"] > 0:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        archive_name = f"queue_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        archive_path = PROCESSED_DIR / archive_name

        # Move queue file to processed
        QUEUE_FILE.rename(archive_path)
        logger.info(f"Archived {results['processed']} events to {archive_path}")

    return results


def run_daemon(interval_seconds: int = 30):
    """
    Run as a daemon, processing the queue periodically.

    Args:
        interval_seconds: How often to check the queue (default 30s)
    """
    logger.info(f"Starting WorkOS Memory Bridge daemon (interval: {interval_seconds}s)")

    while True:
        try:
            results = process_queue()
            if results["processed"] > 0:
                logger.info(f"Processed {results['processed']} events, {results['errors']} errors")
        except Exception as e:
            logger.error(f"Daemon error: {e}")

        time.sleep(interval_seconds)


# =============================================================================
# CLI Interface
# =============================================================================

if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    )

    parser = argparse.ArgumentParser(description="WorkOS Memory Bridge")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--process", action="store_true", help="Process queue once")
    parser.add_argument("--interval", type=int, default=30, help="Daemon interval (seconds)")

    args = parser.parse_args()

    if args.daemon:
        run_daemon(args.interval)
    elif args.process:
        results = process_queue()
        print(json.dumps(results, indent=2))
    else:
        parser.print_help()
