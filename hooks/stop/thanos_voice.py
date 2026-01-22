#!/usr/bin/env python3
"""
Thanos Stop Hook Voice Synthesis

Plays a random Thanos-themed message when a Claude Code session ends.
Uses pre-cached audio for instant playback without API calls.
"""

import sys
import os
import random
from pathlib import Path

# Suppress ALL output immediately to avoid hook framework errors
sys.stdout = open(os.devnull, 'w')
sys.stderr = open(os.devnull, 'w')

# Add Shell/lib to path for voice module
shell_lib_path = Path(__file__).parent.parent.parent / "Shell" / "lib"
sys.path.insert(0, str(shell_lib_path))

try:
    from voice import synthesize
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False


# Thanos Stop Messages (matches precache script)
THANOS_MESSAGES = [
    "The work is done. The universe is grateful.",
    "You could not live with your own failure. Where did that bring you? Back to me.",
    "I am inevitable.",
    "The hardest choices require the strongest wills.",
    "A small price to pay for salvation.",
    "Perfectly balanced, as all things should be.",
    "You should have gone for the head.",
    "I ignored my destiny once. I cannot do that again.",
    "Fun isn't something one considers when balancing the universe. But this does put a smile on my face.",
    "Reality is often disappointing.",
    "I know what it's like to lose. To feel so desperately that you're right, yet to fail nonetheless.",
    "The strongest choices require the strongest wills.",
    "Dread it. Run from it. Destiny arrives all the same.",
    "I will shred this universe down to its last atom.",
    "You're not the only one cursed with knowledge.",
    "The work is complete. Rest now.",
    "I have finally found the courage to do what I must.",
    "The universe required correction.",
]


def select_thanos_message() -> str:
    """
    Select a random Thanos message for the Stop event.

    Returns:
        A randomly selected Thanos quote
    """
    return random.choice(THANOS_MESSAGES)


def main():
    """Main entry point - synthesizes and plays a Thanos stop message."""
    if not VOICE_AVAILABLE:
        # Voice module not available, exit silently
        sys.exit(0)

    # Select message
    message = select_thanos_message()

    try:
        # Synthesize and play
        # Note: cache=True by default, so this uses cached audio if available
        audio_path = synthesize(message, play=True)

        if audio_path:
            # Success - audio is playing in background
            pass
        else:
            # Failed to synthesize, but don't block session stop
            pass

    except Exception:
        # Silently ignore errors - never block session finalization
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
