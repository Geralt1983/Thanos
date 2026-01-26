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
import logging

# Configure logger for this module
logger = logging.getLogger(__name__)


# Maximum number of messages to keep in history (sliding window)
MAX_HISTORY = 100

# Maximum tokens to include in API context (prevents token growth)
MAX_CONTEXT_TOKENS = 4000


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

    def _summarize_before_trim(self) -> Optional[str]:
        """
        Summarize messages that will be trimmed from history.

        Called before _trim_history() removes old messages. Summarizes the
        messages that are about to be discarded and stores the summary in
        Memory V2 for later retrieval.

        Returns:
            Summary text if summarization was performed, None otherwise
        """
        if len(self.session.history) <= MAX_HISTORY:
            return None

        # Determine which messages will be trimmed
        messages_to_remove = len(self.session.history) - MAX_HISTORY
        messages_to_summarize = self.session.history[:messages_to_remove]

        if not messages_to_summarize:
            return None

        # Convert to format expected by summarizer (list of dicts with role and content)
        messages_dict = [
            {"role": msg.role, "content": msg.content}
            for msg in messages_to_summarize
        ]

        try:
            from Tools.conversation_summarizer import ConversationSummarizer

            summarizer = ConversationSummarizer()
            result = summarizer.summarize_messages(messages_dict)

            # Store summary using ConversationSummarizer.store_summary()
            if result:
                summary_text = result.summary if hasattr(result, 'summary') else str(result)

                # Store via ConversationSummarizer's store_summary method
                summarizer.store_summary(
                    summary=result,
                    session_id=self.session.id,
                    metadata={
                        "messages_count": len(messages_to_summarize),
                        "agent": self.session.agent,
                    }
                )

                logger.info(
                    f"Summarized {len(messages_to_summarize)} messages before trim "
                    f"(session={self.session.id})"
                )

                return summary_text

        except Exception as e:
            logger.warning(f"Failed to summarize messages before trim: {e}")
            return None

        return None

    def _trim_history(self) -> None:
        """
        Trim history to MAX_HISTORY messages using sliding window.

        Removes oldest messages (in pairs when possible) while maintaining
        cumulative token counts. This prevents memory growth in long sessions
        while preserving session statistics.

        Before trimming, triggers summarization of messages that will be
        removed to preserve context in Memory V2.
        """
        if len(self.session.history) > MAX_HISTORY:
            # Summarize messages before trimming
            self._summarize_before_trim()

            # Calculate how many messages to remove
            messages_to_remove = len(self.session.history) - MAX_HISTORY

            # Try to remove in pairs to maintain conversation coherence
            # If we have an odd number to remove, just remove from the start
            self.session.history = self.session.history[messages_to_remove:]

    def _estimate_tokens(self, content: str) -> int:
        """
        Estimate token count for a string using rough approximation.

        Uses ~4 characters per token as a conservative estimate.
        This avoids importing tiktoken while providing reasonable accuracy.

        Args:
            content: Text content to estimate tokens for

        Returns:
            Estimated token count
        """
        return len(content) // 4 + 1  # +1 to avoid zero for short strings

    def get_messages_for_api(self, max_tokens: int = MAX_CONTEXT_TOKENS, inject_memory: bool = True) -> List[Dict[str, str]]:
        """
        Convert conversation history to API format with token-based windowing.

        Implements a sliding window that returns only the most recent messages
        that fit within the token limit. This prevents unbounded token growth
        in long conversations while maintaining coherence.

        The method:
        - Always includes at least the last user message
        - Preserves user/assistant pairs together when possible
        - Estimates tokens using ~4 chars per token
        - Injects relevant memories from previous conversations when available

        Args:
            max_tokens: Maximum tokens to include (default: MAX_CONTEXT_TOKENS)
            inject_memory: Whether to inject relevant context from memory (default: True)

        Returns:
            List of message dicts with 'role' and 'content' keys
        """
        if not self.session.history:
            return []

        # Reserve tokens for memory injection if enabled
        memory_budget = 500  # Reserve 500 tokens for injected context
        message_budget = max_tokens - memory_budget if inject_memory else max_tokens

        # Work backwards from most recent messages
        messages_to_include = []
        total_tokens = 0

        # Iterate from most recent to oldest
        for msg in reversed(self.session.history):
            msg_tokens = self._estimate_tokens(msg.content)

            # Always include at least the last user message
            if not messages_to_include and msg.role == "user":
                messages_to_include.insert(0, {"role": msg.role, "content": msg.content})
                total_tokens += msg_tokens
                continue

            # Check if adding this message would exceed limit
            if total_tokens + msg_tokens > message_budget:
                # If we're breaking a pair, try to include the assistant response
                # to maintain coherence (user question + assistant answer)
                if messages_to_include and messages_to_include[0]["role"] == "assistant":
                    # We have an assistant message but no user question - include one more
                    if msg.role == "user":
                        messages_to_include.insert(0, {"role": msg.role, "content": msg.content})
                break

            messages_to_include.insert(0, {"role": msg.role, "content": msg.content})
            total_tokens += msg_tokens

        # Inject relevant context from memory if enabled and we have messages
        if inject_memory and messages_to_include:
            try:
                from Tools.context_optimizer import ContextOptimizer

                # Initialize optimizer (lightweight - caches internally)
                optimizer = ContextOptimizer(
                    max_results=3,
                    relevance_threshold=0.3,
                    max_tokens=memory_budget
                )

                # Get the last user message as the query
                last_user_msg = None
                for msg in reversed(messages_to_include):
                    if msg["role"] == "user":
                        last_user_msg = msg["content"]
                        break

                if last_user_msg:
                    # Retrieve relevant context
                    context = optimizer.retrieve_relevant_context(
                        current_prompt=last_user_msg,
                        session_id=self.session.id,
                        max_tokens=memory_budget
                    )

                    # Inject formatted context if we got results
                    if context.get("formatted_context"):
                        formatted_context = context["formatted_context"]

                        # Inject as a system message at the beginning
                        system_message = {
                            "role": "system",
                            "content": formatted_context
                        }
                        messages_to_include.insert(0, system_message)

                        logger.info(
                            f"Injected {context.get('count', 0)} memories "
                            f"({context.get('token_count', 0)} tokens) into conversation context"
                        )

            except Exception as e:
                # Memory injection is optional - don't fail if it errors
                logger.warning(f"Failed to inject memory context: {e}")

        return messages_to_include

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
            "error_count": getattr(self.session, 'error_count', 0),
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

        # Save to JSON with enhanced metadata for memory integration
        json_filepath = filepath.with_suffix(".json")
        json_data = {
            "id": self.session.id,
            "started_at": self.session.started_at.isoformat(),
            "ended_at": datetime.now().isoformat(),
            "agent": self.session.agent,
            "total_input_tokens": self.session.total_input_tokens,
            "total_output_tokens": self.session.total_output_tokens,
            "total_cost": self.session.total_cost,
            "error_count": getattr(self.session, 'error_count', 0),
            "history": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "tokens": msg.tokens
                }
                for msg in self.session.history
            ],
            # Memory snapshot for contextual recall
            "memory_snapshot": self._build_memory_snapshot()
        }
        json_filepath.write_text(json.dumps(json_data, indent=2))

        return filepath

    def _build_memory_snapshot(self) -> Dict:
        """
        Build memory snapshot for session persistence.

        Extracts key topics, emotional markers, and conversation summary
        for use in contextual memory retrieval.

        Returns:
            Dict with memory metadata
        """
        snapshot = {
            "topics": [],
            "emotional_markers": {
                "frustration": 0,
                "excitement": 0,
                "urgency": 0
            },
            "key_queries": [],
            "blockers_mentioned": False,
            "task_completions": 0
        }

        # Emotional marker patterns
        frustration_markers = ["frustrated", "annoying", "stuck", "can't", "broken", "failing"]
        excitement_markers = ["excited", "amazing", "awesome", "great", "love", "perfect", "finally"]
        urgency_markers = ["urgent", "asap", "deadline", "due today", "must", "critical"]
        blocker_markers = ["blocked", "waiting on", "can't proceed", "need help", "stuck on"]
        completion_markers = ["done", "completed", "finished", "solved", "fixed", "worked"]

        for msg in self.session.history:
            content_lower = msg.content.lower()

            # Count emotional markers
            if any(m in content_lower for m in frustration_markers):
                snapshot["emotional_markers"]["frustration"] += 1
            if any(m in content_lower for m in excitement_markers):
                snapshot["emotional_markers"]["excitement"] += 1
            if any(m in content_lower for m in urgency_markers):
                snapshot["emotional_markers"]["urgency"] += 1

            # Track blockers
            if any(m in content_lower for m in blocker_markers):
                snapshot["blockers_mentioned"] = True

            # Count task completions (from assistant responses)
            if msg.role == "assistant" and any(m in content_lower for m in completion_markers):
                snapshot["task_completions"] += 1

            # Extract key user queries (first 100 chars)
            if msg.role == "user" and len(msg.content) > 20:
                query_preview = msg.content[:100]
                if query_preview not in snapshot["key_queries"]:
                    snapshot["key_queries"].append(query_preview)
                    if len(snapshot["key_queries"]) >= 5:
                        # Limit to 5 key queries
                        pass

        # Keep only top 5 queries
        snapshot["key_queries"] = snapshot["key_queries"][:5]

        return snapshot

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
