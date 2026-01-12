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
