"""
Unit tests for Memory Integration (memory_integration.py).

Tests the MemorySystem class that wraps Neo4j and ChromaDB adapters
into a unified memory system with graceful fallback.
"""

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Mock the adapters before importing
@dataclass
class MockToolResult:
    """Mock ToolResult for adapter responses."""
    success: bool
    data: dict = None
    error: str = None


class TestMemoryResultIntegration:
    """Test MemoryResult dataclass from memory_integration."""

    def test_import_memory_result(self):
        """Test MemoryResult can be imported."""
        from Tools.memory_integration import MemoryResult
        assert MemoryResult is not None

    def test_memory_result_ok(self):
        """Test MemoryResult.ok() class method."""
        from Tools.memory_integration import MemoryResult

        result = MemoryResult.ok(data={"key": "value"})

        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None

    def test_memory_result_ok_with_kwargs(self):
        """Test MemoryResult.ok() with additional kwargs."""
        from Tools.memory_integration import MemoryResult

        result = MemoryResult.ok(
            data="test",
            graph_results={"node": "123"},
            vector_results=[{"doc": "1"}],
            metadata={"query": "test"}
        )

        assert result.success is True
        assert result.data == "test"
        assert result.graph_results == {"node": "123"}
        assert result.vector_results == [{"doc": "1"}]
        assert result.metadata == {"query": "test"}

    def test_memory_result_fail(self):
        """Test MemoryResult.fail() class method."""
        from Tools.memory_integration import MemoryResult

        result = MemoryResult.fail("Something went wrong")

        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.data is None

    def test_memory_result_fail_with_kwargs(self):
        """Test MemoryResult.fail() with additional kwargs."""
        from Tools.memory_integration import MemoryResult

        result = MemoryResult.fail(
            "Error occurred",
            metadata={"attempt": 1}
        )

        assert result.success is False
        assert result.error == "Error occurred"
        assert result.metadata == {"attempt": 1}

    def test_memory_result_default_metadata(self):
        """Test MemoryResult has default empty dict for metadata."""
        from Tools.memory_integration import MemoryResult

        result = MemoryResult(success=True)

        assert result.metadata == {}


class TestMemorySystemInitialization:
    """Test MemorySystem initialization."""

    @patch.dict('os.environ', {}, clear=True)
    @patch('Tools.memory_integration.MemorySystem.__init__', return_value=None)
    def test_init_creates_instance(self, mock_init):
        """Test MemorySystem can be instantiated."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem()
        mock_init.assert_called_once()

    def test_init_no_backends_available(self):
        """Test initialization when no backends are available."""
        # Patch imports to simulate unavailable backends
        with patch.dict('sys.modules', {
            'Tools.adapters.neo4j_adapter': MagicMock(NEO4J_AVAILABLE=False),
            'Tools.adapters.chroma_adapter': MagicMock(CHROMADB_AVAILABLE=False)
        }):
            from Tools.memory_integration import MemorySystem

            system = MemorySystem.__new__(MemorySystem)
            system._neo4j = None
            system._chroma = None
            system._neo4j_available = False
            system._chroma_available = False

            assert system.neo4j_available is False
            assert system.chroma_available is False
            assert system.any_available is False


class TestMemorySystemProperties:
    """Test MemorySystem property accessors."""

    def test_neo4j_available_property(self):
        """Test neo4j_available property."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = True

        assert system.neo4j_available is True

    def test_chroma_available_property(self):
        """Test chroma_available property."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._chroma_available = True

        assert system.chroma_available is True

    def test_any_available_neo4j_only(self):
        """Test any_available when only Neo4j is available."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = True
        system._chroma_available = False

        assert system.any_available is True

    def test_any_available_chroma_only(self):
        """Test any_available when only ChromaDB is available."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = False
        system._chroma_available = True

        assert system.any_available is True

    def test_any_available_none(self):
        """Test any_available when neither backend is available."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = False
        system._chroma_available = False

        assert system.any_available is False


class TestMemorySystemGetStatus:
    """Test MemorySystem.get_status() method."""

    def test_get_status_no_errors(self):
        """Test get_status when no errors present."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = True
        system._chroma_available = True

        status = system.get_status()

        assert status["neo4j"]["available"] is True
        assert status["neo4j"]["error"] is None
        assert status["chroma"]["available"] is True
        assert status["chroma"]["error"] is None

    def test_get_status_with_errors(self):
        """Test get_status when errors are present."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = False
        system._chroma_available = False
        system._neo4j_error = "Neo4j connection failed"
        system._chroma_error = "ChromaDB not installed"

        status = system.get_status()

        assert status["neo4j"]["available"] is False
        assert status["neo4j"]["error"] == "Neo4j connection failed"
        assert status["chroma"]["available"] is False
        assert status["chroma"]["error"] == "ChromaDB not installed"


class TestMemorySystemStoreMemory:
    """Test MemorySystem.store_memory() method."""

    @pytest.mark.asyncio
    async def test_store_memory_no_backends(self):
        """Test store_memory fails when no backends available."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = False
        system._chroma_available = False

        result = await system.store_memory("Test content")

        assert result.success is False
        assert "No memory backends available" in result.error

    @pytest.mark.asyncio
    async def test_store_memory_chroma_only_success(self):
        """Test store_memory with only ChromaDB available."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = False
        system._chroma_available = True
        system._chroma = MagicMock()
        system._chroma.call_tool = AsyncMock(return_value=MockToolResult(
            success=True,
            data={"id": "doc123"}
        ))

        result = await system.store_memory(
            "Test content",
            collection="observations",
            memory_type="observation",
            domain="work"
        )

        assert result.success is True
        assert result.data["stored"] is True
        assert result.data["vector"] is True
        assert result.data["graph"] is False

    @pytest.mark.asyncio
    async def test_store_memory_decision_with_graph(self):
        """Test store_memory creates graph node for decision type."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = True
        system._chroma_available = True
        system._neo4j = MagicMock()
        system._chroma = MagicMock()

        system._chroma.call_tool = AsyncMock(return_value=MockToolResult(
            success=True,
            data={"id": "vec123"}
        ))
        system._neo4j.call_tool = AsyncMock(return_value=MockToolResult(
            success=True,
            data={"id": "node456"}
        ))

        result = await system.store_memory(
            "Use TypeScript for new projects",
            memory_type="decision",
            domain="tech"
        )

        assert result.success is True
        assert result.data["vector"] is True
        assert result.data["graph"] is True
        assert result.graph_results == {"id": "node456"}

    @pytest.mark.asyncio
    async def test_store_memory_pattern_type(self):
        """Test store_memory with pattern type."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = True
        system._chroma_available = False
        system._neo4j = MagicMock()
        system._neo4j.call_tool = AsyncMock(return_value=MockToolResult(
            success=True,
            data={"id": "pattern789"}
        ))

        result = await system.store_memory(
            "Energy drops after 3pm",
            memory_type="pattern",
            domain="health"
        )

        assert result.success is True
        assert result.graph_results == {"id": "pattern789"}

    @pytest.mark.asyncio
    async def test_store_memory_commitment_type(self):
        """Test store_memory with commitment type."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = True
        system._chroma_available = False
        system._neo4j = MagicMock()
        system._neo4j.call_tool = AsyncMock(return_value=MockToolResult(
            success=True,
            data={"id": "commit101"}
        ))

        result = await system.store_memory(
            "Exercise 3x per week",
            memory_type="commitment",
            domain="health",
            metadata={"to_whom": "self"}
        )

        assert result.success is True
        assert result.graph_results == {"id": "commit101"}

    @pytest.mark.asyncio
    async def test_store_memory_with_entities(self):
        """Test store_memory creates entities in graph."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = True
        system._chroma_available = False
        system._neo4j = MagicMock()

        call_count = [0]
        async def mock_call_tool(tool_name, args):
            call_count[0] += 1
            if tool_name == "record_decision":
                return MockToolResult(success=True, data={"id": "dec1"})
            elif tool_name == "create_entity":
                return MockToolResult(success=True, data={"id": f"ent{call_count[0]}"})
            return MockToolResult(success=False, error="Unknown tool")

        system._neo4j.call_tool = mock_call_tool

        result = await system.store_memory(
            "Use Python for scripts",
            memory_type="decision",
            entities=["Python", "scripting"]
        )

        assert result.success is True
        # Should call: record_decision, create_entity (Python), create_entity (scripting)
        assert call_count[0] == 3

    @pytest.mark.asyncio
    async def test_store_memory_vector_error(self):
        """Test store_memory handles vector storage error."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = False
        system._chroma_available = True
        system._chroma = MagicMock()
        system._chroma.call_tool = AsyncMock(return_value=MockToolResult(
            success=False,
            error="Storage failed"
        ))

        result = await system.store_memory("Test content")

        assert result.success is True  # Still succeeds overall
        assert result.metadata.get("vector_error") == "Storage failed"

    @pytest.mark.asyncio
    async def test_store_memory_vector_exception(self):
        """Test store_memory handles vector storage exception."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = False
        system._chroma_available = True
        system._chroma = MagicMock()
        system._chroma.call_tool = AsyncMock(side_effect=Exception("Connection lost"))

        result = await system.store_memory("Test content")

        assert result.success is True  # Still succeeds overall
        assert "Connection lost" in result.metadata.get("vector_error", "")


class TestMemorySystemSearchSemantic:
    """Test MemorySystem.search_semantic() method."""

    @pytest.mark.asyncio
    async def test_search_semantic_no_chroma(self):
        """Test search_semantic fails when ChromaDB not available."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._chroma_available = False

        result = await system.search_semantic("test query")

        assert result.success is False
        assert "ChromaDB not available" in result.error

    @pytest.mark.asyncio
    async def test_search_semantic_with_collection(self):
        """Test search_semantic with specific collection."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._chroma_available = True
        system._chroma = MagicMock()
        system._chroma.call_tool = AsyncMock(return_value=MockToolResult(
            success=True,
            data={"results": [{"content": "match1"}], "count": 1}
        ))

        result = await system.search_semantic(
            "work decisions",
            collection="decisions",
            limit=5,
            filters={"domain": "work"}
        )

        assert result.success is True
        assert result.data == [{"content": "match1"}]
        assert result.metadata["count"] == 1

        # Verify correct tool was called
        system._chroma.call_tool.assert_called_once_with("semantic_search", {
            "query": "work decisions",
            "collection": "decisions",
            "limit": 5,
            "where": {"domain": "work"}
        })

    @pytest.mark.asyncio
    async def test_search_semantic_all_collections(self):
        """Test search_semantic across all collections."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._chroma_available = True
        system._chroma = MagicMock()
        system._chroma.call_tool = AsyncMock(return_value=MockToolResult(
            success=True,
            data={"results": [{"content": "match1"}, {"content": "match2"}], "count": 2}
        ))

        result = await system.search_semantic("general query")

        assert result.success is True
        assert len(result.data) == 2

        # Verify search_all_collections was called
        system._chroma.call_tool.assert_called_once_with("search_all_collections", {
            "query": "general query",
            "limit": 10
        })

    @pytest.mark.asyncio
    async def test_search_semantic_failure(self):
        """Test search_semantic handles adapter failure."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._chroma_available = True
        system._chroma = MagicMock()
        system._chroma.call_tool = AsyncMock(return_value=MockToolResult(
            success=False,
            error="Search failed"
        ))

        result = await system.search_semantic("test query")

        assert result.success is False
        assert result.error == "Search failed"

    @pytest.mark.asyncio
    async def test_search_semantic_exception(self):
        """Test search_semantic handles exception."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._chroma_available = True
        system._chroma = MagicMock()
        system._chroma.call_tool = AsyncMock(side_effect=Exception("Timeout"))

        result = await system.search_semantic("test query")

        assert result.success is False
        assert "Semantic search error" in result.error
        assert "Timeout" in result.error


class TestMemorySystemGetRelated:
    """Test MemorySystem.get_related() method."""

    @pytest.mark.asyncio
    async def test_get_related_no_neo4j(self):
        """Test get_related fails when Neo4j not available."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = False

        result = await system.get_related("node123")

        assert result.success is False
        assert "Neo4j not available" in result.error

    @pytest.mark.asyncio
    async def test_get_related_success(self):
        """Test get_related success."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = True
        system._neo4j = MagicMock()
        system._neo4j.call_tool = AsyncMock(return_value=MockToolResult(
            success=True,
            data={
                "related": [{"id": "rel1"}, {"id": "rel2"}],
                "count": 2
            }
        ))

        result = await system.get_related("node123", relationship_type="RELATES_TO", depth=3)

        assert result.success is True
        assert len(result.data) == 2
        assert result.metadata["node_id"] == "node123"
        assert result.metadata["count"] == 2

    @pytest.mark.asyncio
    async def test_get_related_failure(self):
        """Test get_related handles adapter failure."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = True
        system._neo4j = MagicMock()
        system._neo4j.call_tool = AsyncMock(return_value=MockToolResult(
            success=False,
            error="Node not found"
        ))

        result = await system.get_related("invalid_node")

        assert result.success is False
        assert result.error == "Node not found"

    @pytest.mark.asyncio
    async def test_get_related_exception(self):
        """Test get_related handles exception."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = True
        system._neo4j = MagicMock()
        system._neo4j.call_tool = AsyncMock(side_effect=Exception("Connection failed"))

        result = await system.get_related("node123")

        assert result.success is False
        assert "Graph query error" in result.error


class TestMemorySystemStoreKnowledge:
    """Test MemorySystem.store_knowledge() method."""

    @pytest.mark.asyncio
    async def test_store_knowledge_no_neo4j(self):
        """Test store_knowledge fails when Neo4j not available."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = False

        result = await system.store_knowledge("decision", "Test content")

        assert result.success is False
        assert "Neo4j not available" in result.error

    @pytest.mark.asyncio
    async def test_store_knowledge_decision(self):
        """Test store_knowledge with decision type."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = True
        system._neo4j = MagicMock()
        system._neo4j.call_tool = AsyncMock(return_value=MockToolResult(
            success=True,
            data={"id": "dec1", "type": "Decision"}
        ))

        result = await system.store_knowledge(
            "decision",
            "Use React for frontend",
            rationale="Team expertise"
        )

        assert result.success is True
        assert result.data == {"id": "dec1", "type": "Decision"}

        system._neo4j.call_tool.assert_called_once_with("record_decision", {
            "content": "Use React for frontend",
            "rationale": "Team expertise"
        })

    @pytest.mark.asyncio
    async def test_store_knowledge_pattern(self):
        """Test store_knowledge with pattern type."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = True
        system._neo4j = MagicMock()
        system._neo4j.call_tool = AsyncMock(return_value=MockToolResult(
            success=True,
            data={"id": "pat1"}
        ))

        result = await system.store_knowledge(
            "pattern",
            "Morning focus sessions",
            type="productivity"
        )

        assert result.success is True
        system._neo4j.call_tool.assert_called_once_with("record_pattern", {
            "content": "Morning focus sessions",
            "type": "productivity"
        })

    @pytest.mark.asyncio
    async def test_store_knowledge_commitment(self):
        """Test store_knowledge with commitment type."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = True
        system._neo4j = MagicMock()
        system._neo4j.call_tool = AsyncMock(return_value=MockToolResult(
            success=True,
            data={"id": "com1"}
        ))

        result = await system.store_knowledge(
            "commitment",
            "Daily standup at 9am"
        )

        assert result.success is True
        system._neo4j.call_tool.assert_called_once_with("create_commitment", {
            "content": "Daily standup at 9am"
        })

    @pytest.mark.asyncio
    async def test_store_knowledge_entity(self):
        """Test store_knowledge with entity type uses name arg."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = True
        system._neo4j = MagicMock()
        system._neo4j.call_tool = AsyncMock(return_value=MockToolResult(
            success=True,
            data={"id": "ent1"}
        ))

        result = await system.store_knowledge(
            "entity",
            "Ashley",
            type="person",
            domain="family"
        )

        assert result.success is True
        # Entity uses "name" instead of "content"
        system._neo4j.call_tool.assert_called_once_with("create_entity", {
            "name": "Ashley",
            "type": "person",
            "domain": "family"
        })

    @pytest.mark.asyncio
    async def test_store_knowledge_unknown_type(self):
        """Test store_knowledge fails for unknown type."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = True

        result = await system.store_knowledge("unknown_type", "Content")

        assert result.success is False
        assert "Unknown knowledge type" in result.error
        assert "unknown_type" in result.error

    @pytest.mark.asyncio
    async def test_store_knowledge_adapter_failure(self):
        """Test store_knowledge handles adapter failure."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = True
        system._neo4j = MagicMock()
        system._neo4j.call_tool = AsyncMock(return_value=MockToolResult(
            success=False,
            error="Storage failed"
        ))

        result = await system.store_knowledge("decision", "Test")

        assert result.success is False
        assert result.error == "Storage failed"

    @pytest.mark.asyncio
    async def test_store_knowledge_exception(self):
        """Test store_knowledge handles exception."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j_available = True
        system._neo4j = MagicMock()
        system._neo4j.call_tool = AsyncMock(side_effect=Exception("Crash"))

        result = await system.store_knowledge("decision", "Test")

        assert result.success is False
        assert "Knowledge storage error" in result.error


class TestMemorySystemClose:
    """Test MemorySystem.close() method."""

    @pytest.mark.asyncio
    async def test_close_with_neo4j(self):
        """Test close() closes Neo4j adapter."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j = MagicMock()
        system._neo4j.close = AsyncMock()
        system._chroma = None

        await system.close()

        system._neo4j.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_with_chroma(self):
        """Test close() closes ChromaDB adapter."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j = None
        system._chroma = MagicMock()
        system._chroma.close = AsyncMock()

        await system.close()

        system._chroma.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_with_both_adapters(self):
        """Test close() closes both adapters."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j = MagicMock()
        system._neo4j.close = AsyncMock()
        system._chroma = MagicMock()
        system._chroma.close = AsyncMock()

        await system.close()

        system._neo4j.close.assert_called_once()
        system._chroma.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_no_adapters(self):
        """Test close() handles no adapters gracefully."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j = None
        system._chroma = None

        # Should not raise
        await system.close()


class TestMemorySystemHealthCheck:
    """Test MemorySystem.health_check() method."""

    @pytest.mark.asyncio
    async def test_health_check_no_backends(self):
        """Test health_check with no backends configured."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j = None
        system._chroma = None
        system._neo4j_available = False
        system._chroma_available = False

        result = await system.health_check()

        assert result.success is True
        assert result.data["backends"]["neo4j"]["status"] == "not_configured"
        assert result.data["backends"]["chroma"]["status"] == "not_configured"
        assert result.data["any_available"] is False

    @pytest.mark.asyncio
    async def test_health_check_with_neo4j(self):
        """Test health_check with Neo4j available."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j = MagicMock()
        system._neo4j.health_check = AsyncMock(return_value=MockToolResult(
            success=True,
            data={"status": "healthy", "latency_ms": 5}
        ))
        system._chroma = None
        system._neo4j_available = True
        system._chroma_available = False

        result = await system.health_check()

        assert result.success is True
        assert result.data["backends"]["neo4j"]["status"] == "healthy"
        assert result.data["backends"]["chroma"]["status"] == "not_configured"
        assert result.data["any_available"] is True

    @pytest.mark.asyncio
    async def test_health_check_with_chroma(self):
        """Test health_check with ChromaDB available."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j = None
        system._chroma = MagicMock()
        system._chroma.health_check = AsyncMock(return_value=MockToolResult(
            success=True,
            data={"status": "healthy", "collections": 4}
        ))
        system._neo4j_available = False
        system._chroma_available = True

        result = await system.health_check()

        assert result.success is True
        assert result.data["backends"]["neo4j"]["status"] == "not_configured"
        assert result.data["backends"]["chroma"]["status"] == "healthy"
        assert result.data["any_available"] is True

    @pytest.mark.asyncio
    async def test_health_check_adapter_error(self):
        """Test health_check handles adapter health check failure."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j = MagicMock()
        system._neo4j.health_check = AsyncMock(return_value=MockToolResult(
            success=False,
            error="Connection timeout"
        ))
        system._chroma = None
        system._neo4j_available = True
        system._chroma_available = False

        result = await system.health_check()

        assert result.success is True
        assert result.data["backends"]["neo4j"]["error"] == "Connection timeout"

    @pytest.mark.asyncio
    async def test_health_check_exception(self):
        """Test health_check handles exception."""
        from Tools.memory_integration import MemorySystem

        system = MemorySystem.__new__(MemorySystem)
        system._neo4j = MagicMock()
        system._neo4j.health_check = AsyncMock(side_effect=Exception("Crash"))
        system._chroma = None
        system._neo4j_available = True
        system._chroma_available = False

        result = await system.health_check()

        assert result.success is True
        assert "Crash" in result.data["backends"]["neo4j"]["error"]


class TestMemorySystemSingleton:
    """Test singleton functions for MemorySystem."""

    def test_get_memory_system_returns_none_initially(self):
        """Test get_memory_system returns None when not initialized."""
        import Tools.memory_integration as mi

        # Reset singleton
        mi._memory_system = None

        result = mi.get_memory_system()

        assert result is None

    @pytest.mark.asyncio
    async def test_init_memory_system_creates_instance(self):
        """Test init_memory_system creates and returns instance."""
        import Tools.memory_integration as mi

        # Reset singleton
        mi._memory_system = None

        with patch.object(mi.MemorySystem, '__init__', return_value=None):
            system = await mi.init_memory_system()

        assert system is not None
        assert mi._memory_system is system

    @pytest.mark.asyncio
    async def test_get_memory_system_after_init(self):
        """Test get_memory_system returns instance after init."""
        import Tools.memory_integration as mi

        # Reset singleton
        mi._memory_system = None

        with patch.object(mi.MemorySystem, '__init__', return_value=None):
            await mi.init_memory_system()
            result = mi.get_memory_system()

        assert result is not None
        assert result is mi._memory_system
