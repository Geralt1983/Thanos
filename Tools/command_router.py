#!/usr/bin/env python3
"""
CommandRouter - Routes and executes slash commands for Thanos Interactive Mode

Single Responsibility: Command parsing and delegation
"""

from pathlib import Path
from typing import Callable

# Import handler modules
from Tools.command_handlers import (
    Colors,
    CommandAction,
    CommandResult,
    AgentHandler,
    SessionHandler,
    StateHandler,
    MemoryHandler,
    AnalyticsHandler,
    ModelHandler,
    CoreHandler,
)

# Import routing modules
from Tools.routing import PersonaRouter, CommandRegistry


class CommandRouter:
    """Routes and executes slash commands"""

    def __init__(
        self,
        orchestrator,  # ThanosOrchestrator
        session_manager,  # SessionManager
        context_manager,  # ContextManager
        state_reader,  # StateReader
        thanos_dir: Path,
    ):
        """
        Initialize with injected dependencies.

        Args:
            orchestrator: ThanosOrchestrator for /run command and agent info
            session_manager: SessionManager for history operations
            context_manager: ContextManager for context usage info
            state_reader: StateReader for state and commitments
            thanos_dir: Path to Thanos root directory
        """
        self.orchestrator = orchestrator
        self.session = session_manager
        self.context_mgr = context_manager
        self.state_reader = state_reader
        self.thanos_dir = thanos_dir
        self.current_agent = "ops"  # Track current agent
        self.current_model = None  # None = use default from config

        # Available models (from config/api.json)
        self._available_models = {
            "opus": "claude-opus-4-5-20251101",
            "sonnet": "claude-sonnet-4-20250514",
            "haiku": "claude-3-5-haiku-20241022",
        }
        self._default_model = "opus"

        # Initialize routing modules
        self.persona_router = PersonaRouter(orchestrator, current_agent=self.current_agent)
        self.registry = CommandRegistry()

        # Initialize handler classes with dependency injection
        # Create a getter for current_agent to allow handlers to access it
        current_agent_getter = lambda: self.current_agent

        self.agent_handler = AgentHandler(
            orchestrator, session_manager, context_manager, state_reader, thanos_dir,
            current_agent_getter=current_agent_getter
        )
        self.session_handler = SessionHandler(
            orchestrator, session_manager, context_manager, state_reader, thanos_dir,
            current_agent_getter=current_agent_getter
        )
        self.state_handler = StateHandler(
            orchestrator, session_manager, context_manager, state_reader, thanos_dir,
            current_agent_getter=current_agent_getter
        )
        self.memory_handler = MemoryHandler(
            orchestrator, session_manager, context_manager, state_reader, thanos_dir,
            current_agent_getter=current_agent_getter
        )
        self.analytics_handler = AnalyticsHandler(
            orchestrator, session_manager, context_manager, state_reader, thanos_dir,
            current_agent_getter=current_agent_getter
        )
        self.model_handler = ModelHandler(
            orchestrator, session_manager, context_manager, state_reader, thanos_dir,
            current_agent_getter=current_agent_getter
        )
        self.core_handler = CoreHandler(
            orchestrator, session_manager, context_manager, state_reader, thanos_dir,
            current_agent_getter=current_agent_getter
        )

        # Register commands with the registry
        self._register_commands()

    def detect_agent(self, message: str, auto_switch: bool = True):
        """
        Detect the appropriate agent for a message based on trigger patterns.

        Args:
            message: User message to analyze
            auto_switch: If True, switch current_agent when match found

        Returns:
            Agent name if a better match found, None if current agent is appropriate
        """
        # Delegate to PersonaRouter
        detected = self.persona_router.detect_agent(message, auto_switch)

        # Sync agent state if switching occurred
        if detected and auto_switch:
            self.current_agent = self.persona_router.current_agent

        return detected

    def _wrap_agent_command(self, args: str) -> CommandResult:
        """Wrapper for agent command that syncs state after handler call"""
        result = self.agent_handler.handle_agent(args)
        # Sync current agent state from handler to router and persona router
        self.current_agent = self.agent_handler.get_current_agent()
        self.persona_router.set_current_agent(self.current_agent)
        return result

    def _wrap_resume_command(self, args: str) -> CommandResult:
        """Wrapper for resume command that syncs state after handler call"""
        result = self.session_handler.handle_resume(args)
        if result.success:
            # Sync current agent from restored session
            self.current_agent = self.session.session.agent
            self.persona_router.set_current_agent(self.current_agent)
        return result

    def _wrap_switch_command(self, args: str) -> CommandResult:
        """Wrapper for switch command that syncs state after handler call"""
        result = self.session_handler.handle_switch(args)
        if result.success:
            # Sync current agent from switched branch
            self.current_agent = self.session.session.agent
            self.persona_router.set_current_agent(self.current_agent)
        return result

    def _register_commands(self):
        """Register all available commands with their handlers"""
        # Register commands with the CommandRegistry
        # Map commands to handler methods (with wrappers for state sync when needed)
        self.registry.register_batch({
            # Agent commands (wrapped for state sync)
            "agent": (self._wrap_agent_command, "Switch agent", ["name"]),
            "a": (self._wrap_agent_command, "Switch agent (alias)", ["name"]),
            "agents": (self.agent_handler.handle_list_agents, "List agents", []),

            # Session commands (resume and switch wrapped for state sync)
            "clear": (self.session_handler.handle_clear, "Clear history", []),
            "save": (self.session_handler.handle_save, "Save session", []),
            "sessions": (self.session_handler.handle_sessions, "List saved sessions", []),
            "resume": (self._wrap_resume_command, "Resume a session", ["session_id"]),
            "r": (self._wrap_resume_command, "Resume session (alias)", ["session_id"]),
            "branch": (self.session_handler.handle_branch, "Create conversation branch", ["name"]),
            "branches": (self.session_handler.handle_branches, "List branches", []),
            "switch": (self._wrap_switch_command, "Switch to branch", ["branch"]),

            # State commands
            "usage": (self.state_handler.handle_usage, "Show token stats", []),
            "context": (self.state_handler.handle_context, "Show context usage", []),
            "state": (self.state_handler.handle_state, "Show current state", []),
            "s": (self.state_handler.handle_state, "Show current state (alias)", []),
            "commitments": (self.state_handler.handle_commitments, "Show commitments", []),
            "c": (self.state_handler.handle_commitments, "Show commitments (alias)", []),

            # Memory commands
            "recall": (self.memory_handler.handle_recall, "Search past sessions", ["query"]),
            "remember": (self.memory_handler.handle_remember, "Store a memory in MemOS", ["content"]),
            "memory": (self.memory_handler.handle_memory, "Memory system info", []),

            # Analytics commands
            "patterns": (self.analytics_handler.handle_patterns, "Show conversation patterns", []),

            # Model commands
            "model": (self.model_handler.handle_model, "Switch AI model", ["name"]),
            "m": (self.model_handler.handle_model, "Switch model (alias)", ["name"]),

            # Core commands
            "help": (self.core_handler.handle_help, "Show help", []),
            "h": (self.core_handler.handle_help, "Show help (alias)", []),
            "quit": (self.core_handler.handle_quit, "Exit", []),
            "q": (self.core_handler.handle_quit, "Exit (alias)", []),
            "exit": (self.core_handler.handle_quit, "Exit (alias)", []),
            "run": (self.core_handler.handle_run, "Run Thanos command", ["cmd"]),
        })

    def route_command(self, input_str: str) -> CommandResult:
        """
        Route and execute a command.

        Args:
            input_str: Command string (e.g., "/state", "/agent ops")

        Returns:
            CommandResult with action and message
        """
        parts = input_str.split(maxsplit=1)
        command = parts[0][1:].lower()  # Remove leading '/'
        args = parts[1] if len(parts) > 1 else ""

        # Delegate to CommandRegistry for command lookup
        handler_info = self.registry.get(command)
        if handler_info:
            handler, _, _ = handler_info
            return handler(args)
        else:
            print(
                f"{Colors.DIM}Unknown command: /{command}. "
                f"Type /help for available commands.{Colors.RESET}"
            )
            return CommandResult(action=CommandAction.CONTINUE, success=False)

    def get_available_commands(self) -> list[tuple[str, str, list[str]]]:
        """Get list of available commands for help text"""
        # Delegate to CommandRegistry
        return self.registry.get_available_commands()

    def get_current_model(self) -> str:
        """Get the current model full name for API calls (delegates to ModelHandler)."""
        return self.model_handler.get_current_model()
