#!/usr/bin/env python3
"""
CoreHandler - Handles core system commands

Manages fundamental system commands in Thanos Interactive Mode.
Provides commands for help, quitting, and running Thanos commands.

Commands:
    /help           - Show all available commands and usage information
    /quit           - Exit interactive mode
    /run <cmd>      - Run a Thanos command (e.g., /run pa:daily)
"""

from Tools.command_handlers.base import BaseHandler, CommandAction, CommandResult, Colors


class CoreHandler(BaseHandler):
    """
    Handler for core system commands.

    Provides functionality for:
    - Displaying help information with all available commands
    - Exiting interactive mode
    - Running Thanos commands directly from interactive mode
    """

    def handle_help(self, args: str) -> CommandResult:
        """
        Handle /help command - Show help information.

        Displays a comprehensive list of all available commands with descriptions,
        including shortcuts and usage tips.

        Args:
            args: Not used (help takes no arguments)

        Returns:
            CommandResult with action=CONTINUE and success=True

        Examples:
            /help  -> Display all available commands and shortcuts
        """
        print(f"""
{Colors.CYAN}Commands:{Colors.RESET}
  /agent <name>  - Switch agent (strategy, coach, health, ops)
  /agents        - List all available agents
  /clear         - Clear conversation history
  /context       - Show context window usage
  /state         - Show current Thanos state (focus, top 3, energy)
  /commitments   - Show active commitments
  /usage         - Show token/cost statistics
  /save          - Save session to History/Sessions/
  /sessions      - List saved sessions
  /resume <id>   - Resume a saved session (/resume last for most recent)
  /recall <q>    - Search memories (MemOS hybrid) or past sessions
  /remember <c>  - Store a memory in MemOS knowledge graph
  /memory        - Show memory system info (Neo4j, ChromaDB, sessions)
  /branch [name] - Create conversation branch from current point
  /branches      - List all branches of this session
  /switch <ref>  - Switch to a different branch (by name or id)
  /patterns      - Show conversation patterns and usage analytics
  /model [name]  - Switch AI model (opus, sonnet, haiku)
  /run <cmd>     - Run a Thanos command (e.g., /run pa:daily)
  /help          - Show this help
  /quit          - Exit interactive mode

{Colors.CYAN}Shortcuts:{Colors.RESET}
  /a = /agent, /s = /state, /c = /commitments
  /r = /resume, /m = /model, /h = /help, /q = /quit

{Colors.DIM}Tip: Use \"\"\" for multi-line input{Colors.RESET}
""")
        return CommandResult()

    def handle_quit(self, args: str) -> CommandResult:
        """
        Handle /quit command - Exit interactive mode.

        Terminates the interactive session and returns control to the shell.

        Args:
            args: Not used (quit takes no arguments)

        Returns:
            CommandResult with action=QUIT to signal session termination

        Examples:
            /quit  -> Exit interactive mode
        """
        return CommandResult(action=CommandAction.QUIT)

    def handle_run(self, args: str) -> CommandResult:
        """
        Handle /run command - Run a Thanos command.

        Executes a Thanos command directly from interactive mode. This allows
        running any Thanos command (e.g., pa:daily, st:review) without leaving
        the interactive session.

        Args:
            args: The Thanos command to run (e.g., "pa:daily", "st:review")

        Returns:
            CommandResult with success=True if command ran, success=False if no command provided

        Examples:
            /run pa:daily     -> Run the daily planning assistant command
            /run st:review    -> Run the strategy review command
            /run              -> Show usage error (no command provided)
        """
        if not args:
            print(f"{Colors.DIM}Usage: /run <command> (e.g., /run pa:daily){Colors.RESET}")
            return CommandResult(success=False)

        print(f"{Colors.DIM}Running {args}...{Colors.RESET}\n")
        try:
            self.orchestrator.run_command(args, stream=True)
            return CommandResult()
        except Exception as e:
            print(f"{Colors.DIM}Error running command: {e}{Colors.RESET}")
            return CommandResult(success=False)
