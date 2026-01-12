# Interactive Prompt Configuration

The Thanos interactive mode displays real-time token usage and cost estimates in the prompt to help you monitor API spend during sessions.

## Quick Start

By default, the prompt shows:
```
(1.2K | $0.04) Thanos>
```

Where:
- `1.2K` = Total tokens used (input + output)
- `$0.04` = Estimated cost in USD

## Configuration

Configure the interactive prompt display in `config/api.json` under the `interactive_prompt` key:

```json
{
  "interactive_prompt": {
    "enabled": true,
    "mode": "compact",
    "show_duration": true,
    "show_message_count": false,
    "color_coding": {
      "enabled": true,
      "thresholds": {
        "low": 0.50,
        "medium": 2.00
      }
    }
  }
}
```

### Configuration Options

#### `enabled` (boolean)
- **Default:** `true`
- **Description:** Enable/disable token and cost display in prompt
- **Usage:** Set to `false` if you find the stats distracting

```json
"enabled": false  // Shows plain "Thanos>" prompt
```

#### `mode` (string)
- **Default:** `"compact"`
- **Options:** `"compact"`, `"standard"`, `"verbose"`
- **Description:** Controls how much information is displayed

**Compact Mode** (default):
```
(1.2K | $0.04) Thanos>
```

**Standard Mode**:
```
(45m | 1.2K tokens | $0.04) Thanos>
```

**Verbose Mode**:
```
(45m | 12 msgs | 1.2K in | 3.4K out | $0.04) Thanos>
```

#### `color_coding.enabled` (boolean)
- **Default:** `true`
- **Description:** Enable color-coded cost indicators

When enabled, costs are color-coded:
- 🟢 **GREEN** ($0.00 - $0.50): Low cost, safe to continue
- 🟡 **YELLOW** ($0.51 - $2.00): Medium cost, monitor usage
- 🔴 **RED** ($2.01+): High cost, attention needed

#### `color_coding.thresholds` (object)
- **Default:** `{ "low": 0.50, "medium": 2.00 }`
- **Description:** Customize the dollar amounts for color thresholds

```json
"thresholds": {
  "low": 1.00,    // Green/yellow boundary
  "medium": 5.00  // Yellow/red boundary
}
```

## Example Configurations

### 1. Disable Token Display (Minimal)
If you find token stats distracting:

```json
{
  "interactive_prompt": {
    "enabled": false
  }
}
```

Result: `Thanos>`

### 2. Budget-Conscious User
Show detailed stats with conservative thresholds:

```json
{
  "interactive_prompt": {
    "enabled": true,
    "mode": "standard",
    "color_coding": {
      "enabled": true,
      "thresholds": {
        "low": 0.25,
        "medium": 1.00
      }
    }
  }
}
```

Result: `(45m | 1.2K tokens | $0.04) Thanos>`

### 3. Power User (Maximum Detail)
Show all available information:

```json
{
  "interactive_prompt": {
    "enabled": true,
    "mode": "verbose",
    "color_coding": {
      "enabled": true,
      "thresholds": {
        "low": 0.50,
        "medium": 2.00
      }
    }
  }
}
```

Result: `(45m | 12 msgs | 1.2K in | 3.4K out | $0.04) Thanos>`

### 4. Clean Interface (No Colors)
Disable color coding for better terminal compatibility:

```json
{
  "interactive_prompt": {
    "enabled": true,
    "mode": "compact",
    "color_coding": {
      "enabled": false
    }
  }
}
```

Result: `(1.2K | $0.04) Thanos>` (no color codes)

## Display Modes Comparison

| Mode | Example | When to Use |
|------|---------|-------------|
| **Compact** | `(1.2K \| $0.04) Thanos>` | Default, minimal clutter |
| **Standard** | `(45m \| 1.2K tokens \| $0.04) Thanos>` | Want session duration context |
| **Verbose** | `(45m \| 12 msgs \| 1.2K in \| 3.4K out \| $0.04) Thanos>` | Debugging, detailed monitoring |

## Token Formatting

Tokens are displayed in human-readable format:
- Less than 1,000: `123`
- 1,000 - 999,999: `1.2K`, `12.3K`
- 1,000,000+: `1.5M`, `2.3M`

## Cost Formatting

Costs are always displayed with 2 decimal places:
- `$0.04`
- `$1.23`
- `$15.67`

## Applying Configuration Changes

After editing `config/api.json`:

1. Save the file
2. Restart your Thanos session or start a new interactive session
3. Changes take effect immediately for new sessions

## Troubleshooting

### Prompt stats not showing
1. Check that `"enabled": true` in config
2. Verify `config/api.json` is valid JSON
3. Ensure you have token usage (stats won't show for brand new sessions with 0 tokens)

### Colors not appearing
1. Check that `"color_coding.enabled": true`
2. Verify your terminal supports ANSI color codes
3. Try a different terminal emulator if colors don't render

### Wrong display mode
1. Check the `"mode"` setting in config
2. Ensure it's one of: `"compact"`, `"standard"`, `"verbose"`
3. Restart your session after changing

### Configuration file not found
- The configuration is loaded from `config/api.json` in the Thanos project root
- If the file is missing, default values are used (enabled, compact mode, default thresholds)

## Related Commands

While in interactive mode:
- `/usage` - Show detailed usage statistics
- `/help` - Show available commands
- `/quit` - Exit interactive mode

## Technical Details

- Token counts are cumulative for the entire session
- Costs are estimated based on model pricing in `config/api.json`
- Session duration starts when interactive mode is initialized
- Stats update after each interaction with the agent

## See Also

- [PROMPT_DESIGN.md](.auto-claude/specs/010-add-token-count-and-cost-estimate-to-cli-prompt/PROMPT_DESIGN.md) - Complete design specification
- [config/api.json](../config/api.json) - Main configuration file
- [Tools/prompt_formatter.py](../Tools/prompt_formatter.py) - Implementation
