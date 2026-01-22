# Thanos v2.0 - Integration Testing Strategy

**Document Owner:** Test Strategy Architect (Phase 5)
**Created:** 2026-01-20
**Last Updated:** 2026-01-20
**Status:** Active

---

## Executive Summary

This document defines the comprehensive integration testing strategy for Thanos v2.0, consolidating existing test results and providing a roadmap for remaining validation work. The strategy covers all integration points across Phases 1-4, defines test categories, frameworks, success criteria, and prioritizes critical paths.

### Current State

| Test Category | Coverage | Status | Gaps |
|--------------|----------|--------|------|
| **E2E Workflows** | 80% (12/14 integration points) | ✅ Validated | 2 points (daemon monitoring) |
| **Performance** | 100% (all local ops <15ms) | ✅ Validated | Network latency not measured |
| **Integration Points** | 85.7% (12/14) | ⚠️ Partial | Phase 3 ↔ 4 remote monitoring |
| **Automated Tests** | 0% | ❌ Missing | No test suite exists |

### Key Findings from Existing Results

**Strengths:**
- Core workflows (morning routine, task management) pass at 100%
- File I/O performance excellent (50K+ ops/sec)
- State persistence validated across sessions
- MCP coordination verified (WorkOS, Oura, Claude-Flow)

**Critical Gaps:**
- No automated test suite (0% coverage)
- Daemon remote monitoring not implemented (Phase 3 ↔ 4)
- Network MCP latency not benchmarked
- Concurrent load testing not performed

### Testing Goals

1. **Achieve 95% integration point validation** (14/14 validated)
2. **Create automated test suite** with 80% critical path coverage
3. **Establish performance baselines** for all MCP operations
4. **Validate production readiness** under realistic load conditions

---

## 1. Testing Scope

### 1.1 Phase Integration Points to Validate

#### Phase 1 ↔ Phase 3 (Command Router ↔ Health Monitor)

| Integration Point | Description | Current Status | Test Priority |
|------------------|-------------|----------------|---------------|
| Brain Dump → Classification | User input → BrainDumpProcessor | ✅ Validated | P1 |
| Classification → Energy Detection | Category → Cognitive load mapping | ✅ Validated | P1 |
| Energy Level → Task Gating | Oura readiness → Command routing | ✅ Validated | P0 |
| Operator Daemon → Alert Generation | Health check → Telegram notification | ✅ Validated | P1 |
| Classification → Task Prioritization | Brain dump → Daemon task queue | ⚠️ Partial | P2 |

#### Phase 1 ↔ Phase 4 (Command Router ↔ Access Layer)

| Integration Point | Description | Current Status | Test Priority |
|------------------|-------------|----------------|---------------|
| CLI → Access Coordinator | `thanos-access` command routing | ✅ Validated | P1 |
| Remote Access → Command Router | tmux/ttyd → Claude CLI | ✅ Validated | P1 |
| Mobile → Task Management | Telegram → WorkOS MCP | ✅ Validated | P0 |
| Session Hooks → State Persistence | Hook execution → TimeState updates | ✅ Validated | P1 |

#### Phase 3 ↔ Phase 4 (Health Monitor ↔ Access Layer)

| Integration Point | Description | Current Status | Test Priority |
|------------------|-------------|----------------|---------------|
| Daemon → Remote Monitoring | Alert status → Web interface | ❌ Missing | P0 |
| Health Alerts → Mobile Push | Operator → Telegram notifications | ✅ Validated | P1 |
| Daemon Control → CLI | Start/stop via `thanos-access` | ⚠️ Partial | P2 |

#### Cross-Phase Infrastructure

| Integration Point | Description | Current Status | Test Priority |
|------------------|-------------|----------------|---------------|
| MCP Server Coordination | WorkOS, Oura, Claude-Flow hooks | ✅ Validated | P0 |
| State File Persistence | JSON storage across sessions | ✅ Validated | P1 |
| Hook System Execution | SessionStart, UserPromptSubmit | ✅ Validated | P1 |
| Logging Infrastructure | Daemon, bot, operator logs | ✅ Validated | P2 |

**Priority Legend:**
- **P0:** Critical path, system fails without this
- **P1:** Core functionality, major degradation if broken
- **P2:** Enhancement, system works but less effectively

### 1.2 Critical User Workflows to Test

#### Workflow 1: Morning Startup (P0)

```
User launches thanos-claude
  ↓
SessionStart hook triggers
  ├─ thanos-start.sh displays banner
  ├─ TimeState reset
  └─ daily-brief.ts generates brief
      ├─ Reads State/CurrentFocus.md
      ├─ Queries Google Calendar
      └─ Fetches Oura readiness
  ↓
Daily brief displayed with context
Claude CLI launches with energy awareness
```

**Success Criteria:**
- Brief displays within 3 seconds
- Oura readiness fetched successfully
- TimeState updated with session start
- Energy level detected correctly

**Current Status:** ✅ 100% Pass (E2E test validated)

#### Workflow 2: Voice Brain Dump → Task Creation (P0)

```
User sends Telegram voice message
  "Fix login bug for Memphis by Friday"
  ↓
Telegram bot receives audio
  ├─ Downloads voice file
  ├─ Transcribes via Whisper API
  └─ Raw text extracted
  ↓
BrainDumpProcessor.process()
  ├─ Classifies as Category.TASK
  ├─ Domain: WORK (0.90 confidence)
  ├─ Extracts deadline: Friday
  ├─ Entities: ["Memphis"]
  └─ Energy hint: "medium"
  ↓
BrainDumpRouter.route()
  └─ workos_create_task()
  ↓
Task created in database
Telegram confirmation sent
```

**Success Criteria:**
- Voice transcription accuracy >95%
- Classification confidence >0.70
- Task created with correct metadata
- Response time <5 seconds

**Current Status:** ✅ Validated (components exist, integration confirmed)

#### Workflow 3: Alert Daemon → Mobile Notification (P1)

```
Cron triggers alert_daemon.py (every 15 min)
  ↓
AlertDaemon.run_once()
  ├─ TaskAlertChecker → overdue tasks
  ├─ OuraAlertChecker → low readiness
  ├─ HabitAlertChecker → streak breaks
  └─ CommitmentAlertChecker → due dates
  ↓
Generate Alert objects
Check deduplication cache
  ↓
_send_notification()
  ├─ Format with emoji
  ├─ Send via Telegram API
  └─ Log to journal
  ↓
User receives notification on mobile
```

**Success Criteria:**
- Alerts generated for overdue tasks
- Deduplication prevents spam (1 hour window)
- Telegram delivery <1 second
- Quiet hours respected (22:00-07:00)

**Current Status:** ✅ Validated (code exists, tested manually)

#### Workflow 4: Remote Access via Mobile (P1)

```
User opens mobile browser
  ↓
Navigate to Tailscale URL
  https://{hostname}:7681/
  ↓
VPN authenticates device
ttyd web terminal loads
  ↓
Connect to tmux session "thanos"
  ↓
thanos-claude wrapper executes
  ├─ Session hooks run
  ├─ Daily brief generated
  └─ Claude CLI ready
  ↓
User issues commands remotely
```

**Success Criteria:**
- VPN connection established <2 seconds
- Web terminal responsive (60 FPS)
- tmux session attaches successfully
- All commands work identically to local

**Current Status:** ⚠️ 90% Pass (live mobile connection not tested)

#### Workflow 5: Energy-Aware Task Routing (P1)

```
User asks "what should I work on?"
  ↓
System checks energy level
  ├─ Fetch Oura readiness score
  ├─ Check manual energy logs
  └─ Determine energy tier (high/medium/low)
  ↓
Filter tasks by cognitive load
  High energy → deep work (complex debugging)
  Medium energy → standard tasks (features)
  Low energy → admin work (documentation)
  ↓
workos_get_energy_aware_tasks()
  ├─ Rank by energy-task match
  └─ Suggest top 3 tasks
  ↓
Present recommendations to user
```

**Success Criteria:**
- Readiness score fetched successfully
- Task filtering matches energy level
- Recommendations relevant and actionable
- Response time <500ms

**Current Status:** ⚠️ 85% Pass (API exists, not live-tested)

### 1.3 System Boundaries and Interfaces

#### Internal Boundaries

```
┌─────────────────────────────────────────────────────────┐
│                    THANOS v2.0                          │
│                                                         │
│  ┌───────────┐    ┌──────────┐    ┌────────────┐      │
│  │  Phase 1  │───▶│ Phase 3  │───▶│  Phase 4   │      │
│  │  Router   │    │  Health  │    │   Access   │      │
│  └─────┬─────┘    └────┬─────┘    └─────┬──────┘      │
│        │               │                 │              │
│        └───────────────┴─────────────────┘              │
│                        │                                │
│                  State Layer                            │
│        ┌────────────────┴──────────────┐               │
│        │  TimeState  │  BrainDumps  │ Daemon           │
│        └───────────────────────────────┘               │
└─────────────────────────────────────────────────────────┘
```

**Test Scope:** All interactions between phases and shared state layer

#### External Interfaces

| Interface | Provider | Type | Test Approach |
|-----------|----------|------|---------------|
| **WorkOS MCP** | MCP Server | RPC/Tool Calls | Mock for unit tests, real for integration |
| **Oura MCP** | MCP Server | RPC/Tool Calls | Mock for unit tests, real for integration |
| **Google Calendar** | Google API | REST | Mock responses, rate limit testing |
| **Telegram Bot API** | Telegram | REST | Mock for unit tests, test bot for integration |
| **Whisper API** | OpenAI | REST | Mock for unit tests, sandbox API for integration |
| **Tailscale VPN** | Tailscale | Network | Manual testing only |

**Test Scope:** API contracts, error handling, rate limiting, timeout behavior

---

## 2. Test Categories

### 2.1 Unit Tests (Component-Level)

**Purpose:** Validate individual functions and classes in isolation

**Framework:** pytest

**Coverage Goal:** 80% of critical functions

#### Test Targets

**Phase 1: Command Router**
```python
# test_classification.py
def test_brain_dump_classification():
    """Verify brain dump categorization is accurate."""
    processor = BrainDumpProcessor()

    # Test task classification
    result = processor.process("Fix login bug for Memphis")
    assert result.category == BrainDumpCategory.TASK
    assert result.domain == TaskDomain.WORK
    assert result.confidence > 0.70

    # Test project classification
    result = processor.process("Build automated testing framework")
    assert result.category == BrainDumpCategory.PROJECT

    # Test worry classification
    result = processor.process("Worried about quarterly review")
    assert result.category == BrainDumpCategory.WORRY

def test_energy_hint_extraction():
    """Verify energy level detection from text."""
    processor = BrainDumpProcessor()

    # High energy indicators
    result = processor.process("Deep work session on complex architecture")
    assert result.energy_hint == "high"

    # Low energy indicators
    result = processor.process("Quick admin task - easy routine")
    assert result.energy_hint == "low"
```

**Phase 3: Health Monitor**
```python
# test_alert_generation.py
def test_task_alert_checker():
    """Verify overdue task alerts are generated."""
    checker = TaskAlertChecker()

    # Mock overdue task
    mock_task = Task(
        id=123,
        title="Fix bug",
        deadline=date.today() - timedelta(days=2),
        status="active"
    )

    alert = checker.check_task(mock_task)
    assert alert.priority == AlertPriority.HIGH
    assert "overdue" in alert.message.lower()

def test_deduplication_cache():
    """Verify alerts are not sent repeatedly."""
    daemon = AlertDaemon()

    alert = Alert(
        id="task-123-overdue",
        priority=AlertPriority.HIGH,
        title="Overdue task"
    )

    # First alert should be sent
    assert daemon._should_send_alert(alert) == True
    daemon._mark_alert_sent(alert)

    # Second alert within 1 hour should be blocked
    assert daemon._should_send_alert(alert) == False
```

**Phase 4: Access Layer**
```python
# test_access_coordinator.py
def test_tmux_session_management():
    """Verify tmux session lifecycle."""
    manager = TmuxManager()

    # Create session
    session = manager.ensure_session("thanos")
    assert session.name == "thanos"
    assert session.is_running()

    # Attach to existing
    session2 = manager.ensure_session("thanos")
    assert session2.id == session.id

def test_tailscale_connection():
    """Verify VPN status detection."""
    manager = TailscaleManager()

    status = manager.get_status()
    assert status.is_connected in [True, False]
    assert status.hostname is not None
```

**Shared Infrastructure**
```python
# test_state_persistence.py
def test_timestate_updates():
    """Verify TimeState persistence across operations."""
    tracker = TimeTracker()

    # Reset session
    tracker.reset_session()
    state = tracker.get_state()
    assert state.session_started is not None
    assert state.interaction_count_today == 0

    # Increment interaction
    tracker.increment_interaction()
    state = tracker.get_state()
    assert state.interaction_count_today == 1

def test_json_corruption_recovery():
    """Verify graceful handling of corrupted state files."""
    # Corrupt TimeState.json
    with open("State/TimeState.json", "w") as f:
        f.write("invalid json")

    # Should not crash, should rebuild
    tracker = TimeTracker()
    state = tracker.get_state()
    assert state.session_started is not None
```

**Estimated Effort:** 16 hours for 40+ unit tests

### 2.2 Integration Tests (Phase-to-Phase)

**Purpose:** Validate data flow between phases

**Framework:** pytest with real MCP servers (test environment)

**Coverage Goal:** 100% of integration points (14/14)

#### Test Targets

**Phase 1 → Phase 3 Integration**
```python
# test_phase1_phase3_integration.py
@pytest.mark.integration
async def test_brain_dump_to_alert_flow():
    """Test brain dump creates alert when needed."""
    # Create brain dump with deadline
    processor = BrainDumpProcessor()
    result = processor.process("Fix bug by tomorrow")

    # Route to task creation
    router = BrainDumpRouter()
    task_id = await router.route(result)

    # Wait 1 day (mock time)
    with mock_time(days=1):
        # Daemon should detect overdue task
        daemon = AlertDaemon()
        alerts = await daemon.run_once()

        assert len(alerts) > 0
        assert any(str(task_id) in alert.id for alert in alerts)

@pytest.mark.integration
async def test_energy_aware_routing():
    """Test Oura data influences task suggestions."""
    # Mock low readiness
    with mock_oura_readiness(score=55):
        # Request task suggestions
        tasks = await workos_get_energy_aware_tasks()

        # Should only return low-cognitive tasks
        for task in tasks:
            assert task.cognitiveLoad in ["low", "medium"]
```

**Phase 1 → Phase 4 Integration**
```python
# test_phase1_phase4_integration.py
@pytest.mark.integration
def test_remote_cli_access():
    """Test CLI commands work through remote access."""
    # Start access services
    coordinator = AccessCoordinator()
    coordinator.start_all_services()

    # Simulate remote connection
    with remote_session():
        # Execute thanos-cli command
        result = subprocess.run(
            ["thanos-cli", "status"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "readiness" in result.stdout.lower()

@pytest.mark.integration
async def test_telegram_to_task_creation():
    """Test Telegram voice message creates task in WorkOS."""
    bot = TelegramBrainDumpBot()

    # Simulate voice message
    mock_audio = create_mock_audio("Fix login for Memphis")

    # Process message
    task_id = await bot.process_voice_message(mock_audio)

    # Verify task in WorkOS
    task = await workos_get_task(task_id)
    assert task.title == "Fix login for Memphis"
    assert task.category == "work"
```

**Phase 3 → Phase 4 Integration**
```python
# test_phase3_phase4_integration.py
@pytest.mark.integration
async def test_daemon_status_remote_access():
    """Test daemon status accessible via remote interface."""
    # Start daemon
    daemon = AlertDaemon()
    await daemon.run_once()

    # Access via coordinator
    coordinator = AccessCoordinator()
    status = coordinator.get_daemon_status()

    assert status["last_run"] is not None
    assert status["run_count"] > 0
    assert len(status["enabled_checkers"]) > 0

@pytest.mark.integration
async def test_health_alert_mobile_delivery():
    """Test alert generated by daemon reaches mobile."""
    # Create critical alert condition
    with mock_oura_readiness(score=30):
        daemon = AlertDaemon()
        alerts = await daemon.run_once()

        # Verify Telegram notification sent
        telegram_spy = get_telegram_spy()
        assert telegram_spy.message_count > 0
        assert "🚨 CRITICAL" in telegram_spy.last_message
```

**Estimated Effort:** 20 hours for comprehensive integration test suite

### 2.3 End-to-End Tests (Full Workflows)

**Purpose:** Validate complete user journeys from start to finish

**Framework:** pytest with real external services (sandbox environment)

**Coverage Goal:** 5 critical workflows (100% coverage)

#### Test Scenarios

**E2E Test 1: Full Morning Routine**
```python
# test_e2e_workflows.py
@pytest.mark.e2e
async def test_morning_routine_full_workflow():
    """
    Test complete morning startup workflow:
    1. Session initialization
    2. Daily brief generation
    3. Task prioritization
    4. Energy-aware suggestions
    """
    # Start session
    session = start_thanos_session()

    # Verify hook execution
    assert os.path.exists("State/TimeState.json")

    # Verify daily brief
    brief = get_daily_brief()
    assert brief.readiness_score is not None
    assert brief.active_tasks > 0
    assert brief.habits_due is not None

    # Verify task suggestions match energy
    tasks = await get_suggested_tasks()
    assert len(tasks) > 0

    # Verify session state
    state = get_timestate()
    assert state.session_started is not None
    assert state.interaction_count_today >= 0
```

**E2E Test 2: Voice Capture to Task Completion**
```python
@pytest.mark.e2e
async def test_voice_to_completion_workflow():
    """
    Test full task lifecycle:
    1. Voice message capture
    2. Transcription and classification
    3. Task creation in WorkOS
    4. Task completion
    5. Points awarded
    """
    # Send voice message
    audio_file = create_test_audio("Complete documentation for project")
    task_id = await send_telegram_voice(audio_file)

    # Verify task created
    task = await workos_get_task(task_id)
    assert task.status == "backlog"
    assert task.valueTier in ["checkbox", "progress", "deliverable"]

    # Promote to active
    await workos_promote_task(task_id)

    # Complete task
    result = await workos_complete_task(task_id)
    assert result.points_earned > 0

    # Verify streak updated
    streak = await workos_get_streak()
    assert streak.current_streak >= 1
```

**E2E Test 3: Alert Generation to Mobile Notification**
```python
@pytest.mark.e2e
async def test_alert_to_notification_workflow():
    """
    Test alert system end-to-end:
    1. Create overdue task
    2. Daemon detects issue
    3. Alert generated
    4. Telegram notification sent
    5. User receives message
    """
    # Create task with past deadline
    task_id = await workos_create_task(
        title="Test overdue alert",
        deadline=date.today() - timedelta(days=1)
    )

    # Wait for daemon cycle
    await wait_for_daemon_cycle()

    # Verify alert generated
    daemon_state = read_daemon_state()
    assert daemon_state.total_alerts > 0

    # Verify Telegram notification
    telegram_history = get_telegram_history()
    assert any("overdue" in msg.lower() for msg in telegram_history)
```

**E2E Test 4: Remote Access Full Flow**
```python
@pytest.mark.e2e
def test_remote_access_full_workflow():
    """
    Test complete remote access:
    1. Start access services
    2. Connect via VPN
    3. Open web terminal
    4. Attach to tmux
    5. Execute commands
    6. Verify state updates
    """
    # Start services
    coordinator = AccessCoordinator()
    coordinator.start_all_services()

    # Verify services running
    assert coordinator.is_tmux_running()
    assert coordinator.is_tailscale_connected()
    assert coordinator.is_ttyd_running()

    # Simulate remote connection (mock)
    with remote_connection():
        # Execute command
        result = execute_remote_command("thanos-cli status")
        assert "readiness" in result.stdout

        # Verify state updated
        state = read_timestate()
        assert state.interaction_count_today > 0
```

**E2E Test 5: Multi-Day State Persistence**
```python
@pytest.mark.e2e
async def test_multi_day_persistence_workflow():
    """
    Test state persistence across multiple sessions:
    1. Day 1: Create tasks, log energy
    2. Day 2: Verify data persists
    3. Day 3: Check streak tracking
    """
    # Day 1
    with mock_date("2026-01-20"):
        task_id = await workos_create_task("Day 1 task")
        await workos_complete_task(task_id)
        await life_log_energy("high", note="Great day")

    # Day 2
    with mock_date("2026-01-21"):
        # Verify completed task in history
        completed = await workos_get_tasks(status="done")
        assert any(t.id == task_id for t in completed)

        # Verify energy log persists
        energy_history = await life_get_energy(limit=5)
        assert any(e.note == "Great day" for e in energy_history)

    # Day 3
    with mock_date("2026-01-22"):
        # Verify streak tracking
        streak = await workos_get_streak()
        assert streak.current_streak >= 1
```

**Estimated Effort:** 24 hours for 5 comprehensive E2E tests

### 2.4 Performance Tests (Benchmarks)

**Purpose:** Establish performance baselines and identify bottlenecks

**Framework:** pytest-benchmark + custom timing utilities

**Coverage Goal:** All critical paths measured, baselines established

#### Performance Test Suite

**File I/O Performance**
```python
# test_performance_fileio.py
@pytest.mark.benchmark
def test_state_file_read_performance(benchmark):
    """Benchmark state file read operations."""
    def read_timestate():
        with open("State/TimeState.json") as f:
            return json.load(f)

    result = benchmark(read_timestate)

    # Assert performance targets
    assert result.stats.mean < 0.001  # <1ms average
    assert result.stats.max < 0.01    # <10ms worst case

@pytest.mark.benchmark
def test_brain_dump_parse_performance(benchmark):
    """Benchmark brain dump file parsing."""
    def parse_brain_dumps():
        with open("State/brain_dumps.json") as f:
            data = json.load(f)
            return [BrainDump(**dump) for dump in data]

    result = benchmark(parse_brain_dumps)

    # Should handle 1000 dumps efficiently
    assert result.stats.mean < 0.1  # <100ms for large files
```

**MCP Tool Call Performance**
```python
# test_performance_mcp.py
@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_workos_task_query_performance(benchmark):
    """Benchmark WorkOS task queries."""
    async def get_active_tasks():
        return await workos_get_tasks(status="active")

    result = await benchmark(get_active_tasks)

    # Network call should be reasonable
    assert result.stats.mean < 0.5  # <500ms average
    assert result.stats.p95 < 1.0   # 95th percentile <1s

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_oura_readiness_fetch_performance(benchmark):
    """Benchmark Oura readiness data fetch."""
    async def get_readiness():
        today = date.today()
        return await oura__get_daily_readiness(
            startDate=today.isoformat(),
            endDate=today.isoformat()
        )

    result = await benchmark(get_readiness)

    assert result.stats.mean < 0.2  # <200ms average
```

**Brain Dump Processing Performance**
```python
# test_performance_processing.py
@pytest.mark.benchmark
def test_classification_performance(benchmark):
    """Benchmark brain dump classification speed."""
    processor = BrainDumpProcessor()

    def classify_dump():
        return processor.process(
            "Fix login bug for Memphis client by Friday"
        )

    result = benchmark(classify_dump)

    # Classification should be fast
    assert result.stats.mean < 0.1  # <100ms
    assert result.stats.p99 < 0.2   # 99th percentile <200ms

@pytest.mark.benchmark
def test_batch_classification_performance(benchmark):
    """Benchmark processing multiple brain dumps."""
    processor = BrainDumpProcessor()
    dumps = [
        "Fix bug A",
        "Complete feature B",
        "Worried about project C",
        "Idea for improvement D",
        "Quick admin task E"
    ] * 20  # 100 total

    def process_batch():
        return [processor.process(dump) for dump in dumps]

    result = benchmark(process_batch)

    # Should handle batch efficiently
    assert result.stats.mean < 2.0  # <2s for 100 items
```

**Daemon Cycle Performance**
```python
# test_performance_daemon.py
@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_daemon_check_cycle_performance(benchmark):
    """Benchmark complete daemon check cycle."""
    daemon = AlertDaemon()

    async def run_check_cycle():
        return await daemon.run_once()

    result = await benchmark(run_check_cycle)

    # Should complete quickly
    assert result.stats.mean < 0.5  # <500ms total
    assert result.stats.p95 < 1.0   # 95th percentile <1s
```

**Performance Regression Testing**
```python
# test_performance_regression.py
@pytest.mark.benchmark
def test_performance_regression_suite():
    """
    Run full performance suite and compare to baseline.
    Fails if any operation regresses >20%.
    """
    baseline = load_performance_baseline()
    current = run_performance_suite()

    for operation, current_time in current.items():
        baseline_time = baseline[operation]
        regression = (current_time - baseline_time) / baseline_time

        assert regression < 0.2, (
            f"{operation} regressed {regression*100:.1f}%: "
            f"{baseline_time:.3f}s → {current_time:.3f}s"
        )
```

**Estimated Effort:** 12 hours for comprehensive performance test suite

### 2.5 Security Tests (Audit)

**Purpose:** Validate security boundaries and data protection

**Framework:** pytest + manual penetration testing

**Coverage Goal:** All external interfaces validated

#### Security Test Categories

**API Key Protection**
```python
# test_security_secrets.py
def test_no_hardcoded_secrets():
    """Verify no API keys in source code."""
    # Scan all Python files
    for file in glob.glob("Tools/**/*.py", recursive=True):
        with open(file) as f:
            content = f.read()

            # Check for common secret patterns
            assert "sk-" not in content  # OpenAI keys
            assert "xoxb-" not in content  # Slack tokens
            assert "bot:" not in content  # Telegram tokens

            # Verify env var usage
            if "API" in content.upper():
                assert "os.getenv" in content or "os.environ" in content

def test_env_file_not_committed():
    """Verify .env file is gitignored."""
    gitignore = open(".gitignore").read()
    assert ".env" in gitignore

    # Verify .env not in git
    result = subprocess.run(
        ["git", "ls-files", ".env"],
        capture_output=True
    )
    assert result.stdout == b""
```

**State File Permissions**
```python
# test_security_permissions.py
def test_state_file_permissions():
    """Verify state files have correct permissions."""
    import stat

    for state_file in glob.glob("State/*.json"):
        mode = os.stat(state_file).st_mode

        # Should be readable by owner only
        assert bool(mode & stat.S_IRUSR)  # Owner read
        assert bool(mode & stat.S_IWUSR)  # Owner write
        assert not bool(mode & stat.S_IROTH)  # No world read

def test_log_file_permissions():
    """Verify log files don't expose sensitive data."""
    for log_file in glob.glob("logs/*.log"):
        with open(log_file) as f:
            content = f.read()

            # No API keys in logs
            assert "sk-" not in content
            assert "bot:" not in content

            # No passwords
            assert "password=" not in content.lower()
```

**Telegram Bot Security**
```python
# test_security_telegram.py
@pytest.mark.asyncio
async def test_telegram_user_whitelist():
    """Verify bot only responds to authorized users."""
    bot = TelegramBrainDumpBot()

    # Unauthorized user
    unauthorized_message = create_mock_telegram_message(
        user_id=99999999,  # Not in ALLOWED_USERS
        text="Test message"
    )

    response = await bot.handle_message(unauthorized_message)
    assert response is None  # Should ignore

    # Authorized user
    authorized_message = create_mock_telegram_message(
        user_id=int(os.getenv("TELEGRAM_ALLOWED_USERS")),
        text="Test message"
    )

    response = await bot.handle_message(authorized_message)
    assert response is not None  # Should process

def test_telegram_token_validation():
    """Verify Telegram bot token is validated."""
    # Invalid token format
    with pytest.raises(ValueError):
        TelegramBrainDumpBot(token="invalid-token")

    # Valid format
    bot = TelegramBrainDumpBot(token="123456:ABC-DEF1234ghIkl")
    assert bot.token is not None
```

**VPN Access Security**
```python
# test_security_vpn.py
def test_tailscale_vpn_required():
    """Verify ttyd only accessible via VPN."""
    # Check ttyd config
    config = get_ttyd_config()

    # Should bind to VPN interface only, not 0.0.0.0
    assert config.bind_address != "0.0.0.0"
    assert config.bind_address in ["127.0.0.1", get_tailscale_ip()]

def test_no_public_exposure():
    """Verify no services exposed to public internet."""
    # Check firewall rules
    firewall_rules = get_firewall_rules()

    # Port 7681 (ttyd) should not be public
    assert not any(
        rule.port == 7681 and rule.source == "0.0.0.0/0"
        for rule in firewall_rules
    )
```

**Input Validation**
```python
# test_security_input_validation.py
@pytest.mark.asyncio
async def test_brain_dump_xss_protection():
    """Verify brain dumps sanitize user input."""
    processor = BrainDumpProcessor()

    # Attempt XSS injection
    malicious_input = "<script>alert('XSS')</script>"
    result = processor.process(malicious_input)

    # Should escape HTML
    assert "<script>" not in result.raw_content
    assert "&lt;script&gt;" in result.raw_content or result.raw_content == ""

@pytest.mark.asyncio
async def test_sql_injection_protection():
    """Verify task titles don't allow SQL injection."""
    # Attempt SQL injection
    malicious_title = "'; DROP TABLE tasks; --"

    task_id = await workos_create_task(title=malicious_title)

    # Should store safely (parameterized queries)
    task = await workos_get_task(task_id)
    assert task.title == malicious_title  # Stored as-is

    # Database should still exist
    all_tasks = await workos_get_tasks()
    assert isinstance(all_tasks, list)
```

**Estimated Effort:** 10 hours for security test suite + 4 hours manual testing

---

## 3. Test Framework

### 3.1 Testing Tools and Frameworks

#### Primary Framework: pytest

**Rationale:**
- Industry standard for Python testing
- Excellent fixture support for setup/teardown
- Powerful assertion introspection
- Rich plugin ecosystem (pytest-asyncio, pytest-benchmark, pytest-cov)

**Installation:**
```bash
pip install pytest pytest-asyncio pytest-benchmark pytest-cov pytest-mock
```

**Configuration (`pytest.ini`):**
```ini
[pytest]
testpaths = Testing/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto

markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (slower, uses real MCP)
    e2e: End-to-end tests (slow, uses external services)
    benchmark: Performance benchmarks
    security: Security validation tests

addopts =
    --verbose
    --strict-markers
    --tb=short
    --cov=Tools
    --cov-report=html
    --cov-report=term-missing
```

#### Secondary Tools

**1. Bash Scripts for CLI Testing**

```bash
# Testing/scripts/test_cli_access.sh
#!/bin/bash
set -euo pipefail

echo "Testing CLI access commands..."

# Test thanos-cli status
output=$(./Tools/thanos-cli status)
echo "$output" | grep -q "readiness" || exit 1

# Test thanos-access status
output=$(./Access/thanos-access status)
echo "$output" | grep -q "tmux" || exit 1

echo "✅ CLI tests passed"
```

**2. Manual Testing Checklists**

```markdown
# Testing/checklists/remote_access_manual.md

## Remote Access Manual Test Checklist

### Prerequisites
- [ ] Tailscale installed and authenticated
- [ ] Mobile device on same VPN

### Test Steps
1. [ ] On desktop: Run `thanos-access start`
2. [ ] Verify services: `thanos-access status`
3. [ ] On mobile: Navigate to `https://{hostname}:7681/`
4. [ ] Verify web terminal loads
5. [ ] In terminal: Run `tmux attach -t thanos`
6. [ ] Verify tmux session active
7. [ ] Run `thanos-cli status`
8. [ ] Verify output matches desktop
9. [ ] Create brain dump via Telegram
10. [ ] Verify appears in CLI

### Success Criteria
- All steps complete without errors
- Response time <3 seconds for all operations
- Terminal responsive at 60 FPS
```

**3. GitHub Actions CI/CD**

```yaml
# .github/workflows/test.yml
name: Thanos v2.0 Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run unit tests
        run: pytest -m unit --cov

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run integration tests
        run: pytest -m integration
        env:
          WORKOS_API_KEY: ${{ secrets.WORKOS_TEST_API_KEY }}
          OURA_API_KEY: ${{ secrets.OURA_TEST_API_KEY }}

  performance-regression:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - name: Run benchmarks
        run: pytest -m benchmark --benchmark-only
      - name: Compare to baseline
        run: python Testing/scripts/compare_benchmarks.py
```

### 3.2 Test Data Requirements

#### Mock Data Sets

**1. Brain Dump Test Data**
```json
{
  "test_brain_dumps": [
    {
      "input": "Fix login bug for Memphis by Friday",
      "expected": {
        "category": "task",
        "domain": "work",
        "confidence": 0.85,
        "entities": ["Memphis"],
        "deadline": "Friday"
      }
    },
    {
      "input": "Worried about quarterly review next week",
      "expected": {
        "category": "worry",
        "domain": "personal",
        "confidence": 0.90,
        "deadline": "next week"
      }
    },
    {
      "input": "Idea: Automated testing framework for brain dumps",
      "expected": {
        "category": "idea",
        "domain": "work",
        "confidence": 0.95
      }
    }
  ]
}
```

**2. Oura API Mock Responses**
```json
{
  "readiness_high": {
    "data": [{
      "day": "2026-01-20",
      "score": 85,
      "contributors": {
        "hrv_balance": 85,
        "sleep_balance": 80,
        "recovery_index": 100
      }
    }]
  },
  "readiness_low": {
    "data": [{
      "day": "2026-01-20",
      "score": 45,
      "contributors": {
        "hrv_balance": 40,
        "sleep_balance": 30,
        "recovery_index": 50
      }
    }]
  }
}
```

**3. WorkOS Task Test Data**
```python
# Testing/fixtures/workos_tasks.py
MOCK_TASKS = [
    {
        "id": 1,
        "title": "Fix login bug",
        "status": "active",
        "clientId": 1,  # Memphis
        "valueTier": "deliverable",
        "drainType": "deep",
        "cognitiveLoad": "high",
        "deadline": "2026-01-24"
    },
    {
        "id": 2,
        "title": "Update documentation",
        "status": "backlog",
        "valueTier": "checkbox",
        "drainType": "admin",
        "cognitiveLoad": "low"
    }
]
```

#### Test Database Setup

**SQLite Test Database**
```python
# Testing/conftest.py (pytest fixtures)
import pytest
import sqlite3

@pytest.fixture
def test_db():
    """Create temporary test database."""
    db = sqlite3.connect(":memory:")

    # Create schema
    db.execute("""
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT,
            deadline DATE
        )
    """)

    # Populate test data
    db.execute("""
        INSERT INTO tasks (title, status, deadline)
        VALUES ('Test task', 'active', '2026-01-25')
    """)

    yield db
    db.close()

@pytest.fixture
def mock_oura_api(monkeypatch):
    """Mock Oura API responses."""
    async def mock_get_readiness(startDate, endDate):
        return {
            "data": [{
                "day": startDate,
                "score": 75,
                "contributors": {
                    "hrv_balance": 70,
                    "sleep_balance": 80
                }
            }]
        }

    monkeypatch.setattr(
        "Tools.oura_client.get_daily_readiness",
        mock_get_readiness
    )
```

### 3.3 Environment Setup

#### Test Environment Configuration

**Directory Structure**
```
Testing/
├── tests/
│   ├── unit/
│   │   ├── test_classification.py
│   │   ├── test_alert_generation.py
│   │   └── test_state_persistence.py
│   ├── integration/
│   │   ├── test_phase1_phase3.py
│   │   ├── test_phase1_phase4.py
│   │   └── test_phase3_phase4.py
│   ├── e2e/
│   │   ├── test_morning_routine.py
│   │   ├── test_voice_to_task.py
│   │   └── test_alert_flow.py
│   ├── performance/
│   │   ├── test_fileio_perf.py
│   │   ├── test_mcp_perf.py
│   │   └── test_daemon_perf.py
│   └── security/
│       ├── test_secrets.py
│       ├── test_permissions.py
│       └── test_input_validation.py
├── fixtures/
│   ├── brain_dumps.json
│   ├── oura_responses.json
│   └── workos_tasks.py
├── scripts/
│   ├── test_cli_access.sh
│   ├── compare_benchmarks.py
│   └── setup_test_env.sh
├── checklists/
│   ├── remote_access_manual.md
│   └── security_audit.md
├── conftest.py
└── pytest.ini
```

**Environment Variables (`.env.test`)**
```bash
# Test environment configuration
THANOS_ENV=test
THANOS_STATE_DIR=/tmp/thanos-test-state
THANOS_LOG_DIR=/tmp/thanos-test-logs

# Test API keys (sandbox/mock)
WORKOS_API_KEY=test_workos_key
OURA_API_KEY=test_oura_key
TELEGRAM_BOT_TOKEN=test_bot_token
TELEGRAM_ALLOWED_USERS=123456789

# Mock external services
MOCK_CALENDAR_API=true
MOCK_WHISPER_API=true
```

**Setup Script (`Testing/scripts/setup_test_env.sh`)**
```bash
#!/bin/bash
set -euo pipefail

echo "Setting up Thanos test environment..."

# Create test directories
mkdir -p /tmp/thanos-test-state
mkdir -p /tmp/thanos-test-logs

# Copy test configuration
cp Testing/.env.test .env

# Initialize test state files
echo '{"session_started": null, "interaction_count_today": 0}' > /tmp/thanos-test-state/TimeState.json
echo '{"dumps": []}' > /tmp/thanos-test-state/brain_dumps.json

# Install test dependencies
pip install -r Testing/requirements-test.txt

echo "✅ Test environment ready"
```

### 3.4 Automation Approach

#### CI/CD Pipeline

**Trigger Events:**
- Push to main branch
- Pull request creation
- Nightly scheduled run (comprehensive tests)

**Pipeline Stages:**

**Stage 1: Fast Checks (2 minutes)**
```yaml
- Linting (ruff, black)
- Type checking (mypy)
- Security scan (bandit)
- Unit tests (pytest -m unit)
```

**Stage 2: Integration Tests (10 minutes)**
```yaml
- Integration tests (pytest -m integration)
- Mock MCP servers
- Test database setup
- API contract validation
```

**Stage 3: E2E Tests (30 minutes)**
```yaml
- E2E workflows (pytest -m e2e)
- Real MCP servers (sandbox)
- External API calls (test accounts)
- Full user journeys
```

**Stage 4: Performance & Security (15 minutes)**
```yaml
- Performance benchmarks (pytest -m benchmark)
- Compare to baseline
- Security tests (pytest -m security)
- Vulnerability scan
```

**Stage 5: Deployment (if all pass)**
```yaml
- Tag release
- Generate test report
- Update documentation
- Notify team
```

#### Local Development Workflow

**Pre-commit Hooks**
```bash
# .git/hooks/pre-commit
#!/bin/bash

# Run fast tests before commit
pytest -m unit --quiet

# Check code style
ruff check .
black --check .

# Type check
mypy Tools/
```

**Test Run Commands**
```bash
# Run all tests
pytest

# Run specific category
pytest -m unit
pytest -m integration
pytest -m e2e

# Run with coverage
pytest --cov --cov-report=html

# Run benchmarks
pytest -m benchmark --benchmark-only

# Run security tests
pytest -m security
```

---

## 4. Success Criteria

### 4.1 Pass/Fail Thresholds

#### Unit Tests

| Metric | Threshold | Current | Status |
|--------|-----------|---------|--------|
| **Test Pass Rate** | ≥95% | N/A (no tests) | ❌ Missing |
| **Code Coverage** | ≥80% | N/A | ❌ Missing |
| **Critical Path Coverage** | 100% | N/A | ❌ Missing |

**Pass Criteria:**
- All unit tests must pass
- No critical assertions skipped
- Mock data covers edge cases

#### Integration Tests

| Metric | Threshold | Current | Status |
|--------|-----------|---------|--------|
| **Integration Points Validated** | 14/14 (100%) | 12/14 (85.7%) | ⚠️ Partial |
| **Test Pass Rate** | ≥90% | N/A | ❌ Missing |
| **Phase-to-Phase Coverage** | 100% | 85.7% | ⚠️ Partial |

**Pass Criteria:**
- All 14 integration points validated
- No critical data flow failures
- State consistency maintained

#### E2E Tests

| Metric | Threshold | Current | Status |
|--------|-----------|---------|--------|
| **Critical Workflows** | 5/5 (100%) | 4/5 (80%) | ⚠️ Partial |
| **Test Pass Rate** | ≥85% | 80% | ⚠️ Borderline |
| **User Journey Coverage** | 100% | 80% | ⚠️ Partial |

**Pass Criteria:**
- All 5 critical workflows complete successfully
- End-to-end latency acceptable
- No data loss or corruption

### 4.2 Performance Benchmarks

#### File I/O Performance

| Operation | Target | Current | Status |
|-----------|--------|---------|--------|
| **State File Read** | <1ms | 0.02ms | ✅ Excellent |
| **JSON Parse (TimeState)** | <5ms | 0.02ms | ✅ Excellent |
| **JSON Parse (brain_dumps)** | <10ms | 0.06ms | ✅ Excellent |
| **Throughput** | >10K ops/sec | 15K-54K ops/sec | ✅ Excellent |

#### MCP Tool Call Performance

| Operation | Target | Current | Status |
|-----------|--------|---------|--------|
| **workos_get_tasks** | <500ms | Not measured | ⚠️ Unknown |
| **oura_get_readiness** | <300ms | Not measured | ⚠️ Unknown |
| **Brain dump classification** | <100ms | 80ms | ✅ Good |

**Target Establishment:**
```python
# Testing/performance_targets.py
PERFORMANCE_TARGETS = {
    "file_io": {
        "state_read": 0.001,  # 1ms
        "json_parse": 0.005,  # 5ms
        "throughput": 10000   # ops/sec
    },
    "mcp_calls": {
        "workos_get_tasks": 0.5,      # 500ms
        "oura_readiness": 0.3,        # 300ms
        "brain_dump_classify": 0.1    # 100ms
    },
    "daemon": {
        "check_cycle": 0.5,   # 500ms total
        "alert_send": 1.0     # 1s max
    }
}
```

#### Regression Tolerance

**Acceptable Regression:** ≤10% from baseline
**Warning Threshold:** >10% regression
**Failure Threshold:** >20% regression

```python
def check_performance_regression(baseline, current):
    """Verify performance hasn't regressed significantly."""
    for operation, baseline_time in baseline.items():
        current_time = current[operation]
        regression = (current_time - baseline_time) / baseline_time

        if regression > 0.20:
            raise PerformanceRegressionError(
                f"{operation} regressed {regression*100:.1f}%"
            )
        elif regression > 0.10:
            warnings.warn(
                f"{operation} regression detected: {regression*100:.1f}%"
            )
```

### 4.3 Security Requirements

#### Authentication & Authorization

| Requirement | Status | Validation |
|-------------|--------|------------|
| **No hardcoded secrets** | ⚠️ Unknown | Code scan required |
| **Env vars for API keys** | ✅ Implemented | Manual verification |
| **Telegram whitelist** | ✅ Implemented | Test coverage needed |
| **VPN-only access** | ✅ Implemented | Manual testing required |

#### Data Protection

| Requirement | Status | Validation |
|-------------|--------|------------|
| **State file permissions (600)** | ⚠️ Unknown | Permission test required |
| **No logs contain secrets** | ⚠️ Unknown | Log scan required |
| **Input sanitization** | ⚠️ Unknown | XSS/injection tests required |

**Security Test Pass Criteria:**
- No secrets in codebase or logs
- All API keys from environment variables
- State files readable by owner only
- Telegram bot rejects unauthorized users
- No public exposure of internal services

### 4.4 Coverage Goals

#### Code Coverage by Component

| Component | Target Coverage | Priority |
|-----------|----------------|----------|
| **Phase 1: Router** | 85% | High |
| **Phase 3: Health** | 80% | High |
| **Phase 4: Access** | 70% | Medium |
| **Shared Infrastructure** | 90% | Critical |

**Coverage Enforcement:**
```ini
# pytest.ini
[pytest]
addopts = --cov-fail-under=80
```

**Exclude from Coverage:**
- Test files themselves
- Mock/fixture data
- Deprecated code paths
- Debug/development utilities

---

## 5. Test Matrix

### 5.1 Workflow × Test Type Matrix

| Workflow | Unit | Integration | E2E | Performance | Security | Priority |
|----------|------|-------------|-----|-------------|----------|----------|
| **Morning Routine** | ✅ | ✅ | ✅ | ✅ | ⚠️ | P0 |
| **Voice → Task** | ✅ | ✅ | ✅ | ⚠️ | ✅ | P0 |
| **Alert → Mobile** | ✅ | ✅ | ✅ | ✅ | ✅ | P1 |
| **Remote Access** | ⚠️ | ✅ | ⚠️ | ❌ | ✅ | P1 |
| **Energy Routing** | ✅ | ⚠️ | ⚠️ | ⚠️ | ❌ | P1 |
| **State Persistence** | ✅ | ✅ | ✅ | ✅ | ⚠️ | P0 |

**Legend:**
- ✅ Test exists or planned with high confidence
- ⚠️ Partial coverage or needs validation
- ❌ Not covered, needs creation

### 5.2 Integration Point × Test Coverage Matrix

| Integration Point | Unit | Integration | E2E | Status |
|------------------|------|-------------|-----|--------|
| **Phase 1 → 3: Classification** | ✅ | ✅ | ✅ | Complete |
| **Phase 1 → 3: Energy Gating** | ✅ | ⚠️ | ⚠️ | Partial |
| **Phase 1 → 4: CLI Access** | ⚠️ | ✅ | ⚠️ | Partial |
| **Phase 1 → 4: Telegram** | ✅ | ✅ | ✅ | Complete |
| **Phase 3 → 4: Remote Monitor** | ❌ | ❌ | ❌ | **CRITICAL GAP** |
| **Phase 3 → 4: Mobile Alerts** | ✅ | ✅ | ✅ | Complete |
| **MCP: WorkOS** | ⚠️ | ✅ | ✅ | Partial (need mocks) |
| **MCP: Oura** | ⚠️ | ✅ | ✅ | Partial (need mocks) |
| **State: TimeState** | ✅ | ✅ | ✅ | Complete |
| **State: BrainDumps** | ✅ | ✅ | ⚠️ | Partial (concurrency) |

### 5.3 Critical Path Identification

#### Path 1: User Input → Task Creation (P0)

```
Voice/Text Input → Classification → Task Creation → Confirmation
```

**Test Coverage:**
- Unit: ✅ BrainDumpProcessor
- Integration: ✅ Telegram → WorkOS
- E2E: ✅ Full voice-to-task flow
- Performance: ⚠️ Need baseline

**Critical Because:** Core value proposition of system

#### Path 2: Health Data → Task Suggestions (P0)

```
Oura Readiness → Energy Level → Task Filtering → Suggestions
```

**Test Coverage:**
- Unit: ✅ Energy detection
- Integration: ⚠️ Oura → Routing
- E2E: ⚠️ Need live validation
- Performance: ⚠️ Need MCP timing

**Critical Because:** ADHD-optimized workflow depends on this

#### Path 3: Session Start → Context Display (P0)

```
Claude Launch → Hook Execution → Daily Brief → CLI Ready
```

**Test Coverage:**
- Unit: ✅ TimeState updates
- Integration: ✅ Hook → State
- E2E: ✅ Full startup flow
- Performance: ✅ Benchmarked (<3s)

**Critical Because:** First user interaction, sets daily context

#### Path 4: Alert Generation → Mobile Delivery (P1)

```
Daemon Check → Alert Created → Telegram Sent → User Notified
```

**Test Coverage:**
- Unit: ✅ Alert checkers
- Integration: ✅ Daemon → Telegram
- E2E: ✅ Full notification flow
- Security: ✅ User whitelist

**Critical Because:** Keeps user accountable, prevents missed deadlines

#### Path 5: Remote Access → Command Execution (P1)

```
Mobile → VPN → Web Terminal → tmux → CLI → Response
```

**Test Coverage:**
- Unit: ⚠️ Access components
- Integration: ✅ CLI → Coordinator
- E2E: ⚠️ Live mobile test needed
- Security: ✅ VPN-only validated

**Critical Because:** Enables mobile workflow, key differentiator

### 5.4 Priority Assignment

#### P0: Critical Paths (System Fails Without These)

1. User input → Task creation
2. Health data → Task suggestions
3. Session start → Context display
4. State persistence across sessions

**Required Test Coverage:** 95%+
**Failure Impact:** System unusable
**Test Frequency:** Every commit

#### P1: Core Functionality (Major Degradation if Broken)

5. Alert generation → Mobile delivery
6. Remote access → Command execution
7. Brain dump classification accuracy
8. Energy-aware routing

**Required Test Coverage:** 85%+
**Failure Impact:** Reduced functionality
**Test Frequency:** Every PR, nightly

#### P2: Enhancements (System Works But Less Effectively)

9. Daemon remote monitoring
10. Performance optimization
11. Advanced classification features
12. Multi-day state tracking

**Required Test Coverage:** 70%+
**Failure Impact:** Reduced UX quality
**Test Frequency:** Weekly, before releases

---

## 6. Integration with Existing Results

### 6.1 E2E Test Results Reference

**Source:** `/Users/jeremy/Projects/Thanos/Testing/E2E_TEST_RESULTS.md`
**Date:** 2026-01-20 21:50:00 EST
**Success Rate:** 80% (12/14 integration points)

#### Key Findings to Incorporate

**Validated Workflows (Use as Baseline):**
1. Morning Routine Flow - 100% pass
   - **Action:** Convert to automated E2E test
   - **Estimated Effort:** 4 hours

2. Task Management Flow - 100% pass
   - **Action:** Create regression test
   - **Estimated Effort:** 3 hours

3. Remote Access Flow - 90% pass
   - **Action:** Add live mobile connection test
   - **Estimated Effort:** 6 hours

**Failed Workflows (Requires Implementation):**
4. Daemon Coordination - 40% pass
   - **Gap:** Daemons not running in production mode
   - **Action:** Implement daemon startup, add tests
   - **Estimated Effort:** 8 hours

#### Integration Points Already Validated

| Point | Validation Method | Confidence |
|-------|------------------|------------|
| Phase 3 → Phase 1 (Health → Routing) | Manual execution | High |
| Oura MCP → WorkOS MCP | Tool calls verified | High |
| Hook system → State persistence | File inspection | High |
| Brain dump → MCP storage | Data flow traced | High |

**Action:** Automate these manual validations into integration test suite

### 6.2 Performance Benchmarks Reference

**Source:** `/Users/jeremy/Projects/Thanos/Testing/PERFORMANCE_BENCHMARKS.md`
**Date:** 2026-01-20 21:49:12
**Overall Grade:** A (Excellent)

#### Baselines Established

| Component | Metric | Baseline | Use In Testing |
|-----------|--------|----------|----------------|
| **FileIO** | Read TimeState | 0.02ms | Regression threshold: 0.03ms |
| **FileIO** | Parse brain_dumps | 0.06ms | Regression threshold: 0.10ms |
| **Python** | Import state_reader | 0.37ms | Regression threshold: 0.50ms |
| **External** | Command execution | 3-10ms | Warning threshold: >15ms |

**Action:** Import baselines into `Testing/performance_baselines.json`

#### Performance Gaps Identified

| Gap | Current | Target | Estimated Work |
|-----|---------|--------|----------------|
| MCP call latency | Not measured | <500ms | 4 hours (add benchmarks) |
| Network simulation | Not tested | Failure scenarios | 6 hours (mock network) |
| Concurrent load | Single-threaded only | 10 users | 8 hours (load testing) |

**Action:** Create performance test roadmap addressing these gaps

#### Optimization Recommendations

From PERFORMANCE_BENCHMARKS.md (Priority 1):
1. Batch MCP calls - 50% cycle time reduction
2. Cache MCP responses - 90% reduction for repeated queries
3. Preload critical state - 0.5ms → 0ms improvement

**Action:**
- Add performance tests validating these optimizations
- Create before/after benchmarks for each improvement
- Track in test suite

### 6.3 Integration Validation Reference

**Source:** `/Users/jeremy/Projects/Thanos/Testing/INTEGRATION_VALIDATION.md`
**Date:** 2026-01-20 21:46 PM
**Status:** ✅ Validated with 3 issues

#### Issues to Address in Testing Strategy

**Critical Issue #1: Daemon → Remote Monitoring (P0)**
- **Gap:** No web interface for daemon status
- **Testing Need:**
  - Create integration test for health dashboard
  - Add E2E test for remote daemon access
  - Validate via `thanos-access health` command
- **Estimated Effort:** 6 hours

**Minor Issue #2: State File Location Inconsistency (P2)**
- **Gap:** Multiple state directories
- **Testing Need:**
  - Add test validating single canonical location
  - Test `THANOS_STATE_DIR` environment variable
  - Verify no data in deprecated locations
- **Estimated Effort:** 2 hours

**Minor Issue #3: MCP Server Path Validation (P2)**
- **Gap:** Hardcoded paths in settings.json
- **Testing Need:**
  - Test path validation on hook execution
  - Verify `$THANOS_ROOT` environment variable
  - Add error logging for invalid paths
- **Estimated Effort:** 2 hours

#### API Contract Validation Results

From INTEGRATION_VALIDATION.md - 100% compliance:
- WorkOS MCP: 6/6 tools compliant
- Oura MCP: 2/2 tools compliant

**Action:** Create contract tests ensuring continued compliance

```python
# test_api_contracts.py
@pytest.mark.integration
async def test_workos_api_contracts():
    """Verify WorkOS MCP tool signatures match specification."""
    # Test get_tasks signature
    tasks = await workos_get_tasks(status="active", limit=5)
    assert isinstance(tasks, list)
    assert all(hasattr(t, "id") for t in tasks)

    # Test create_task signature
    task = await workos_create_task(
        title="Test",
        clientId=1,
        valueTier="checkbox"
    )
    assert task.id is not None
```

#### Data Flow Validation

From INTEGRATION_VALIDATION.md Section 6:
- Brain Dump → Task Creation: ✅ Validated
- Daily Brief Generation: ✅ Validated
- Alert → Telegram: ✅ Validated

**Action:** Convert these manual validations to automated E2E tests

### 6.4 Unified Testing Roadmap

#### Phase 1: Consolidate Existing Results (Week 1)

**Tasks:**
1. Import performance baselines into test suite
2. Convert manual E2E validations to automated tests
3. Document API contracts as test specifications
4. Create test data fixtures from validation examples

**Deliverables:**
- `Testing/performance_baselines.json`
- `Testing/tests/e2e/test_morning_routine.py`
- `Testing/tests/integration/test_api_contracts.py`
- `Testing/fixtures/` populated with real data

**Estimated Effort:** 20 hours

#### Phase 2: Fill Critical Gaps (Week 2)

**Tasks:**
1. Implement daemon remote monitoring (from Issue #1)
2. Create integration tests for Phase 3 ↔ 4
3. Add MCP call performance benchmarks
4. Implement security test suite

**Deliverables:**
- `Access/access_coordinator.py` with health dashboard
- `Testing/tests/integration/test_phase3_phase4.py`
- `Testing/tests/performance/test_mcp_perf.py`
- `Testing/tests/security/` complete

**Estimated Effort:** 30 hours

#### Phase 3: Automation & CI/CD (Week 3)

**Tasks:**
1. Set up GitHub Actions workflows
2. Create pre-commit hooks
3. Add performance regression detection
4. Implement coverage enforcement

**Deliverables:**
- `.github/workflows/test.yml`
- `.git/hooks/pre-commit`
- `Testing/scripts/compare_benchmarks.py`
- Coverage reports in CI

**Estimated Effort:** 16 hours

#### Phase 4: Production Readiness (Week 4)

**Tasks:**
1. Run full test suite against production config
2. Load testing (10 concurrent users)
3. Security audit and penetration testing
4. Documentation and training

**Deliverables:**
- Production test report
- Load test results
- Security audit report
- Testing runbook

**Estimated Effort:** 24 hours

**Total Estimated Effort:** 90 hours (4 weeks)

---

## 7. Remaining Validation Work

### 7.1 High Priority (P0) - Required for Production

#### 1. Daemon Remote Monitoring Integration

**Gap:** Phase 3 ↔ Phase 4 remote monitoring not implemented

**Validation Needed:**
- ✅ Create `thanos-access health` command
- ✅ Integration test: Daemon status via coordinator
- ✅ E2E test: Mobile access to daemon status
- ✅ Performance: <1s response time

**Test Cases:**
```python
@pytest.mark.integration
async def test_daemon_remote_monitoring():
    """Verify daemon status accessible remotely."""
    # Start daemon
    daemon = AlertDaemon()
    await daemon.run_once()

    # Access via coordinator
    coordinator = AccessCoordinator()
    status = coordinator.get_daemon_status()

    assert status["running"] == True
    assert status["last_check"] is not None
    assert len(status["enabled_checkers"]) > 0

@pytest.mark.e2e
def test_mobile_daemon_access():
    """Test daemon status from mobile device."""
    with remote_session():
        result = execute_command("thanos-access health")
        assert "daemon" in result.stdout.lower()
        assert "running" in result.stdout.lower()
```

**Estimated Effort:** 8 hours

#### 2. MCP Network Performance Baselines

**Gap:** Network latency for MCP calls not measured

**Validation Needed:**
- ✅ Benchmark `workos_get_tasks` latency
- ✅ Benchmark `oura_get_readiness` latency
- ✅ Benchmark brain dump → task creation end-to-end
- ✅ Establish P50, P95, P99 latency targets

**Test Cases:**
```python
@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_workos_latency_baseline(benchmark):
    """Establish WorkOS MCP latency baseline."""
    async def fetch_tasks():
        return await workos_get_tasks(status="active")

    result = await benchmark(fetch_tasks)

    # Record baseline
    record_baseline("workos_get_tasks", {
        "p50": result.stats.median,
        "p95": result.stats.p95,
        "p99": result.stats.p99
    })

    # Verify reasonable performance
    assert result.stats.median < 0.5  # 500ms
    assert result.stats.p99 < 2.0     # 2s worst case
```

**Estimated Effort:** 6 hours

#### 3. Concurrent Load Testing

**Gap:** No testing under concurrent access

**Validation Needed:**
- ✅ 5 concurrent users accessing CLI
- ✅ Multiple brain dumps processed simultaneously
- ✅ State file race condition testing
- ✅ MCP connection pool behavior

**Test Cases:**
```python
@pytest.mark.load
async def test_concurrent_brain_dump_processing():
    """Test multiple brain dumps processed in parallel."""
    processor = BrainDumpProcessor()

    # Simulate 10 concurrent brain dumps
    dumps = [f"Task {i} for testing" for i in range(10)]

    async def process_dump(dump):
        return processor.process(dump)

    # Process all concurrently
    results = await asyncio.gather(*[
        process_dump(dump) for dump in dumps
    ])

    # Verify all processed successfully
    assert len(results) == 10
    assert all(r.category == BrainDumpCategory.TASK for r in results)

@pytest.mark.load
def test_state_file_concurrent_access():
    """Test race conditions on state file writes."""
    import multiprocessing

    def update_state(process_id):
        tracker = TimeTracker()
        for _ in range(100):
            tracker.increment_interaction()

    # Spawn 5 processes
    processes = [
        multiprocessing.Process(target=update_state, args=(i,))
        for i in range(5)
    ]

    for p in processes:
        p.start()
    for p in processes:
        p.join()

    # Verify count is correct (no lost updates)
    state = TimeTracker().get_state()
    assert state.interaction_count_today == 500  # 5 * 100
```

**Estimated Effort:** 10 hours

#### 4. Automated E2E Test Suite

**Gap:** 0% automated E2E coverage

**Validation Needed:**
- ✅ Morning Routine automated test
- ✅ Voice → Task automated test
- ✅ Alert → Mobile automated test
- ✅ Remote Access automated test
- ✅ Energy Routing automated test

**Estimated Effort:** 20 hours (4 hours per workflow)

**Total P0 Effort:** 44 hours

### 7.2 Medium Priority (P1) - Improves Confidence

#### 5. Security Test Suite

**Gap:** No automated security validation

**Validation Needed:**
- ✅ No hardcoded secrets scan
- ✅ State file permission validation
- ✅ Input sanitization tests (XSS, SQL injection)
- ✅ Telegram user whitelist enforcement
- ✅ VPN-only access verification

**Estimated Effort:** 10 hours

#### 6. API Contract Regression Tests

**Gap:** No ongoing contract validation

**Validation Needed:**
- ✅ WorkOS MCP tool signature tests
- ✅ Oura MCP tool signature tests
- ✅ Version compatibility checks
- ✅ Breaking change detection

**Estimated Effort:** 6 hours

#### 7. Performance Regression Detection

**Gap:** No automated performance monitoring

**Validation Needed:**
- ✅ CI/CD benchmark comparison
- ✅ Automatic baseline updates
- ✅ Regression alerts (>20% slowdown)
- ✅ Historical trend tracking

**Estimated Effort:** 8 hours

**Total P1 Effort:** 24 hours

### 7.3 Low Priority (P2) - Nice to Have

#### 8. State File Consolidation Tests

**Gap:** Multiple state directories not tested

**Validation Needed:**
- ✅ Single canonical location verified
- ✅ Environment variable usage
- ✅ Migration from legacy locations
- ✅ Cleanup of deprecated files

**Estimated Effort:** 4 hours

#### 9. Long-Term Persistence Testing

**Gap:** Multi-day state tracking not validated

**Validation Needed:**
- ✅ State survives across days
- ✅ Streak tracking accuracy
- ✅ Historical data integrity
- ✅ Archive/cleanup behavior

**Estimated Effort:** 6 hours

#### 10. Mobile Device Real Testing

**Gap:** Only simulated mobile access tested

**Validation Needed:**
- ✅ Real iPhone/Android connection
- ✅ Network latency on mobile
- ✅ Touch interface usability
- ✅ Background notification delivery

**Estimated Effort:** 8 hours (requires physical devices)

**Total P2 Effort:** 18 hours

### 7.4 Overall Validation Roadmap

| Priority | Category | Effort | Deadline |
|----------|----------|--------|----------|
| **P0** | Daemon Remote Monitoring | 8h | Week 2 |
| **P0** | MCP Performance Baselines | 6h | Week 2 |
| **P0** | Concurrent Load Testing | 10h | Week 3 |
| **P0** | Automated E2E Suite | 20h | Week 3 |
| **P1** | Security Test Suite | 10h | Week 4 |
| **P1** | API Contract Tests | 6h | Week 4 |
| **P1** | Performance Regression | 8h | Week 4 |
| **P2** | State Consolidation | 4h | Backlog |
| **P2** | Long-Term Persistence | 6h | Backlog |
| **P2** | Mobile Real Testing | 8h | Backlog |

**Total Remaining Work:** 86 hours (11 days @ 8 hours/day)

**Critical Path:** P0 items (44 hours / 5.5 days)

---

## 8. Implementation Recommendations

### 8.1 Quick Wins (1-2 hours each)

1. **Import Performance Baselines**
   - Copy PERFORMANCE_BENCHMARKS.md metrics to `performance_baselines.json`
   - Create comparison script
   - Add to CI/CD

2. **Document API Contracts**
   - Extract from INTEGRATION_VALIDATION.md
   - Create contract specifications
   - Add to test fixtures

3. **Set Up pytest Infrastructure**
   - Create `Testing/tests/` directory structure
   - Add `conftest.py` with basic fixtures
   - Configure `pytest.ini`

4. **Create Manual Test Checklists**
   - Convert E2E_TEST_RESULTS.md steps to checklists
   - Add to `Testing/checklists/`
   - Include in release process

### 8.2 High-Impact Tasks (4-8 hours each)

5. **Daemon Remote Monitoring**
   - Implement `AccessCoordinator.get_daemon_status()`
   - Add `thanos-access health` command
   - Create integration test

6. **Automated Morning Routine Test**
   - Convert E2E_TEST_RESULTS.md Section 1.1 to pytest
   - Mock Oura/Calendar APIs
   - Validate TimeState updates

7. **MCP Performance Benchmarking**
   - Add `pytest-benchmark` tests for all MCP tools
   - Establish P50/P95/P99 targets
   - Create regression detection

8. **Security Test Suite**
   - Scan for hardcoded secrets
   - Validate file permissions
   - Test input sanitization

### 8.3 Long-Term Improvements (1-2 weeks)

9. **Comprehensive E2E Suite**
   - All 5 critical workflows automated
   - Mock external services
   - Run in CI/CD

10. **Load Testing Framework**
    - Concurrent user simulation
    - State file race condition detection
    - MCP connection pooling validation

11. **Production Monitoring**
    - Real-time performance dashboards
    - Alerting on test failures
    - Trend analysis

### 8.4 Testing Best Practices

#### Test Organization

```python
# Good: Focused, single-purpose test
def test_brain_dump_task_classification():
    """Verify work task classification."""
    processor = BrainDumpProcessor()
    result = processor.process("Fix bug for Memphis")
    assert result.category == BrainDumpCategory.TASK
    assert result.domain == TaskDomain.WORK

# Bad: Testing multiple concerns
def test_everything():
    """Test brain dump processing."""
    processor = BrainDumpProcessor()
    # Tests classification, routing, API calls, etc.
    # Too much in one test!
```

#### Test Naming Convention

```python
# Pattern: test_[component]_[behavior]_[condition]

def test_classifier_returns_task_when_action_verb_present()
def test_daemon_generates_alert_when_task_overdue()
def test_coordinator_starts_services_when_all_prerequisites_met()
```

#### Fixture Usage

```python
# conftest.py
@pytest.fixture
def brain_dump_processor():
    """Create BrainDumpProcessor instance."""
    return BrainDumpProcessor()

@pytest.fixture
def mock_oura_high_readiness(monkeypatch):
    """Mock Oura API with high readiness score."""
    async def mock_get_readiness(startDate, endDate):
        return {"data": [{"score": 85}]}

    monkeypatch.setattr(
        "Tools.oura_client.get_daily_readiness",
        mock_get_readiness
    )

# test_classification.py
def test_classification(brain_dump_processor, mock_oura_high_readiness):
    """Test uses fixtures for clean setup."""
    result = brain_dump_processor.process("Test task")
    assert result.energy_hint == "high"
```

#### Assertion Messages

```python
# Good: Helpful failure message
assert task.valueTier == "deliverable", (
    f"Expected deliverable tier for complex task, got {task.valueTier}"
)

# Bad: Cryptic failure
assert task.valueTier == "deliverable"
```

#### Test Independence

```python
# Good: Each test cleans up after itself
@pytest.fixture
def temp_state_file(tmp_path):
    """Create temporary state file."""
    state_file = tmp_path / "TimeState.json"
    yield state_file
    state_file.unlink(missing_ok=True)  # Cleanup

# Bad: Tests rely on shared state
def test_writes_state():
    write_state("data")  # Pollutes global state

def test_reads_state():
    data = read_state()  # Depends on previous test!
```

---

## 9. Conclusion

### 9.1 Testing Strategy Summary

This integration testing strategy provides a comprehensive framework for validating Thanos v2.0 across all phases. The strategy consolidates existing test results (E2E, Performance, Integration Validation) and defines clear paths forward for remaining validation work.

**Key Components:**
1. **Test Scope:** 14 integration points across Phases 1-4
2. **Test Categories:** Unit, Integration, E2E, Performance, Security
3. **Test Framework:** pytest + bash + manual checklists
4. **Success Criteria:** 95% integration validation, 80% code coverage, <500ms MCP calls
5. **Test Matrix:** 5 critical workflows × 5 test types = comprehensive coverage

### 9.2 Current State Assessment

**Strengths:**
- 85.7% of integration points already validated (12/14)
- Grade A performance for all local operations
- Strong foundation in E2E and integration testing
- Clear documentation of existing results

**Gaps:**
- 0% automated test coverage (all manual)
- Daemon remote monitoring not implemented (critical gap)
- MCP network latency not benchmarked
- No security test suite
- No load/concurrency testing

### 9.3 Roadmap to Production Readiness

**Week 1: Foundation (20 hours)**
- Import performance baselines
- Set up pytest infrastructure
- Convert manual tests to automated

**Week 2: Critical Gaps (30 hours)**
- Implement daemon remote monitoring
- Add MCP performance benchmarks
- Create integration test suite

**Week 3: Automation (16 hours)**
- Set up CI/CD pipelines
- Add pre-commit hooks
- Implement regression detection

**Week 4: Production Ready (24 hours)**
- Security audit and testing
- Load testing (10 concurrent users)
- Final validation and documentation

**Total Effort:** 90 hours over 4 weeks

### 9.4 Success Metrics

**Pre-Production Checklist:**
- [ ] 95% integration point validation (14/14)
- [ ] 80% code coverage on critical paths
- [ ] All P0 E2E tests automated and passing
- [ ] Performance baselines established
- [ ] Security tests passing (no vulnerabilities)
- [ ] Load testing completed (10 concurrent users)
- [ ] CI/CD pipeline operational
- [ ] Documentation complete

**Production Ready When:**
- All checkboxes above are checked
- No critical bugs in test results
- Performance meets or exceeds targets
- Security audit passed
- Team trained on test execution

### 9.5 Risk Mitigation

**Risk 1: Daemon Not Running**
- **Mitigation:** Implement daemon monitoring (Week 2)
- **Fallback:** Manual daemon execution documented

**Risk 2: MCP Latency Too High**
- **Mitigation:** Benchmark early, optimize if needed
- **Fallback:** Caching layer for frequent queries

**Risk 3: Concurrent Access Issues**
- **Mitigation:** Load testing in Week 3
- **Fallback:** File locking implementation

**Risk 4: Security Vulnerabilities**
- **Mitigation:** Security test suite in Week 4
- **Fallback:** Manual penetration testing

### 9.6 Next Steps

**Immediate Actions (This Week):**
1. Create `Testing/` directory structure
2. Set up pytest configuration
3. Import performance baselines
4. Begin daemon monitoring implementation

**Short-Term (Next 2 Weeks):**
5. Complete P0 validation work (44 hours)
6. Set up CI/CD pipeline
7. Create first automated E2E tests

**Medium-Term (Next Month):**
8. Complete P1 validation work (24 hours)
9. Security audit and testing
10. Production readiness sign-off

---

**Document Owner:** Test Strategy Architect
**Review Frequency:** Weekly during implementation
**Next Review:** After Week 1 completion
**Approval Required From:** System Architect, QA Lead

**Status:** Ready for Implementation
