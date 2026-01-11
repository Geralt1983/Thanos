"""
Neo4j AuraDB adapter for Thanos MemOS knowledge graph.

Provides graph database operations for:
- Commitments (promises, deadlines, accountability)
- Decisions (choices, rationale, alternatives)
- Patterns (recurring behaviors, learnings)
- Sessions (conversations, context)
- Entities (people, clients, projects)

Uses async Neo4j driver for non-blocking operations.
"""

from dataclasses import dataclass
from datetime import datetime
import os
from typing import Any, Dict, List, Optional

from .base import BaseAdapter, ToolResult


# Neo4j driver import with graceful fallback
try:
    from neo4j import AsyncGraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    AsyncGraphDatabase = None


@dataclass
class GraphNode:
    """Represents a node in the knowledge graph."""
    id: str
    labels: List[str]
    properties: Dict[str, Any]


@dataclass
class GraphRelationship:
    """Represents a relationship between nodes."""
    type: str
    from_id: str
    to_id: str
    properties: Dict[str, Any]


# =============================================================================
# Graph Schema Definition
# =============================================================================

GRAPH_SCHEMA = {
    "nodes": {
        "Commitment": {
            "description": "A promise or obligation",
            "properties": {
                "id": "string (required)",
                "content": "string - what was committed",
                "to_whom": "string - person/entity committed to",
                "deadline": "datetime - when due",
                "status": "string - pending|completed|failed|deferred",
                "domain": "string - work|personal|health|relationship",
                "priority": "integer - 1-5 scale",
                "created_at": "datetime",
                "completed_at": "datetime (optional)"
            }
        },
        "Decision": {
            "description": "A choice made with reasoning",
            "properties": {
                "id": "string (required)",
                "content": "string - what was decided",
                "rationale": "string - why this choice",
                "alternatives": "list[string] - other options considered",
                "domain": "string - work|personal|health|relationship",
                "confidence": "float - 0.0-1.0",
                "created_at": "datetime",
                "outcome": "string (optional) - how it turned out"
            }
        },
        "Pattern": {
            "description": "A recurring behavior or insight",
            "properties": {
                "id": "string (required)",
                "description": "string - the pattern observed",
                "type": "string - behavior|trigger|success|failure",
                "domain": "string - work|personal|health|relationship",
                "frequency": "string - daily|weekly|situational",
                "first_observed": "datetime",
                "last_observed": "datetime",
                "strength": "float - 0.0-1.0 confidence"
            }
        },
        "Session": {
            "description": "A conversation or work session",
            "properties": {
                "id": "string (required)",
                "agent": "string - which agent (ops|coach|strategy|health)",
                "summary": "string - what was discussed",
                "started_at": "datetime",
                "ended_at": "datetime",
                "tokens_used": "integer",
                "mood": "string (optional) - user mood during session"
            }
        },
        "Entity": {
            "description": "A person, project, or organization",
            "properties": {
                "id": "string (required)",
                "name": "string",
                "type": "string - person|client|project|organization",
                "domain": "string (optional)",
                "notes": "string (optional)",
                "created_at": "datetime"
            }
        },
        "EnergyState": {
            "description": "Energy/mood snapshot",
            "properties": {
                "id": "string (required)",
                "level": "string - high|medium|low",
                "timestamp": "datetime",
                "context": "string (optional)",
                "oura_readiness": "integer (optional)",
                "oura_sleep": "integer (optional)"
            }
        }
    },
    "relationships": {
        "LEADS_TO": "Commitment|Decision -> Commitment|Decision|Pattern",
        "INVOLVES": "Commitment|Decision|Session -> Entity",
        "LEARNED_FROM": "Pattern -> Session|Decision",
        "DURING": "Commitment|Decision -> Session",
        "IMPACTS": "Decision -> Commitment",
        "PRECEDED_BY": "Session -> Session",
        "AT_ENERGY": "Session -> EnergyState"
    }
}


class Neo4jAdapter(BaseAdapter):
    """
    Neo4j AuraDB adapter for Thanos knowledge graph.

    Provides graph-based memory operations:
    - Store and query commitments, decisions, patterns
    - Track relationships between entities
    - Find paths and patterns across time
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        Initialize Neo4j connection.

        Args:
            uri: Neo4j connection URI (defaults to NEO4J_URL env var)
            username: Neo4j username (defaults to NEO4J_USERNAME env var)
            password: Neo4j password (defaults to NEO4J_PASSWORD env var)
        """
        if not NEO4J_AVAILABLE:
            raise ImportError(
                "neo4j package not installed. Install with: pip install neo4j"
            )

        self._uri = uri or os.getenv("NEO4J_URL")
        self._username = username or os.getenv("NEO4J_USERNAME", "neo4j")
        self._password = password or os.getenv("NEO4J_PASSWORD")

        if not self._uri:
            raise ValueError("Neo4j URI not provided. Set NEO4J_URL env var.")
        if not self._password:
            raise ValueError("Neo4j password not provided. Set NEO4J_PASSWORD env var.")

        self._driver = AsyncGraphDatabase.driver(
            self._uri,
            auth=(self._username, self._password)
        )

    @property
    def name(self) -> str:
        return "neo4j"

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return available graph operations."""
        return [
            # Commitment operations
            {
                "name": "create_commitment",
                "description": "Create a new commitment in the knowledge graph",
                "parameters": {
                    "content": {"type": "string", "required": True},
                    "to_whom": {"type": "string", "required": False},
                    "deadline": {"type": "string", "required": False},
                    "domain": {"type": "string", "required": False},
                    "priority": {"type": "integer", "required": False}
                }
            },
            {
                "name": "complete_commitment",
                "description": "Mark a commitment as completed",
                "parameters": {
                    "commitment_id": {"type": "string", "required": True},
                    "outcome": {"type": "string", "required": False}
                }
            },
            {
                "name": "get_commitments",
                "description": "Get commitments, optionally filtered",
                "parameters": {
                    "status": {"type": "string", "required": False},
                    "domain": {"type": "string", "required": False},
                    "to_whom": {"type": "string", "required": False},
                    "limit": {"type": "integer", "required": False}
                }
            },
            # Decision operations
            {
                "name": "record_decision",
                "description": "Record a decision with rationale",
                "parameters": {
                    "content": {"type": "string", "required": True},
                    "rationale": {"type": "string", "required": True},
                    "alternatives": {"type": "array", "required": False},
                    "domain": {"type": "string", "required": False},
                    "confidence": {"type": "number", "required": False}
                }
            },
            {
                "name": "get_decisions",
                "description": "Get decisions, optionally filtered",
                "parameters": {
                    "domain": {"type": "string", "required": False},
                    "days": {"type": "integer", "required": False},
                    "limit": {"type": "integer", "required": False}
                }
            },
            # Pattern operations
            {
                "name": "record_pattern",
                "description": "Record a behavioral pattern or insight",
                "parameters": {
                    "description": {"type": "string", "required": True},
                    "type": {"type": "string", "required": True},
                    "domain": {"type": "string", "required": False},
                    "frequency": {"type": "string", "required": False}
                }
            },
            {
                "name": "get_patterns",
                "description": "Get recorded patterns",
                "parameters": {
                    "type": {"type": "string", "required": False},
                    "domain": {"type": "string", "required": False},
                    "limit": {"type": "integer", "required": False}
                }
            },
            # Session operations
            {
                "name": "start_session",
                "description": "Record start of a conversation session",
                "parameters": {
                    "agent": {"type": "string", "required": True},
                    "mood": {"type": "string", "required": False}
                }
            },
            {
                "name": "end_session",
                "description": "Record end of session with summary",
                "parameters": {
                    "session_id": {"type": "string", "required": True},
                    "summary": {"type": "string", "required": True},
                    "tokens_used": {"type": "integer", "required": False}
                }
            },
            # Relationship operations
            {
                "name": "link_nodes",
                "description": "Create a relationship between nodes",
                "parameters": {
                    "from_id": {"type": "string", "required": True},
                    "relationship": {"type": "string", "required": True},
                    "to_id": {"type": "string", "required": True},
                    "properties": {"type": "object", "required": False}
                }
            },
            # Query operations
            {
                "name": "find_related",
                "description": "Find nodes related to a given node",
                "parameters": {
                    "node_id": {"type": "string", "required": True},
                    "relationship_type": {"type": "string", "required": False},
                    "depth": {"type": "integer", "required": False}
                }
            },
            {
                "name": "query_graph",
                "description": "Execute a custom Cypher query (read-only)",
                "parameters": {
                    "query": {"type": "string", "required": True},
                    "parameters": {"type": "object", "required": False}
                }
            },
            # Entity operations
            {
                "name": "create_entity",
                "description": "Create a person, client, or project entity",
                "parameters": {
                    "name": {"type": "string", "required": True},
                    "type": {"type": "string", "required": True},
                    "domain": {"type": "string", "required": False},
                    "notes": {"type": "string", "required": False}
                }
            },
            {
                "name": "get_entity_context",
                "description": "Get all context about an entity (commitments, decisions, etc)",
                "parameters": {
                    "name": {"type": "string", "required": True}
                }
            }
        ]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Route tool calls to appropriate handlers."""
        handlers = {
            "create_commitment": self._create_commitment,
            "complete_commitment": self._complete_commitment,
            "get_commitments": self._get_commitments,
            "record_decision": self._record_decision,
            "get_decisions": self._get_decisions,
            "record_pattern": self._record_pattern,
            "get_patterns": self._get_patterns,
            "start_session": self._start_session,
            "end_session": self._end_session,
            "link_nodes": self._link_nodes,
            "find_related": self._find_related,
            "query_graph": self._query_graph,
            "create_entity": self._create_entity,
            "get_entity_context": self._get_entity_context
        }

        handler = handlers.get(tool_name)
        if not handler:
            return ToolResult.fail(f"Unknown tool: {tool_name}")

        try:
            return await handler(arguments)
        except Exception as e:
            return ToolResult.fail(f"Neo4j error: {str(e)}")

    # =========================================================================
    # Commitment Operations
    # =========================================================================

    async def _create_commitment(self, args: Dict[str, Any]) -> ToolResult:
        """Create a new commitment node."""
        import uuid

        commitment_id = f"commitment_{uuid.uuid4().hex[:8]}"
        now = datetime.utcnow().isoformat()

        query = """
        CREATE (c:Commitment {
            id: $id,
            content: $content,
            to_whom: $to_whom,
            deadline: $deadline,
            domain: $domain,
            priority: $priority,
            status: 'pending',
            created_at: $created_at
        })
        RETURN c
        """

        params = {
            "id": commitment_id,
            "content": args["content"],
            "to_whom": args.get("to_whom", "self"),
            "deadline": args.get("deadline"),
            "domain": args.get("domain", "work"),
            "priority": args.get("priority", 3),
            "created_at": now
        }

        async with self._driver.session() as session:
            await session.run(query, params)

        return ToolResult.ok({
            "id": commitment_id,
            "message": f"Created commitment: {args['content'][:50]}..."
        })

    async def _complete_commitment(self, args: Dict[str, Any]) -> ToolResult:
        """Mark a commitment as completed."""
        now = datetime.utcnow().isoformat()

        query = """
        MATCH (c:Commitment {id: $id})
        SET c.status = 'completed',
            c.completed_at = $completed_at,
            c.outcome = $outcome
        RETURN c
        """

        params = {
            "id": args["commitment_id"],
            "completed_at": now,
            "outcome": args.get("outcome")
        }

        async with self._driver.session() as session:
            result = await session.run(query, params)
            record = await result.single()

            if not record:
                return ToolResult.fail(f"Commitment not found: {args['commitment_id']}")

        return ToolResult.ok({
            "id": args["commitment_id"],
            "status": "completed",
            "completed_at": now
        })

    async def _get_commitments(self, args: Dict[str, Any]) -> ToolResult:
        """Get commitments with optional filters."""
        conditions = []
        params = {"limit": args.get("limit", 20)}

        if args.get("status"):
            conditions.append("c.status = $status")
            params["status"] = args["status"]

        if args.get("domain"):
            conditions.append("c.domain = $domain")
            params["domain"] = args["domain"]

        if args.get("to_whom"):
            conditions.append("c.to_whom = $to_whom")
            params["to_whom"] = args["to_whom"]

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
        MATCH (c:Commitment)
        {where_clause}
        RETURN c
        ORDER BY c.created_at DESC
        LIMIT $limit
        """

        async with self._driver.session() as session:
            result = await session.run(query, params)
            records = await result.data()

        commitments = [dict(r["c"]) for r in records]
        return ToolResult.ok({"commitments": commitments, "count": len(commitments)})

    # =========================================================================
    # Decision Operations
    # =========================================================================

    async def _record_decision(self, args: Dict[str, Any]) -> ToolResult:
        """Record a decision with rationale."""
        import uuid

        decision_id = f"decision_{uuid.uuid4().hex[:8]}"
        now = datetime.utcnow().isoformat()

        query = """
        CREATE (d:Decision {
            id: $id,
            content: $content,
            rationale: $rationale,
            alternatives: $alternatives,
            domain: $domain,
            confidence: $confidence,
            created_at: $created_at
        })
        RETURN d
        """

        params = {
            "id": decision_id,
            "content": args["content"],
            "rationale": args["rationale"],
            "alternatives": args.get("alternatives", []),
            "domain": args.get("domain", "work"),
            "confidence": args.get("confidence", 0.7),
            "created_at": now
        }

        async with self._driver.session() as session:
            await session.run(query, params)

        return ToolResult.ok({
            "id": decision_id,
            "message": f"Recorded decision: {args['content'][:50]}..."
        })

    async def _get_decisions(self, args: Dict[str, Any]) -> ToolResult:
        """Get decisions with optional filters."""
        conditions = []
        params = {"limit": args.get("limit", 20)}

        if args.get("domain"):
            conditions.append("d.domain = $domain")
            params["domain"] = args["domain"]

        if args.get("days"):
            conditions.append("d.created_at >= datetime() - duration({days: $days})")
            params["days"] = args["days"]

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
        MATCH (d:Decision)
        {where_clause}
        RETURN d
        ORDER BY d.created_at DESC
        LIMIT $limit
        """

        async with self._driver.session() as session:
            result = await session.run(query, params)
            records = await result.data()

        decisions = [dict(r["d"]) for r in records]
        return ToolResult.ok({"decisions": decisions, "count": len(decisions)})

    # =========================================================================
    # Pattern Operations
    # =========================================================================

    async def _record_pattern(self, args: Dict[str, Any]) -> ToolResult:
        """Record or update a behavioral pattern."""
        import uuid

        now = datetime.utcnow().isoformat()

        # Check if similar pattern exists
        check_query = """
        MATCH (p:Pattern)
        WHERE p.description CONTAINS $keyword
        AND p.domain = $domain
        RETURN p
        LIMIT 1
        """

        # Extract first significant word as keyword
        keyword = args["description"].split()[0] if args["description"] else ""

        async with self._driver.session() as session:
            result = await session.run(check_query, {
                "keyword": keyword,
                "domain": args.get("domain", "work")
            })
            existing = await result.single()

            if existing:
                # Update existing pattern
                update_query = """
                MATCH (p:Pattern {id: $id})
                SET p.last_observed = $now,
                    p.strength = p.strength + 0.1
                RETURN p
                """
                await session.run(update_query, {
                    "id": existing["p"]["id"],
                    "now": now
                })
                return ToolResult.ok({
                    "id": existing["p"]["id"],
                    "message": "Updated existing pattern strength",
                    "new": False
                })

            # Create new pattern
            pattern_id = f"pattern_{uuid.uuid4().hex[:8]}"
            create_query = """
            CREATE (p:Pattern {
                id: $id,
                description: $description,
                type: $type,
                domain: $domain,
                frequency: $frequency,
                first_observed: $now,
                last_observed: $now,
                strength: 0.5
            })
            RETURN p
            """

            await session.run(create_query, {
                "id": pattern_id,
                "description": args["description"],
                "type": args.get("type", "behavioral"),
                "domain": args.get("domain", "work"),
                "frequency": args.get("frequency", "situational"),
                "now": now
            })

        return ToolResult.ok({
            "id": pattern_id,
            "message": f"Created new pattern: {args['description'][:50]}...",
            "new": True
        })

    async def _get_patterns(self, args: Dict[str, Any]) -> ToolResult:
        """Get recorded patterns."""
        conditions = []
        params = {"limit": args.get("limit", 20)}

        if args.get("type"):
            conditions.append("p.type = $type")
            params["type"] = args["type"]

        if args.get("domain"):
            conditions.append("p.domain = $domain")
            params["domain"] = args["domain"]

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
        MATCH (p:Pattern)
        {where_clause}
        RETURN p
        ORDER BY p.strength DESC, p.last_observed DESC
        LIMIT $limit
        """

        async with self._driver.session() as session:
            result = await session.run(query, params)
            records = await result.data()

        patterns = [dict(r["p"]) for r in records]
        return ToolResult.ok({"patterns": patterns, "count": len(patterns)})

    # =========================================================================
    # Session Operations
    # =========================================================================

    async def _start_session(self, args: Dict[str, Any]) -> ToolResult:
        """Record start of a conversation session."""
        import uuid

        session_id = f"session_{uuid.uuid4().hex[:8]}"
        now = datetime.utcnow().isoformat()

        query = """
        CREATE (s:Session {
            id: $id,
            agent: $agent,
            mood: $mood,
            started_at: $started_at
        })
        RETURN s
        """

        async with self._driver.session() as session:
            await session.run(query, {
                "id": session_id,
                "agent": args["agent"],
                "mood": args.get("mood"),
                "started_at": now
            })

        return ToolResult.ok({"session_id": session_id, "started_at": now})

    async def _end_session(self, args: Dict[str, Any]) -> ToolResult:
        """Record end of session with summary."""
        now = datetime.utcnow().isoformat()

        query = """
        MATCH (s:Session {id: $id})
        SET s.ended_at = $ended_at,
            s.summary = $summary,
            s.tokens_used = $tokens_used
        RETURN s
        """

        async with self._driver.session() as session:
            result = await session.run(query, {
                "id": args["session_id"],
                "ended_at": now,
                "summary": args["summary"],
                "tokens_used": args.get("tokens_used", 0)
            })
            record = await result.single()

            if not record:
                return ToolResult.fail(f"Session not found: {args['session_id']}")

        return ToolResult.ok({
            "session_id": args["session_id"],
            "ended_at": now
        })

    # =========================================================================
    # Relationship Operations
    # =========================================================================

    async def _link_nodes(self, args: Dict[str, Any]) -> ToolResult:
        """Create a relationship between two nodes."""
        rel_type = args["relationship"].upper().replace(" ", "_")

        # Validate relationship type
        valid_rels = list(GRAPH_SCHEMA["relationships"].keys())
        if rel_type not in valid_rels:
            return ToolResult.fail(
                f"Invalid relationship type. Valid types: {', '.join(valid_rels)}"
            )

        query = f"""
        MATCH (a {{id: $from_id}})
        MATCH (b {{id: $to_id}})
        CREATE (a)-[r:{rel_type} $props]->(b)
        RETURN a, r, b
        """

        async with self._driver.session() as session:
            result = await session.run(query, {
                "from_id": args["from_id"],
                "to_id": args["to_id"],
                "props": args.get("properties", {})
            })
            record = await result.single()

            if not record:
                return ToolResult.fail("One or both nodes not found")

        return ToolResult.ok({
            "from": args["from_id"],
            "relationship": rel_type,
            "to": args["to_id"]
        })

    async def _find_related(self, args: Dict[str, Any]) -> ToolResult:
        """Find nodes related to a given node."""
        depth = args.get("depth", 2)
        rel_filter = f":{args['relationship_type']}" if args.get("relationship_type") else ""

        query = f"""
        MATCH (n {{id: $node_id}})-[r{rel_filter}*1..{depth}]-(related)
        RETURN DISTINCT related, type(r[0]) as relationship
        LIMIT 50
        """

        async with self._driver.session() as session:
            result = await session.run(query, {"node_id": args["node_id"]})
            records = await result.data()

        related = [
            {"node": dict(r["related"]), "relationship": r["relationship"]}
            for r in records
        ]

        return ToolResult.ok({"related": related, "count": len(related)})

    async def _query_graph(self, args: Dict[str, Any]) -> ToolResult:
        """Execute a custom Cypher query (read-only for safety)."""
        query = args["query"].strip()

        # Safety check - only allow read operations
        dangerous_keywords = ["CREATE", "DELETE", "SET", "REMOVE", "MERGE", "DROP"]
        query_upper = query.upper()

        if any(kw in query_upper for kw in dangerous_keywords):
            return ToolResult.fail(
                "Only read-only queries allowed. Use specific tools for writes."
            )

        async with self._driver.session() as session:
            result = await session.run(query, args.get("parameters", {}))
            records = await result.data()

        return ToolResult.ok({"results": records, "count": len(records)})

    # =========================================================================
    # Entity Operations
    # =========================================================================

    async def _create_entity(self, args: Dict[str, Any]) -> ToolResult:
        """Create a person, client, or project entity."""
        import uuid

        entity_id = f"entity_{uuid.uuid4().hex[:8]}"
        now = datetime.utcnow().isoformat()

        query = """
        MERGE (e:Entity {name: $name})
        ON CREATE SET
            e.id = $id,
            e.type = $type,
            e.domain = $domain,
            e.notes = $notes,
            e.created_at = $created_at
        ON MATCH SET
            e.notes = COALESCE($notes, e.notes),
            e.domain = COALESCE($domain, e.domain)
        RETURN e
        """

        async with self._driver.session() as session:
            result = await session.run(query, {
                "id": entity_id,
                "name": args["name"],
                "type": args["type"],
                "domain": args.get("domain"),
                "notes": args.get("notes"),
                "created_at": now
            })
            record = await result.single()

        return ToolResult.ok({
            "id": record["e"]["id"],
            "name": args["name"],
            "type": args["type"]
        })

    async def _get_entity_context(self, args: Dict[str, Any]) -> ToolResult:
        """Get all context about an entity."""
        query = """
        MATCH (e:Entity {name: $name})
        OPTIONAL MATCH (e)<-[:INVOLVES]-(commitment:Commitment)
        OPTIONAL MATCH (e)<-[:INVOLVES]-(decision:Decision)
        OPTIONAL MATCH (e)<-[:INVOLVES]-(session:Session)
        RETURN e,
               COLLECT(DISTINCT commitment) as commitments,
               COLLECT(DISTINCT decision) as decisions,
               COLLECT(DISTINCT session) as sessions
        """

        async with self._driver.session() as session:
            result = await session.run(query, {"name": args["name"]})
            record = await result.single()

            if not record:
                return ToolResult.fail(f"Entity not found: {args['name']}")

        return ToolResult.ok({
            "entity": dict(record["e"]),
            "commitments": [dict(c) for c in record["commitments"] if c],
            "decisions": [dict(d) for d in record["decisions"] if d],
            "sessions": [dict(s) for s in record["sessions"] if s]
        })

    # =========================================================================
    # Lifecycle
    # =========================================================================

    async def close(self):
        """Close the Neo4j driver connection."""
        await self._driver.close()

    async def health_check(self) -> ToolResult:
        """Check Neo4j connectivity."""
        try:
            async with self._driver.session() as session:
                result = await session.run("RETURN 1 as n")
                record = await result.single()

                if record and record["n"] == 1:
                    return ToolResult.ok({
                        "status": "ok",
                        "adapter": self.name,
                        "database": "Neo4j AuraDB"
                    })
        except Exception as e:
            return ToolResult.fail(f"Neo4j connection failed: {str(e)}")

        return ToolResult.fail("Neo4j health check failed")
