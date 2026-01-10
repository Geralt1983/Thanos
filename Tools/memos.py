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

import os
import asyncio
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Conditional imports with graceful fallbacks
try:
    from .adapters.neo4j_adapter import Neo4jAdapter, GRAPH_SCHEMA
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


@dataclass
class MemoryResult:
    """Result from a MemOS query combining graph and vector results."""
    success: bool
    graph_results: List[Dict[str, Any]] = field(default_factory=list)
    vector_results: List[Dict[str, Any]] = field(default_factory=list)
    combined: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(
        cls,
        graph_results: List[Dict] = None,
        vector_results: List[Dict] = None,
        **metadata
    ) -> 'MemoryResult':
        """Create successful result."""
        graph = graph_results or []
        vector = vector_results or []

        # Combine and deduplicate by id if present
        seen_ids = set()
        combined = []

        for item in graph + vector:
            item_id = item.get('id') or item.get('content', '')[:50]
            if item_id not in seen_ids:
                seen_ids.add(item_id)
                combined.append(item)

        return cls(
            success=True,
            graph_results=graph,
            vector_results=vector,
            combined=combined,
            metadata=metadata
        )

    @classmethod
    def fail(cls, error: str, **metadata) -> 'MemoryResult':
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
        openai_api_key: Optional[str] = None
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

        # Initialize Neo4j if available
        if NEO4J_AVAILABLE:
            try:
                self._neo4j = Neo4jAdapter(
                    uri=neo4j_uri,
                    username=neo4j_username,
                    password=neo4j_password
                )
            except (ValueError, ImportError) as e:
                print(f"[MemOS] Neo4j not configured: {e}")

        # Initialize ChromaDB if available
        if CHROMA_AVAILABLE:
            chroma_path = chroma_path or os.path.expanduser("~/.claude/Memory/vectors")
            Path(chroma_path).mkdir(parents=True, exist_ok=True)

            self._chroma = ChromaClient(Settings(
                persist_directory=chroma_path,
                anonymized_telemetry=False
            ))

        # Initialize OpenAI for embeddings
        if OPENAI_AVAILABLE:
            api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
            if api_key:
                self._openai_client = openai.OpenAI(api_key=api_key)

    @property
    def graph_available(self) -> bool:
        """Check if graph database is available."""
        return self._neo4j is not None

    @property
    def vector_available(self) -> bool:
        """Check if vector database is available."""
        return self._chroma is not None

    @property
    def status(self) -> Dict[str, Any]:
        """Get MemOS status."""
        return {
            "neo4j": "connected" if self._neo4j else "unavailable",
            "chromadb": "connected" if self._chroma else "unavailable",
            "embeddings": "available" if self._openai_client else "unavailable"
        }

    # =========================================================================
    # Core Operations: Remember, Recall, Relate, Reflect
    # =========================================================================

    async def remember(
        self,
        content: str,
        memory_type: str = "observation",
        domain: str = "general",
        entities: List[str] = None,
        metadata: Dict[str, Any] = None
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
                    result = await self._neo4j.call_tool("create_commitment", {
                        "content": content,
                        "domain": domain,
                        "to_whom": metadata.get("to_whom", "self"),
                        "deadline": metadata.get("deadline"),
                        "priority": metadata.get("priority", 3)
                    })
                elif memory_type == "decision":
                    result = await self._neo4j.call_tool("record_decision", {
                        "content": content,
                        "rationale": metadata.get("rationale", ""),
                        "domain": domain,
                        "alternatives": metadata.get("alternatives", []),
                        "confidence": metadata.get("confidence", 0.7)
                    })
                elif memory_type == "pattern":
                    result = await self._neo4j.call_tool("record_pattern", {
                        "description": content,
                        "type": metadata.get("pattern_type", "behavior"),
                        "domain": domain,
                        "frequency": metadata.get("frequency", "situational")
                    })
                else:
                    # Generic observation - store as Session note
                    result = await self._neo4j.call_tool("start_session", {
                        "agent": "memos",
                        "mood": metadata.get("mood")
                    })

                if result.success:
                    graph_results.append(result.data)

                    # Link to entities
                    for entity in entities:
                        await self._neo4j.call_tool("create_entity", {
                            "name": entity,
                            "type": "auto",
                            "domain": domain
                        })
                        if result.data.get("id"):
                            await self._neo4j.call_tool("link_nodes", {
                                "from_id": result.data["id"],
                                "relationship": "INVOLVES",
                                "to_id": f"entity_{entity}"
                            })

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
                    model="text-embedding-3-small",
                    input=content
                )
                embedding = embedding_response.data[0].embedding

                # Store with metadata
                doc_id = f"{memory_type}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                collection.add(
                    ids=[doc_id],
                    embeddings=[embedding],
                    documents=[content],
                    metadatas=[{
                        "type": memory_type,
                        "domain": domain,
                        "entities": ",".join(entities),
                        "timestamp": datetime.utcnow().isoformat(),
                        **{k: str(v) for k, v in metadata.items() if v}
                    }]
                )

                vector_results.append({
                    "id": doc_id,
                    "collection": memory_type + "s"
                })

            except Exception as e:
                print(f"[MemOS] Vector storage error: {e}")

        if not graph_results and not vector_results:
            return MemoryResult.fail("No storage backends available or all failed")

        return MemoryResult.ok(
            graph_results=graph_results,
            vector_results=vector_results,
            stored_in=["neo4j"] if graph_results else [] + ["chromadb"] if vector_results else []
        )

    async def recall(
        self,
        query: str,
        memory_types: List[str] = None,
        domain: str = None,
        limit: int = 10,
        use_graph: bool = True,
        use_vector: bool = True
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
                        result = await self._neo4j.call_tool("get_commitments", {
                            "domain": domain,
                            "limit": limit
                        })
                    elif memory_type == "decision":
                        result = await self._neo4j.call_tool("get_decisions", {
                            "domain": domain,
                            "limit": limit
                        })
                    elif memory_type == "pattern":
                        result = await self._neo4j.call_tool("get_patterns", {
                            "domain": domain,
                            "limit": limit
                        })
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
                    model="text-embedding-3-small",
                    input=query
                )
                query_embedding = embedding_response.data[0].embedding

                # Search each relevant collection
                for memory_type in memory_types:
                    try:
                        collection = self._chroma.get_collection(name=memory_type + "s")
                        results = collection.query(
                            query_embeddings=[query_embedding],
                            n_results=limit,
                            where={"domain": domain} if domain else None
                        )

                        for i, doc in enumerate(results["documents"][0]):
                            vector_results.append({
                                "content": doc,
                                "metadata": results["metadatas"][0][i],
                                "distance": results["distances"][0][i] if results.get("distances") else 0,
                                "_source": "vector",
                                "_type": memory_type
                            })

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
            filters={"types": memory_types, "domain": domain}
        )

    async def relate(
        self,
        from_id: str,
        relationship: str,
        to_id: str,
        properties: Dict[str, Any] = None
    ) -> MemoryResult:
        """
        Create a relationship between two memories in the graph.

        Args:
            from_id: Source node ID
            relationship: Relationship type (LEADS_TO, IMPACTS, etc.)
            to_id: Target node ID
            properties: Relationship properties

        Returns:
            MemoryResult with relationship confirmation
        """
        if not self._neo4j:
            return MemoryResult.fail("Neo4j not available for relationship creation")

        result = await self._neo4j.call_tool("link_nodes", {
            "from_id": from_id,
            "relationship": relationship,
            "to_id": to_id,
            "properties": properties or {}
        })

        if result.success:
            return MemoryResult.ok(graph_results=[result.data])
        else:
            return MemoryResult.fail(result.error)

    async def reflect(
        self,
        topic: str,
        timeframe_days: int = 30,
        domain: str = None
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
                result = await self._neo4j.call_tool("get_patterns", {
                    "domain": domain,
                    "limit": 20
                })

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
                    input=f"patterns and recurring themes about {topic}"
                )
                query_embedding = embedding_response.data[0].embedding

                try:
                    collection = self._chroma.get_collection(name="patterns")
                    results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=10
                    )

                    for i, doc in enumerate(results["documents"][0]):
                        vector_patterns.append({
                            "description": doc,
                            "metadata": results["metadatas"][0][i],
                            "relevance": 1 - results["distances"][0][i],
                            "_source": "vector"
                        })

                except Exception:
                    pass

            except Exception as e:
                print(f"[MemOS] Vector pattern search error: {e}")

        return MemoryResult.ok(
            graph_results=graph_patterns,
            vector_results=vector_patterns,
            topic=topic,
            timeframe_days=timeframe_days
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

        result = await self._neo4j.call_tool("get_entity_context", {
            "name": entity_name
        })

        if result.success:
            return MemoryResult.ok(graph_results=[result.data])
        else:
            return MemoryResult.fail(result.error)

    # =========================================================================
    # Lifecycle
    # =========================================================================

    async def close(self):
        """Close all connections."""
        if self._neo4j:
            await self._neo4j.close()

    async def health_check(self) -> Dict[str, Any]:
        """Check health of all storage backends."""
        status = {"healthy": True, "backends": {}}

        if self._neo4j:
            result = await self._neo4j.health_check()
            status["backends"]["neo4j"] = {
                "status": "ok" if result.success else "error",
                "error": result.error
            }
            if not result.success:
                status["healthy"] = False
        else:
            status["backends"]["neo4j"] = {"status": "not_configured"}

        if self._chroma:
            try:
                # Simple health check - list collections
                collections = self._chroma.list_collections()
                status["backends"]["chromadb"] = {
                    "status": "ok",
                    "collections": len(collections)
                }
            except Exception as e:
                status["backends"]["chromadb"] = {
                    "status": "error",
                    "error": str(e)
                }
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
