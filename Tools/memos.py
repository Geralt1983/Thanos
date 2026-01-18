"""
MemOS - Memory Operating System for Thanos

Unified memory interface combining:
- Neo4j AuraDB: Knowledge graph for relationships (commitments → decisions → outcomes)
- ChromaDB: Vector store for semantic search

This hybrid architecture provides:
- Graph traversal for "what led to this?" queries
- Semantic search for "find things like this" queries
- Pattern recognition across both stores
"""

from dataclasses import dataclass, field
from datetime import datetime
import os
from pathlib import Path
from typing import Any, Optional

# Load environment variables BEFORE any initialization
try:
    from dotenv import load_dotenv
    # Load from project root .env file
    _project_root = Path(__file__).parent.parent
    _env_file = _project_root / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
    else:
        load_dotenv()  # Try default locations
except ImportError:
    pass  # dotenv not installed, rely on system env vars


# Conditional imports with graceful fallbacks
try:
    from .adapters.neo4j_adapter import GRAPH_SCHEMA, Neo4jAdapter

    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    Neo4jAdapter = None
    GRAPH_SCHEMA = {}

try:
    from chromadb import Client as ChromaClient
    from chromadb.config import Settings

    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    ChromaClient = None

try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# SQLite relationship layer (always available)
try:
    from .relationships import (
        RelationshipStore,
        RelationType,
        get_relationship_store,
    )
    RELATIONSHIPS_AVAILABLE = True
except ImportError:
    RELATIONSHIPS_AVAILABLE = False
    RelationshipStore = None
    RelationType = None


@dataclass
class MemoryResult:
    """Result from a MemOS query combining graph and vector results."""

    success: bool
    graph_results: list[dict[str, Any]] = field(default_factory=list)
    vector_results: list[dict[str, Any]] = field(default_factory=list)
    combined: list[dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(
        cls, graph_results: list[dict] = None, vector_results: list[dict] = None, **metadata
    ) -> "MemoryResult":
        """Create successful result."""
        graph = graph_results or []
        vector = vector_results or []

        # Combine and deduplicate by id if present
        seen_ids = set()
        combined = []

        for item in graph + vector:
            item_id = item.get("id") or item.get("content", "")[:50]
            if item_id not in seen_ids:
                seen_ids.add(item_id)
                combined.append(item)

        return cls(
            success=True,
            graph_results=graph,
            vector_results=vector,
            combined=combined,
            metadata=metadata,
        )

    @classmethod
    def fail(cls, error: str, **metadata) -> "MemoryResult":
        """Create failed result."""
        return cls(success=False, error=error, metadata=metadata)


class MemOS:
    """
    Memory Operating System - Unified memory interface for Thanos.

    Combines Neo4j (graph) and ChromaDB (vector) for hybrid memory:
    - Remember: Store to both graph (structured) and vector (semantic)
    - Recall: Query both and merge results intelligently
    - Relate: Create and traverse relationships in graph
    - Reflect: Find patterns across time using both stores
    """

    def __init__(
        self,
        neo4j_uri: Optional[str] = None,
        neo4j_username: Optional[str] = None,
        neo4j_password: Optional[str] = None,
        chroma_path: Optional[str] = None,
        openai_api_key: Optional[str] = None,
    ):
        """
        Initialize MemOS with both storage backends.

        Args:
            neo4j_uri: Neo4j connection URI (defaults to NEO4J_URL env var)
            neo4j_username: Neo4j username
            neo4j_password: Neo4j password
            chroma_path: Path for ChromaDB persistence
            openai_api_key: OpenAI API key for embeddings
        """
        self._neo4j: Optional[Neo4jAdapter] = None
        self._chroma: Optional[ChromaClient] = None
        self._openai_client = None
        self._relationships: Optional[RelationshipStore] = None

        # Initialize Neo4j if available
        self._neo4j_error: Optional[str] = None
        if NEO4J_AVAILABLE:
            try:
                self._neo4j = Neo4jAdapter(
                    uri=neo4j_uri, username=neo4j_username, password=neo4j_password
                )
            except (ValueError, ImportError) as e:
                self._neo4j_error = str(e)
                # Silent fail - Neo4j is optional, ChromaDB can work alone
            except Exception as e:
                self._neo4j_error = str(e)
                # Catch DNS/connection errors gracefully

        # Initialize ChromaDB if available
        if CHROMA_AVAILABLE:
            try:
                import chromadb
                # increased timeout for initial connection test
                # Try to connect to server first
                self._chroma = chromadb.HttpClient(host='localhost', port=8000)
                self._chroma.heartbeat()  # Test connection
                print("[MemOS] Connected to ChromaDB server at localhost:8000")
            except Exception:
                # Fallback to local persistent client
                print("[MemOS] ChromaDB server not found, falling back to local storage")
                chroma_path = chroma_path or os.path.expanduser("~/.claude/Memory/vectors")
                Path(chroma_path).mkdir(parents=True, exist_ok=True)

                self._chroma = ChromaClient(
                    Settings(persist_directory=chroma_path, anonymized_telemetry=False)
                )

        # Initialize OpenAI for embeddings
        if OPENAI_AVAILABLE:
            api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
            if api_key:
                self._openai_client = openai.OpenAI(api_key=api_key)

        # Initialize SQLite relationship store (always available, zero overhead)
        if RELATIONSHIPS_AVAILABLE:
            try:
                self._relationships = get_relationship_store()
            except Exception as e:
                print(f"[MemOS] Relationship store init error: {e}")

        # Ensure all ChromaDB collections exist
        if self._chroma:
            self._ensure_collections()

    def _ensure_collections(self) -> None:
        """Ensure all required ChromaDB collections exist."""
        required_collections = [
            "commitments",
            "decisions",
            "patterns",
            "observations",
            "conversations",
            "entities",
        ]
        try:
            for collection_name in required_collections:
                self._chroma.get_or_create_collection(name=collection_name)
        except Exception as e:
            print(f"[MemOS] Warning: Could not create collections: {e}")

    @property
    def graph_available(self) -> bool:
        """Check if graph database is available."""
        return self._neo4j is not None

    @property
    def vector_available(self) -> bool:
        """Check if vector database is available."""
        return self._chroma is not None

    @property
    def relationships_available(self) -> bool:
        """Check if relationship store is available."""
        return self._relationships is not None

    @property
    def status(self) -> dict[str, Any]:
        """Get MemOS status."""
        neo4j_status = "connected" if self._neo4j else "unavailable"
        if self._neo4j_error and not self._neo4j:
            neo4j_status = f"error: {self._neo4j_error[:50]}"

        rel_stats = None
        if self._relationships:
            try:
                rel_stats = self._relationships.get_stats()
            except Exception:
                pass

        return {
            "neo4j": neo4j_status,
            "chromadb": "connected" if self._chroma else "unavailable",
            "embeddings": "available" if self._openai_client else "unavailable",
            "relationships": "connected" if self._relationships else "unavailable",
            "relationship_stats": rel_stats,
            "vector_only_mode": self._chroma is not None and self._neo4j is None,
            "hybrid_mode": self._chroma is not None and self._relationships is not None,
        }

    # =========================================================================
    # Core Operations: Remember, Recall, Relate, Reflect
    # =========================================================================

    async def remember(
        self,
        content: str,
        memory_type: str = "observation",
        domain: str = "general",
        entities: list[str] = None,
        metadata: dict[str, Any] = None,
    ) -> MemoryResult:
        """
        Store a memory in both graph and vector stores.

        Args:
            content: The memory content
            memory_type: Type of memory (commitment, decision, pattern, observation)
            domain: Domain (work, personal, health, relationship)
            entities: Related entities (people, clients, projects)
            metadata: Additional metadata

        Returns:
            MemoryResult with storage confirmation
        """
        metadata = metadata or {}
        entities = entities or []
        graph_results = []
        vector_results = []

        # Store in Neo4j graph
        if self._neo4j:
            try:
                if memory_type == "commitment":
                    result = await self._neo4j.call_tool(
                        "create_commitment",
                        {
                            "content": content,
                            "domain": domain,
                            "to_whom": metadata.get("to_whom", "self"),
                            "deadline": metadata.get("deadline"),
                            "priority": metadata.get("priority", 3),
                        },
                    )
                elif memory_type == "decision":
                    result = await self._neo4j.call_tool(
                        "record_decision",
                        {
                            "content": content,
                            "rationale": metadata.get("rationale", ""),
                            "domain": domain,
                            "alternatives": metadata.get("alternatives", []),
                            "confidence": metadata.get("confidence", 0.7),
                        },
                    )
                elif memory_type == "pattern":
                    result = await self._neo4j.call_tool(
                        "record_pattern",
                        {
                            "description": content,
                            "type": metadata.get("pattern_type", "behavior"),
                            "domain": domain,
                            "frequency": metadata.get("frequency", "situational"),
                        },
                    )
                else:
                    # Generic observation - store as Session note
                    result = await self._neo4j.call_tool(
                        "start_session", {"agent": "memos", "mood": metadata.get("mood")}
                    )

                if result.success:
                    graph_results.append(result.data)

                    # Link to entities
                    for entity in entities:
                        await self._neo4j.call_tool(
                            "create_entity", {"name": entity, "type": "auto", "domain": domain}
                        )
                        if result.data.get("id"):
                            await self._neo4j.call_tool(
                                "link_nodes",
                                {
                                    "from_id": result.data["id"],
                                    "relationship": "INVOLVES",
                                    "to_id": f"entity_{entity}",
                                },
                            )

            except Exception as e:
                print(f"[MemOS] Graph storage error: {e}")

        # Store in ChromaDB vector store
        if self._chroma and self._openai_client:
            try:
                collection = self._chroma.get_or_create_collection(
                    name=memory_type + "s"  # pluralize
                )

                # Generate embedding
                embedding_response = self._openai_client.embeddings.create(
                    model="text-embedding-3-small", input=content
                )
                embedding = embedding_response.data[0].embedding

                # Store with metadata
                doc_id = f"{memory_type}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                collection.add(
                    ids=[doc_id],
                    embeddings=[embedding],
                    documents=[content],
                    metadatas=[
                        {
                            "type": memory_type,
                            "domain": domain,
                            "entities": ",".join(entities),
                            "timestamp": datetime.utcnow().isoformat(),
                            **{k: str(v) for k, v in metadata.items() if v},
                        }
                    ],
                )

                vector_results.append({"id": doc_id, "collection": memory_type + "s"})

            except Exception as e:
                print(f"[MemOS] Vector storage error: {e}")

        if not graph_results and not vector_results:
            return MemoryResult.fail("No storage backends available or all failed")

        return MemoryResult.ok(
            graph_results=graph_results,
            vector_results=vector_results,
            stored_in=["neo4j"] if graph_results else [] + ["chromadb"] if vector_results else [],
        )

    async def recall(
        self,
        query: str,
        memory_types: list[str] = None,
        domain: str = None,
        limit: int = 10,
        use_graph: bool = True,
        use_vector: bool = True,
    ) -> MemoryResult:
        """
        Recall memories using both graph traversal and semantic search.

        Args:
            query: Natural language query
            memory_types: Filter by types (commitment, decision, pattern)
            domain: Filter by domain
            limit: Maximum results per source
            use_graph: Include graph results
            use_vector: Include vector results

        Returns:
            MemoryResult with combined results
        """
        memory_types = memory_types or ["commitment", "decision", "pattern", "observation"]
        graph_results = []
        vector_results = []

        # Query Neo4j graph
        if use_graph and self._neo4j:
            try:
                for memory_type in memory_types:
                    if memory_type == "commitment":
                        result = await self._neo4j.call_tool(
                            "get_commitments", {"domain": domain, "limit": limit}
                        )
                    elif memory_type == "decision":
                        result = await self._neo4j.call_tool(
                            "get_decisions", {"domain": domain, "limit": limit}
                        )
                    elif memory_type == "pattern":
                        result = await self._neo4j.call_tool(
                            "get_patterns", {"domain": domain, "limit": limit}
                        )
                    else:
                        continue

                    if result.success and result.data:
                        items = result.data.get(memory_type + "s", [])
                        for item in items:
                            item["_source"] = "graph"
                            item["_type"] = memory_type
                        graph_results.extend(items)

            except Exception as e:
                print(f"[MemOS] Graph query error: {e}")

        # Query ChromaDB with semantic search
        if use_vector and self._chroma and self._openai_client:
            try:
                # Generate query embedding
                embedding_response = self._openai_client.embeddings.create(
                    model="text-embedding-3-small", input=query
                )
                query_embedding = embedding_response.data[0].embedding

                # Search each relevant collection
                for memory_type in memory_types:
                    try:
                        collection = self._chroma.get_collection(name=memory_type + "s")
                        results = collection.query(
                            query_embeddings=[query_embedding],
                            n_results=limit,
                            where={"domain": domain} if domain else None,
                        )

                        for i, doc in enumerate(results["documents"][0]):
                            vector_results.append(
                                {
                                    "content": doc,
                                    "metadata": results["metadatas"][0][i],
                                    "distance": results["distances"][0][i]
                                    if results.get("distances")
                                    else 0,
                                    "_source": "vector",
                                    "_type": memory_type,
                                }
                            )

                    except Exception:
                        # Collection might not exist yet
                        pass

            except Exception as e:
                print(f"[MemOS] Vector query error: {e}")

        # Sort vector results by relevance (distance)
        vector_results.sort(key=lambda x: x.get("distance", 0))

        return MemoryResult.ok(
            graph_results=graph_results[:limit],
            vector_results=vector_results[:limit],
            query=query,
            filters={"types": memory_types, "domain": domain},
        )

    async def relate(
        self, from_id: str, relationship: str, to_id: str, properties: dict[str, Any] = None
    ) -> MemoryResult:
        """
        Create a relationship between two memories.

        Uses Neo4j if available, falls back to SQLite relationship store.

        Args:
            from_id: Source node ID
            relationship: Relationship type (LEADS_TO, IMPACTS, CAUSED, etc.)
            to_id: Target node ID
            properties: Relationship properties

        Returns:
            MemoryResult with relationship confirmation
        """
        results = []

        # Try Neo4j first
        if self._neo4j:
            result = await self._neo4j.call_tool(
                "link_nodes",
                {
                    "from_id": from_id,
                    "relationship": relationship,
                    "to_id": to_id,
                    "properties": properties or {},
                },
            )
            if result.success:
                results.append({"source": "neo4j", "data": result.data})

        # Also store in SQLite relationship store (hybrid approach)
        if self._relationships and RELATIONSHIPS_AVAILABLE:
            try:
                # Map relationship string to RelationType
                rel_type_map = {
                    "LEADS_TO": RelationType.CAUSED,
                    "CAUSED": RelationType.CAUSED,
                    "PREVENTED": RelationType.PREVENTED,
                    "ENABLED": RelationType.ENABLED,
                    "PRECEDED": RelationType.PRECEDED,
                    "FOLLOWED": RelationType.FOLLOWED,
                    "RELATED_TO": RelationType.RELATED_TO,
                    "IMPACTS": RelationType.IMPACTS,
                    "SUPPORTS": RelationType.SUPPORTS,
                    "CONTRADICTS": RelationType.CONTRADICTS,
                }
                rel_type = rel_type_map.get(relationship.upper(), RelationType.RELATED_TO)

                rel = self._relationships.link_memories(
                    source_id=from_id,
                    target_id=to_id,
                    rel_type=rel_type,
                    strength=properties.get("strength", 1.0) if properties else 1.0,
                    metadata=properties,
                )
                results.append({
                    "source": "sqlite",
                    "relationship_id": rel.id,
                    "type": rel.rel_type.value,
                })
            except Exception as e:
                print(f"[MemOS] SQLite relationship error: {e}")

        if not results:
            return MemoryResult.fail("No relationship storage available")

        return MemoryResult.ok(graph_results=results)

    async def reflect(
        self, topic: str, timeframe_days: int = 30, domain: str = None
    ) -> MemoryResult:
        """
        Find patterns and insights across memories for a topic.

        Combines:
        - Graph traversal for relationship patterns
        - Vector similarity for semantic patterns

        Args:
            topic: Topic to reflect on
            timeframe_days: How far back to look
            domain: Filter by domain

        Returns:
            MemoryResult with patterns and insights
        """
        graph_patterns = []
        vector_patterns = []

        # Find patterns in graph
        if self._neo4j:
            try:
                result = await self._neo4j.call_tool(
                    "get_patterns", {"domain": domain, "limit": 20}
                )

                if result.success:
                    patterns = result.data.get("patterns", [])
                    # Filter by topic relevance
                    topic_lower = topic.lower()
                    for p in patterns:
                        desc = p.get("description", "").lower()
                        if any(word in desc for word in topic_lower.split()):
                            p["_source"] = "graph"
                            graph_patterns.append(p)

            except Exception as e:
                print(f"[MemOS] Pattern search error: {e}")

        # Find similar patterns via vector search
        if self._chroma and self._openai_client:
            try:
                embedding_response = self._openai_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=f"patterns and recurring themes about {topic}",
                )
                query_embedding = embedding_response.data[0].embedding

                try:
                    collection = self._chroma.get_collection(name="patterns")
                    results = collection.query(query_embeddings=[query_embedding], n_results=10)

                    for i, doc in enumerate(results["documents"][0]):
                        vector_patterns.append(
                            {
                                "description": doc,
                                "metadata": results["metadatas"][0][i],
                                "relevance": 1 - results["distances"][0][i],
                                "_source": "vector",
                            }
                        )

                except Exception:
                    pass

            except Exception as e:
                print(f"[MemOS] Vector pattern search error: {e}")

        return MemoryResult.ok(
            graph_results=graph_patterns,
            vector_results=vector_patterns,
            topic=topic,
            timeframe_days=timeframe_days,
        )

    # =========================================================================
    # Entity Context
    # =========================================================================

    async def get_entity_context(self, entity_name: str) -> MemoryResult:
        """
        Get all context about a person, client, or project.

        Combines graph relationships and vector similarities.
        """
        if not self._neo4j:
            return MemoryResult.fail("Neo4j required for entity context")

        result = await self._neo4j.call_tool("get_entity_context", {"name": entity_name})

        if result.success:
            return MemoryResult.ok(graph_results=[result.data])
        else:
            return MemoryResult.fail(result.error)

    # =========================================================================
    # Chain Traversal (SQLite Relationship Layer)
    # =========================================================================

    def what_led_to(
        self,
        memory_id: str,
        max_depth: int = 5,
        min_strength: float = 0.3,
    ) -> list[dict[str, Any]]:
        """
        Find what led to a specific memory (backward chain traversal).

        Answers "what caused this?" or "what led to this outcome?"

        Args:
            memory_id: Memory ID to trace back from
            max_depth: How far back to traverse
            min_strength: Minimum relationship strength to follow

        Returns:
            List of causal chain results with paths
        """
        if not self._relationships:
            return []

        try:
            results = self._relationships.traverse_chain(
                start_id=memory_id,
                direction="backward",
                rel_types=[RelationType.CAUSED, RelationType.ENABLED, RelationType.PRECEDED],
                max_depth=max_depth,
                min_strength=min_strength,
            )

            return [
                {
                    "memory_id": r.memory_id,
                    "depth": r.depth,
                    "path": r.path,
                    "relationships": [
                        {"type": rel.rel_type.value, "strength": rel.strength}
                        for rel in r.relationships
                    ],
                }
                for r in results
            ]
        except Exception as e:
            print(f"[MemOS] Chain traversal error: {e}")
            return []

    def what_resulted_from(
        self,
        memory_id: str,
        max_depth: int = 5,
        min_strength: float = 0.3,
    ) -> list[dict[str, Any]]:
        """
        Find what resulted from a specific memory (forward chain traversal).

        Answers "what did this cause?" or "what were the effects?"

        Args:
            memory_id: Memory ID to trace forward from
            max_depth: How far forward to traverse
            min_strength: Minimum relationship strength to follow

        Returns:
            List of effect chain results with paths
        """
        if not self._relationships:
            return []

        try:
            results = self._relationships.traverse_chain(
                start_id=memory_id,
                direction="forward",
                rel_types=[RelationType.CAUSED, RelationType.ENABLED],
                max_depth=max_depth,
                min_strength=min_strength,
            )

            return [
                {
                    "memory_id": r.memory_id,
                    "depth": r.depth,
                    "path": r.path,
                    "relationships": [
                        {"type": rel.rel_type.value, "strength": rel.strength}
                        for rel in r.relationships
                    ],
                }
                for r in results
            ]
        except Exception as e:
            print(f"[MemOS] Chain traversal error: {e}")
            return []

    def find_correlations(
        self,
        memory_ids: list[str],
        min_connections: int = 2,
    ) -> list[dict[str, Any]]:
        """
        Find memories that connect multiple input memories.

        Useful for cross-domain correlation discovery.
        Example: Find what connects "poor sleep" and "missed commitment"

        Args:
            memory_ids: Memory IDs to find connections between
            min_connections: Minimum shared connections

        Returns:
            List of correlation candidates
        """
        if not self._relationships:
            return []

        try:
            return self._relationships.get_correlation_candidates(
                memory_ids=memory_ids,
                min_shared_connections=min_connections,
            )
        except Exception as e:
            print(f"[MemOS] Correlation search error: {e}")
            return []

    # =========================================================================
    # Proactive Insight Surfacing
    # =========================================================================

    def store_insight(
        self,
        insight_type: str,
        content: str,
        source_memories: list[str],
        confidence: float = 0.5,
    ) -> Optional[int]:
        """
        Store a discovered insight for later proactive surfacing.

        Args:
            insight_type: Type (pattern, correlation, warning, opportunity)
            content: Human-readable insight
            source_memories: Memory IDs that support this insight
            confidence: Confidence level (0.0-1.0)

        Returns:
            Insight ID if stored successfully
        """
        if not self._relationships:
            return None

        try:
            return self._relationships.store_insight(
                insight_type=insight_type,
                content=content,
                source_memories=source_memories,
                confidence=confidence,
            )
        except Exception as e:
            print(f"[MemOS] Insight storage error: {e}")
            return None

    def get_pending_insights(
        self,
        min_confidence: float = 0.5,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Get insights that should be proactively surfaced to the user.

        Args:
            min_confidence: Minimum confidence threshold
            limit: Maximum insights to return

        Returns:
            List of pending insights
        """
        if not self._relationships:
            return []

        try:
            return self._relationships.get_unsurfaced_insights(
                min_confidence=min_confidence,
                limit=limit,
            )
        except Exception as e:
            print(f"[MemOS] Insight retrieval error: {e}")
            return []

    def mark_insight_shown(self, insight_id: int) -> None:
        """Mark an insight as having been shown to the user."""
        if self._relationships:
            try:
                self._relationships.mark_insight_surfaced(insight_id)
            except Exception as e:
                print(f"[MemOS] Insight update error: {e}")

    # =========================================================================
    # Lifecycle
    # =========================================================================

    async def close(self):
        """Close all connections."""
        if self._neo4j:
            await self._neo4j.close()

    async def health_check(self) -> dict[str, Any]:
        """Check health of all storage backends."""
        status = {"healthy": True, "backends": {}}

        if self._neo4j:
            result = await self._neo4j.health_check()
            status["backends"]["neo4j"] = {
                "status": "ok" if result.success else "error",
                "error": result.error,
            }
            if not result.success:
                status["healthy"] = False
        else:
            status["backends"]["neo4j"] = {"status": "not_configured"}

        if self._chroma:
            try:
                # Simple health check - list collections
                collections = self._chroma.list_collections()
                status["backends"]["chromadb"] = {"status": "ok", "collections": len(collections)}
            except Exception as e:
                status["backends"]["chromadb"] = {"status": "error", "error": str(e)}
                status["healthy"] = False
        else:
            status["backends"]["chromadb"] = {"status": "not_configured"}

        return status


# =============================================================================
# Singleton instance for easy access
# =============================================================================

_memos_instance: Optional[MemOS] = None


def get_memos() -> MemOS:
    """Get or create the MemOS singleton instance."""
    global _memos_instance
    if _memos_instance is None:
        _memos_instance = MemOS()
    return _memos_instance


async def init_memos() -> MemOS:
    """Initialize and return MemOS instance."""
    memos = get_memos()
    health = await memos.health_check()
    print(f"[MemOS] Initialized: {health}")
    return memos
