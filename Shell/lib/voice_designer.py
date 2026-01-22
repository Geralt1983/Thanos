#!/usr/bin/env python3
"""
Thanos Voice Designer

Create custom voice using ElevenLabs Text-to-Voice API.
Design voices from text descriptions, preview them, and save the best.
"""

import os
import base64
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
import json
import tempfile

load_dotenv()


class VoiceDesigner:
    """Design and create custom voices via ElevenLabs API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('ELEVENLABS_API_KEY')
        self.base_url = "https://api.elevenlabs.io/v1"

        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY not set")

    def design_voice(
        self,
        description: str,
        model_id: str = "eleven_ttv_v3",
        auto_generate_text: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Generate voice previews from text description.

        Args:
            description: Detailed voice characteristics
            model_id: TTV model to use (eleven_ttv_v3 recommended)
            auto_generate_text: Let API generate preview text

        Returns:
            List of preview objects with generated_voice_id and audio
        """
        url = f"{self.base_url}/text-to-voice/design"

        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        payload = {
            "voice_description": description,
            "model_id": model_id,
            "auto_generate_text": auto_generate_text
        }

        print(f"Designing voices with description:")
        print(f'  "{description}"')
        print()

        response = requests.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()

        data = response.json()
        previews = data.get("previews", [])

        print(f"✅ Generated {len(previews)} voice previews")
        return previews

    def save_preview_audio(
        self,
        preview: Dict[str, Any],
        output_dir: Optional[Path] = None
    ) -> Path:
        """
        Save preview audio to file.

        Args:
            preview: Preview object with audio_base_64
            output_dir: Directory to save audio (default: temp)

        Returns:
            Path to saved audio file
        """
        audio_b64 = preview.get("audio_base_64")
        if not audio_b64:
            raise ValueError("No audio data in preview")

        # Decode base64 audio
        audio_bytes = base64.b64decode(audio_b64)

        # Save to file
        if output_dir is None:
            output_dir = Path(tempfile.gettempdir()) / "thanos-voice-previews"

        output_dir.mkdir(parents=True, exist_ok=True)

        voice_id = preview.get("generated_voice_id", "preview")
        output_path = output_dir / f"{voice_id}.mp3"

        output_path.write_bytes(audio_bytes)
        return output_path

    def play_preview(self, preview: Dict[str, Any]) -> None:
        """
        Play preview audio (macOS).

        Args:
            preview: Preview object with audio
        """
        audio_path = self.save_preview_audio(preview)

        print(f"Playing preview: {audio_path.name}")
        print(f"  Duration: {preview.get('duration_secs', 'unknown')}s")

        # Play with afplay (macOS)
        os.system(f"afplay '{audio_path}'")

    def create_voice(
        self,
        generated_voice_id: str,
        voice_name: str,
        voice_description: str
    ) -> str:
        """
        Save a preview as a permanent voice.

        Args:
            generated_voice_id: ID from design preview
            voice_name: Name for the voice (e.g., "Thanos")
            voice_description: Description for reference

        Returns:
            Permanent voice_id to use for TTS
        """
        url = f"{self.base_url}/text-to-voice/create"

        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        payload = {
            "voice_name": voice_name,
            "voice_description": voice_description,
            "generated_voice_id": generated_voice_id
        }

        print(f"Saving voice as '{voice_name}'...")

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()
        voice_id = data.get("voice_id")

        print(f"✅ Voice saved with ID: {voice_id}")
        return voice_id

    def interactive_design(
        self,
        description: str,
        voice_name: str = "Thanos"
    ) -> Optional[str]:
        """
        Interactive voice design workflow.

        Args:
            description: Voice characteristics
            voice_name: Name to save voice as

        Returns:
            voice_id if saved, None if cancelled
        """
        print("=" * 60)
        print("THANOS VOICE DESIGNER")
        print("=" * 60)
        print()

        # Generate previews
        try:
            previews = self.design_voice(description)
        except Exception as e:
            print(f"❌ Design failed: {e}")
            return None

        if not previews:
            print("❌ No previews generated")
            return None

        # Save all previews
        print()
        print(f"Saving {len(previews)} previews...")
        preview_paths = []

        for i, preview in enumerate(previews, 1):
            path = self.save_preview_audio(preview)
            preview_paths.append(path)
            duration = preview.get("duration_secs", "?")
            print(f"  Preview {i}: {path.name} ({duration}s)")

        print()
        print("=" * 60)
        print()

        # Play previews
        for i, preview in enumerate(previews, 1):
            print(f"Playing Preview {i}/{len(previews)}...")
            self.play_preview(preview)
            print()

        # Select best
        print("=" * 60)
        print()
        print("Which preview sounds most like inevitability?")

        while True:
            choice = input(f"Enter number (1-{len(previews)}, or 'n' to cancel): ").strip()

            if choice.lower() == 'n':
                print("Cancelled.")
                return None

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(previews):
                    break
                else:
                    print(f"Invalid choice. Enter 1-{len(previews)}")
            except ValueError:
                print(f"Invalid input. Enter 1-{len(previews)} or 'n'")

        # Save selected voice
        selected = previews[idx]
        print()
        print(f"Saving Preview {idx + 1} as permanent voice...")

        try:
            voice_id = self.create_voice(
                generated_voice_id=selected["generated_voice_id"],
                voice_name=voice_name,
                voice_description=description
            )

            print()
            print("=" * 60)
            print(f"SUCCESS! Voice ID: {voice_id}")
            print()
            print("Add this to your .env:")
            print(f"THANOS_VOICE_ID={voice_id}")
            print("=" * 60)

            return voice_id

        except Exception as e:
            print(f"❌ Failed to save voice: {e}")
            return None


def main():
    """CLI entry point."""

    # Thanos voice description
    THANOS_DESCRIPTION = (
        "A deep, gravelly male voice with immense gravitas and authority. "
        "Middle-aged titan with resonant, rumbling bass tones. "
        "Speaks slowly and deliberately with philosophical weight. "
        "Calm yet menacing undertone, like distant thunder. "
        "Perfect clarity and audio quality."
    )

    try:
        designer = VoiceDesigner()
        voice_id = designer.interactive_design(
            description=THANOS_DESCRIPTION,
            voice_name="Thanos"
        )

        if voice_id:
            # Update .env file
            env_path = Path(__file__).parent.parent.parent / '.env'

            if env_path.exists():
                print()
                print("Updating .env file...")

                # Read existing .env
                env_content = env_path.read_text()

                # Update or add THANOS_VOICE_ID
                if 'THANOS_VOICE_ID=' in env_content:
                    # Replace existing
                    import re
                    env_content = re.sub(
                        r'THANOS_VOICE_ID=.*',
                        f'THANOS_VOICE_ID={voice_id}',
                        env_content
                    )
                else:
                    # Add new
                    env_content += f'\n# Thanos Custom Voice\nTHANOS_VOICE_ID={voice_id}\n'

                env_path.write_text(env_content)
                print("✅ .env updated")

            print()
            print("The voice of inevitability is ready.")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
