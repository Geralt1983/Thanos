## Relations
@structure/architecture/core_architecture_overview.md
@structure/mcp_servers/mcp_server_infrastructure.md

## Raw Concept
**Task:**
Finalize Memory V2 heat system integration and clear technical debt

**Changes:**
- Removed _degraded flag and fallback logic from heat.py
- Created and executed backfill_heat.py for legacy data migration
- Backfilled 22,354 memories with recency-based heat values

**Files:**
- Tools/memory_v2/heat.py
- Tools/memory_v2/backfill_heat.py

**Flow:**
Memory Access -> Boost Heat -> Update payload -> Recurring Decay (Cron) -> Surface Cold/Hot (Native heat values only)

**Timestamp:** 2026-01-31

## Narrative
### Structure
- Tools/memory_v2/heat.py: Main service logic (Cleaned: removed _degraded flag)
- Tools/memory_v2/backfill_heat.py: Batch migration tool
- HeatScore range: 0.05 (floor) to 2.0 (ceiling)

### Dependencies
- Neon Database (PostgreSQL)
- psycopg2 for database connectivity
- Consolidated thanos_memories table payload JSONB

### Features
- Heat-based decay (heat *= 0.97 daily)
- Access boost (heat += 0.15)
- Mention boost (heat += 0.10)
- Memory pinning (never decay, heat = 2.0)
- ADHD-optimized surfacing of neglected memories
- **Fully Unified**: No legacy fallback calculations; all 22,000+ memories now have native heat values.
