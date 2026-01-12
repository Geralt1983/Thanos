"""
Personal Assistant Commands

Quick commands for daily productivity:
- briefing  : Manual briefing generation
- briefing_config : Briefing configuration management
"""

# Only import modules that exist in this worktree
from . import briefing, briefing_config


__all__ = ["briefing", "briefing_config"]
