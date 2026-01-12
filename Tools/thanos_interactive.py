#!/usr/bin/env python3
"""
ThanosInteractive - Interactive mode for Thanos with real-time token/cost display.

This module provides an interactive command-line interface for conversing with
Thanos agents. It displays real-time token usage and cost estimates in the prompt,
allowing users to monitor their API spend during sessions.

Key Features:
    - Interactive conversation loop with agent responses
    - Real-time token count and cost display in prompt
    - Slash command support via CommandRouter
    - Session management and persistence
    - Agent switching and context tracking
    - Graceful exit handling (Ctrl+C, Ctrl+D)

Key Classes:
    ThanosInteractive: Main interactive mode controller

Usage:
    from Tools.thanos_interactive import ThanosInteractive

    # Initialize with orchestrator
    interactive = ThanosInteractive(orchestrator)

    # Start interactive session
    interactive.run()

Example Session:
    Welcome to Thanos Interactive Mode
    Type /help for commands, /quit to exit

    (0 | $0.00) Thanos> Hello
    [Agent responds...]

    (1.2K | $0.04) Thanos> /usage
    [Shows detailed usage stats...]

    (1.2K | $0.04) Thanos> /quit
    Goodbye!

See Also:
    - Tools.prompt_formatter: Prompt formatting with token/cost display
    - Tools.command_router: Slash command routing and execution
    - Tools.session_manager: Session state and history management
"""

import sys
from pathlib import Path
from typing import Optional

from Tools.command_router import CommandRouter, CommandAction, Colors
from Tools.context_manager import ContextManager
from Tools.prompt_formatter import PromptFormatter
from Tools.session_manager import SessionManager
from Tools.state_reader import StateReader


class ThanosInteractive:
    """
    Interactive mode controller for Thanos conversations.

    Manages the interactive session loop, integrating prompt formatting,
    command routing, session management, and orchestrator communication.

    Attributes:
        orchestrator: ThanosOrchestrator instance for agent communication
        session_manager: SessionManager for conversation history
        context_manager: ContextManager for context window tracking
        state_reader: StateReader for Thanos state access
        command_router: CommandRouter for slash command handling
        prompt_formatter: PromptFormatter for prompt display
        thanos_dir: Path to Thanos project root
    """

    def __init__(self, orchestrator):
        """
        Initialize ThanosInteractive with orchestrator.

        Args:
            orchestrator: ThanosOrchestrator instance for agent communication
        """
        self.orchestrator = orchestrator

        # Determine Thanos directory (parent of Tools)
        self.thanos_dir = Path(__file__).parent.parent

        # Initialize components
        self.session_manager = SessionManager(
            history_dir=self.thanos_dir / "History" / "Sessions"
        )
        self.context_manager = ContextManager()
        self.state_reader = StateReader(self.thanos_dir / "State")

        # Initialize command router with dependencies
        self.command_router = CommandRouter(
            orchestrator=orchestrator,
            session_manager=self.session_manager,
            context_manager=self.context_manager,
            state_reader=self.state_reader,
            thanos_dir=self.thanos_dir,
        )

        # Initialize prompt formatter (loads config from config/api.json)
        self.prompt_formatter = PromptFormatter()

    def run(self) -> None:
        """
        Start the interactive session loop.

        This is the main entry point for interactive mode. It displays a welcome
        message, then enters a loop that:
        1. Displays prompt with current token/cost stats
        2. Gets user input
        3. Routes commands or sends messages to orchestrator
        4. Updates session stats
        5. Repeats until user quits

        The loop handles Ctrl+C and Ctrl+D gracefully for clean exits.
        """
        # Display welcome message
        self._show_welcome()

        # Main interaction loop
        while True:
            try:
                # Get current session stats for prompt
                stats = self.session_manager.get_stats()

                # Format prompt with stats (uses mode from command router or config default)
                prompt_mode = self.command_router.current_prompt_mode
                prompt = self.prompt_formatter.format(stats, mode=prompt_mode)

                # Get user input
                user_input = input(prompt).strip()

                # Skip empty input
                if not user_input:
                    continue

                # Handle slash commands
                if user_input.startswith("/"):
                    result = self.command_router.route_command(user_input)
                    if result.action == CommandAction.QUIT:
                        break
                    continue

                # Check for intelligent agent routing
                suggested_agent = self.command_router.detect_agent(user_input, auto_switch=False)
                if suggested_agent and suggested_agent != self.command_router.current_agent:
                    agent_name = self.orchestrator.agents[suggested_agent].name
                    print(f"{Colors.DIM}[Routing to {agent_name}]{Colors.RESET}")
                    self.command_router.current_agent = suggested_agent

                # Add user message to session (token count will be updated after API call)
                self.session_manager.add_user_message(user_input, tokens=0)

                # Send message to orchestrator
                current_agent = self.command_router.current_agent
                model = self.command_router.get_current_model()

                try:
                    # Get response from orchestrator
                    response = self.orchestrator.chat(
                        message=user_input,
                        agent=current_agent,
                        model=model,
                        stream=True
                    )

                    # Add assistant response to session
                    # Note: Token counts will need to be tracked from API response
                    # For now, we'll use placeholder values
                    if response:
                        self.session_manager.add_assistant_message(response, tokens=0)

                        # TODO: Update token counts from actual API response
                        # This requires integration with the orchestrator's usage tracking
                        # For MVP, stats will be updated when available

                except Exception as e:
                    print(f"{Colors.DIM}Error: {e}{Colors.RESET}")
                    continue

            except (KeyboardInterrupt, EOFError):
                # Handle Ctrl+C or Ctrl+D gracefully
                print("\n")
                break
            except Exception as e:
                # Catch any other errors to prevent crash
                print(f"{Colors.DIM}Unexpected error: {e}{Colors.RESET}")
                continue

        # Show goodbye message
        self._show_goodbye()

    def _show_welcome(self) -> None:
        """Display welcome message when starting interactive mode."""
        print(f"\n{Colors.CYAN}Welcome to Thanos Interactive Mode{Colors.RESET}")
        print(f"{Colors.DIM}Type /help for commands, /quit to exit{Colors.RESET}\n")

        # Show current state context
        ctx = self.state_reader.get_quick_context()
        if ctx.get("focus"):
            print(f"{Colors.DIM}Current focus: {ctx['focus']}{Colors.RESET}")
        if ctx.get("top3"):
            print(f"{Colors.DIM}Today's top 3: {', '.join(ctx['top3'][:2])}...{Colors.RESET}")
        if ctx["focus"] or ctx["top3"]:
            print()

    def _show_goodbye(self) -> None:
        """Display goodbye message when exiting interactive mode."""
        stats = self.session_manager.get_stats()

        print(f"\n{Colors.CYAN}Session Summary:{Colors.RESET}")
        print(f"  Messages: {stats['message_count']}")
        print(f"  Total tokens: {stats['total_input_tokens'] + stats['total_output_tokens']:,}")
        print(f"  Estimated cost: ${stats['total_cost']:.4f}")
        print(f"  Duration: {stats['duration_minutes']} minutes")

        # Offer to save session if there were messages
        if stats['message_count'] > 0:
            try:
                save_input = input(f"\n{Colors.DIM}Save session? (y/N): {Colors.RESET}").strip().lower()
                if save_input in ['y', 'yes']:
                    filepath = self.session_manager.save()
                    print(f"{Colors.DIM}Session saved: {filepath}{Colors.RESET}")
            except (KeyboardInterrupt, EOFError):
                pass  # Skip save if user cancels

        print(f"\n{Colors.CYAN}Goodbye!{Colors.RESET}\n")
