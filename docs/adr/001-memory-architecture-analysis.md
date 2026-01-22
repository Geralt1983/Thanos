# ADR-001: Memory Architecture Analysis

**Date:** 2026-01-20
**Status:** Investigation Complete
**Investigator:** Hive Mind Swarm (Researcher + Analyst + Architect)

## Executive Summary

Thanos has **TWO SEPARATE MEMORY ARCHITECTURES** that are not connected:

1. **claude-mem plugin** (thedotmack) - **ACTIVE & WORKING**
2. **Thanos Memory System** (Tools/memory/) - **CODE EXISTS BUT NEVER INITIALIZED**

## The Mystery Solved

**Why search works but observations don't persist to disk:**
- Observations ARE persisting - just not to JSONL files
- They're stored in ChromaDB via the claude-mem worker service
- Storage location: `~/.claude/Memory/vectors/chroma.sqlite3` (593KB, actively used)
- MCP tools query the worker API, which returns results from ChromaDB

## Architecture Inventory

### 1. claude-mem Plugin (WORKING)

**Location:** `plugins/cache/thedotmack/claude-mem/9.0.0/`

**Components:**
- Worker service on port 37777 (configured in `settings.json`)
- ChromaDB storage: `~/.claude/Memory/vectors/`
  - 3 collections (UUIDs)
  - `chroma.sqlite3` (593KB, last modified Jan 19)
- Hooks:
  - `SessionStart`: `context-hook.js`, `user-message-hook.js`
  - `UserPromptSubmit`: `new-hook.js`
  - `PostToolUse`: `save-hook.js` ← **This captures observations**
  - `Stop`: `summary-hook.js`

**Data Flow:**
```
PostToolUse Hook
  ↓
save-hook.js (minified)
  ↓
POST http://127.0.0.1:37777/api/sessions/observations
  ↓
Worker Service
  ↓
ChromaDB (chroma.sqlite3)
```

**MCP Tools:**
- `mcp__plugin_claude-mem_mcp-search__search` - Search by query
- `mcp__plugin_claude-mem_mcp-search__timeline` - Get context around results
- `mcp__plugin_claude-mem_mcp-search__get_observations` - Fetch full details by IDs

**Status:** ✅ FUNCTIONAL

### 2. Thanos Memory System (NOT INITIALIZED)

**Location:** `Tools/memory/`

**Components:**
- `store.py` - SQLite storage (activities, struggles, values, relationships, summaries)
- `service.py` - High-level API coordinating SQLite + ChromaDB
- `capture.py` - Memory capture pipeline
- `query_parser.py` - Natural language query parsing
- `struggle_detector.py` - Pattern detection
- `value_detector.py` - Value extraction
- `brain_dump_ingester.py` - Full brain dump processing
- `models.py` - Data models

**Intended Storage:**
- SQLite: `State/memory.db` ← **DOES NOT EXIST**
- ChromaDB: Lazy-loaded via `Tools/adapters/chroma_adapter.py`
  - Would use `~/.claude/Memory/vectors/` (same as claude-mem!)

**Status:** 📁 CODE EXISTS, NEVER INSTANTIATED

### 3. Other State Databases

**Active Databases:**
- `State/thanos_unified.db` - Tasks, commitments, ideas, notes (NOT memory observations)
- `State/thanos_memory.db` - Unknown schema
- `State/relationships.db` - Graph relationships
- `State/reasoning_bank.db` - Pattern learning

## The Gap Analysis

### What You Asked For
"Why observations aren't persisting to disk despite search functionality working"

### What We Found

**Observations ARE persisting** - just not where expected:
- ❌ NOT in `.claude-mem/observations.jsonl` (this file doesn't exist in this architecture)
- ✅ YES in `~/.claude/Memory/vectors/chroma.sqlite3` (ChromaDB vector database)

**Why Search Works:**
- MCP tools query the claude-mem worker service API
- Worker retrieves from ChromaDB
- ChromaDB has 3 collections with embedded observations
- Search returns results from vector similarity + metadata filters

**Why No JSONL Files:**
- claude-mem plugin uses ChromaDB as primary storage
- No intermediate JSONL export configured
- Observations stored as vectors + metadata in SQLite (ChromaDB format)

**Why Thanos Memory Isn't Used:**
- Never initialized in any startup script
- No code path creates `MemoryService` instance
- Completely separate from claude-mem plugin
- Would conflict if both tried to use `~/.claude/Memory/vectors/`

## Architectural Insights

### Design Conflict

**Two philosophies colliding:**

1. **claude-mem**: MCP plugin + worker service + ChromaDB
   - Centralized worker process
   - Vector-first storage
   - Hook-driven capture
   - API-based retrieval

2. **Thanos Memory**: Hybrid SQLite + ChromaDB
   - Direct Python library usage
   - Structured data (SQLite) + vectors (ChromaDB)
   - Programmatic capture via `MemoryService`
   - Query language support

**Both want to own:**
- ChromaDB storage at `~/.claude/Memory/vectors/`
- Observation capture pipeline
- Search/retrieval interface

### Why This Happened

1. **Incremental Evolution**
   - Started with claude-mem plugin for memory
   - Later designed custom Thanos memory system
   - Never migrated or integrated

2. **Parallel Development**
   - Tools/memory/ built as standalone system
   - Never connected to claude-mem hooks
   - No bootstrap code to initialize MemoryService

3. **Hidden Dependencies**
   - Search "works" via MCP tools → masks the architectural split
   - Hooks run silently → no visibility into what's stored where
   - Multiple DBs in State/ → unclear which is authoritative

## Data Flow Diagram

### Current State (claude-mem)
```
Claude Code
   ↓
PostToolUse Hook
   ↓
save-hook.js
   ↓
Worker Service (port 37777)
   ↓
ChromaDB (~/.claude/Memory/vectors/chroma.sqlite3)
   ↑
   |
MCP Search Tools ← You query here
```

### Intended State (Thanos Memory - NOT ACTIVE)
```
Thanos Code
   ↓
MemoryService.capture_activity()
   ↓
MemoryCapturePipeline
   ├→ SQLite (State/memory.db) - structured data
   └→ ChromaDB (via ChromaAdapter) - vectors
       ↑
       |
MemoryService.search() ← Would query here
```

## Recommendations

### Option 1: Keep claude-mem, Abandon Thanos Memory (LOW EFFORT)

**Pros:**
- Already working
- MCP integration functional
- No migration needed

**Cons:**
- Lose custom Thanos features:
  - Struggle detection
  - Value tracking
  - Natural language queries
  - Day/week summaries
  - Relationship graphs
- No SQLite structured storage
- Limited to claude-mem's observation model

**Effort:** 0 hours (status quo)

### Option 2: Migrate to Thanos Memory (HIGH VALUE)

**Pros:**
- Full-featured memory system
- Hybrid storage (SQLite + vectors)
- Custom query language
- ADHD-optimized features
- Extensible architecture

**Cons:**
- Must disable claude-mem hooks
- Migration path for existing observations
- More complex architecture

**Effort:** 8-12 hours

**Migration Steps:**
1. Export claude-mem observations from ChromaDB
2. Initialize MemoryService in startup hooks
3. Import observations into Thanos Memory
4. Disable claude-mem PostToolUse hook
5. Add Thanos capture hooks

### Option 3: Hybrid Integration (MOST COMPLEX)

Use claude-mem for capture, Thanos Memory for analysis.

**Architecture:**
```
claude-mem hooks → Worker API → ChromaDB (capture)
                                   ↓
              Periodic sync to Thanos Memory (SQLite + analysis)
                                   ↓
                        MemoryService queries (rich features)
```

**Pros:**
- Keep working hooks
- Add Thanos features
- Best of both worlds

**Cons:**
- Most complex
- Sync latency
- Two sources of truth

**Effort:** 16-20 hours

### Option 4: Replace claude-mem with Lightweight Bridge (RECOMMENDED)

Build minimal hooks that call Thanos Memory directly.

**Architecture:**
```
Custom PostToolUse Hook
   ↓
MemoryService.capture_activity()
   ├→ SQLite (structured)
   └→ ChromaDB (vectors)
      ↑
      |
MCP Tools → Thin wrapper → MemoryService.search()
```

**Pros:**
- Full Thanos features
- No worker service dependency
- Direct Python control
- Simpler architecture

**Cons:**
- Rewrite hooks
- Replace MCP tools
- Migration needed

**Effort:** 12-16 hours

**Implementation:**
1. Create `hooks/post-tool/thanos-memory.sh`
2. Call `Tools/memory/capture.py` CLI
3. Build MCP server for MemoryService
4. Update `.claude/settings.json` to use new tools
5. Migrate existing observations

## Recommendations Priority

**For Jeremy's ADHD workflow:**

1. **Option 4** (Replace claude-mem) - **RECOMMENDED**
   - Cleanest long-term architecture
   - Full feature set
   - Maintainable by you

2. **Option 2** (Pure Thanos) - **ALSO GOOD**
   - Simpler than Option 4
   - No MCP complexity
   - Direct Python calls

3. **Option 1** (Status Quo) - **IF TIME IS CRITICAL**
   - Zero effort
   - Works today
   - Limited features

4. **Option 3** (Hybrid) - **AVOID**
   - Too complex
   - Sync issues
   - Hard to debug

## Next Steps

1. **Decide** on option (recommend #4 or #2)
2. **If migrating:**
   - Export claude-mem observations
   - Test Thanos Memory in isolation
   - Build migration script
   - Create new hooks
3. **If keeping claude-mem:**
   - Delete unused Tools/memory/ code
   - Document the actual architecture
   - Accept feature limitations

## Files to Update

**For Option 4 (Replace claude-mem):**
- Create: `hooks/post-tool/thanos-memory-capture.sh`
- Create: `Tools/memory/cli.py` (capture CLI interface)
- Create: `mcp-servers/thanos-memory-mcp/` (MCP server)
- Update: `.claude/settings.json` (swap MCP tools)
- Update: `hooks/session-start/thanos-start.sh` (init MemoryService)

**For Option 2 (Pure Thanos):**
- Create: `hooks/post-tool/thanos-memory-capture.sh`
- Create: `Tools/memory/cli.py`
- Update: `hooks/session-start/thanos-start.sh`
- Update: `.claude/settings.json` (remove claude-mem)

## Conclusion

**The system isn't broken - you have TWO systems.**

- claude-mem: Working but limited
- Thanos Memory: Feature-rich but dormant

**Decision needed:** Commit to one architecture.

**Recommendation:** Build Thanos Memory hooks (Option 4) for full ADHD-optimized features.

---

**Investigation Team:**
- Researcher Agent: Codebase exploration
- Analyst Agent: Gap analysis
- Architect Agent: Recommendations

**Swarm ID:** `swarm_1768945470493_bvhz6wwen`
**Completed:** 2026-01-20 16:37 EST
