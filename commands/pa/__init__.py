"""
Personal Assistant Commands

Quick commands for daily productivity:
- daily     : Morning briefing
- email     : Email management
- schedule  : Calendar management
- tasks     : Task management
- brainstorm: Idea generation
- process   : Brain dump processing
- weekly    : Weekly review
"""

from . import brainstorm, daily, email, process, schedule, tasks, weekly


__all__ = ["daily", "email", "schedule", "tasks", "brainstorm", "process", "weekly"]
