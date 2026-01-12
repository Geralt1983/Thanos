#!/usr/bin/env python3
"""
StateHandler - Handles state and context information commands in Thanos Interactive Mode.

This module manages the display of system state, commitments, context window usage,
and session token usage statistics. It provides comprehensive visibility into
conversation state, resource utilization, and active work/personal commitments.

Commands:
    /state          - Show current Thanos state from Today.md
    /commitments    - Show active commitments from Commitments.md
    /context        - Show context window usage and availability
    /usage          - Show session token usage and cost statistics

Classes:
    StateHandler: Handler for all state and context information commands

Dependencies:
    - BaseHandler: Provides shared utilities and dependency injection
    - CommandResult: Standard result format for command execution
    - Colors: ANSI color codes for formatted output
    - StateReader: Reads state from Today.md and Commitments.md
    - ContextManager: Tracks context window usage

Architecture:
    State information is read from markdown files in the Thanos directory:
    - Today.md contains daily focus, top 3 priorities, commitments, and blockers
    - Commitments.md contains active work and personal commitments
    Context and usage statistics are tracked in real-time during conversation.

Example:
    handler = StateHandler(orchestrator, session_mgr, context_mgr,
                          state_reader, thanos_dir)

    # Show current Thanos state
    result = handler.handle_state("")

    # Display token usage stats
    result = handler.handle_usage("")

    # Check context window
    result = handler.handle_context("")

See Also:
    - Tools.command_handlers.base: Base handler infrastructure
    - Today.md: Daily state and focus
    - Commitments.md: Active commitments
"""

from Tools.command_handlers.base import BaseHandler, CommandResult, Colors


class StateHandler(BaseHandler):
    """
    Handler for state and context information commands.

    Provides functionality for:
    - Displaying current Thanos state (focus, top 3, commitments)
    - Showing active work and personal commitments
    - Monitoring context window usage
    - Tracking session token usage and costs
    """

    def __init__(self, orchestrator, session_manager, context_manager, state_reader, thanos_dir, **kwargs):
        """
        Initialize StateHandler with dependencies.

        Args:
            orchestrator: ThanosOrchestrator for agent info
            session_manager: SessionManager for session operations
            context_manager: ContextManager for context operations
            state_reader: StateReader for state operations
            thanos_dir: Path to Thanos root directory
            **kwargs: Additional arguments passed to BaseHandler
        """
        super().__init__(orchestrator, session_manager, context_manager, state_reader, thanos_dir, **kwargs)

    def handle_usage(self, args: str) -> CommandResult:
        """
        Handle /usage command - Show token usage statistics.

        Displays comprehensive session statistics including duration,
        message count, token usage, and estimated API costs.

        Args:
            args: Command arguments (ignored for this command)

        Returns:
            CommandResult with action and success status
        """
        stats = self.session.get_stats()
        print(f"""
{Colors.CYAN}Session Usage:{Colors.RESET}
  Duration: {stats["duration_minutes"]} minutes
  Messages: {stats["message_count"]}
  Input tokens: {stats["total_input_tokens"]:,}
  Output tokens: {stats["total_output_tokens"]:,}
  Estimated cost: ${stats["total_cost"]:.4f}
""")
        return CommandResult()

    def handle_context(self, args: str) -> CommandResult:
        """
        Handle /context command - Show context window usage.

        Displays how much of the available context window is being used
        by the system prompt and conversation history, helping users
        understand when they might be approaching limits.

        Args:
            args: Command arguments (ignored for this command)

        Returns:
            CommandResult with action and success status
        """
        current_agent = self._get_current_agent()
        agent = self.orchestrator.agents.get(current_agent)
        system_prompt = self.orchestrator._build_system_prompt(agent=agent)
        history = self.session.get_messages_for_api()

        report = self.context_mgr.get_usage_report(history, system_prompt)
        print(f"""
{Colors.CYAN}Context Window:{Colors.RESET}
  System prompt: ~{report["system_tokens"]:,} tokens
  Conversation: ~{report["history_tokens"]:,} tokens ({report["messages_in_context"]} messages)
  Total used: ~{report["total_used"]:,} / {report["available"]:,} tokens
  Usage: {report["usage_percent"]:.1f}%
""")
        return CommandResult()

    def handle_state(self, args: str) -> CommandResult:
        """
        Handle /state command - Show current Thanos state.

        Displays the current state from Today.md including focus,
        top 3 priorities, pending commitments, blockers, energy level,
        and week theme.

        Args:
            args: Command arguments (ignored for this command)

        Returns:
            CommandResult with action and success status
        """
        ctx = self.state_reader.get_quick_context()
        print(f"""
{Colors.CYAN}Current Thanos State:{Colors.RESET}""")

        if ctx["focus"]:
            print(f"  Focus: {ctx['focus']}")

        if ctx["top3"]:
            print("\n  Today's Top 3:")
            for i, item in enumerate(ctx["top3"], 1):
                print(f"    {i}. {item}")

        if ctx["pending_commitments"] > 0:
            print(f"\n  Pending Commitments: {ctx['pending_commitments']}")

        if ctx["blockers"]:
            print(f"  Blockers: {', '.join(ctx['blockers'])}")

        if ctx["energy"]:
            print(f"  Energy: {ctx['energy']}")

        if ctx["week_theme"]:
            print(f"  Week Theme: {ctx['week_theme']}")

        if not any([ctx["focus"], ctx["top3"], ctx["pending_commitments"]]):
            print(f"  {Colors.DIM}No active state loaded{Colors.RESET}")

        print()
        return CommandResult()

    def handle_commitments(self, args: str) -> CommandResult:
        """
        Handle /commitments command - Show active commitments.

        Displays all uncompleted commitments from Commitments.md,
        organized by Work Commitments and Personal Commitments sections.
        Only shows items marked as pending (- [ ]).

        Args:
            args: Command arguments (ignored for this command)

        Returns:
            CommandResult with action and success status
        """
        commitments_file = self.thanos_dir / "State" / "Commitments.md"
        if not commitments_file.exists():
            print(f"{Colors.RED}No commitments file found.{Colors.RESET}")
            return CommandResult(success=False)

        try:
            content = commitments_file.read_text()
            print(f"\n{Colors.CYAN}Active Commitments:{Colors.RESET}\n")

            # Parse and display uncompleted commitments
            lines = content.split("\n")
            in_section = False
            shown_count = 0

            for line in lines:
                if line.startswith("## Work Commitments") or line.startswith(
                    "## Personal Commitments"
                ):
                    in_section = True
                    print(f"{Colors.BOLD}{line[3:]}{Colors.RESET}")
                    continue

                if in_section and line.startswith("##"):
                    in_section = False

                if in_section and "- [ ]" in line:
                    print(f"  {line.strip()}")
                    shown_count += 1

            if shown_count == 0:
                print(f"  {Colors.DIM}No pending commitments{Colors.RESET}")
            print()
            return CommandResult()

        except Exception as e:
            print(f"{Colors.RED}Error reading commitments: {e}{Colors.RESET}")
            return CommandResult(success=False)
