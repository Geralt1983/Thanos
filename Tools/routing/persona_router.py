#!/usr/bin/env python3
"""
PersonaRouter - Intelligent routing for agent detection and selection

Handles agent detection based on trigger patterns, scoring agents by message content,
and managing agent switching in Thanos Interactive Mode.

Single Responsibility: Agent detection and intelligent routing
"""

import re
from typing import Optional, Dict


class PersonaRouter:
    """
    Routes messages to appropriate agents based on trigger patterns.

    The PersonaRouter analyzes user messages and detects which agent should handle
    the conversation based on trigger words defined in agent configurations.

    Example:
        router = PersonaRouter(orchestrator)
        detected_agent = router.detect_agent("I need urgent help with deployment")
        # Returns "ops" if ops agent has "urgent" as a trigger
    """

    def __init__(self, orchestrator, current_agent: str = "ops"):
        """
        Initialize PersonaRouter with agent definitions.

        Args:
            orchestrator: ThanosOrchestrator instance with agent definitions
            current_agent: Name of the currently active agent (default: "ops")
        """
        self.orchestrator = orchestrator
        self.current_agent = current_agent

        # Build trigger patterns for intelligent routing
        self._trigger_patterns: Dict[str, list[re.Pattern]] = {}
        self._build_trigger_patterns()

    def _build_trigger_patterns(self):
        """
        Build regex patterns from agent triggers for intelligent routing.

        Iterates through all registered agents and compiles case-insensitive
        regex patterns for each trigger phrase defined in the agent configuration.
        """
        for agent_name, agent in self.orchestrator.agents.items():
            triggers = getattr(agent, "triggers", None)
            if triggers:
                patterns = []
                for trigger in triggers:
                    # Build case-insensitive pattern for each trigger phrase
                    # Escape special regex chars and create word boundary pattern
                    escaped = re.escape(trigger.lower())
                    patterns.append(re.compile(escaped, re.IGNORECASE))
                self._trigger_patterns[agent_name] = patterns

    def detect_agent(self, message: str, auto_switch: bool = True) -> Optional[str]:
        """
        Detect the appropriate agent for a message based on trigger patterns.

        Analyzes the message content and scores each agent based on how many
        of their trigger phrases appear in the message. Returns the highest
        scoring agent if it differs from the current agent.

        Args:
            message: User message to analyze
            auto_switch: If True, switch current_agent when match found

        Returns:
            Agent name if a better match found, None if current agent is appropriate

        Example:
            >>> router.detect_agent("urgent task needs attention")
            'ops'  # If ops agent has "urgent" as a trigger

            >>> router.detect_agent("let's strategize about Q2")
            'strategy'  # If strategy agent has "strategize" as a trigger
        """
        message_lower = message.lower()
        scores: Dict[str, int] = {}

        # Score each agent based on trigger matches
        for agent_name, patterns in self._trigger_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern.search(message_lower):
                    score += 1
            if score > 0:
                scores[agent_name] = score

        if not scores:
            return None

        # Find highest scoring agent
        best_agent = max(scores, key=scores.get)

        # Only switch if different from current and score is meaningful
        if best_agent != self.current_agent and scores[best_agent] >= 1:
            if auto_switch:
                self.current_agent = best_agent
                return best_agent
            return best_agent

        return None

    def get_current_agent(self) -> str:
        """
        Get the name of the currently active agent.

        Returns:
            Current agent name (e.g., "ops", "strategy", "coach", "health")
        """
        return self.current_agent

    def set_current_agent(self, agent_name: str) -> bool:
        """
        Manually switch to a different agent.

        Args:
            agent_name: Name of the agent to switch to

        Returns:
            True if agent exists and switch was successful, False otherwise
        """
        if agent_name in self.orchestrator.agents:
            self.current_agent = agent_name
            return True
        return False

    def get_available_agents(self) -> list[str]:
        """
        Get list of all available agent names.

        Returns:
            List of agent names (e.g., ["ops", "strategy", "coach", "health"])
        """
        return list(self.orchestrator.agents.keys())

    def get_agent_triggers(self, agent_name: str) -> list[str]:
        """
        Get trigger phrases for a specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            List of trigger phrases, or empty list if agent not found
        """
        agent = self.orchestrator.agents.get(agent_name)
        if agent:
            return getattr(agent, "triggers", [])
        return []

    def rebuild_patterns(self):
        """
        Rebuild trigger patterns from current agent definitions.

        Useful if agent configurations have been dynamically updated
        and patterns need to be refreshed.
        """
        self._trigger_patterns.clear()
        self._build_trigger_patterns()
