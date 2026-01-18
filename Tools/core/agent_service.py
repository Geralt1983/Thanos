"""
Agent Service - Agent loading and management

Extracted from ThanosOrchestrator for single-responsibility.
Handles loading agent definitions from markdown files and agent lookup.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Agent:
    """Represents a Thanos agent with personality and triggers."""

    name: str
    role: str
    voice: str
    triggers: List[str]
    content: str
    file_path: str

    @classmethod
    def from_markdown(cls, file_path: Path) -> "Agent":
        """Parse an agent definition from markdown file."""
        content = file_path.read_text(encoding='utf-8')

        # Extract frontmatter
        frontmatter = {}
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        key = key.strip()
                        value = value.strip()
                        # Parse list values
                        if value.startswith("["):
                            value = json.loads(value.replace("'", '"'))
                        frontmatter[key] = value
                content = parts[2]

        return cls(
            name=frontmatter.get("name", file_path.stem),
            role=frontmatter.get("role", "Assistant"),
            voice=frontmatter.get("voice", "helpful"),
            triggers=frontmatter.get("triggers", []),
            content=content.strip(),
            file_path=str(file_path),
        )


class AgentService:
    """Service for loading and managing agents.

    Usage:
        service = AgentService()
        service.load_agents(Path("Agents"))
        agent = service.get_agent("ops")
    """

    def __init__(self):
        self._agents: Dict[str, Agent] = {}

    def load_agents(self, agents_dir: Path) -> Dict[str, Agent]:
        """Load all agent definitions from directory.

        Args:
            agents_dir: Path to the Agents directory

        Returns:
            Dictionary mapping agent names to Agent instances
        """
        self._agents.clear()

        if not agents_dir.exists():
            return self._agents

        for file in agents_dir.glob("*.md"):
            if file.name != "AgentFactory.md":
                try:
                    agent = Agent.from_markdown(file)
                    self._agents[agent.name.lower()] = agent
                except Exception as e:
                    print(f"Warning: Failed to load agent {file}: {e}")

        return self._agents

    def get_agent(self, name: str) -> Optional[Agent]:
        """Get an agent by name.

        Args:
            name: Agent name (case-insensitive)

        Returns:
            Agent instance or None if not found
        """
        return self._agents.get(name.lower())

    def list_agents(self) -> List[str]:
        """List all available agents.

        Returns:
            List of agent descriptions in format "name (role)"
        """
        return [f"{a.name} ({a.role})" for a in self._agents.values()]

    def get_all_agents(self) -> Dict[str, Agent]:
        """Get all loaded agents.

        Returns:
            Dictionary of all agents
        """
        return self._agents.copy()

    def get_agent_triggers(self) -> Dict[str, List[str]]:
        """Get triggers for all agents.

        Returns:
            Dictionary mapping agent names to their trigger lists
        """
        return {
            name: agent.triggers
            for name, agent in self._agents.items()
            if agent.triggers
        }
