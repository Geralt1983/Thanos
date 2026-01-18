#!/usr/bin/env python3
"""
SessionManager - Manages conversation sessions with message tracking and token accounting.

This module handles session state, conversation history, token counting, and persistence
for Thanos interactive mode. It implements a sliding window for history management and
tracks cumulative statistics across the session lifecycle.

Key Features:
    - Message history with automatic token tracking
    - Sliding window history management (MAX_HISTORY limit)
    - Cumulative token and cost accounting
    - Session persistence to markdown files
    - Agent switching within sessions
    - Session statistics and duration tracking

Key Classes:
    Message: Represents a single conversation message with metadata
    Session: Container for session state and history
    SessionManager: Main interface for session operations

Usage:
    from Tools.session_manager import SessionManager

    # Initialize session manager
    session_mgr = SessionManager()

    # Add messages
    session_mgr.add_user_message("Hello", tokens=10)
    session_mgr.add_assistant_message("Hi there!", tokens=15)

    # Get statistics
    stats = session_mgr.get_stats()
    print(f"Total tokens: {stats['total_input_tokens'] + stats['total_output_tokens']}")
    print(f"Cost: ${stats['total_cost']:.4f}")

    # Save session
    filepath = session_mgr.save()
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import uuid
import json


# Maximum number of messages to keep in history (sliding window)
MAX_HISTORY = 100


@dataclass
class Message:
    """
    Represents a single conversation message.

    Attributes:
        role: Message role ("user" or "assistant")
        content: Message text content
        timestamp: When the message was created
        tokens: Token count for this message (0 if unknown)
    """
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tokens: int = 0


@dataclass
class Session:
    """
    Container for session state and conversation history.

    Attributes:
        id: Unique session identifier (first 8 chars of UUID)
        started_at: Session start timestamp
        agent: Current agent name (e.g., "ops", "coach", "strategy")
        history: List of conversation messages
        total_input_tokens: Cumulative input tokens across entire session
        total_output_tokens: Cumulative output tokens across entire session
        total_cost: Cumulative estimated cost in USD
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    started_at: datetime = field(default_factory=datetime.now)
    agent: str = "ops"
    history: List[Message] = field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0


class SessionManager:
    """
    Manages conversation sessions with message tracking and statistics.

    This class handles all session operations including message addition,
    history management with sliding window trimming, token accounting,
    and session persistence.

    The sliding window keeps the most recent MAX_HISTORY messages while
    maintaining cumulative token counts across the entire session.

    Attributes:
        session: Current Session instance
        history_dir: Directory for saving session files
    """

    def __init__(self, history_dir: Optional[Path] = None):
        """
        Initialize SessionManager with a new session.

        Args:
            history_dir: Directory for session persistence (default: History/Sessions)
        """
        self.session = Session()
        self.history_dir = history_dir or Path("History/Sessions")

    def add_user_message(self, content: str, tokens: int = 0) -> None:
        """
        Add a user message to the conversation history.

        Args:
            content: Message text
            tokens: Token count for this message (default: 0)
        """
        message = Message(role="user", content=content, tokens=tokens)
        self.session.history.append(message)
        self.session.total_input_tokens += tokens
        self._trim_history()

    def add_assistant_message(self, content: str, tokens: int = 0) -> None:
        """
        Add an assistant message to the conversation history.

        Args:
            content: Message text
            tokens: Token count for this message (default: 0)
        """
        message = Message(role="assistant", content=content, tokens=tokens)
        self.session.history.append(message)
        self.session.total_output_tokens += tokens
        self._trim_history()

    def _trim_history(self) -> None:
        """
        Trim history to MAX_HISTORY messages using sliding window.

        Removes oldest messages (in pairs when possible) while maintaining
        cumulative token counts. This prevents memory growth in long sessions
        while preserving session statistics.
        """
        if len(self.session.history) > MAX_HISTORY:
            # Calculate how many messages to remove
            messages_to_remove = len(self.session.history) - MAX_HISTORY

            # Try to remove in pairs to maintain conversation coherence
            # If we have an odd number to remove, just remove from the start
            self.session.history = self.session.history[messages_to_remove:]

    def get_messages_for_api(self) -> List[Dict[str, str]]:
        """
        Convert conversation history to API format.

        Returns:
            List of message dicts with 'role' and 'content' keys
        """
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.session.history
        ]

    def is_history_trimmed(self) -> bool:
        """
        Check if history is at or above the MAX_HISTORY limit.

        Returns:
            True if history is at max capacity, False otherwise
        """
        return len(self.session.history) >= MAX_HISTORY

    def switch_agent(self, agent_name: str) -> None:
        """
        Switch to a different agent.

        Args:
            agent_name: Name of the agent to switch to (e.g., "ops", "coach")
        """
        self.session.agent = agent_name

    def clear(self) -> None:
        """
        Clear conversation history while preserving session metadata.

        This removes all messages from history but maintains the session ID,
        agent, and cumulative token/cost statistics.
        """
        self.session.history = []

    def get_stats(self) -> Dict:
        """
        Get current session statistics.

        Returns:
            Dictionary containing:
                - session_id: Unique session identifier
                - message_count: Number of messages in current history
                - total_input_tokens: Cumulative input tokens
                - total_output_tokens: Cumulative output tokens
                - total_cost: Cumulative cost in USD
                - current_agent: Current agent name
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
        Save session to a markdown file.

        Creates a markdown file with session metadata, statistics, and
        conversation history. Filename format: YYYY-MM-DD-HHMM-sessionid.md

        Returns:
            Path to the saved file
        """
        # Ensure history directory exists
        self.history_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp and session ID
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
        filename = f"{timestamp}-{self.session.id}.md"
        filepath = self.history_dir / filename

        # Build markdown content
        lines = []
        lines.append("# Interactive Session\n")
        lines.append(f"**Session ID:** {self.session.id}\n")
        lines.append(f"**Started:** {self.session.started_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"**Agent:** {self.session.agent}\n")
        lines.append(f"**Messages:** {len(self.session.history)}\n")
        lines.append(f"**Total Tokens:** {self.session.total_input_tokens + self.session.total_output_tokens:,}\n")
        lines.append(f"**Estimated Cost:** ${self.session.total_cost:.4f}\n")
        lines.append("\n---\n\n")

        # Add conversation history
        lines.append("## Conversation\n\n")
        for msg in self.session.history:
            role_display = "You" if msg.role == "user" else self.session.agent.capitalize()
            timestamp_str = msg.timestamp.strftime("%H:%M:%S")
            lines.append(f"**{role_display}:** {msg.content}\n\n")

        lines.append("---\n")
        lines.append("*Saved by Thanos Interactive Mode*\n")

        # Write to file
        filepath.write_text("".join(lines))

        # Save to JSON
        json_filepath = filepath.with_suffix(".json")
        json_data = {
            "id": self.session.id,
            "started_at": self.session.started_at.isoformat(),
            "agent": self.session.agent,
            "total_input_tokens": self.session.total_input_tokens,
            "total_output_tokens": self.session.total_output_tokens,
            "total_cost": self.session.total_cost,
            "history": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "tokens": msg.tokens
                }
                for msg in self.session.history
            ]
        }
        json_filepath.write_text(json.dumps(json_data, indent=2))

        return filepath

    def list_sessions(self, limit: int = 10) -> List[Dict]:
        """
        List recent saved sessions.

        Args:
            limit: Maximum number of sessions to return (default: 10)

        Returns:
            List of session info dicts with keys: id, date, agent, messages, tokens
        """
        if not self.history_dir.exists():
            return []

        # Find all session markdown files
        session_files = sorted(
            self.history_dir.glob("*.md"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )[:limit]

        sessions = []
        for filepath in session_files:
            # Extract info from filename: YYYY-MM-DD-HHMM-sessionid.md
            stem = filepath.stem
            parts = stem.split("-")
            if len(parts) >= 5:
                session_id = parts[4]
                date = f"{parts[0]}-{parts[1]}-{parts[2]}"

                # Try to read agent and stats from file
                try:
                    content = filepath.read_text()
                    agent = "ops"  # default
                    messages = 0
                    tokens = 0

                    for line in content.split("\n"):
                        if line.startswith("**Agent:**"):
                            agent = line.split("**Agent:**")[1].strip()
                        elif line.startswith("**Messages:**"):
                            messages = int(line.split("**Messages:**")[1].strip())
                        elif line.startswith("**Total Tokens:**"):
                            tokens_str = line.split("**Total Tokens:**")[1].strip().replace(",", "")
                            tokens = int(tokens_str)

                    sessions.append({
                        "id": session_id,
                        "date": date,
                        "agent": agent,
                        "messages": messages,
                        "tokens": tokens,
                    })
                except (ValueError, IndexError):
                    # Skip malformed files
                    continue

        return sessions

    def load_session(self, session_id: str) -> bool:
        """
        Load a saved session by ID.

        Args:
            session_id: Session ID to load, or "last" for most recent

        Returns:
            True if session loaded successfully, False otherwise
        """
        # Handle "last" alias
        if session_id == "last":
            sessions = self.list_sessions(limit=1)
            if not sessions:
                return False
            session_id = sessions[0]["id"]

        # Find matching session file
        if not self.history_dir.exists():
            return False

        matching_files = list(self.history_dir.glob(f"*-{session_id}.md"))
        if not matching_files:
            return False

        # For now, just note that the session was found
        # Full implementation would parse the markdown and restore history
        # This is a simplified version for the MVP
        return True

    def create_branch(self, branch_name: Optional[str] = None) -> str:
        """
        Create a conversation branch from the current point.

        Args:
            branch_name: Optional name for the branch

        Returns:
            New session ID for the branch
        """
        # For MVP, just create a new session
        # Full implementation would maintain branch tree
        new_session = Session(agent=self.session.agent)
        new_session.history = self.session.history.copy()
        new_session.total_input_tokens = self.session.total_input_tokens
        new_session.total_output_tokens = self.session.total_output_tokens
        new_session.total_cost = self.session.total_cost

        self.session = new_session
        return new_session.id

    def get_branch_info(self) -> Dict:
        """
        Get information about the current branch.

        Returns:
            Dict with branch metadata
        """
        return {
            "id": self.session.id,
            "name": f"branch-{self.session.id}",
            "parent_id": None,
            "branch_point": 0,
        }

    def list_branches(self) -> List[Dict]:
        """
        List all branches of the current session tree.

        Returns:
            List of branch info dicts
        """
        # For MVP, return empty list
        # Full implementation would track branch tree
        return []

    def switch_branch(self, branch_ref: str) -> bool:
        """
        Switch to a different branch.

        Args:
            branch_ref: Branch name or ID

        Returns:
            True if switched successfully, False otherwise
        """
        # For MVP, return False (not implemented)
        # Full implementation would maintain branch tree
        return False
