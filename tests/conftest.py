"""
Pytest configuration and shared fixtures for Thanos tests.
"""
from pathlib import Path
import sys

import pytest


# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def project_root_path():
    """Return the project root directory path."""
    return project_root


@pytest.fixture
def mock_anthropic_response():
    """Mock a standard Anthropic API response."""
    return {
        "id": "msg_test123",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": "Test response"}],
        "model": "claude-sonnet-4-5-20250929",
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 100, "output_tokens": 50},
    }


@pytest.fixture
def mock_anthropic_client(mocker, mock_anthropic_response):
    """Mock the Anthropic client for testing."""
    mock_client = mocker.Mock()
    mock_message = mocker.Mock()
    mock_message.content = [mocker.Mock(text="Test response")]
    mock_message.usage = mocker.Mock(input_tokens=100, output_tokens=50)
    mock_message.stop_reason = "end_turn"
    mock_client.messages.create.return_value = mock_message
    return mock_client


@pytest.fixture
def sample_messages():
    """Sample conversation messages for testing."""
    return [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you!"},
    ]


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary configuration directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def mock_api_config(temp_config_dir):
    """Create a mock API configuration file."""
    import json

    config = {
        "anthropic_api_key": "test_api_key_12345",
        "model": "claude-sonnet-4-5-20250929",
    }
    config_file = temp_config_dir / "api.json"
    config_file.write_text(json.dumps(config, indent=2))
    return config_file
