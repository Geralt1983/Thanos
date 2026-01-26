"""
Command Handlers Module

Provides handlers for user commands that control Thanos behavior.
"""

from .core_handler import handle_more_context, handle_less_context

__all__ = [
    'handle_more_context',
    'handle_less_context',
]
