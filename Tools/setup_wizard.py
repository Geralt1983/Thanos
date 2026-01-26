#!/usr/bin/env python3
"""
Thanos Setup Wizard - Zero-Configuration Onboarding

This wizard guides new users through the essential setup process in under 5 minutes.
It auto-detects existing configuration, prompts only for missing required keys,
and defers advanced integrations to progressive disclosure.

Usage:
    python3 Tools/setup_wizard.py

Key Features:
    - Auto-detection of existing API keys
    - Minimal required configuration (ANTHROPIC_API_KEY only)
    - Recommended configuration (OPENAI_API_KEY for voice/embeddings)
    - Deferred advanced integrations (Google Calendar, Oura)
    - Optional, skippable tutorial
    - Creates .env from .env.example if missing
    - Marks setup as complete for first-run detection
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv, set_key
except ImportError:
    print("Error: python-dotenv not installed. Please run: pip install python-dotenv")
    sys.exit(1)

from Tools.env_detector import EnvDetector
from Tools.first_run_detector import FirstRunDetector


# ============================================================================
# Display Helper Functions
# ============================================================================

def print_header(text: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"✓ {text}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"✗ {text}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"⚠️  {text}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"ℹ️  {text}")


# ============================================================================
# Setup Wizard Class
# ============================================================================

class SetupWizard:
    """
    Interactive setup wizard for Thanos first-run configuration.

    Guides users through essential setup in 5 minutes or less by:
    - Auto-detecting existing configuration
    - Prompting only for missing required keys
    - Offering recommended enhancements
    - Deferring advanced integrations
    - Providing skippable tutorial
    """

    def __init__(self):
        """Initialize the setup wizard."""
        self.project_root = project_root
        self.env_path = self.project_root / ".env"
        self.env_example_path = self.project_root / ".env.example"
        self.detector = EnvDetector()
        self.first_run_detector = FirstRunDetector()

    def run(self) -> bool:
        """
        Run the complete setup wizard flow.

        Returns:
            True if setup completed successfully, False otherwise.
        """
        self._print_welcome()

        # Step 1: Check and create .env file if needed
        if not self._ensure_env_file():
            return False

        # Reload detector after creating .env
        self.detector = EnvDetector()

        # Step 2: Configure required API keys
        if not self._configure_required_keys():
            return False

        # Step 3: Offer recommended enhancements
        self._configure_recommended_keys()

        # Step 4: Mention deferred integrations
        self._mention_advanced_integrations()

        # Step 5: Optional tutorial
        self._offer_tutorial()

        # Step 6: Mark setup complete
        if not self._mark_complete():
            return False

        # Step 7: Print success and next steps
        self._print_completion()

        return True

    def _print_welcome(self) -> None:
        """Print the welcome banner."""
        print_header("Welcome to Thanos - Your AI Life Management System")
        print("This wizard will get you up and running in under 5 minutes.")
        print("We'll only ask for what's essential - everything else can wait.\n")

    def _ensure_env_file(self) -> bool:
        """
        Ensure .env file exists, create from .env.example if needed.

        Returns:
            True if .env exists or was created successfully, False on error.
        """
        print_header("Step 1: Environment File")

        if self.env_path.exists():
            print_success(f"Found .env file at: {self.env_path}")
            return True

        print_info("No .env file found. Let's create one.")

        # Check if .env.example exists
        if not self.env_example_path.exists():
            print_error(f"Missing .env.example template at: {self.env_example_path}")
            print_info("Creating minimal .env file...")

            try:
                self.env_path.write_text("# Thanos Environment Configuration\n\n")
                print_success(f"Created .env file at: {self.env_path}")
                return True
            except Exception as e:
                print_error(f"Failed to create .env file: {e}")
                return False

        # Copy from .env.example
        try:
            content = self.env_example_path.read_text()
            self.env_path.write_text(content)
            print_success(f"Created .env from template at: {self.env_path}")
            return True
        except Exception as e:
            print_error(f"Failed to create .env from template: {e}")
            return False

    def _configure_required_keys(self) -> bool:
        """
        Configure required API keys (ANTHROPIC_API_KEY).

        Returns:
            True if all required keys are configured, False otherwise.
        """
        print_header("Step 2: Required Configuration")
        print("Thanos requires an Anthropic API key to function.")
        print("Get your key at: https://console.anthropic.com/")
        print()

        # Check if already configured
        if self.detector.has_anthropic_key():
            masked = self.detector.get_key_value("ANTHROPIC_API_KEY", masked=True)
            print_success(f"ANTHROPIC_API_KEY already configured: {masked}")

            # Validate format
            is_valid, error = self.detector.validate_key_format("ANTHROPIC_API_KEY")
            if not is_valid:
                print_warning(f"Format warning: {error}")
                response = self._prompt("Replace with a new key? (y/n)", default="n")
                if response.lower() != 'y':
                    return True
            else:
                return True

        # Prompt for key
        while True:
            api_key = self._prompt("Enter your Anthropic API key (starts with sk-ant-)")

            if not api_key:
                print_error("API key is required. Thanos cannot function without it.")
                retry = self._prompt("Try again? (y/n)", default="y")
                if retry.lower() != 'y':
                    return False
                continue

            # Basic validation
            if not api_key.startswith("sk-ant-"):
                print_warning("Key doesn't start with 'sk-ant-'. Are you sure this is correct?")
                confirm = self._prompt("Use this key anyway? (y/n)", default="n")
                if confirm.lower() != 'y':
                    continue

            # Write to .env
            if self._write_env_var("ANTHROPIC_API_KEY", api_key):
                print_success("Anthropic API key configured!")
                return True
            else:
                print_error("Failed to write API key to .env file.")
                return False

    def _configure_recommended_keys(self) -> None:
        """Configure recommended API keys (OPENAI_API_KEY)."""
        print_header("Step 3: Recommended Enhancements (Optional)")

        # Check if already configured
        if self.detector.has_openai_key():
            masked = self.detector.get_key_value("OPENAI_API_KEY", masked=True)
            print_success(f"OPENAI_API_KEY already configured: {masked}")
            return

        print("OpenAI API key is optional but recommended for:")
        print("  • Voice transcription (Whisper)")
        print("  • Text embeddings (for enhanced memory search)")
        print("  • Future multi-model capabilities")
        print()
        print_info("You can always add this later by editing .env")
        print()

        response = self._prompt("Set up OpenAI API key now? (y/n)", default="n")

        if response.lower() != 'y':
            print_info("Skipping OpenAI setup. You can add it later to .env")
            return

        print()
        print("Get your OpenAI API key at: https://platform.openai.com/api-keys")

        while True:
            api_key = self._prompt("Enter your OpenAI API key (starts with sk-)")

            if not api_key:
                print_info("Skipping OpenAI key.")
                return

            # Basic validation
            if not api_key.startswith("sk-"):
                print_warning("Key doesn't start with 'sk-'. Are you sure this is correct?")
                confirm = self._prompt("Use this key anyway? (y/n)", default="n")
                if confirm.lower() != 'y':
                    continue

            # Write to .env
            if self._write_env_var("OPENAI_API_KEY", api_key):
                print_success("OpenAI API key configured!")
                return
            else:
                print_warning("Failed to write OpenAI key to .env file.")
                return

    def _mention_advanced_integrations(self) -> None:
        """Mention deferred advanced integrations."""
        print_header("Optional Integrations (Available Later)")

        print("Thanos supports additional integrations that you can set up anytime:")
        print()
        print("  📅 Google Calendar - Sync events and schedule")
        print("     Setup: python3 scripts/setup_google_calendar.py")
        print()
        print("  💍 Oura Ring - Track sleep, readiness, and activity")
        print("     Setup: Add OURA_PERSONAL_ACCESS_TOKEN to .env")
        print()
        print_info("These are optional. Core features work without them.")
        print()

    def _offer_tutorial(self) -> None:
        """Offer optional, skippable tutorial."""
        print_header("Quick Start Tutorial (Optional)")

        response = self._prompt("See quick tutorial? (y/n/s to skip)", default="s")

        if response.lower() not in ['y', 'yes']:
            print_info("Skipping tutorial. Type 'thanos --help' anytime for guidance.")
            return

        print()
        print("="*70)
        print("  Thanos Quick Tutorial")
        print("="*70)
        print()
        print("Thanos is designed for natural language interaction. Just ask:")
        print()
        print("  $ thanos 'What should I focus on today?'")
        print("  $ thanos 'Add a task to review Q4 planning'")
        print("  $ thanos daily")
        print()
        print("For interactive mode:")
        print()
        print("  $ thanos interactive")
        print()
        print("For help and commands:")
        print()
        print("  $ thanos --help")
        print("  $ thanos /help    (in interactive mode)")
        print()
        print_success("That's it! Thanos learns your patterns over time.")
        print()

    def _mark_complete(self) -> bool:
        """
        Mark setup as complete.

        Returns:
            True if marked successfully, False otherwise.
        """
        if self.first_run_detector.mark_setup_complete():
            return True
        else:
            print_error("Failed to mark setup as complete.")
            print_info("You may need to run setup again on next start.")
            return False

    def _print_completion(self) -> None:
        """Print completion message and next steps."""
        print_header("Setup Complete! 🎉")

        print("Thanos is ready to use. Here's what you can do now:")
        print()
        print("  1. Try your first command:")
        print("     $ thanos 'What should I do today?'")
        print()
        print("  2. Start an interactive session:")
        print("     $ thanos interactive")
        print()
        print("  3. See all available commands:")
        print("     $ thanos --help")
        print()
        print_info("For advanced setup and integrations, see: docs/SETUP_GUIDE.md")
        print()
        print("="*70)

    def _prompt(self, message: str, default: Optional[str] = None) -> str:
        """
        Prompt user for input with optional default.

        Args:
            message: The prompt message to display.
            default: Optional default value if user presses Enter.

        Returns:
            User input string (or default if Enter pressed).
        """
        if default:
            prompt_text = f"{message} [{default}]: "
        else:
            prompt_text = f"{message}: "

        try:
            response = input(prompt_text).strip()
            return response if response else (default or "")
        except (KeyboardInterrupt, EOFError):
            print("\n")
            print_warning("Setup interrupted by user.")
            sys.exit(0)

    def _write_env_var(self, key: str, value: str) -> bool:
        """
        Write an environment variable to .env file.

        Args:
            key: Environment variable name.
            value: Environment variable value.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Use set_key from python-dotenv for safe writing
            set_key(str(self.env_path), key, value)

            # Reload environment
            load_dotenv(self.env_path, override=True)

            return True
        except Exception as e:
            print_error(f"Error writing to .env: {e}")
            return False


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point for the setup wizard."""
    wizard = SetupWizard()

    try:
        success = wizard.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n")
        print_warning("Setup interrupted by user.")
        print_info("Run 'python3 Tools/setup_wizard.py' again to continue setup.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error during setup: {e}")
        print_info("Please report this issue or try manual setup.")
        sys.exit(1)


if __name__ == "__main__":
    main()
