# Kitty Terminal Visual State System

**Reality bends to your workflow state.**

## Overview

The Thanos wallpaper system provides visual feedback of your current workflow state through Kitty terminal background images:

| State | Wallpaper | Meaning |
|-------|-----------|---------|
| **CHAOS** | `nebula_storm.png` | Morning disorder, unsorted tasks, starting state |
| **FOCUS** | `infinity_gauntlet_fist.png` | Deep work engaged, concentrated execution |
| **BALANCE** | `farm_sunrise.png` | Daily goals achieved, "The Garden" realized |

## Setup

### 1. Install Wallpapers

```bash
# Run setup script to create directory and get sourcing instructions
bash ~/Projects/Thanos/Tools/setup_wallpapers.sh
```

This creates `~/.thanos/wallpapers/` and provides guidance on sourcing the three required images.

### 2. Source Wallpapers

**Option A: Manual Download**
- Search for high-quality 4K wallpapers matching each theme
- Save to `~/.thanos/wallpapers/[name].png`

**Option B: Quick Sourcing**
```bash
# Example using wget (replace URLs with your chosen images)
cd ~/.thanos/wallpapers/

wget -O nebula_storm.png "https://[your-nebula-image-url]"
wget -O infinity_gauntlet_fist.png "https://[your-gauntlet-image-url]"
wget -O farm_sunrise.png "https://[your-farm-image-url]"
```

**Recommended Sources:**
- unsplash.com
- pexels.com
- wallhaven.cc
- hdqwalls.com

### 3. Verify Installation

```bash
python3 ~/Projects/Thanos/Tools/wallpaper_manager.py --check
```

Should output: "Kitty terminal detected"

## Usage

### Automatic State Management

The system auto-detects and applies states based on:

- **SessionStart Hook** → Auto-applies appropriate state on startup
- **Time of Day** → Morning (5am-12pm) defaults to CHAOS
- **WorkOS Metrics** → Points >= target triggers BALANCE
- **Session Duration** → Long sessions (>30min) indicate FOCUS

### Manual State Control

```bash
# Apply specific state
python3 ~/Projects/Thanos/Tools/wallpaper_manager.py --state chaos
python3 ~/Projects/Thanos/Tools/wallpaper_manager.py --state focus
python3 ~/Projects/Thanos/Tools/wallpaper_manager.py --state balance

# Auto-detect and apply
python3 ~/Projects/Thanos/Tools/wallpaper_manager.py --auto

# Detect current state without applying
python3 ~/Projects/Thanos/Tools/wallpaper_manager.py --detect
```

### Quick Aliases

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
alias chaos='python3 ~/Projects/Thanos/Tools/wallpaper_manager.py --state chaos'
alias focus='python3 ~/Projects/Thanos/Tools/wallpaper_manager.py --state focus'
alias balance='python3 ~/Projects/Thanos/Tools/wallpaper_manager.py --state balance'
```

## State Transition Logic

### CHAOS State
**Triggers:**
- Session start in morning hours (5am-12pm)
- More than 3 active tasks
- Fresh session with no deep work indicators

**Meaning:** Organization mode, inbox processing, task sorting

### FOCUS State
**Triggers:**
- Session running >30 minutes
- Afternoon/evening hours (12pm-9pm)
- Default work state

**Meaning:** Deep work, execution mode, concentrated effort

### BALANCE State
**Triggers:**
- Daily point goal achieved (points >= target)
- Manual invocation after completing work

**Meaning:** "The Garden" achieved, rest earned, goals completed

## Integration with Hooks

The wallpaper system integrates with:

**SessionStart Hook** (`hooks/session-start/thanos-start.sh`)
- Automatically applies appropriate state on session startup
- Uses `--auto` flag for intelligent state detection

**Future Integration Points:**
- UserPromptSubmit: Detect deep work requests → trigger FOCUS
- Daily goal tracking: Auto-trigger BALANCE when target reached
- Task completion: Transition states based on remaining work

## Troubleshooting

### Wallpaper Doesn't Change

1. **Check Kitty is running:**
   ```bash
   echo $KITTY_PID
   ```
   Should output a process ID. If empty, not in Kitty.

2. **Verify wallpapers exist:**
   ```bash
   ls -lh ~/.thanos/wallpapers/
   ```
   Should show all three PNG files.

3. **Test Kitty command manually:**
   ```bash
   kitty @ set-background-image ~/.thanos/wallpapers/nebula_storm.png
   ```

4. **Check for errors:**
   ```bash
   python3 ~/Projects/Thanos/Tools/wallpaper_manager.py --auto
   ```
   Will show any error messages.

### Not Running in Kitty

The wallpaper system only works in Kitty terminal. If you're in:
- SSH session
- WSL
- Different terminal (iTerm2, Alacritty, etc.)

The system will silently do nothing (graceful degradation).

### State Detection Issues

Run manual detection to see what state the system thinks you're in:

```bash
python3 ~/Projects/Thanos/Tools/wallpaper_manager.py --detect
```

Override with manual state if needed:

```bash
python3 ~/Projects/Thanos/Tools/wallpaper_manager.py --state [chaos|focus|balance]
```

## Architecture

**State Detection Logic:**
1. Check if daily goals achieved → BALANCE
2. Check if long-running session (>30min) → FOCUS
3. Check if morning hours OR many active tasks → CHAOS
4. Default → FOCUS

**Files:**
- `Tools/wallpaper_manager.py` - Core state management
- `Tools/setup_wallpapers.sh` - Installation helper
- `hooks/session-start/thanos-start.sh` - Auto-apply on startup
- `~/.thanos/wallpapers/` - Wallpaper storage

**Dependencies:**
- Kitty terminal
- Python 3
- WorkOS MCP (optional, for goal detection)
- TimeState.json (optional, for session duration)

## Philosophy

> "Reality is often disappointing. That is, it was. Now reality can be whatever I want."
> — Thanos

Your terminal reflects your state of being:
- **CHAOS** - The beginning. Disorder before order.
- **FOCUS** - The execution. Power concentrated.
- **BALANCE** - The achievement. The Garden earned.

Watch your terminal transform as you transform your day.

---

**The visual universe awaits your command.**
