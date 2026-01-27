"""
Integration test for the complete first-run onboarding flow.

Tests the end-to-end flow of:
1. No .env file exists
2. No setup marker exists
3. Setup wizard runs
4. Keys are configured
5. Setup marker is created
6. Subsequent runs skip the wizard
"""

import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch
from Tools.first_run_detector import FirstRunDetector
from Tools.setup_wizard import SetupWizard
from Tools.env_detector import EnvDetector


class TestFirstRunFlow:
    """Integration test suite for the complete first-run onboarding flow."""

    @pytest.fixture
    def clean_env(self, tmp_path, monkeypatch):
        """Setup clean test environment"""
        # Set project root to tmp_path
        monkeypatch.setattr('Tools.setup_wizard.project_root', tmp_path)

        # Mock .thanos directory
        thanos_dir = tmp_path / '.thanos'
        monkeypatch.setattr('Tools.first_run_detector.THANOS_DIR', thanos_dir)
        monkeypatch.setattr('Tools.first_run_detector.SETUP_MARKER', thanos_dir / 'setup_complete')

        # Create .env.example
        env_example = tmp_path / '.env.example'
        env_example.write_text('ANTHROPIC_API_KEY=\nOPENAI_API_KEY=\n')

        yield tmp_path

    def test_complete_first_run_flow(self, clean_env, monkeypatch):
        """Test complete first-run onboarding flow"""
        # Phase 1: Initial state - no .env, no marker
        env_path = clean_env / '.env'
        env_example = clean_env / '.env.example'

        detector = FirstRunDetector()
        assert detector.is_first_run() is True

        # Phase 2: Run wizard with mocked input
        inputs = [
            'sk-ant-test1234567890',  # Anthropic key
            'n',                       # Skip OpenAI
            'n',                       # Skip tutorial
        ]

        # Create iterator for sequential inputs
        input_iter = iter(inputs)

        def mock_input(prompt):
            return next(input_iter)

        monkeypatch.setattr('builtins.input', mock_input)

        # Mock set_key and load_dotenv to actually write to file
        def mock_set_key(file_path, key, value):
            # Append to .env file
            with open(file_path, 'a') as f:
                f.write(f"{key}={value}\n")

        with patch('Tools.setup_wizard.set_key', side_effect=mock_set_key), \
             patch('Tools.setup_wizard.load_dotenv'):

            wizard = SetupWizard()
            success = wizard.run()

            assert success is True

        # Phase 3: Verify post-setup state
        # Verify .env created with API key
        assert env_path.exists()
        env_content = env_path.read_text()
        assert 'sk-ant-test1234567890' in env_content

        # Verify setup marker created
        assert detector.is_first_run() is False

        # Phase 4: Verify subsequent run skips wizard
        detector2 = FirstRunDetector()
        assert detector2.is_first_run() is False

    def test_wizard_skip_if_setup_complete(self, clean_env):
        """Test wizard not shown if setup already complete"""
        detector = FirstRunDetector()
        detector.mark_setup_complete()

        assert detector.is_first_run() is False

    def test_env_detector_integration(self, clean_env):
        """Test EnvDetector correctly detects configuration after wizard"""
        # Save original values
        original_anthropic = os.environ.get('ANTHROPIC_API_KEY')
        original_openai = os.environ.get('OPENAI_API_KEY')

        try:
            # Create .env with test keys
            env_path = clean_env / '.env'
            env_path.write_text('ANTHROPIC_API_KEY=sk-ant-test123\n')

            # Set environment
            os.environ['ANTHROPIC_API_KEY'] = 'sk-ant-test123'
            os.environ.pop('OPENAI_API_KEY', None)

            # Test detection
            env_detector = EnvDetector(env_path=env_path)
            assert env_detector.has_anthropic_key() is True
            assert env_detector.has_openai_key() is False
        finally:
            # Restore original values
            if original_anthropic is not None:
                os.environ['ANTHROPIC_API_KEY'] = original_anthropic
            else:
                os.environ.pop('ANTHROPIC_API_KEY', None)
            if original_openai is not None:
                os.environ['OPENAI_API_KEY'] = original_openai
            else:
                os.environ.pop('OPENAI_API_KEY', None)

    def test_first_run_after_marker_deletion(self, clean_env):
        """Test that deleting marker causes wizard to run again"""
        detector = FirstRunDetector()

        # Mark as complete
        detector.mark_setup_complete()
        assert not detector.is_first_run()

        # Delete marker
        detector.reset()

        # Verify first run again
        assert detector.is_first_run()

    def test_env_file_creation_from_example(self, clean_env, monkeypatch):
        """Test that .env is created from .env.example on first run"""
        env_path = clean_env / '.env'
        env_example = clean_env / '.env.example'

        # Verify .env doesn't exist initially
        assert not env_path.exists()
        assert env_example.exists()

        # Mock inputs to skip everything quickly
        inputs = ['sk-ant-test123', 'n', 'n']
        input_iter = iter(inputs)
        monkeypatch.setattr('builtins.input', lambda x: next(input_iter))

        # Mock file writing
        with patch('Tools.setup_wizard.set_key'), \
             patch('Tools.setup_wizard.load_dotenv'):

            wizard = SetupWizard()
            wizard.run()

            # Verify .env was created
            assert env_path.exists()

    def test_setup_complete_marker_persists(self, clean_env):
        """Test that setup marker persists across detector instances"""
        detector1 = FirstRunDetector()

        # Initially first run
        assert detector1.is_first_run()

        # Mark complete
        detector1.mark_setup_complete()
        assert not detector1.is_first_run()

        # Create new detector instance
        detector2 = FirstRunDetector()

        # Should still be marked complete
        assert not detector2.is_first_run()

    def test_wizard_handles_existing_env_file(self, clean_env, monkeypatch):
        """Test wizard handles case where .env already exists"""
        env_path = clean_env / '.env'
        existing_content = "EXISTING_KEY=existing_value\n"
        env_path.write_text(existing_content)

        # Mock inputs
        inputs = ['sk-ant-test123', 'n', 'n']
        input_iter = iter(inputs)
        monkeypatch.setattr('builtins.input', lambda x: next(input_iter))

        # Mock file operations
        with patch('Tools.setup_wizard.set_key'), \
             patch('Tools.setup_wizard.load_dotenv'):

            wizard = SetupWizard()
            result = wizard.run()

            # Should complete successfully
            assert result is True

            # .env should still exist
            assert env_path.exists()

    def test_integration_status_after_full_setup(self, clean_env):
        """Test that integration status is correct after full setup"""
        # Save original values
        original_anthropic = os.environ.get('ANTHROPIC_API_KEY')
        original_openai = os.environ.get('OPENAI_API_KEY')
        original_gcal_id = os.environ.get('GOOGLE_CALENDAR_CLIENT_ID')
        original_gcal_secret = os.environ.get('GOOGLE_CALENDAR_CLIENT_SECRET')
        original_oura = os.environ.get('OURA_PERSONAL_ACCESS_TOKEN')

        try:
            # Create test .env file with only Anthropic and OpenAI keys
            test_env = clean_env / '.env'
            test_env.write_text('ANTHROPIC_API_KEY=sk-ant-test1234567890\nOPENAI_API_KEY=sk-test1234567890\n')

            # Setup environment variables
            os.environ['ANTHROPIC_API_KEY'] = 'sk-ant-test1234567890'
            os.environ['OPENAI_API_KEY'] = 'sk-test1234567890'
            os.environ.pop('GOOGLE_CALENDAR_CLIENT_ID', None)
            os.environ.pop('GOOGLE_CALENDAR_CLIENT_SECRET', None)
            os.environ.pop('OURA_PERSONAL_ACCESS_TOKEN', None)

            # Create EnvDetector with the test env file
            env_detector = EnvDetector(env_path=test_env)

            # Check integration status
            status = env_detector.get_integration_status()

            assert status['anthropic'] is True
            assert status['openai'] is True
            assert status['google_calendar'] is False
            assert status['oura'] is False
        finally:
            # Restore original values
            if original_anthropic is not None:
                os.environ['ANTHROPIC_API_KEY'] = original_anthropic
            else:
                os.environ.pop('ANTHROPIC_API_KEY', None)
            if original_openai is not None:
                os.environ['OPENAI_API_KEY'] = original_openai
            else:
                os.environ.pop('OPENAI_API_KEY', None)
            if original_gcal_id is not None:
                os.environ['GOOGLE_CALENDAR_CLIENT_ID'] = original_gcal_id
            else:
                os.environ.pop('GOOGLE_CALENDAR_CLIENT_ID', None)
            if original_gcal_secret is not None:
                os.environ['GOOGLE_CALENDAR_CLIENT_SECRET'] = original_gcal_secret
            else:
                os.environ.pop('GOOGLE_CALENDAR_CLIENT_SECRET', None)
            if original_oura is not None:
                os.environ['OURA_PERSONAL_ACCESS_TOKEN'] = original_oura
            else:
                os.environ.pop('OURA_PERSONAL_ACCESS_TOKEN', None)

    def test_wizard_creates_thanos_directory(self, clean_env):
        """Test that wizard creates .thanos directory for marker"""
        thanos_dir = clean_env / '.thanos'

        # Verify directory doesn't exist
        assert not thanos_dir.exists()

        # Run first run detector
        detector = FirstRunDetector()
        detector.mark_setup_complete()

        # Verify directory was created
        assert thanos_dir.exists()
        assert thanos_dir.is_dir()

    def test_minimal_env_creation_without_example(self, clean_env, monkeypatch):
        """Test wizard creates minimal .env when .env.example is missing"""
        env_path = clean_env / '.env'
        env_example = clean_env / '.env.example'

        # Remove .env.example
        if env_example.exists():
            env_example.unlink()

        # Mock inputs
        inputs = ['sk-ant-test123', 'n', 'n']
        input_iter = iter(inputs)
        monkeypatch.setattr('builtins.input', lambda x: next(input_iter))

        # Mock file operations
        with patch('Tools.setup_wizard.set_key'), \
             patch('Tools.setup_wizard.load_dotenv'):

            wizard = SetupWizard()
            result = wizard.run()

            # Should complete successfully
            assert result is True

            # .env should be created
            assert env_path.exists()
