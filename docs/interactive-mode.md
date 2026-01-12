# Thanos Interactive Mode

Interactive mode provides a conversational interface to Thanos, allowing you to chat with AI agents, run commands, and monitor resource usage in real-time.

## Table of Contents

- [Getting Started](#getting-started)
- [Real-Time Token & Cost Display](#real-time-token--cost-display)
- [Available Commands](#available-commands)
- [Configuration](#configuration)
- [Usage Patterns](#usage-patterns)
- [Tips & Best Practices](#tips--best-practices)

## Getting Started

Start interactive mode with:

```bash
python thanos.py interactive
```

You'll see a prompt that displays real-time token usage and cost estimates:

```
(1.2K | $0.04) Thanos>
```

This prompt updates after each interaction, helping you monitor API spend throughout your session.

## Real-Time Token & Cost Display

### What You See

The interactive prompt shows **real-time session statistics** to help you track API costs:

```
(1.2K | $0.04) Thanos>
```

Where:
- **1.2K** = Total tokens used (input + output combined)
- **$0.04** = Estimated session cost in USD

### Why This Matters

**Cost Awareness**: No more surprises on your API bill. You can see exactly how much each conversation is costing as you go.

**Budget Control**: Set yourself a spending limit (e.g., "I'll stop when I hit $2") and watch the counter.

**Session Planning**: Decide when to start a new session based on current usage.

### Display Modes

Choose how much information you want to see:

#### Compact Mode (Default)
```
(1.2K | $0.04) Thanos>
```
Minimal and clean. Shows just tokens and cost.

#### Standard Mode
```
(45m | 1.2K tokens | $0.04) Thanos>
```
Adds session duration for context about how long you've been working.

#### Verbose Mode
```
(45m | 12 msgs | 1.2K in | 3.4K out | $0.04) Thanos>
```
Maximum detail: duration, message count, input/output tokens breakdown, and cost.

**Switch modes at runtime:**
```
/prompt compact    # Minimal
/prompt standard   # With duration
/prompt verbose    # All details
/p standard        # Shortcut works too
```

Or press `/prompt` without arguments to see current mode and options.

### Color-Coded Cost Indicators

Costs are color-coded to help you quickly identify when spending is getting high:

- 🟢 **GREEN** ($0.00 - $0.50): Low cost, safe to continue
- 🟡 **YELLOW** ($0.51 - $2.00): Medium cost, monitor usage
- 🔴 **RED** ($2.01+): High cost, attention recommended

You can customize these thresholds or disable colors entirely. See [Configuration](#configuration) below.

## Available Commands

Interactive mode supports powerful slash commands:

### Session Management
- `/clear` - Clear conversation history (start fresh)
- `/resume [id]` - Resume a previous session
- `/history` - View conversation history
- `/usage` - Show detailed token/cost statistics
- `/quit` or `/q` - Exit interactive mode

### Agent Operations
- `/agent <name>` or `/a <name>` - Switch to a different agent
- `/agents` - List available agents

### State & Commitments
- `/state` or `/s` - Show current state
- `/commitments` or `/c` - View active commitments
- `/patterns` - Show conversation patterns and analytics

### Display Customization
- `/prompt [mode]` or `/p [mode]` - Switch display mode (compact/standard/verbose)
- `/model [name]` or `/m [name]` - Switch AI model (opus/sonnet/haiku)

### Calendar Integration
- `/calendar [when]` or `/cal [when]` - Show calendar events
- `/schedule <task>` - Schedule a task
- `/free [when]` - Find free time slots

### Execution
- `/run <cmd>` - Run a Thanos command (e.g., `/run pa:daily`)

### Help
- `/help` or `/h` - Show all available commands

## Configuration

### Static Configuration

Configure the interactive prompt in `config/api.json`:

```json
{
  "interactive_prompt": {
    "enabled": true,
    "mode": "compact",
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

**See the full configuration guide**: [docs/interactive-prompt-configuration.md](./interactive-prompt-configuration.md)

The configuration guide covers:
- All available options with examples
- How to customize color thresholds
- How to disable the feature
- Example configurations for different use cases
- Troubleshooting tips

### Runtime Configuration

Many settings can be changed on-the-fly without editing config files:

```bash
# Switch display mode
/prompt verbose

# Change AI model
/model sonnet

# Switch agent
/agent research
```

Changes take effect immediately for the current session.

## Usage Patterns

### Budget-Conscious Development

Keep an eye on costs while working on a project:

```
(1.2K | $0.04) Thanos> help me refactor this authentication module
[... AI responds ...]
(3.5K | $0.12) Thanos> can you add unit tests too?
[... AI responds ...]
(7.8K | $0.26) Thanos> /usage
```

The `/usage` command provides detailed breakdown when you need more info.

### Long-Running Sessions

Use standard or verbose mode to track session duration:

```
(2h15m | 45.2K tokens | $1.52) Thanos>
```

Helps you decide: "I've been at this for 2 hours and spent $1.52, maybe I should take a break."

### Multi-Agent Workflows

Switch between agents while monitoring cumulative costs:

```
(1.2K | $0.04) Thanos> /agent research
Switched to agent: research
(1.2K | $0.04) Thanos> analyze this codebase
[... research agent responds ...]
(5.6K | $0.19) Thanos> /agent coder
Switched to agent: coder
(5.6K | $0.19) Thanos> implement the changes we discussed
```

Costs accumulate across agent switches within the same session.

### Cost Threshold Management

Watch the color change from green → yellow → red:

```
(12K | $0.40) Thanos>    # Green - safe
(38K | $1.28) Thanos>    # Yellow - monitoring
(65K | $2.18) Thanos>    # Red - high cost
```

When you hit red, consider:
- Starting a new session
- Using a smaller model (`/model haiku`)
- Reviewing `/usage` for breakdown

## Tips & Best Practices

### 1. Start with Compact Mode

The default compact mode `(1.2K | $0.04)` provides the essential information without clutter. Switch to verbose only when debugging or doing detailed monitoring.

### 2. Set Mental Thresholds

Before starting a session, decide your budget:
- Quick questions: ~$0.10
- Code reviews: ~$0.50
- Major refactoring: ~$2.00

Stop when you hit your limit.

### 3. Use /clear for Fresh Starts

Token counts accumulate. If you're moving to a new topic, use `/clear` to reset the conversation context (note: this starts a new session, so stats reset too).

### 4. Monitor Verbose Mode During Complex Tasks

When doing complex multi-step tasks, switch to verbose mode to see the input/output token breakdown:

```
(45m | 12 msgs | 1.2K in | 3.4K out | $0.04) Thanos>
```

This helps identify if responses are unusually long (high output tokens).

### 5. Combine with /usage for Deep Dives

The prompt shows high-level stats. Use `/usage` for detailed breakdowns:

```
(7.8K | $0.26) Thanos> /usage

Session Statistics:
  Session ID: abc123
  Duration: 23 minutes
  Messages: 8
  Total Tokens: 7,834
  ├─ Input:  2,145 tokens
  └─ Output: 5,689 tokens
  Estimated Cost: $0.26
```

### 6. Customize Thresholds for Your Budget

If you're very cost-conscious, lower the thresholds in config:

```json
"thresholds": {
  "low": 0.10,     # Yellow at $0.10
  "medium": 0.50   # Red at $0.50
}
```

### 7. Disable When Not Needed

If you find the stats distracting during creative brainstorming, disable them:

```json
"enabled": false
```

Or use the plain `Thanos>` prompt.

### 8. Multi-line Input for Complex Prompts

Use triple quotes for multi-line input:

```
(1.2K | $0.04) Thanos> """
Please help me:
1. Refactor this function
2. Add error handling
3. Write unit tests
"""
```

This helps organize complex requests without worrying about the prompt stats.

## Interpreting the Display

### Token Formatting

Tokens are shown in human-readable format:
- `123` - Less than 1,000 tokens
- `1.2K` - Thousands (1,200 tokens)
- `45.7K` - Tens of thousands
- `1.5M` - Millions (rare in typical sessions)

### Cost Calculation

Costs are estimated based on:
- Model pricing from `config/api.json`
- Actual token usage (input + output)
- Current pricing rates

**Note**: These are estimates. Final billing may vary slightly based on:
- Rate limiting charges
- Special model features
- Promotional credits

### Session Duration

Duration starts when you enter interactive mode and counts upward:
- `15m` - 15 minutes
- `1h30m` - 1 hour 30 minutes
- `2h` - Exactly 2 hours

## Troubleshooting

### Stats Not Showing

**Problem**: Prompt shows plain `Thanos>` without stats

**Solutions**:
1. Check `config/api.json` has `"enabled": true`
2. Verify the config file is valid JSON
3. Stats won't show for brand new sessions with 0 tokens (make at least one query first)

### Colors Not Appearing

**Problem**: Costs show but without color

**Solutions**:
1. Check `"color_coding.enabled": true` in config
2. Verify your terminal supports ANSI color codes
3. Try a different terminal emulator (iTerm2, Windows Terminal, etc.)

### Wrong Display Mode

**Problem**: Seeing verbose mode but want compact

**Solutions**:
1. Use `/prompt compact` to switch immediately
2. Or edit `config/api.json` and change `"mode": "compact"`
3. Restart interactive mode for config changes to take effect

### Costs Seem Wrong

**Problem**: Displayed cost doesn't match expectations

**Solutions**:
1. Use `/usage` to see detailed breakdown
2. Check model pricing in `config/api.json`
3. Remember costs are cumulative for the entire session
4. Different models have different pricing (opus > sonnet > haiku)

## Related Documentation

- **[Interactive Prompt Configuration Guide](./interactive-prompt-configuration.md)** - Detailed configuration options and examples
- **[Architecture Documentation](./architecture.md)** - How interactive mode fits into Thanos architecture
- **[Usage Tracking Implementation](../Tools/litellm/usage_tracker.py)** - Technical details on token tracking

## Advanced Features

### Session Persistence

Sessions are automatically saved. You can resume them later:

```bash
# Exit interactive mode
/quit

# Later, see available sessions
python thanos.py sessions list

# Resume a specific session
python thanos.py interactive --resume abc123
```

Token counts and costs persist across resumed sessions.

### Branch Conversations

Create branches from any point in the conversation:

```
(5.6K | $0.19) Thanos> /branch experiment-1
Created branch: experiment-1

(5.6K | $0.19) Thanos> try implementing it this way instead
[... AI responds ...]

(7.2K | $0.24) Thanos> /switch main
Switched to branch: main

(5.6K | $0.19) Thanos> /branches
Available branches:
  * main
    experiment-1
```

Each branch maintains its own token count from the branch point.

### Pattern Recognition

Interactive mode tracks conversation patterns:

```
(15.3K | $0.51) Thanos> /patterns

Conversation Patterns:
  • Frequent topics: authentication, error handling, testing
  • Agent switches: 3 (ops → research → coder)
  • Average response length: 450 tokens
  • Most active time: 2:00 PM - 4:00 PM
```

Helps you understand your usage patterns over time.

## Feedback & Improvements

The interactive prompt feature is designed to be non-intrusive while providing valuable cost awareness. If you have feedback or suggestions:

1. Try different display modes to find what works for you
2. Experiment with color threshold customization
3. Share your usage patterns with the team

The goal is to make cost-conscious development feel natural, not burdensome.

---

**Quick Reference Card**:

| Command | Shortcut | Purpose |
|---------|----------|---------|
| `/prompt compact` | `/p compact` | Minimal display: `(1.2K \| $0.04)` |
| `/prompt standard` | `/p standard` | Add duration: `(45m \| 1.2K tokens \| $0.04)` |
| `/prompt verbose` | `/p verbose` | Full details: `(45m \| 12 msgs \| 1.2K in \| 3.4K out \| $0.04)` |
| `/usage` | - | Detailed cost breakdown |
| `/clear` | - | Reset conversation (starts fresh session) |
| `/quit` | `/q` | Exit interactive mode |

**Color Guide**:
- 🟢 GREEN: $0.00 - $0.50 (safe)
- 🟡 YELLOW: $0.51 - $2.00 (monitor)
- 🔴 RED: $2.01+ (attention)
