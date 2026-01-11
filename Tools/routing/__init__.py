"""
Thanos Routing System

Modular routing components for command dispatching and persona detection:

- persona_router: PersonaRouter class for agent detection and intelligent routing
- command_registry: CommandRegistry class for command registration and lookup

These modules handle the routing logic previously embedded in command_router.py,
enabling better separation of concerns and testability.

Usage:
    from Tools.routing import PersonaRouter, CommandRegistry

    persona_router = PersonaRouter()
    agent_type = persona_router.detect_agent(message)

    registry = CommandRegistry()
    registry.register('help', handler.handle_help)
    result = registry.route_command('help', args)
"""

from .persona_router import PersonaRouter
from .command_registry import CommandRegistry

__all__ = [
    "PersonaRouter",
    "CommandRegistry",
]
