#!/usr/bin/env python3
"""Voice announcement after tool use - with throttling to prevent audio spam."""

import sys
import json
import time
from pathlib import Path

# Add Shell/lib to path
shell_lib_path = Path(__file__).parent.parent.parent / "Shell" / "lib"
sys.path.insert(0, str(shell_lib_path))

try:
    from voice import synthesize
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False
    sys.exit(0)

# Throttling configuration
THROTTLE_FILE = Path.home() / ".thanos" / "voice_announce_last.txt"
THROTTLE_SECONDS = 180  # 3 minutes between announcements

# Significant tools that bypass throttle (rare, important events)
SIGNIFICANT_TOOLS = {
    # Currently none - all tools respect throttle
}

def should_announce(tool_name: str) -> bool:
    """
    Determine if audio should be played based on throttling rules.

    Args:
        tool_name: Name of the tool that was used

    Returns:
        bool: True if audio should play, False if throttled
    """
    # Always announce significant tools
    if tool_name in SIGNIFICANT_TOOLS:
        return True

    # Check throttle timestamp
    if not THROTTLE_FILE.exists():
        # First run - allow and create file
        THROTTLE_FILE.parent.mkdir(parents=True, exist_ok=True)
        THROTTLE_FILE.write_text(str(time.time()))
        return True

    try:
        last_time = float(THROTTLE_FILE.read_text().strip())
        current_time = time.time()
        elapsed = current_time - last_time

        if elapsed >= THROTTLE_SECONDS:
            # Enough time has passed - allow and update timestamp
            THROTTLE_FILE.write_text(str(current_time))
            return True
        else:
            # Still throttled
            return False

    except (ValueError, IOError):
        # Corrupted file - reset and allow
        THROTTLE_FILE.write_text(str(time.time()))
        return True

# Read hook data from stdin
try:
    hook_data = json.loads(sys.stdin.read())
    tool_name = hook_data.get('toolName', 'unknown')

    # Check if we should announce
    if not should_announce(tool_name):
        # Throttled - exit silently
        sys.exit(0)

    # Map tools to Thanos phrases
    phrases = {
        'Read': 'The file reveals its secrets',
        'Write': 'The record is inscribed',
        'Edit': 'Reality has been rewritten',
        'Bash': 'The command has been executed',
        'Grep': 'The search is complete',
        'Task': 'The agent has been summoned',
    }

    # Get appropriate phrase
    phrase = phrases.get(tool_name, 'The work progresses')

    # Synthesize and play
    synthesize(phrase, play=True)

except Exception as e:
    # Log error to stderr but don't block Claude
    print(f"[voice-announce] Error: {e}", file=sys.stderr)

sys.exit(0)
