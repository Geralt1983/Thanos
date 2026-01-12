"""
Configuration Validator for Briefing Schedule

Validates briefing_schedule.json against the JSON schema and provides
helpful error messages for common configuration issues.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

try:
    import jsonschema
    from jsonschema import validate, ValidationError
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False


class ConfigValidator:
    """Validates briefing schedule configuration files."""

    def __init__(self, config_path: str, schema_path: str = None):
        """
        Initialize validator.

        Args:
            config_path: Path to config file (briefing_schedule.json or briefing_config.json)
            schema_path: Path to schema file (auto-detected if None)
        """
        self.config_path = Path(config_path)

        if schema_path is None:
            # Auto-detect schema based on config filename
            if 'briefing_config.json' in str(self.config_path):
                schema_path = self.config_path.parent / "briefing_config.schema.json"
            else:
                schema_path = self.config_path.parent / "briefing_schedule.schema.json"
        self.schema_path = Path(schema_path)

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate configuration file.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check if config file exists
        if not self.config_path.exists():
            errors.append(f"Config file not found: {self.config_path}")
            return False, errors

        # Load config
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON in config file: {e}")
            return False, errors
        except Exception as e:
            errors.append(f"Error reading config file: {e}")
            return False, errors

        # Validate against schema (if jsonschema available)
        if JSONSCHEMA_AVAILABLE and self.schema_path.exists():
            try:
                with open(self.schema_path, 'r') as f:
                    schema = json.load(f)
                validate(instance=config, schema=schema)
            except ValidationError as e:
                errors.append(f"Schema validation error: {e.message}")
                if e.path:
                    path = " -> ".join(str(p) for p in e.path)
                    errors.append(f"  Location: {path}")
                return False, errors
            except Exception as e:
                errors.append(f"Error validating against schema: {e}")
                return False, errors

        # Custom validation checks
        custom_errors = self._custom_validations(config)
        errors.extend(custom_errors)

        if errors:
            return False, errors
        return True, []

    def _custom_validations(self, config: Dict[str, Any]) -> List[str]:
        """
        Perform custom validation checks beyond schema.

        Args:
            config: Parsed configuration dictionary

        Returns:
            List of error messages
        """
        errors = []

        # Check version format
        if 'version' in config:
            version = config['version']
            if not isinstance(version, str) or len(version.split('.')) != 3:
                errors.append("Version must be in format X.Y.Z (e.g., '1.0.0')")

        # Validate briefings section
        if 'briefings' in config:
            for briefing_name, briefing_config in config['briefings'].items():
                errors.extend(self._validate_briefing(briefing_name, briefing_config))

        # Validate delivery channels
        if 'delivery' in config:
            errors.extend(self._validate_delivery(config['delivery']))

        # Validate content settings
        if 'content' in config:
            errors.extend(self._validate_content(config['content']))

        # Validate scheduler settings
        if 'scheduler' in config:
            errors.extend(self._validate_scheduler(config['scheduler']))

        # Validate health settings (new in comprehensive config)
        if 'health' in config:
            errors.extend(self._validate_health(config['health']))

        # Validate templates settings (new in comprehensive config)
        if 'templates' in config:
            errors.extend(self._validate_templates(config['templates']))

        # Validate patterns settings (new in comprehensive config)
        if 'patterns' in config:
            errors.extend(self._validate_patterns(config['patterns']))

        return errors

    def _validate_briefing(self, name: str, config: Dict[str, Any]) -> List[str]:
        """Validate a single briefing configuration."""
        errors = []

        # Check time format
        if 'time' in config:
            time_str = config['time']
            if not isinstance(time_str, str) or ':' not in time_str:
                errors.append(f"Briefing '{name}': Invalid time format '{time_str}' (use HH:MM)")
            else:
                try:
                    hours, minutes = time_str.split(':')
                    h, m = int(hours), int(minutes)
                    if not (0 <= h <= 23 and 0 <= m <= 59):
                        errors.append(f"Briefing '{name}': Time out of range: {time_str}")
                except ValueError:
                    errors.append(f"Briefing '{name}': Invalid time format: {time_str}")

        # Check days configuration
        if 'days' in config:
            days = config['days']
            expected_days = ['monday', 'tuesday', 'wednesday', 'thursday',
                           'friday', 'saturday', 'sunday']
            for day in expected_days:
                if day not in days:
                    errors.append(f"Briefing '{name}': Missing day '{day}' in days config")
                elif not isinstance(days[day], bool):
                    errors.append(f"Briefing '{name}': Day '{day}' must be true/false")

            # Warn if no days enabled
            if all(not days[day] for day in expected_days if day in days):
                errors.append(f"Briefing '{name}': Warning - no days enabled")

        # Validate delivery channels
        if 'delivery_channels' in config:
            valid_channels = ['cli', 'file', 'notification', 'state_sync', 'email']
            channels = config['delivery_channels']
            if not isinstance(channels, list):
                errors.append(f"Briefing '{name}': delivery_channels must be an array")
            else:
                for channel in channels:
                    if channel not in valid_channels:
                        errors.append(
                            f"Briefing '{name}': Unknown delivery channel '{channel}' "
                            f"(valid: {', '.join(valid_channels)})"
                        )

        return errors

    def _validate_delivery(self, config: Dict[str, Any]) -> List[str]:
        """Validate delivery configuration."""
        errors = []

        # Validate file output settings
        if 'file' in config and config['file'].get('enabled'):
            file_config = config['file']
            if 'output_dir' in file_config:
                output_dir = Path(file_config['output_dir'])
                # Don't fail if dir doesn't exist (might be created), just warn
                if output_dir.is_absolute() and not output_dir.parent.exists():
                    errors.append(
                        f"Warning: Output directory parent does not exist: {output_dir.parent}"
                    )

        return errors

    def _validate_content(self, config: Dict[str, Any]) -> List[str]:
        """Validate content configuration."""
        errors = []

        # Validate max_priorities
        if 'max_priorities' in config:
            max_priorities = config['max_priorities']
            if not isinstance(max_priorities, int) or not (1 <= max_priorities <= 10):
                errors.append(
                    f"max_priorities must be an integer between 1 and 10 (got: {max_priorities})"
                )

        return errors

    def _validate_scheduler(self, config: Dict[str, Any]) -> List[str]:
        """Validate scheduler configuration."""
        errors = []

        # Validate check_interval_minutes
        if 'check_interval_minutes' in config:
            interval = config['check_interval_minutes']
            if not isinstance(interval, int) or not (1 <= interval <= 60):
                errors.append(
                    f"check_interval_minutes must be between 1 and 60 (got: {interval})"
                )

        # Validate log_level
        if 'log_level' in config:
            log_level = config['log_level']
            valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
            if log_level not in valid_levels:
                errors.append(
                    f"log_level must be one of {valid_levels} (got: {log_level})"
                )

        return errors

    def _validate_health(self, config: Dict[str, Any]) -> List[str]:
        """Validate health tracking configuration."""
        errors = []

        # Validate energy scale
        if 'energy_scale' in config:
            scale = config['energy_scale']
            if 'min' in scale and 'max' in scale:
                min_val, max_val = scale['min'], scale['max']
                if not isinstance(min_val, int) or not isinstance(max_val, int):
                    errors.append("Health: energy_scale min/max must be integers")
                elif min_val >= max_val:
                    errors.append(f"Health: energy_scale min ({min_val}) must be < max ({max_val})")

        # Validate medication settings
        if 'medication' in config:
            med = config['medication']
            if 'peak_hours_after' in med:
                hours = med['peak_hours_after']
                if not isinstance(hours, int) or not (1 <= hours <= 8):
                    errors.append(
                        f"Health: peak_hours_after must be between 1 and 8 (got: {hours})"
                    )
            if 'peak_duration_hours' in med:
                duration = med['peak_duration_hours']
                if not isinstance(duration, int) or not (1 <= duration <= 6):
                    errors.append(
                        f"Health: peak_duration_hours must be between 1 and 6 (got: {duration})"
                    )

        return errors

    def _validate_templates(self, config: Dict[str, Any]) -> List[str]:
        """Validate templates configuration."""
        errors = []

        # Validate templates_dir exists (warning only)
        if 'templates_dir' in config:
            templates_dir = Path(config['templates_dir'])
            if not templates_dir.exists():
                errors.append(f"Warning: Templates directory does not exist: {templates_dir}")

        # Validate fallback_behavior
        if 'fallback_behavior' in config:
            fallback = config['fallback_behavior']
            valid_behaviors = ['error', 'default', 'llm']
            if fallback not in valid_behaviors:
                errors.append(
                    f"Templates: fallback_behavior must be one of {valid_behaviors} (got: {fallback})"
                )

        return errors

    def _validate_patterns(self, config: Dict[str, Any]) -> List[str]:
        """Validate pattern learning configuration."""
        errors = []

        # Validate minimum_days_required
        if 'minimum_days_required' in config:
            days = config['minimum_days_required']
            if not isinstance(days, int) or not (7 <= days <= 90):
                errors.append(
                    f"Patterns: minimum_days_required must be between 7 and 90 (got: {days})"
                )

        # Validate lookback_days
        if 'lookback_days' in config:
            days = config['lookback_days']
            if not isinstance(days, int) or not (14 <= days <= 180):
                errors.append(
                    f"Patterns: lookback_days must be between 14 and 180 (got: {days})"
                )

        # Validate influence_level
        if 'influence_level' in config:
            level = config['influence_level']
            valid_levels = ['low', 'medium', 'high']
            if level not in valid_levels:
                errors.append(
                    f"Patterns: influence_level must be one of {valid_levels} (got: {level})"
                )

        return errors


def validate_config(config_path: str, schema_path: str = None, verbose: bool = True) -> bool:
    """
    Validate a briefing configuration file (schedule or comprehensive config).

    Args:
        config_path: Path to config file (briefing_schedule.json or briefing_config.json)
        schema_path: Path to schema file (auto-detected if None)
        verbose: Print validation results

    Returns:
        True if valid, False otherwise
    """
    validator = ConfigValidator(config_path, schema_path)
    is_valid, errors = validator.validate()

    if verbose:
        if is_valid:
            print(f"✓ Configuration valid: {config_path}")
        else:
            print(f"✗ Configuration invalid: {config_path}")
            print("\nErrors found:")
            for error in errors:
                print(f"  • {error}")

    return is_valid


def main():
    """CLI entry point for config validation."""
    if len(sys.argv) < 2:
        print("Usage: python -m Tools.config_validator <config_path> [schema_path]")
        print("\nExamples:")
        print("  python -m Tools.config_validator config/briefing_schedule.json")
        print("  python -m Tools.config_validator config/briefing_config.json")
        print("  python -m Tools.config_validator config/briefing_config.json config/briefing_config.schema.json")
        sys.exit(1)

    config_path = sys.argv[1]
    schema_path = sys.argv[2] if len(sys.argv) > 2 else None

    is_valid = validate_config(config_path, schema_path, verbose=True)
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
