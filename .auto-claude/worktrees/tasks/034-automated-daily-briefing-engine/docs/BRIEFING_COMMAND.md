# Manual Briefing Trigger Command

The `commands.pa.briefing` module provides a CLI command for manually generating and delivering briefings on demand. This is useful for testing, manual use, and as a fallback when automated scheduling is not desired.

## Overview

The briefing command allows you to generate morning or evening briefings at any time, with options for:
- Dry-run mode (preview without saving)
- Custom configuration
- Energy level input
- Verbose logging

## Usage

### Basic Usage

```bash
# Generate morning briefing
python -m commands.pa.briefing morning

# Generate evening briefing
python -m commands.pa.briefing evening
```

### Dry Run Mode

Preview the briefing without saving to file:

```bash
python -m commands.pa.briefing morning --dry-run
python -m commands.pa.briefing evening --dry-run
```

### Custom Configuration

Use a custom config file instead of the default:

```bash
python -m commands.pa.briefing morning --config /path/to/config.json
```

### Energy Level

Provide your current energy level (1-10) to get task recommendations tailored to your state:

```bash
# Low energy - will suggest simpler tasks
python -m commands.pa.briefing morning --energy-level 3

# High energy - will suggest complex/deep work tasks
python -m commands.pa.briefing morning --energy-level 9
```

### Verbose Logging

Enable detailed debug logging:

```bash
python -m commands.pa.briefing morning --verbose
python -m commands.pa.briefing morning -v
```

## Command Line Options

| Option | Type | Description |
|--------|------|-------------|
| `type` | positional | Type of briefing: `morning` or `evening` (required) |
| `--dry-run` | flag | Print briefing without saving to file |
| `--config PATH` | string | Path to custom config file (default: `config/briefing_schedule.json`) |
| `--energy-level N` | integer | Current energy level 1-10 (affects task recommendations) |
| `--verbose`, `-v` | flag | Enable verbose debug logging |
| `--help`, `-h` | flag | Show help message and exit |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success - briefing generated successfully |
| 1 | Failure - error occurred (missing config, invalid type, engine error) |

## Output

### Console Output

The command prints the briefing to stdout with:
- Header with date and emoji (☀️ for morning, 🌙 for evening)
- Full briefing content (formatted as markdown)
- Footer with file path (if saved)
- Success/error messages

Example:

```
☀️  Generating morning briefing for Thursday, January 11, 2024...

------------------------------------------------------------
# Good Morning! 🌅

Today is Thursday, January 11, 2024

## 🎯 Top 3 Priorities

1. **[HIGH URGENCY]** Ship Epic interface updates (Due: today)
   ...

------------------------------------------------------------
💾 Saved to: History/DailyBriefings/2024-01-11_morning_briefing_0700.md

✅ Morning briefing generated successfully!
```

### File Output

Unless `--dry-run` is specified, the briefing is saved to:

**Default location:** `History/DailyBriefings/`

**Filename format:** `{date}_{type}_briefing_{time}.md`

Example: `2024-01-11_morning_briefing_0723.md`

The file includes:
- Markdown header with date
- Generation timestamp
- Full briefing content

## Configuration

The command uses the configuration file at `config/briefing_schedule.json` (or a custom path via `--config`).

**Relevant config sections:**

```json
{
  "delivery": {
    "file": {
      "enabled": true,
      "output_dir": "History/DailyBriefings"
    }
  },
  "advanced": {
    "state_dir": "State",
    "templates_dir": "Templates"
  }
}
```

## Implementation Details

### Architecture

1. **Config Loading:** Loads and validates configuration from JSON file
2. **Engine Initialization:** Creates BriefingEngine with configured paths
3. **Context Gathering:** Reads State files (Commitments.md, ThisWeek.md, etc.)
4. **Template Rendering:** Renders briefing using Jinja2 templates
5. **Output:** Prints to console and optionally saves to file

### Error Handling

The command handles errors gracefully:

- **Missing config:** Clear error with path information
- **Invalid JSON:** Reports JSON parsing errors
- **Engine initialization failure:** Reports initialization errors
- **Context gathering errors:** Reports State file reading issues
- **Template rendering errors:** Reports rendering failures
- **File save errors:** Warns but continues (briefing still printed)

All errors are logged and return exit code 1.

### Dependencies

- `Tools.briefing_engine.BriefingEngine` - Core briefing generation
- `config/briefing_schedule.json` - Configuration file
- `State/` directory - State files for context
- `Templates/` directory - Jinja2 templates
- `History/DailyBriefings/` - Output directory (created if needed)

## Examples

### 1. Morning Briefing with Energy Level

```bash
python -m commands.pa.briefing morning --energy-level 7
```

Output includes task recommendations appropriate for medium-high energy.

### 2. Dry Run for Testing

```bash
python -m commands.pa.briefing evening --dry-run
```

Shows what the evening briefing would contain without saving.

### 3. Custom Config for Testing

```bash
python -m commands.pa.briefing morning --config ./test_config.json --dry-run
```

Tests briefing generation with a custom configuration.

### 4. Verbose Debugging

```bash
python -m commands.pa.briefing morning --verbose
```

Shows detailed logs of context gathering, template rendering, etc.

## Integration with Scheduler

While this command is designed for manual use, it follows the same code path as the automated scheduler (`Tools/briefing_scheduler.py`), ensuring consistent output.

The scheduler internally uses `BriefingEngine` just like this command does.

## Testing

Run unit tests:

```bash
python -m pytest tests/unit/test_briefing_command.py -v
```

Test coverage includes:
- Config loading (default and custom paths)
- Error handling (missing files, invalid types)
- Dry run mode
- File saving
- Energy level integration
- Engine initialization
- Context gathering
- Template rendering

## Troubleshooting

### Error: Config file not found

**Problem:** The config file doesn't exist at the default or specified path.

**Solution:**
- Ensure `config/briefing_schedule.json` exists
- Or provide a valid `--config` path
- See `config/briefing_schedule.example.json` for reference

### Error: Invalid JSON in config file

**Problem:** The config file contains syntax errors.

**Solution:**
- Validate JSON syntax using `python -m json.tool config/briefing_schedule.json`
- Check for missing commas, quotes, or brackets

### Error: Failed to initialize BriefingEngine

**Problem:** Required directories or files are missing.

**Solution:**
- Ensure `State/` and `Templates/` directories exist
- Check paths in config `advanced` section
- Verify file permissions

### Warning: Failed to save briefing to file

**Problem:** Output directory is not writable or doesn't exist.

**Solution:**
- Check permissions on output directory
- Ensure parent directory exists
- Use `--dry-run` to skip file saving

### Template rendering issues

**Problem:** Jinja2 templates are missing or have syntax errors.

**Solution:**
- Ensure templates exist in `Templates/` directory
- Verify Jinja2 is installed: `pip install jinja2`
- Check template syntax

## See Also

- [Briefing Scheduler Guide](./SCHEDULER_GUIDE.md) - Automated scheduling
- [Template Customization](../Templates/README.md) - Customize briefing templates
- [Configuration Guide](../config/README.md) - Configure briefing behavior
- [BriefingEngine API](./INTEGRATION_NOTES.md) - Developer reference
