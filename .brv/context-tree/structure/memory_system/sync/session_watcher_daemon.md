## Relations
@structure/memory_system/memory_v2_heat_system.md
@structure/architecture/hooks/ai_lifecycle_hooks.md

## Raw Concept
**Task:**
Implement real-time session synchronization to long-term memory

**Changes:**
- Introduced real-time conversation sync via file watcher to bypass OpenClaw hook limitations

**Files:**
- ~/.openclaw/workspace/scripts/session_watcher.py

**Flow:**
OpenClaw Session (JSONL) -> Session Watcher -> Thanos memory_v2 -> Semantic Search Index

**Timestamp:** 2026-01-31

## Narrative
### Structure
- Script: ~/.openclaw/workspace/scripts/session_watcher.py
- State: ~/.openclaw/workspace/.session_watcher_state.json
- Target: Thanos memory_v2 (semantic search index)

### Dependencies
- OpenClaw session JSONL files
- Thanos memory_v2 (Neon/PostgreSQL)
- Python .venv environment

### Features
- Real-time conversation syncing to memory_v2
- State persistence in .session_watcher_state.json
- Background execution (daemon/nohup)
- Configurable sync interval (default 10s)
