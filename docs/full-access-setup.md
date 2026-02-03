# Full macOS Access Setup for OpenClaw

## Goal
Give Thanos (OpenClaw) full autonomous access to all apps and system functions.

## Permissions Needed

### 1. Accessibility (Critical)
**System Settings → Privacy & Security → Accessibility**

Add these apps:
- [ ] Terminal.app
- [ ] Node (if running standalone)
- [ ] OpenClaw.app (if using menubar app)

This enables: clicking, typing, window management via Peekaboo/cliclick

### 2. Screen Recording
**System Settings → Privacy & Security → Screen Recording**

Add:
- [ ] Terminal.app
- [ ] OpenClaw.app

This enables: Peekaboo screenshots, screen capture

### 3. Full Disk Access
**System Settings → Privacy & Security → Full Disk Access**

Add:
- [ ] Terminal.app

This enables: reading/writing files anywhere (Mail, Notes databases, etc.)

### 4. Automation
**System Settings → Privacy & Security → Automation**

Allow Terminal to control:
- [ ] System Events
- [ ] Finder
- [ ] Calendar
- [ ] Mail
- [ ] Messages (if desired)
- [ ] Notes
- [ ] Reminders

This enables: AppleScript automation of native apps

---

## Tools to Install

```bash
# cliclick - command line mouse/keyboard control
brew install cliclick

# Peekaboo already available via skill
```

## Verification Commands

```bash
# Test Accessibility
cliclick c:100,100  # Should click at coordinates

# Test Screen Recording
/opt/homebrew/bin/peekaboo ocr --app "Finder"

# Test AppleScript
osascript -e 'tell application "Finder" to get name of front window'
```

## Post-Setup Capabilities

Once configured, I can:
- Click any button in any app
- Read text from any screen
- Control native macOS apps (Notes, Reminders, Mail, Calendar)
- Take screenshots of specific apps/windows
- Type into any text field
- Navigate any UI autonomously

## Security Notes

- These permissions are powerful - equivalent to a human at the keyboard
- All actions are logged in memory/daily notes
- Still ask permission for: purchases, external messages, public posts
- Browser autonomy metaprompt still applies

---

*Setup guide for Jeremy - run through when feeling better*
