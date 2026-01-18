"""
Context Service - Context aggregation and prompt building

Extracted from ThanosOrchestrator for single-responsibility.
Handles loading context files and building system prompts.
"""

from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime

from .agent_service import Agent
from .command_service import Command


class ContextService:
    """Service for context aggregation and prompt building.

    Usage:
        service = ContextService(base_dir=Path("."))
        service.load_context(Path("Context"))
        prompt = service.build_system_prompt(agent=agent_obj)
    """

    def __init__(
        self,
        base_dir: Path,
        state_reader: Optional[Any] = None,
        state_store: Optional[Any] = None,
    ):
        """Initialize context service.

        Args:
            base_dir: Base directory for Thanos files
            state_reader: Optional StateReader instance
            state_store: Optional SQLiteStateStore instance
        """
        self.base_dir = base_dir
        self.state_reader = state_reader
        self.state_store = state_store
        self._context: Dict[str, str] = {}

    def load_context(self, context_dir: Path) -> Dict[str, str]:
        """Load context files from directory.

        Args:
            context_dir: Path to the Context directory

        Returns:
            Dictionary mapping context names to content
        """
        self._context.clear()

        if not context_dir.exists():
            return self._context

        for file in context_dir.glob("*.md"):
            try:
                self._context[file.stem] = file.read_text(encoding='utf-8')
            except Exception as e:
                print(f"Warning: Failed to load context {file}: {e}")

        return self._context

    def get_context(self, name: str) -> Optional[str]:
        """Get a context file by name.

        Args:
            name: Context file name (without extension)

        Returns:
            Context content or None if not found
        """
        return self._context.get(name)

    def build_time_context(self) -> str:
        """Build temporal context string.

        Returns:
            Formatted time context with current time and elapsed time
        """
        now = datetime.now()
        parts = [f"## Temporal Context\nCurrent time: {now.strftime('%Y-%m-%d %H:%M')}"]

        # Get elapsed time since last interaction
        if self.state_reader:
            elapsed = self.state_reader.calculate_elapsed_time()
            readable_elapsed = self.state_reader.format_elapsed_time(elapsed)
            parts.append(f"Last interaction: {readable_elapsed}")

        return "\n".join(parts)

    def build_system_prompt(
        self,
        agent: Optional[Agent] = None,
        command: Optional[Command] = None,
        include_context: bool = True,
        max_length: int = 6000,
    ) -> str:
        """Build system prompt for API call.

        Args:
            agent: Optional Agent to include personality for
            command: Optional Command to include workflow for
            include_context: Whether to include context files
            max_length: Maximum prompt length

        Returns:
            Complete system prompt string
        """
        parts = []

        # Base identity
        parts.append(
            """You are The Operator.
You are stoic and direct.
You enforce accountability.
You turn vague goals into next actions.
You maintain a compact daily plan and a scoreboard.
"""
        )

        # Add temporal context
        if include_context:
            parts.append(self.build_time_context())

        # Add core context
        if include_context and "CORE" in self._context:
            parts.append("\n## About Jeremy\n" + self._context["CORE"])

        # Add agent personality
        if agent:
            parts.append(f"\n## Current Role: {agent.role}")
            parts.append(f"Voice: {agent.voice}")
            parts.append(f"\n{agent.content}")

        # Add command context
        if command:
            parts.append(f"\n## Current Command: {command.name}")
            parts.append(f"{command.description}")
            parts.append(f"\n### Workflow\n{command.workflow}")

        # Add current state
        state_file = self.base_dir / "State" / "Today.md"
        if state_file.exists():
            try:
                today_state = state_file.read_text(encoding='utf-8')
                parts.append(f"\n## Today's State\n{today_state[:2000]}")
            except Exception:
                pass

        # Add stored summaries
        if include_context and self.state_store:
            workos_summary = self.state_store.get_state("workos_summary")
            if workos_summary:
                parts.append("\n## WorkOS Summary")
                parts.append(workos_summary)

            calendar_summary = self.state_store.get_state("calendar_summary")
            if calendar_summary:
                parts.append("\n## Calendar Summary")
                parts.append(calendar_summary)

            recent_tool_summaries = self.state_store.get_recent_summaries(limit=3)
            if recent_tool_summaries:
                parts.append("\n## Recent Tool Summaries")
                for entry in recent_tool_summaries:
                    parts.append(
                        f"{entry.get('tool_name')} id {entry.get('summary_id')} {entry.get('summary_text')}"
                    )

        prompt = "\n\n".join(parts)
        if len(prompt) > max_length:
            prompt = prompt[:max_length]
        return prompt

    def get_all_context(self) -> Dict[str, str]:
        """Get all loaded context files.

        Returns:
            Dictionary of all context content
        """
        return self._context.copy()
