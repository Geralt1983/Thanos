"""
Service Interfaces for Thanos Core

Defines Protocol classes (structural subtyping) for all core services.
These interfaces enable dependency injection and easier testing.
"""

from typing import Protocol, Optional, Dict, List, Any, Union
from datetime import datetime
from pathlib import Path


class IAgentService(Protocol):
    """Interface for agent loading and management."""

    def load_agents(self, agents_dir: Path) -> Dict[str, Any]:
        """Load all agent definitions from directory."""
        ...

    def get_agent(self, name: str) -> Optional[Any]:
        """Get an agent by name."""
        ...

    def list_agents(self) -> List[str]:
        """List all available agents."""
        ...


class ICommandService(Protocol):
    """Interface for command registry and lookup."""

    def load_commands(self, commands_dir: Path) -> Dict[str, Any]:
        """Load all command definitions from directory."""
        ...

    def find_command(self, query: str) -> Optional[Any]:
        """Find a command by name or pattern."""
        ...

    def list_commands(self) -> List[str]:
        """List all available commands."""
        ...


class IContextService(Protocol):
    """Interface for context aggregation and prompt building."""

    def load_context(self, context_dir: Path) -> Dict[str, str]:
        """Load context files from directory."""
        ...

    def build_time_context(self) -> str:
        """Build temporal context string."""
        ...

    def build_system_prompt(
        self,
        agent: Optional[Any] = None,
        command: Optional[Any] = None,
        include_context: bool = True,
    ) -> str:
        """Build system prompt for API call."""
        ...


class IIntentService(Protocol):
    """Interface for natural language intent matching."""

    def match_intent(self, message: str) -> Dict[str, float]:
        """Match message to agent scores."""
        ...

    def find_agent(self, message: str) -> Optional[Any]:
        """Find the most appropriate agent for a message."""
        ...


class ICalendarService(Protocol):
    """Interface for calendar and external service integration."""

    async def get_calendar_context(
        self, force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get calendar context with caching."""
        ...

    async def check_time_conflict(
        self, start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """Check if a time slot conflicts with calendar events."""
        ...

    async def get_workos_context(
        self, force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get WorkOS context with caching."""
        ...
