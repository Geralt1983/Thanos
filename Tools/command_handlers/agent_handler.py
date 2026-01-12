#!/usr/bin/env python3
"""
AgentHandler - Handles agent management commands in Thanos Interactive Mode.

This module manages agent switching and listing operations. It provides commands
for viewing available agents (personas) and switching between them to change the
conversational context and expertise focus.

Commands:
    /agent [name]   - Switch to a different agent or show current agent
    /agents         - List all available agents with their roles

Classes:
    AgentHandler: Handler for agent management commands

Dependencies:
    - BaseHandler: Provides shared utilities and dependency injection
    - CommandResult: Standard result format for command execution
    - Colors: ANSI color codes for formatted output

Architecture:
    This handler integrates with the PersonaRouter for agent detection and the
    orchestrator's agent configuration to provide seamless agent switching and
    discovery capabilities.

Example:
    handler = AgentHandler(orchestrator, session_mgr, context_mgr,
                          state_reader, thanos_dir)

    # Switch to a specific agent
    result = handler.handle_agent("dev")  # Switches to dev agent

    # List all available agents
    result = handler.handle_list_agents("")  # Shows all agents with roles

See Also:
    - Tools.routing.persona_router: Intelligent agent detection and routing
    - Tools.command_handlers.base: Base handler infrastructure
"""

from Tools.command_handlers.base import BaseHandler, CommandResult, Colors


class AgentHandler(BaseHandler):
    """
    Handler for agent management commands.

    Provides functionality for:
    - Switching between agents
    - Listing available agents
    - Showing current agent information
    """

    def __init__(self, orchestrator, session_manager, context_manager, state_reader, thanos_dir, **kwargs):
        """
        Initialize AgentHandler with dependencies.

        Args:
            orchestrator: ThanosOrchestrator for agent info
            session_manager: SessionManager for session operations
            context_manager: ContextManager for context operations
            state_reader: StateReader for state operations
            thanos_dir: Path to Thanos root directory
            **kwargs: Additional arguments passed to BaseHandler
        """
        super().__init__(orchestrator, session_manager, context_manager, state_reader, thanos_dir, **kwargs)
        self._current_agent = "ops"  # Default agent

    def get_current_agent(self) -> str:
        """
        Get the current agent name.

        Returns:
            Name of the currently active agent
        """
        return self._current_agent

    def set_current_agent(self, agent_name: str) -> bool:
        """
        Set the current agent.

        Args:
            agent_name: Name of the agent to switch to

        Returns:
            True if agent exists and was set, False otherwise
        """
        if agent_name in self.orchestrator.agents:
            self._current_agent = agent_name
            return True
        return False

    def handle_agent(self, args: str) -> CommandResult:
        """
        Handle /agent command - Switch to a different agent.

        Args:
            args: Agent name to switch to (empty to show current)

        Returns:
            CommandResult with action and success status
        """
        if not args:
            # No args - show current agent and available agents
            print(f"Current agent: {self._current_agent}")
            print(f"Available: {', '.join(self.orchestrator.agents.keys())}")
            return CommandResult()

        agent_name = args.lower().strip()
        if agent_name in self.orchestrator.agents:
            # Valid agent - switch to it
            self._current_agent = agent_name
            agent = self.orchestrator.agents[agent_name]
            print(f"{Colors.DIM}Switched to {agent.name} ({agent.role}){Colors.RESET}")
            return CommandResult()
        else:
            # Unknown agent
            print(f"{Colors.DIM}Unknown agent: {agent_name}{Colors.RESET}")
            print(f"Available: {', '.join(self.orchestrator.agents.keys())}")
            return CommandResult(success=False)

    def handle_list_agents(self, args: str) -> CommandResult:
        """
        Handle /agents command - List all available agents.

        Args:
            args: Command arguments (ignored for this command)

        Returns:
            CommandResult with action and success status
        """
        print(f"\n{Colors.CYAN}Available Agents:{Colors.RESET}")
        for name, agent in self.orchestrator.agents.items():
            marker = "→" if name == self._current_agent else " "
            print(f"  {marker} {name}: {agent.role}")
            print(f"      Voice: {agent.voice}")
        print()
        return CommandResult()
