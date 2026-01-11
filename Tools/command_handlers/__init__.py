"""
Thanos Command Handlers

Modular command handlers for the Thanos command router.
Each handler module manages a specific category of commands:

- agent_handler: Agent management (/agent, /agents)
- session_handler: Session management (/clear, /save, /sessions, etc.)
- state_handler: State and context (/state, /commitments, /context, /usage)
- memory_handler: MemOS integration (/remember, /recall, /memory)
- analytics_handler: Analytics and patterns (/patterns)
- model_handler: Model management (/model)
- core_handler: Core commands (/help, /quit, /run)

All handlers inherit from BaseHandler which provides shared utilities
including Colors, CommandResult, CommandAction, and dependency access.

Usage:
    from Tools.command_handlers import AgentHandler, SessionHandler

    agent_handler = AgentHandler(colors, dependencies)
    result = agent_handler.handle_agent_command(args)
"""

from Tools.command_handlers.base import (
    BaseHandler,
    Colors,
    CommandAction,
    CommandResult,
)
from Tools.command_handlers.agent_handler import AgentHandler
from Tools.command_handlers.session_handler import SessionHandler
from Tools.command_handlers.state_handler import StateHandler
from Tools.command_handlers.memory_handler import MemoryHandler
from Tools.command_handlers.analytics_handler import AnalyticsHandler

__all__ = [
    "BaseHandler",
    "Colors",
    "CommandAction",
    "CommandResult",
    "AgentHandler",
    "SessionHandler",
    "StateHandler",
    "MemoryHandler",
    "AnalyticsHandler",
]
