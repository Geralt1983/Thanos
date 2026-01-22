# Operator Daemon - Thanos v2.0 Phase 3

Background monitoring daemon that provides proactive alerts for health metrics, task deadlines, and procrastination patterns.

## Quick Start

```bash
# Test with dry-run (no alerts sent)
python3 Operator/daemon.py --dry-run --once --verbose

# Check status
python3 Operator/daemon.py --status

# Run continuous (development)
python3 Operator/daemon.py --config Operator/config.yaml

# Production: Install LaunchAgent (auto-start on boot)
./Operator/install_launchagent.sh
```

## Architecture

```
Operator Daemon
├── daemon.py           # Main daemon process with event loop
├── config.yaml         # Configuration (intervals, thresholds)
├── monitors/           # Health, task, pattern monitors
│   ├── health.py       # Oura readiness, sleep, HRV, stress
│   ├── tasks.py        # Deadlines, overdue, commitments
│   └── patterns.py     # Procrastination, energy trends
└── alerters/           # Alert delivery channels
    ├── telegram.py     # Telegram bot notifications
    ├── macos.py        # macOS notifications (osascript)
    └── journal.py      # Always-on journal logging
```

## Features

### Core Capabilities
- **AsyncIO Event Loop**: Non-blocking, efficient monitoring
- **Circuit Breakers**: Graceful degradation when MCP servers unavailable
- **Alert Deduplication**: 1-hour window to prevent spam
- **Quiet Hours**: Suppress non-critical alerts 10pm-7am
- **State Persistence**: Maintains state across restarts
- **Graceful Shutdown**: SIGTERM/SIGINT handling with cleanup

### Monitoring
- **Health**: Oura readiness, sleep quality, HRV, stress levels
- **Tasks**: Deadlines, overdue items, commitment tracking
- **Patterns**: Procrastination detection, energy trends

### Alerting
- **Telegram**: High/critical alerts with rich formatting
- **macOS Notifications**: Desktop notifications for high-priority items
- **Journal**: All alerts logged for audit trail

## Configuration

### File: `Operator/config.yaml`

```yaml
# Check intervals (seconds)
intervals:
  check_interval: 300       # Main loop (5 min)
  health_check: 900         # 15 min
  task_check: 900           # 15 min
  pattern_check: 1800       # 30 min

# Quiet hours
quiet_hours:
  enabled: true
  start: 22                 # 10 PM
  end: 7                    # 7 AM

# Alert deduplication
deduplication:
  window_seconds: 3600      # 1 hour
  max_alerts_per_run: 20    # Storm prevention

# Circuit breaker
circuit_breaker:
  failure_threshold: 3
  timeout_seconds: 60
  half_open_attempts: 1
```

## Command-Line Interface

### Basic Usage
```bash
# Show help
python3 Operator/daemon.py --help

# Run once and exit (testing)
python3 Operator/daemon.py --once

# Dry-run mode (no alerts sent)
python3 Operator/daemon.py --dry-run --once

# Verbose logging
python3 Operator/daemon.py --verbose

# Custom config
python3 Operator/daemon.py --config /path/to/config.yaml

# Status check
python3 Operator/daemon.py --status
```

### Testing Workflow
```bash
# 1. Test configuration loading
python3 Operator/daemon.py --status

# 2. Test one cycle with verbose output
python3 Operator/daemon.py --dry-run --once --verbose

# 3. Test continuous mode (Ctrl+C to stop)
python3 Operator/daemon.py --dry-run --verbose

# 4. Check logs
tail -f logs/operator.log
```

## State Files

### `State/operator_state.json`
```json
{
  "last_run": "2026-01-20T20:22:27",
  "run_count": 42,
  "total_alerts": 156,
  "uptime_start": "2026-01-20T08:00:00",
  "recent_dedup_keys": {
    "health:readiness_low": "2026-01-20T20:20:00"
  },
  "monitor_states": {
    "health": {
      "last_check": "2026-01-20T20:22:27",
      "duration_ms": 250,
      "alerts_generated": 1
    }
  },
  "circuit_states": {
    "workos": "closed",
    "oura": "closed"
  }
}
```

### `logs/operator.log`
```
2026-01-20 20:22:27 - operator - INFO - Check cycle complete: 3 alerts sent (0.5s)
2026-01-20 20:27:27 - operator - INFO - Check cycle complete: 0 alerts sent (0.3s)
```

## LaunchAgent Installation

For production use, install as a macOS LaunchAgent:

```bash
# Install (auto-start on boot)
./Operator/install_launchagent.sh

# Start manually
launchctl start com.thanos.operator

# Stop
launchctl stop com.thanos.operator

# Check status
launchctl list | grep thanos.operator

# View logs
tail -f logs/operator_stdout.log
tail -f logs/operator_stderr.log

# Uninstall
launchctl unload ~/Library/LaunchAgents/com.thanos.operator.plist
rm ~/Library/LaunchAgents/com.thanos.operator.plist
```

## Circuit Breaker Integration

The daemon uses circuit breakers to handle MCP server failures gracefully:

```
┌─────────────────────────────────────┐
│         Circuit States              │
├─────────────────────────────────────┤
│ CLOSED   → Normal operation         │
│ OPEN     → Using cached data        │
│ HALF_OPEN → Testing recovery        │
└─────────────────────────────────────┘

Fallback Strategy:
1. Try MCP cache DB (fast, local)
2. Try direct API call (slow, requires network)
3. Skip check this cycle, log warning
```

## Alert Deduplication

Prevents alert spam by tracking recent alerts:

```python
# Dedup key format: "{alert_type}:{entity_id}"
"health:readiness_low"
"task:deadline_overdue:123"
"pattern:procrastination:write_report"

# Window: 1 hour (configurable)
# Same alert won't trigger twice within window
```

## Quiet Hours

Automatically suppresses non-critical alerts during sleep hours:

```yaml
quiet_hours:
  enabled: true
  start: 22    # 10 PM
  end: 7       # 7 AM
```

- **Critical alerts**: Always sent (readiness <40, commitment violations)
- **High/Medium/Low**: Suppressed during quiet hours
- **Journal**: All alerts logged regardless of quiet hours

## Error Handling

### Transient Errors
- Network timeouts → Retry with exponential backoff
- MCP busy → Circuit breaker opens, use cache

### Configuration Errors
- Invalid YAML → Fail fast with clear error message
- Missing env vars → Log warning, use defaults

### Data Errors
- Corrupted cache → Skip check, log warning
- Invalid JSON → Fallback to empty state

### Service Unavailable
- MCP down → Circuit breaker opens, graceful degradation
- Postgres offline → Use cache, continue with other monitors

## Monitoring the Daemon

### Health Check
```bash
# Status endpoint
python3 Operator/daemon.py --status

# Check PID
cat logs/operator.pid

# Check uptime
launchctl list | grep thanos.operator
```

### Metrics
```json
{
  "run_count": 42,
  "total_alerts": 156,
  "uptime_seconds": 3600,
  "circuit_states": {
    "workos": "closed",
    "oura": "closed"
  },
  "dedup_cache_size": 12
}
```

### Logs
```bash
# Real-time monitoring
tail -f logs/operator.log

# Error search
grep ERROR logs/operator.log

# Circuit breaker events
grep "Circuit" logs/operator.log
```

## Development

### Adding a Monitor

1. Create `Operator/monitors/my_monitor.py`:
```python
from typing import List
from Operator.daemon import Alert

class MyMonitor:
    def __init__(self, circuit):
        self.circuit = circuit
        self.checker_name = "my_monitor"

    async def check(self) -> List[Alert]:
        alerts = []
        # Your monitoring logic here
        return alerts
```

2. Update `Operator/monitors/__init__.py`:
```python
from .my_monitor import MyMonitor
__all__ = ['MyMonitor']
```

3. Enable in `daemon.py`:
```python
if monitor_name == 'my_monitor':
    self.monitors.append(MyMonitor(self.circuits['workos']))
```

### Adding an Alerter

1. Create `Operator/alerters/my_alerter.py`:
```python
class MyAlerter:
    async def send_batch(self, alerts):
        for alert in alerts:
            # Your alert delivery logic
            pass
```

2. Register in `daemon.py`

## Troubleshooting

### Daemon won't start
```bash
# Check Python version
python3 --version  # Requires 3.7+

# Check dependencies
pip install pyyaml  # For config loading

# Check permissions
chmod +x Operator/daemon.py

# Check logs
cat logs/operator_stderr.log
```

### No alerts being sent
```bash
# Verify dry-run is disabled
python3 Operator/daemon.py --status | grep dry_run

# Check quiet hours
python3 Operator/daemon.py --status | grep is_quiet_hours

# Check dedup cache
python3 Operator/daemon.py --status | grep dedup_cache_size

# Test with verbose
python3 Operator/daemon.py --dry-run --once --verbose
```

### Circuit breaker stuck open
```bash
# Check circuit states
python3 Operator/daemon.py --status | grep circuit_states

# Verify MCP servers
# WorkOS: Check postgres connection
# Oura: Check cache DB at ~/.oura-cache/oura-health.db

# Manual circuit reset (restart daemon)
launchctl stop com.thanos.operator
launchctl start com.thanos.operator
```

### High CPU usage
```bash
# Check interval (shouldn't be < 60 seconds)
grep check_interval Operator/config.yaml

# Check monitor count
python3 Operator/daemon.py --status | grep enabled_monitors

# Disable verbose logging
# Edit config.yaml: logging.level = "INFO"
```

## Future Enhancements

### Phase 4 (Week 5)
- [ ] Machine learning for personalized thresholds
- [ ] Predictive alerts based on patterns
- [ ] Health check HTTP endpoint (port 8765)
- [ ] Metrics export (Prometheus format)
- [ ] Email alerter integration

### Phase 5 (Week 6+)
- [ ] Web dashboard for real-time monitoring
- [ ] Mobile app notifications (iOS/Android)
- [ ] Integration with Google Calendar
- [ ] Burnout risk scoring
- [ ] Smart scheduling recommendations

## Related Documentation

- [Architecture Design](./ARCHITECTURE.md) - Complete system design
- [Monitors Guide](./monitors/README.md) - Monitor implementation details
- [Alerters Guide](./alerters/README.md) - Alerter configuration
- [Circuit Breakers](../Tools/circuit_breaker.py) - Resilience patterns

## Support

For issues or questions:
1. Check logs: `tail -f logs/operator.log`
2. Test with dry-run: `python3 Operator/daemon.py --dry-run --once --verbose`
3. Review architecture: `cat Operator/ARCHITECTURE.md`
