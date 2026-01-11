# Neo4j Python Driver Async Session Best Practices

## Research Summary
*Compiled: 2026-01-11*
*Neo4j Python Driver Version: 6.0*

This document summarizes official Neo4j recommendations for async session management, connection pooling, and transaction handling patterns.

---

## 1. Driver vs Session Lifecycle

### Driver (Heavyweight - Reuse)
- **Cost**: Expensive to create, contains connection pools
- **Pattern**: **ONE driver instance per application** (singleton pattern)
- **Lifetime**: Long-lived, survives entire application lifecycle
- **Thread Safety**: Thread-safe and can be shared across async tasks
- **Key Principle**: "Drivers are heavyweight objects that expect to be reused many times"

### Session (Lightweight - Create/Destroy)
- **Cost**: Cheap to create and destroy
- **Pattern**: **Create new session per operation or request context**
- **Lifetime**: Short-lived, typically within a single request or operation
- **Concurrency Safety**: **NOT concurrency-safe** - one session per async task
- **Key Principle**: "Sessions are cheap—create and close as many sessions as you like"

### Critical Finding
**Connection pooling exists at the DRIVER level, not the session level.** Sessions borrow connections from the driver's connection pool. Creating a new session does NOT create a new connection—it borrows from the existing pool.

---

## 2. Connection Pooling Architecture

### How It Works
1. Driver maintains a connection pool (configured at driver creation)
2. Sessions borrow connections from the pool when executing queries
3. Connections return to pool when session closes or transaction completes
4. Multiple sessions can reuse the same underlying connections

### Configuration Parameters
```python
AsyncGraphDatabase.driver(
    uri,
    auth=auth,
    max_connection_pool_size=100,      # Default: 100
    connection_acquisition_timeout=60,  # Seconds
    connection_timeout=30,              # Seconds (should be < acquisition_timeout)
    liveness_check_timeout=None         # Balance between performance and stale connections
)
```

### Best Practices
- **Pool Size**: Set based on concurrency needs (each `.run()` borrows one connection)
- **Timeout Tuning**: `connection_timeout` < `connection_acquisition_timeout`
- **Liveness Checks**: Balance between extra network round-trips and stale connection risk
- **Serverless Environments**: Reduce connections to minimize cold startup time

---

## 3. Async Session Management

### Proper Usage Pattern
```python
# CORRECT: Use async context managers
async with driver.session(database="mydb") as session:
    result = await session.run("MATCH (n) RETURN n")
    records = await result.data()
```

### Session Lifecycle Rules
1. **Always use async context managers** (`async with`) for automatic cleanup
2. **Sessions must not span multiple async tasks** - create separate sessions for concurrent operations
3. **Sessions should be short-lived** - create, use, close within single operation/request
4. **Always specify database** - avoid extra round-trip to determine default database

### Concurrency Constraints
⚠️ **CRITICAL**: AsyncSession is **NOT concurrency-safe**

```python
# INCORRECT: Sharing session across tasks
async with driver.session() as session:
    await asyncio.gather(
        task1(session),  # ❌ Multiple tasks using same session
        task2(session)   # ❌ This is unsafe!
    )

# CORRECT: Separate sessions for concurrent tasks
async def task_with_own_session():
    async with driver.session() as session:  # ✅ Each task gets its own session
        ...

await asyncio.gather(
    task_with_own_session(),
    task_with_own_session()
)
```

### Error Handling Pattern
```python
async with driver.session() as session:
    tx = await session.begin_transaction()
    try:
        # Execute queries
        await tx.run("CREATE ...")
        await tx.commit()
    except asyncio.CancelledError:
        tx.cancel()  # Force close connections
        raise
    except Exception:
        await tx.rollback()
        raise
```

---

## 4. Transaction Patterns

### Three Approaches with Performance/Robustness Tradeoffs

#### A. Managed Transactions (RECOMMENDED - Most Robust)
```python
async def create_person(tx, name):
    await tx.run("CREATE (p:Person {name: $name})", name=name)

async with driver.session() as session:
    await session.execute_write(create_person, "Alice")
```

**Characteristics:**
- ✅ Automatic retry with exponential backoff
- ✅ Proper routing in clusters (write to leader, read from any)
- ✅ Best for production robustness
- ⚠️ Slight overhead from retry logic

**Use for:** Production code, operations requiring retries

#### B. Grouped Transactions (Balanced)
```python
async with driver.session() as session:
    async with await session.begin_transaction() as tx:
        await tx.run("CREATE (p1:Person {name: 'Alice'})")
        await tx.run("CREATE (p2:Person {name: 'Bob'})")
        await tx.run("MATCH (p1:Person {name: 'Alice'}), (p2:Person {name: 'Bob'}) CREATE (p1)-[:KNOWS]->(p2)")
        await tx.commit()
```

**Characteristics:**
- ✅ Better throughput (single transaction unit)
- ✅ Isolation from concurrent operations
- ⚠️ No automatic retries
- ⚠️ All-or-nothing (one failure rolls back all)

**Use for:** Batching related operations that should succeed/fail together

#### C. Auto-commit Transactions (Fastest - Least Robust)
```python
async with driver.session() as session:
    await session.run("CREATE (p:Person {name: 'Alice'})")
```

**Characteristics:**
- ✅ Highest throughput
- ✅ Still isolated from other concurrent queries
- ❌ No automatic retries on failure
- ❌ Must handle failures manually

**Use for:** High-throughput scenarios where occasional failures are acceptable

### Performance Impact
**Benchmark results from documentation:**
- Individual transactions: Slowest (each query = separate transaction overhead)
- Grouped transactions: 2-5x faster for multi-query operations
- Auto-commit: Fastest, but trades robustness for speed

---

## 5. Optimization Strategies

### Current Pattern (One Session Per Operation)
```python
async def create_commitment(self, data):
    async with self._driver.session() as session:
        result = await session.run("CREATE (c:Commitment {data: $data}) RETURN c", data=data)

async def record_decision(self, data):
    async with self._driver.session() as session:
        result = await session.run("CREATE (d:Decision {data: $data}) RETURN d", data=data)
```

**Analysis:**
- ✅ Follows Neo4j best practices
- ✅ Properly leverages driver connection pool
- ✅ Each session borrows from existing connection pool
- ⚠️ Multiple session creations add overhead
- ⚠️ Each operation is a separate transaction

### Optimization Opportunity: Session Context Reuse
```python
async def store_memory_batch(self, memory_data):
    """Execute multiple related operations in a single session context."""
    async with self._driver.session(database="neo4j") as session:
        async with await session.begin_transaction() as tx:
            # All operations in one transaction, one session
            commitment = await tx.run("CREATE (c:Commitment ...) RETURN c")
            decision = await tx.run("CREATE (d:Decision ...) RETURN d")
            await tx.run("MATCH (c:Commitment), (d:Decision) WHERE ... CREATE (c)-[:LEADS_TO]->(d)")
            await tx.commit()
```

**Benefits:**
- ✅ Single session creation overhead
- ✅ Single transaction (atomic batch)
- ✅ Still uses driver connection pool
- ✅ Better for related operations in single request

### When to Use Each Pattern

**Create New Session (Current Pattern):**
- Independent operations
- Long time between operations
- Operations from different requests/contexts
- Need isolation between operations

**Reuse Session (Optimization):**
- Multiple related operations in single request
- Operations should be atomic (all succeed or all fail)
- High-frequency batch operations
- Memory storage with multiple graph updates

---

## 6. Causal Consistency with Bookmarks

### Use Case
When you need to ensure that a read query sees the results of a previous write query, even across different sessions.

### Pattern
```python
# Using default bookmark manager (driver-level)
async with driver.session() as session:
    await session.execute_write(create_person, "Alice")
    # Bookmark automatically captured

async with driver.session() as session:
    # This read will see Alice even if it routes to a different cluster node
    result = await session.execute_read(find_person, "Alice")

# Manual bookmark management
async with driver.session() as session1:
    await session1.execute_write(create_person, "Alice")
    bookmarks = await session1.last_bookmarks()

async with driver.session(bookmarks=bookmarks) as session2:
    result = await session2.execute_read(find_person, "Alice")
```

**When to use:**
- Cluster deployments
- Read-after-write consistency required
- Operations across different sessions

---

## 7. Performance Best Practices Summary

### Do's ✅
1. **Create ONE driver instance** - reuse for entire application
2. **Create many sessions** - they're cheap and use connection pool
3. **Use async context managers** - ensure proper cleanup
4. **Specify database on all queries** - avoid extra round-trip
5. **Use managed transactions** - get automatic retries
6. **Batch related operations** - group into single transaction when appropriate
7. **Route reads to any reader** - distribute load in clusters
8. **Use lazy loading** - for large result sets
9. **Use concurrency** - multiple async tasks with separate sessions
10. **Configure pool size** - based on expected concurrency

### Don'ts ❌
1. **Don't create multiple drivers** - wastes resources, expensive
2. **Don't share sessions across async tasks** - not concurrency-safe
3. **Don't keep sessions open long** - they should be short-lived
4. **Don't convert large results to lists eagerly** - use lazy loading
5. **Don't use asyncio.shield() with sessions** - can cause undefined behavior
6. **Don't set liveness_check_timeout too low** - causes extra network round-trips
7. **Don't forget error handling** - especially asyncio.CancelledError
8. **Don't omit database parameter** - causes extra request

---

## 8. Implementation Recommendations for Thanos Project

### Current State Analysis
- ✅ Using `async with self._driver.session()` pattern (correct)
- ✅ Single driver instance per adapter (correct)
- ⚠️ Each operation creates new session (follows best practice but has optimization opportunity)
- ⚠️ Multiple operations in single request (e.g., memory storage) use separate sessions

### Recommended Optimization Strategy

**Option 1: Session Context Manager (RECOMMENDED)**
Add optional session parameter to methods for context reuse:

```python
async def create_commitment(self, data, session=None):
    async def _execute(tx):
        return await tx.run("CREATE ...", data=data)

    if session:
        return await session.execute_write(_execute)
    else:
        async with self._driver.session() as session:
            return await session.execute_write(_execute)
```

**Benefits:**
- Backward compatible (session parameter is optional)
- Allows batch operations to reuse session
- Still supports individual operation calls
- Maintains proper transaction semantics

**Option 2: Explicit Batch Methods**
Create new methods specifically for batch operations:

```python
async def store_memory_batch(self, vector_data, decision_data, entity_data):
    """Store complete memory graph in single transaction."""
    async with self._driver.session(database="neo4j") as session:
        async with await session.begin_transaction() as tx:
            # All operations in one transaction
            ...
```

**Benefits:**
- Clear intent for batch operations
- Single transaction ensures atomicity
- Explicit API for performance-critical paths

**Recommendation:** Use **Option 1** as it provides maximum flexibility while maintaining backward compatibility.

---

## Sources

- [Neo4j Python Driver Performance Recommendations](https://neo4j.com/docs/python-manual/current/performance/)
- [Run Concurrent Transactions - Neo4j Python Driver Manual](https://neo4j.com/docs/python-manual/current/concurrency/)
- [Async API Documentation — Neo4j Python Driver 6.0](https://neo4j.com/docs/api/python-driver/current/async_api.html)
- [Neo4j Driver Best Practices](https://neo4j.com/blog/developer/neo4j-driver-best-practices/)
- [Driver Configuration Best Practices](https://deepwiki.com/neo4j/neo4j-python-driver/5.1-driver-configuration)
- [Advanced Connection Information](https://neo4j.com/docs/python-manual/current/connect-advanced/)
- [Run Your Own Transactions](https://neo4j.com/docs/python-manual/current/transactions/)
- [Coordinate Parallel Transactions](https://neo4j.com/docs/python-manual/current/bookmarks/)

---

## Key Insights for Implementation

1. **"Connection pooling" is a misnomer** - Neo4j driver already has connection pooling. The real opportunity is **session reuse within request contexts**.

2. **Sessions are already cheap** - Creating sessions doesn't create connections. The overhead is minimal but can be eliminated for batch operations.

3. **Transaction grouping is the real win** - Batching multiple operations into a single transaction reduces overhead more than session reuse alone.

4. **Backward compatibility is critical** - Existing code using individual sessions is correct and should continue to work.

5. **Context-based pattern is ideal** - Optional session parameter allows both patterns:
   - Individual calls: `await adapter.create_commitment(data)` (creates own session)
   - Batch calls: Use shared session for multiple operations

6. **Managed transactions provide retries** - Using `execute_read/write` instead of direct `run()` adds robustness for production environments.
