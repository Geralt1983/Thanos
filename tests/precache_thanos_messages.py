#!/usr/bin/env python3
"""
Pre-cache Thanos Stop Messages

Generates and caches all possible Thanos stop messages using ElevenLabs TTS.
This ensures fast playback during Stop events with no API calls needed.
"""

import sys
from pathlib import Path

# Add Shell/lib to path
shell_lib = Path(__file__).parent.parent / "Shell" / "lib"
sys.path.insert(0, str(shell_lib))

from voice import VoiceSynthesizer

# Thanos Stop Messages
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


def main():
    """Pre-cache all Thanos messages."""
    print("🎯 Pre-caching Thanos Stop messages...")
    print(f"Total messages: {len(THANOS_MESSAGES)}\n")

    synth = VoiceSynthesizer()

    if not synth.api_key:
        print("❌ ERROR: ELEVENLABS_API_KEY not found in environment")
        print("Please set your API key in .env file")
        sys.exit(1)

    print(f"Voice ID: {synth.voice_id}")
    print(f"Cache dir: {synth.cache_dir}\n")

    success_count = 0
    cache_hit_count = 0
    error_count = 0

    for i, message in enumerate(THANOS_MESSAGES, 1):
        print(f"[{i}/{len(THANOS_MESSAGES)}] {message[:60]}...")

        # Check if already cached
        cache_key = synth._get_cache_key(message)
        audio_path = synth.cache_dir / f"{cache_key}.mp3"

        if audio_path.exists():
            print(f"    ✓ Already cached: {cache_key}.mp3")
            cache_hit_count += 1
            success_count += 1
            continue

        # Synthesize and cache
        try:
            result = synth.synthesize(message, play=False, cache=True)
            if result and result.exists():
                size_kb = result.stat().st_size / 1024
                print(f"    ✓ Cached: {cache_key}.mp3 ({size_kb:.1f} KB)")
                success_count += 1
            else:
                print(f"    ✗ Failed to synthesize")
                error_count += 1
        except Exception as e:
            print(f"    ✗ Error: {e}")
            error_count += 1

        print()

    # Summary
    print("=" * 70)
    print(f"✓ Successfully cached: {success_count}/{len(THANOS_MESSAGES)}")
    print(f"  - New: {success_count - cache_hit_count}")
    print(f"  - Already cached: {cache_hit_count}")

    if error_count > 0:
        print(f"✗ Errors: {error_count}")

    # Cache stats
    stats = synth.cache_stats()
    print(f"\n📊 Cache Statistics:")
    print(f"  - Total files: {stats['file_count']}")
    print(f"  - Total size: {stats['total_size_mb']:.2f} MB")
    print(f"  - Location: {stats['cache_dir']}")

    if error_count > 0:
        sys.exit(1)
    else:
        print("\n🎯 All messages successfully cached!")


if __name__ == "__main__":
    main()
