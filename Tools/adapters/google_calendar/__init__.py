"""
Google Calendar Adapter Package

Exposes the GoogleCalendarAdapter, currently implemented in legacy.py.
Future refactoring will split this into focused modules.
"""

from .legacy import GoogleCalendarAdapter

__all__ = ["GoogleCalendarAdapter"]
