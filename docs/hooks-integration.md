# Thanos Orchestrator - Claude Hooks Integration Design

## Executive Summary

This document describes how to integrate the Thanos Python orchestrator (`Tools/thanos_orchestrator.py`) with the existing Claude Code lifecycle hooks system. The goal is to enable the orchestrator to be invoked from hooks for morning briefings, conversation logging, and commitment extraction.

---

## Current Hook Architecture Summary

### Hook System Overview

Claude Code uses a JSON-based hook configuration in `~/.claude/settings.json` that triggers shell scripts at specific lifecycle events:

```json
{
  "hooks": {
    "SessionStart": [...],
    "Stop": [...],
    "UserPromptSubmit": [...]
  }
}
```

### Existing Hook Files (`~/.claude/hooks/`)

| File | Event | Purpose |
|------|-------|---------|
| `on-session-start.sh` | SessionStart | Context injection, morning brief triggers, Oura health data |
| `on-session-end.sh` | Stop | Session logging to History/, memory service sync |
| `extract-commitments.sh` | UserPromptSubmit | Pattern-based commitment detection |
| `agent-router.sh` | UserPromptSubmit | Suggests appropriate agent based on keywords |
| `workos-memory-bridge.sh` | Manual | Syncs WorkOS data to semantic memory |
| `track-token-usage.sh` | Stop | Records token usage statistics |

### Hook Output Contract

Hooks communicate with Claude Code via JSON on stdout:

```json
{
  "hookSpecificOutput": {
    "additionalContext": "Context injected into conversation..."
  }
}
```

### Key Services

1. **Memory Service** (`localhost:8766`): Semantic memory storage and retrieval
2. **WorkOS MCP**: Task and habit management via MCP protocol
3. **claude-mem**: Plugin providing observation history and context injection

---

## Integration Points Identified

### 1. Morning Briefing Integration

**Current State**: `on-session-start.sh` detects morning sessions and suggests running `/pa:daily`

**Proposed Enhancement**: Directly invoke orchestrator for automated brief generation

**Integration Point**: SessionStart hook

**Flow**:
```
SessionStart triggered
  └─> Check if morning (5-12) AND first session
        └─> Invoke: python thanos_orchestrator.py run pa:daily --brief-only
              └─> Return formatted brief as additionalContext
```

### 2. Session History Logging

**Current State**: `on-session-end.sh` creates minimal session log template

**Proposed Enhancement**: Use orchestrator to generate intelligent session summary

**Integration Point**: Stop hook

**Flow**:
```
Stop triggered
  └─> Collect session transcript (if available)
        └─> Invoke: python thanos_orchestrator.py summarize-session
              └─> Write to History/Sessions/{timestamp}.md
              └─> Store summary to memory service
```

### 3. Commitment Extraction Enhancement

**Current State**: `extract-commitments.sh` uses regex patterns for basic extraction

**Proposed Enhancement**: Use Claude API via orchestrator for semantic extraction

**Integration Point**: UserPromptSubmit hook (or post-session)

**Flow**:
```
UserPromptSubmit triggered
  └─> Fast regex check (existing behavior)
  └─> Queue for semantic analysis if ambiguous
        └─> Post-session: python thanos_orchestrator.py extract-commitments --transcript
```

### 4. Agent Routing Enhancement

**Current State**: `agent-router.sh` matches keywords to suggest agents

**Proposed Enhancement**: Use orchestrator's agent detection with full context

**Integration Point**: UserPromptSubmit hook

---

## Recommended Implementation Approach

### Phase 1: Hook Wrapper Script

Create a Python wrapper that can be called from bash hooks:

**File**: `~/.claude/hooks/thanos-hook.py`

```python
#!/usr/bin/env python3
"""
Thanos Hook Wrapper - Bridge between bash hooks and Python orchestrator.
Called from shell hook scripts to invoke orchestrator functions.

Usage:
    thanos-hook.py morning-brief
    thanos-hook.py session-end --transcript /path/to/transcript
    thanos-hook.py extract-commitments --message "..."
"""

import sys
import os
import json
from pathlib import Path

# Add Thanos to path
THANOS_DIR = Path.home() / "Projects" / "Thanos"
sys.path.insert(0, str(THANOS_DIR))

def output_hook_response(context: str):
    """Output JSON in Claude hook format."""
    print(json.dumps({
        "hookSpecificOutput": {
            "additionalContext": context
        }
    }))

def morning_brief():
    """Generate morning brief via orchestrator."""
    try:
        from Tools.thanos_orchestrator import ThanosOrchestrator

        orchestrator = ThanosOrchestrator(str(THANOS_DIR))

        # Check if command exists
        cmd = orchestrator.find_command("pa:daily")
        if not cmd:
            return

        # Build brief context without full API call (fast path)
        # Read state files directly for quick injection
        state_dir = THANOS_DIR / "State"

        brief_parts = []

        # Current focus
        focus_file = state_dir / "CurrentFocus.md"
        if focus_file.exists():
            content = focus_file.read_text()
            if "Primary focus" in content:
                for line in content.split('\n'):
                    if "Primary focus" in line:
                        brief_parts.append(f"FOCUS: {line.split(':')[-1].strip()}")
                        break

        # Today's priorities
        today_file = state_dir / "Today.md"
        if today_file.exists():
            content = today_file.read_text()
            if "Top 3" in content or "Priorities" in content:
                brief_parts.append("Today's priorities are set - review State/Today.md")

        # Pending commitments
        commit_file = state_dir / "Commitments.md"
        if commit_file.exists():
            content = commit_file.read_text()
            pending = content.count("- [ ]")
            if pending > 0:
                brief_parts.append(f"COMMITMENTS: {pending} pending items")

        if brief_parts:
            context = "[MORNING_CONTEXT] " + " | ".join(brief_parts)
            context += "\n[ACTION] Consider running /pa:daily for full morning briefing"
            output_hook_response(context)

    except Exception as e:
        # Log error but don't break hook chain
        log_file = Path.home() / ".claude" / "logs" / "hooks.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, 'a') as f:
            f.write(f"[thanos-hook] morning_brief error: {e}\n")

def session_end(transcript_path: str = None):
    """Log session end with optional summary."""
    try:
        from datetime import datetime

        history_dir = THANOS_DIR / "History" / "Sessions"
        history_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now()
        filename = now.strftime("%Y-%m-%d-%H%M.md")

        # Create session log
        session_log = f"""# Session: {now.strftime("%Y-%m-%d %H:%M")}

## Duration
- Ended: {now.strftime("%H:%M")}

## Topics
- [Auto-populated from conversation analysis]

## Commitments Made
- See State/Commitments.md for any new items

## State Changes
- [Files modified during session]

---
*Auto-logged by Thanos*
"""

        log_path = history_dir / filename
        if not log_path.exists():  # Don't overwrite
            log_path.write_text(session_log)

    except Exception as e:
        log_file = Path.home() / ".claude" / "logs" / "hooks.log"
        with open(log_file, 'a') as f:
            f.write(f"[thanos-hook] session_end error: {e}\n")

def extract_commitments(message: str):
    """Enhanced commitment extraction using orchestrator patterns."""
    # This would use the orchestrator's agent routing
    # For now, delegate to the existing bash script behavior
    pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: thanos-hook.py <command> [args]", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == "morning-brief":
        morning_brief()
    elif command == "session-end":
        transcript = sys.argv[2] if len(sys.argv) > 2 else None
        session_end(transcript)
    elif command == "extract-commitments":
        if len(sys.argv) > 2:
            extract_commitments(sys.argv[2])
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)
```

### Phase 2: Modified Session-Start Hook

**File**: `~/.claude/hooks/on-session-start.sh` (additions)

```bash
# Add after existing morning check (around line 105)

# Try Python orchestrator for richer morning context
if is_morning && is_first_session_today; then
    THANOS_HOOK="$HOME/Projects/Thanos/hooks/thanos-hook.py"
    if [ -x "$THANOS_HOOK" ]; then
        ORCHESTRATOR_CONTEXT=$(python3 "$THANOS_HOOK" morning-brief 2>/dev/null) || true
        if [ -n "$ORCHESTRATOR_CONTEXT" ]; then
            log "Injected orchestrator morning context"
            # Merge with existing context
            context="$context\n$ORCHESTRATOR_CONTEXT"
        fi
    fi
fi
```

### Phase 3: Enhanced Session-End Hook

**File**: `~/.claude/hooks/on-session-end.sh` (additions)

```bash
# Replace create_session_log function or add after it

# Enhanced session logging via orchestrator
log_session_via_orchestrator() {
    THANOS_HOOK="$HOME/Projects/Thanos/hooks/thanos-hook.py"
    if [ -x "$THANOS_HOOK" ]; then
        python3 "$THANOS_HOOK" session-end 2>/dev/null || {
            log "Orchestrator session logging failed, using fallback"
            create_session_log
        }
    else
        create_session_log
    fi
}
```

### Phase 4: Add Orchestrator Hook Entry Point

**File**: `/Users/jeremy/Projects/Thanos/hooks/thanos-hook.py`

Create the wrapper script in the Thanos project itself:

```python
#!/usr/bin/env python3
# See Phase 1 code above
```

---

## Code Snippets for Key Integrations

### 1. Fast State Reader (for hook performance)

```python
# Tools/state_reader.py
"""Fast state file reader for hooks - no API calls."""

from pathlib import Path
from typing import Dict, List, Optional
import re

class StateReader:
    """Read Thanos state files quickly for hook context."""

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir

    def get_current_focus(self) -> Optional[str]:
        """Extract current focus from CurrentFocus.md."""
        path = self.state_dir / "CurrentFocus.md"
        if not path.exists():
            return None

        content = path.read_text()
        match = re.search(r'\*\*Primary focus\*\*:\s*(.+)', content)
        return match.group(1).strip() if match else None

    def get_pending_commitments(self) -> int:
        """Count pending commitments."""
        path = self.state_dir / "Commitments.md"
        if not path.exists():
            return 0
        return path.read_text().count("- [ ]")

    def get_todays_top3(self) -> List[str]:
        """Extract today's top 3 priorities."""
        path = self.state_dir / "Today.md"
        if not path.exists():
            path = self.state_dir / "CurrentFocus.md"
        if not path.exists():
            return []

        content = path.read_text()
        items = []
        in_top3 = False

        for line in content.split('\n'):
            if 'Top 3' in line or 'Priorities' in line:
                in_top3 = True
                continue
            if in_top3:
                if line.startswith('#'):
                    break
                match = re.match(r'^[\d\.\-\*]\s*\[[ x]\]\s*(.+)', line)
                if match:
                    items.append(match.group(1).split('|')[0].strip())
                    if len(items) >= 3:
                        break

        return items

    def get_quick_context(self) -> Dict:
        """Get quick context summary for hooks."""
        return {
            "focus": self.get_current_focus(),
            "pending_commitments": self.get_pending_commitments(),
            "top3": self.get_todays_top3()
        }
```

### 2. Orchestrator CLI Extension

```python
# Add to thanos_orchestrator.py main block

elif sys.argv[1] == "hook":
    if len(sys.argv) < 3:
        print("Usage: thanos_orchestrator.py hook <event> [args]")
        sys.exit(1)

    event = sys.argv[2]
    t = ThanosOrchestrator()

    if event == "morning-brief":
        # Fast path: no API, just state reading
        from Tools.state_reader import StateReader
        reader = StateReader(t.base_dir / "State")
        ctx = reader.get_quick_context()

        parts = []
        if ctx["focus"]:
            parts.append(f"FOCUS: {ctx['focus']}")
        if ctx["top3"]:
            parts.append(f"TOP3: {', '.join(ctx['top3'][:2])}...")
        if ctx["pending_commitments"] > 0:
            parts.append(f"PENDING: {ctx['pending_commitments']} commitments")

        if parts:
            print(json.dumps({
                "hookSpecificOutput": {
                    "additionalContext": "[THANOS] " + " | ".join(parts)
                }
            }))

    elif event == "session-end":
        # Log session to History
        from datetime import datetime
        history_dir = t.base_dir / "History" / "Sessions"
        history_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now()
        log_file = history_dir / f"{now.strftime('%Y-%m-%d-%H%M')}.md"

        if not log_file.exists():
            log_file.write_text(f"""# Session: {now.strftime("%Y-%m-%d %H:%M")}

## Summary
- Duration: ~unknown
- Topics: [auto-detected]

## State Changes
- Check git diff for file changes

---
*Auto-logged by Thanos Orchestrator*
""")
            print(f"Session logged: {log_file}")
```

### 3. settings.json Hook Configuration

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/jeremy/.claude/hooks/on-session-start.sh",
            "timeout": 30
          },
          {
            "type": "command",
            "command": "python3 /Users/jeremy/Projects/Thanos/Tools/thanos_orchestrator.py hook morning-brief",
            "timeout": 10
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/jeremy/.claude/hooks/on-session-end.sh",
            "timeout": 30
          },
          {
            "type": "command",
            "command": "python3 /Users/jeremy/Projects/Thanos/Tools/thanos_orchestrator.py hook session-end",
            "timeout": 15
          },
          {
            "type": "command",
            "command": "/Users/jeremy/.claude/hooks/track-token-usage.sh record",
            "timeout": 10
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/jeremy/.claude/hooks/extract-commitments.sh",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

---

## Architecture Diagram

```
                    Claude Code Session
                           │
    ┌──────────────────────┼──────────────────────┐
    │                      │                      │
    ▼                      ▼                      ▼
SessionStart          UserPromptSubmit          Stop
    │                      │                      │
    ▼                      ▼                      ▼
on-session-start.sh   extract-commitments.sh   on-session-end.sh
    │                      │                      │
    ├─ Oura data           ├─ Regex patterns      ├─ Session log
    ├─ Memory query        ├─ Agent routing       ├─ Memory sync
    └─ Morning trigger     └─ Commitment capture  └─ Token tracking
    │                                             │
    ▼                                             ▼
thanos_orchestrator.py                   thanos_orchestrator.py
hook morning-brief                       hook session-end
    │                                             │
    ├─ StateReader                                ├─ History/Sessions/
    ├─ Quick context                              └─ Summary generation
    └─ additionalContext
           │
           ▼
    ┌─────────────────┐
    │  Claude Code    │
    │  Conversation   │
    │  Context        │
    └─────────────────┘
```

---

## Implementation Checklist

### Phase 1: Foundation (Day 1)
- [ ] Create `Tools/state_reader.py` for fast state access
- [ ] Add `hook` subcommand to `thanos_orchestrator.py`
- [ ] Test hook output format matches Claude expectations

### Phase 2: Session Start Integration (Day 2)
- [ ] Create `hooks/thanos-hook.py` wrapper
- [ ] Modify `on-session-start.sh` to call orchestrator
- [ ] Test morning brief injection

### Phase 3: Session End Integration (Day 3)
- [ ] Implement `session-end` hook event
- [ ] Test History logging
- [ ] Verify no performance regression

### Phase 4: Full Integration (Day 4)
- [ ] Update `~/.claude/settings.json` with orchestrator hooks
- [ ] Test full session lifecycle
- [ ] Document any edge cases

---

## Performance Considerations

1. **Hook Timeout**: Claude hooks have configurable timeouts (default 30s)
   - Orchestrator hooks should complete in <5s
   - Use fast StateReader, not API calls

2. **No API Calls in Hooks**: The orchestrator's `chat()` method should NOT be called from hooks
   - Hooks should only read/write local files
   - Use pre-computed summaries

3. **Graceful Degradation**: All hook integrations must:
   - Exit cleanly on error (exit 0)
   - Log errors to `~/.claude/logs/hooks.log`
   - Fall back to basic behavior if orchestrator unavailable

4. **Python Path**: Ensure orchestrator can be imported:
   ```bash
   export PYTHONPATH="$HOME/Projects/Thanos:$PYTHONPATH"
   ```

---

## Future Enhancements

1. **Semantic Commitment Extraction**: Use Claude API post-session for deeper analysis
2. **Conversation Summarization**: Generate AI summaries for History logs
3. **Pattern Detection**: Surface productivity patterns from aggregated session data
4. **Cross-Session Context**: Maintain context across sessions via memory service

---

## Related Files

| File | Purpose |
|------|---------|
| `/Users/jeremy/Projects/Thanos/Tools/thanos_orchestrator.py` | Main orchestrator |
| `/Users/jeremy/Projects/Thanos/Tools/claude_api_client.py` | API client |
| `/Users/jeremy/Projects/Thanos/Tools/daily-brief.ts` | TypeScript brief generator |
| `/Users/jeremy/.claude/hooks/on-session-start.sh` | Session start hook |
| `/Users/jeremy/.claude/hooks/on-session-end.sh` | Session end hook |
| `/Users/jeremy/.claude/settings.json` | Hook configuration |
| `/Users/jeremy/Projects/Thanos/State/*.md` | State files |
| `/Users/jeremy/Projects/Thanos/History/Sessions/` | Session logs |

---

*Document created: 2026-01-08*
*Last updated: 2026-01-08*
