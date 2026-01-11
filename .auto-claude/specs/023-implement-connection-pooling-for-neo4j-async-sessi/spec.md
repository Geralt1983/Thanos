# Implement connection pooling for Neo4j async sessions

## Overview

The Neo4j adapter creates a new session for each operation via `async with self._driver.session()`. While the driver has built-in pooling, session creation overhead can be reduced by reusing sessions for related operations within a request context.

## Rationale

Each graph operation (create_commitment, record_decision, find_related) opens a new session. In memory_integration.py's store_memory, up to 4 separate sessions may be created for a single memory storage operation (vector + decision + entity creation + linking). Session pooling or batching reduces network round-trips.

---
*This spec was created from ideation and is pending detailed specification.*
