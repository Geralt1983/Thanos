#!/usr/bin/env python3
"""
Base handler for command execution in Thanos Interactive Mode.

This module provides the foundational infrastructure for all command handlers
in the Thanos command routing system. It defines shared utilities, result types,
and the base class that all specific handlers inherit from.

Classes:
    Colors: ANSI color codes for formatted terminal output
    CommandAction: Enum defining post-command actions (CONTINUE, QUIT)
    CommandResult: Dataclass for command execution results
    BaseHandler: Base class providing dependency injection and shared utilities

Architecture:
    All handler classes (AgentHandler, SessionHandler, etc.) inherit from BaseHandler
    to gain access to shared dependencies and utilities. This promotes code reuse
    and ensures consistent dependency injection across all handlers.

    Memory operations are routed through memory_router.py, which handles
    backend selection and fallbacks automatically.

Example:
    class MyHandler(BaseHandler):
        def handle_command(self, args: str) -> CommandResult:
            # Access shared utilities
            agent = self._get_current_agent()

            # Return formatted result
            return CommandResult(success=True, message="Done!")

See Also:
    - Tools.command_handlers.agent_handler: Agent management commands
    - Tools.command_handlers.session_handler: Session management commands
    - Tools.routing.command_registry: Command registration system
    - Tools.memory_router: Unified memory routing layer
"""

import asyncio
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for formatted terminal output"""

    PURPLE = "\033[35m"
    CYAN = "\033[36m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    GREEN = "\033[32m"
    DIM = "\033[2m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


class CommandAction(Enum):
    """Action to take after command execution"""

    CONTINUE = "continue"
    QUIT = "quit"


@dataclass
class CommandResult:
    """Result from command execution"""

    action: CommandAction = CommandAction.CONTINUE
    message: Optional[str] = None
    success: bool = True


class BaseHandler:
    """
    Base class for all command handlers.

    Provides shared utilities and dependency access for command handlers.
    Each specific handler (AgentHandler, SessionHandler, etc.) inherits from this.

    Memory operations should use Tools.memory_router instead of direct service access.
    """

    def __init__(
        self,
        orchestrator,  # ThanosOrchestrator
        session_manager,  # SessionManager
        context_manager,  # ContextManager
        state_reader,  # StateReader
        thanos_dir: Path,
        current_agent_getter: Optional[Callable[[], str]] = None,
    ):
        """
        Initialize with injected dependencies.

        Args:
            orchestrator: ThanosOrchestrator for agent info and orchestration
            session_manager: SessionManager for history operations
            context_manager: ContextManager for context usage info
            state_reader: StateReader for state and commitments
            thanos_dir: Path to Thanos root directory
            current_agent_getter: Optional callable to get current agent name
        """
        self.orchestrator = orchestrator
        self.session = session_manager
        self.context_mgr = context_manager
        self.state_reader = state_reader
        self.thanos_dir = thanos_dir
        self._current_agent_getter = current_agent_getter

    def _get_current_agent(self) -> str:
        """
        Get the current agent name.

        Returns:
            Name of the currently active agent, or "ops" as default
        """
        if self._current_agent_getter:
            return self._current_agent_getter()
        return "ops"  # Default fallback

    def _run_async(self, coro):
        """
        Run async coroutine from sync context.

        Args:
            coro: Coroutine to execute

        Returns:
            Result from coroutine execution, or None if error
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a new loop for nested async
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(coro)
        except Exception:
            return None
