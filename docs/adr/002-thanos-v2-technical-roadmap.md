# ADR-002: Thanos v2.0 Technical Roadmap

**Date:** 2026-01-20
**Status:** Active Implementation
**Architect:** Hive Mind Swarm (System Architect + Project Coordinator)
**Related:** ADR-001 (Memory Architecture Analysis)

## Executive Summary

This document provides the technical roadmap for transforming Thanos from its current state into a modular, skill-based Personal AI (PAI) system with 4 architectural layers:

1. **PAI Architecture**: Classification-first routing with energy-aware gating
2. **Shell Identity**: Thanos persona with voice, visuals, and behavioral protocols
3. **Operator Vigilance**: Background daemon monitoring system health
4. **Ubiquitous Access**: Cross-device terminal access via tmux + ttyd + Tailscale

## Current State Analysis

### What Exists Today

**Working Systems:**
- WorkOS MCP: Tasks, habits, energy tracking, brain dumps, clients
- Oura MCP: Sleep, readiness, activity, health metrics
- claude-mem plugin: ChromaDB-based memory with worker service
- Basic CLI at `thanos.py`: Natural language command routing
- State files: CurrentFocus.md, TimeState.json, brain_dumps.json
- Tools: Command router, adapters (calendar, MCP, Oura), accountability processor

**Architecture Gaps:**
- No classification gate (casual thoughts become tasks)
- No energy-aware task routing
- No skill-based architecture
- No operator daemon for background monitoring
- No voice synthesis or visual state management
- No ubiquitous access system
- Memory architecture split (ADR-001: claude-mem vs Thanos Memory)

### Migration Considerations

**Preserve:**
- All existing State/ files and databases
- MCP integrations (WorkOS, Oura, Monarch when ready)
- Tools/ directory utilities
- Current hook system structure

**Transform:**
- thanos.py → Shell wrapper with classification gate
- Tools/command_router.py → Modular skills system
- Add daemon layer for background monitoring
- Add shell libraries for voice/visuals/notifications
- Add tmux/ttyd/Tailscale access layer

## Target Architecture

### Layer 1: PAI (Personal AI)

**Purpose:** Classification-first routing with skill-based execution

**Directory Structure:**
```
.claude/
  skills/
    task-router/         # Task management skill
    health-insight/      # Health data interpretation
    finance/             # Monarch Money integration (future)
    orchestrator/        # Meta-skill for complex workflows
  hooks/
    session-start/
      hydrate.sh         # Load state, show brief
    pre-tool-use/
      classify_input.py  # Gate: thinking/venting/observation/question/task
    post-tool-use/
      audit_log.py       # Log all tool uses
      dynamic_priority.py # Update CurrentFocus.md on priority shifts
```

**Skills Specification:**

**TaskRouter Skill:**
```yaml
name: task-router
version: 1.0.0
use_when:
  - "User explicitly requests task operation"
  - "Classified input type is 'task'"
  - "Action verbs: create, add, complete, review, promote"
tools_required:
  - workos_*
workflow: |
  1. Parse intent (create/complete/review/promote)
  2. Check energy level (workos_get_energy or oura readiness)
  3. If energy < 60 and task is complex: suggest simple alternatives
  4. Execute task operation with appropriate WorkOS tool
  5. Update CurrentFocus.md if priority shifts
  6. Respond in Thanos voice
```

**HealthInsight Skill:**
```yaml
name: health-insight
version: 1.0.0
use_when:
  - "User asks about health, sleep, readiness, energy"
  - "Morning brief requested"
  - "Oura-related queries"
tools_required:
  - oura__*
  - workos_get_energy
workflow: |
  1. Fetch today's Oura data (readiness, sleep, activity)
  2. Calculate health snapshot
  3. Map to energy level (readiness > 85 = high, 70-84 = medium, < 70 = low)
  4. Suggest energy-appropriate tasks from WorkOS
  5. Format in Thanos voice with visual state
```

**Orchestrator Skill:**
```yaml
name: orchestrator
version: 1.0.0
use_when:
  - "Complex multi-step request"
  - "Requires coordination of multiple skills"
  - "Code/architecture/technical work"
workflow: |
  1. Initialize hive mind swarm (MANDATORY for technical work)
  2. Decompose objective into skill-specific sub-tasks
  3. Route to TaskRouter, HealthInsight, Finance as needed
  4. Coordinate results
  5. Report completion
```

**Classification Hook:**
```python
# .claude/hooks/pre-tool-use/classify_input.py
import sys
import re

def classify_input(user_message: str) -> str:
    """
    Classify user input to prevent casual thoughts becoming tasks.

    Returns: thinking|venting|observation|question|task
    """
    # Thinking indicators
    thinking_patterns = [
        r"i'm wondering",
        r"what if",
        r"thinking about",
        r"considering",
    ]

    # Venting indicators
    venting_patterns = [
        r"frustrated",
        r"overwhelmed",
        r"stressed",
        r"i hate",
        r"annoying",
    ]

    # Observation indicators
    observation_patterns = [
        r"i noticed",
        r"just saw",
        r"interesting that",
    ]

    # Task indicators (must be explicit)
    task_patterns = [
        r"\b(add|create|make|build|do|complete|finish)\s+(?:a\s+)?task",
        r"can you.*(?:add|create|make)",
        r"help me.*(?:plan|organize|do)",
    ]

    lower_msg = user_message.lower()

    # Check question first (highest priority)
    if "?" in user_message:
        return "question"

    # Check task patterns (must be explicit)
    for pattern in task_patterns:
        if re.search(pattern, lower_msg):
            return "task"

    # Check venting
    for pattern in venting_patterns:
        if re.search(pattern, lower_msg):
            return "venting"

    # Check observation
    for pattern in observation_patterns:
        if re.search(pattern, lower_msg):
            return "observation"

    # Check thinking
    for pattern in thinking_patterns:
        if re.search(pattern, lower_msg):
            return "thinking"

    # Default: observation (safe default, doesn't create tasks)
    return "observation"

if __name__ == "__main__":
    message = sys.argv[1] if len(sys.argv) > 1 else ""
    print(classify_input(message))
```

### Layer 2: Shell Identity

**Purpose:** Thanos persona, voice, visuals, behavioral protocols

**Directory Structure:**
```
Shell/
  lib/
    voice.py           # ElevenLabs TTS integration
    visuals.py         # Kitty image protocol
    notifications.py   # macOS notifications + Telegram
    parser.py          # Voice command parsing
  thanos-cli          # Main wrapper script
```

**Voice Synthesis (voice.py):**
```python
import os
import requests
from pathlib import Path

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
THANOS_VOICE_ID = "thanos-deep-voice-id"  # Custom voice clone
AUDIO_CACHE_DIR = Path.home() / ".thanos" / "audio-cache"

def synthesize_speech(text: str, play: bool = True) -> Path:
    """
    Synthesize speech using ElevenLabs API.

    Args:
        text: Text to synthesize
        play: Whether to play immediately

    Returns:
        Path to cached audio file
    """
    # Hash text for cache key
    import hashlib
    cache_key = hashlib.md5(text.encode()).hexdigest()
    audio_path = AUDIO_CACHE_DIR / f"{cache_key}.mp3"

    # Check cache
    if audio_path.exists():
        if play:
            os.system(f"afplay {audio_path}")
        return audio_path

    # Call ElevenLabs API
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{THANOS_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.75,
            "similarity_boost": 0.85
        }
    }

    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()

    # Cache audio
    AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(response.content)

    if play:
        os.system(f"afplay {audio_path}")

    return audio_path
```

**Visual State (visuals.py):**
```python
import os
from pathlib import Path

WALLPAPER_DIR = Path.home() / ".thanos" / "wallpapers"

class ThanosVisualState:
    """Manage Thanos visual state in Kitty terminal."""

    STATES = {
        "CHAOS": WALLPAPER_DIR / "nebula_storm.png",
        "FOCUS": WALLPAPER_DIR / "infinity_gauntlet_fist.png",
        "BALANCE": WALLPAPER_DIR / "farm_sunrise.png",
    }

    @classmethod
    def set_state(cls, state: str):
        """Set visual state by changing terminal wallpaper."""
        if state not in cls.STATES:
            raise ValueError(f"Invalid state: {state}")

        wallpaper = cls.STATES[state]
        if not wallpaper.exists():
            print(f"Warning: Wallpaper not found: {wallpaper}")
            return

        # Use Kitty remote control
        os.system(f"kitty @ set-background-image {wallpaper}")

    @classmethod
    def auto_transition(cls, context: dict):
        """Auto-transition based on context."""
        # Morning/unsorted → CHAOS
        if context.get("time_of_day") == "morning" and context.get("inbox", 0) > 0:
            cls.set_state("CHAOS")

        # Deep work → FOCUS
        elif context.get("cognitive_load") == "high":
            cls.set_state("FOCUS")

        # Goals achieved → BALANCE
        elif context.get("daily_goal_achieved"):
            cls.set_state("BALANCE")
```

**Shell Wrapper (thanos-cli):**
```bash
#!/bin/bash
# Main Thanos CLI wrapper

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Classification gate
USER_INPUT="$*"
CLASSIFICATION=$(python3 "$PROJECT_ROOT/.claude/hooks/pre-tool-use/classify_input.py" "$USER_INPUT")

# Route based on classification
case "$CLASSIFICATION" in
    task)
        # Execute via Claude with TaskRouter skill
        echo "Routing to TaskRouter skill..."
        claude "$USER_INPUT"
        ;;

    question)
        # Direct execution
        claude "$USER_INPUT"
        ;;

    thinking|venting|observation)
        # Acknowledge without creating tasks
        echo "### THANOS // $(date +"%H:%M")"
        echo ""
        case "$CLASSIFICATION" in
            thinking)
                echo "You contemplate the path ahead. The universe listens."
                echo ""
                echo "Would you like me to capture this thought?"
                ;;
            venting)
                echo "Exhaustion is a chemical reaction. It is irrelevant to the objective."
                echo ""
                echo "But I acknowledge your struggle. Rest if needed."
                ;;
            observation)
                echo "The universe notes your observation."
                echo ""
                echo "Should I remember this?"
                ;;
        esac
        ;;

    *)
        # Default: pass through to Claude
        claude "$USER_INPUT"
        ;;
esac
```

### Layer 3: Operator Vigilance

**Purpose:** Background daemon for system monitoring and alerts

**Directory Structure:**
```
Operator/
  daemon.py           # Main daemon process
  config.yaml         # Configuration
  monitors/
    health.py         # Oura sync, low readiness alerts
    tasks.py          # Overdue tasks, missed habits
    finance.py        # Monarch balance checks (future)
    patterns.py       # Unusual behavior detection
  alerters/
    telegram.py       # Telegram bot integration
    notification.py   # macOS notification center
    voice.py          # Voice alerts via ElevenLabs
  LaunchAgent/
    com.thanos.operator.plist  # macOS launch agent
```

**Daemon Implementation (daemon.py):**
```python
#!/usr/bin/env python3
"""
Thanos Operator Daemon

Background monitoring and alerting for Thanos system.
Runs continuously, checking health/tasks/finance on intervals.
"""

import os
import sys
import time
import yaml
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add project to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from Operator.monitors.health import HealthMonitor
from Operator.monitors.tasks import TaskMonitor
from Operator.monitors.patterns import PatternMonitor
from Operator.alerters.telegram import TelegramAlerter
from Operator.alerters.notification import NotificationAlerter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PROJECT_ROOT / 'logs' / 'operator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('thanos.operator')

class OperatorDaemon:
    """Main daemon orchestrator."""

    def __init__(self, config_path: Path):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        # Initialize monitors
        self.monitors = {
            'health': HealthMonitor(self.config['monitors']['health']),
            'tasks': TaskMonitor(self.config['monitors']['tasks']),
            'patterns': PatternMonitor(self.config['monitors']['patterns']),
        }

        # Initialize alerters
        self.alerters = {
            'telegram': TelegramAlerter(self.config['alerters']['telegram']),
            'notification': NotificationAlerter(self.config['alerters']['notification']),
        }

        self.running = False

    def start(self):
        """Start daemon loop."""
        logger.info("Thanos Operator starting...")
        self.running = True

        try:
            while self.running:
                self.tick()
                time.sleep(self.config['tick_interval'])
        except KeyboardInterrupt:
            logger.info("Operator shutting down gracefully...")
            self.running = False

    def tick(self):
        """Execute one monitoring cycle."""
        alerts = []

        # Run each monitor
        for name, monitor in self.monitors.items():
            try:
                monitor_alerts = monitor.check()
                alerts.extend(monitor_alerts)
            except Exception as e:
                logger.error(f"Monitor {name} failed: {e}")

        # Send alerts
        for alert in alerts:
            self.send_alert(alert)

    def send_alert(self, alert: Dict[str, Any]):
        """Send alert via configured channels."""
        severity = alert.get('severity', 'info')

        # Route based on severity
        if severity == 'critical':
            # Telegram + macOS notification + voice
            for alerter in self.alerters.values():
                try:
                    alerter.send(alert)
                except Exception as e:
                    logger.error(f"Alerter {alerter.__class__.__name__} failed: {e}")

        elif severity == 'warning':
            # Telegram + macOS notification
            for name in ['telegram', 'notification']:
                try:
                    self.alerters[name].send(alert)
                except Exception as e:
                    logger.error(f"Alerter {name} failed: {e}")

        else:
            # Just log
            logger.info(f"Info alert: {alert['message']}")

def main():
    config_path = PROJECT_ROOT / 'Operator' / 'config.yaml'
    daemon = OperatorDaemon(config_path)
    daemon.start()

if __name__ == '__main__':
    main()
```

**Health Monitor (monitors/health.py):**
```python
from datetime import datetime, timedelta
from typing import List, Dict, Any
import os
import sys

# MCP client for Oura data
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'Tools'))
from adapters.mcp_client import MCPClient

class HealthMonitor:
    """Monitor Oura Ring health data and alert on issues."""

    def __init__(self, config: dict):
        self.config = config
        self.mcp = MCPClient('oura-mcp')

    def check(self) -> List[Dict[str, Any]]:
        """Check health metrics and return alerts."""
        alerts = []

        # Get today's readiness
        today = datetime.now().strftime('%Y-%m-%d')
        try:
            readiness_data = self.mcp.call('get_daily_readiness', {
                'startDate': today,
                'endDate': today
            })

            if readiness_data and len(readiness_data) > 0:
                score = readiness_data[0].get('score', 0)

                # Critical: readiness < 50
                if score < 50:
                    alerts.append({
                        'type': 'health',
                        'severity': 'critical',
                        'title': 'CRITICAL: Low Readiness Detected',
                        'message': f'Readiness score: {score}. The stones require charging. Rest is not optional.',
                        'data': {'readiness': score}
                    })

                # Warning: readiness 50-65
                elif score < 65:
                    alerts.append({
                        'type': 'health',
                        'severity': 'warning',
                        'title': 'Warning: Below Optimal Readiness',
                        'message': f'Readiness: {score}. Light tasks only today.',
                        'data': {'readiness': score}
                    })

        except Exception as e:
            # Alert on sync failure if last sync > 24h ago
            alerts.append({
                'type': 'health',
                'severity': 'warning',
                'title': 'Oura Sync Issue',
                'message': f'Failed to fetch readiness data: {e}',
                'data': {}
            })

        return alerts
```

**Task Monitor (monitors/tasks.py):**
```python
from datetime import datetime, timedelta
from typing import List, Dict, Any

class TaskMonitor:
    """Monitor tasks and habits for overdue items."""

    def __init__(self, config: dict):
        self.config = config
        self.mcp = MCPClient('workos-mcp')

    def check(self) -> List[Dict[str, Any]]:
        """Check for overdue tasks and missed habits."""
        alerts = []

        # Get active tasks
        try:
            tasks = self.mcp.call('workos_get_tasks', {'status': 'active'})

            # Check for top priority tasks that have been active > 3 days
            for task in tasks:
                if task.get('valueTier') == 'milestone':
                    created = datetime.fromisoformat(task['createdAt'])
                    age_days = (datetime.now() - created).days

                    if age_days > 3:
                        alerts.append({
                            'type': 'task',
                            'severity': 'warning',
                            'title': 'Milestone Task Stalled',
                            'message': f"Milestone '{task['title']}' has been active for {age_days} days. The work does not wait.",
                            'data': {'task': task}
                        })

        except Exception as e:
            logger.error(f"Task check failed: {e}")

        # Check habits
        try:
            habits = self.mcp.call('life_habit_checkin', {'timeOfDay': 'all'})

            overdue_count = sum(1 for h in habits if not h.get('completed_today'))

            if overdue_count > 3:
                alerts.append({
                    'type': 'habits',
                    'severity': 'warning',
                    'title': 'Habits Falling Behind',
                    'message': f'{overdue_count} habits not completed today. Small disciplines prevent great failures.',
                    'data': {'overdue_count': overdue_count}
                })

        except Exception as e:
            logger.error(f"Habit check failed: {e}")

        return alerts
```

### Layer 4: Ubiquitous Access

**Purpose:** Cross-device terminal access

**Directory Structure:**
```
Access/
  thanos-session.sh    # Tmux session manager
  ttyd-server.sh       # Web terminal server
  LaunchAgent/
    com.thanos.ttyd.plist  # macOS launch agent for ttyd
```

**Tmux Session Manager (thanos-session.sh):**
```bash
#!/bin/bash
# Thanos tmux session manager

SESSION_NAME="thanos"

# Create or attach to session
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "Attaching to existing Thanos session..."
    tmux attach-session -t "$SESSION_NAME"
else
    echo "Creating new Thanos session..."

    # Create session with main window
    tmux new-session -d -s "$SESSION_NAME" -n "main"

    # Window 1: Main Thanos CLI
    tmux send-keys -t "$SESSION_NAME:main" "cd $HOME/Projects/Thanos" C-m
    tmux send-keys -t "$SESSION_NAME:main" "clear && ./Shell/thanos-cli" C-m

    # Window 2: Logs
    tmux new-window -t "$SESSION_NAME" -n "logs"
    tmux send-keys -t "$SESSION_NAME:logs" "cd $HOME/Projects/Thanos/logs" C-m
    tmux send-keys -t "$SESSION_NAME:logs" "tail -f operator.log" C-m

    # Window 3: State
    tmux new-window -t "$SESSION_NAME" -n "state"
    tmux send-keys -t "$SESSION_NAME:state" "cd $HOME/Projects/Thanos/State" C-m
    tmux send-keys -t "$SESSION_NAME:state" "watch -n 60 'cat CurrentFocus.md'" C-m

    # Select main window and attach
    tmux select-window -t "$SESSION_NAME:main"
    tmux attach-session -t "$SESSION_NAME"
fi
```

**Web Terminal Server (ttyd-server.sh):**
```bash
#!/bin/bash
# ttyd web terminal server for remote access

PORT=7681
CREDENTIAL_FILE="$HOME/.thanos/ttyd-credentials"

# Generate credentials if not exist
if [ ! -f "$CREDENTIAL_FILE" ]; then
    echo "Generating ttyd credentials..."
    mkdir -p "$(dirname "$CREDENTIAL_FILE")"
    echo "thanos:$(openssl rand -base64 32)" > "$CREDENTIAL_FILE"
    chmod 600 "$CREDENTIAL_FILE"
fi

CREDENTIALS=$(cat "$CREDENTIAL_FILE")

# Start ttyd server
ttyd \
    --port "$PORT" \
    --credential "$CREDENTIALS" \
    --writable \
    --client-option fontSize=14 \
    --client-option fontFamily="'JetBrains Mono', monospace" \
    --client-option theme='{"background": "#1a1a2e", "foreground": "#eee"}' \
    bash -c "tmux attach-session -t thanos || tmux new-session -s thanos"
```

**Tailscale Funnel Integration:**
```bash
# Expose ttyd via Tailscale Funnel
tailscale funnel --bg --https=443 7681

# Access from anywhere: https://<machine-name>.<tailnet>.ts.net
```

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1)

**Tasks:**
1. Create directory structure (PAI, Shell, Operator, Access)
2. Implement classification hook (pre-tool-use/classify_input.py)
3. Build basic skills: TaskRouter, HealthInsight
4. Update dynamic priority hook (post-tool-use/dynamic_priority.py)
5. Test classification gate with various input types

**Success Criteria:**
- Classification correctly distinguishes thinking/venting/observation/question/task
- TaskRouter skill executes task operations via WorkOS
- HealthInsight skill fetches Oura data and suggests energy-appropriate tasks
- CurrentFocus.md updates automatically on priority shifts
- No casual thoughts accidentally create tasks

**Files Created:**
```
.claude/hooks/pre-tool-use/classify_input.py
.claude/hooks/post-tool-use/dynamic_priority.py
.claude/skills/task-router/skill.yaml
.claude/skills/task-router/workflow.py
.claude/skills/health-insight/skill.yaml
.claude/skills/health-insight/workflow.py
```

### Phase 2: Shell Identity (Week 2)

**Tasks:**
1. Implement Shell/lib/voice.py (ElevenLabs integration)
2. Implement Shell/lib/visuals.py (Kitty wallpaper control)
3. Implement Shell/lib/notifications.py (macOS + Telegram)
4. Build Shell/thanos-cli wrapper with classification routing
5. Create wallpaper set (nebula_storm, infinity_gauntlet_fist, farm_sunrise)
6. Test voice synthesis with cached responses
7. Test visual state transitions

**Success Criteria:**
- Voice synthesis works with ElevenLabs API
- Kitty wallpaper changes based on state (CHAOS/FOCUS/BALANCE)
- thanos-cli routes correctly based on classification
- macOS notifications display properly
- Audio caching reduces API calls

**Files Created:**
```
Shell/lib/voice.py
Shell/lib/visuals.py
Shell/lib/notifications.py
Shell/lib/parser.py
Shell/thanos-cli
~/.thanos/wallpapers/nebula_storm.png
~/.thanos/wallpapers/infinity_gauntlet_fist.png
~/.thanos/wallpapers/farm_sunrise.png
```

### Phase 3: Operator Daemon (Week 3)

**Tasks:**
1. Implement Operator/daemon.py main loop
2. Implement monitors: health.py, tasks.py, patterns.py
3. Implement alerters: telegram.py, notification.py
4. Create Operator/config.yaml
5. Create LaunchAgent plist for auto-start
6. Test daemon monitoring cycle
7. Test alert routing (info/warning/critical)

**Success Criteria:**
- Daemon runs continuously without crashes
- Health monitor detects low readiness and alerts
- Task monitor detects overdue milestones
- Telegram alerts deliver successfully
- macOS notifications display
- Daemon auto-starts on login via LaunchAgent

**Files Created:**
```
Operator/daemon.py
Operator/config.yaml
Operator/monitors/health.py
Operator/monitors/tasks.py
Operator/monitors/patterns.py
Operator/alerters/telegram.py
Operator/alerters/notification.py
Operator/LaunchAgent/com.thanos.operator.plist
```

### Phase 4: Ubiquitous Access (Week 4)

**Tasks:**
1. Create Access/thanos-session.sh (tmux manager)
2. Create Access/ttyd-server.sh (web terminal)
3. Create LaunchAgent plist for ttyd auto-start
4. Configure Tailscale Funnel for HTTPS access
5. Test tmux session creation and attachment
6. Test ttyd web access from phone/tablet
7. Test Tailscale Funnel remote access

**Success Criteria:**
- Tmux session creates/attaches correctly with 3 windows
- ttyd serves terminal over HTTPS with auth
- Tailscale Funnel provides secure remote access
- Can access Thanos CLI from any device with Tailscale
- Sessions persist across terminal closes

**Files Created:**
```
Access/thanos-session.sh
Access/ttyd-server.sh
Access/LaunchAgent/com.thanos.ttyd.plist
~/.thanos/ttyd-credentials
```

### Phase 5: Integration & Testing (Week 5)

**Tasks:**
1. End-to-end workflow testing
2. Performance optimization
3. Error handling improvements
4. Documentation updates
5. Migration from current thanos.py to new architecture
6. Backup current state before migration
7. Gradual rollout with fallback option

**Success Criteria:**
- All 4 layers working together seamlessly
- Classification gate prevents unwanted task creation
- Energy-aware routing works correctly
- Operator daemon runs stably for 7+ days
- Remote access functional from multiple devices
- No regressions in existing functionality
- User can fall back to old system if needed

## Memory Architecture Decision

**From ADR-001**, we have 4 options for resolving the memory split. For Thanos v2.0:

**Recommendation: Option 4 (Replace claude-mem with Thanos hooks)**

**Rationale:**
- Simplifies architecture (no external worker service)
- Full control over memory pipeline
- Aligns with v2.0 skill-based design
- Can integrate with post-tool-use hooks easily

**Implementation:**
1. Build MCP server for Thanos Memory (`mcp-servers/thanos-memory-mcp/`)
2. Update post-tool-use hook to call MemoryService.capture_activity()
3. Replace claude-mem MCP tools in `.claude/settings.json`
4. Migrate existing observations from ChromaDB to Thanos Memory
5. Disable claude-mem worker service

**Timeline:** Integrate into Phase 1 (Core Infrastructure)

## Risk Analysis

### High-Risk Items

1. **Voice API Dependency**
   - Risk: ElevenLabs API changes or quota limits
   - Mitigation: Implement aggressive caching, fallback to text-only

2. **Daemon Stability**
   - Risk: Daemon crashes and doesn't restart
   - Mitigation: LaunchAgent with automatic restart, comprehensive error handling

3. **Memory Migration**
   - Risk: Data loss during claude-mem → Thanos Memory migration
   - Mitigation: Full backup before migration, parallel systems during transition

4. **Classification Accuracy**
   - Risk: False positives (casual thoughts → tasks) or false negatives (missing real tasks)
   - Mitigation: Extensive testing, user feedback loop, adjustable patterns

### Medium-Risk Items

1. **Tailscale Funnel Security**
   - Risk: Exposed terminal could be compromised
   - Mitigation: Strong credentials, Tailscale ACLs, audit logging

2. **Visual State Transitions**
   - Risk: Kitty-specific features may not work in all terminals
   - Mitigation: Graceful degradation to text-only mode

## Success Metrics

**Technical:**
- Classification accuracy > 95% (measured over 100 inputs)
- Daemon uptime > 99.5% (weekly)
- Voice synthesis latency < 2s (cached) / < 5s (uncached)
- Remote access response time < 500ms
- Zero data loss during memory migration

**Functional:**
- User reports fewer accidental task creations
- Energy-aware routing matches user's actual capacity
- Visual/voice feedback enhances experience (user survey)
- Remote access used at least weekly
- Operator catches real issues before user notices

**Behavioral:**
- CurrentFocus.md stays current (checked weekly)
- Brain dump → task conversion more intentional
- User can articulate difference between thinking/venting/task
- Response style matches Thanos persona consistently

## Dependencies

**External Services:**
- ElevenLabs API (voice synthesis)
- WorkOS MCP (tasks, habits, energy)
- Oura MCP (health data)
- Monarch MCP (future - finance)
- Telegram Bot API (alerts)
- Tailscale (remote access)

**System Requirements:**
- macOS (for LaunchAgent, Notification Center)
- Kitty terminal (for visual state)
- tmux (for session management)
- ttyd (for web terminal)
- Python 3.11+
- Bun or Node.js (for MCP servers)

## Next Steps

1. **Create Phase 1 implementation tasks** (next todo item)
2. **Set up development branch** for v2.0 work
3. **Backup current State/** before making changes
4. **Begin Phase 1: Core Infrastructure** implementation

---

**Prepared By:** Hive Mind Swarm
- System Architect: Architecture design, layer specifications
- Project Coordinator: Phasing, timeline, risk analysis

**Swarm ID:** `swarm_1768954645922_fe0i4itw2`
**Completed:** 2026-01-20 19:20 EST
