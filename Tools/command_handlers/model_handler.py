#!/usr/bin/env python3
"""
ModelHandler - Handles AI model management commands

Manages model switching and display operations in Thanos Interactive Mode.
Provides commands for viewing available models and switching between them.

Commands:
    /model [name]   - Switch AI model or show current model and options
"""

from Tools.command_handlers.base import BaseHandler, CommandResult, Colors


class ModelHandler(BaseHandler):
    """
    Handler for AI model management commands.

    Provides functionality for:
    - Switching between AI models (opus, sonnet, haiku)
    - Displaying current model and available options
    - Providing cost information for each model
    - Getting current model name for API calls
    """

    def __init__(self, orchestrator, session_manager, context_manager, state_reader, thanos_dir, **kwargs):
        """
        Initialize ModelHandler with dependencies.

        Args:
            orchestrator: ThanosOrchestrator for agent info
            session_manager: SessionManager for session operations
            context_manager: ContextManager for context operations
            state_reader: StateReader for state operations
            thanos_dir: Path to Thanos root directory
            **kwargs: Additional arguments passed to BaseHandler
        """
        super().__init__(orchestrator, session_manager, context_manager, state_reader, thanos_dir, **kwargs)

        # Model state tracking
        self.current_model = None  # None = use default from config

        # Available models (from config/api.json)
        self._available_models = {
            "opus": "claude-opus-4-5-20251101",
            "sonnet": "claude-sonnet-4-20250514",
            "haiku": "claude-3-5-haiku-20241022",
        }
        self._default_model = "opus"

    def handle_model(self, args: str) -> CommandResult:
        """
        Handle /model command - Switch AI model or show current.

        Without arguments, displays the current model and all available options
        with pricing information. With a model name argument, switches to that
        model if it exists.

        Args:
            args: Model name to switch to (empty to show current and options)

        Returns:
            CommandResult with action and success status

        Examples:
            /model         -> Show current model and available options
            /model opus    -> Switch to Claude Opus 4.5
            /model sonnet  -> Switch to Claude Sonnet 4
            /model haiku   -> Switch to Claude Haiku 3.5
        """
        if not args:
            # Show current model and available options
            current = self.current_model or self._default_model
            print(f"\n{Colors.CYAN}AI Model:{Colors.RESET}")
            print(f"  Current: {current} ({self._available_models.get(current, 'unknown')})")
            print(f"\n{Colors.CYAN}Available Models:{Colors.RESET}")
            for alias, full_name in self._available_models.items():
                marker = "→" if alias == current else " "
                # Add cost hints
                if alias == "opus":
                    cost = "$15/$75 per 1M tokens (most capable)"
                elif alias == "sonnet":
                    cost = "$3/$15 per 1M tokens (balanced)"
                else:
                    cost = "$0.25/$1.25 per 1M tokens (fastest)"
                print(f"  {marker} {alias:8} {full_name}")
                print(f"           {Colors.DIM}{cost}{Colors.RESET}")
            print(f"\n{Colors.DIM}Usage: /model <opus|sonnet|haiku>{Colors.RESET}\n")
            return CommandResult()

        model_name = args.lower().strip()
        if model_name in self._available_models:
            old_model = self.current_model or self._default_model
            self.current_model = model_name
            print(f"{Colors.CYAN}Model switched:{Colors.RESET} {old_model} → {model_name}")
            print(f"{Colors.DIM}Using: {self._available_models[model_name]}{Colors.RESET}")
            return CommandResult()
        else:
            print(f"{Colors.DIM}Unknown model: {model_name}{Colors.RESET}")
            print(f"Available: {', '.join(self._available_models.keys())}")
            return CommandResult(success=False)

    def get_current_model(self) -> str:
        """
        Get the current model full name for API calls.

        Returns the full model identifier string used in API requests,
        not the short alias. Falls back to default model if none is set.

        Returns:
            Full model name (e.g., "claude-opus-4-5-20251101")

        Examples:
            >>> handler.current_model = "opus"
            >>> handler.get_current_model()
            "claude-opus-4-5-20251101"

            >>> handler.current_model = None
            >>> handler.get_current_model()
            "claude-opus-4-5-20251101"  # Returns default
        """
        model_alias = self.current_model or self._default_model
        return self._available_models.get(model_alias, self._available_models[self._default_model])
