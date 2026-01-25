#!/usr/bin/env python3
"""
Inter-Session Messaging - Enables agents to communicate across sessions.

Inspired by clawdbot's sessions_list/sessions_history/sessions_send pattern.
Allows swarm agents to coordinate directly without going through the orchestrator.

Key Features:
    - Discover active sessions (sessions_list)
    - Fetch another session's transcript (sessions_history)
    - Send messages to another session with optional reply-back (sessions_send)
    - Message queue for async delivery
    - Session registry for discovery

Usage:
    from Tools.session_messenger import SessionMessenger

    messenger = SessionMessenger()

    # Discover active sessions
    sessions = messenger.list_sessions()

    # Send message to another session
    response = messenger.send(
        target_session_id="abc123",
        message="Can you validate the test results?",
        reply_back=True  # Wait for response
    )

    # Get session history
    history = messenger.get_history(session_id="abc123", limit=10)
"""

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from threading import Lock
import logging

logger = logging.getLogger(__name__)

# Session registry directory
SESSION_REGISTRY_DIR = Path("State/session_registry")
MESSAGE_QUEUE_DIR = Path("State/message_queue")


@dataclass
class SessionInfo:
    """Information about an active session."""
    session_id: str
    agent_type: str  # e.g., "coder", "tester", "orchestrator"
    agent_name: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_active: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "active"  # active, idle, busy, terminated
    capabilities: List[str] = field(default_factory=list)
    current_task: Optional[str] = None
    parent_session_id: Optional[str] = None  # For swarm hierarchy
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InterSessionMessage:
    """A message between sessions."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    from_session: str = ""
    to_session: str = ""
    content: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    message_type: str = "request"  # request, response, notification, broadcast
    reply_to: Optional[str] = None  # Message ID this is replying to
    reply_back: bool = False  # Whether sender expects a response
    ttl_seconds: int = 300  # Time to live (5 min default)
    delivered: bool = False
    read: bool = False
    response: Optional[str] = None


class SessionMessenger:
    """
    Manages inter-session communication for swarm coordination.

    Provides three core operations:
    1. list_sessions() - Discover active agents
    2. get_history() - Fetch another session's transcript
    3. send() - Message another session with optional reply-back
    """

    def __init__(self, session_id: Optional[str] = None):
        """
        Initialize messenger for a session.

        Args:
            session_id: This session's ID. If None, generates new one.
        """
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self._lock = Lock()
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure registry and queue directories exist."""
        SESSION_REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
        MESSAGE_QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # Session Registry Operations
    # =========================================================================

    def register_session(
        self,
        agent_type: str,
        agent_name: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        parent_session_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> SessionInfo:
        """
        Register this session in the registry for discovery.

        Args:
            agent_type: Type of agent (coder, tester, orchestrator, etc.)
            agent_name: Human-readable name
            capabilities: List of capabilities this agent has
            parent_session_id: Parent session if part of a swarm
            metadata: Additional metadata

        Returns:
            SessionInfo for this session
        """
        info = SessionInfo(
            session_id=self.session_id,
            agent_type=agent_type,
            agent_name=agent_name,
            capabilities=capabilities or [],
            parent_session_id=parent_session_id,
            metadata=metadata or {}
        )

        # Write to registry
        registry_file = SESSION_REGISTRY_DIR / f"{self.session_id}.json"
        with self._lock:
            registry_file.write_text(json.dumps(asdict(info), indent=2))

        logger.info(f"Registered session {self.session_id} as {agent_type}")
        return info

    def unregister_session(self):
        """Remove this session from the registry."""
        registry_file = SESSION_REGISTRY_DIR / f"{self.session_id}.json"
        with self._lock:
            if registry_file.exists():
                registry_file.unlink()
        logger.info(f"Unregistered session {self.session_id}")

    def update_status(self, status: str, current_task: Optional[str] = None):
        """
        Update this session's status.

        Args:
            status: New status (active, idle, busy, terminated)
            current_task: Description of current task (if busy)
        """
        registry_file = SESSION_REGISTRY_DIR / f"{self.session_id}.json"
        with self._lock:
            if registry_file.exists():
                info = json.loads(registry_file.read_text())
                info["status"] = status
                info["current_task"] = current_task
                info["last_active"] = datetime.now().isoformat()
                registry_file.write_text(json.dumps(info, indent=2))

    def heartbeat(self):
        """Update last_active timestamp (call periodically to stay in registry)."""
        self.update_status("active")

    # =========================================================================
    # Session Discovery (sessions_list)
    # =========================================================================

    def list_sessions(
        self,
        agent_type: Optional[str] = None,
        status: Optional[str] = None,
        capability: Optional[str] = None,
        exclude_self: bool = True
    ) -> List[SessionInfo]:
        """
        Discover active sessions.

        Args:
            agent_type: Filter by agent type
            status: Filter by status
            capability: Filter by capability
            exclude_self: Exclude this session from results

        Returns:
            List of matching SessionInfo objects
        """
        sessions = []
        stale_threshold = 60  # Seconds before session considered stale
        now = datetime.now()

        for registry_file in SESSION_REGISTRY_DIR.glob("*.json"):
            try:
                info_dict = json.loads(registry_file.read_text())
                info = SessionInfo(**info_dict)

                # Check staleness
                last_active = datetime.fromisoformat(info.last_active)
                if (now - last_active).total_seconds() > stale_threshold:
                    info.status = "stale"

                # Apply filters
                if exclude_self and info.session_id == self.session_id:
                    continue
                if agent_type and info.agent_type != agent_type:
                    continue
                if status and info.status != status:
                    continue
                if capability and capability not in info.capabilities:
                    continue

                sessions.append(info)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Invalid registry file {registry_file}: {e}")

        return sessions

    def find_session(
        self,
        agent_type: Optional[str] = None,
        capability: Optional[str] = None
    ) -> Optional[SessionInfo]:
        """
        Find a single session matching criteria.

        Useful for: "Find me a tester to validate this"

        Args:
            agent_type: Required agent type
            capability: Required capability

        Returns:
            SessionInfo if found, None otherwise
        """
        sessions = self.list_sessions(
            agent_type=agent_type,
            status="active",
            capability=capability
        )
        return sessions[0] if sessions else None

    # =========================================================================
    # Session History (sessions_history)
    # =========================================================================

    def get_history(
        self,
        session_id: str,
        limit: int = 20,
        since: Optional[str] = None
    ) -> List[Dict]:
        """
        Fetch another session's conversation history.

        Reads from the session's saved JSON files in History/Sessions.

        Args:
            session_id: Session to fetch history from
            limit: Maximum messages to return
            since: ISO timestamp to fetch messages after

        Returns:
            List of message dicts with role, content, timestamp
        """
        history_dir = Path("History/Sessions")
        if not history_dir.exists():
            return []

        # Find matching session files
        matching_files = sorted(
            history_dir.glob(f"*-{session_id}.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )

        if not matching_files:
            # Try partial match
            for f in history_dir.glob("*.json"):
                if session_id in f.stem:
                    matching_files = [f]
                    break

        if not matching_files:
            return []

        # Load most recent session file
        try:
            session_data = json.loads(matching_files[0].read_text())
            history = session_data.get("history", [])

            # Filter by since timestamp if provided
            if since:
                since_dt = datetime.fromisoformat(since)
                history = [
                    msg for msg in history
                    if datetime.fromisoformat(msg["timestamp"]) > since_dt
                ]

            # Apply limit
            return history[-limit:]
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Error reading session history: {e}")
            return []

    # =========================================================================
    # Inter-Session Messaging (sessions_send)
    # =========================================================================

    def send(
        self,
        target_session_id: str,
        message: str,
        message_type: str = "request",
        reply_back: bool = False,
        timeout: int = 30
    ) -> Optional[InterSessionMessage]:
        """
        Send a message to another session.

        Args:
            target_session_id: Session to send to
            message: Message content
            message_type: request, notification, or broadcast
            reply_back: Wait for response (ping-pong mode)
            timeout: Seconds to wait for reply (if reply_back=True)

        Returns:
            InterSessionMessage with response (if reply_back) or delivery status
        """
        msg = InterSessionMessage(
            from_session=self.session_id,
            to_session=target_session_id,
            content=message,
            message_type=message_type,
            reply_back=reply_back
        )

        # Write to target's message queue
        queue_file = MESSAGE_QUEUE_DIR / f"{target_session_id}_{msg.id}.json"
        queue_file.write_text(json.dumps(asdict(msg), indent=2))

        logger.info(f"Sent message {msg.id} to session {target_session_id}")

        if not reply_back:
            return msg

        # Wait for response
        response_file = MESSAGE_QUEUE_DIR / f"{self.session_id}_reply_{msg.id}.json"
        start_time = time.time()

        while time.time() - start_time < timeout:
            if response_file.exists():
                try:
                    response_data = json.loads(response_file.read_text())
                    response_file.unlink()  # Clean up
                    msg.response = response_data.get("content")
                    msg.delivered = True
                    return msg
                except json.JSONDecodeError:
                    pass
            time.sleep(0.5)

        logger.warning(f"Timeout waiting for reply to message {msg.id}")
        return msg

    def check_messages(self) -> List[InterSessionMessage]:
        """
        Check for incoming messages to this session.

        Returns:
            List of pending messages
        """
        messages = []

        for queue_file in MESSAGE_QUEUE_DIR.glob(f"{self.session_id}_*.json"):
            # Skip reply files
            if "_reply_" in queue_file.name:
                continue

            try:
                msg_data = json.loads(queue_file.read_text())
                msg = InterSessionMessage(**msg_data)
                msg.delivered = True
                msg.read = True
                messages.append(msg)

                # Update file to mark as read
                msg_data["delivered"] = True
                msg_data["read"] = True
                queue_file.write_text(json.dumps(msg_data, indent=2))
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Invalid message file {queue_file}: {e}")

        return messages

    def reply(
        self,
        original_message: InterSessionMessage,
        response_content: str
    ):
        """
        Reply to a message that requested reply_back.

        Args:
            original_message: The message being replied to
            response_content: Response content
        """
        if not original_message.reply_back:
            return

        response = InterSessionMessage(
            from_session=self.session_id,
            to_session=original_message.from_session,
            content=response_content,
            message_type="response",
            reply_to=original_message.id
        )

        # Write to sender's reply queue
        reply_file = MESSAGE_QUEUE_DIR / f"{original_message.from_session}_reply_{original_message.id}.json"
        reply_file.write_text(json.dumps(asdict(response), indent=2))

        logger.info(f"Sent reply to message {original_message.id}")

    def broadcast(
        self,
        message: str,
        agent_type: Optional[str] = None,
        capability: Optional[str] = None
    ) -> int:
        """
        Broadcast message to multiple sessions.

        Args:
            message: Message to broadcast
            agent_type: Filter recipients by type
            capability: Filter recipients by capability

        Returns:
            Number of sessions messaged
        """
        sessions = self.list_sessions(agent_type=agent_type, capability=capability)

        for session in sessions:
            self.send(
                target_session_id=session.session_id,
                message=message,
                message_type="broadcast",
                reply_back=False
            )

        return len(sessions)

    def cleanup_old_messages(self, max_age_seconds: int = 300):
        """
        Clean up expired messages from the queue.

        Args:
            max_age_seconds: Delete messages older than this (default: 5 min)
        """
        now = datetime.now()

        for queue_file in MESSAGE_QUEUE_DIR.glob("*.json"):
            try:
                msg_data = json.loads(queue_file.read_text())
                timestamp = datetime.fromisoformat(msg_data.get("timestamp", ""))

                if (now - timestamp).total_seconds() > max_age_seconds:
                    queue_file.unlink()
                    logger.debug(f"Cleaned up expired message {queue_file.name}")
            except (json.JSONDecodeError, ValueError):
                pass

    def cleanup_stale_sessions(self, max_age_seconds: int = 120):
        """
        Clean up stale session registrations.

        Args:
            max_age_seconds: Consider stale after this many seconds
        """
        now = datetime.now()

        for registry_file in SESSION_REGISTRY_DIR.glob("*.json"):
            try:
                info_data = json.loads(registry_file.read_text())
                last_active = datetime.fromisoformat(info_data.get("last_active", ""))

                if (now - last_active).total_seconds() > max_age_seconds:
                    registry_file.unlink()
                    logger.info(f"Cleaned up stale session {registry_file.stem}")
            except (json.JSONDecodeError, ValueError):
                pass


# Convenience function for quick session listing
def list_active_sessions() -> List[Dict]:
    """Quick function to list all active sessions."""
    messenger = SessionMessenger()
    sessions = messenger.list_sessions(exclude_self=False)
    return [asdict(s) for s in sessions]


# Convenience function for quick message sending
def send_to_session(target: str, message: str, reply_back: bool = False) -> Optional[str]:
    """
    Quick function to send a message to another session.

    Args:
        target: Target session ID or agent type (will find first match)
        message: Message to send
        reply_back: Wait for response

    Returns:
        Response content if reply_back, else message ID
    """
    messenger = SessionMessenger()

    # Check if target is a session ID or agent type
    if len(target) == 8 and target.replace("-", "").isalnum():
        target_id = target
    else:
        # Find session by agent type
        session = messenger.find_session(agent_type=target)
        if not session:
            return None
        target_id = session.session_id

    result = messenger.send(target_id, message, reply_back=reply_back)

    if reply_back:
        return result.response if result else None
    return result.id if result else None
