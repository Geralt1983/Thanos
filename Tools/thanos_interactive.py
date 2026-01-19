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
import json
from pathlib import Path
from typing import Optional

import asyncio
from Tools.command_router import CommandRouter, CommandAction, Colors
from Tools.context_manager import ContextManager
from Tools.prompt_formatter import PromptFormatter
from Tools.session_manager import SessionManager
from Tools.state_reader import StateReader
from Tools.memos import get_memos


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

    def __init__(self, orchestrator, startup_command: Optional[str] = None):
        """
        Initialize ThanosInteractive with orchestrator.

        Args:
            orchestrator: ThanosOrchestrator instance for agent communication
            startup_command: Optional command to execute immediately on startup
        """
        # Ensure stdout handles UTF-8 (crucial for Windows console)
        if sys.platform == "win32":
            sys.stdout.reconfigure(encoding='utf-8')
        
        self.orchestrator = orchestrator

        # Determine Thanos directory (parent of Tools)
        self.thanos_dir = Path(__file__).parent.parent
        
        # Load default startup command from config if not provided
        if startup_command is None:
            # Try to get config from orchestrator, or load from file
            if hasattr(self.orchestrator, "config"):
                config = self.orchestrator.config
            else:
                config_path = self.thanos_dir / "config" / "api.json"
                if config_path.exists():
                    try:
                        config = json.loads(config_path.read_text(encoding='utf-8'))
                    except Exception:
                        config = {}
                else:
                    config = {}

            startup_config = config.get("startup", {})
            startup_command = startup_config.get("default_command")
            
        self.startup_command = startup_command

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
        first_turn = True
        
        while True:
            try:
                # Handle startup command on first turn
                if first_turn and self.startup_command:
                    user_input = self.startup_command
                    # Print it to simulate user typing
                    stats = self.session_manager.get_stats()
                    prompt_mode = self.command_router.current_prompt_mode
                    prompt = self.prompt_formatter.format(stats, mode=prompt_mode)
                    print(f"{prompt}{user_input}")
                    first_turn = False
                else:
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
                
                # Get history for context
                history = self.session_manager.get_messages_for_api()

                try:
                    # Get response from orchestrator
                    response = self.orchestrator.chat(
                        message=user_input,
                        agent=current_agent,
                        model=model,
                        stream=True,
                        history=history
                    )

                    
                    # Process response structure
                    content = ""
                    usage = None
                    api_error = False

                    if isinstance(response, dict):
                        content = response.get("content", "")
                        usage = response.get("usage")
                        api_error = response.get("api_error", False)

                        # Check for error indicators: api_error flag or empty usage with no content
                        if api_error or (not usage and not content):
                            self.session_manager.session.error_count = getattr(
                                self.session_manager.session, 'error_count', 0
                            ) + 1
                            error_msg = response.get("error_message", "Request failed")
                            print(f"{Colors.DIM}[API Error: {error_msg} - will retry automatically]{Colors.RESET}")
                            continue
                    else:
                        content = response

                    # Add assistant response to session
                    if content:
                        output_tokens = usage.get("output_tokens", 0) if usage else 0
                        input_tokens = usage.get("input_tokens", 0) if usage else 0
                        cost = usage.get("cost_usd", 0.0) if usage else 0.0
                        
                        # Update the last user message with actual input tokens
                        if usage:
                             # Find the last message (which is the user message we just added)
                             if self.session_manager.session.history:
                                 last_msg = self.session_manager.session.history[-1]
                                 if last_msg.role == "user":
                                     # Adjust total input tokens (remove old estimate, add new actual)
                                     self.session_manager.session.total_input_tokens -= last_msg.tokens
                                     last_msg.tokens = input_tokens
                                     self.session_manager.session.total_input_tokens += input_tokens
                                 elif len(self.session_manager.session.history) >= 2:
                                     # Try second to last (if we have async issues or other messages)
                                     prev_msg = self.session_manager.session.history[-2]
                                     if prev_msg.role == "user":
                                         self.session_manager.session.total_input_tokens -= prev_msg.tokens
                                         prev_msg.tokens = input_tokens
                                         self.session_manager.session.total_input_tokens += input_tokens

                        # Add assistant message with output tokens
                        self.session_manager.add_assistant_message(content, tokens=output_tokens)
                        
                        # Update total session cost
                        if usage:
                            # If usage dict has cost, use it directly as the increment
                            self.session_manager.session.total_cost += cost
                        elif self.orchestrator.api_client.usage_tracker:
                            # Fallback: estimate cost if usage dict is missing but tracker exists
                            # Note: This is an estimation fallback
                            est_cost = self.orchestrator.api_client.usage_tracker.calculate_cost(
                                model or "default", input_tokens, output_tokens
                            )
                            self.session_manager.session.total_cost += est_cost

                        # Update last interaction time after each successful chat
                        self.state_reader.update_last_interaction(
                            interaction_type="chat",
                            agent=current_agent
                        )

                except Exception as e:
                    # Track error count
                    self.session_manager.session.error_count = getattr(
                        self.session_manager.session, 'error_count', 0
                    ) + 1

                    # Provide informative error messages based on error type
                    error_msg = str(e)
                    if "404" in error_msg:
                        print(f"{Colors.DIM}[API endpoint not found - check model name]{Colors.RESET}")
                    elif "rate" in error_msg.lower() or "429" in error_msg:
                        print(f"{Colors.DIM}[Rate limited - waiting...]{Colors.RESET}")
                    elif "401" in error_msg or "unauthorized" in error_msg.lower():
                        print(f"{Colors.DIM}[Authentication failed - check API key]{Colors.RESET}")
                    elif "timeout" in error_msg.lower():
                        print(f"{Colors.DIM}[Request timed out - will retry]{Colors.RESET}")
                    elif "connection" in error_msg.lower():
                        print(f"{Colors.DIM}[Connection error - check network]{Colors.RESET}")
                    else:
                        print(f"{Colors.DIM}[Error: {e}]{Colors.RESET}")
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

        # Update last interaction time for cross-session awareness
        self.state_reader.update_last_interaction(
            interaction_type="session_start",
            agent=self.command_router.current_agent
        )

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
        # Update last interaction time for session end
        self.state_reader.update_last_interaction(
            interaction_type="session_end",
            agent=self.command_router.current_agent
        )

        stats = self.session_manager.get_stats()

        print(f"\n{Colors.CYAN}Session Summary:{Colors.RESET}")
        print(f"  Messages: {stats['message_count']}")
        print(f"  Total tokens: {stats['total_input_tokens'] + stats['total_output_tokens']:,}")
        print(f"  Estimated cost: ${stats['total_cost']:.4f}")
        print(f"  Duration: {stats['duration_minutes']} minutes")

        # Offer to save session if there were messages
        # Auto-save session if there were messages
        if stats['message_count'] > 0:
            try:
                filepath = self.session_manager.save()
                print(f"\n{Colors.DIM}Session saved: {filepath}{Colors.RESET}")
                
                # Auto-ingest into MemOS logic
                print(f"{Colors.DIM}Indexing memory...{Colors.RESET}", end="", flush=True)
                asyncio.run(self._ingest_session(filepath))
                print(f" {Colors.GREEN}Done{Colors.RESET}")
            except Exception as e:
                print(f"\n{Colors.RED}Auto-save failed: {e}{Colors.RESET}")



        print(f"\n{Colors.CYAN}Goodbye!{Colors.RESET}\n")

    async def _ingest_session(self, filepath: Path) -> None:
        """Ingest saved session into MemOS vector store."""
        memos = get_memos()
        content = filepath.read_text(encoding='utf-8')
        
        # Store as observation/session_log
        await memos.remember(
            content=content,
            memory_type="observation",
            domain="personal",
            metadata={
                "source": "session_import", 
                "filename": filepath.name,
                "type": "session_log"
            }
        )
