"""
Unit tests for Tools/setup_wizard.py

Tests the SetupWizard class which guides users through first-run configuration.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
from Tools.setup_wizard import SetupWizard


class TestSetupWizard:
    """Test suite for SetupWizard class."""

    @pytest.fixture
    def wizard(self, tmp_path, monkeypatch):
        """Create wizard instance with temp directory"""
        # Mock project_root
        monkeypatch.setattr('Tools.setup_wizard.project_root', tmp_path)

        # Create .env.example
        env_example = tmp_path / ".env.example"
        env_example.write_text("ANTHROPIC_API_KEY=\nOPENAI_API_KEY=\n")

        # Mock FirstRunDetector
        mock_first_run = Mock()
        mock_first_run.mark_setup_complete = Mock(return_value=True)
        monkeypatch.setattr('Tools.setup_wizard.FirstRunDetector', Mock(return_value=mock_first_run))

        # Mock EnvDetector
        mock_env_detector = Mock()
        mock_env_detector.has_anthropic_key = Mock(return_value=False)
        mock_env_detector.has_openai_key = Mock(return_value=False)
        monkeypatch.setattr('Tools.setup_wizard.EnvDetector', Mock(return_value=mock_env_detector))

        return SetupWizard()

    def test_ensure_env_file_creates_from_example(self, wizard, tmp_path, monkeypatch):
        """Test .env creation from .env.example when missing"""
        monkeypatch.setattr('Tools.setup_wizard.project_root', tmp_path)

        # Create .env.example with content
        env_example = tmp_path / ".env.example"
        test_content = "ANTHROPIC_API_KEY=\nOPENAI_API_KEY=\nTEST_VAR=value\n"
        env_example.write_text(test_content)

        # Recreate wizard to pick up new paths
        wizard.project_root = tmp_path
        wizard.env_path = tmp_path / ".env"
        wizard.env_example_path = env_example

        # Call _ensure_env_file()
        result = wizard._ensure_env_file()

        # Verify .env created with same content
        assert result is True
        assert wizard.env_path.exists()
        assert wizard.env_path.read_text() == test_content

    def test_ensure_env_file_skips_if_exists(self, wizard, tmp_path, monkeypatch):
        """Test skips creation if .env already exists"""
        monkeypatch.setattr('Tools.setup_wizard.project_root', tmp_path)

        # Create .env file
        env_file = tmp_path / ".env"
        original_content = "EXISTING_CONTENT=test\n"
        env_file.write_text(original_content)

        # Recreate wizard to pick up new paths
        wizard.project_root = tmp_path
        wizard.env_path = env_file
        wizard.env_example_path = tmp_path / ".env.example"

        # Call _ensure_env_file()
        result = wizard._ensure_env_file()

        # Verify file not overwritten
        assert result is True
        assert env_file.read_text() == original_content

    def test_ensure_env_file_creates_minimal_if_no_example(self, wizard, tmp_path, monkeypatch):
        """Test creates minimal .env if .env.example missing"""
        monkeypatch.setattr('Tools.setup_wizard.project_root', tmp_path)

        # Ensure .env.example doesn't exist
        env_example = tmp_path / ".env.example"
        if env_example.exists():
            env_example.unlink()

        # Recreate wizard to pick up new paths
        wizard.project_root = tmp_path
        wizard.env_path = tmp_path / ".env"
        wizard.env_example_path = env_example

        # Call _ensure_env_file()
        result = wizard._ensure_env_file()

        # Verify minimal .env created
        assert result is True
        assert wizard.env_path.exists()
        assert "# Thanos Environment Configuration" in wizard.env_path.read_text()

    def test_write_env_var(self, wizard, tmp_path, monkeypatch):
        """Test writing environment variable to .env"""
        monkeypatch.setattr('Tools.setup_wizard.project_root', tmp_path)

        # Create .env file
        env_file = tmp_path / ".env"
        env_file.write_text("# Test file\n")

        # Recreate wizard to pick up new paths
        wizard.project_root = tmp_path
        wizard.env_path = env_file

        # Mock set_key and load_dotenv
        with patch('Tools.setup_wizard.set_key') as mock_set_key, \
             patch('Tools.setup_wizard.load_dotenv') as mock_load_dotenv:

            # Call _write_env_var('TEST_KEY', 'test-value')
            result = wizard._write_env_var('TEST_KEY', 'test-value')

            # Verify returns True
            assert result is True

            # Verify set_key was called correctly
            mock_set_key.assert_called_once_with(str(env_file), 'TEST_KEY', 'test-value')

            # Verify load_dotenv was called
            mock_load_dotenv.assert_called_once()

    def test_write_env_var_handles_errors(self, wizard, monkeypatch):
        """Test error handling when write fails"""
        # Mock set_key to raise exception
        with patch('Tools.setup_wizard.set_key', side_effect=Exception("Write failed")):
            # Verify returns False
            result = wizard._write_env_var('TEST_KEY', 'test-value')
            assert result is False

    def test_mark_complete(self, wizard):
        """Test marking setup as complete"""
        # Mock FirstRunDetector.mark_setup_complete()
        wizard.first_run_detector.mark_setup_complete = Mock(return_value=True)

        # Call _mark_complete()
        result = wizard._mark_complete()

        # Verify detector method called
        wizard.first_run_detector.mark_setup_complete.assert_called_once()

        # Verify returns True
        assert result is True

    def test_mark_complete_handles_failure(self, wizard):
        """Test handling when mark_setup_complete fails"""
        # Mock FirstRunDetector.mark_setup_complete() to return False
        wizard.first_run_detector.mark_setup_complete = Mock(return_value=False)

        # Call _mark_complete()
        result = wizard._mark_complete()

        # Verify returns False
        assert result is False

    def test_prompt_returns_input(self, wizard, monkeypatch):
        """Test _prompt returns user input"""
        monkeypatch.setattr('builtins.input', lambda x: 'user input')
        result = wizard._prompt("Test prompt")
        assert result == 'user input'

    def test_prompt_returns_default_on_empty(self, wizard, monkeypatch):
        """Test _prompt returns default when Enter pressed"""
        monkeypatch.setattr('builtins.input', lambda x: '')
        result = wizard._prompt("Test prompt", default='default')
        assert result == 'default'

    def test_prompt_handles_keyboard_interrupt(self, wizard, monkeypatch):
        """Test KeyboardInterrupt exits gracefully"""
        monkeypatch.setattr('builtins.input', Mock(side_effect=KeyboardInterrupt))
        with pytest.raises(SystemExit) as exc_info:
            wizard._prompt("Test prompt")
        assert exc_info.value.code == 0

    def test_prompt_handles_eoferror(self, wizard, monkeypatch):
        """Test EOFError exits gracefully"""
        monkeypatch.setattr('builtins.input', Mock(side_effect=EOFError))
        with pytest.raises(SystemExit) as exc_info:
            wizard._prompt("Test prompt")
        assert exc_info.value.code == 0

    def test_prompt_strips_whitespace(self, wizard, monkeypatch):
        """Test _prompt strips leading/trailing whitespace"""
        monkeypatch.setattr('builtins.input', lambda x: '  user input  ')
        result = wizard._prompt("Test prompt")
        assert result == 'user input'

    def test_prompt_with_default_format(self, wizard, monkeypatch):
        """Test _prompt formats prompt correctly with default"""
        captured_prompt = []

        def mock_input(prompt):
            captured_prompt.append(prompt)
            return ''

        monkeypatch.setattr('builtins.input', mock_input)
        wizard._prompt("Test question", default='yes')

        assert "[yes]" in captured_prompt[0]

    def test_configure_required_keys_skips_if_present(self, wizard, monkeypatch):
        """Test configure_required_keys skips if Anthropic key already present"""
        # Mock detector to show key is present
        wizard.detector.has_anthropic_key = Mock(return_value=True)
        wizard.detector.get_key_value = Mock(return_value="sk-ant-xxx...")
        wizard.detector.validate_key_format = Mock(return_value=(True, None))

        # Should return True without prompting
        result = wizard._configure_required_keys()
        assert result is True

    def test_configure_required_keys_prompts_if_missing(self, wizard, monkeypatch):
        """Test configure_required_keys prompts if Anthropic key missing"""
        # Mock detector to show key is missing
        wizard.detector.has_anthropic_key = Mock(return_value=False)

        # Mock prompt to provide key
        monkeypatch.setattr('builtins.input', lambda x: 'sk-ant-test1234567890')

        # Mock _write_env_var to succeed
        wizard._write_env_var = Mock(return_value=True)

        # Should prompt and return True
        result = wizard._configure_required_keys()
        assert result is True
        wizard._write_env_var.assert_called_once_with('ANTHROPIC_API_KEY', 'sk-ant-test1234567890')

    def test_configure_recommended_keys_skips_if_present(self, wizard):
        """Test configure_recommended_keys skips if OpenAI key already present"""
        # Mock detector to show key is present
        wizard.detector.has_openai_key = Mock(return_value=True)
        wizard.detector.get_key_value = Mock(return_value="sk-xxx...")

        # Should return without prompting
        wizard._configure_recommended_keys()

        # Verify no write attempted
        # (no direct way to verify, but function should exit early)

    def test_configure_recommended_keys_is_optional(self, wizard, monkeypatch):
        """Test configure_recommended_keys allows skipping"""
        # Mock detector to show key is missing
        wizard.detector.has_openai_key = Mock(return_value=False)

        # Mock prompt to decline
        monkeypatch.setattr('builtins.input', lambda x: 'n')

        # Should not raise error and should allow skipping
        wizard._configure_recommended_keys()

        # Test passes if no exception raised

    def test_offer_tutorial_is_skippable(self, wizard, monkeypatch):
        """Test tutorial can be skipped"""
        # Mock prompt to skip tutorial
        monkeypatch.setattr('builtins.input', lambda x: 's')

        # Should not raise error
        wizard._offer_tutorial()

        # Test passes if no exception raised

    def test_run_flow_completes_successfully(self, wizard, tmp_path, monkeypatch):
        """Test complete run flow with mocked inputs"""
        monkeypatch.setattr('Tools.setup_wizard.project_root', tmp_path)

        # Setup environment
        env_file = tmp_path / ".env"
        env_example = tmp_path / ".env.example"
        env_example.write_text("ANTHROPIC_API_KEY=\n")

        wizard.project_root = tmp_path
        wizard.env_path = env_file
        wizard.env_example_path = env_example

        # Mock detector
        wizard.detector.has_anthropic_key = Mock(return_value=False)
        wizard.detector.has_openai_key = Mock(return_value=False)

        # Mock prompts (skip everything)
        inputs = ['sk-ant-test123', 'n', 's']
        input_iterator = iter(inputs)
        monkeypatch.setattr('builtins.input', lambda x: next(input_iterator))

        # Mock _write_env_var
        wizard._write_env_var = Mock(return_value=True)

        # Mock mark_complete
        wizard._mark_complete = Mock(return_value=True)

        # Run wizard
        result = wizard.run()

        # Verify completed successfully
        assert result is True
        wizard._mark_complete.assert_called_once()
