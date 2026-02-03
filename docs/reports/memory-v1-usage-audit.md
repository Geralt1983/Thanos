# Memory V1 Usage Audit (2026-02-03)

Legacy `memory/` (mem0 pipeline) is still referenced in multiple components.
This audit lists files that import or reference the V1 modules.

## V1 References (non-exhaustive)

- `Tools/telegram_bot.py`
- `Tools/thanos_orchestrator.py`
- `Tools/context_injector.py`
- `Tools/router_executor.py`
- `Tools/session_manager.py`
- `Tools/proactive_context.py`
- `Tools/conversation_summarizer.py`
- `Tools/memory_checkpoint.py`
- `Tools/intelligent_memory.py`
- `Tools/context_optimizer.py`
- `Tools/memory_router.py`
- `Tools/command_handlers/history_search_handler.py`
- `Tools/memory/service.py`
- `Tools/memory/brain_dump_ingester.py`
- `Tools/memory/__init__.py`
- `Tools/memory/unified_query.py`
- `Tools/adapters/workos_memory_bridge.py`
- `Tools/adapters/calendar_memory_bridge.py`
- `Tools/brain_dump/pipeline.py`
- `scripts/migrate_to_memory_v2.py`
- `memory/pipelines/ingest.py`
- `memory/mcp/memory_tool.py`
- `memory/handlers/hey_pocket.py`
- `memory/handlers/telegram_handler.py`

## Recommendation

Before deprecating V1, decide whether V1 ingestion is still required as an input
to V2. If not, migrate these call sites to `Tools/memory_v2` or isolate V1 in
`memory/legacy/` and provide compatibility wrappers.

## Status

- Compatibility wrapper implemented in `memory/services/memory_service.py` to route
  V1 calls into Memory V2.
