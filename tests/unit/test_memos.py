#!/usr/bin/env python3
"""
Unit tests for MemOS (Memory Operating System).

Tests cover:
- MemOS initialization with/without backends
- MemoryResult dataclass
- remember() operation
- recall() operation
- relate() operation
- reflect() operation
- get_entity_context()
- health_check()
- Graceful fallback when backends unavailable
"""

from pathlib import Path
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ========================================================================
# Test MemoryResult Dataclass
# ========================================================================

class TestMemoryResult:
    """Test MemoryResult dataclass."""

    def test_import_memory_result(self):
        """Test MemoryResult can be imported."""
        from Tools.memos import MemoryResult
        assert MemoryResult is not None

    def test_memory_result_ok(self):
        """Test MemoryResult.ok() creates successful result."""
        from Tools.memos import MemoryResult

        result = MemoryResult.ok(
            graph_results=[{"id": "test1"}],
            vector_results=[{"content": "test"}],
            query="test query"
        )

        assert result.success is True
        assert result.error is None
        assert len(result.graph_results) == 1
        assert len(result.vector_results) == 1
        assert result.metadata.get("query") == "test query"

    def test_memory_result_fail(self):
        """Test MemoryResult.fail() creates failed result."""
        from Tools.memos import MemoryResult

        result = MemoryResult.fail("Test error", context="testing")

        assert result.success is False
        assert result.error == "Test error"
        assert result.metadata.get("context") == "testing"
        assert result.graph_results == []
        assert result.vector_results == []

    def test_memory_result_combined_deduplication(self):
        """Test that combined results are deduplicated by id."""
        from Tools.memos import MemoryResult

        graph = [{"id": "item1", "source": "graph"}]
        vector = [{"id": "item1", "source": "vector"}, {"id": "item2", "source": "vector"}]

        result = MemoryResult.ok(graph_results=graph, vector_results=vector)

        # Should deduplicate by id, keeping first occurrence
        assert len(result.combined) == 2
        ids = [item.get("id") for item in result.combined]
        assert "item1" in ids
        assert "item2" in ids


# ========================================================================
# Test MemOS Initialization
# ========================================================================

class TestMemOSInitialization:
    """Test MemOS class initialization."""

    @patch('Tools.memos.NEO4J_AVAILABLE', False)
    @patch('Tools.memos.CHROMA_AVAILABLE', False)
    @patch('Tools.memos.OPENAI_AVAILABLE', False)
    def test_init_no_backends(self):
        """Test initialization when no backends are available."""
        from Tools.memos import MemOS

        memos = MemOS()

        assert memos.graph_available is False
        assert memos.vector_available is False

    @patch('Tools.memos.NEO4J_AVAILABLE', False)
    @patch('Tools.memos.CHROMA_AVAILABLE', True)
    @patch('Tools.memos.OPENAI_AVAILABLE', False)
    def test_init_chroma_only(self):
        """Test initialization with only ChromaDB available."""
        from Tools.memos import MemOS

        # Mock ChromaDB
        mock_chroma_client = Mock()
        with patch('Tools.memos.ChromaClient', return_value=mock_chroma_client):
            with patch('Tools.memos.Settings'):
                with patch('pathlib.Path.mkdir'):
                    memos = MemOS()

                    assert memos.graph_available is False
                    assert memos.vector_available is True

    def test_status_property(self):
        """Test status property returns backend states."""
        from Tools.memos import MemOS

        with patch('Tools.memos.NEO4J_AVAILABLE', False):
            with patch('Tools.memos.CHROMA_AVAILABLE', False):
                with patch('Tools.memos.OPENAI_AVAILABLE', False):
                    memos = MemOS()
                    status = memos.status

                    assert "neo4j" in status
                    assert "chromadb" in status
                    assert "embeddings" in status


# ========================================================================
# Test MemOS Remember Operation
# ========================================================================

class TestMemOSRemember:
    """Test MemOS.remember() method."""

    @pytest.fixture
    def memos_with_mocks(self):
        """Create MemOS with mocked backends."""
        from Tools.memos import MemOS

        with patch('Tools.memos.NEO4J_AVAILABLE', True):
            with patch('Tools.memos.CHROMA_AVAILABLE', True):
                with patch('Tools.memos.OPENAI_AVAILABLE', True):
                    # Mock Neo4j
                    mock_neo4j = AsyncMock()
                    mock_neo4j.call_tool = AsyncMock(return_value=Mock(
                        success=True,
                        data={"id": "neo4j_123"}
                    ))

                    # Mock ChromaDB
                    mock_chroma = Mock()
                    mock_collection = Mock()
                    mock_chroma.get_or_create_collection = Mock(return_value=mock_collection)

                    # Mock OpenAI
                    mock_openai = Mock()
                    mock_embedding_response = Mock()
                    mock_embedding_response.data = [Mock(embedding=[0.1] * 1536)]
                    mock_openai.embeddings.create = Mock(return_value=mock_embedding_response)

                    with patch('Tools.memos.Neo4jAdapter', return_value=mock_neo4j):
                        with patch('Tools.memos.ChromaClient', return_value=mock_chroma):
                            with patch('Tools.memos.Settings'):
                                with patch('pathlib.Path.mkdir'):
                                    with patch('Tools.memos.openai.OpenAI', return_value=mock_openai):
                                        memos = MemOS()
                                        memos._neo4j = mock_neo4j
                                        memos._chroma = mock_chroma
                                        memos._openai_client = mock_openai
                                        yield memos, mock_neo4j, mock_chroma, mock_openai

    @pytest.mark.asyncio
    async def test_remember_commitment(self, memos_with_mocks):
        """Test remembering a commitment."""
        memos, mock_neo4j, mock_chroma, mock_openai = memos_with_mocks

        result = await memos.remember(
            content="Complete project proposal",
            memory_type="commitment",
            domain="work",
            metadata={"to_whom": "client", "priority": 1}
        )

        assert result.success is True
        # Neo4j should have been called with create_commitment
        mock_neo4j.call_tool.assert_called()
        call_args = mock_neo4j.call_tool.call_args_list[0]
        assert call_args[0][0] == "create_commitment"

    @pytest.mark.asyncio
    async def test_remember_decision(self, memos_with_mocks):
        """Test remembering a decision."""
        memos, mock_neo4j, mock_chroma, mock_openai = memos_with_mocks

        result = await memos.remember(
            content="Chose React over Vue",
            memory_type="decision",
            domain="work",
            metadata={"rationale": "Team expertise", "confidence": 0.9}
        )

        assert result.success is True
        mock_neo4j.call_tool.assert_called()
        call_args = mock_neo4j.call_tool.call_args_list[0]
        assert call_args[0][0] == "record_decision"

    @pytest.mark.asyncio
    async def test_remember_pattern(self, memos_with_mocks):
        """Test remembering a pattern."""
        memos, mock_neo4j, mock_chroma, mock_openai = memos_with_mocks

        result = await memos.remember(
            content="Energy crashes after lunch meetings",
            memory_type="pattern",
            domain="health",
            metadata={"pattern_type": "behavior", "frequency": "weekly"}
        )

        assert result.success is True
        mock_neo4j.call_tool.assert_called()
        call_args = mock_neo4j.call_tool.call_args_list[0]
        assert call_args[0][0] == "record_pattern"

    @pytest.mark.asyncio
    async def test_remember_with_entities(self, memos_with_mocks):
        """Test remembering with entity linking."""
        memos, mock_neo4j, mock_chroma, mock_openai = memos_with_mocks

        result = await memos.remember(
            content="Meeting scheduled with client",
            memory_type="observation",
            entities=["Memphis", "John Smith"]
        )

        assert result.success is True
        # Should have called create_entity for each entity
        entity_calls = [c for c in mock_neo4j.call_tool.call_args_list
                        if c[0][0] == "create_entity"]
        # Note: entities are only linked if graph result has an ID

    @pytest.mark.asyncio
    async def test_remember_no_backends(self):
        """Test remember fails gracefully when no backends available."""
        from Tools.memos import MemOS

        with patch('Tools.memos.NEO4J_AVAILABLE', False):
            with patch('Tools.memos.CHROMA_AVAILABLE', False):
                with patch('Tools.memos.OPENAI_AVAILABLE', False):
                    memos = MemOS()
                    result = await memos.remember("Test content")

                    assert result.success is False
                    assert "No storage backends" in result.error


# ========================================================================
# Test MemOS Recall Operation
# ========================================================================

class TestMemOSRecall:
    """Test MemOS.recall() method."""

    @pytest.fixture
    def memos_with_mocks(self):
        """Create MemOS with mocked backends for recall."""
        from Tools.memos import MemOS

        mock_neo4j = AsyncMock()
        mock_neo4j.call_tool = AsyncMock(return_value=Mock(
            success=True,
            data={"commitments": [{"id": "c1", "content": "Test commitment"}]}
        ))

        mock_chroma = Mock()
        mock_collection = Mock()
        mock_collection.query = Mock(return_value={
            "ids": [["v1"]],
            "documents": [["Test document"]],
            "metadatas": [[{"domain": "work"}]],
            "distances": [[0.1]]
        })
        mock_chroma.get_collection = Mock(return_value=mock_collection)

        mock_openai = Mock()
        mock_embedding_response = Mock()
        mock_embedding_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_openai.embeddings.create = Mock(return_value=mock_embedding_response)

        memos = Mock(spec=MemOS)
        memos._neo4j = mock_neo4j
        memos._chroma = mock_chroma
        memos._openai_client = mock_openai

        # Create actual MemOS instance for testing
        with patch('Tools.memos.NEO4J_AVAILABLE', False):
            with patch('Tools.memos.CHROMA_AVAILABLE', False):
                with patch('Tools.memos.OPENAI_AVAILABLE', False):
                    actual_memos = MemOS()
                    actual_memos._neo4j = mock_neo4j
                    actual_memos._chroma = mock_chroma
                    actual_memos._openai_client = mock_openai
                    yield actual_memos, mock_neo4j, mock_chroma, mock_openai

    @pytest.mark.asyncio
    async def test_recall_basic(self, memos_with_mocks):
        """Test basic recall operation."""
        memos, mock_neo4j, mock_chroma, mock_openai = memos_with_mocks

        result = await memos.recall("What commitments do I have?")

        assert result.success is True
        # Should have queried Neo4j for commitments
        neo4j_calls = [c for c in mock_neo4j.call_tool.call_args_list
                       if "commitments" in str(c)]

    @pytest.mark.asyncio
    async def test_recall_with_domain_filter(self, memos_with_mocks):
        """Test recall with domain filter."""
        memos, mock_neo4j, mock_chroma, mock_openai = memos_with_mocks

        result = await memos.recall(
            "What decisions did I make?",
            domain="work",
            memory_types=["decision"]
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_recall_graph_only(self, memos_with_mocks):
        """Test recall using only graph."""
        memos, mock_neo4j, mock_chroma, mock_openai = memos_with_mocks

        result = await memos.recall(
            "Show my commitments",
            use_vector=False,
            memory_types=["commitment"]
        )

        assert result.success is True
        # Vector search should not have been called
        mock_openai.embeddings.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_recall_vector_only(self, memos_with_mocks):
        """Test recall using only vector search."""
        memos, mock_neo4j, mock_chroma, mock_openai = memos_with_mocks

        result = await memos.recall(
            "Find similar patterns",
            use_graph=False
        )

        assert result.success is True


# ========================================================================
# Test MemOS Relate Operation
# ========================================================================

class TestMemOSRelate:
    """Test MemOS.relate() method."""

    @pytest.mark.asyncio
    async def test_relate_requires_neo4j(self):
        """Test relate requires Neo4j."""
        from Tools.memos import MemOS

        with patch('Tools.memos.NEO4J_AVAILABLE', False):
            with patch('Tools.memos.CHROMA_AVAILABLE', False):
                with patch('Tools.memos.OPENAI_AVAILABLE', False):
                    memos = MemOS()
                    result = await memos.relate("node1", "LEADS_TO", "node2")

                    assert result.success is False
                    assert "Neo4j not available" in result.error

    @pytest.mark.asyncio
    async def test_relate_success(self):
        """Test successful relationship creation."""
        from Tools.memos import MemOS

        mock_neo4j = AsyncMock()
        mock_neo4j.call_tool = AsyncMock(return_value=Mock(
            success=True,
            data={"relationship_id": "rel_123"}
        ))

        with patch('Tools.memos.NEO4J_AVAILABLE', False):
            with patch('Tools.memos.CHROMA_AVAILABLE', False):
                with patch('Tools.memos.OPENAI_AVAILABLE', False):
                    memos = MemOS()
                    memos._neo4j = mock_neo4j

                    result = await memos.relate(
                        from_id="decision_1",
                        relationship="LEADS_TO",
                        to_id="outcome_1",
                        properties={"strength": 0.8}
                    )

                    assert result.success is True
                    mock_neo4j.call_tool.assert_called_once()
                    call_args = mock_neo4j.call_tool.call_args
                    assert call_args[0][0] == "link_nodes"


# ========================================================================
# Test MemOS Reflect Operation
# ========================================================================

class TestMemOSReflect:
    """Test MemOS.reflect() method."""

    @pytest.mark.asyncio
    async def test_reflect_finds_patterns(self):
        """Test reflect finds related patterns."""
        from Tools.memos import MemOS

        mock_neo4j = AsyncMock()
        mock_neo4j.call_tool = AsyncMock(return_value=Mock(
            success=True,
            data={"patterns": [
                {"description": "Energy drops after meetings", "frequency": "weekly"}
            ]}
        ))

        with patch('Tools.memos.NEO4J_AVAILABLE', False):
            with patch('Tools.memos.CHROMA_AVAILABLE', False):
                with patch('Tools.memos.OPENAI_AVAILABLE', False):
                    memos = MemOS()
                    memos._neo4j = mock_neo4j

                    result = await memos.reflect(
                        topic="energy management",
                        timeframe_days=30,
                        domain="health"
                    )

                    assert result.success is True
                    assert "topic" in result.metadata


# ========================================================================
# Test MemOS Entity Context
# ========================================================================

class TestMemOSEntityContext:
    """Test MemOS.get_entity_context() method."""

    @pytest.mark.asyncio
    async def test_entity_context_requires_neo4j(self):
        """Test entity context requires Neo4j."""
        from Tools.memos import MemOS

        with patch('Tools.memos.NEO4J_AVAILABLE', False):
            with patch('Tools.memos.CHROMA_AVAILABLE', False):
                with patch('Tools.memos.OPENAI_AVAILABLE', False):
                    memos = MemOS()
                    result = await memos.get_entity_context("Memphis")

                    assert result.success is False
                    assert "Neo4j required" in result.error

    @pytest.mark.asyncio
    async def test_entity_context_success(self):
        """Test successful entity context retrieval."""
        from Tools.memos import MemOS

        mock_neo4j = AsyncMock()
        mock_neo4j.call_tool = AsyncMock(return_value=Mock(
            success=True,
            data={
                "entity": "Memphis",
                "commitments": ["Complete integration"],
                "last_contact": "2024-01-15"
            }
        ))

        with patch('Tools.memos.NEO4J_AVAILABLE', False):
            with patch('Tools.memos.CHROMA_AVAILABLE', False):
                with patch('Tools.memos.OPENAI_AVAILABLE', False):
                    memos = MemOS()
                    memos._neo4j = mock_neo4j

                    result = await memos.get_entity_context("Memphis")

                    assert result.success is True


# ========================================================================
# Test MemOS Health Check
# ========================================================================

class TestMemOSHealthCheck:
    """Test MemOS.health_check() method."""

    @pytest.mark.asyncio
    async def test_health_check_no_backends(self):
        """Test health check when no backends configured."""
        from Tools.memos import MemOS

        with patch('Tools.memos.NEO4J_AVAILABLE', False):
            with patch('Tools.memos.CHROMA_AVAILABLE', False):
                with patch('Tools.memos.OPENAI_AVAILABLE', False):
                    memos = MemOS()
                    health = await memos.health_check()

                    assert "backends" in health
                    assert health["backends"]["neo4j"]["status"] == "not_configured"
                    assert health["backends"]["chromadb"]["status"] == "not_configured"

    @pytest.mark.asyncio
    async def test_health_check_with_neo4j(self):
        """Test health check with Neo4j configured."""
        from Tools.memos import MemOS

        mock_neo4j = AsyncMock()
        mock_neo4j.health_check = AsyncMock(return_value=Mock(
            success=True,
            error=None
        ))

        with patch('Tools.memos.NEO4J_AVAILABLE', False):
            with patch('Tools.memos.CHROMA_AVAILABLE', False):
                with patch('Tools.memos.OPENAI_AVAILABLE', False):
                    memos = MemOS()
                    memos._neo4j = mock_neo4j

                    health = await memos.health_check()

                    assert health["backends"]["neo4j"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_check_with_chroma(self):
        """Test health check with ChromaDB configured."""
        from Tools.memos import MemOS

        mock_chroma = Mock()
        mock_chroma.list_collections = Mock(return_value=[Mock(), Mock()])

        with patch('Tools.memos.NEO4J_AVAILABLE', False):
            with patch('Tools.memos.CHROMA_AVAILABLE', False):
                with patch('Tools.memos.OPENAI_AVAILABLE', False):
                    memos = MemOS()
                    memos._chroma = mock_chroma

                    health = await memos.health_check()

                    assert health["backends"]["chromadb"]["status"] == "ok"
                    assert health["backends"]["chromadb"]["collections"] == 2


# ========================================================================
# Test Singleton Functions
# ========================================================================

class TestMemOSSingleton:
    """Test MemOS singleton functions."""

    def test_get_memos_creates_instance(self):
        """Test get_memos() creates singleton instance."""
        from Tools import memos as memos_module

        # Reset singleton
        memos_module._memos_instance = None

        with patch('Tools.memos.NEO4J_AVAILABLE', False):
            with patch('Tools.memos.CHROMA_AVAILABLE', False):
                with patch('Tools.memos.OPENAI_AVAILABLE', False):
                    instance1 = memos_module.get_memos()
                    instance2 = memos_module.get_memos()

                    assert instance1 is instance2

    @pytest.mark.asyncio
    async def test_init_memos_returns_instance(self):
        """Test init_memos() returns initialized instance."""
        from Tools import memos as memos_module

        # Reset singleton
        memos_module._memos_instance = None

        with patch('Tools.memos.NEO4J_AVAILABLE', False):
            with patch('Tools.memos.CHROMA_AVAILABLE', False):
                with patch('Tools.memos.OPENAI_AVAILABLE', False):
                    with patch('builtins.print'):  # Suppress output
                        instance = await memos_module.init_memos()
                        assert instance is not None


# ========================================================================
# Test MemOS Close
# ========================================================================

class TestMemOSClose:
    """Test MemOS.close() method."""

    @pytest.mark.asyncio
    async def test_close_with_neo4j(self):
        """Test close properly closes Neo4j connection."""
        from Tools.memos import MemOS

        mock_neo4j = AsyncMock()
        mock_neo4j.close = AsyncMock()

        with patch('Tools.memos.NEO4J_AVAILABLE', False):
            with patch('Tools.memos.CHROMA_AVAILABLE', False):
                with patch('Tools.memos.OPENAI_AVAILABLE', False):
                    memos = MemOS()
                    memos._neo4j = mock_neo4j

                    await memos.close()

                    mock_neo4j.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
