#!/usr/bin/env python3
"""
CommandRegistry - Command registration and lookup system

Manages command registration, lookup, and metadata for Thanos Interactive Mode.
Provides a centralized registry for all slash commands and their handlers.

Single Responsibility: Command registration and lookup
"""

from typing import Callable, Optional


class CommandRegistry:
    """
    Manages registration and lookup of slash commands.

    The CommandRegistry maintains a centralized mapping of command names to
    their handler functions, descriptions, and expected arguments. It supports
    command aliases and provides utilities for command introspection.

    Example:
        registry = CommandRegistry()
        registry.register("help", handler.handle_help, "Show help", [])
        registry.register("h", handler.handle_help, "Show help (alias)", [])

        handler_info = registry.get("help")
        if handler_info:
            handler, description, args = handler_info
            result = handler()
    """

    def __init__(self):
        """Initialize an empty command registry."""
        # Command registry: {command_name: (handler_function, description, arg_names)}
        self._commands: dict[str, tuple[Callable, str, list[str]]] = {}

    def register(
        self,
        command: str,
        handler: Callable,
        description: str,
        args: Optional[list[str]] = None,
    ) -> None:
        """
        Register a single command with its handler.

        Args:
            command: Command name (without leading slash, e.g., "help", "state")
            handler: Function to handle the command execution
            description: Human-readable description for help text
            args: List of argument names expected by the handler (default: [])

        Example:
            >>> registry.register("help", self._handle_help, "Show help", [])
            >>> registry.register("agent", self._handle_agent, "Switch agent", ["name"])
        """
        if args is None:
            args = []
        self._commands[command.lower()] = (handler, description, args)

    def register_batch(self, commands: dict[str, tuple[Callable, str, list[str]]]):
        """
        Register multiple commands at once.

        Args:
            commands: Dictionary mapping command names to (handler, description, args) tuples

        Example:
            >>> registry.register_batch({
            ...     "help": (handler.help, "Show help", []),
            ...     "state": (handler.state, "Show state", []),
            ...     "s": (handler.state, "Show state (alias)", []),
            ... })
        """
        for command, (handler, description, args) in commands.items():
            self.register(command, handler, description, args)

    def get(self, command: str) -> Optional[tuple[Callable, str, list[str]]]:
        """
        Get handler information for a command.

        Args:
            command: Command name (without leading slash)

        Returns:
            Tuple of (handler_function, description, arg_names) if command exists,
            None otherwise

        Example:
            >>> handler_info = registry.get("help")
            >>> if handler_info:
            ...     handler, desc, args = handler_info
            ...     result = handler()
        """
        return self._commands.get(command.lower())

    def has_command(self, command: str) -> bool:
        """
        Check if a command exists in the registry.

        Args:
            command: Command name (without leading slash)

        Returns:
            True if command is registered, False otherwise

        Example:
            >>> if registry.has_command("help"):
            ...     print("Help command available")
        """
        return command.lower() in self._commands

    def get_all_commands(self) -> dict[str, tuple[Callable, str, list[str]]]:
        """
        Get all registered commands.

        Returns:
            Dictionary mapping command names to (handler, description, args) tuples

        Note:
            This includes aliases. Use get_available_commands() to filter aliases.
        """
        return self._commands.copy()

    def get_available_commands(self) -> list[tuple[str, str, list[str]]]:
        """
        Get list of available commands, filtering out aliases.

        Returns unique commands only (based on handler function), excluding
        aliases from the list. Useful for generating help text without duplication.

        Returns:
            List of (command_name, description, arg_names) tuples, sorted by name

        Example:
            >>> for cmd, desc, args in registry.get_available_commands():
            ...     print(f"/{cmd} - {desc}")
        """
        unique_commands = []
        seen_handlers = set()

        for cmd, (handler, desc, args) in self._commands.items():
            if handler not in seen_handlers:
                unique_commands.append((cmd, desc, args))
                seen_handlers.add(handler)

        return sorted(unique_commands)

    def get_command_names(self) -> list[str]:
        """
        Get list of all registered command names (including aliases).

        Returns:
            Sorted list of command names

        Example:
            >>> registry.get_command_names()
            ['agent', 'clear', 'help', 'h', 'quit', 'q', 'state', 's']
        """
        return sorted(self._commands.keys())

    def unregister(self, command: str) -> bool:
        """
        Remove a command from the registry.

        Args:
            command: Command name to remove

        Returns:
            True if command was removed, False if command didn't exist

        Example:
            >>> registry.unregister("deprecated_cmd")
            True
        """
        command_lower = command.lower()
        if command_lower in self._commands:
            del self._commands[command_lower]
            return True
        return False

    def clear(self):
        """
        Clear all registered commands.

        Useful for testing or complete registry resets.
        """
        self._commands.clear()

    def get_aliases(self, handler: Callable) -> list[str]:
        """
        Get all command names (aliases) that map to the same handler.

        Args:
            handler: Handler function to find aliases for

        Returns:
            List of command names that use this handler

        Example:
            >>> registry.get_aliases(handler.handle_help)
            ['help', 'h', '?']
        """
        aliases = []
        for cmd, (cmd_handler, _, _) in self._commands.items():
            if cmd_handler is handler:
                aliases.append(cmd)
        return sorted(aliases)
