#!/usr/bin/env python3
"""
Unit tests for Routing Modules

Tests PersonaRouter and CommandRegistry in isolation with mocked dependencies.
Verifies agent detection, command registration, and routing logic.
"""

from unittest.mock import Mock
import re

import pytest

from Tools.routing import PersonaRouter, CommandRegistry


# ========================================================================
# Module-level Fixtures
# ========================================================================


@pytest.fixture
def mock_orchestrator():
    """Create mock orchestrator with agents and triggers"""
    orchestrator = Mock()
    orchestrator.agents = {
        "ops": Mock(
            name="Ops",
            role="Operations Manager",
            voice="Professional",
            triggers=["urgent", "deploy", "production", "incident"]
        ),
        "strategy": Mock(
            name="Strategy",
            role="Strategic Advisor",
            voice="Thoughtful",
            triggers=["strategy", "plan", "goal", "vision"]
        ),
        "coach": Mock(
            name="Coach",
            role="Accountability Coach",
            voice="Direct",
            triggers=["commitment", "accountability", "focus", "energy"]
        ),
        "health": Mock(
            name="Health",
            role="Health Optimizer",
            voice="Supportive",
            triggers=["health", "exercise", "sleep", "wellness"]
        ),
    }
    return orchestrator


@pytest.fixture
def persona_router(mock_orchestrator):
    """Create PersonaRouter with mocked orchestrator"""
    return PersonaRouter(mock_orchestrator, current_agent="ops")


@pytest.fixture
def command_registry():
    """Create empty CommandRegistry"""
    return CommandRegistry()


@pytest.fixture
def mock_handlers():
    """Create mock handler functions for testing"""
    return {
        "handle_help": Mock(return_value="help output"),
        "handle_state": Mock(return_value="state output"),
        "handle_quit": Mock(return_value="quit output"),
        "handle_agent": Mock(return_value="agent output"),
    }


# ========================================================================
# PersonaRouter Tests
# ========================================================================


class TestPersonaRouterInitialization:
    """Test PersonaRouter initialization"""

    def test_initialization_defaults(self, mock_orchestrator):
        """Test PersonaRouter initializes with default agent"""
        router = PersonaRouter(mock_orchestrator)
        assert router.orchestrator is mock_orchestrator
        assert router.current_agent == "ops"
        assert len(router._trigger_patterns) == 4  # 4 agents with triggers

    def test_initialization_custom_agent(self, mock_orchestrator):
        """Test PersonaRouter initializes with custom agent"""
        router = PersonaRouter(mock_orchestrator, current_agent="strategy")
        assert router.current_agent == "strategy"

    def test_trigger_patterns_built(self, persona_router):
        """Test trigger patterns are compiled on initialization"""
        assert "ops" in persona_router._trigger_patterns
        assert "strategy" in persona_router._trigger_patterns
        assert "coach" in persona_router._trigger_patterns
        assert "health" in persona_router._trigger_patterns

        # Verify patterns are compiled regex
        ops_patterns = persona_router._trigger_patterns["ops"]
        assert len(ops_patterns) == 4  # urgent, deploy, production, incident
        assert all(isinstance(p, re.Pattern) for p in ops_patterns)


class TestPersonaRouterAgentDetection:
    """Test PersonaRouter agent detection logic"""

    def test_detect_agent_ops_trigger(self, persona_router):
        """Test detecting ops agent from trigger words"""
        # Start with strategy agent
        persona_router.current_agent = "strategy"

        detected = persona_router.detect_agent("We have an urgent production incident")
        assert detected == "ops"
        assert persona_router.current_agent == "ops"  # Auto-switched

    def test_detect_agent_strategy_trigger(self, persona_router):
        """Test detecting strategy agent from trigger words"""
        detected = persona_router.detect_agent("Let's plan our strategy for Q2")
        assert detected == "strategy"
        assert persona_router.current_agent == "strategy"

    def test_detect_agent_coach_trigger(self, persona_router):
        """Test detecting coach agent from trigger words"""
        detected = persona_router.detect_agent("I need help with my commitments and focus")
        assert detected == "coach"
        assert persona_router.current_agent == "coach"

    def test_detect_agent_health_trigger(self, persona_router):
        """Test detecting health agent from trigger words"""
        detected = persona_router.detect_agent("How can I improve my sleep and wellness?")
        assert detected == "health"
        assert persona_router.current_agent == "health"

    def test_detect_agent_no_match(self, persona_router):
        """Test no detection when no triggers match"""
        detected = persona_router.detect_agent("Just a regular message")
        assert detected is None
        assert persona_router.current_agent == "ops"  # Unchanged

    def test_detect_agent_case_insensitive(self, persona_router):
        """Test detection is case-insensitive"""
        persona_router.current_agent = "strategy"

        detected = persona_router.detect_agent("URGENT deployment needed")
        assert detected == "ops"

        # Reset for second test
        persona_router.current_agent = "strategy"
        detected = persona_router.detect_agent("Urgent Deployment Needed")
        assert detected == "ops"

    def test_detect_agent_multiple_triggers(self, persona_router):
        """Test detection with multiple trigger matches"""
        persona_router.current_agent = "strategy"

        # ops has "urgent" and "production" triggers
        detected = persona_router.detect_agent("Urgent production deploy needed")
        assert detected == "ops"

    def test_detect_agent_no_auto_switch(self, persona_router):
        """Test detection without auto-switching"""
        persona_router.current_agent = "strategy"

        detected = persona_router.detect_agent("urgent task", auto_switch=False)
        assert detected == "ops"  # Detected
        assert persona_router.current_agent == "strategy"  # Not switched

    def test_detect_agent_same_as_current(self, persona_router):
        """Test no detection when current agent matches"""
        persona_router.current_agent = "ops"

        # "urgent" is an ops trigger, but ops is already current
        detected = persona_router.detect_agent("urgent task")
        assert detected is None  # No switch needed
        assert persona_router.current_agent == "ops"


class TestPersonaRouterAgentManagement:
    """Test PersonaRouter agent get/set operations"""

    def test_get_current_agent(self, persona_router):
        """Test getting current agent"""
        assert persona_router.get_current_agent() == "ops"

        persona_router.current_agent = "strategy"
        assert persona_router.get_current_agent() == "strategy"

    def test_set_current_agent_valid(self, persona_router):
        """Test setting valid agent"""
        result = persona_router.set_current_agent("strategy")
        assert result is True
        assert persona_router.current_agent == "strategy"

        result = persona_router.set_current_agent("coach")
        assert result is True
        assert persona_router.current_agent == "coach"

    def test_set_current_agent_invalid(self, persona_router):
        """Test setting invalid agent"""
        result = persona_router.set_current_agent("invalid")
        assert result is False
        assert persona_router.current_agent == "ops"  # Unchanged

    def test_get_available_agents(self, persona_router):
        """Test getting list of available agents"""
        agents = persona_router.get_available_agents()
        assert len(agents) == 4
        assert "ops" in agents
        assert "strategy" in agents
        assert "coach" in agents
        assert "health" in agents

    def test_get_agent_triggers_valid(self, persona_router):
        """Test getting triggers for valid agent"""
        triggers = persona_router.get_agent_triggers("ops")
        assert triggers == ["urgent", "deploy", "production", "incident"]

        triggers = persona_router.get_agent_triggers("strategy")
        assert triggers == ["strategy", "plan", "goal", "vision"]

    def test_get_agent_triggers_invalid(self, persona_router):
        """Test getting triggers for invalid agent"""
        triggers = persona_router.get_agent_triggers("invalid")
        assert triggers == []

    def test_get_agent_triggers_no_triggers(self, mock_orchestrator):
        """Test getting triggers for agent without triggers attribute"""
        # Create a mock agent without triggers attribute (delattr doesn't work on Mock, so use spec)
        no_trigger_agent = Mock(name="NoTriggers", role="Test", spec=['name', 'role'])
        mock_orchestrator.agents["notriggers"] = no_trigger_agent
        router = PersonaRouter(mock_orchestrator)

        triggers = router.get_agent_triggers("notriggers")
        assert triggers == []


class TestPersonaRouterRebuildPatterns:
    """Test PersonaRouter pattern rebuilding"""

    def test_rebuild_patterns(self, persona_router, mock_orchestrator):
        """Test rebuilding patterns after agent changes"""
        # Verify initial state
        assert len(persona_router._trigger_patterns) == 4

        # Modify agent triggers
        mock_orchestrator.agents["ops"].triggers = ["urgent", "deploy", "newkeyword"]

        # Rebuild patterns
        persona_router.rebuild_patterns()

        # Verify patterns updated
        ops_patterns = persona_router._trigger_patterns["ops"]
        assert len(ops_patterns) == 3  # Now has 3 triggers

        # Verify detection works with new trigger
        persona_router.current_agent = "strategy"
        detected = persona_router.detect_agent("newkeyword in message")
        assert detected == "ops"

    def test_rebuild_patterns_clears_old(self, persona_router):
        """Test rebuild clears old patterns"""
        initial_patterns = persona_router._trigger_patterns.copy()
        assert len(initial_patterns) > 0

        persona_router.rebuild_patterns()

        # Should still have patterns, but rebuilt
        assert len(persona_router._trigger_patterns) == 4
        # Patterns should be different objects (newly compiled)
        assert persona_router._trigger_patterns is not initial_patterns


# ========================================================================
# CommandRegistry Tests
# ========================================================================


class TestCommandRegistryInitialization:
    """Test CommandRegistry initialization"""

    def test_initialization(self):
        """Test CommandRegistry initializes empty"""
        registry = CommandRegistry()
        assert len(registry._commands) == 0
        assert registry.get_all_commands() == {}


class TestCommandRegistryRegistration:
    """Test CommandRegistry command registration"""

    def test_register_single_command(self, command_registry, mock_handlers):
        """Test registering a single command"""
        command_registry.register(
            "help",
            mock_handlers["handle_help"],
            "Show help",
            []
        )

        assert command_registry.has_command("help")
        handler, desc, args = command_registry.get("help")
        assert handler is mock_handlers["handle_help"]
        assert desc == "Show help"
        assert args == []

    def test_register_command_with_args(self, command_registry, mock_handlers):
        """Test registering command with arguments"""
        command_registry.register(
            "agent",
            mock_handlers["handle_agent"],
            "Switch agent",
            ["name"]
        )

        handler, desc, args = command_registry.get("agent")
        assert handler is mock_handlers["handle_agent"]
        assert desc == "Switch agent"
        assert args == ["name"]

    def test_register_command_case_insensitive(self, command_registry, mock_handlers):
        """Test registration is case-insensitive"""
        command_registry.register(
            "HELP",
            mock_handlers["handle_help"],
            "Show help",
            []
        )

        # Should be retrievable with lowercase
        assert command_registry.has_command("help")
        assert command_registry.has_command("HELP")
        assert command_registry.has_command("HeLp")

    def test_register_batch(self, command_registry, mock_handlers):
        """Test batch registration of multiple commands"""
        commands = {
            "help": (mock_handlers["handle_help"], "Show help", []),
            "state": (mock_handlers["handle_state"], "Show state", []),
            "quit": (mock_handlers["handle_quit"], "Exit", []),
        }

        command_registry.register_batch(commands)

        assert command_registry.has_command("help")
        assert command_registry.has_command("state")
        assert command_registry.has_command("quit")
        assert len(command_registry.get_all_commands()) == 3

    def test_register_overwrites_existing(self, command_registry, mock_handlers):
        """Test registering same command twice overwrites"""
        command_registry.register(
            "help",
            mock_handlers["handle_help"],
            "Show help",
            []
        )

        new_handler = Mock()
        command_registry.register(
            "help",
            new_handler,
            "New help",
            ["optional"]
        )

        handler, desc, args = command_registry.get("help")
        assert handler is new_handler
        assert desc == "New help"
        assert args == ["optional"]


class TestCommandRegistryRetrieval:
    """Test CommandRegistry command retrieval"""

    def test_get_existing_command(self, command_registry, mock_handlers):
        """Test getting existing command"""
        command_registry.register(
            "help",
            mock_handlers["handle_help"],
            "Show help",
            []
        )

        result = command_registry.get("help")
        assert result is not None
        handler, desc, args = result
        assert handler is mock_handlers["handle_help"]

    def test_get_nonexistent_command(self, command_registry):
        """Test getting nonexistent command returns None"""
        result = command_registry.get("nonexistent")
        assert result is None

    def test_get_case_insensitive(self, command_registry, mock_handlers):
        """Test get is case-insensitive"""
        command_registry.register(
            "help",
            mock_handlers["handle_help"],
            "Show help",
            []
        )

        assert command_registry.get("HELP") is not None
        assert command_registry.get("HeLp") is not None
        assert command_registry.get("help") is not None

    def test_has_command_true(self, command_registry, mock_handlers):
        """Test has_command returns True for existing command"""
        command_registry.register(
            "help",
            mock_handlers["handle_help"],
            "Show help",
            []
        )

        assert command_registry.has_command("help") is True

    def test_has_command_false(self, command_registry):
        """Test has_command returns False for nonexistent command"""
        assert command_registry.has_command("nonexistent") is False

    def test_get_all_commands(self, command_registry, mock_handlers):
        """Test getting all registered commands"""
        command_registry.register("help", mock_handlers["handle_help"], "Help", [])
        command_registry.register("state", mock_handlers["handle_state"], "State", [])
        command_registry.register("quit", mock_handlers["handle_quit"], "Quit", [])

        all_commands = command_registry.get_all_commands()
        assert len(all_commands) == 3
        assert "help" in all_commands
        assert "state" in all_commands
        assert "quit" in all_commands

    def test_get_all_commands_is_copy(self, command_registry, mock_handlers):
        """Test get_all_commands returns a copy"""
        command_registry.register("help", mock_handlers["handle_help"], "Help", [])

        all_commands = command_registry.get_all_commands()
        all_commands["newcmd"] = (Mock(), "Test", [])

        # Original should be unchanged
        assert not command_registry.has_command("newcmd")


class TestCommandRegistryAvailableCommands:
    """Test CommandRegistry available commands filtering"""

    def test_get_available_commands_no_aliases(self, command_registry, mock_handlers):
        """Test getting available commands without aliases"""
        command_registry.register("help", mock_handlers["handle_help"], "Show help", [])
        command_registry.register("state", mock_handlers["handle_state"], "Show state", [])
        command_registry.register("quit", mock_handlers["handle_quit"], "Exit", [])

        available = command_registry.get_available_commands()
        assert len(available) == 3

        # Should be sorted
        assert available[0][0] == "help"
        assert available[1][0] == "quit"
        assert available[2][0] == "state"

    def test_get_available_commands_filters_aliases(self, command_registry, mock_handlers):
        """Test available commands filters out aliases"""
        # Register command with aliases
        command_registry.register("help", mock_handlers["handle_help"], "Show help", [])
        command_registry.register("h", mock_handlers["handle_help"], "Show help (alias)", [])
        command_registry.register("?", mock_handlers["handle_help"], "Show help (alias)", [])

        command_registry.register("state", mock_handlers["handle_state"], "Show state", [])
        command_registry.register("s", mock_handlers["handle_state"], "Show state (alias)", [])

        available = command_registry.get_available_commands()
        # Should only include unique handlers (help and state)
        assert len(available) == 2

        # Should pick first registered command name
        command_names = [cmd for cmd, _, _ in available]
        assert "help" in command_names
        assert "state" in command_names
        assert "h" not in command_names
        assert "s" not in command_names

    def test_get_command_names(self, command_registry, mock_handlers):
        """Test getting all command names including aliases"""
        command_registry.register("help", mock_handlers["handle_help"], "Show help", [])
        command_registry.register("h", mock_handlers["handle_help"], "Show help (alias)", [])
        command_registry.register("state", mock_handlers["handle_state"], "Show state", [])

        names = command_registry.get_command_names()
        assert len(names) == 3
        assert names == ["h", "help", "state"]  # Sorted

    def test_get_aliases(self, command_registry, mock_handlers):
        """Test getting all aliases for a handler"""
        command_registry.register("help", mock_handlers["handle_help"], "Show help", [])
        command_registry.register("h", mock_handlers["handle_help"], "Show help (alias)", [])
        command_registry.register("?", mock_handlers["handle_help"], "Show help (alias)", [])
        command_registry.register("state", mock_handlers["handle_state"], "Show state", [])

        aliases = command_registry.get_aliases(mock_handlers["handle_help"])
        assert len(aliases) == 3
        assert "help" in aliases
        assert "h" in aliases
        assert "?" in aliases

    def test_get_aliases_no_matches(self, command_registry):
        """Test getting aliases for unregistered handler"""
        unregistered_handler = Mock()
        aliases = command_registry.get_aliases(unregistered_handler)
        assert aliases == []


class TestCommandRegistryUnregister:
    """Test CommandRegistry command removal"""

    def test_unregister_existing(self, command_registry, mock_handlers):
        """Test unregistering existing command"""
        command_registry.register("help", mock_handlers["handle_help"], "Show help", [])

        result = command_registry.unregister("help")
        assert result is True
        assert not command_registry.has_command("help")

    def test_unregister_nonexistent(self, command_registry):
        """Test unregistering nonexistent command"""
        result = command_registry.unregister("nonexistent")
        assert result is False

    def test_unregister_case_insensitive(self, command_registry, mock_handlers):
        """Test unregister is case-insensitive"""
        command_registry.register("help", mock_handlers["handle_help"], "Show help", [])

        result = command_registry.unregister("HELP")
        assert result is True
        assert not command_registry.has_command("help")

    def test_clear_all_commands(self, command_registry, mock_handlers):
        """Test clearing all commands"""
        command_registry.register("help", mock_handlers["handle_help"], "Show help", [])
        command_registry.register("state", mock_handlers["handle_state"], "Show state", [])
        command_registry.register("quit", mock_handlers["handle_quit"], "Exit", [])

        assert len(command_registry.get_all_commands()) == 3

        command_registry.clear()

        assert len(command_registry.get_all_commands()) == 0
        assert not command_registry.has_command("help")
        assert not command_registry.has_command("state")
        assert not command_registry.has_command("quit")


class TestCommandRegistryEdgeCases:
    """Test CommandRegistry edge cases"""

    def test_register_with_none_args(self, command_registry, mock_handlers):
        """Test registering command with None args defaults to empty list"""
        command_registry.register(
            "help",
            mock_handlers["handle_help"],
            "Show help",
            None  # Explicitly None
        )

        handler, desc, args = command_registry.get("help")
        assert args == []  # Should default to empty list

    def test_register_empty_command_name(self, command_registry, mock_handlers):
        """Test registering with empty command name"""
        command_registry.register(
            "",
            mock_handlers["handle_help"],
            "Empty command",
            []
        )

        assert command_registry.has_command("")
        assert command_registry.get("") is not None

    def test_multiple_handlers_same_description(self, command_registry):
        """Test different handlers can have same description"""
        handler1 = Mock()
        handler2 = Mock()

        command_registry.register("cmd1", handler1, "Same description", [])
        command_registry.register("cmd2", handler2, "Same description", [])

        # Both should be registered separately
        assert command_registry.has_command("cmd1")
        assert command_registry.has_command("cmd2")

        h1, _, _ = command_registry.get("cmd1")
        h2, _, _ = command_registry.get("cmd2")
        assert h1 is handler1
        assert h2 is handler2
