#!/usr/bin/env python3
"""
Tmux Session Manager for Thanos.

Provides programmatic tmux session management with:
- Named session creation and attachment
- Auto-recovery from crashed sessions
- Session lifecycle management
- State tracking and persistence
- Graceful degradation when tmux not installed

Usage:
    from Access.tmux_manager import TmuxManager

    manager = TmuxManager()
    manager.attach_or_create("thanos-main")
"""

import json
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class SessionInfo:
    """Tmux session information."""
    name: str
    created_at: str
    last_attached: Optional[str] = None
    window_count: int = 1
    is_attached: bool = False
    metadata: Optional[Dict[str, Any]] = None


class TmuxManager:
    """Manages tmux sessions for Thanos."""

    STATE_FILE = Path(__file__).parent.parent / "State" / "tmux_sessions.json"
    VALID_SESSIONS = {"thanos-main", "thanos-dev", "thanos-monitor"}

    def __init__(self):
        """Initialize tmux manager."""
        self.logger = self._setup_logging()
        self.tmux_available = self._check_tmux_available()
        self.sessions_state = self._load_state()

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for tmux manager."""
        logger = logging.getLogger("thanos.tmux")
        logger.setLevel(logging.INFO)

        # Console handler
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _check_tmux_available(self) -> bool:
        """Check if tmux is installed and available."""
        return shutil.which("tmux") is not None

    def _load_state(self) -> Dict[str, SessionInfo]:
        """Load session state from disk."""
        if not self.STATE_FILE.exists():
            return {}

        try:
            with open(self.STATE_FILE, 'r') as f:
                data = json.load(f)
                return {
                    name: SessionInfo(**info)
                    for name, info in data.items()
                }
        except Exception as e:
            self.logger.warning(f"Failed to load session state: {e}")
            return {}

    def _save_state(self) -> None:
        """Save session state to disk."""
        try:
            self.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(self.STATE_FILE, 'w') as f:
                json.dump(
                    {name: asdict(info) for name, info in self.sessions_state.items()},
                    f,
                    indent=2
                )
        except Exception as e:
            self.logger.error(f"Failed to save session state: {e}")

    def _run_tmux(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """Run tmux command with error handling.

        Args:
            *args: Tmux command arguments
            check: Whether to check return code

        Returns:
            CompletedProcess result

        Raises:
            RuntimeError: If tmux is not available
        """
        if not self.tmux_available:
            raise RuntimeError("tmux is not installed or not in PATH")

        try:
            result = subprocess.run(
                ["tmux"] + list(args),
                capture_output=True,
                text=True,
                check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Tmux command failed: {e.stderr}")
            raise

    def session_exists(self, session_name: str) -> bool:
        """Check if a tmux session exists.

        Args:
            session_name: Name of the session

        Returns:
            True if session exists
        """
        if not self.tmux_available:
            return False

        try:
            result = self._run_tmux("has-session", "-t", session_name, check=False)
            return result.returncode == 0
        except Exception as e:
            self.logger.warning(f"Error checking session existence: {e}")
            return False

    def list_sessions(self) -> List[str]:
        """List all active tmux sessions.

        Returns:
            List of session names
        """
        if not self.tmux_available:
            return []

        try:
            result = self._run_tmux("list-sessions", "-F", "#{session_name}", check=False)
            if result.returncode != 0:
                return []
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]
        except Exception as e:
            self.logger.warning(f"Error listing sessions: {e}")
            return []

    def create_session(
        self,
        session_name: str,
        detached: bool = True,
        start_directory: Optional[Path] = None
    ) -> bool:
        """Create a new tmux session.

        Args:
            session_name: Name for the session
            detached: Create in detached mode
            start_directory: Starting directory for session

        Returns:
            True if session was created successfully
        """
        if not self.tmux_available:
            self.logger.error("Cannot create session: tmux not available")
            return False

        if session_name not in self.VALID_SESSIONS:
            self.logger.warning(f"Non-standard session name: {session_name}")

        if self.session_exists(session_name):
            self.logger.info(f"Session {session_name} already exists")
            return True

        try:
            args = ["new-session", "-s", session_name]

            if detached:
                args.append("-d")

            if start_directory:
                args.extend(["-c", str(start_directory)])

            self._run_tmux(*args)

            # Update state
            self.sessions_state[session_name] = SessionInfo(
                name=session_name,
                created_at=datetime.now().isoformat(),
                is_attached=not detached,
                metadata={"start_directory": str(start_directory)} if start_directory else None
            )
            self._save_state()

            self.logger.info(f"Created session: {session_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create session {session_name}: {e}")
            return False

    def attach_session(self, session_name: str, read_only: bool = False) -> bool:
        """Attach to an existing tmux session.

        Args:
            session_name: Name of the session to attach
            read_only: Attach in read-only mode

        Returns:
            True if attach was successful
        """
        if not self.tmux_available:
            self.logger.error("Cannot attach: tmux not available")
            return False

        if not self.session_exists(session_name):
            self.logger.error(f"Session {session_name} does not exist")
            return False

        try:
            args = ["attach-session", "-t", session_name]

            if read_only:
                args.append("-r")

            # This will exec into tmux, so we won't return
            subprocess.run(["tmux"] + args)

            # Update state (this might not execute if exec succeeds)
            if session_name in self.sessions_state:
                self.sessions_state[session_name].last_attached = datetime.now().isoformat()
                self.sessions_state[session_name].is_attached = True
                self._save_state()

            return True

        except Exception as e:
            self.logger.error(f"Failed to attach to session {session_name}: {e}")
            return False

    def detach_session(self, session_name: Optional[str] = None) -> bool:
        """Detach from a tmux session.

        Args:
            session_name: Session to detach from (current if None)

        Returns:
            True if detach was successful
        """
        if not self.tmux_available:
            return False

        try:
            args = ["detach-client"]
            if session_name:
                args.extend(["-s", session_name])

            self._run_tmux(*args, check=False)

            # Update state
            if session_name and session_name in self.sessions_state:
                self.sessions_state[session_name].is_attached = False
                self._save_state()

            return True

        except Exception as e:
            self.logger.error(f"Failed to detach session: {e}")
            return False

    def kill_session(self, session_name: str) -> bool:
        """Kill a tmux session.

        Args:
            session_name: Name of session to kill

        Returns:
            True if session was killed
        """
        if not self.tmux_available:
            return False

        if not self.session_exists(session_name):
            self.logger.warning(f"Session {session_name} does not exist")
            return False

        try:
            self._run_tmux("kill-session", "-t", session_name)

            # Remove from state
            if session_name in self.sessions_state:
                del self.sessions_state[session_name]
                self._save_state()

            self.logger.info(f"Killed session: {session_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to kill session {session_name}: {e}")
            return False

    def attach_or_create(
        self,
        session_name: str,
        start_directory: Optional[Path] = None
    ) -> bool:
        """Attach to session if exists, create and attach if not.

        Args:
            session_name: Name of the session
            start_directory: Starting directory if creating

        Returns:
            True if successful
        """
        if not self.tmux_available:
            self.logger.warning("tmux not available - running without session management")
            return False

        if self.session_exists(session_name):
            self.logger.info(f"Attaching to existing session: {session_name}")
            return self.attach_session(session_name)
        else:
            self.logger.info(f"Creating and attaching to session: {session_name}")
            if self.create_session(session_name, detached=True, start_directory=start_directory):
                return self.attach_session(session_name)
            return False

    def get_session_info(self, session_name: str) -> Optional[SessionInfo]:
        """Get information about a session.

        Args:
            session_name: Name of the session

        Returns:
            SessionInfo if available
        """
        # First check if session actually exists in tmux
        if self.tmux_available and self.session_exists(session_name):
            try:
                # Get window count
                result = self._run_tmux(
                    "list-windows", "-t", session_name, "-F", "#{window_index}",
                    check=False
                )
                window_count = len(result.stdout.splitlines())

                # Update state with current info
                if session_name not in self.sessions_state:
                    self.sessions_state[session_name] = SessionInfo(
                        name=session_name,
                        created_at=datetime.now().isoformat(),
                        window_count=window_count
                    )
                else:
                    self.sessions_state[session_name].window_count = window_count

                self._save_state()

            except Exception as e:
                self.logger.warning(f"Error getting session info: {e}")

        return self.sessions_state.get(session_name)

    def cleanup_orphaned_state(self) -> int:
        """Remove state for sessions that no longer exist.

        Returns:
            Number of orphaned states removed
        """
        if not self.tmux_available:
            return 0

        active_sessions = set(self.list_sessions())
        orphaned = []

        for session_name in list(self.sessions_state.keys()):
            if session_name not in active_sessions:
                orphaned.append(session_name)
                del self.sessions_state[session_name]

        if orphaned:
            self._save_state()
            self.logger.info(f"Cleaned up {len(orphaned)} orphaned session states")

        return len(orphaned)

    def get_status(self) -> Dict[str, Any]:
        """Get overall tmux status.

        Returns:
            Status dictionary
        """
        active_sessions = self.list_sessions() if self.tmux_available else []

        return {
            "tmux_available": self.tmux_available,
            "active_sessions": active_sessions,
            "tracked_sessions": list(self.sessions_state.keys()),
            "session_count": len(active_sessions),
            "valid_sessions": list(self.VALID_SESSIONS),
            "state_file": str(self.STATE_FILE)
        }


def main():
    """Test tmux manager functionality."""
    manager = TmuxManager()

    print("Tmux Manager Status:")
    print("=" * 60)
    status = manager.get_status()
    for key, value in status.items():
        print(f"{key}: {value}")
    print()

    # Cleanup orphaned states
    cleaned = manager.cleanup_orphaned_state()
    if cleaned > 0:
        print(f"Cleaned up {cleaned} orphaned session states")
        print()


if __name__ == "__main__":
    main()
