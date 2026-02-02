## Relations
@structure/architecture/core_architecture_overview.md

## Raw Concept
**Task:**
Manage AI lifecycle hooks and real-time context injection

**Changes:**
- Corrected OpenClaw hook event availability and roadmap status
- Implemented robust fail-safe logging for hook failures

**Files:**
- Tools/thanos_orchestrator.py
- hooks/pre-tool-use/proactive_context.py

**Flow:**
Claude Event -> thanos_orchestrator.py hook -> handle_hook -> JSON Response -> Claude Context

**Timestamp:** 2026-01-31

## Narrative
### Structure
- Tools/thanos_orchestrator.py: Main hook handler (handle_hook)
- hooks/pre-tool-use/: Domain-specific pre-processing hooks (e.g., proactive_context.py)

### Dependencies
- Claude Code lifecycle events
- File-based state reading (StateReader)
- Local history logging (History/Sessions/)

### Features
- command:new, command:reset, command:stop, agent:bootstrap, gateway:startup (Available)
- morning-brief: Fast state-based context injection
- session-end: Automated session logging to markdown
- Multi-layer fail-safe error handling (always exit 0)
- Real-time sync currently limited to file watchers (per-turn events planned but not implemented)
