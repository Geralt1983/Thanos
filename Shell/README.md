# Thanos Shell CLI - Phase 2

Unified command interface for Thanos OS with classification routing, persona integration, and multi-modal feedback.

## Architecture

```
User Input
    ↓
[thanos-cli] ─→ Classify (Shell/lib/classifier.py)
    ↓
┌─────────────────────────────────────────────┐
│  Classification Gate                        │
│  - thinking: Reflective, no action         │
│  - venting: Emotional validation           │
│  - observation: Optional capture           │
│  - question: Direct Claude execution       │
│  - task: Full orchestration + feedback     │
└─────────────────────────────────────────────┘
    ↓
Route to Handler
    ↓
┌─────────────────────────────────────────────┐
│  Multi-Modal Feedback                       │
│  - Voice (Shell/lib/voice.py)              │
│  - Visuals (Shell/lib/visuals.py)          │
│  - Notifications (Shell/lib/notifications.py)│
│  - Activity Log (State/shell_activity.log) │
└─────────────────────────────────────────────┘
```

## Components

### Core

- **thanos-cli**: Main entry point with classification routing
  - Classification gate (prevent casual thoughts → tasks)
  - Route handlers for each classification type
  - Integration with voice, visuals, notifications
  - Activity logging

### Libraries (Shell/lib/)

- **classifier.py**: Input classification engine
  - Pattern-based classification
  - Priority ordering: venting → task → question → thinking → observation
  - Test coverage for all classification types

- **voice.py**: Voice synthesis integration
  - ElevenLabs API integration
  - Thanos persona voice responses
  - Async playback for non-blocking feedback

- **visuals.py**: Terminal visual state management
  - Kitty terminal wallpaper control
  - State transitions: CHAOS → FOCUS → BALANCE
  - Automatic state detection

- **notifications.py**: System notification triggers
  - macOS notification center integration
  - Telegram bot notifications (optional)
  - Urgency levels: low, normal, critical

## Usage

### Basic Commands

```bash
# Task execution with full feedback
./Shell/thanos-cli "Add a task to review Q4 planning"

# Direct question
./Shell/thanos-cli "What's my readiness?"

# Casual thought (no task created)
./Shell/thanos-cli "I'm wondering if we should refactor this"

# Emotional venting (validation only)
./Shell/thanos-cli "I'm so tired of this bug"

# Observation (optional capture)
./Shell/thanos-cli "I noticed the API is slow"
```

### Dry-Run Mode

```bash
# Show classification without execution
./Shell/thanos-cli --dry-run "Add a task..."
# Output: Classification: task
#         Input: Add a task...
```

### Help

```bash
./Shell/thanos-cli --help
```

## Classification Examples

| Input | Classification | Behavior |
|-------|----------------|----------|
| "Add a task to..." | task | Execute via Claude, voice feedback, visual state |
| "What's my readiness?" | question | Direct Claude execution |
| "I'm wondering if..." | thinking | Acknowledge, offer to capture |
| "I'm so tired..." | venting | Validate, no forced action |
| "I noticed..." | observation | Note, offer to remember |
| "Can you help debug?" | task | Execute with full orchestration |

## Configuration

### Environment Variables

```bash
# Enable voice synthesis
export THANOS_VOICE=1
export ELEVENLABS_API_KEY="your-key"

# Enable Telegram notifications
export TELEGRAM_BOT_TOKEN="your-token"
export TELEGRAM_CHAT_ID="your-chat-id"

# Dry-run mode (disable feedback)
export DRY_RUN=1

# Debug logging
export DEBUG=1
```

## Logging

All activity logged to: `State/shell_activity.log`

```
[2026-01-21 02:00:00] [INFO] Input received: Add a task...
[2026-01-21 02:00:00] [INFO] Classification: task
[2026-01-21 02:00:01] [INFO] Task completed successfully
```

## Integration Points

### Claude CLI Integration

Task and question classifications are routed to Claude CLI:

```bash
claude "$USER_INPUT"
```

### Voice Integration

On task completion:

```python
from Shell.lib.voice import VoiceManager
voice = VoiceManager()
voice.speak("The work is done")
```

### Visual State Integration

On task start:

```python
from Shell.lib.visuals import VisualStateManager
vsm = VisualStateManager()
vsm.set_state("FOCUS")
```

### Notification Integration

On task completion:

```python
from Shell.lib.notifications import NotificationManager
nm = NotificationManager()
nm.send("Thanos", "Task completed", "normal")
```

## Persona Responses

Thanos quotes based on context:

| Context | Quote |
|---------|-------|
| completion | "A small price to pay for salvation. Good." |
| resistance | "You could not live with your own failure." |
| low_energy | "Exhaustion is a chemical reaction." |
| thinking | "You contemplate the path ahead." |
| venting | "The hardest choices require the strongest wills." |
| observation | "The universe notes your observation." |
| victory | "The Snap is complete. Rest now." |

## Testing

### Classifier Tests

```bash
python3 Shell/lib/classifier.py
```

Expected output:
```
Classification Test Results:
------------------------------------------------------------
✓ 'I'm wondering if we should refactor this' → thinking
✓ 'I'm so tired of this bug' → venting
✓ 'I noticed the API is slow' → observation
✓ 'What's on my calendar?' → question
✓ 'Add a task to review Q4 planning' → task
✓ 'Can you help me debug this?' → task
✓ 'This is so frustrating' → venting
✓ 'I'm thinking about changing careers' → thinking
```

### Manual CLI Tests

```bash
# Test each classification type
./Shell/thanos-cli --dry-run "Add task to test"        # → task
./Shell/thanos-cli --dry-run "What's my energy?"       # → question
./Shell/thanos-cli --dry-run "I'm wondering about X"   # → thinking
./Shell/thanos-cli --dry-run "I'm so frustrated"       # → venting
./Shell/thanos-cli --dry-run "I noticed API slowness"  # → observation
```

## Future Enhancements

1. **Energy-Aware Gating**: Integrate Oura data to block complex tasks on low energy
2. **Smart Routing**: Direct health questions to health-insight skill
3. **Brain Dump Integration**: Automatic capture of thoughts/observations
4. **Completion Tracking**: Detect daily goal achievement for "Snap" completion
5. **Interactive Prompts**: Y/N prompts for thinking/observation capture

## Dependencies

- Python 3.9+
- Claude CLI (for task/question execution)
- Kitty terminal (for visual states)
- ElevenLabs API key (for voice, optional)
- Telegram bot token (for notifications, optional)

## File Structure

```
Shell/
├── thanos-cli              # Main CLI entry point (executable)
├── lib/
│   ├── classifier.py       # Classification engine
│   ├── voice.py            # Voice synthesis
│   ├── visuals.py          # Visual state manager
│   └── notifications.py    # Notification triggers
└── README.md               # This file

State/
└── shell_activity.log      # Activity log
```

## Philosophy

"Dread it. Run from it. The work arrives all the same."

The Shell CLI enforces ruthless discipline through:
- **Classification Gate**: Prevents casual thoughts from becoming tasks
- **Persona Integration**: Thanos-style responses for motivation
- **Multi-Modal Feedback**: Voice, visuals, notifications for immersion
- **Activity Logging**: Complete audit trail for accountability

Perfect balance, as all things should be.
