# Thanos Mobile Command Center

Three enhancements for Claude Code mobile workflow:
1. **Thanos Launcher** - Epic audio intro when starting Claude Code
2. **Image Inbox** - Send images from phone to Mac for Claude Code to see
3. **Audio Listener** - Phone plays Thanos quotes when Claude completes tasks

## Quick Setup

### Prerequisites
- Termux installed on Android
- Termux:API installed from **F-Droid** (NOT Play Store)
- SSH key set up between phone and Mac
- Tailscale running on both devices

### Mac Side (Already Done)
```bash
# Created automatically:
~/inbox/           # Images land here
~/bin/inbox        # Inbox helper command
~/inbox/cleanup.sh # Auto-cleanup (runs at 3am)
```

### Phone Side (Termux)
```bash
# Copy this script to phone and run:
bash setup-termux.sh

# Or manually:
pkg install termux-api openssh
# Then follow the setup script steps
```

## Usage

### Start a session
```bash
thanos
# 🟣 "Fine, I'll do it myself."
# [connects to Mac, launches Claude Code]
```

### Send an image
```bash
# From phone
lastshot error    # Send latest screenshot as error.png
img photo.jpg bug # Send specific file as bug.jpg

# In Claude Code (Mac)
> Look at ~/inbox/error.png
```

### Check inbox
```bash
inbox list   # See what's there
inbox latest # Get path to newest
inbox show   # Open in Preview
inbox clear  # Delete all
```

## Audio Files

Download Thanos quotes and save to `/sdcard/sounds/`:
- `thanos-ill-do-it-myself.mp3`
- `thanos-inevitable.mp3`
- `thanos-perfectly-balanced.mp3`
- `thanos-destiny.mp3`
- `thanos-small-price.mp3`
- `thanos-hardest-choices.mp3`

Find them on YouTube (use youtube-dl or a converter).

## Troubleshooting

**No sound:** Install Termux:API from F-Droid, then `pkg install termux-api`

**SSH fails:** Check Tailscale is running, verify `~/.ssh/config`

**Images don't arrive:** Check `~/inbox` exists on Mac, test with `scp test.png mac:~/inbox/`

---

## Audio Listener (Claude → Phone)

When Claude Code completes tasks on Mac, your phone plays Thanos quotes.

### Setup

```bash
# Copy listener to phone
cp mobile/thanos-listener ~/bin/
chmod +x ~/bin/thanos-listener

# Add to ~/.bashrc for auto-controls:
cat >> ~/.bashrc << 'EOF'

# ==========================================
# THANOS AUDIO LISTENER
# ==========================================

start_thanos_listener() {
    if ! pgrep -f "thanos-listener" > /dev/null 2>&1; then
        nohup ~/bin/thanos-listener > ~/.thanos-listener.log 2>&1 &
        echo "🟣 Thanos listener started"
    fi
}

# Auto-start (uncomment to enable):
# start_thanos_listener

alias thanos-start='start_thanos_listener'
alias thanos-stop='pkill -f thanos-listener && echo "🟣 Listener stopped"'
alias thanos-status='pgrep -f thanos-listener > /dev/null && echo "🟣 Listener running" || echo "⚫ Listener stopped"'
alias thanos-log='tail -f ~/.thanos-listener.log'
EOF

source ~/.bashrc
```

### Usage

```bash
thanos-start   # Start listener in background
thanos-stop    # Stop listener
thanos-status  # Check if running
thanos-log     # View listener log
```

### How It Works

```
Mac (Claude Code)              Cloud              Phone (Termux)
─────────────────             ───────            ────────────────
thanos-say snap  ──publish──▶ ntfy.sh ──subscribe──▶ thanos-listener
                                                          │
                                                          ▼
                                                   Plays audio 🔊
```

### Test

```bash
# On phone: start listener
thanos-start

# On Mac: trigger audio
~/bin/thanos-say snap

# Phone should play "I'll do it myself" 🔊
```

### Trigger Reference

| Trigger | Quote |
|---------|-------|
| `snap`, `done` | "I'll do it myself" |
| `inevitable` | "I am inevitable" |
| `balanced` | "Perfectly balanced" |
| `destiny` | "Dread it, run from it" |
| `price` | "A small price to pay" |
| `hard` | "The hardest choices" |
