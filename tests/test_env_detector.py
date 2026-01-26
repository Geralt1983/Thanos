"""
Unit tests for Tools/env_detector.py

Tests the EnvDetector class which detects and validates API keys and
integration configurations in the environment.
"""

import pytest
import os
from pathlib import Path
from Tools.env_detector import EnvDetector


class TestEnvDetector:
    """Test suite for EnvDetector class."""

    def test_has_env_file(self, tmp_path):
        """Test detection of .env file existence"""
        # Test when .env exists
        env_file = tmp_path / ".env"
        env_file.write_text("ANTHROPIC_API_KEY=test\n")

        detector = EnvDetector(env_path=env_file)

        assert detector.has_env_file() is True
        assert detector.env_path == env_file

        # Test when .env missing
        non_existent = tmp_path / "nonexistent.env"
        detector2 = EnvDetector(env_path=non_existent)
        assert detector2.has_env_file() is False

    def test_has_anthropic_key(self):
        """Test detection of ANTHROPIC_API_KEY"""
        # Save original value
        original_value = os.environ.get("ANTHROPIC_API_KEY")

        try:
            # Test when key present
            os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test1234567890abcdef"
            detector = EnvDetector()
            assert detector.has_anthropic_key() is True

            # Test when key missing
            os.environ.pop("ANTHROPIC_API_KEY", None)
            detector2 = EnvDetector()
            assert detector2.has_anthropic_key() is False

            # Test when key empty
            os.environ["ANTHROPIC_API_KEY"] = ""
            detector3 = EnvDetector()
            assert detector3.has_anthropic_key() is False

            # Test when key is whitespace only
            os.environ["ANTHROPIC_API_KEY"] = "   "
            detector4 = EnvDetector()
            assert detector4.has_anthropic_key() is False
        finally:
            # Restore original value
            if original_value is not None:
                os.environ["ANTHROPIC_API_KEY"] = original_value
            else:
                os.environ.pop("ANTHROPIC_API_KEY", None)

    def test_has_openai_key(self):
        """Test detection of OPENAI_API_KEY"""
        # Save original value
        original_value = os.environ.get("OPENAI_API_KEY")

        try:
            # Test when key present
            os.environ["OPENAI_API_KEY"] = "sk-test1234567890abcdef"
            detector = EnvDetector()
            assert detector.has_openai_key() is True

            # Test when key missing
            os.environ.pop("OPENAI_API_KEY", None)
            detector2 = EnvDetector()
            assert detector2.has_openai_key() is False

            # Test when key empty
            os.environ["OPENAI_API_KEY"] = ""
            detector3 = EnvDetector()
            assert detector3.has_openai_key() is False
        finally:
            # Restore original value
            if original_value is not None:
                os.environ["OPENAI_API_KEY"] = original_value
            else:
                os.environ.pop("OPENAI_API_KEY", None)

    def test_has_google_calendar(self):
        """Test detection of Google Calendar integration"""
        # Save original values
        original_id = os.environ.get("GOOGLE_CALENDAR_CLIENT_ID")
        original_secret = os.environ.get("GOOGLE_CALENDAR_CLIENT_SECRET")

        try:
            # Test when both CLIENT_ID and CLIENT_SECRET present
            os.environ["GOOGLE_CALENDAR_CLIENT_ID"] = "test.apps.googleusercontent.com"
            os.environ["GOOGLE_CALENDAR_CLIENT_SECRET"] = "GOCSPX-test1234567890abcdef"
            detector = EnvDetector()
            assert detector.has_google_calendar() is True

            # Test when one missing (only CLIENT_ID)
            os.environ.pop("GOOGLE_CALENDAR_CLIENT_SECRET", None)
            detector2 = EnvDetector()
            assert detector2.has_google_calendar() is False

            # Test when one missing (only CLIENT_SECRET)
            os.environ.pop("GOOGLE_CALENDAR_CLIENT_ID", None)
            os.environ["GOOGLE_CALENDAR_CLIENT_SECRET"] = "GOCSPX-test1234567890abcdef"
            detector3 = EnvDetector()
            assert detector3.has_google_calendar() is False

            # Test when both missing
            os.environ.pop("GOOGLE_CALENDAR_CLIENT_ID", None)
            os.environ.pop("GOOGLE_CALENDAR_CLIENT_SECRET", None)
            detector4 = EnvDetector()
            assert detector4.has_google_calendar() is False
        finally:
            # Restore original values
            if original_id is not None:
                os.environ["GOOGLE_CALENDAR_CLIENT_ID"] = original_id
            else:
                os.environ.pop("GOOGLE_CALENDAR_CLIENT_ID", None)
            if original_secret is not None:
                os.environ["GOOGLE_CALENDAR_CLIENT_SECRET"] = original_secret
            else:
                os.environ.pop("GOOGLE_CALENDAR_CLIENT_SECRET", None)

    def test_has_oura(self):
        """Test detection of Oura integration"""
        # Save original value
        original_value = os.environ.get("OURA_PERSONAL_ACCESS_TOKEN")

        try:
            # Test token present
            os.environ["OURA_PERSONAL_ACCESS_TOKEN"] = "test_oura_token_1234567890"
            detector = EnvDetector()
            assert detector.has_oura() is True

            # Test token missing
            os.environ.pop("OURA_PERSONAL_ACCESS_TOKEN", None)
            detector2 = EnvDetector()
            assert detector2.has_oura() is False
        finally:
            # Restore original value
            if original_value is not None:
                os.environ["OURA_PERSONAL_ACCESS_TOKEN"] = original_value
            else:
                os.environ.pop("OURA_PERSONAL_ACCESS_TOKEN", None)

    def test_get_missing_required_keys(self):
        """Test identification of missing required keys"""
        # Save original value
        original_value = os.environ.get("ANTHROPIC_API_KEY")

        try:
            # Test returns ['ANTHROPIC_API_KEY'] when missing
            os.environ.pop("ANTHROPIC_API_KEY", None)
            detector = EnvDetector()
            missing = detector.get_missing_required_keys()
            assert "ANTHROPIC_API_KEY" in missing
            assert len(missing) == 1

            # Test returns [] when present
            os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test1234567890abcdef"
            detector2 = EnvDetector()
            missing2 = detector2.get_missing_required_keys()
            assert missing2 == []
        finally:
            # Restore original value
            if original_value is not None:
                os.environ["ANTHROPIC_API_KEY"] = original_value
            else:
                os.environ.pop("ANTHROPIC_API_KEY", None)

    def test_validate_key_format_anthropic(self):
        """Test Anthropic API key format validation"""
        detector = EnvDetector()

        # Test valid key (starts with sk-ant-)
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test1234567890abcdef"
        is_valid, error = detector.validate_key_format("ANTHROPIC_API_KEY")
        assert is_valid is True
        assert error is None

        # Test invalid prefix
        os.environ["ANTHROPIC_API_KEY"] = "invalid-prefix-test1234567890"
        is_valid, error = detector.validate_key_format("ANTHROPIC_API_KEY")
        assert is_valid is False
        assert "should start with 'sk-ant-'" in error

        # Test too short
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-123"
        is_valid, error = detector.validate_key_format("ANTHROPIC_API_KEY")
        assert is_valid is False
        assert "too short" in error

        # Clean up
        os.environ.pop("ANTHROPIC_API_KEY", None)

    def test_validate_key_format_openai(self):
        """Test OpenAI API key format validation"""
        detector = EnvDetector()

        # Test valid key (starts with sk-)
        os.environ["OPENAI_API_KEY"] = "sk-test1234567890abcdefghijklmnop"
        is_valid, error = detector.validate_key_format("OPENAI_API_KEY")
        assert is_valid is True
        assert error is None

        # Test invalid format (wrong prefix)
        os.environ["OPENAI_API_KEY"] = "invalid-test1234567890abcdefghijklmnop"
        is_valid, error = detector.validate_key_format("OPENAI_API_KEY")
        assert is_valid is False
        assert "should start with 'sk-'" in error

        # Test too short
        os.environ["OPENAI_API_KEY"] = "sk-short"
        is_valid, error = detector.validate_key_format("OPENAI_API_KEY")
        assert is_valid is False
        assert "too short" in error

        # Clean up
        os.environ.pop("OPENAI_API_KEY", None)

    def test_mask_value(self):
        """Test API key masking for display"""
        detector = EnvDetector()

        # Test long value (>10 chars)
        masked = detector._mask_value("sk-ant-1234567890abcdef")
        assert masked == "sk-ant-123..."

        # Test value exactly 10 chars
        masked = detector._mask_value("short12345")
        assert masked == "short12345..."

        # Test short value (<10 chars) - shows first 4 chars
        masked = detector._mask_value("short")
        assert masked == "shor..."

    def test_get_integration_status(self):
        """Test comprehensive integration status report"""
        # Save original values
        original_anthropic = os.environ.get("ANTHROPIC_API_KEY")
        original_openai = os.environ.get("OPENAI_API_KEY")
        original_gcal_id = os.environ.get("GOOGLE_CALENDAR_CLIENT_ID")
        original_gcal_secret = os.environ.get("GOOGLE_CALENDAR_CLIENT_SECRET")
        original_oura = os.environ.get("OURA_PERSONAL_ACCESS_TOKEN")

        try:
            # Setup test environment
            os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test1234567890abcdef"
            os.environ["OPENAI_API_KEY"] = "sk-test1234567890abcdef"
            os.environ["GOOGLE_CALENDAR_CLIENT_ID"] = "test.apps.googleusercontent.com"
            os.environ["GOOGLE_CALENDAR_CLIENT_SECRET"] = "GOCSPX-test123"
            os.environ.pop("OURA_PERSONAL_ACCESS_TOKEN", None)

            detector = EnvDetector()
            status = detector.get_integration_status()

            # Test returns dict with all integrations
            assert isinstance(status, dict)
            assert "anthropic" in status
            assert "openai" in status
            assert "google_calendar" in status
            assert "oura" in status

            # Verify boolean values correct
            assert status["anthropic"] is True
            assert status["openai"] is True
            assert status["google_calendar"] is True
            assert status["oura"] is False
        finally:
            # Restore original values
            if original_anthropic is not None:
                os.environ["ANTHROPIC_API_KEY"] = original_anthropic
            else:
                os.environ.pop("ANTHROPIC_API_KEY", None)
            if original_openai is not None:
                os.environ["OPENAI_API_KEY"] = original_openai
            else:
                os.environ.pop("OPENAI_API_KEY", None)
            if original_gcal_id is not None:
                os.environ["GOOGLE_CALENDAR_CLIENT_ID"] = original_gcal_id
            else:
                os.environ.pop("GOOGLE_CALENDAR_CLIENT_ID", None)
            if original_gcal_secret is not None:
                os.environ["GOOGLE_CALENDAR_CLIENT_SECRET"] = original_gcal_secret
            else:
                os.environ.pop("GOOGLE_CALENDAR_CLIENT_SECRET", None)
            if original_oura is not None:
                os.environ["OURA_PERSONAL_ACCESS_TOKEN"] = original_oura
            else:
                os.environ.pop("OURA_PERSONAL_ACCESS_TOKEN", None)

    def test_get_key_value_masked(self):
        """Test getting masked key values"""
        # Save original value
        original_value = os.environ.get("ANTHROPIC_API_KEY")

        try:
            os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test1234567890abcdef"
            detector = EnvDetector()

            # Test masked retrieval (default)
            masked = detector.get_key_value("ANTHROPIC_API_KEY", masked=True)
            assert masked == "sk-ant-tes..."

            # Test unmasked retrieval
            unmasked = detector.get_key_value("ANTHROPIC_API_KEY", masked=False)
            assert unmasked == "sk-ant-test1234567890abcdef"

            # Test missing key
            result = detector.get_key_value("NONEXISTENT_KEY", masked=True)
            assert result is None
        finally:
            # Restore original value
            if original_value is not None:
                os.environ["ANTHROPIC_API_KEY"] = original_value
            else:
                os.environ.pop("ANTHROPIC_API_KEY", None)

    def test_get_summary(self):
        """Test comprehensive environment summary"""
        # Save original values
        original_anthropic = os.environ.get("ANTHROPIC_API_KEY")
        original_openai = os.environ.get("OPENAI_API_KEY")

        try:
            # Setup test environment
            os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test1234567890abcdef"
            os.environ.pop("OPENAI_API_KEY", None)

            detector = EnvDetector()
            summary = detector.get_summary()

            # Verify summary structure
            assert "env_file_exists" in summary
            assert "env_path" in summary
            assert "required_keys_present" in summary
            assert "required_keys_missing" in summary
            assert "recommended_keys_present" in summary
            assert "recommended_keys_missing" in summary
            assert "integrations" in summary

            # Verify required keys
            assert "ANTHROPIC_API_KEY" in summary["required_keys_present"]
            assert "ANTHROPIC_API_KEY" not in summary["required_keys_missing"]

            # Verify recommended keys
            assert "OPENAI_API_KEY" in summary["recommended_keys_missing"]
            assert "OPENAI_API_KEY" not in summary["recommended_keys_present"]
        finally:
            # Restore original values
            if original_anthropic is not None:
                os.environ["ANTHROPIC_API_KEY"] = original_anthropic
            else:
                os.environ.pop("ANTHROPIC_API_KEY", None)
            if original_openai is not None:
                os.environ["OPENAI_API_KEY"] = original_openai
            else:
                os.environ.pop("OPENAI_API_KEY", None)

    def test_get_missing_recommended_keys(self):
        """Test identification of missing recommended keys"""
        # Save original value
        original_value = os.environ.get("OPENAI_API_KEY")

        try:
            # Test when OPENAI_API_KEY missing
            os.environ.pop("OPENAI_API_KEY", None)
            detector = EnvDetector()
            missing = detector.get_missing_recommended_keys()
            assert "OPENAI_API_KEY" in missing

            # Test when OPENAI_API_KEY present
            os.environ["OPENAI_API_KEY"] = "sk-test1234567890abcdef"
            detector2 = EnvDetector()
            missing2 = detector2.get_missing_recommended_keys()
            assert "OPENAI_API_KEY" not in missing2
        finally:
            # Restore original value
            if original_value is not None:
                os.environ["OPENAI_API_KEY"] = original_value
            else:
                os.environ.pop("OPENAI_API_KEY", None)
