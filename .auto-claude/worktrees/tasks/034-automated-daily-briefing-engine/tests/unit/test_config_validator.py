"""
Unit tests for ConfigValidator

Tests validation of briefing schedule configuration files.
"""

import json
import pytest
from pathlib import Path
import tempfile
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.config_validator import ConfigValidator, validate_config


class TestConfigValidator:
    """Test ConfigValidator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def _write_config(self, config_data: dict, filename: str = "test_config.json") -> Path:
        """Helper to write config to temp file."""
        config_path = self.temp_path / filename
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        return config_path

    def _write_schema(self, schema_data: dict, filename: str = "test_schema.json") -> Path:
        """Helper to write schema to temp file."""
        schema_path = self.temp_path / filename
        with open(schema_path, 'w') as f:
            json.dump(schema_data, f)
        return schema_path

    def test_valid_minimal_config(self):
        """Test validation of minimal valid config."""
        config = {
            "version": "1.0.0",
            "briefings": {
                "morning": {
                    "enabled": True,
                    "time": "07:00",
                    "days": {
                        "monday": True,
                        "tuesday": True,
                        "wednesday": True,
                        "thursday": True,
                        "friday": True,
                        "saturday": True,
                        "sunday": True
                    }
                }
            }
        }

        config_path = self._write_config(config)
        validator = ConfigValidator(str(config_path))
        is_valid, errors = validator.validate()

        assert is_valid, f"Expected valid config, got errors: {errors}"
        assert len(errors) == 0

    def test_invalid_time_format(self):
        """Test validation catches invalid time format."""
        config = {
            "version": "1.0.0",
            "briefings": {
                "morning": {
                    "enabled": True,
                    "time": "7:00 AM",  # Invalid format
                    "days": {
                        "monday": True,
                        "tuesday": True,
                        "wednesday": True,
                        "thursday": True,
                        "friday": True,
                        "saturday": True,
                        "sunday": True
                    }
                }
            }
        }

        config_path = self._write_config(config)
        validator = ConfigValidator(str(config_path))
        is_valid, errors = validator.validate()

        assert not is_valid
        assert any("time format" in err.lower() for err in errors)

    def test_invalid_time_range(self):
        """Test validation catches time out of range."""
        config = {
            "version": "1.0.0",
            "briefings": {
                "morning": {
                    "enabled": True,
                    "time": "25:00",  # Invalid hour
                    "days": {
                        "monday": True,
                        "tuesday": True,
                        "wednesday": True,
                        "thursday": True,
                        "friday": True,
                        "saturday": True,
                        "sunday": True
                    }
                }
            }
        }

        config_path = self._write_config(config)
        validator = ConfigValidator(str(config_path))
        is_valid, errors = validator.validate()

        assert not is_valid
        assert any("out of range" in err.lower() or "invalid time" in err.lower() for err in errors)

    def test_missing_days(self):
        """Test validation catches missing days in config."""
        config = {
            "version": "1.0.0",
            "briefings": {
                "morning": {
                    "enabled": True,
                    "time": "07:00",
                    "days": {
                        "monday": True,
                        "tuesday": True,
                        # Missing other days
                    }
                }
            }
        }

        config_path = self._write_config(config)
        validator = ConfigValidator(str(config_path))
        is_valid, errors = validator.validate()

        assert not is_valid
        assert any("missing day" in err.lower() for err in errors)

    def test_invalid_delivery_channel(self):
        """Test validation catches invalid delivery channel."""
        config = {
            "version": "1.0.0",
            "briefings": {
                "morning": {
                    "enabled": True,
                    "time": "07:00",
                    "days": {
                        "monday": True,
                        "tuesday": True,
                        "wednesday": True,
                        "thursday": True,
                        "friday": True,
                        "saturday": True,
                        "sunday": True
                    },
                    "delivery_channels": ["cli", "invalid_channel"]
                }
            }
        }

        config_path = self._write_config(config)
        validator = ConfigValidator(str(config_path))
        is_valid, errors = validator.validate()

        assert not is_valid
        assert any("unknown delivery channel" in err.lower() for err in errors)

    def test_invalid_max_priorities(self):
        """Test validation catches invalid max_priorities value."""
        config = {
            "version": "1.0.0",
            "briefings": {
                "morning": {
                    "enabled": True,
                    "time": "07:00",
                    "days": {
                        "monday": True,
                        "tuesday": True,
                        "wednesday": True,
                        "thursday": True,
                        "friday": True,
                        "saturday": True,
                        "sunday": True
                    }
                }
            },
            "content": {
                "max_priorities": 15  # Out of range (1-10)
            }
        }

        config_path = self._write_config(config)
        validator = ConfigValidator(str(config_path))
        is_valid, errors = validator.validate()

        assert not is_valid
        assert any("max_priorities" in err.lower() for err in errors)

    def test_invalid_check_interval(self):
        """Test validation catches invalid check_interval_minutes."""
        config = {
            "version": "1.0.0",
            "briefings": {
                "morning": {
                    "enabled": True,
                    "time": "07:00",
                    "days": {
                        "monday": True,
                        "tuesday": True,
                        "wednesday": True,
                        "thursday": True,
                        "friday": True,
                        "saturday": True,
                        "sunday": True
                    }
                }
            },
            "scheduler": {
                "check_interval_minutes": 0  # Invalid (must be 1-60)
            }
        }

        config_path = self._write_config(config)
        validator = ConfigValidator(str(config_path))
        is_valid, errors = validator.validate()

        assert not is_valid
        assert any("check_interval_minutes" in err.lower() for err in errors)

    def test_config_file_not_found(self):
        """Test validation handles missing config file."""
        config_path = self.temp_path / "nonexistent.json"
        validator = ConfigValidator(str(config_path))
        is_valid, errors = validator.validate()

        assert not is_valid
        assert any("not found" in err.lower() for err in errors)

    def test_invalid_json(self):
        """Test validation handles invalid JSON."""
        config_path = self.temp_path / "invalid.json"
        with open(config_path, 'w') as f:
            f.write("{ this is not valid JSON }")

        validator = ConfigValidator(str(config_path))
        is_valid, errors = validator.validate()

        assert not is_valid
        assert any("invalid json" in err.lower() for err in errors)

    def test_validate_config_function(self):
        """Test the validate_config convenience function."""
        config = {
            "version": "1.0.0",
            "briefings": {
                "morning": {
                    "enabled": True,
                    "time": "07:00",
                    "days": {
                        "monday": True,
                        "tuesday": True,
                        "wednesday": True,
                        "thursday": True,
                        "friday": True,
                        "saturday": True,
                        "sunday": True
                    }
                }
            }
        }

        config_path = self._write_config(config)
        is_valid = validate_config(str(config_path), verbose=False)
        assert is_valid

    def test_no_days_enabled_warning(self):
        """Test warning when no days are enabled for a briefing."""
        config = {
            "version": "1.0.0",
            "briefings": {
                "morning": {
                    "enabled": True,
                    "time": "07:00",
                    "days": {
                        "monday": False,
                        "tuesday": False,
                        "wednesday": False,
                        "thursday": False,
                        "friday": False,
                        "saturday": False,
                        "sunday": False
                    }
                }
            }
        }

        config_path = self._write_config(config)
        validator = ConfigValidator(str(config_path))
        is_valid, errors = validator.validate()

        assert not is_valid
        assert any("no days enabled" in err.lower() for err in errors)

    def test_real_config_file_valid(self):
        """Test that the actual config file in repo is valid."""
        # Path to real config file
        config_path = Path(__file__).parent.parent.parent / "config" / "briefing_schedule.json"

        if config_path.exists():
            is_valid = validate_config(str(config_path), verbose=False)
            assert is_valid, "The actual config file should be valid"

    def test_example_config_file_valid(self):
        """Test that the example config file in repo is valid."""
        # Path to example config file
        config_path = Path(__file__).parent.parent.parent / "config" / "briefing_schedule.example.json"

        if config_path.exists():
            is_valid = validate_config(str(config_path), verbose=False)
            assert is_valid, "The example config file should be valid"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
