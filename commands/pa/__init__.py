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

from . import brainstorm, daily, email, schedule, tasks, weekly


__all__ = ['daily', 'email', 'schedule', 'tasks', 'brainstorm', 'weekly']
