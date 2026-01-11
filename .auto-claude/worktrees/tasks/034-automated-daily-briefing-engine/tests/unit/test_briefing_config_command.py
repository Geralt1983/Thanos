"""
Unit tests for briefing_config command.
"""

import unittest
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from commands.pa import briefing_config


class TestConfigPath(unittest.TestCase):
    """Test config path resolution."""

    def test_default_schedule_config(self):
        """Test default schedule config path."""
        path = briefing_config.get_config_path()
        self.assertIn('briefing_schedule.json', str(path))
        self.assertIn('config', str(path))

    def test_comprehensive_config(self):
        """Test comprehensive config path."""
        path = briefing_config.get_config_path(comprehensive=True)
        self.assertIn('briefing_config.json', str(path))
        self.assertIn('config', str(path))

    def test_explicit_path(self):
        """Test explicit config path."""
        explicit = '/path/to/config.json'
        path = briefing_config.get_config_path(explicit)
        self.assertEqual(str(path), explicit)


class TestLoadSaveConfig(unittest.TestCase):
    """Test config loading and saving."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / 'test_config.json'
        self.test_config = {
            'version': '1.0.0',
            'briefings': {
                'morning': {
                    'enabled': True,
                    'time': '07:00'
                }
            }
        }

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_load_config(self):
        """Test loading config file."""
        # Write test config
        with open(self.config_path, 'w') as f:
            json.dump(self.test_config, f)

        # Load it
        config = briefing_config.load_config(self.config_path)
        self.assertEqual(config, self.test_config)

    def test_load_missing_file(self):
        """Test loading missing config file."""
        missing_path = Path(self.temp_dir) / 'missing.json'
        with self.assertRaises(FileNotFoundError):
            briefing_config.load_config(missing_path)

    def test_load_invalid_json(self):
        """Test loading invalid JSON."""
        with open(self.config_path, 'w') as f:
            f.write('{ invalid json }')

        with self.assertRaises(json.JSONDecodeError):
            briefing_config.load_config(self.config_path)

    def test_save_config(self):
        """Test saving config file."""
        briefing_config.save_config(self.test_config, self.config_path)

        # Verify saved
        with open(self.config_path, 'r') as f:
            saved = json.load(f)
        self.assertEqual(saved, self.test_config)

    def test_save_creates_backup(self):
        """Test that saving creates backup of existing file."""
        # Write initial config
        with open(self.config_path, 'w') as f:
            json.dump({'old': 'data'}, f)

        # Save new config
        briefing_config.save_config(self.test_config, self.config_path)

        # Check backup exists
        backup_path = self.config_path.with_suffix('.json.bak')
        self.assertTrue(backup_path.exists())

        # Verify backup content
        with open(backup_path, 'r') as f:
            backup = json.load(f)
        self.assertEqual(backup, {'old': 'data'})


class TestNestedOperations(unittest.TestCase):
    """Test nested get/set operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'briefings': {
                'morning': {
                    'enabled': True,
                    'time': '07:00',
                    'days': {
                        'monday': True
                    }
                }
            },
            'content': {
                'max_priorities': 3
            }
        }

    def test_get_top_level(self):
        """Test getting top-level value."""
        value = briefing_config.get_nested_value(self.config, 'content')
        self.assertEqual(value, {'max_priorities': 3})

    def test_get_nested(self):
        """Test getting nested value."""
        value = briefing_config.get_nested_value(self.config, 'briefings.morning.time')
        self.assertEqual(value, '07:00')

    def test_get_deeply_nested(self):
        """Test getting deeply nested value."""
        value = briefing_config.get_nested_value(self.config, 'briefings.morning.days.monday')
        self.assertEqual(value, True)

    def test_get_missing_key(self):
        """Test getting missing key."""
        with self.assertRaises(KeyError):
            briefing_config.get_nested_value(self.config, 'briefings.evening')

    def test_get_invalid_path(self):
        """Test getting with invalid path (accessing non-dict)."""
        with self.assertRaises(KeyError):
            briefing_config.get_nested_value(self.config, 'briefings.morning.time.foo')

    def test_set_nested(self):
        """Test setting nested value."""
        briefing_config.set_nested_value(self.config, 'briefings.morning.time', '08:00')
        self.assertEqual(self.config['briefings']['morning']['time'], '08:00')

    def test_set_deeply_nested(self):
        """Test setting deeply nested value."""
        briefing_config.set_nested_value(self.config, 'briefings.morning.days.monday', False)
        self.assertEqual(self.config['briefings']['morning']['days']['monday'], False)

    def test_set_missing_key(self):
        """Test setting missing key."""
        with self.assertRaises(KeyError):
            briefing_config.set_nested_value(self.config, 'briefings.evening.time', '19:00')

    def test_set_invalid_path(self):
        """Test setting with invalid path (parent is non-dict)."""
        with self.assertRaises(KeyError):
            briefing_config.set_nested_value(self.config, 'content.max_priorities.foo', 'bar')


class TestParseValue(unittest.TestCase):
    """Test value parsing."""

    def test_parse_boolean_true(self):
        """Test parsing boolean true values."""
        self.assertEqual(briefing_config.parse_value('true'), True)
        self.assertEqual(briefing_config.parse_value('True'), True)
        self.assertEqual(briefing_config.parse_value('TRUE'), True)
        self.assertEqual(briefing_config.parse_value('yes'), True)
        self.assertEqual(briefing_config.parse_value('on'), True)

    def test_parse_boolean_false(self):
        """Test parsing boolean false values."""
        self.assertEqual(briefing_config.parse_value('false'), False)
        self.assertEqual(briefing_config.parse_value('False'), False)
        self.assertEqual(briefing_config.parse_value('FALSE'), False)
        self.assertEqual(briefing_config.parse_value('no'), False)
        self.assertEqual(briefing_config.parse_value('off'), False)

    def test_parse_integer(self):
        """Test parsing integer values."""
        self.assertEqual(briefing_config.parse_value('42'), 42)
        self.assertEqual(briefing_config.parse_value('0'), 0)
        self.assertEqual(briefing_config.parse_value('-10'), -10)

    def test_parse_float(self):
        """Test parsing float values."""
        self.assertEqual(briefing_config.parse_value('3.14'), 3.14)
        self.assertEqual(briefing_config.parse_value('0.5'), 0.5)
        self.assertEqual(briefing_config.parse_value('-2.5'), -2.5)

    def test_parse_string(self):
        """Test parsing string values."""
        self.assertEqual(briefing_config.parse_value('hello'), 'hello')
        self.assertEqual(briefing_config.parse_value('07:00'), '07:00')
        self.assertEqual(briefing_config.parse_value('some text'), 'some text')


class TestListKeys(unittest.TestCase):
    """Test listing configuration keys."""

    def test_list_flat_config(self):
        """Test listing keys in flat config."""
        config = {'a': 1, 'b': 2, 'c': 3}
        keys = briefing_config.list_all_keys(config)
        self.assertEqual(sorted(keys), ['a', 'b', 'c'])

    def test_list_nested_config(self):
        """Test listing keys in nested config."""
        config = {
            'briefings': {
                'morning': {'enabled': True}
            },
            'content': {'max_priorities': 3}
        }
        keys = briefing_config.list_all_keys(config)
        self.assertIn('briefings', keys)
        self.assertIn('briefings.morning', keys)
        self.assertIn('briefings.morning.enabled', keys)
        self.assertIn('content', keys)
        self.assertIn('content.max_priorities', keys)

    def test_list_empty_config(self):
        """Test listing keys in empty config."""
        config = {}
        keys = briefing_config.list_all_keys(config)
        self.assertEqual(keys, [])


class TestCommands(unittest.TestCase):
    """Test CLI commands."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / 'test_config.json'
        self.schema_path = Path(self.temp_dir) / 'test_config.schema.json'

        # Create test config
        self.test_config = {
            '$schema': './test_config.schema.json',
            'version': '1.0.0',
            'briefings': {
                'morning': {
                    'enabled': True,
                    'time': '07:00'
                },
                'evening': {
                    'enabled': False,
                    'time': '19:00'
                }
            },
            'content': {
                'max_priorities': 3
            }
        }

        # Create test schema (minimal for validation)
        self.test_schema = {
            '$schema': 'http://json-schema.org/draft-07/schema#',
            'type': 'object',
            'properties': {
                'briefings': {'type': 'object'},
                'content': {'type': 'object'}
            }
        }

        # Write test config and schema
        with open(self.config_path, 'w') as f:
            json.dump(self.test_config, f)
        with open(self.schema_path, 'w') as f:
            json.dump(self.test_schema, f)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_cmd_show(self):
        """Test show command."""
        args = MagicMock()
        args.config = str(self.config_path)
        args.comprehensive = False

        # Capture output
        with patch('sys.stdout', new=StringIO()) as fake_out:
            result = briefing_config.cmd_show(args)

        self.assertEqual(result, 0)
        output = fake_out.getvalue()
        self.assertIn('briefings', output)
        self.assertIn('morning', output)

    def test_cmd_get(self):
        """Test get command."""
        args = MagicMock()
        args.config = str(self.config_path)
        args.comprehensive = False
        args.key = 'briefings.morning.time'

        with patch('sys.stdout', new=StringIO()) as fake_out:
            result = briefing_config.cmd_get(args)

        self.assertEqual(result, 0)
        output = fake_out.getvalue()
        self.assertIn('07:00', output)

    def test_cmd_set(self):
        """Test set command."""
        args = MagicMock()
        args.config = str(self.config_path)
        args.comprehensive = False
        args.key = 'briefings.morning.time'
        args.value = '08:00'

        with patch('sys.stdout', new=StringIO()):
            result = briefing_config.cmd_set(args)

        self.assertEqual(result, 0)

        # Verify change
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        self.assertEqual(config['briefings']['morning']['time'], '08:00')

    def test_cmd_enable(self):
        """Test enable command."""
        args = MagicMock()
        args.config = str(self.config_path)
        args.comprehensive = False
        args.target = 'evening'

        with patch('sys.stdout', new=StringIO()):
            result = briefing_config.cmd_enable(args)

        self.assertEqual(result, 0)

        # Verify change
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        self.assertEqual(config['briefings']['evening']['enabled'], True)

    def test_cmd_disable(self):
        """Test disable command."""
        args = MagicMock()
        args.config = str(self.config_path)
        args.comprehensive = False
        args.target = 'morning'

        with patch('sys.stdout', new=StringIO()):
            result = briefing_config.cmd_disable(args)

        self.assertEqual(result, 0)

        # Verify change
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        self.assertEqual(config['briefings']['morning']['enabled'], False)

    def test_cmd_validate(self):
        """Test validate command."""
        args = MagicMock()
        args.config = str(self.config_path)
        args.comprehensive = False

        with patch('sys.stdout', new=StringIO()):
            result = briefing_config.cmd_validate(args)

        self.assertEqual(result, 0)

    def test_cmd_list_keys(self):
        """Test list-keys command."""
        args = MagicMock()
        args.config = str(self.config_path)
        args.comprehensive = False

        with patch('sys.stdout', new=StringIO()) as fake_out:
            result = briefing_config.cmd_list_keys(args)

        self.assertEqual(result, 0)
        output = fake_out.getvalue()
        self.assertIn('briefings.morning.time', output)
        self.assertIn('briefings.evening.enabled', output)


class TestColorOutput(unittest.TestCase):
    """Test color output functionality."""

    def test_colors_disable(self):
        """Test disabling colors."""
        briefing_config.Colors.disable()
        self.assertEqual(briefing_config.Colors.RED, '')
        self.assertEqual(briefing_config.Colors.GREEN, '')
        self.assertEqual(briefing_config.Colors.BLUE, '')


if __name__ == '__main__':
    unittest.main()
