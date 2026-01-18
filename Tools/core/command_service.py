"""
Command Service - Command registry and lookup

Extracted from ThanosOrchestrator for single-responsibility.
Handles loading command definitions from markdown files and command lookup.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Command:
    """Represents a Thanos command/skill."""

    name: str
    description: str
    parameters: List[str]
    workflow: str
    content: str
    file_path: str

    @classmethod
    def from_markdown(cls, file_path: Path) -> "Command":
        """Parse a command definition from markdown file."""
        content = file_path.read_text(encoding='utf-8')

        # Extract command name from first heading
        name_match = re.search(r"^#\s+(/\w+:\w+)", content, re.MULTILINE)
        name = name_match.group(1) if name_match else file_path.stem

        # Extract description (first paragraph after heading)
        desc_match = re.search(r"^#[^\n]+\n+([^\n#]+)", content, re.MULTILINE)
        description = desc_match.group(1).strip() if desc_match else ""

        # Extract parameters section
        params = []
        params_match = re.search(
            r"## Parameters\n(.*?)(?=\n##|\Z)", content, re.DOTALL
        )
        if params_match:
            for line in params_match.group(1).split("\n"):
                if line.strip().startswith("-"):
                    params.append(line.strip()[1:].strip())

        # Extract workflow section
        workflow_match = re.search(
            r"## Workflow\n(.*?)(?=\n##|\Z)", content, re.DOTALL
        )
        workflow = workflow_match.group(1).strip() if workflow_match else ""

        return cls(
            name=name,
            description=description,
            parameters=params,
            workflow=workflow,
            content=content,
            file_path=str(file_path),
        )


class CommandService:
    """Service for loading and managing commands.

    Usage:
        service = CommandService()
        service.load_commands(Path("commands"))
        cmd = service.find_command("pa:daily")
    """

    def __init__(self):
        self._commands: Dict[str, Command] = {}

    def load_commands(self, commands_dir: Path) -> Dict[str, Command]:
        """Load all command definitions from directory.

        Args:
            commands_dir: Path to the commands directory

        Returns:
            Dictionary mapping command names to Command instances
        """
        self._commands.clear()

        if not commands_dir.exists():
            return self._commands

        for subdir in commands_dir.iterdir():
            if subdir.is_dir():
                for file in subdir.glob("*.md"):
                    if file.name != "README.md":
                        try:
                            cmd = Command.from_markdown(file)
                            # Store by multiple keys for flexible lookup
                            self._commands[cmd.name] = cmd
                            self._commands[file.stem] = cmd
                            # Also store as prefix:name
                            prefix = subdir.name
                            self._commands[f"{prefix}:{file.stem}"] = cmd
                        except Exception as e:
                            print(f"Warning: Failed to load command {file}: {e}")

        return self._commands

    def find_command(self, query: str) -> Optional[Command]:
        """Find a command by name or pattern.

        Args:
            query: Command name, prefix:name, or search term

        Returns:
            Command instance or None if not found
        """
        # Direct lookup
        if query in self._commands:
            return self._commands[query]

        # Try with common prefixes
        for prefix in ["pa", "sc"]:
            key = f"{prefix}:{query}"
            if key in self._commands:
                return self._commands[key]

        # Fuzzy match
        query_lower = query.lower()
        for name, cmd in self._commands.items():
            if query_lower in name.lower():
                return cmd

        return None

    def list_commands(self) -> List[str]:
        """List all available commands with descriptions.

        Returns:
            Sorted list of command descriptions
        """
        seen = set()
        result = []
        for name, cmd in self._commands.items():
            if cmd.name not in seen:
                seen.add(cmd.name)
                result.append(f"{cmd.name} - {cmd.description[:50]}...")
        return sorted(result)

    def get_command(self, name: str) -> Optional[Command]:
        """Get a command by exact name.

        Args:
            name: Exact command name

        Returns:
            Command instance or None if not found
        """
        return self._commands.get(name)

    def get_all_commands(self) -> Dict[str, Command]:
        """Get all loaded commands.

        Returns:
            Dictionary of all commands
        """
        return self._commands.copy()
