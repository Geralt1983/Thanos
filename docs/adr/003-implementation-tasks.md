# ADR-003: Thanos v2.0 Implementation Tasks

**Date:** 2026-01-20
**Status:** Active Execution
**Related:** ADR-002 (Technical Roadmap)

## Overview

This document provides the concrete, actionable task breakdown for implementing Thanos v2.0. Tasks are organized by phase with clear dependencies, assignees, and acceptance criteria.

## Phase 1: Core Infrastructure (Estimated: 12-16 hours)

### Task 1.1: Create Directory Structure
**Assigned:** Shell Developer
**Priority:** Critical
**Dependencies:** None
**Estimated Time:** 30 minutes

**Actions:**
```bash
mkdir -p .claude/skills/{task-router,health-insight,orchestrator}
mkdir -p .claude/hooks/{pre-tool-use,post-tool-use}
mkdir -p Shell/lib
mkdir -p Operator/{monitors,alerters,LaunchAgent}
mkdir -p Access/LaunchAgent
mkdir -p docs/adr
```

**Acceptance Criteria:**
- All directories created
- Project structure matches roadmap specification
- Git ignores appropriate files (.thanos/, logs/)

---

### Task 1.2: Implement Classification Hook
**Assigned:** Python Backend Developer
**Priority:** Critical
**Dependencies:** Task 1.1
**Estimated Time:** 2 hours

**File:** `.claude/hooks/pre-tool-use/classify_input.py`

**Implementation Checklist:**
- [ ] Implement classify_input() function with regex patterns
- [ ] Add patterns for: thinking, venting, observation, question, task
- [ ] Handle edge cases (empty input, mixed signals)
- [ ] Add logging for classification decisions
- [ ] Create test suite with 20+ examples
- [ ] Document pattern matching logic

**Test Cases:**
```python
# Test thinking
assert classify_input("I'm wondering if I should switch frameworks") == "thinking"

# Test venting
assert classify_input("I'm so frustrated with this bug") == "venting"

# Test observation
assert classify_input("I noticed the API is slow") == "observation"

# Test question
assert classify_input("What's on my calendar?") == "question"

# Test task (must be explicit)
assert classify_input("Add a task to review Q4 planning") == "task"
assert classify_input("Can you help me plan my morning") == "task"

# Test default (should not auto-create tasks)
assert classify_input("thinking about dinner") == "thinking"
```

**Acceptance Criteria:**
- All test cases pass
- False positive rate < 5% (casual thoughts → tasks)
- False negative rate < 2% (real tasks missed)
- Executable as standalone script
- Returns classification to stdout for hook integration

---

### Task 1.3: Build TaskRouter Skill
**Assigned:** Python Backend Developer
**Priority:** Critical
**Dependencies:** Task 1.2
**Estimated Time:** 3 hours

**Files:**
- `.claude/skills/task-router/skill.yaml`
- `.claude/skills/task-router/workflow.py`

**Implementation Checklist:**
- [ ] Create skill.yaml with USE_WHEN triggers
- [ ] Implement workflow.py with parse_intent()
- [ ] Integrate WorkOS MCP tools (get_tasks, create_task, complete_task, promote_task)
- [ ] Add energy check before complex tasks
- [ ] Implement priority shift detection
- [ ] Add Thanos voice response templating
- [ ] Create comprehensive test suite

**Workflow Logic:**
```python
def execute_task_operation(user_input: str, energy_level: str) -> dict:
    """
    Main workflow execution.

    Returns:
        {
            'success': bool,
            'action': str,  # create|complete|review|promote
            'response': str,  # Thanos voice response
            'priority_shift': bool,
            'updated_focus': list  # if priority shift detected
        }
    """
    # 1. Parse intent
    intent = parse_intent(user_input)

    # 2. Check energy gating
    if energy_level == 'low' and intent['complexity'] == 'high':
        return gate_complex_task(intent)

    # 3. Execute via WorkOS MCP
    result = execute_workos_operation(intent)

    # 4. Check for priority shift
    if detect_priority_shift(user_input, result):
        update_current_focus()

    # 5. Format response
    response = format_thanos_response(intent, result)

    return result
```

**Acceptance Criteria:**
- Skill correctly routes task operations (create/complete/review/promote)
- Energy gating blocks high-complexity tasks when energy < 60
- Priority shifts detected and CurrentFocus.md updated
- Responses use Thanos voice templates
- All WorkOS MCP tools integrated correctly
- Test coverage > 90%

---

### Task 1.4: Build HealthInsight Skill
**Assigned:** Python Backend Developer
**Priority:** High
**Dependencies:** Task 1.2
**Estimated Time:** 2 hours

**Files:**
- `.claude/skills/health-insight/skill.yaml`
- `.claude/skills/health-insight/workflow.py`

**Implementation Checklist:**
- [ ] Create skill.yaml with health-related triggers
- [ ] Implement Oura MCP integration (get_daily_readiness, get_daily_sleep)
- [ ] Calculate health snapshot (readiness, sleep, activity)
- [ ] Map readiness to energy level (>85=high, 70-84=medium, <70=low)
- [ ] Fetch energy-appropriate tasks from WorkOS
- [ ] Format health brief in Thanos voice
- [ ] Add morning brief workflow

**Health Snapshot Logic:**
```python
def get_health_snapshot() -> dict:
    """
    Fetch Oura data and calculate health snapshot.

    Returns:
        {
            'readiness': int,      # 0-100
            'sleep_score': int,    # 0-100
            'activity': dict,
            'energy_level': str,   # low|medium|high
            'suggested_tasks': list
        }
    """
    today = datetime.now().strftime('%Y-%m-%d')

    # Fetch Oura data
    readiness = oura_mcp.get_daily_readiness(today, today)
    sleep = oura_mcp.get_daily_sleep(today, today)

    # Calculate energy level
    score = readiness[0]['score'] if readiness else 0
    energy = map_readiness_to_energy(score)

    # Get appropriate tasks
    tasks = get_energy_appropriate_tasks(energy)

    return {
        'readiness': score,
        'sleep_score': sleep[0]['score'] if sleep else 0,
        'energy_level': energy,
        'suggested_tasks': tasks
    }
```

**Acceptance Criteria:**
- Oura data fetched correctly
- Energy mapping accurate (readiness score → low/medium/high)
- Task suggestions match energy level
- Morning brief includes health snapshot + top 3 tasks
- Thanos voice responses implemented
- Handles missing Oura data gracefully

---

### Task 1.5: Implement Dynamic Priority Hook
**Assigned:** Python Backend Developer
**Priority:** High
**Dependencies:** Task 1.3
**Estimated Time:** 1.5 hours

**File:** `.claude/hooks/post-tool-use/dynamic_priority.py`

**Implementation Checklist:**
- [ ] Implement priority shift detection
- [ ] Parse tool use context for priority indicators
- [ ] Update State/CurrentFocus.md automatically
- [ ] Preserve file structure and formatting
- [ ] Add logging for priority updates
- [ ] Create rollback mechanism if update fails

**Priority Shift Triggers:**
- User explicitly states new priority ("top priority this week")
- High-value task completed (milestone/deliverable)
- User reprioritizes in conversation ("more urgent than X")
- New commitment added with high importance

**Logic:**
```python
def detect_priority_shift(tool_use_context: dict) -> bool:
    """
    Detect if conversation involves priority shift.

    Args:
        tool_use_context: {
            'tool': str,
            'args': dict,
            'user_message': str,
            'assistant_response': str
        }

    Returns:
        bool: True if priority shift detected
    """
    indicators = [
        r"top priority",
        r"more important than",
        r"focus on.*instead",
        r"switch to",
        r"highest priority",
    ]

    message = tool_use_context['user_message'].lower()

    for pattern in indicators:
        if re.search(pattern, message):
            return True

    return False

def update_current_focus(new_priorities: list):
    """
    Update State/CurrentFocus.md with new priorities.

    Args:
        new_priorities: List of priority items
    """
    focus_file = Path(__file__).parent.parent.parent.parent / 'State' / 'CurrentFocus.md'

    # Read current content
    content = focus_file.read_text()

    # Update priorities section
    updated = update_priorities_section(content, new_priorities)

    # Write back
    focus_file.write_text(updated)

    # Log update
    logger.info(f"Updated priorities: {new_priorities}")
```

**Acceptance Criteria:**
- Priority shifts detected accurately
- CurrentFocus.md updated without breaking structure
- Preserves other sections (Current Project, Sprint, Notes)
- Logging captures all updates
- No false positives on casual priority mentions
- Test coverage > 85%

---

### Task 1.6: Memory Architecture Migration
**Assigned:** Integration Specialist
**Priority:** High
**Dependencies:** Task 1.1
**Estimated Time:** 4 hours

**Actions:**
1. Export existing observations from claude-mem ChromaDB
2. Initialize Thanos MemoryService
3. Import observations into Thanos Memory (State/memory.db + ChromaDB)
4. Build MCP server wrapper for MemoryService
5. Update .claude/settings.json to use new MCP tools
6. Test search/retrieval equivalence
7. Disable claude-mem worker service

**Migration Script:**
```python
#!/usr/bin/env python3
"""
Migrate observations from claude-mem to Thanos Memory.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from Tools.memory.service import MemoryService
import chromadb

def export_claude_mem_observations():
    """Export observations from claude-mem ChromaDB."""
    client = chromadb.PersistentClient(
        path=str(Path.home() / '.claude' / 'Memory' / 'vectors')
    )

    observations = []
    for collection_name in client.list_collections():
        collection = client.get_collection(collection_name.name)
        results = collection.get()

        for i, doc in enumerate(results['documents']):
            observations.append({
                'content': doc,
                'metadata': results['metadatas'][i],
                'collection': collection_name.name
            })

    return observations

def import_to_thanos_memory(observations: list):
    """Import observations into Thanos Memory."""
    memory = MemoryService()

    for obs in observations:
        memory.capture_activity(
            content=obs['content'],
            activity_type=obs['collection'],
            metadata=obs['metadata']
        )

    print(f"Migrated {len(observations)} observations")

if __name__ == '__main__':
    print("Exporting from claude-mem...")
    observations = export_claude_mem_observations()

    print(f"Found {len(observations)} observations")

    print("Importing to Thanos Memory...")
    import_to_thanos_memory(observations)

    print("Migration complete!")
```

**Acceptance Criteria:**
- All observations migrated without data loss
- Search results match before/after migration
- MemoryService MCP tools functional
- claude-mem worker service disabled
- Backup created before migration
- Rollback tested and documented

---

### Task 1.7: Phase 1 Integration Testing
**Assigned:** QA Validator
**Priority:** Critical
**Dependencies:** Tasks 1.2-1.6
**Estimated Time:** 2 hours

**Test Scenarios:**
1. **Classification Gate:**
   - Submit thinking/venting/observation → No task created
   - Submit explicit task request → Task created
   - Submit question → Direct response, no task

2. **TaskRouter Skill:**
   - Create task with low energy → Gated, alternatives suggested
   - Create task with high energy → Executed successfully
   - Complete task → Marked complete in WorkOS
   - Priority shift detected → CurrentFocus.md updated

3. **HealthInsight Skill:**
   - Morning brief request → Health snapshot + task suggestions
   - Health query → Oura data fetched and formatted
   - Missing Oura data → Graceful fallback

4. **Memory Migration:**
   - Search query → Results match claude-mem
   - Timeline query → Context retrieved correctly
   - Observation fetch → Full details returned

**Acceptance Criteria:**
- All test scenarios pass
- No regressions in existing functionality
- Error handling tested and robust
- Performance acceptable (<2s for most operations)
- Documentation updated with test results

---

## Phase 2: Shell Identity (Estimated: 10-14 hours)

### Task 2.1: Implement Voice Synthesis
**Assigned:** Python Backend Developer
**Priority:** High
**Dependencies:** Phase 1 complete
**Estimated Time:** 3 hours

**File:** `Shell/lib/voice.py`

**Implementation Checklist:**
- [ ] ElevenLabs API integration
- [ ] Audio caching with MD5 hash keys
- [ ] Async synthesis for non-blocking
- [ ] Playback via afplay (macOS)
- [ ] Error handling for API failures
- [ ] Quota tracking to prevent overages

**Voice Configuration:**
```python
VOICE_SETTINGS = {
    'stability': 0.75,        # Consistent delivery
    'similarity_boost': 0.85,  # Match voice clone
    'style': 0.5,             # Neutral style
    'use_speaker_boost': True
}
```

**Acceptance Criteria:**
- Voice synthesis works with custom Thanos voice
- Caching reduces API calls by >80%
- Synthesis latency <5s uncached, <0.5s cached
- Graceful degradation to text-only on API failure
- Quota tracking prevents unexpected charges

---

### Task 2.2: Implement Visual State Management
**Assigned:** Shell Developer
**Priority:** High
**Dependencies:** Phase 1 complete
**Estimated Time:** 2 hours

**File:** `Shell/lib/visuals.py`

**Implementation Checklist:**
- [ ] Kitty image protocol integration
- [ ] State enumeration (CHAOS, FOCUS, BALANCE)
- [ ] Wallpaper management
- [ ] Auto-transition logic
- [ ] Fallback for non-Kitty terminals

**State Transition Rules:**
```python
TRANSITION_RULES = {
    'CHAOS': {
        'triggers': [
            'time_of_day == morning',
            'inbox > 0',
            'tasks_unsorted > 5'
        ]
    },
    'FOCUS': {
        'triggers': [
            'cognitive_load == high',
            'deep_work_session_started'
        ]
    },
    'BALANCE': {
        'triggers': [
            'daily_goal_achieved',
            'snap_completed',
            'time_of_day == evening AND inbox == 0'
        ]
    }
}
```

**Acceptance Criteria:**
- Kitty wallpaper changes correctly for each state
- Auto-transitions triggered by context
- Graceful degradation to text-only mode
- Wallpapers downloaded/created
- Terminal detection works correctly

---

### Task 2.3: Build Notification System
**Assigned:** Python Backend Developer
**Priority:** Medium
**Dependencies:** Task 2.1
**Estimated Time:** 2 hours

**File:** `Shell/lib/notifications.py`

**Implementation Checklist:**
- [ ] macOS Notification Center integration
- [ ] Telegram bot API integration
- [ ] Notification priority routing
- [ ] Rich notifications with actions
- [ ] Notification history tracking

**Notification Channels:**
```python
class NotificationRouter:
    """Route notifications based on priority."""

    ROUTING = {
        'critical': ['notification_center', 'telegram', 'voice'],
        'warning': ['notification_center', 'telegram'],
        'info': ['notification_center'],
        'debug': []  # Log only
    }

    def send(self, notification: dict):
        """Send notification via appropriate channels."""
        priority = notification.get('priority', 'info')

        for channel in self.ROUTING[priority]:
            self._send_via_channel(channel, notification)
```

**Acceptance Criteria:**
- macOS notifications display correctly
- Telegram messages deliver
- Priority routing works
- Actions in notifications functional
- Notification history persisted

---

### Task 2.4: Build Shell Wrapper CLI
**Assigned:** Shell Developer
**Priority:** Critical
**Dependencies:** Tasks 2.1-2.3, Task 1.2 (classification)
**Estimated Time:** 3 hours

**File:** `Shell/thanos-cli`

**Implementation Checklist:**
- [ ] Classification gate integration
- [ ] Routing logic (task/question/thinking/venting/observation)
- [ ] Voice synthesis integration
- [ ] Visual state integration
- [ ] Error handling and logging
- [ ] Help/version flags

**CLI Structure:**
```bash
#!/bin/bash
# Thanos CLI - Main entry point

set -euo pipefail

# 1. Classify input
CLASSIFICATION=$(python3 .claude/hooks/pre-tool-use/classify_input.py "$*")

# 2. Route based on classification
case "$CLASSIFICATION" in
    task)
        # Execute via Claude with TaskRouter skill
        claude "$*"
        # Synthesize response
        python3 Shell/lib/voice.py synthesize "Task acknowledged."
        ;;

    question)
        claude "$*"
        ;;

    thinking)
        echo "### THANOS // $(date +"%H:%M")"
        echo "You contemplate the path ahead. The universe listens."
        echo "Would you like me to capture this thought?"
        ;;

    venting)
        echo "### THANOS // $(date +"%H:%M")"
        echo "Exhaustion is a chemical reaction. It is irrelevant to the objective."
        python3 Shell/lib/voice.py synthesize "But I acknowledge your struggle."
        ;;

    observation)
        echo "### THANOS // $(date +"%H:%M")"
        echo "The universe notes your observation."
        echo "Should I remember this?"
        ;;
esac
```

**Acceptance Criteria:**
- Classification routing works correctly
- Voice synthesis triggered appropriately
- Visual state updates automatically
- Help and version flags functional
- Executable from PATH
- Error messages clear and actionable

---

### Task 2.5: Create Wallpaper Assets
**Assigned:** QA Validator
**Priority:** Low
**Dependencies:** Task 2.2
**Estimated Time:** 1 hour

**Actions:**
1. Source or create 3 wallpapers:
   - `nebula_storm.png` - Purple/blue chaos, swirling energy
   - `infinity_gauntlet_fist.png` - Glowing stones, power focus
   - `farm_sunrise.png` - Peaceful farmland at sunrise

2. Optimize for terminal display (1920x1080 recommended)
3. Install to `~/.thanos/wallpapers/`
4. Test visual quality in Kitty terminal

**Acceptance Criteria:**
- All 3 wallpapers created/sourced
- Optimized file sizes (<500KB each)
- Visual quality good in Kitty
- Correctly represent CHAOS/FOCUS/BALANCE states

---

### Task 2.6: Phase 2 Integration Testing
**Assigned:** QA Validator
**Priority:** Critical
**Dependencies:** Tasks 2.1-2.5
**Estimated Time:** 2 hours

**Test Scenarios:**
1. **Voice Synthesis:**
   - First call → API request, audio cached
   - Second call → Cache hit, instant playback
   - API failure → Graceful text-only fallback

2. **Visual States:**
   - Morning with inbox > 0 → CHAOS wallpaper
   - Start deep work task → FOCUS wallpaper
   - Complete daily goal → BALANCE wallpaper

3. **Shell Wrapper:**
   - Input "I'm frustrated" → Venting response, no task
   - Input "Add task to review code" → Task created
   - Input "What's my readiness?" → HealthInsight skill

4. **Notifications:**
   - Critical alert → All channels (notification + Telegram + voice)
   - Warning → notification + Telegram
   - Info → notification only

**Acceptance Criteria:**
- All test scenarios pass
- Voice/visuals enhance experience (subjective but measurable via user feedback)
- No regressions from Phase 1
- Shell wrapper is primary interface (old thanos.py deprecated)

---

## Phase 3: Operator Daemon (Estimated: 12-16 hours)

### Task 3.1: Implement Daemon Core
**Assigned:** Python Backend Developer
**Priority:** Critical
**Dependencies:** Phase 2 complete
**Estimated Time:** 4 hours

**File:** `Operator/daemon.py`

**Implementation Checklist:**
- [ ] Main event loop with tick() cycle
- [ ] Signal handling (SIGTERM, SIGINT)
- [ ] Graceful shutdown
- [ ] Logging infrastructure
- [ ] Configuration loading from YAML
- [ ] Monitor orchestration
- [ ] Alerter orchestration

**Daemon Structure:**
```python
class OperatorDaemon:
    def __init__(self, config_path: Path):
        self.config = load_config(config_path)
        self.monitors = self._init_monitors()
        self.alerters = self._init_alerters()
        self.running = False

    def start(self):
        """Start daemon loop."""
        signal.signal(signal.SIGTERM, self._shutdown_handler)
        signal.signal(signal.SIGINT, self._shutdown_handler)

        logger.info("Operator daemon starting...")
        self.running = True

        try:
            while self.running:
                self.tick()
                time.sleep(self.config['tick_interval'])
        except Exception as e:
            logger.exception("Daemon crashed")
            raise

    def tick(self):
        """Execute one monitoring cycle."""
        for monitor in self.monitors.values():
            try:
                alerts = monitor.check()
                for alert in alerts:
                    self.send_alert(alert)
            except Exception as e:
                logger.error(f"Monitor {monitor.__class__.__name__} failed: {e}")

    def _shutdown_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
```

**Acceptance Criteria:**
- Daemon starts and runs continuously
- Tick cycle executes at configured interval
- Graceful shutdown on SIGTERM/SIGINT
- Logging to file and stdout
- Configuration loaded from YAML
- All errors logged and handled

---

### Task 3.2: Implement Health Monitor
**Assigned:** Python Backend Developer
**Priority:** High
**Dependencies:** Task 3.1
**Estimated Time:** 2.5 hours

**File:** `Operator/monitors/health.py`

**Implementation Checklist:**
- [ ] Oura MCP integration
- [ ] Readiness score checking
- [ ] Low readiness alert generation
- [ ] Sync failure detection
- [ ] HRV trend monitoring (future)

**Monitor Logic:**
```python
class HealthMonitor:
    def __init__(self, config: dict):
        self.config = config
        self.oura_mcp = MCPClient('oura-mcp')
        self.last_check = None

    def check(self) -> List[Dict[str, Any]]:
        """Check health metrics and return alerts."""
        alerts = []

        # Get today's readiness
        today = datetime.now().strftime('%Y-%m-%d')

        try:
            readiness = self.oura_mcp.call('get_daily_readiness', {
                'startDate': today,
                'endDate': today
            })

            if readiness and len(readiness) > 0:
                score = readiness[0]['score']

                # Critical: <50
                if score < 50:
                    alerts.append(self._critical_low_readiness(score))

                # Warning: 50-65
                elif score < 65:
                    alerts.append(self._warning_low_readiness(score))

            self.last_check = datetime.now()

        except Exception as e:
            # Sync failure alert
            if self._sync_stale():
                alerts.append(self._sync_failure_alert(e))

        return alerts
```

**Acceptance Criteria:**
- Readiness scores fetched correctly
- Critical alerts (<50) generated
- Warning alerts (50-65) generated
- Sync failures detected
- Last check timestamp tracked

---

### Task 3.3: Implement Task Monitor
**Assigned:** Python Backend Developer
**Priority:** High
**Dependencies:** Task 3.1
**Estimated Time:** 2.5 hours

**File:** `Operator/monitors/tasks.py`

**Implementation Checklist:**
- [ ] WorkOS MCP integration
- [ ] Overdue milestone detection
- [ ] Missed habit tracking
- [ ] Stalled task alerts
- [ ] Daily goal progress monitoring

**Monitor Logic:**
```python
class TaskMonitor:
    def __init__(self, config: dict):
        self.config = config
        self.workos_mcp = MCPClient('workos-mcp')

    def check(self) -> List[Dict[str, Any]]:
        """Monitor tasks and habits."""
        alerts = []

        # Check for stalled milestones
        tasks = self.workos_mcp.call('workos_get_tasks', {'status': 'active'})

        for task in tasks:
            if task['valueTier'] == 'milestone':
                age_days = self._task_age_days(task)

                if age_days > 3:
                    alerts.append({
                        'type': 'task',
                        'severity': 'warning',
                        'title': 'Milestone Stalled',
                        'message': f"'{task['title']}' active for {age_days} days. The work does not wait.",
                        'data': {'task': task}
                    })

        # Check missed habits
        habits = self.workos_mcp.call('life_habit_checkin', {'timeOfDay': 'all'})
        overdue = sum(1 for h in habits if not h.get('completed_today'))

        if overdue > 3:
            alerts.append({
                'type': 'habits',
                'severity': 'warning',
                'title': 'Habits Falling Behind',
                'message': f'{overdue} habits incomplete. Small disciplines prevent great failures.',
                'data': {'overdue_count': overdue}
            })

        return alerts
```

**Acceptance Criteria:**
- Stalled milestone alerts generated
- Habit tracking working
- Daily goal progress monitored
- WorkOS integration functional

---

### Task 3.4: Implement Pattern Monitor
**Assigned:** Python Backend Developer
**Priority:** Medium
**Dependencies:** Task 3.1
**Estimated Time:** 2 hours

**File:** `Operator/monitors/patterns.py`

**Implementation Checklist:**
- [ ] Brain dump frequency tracking
- [ ] Task creation/completion ratio
- [ ] Energy level trends
- [ ] Unusual behavior detection
- [ ] Pattern baseline learning

**Acceptance Criteria:**
- Patterns tracked over time
- Unusual behavior detected
- Baseline learned from historical data
- Alerts generated for anomalies

---

### Task 3.5: Implement Telegram Alerter
**Assigned:** Python Backend Developer
**Priority:** High
**Dependencies:** Task 3.1
**Estimated Time:** 1.5 hours

**File:** `Operator/alerters/telegram.py`

**Implementation Checklist:**
- [ ] Telegram Bot API integration
- [ ] Message formatting
- [ ] Rich formatting (bold, code blocks)
- [ ] Rate limiting
- [ ] Error retry logic

**Acceptance Criteria:**
- Messages delivered to Telegram
- Formatting correct
- Rate limiting prevents spam
- Retry on transient failures

---

### Task 3.6: Configure LaunchAgent
**Assigned:** Shell Developer
**Priority:** High
**Dependencies:** Tasks 3.1-3.5
**Estimated Time:** 1 hour

**File:** `Operator/LaunchAgent/com.thanos.operator.plist`

**Implementation:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.thanos.operator</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/jeremy/Projects/Thanos/Operator/daemon.py</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>

    <key>StandardOutPath</key>
    <string>/Users/jeremy/Projects/Thanos/logs/operator-stdout.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/jeremy/Projects/Thanos/logs/operator-stderr.log</string>

    <key>WorkingDirectory</key>
    <string>/Users/jeremy/Projects/Thanos</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
```

**Installation:**
```bash
cp Operator/LaunchAgent/com.thanos.operator.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.thanos.operator.plist
```

**Acceptance Criteria:**
- LaunchAgent plist created
- Daemon starts on login
- Automatic restart on crash
- Logs written to correct location
- Environment variables set correctly

---

### Task 3.7: Phase 3 Integration Testing
**Assigned:** QA Validator
**Priority:** Critical
**Dependencies:** Tasks 3.1-3.6
**Estimated Time:** 2 hours

**Test Scenarios:**
1. **Daemon Stability:**
   - Start daemon → Runs continuously for 1 hour
   - Kill daemon → LaunchAgent restarts within 60s
   - Send SIGTERM → Graceful shutdown

2. **Health Monitoring:**
   - Simulate low readiness (<50) → Critical alert sent
   - Simulate missing Oura data → Sync failure alert
   - Normal readiness (>75) → No alerts

3. **Task Monitoring:**
   - Create milestone task → Monitor it
   - Wait 3 days → Stalled alert generated
   - Miss 4 habits → Habits alert generated

4. **Alerting:**
   - Critical alert → Telegram + notification
   - Warning → Telegram + notification
   - Info → Log only

**Acceptance Criteria:**
- Daemon runs stably for 24+ hours
- All monitors functional
- Alerts delivered correctly
- LaunchAgent auto-restart works
- No memory leaks or CPU spikes

---

## Phase 4: Ubiquitous Access (Estimated: 8-12 hours)

### Task 4.1: Create Tmux Session Manager
**Assigned:** Shell Developer
**Priority:** High
**Dependencies:** Phase 3 complete
**Estimated Time:** 2 hours

**File:** `Access/thanos-session.sh`

**Implementation Checklist:**
- [ ] Session creation logic
- [ ] Session attachment logic
- [ ] 3-window layout (main, logs, state)
- [ ] Window initialization commands
- [ ] Session persistence

**Acceptance Criteria:**
- Tmux session creates with 3 windows
- Attaches to existing session if present
- Windows initialized with correct commands
- Sessions persist across terminal closes

---

### Task 4.2: Create Web Terminal Server
**Assigned:** Shell Developer
**Priority:** High
**Dependencies:** Task 4.1
**Estimated Time:** 2 hours

**File:** `Access/ttyd-server.sh`

**Implementation Checklist:**
- [ ] ttyd installation check
- [ ] Credential generation
- [ ] Server startup script
- [ ] Client options (font, theme)
- [ ] Attach to tmux session

**Acceptance Criteria:**
- ttyd server starts correctly
- Credentials generated securely
- Web interface loads and connects
- Tmux session accessible via web
- Styling matches terminal theme

---

### Task 4.3: Configure Tailscale Funnel
**Assigned:** Integration Specialist
**Priority:** High
**Dependencies:** Task 4.2
**Estimated Time:** 1 hour

**Actions:**
1. Install Tailscale on system
2. Enable Funnel feature
3. Configure HTTPS mapping (443 → 7681)
4. Test remote access from phone/tablet
5. Configure ACLs for security

**Commands:**
```bash
# Enable Tailscale Funnel
tailscale funnel --bg --https=443 7681

# Test access
# From any Tailscale device:
# https://<machine-name>.<tailnet>.ts.net
```

**Acceptance Criteria:**
- Tailscale installed and authenticated
- Funnel enabled and routing correctly
- HTTPS access works from remote devices
- ACLs restrict access appropriately
- Credentials required for terminal access

---

### Task 4.4: Create ttyd LaunchAgent
**Assigned:** Shell Developer
**Priority:** Medium
**Dependencies:** Task 4.2
**Estimated Time:** 1 hour

**File:** `Access/LaunchAgent/com.thanos.ttyd.plist`

**Implementation:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.thanos.ttyd</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/jeremy/Projects/Thanos/Access/ttyd-server.sh</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>WorkingDirectory</key>
    <string>/Users/jeremy/Projects/Thanos</string>
</dict>
</plist>
```

**Acceptance Criteria:**
- LaunchAgent plist created
- ttyd starts on login
- Auto-restart on crash
- Accessible via Tailscale Funnel

---

### Task 4.5: Phase 4 Integration Testing
**Assigned:** QA Validator
**Priority:** Critical
**Dependencies:** Tasks 4.1-4.4
**Estimated Time:** 2 hours

**Test Scenarios:**
1. **Tmux Sessions:**
   - Create new session → 3 windows present
   - Detach and reattach → State preserved
   - Close terminal → Session persists

2. **Web Terminal:**
   - Access via HTTPS → ttyd loads
   - Enter credentials → Terminal accessible
   - Execute commands → Works correctly

3. **Remote Access:**
   - Access from phone → Terminal usable
   - Access from tablet → Terminal usable
   - Access from different network → Works via Tailscale

4. **Security:**
   - No credentials → Access denied
   - Wrong credentials → Access denied
   - Correct credentials → Access granted

**Acceptance Criteria:**
- All access methods functional
- Security working correctly
- Performance acceptable (<500ms latency)
- Mobile experience usable

---

## Phase 5: Integration & Deployment (Estimated: 8-12 hours)

### Task 5.1: End-to-End Integration Testing
**Assigned:** QA Validator + Integration Specialist
**Priority:** Critical
**Dependencies:** Phases 1-4 complete
**Estimated Time:** 4 hours

**Test Workflows:**

1. **Morning Routine:**
   ```
   User: Good morning
   → HealthInsight skill activated
   → Oura data fetched
   → Health snapshot displayed
   → Energy-appropriate tasks suggested
   → Visual state → CHAOS (if inbox > 0)
   ```

2. **Task Management:**
   ```
   User: Add a task to review Q4 planning
   → Classification: task
   → TaskRouter skill activated
   → Energy check (if low, suggest alternatives)
   → Task created in WorkOS
   → Priority shift detected? → Update CurrentFocus.md
   → Voice confirmation
   ```

3. **Deep Work Session:**
   ```
   User: Starting deep work on architecture design
   → Operator detects high cognitive load
   → Visual state → FOCUS
   → Notifications silenced
   → After 2 hours: break reminder via voice
   ```

4. **Low Energy Detection:**
   ```
   Operator: Oura readiness = 45 (critical)
   → Telegram alert sent
   → macOS notification
   → Voice alert (if enabled)
   → User opens Thanos
   → Suggested tasks filtered to low-cognitive only
   ```

5. **Daily Goal Completion:**
   ```
   User: Complete last task
   → TaskRouter marks complete
   → Daily goal achieved (18/18 points)
   → Visual state → BALANCE
   → Voice: "The Snap is complete. Rest now."
   → Wallpaper: farm_sunrise.png
   ```

6. **Remote Access:**
   ```
   User on phone → Opens Tailscale
   → Navigate to https://thanos.<tailnet>.ts.net
   → Enter credentials
   → Web terminal loads
   → Tmux session accessible
   → Execute: thanos "What's my readiness?"
   → HealthInsight responds
   ```

**Acceptance Criteria:**
- All workflows complete successfully
- No errors or crashes
- Performance acceptable throughout
- User experience coherent and smooth

---

### Task 5.2: Performance Optimization
**Assigned:** Integration Specialist
**Priority:** High
**Dependencies:** Task 5.1
**Estimated Time:** 3 hours

**Optimization Targets:**
- Classification latency < 100ms
- Skill execution < 2s
- Voice synthesis < 5s (uncached)
- Visual state transition < 500ms
- Operator tick cycle < 30s
- Memory search < 1s

**Actions:**
1. Profile critical paths
2. Optimize database queries
3. Implement caching where appropriate
4. Reduce unnecessary API calls
5. Parallelize independent operations

**Acceptance Criteria:**
- All performance targets met
- No user-facing latency issues
- Resource usage reasonable (CPU < 10%, RAM < 500MB)

---

### Task 5.3: Documentation Updates
**Assigned:** Integration Specialist
**Priority:** Medium
**Dependencies:** Task 5.1
**Estimated Time:** 2 hours

**Documents to Create/Update:**
1. README.md - Overview of Thanos v2.0
2. Installation guide
3. Configuration guide
4. Troubleshooting guide
5. Skill development guide
6. Architecture diagrams

**Acceptance Criteria:**
- Documentation complete and accurate
- Installation guide tested on clean system
- Troubleshooting covers common issues
- Examples provided for customization

---

### Task 5.4: Migration from v1 to v2
**Assigned:** Integration Specialist
**Priority:** Critical
**Dependencies:** Tasks 5.1-5.3
**Estimated Time:** 3 hours

**Migration Steps:**
1. **Backup:**
   - Full backup of State/
   - Backup of current thanos.py
   - Backup of .claude/settings.json

2. **Gradual Rollout:**
   - Install v2 alongside v1
   - Create alias: `thanos2` → Shell/thanos-cli
   - Test for 1 week with v2
   - Switch primary alias after validation

3. **Cutover:**
   - Update PATH to use Shell/thanos-cli
   - Deprecate old thanos.py
   - Update session-start hooks

4. **Rollback Plan:**
   - Keep v1 backup for 30 days
   - Documented rollback procedure
   - Quick switch command

**Acceptance Criteria:**
- Backup complete and verified
- Migration tested without data loss
- Rollback procedure documented and tested
- User can switch between v1/v2 during transition

---

## Success Metrics

### Technical Metrics
- [ ] Classification accuracy > 95%
- [ ] Skill execution success rate > 98%
- [ ] Daemon uptime > 99.5%
- [ ] Voice synthesis cache hit rate > 80%
- [ ] Remote access latency < 500ms
- [ ] Memory migration 100% data preservation

### Functional Metrics
- [ ] Zero accidental task creations from casual thoughts
- [ ] Energy-aware routing matches user capacity
- [ ] Visual/voice feedback enhances experience
- [ ] Operator catches issues before user impact
- [ ] Remote access used weekly
- [ ] CurrentFocus.md stays current

### User Experience Metrics
- [ ] User can articulate classification types
- [ ] Response style consistently Thanos persona
- [ ] Morning routine streamlined
- [ ] Deep work sessions uninterrupted
- [ ] Low energy days properly supported

---

## Timeline Summary

| Phase | Duration | Tasks | Completion Criteria |
|-------|----------|-------|---------------------|
| Phase 1: Core Infrastructure | 2-3 days | 7 tasks | Classification working, skills functional, memory migrated |
| Phase 2: Shell Identity | 2-3 days | 6 tasks | Voice/visuals working, shell wrapper primary interface |
| Phase 3: Operator Daemon | 2-3 days | 7 tasks | Daemon stable, monitors alerting, LaunchAgent configured |
| Phase 4: Ubiquitous Access | 1-2 days | 5 tasks | Remote access functional, tmux/ttyd/Tailscale integrated |
| Phase 5: Integration & Deployment | 2-3 days | 4 tasks | All workflows tested, documented, migrated |
| **Total** | **9-14 days** | **29 tasks** | Full v2.0 system operational |

---

## Next Actions

1. **Mark current task complete** - Decomposition finished
2. **Begin Phase 1 implementation** - Start with Task 1.1 (directory structure)
3. **Assign swarm agents to tasks** - Distribute work across specialists
4. **Set up progress tracking** - Update todo list as tasks complete

---

**Prepared By:** Hive Mind Swarm
- System Architect: Technical design
- Project Coordinator: Task breakdown and timeline
- Python Backend Developer: Implementation details
- Shell Developer: Shell scripting specifications
- QA Validator: Test scenarios and acceptance criteria
- Integration Specialist: Migration and deployment planning

**Swarm ID:** `swarm_1768954645922_fe0i4itw2`
**Completed:** 2026-01-20 19:21 EST
