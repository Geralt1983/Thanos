# Briefing Configuration CLI

Command-line tool for managing briefing configuration without manual JSON editing.

## Overview

The `briefing_config` command provides a user-friendly interface for viewing and editing briefing configuration files. It supports both the simple schedule config (`briefing_schedule.json`) and comprehensive config (`briefing_config.json`).

## Features

- **Show** - Display entire configuration with pretty-printing and colors
- **Get** - Retrieve specific configuration values
- **Set** - Update configuration values with validation
- **Enable/Disable** - Toggle features and briefings
- **Validate** - Check configuration against schema
- **List Keys** - Browse all available configuration keys

## Installation

No installation required. The command is available once you have the briefing engine set up.

## Usage

### Basic Syntax

```bash
python -m commands.pa.briefing_config [options] <command> [arguments]
```

Or run directly:

```bash
python3 ./commands/pa/briefing_config.py [options] <command> [arguments]
```

### Global Options

- `--config PATH` - Path to custom config file
- `--comprehensive` - Use comprehensive config (`briefing_config.json`)
- `--no-color` - Disable colored output

### Commands

#### 1. Show Configuration

Display the entire configuration with pretty-printing:

```bash
python -m commands.pa.briefing_config show

# Use comprehensive config
python -m commands.pa.briefing_config --comprehensive show

# Use custom config file
python -m commands.pa.briefing_config --config /path/to/config.json show
```

**Output:**
```
Configuration: /path/to/briefing_schedule.json

briefings: {
  morning: {
    enabled: true,
    time: "07:00",
    ...
  }
}
```

#### 2. Get Specific Value

Retrieve a specific configuration value using dot notation:

```bash
# Get briefing time
python -m commands.pa.briefing_config get briefings.morning.time

# Get nested value
python -m commands.pa.briefing_config get briefings.morning.days.monday

# Get complex value (dict/list)
python -m commands.pa.briefing_config get briefings.morning.days
```

**Output:**
```
briefings.morning.time: "07:00"
```

#### 3. Set Value

Update a configuration value (with automatic validation and backup):

```bash
# Set briefing time
python -m commands.pa.briefing_config set briefings.morning.time 08:30

# Set boolean value (accepts: true/false, yes/no, on/off)
python -m commands.pa.briefing_config set briefings.morning.enabled true

# Set number
python -m commands.pa.briefing_config set content.max_priorities 5
```

**Features:**
- Automatic type parsing (bool, int, float, string)
- Shows old and new values
- Validates before saving
- Creates backup (`.json.bak`)
- Rolls back if validation fails

**Output:**
```
briefings.morning.time:
  Old: 07:00
  New: 08:30

✓ Configuration is valid: /path/to/config.json.tmp
✓ Configuration saved: /path/to/config.json
ℹ Backup saved: /path/to/config.json.bak
```

#### 4. Enable Feature

Enable a briefing or feature:

```bash
# Enable evening briefing
python -m commands.pa.briefing_config enable evening

# Enable health tracking
python -m commands.pa.briefing_config --comprehensive enable health

# Enable notifications
python -m commands.pa.briefing_config enable notifications
```

**Shortcuts:**
- `morning` → `briefings.morning.enabled`
- `evening` → `briefings.evening.enabled`
- `health` → `health.enabled`
- `patterns` → `patterns.enabled`
- `notification` / `notifications` → `delivery.notification.enabled`
- `state_sync` → `delivery.state_sync.enabled`
- `email` → `delivery.email.enabled`

**Output:**
```
✓ Enabled: evening
  Setting: briefings.evening.enabled = true

✓ Configuration saved: /path/to/config.json
```

#### 5. Disable Feature

Disable a briefing or feature:

```bash
# Disable evening briefing
python -m commands.pa.briefing_config disable evening

# Disable health tracking
python -m commands.pa.briefing_config --comprehensive disable health

# Disable notifications
python -m commands.pa.briefing_config disable notifications
```

**Output:**
```
⚠ Disabled: evening
  Setting: briefings.evening.enabled = false

✓ Configuration saved: /path/to/config.json
```

#### 6. Validate Configuration

Validate configuration against JSON schema:

```bash
python -m commands.pa.briefing_config validate

# Validate comprehensive config
python -m commands.pa.briefing_config --comprehensive validate

# Validate custom config
python -m commands.pa.briefing_config --config /path/to/config.json validate
```

**Output (success):**
```
✓ Configuration is valid: /path/to/config.json
```

**Output (error):**
```
✗ Configuration is invalid:
  • Schema validation error: 'time' is a required property
  • Location: briefings -> morning
```

#### 7. List All Keys

Browse all available configuration keys:

```bash
python -m commands.pa.briefing_config list-keys

# List comprehensive config keys
python -m commands.pa.briefing_config --comprehensive list-keys
```

**Output:**
```
Configuration keys: /path/to/briefing_schedule.json

briefings:
  briefings                                          [dict (2 keys)]
  briefings.morning                                  [dict (6 keys)]
  briefings.morning.enabled                          [bool]
  briefings.morning.time                             [str]
  briefings.morning.days                             [dict (7 keys)]
  briefings.morning.days.monday                      [bool]
  ...

delivery:
  delivery                                           [dict (4 keys)]
  delivery.cli                                       [dict (2 keys)]
  delivery.cli.enabled                               [bool]
  ...

Total: 85 keys
```

## Examples

### Common Workflows

#### Change Morning Briefing Time

```bash
# Show current time
python -m commands.pa.briefing_config get briefings.morning.time

# Change to 08:30
python -m commands.pa.briefing_config set briefings.morning.time 08:30

# Verify change
python -m commands.pa.briefing_config get briefings.morning.time
```

#### Enable Evening Briefing on Weekdays Only

```bash
# Enable evening briefing
python -m commands.pa.briefing_config enable evening

# Disable for Saturday
python -m commands.pa.briefing_config set briefings.evening.days.saturday false

# Verify configuration
python -m commands.pa.briefing_config get briefings.evening.days
```

#### Enable Health Tracking

```bash
# Enable health tracking (comprehensive config)
python -m commands.pa.briefing_config --comprehensive enable health

# Enable energy prompts
python -m commands.pa.briefing_config --comprehensive set health.prompt_for_energy true

# Enable evening reflection
python -m commands.pa.briefing_config --comprehensive set health.evening_reflection true

# Verify
python -m commands.pa.briefing_config --comprehensive get health
```

#### Configure Delivery Channels

```bash
# Enable notifications
python -m commands.pa.briefing_config enable notifications

# Enable state sync (comprehensive config)
python -m commands.pa.briefing_config --comprehensive enable state_sync

# Disable CLI output
python -m commands.pa.briefing_config set delivery.cli.enabled false
```

#### Adjust Content Settings

```bash
# Change max priorities
python -m commands.pa.briefing_config set content.max_priorities 5

# Enable quick wins
python -m commands.pa.briefing_config set content.include_quick_wins true

# Enable weekend mode
python -m commands.pa.briefing_config set content.weekend_mode.enabled true
```

## Configuration Files

### Simple Schedule Config

**File:** `config/briefing_schedule.json`

**Features:**
- Basic scheduling (morning/evening times)
- Day-of-week configuration
- Delivery channel selection
- Content options

**Use when:** You only need basic scheduling without health tracking or advanced features.

**Command:**
```bash
python -m commands.pa.briefing_config <command>
```

### Comprehensive Config

**File:** `config/briefing_config.json`

**Features:**
- Everything in schedule config, plus:
- Health tracking configuration
- Custom content sections
- Pattern learning settings
- Advanced LLM options
- Extended delivery options

**Use when:** You want full control over all briefing engine features.

**Command:**
```bash
python -m commands.pa.briefing_config --comprehensive <command>
```

## Key Path Notation

Configuration keys use dot notation to access nested values:

| Path | Description |
|------|-------------|
| `briefings.morning.time` | Morning briefing time |
| `briefings.morning.enabled` | Enable/disable morning briefing |
| `briefings.morning.days.monday` | Enable Monday morning briefing |
| `delivery.cli.enabled` | Enable CLI output |
| `delivery.file.output_dir` | File delivery directory |
| `content.max_priorities` | Number of priorities to show |
| `health.enabled` | Enable health tracking (comprehensive) |
| `patterns.enabled` | Enable pattern learning (comprehensive) |

Use `list-keys` command to see all available keys.

## Value Types

The tool automatically parses values based on their type:

### Boolean Values

Accepts multiple formats:
- `true`, `True`, `TRUE`, `yes`, `on` → `true`
- `false`, `False`, `FALSE`, `no`, `off` → `false`

```bash
python -m commands.pa.briefing_config set briefings.morning.enabled true
python -m commands.pa.briefing_config set briefings.evening.enabled no
```

### Numbers

Automatically detected:
- Integer: `3`, `42`, `-10`
- Float: `3.14`, `0.5`, `-2.5`

```bash
python -m commands.pa.briefing_config set content.max_priorities 5
python -m commands.pa.briefing_config --comprehensive set health.energy_scale.max 10
```

### Strings

Everything else is treated as string:

```bash
python -m commands.pa.briefing_config set briefings.morning.time 08:30
python -m commands.pa.briefing_config set delivery.file.output_dir History/Briefings
```

## Validation

### Automatic Validation

Every `set`, `enable`, and `disable` command validates the configuration before saving:

1. Writes to temporary file
2. Validates against JSON schema
3. Runs custom validation checks
4. Only saves if valid
5. Creates backup of previous version

### Manual Validation

Run validation at any time:

```bash
python -m commands.pa.briefing_config validate
```

### Validation Errors

Clear error messages with location information:

```
✗ Configuration is invalid:
  • Schema validation error: '07:00' does not match pattern '^([0-1][0-9]|2[0-3]):[0-5][0-9]$'
  • Location: briefings -> morning -> time
```

## Safety Features

### Automatic Backups

Every change creates a backup of the previous configuration:

**Backup file:** `<config>.json.bak`

To restore from backup:
```bash
cp config/briefing_schedule.json.bak config/briefing_schedule.json
```

### Validation Before Save

Configuration is validated before writing to ensure you never end up with invalid config:

```bash
# This will fail validation and not save
python -m commands.pa.briefing_config set briefings.morning.time 25:00

# Output:
# ✗ Configuration is invalid:
#   • Time must be in HH:MM format (00:00 to 23:59)
# Error: Configuration would be invalid. Changes not saved.
```

### Non-Destructive Operations

- `show` - read-only
- `get` - read-only
- `list-keys` - read-only
- `validate` - read-only
- `set` / `enable` / `disable` - validated before save

## Colored Output

By default, output includes colors for better readability:

- **Green** - success, true values, enabled
- **Yellow** - warnings, false values, disabled, strings
- **Blue** - information, numbers
- **Cyan** - keys, section headers
- **Red** - errors

To disable colors:
```bash
python -m commands.pa.briefing_config --no-color <command>
```

## Error Handling

### Common Errors

#### Key Not Found

```bash
$ python -m commands.pa.briefing_config get foo.bar
Error: Key not found: foo.bar
```

**Solution:** Use `list-keys` to see available keys.

#### Invalid Value Type

```bash
$ python -m commands.pa.briefing_config set content.max_priorities hello
# This will save "hello" as string - validation will catch type mismatch
Error: Schema validation error: 'hello' is not of type 'integer'
```

**Solution:** Use correct value type (number, boolean, string).

#### Missing Parent Key

```bash
$ python -m commands.pa.briefing_config set nonexistent.key value
Error: Key not found: nonexistent.key
```

**Solution:** Only set values for existing keys. Use `list-keys` to see structure.

#### Config File Not Found

```bash
$ python -m commands.pa.briefing_config --config missing.json show
Error: Config file not found: missing.json
```

**Solution:** Check file path or omit `--config` to use default.

## Integration

### With BriefingScheduler

Changes take effect immediately for manual briefings. For scheduled briefings:

1. Edit config with CLI tool
2. Restart scheduler daemon (if running)
3. Or wait for next scheduled run (checks config on each run in `once` mode)

### With Manual Briefing Command

The `briefing` command automatically picks up config changes:

```bash
# Change config
python -m commands.pa.briefing_config set briefings.morning.time 08:00

# Generate morning briefing (uses new time)
python -m commands.pa.briefing morning
```

### In Scripts

You can use the CLI tool in shell scripts:

```bash
#!/bin/bash
# Enable evening briefing for the week
python -m commands.pa.briefing_config enable evening

# Disable it on weekends
python -m commands.pa.briefing_config set briefings.evening.days.saturday false
python -m commands.pa.briefing_config set briefings.evening.days.sunday false
```

## Troubleshooting

### Command Not Found

If `python -m commands.pa.briefing_config` doesn't work:

```bash
# Try running directly
python3 ./commands/pa/briefing_config.py --help

# Or add to PATH
export PATH="$PATH:$(pwd)/commands/pa"
```

### Import Errors

If you see import errors, make sure you're running from the project root:

```bash
cd /path/to/thanos
python -m commands.pa.briefing_config show
```

### Validation Always Fails

If validation fails even with correct values:

1. Check schema file exists:
   ```bash
   ls config/briefing_schedule.schema.json
   ls config/briefing_config.schema.json
   ```

2. Manually validate JSON syntax:
   ```bash
   python3 -m json.tool config/briefing_schedule.json
   ```

3. Run validator directly:
   ```bash
   python3 -m Tools.config_validator config/briefing_schedule.json
   ```

## See Also

- [Configuration Guide](BRIEFING_CONFIG_COMPREHENSIVE.md) - Detailed config documentation
- [Template Customization](briefing_customization.md) - Template syntax and examples
- [Custom Sections](CUSTOM_SECTIONS.md) - Adding custom content sections
- [Scheduler Guide](SCHEDULER_GUIDE.md) - Setting up automated briefings

## Examples Repository

More examples in `example_briefing_config.py` (if available).

## Support

For issues or questions:
1. Check this documentation
2. Run `--help` on any command
3. Use `list-keys` to explore configuration
4. Validate configuration after changes
