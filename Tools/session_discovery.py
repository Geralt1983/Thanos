#!/usr/bin/env python3
"""
Session Discovery Utility

Discovers Claude Code session context from the filesystem instead of relying
on stdin (which has issues with passStdin in hooks).

Works by:
1. Finding the most recently modified session transcript in ~/.claude/projects/
2. Extracting session_id from the filename
3. Inferring project/client from the working directory

This is a workaround for Claude Code's passStdin not reliably delivering data.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


def find_active_session(max_age_seconds: int = 60) -> Optional[Dict[str, Any]]:
    """
    Find the currently active Claude Code session by looking for
    recently modified transcript files.

    Args:
        max_age_seconds: Only consider sessions modified within this many seconds

    Returns:
        Dict with session_id, transcript_path, cwd, or None if not found
    """
    claude_projects = Path.home() / '.claude' / 'projects'

    if not claude_projects.exists():
        return None

    # Find all .jsonl transcript files
    transcripts = list(claude_projects.rglob('*.jsonl'))

    if not transcripts:
        return None

    # Sort by modification time, most recent first
    now = time.time()
    recent_transcripts = []

    for t in transcripts:
        try:
            mtime = t.stat().st_mtime
            age = now - mtime
            if age <= max_age_seconds:
                recent_transcripts.append((t, mtime, age))
        except (OSError, IOError):
            continue

    if not recent_transcripts:
        # Fall back to most recent regardless of age
        try:
            latest = max(transcripts, key=lambda p: p.stat().st_mtime)
            mtime = latest.stat().st_mtime
            age = now - mtime
            recent_transcripts = [(latest, mtime, age)]
        except (OSError, IOError, ValueError):
            return None

    # Sort by recency
    recent_transcripts.sort(key=lambda x: x[1], reverse=True)

    # Get the most recent
    transcript_path, mtime, age = recent_transcripts[0]
    session_id = transcript_path.stem

    return {
        'session_id': session_id,
        'transcript_path': str(transcript_path),
        'last_modified': datetime.fromtimestamp(mtime).isoformat(),
        'age_seconds': age,
        'cwd': os.getcwd()
    }


def try_read_stdin() -> Optional[Dict[str, Any]]:
    """
    Try to read session data from stdin (original method).
    Returns None if stdin is empty or not available.
    """
    try:
        # Don't block if stdin is a tty or empty
        if sys.stdin.isatty():
            return None

        # Try to read with a very short timeout approach
        import select
        if hasattr(select, 'select'):
            # Unix: check if there's data available
            readable, _, _ = select.select([sys.stdin], [], [], 0.1)
            if not readable:
                return None

        content = sys.stdin.read()
        if not content or not content.strip():
            return None

        return json.loads(content)
    except (json.JSONDecodeError, IOError, OSError, Exception):
        return None


def discover_session_context(
    prefer_stdin: bool = True,
    max_age_seconds: int = 60
) -> Dict[str, Any]:
    """
    Discover session context using multiple methods.

    Priority:
    1. stdin (if prefer_stdin=True and data available)
    2. Environment variables
    3. Filesystem discovery
    4. Generated fallback

    Args:
        prefer_stdin: Try stdin first before filesystem
        max_age_seconds: Max age for filesystem session discovery

    Returns:
        Dict with session_id, cwd, and optionally transcript_path
    """
    context = {}
    source = 'unknown'

    # Method 1: Try stdin if preferred
    if prefer_stdin:
        stdin_data = try_read_stdin()
        if stdin_data and stdin_data.get('session_id'):
            context = stdin_data
            source = 'stdin'

    # Method 2: Environment variables
    if not context.get('session_id'):
        env_session = os.environ.get('CLAUDE_SESSION_ID')
        if env_session:
            context['session_id'] = env_session
            context['cwd'] = os.environ.get('CLAUDE_CWD') or os.getcwd()
            source = 'environment'

    # Method 3: Filesystem discovery
    if not context.get('session_id'):
        fs_context = find_active_session(max_age_seconds)
        if fs_context:
            context = fs_context
            source = 'filesystem'

    # Method 4: Fallback - generate session ID
    if not context.get('session_id'):
        context['session_id'] = f"fallback_{int(time.time())}_{os.getpid()}"
        context['cwd'] = os.getcwd()
        source = 'fallback'

    # Ensure cwd is always set
    if 'cwd' not in context:
        context['cwd'] = os.getcwd()

    context['_discovery_source'] = source

    return context


def infer_project_client(cwd: str) -> tuple:
    """
    Infer project and client from working directory.

    Returns:
        (project, client) tuple
    """
    cwd_lower = cwd.lower()
    project = None
    client = None

    # Known project patterns
    if 'thanos' in cwd_lower:
        project = 'thanos'
    elif 'versacare' in cwd_lower or 'kentucky' in cwd_lower:
        project = 'versacare'
        client = 'kentucky'

    # Known client patterns
    if 'orlando' in cwd_lower:
        client = 'orlando'
    elif 'memphis' in cwd_lower:
        client = 'memphis'
    elif 'raleigh' in cwd_lower:
        client = 'raleigh'

    return project, client


if __name__ == '__main__':
    # CLI for testing
    import argparse

    parser = argparse.ArgumentParser(description='Discover Claude session context')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--max-age', type=int, default=60, help='Max session age in seconds')
    args = parser.parse_args()

    context = discover_session_context(max_age_seconds=args.max_age)
    project, client = infer_project_client(context.get('cwd', ''))
    context['project'] = project
    context['client'] = client

    if args.json:
        print(json.dumps(context, indent=2))
    else:
        print(f"Session ID: {context.get('session_id')}")
        print(f"Source: {context.get('_discovery_source')}")
        print(f"CWD: {context.get('cwd')}")
        print(f"Transcript: {context.get('transcript_path', 'N/A')}")
        print(f"Project: {project or 'N/A'}")
        print(f"Client: {client or 'N/A'}")
