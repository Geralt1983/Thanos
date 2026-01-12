"""
Personal Assistant: Briefing Configuration Manager

View and edit briefing configuration without manual JSON editing.

Usage:
    python -m commands.pa.briefing_config show
    python -m commands.pa.briefing_config get briefings.morning.time
    python -m commands.pa.briefing_config set briefings.morning.time 07:30
    python -m commands.pa.briefing_config enable evening
    python -m commands.pa.briefing_config disable evening
    python -m commands.pa.briefing_config validate
    python -m commands.pa.briefing_config list-keys

Options:
    --config PATH       Path to config file (default: config/briefing_schedule.json)
    --comprehensive     Use comprehensive config (config/briefing_config.json)
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.config_validator import ConfigValidator


# ANSI color codes for pretty printing
class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

    @staticmethod
    def disable():
        """Disable colors."""
        Colors.HEADER = ''
        Colors.BLUE = ''
        Colors.CYAN = ''
        Colors.GREEN = ''
        Colors.YELLOW = ''
        Colors.RED = ''
        Colors.BOLD = ''
        Colors.UNDERLINE = ''
        Colors.END = ''


def get_config_path(config_path: Optional[str] = None, comprehensive: bool = False) -> Path:
    """
    Get the configuration file path.

    Args:
        config_path: Optional explicit path
        comprehensive: Use comprehensive config instead of simple schedule

    Returns:
        Path to config file
    """
    if config_path:
        return Path(config_path)

    project_root = Path(__file__).parent.parent.parent
    if comprehensive:
        return project_root / "config" / "briefing_config.json"
    else:
        return project_root / "config" / "briefing_schedule.json"


def load_config(config_path: Path) -> Dict[str, Any]:
    """
    Load configuration file.

    Args:
        config_path: Path to config file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is not valid JSON
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r') as f:
        return json.load(f)


def save_config(config: Dict[str, Any], config_path: Path) -> None:
    """
    Save configuration file.

    Args:
        config: Configuration dictionary
        config_path: Path to save to
    """
    # Create backup
    if config_path.exists():
        backup_path = config_path.with_suffix('.json.bak')
        with open(config_path, 'r') as f:
            backup_content = f.read()
        with open(backup_path, 'w') as f:
            f.write(backup_content)

    # Save new config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
        f.write('\n')  # Add trailing newline


def validate_config(config_path: Path) -> bool:
    """
    Validate configuration file.

    Args:
        config_path: Path to config file

    Returns:
        True if valid, False otherwise
    """
    validator = ConfigValidator(str(config_path))
    is_valid, errors = validator.validate()

    if is_valid:
        print(f"{Colors.GREEN}✓{Colors.END} Configuration is valid: {config_path}")
        return True
    else:
        print(f"{Colors.RED}✗{Colors.END} Configuration is invalid:")
        for error in errors:
            print(f"  {Colors.RED}•{Colors.END} {error}")
        return False


def get_nested_value(config: Dict[str, Any], key_path: str) -> Any:
    """
    Get nested value from config using dot notation.

    Args:
        config: Configuration dictionary
        key_path: Dot-separated key path (e.g., "briefings.morning.time")

    Returns:
        Value at key path

    Raises:
        KeyError: If key path doesn't exist
    """
    keys = key_path.split('.')
    value = config

    for key in keys:
        if isinstance(value, dict):
            if key not in value:
                raise KeyError(f"Key not found: {key_path}")
            value = value[key]
        else:
            raise KeyError(f"Cannot access '{key}' in non-dict value at {key_path}")

    return value


def set_nested_value(config: Dict[str, Any], key_path: str, value: Any) -> None:
    """
    Set nested value in config using dot notation.

    Args:
        config: Configuration dictionary
        key_path: Dot-separated key path (e.g., "briefings.morning.time")
        value: Value to set

    Raises:
        KeyError: If parent keys don't exist
    """
    keys = key_path.split('.')
    target = config

    # Navigate to parent
    for key in keys[:-1]:
        if key not in target:
            raise KeyError(f"Parent key not found: {key}")
        if not isinstance(target[key], dict):
            raise KeyError(f"Cannot set value in non-dict at {key}")
        target = target[key]

    # Set value
    final_key = keys[-1]
    if final_key not in target:
        raise KeyError(f"Key not found: {key_path}")

    target[final_key] = value


def parse_value(value_str: str) -> Any:
    """
    Parse string value to appropriate type.

    Args:
        value_str: String value to parse

    Returns:
        Parsed value (bool, int, float, or string)
    """
    # Try boolean
    if value_str.lower() in ('true', 'yes', 'on'):
        return True
    if value_str.lower() in ('false', 'no', 'off'):
        return False

    # Try number
    try:
        if '.' in value_str:
            return float(value_str)
        else:
            return int(value_str)
    except ValueError:
        pass

    # Return as string
    return value_str


def pretty_print_json(data: Any, indent: int = 0, max_depth: int = 10) -> None:
    """
    Pretty print JSON data with colors.

    Args:
        data: Data to print
        indent: Current indentation level
        max_depth: Maximum depth to print
    """
    if indent > max_depth:
        print(f"{' ' * (indent * 2)}...")
        return

    if isinstance(data, dict):
        if not data:
            print("{}")
            return

        for i, (key, value) in enumerate(data.items()):
            is_last = (i == len(data) - 1)
            prefix = ' ' * (indent * 2)

            # Print key
            print(f"{prefix}{Colors.CYAN}{key}{Colors.END}: ", end='')

            # Print value
            if isinstance(value, dict):
                print("{")
                pretty_print_json(value, indent + 1, max_depth)
                print(f"{prefix}" + (',' if not is_last else '}'))
            elif isinstance(value, list):
                print("[")
                pretty_print_json(value, indent + 1, max_depth)
                print(f"{prefix}" + (',' if not is_last else ']'))
            elif isinstance(value, bool):
                color = Colors.GREEN if value else Colors.YELLOW
                print(f"{color}{str(value).lower()}{Colors.END}" + (',' if not is_last else ''))
            elif isinstance(value, (int, float)):
                print(f"{Colors.BLUE}{value}{Colors.END}" + (',' if not is_last else ''))
            elif isinstance(value, str):
                print(f'{Colors.YELLOW}"{value}"{Colors.END}' + (',' if not is_last else ''))
            elif value is None:
                print(f"{Colors.YELLOW}null{Colors.END}" + (',' if not is_last else ''))
            else:
                print(f"{value}" + (',' if not is_last else ''))

    elif isinstance(data, list):
        if not data:
            print("[]")
            return

        for i, item in enumerate(data):
            is_last = (i == len(data) - 1)
            prefix = ' ' * (indent * 2)
            print(f"{prefix}", end='')

            if isinstance(item, (dict, list)):
                pretty_print_json(item, indent + 1, max_depth)
                if not is_last:
                    print(",")
            elif isinstance(item, bool):
                color = Colors.GREEN if item else Colors.YELLOW
                print(f"{color}{str(item).lower()}{Colors.END}" + (',' if not is_last else ''))
            elif isinstance(item, (int, float)):
                print(f"{Colors.BLUE}{item}{Colors.END}" + (',' if not is_last else ''))
            elif isinstance(item, str):
                print(f'{Colors.YELLOW}"{item}"{Colors.END}' + (',' if not is_last else ''))
            else:
                print(f"{item}" + (',' if not is_last else ''))


def list_all_keys(data: Dict[str, Any], prefix: str = '') -> List[str]:
    """
    List all keys in config (dot notation paths).

    Args:
        data: Configuration dictionary
        prefix: Current key prefix

    Returns:
        List of dot-notation key paths
    """
    keys = []

    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        keys.append(full_key)

        if isinstance(value, dict):
            keys.extend(list_all_keys(value, full_key))

    return keys


def cmd_show(args: argparse.Namespace) -> int:
    """Show entire configuration."""
    try:
        config_path = get_config_path(args.config, args.comprehensive)
        config = load_config(config_path)

        print(f"\n{Colors.BOLD}Configuration:{Colors.END} {config_path}\n")
        pretty_print_json(config)
        print()

        return 0
    except FileNotFoundError as e:
        print(f"{Colors.RED}Error:{Colors.END} {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"{Colors.RED}Error:{Colors.END} Invalid JSON: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"{Colors.RED}Error:{Colors.END} {e}", file=sys.stderr)
        return 1


def cmd_get(args: argparse.Namespace) -> int:
    """Get specific configuration value."""
    try:
        config_path = get_config_path(args.config, args.comprehensive)
        config = load_config(config_path)

        value = get_nested_value(config, args.key)

        print(f"\n{Colors.CYAN}{args.key}{Colors.END}: ", end='')
        if isinstance(value, (dict, list)):
            print()
            pretty_print_json(value, indent=1)
            print()
        else:
            if isinstance(value, bool):
                color = Colors.GREEN if value else Colors.YELLOW
                print(f"{color}{str(value).lower()}{Colors.END}")
            elif isinstance(value, (int, float)):
                print(f"{Colors.BLUE}{value}{Colors.END}")
            elif isinstance(value, str):
                print(f'{Colors.YELLOW}"{value}"{Colors.END}')
            else:
                print(value)

        return 0
    except FileNotFoundError as e:
        print(f"{Colors.RED}Error:{Colors.END} {e}", file=sys.stderr)
        return 1
    except KeyError as e:
        print(f"{Colors.RED}Error:{Colors.END} {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"{Colors.RED}Error:{Colors.END} {e}", file=sys.stderr)
        return 1


def cmd_set(args: argparse.Namespace) -> int:
    """Set specific configuration value."""
    try:
        config_path = get_config_path(args.config, args.comprehensive)
        config = load_config(config_path)

        # Parse value
        new_value = parse_value(args.value)

        # Get old value
        try:
            old_value = get_nested_value(config, args.key)
            print(f"\n{Colors.CYAN}{args.key}{Colors.END}:")
            print(f"  Old: {Colors.YELLOW}{old_value}{Colors.END}")
            print(f"  New: {Colors.GREEN}{new_value}{Colors.END}\n")
        except KeyError:
            print(f"\n{Colors.CYAN}{args.key}{Colors.END}:")
            print(f"  Setting new value: {Colors.GREEN}{new_value}{Colors.END}\n")

        # Set new value
        set_nested_value(config, args.key, new_value)

        # Validate before saving
        temp_path = config_path.with_suffix('.json.tmp')
        with open(temp_path, 'w') as f:
            json.dump(config, f, indent=2)

        if not validate_config(temp_path):
            temp_path.unlink()
            print(f"\n{Colors.RED}Error:{Colors.END} Configuration would be invalid. Changes not saved.", file=sys.stderr)
            return 1

        temp_path.unlink()

        # Save
        save_config(config, config_path)
        print(f"{Colors.GREEN}✓{Colors.END} Configuration saved: {config_path}")

        # Show backup location
        backup_path = config_path.with_suffix('.json.bak')
        if backup_path.exists():
            print(f"{Colors.BLUE}ℹ{Colors.END} Backup saved: {backup_path}")

        return 0
    except FileNotFoundError as e:
        print(f"{Colors.RED}Error:{Colors.END} {e}", file=sys.stderr)
        return 1
    except KeyError as e:
        print(f"{Colors.RED}Error:{Colors.END} {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"{Colors.RED}Error:{Colors.END} {e}", file=sys.stderr)
        return 1


def cmd_enable(args: argparse.Namespace) -> int:
    """Enable a briefing or feature."""
    try:
        config_path = get_config_path(args.config, args.comprehensive)
        config = load_config(config_path)

        # Determine what to enable
        target = args.target.lower()

        # Map common names to config keys
        key_map = {
            'morning': 'briefings.morning.enabled',
            'evening': 'briefings.evening.enabled',
            'health': 'health.enabled',
            'patterns': 'patterns.enabled',
            'notification': 'delivery.notification.enabled',
            'notifications': 'delivery.notification.enabled',
            'state_sync': 'delivery.state_sync.enabled',
            'email': 'delivery.email.enabled',
        }

        if target in key_map:
            key = key_map[target]
        else:
            # Assume it's a direct key path
            key = target

        # Enable it
        set_nested_value(config, key, True)

        print(f"\n{Colors.GREEN}✓{Colors.END} Enabled: {Colors.CYAN}{target}{Colors.END}")
        print(f"  Setting: {Colors.CYAN}{key}{Colors.END} = {Colors.GREEN}true{Colors.END}\n")

        # Validate before saving
        temp_path = config_path.with_suffix('.json.tmp')
        with open(temp_path, 'w') as f:
            json.dump(config, f, indent=2)

        if not validate_config(temp_path):
            temp_path.unlink()
            print(f"\n{Colors.RED}Error:{Colors.END} Configuration would be invalid. Changes not saved.", file=sys.stderr)
            return 1

        temp_path.unlink()

        # Save
        save_config(config, config_path)
        print(f"{Colors.GREEN}✓{Colors.END} Configuration saved: {config_path}")

        return 0
    except FileNotFoundError as e:
        print(f"{Colors.RED}Error:{Colors.END} {e}", file=sys.stderr)
        return 1
    except KeyError as e:
        print(f"{Colors.RED}Error:{Colors.END} Key not found: {e}", file=sys.stderr)
        print(f"{Colors.YELLOW}Hint:{Colors.END} Use 'list-keys' to see all available keys", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"{Colors.RED}Error:{Colors.END} {e}", file=sys.stderr)
        return 1


def cmd_disable(args: argparse.Namespace) -> int:
    """Disable a briefing or feature."""
    try:
        config_path = get_config_path(args.config, args.comprehensive)
        config = load_config(config_path)

        # Determine what to disable
        target = args.target.lower()

        # Map common names to config keys
        key_map = {
            'morning': 'briefings.morning.enabled',
            'evening': 'briefings.evening.enabled',
            'health': 'health.enabled',
            'patterns': 'patterns.enabled',
            'notification': 'delivery.notification.enabled',
            'notifications': 'delivery.notification.enabled',
            'state_sync': 'delivery.state_sync.enabled',
            'email': 'delivery.email.enabled',
        }

        if target in key_map:
            key = key_map[target]
        else:
            # Assume it's a direct key path
            key = target

        # Disable it
        set_nested_value(config, key, False)

        print(f"\n{Colors.YELLOW}⚠{Colors.END} Disabled: {Colors.CYAN}{target}{Colors.END}")
        print(f"  Setting: {Colors.CYAN}{key}{Colors.END} = {Colors.YELLOW}false{Colors.END}\n")

        # Validate before saving
        temp_path = config_path.with_suffix('.json.tmp')
        with open(temp_path, 'w') as f:
            json.dump(config, f, indent=2)

        if not validate_config(temp_path):
            temp_path.unlink()
            print(f"\n{Colors.RED}Error:{Colors.END} Configuration would be invalid. Changes not saved.", file=sys.stderr)
            return 1

        temp_path.unlink()

        # Save
        save_config(config, config_path)
        print(f"{Colors.GREEN}✓{Colors.END} Configuration saved: {config_path}")

        return 0
    except FileNotFoundError as e:
        print(f"{Colors.RED}Error:{Colors.END} {e}", file=sys.stderr)
        return 1
    except KeyError as e:
        print(f"{Colors.RED}Error:{Colors.END} Key not found: {e}", file=sys.stderr)
        print(f"{Colors.YELLOW}Hint:{Colors.END} Use 'list-keys' to see all available keys", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"{Colors.RED}Error:{Colors.END} {e}", file=sys.stderr)
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate configuration file."""
    try:
        config_path = get_config_path(args.config, args.comprehensive)
        return 0 if validate_config(config_path) else 1
    except FileNotFoundError as e:
        print(f"{Colors.RED}Error:{Colors.END} {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"{Colors.RED}Error:{Colors.END} {e}", file=sys.stderr)
        return 1


def cmd_list_keys(args: argparse.Namespace) -> int:
    """List all configuration keys."""
    try:
        config_path = get_config_path(args.config, args.comprehensive)
        config = load_config(config_path)

        keys = list_all_keys(config)

        print(f"\n{Colors.BOLD}Configuration keys:{Colors.END} {config_path}\n")

        # Group by top-level section
        sections = {}
        for key in keys:
            parts = key.split('.')
            section = parts[0]
            if section not in sections:
                sections[section] = []
            sections[section].append(key)

        for section, section_keys in sorted(sections.items()):
            print(f"{Colors.CYAN}{section}{Colors.END}:")
            for key in sorted(section_keys):
                # Get value type
                try:
                    value = get_nested_value(config, key)
                    type_str = type(value).__name__
                    if isinstance(value, dict):
                        type_str = f"dict ({len(value)} keys)"
                    elif isinstance(value, list):
                        type_str = f"list ({len(value)} items)"
                    print(f"  {key:50} {Colors.BLUE}[{type_str}]{Colors.END}")
                except:
                    print(f"  {key}")
            print()

        print(f"{Colors.BLUE}Total: {len(keys)} keys{Colors.END}\n")

        return 0
    except FileNotFoundError as e:
        print(f"{Colors.RED}Error:{Colors.END} {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"{Colors.RED}Error:{Colors.END} Invalid JSON: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"{Colors.RED}Error:{Colors.END} {e}", file=sys.stderr)
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Briefing configuration manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show entire configuration
  python -m commands.pa.briefing_config show

  # Get specific value
  python -m commands.pa.briefing_config get briefings.morning.time

  # Set a value
  python -m commands.pa.briefing_config set briefings.morning.time 07:30

  # Enable/disable features
  python -m commands.pa.briefing_config enable evening
  python -m commands.pa.briefing_config disable notifications

  # Validate configuration
  python -m commands.pa.briefing_config validate

  # List all keys
  python -m commands.pa.briefing_config list-keys

  # Use comprehensive config
  python -m commands.pa.briefing_config show --comprehensive
        """
    )

    # Global options
    parser.add_argument('--config', type=str, help='Path to config file')
    parser.add_argument('--comprehensive', action='store_true',
                       help='Use comprehensive config (briefing_config.json)')
    parser.add_argument('--no-color', action='store_true', help='Disable colored output')

    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # show command
    subparsers.add_parser('show', help='Show entire configuration')

    # get command
    parser_get = subparsers.add_parser('get', help='Get specific configuration value')
    parser_get.add_argument('key', help='Configuration key (dot notation, e.g., briefings.morning.time)')

    # set command
    parser_set = subparsers.add_parser('set', help='Set configuration value')
    parser_set.add_argument('key', help='Configuration key (dot notation)')
    parser_set.add_argument('value', help='New value')

    # enable command
    parser_enable = subparsers.add_parser('enable', help='Enable a briefing or feature')
    parser_enable.add_argument('target', help='What to enable (morning, evening, health, patterns, notifications, etc.)')

    # disable command
    parser_disable = subparsers.add_parser('disable', help='Disable a briefing or feature')
    parser_disable.add_argument('target', help='What to disable (morning, evening, health, patterns, notifications, etc.)')

    # validate command
    subparsers.add_parser('validate', help='Validate configuration file')

    # list-keys command
    subparsers.add_parser('list-keys', help='List all configuration keys')

    args = parser.parse_args()

    # Disable colors if requested
    if args.no_color:
        Colors.disable()

    # Execute command
    if args.command == 'show':
        return cmd_show(args)
    elif args.command == 'get':
        return cmd_get(args)
    elif args.command == 'set':
        return cmd_set(args)
    elif args.command == 'enable':
        return cmd_enable(args)
    elif args.command == 'disable':
        return cmd_disable(args)
    elif args.command == 'validate':
        return cmd_validate(args)
    elif args.command == 'list-keys':
        return cmd_list_keys(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
