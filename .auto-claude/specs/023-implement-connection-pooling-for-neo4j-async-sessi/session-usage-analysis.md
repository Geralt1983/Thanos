# Neo4j Session Usage Analysis

**Task:** Subtask 1.1 - Analyze current session usage patterns
**Date:** 2026-01-11
**Analyzed Files:**
- `Tools/adapters/neo4j_adapter.py`
- `Tools/memos.py`
- `tests/unit/test_memory_integration.py`

---

## Executive Summary

**Current State:** The Neo4j adapter creates a new session for every operation using `async with self._driver.session()`. While a `Neo4jSessionContext` class already exists (lines 51-121 in neo4j_adapter.py), **none of the adapter methods currently support optional session parameters**, so the context manager cannot be used to reuse sessions across operations.

**Key Finding:** The `MemOS.remember()` method can create **up to 5+ separate sessions** for a single memory storage operation when entities are involved, representing significant session overhead that could be eliminated through session reuse.

---

## 1. Current Session Creation Pattern

### 1.1 Standard Pattern (Used by All Methods)

All Neo4j adapter methods follow this pattern:

```python
async def _some_method(self, args: Dict[str, Any]) -> ToolResult:
    # Build query and params...

    async with self._driver.session() as session:
        result = await session.run(query, params)
        record = await result.single()  # or result.data()

    return ToolResult.ok(...)
```

**Characteristics:**
- Creates a new session for every call
- Session is automatically closed when context exits
- No session reuse across operations
- No transaction batching

### 1.2 Exception: `_record_pattern()` Method

The `_record_pattern()` method (lines 647-719) **already demonstrates session reuse** within a single method:

```python
async def _record_pattern(self, args: Dict[str, Any]) -> ToolResult:
    # Opens ONE session
    async with self._driver.session() as session:
        # First query: Check for existing pattern
        result = await session.run(check_query, {...})
        existing = await result.single()

        if existing:
            # Second query: Update pattern (same session)
            await session.run(update_query, {...})
        else:
            # Second query: Create pattern (same session)
            await session.run(create_query, {...})

    return ToolResult.ok(...)
```

This is a **good pattern** that reduces 2 session creations to 1.

---

## 2. Methods Analyzed

### 2.1 Commitment Operations

| Method | Lines | Sessions Created | Transaction Pattern |
|--------|-------|------------------|---------------------|
| `_create_commitment` | 466-504 | 1 per call | Single query |
| `_complete_commitment` | 506-535 | 1 per call | Single UPDATE query |
| `_get_commitments` | 537-569 | 1 per call | Single SELECT query |

### 2.2 Decision Operations

| Method | Lines | Sessions Created | Transaction Pattern |
|--------|-------|------------------|---------------------|
| `_record_decision` | 575-611 | 1 per call | Single CREATE query |
| `_get_decisions` | 613-641 | 1 per call | Single SELECT query |

### 2.3 Pattern Operations

| Method | Lines | Sessions Created | Transaction Pattern |
|--------|-------|------------------|---------------------|
| `_record_pattern` | 647-719 | 1 per call | **2 queries in same session** ✅ |
| `_get_patterns` | 721-749 | 1 per call | Single SELECT query |

### 2.4 Session Operations

| Method | Lines | Sessions Created | Transaction Pattern |
|--------|-------|------------------|---------------------|
| `_start_session` | 755-780 | 1 per call | Single CREATE query |
| `_end_session` | 782-809 | 1 per call | Single UPDATE query |

### 2.5 Relationship Operations

| Method | Lines | Sessions Created | Transaction Pattern |
|--------|-------|------------------|---------------------|
| `_link_nodes` | 815-848 | 1 per call | Single CREATE query |
| `_find_related` | 850-870 | 1 per call | Single graph traversal query |

### 2.6 Entity Operations

| Method | Lines | Sessions Created | Transaction Pattern |
|--------|-------|------------------|---------------------|
| `_create_entity` | 895-931 | 1 per call | Single MERGE query |
| `_get_entity_context` | 933-958 | 1 per call | Complex query with OPTIONAL MATCH |

### 2.7 Query Operations

| Method | Lines | Sessions Created | Transaction Pattern |
|--------|-------|------------------|---------------------|
| `_query_graph` | 872-889 | 1 per call | User-provided query (read-only) |
| `health_check` | 968-984 | 1 per call | Simple RETURN 1 query |

---

## 3. Real-World Usage Analysis: MemOS Class

### 3.1 The `remember()` Method - Critical Performance Issue

**File:** `Tools/memos.py`, lines 173-296

This method demonstrates the **worst-case scenario** for session overhead:

```python
async def remember(self, content: str, memory_type: str, domain: str,
                   entities: List[str] = None, metadata: Dict = None):

    # Session 1: Create the main memory node
    if memory_type == "commitment":
        result = await self._neo4j.call_tool("create_commitment", {...})
    elif memory_type == "decision":
        result = await self._neo4j.call_tool("record_decision", {...})
    elif memory_type == "pattern":
        result = await self._neo4j.call_tool("record_pattern", {...})

    # Sessions 2-N: For EACH entity
    for entity in entities:
        # Session N: Create entity
        await self._neo4j.call_tool("create_entity", {
            "name": entity, "type": "auto", "domain": domain
        })

        # Session N+1: Link entity to memory node
        await self._neo4j.call_tool("link_nodes", {
            "from_id": result.data["id"],
            "relationship": "INVOLVES",
            "to_id": f"entity_{entity}"
        })
```

**Session Count Example:**
- Store decision with 2 entities (e.g., ["Python", "FastAPI"]):
  - 1 session: `record_decision`
  - 1 session: `create_entity("Python")`
  - 1 session: `link_nodes` (decision -> Python)
  - 1 session: `create_entity("FastAPI")`
  - 1 session: `link_nodes` (decision -> FastAPI)
  - **Total: 5 sessions for one remember() call**

- Store commitment with 3 entities:
  - 1 + (3 × 2) = **7 sessions**

### 3.2 The `recall()` Method

**File:** `Tools/memos.py`, lines 298-401

```python
async def recall(self, query: str, memory_types: List[str], ...):
    for memory_type in memory_types:  # e.g., ["commitment", "decision", "pattern"]
        if memory_type == "commitment":
            result = await self._neo4j.call_tool("get_commitments", {...})
        elif memory_type == "decision":
            result = await self._neo4j.call_tool("get_decisions", {...})
        elif memory_type == "pattern":
            result = await self._neo4j.call_tool("get_patterns", {...})
```

**Session Count:**
- Querying 3 memory types = **3 sessions**
- Each query is independent, could be batched into 1 session

### 3.3 Other MemOS Methods

| Method | Sessions per Call | Could Batch? |
|--------|-------------------|--------------|
| `relate()` | 1 | N/A (single operation) |
| `reflect()` | 1 | N/A (single operation) |
| `get_entity_context()` | 1 | N/A (single operation) |

---

## 4. Opportunities for Session Reuse

### 4.1 HIGH IMPACT: Batch Operations in `remember()`

**Current:** 1 + (2 × N entities) sessions
**With Session Context:** 1 session for all operations
**Potential Reduction:** 80-85% fewer sessions for typical use cases

**Implementation Strategy:**
```python
async with adapter.session_context() as session:
    # Create main node
    result = await adapter._record_decision(args, session=session)

    # Create and link all entities in same session
    for entity in entities:
        await adapter._create_entity(entity_args, session=session)
        await adapter._link_nodes(link_args, session=session)
```

### 4.2 MEDIUM IMPACT: Batch Reads in `recall()`

**Current:** N sessions (one per memory type)
**With Session Context:** 1 session for all reads
**Potential Reduction:** 66% fewer sessions for 3-type query

**Implementation Strategy:**
```python
async with adapter.session_context() as session:
    for memory_type in memory_types:
        results = await adapter._get_commitments(args, session=session)
```

### 4.3 LOW IMPACT: Single-Operation Methods

Methods like `relate()`, `reflect()`, and `get_entity_context()` already use only 1 session per call. Session reuse won't help unless they're called multiple times in sequence.

---

## 5. Existing Infrastructure

### 5.1 Neo4jSessionContext Class (Already Implemented!)

**File:** `Tools/adapters/neo4j_adapter.py`, lines 51-121

The infrastructure for session pooling **already exists** but is not being used:

```python
class Neo4jSessionContext:
    """
    Async context manager for Neo4j session lifecycle management.

    Supports:
    - Automatic session creation/cleanup
    - Session reuse across operations
    - Exception-safe resource handling
    - Optional transaction batching
    """

    async def __aenter__(self):
        self._session = self._adapter._driver.session(database=self._database)
        if self._batch_transaction:
            self._transaction = await self._session.begin_transaction()
            return self._transaction
        return self._session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._transaction:
            if exc_type is None:
                await self._transaction.commit()
            else:
                await self._transaction.rollback()
        if self._session:
            await self._session.close()
        return False
```

**Usage Pattern (from docstring):**
```python
# Pattern A: Session reuse for multiple independent operations
async with adapter.session_context() as session:
    await adapter._create_entity(entity_data, session=session)
    await adapter._link_nodes(link_data, session=session)

# Pattern B: Atomic batch with transaction guarantee
async with adapter.session_context(batch_transaction=True) as tx:
    await adapter._create_entity(entity_data, session=tx)
    await adapter._link_nodes(link_data, session=tx)
```

### 5.2 Session Context Factory Method

**File:** `Tools/adapters/neo4j_adapter.py`, lines 266-291

```python
def session_context(self, batch_transaction: bool = False) -> Neo4jSessionContext:
    """Create a session context manager for session reuse."""
    return Neo4jSessionContext(
        adapter=self,
        database=self._database,
        batch_transaction=batch_transaction
    )
```

**Status:** ✅ Implemented, not used

---

## 6. Blockers Preventing Session Reuse

### 6.1 No Session Parameter Support

**Problem:** None of the adapter methods accept an optional `session` parameter.

**Current signature:**
```python
async def _create_commitment(self, args: Dict[str, Any]) -> ToolResult:
    async with self._driver.session() as session:
        # ...
```

**Needed signature:**
```python
async def _create_commitment(
    self,
    args: Dict[str, Any],
    session: Optional[Any] = None  # <-- Add this
) -> ToolResult:
    if session is None:
        # Backward compatibility: create own session
        async with self._driver.session() as session:
            return await self._execute_create_commitment(session, args)
    else:
        # Use provided session
        return await self._execute_create_commitment(session, args)
```

### 6.2 Session Creation Embedded in Method Logic

All methods have the session creation (`async with self._driver.session()`) tightly coupled with the query logic. This needs to be refactored to:

1. Accept optional session parameter
2. Create session only if not provided
3. Extract query execution into separate logic

---

## 7. Recommendations

### 7.1 Priority 1: Add Optional Session Parameters

**Effort:** Medium (affects all 14 methods)
**Impact:** High (enables all session reuse patterns)
**Subtasks:** 3.1, 3.2, 3.3, 3.4 in implementation plan

Update all adapter methods to:
```python
async def _method_name(
    self,
    args: Dict[str, Any],
    session: Optional[Any] = None
) -> ToolResult:
```

### 7.2 Priority 2: Update MemOS to Use Session Context

**Effort:** Small
**Impact:** High (immediate 80% reduction in remember() overhead)
**Subtask:** 3.5 in implementation plan

Refactor `MemOS.remember()` to use session context:
```python
async with self._neo4j.session_context() as session:
    # All operations in one session
```

### 7.3 Priority 3: Create Batch Operation Helpers

**Effort:** Small
**Impact:** Medium (improves developer experience)
**Subtask:** 3.5 in implementation plan

Add convenience methods like:
```python
async def store_memory_batch(
    self,
    memory_data: Dict,
    entities: List[str]
) -> ToolResult:
    async with self.session_context(batch_transaction=True) as tx:
        # Atomic batch operation
        result = await self._record_decision(memory_data, session=tx)
        for entity in entities:
            await self._create_entity({"name": entity}, session=tx)
            await self._link_nodes({...}, session=tx)
```

---

## 8. Performance Impact Estimates

### 8.1 Session Creation Overhead

Based on Neo4j driver documentation:
- Session creation: ~1-5ms overhead per session
- Transaction overhead: ~0.5-2ms per transaction

### 8.2 Expected Improvements

| Scenario | Current | With Pooling | Improvement |
|----------|---------|--------------|-------------|
| `remember()` with 2 entities | 5 sessions (~25ms overhead) | 1 session (~5ms overhead) | **80% reduction** |
| `recall()` with 3 types | 3 sessions (~15ms overhead) | 1 session (~5ms overhead) | **66% reduction** |
| Bulk import (100 memories) | 500+ sessions | 1-10 sessions | **95%+ reduction** |

**Note:** These are overhead estimates only, not including actual query execution time.

---

## 9. Risk Mitigation

### 9.1 Backward Compatibility

**Risk:** Breaking existing code that calls adapter methods
**Mitigation:** Make session parameter optional (defaults to None), maintain current behavior when not provided

### 9.2 Transaction Boundaries

**Risk:** Accidentally batching operations that should be in separate transactions
**Mitigation:**
- Default to session reuse (independent transactions)
- Only use `batch_transaction=True` when atomicity is required
- Document when to use each pattern

### 9.3 Session Leaks

**Risk:** Sessions not cleaned up on errors
**Mitigation:**
- Already handled by `Neo4jSessionContext.__aexit__`
- Comprehensive error handling tests (subtask 4.5)

---

## 10. Next Steps

1. ✅ **Completed:** Document current session usage patterns (this document)
2. **Next:** Research Neo4j async session best practices (subtask 1.2)
3. **Next:** Design session pooling strategy (subtask 1.3)
4. **Implementation:** Add session parameters to all methods (phase 3)
5. **Validation:** Performance benchmarks (subtask 4.4)

---

## Appendix: Method Session Usage Matrix

| Method | Current Sessions | Queries per Session | Session Reuse Opportunity | Priority |
|--------|------------------|---------------------|---------------------------|----------|
| `_create_commitment` | 1 | 1 | Medium (used in batches) | P1 |
| `_complete_commitment` | 1 | 1 | Low (single operation) | P2 |
| `_get_commitments` | 1 | 1 | High (used in recall) | P1 |
| `_record_decision` | 1 | 1 | High (used in remember) | P1 |
| `_get_decisions` | 1 | 1 | High (used in recall) | P1 |
| `_record_pattern` | 1 | 2 | Medium (already optimized) | P2 |
| `_get_patterns` | 1 | 1 | High (used in recall/reflect) | P1 |
| `_start_session` | 1 | 1 | Low (single operation) | P3 |
| `_end_session` | 1 | 1 | Low (single operation) | P3 |
| `_link_nodes` | 1 | 1 | High (used in remember loop) | P1 |
| `_find_related` | 1 | 1 | Medium (single operation) | P2 |
| `_query_graph` | 1 | 1 | Medium (user queries) | P2 |
| `_create_entity` | 1 | 1 | High (used in remember loop) | P1 |
| `_get_entity_context` | 1 | 1 | Medium (single operation) | P2 |

**Priority Legend:**
- P1: High priority - used in batch operations or tight loops
- P2: Medium priority - used occasionally in batches
- P3: Low priority - typically single operations
