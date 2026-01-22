# Thanos Visual State Management

Complete implementation of visual state management using Kitty terminal wallpaper control.

## Overview

The visual state system represents Thanos workflow states through terminal wallpapers:

- **CHAOS**: Morning/Unsorted - Tasks in disarray, inbox awaits
- **FOCUS**: Deep Work - Engaged and executing with power
- **BALANCE**: End of Day/Complete - The Garden achieved

## Features

### ✅ Implemented

1. **Visual State Management**
   - 3 distinct states: CHAOS, FOCUS, BALANCE
   - Wallpaper mapping to visual representations
   - Kitty terminal API integration via remote control

2. **Wallpaper Control**
   - `kitty @ set-background-image` for wallpaper changes
   - Wallpaper file validation
   - Graceful degradation for non-Kitty terminals
   - Comprehensive error handling

3. **Auto-Transition Logic**
   - Morning + inbox > 0 → CHAOS
   - High cognitive load → FOCUS
   - Daily goal achieved → BALANCE
   - Evening + clear inbox → BALANCE
   - Low energy + many tasks → CHAOS
   - Manual override support

4. **State Persistence**
   - Saves to `State/visual_state.json` (as per requirements)
   - Tracks state history (last 100 transitions)
   - Timestamps and descriptions included
   - Restore state on session start

5. **Terminal Detection**
   - Checks `TERM` and `TERM_PROGRAM` environment variables
   - Works in Kitty terminal only
   - Graceful degradation with warnings

## File Structure

```
Shell/lib/
├── visuals.py                      # Main implementation
├── visual_integration_example.py   # Integration examples
└── VISUAL_STATE_README.md         # This file

State/
└── visual_state.json              # Persistent state storage

~/.thanos/wallpapers/
├── nebula_storm.png               # CHAOS wallpaper
├── infinity_gauntlet_fist.png     # FOCUS wallpaper
└── farm_sunrise.png               # BALANCE wallpaper
```

## Usage

### Command Line Interface

```bash
# Set visual state manually
python3 Shell/lib/visuals.py set CHAOS
python3 Shell/lib/visuals.py set FOCUS
python3 Shell/lib/visuals.py set BALANCE

# Auto-detect and set state
python3 Shell/lib/visuals.py auto

# Get current state
python3 Shell/lib/visuals.py get

# View state history
python3 Shell/lib/visuals.py history      # Last 10
python3 Shell/lib/visuals.py history 20   # Last 20

# Download/create wallpapers
python3 Shell/lib/visuals.py download

# Check if running in Kitty
python3 Shell/lib/visuals.py check
```

### Python API

```python
from visuals import ThanosVisualState

# Set state manually
ThanosVisualState.set_state("FOCUS")

# Auto-transition based on context
context = {
    "time_of_day": "morning",
    "inbox": 5,
    "cognitive_load": "medium",
    "energy_level": "high",
    "daily_goal_achieved": False,
    "tasks_active": 3
}
state = ThanosVisualState.auto_transition(context)

# Get current state
current = ThanosVisualState.get_current_state()

# Get state history
history = ThanosVisualState.get_state_history(limit=10)

# Check if Kitty terminal
is_kitty = ThanosVisualState.is_kitty_terminal()
```

## Auto-Transition Logic

The system automatically determines the appropriate visual state based on context:

| Priority | Condition | State | Rationale |
|----------|-----------|-------|-----------|
| 1 | `daily_goal_achieved == True` | BALANCE | Goals complete |
| 2 | `time_of_day == "evening"` AND `inbox == 0` | BALANCE | Day wrapping up |
| 3 | `time_of_day == "morning"` AND `inbox > 0` | CHAOS | Morning processing |
| 4 | `energy_level == "low"` AND `tasks_active > 5` | CHAOS | Overwhelmed |
| 5 | `cognitive_load == "high"` | FOCUS | Deep work |
| 6 | `energy_level == "high"` AND `tasks_active > 0` | FOCUS | Productive state |
| 7 | _default_ | FOCUS | Working state |

## Integration Points

### Session Start (hooks/session-start/)

```python
from Shell.lib.visuals import ThanosVisualState

# Get context from WorkOS and Oura
context = {
    "inbox": workos_brain_dump_count,
    "tasks_active": workos_active_task_count,
    "energy_level": oura_energy_level,
}

# Set appropriate visual state
ThanosVisualState.auto_transition(context)
```

### Task Completion

```python
def on_task_complete(points_earned, daily_target):
    if points_earned >= daily_target:
        ThanosVisualState.set_state("BALANCE")
```

### Deep Work Mode

```python
def enter_deep_work(task):
    if task.cognitive_load == "high":
        ThanosVisualState.set_state("FOCUS")
```

### Brain Dump Processing

```python
def process_brain_dump():
    ThanosVisualState.set_state("CHAOS")
    # Process entries...
```

## State Persistence Format

`State/visual_state.json`:

```json
{
  "current_state": "FOCUS",
  "history": [
    {
      "state": "CHAOS",
      "timestamp": "2026-01-21T01:35:43.488043",
      "description": "Morning/Unsorted - Tasks in disarray, inbox awaits"
    },
    {
      "state": "FOCUS",
      "timestamp": "2026-01-21T01:35:44.589437",
      "description": "Deep Work - Engaged and executing with power"
    }
  ]
}
```

## Error Handling

### Non-Kitty Terminal
```
WARNING: Not running in Kitty terminal - visual state tracking only
```
State is still saved to `visual_state.json` for tracking purposes, but wallpaper is not changed.

### Missing Wallpaper
```
WARNING: Wallpaper not found: /Users/jeremy/.thanos/wallpapers/nebula_storm.png
INFO: Run 'python3 visuals.py download' to get wallpapers
```

### Kitty Command Failure
```
ERROR: Failed to set wallpaper (exit code: 1)
```

## Testing

Run the test suite:

```bash
# Run integration examples
python3 Shell/lib/visual_integration_example.py

# Test auto-transitions
python3 -c "
from Shell.lib.visuals import ThanosVisualState

contexts = [
    {'time_of_day': 'morning', 'inbox': 5},
    {'cognitive_load': 'high'},
    {'daily_goal_achieved': True},
]

for ctx in contexts:
    result = ThanosVisualState.auto_transition(ctx)
    print(f'{ctx} → {result}')
"
```

## Requirements Met

✅ **Visual State Management**
- 3 states: CHAOS, FOCUS, BALANCE
- State transition logic
- Wallpaper mapping
- Kitty API integration

✅ **Wallpaper Control**
- Uses `kitty @ set-background-image`
- Validates wallpaper file existence
- Graceful degradation (non-Kitty terminals)
- Error handling

✅ **Auto-Transition Logic**
- Morning + inbox > 0 → CHAOS
- Deep work (high cognitive load) → FOCUS
- Daily goal achieved → BALANCE
- Manual override support

✅ **State Persistence**
- Saves to `State/visual_state.json`
- Restores state on session start
- Tracks state history (last 100 entries)

## Future Enhancements

Potential additions (not required for Phase 2):

1. **Custom Wallpapers**: Download high-quality wallpapers automatically
2. **Smooth Transitions**: Fade between wallpapers
3. **State Triggers**: Webhook support for external events
4. **Analytics**: Track time spent in each state
5. **Notifications**: Visual cues for state changes
6. **Themes**: Multiple wallpaper sets

## Dependencies

- Python 3.7+
- Kitty terminal (for wallpaper control)
- No external Python packages required

## License

Part of Thanos Operating System v2.0
