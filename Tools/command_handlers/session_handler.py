#!/usr/bin/env python3
"""
SessionHandler - Handles session management commands in Thanos Interactive Mode.

This module manages the complete lifecycle of conversation sessions, including
saving, loading, clearing, and branching. It provides git-like branching capabilities
for conversations, allowing users to explore different conversation paths and
maintain multiple conversation threads.

Commands:
    /clear              - Clear current conversation history
    /save               - Save current session to disk
    /sessions           - List recently saved sessions
    /resume [id]        - Resume a saved session by ID
    /branch [name]      - Create a conversation branch from current point
    /branches           - List all branches in current session tree
    /switch <ref>       - Switch to a different conversation branch

Classes:
    SessionHandler: Handler for all session management commands

Dependencies:
    - BaseHandler: Provides shared utilities and dependency injection
    - CommandResult: Standard result format for command execution
    - Colors: ANSI color codes for formatted output
    - SessionManager: Manages session persistence and retrieval

Architecture:
    Sessions are stored in History/Sessions/ directory with JSON format containing
    conversation messages, metadata, and timestamps. Branching creates a tree
    structure similar to git, enabling conversation version control.

Example:
    handler = SessionHandler(orchestrator, session_mgr, context_mgr,
                            state_reader, thanos_dir)

    # Save current session
    result = handler.handle_save("")

    # Create a branch
    result = handler.handle_branch("experimental-feature")

    # List all sessions
    result = handler.handle_sessions("")

See Also:
    - Tools.command_handlers.base: Base handler infrastructure
    - History/Sessions/: Session storage directory
"""

from Tools.command_handlers.base import BaseHandler, CommandResult, Colors
from Tools.output_formatter import truncate_smart


class SessionHandler(BaseHandler):
    """
    Handler for session management commands.

    Provides functionality for:
    - Clearing conversation history
    - Saving sessions to disk
    - Listing and resuming saved sessions
    - Creating and managing conversation branches
    - Switching between branches
    """

    def __init__(self, orchestrator, session_manager, context_manager, state_reader, thanos_dir, **kwargs):
        """
        Initialize SessionHandler with dependencies.

        Args:
            orchestrator: ThanosOrchestrator for agent info
            session_manager: SessionManager for session operations
            context_manager: ContextManager for context operations
            state_reader: StateReader for state operations
            thanos_dir: Path to Thanos root directory
            **kwargs: Additional arguments passed to BaseHandler
        """
        super().__init__(orchestrator, session_manager, context_manager, state_reader, thanos_dir, **kwargs)

    def handle_clear(self, args: str) -> CommandResult:
        """
        Handle /clear command - Clear conversation history.

        Removes all messages from the current conversation session,
        providing a fresh start while maintaining the same session ID.

        Args:
            args: Command arguments (ignored for this command)

        Returns:
            CommandResult with action and success status
        """
        self.session.clear()
        print(f"{Colors.GREEN}Conversation cleared.{Colors.RESET}")
        return CommandResult()

    def handle_save(self, args: str) -> CommandResult:
        """
        Handle /save command - Save session to History/Sessions/.

        Persists the current conversation session to disk, making it
        available for future restoration via /resume command.

        Args:
            args: Command arguments (ignored for this command)

        Returns:
            CommandResult with action and success status
        """
        filepath = self.session.save()
        print(f"{Colors.GREEN}Session saved: {filepath}{Colors.RESET}")
        return CommandResult()

    def handle_sessions(self, args: str) -> CommandResult:
        """
        Handle /sessions command - List recent saved sessions.

        Displays the 10 most recent saved sessions with their metadata
        including ID, date, agent, message count, and token usage.

        Args:
            args: Command arguments (ignored for this command)

        Returns:
            CommandResult with action and success status
        """
        sessions = self.session.list_sessions(limit=10)
        if not sessions:
            print(f"{Colors.DIM}No saved sessions found.{Colors.RESET}")
            return CommandResult()

        print(f"\n{Colors.CYAN}Recent Sessions:{Colors.RESET}")
        for s in sessions:
            session_id = truncate_smart(s['id'], max_length=20)
            agent_name = truncate_smart(s['agent'], max_length=12)
            print(
                f"  {session_id}  {s['date']}  {agent_name:12}  "
                f"{s['messages']:3} msgs  {s['tokens']:,} tokens"
            )
        print(f"\n{Colors.DIM}Use /resume <id> or /resume last to restore{Colors.RESET}\n")
        return CommandResult()

    def handle_resume(self, args: str) -> CommandResult:
        """
        Handle /resume command - Resume a saved session.

        Loads a previously saved session from disk, restoring the full
        conversation history and agent context. If no session ID is provided,
        displays a list of recent sessions to choose from.

        Args:
            args: Session ID to resume (or "last" for most recent)

        Returns:
            CommandResult with action and success status
        """
        if not args:
            # Show sessions and prompt
            sessions = self.session.list_sessions(limit=5)
            if not sessions:
                print(f"{Colors.RED}No saved sessions to resume.{Colors.RESET}")
                return CommandResult(success=False)

            print(f"\n{Colors.CYAN}Recent Sessions:{Colors.RESET}")
            for s in sessions:
                session_id = truncate_smart(s['id'], max_length=20)
                agent_name = truncate_smart(s['agent'], max_length=12)
                print(f"  {session_id}  {s['date']}  {agent_name:12}  {s['messages']:3} msgs")
            print(f"\n{Colors.DIM}Usage: /resume <session_id> or /resume last{Colors.RESET}\n")
            return CommandResult()

        session_id = args.strip()
        if self.session.load_session(session_id):
            # Update current agent to match restored session
            # Note: This requires access to parent's current_agent attribute
            # The orchestrator will need to handle agent switching
            stats = self.session.get_stats()
            print(f"{Colors.CYAN}Session restored:{Colors.RESET}")
            print(f"  ID: {stats['session_id']}")
            print(f"  Agent: {stats['current_agent']}")
            print(f"  Messages: {stats['message_count']}")
            print(
                f"  Previous tokens: {stats['total_input_tokens'] + stats['total_output_tokens']:,}"
            )
            print(
                f"\n{Colors.DIM}Conversation history loaded. "
                f"Continue where you left off.{Colors.RESET}\n"
            )
            return CommandResult()
        else:
            print(f"{Colors.RED}Session not found: {session_id}{Colors.RESET}")
            print(f"{Colors.DIM}Use /sessions to list available sessions.{Colors.RESET}")
            return CommandResult(success=False)

    def handle_branch(self, args: str) -> CommandResult:
        """
        Handle /branch command - Create a conversation branch from current point.

        Creates a new branch from the current conversation state, allowing
        exploration of alternative conversation paths while preserving the
        original conversation.

        Args:
            args: Optional branch name (auto-generated if not provided)

        Returns:
            CommandResult with action and success status
        """
        branch_name = args.strip() if args else None
        new_id = self.session.create_branch(branch_name)
        branch_info = self.session.get_branch_info()

        print(f"\n{Colors.CYAN}Branch created:{Colors.RESET}")
        print(f"  Name: {branch_info['name']}")
        print(f"  ID: {new_id}")
        print(f"  Branched from: {branch_info['parent_id']}")
        print(f"  At message: {branch_info['branch_point']}")
        print(
            f"\n{Colors.DIM}Continue conversation on this branch. "
            f"Use /branches to list all.{Colors.RESET}\n"
        )
        return CommandResult()

    def handle_branches(self, args: str) -> CommandResult:
        """
        Handle /branches command - List all branches of current session tree.

        Displays all branches in the current session tree with their metadata,
        showing the branch hierarchy and relationships.

        Args:
            args: Command arguments (ignored for this command)

        Returns:
            CommandResult with action and success status
        """
        branches = self.session.list_branches()

        if not branches:
            print(f"{Colors.DIM}No branches found for this session.{Colors.RESET}")
            return CommandResult()

        print(f"\n{Colors.CYAN}Session Branches:{Colors.RESET}\n")
        for b in branches:
            marker = "→" if b.get("is_current") else " "
            branch_name = truncate_smart(b['name'], max_length=25)
            branch_id = truncate_smart(b['id'], max_length=20)
            parent_info = (
                f" (from {b['parent_id'][:4]}... at msg {b['branch_point']})"
                if b.get("parent_id")
                else ""
            )
            print(f"  {marker} {branch_name}: {branch_id}{parent_info}")
            print(f"      {b['date']}  {b['messages']} messages")

        print(f"\n{Colors.DIM}Use /switch <name or id> to change branches{Colors.RESET}\n")
        return CommandResult()

    def handle_switch(self, args: str) -> CommandResult:
        """
        Handle /switch command - Switch to a different branch.

        Changes the active conversation branch, loading the conversation
        history from the specified branch. If no branch reference is provided,
        displays a list of available branches.

        Args:
            args: Branch name or ID to switch to

        Returns:
            CommandResult with action and success status
        """
        if not args:
            # Show branches
            return self.handle_branches("")

        branch_ref = args.strip()
        if self.session.switch_branch(branch_ref):
            # Note: Agent switching needs to be handled by the router/orchestrator
            # The session has been switched, and session.session.agent contains the agent
            branch_info = self.session.get_branch_info()
            stats = self.session.get_stats()

            print(f"\n{Colors.CYAN}Switched to branch:{Colors.RESET}")
            print(f"  Name: {branch_info['name']}")
            print(f"  ID: {branch_info['id']}")
            print(f"  Messages: {stats['message_count']}")
            print(f"\n{Colors.DIM}Conversation restored from branch point.{Colors.RESET}\n")
            return CommandResult()
        else:
            print(f"{Colors.RED}Branch not found: {branch_ref}{Colors.RESET}")
            print(f"{Colors.DIM}Use /branches to list available branches.{Colors.RESET}")
            return CommandResult(success=False)
