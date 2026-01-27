#!/usr/bin/env python3
"""
Environment Detector for Thanos

This module detects and validates API keys and integration configurations
in the environment. It provides methods to check for required and optional
API keys, validate their format, and return masked values for display.

Usage:
    from Tools.env_detector import EnvDetector

    detector = EnvDetector()
    if detector.has_anthropic_key():
        print("Anthropic API key found!")

    status = detector.get_integration_status()
    print(f"Available integrations: {status}")
"""

import os
from pathlib import Path
from typing import Dict, Optional, List, Tuple

# Load dotenv if available, otherwise work with existing environment
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    load_dotenv = None


class EnvDetector:
    """
    Detects and validates API keys and integration configurations.

    This class scans for .env files, loads environment variables, and provides
    methods to check for the presence and validity of various API keys needed
    for Thanos integrations.
    """

    # Required API keys (minimum for basic functionality)
    REQUIRED_KEYS = [
        "ANTHROPIC_API_KEY",
    ]

    # Recommended API keys (enhanced features)
    RECOMMENDED_KEYS = [
        "OPENAI_API_KEY",
    ]

    # Optional integration keys
    OPTIONAL_KEYS = {
        "google_calendar": [
            "GOOGLE_CALENDAR_CLIENT_ID",
            "GOOGLE_CALENDAR_CLIENT_SECRET",
        ],
        "oura": [
            "OURA_PERSONAL_ACCESS_TOKEN",
        ],
    }

    def __init__(self, env_path: Optional[Path] = None):
        """
        Initialize the environment detector.

        Args:
            env_path: Optional path to .env file. If not provided, searches
                     for .env in the project root.
        """
        self.project_root = self._find_project_root()
        self.env_path = env_path or self.project_root / ".env"
        self.env_exists = self.env_path.exists()

        # Load environment variables from .env if it exists and dotenv is available
        if self.env_exists and DOTENV_AVAILABLE and load_dotenv:
            load_dotenv(self.env_path)

    def _find_project_root(self) -> Path:
        """
        Find the project root directory by looking for marker files.

        Returns:
            Path to the project root directory.
        """
        current = Path(__file__).resolve().parent

        # Go up from Tools/ to project root
        while current != current.parent:
            # Check for marker files that indicate project root
            if (current / "thanos.py").exists() or (current / ".git").exists():
                return current
            current = current.parent

        # Fallback to parent of Tools/
        return Path(__file__).resolve().parent.parent

    def has_env_file(self) -> bool:
        """
        Check if a .env file exists.

        Returns:
            True if .env file exists, False otherwise.
        """
        return self.env_exists

    def has_anthropic_key(self) -> bool:
        """
        Check if Anthropic API key is configured.

        Returns:
            True if ANTHROPIC_API_KEY is set and non-empty, False otherwise.
        """
        return self._has_key("ANTHROPIC_API_KEY")

    def has_openai_key(self) -> bool:
        """
        Check if OpenAI API key is configured.

        Returns:
            True if OPENAI_API_KEY is set and non-empty, False otherwise.
        """
        return self._has_key("OPENAI_API_KEY")

    def has_google_calendar(self) -> bool:
        """
        Check if Google Calendar integration is configured.

        Returns:
            True if all required Google Calendar keys are set, False otherwise.
        """
        return all(
            self._has_key(key)
            for key in self.OPTIONAL_KEYS["google_calendar"]
        )

    def has_oura(self) -> bool:
        """
        Check if Oura Ring integration is configured.

        Returns:
            True if OURA_PERSONAL_ACCESS_TOKEN is set, False otherwise.
        """
        return all(
            self._has_key(key)
            for key in self.OPTIONAL_KEYS["oura"]
        )

    def _has_key(self, key_name: str) -> bool:
        """
        Check if an environment variable is set and non-empty.

        Args:
            key_name: Name of the environment variable to check.

        Returns:
            True if the key is set and non-empty, False otherwise.
        """
        value = os.environ.get(key_name, "").strip()
        return bool(value)

    def get_key_value(self, key_name: str, masked: bool = True) -> Optional[str]:
        """
        Get the value of an environment variable, optionally masked.

        Args:
            key_name: Name of the environment variable.
            masked: If True, return a masked version for display. Default True.

        Returns:
            The key value (masked or unmasked), or None if not set.
        """
        value = os.environ.get(key_name, "").strip()
        if not value:
            return None

        if masked:
            return self._mask_value(value)
        return value

    def _mask_value(self, value: str, show_chars: int = 10) -> str:
        """
        Mask a value for safe display.

        Args:
            value: The value to mask.
            show_chars: Number of characters to show at the start. Default 10.

        Returns:
            Masked value in format "first_chars..."
        """
        if len(value) <= show_chars:
            # For short values, show partial
            return value[:4] + "..."
        return value[:show_chars] + "..."

    def validate_key_format(self, key_name: str) -> Tuple[bool, Optional[str]]:
        """
        Perform basic validation on a key's format.

        Args:
            key_name: Name of the environment variable to validate.

        Returns:
            Tuple of (is_valid, error_message). error_message is None if valid.
        """
        value = os.environ.get(key_name, "").strip()

        if not value:
            return False, f"{key_name} is not set"

        # Basic validation rules by key type
        if key_name == "ANTHROPIC_API_KEY":
            if not value.startswith("sk-ant-"):
                return False, "Anthropic API key should start with 'sk-ant-'"
            if len(value) < 20:
                return False, "Anthropic API key seems too short"

        elif key_name == "OPENAI_API_KEY":
            if not value.startswith("sk-"):
                return False, "OpenAI API key should start with 'sk-'"
            if len(value) < 20:
                return False, "OpenAI API key seems too short"

        elif key_name == "GOOGLE_CALENDAR_CLIENT_ID":
            if not value.endswith(".apps.googleusercontent.com"):
                return False, "Google Calendar Client ID should end with '.apps.googleusercontent.com'"

        elif key_name == "GOOGLE_CALENDAR_CLIENT_SECRET":
            if not value.startswith("GOCSPX-") and len(value) < 20:
                return False, "Google Calendar Client Secret format seems incorrect"

        elif key_name == "OURA_PERSONAL_ACCESS_TOKEN":
            if len(value) < 20:
                return False, "Oura token seems too short"

        return True, None

    def get_missing_required_keys(self) -> List[str]:
        """
        Get a list of required keys that are missing.

        Returns:
            List of missing required key names.
        """
        return [key for key in self.REQUIRED_KEYS if not self._has_key(key)]

    def get_missing_recommended_keys(self) -> List[str]:
        """
        Get a list of recommended keys that are missing.

        Returns:
            List of missing recommended key names.
        """
        return [key for key in self.RECOMMENDED_KEYS if not self._has_key(key)]

    def get_integration_status(self) -> Dict[str, bool]:
        """
        Get the status of all integrations.

        Returns:
            Dictionary mapping integration names to their availability status.
        """
        return {
            "anthropic": self.has_anthropic_key(),
            "openai": self.has_openai_key(),
            "google_calendar": self.has_google_calendar(),
            "oura": self.has_oura(),
        }

    def get_summary(self) -> Dict[str, any]:
        """
        Get a comprehensive summary of environment configuration.

        Returns:
            Dictionary containing:
                - env_file_exists: bool
                - required_keys_present: List[str]
                - required_keys_missing: List[str]
                - recommended_keys_present: List[str]
                - recommended_keys_missing: List[str]
                - integrations: Dict[str, bool]
        """
        required_present = [key for key in self.REQUIRED_KEYS if self._has_key(key)]
        required_missing = self.get_missing_required_keys()

        recommended_present = [key for key in self.RECOMMENDED_KEYS if self._has_key(key)]
        recommended_missing = self.get_missing_recommended_keys()

        return {
            "env_file_exists": self.env_exists,
            "env_path": str(self.env_path),
            "required_keys_present": required_present,
            "required_keys_missing": required_missing,
            "recommended_keys_present": recommended_present,
            "recommended_keys_missing": recommended_missing,
            "integrations": self.get_integration_status(),
        }

    def print_status(self) -> None:
        """
        Print a formatted status report of all environment configurations.
        """
        print("\n" + "="*70)
        print("  Environment Configuration Status")
        print("="*70 + "\n")

        # .env file status
        if self.env_exists:
            print(f"✓ .env file found at: {self.env_path}")
        else:
            print(f"✗ No .env file found at: {self.env_path}")

        print("\n" + "-"*70)
        print("  Required Keys (minimum for basic functionality)")
        print("-"*70)

        for key in self.REQUIRED_KEYS:
            if self._has_key(key):
                masked = self.get_key_value(key, masked=True)
                is_valid, error = self.validate_key_format(key)
                if is_valid:
                    print(f"✓ {key}: {masked}")
                else:
                    print(f"⚠️  {key}: {masked} (Warning: {error})")
            else:
                print(f"✗ {key}: NOT SET")

        print("\n" + "-"*70)
        print("  Recommended Keys (enhanced features)")
        print("-"*70)

        for key in self.RECOMMENDED_KEYS:
            if self._has_key(key):
                masked = self.get_key_value(key, masked=True)
                print(f"✓ {key}: {masked}")
            else:
                print(f"ℹ️  {key}: Not set (optional but recommended)")

        print("\n" + "-"*70)
        print("  Optional Integrations")
        print("-"*70)

        integrations = self.get_integration_status()
        if integrations["google_calendar"]:
            print("✓ Google Calendar: Configured")
        else:
            print("ℹ️  Google Calendar: Not configured")

        if integrations["oura"]:
            print("✓ Oura Ring: Configured")
        else:
            print("ℹ️  Oura Ring: Not configured")

        print("\n" + "="*70)


def main():
    """
    Main function for testing the EnvDetector module.
    """
    detector = EnvDetector()
    detector.print_status()

    print("\nDetailed Summary:")
    summary = detector.get_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
