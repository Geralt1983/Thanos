#!/usr/bin/env python3
"""
Thanos Voice Synthesis

ElevenLabs TTS integration with aggressive caching.
The voice of inevitability.
"""

import os
import hashlib
import requests
from pathlib import Path
from typing import Optional
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("thanos.voice")

# Configuration
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
THANOS_VOICE_ID = os.getenv("THANOS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Default voice
AUDIO_CACHE_DIR = Path.home() / ".thanos" / "audio-cache"
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# API endpoint
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech"


class VoiceSynthesizer:
    """Thanos voice synthesis with caching."""

    def __init__(self, api_key: Optional[str] = None, voice_id: Optional[str] = None):
        self.api_key = api_key or ELEVENLABS_API_KEY
        self.voice_id = voice_id or THANOS_VOICE_ID
        self.cache_dir = AUDIO_CACHE_DIR

        if not self.api_key:
            logger.warning("No ELEVENLABS_API_KEY set - voice synthesis disabled")

    def synthesize(
        self, text: str, play: bool = True, cache: bool = True
    ) -> Optional[Path]:
        """
        Synthesize speech from text.

        Args:
            text: Text to synthesize
            play: Whether to play immediately
            cache: Whether to use/update cache

        Returns:
            Path to audio file, or None if synthesis fails
        """
        if not self.api_key:
            logger.warning("Voice synthesis skipped - no API key")
            return None

        # Check cache first
        if cache:
            cache_key = self._get_cache_key(text)
            audio_path = self.cache_dir / f"{cache_key}.mp3"

            if audio_path.exists():
                logger.info(f"Cache hit for: {text[:50]}...")
                if play:
                    self._play_audio(audio_path)
                return audio_path

        # Call ElevenLabs API
        try:
            audio_data = self._call_api(text)

            if cache:
                audio_path = self.cache_dir / f"{cache_key}.mp3"
                audio_path.write_bytes(audio_data)
                logger.info(f"Cached audio: {cache_key}")
            else:
                # Temp file
                import tempfile

                fd, temp_path = tempfile.mkstemp(suffix=".mp3")
                os.close(fd)
                audio_path = Path(temp_path)
                audio_path.write_bytes(audio_data)

            if play:
                self._play_audio(audio_path)

            return audio_path

        except Exception as e:
            logger.error(f"Voice synthesis failed: {e}")
            return None

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text."""
        # Include voice_id in hash to support multiple voices
        content = f"{self.voice_id}:{text}"
        return hashlib.md5(content.encode()).hexdigest()

    def _call_api(self, text: str) -> bytes:
        """Call ElevenLabs API."""
        url = f"{ELEVENLABS_API_URL}/{self.voice_id}"

        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        data = {
            "text": text,
            "model_id": "eleven_turbo_v2_5",  # Free tier model (v2.5)
            "voice_settings": {
                "stability": 0.75,
                "similarity_boost": 0.85,
                "style": 0.5,
                "use_speaker_boost": True,
            },
        }

        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()

        return response.content

    def _play_audio(self, audio_path: Path) -> None:
        """Play audio file (macOS only for now)."""
        try:
            # Use afplay on macOS
            os.system(f"afplay '{audio_path}' >/dev/null 2>&1 &")
        except Exception as e:
            logger.error(f"Audio playback failed: {e}")

    def clear_cache(self) -> int:
        """Clear all cached audio files."""
        count = 0
        for audio_file in self.cache_dir.glob("*.mp3"):
            audio_file.unlink()
            count += 1

        logger.info(f"Cleared {count} cached audio files")
        return count

    def cache_stats(self) -> dict:
        """Get cache statistics."""
        files = list(self.cache_dir.glob("*.mp3"))
        total_size = sum(f.stat().st_size for f in files)

        return {
            "file_count": len(files),
            "total_size_mb": total_size / (1024 * 1024),
            "cache_dir": str(self.cache_dir),
        }


# Global instance
_synthesizer = None


def get_synthesizer() -> VoiceSynthesizer:
    """Get or create global synthesizer instance."""
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = VoiceSynthesizer()
    return _synthesizer


def synthesize(text: str, play: bool = True) -> Optional[Path]:
    """
    Convenience function for voice synthesis.

    Args:
        text: Text to synthesize
        play: Whether to play immediately

    Returns:
        Path to audio file, or None if synthesis fails
    """
    synth = get_synthesizer()
    return synth.synthesize(text, play=play)


def main():
    """CLI entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 voice.py <command> [args]")
        print("\nCommands:")
        print("  synthesize <text>  - Synthesize and play text")
        print("  cache-stats        - Show cache statistics")
        print("  clear-cache        - Clear audio cache")
        sys.exit(1)

    command = sys.argv[1]
    synth = get_synthesizer()

    if command == "synthesize":
        if len(sys.argv) < 3:
            print("Error: Missing text argument")
            sys.exit(1)

        text = " ".join(sys.argv[2:])
        result = synth.synthesize(text, play=True)

        if result:
            print(f"✓ Synthesized: {result}")
        else:
            print("✗ Synthesis failed")

    elif command == "cache-stats":
        stats = synth.cache_stats()
        print(f"Cache: {stats['file_count']} files, {stats['total_size_mb']:.2f} MB")
        print(f"Location: {stats['cache_dir']}")

    elif command == "clear-cache":
        count = synth.clear_cache()
        print(f"✓ Cleared {count} files")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
