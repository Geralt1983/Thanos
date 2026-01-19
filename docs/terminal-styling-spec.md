# Thanos CLI Terminal Styling Specification

## Overview

This document specifies a comprehensive terminal styling system for the Thanos CLI that creates a distinctive, professional appearance with clear visual hierarchy between user input, system messages, and AI responses.

## Design Principles

1. **Brand Identity**: Purple/magenta as the primary Thanos color
2. **Visual Clarity**: Clear separation between conversation turns
3. **Non-Intrusive Tooling**: Tool execution messages should be subtle
4. **Readability First**: Response text should be highly readable
5. **Terminal Compatibility**: Use standard ANSI codes that work across terminals

---

## ANSI Escape Code Reference

### Basic Colors (30-37 foreground, 40-47 background)

```
\033[30m  Black
\033[31m  Red
\033[32m  Green
\033[33m  Yellow
\033[34m  Blue
\033[35m  Magenta/Purple  <-- Thanos primary
\033[36m  Cyan
\033[37m  White
```

### Bright/High-Intensity Colors (90-97)

```
\033[90m  Bright Black (Gray)
\033[91m  Bright Red
\033[92m  Bright Green
\033[93m  Bright Yellow
\033[94m  Bright Blue
\033[95m  Bright Magenta  <-- Thanos bright variant
\033[96m  Bright Cyan
\033[97m  Bright White
```

### Text Attributes

```
\033[0m   Reset all
\033[1m   Bold
\033[2m   Dim/Faint
\033[3m   Italic
\033[4m   Underline
\033[7m   Inverse
\033[9m   Strikethrough
```

### Combined Examples

```
\033[1;35m     Bold Magenta
\033[2;37m     Dim White (for tool messages)
\033[3;90m     Italic Gray (for status)
\033[1;95m     Bold Bright Magenta
```

---

## Color Palette Definition

### Python Constants (for `prompt_formatter.py` and `command_router.py`)

```python
class ThanosStyle:
    """Thanos CLI styling constants."""

    # Reset
    RESET = "\033[0m"

    # Thanos Branding
    THANOS_PURPLE = "\033[35m"           # Primary brand color
    THANOS_BRIGHT = "\033[95m"           # Bright variant
    THANOS_BOLD = "\033[1;35m"           # Bold purple
    THANOS_BRIGHT_BOLD = "\033[1;95m"    # Bold bright purple

    # Text Styles
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    DIM_ITALIC = "\033[2;3m"

    # Status Colors
    SUCCESS = "\033[32m"      # Green
    WARNING = "\033[33m"      # Yellow
    ERROR = "\033[31m"        # Red
    INFO = "\033[36m"         # Cyan
    MUTED = "\033[90m"        # Bright black (gray)

    # Semantic Colors
    COST_LOW = "\033[32m"     # Green (<$0.50)
    COST_MED = "\033[33m"     # Yellow ($0.50-$2.00)
    COST_HIGH = "\033[31m"    # Red (>$2.00)

    # Dividers
    DIVIDER_COLOR = "\033[90m"  # Gray dividers
```

---

## Visual Components

### 1. Thanos Prompt

**Current Implementation:**
```
(1.2K | $0.04) Thanos>
```

**New Design:**
```
(1.2K | $0.04) [purple]Thanos>[/purple]
```

**With Glyph Option (configurable):**
```
(1.2K | $0.04) [purple]Thanos>[/purple]
```

**Implementation:**
```python
# In prompt_formatter.py
PROMPT_PREFIX = ""  # Optional glyph: "+" or "T"
PROMPT_NAME = f"{ThanosStyle.THANOS_BOLD}Thanos>{ThanosStyle.RESET} "

def format_prompt(self, stats, mode=None):
    stats_part = self._format_stats(stats, mode)
    return f"{stats_part}{PROMPT_NAME}"
```

### 2. Response Header (Turn Marker)

**Design:**
Add a visual divider BEFORE each Thanos response to clearly separate turns.

**ASCII Art Options:**

Option A - Thin Line:
```
---
```

Option B - Labeled Divider:
```
--- Thanos ---
```

Option C - Minimal Spacing:
```
[blank line]
```

**Recommended: Option A with conditional display**

```python
# In thanos_interactive.py, before printing response
def _print_response_header(self):
    """Print visual separator before Thanos response."""
    # Print newline for spacing
    print()
    # Optional: print dim divider
    # print(f"{ThanosStyle.DIM}---{ThanosStyle.RESET}")
```

### 3. Tool Execution Messages

**Current:**
```
[Executing 3 tool(s)...]
```

**New Design - Dimmed and Italicized:**
```
[2;3m  Executing 3 tools...[0m
```

**Implementation:**
```python
TOOL_STYLE = f"{ThanosStyle.DIM_ITALIC}"
TOOL_RESET = f"{ThanosStyle.RESET}"

# Usage
print(f"{TOOL_STYLE}  Executing {len(tool_calls)} tools...{TOOL_RESET}")
```

**Alternative - With Spinner Character:**
```
  > Running tools...
```

### 4. System Status Messages

**Design Hierarchy:**

| Message Type | Style | Example |
|-------------|-------|---------|
| Success | Dim Green | `[dim green]Session saved[/]` |
| Info | Dim | `[dim]Using cached data[/]` |
| Warning | Dim Yellow | `[dim yellow]Rate limited[/]` |
| Error | Dim Red | `[dim red]Connection error[/]` |

**Implementation:**
```python
def status_msg(text: str, level: str = "info") -> str:
    """Format a status message with appropriate styling."""
    styles = {
        "success": f"{ThanosStyle.DIM}\033[32m",  # Dim green
        "info": f"{ThanosStyle.DIM}",              # Just dim
        "warning": f"{ThanosStyle.DIM}\033[33m",  # Dim yellow
        "error": f"{ThanosStyle.DIM}\033[31m",    # Dim red
    }
    style = styles.get(level, styles["info"])
    return f"{style}[{text}]{ThanosStyle.RESET}"
```

### 5. Response Formatting

**Principles:**
- Main response text: Default terminal color (white/light gray)
- Headers in response: Bold (not colored)
- Numbered lists: Clear, consistent formatting
- Code blocks: Maintain terminal default

**Headers:**
```python
# In response processing
def format_response_header(text: str) -> str:
    """Format markdown headers in response."""
    return f"{ThanosStyle.BOLD}{text}{ThanosStyle.RESET}"
```

**Lists:**
```
1. First item
2. Second item
   - Sub-item (indented)
```

### 6. Welcome and Goodbye Messages

**Welcome:**
```
[blank line]
[cyan]Welcome to Thanos Interactive Mode[/cyan]
[dim]Type /help for commands, /quit to exit[/dim]
[blank line]
```

**Goodbye (Session Summary):**
```
[blank line]
[cyan]Session Summary:[/cyan]
  Messages: 12
  Total tokens: 4,521
  Estimated cost: $0.15
  Duration: 23 minutes
[blank line]
[dim]Session saved: History/Sessions/2026-01-19-xxxx.json[/dim]
[blank line]
[cyan]Goodbye![/cyan]
[blank line]
```

---

## Example Output Mockups

### Full Conversation Turn

```
                                            <-- User types here (default color)
(1.2K | $0.04) Thanos> What's my readiness?
                                            <-- Blank line separator
  Fetching health context...                <-- Dim italic, indented
                                            <-- Blank line
Based on your Oura data for today:          <-- Response starts (default color)

**Readiness Score: 78**                     <-- Bold headers

Your readiness is in the "fair" range.
Key factors:
1. Sleep score: 82 (good)                   <-- Numbered list
2. HRV balance: 65 (fair)
3. Recovery: 71 (fair)

Consider lighter cognitive tasks today.
                                            <-- Blank line after response
(2.1K | $0.08) Thanos> _                    <-- Next prompt
```

### Tool Execution Sequence

```
(1.5K | $0.06) Thanos> Show my calendar for today

  Executing 1 tool...                       <-- Dim, italic

Here are your events for today:

* 09:00 AM  Team standup
* 11:30 AM  Client call with Memphis
* 02:00 PM  Code review

You have 3 events scheduled.

(2.3K | $0.09) Thanos> _
```

### Error State

```
(1.5K | $0.06) Thanos> Check my sleep data

  Fetching Oura data...                     <-- Dim italic
  [API Error: timeout - will retry]         <-- Dim red, bracketed

I couldn't fetch your current sleep data.
Would you like me to show cached data
from earlier today?

(1.8K | $0.07) Thanos> _
```

---

## Implementation Approach

### Phase 1: Core Styling Constants

**File:** `Tools/styles.py` (new file)

```python
#!/usr/bin/env python3
"""
Thanos CLI Styling Constants and Utilities.

Centralized styling for consistent terminal output across the Thanos CLI.
"""

class ThanosStyle:
    """ANSI escape codes for Thanos CLI styling."""

    # Reset
    RESET = "\033[0m"

    # Thanos Branding
    PURPLE = "\033[35m"
    BRIGHT_PURPLE = "\033[95m"
    BOLD_PURPLE = "\033[1;35m"

    # Text Attributes
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    DIM_ITALIC = "\033[2;3m"

    # Colors
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    CYAN = "\033[36m"
    GRAY = "\033[90m"


def styled(text: str, *styles: str) -> str:
    """Apply styles to text with automatic reset."""
    style_codes = "".join(styles)
    return f"{style_codes}{text}{ThanosStyle.RESET}"


def thanos_prompt(prefix: str = "") -> str:
    """Generate the styled Thanos prompt."""
    return f"{prefix}{ThanosStyle.BOLD_PURPLE}Thanos>{ThanosStyle.RESET} "


def tool_status(message: str) -> str:
    """Format a tool execution status message."""
    return f"{ThanosStyle.DIM_ITALIC}  {message}{ThanosStyle.RESET}"


def system_status(message: str, level: str = "info") -> str:
    """Format a system status message."""
    color = {
        "success": ThanosStyle.GREEN,
        "warning": ThanosStyle.YELLOW,
        "error": ThanosStyle.RED,
        "info": "",
    }.get(level, "")
    return f"{ThanosStyle.DIM}{color}[{message}]{ThanosStyle.RESET}"


def turn_separator() -> str:
    """Return the visual separator between conversation turns."""
    return ""  # Just a newline; can be changed to "---" if desired
```

### Phase 2: Update prompt_formatter.py

```python
# Import new styles
from Tools.styles import ThanosStyle, thanos_prompt

# Update _format_compact etc. to use thanos_prompt()
def _format_compact(self, total_tokens: int, cost: float, error_count: int = 0) -> str:
    tokens_display = self._format_token_count(total_tokens)
    cost_display = self._format_cost(cost)
    error_display = self._format_error_count(error_count)
    return f"({tokens_display} | {cost_display}{error_display}) {thanos_prompt()}"
```

### Phase 3: Update thanos_interactive.py

```python
from Tools.styles import ThanosStyle, tool_status, system_status, turn_separator

# Before printing response
print(turn_separator())

# Tool execution
print(tool_status(f"Executing {len(tool_calls)} tools..."))

# Status messages
print(system_status("Session saved", "success"))
print(system_status("Rate limited - waiting...", "warning"))
```

### Phase 4: Update command_router.py

Replace existing `Colors` class usage with imports from `Tools/styles.py`.

---

## Configuration Options

Add to `config/api.json`:

```json
{
  "interactive_prompt": {
    "enabled": true,
    "mode": "compact",
    "styling": {
      "prompt_glyph": "",
      "show_turn_divider": false,
      "tool_messages": "dim_italic",
      "response_headers": "bold"
    },
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

---

## Accessibility Considerations

1. **Color Blindness**: Don't rely solely on color for meaning
   - Use text labels with colors (e.g., "[ERROR]" not just red)
   - Maintain sufficient contrast

2. **Screen Readers**: ANSI codes are typically stripped
   - Ensure messages are meaningful without styling

3. **NO_COLOR Environment Variable**: Respect `NO_COLOR` env var
   ```python
   import os
   COLORS_ENABLED = os.environ.get("NO_COLOR") is None
   ```

4. **Terminal Compatibility**: Test on:
   - macOS Terminal / iTerm2
   - Windows Terminal / PowerShell
   - Linux terminals (GNOME Terminal, Konsole)
   - Termux (Android)

---

## Migration Path

1. Create `Tools/styles.py` with all constants
2. Update `Tools/prompt_formatter.py` to use new styles
3. Update `Tools/thanos_interactive.py` for turn separation
4. Update `Tools/command_router.py` to use centralized styles
5. Add configuration options to `config/api.json`
6. Update tests to verify styling output

---

## Summary

| Component | Style | ANSI Code |
|-----------|-------|-----------|
| "Thanos>" prompt | Bold Purple | `\033[1;35m` |
| Stats prefix | Default | (none) |
| Tool execution | Dim Italic | `\033[2;3m` |
| Success status | Dim Green | `\033[2m\033[32m` |
| Warning status | Dim Yellow | `\033[2m\033[33m` |
| Error status | Dim Red | `\033[2m\033[31m` |
| Response headers | Bold | `\033[1m` |
| Response text | Default | (none) |
| Turn separator | Newline | `\n` |

This specification provides a consistent, professional appearance while maintaining readability and terminal compatibility.
