#!/usr/bin/env python3
"""
SessionManager - Manages conversation history and session persistence.

This module provides the core session management infrastructure for Thanos,
handling message storage, token tracking, history management with sliding window,
and session persistence to both JSON and Markdown formats.

Classes:
    Message: Dataclass representing a single conversation message
    Session: Dataclass representing a conversation session with metadata
    SessionManager: Main class for managing sessions and conversation history

Constants:
    MAX_HISTORY: Maximum number of messages to keep in active history (sliding window)

Features:
    - Message tracking with role, content, and token counting
    - Sliding window history management (auto-trims old messages)
    - Session persistence to JSON and Markdown formats
    - Agent switching support
    - Session statistics and metadata tracking
    - Token accumulation across trimmed history

Architecture:
    Sessions are stored in History/Sessions/ directory in both formats:
    - Markdown (.md): Human-readable session transcripts
    - JSON (.json): Machine-readable format for search and analysis

Example:
    manager = SessionManager()
    manager.add_user_message("Hello", tokens=5)
    manager.add_assistant_message("Hi there!", tokens=10)
    filepath = manager.save()
    stats = manager.get_stats()
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Maximum number of messages to keep in active history (sliding window)
# Older messages are trimmed but token counts persist
MAX_HISTORY = 50


@dataclass
class Message:
    """
    Represents a single conversation message.

    Attributes:
        role: Message role ('user', 'assistant', 'system')
        content: Message text content
        timestamp: When the message was created
        tokens: Token count for this message
    """

    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tokens: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "tokens": self.tokens,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create message from dictionary."""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            tokens=data.get("tokens", 0),
        )


@dataclass
class Session:
    """
    Represents a conversation session with metadata.

    Attributes:
        id: Unique session identifier (8-character UUID prefix)
        started_at: Session start timestamp
        agent: Current active agent name
        history: List of conversation messages
        total_input_tokens: Cumulative input tokens (persists across trims)
        total_output_tokens: Cumulative output tokens (persists across trims)
        total_cost: Cumulative cost in USD
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    started_at: datetime = field(default_factory=datetime.now)
    agent: str = "ops"
    history: List[Message] = field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for serialization."""
        return {
            "id": self.id,
            "started_at": self.started_at.isoformat(),
            "agent": self.agent,
            "history": [msg.to_dict() for msg in self.history],
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost": self.total_cost,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """Create session from dictionary."""
        return cls(
            id=data["id"],
            started_at=datetime.fromisoformat(data["started_at"]),
            agent=data.get("agent", "ops"),
            history=[Message.from_dict(msg) for msg in data.get("history", [])],
            total_input_tokens=data.get("total_input_tokens", 0),
            total_output_tokens=data.get("total_output_tokens", 0),
            total_cost=data.get("total_cost", 0.0),
        )


class SessionManager:
    """
    Manages conversation sessions and message history.

    Provides:
    - Message addition with automatic token tracking
    - Sliding window history management (MAX_HISTORY limit)
    - Session persistence to JSON and Markdown formats
    - Agent switching
    - Session statistics

    The sliding window ensures history stays at MAX_HISTORY messages by
    trimming oldest messages when limit is reached. Token counts persist
    across trims to maintain accurate usage tracking.
    """

    def __init__(self, history_dir: Path = None):
        """
        Initialize SessionManager.

        Args:
            history_dir: Directory for session storage (default: ~/.claude/History/Sessions)
        """
        self.history_dir = history_dir or Path.home() / ".claude" / "History" / "Sessions"
        self.session = Session()

    def add_user_message(self, content: str, tokens: int = 0) -> None:
        """
        Add a user message to the conversation history.

        Args:
            content: Message text content
            tokens: Token count for this message
        """
        message = Message(role="user", content=content, tokens=tokens)
        self.session.history.append(message)
        self.session.total_input_tokens += tokens
        self._trim_history_if_needed()

    def add_assistant_message(self, content: str, tokens: int = 0) -> None:
        """
        Add an assistant message to the conversation history.

        Args:
            content: Message text content
            tokens: Token count for this message
        """
        message = Message(role="assistant", content=content, tokens=tokens)
        self.session.history.append(message)
        self.session.total_output_tokens += tokens
        self._trim_history_if_needed()

    def _trim_history_if_needed(self) -> None:
        """
        Trim history to MAX_HISTORY messages using sliding window.

        Removes oldest messages in pairs (user + assistant) to maintain
        conversation coherence. Token counts persist across trims.
        """
        if len(self.session.history) > MAX_HISTORY:
            # Remove oldest messages in pairs to maintain conversation flow
            # Calculate how many messages to remove
            excess = len(self.session.history) - MAX_HISTORY

            # Remove in pairs if possible to maintain user/assistant pairing
            if excess % 2 == 1:
                excess += 1  # Round up to even number

            # Trim from the beginning
            self.session.history = self.session.history[excess:]

    def get_messages_for_api(self) -> List[Dict[str, str]]:
        """
        Convert history to API format.

        Returns:
            List of message dicts with 'role' and 'content' keys
        """
        return [{"role": msg.role, "content": msg.content} for msg in self.session.history]

    def is_history_trimmed(self) -> bool:
        """
        Check if history is at the maximum limit.

        Returns:
            True if history length equals MAX_HISTORY
        """
        return len(self.session.history) >= MAX_HISTORY

    def switch_agent(self, agent_name: str) -> None:
        """
        Switch to a different agent.

        Args:
            agent_name: Name of the agent to switch to
        """
        self.session.agent = agent_name

    def clear(self) -> None:
        """
        Clear conversation history while preserving session metadata.

        Removes all messages but keeps token counts, session ID, and timestamps.
        """
        self.session.history.clear()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get session statistics.

        Returns:
            Dictionary with session metrics including:
            - session_id: Unique session identifier
            - message_count: Number of messages in current history
            - total_input_tokens: Cumulative input tokens
            - total_output_tokens: Cumulative output tokens
            - total_cost: Cumulative cost
            - current_agent: Active agent name
            - duration_minutes: Session duration in minutes
        """
        duration = datetime.now() - self.session.started_at
        duration_minutes = int(duration.total_seconds() / 60)

        return {
            "session_id": self.session.id,
            "message_count": len(self.session.history),
            "total_input_tokens": self.session.total_input_tokens,
            "total_output_tokens": self.session.total_output_tokens,
            "total_cost": self.session.total_cost,
            "current_agent": self.session.agent,
            "duration_minutes": duration_minutes,
        }

    def save(self) -> Path:
        """
        Save session to both JSON and Markdown formats.

        Saves to History/Sessions/ with timestamp-based filename.
        Creates directory if it doesn't exist.

        Returns:
            Path to the saved Markdown file
        """
        # Ensure history directory exists
        self.history_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp and session ID
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
        base_filename = f"{timestamp}-{self.session.id}"

        # Save JSON format
        json_path = self.history_dir / f"{base_filename}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.session.to_dict(), f, indent=2, ensure_ascii=False)

        # Save Markdown format
        md_path = self.history_dir / f"{base_filename}.md"
        md_content = self._generate_markdown()
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return md_path

    def _generate_markdown(self) -> str:
        """
        Generate markdown representation of session.

        Returns:
            Markdown-formatted session transcript
        """
        lines = []

        # Header
        lines.append(f"# Interactive Session")
        lines.append(f"\n**Session ID:** {self.session.id}")
        lines.append(f"**Agent:** {self.session.agent}")
        lines.append(f"**Started:** {self.session.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Duration:** {self.get_stats()['duration_minutes']} minutes")
        lines.append("")

        # Statistics
        lines.append("## Statistics")
        lines.append(f"- Messages: {len(self.session.history)}")
        lines.append(f"- Input tokens: {self.session.total_input_tokens:,}")
        lines.append(f"- Output tokens: {self.session.total_output_tokens:,}")
        lines.append(f"- Total tokens: {self.session.total_input_tokens + self.session.total_output_tokens:,}")
        lines.append(f"- Cost: ${self.session.total_cost:.4f}")
        lines.append("")

        # Conversation history
        lines.append("## Conversation")
        lines.append("")

        for msg in self.session.history:
            if msg.role == "user":
                role_label = "You"
            elif msg.role == "assistant":
                role_label = self.session.agent.capitalize()
            else:
                role_label = msg.role.capitalize()
            lines.append(f"**{role_label}:** {msg.content}")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append("*Saved by Thanos Interactive Mode*")

        return "\n".join(lines)

    def list_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent saved sessions.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session metadata dictionaries
        """
        if not self.history_dir.exists():
            return []

        # Find all JSON session files
        session_files = sorted(
            self.history_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
        )

        sessions = []
        for filepath in session_files[:limit]:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Extract metadata
                sessions.append(
                    {
                        "id": data.get("id", "unknown"),
                        "date": datetime.fromisoformat(data["started_at"]).strftime(
                            "%Y-%m-%d %H:%M"
                        ),
                        "agent": data.get("agent", "ops"),
                        "messages": len(data.get("history", [])),
                        "tokens": data.get("total_input_tokens", 0)
                        + data.get("total_output_tokens", 0),
                    }
                )
            except (json.JSONDecodeError, KeyError, ValueError):
                # Skip invalid session files
                continue

        return sessions

    def load_session(self, session_id: str) -> bool:
        """
        Load a saved session by ID.

        Args:
            session_id: Session ID to load (or "last" for most recent)

        Returns:
            True if session was loaded successfully, False otherwise
        """
        if not self.history_dir.exists():
            return False

        # Handle "last" shortcut
        if session_id == "last":
            sessions = self.list_sessions(limit=1)
            if not sessions:
                return False
            session_id = sessions[0]["id"]

        # Find session file by ID
        session_files = list(self.history_dir.glob(f"*-{session_id}.json"))

        if not session_files:
            return False

        try:
            with open(session_files[0], "r", encoding="utf-8") as f:
                data = json.load(f)

            # Load session from data
            self.session = Session.from_dict(data)
            return True

        except (json.JSONDecodeError, KeyError, ValueError):
            return False

    def create_branch(self, branch_name: str = None) -> str:
        """
        Create a conversation branch from current point.

        Args:
            branch_name: Optional name for the branch

        Returns:
            New session ID for the branch
        """
        # For now, create a new session with copied history
        # Full branching implementation will be added in later phases
        old_session = self.session

        # Create new session with fresh ID
        self.session = Session(
            agent=old_session.agent,
            history=old_session.history.copy(),
            total_input_tokens=old_session.total_input_tokens,
            total_output_tokens=old_session.total_output_tokens,
            total_cost=old_session.total_cost,
        )

        return self.session.id

    def get_branch_info(self) -> Dict[str, Any]:
        """
        Get information about the current branch.

        Returns:
            Dictionary with branch metadata
        """
        # Basic implementation for now
        return {
            "id": self.session.id,
            "name": "main",
            "parent_id": None,
            "branch_point": 0,
        }

    def list_branches(self) -> List[Dict[str, Any]]:
        """
        List all branches in the session tree.

        Returns:
            List of branch metadata dictionaries
        """
        # Basic implementation for now - return current session only
        return []

    def switch_branch(self, branch_ref: str) -> bool:
        """
        Switch to a different branch.

        Args:
            branch_ref: Branch name or ID to switch to

        Returns:
            True if branch was switched successfully, False otherwise
        """
        # Basic implementation for now - treat as load_session
        return self.load_session(branch_ref)
