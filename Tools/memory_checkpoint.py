"""
Memory Checkpoint System for Thanos.

Provides crash-resilient memory capture through:
1. Incremental checkpoints during long sessions
2. Orphan detection for crashed sessions
3. Checkpoint-to-memory extraction pipeline

Design:
- Checkpoints written every N prompts or M minutes
- Each checkpoint is incremental (only new content since last)
- Operator watchdog processes orphaned checkpoints
- Session-end hook does final capture and cleanup
"""

import json
import os
import time
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# Configuration
CHECKPOINT_DIR = Path("/Users/jeremy/Projects/Thanos/State/session_checkpoints")
CHECKPOINT_INTERVAL_PROMPTS = 10  # Write checkpoint every N prompts
CHECKPOINT_INTERVAL_MINUTES = 30  # Or every M minutes, whichever comes first
ORPHAN_THRESHOLD_HOURS = 2  # Session considered orphaned after N hours of no activity


@dataclass
class CheckpointEntry:
    """Single checkpoint entry representing accumulated context."""
    prompt_number: int
    timestamp: str
    content_hash: str
    summary: str  # Brief summary of what happened
    key_facts: List[str]  # Extracted facts/decisions
    files_modified: List[str]
    tools_used: List[str]


@dataclass
class SessionCheckpoint:
    """Full checkpoint state for a session."""
    session_id: str
    claude_pid: int
    started_at: str
    last_updated: str
    prompt_count: int
    working_directory: str
    entries: List[Dict[str, Any]]  # List of CheckpointEntry dicts

    # Metadata
    project: Optional[str] = None
    client: Optional[str] = None
    cumulative_summary: str = ""


class CheckpointManager:
    """
    Manages session checkpoints for crash-resilient memory capture.

    Usage:
        manager = CheckpointManager()

        # On each prompt (in UserPromptSubmit hook):
        manager.record_prompt(session_id, prompt_data)

        # Check if checkpoint needed:
        if manager.should_checkpoint(session_id):
            manager.write_checkpoint(session_id)

        # On session end:
        manager.finalize_session(session_id)

        # Cron job for orphans:
        manager.process_orphaned_sessions()
    """

    def __init__(self, checkpoint_dir: Path = CHECKPOINT_DIR):
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # In-memory state (per session)
        self._sessions: Dict[str, SessionCheckpoint] = {}
        self._pending_content: Dict[str, List[Dict]] = {}  # Content since last checkpoint
        self._last_checkpoint_time: Dict[str, float] = {}
        self._prompt_since_checkpoint: Dict[str, int] = {}

    def _get_checkpoint_path(self, session_id: str) -> Path:
        """Get path to checkpoint file for session."""
        return self.checkpoint_dir / f"{session_id}.json"

    def _get_lock_path(self, session_id: str) -> Path:
        """Get path to lock file for session."""
        return self.checkpoint_dir / f"{session_id}.lock"

    def initialize_session(
        self,
        session_id: str,
        claude_pid: int,
        working_directory: str,
        project: str = None,
        client: str = None
    ) -> SessionCheckpoint:
        """Initialize checkpoint tracking for a new session."""
        now = datetime.now().isoformat()

        checkpoint = SessionCheckpoint(
            session_id=session_id,
            claude_pid=claude_pid,
            started_at=now,
            last_updated=now,
            prompt_count=0,
            working_directory=working_directory,
            entries=[],
            project=project,
            client=client,
            cumulative_summary=""
        )

        self._sessions[session_id] = checkpoint
        self._pending_content[session_id] = []
        self._last_checkpoint_time[session_id] = time.time()
        self._prompt_since_checkpoint[session_id] = 0

        # Write initial checkpoint
        self._write_to_disk(session_id)

        # Create lock file with PID
        lock_path = self._get_lock_path(session_id)
        lock_path.write_text(json.dumps({
            "pid": claude_pid,
            "started": now
        }))

        logger.info(f"Initialized checkpoint for session {session_id}")
        return checkpoint

    def load_session(self, session_id: str) -> Optional[SessionCheckpoint]:
        """Load existing session checkpoint from disk."""
        checkpoint_path = self._get_checkpoint_path(session_id)

        if not checkpoint_path.exists():
            return None

        try:
            data = json.loads(checkpoint_path.read_text())
            checkpoint = SessionCheckpoint(**data)
            self._sessions[session_id] = checkpoint
            self._pending_content[session_id] = []
            self._last_checkpoint_time[session_id] = time.time()
            self._prompt_since_checkpoint[session_id] = 0
            return checkpoint
        except Exception as e:
            logger.error(f"Failed to load checkpoint {session_id}: {e}")
            return None

    def record_prompt(
        self,
        session_id: str,
        prompt_summary: str = "",
        key_facts: List[str] = None,
        files_modified: List[str] = None,
        tools_used: List[str] = None
    ):
        """
        Record a prompt interaction for later checkpointing.

        Called from UserPromptSubmit hook with extracted context.
        """
        if session_id not in self._sessions:
            # Try to load from disk
            if not self.load_session(session_id):
                logger.warning(f"No checkpoint found for session {session_id}")
                return

        checkpoint = self._sessions[session_id]
        checkpoint.prompt_count += 1
        checkpoint.last_updated = datetime.now().isoformat()

        # Accumulate pending content
        self._pending_content[session_id].append({
            "prompt_number": checkpoint.prompt_count,
            "timestamp": checkpoint.last_updated,
            "summary": prompt_summary,
            "key_facts": key_facts or [],
            "files_modified": files_modified or [],
            "tools_used": tools_used or []
        })

        self._prompt_since_checkpoint[session_id] += 1

        # Update lock file timestamp
        lock_path = self._get_lock_path(session_id)
        if lock_path.exists():
            lock_data = json.loads(lock_path.read_text())
            lock_data["last_activity"] = checkpoint.last_updated
            lock_path.write_text(json.dumps(lock_data))

    def should_checkpoint(self, session_id: str) -> bool:
        """Check if we should write a checkpoint now."""
        prompts = self._prompt_since_checkpoint.get(session_id, 0)
        last_time = self._last_checkpoint_time.get(session_id, 0)

        # Check prompt threshold
        if prompts >= CHECKPOINT_INTERVAL_PROMPTS:
            return True

        # Check time threshold
        elapsed_minutes = (time.time() - last_time) / 60
        if elapsed_minutes >= CHECKPOINT_INTERVAL_MINUTES and prompts > 0:
            return True

        return False

    def write_checkpoint(self, session_id: str) -> bool:
        """Write accumulated content to checkpoint file."""
        if session_id not in self._sessions:
            return False

        checkpoint = self._sessions[session_id]
        pending = self._pending_content.get(session_id, [])

        if not pending:
            return False

        # Create checkpoint entry from pending content
        entry = CheckpointEntry(
            prompt_number=checkpoint.prompt_count,
            timestamp=datetime.now().isoformat(),
            content_hash=hashlib.md5(json.dumps(pending).encode()).hexdigest()[:8],
            summary=self._summarize_pending(pending),
            key_facts=self._extract_facts(pending),
            files_modified=list(set(f for p in pending for f in p.get("files_modified", []))),
            tools_used=list(set(t for p in pending for t in p.get("tools_used", [])))
        )

        checkpoint.entries.append(asdict(entry))
        checkpoint.cumulative_summary = self._update_cumulative_summary(
            checkpoint.cumulative_summary,
            entry.summary
        )

        # Write to disk
        self._write_to_disk(session_id)

        # Reset counters
        self._pending_content[session_id] = []
        self._last_checkpoint_time[session_id] = time.time()
        self._prompt_since_checkpoint[session_id] = 0

        logger.info(f"Wrote checkpoint for session {session_id} (prompt {checkpoint.prompt_count})")
        return True

    def _write_to_disk(self, session_id: str):
        """Write checkpoint state to disk."""
        checkpoint = self._sessions[session_id]
        checkpoint_path = self._get_checkpoint_path(session_id)

        # Write atomically via temp file
        temp_path = checkpoint_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(asdict(checkpoint), indent=2))
        temp_path.rename(checkpoint_path)

    def _summarize_pending(self, pending: List[Dict]) -> str:
        """Create brief summary of pending content."""
        summaries = [p.get("summary", "") for p in pending if p.get("summary")]
        if not summaries:
            return f"{len(pending)} prompts processed"
        return "; ".join(summaries[:3])  # First 3 summaries

    def _extract_facts(self, pending: List[Dict]) -> List[str]:
        """Extract key facts from pending content."""
        facts = []
        for p in pending:
            facts.extend(p.get("key_facts", []))
        return facts[:10]  # Cap at 10 facts per checkpoint

    def _update_cumulative_summary(self, existing: str, new: str) -> str:
        """Update cumulative summary with new content."""
        if not existing:
            return new
        # Keep it bounded
        lines = existing.split("\n")
        lines.append(f"- {new}")
        if len(lines) > 20:
            lines = lines[-20:]  # Keep last 20 entries
        return "\n".join(lines)

    def finalize_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Finalize session checkpoint and prepare for memory extraction.

        Called from session-end hook. Returns data for Memory V2 ingestion.
        """
        # Write any pending content first
        if session_id in self._pending_content and self._pending_content[session_id]:
            self.write_checkpoint(session_id)

        if session_id not in self._sessions:
            if not self.load_session(session_id):
                return None

        checkpoint = self._sessions[session_id]

        # Prepare extraction data
        extraction_data = {
            "session_id": session_id,
            "duration_minutes": self._calculate_duration(checkpoint),
            "prompt_count": checkpoint.prompt_count,
            "working_directory": checkpoint.working_directory,
            "project": checkpoint.project,
            "client": checkpoint.client,
            "cumulative_summary": checkpoint.cumulative_summary,
            "all_facts": self._collect_all_facts(checkpoint),
            "all_files_modified": self._collect_all_files(checkpoint),
            "entries": checkpoint.entries
        }

        # Clean up
        self._cleanup_session(session_id)

        return extraction_data

    def _calculate_duration(self, checkpoint: SessionCheckpoint) -> int:
        """Calculate session duration in minutes."""
        try:
            start = datetime.fromisoformat(checkpoint.started_at)
            end = datetime.fromisoformat(checkpoint.last_updated)
            return int((end - start).total_seconds() / 60)
        except:
            return 0

    def _collect_all_facts(self, checkpoint: SessionCheckpoint) -> List[str]:
        """Collect all facts from all checkpoint entries."""
        facts = []
        for entry in checkpoint.entries:
            facts.extend(entry.get("key_facts", []))
        return list(set(facts))  # Dedupe

    def _collect_all_files(self, checkpoint: SessionCheckpoint) -> List[str]:
        """Collect all modified files from all entries."""
        files = []
        for entry in checkpoint.entries:
            files.extend(entry.get("files_modified", []))
        return list(set(files))

    def _cleanup_session(self, session_id: str):
        """Clean up session data after finalization."""
        # Remove from memory
        self._sessions.pop(session_id, None)
        self._pending_content.pop(session_id, None)
        self._last_checkpoint_time.pop(session_id, None)
        self._prompt_since_checkpoint.pop(session_id, None)

        # Archive checkpoint file (don't delete, move to archive)
        checkpoint_path = self._get_checkpoint_path(session_id)
        if checkpoint_path.exists():
            archive_dir = self.checkpoint_dir / "archive"
            archive_dir.mkdir(exist_ok=True)
            archive_path = archive_dir / f"{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            checkpoint_path.rename(archive_path)

        # Remove lock file
        lock_path = self._get_lock_path(session_id)
        if lock_path.exists():
            lock_path.unlink()

    def get_orphaned_sessions(self) -> List[str]:
        """
        Find sessions that appear to be orphaned (crashed/abandoned).

        A session is orphaned if:
        - Has a checkpoint file
        - Lock file PID is not running OR
        - No activity for ORPHAN_THRESHOLD_HOURS
        """
        orphaned = []

        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            if checkpoint_file.name.startswith("archive"):
                continue

            session_id = checkpoint_file.stem
            lock_path = self._get_lock_path(session_id)

            # Check if lock exists
            if not lock_path.exists():
                orphaned.append(session_id)
                continue

            try:
                lock_data = json.loads(lock_path.read_text())
                pid = lock_data.get("pid")
                last_activity = lock_data.get("last_activity", lock_data.get("started"))

                # Check if PID is still running
                if pid and not self._is_pid_running(pid):
                    orphaned.append(session_id)
                    continue

                # Check activity threshold
                if last_activity:
                    last_time = datetime.fromisoformat(last_activity)
                    threshold = datetime.now() - timedelta(hours=ORPHAN_THRESHOLD_HOURS)
                    if last_time < threshold:
                        orphaned.append(session_id)

            except Exception as e:
                logger.warning(f"Error checking session {session_id}: {e}")
                orphaned.append(session_id)

        return orphaned

    def _is_pid_running(self, pid: int) -> bool:
        """Check if a PID is still running."""
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def process_orphaned_sessions(self) -> List[Dict[str, Any]]:
        """
        Process all orphaned sessions and extract their memories.

        Returns list of extraction data for Memory V2 ingestion.
        """
        orphaned = self.get_orphaned_sessions()
        results = []

        for session_id in orphaned:
            logger.info(f"Processing orphaned session: {session_id}")

            # Load and finalize
            if self.load_session(session_id):
                extraction = self.finalize_session(session_id)
                if extraction:
                    extraction["orphaned"] = True
                    results.append(extraction)

        return results


# Convenience functions for hook usage
_manager: Optional[CheckpointManager] = None

def get_checkpoint_manager() -> CheckpointManager:
    """Get singleton checkpoint manager instance."""
    global _manager
    if _manager is None:
        _manager = CheckpointManager()
    return _manager


def checkpoint_prompt(
    session_id: str,
    claude_pid: int = None,
    working_directory: str = None,
    prompt_summary: str = "",
    key_facts: List[str] = None,
    files_modified: List[str] = None,
    tools_used: List[str] = None,
    project: str = None,
    client: str = None
) -> bool:
    """
    Convenience function for UserPromptSubmit hook.

    Records prompt and writes checkpoint if threshold reached.
    Returns True if checkpoint was written.
    """
    manager = get_checkpoint_manager()

    # Initialize if needed
    if session_id not in manager._sessions:
        if not manager.load_session(session_id):
            if claude_pid and working_directory:
                manager.initialize_session(
                    session_id=session_id,
                    claude_pid=claude_pid,
                    working_directory=working_directory,
                    project=project,
                    client=client
                )
            else:
                return False

    # Record prompt
    manager.record_prompt(
        session_id=session_id,
        prompt_summary=prompt_summary,
        key_facts=key_facts,
        files_modified=files_modified,
        tools_used=tools_used
    )

    # Check and write checkpoint if needed
    if manager.should_checkpoint(session_id):
        return manager.write_checkpoint(session_id)

    return False


def finalize_session_checkpoint(session_id: str) -> Optional[Dict[str, Any]]:
    """Convenience function for session-end hook."""
    manager = get_checkpoint_manager()
    return manager.finalize_session(session_id)


def process_orphans() -> List[Dict[str, Any]]:
    """Convenience function for cron/watchdog."""
    manager = get_checkpoint_manager()
    return manager.process_orphaned_sessions()


if __name__ == "__main__":
    # CLI for testing/manual processing
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1 and sys.argv[1] == "orphans":
        print("Processing orphaned sessions...")
        results = process_orphans()
        print(f"Processed {len(results)} orphaned sessions")
        for r in results:
            print(f"  - {r['session_id']}: {r['prompt_count']} prompts, {r['duration_minutes']}min")
    else:
        print("Usage: python memory_checkpoint.py orphans")
