"""
Personal Assistant Commands

Quick commands for daily productivity:
- daily     : Morning briefing
- email     : Email management
- schedule  : Calendar management
- tasks     : Task management
- brainstorm: Idea generation
- weekly    : Weekly review
"""

from . import daily
from . import email
from . import schedule
from . import tasks
from . import brainstorm
from . import weekly

__all__ = ['daily', 'email', 'schedule', 'tasks', 'brainstorm', 'weekly']
