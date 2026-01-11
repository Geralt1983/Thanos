"""
Unit tests for ChromaDB adapter (chroma_adapter.py).

Tests the ChromaAdapter class for vector storage operations
with semantic search capabilities.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
from dataclasses import dataclass


# Mock chromadb before importing the adapter
mock_chromadb = MagicMock()
mock_settings = MagicMock()
mock_openai = MagicMock()


class TestChromaAdapterImports:
    """Test ChromaDB adapter import behavior."""

    def test_chromadb_available_flag_exists(self):
        """Test CHROMADB_AVAILABLE flag is defined."""
        with patch.dict(sys.modules, {'chromadb': mock_chromadb, 'chromadb.config': MagicMock()}):
            # Force reimport
            if 'Tools.adapters.chroma_adapter' in sys.modules:
                del sys.modules['Tools.adapters.chroma_adapter']
            from Tools.adapters.chroma_adapter import CHROMADB_AVAILABLE
            # The actual value depends on whether chromadb is installed
            assert isinstance(CHROMADB_AVAILABLE, bool)

    def test_vector_schema_defined(self):
        """Test VECTOR_SCHEMA is properly defined."""
        from Tools.adapters.chroma_adapter import VECTOR_SCHEMA

        assert "collections" in VECTOR_SCHEMA
        assert "commitments" in VECTOR_SCHEMA["collections"]
        assert "decisions" in VECTOR_SCHEMA["collections"]
        assert "patterns" in VECTOR_SCHEMA["collections"]
        assert "observations" in VECTOR_SCHEMA["collections"]
        assert "conversations" in VECTOR_SCHEMA["collections"]
        assert "entities" in VECTOR_SCHEMA["collections"]
        assert VECTOR_SCHEMA["embedding_model"] == "text-embedding-3-small"
        assert VECTOR_SCHEMA["embedding_dimensions"] == 1536


class TestChromaAdapterInitialization:
    """Test ChromaAdapter initialization."""

    @patch('Tools.adapters.chroma_adapter.CHROMADB_AVAILABLE', False)
    def test_init_raises_without_chromadb(self):
        """Test initialization fails when chromadb not available."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        with pytest.raises(ImportError) as exc:
            ChromaAdapter()
        assert "chromadb package not installed" in str(exc.value)


class TestChromaAdapterProperties:
    """Test ChromaAdapter property accessors."""

    def test_name_property(self):
        """Test name property returns 'chroma'."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        # Create mock instance
        adapter = object.__new__(ChromaAdapter)
        assert adapter.name == "chroma"


class TestChromaAdapterListTools:
    """Test ChromaAdapter.list_tools() method."""

    def test_list_tools_returns_all_tools(self):
        """Test list_tools returns all available operations."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        tools = adapter.list_tools()

        tool_names = [t["name"] for t in tools]
        expected_tools = [
            "store_memory",
            "store_batch",
            "semantic_search",
            "search_all_collections",
            "list_collections",
            "get_collection_stats",
            "delete_memory",
            "clear_collection",
            "get_memory",
            "update_metadata"
        ]

        for expected in expected_tools:
            assert expected in tool_names

    def test_list_tools_has_descriptions(self):
        """Test all tools have descriptions."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        tools = adapter.list_tools()

        for tool in tools:
            assert "description" in tool
            assert len(tool["description"]) > 0

    def test_list_tools_has_parameters(self):
        """Test all tools have parameters defined."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        tools = adapter.list_tools()

        for tool in tools:
            assert "parameters" in tool


class TestChromaAdapterCallTool:
    """Test ChromaAdapter.call_tool() routing."""

    @pytest.mark.asyncio
    async def test_call_tool_unknown_tool(self):
        """Test call_tool returns error for unknown tool."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        result = await adapter.call_tool("unknown_tool", {})

        assert result.success is False
        assert "Unknown tool" in result.error

    @pytest.mark.asyncio
    async def test_call_tool_routes_to_handler(self):
        """Test call_tool routes to correct handler."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        adapter._list_collections = AsyncMock(return_value=MagicMock(success=True))

        await adapter.call_tool("list_collections", {})

        adapter._list_collections.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_tool_catches_exception(self):
        """Test call_tool catches and returns exceptions."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        adapter._list_collections = AsyncMock(side_effect=Exception("Crash"))

        result = await adapter.call_tool("list_collections", {})

        assert result.success is False
        assert "ChromaDB error" in result.error


class TestChromaAdapterStoreMemory:
    """Test ChromaAdapter._store_memory() method."""

    @pytest.mark.asyncio
    async def test_store_memory_no_embedding(self):
        """Test store_memory fails without embedding."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        adapter._generate_embedding = MagicMock(return_value=None)

        result = await adapter._store_memory({"content": "test content"})

        assert result.success is False
        assert "Could not generate embedding" in result.error

    @pytest.mark.asyncio
    async def test_store_memory_success(self):
        """Test store_memory stores content correctly."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        adapter._generate_embedding = MagicMock(return_value=[0.1] * 1536)

        mock_collection = MagicMock()
        adapter._get_collection = MagicMock(return_value=mock_collection)

        result = await adapter._store_memory({
            "content": "This is a test memory",
            "collection": "observations",
            "metadata": {"domain": "test"}
        })

        assert result.success is True
        assert "id" in result.data
        assert result.data["collection"] == "observations"
        mock_collection.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_memory_default_collection(self):
        """Test store_memory uses default collection."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        adapter._generate_embedding = MagicMock(return_value=[0.1] * 1536)

        mock_collection = MagicMock()
        adapter._get_collection = MagicMock(return_value=mock_collection)

        result = await adapter._store_memory({"content": "test"})

        adapter._get_collection.assert_called_with("observations")

    @pytest.mark.asyncio
    async def test_store_memory_cleans_metadata(self):
        """Test store_memory converts metadata to valid types."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        adapter._generate_embedding = MagicMock(return_value=[0.1] * 1536)

        mock_collection = MagicMock()
        adapter._get_collection = MagicMock(return_value=mock_collection)

        result = await adapter._store_memory({
            "content": "test",
            "metadata": {
                "string": "value",
                "number": 123,
                "bool": True,
                "none": None,  # Should be filtered
                "list": [1, 2, 3]  # Should be converted to string
            }
        })

        assert result.success is True
        # Verify metadata was passed correctly
        call_args = mock_collection.add.call_args
        metadata = call_args.kwargs.get("metadatas", call_args[1].get("metadatas"))[0]
        assert "string" in metadata
        assert "number" in metadata
        assert "bool" in metadata
        assert "none" not in metadata  # None values filtered


class TestChromaAdapterStoreBatch:
    """Test ChromaAdapter._store_batch() method."""

    @pytest.mark.asyncio
    async def test_store_batch_empty_items(self):
        """Test store_batch fails with empty items."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)

        result = await adapter._store_batch({"items": []})

        assert result.success is False
        assert "No items provided" in result.error

    @pytest.mark.asyncio
    async def test_store_batch_no_embeddings(self):
        """Test store_batch fails when batch embedding generation fails."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        # Mock batch method to return None (simulating API failure)
        adapter._generate_embeddings_batch = MagicMock(return_value=None)

        result = await adapter._store_batch({
            "items": [{"content": "item1"}, {"content": "item2"}]
        })

        assert result.success is False
        assert "Could not generate embeddings" in result.error
        # Verify batch method was called once with both texts
        adapter._generate_embeddings_batch.assert_called_once_with(["item1", "item2"])

    @pytest.mark.asyncio
    async def test_store_batch_success(self):
        """Test store_batch stores multiple items using batch embeddings."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        # Mock batch method to return list of embeddings (one per item)
        adapter._generate_embeddings_batch = MagicMock(return_value=[[0.1] * 1536, [0.1] * 1536])

        mock_collection = MagicMock()
        adapter._get_collection = MagicMock(return_value=mock_collection)

        result = await adapter._store_batch({
            "items": [
                {"content": "item1", "metadata": {"key": "val1"}},
                {"content": "item2", "metadata": {"key": "val2"}}
            ],
            "collection": "decisions"
        })

        assert result.success is True
        assert result.data["stored"] == 2
        assert len(result.data["ids"]) == 2
        # Verify batch method was called once with both texts
        adapter._generate_embeddings_batch.assert_called_once_with(["item1", "item2"])

    @pytest.mark.asyncio
    async def test_store_batch_skips_items_without_content(self):
        """Test store_batch skips items without content before batch processing."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        # Mock batch method to return embeddings only for items with content
        # Only item1 and item3 have content, so batch receives 2 texts
        adapter._generate_embeddings_batch = MagicMock(return_value=[[0.1] * 1536, [0.2] * 1536])

        mock_collection = MagicMock()
        adapter._get_collection = MagicMock(return_value=mock_collection)

        result = await adapter._store_batch({
            "items": [
                {"content": "item1"},
                {"content": ""},  # Empty content - filtered out
                {"content": "item3"}
            ]
        })

        assert result.success is True
        assert result.data["stored"] == 2  # Only 2 items with content
        # Verify batch method was called once with only non-empty content
        adapter._generate_embeddings_batch.assert_called_once_with(["item1", "item3"])


class TestChromaAdapterSemanticSearch:
    """Test ChromaAdapter._semantic_search() method."""

    @pytest.mark.asyncio
    async def test_semantic_search_no_embedding(self):
        """Test semantic_search fails without query embedding."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        adapter._generate_embedding = MagicMock(return_value=None)

        result = await adapter._semantic_search({"query": "test query"})

        assert result.success is False
        assert "Could not generate query embedding" in result.error

    @pytest.mark.asyncio
    async def test_semantic_search_returns_results(self):
        """Test semantic_search returns formatted results."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        adapter._generate_embedding = MagicMock(return_value=[0.1] * 1536)

        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["id1", "id2"]],
            "documents": [["content1", "content2"]],
            "metadatas": [[{"domain": "work"}, {"domain": "personal"}]],
            "distances": [[0.1, 0.2]]
        }
        adapter._get_collection = MagicMock(return_value=mock_collection)

        result = await adapter._semantic_search({
            "query": "test query",
            "collection": "observations",
            "limit": 10
        })

        assert result.success is True
        assert result.data["count"] == 2
        assert len(result.data["results"]) == 2
        assert result.data["results"][0]["similarity"] == 0.9  # 1 - 0.1

    @pytest.mark.asyncio
    async def test_semantic_search_with_filter(self):
        """Test semantic_search passes filter correctly."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        adapter._generate_embedding = MagicMock(return_value=[0.1] * 1536)

        mock_collection = MagicMock()
        mock_collection.query.return_value = {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
        adapter._get_collection = MagicMock(return_value=mock_collection)

        await adapter._semantic_search({
            "query": "test",
            "where": {"domain": "work"}
        })

        call_args = mock_collection.query.call_args
        assert call_args.kwargs.get("where") == {"domain": "work"}

    @pytest.mark.asyncio
    async def test_semantic_search_empty_results(self):
        """Test semantic_search handles empty results."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        adapter._generate_embedding = MagicMock(return_value=[0.1] * 1536)

        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }
        adapter._get_collection = MagicMock(return_value=mock_collection)

        result = await adapter._semantic_search({"query": "test"})

        assert result.success is True
        assert result.data["count"] == 0
        assert result.data["results"] == []


class TestChromaAdapterSearchAllCollections:
    """Test ChromaAdapter._search_all_collections() method."""

    @pytest.mark.asyncio
    async def test_search_all_no_embedding(self):
        """Test search_all_collections fails without embedding."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        adapter._generate_embedding = MagicMock(return_value=None)

        result = await adapter._search_all_collections({"query": "test"})

        assert result.success is False

    @pytest.mark.asyncio
    async def test_search_all_collections_success(self):
        """Test search_all_collections searches all collections."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        adapter._generate_embedding = MagicMock(return_value=[0.1] * 1536)

        mock_coll1 = MagicMock()
        mock_coll1.name = "decisions"
        mock_coll1.query.return_value = {
            "ids": [["id1"]],
            "documents": [["doc1"]],
            "metadatas": [[{}]],
            "distances": [[0.1]]
        }

        mock_coll2 = MagicMock()
        mock_coll2.name = "patterns"
        mock_coll2.query.return_value = {
            "ids": [["id2"]],
            "documents": [["doc2"]],
            "metadatas": [[{}]],
            "distances": [[0.2]]
        }

        adapter._client = MagicMock()
        adapter._client.list_collections.return_value = [mock_coll1, mock_coll2]

        result = await adapter._search_all_collections({"query": "test", "limit": 5})

        assert result.success is True
        assert result.data["count"] == 2
        # Results should be sorted by similarity
        assert result.data["results"][0]["similarity"] > result.data["results"][1]["similarity"]


class TestChromaAdapterListCollections:
    """Test ChromaAdapter._list_collections() method."""

    @pytest.mark.asyncio
    async def test_list_collections_success(self):
        """Test list_collections returns all collections."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)

        mock_coll1 = MagicMock()
        mock_coll1.name = "decisions"
        mock_coll1.count.return_value = 10
        mock_coll1.metadata = {"hnsw:space": "cosine"}

        mock_coll2 = MagicMock()
        mock_coll2.name = "patterns"
        mock_coll2.count.return_value = 5
        mock_coll2.metadata = {}

        adapter._client = MagicMock()
        adapter._client.list_collections.return_value = [mock_coll1, mock_coll2]

        result = await adapter._list_collections({})

        assert result.success is True
        assert result.data["total"] == 2
        assert len(result.data["collections"]) == 2
        assert result.data["collections"][0]["name"] == "decisions"
        assert result.data["collections"][0]["count"] == 10


class TestChromaAdapterGetCollectionStats:
    """Test ChromaAdapter._get_collection_stats() method."""

    @pytest.mark.asyncio
    async def test_get_collection_stats_success(self):
        """Test get_collection_stats returns stats."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)

        mock_collection = MagicMock()
        mock_collection.count.return_value = 25
        mock_collection.metadata = {"hnsw:space": "cosine"}
        adapter._get_collection = MagicMock(return_value=mock_collection)

        result = await adapter._get_collection_stats({"collection": "decisions"})

        assert result.success is True
        assert result.data["collection"] == "decisions"
        assert result.data["count"] == 25

    @pytest.mark.asyncio
    async def test_get_collection_stats_not_found(self):
        """Test get_collection_stats handles missing collection."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        adapter._get_collection = MagicMock(side_effect=Exception("Not found"))

        result = await adapter._get_collection_stats({"collection": "nonexistent"})

        assert result.success is False
        assert "Collection not found" in result.error


class TestChromaAdapterDeleteMemory:
    """Test ChromaAdapter._delete_memory() method."""

    @pytest.mark.asyncio
    async def test_delete_memory_success(self):
        """Test delete_memory deletes correctly."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)

        mock_collection = MagicMock()
        adapter._get_collection = MagicMock(return_value=mock_collection)

        result = await adapter._delete_memory({
            "memory_id": "mem123",
            "collection": "decisions"
        })

        assert result.success is True
        assert result.data["deleted"] == "mem123"
        mock_collection.delete.assert_called_once_with(ids=["mem123"])


class TestChromaAdapterClearCollection:
    """Test ChromaAdapter._clear_collection() method."""

    @pytest.mark.asyncio
    async def test_clear_collection_no_confirm(self):
        """Test clear_collection requires confirmation."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)

        result = await adapter._clear_collection({
            "collection": "decisions",
            "confirm": False
        })

        assert result.success is False
        assert "confirm=true" in result.error

    @pytest.mark.asyncio
    async def test_clear_collection_success(self):
        """Test clear_collection deletes collection."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        adapter._client = MagicMock()
        adapter._collections = {"decisions": MagicMock()}

        result = await adapter._clear_collection({
            "collection": "decisions",
            "confirm": True
        })

        assert result.success is True
        assert result.data["cleared"] == "decisions"
        adapter._client.delete_collection.assert_called_once_with(name="decisions")
        assert "decisions" not in adapter._collections


class TestChromaAdapterGetMemory:
    """Test ChromaAdapter._get_memory() method."""

    @pytest.mark.asyncio
    async def test_get_memory_not_found(self):
        """Test get_memory handles missing memory."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)

        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": [], "documents": [], "metadatas": [], "embeddings": []}
        adapter._get_collection = MagicMock(return_value=mock_collection)

        result = await adapter._get_memory({
            "memory_id": "nonexistent",
            "collection": "decisions"
        })

        assert result.success is False
        assert "Memory not found" in result.error

    @pytest.mark.asyncio
    async def test_get_memory_success(self):
        """Test get_memory returns memory correctly."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)

        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": ["mem123"],
            "documents": ["Test content"],
            "metadatas": [{"domain": "work"}],
            "embeddings": [[0.1] * 1536]
        }
        adapter._get_collection = MagicMock(return_value=mock_collection)

        result = await adapter._get_memory({
            "memory_id": "mem123",
            "collection": "decisions"
        })

        assert result.success is True
        assert result.data["id"] == "mem123"
        assert result.data["content"] == "Test content"
        assert result.data["has_embedding"] is True


class TestChromaAdapterUpdateMetadata:
    """Test ChromaAdapter._update_metadata() method."""

    @pytest.mark.asyncio
    async def test_update_metadata_not_found(self):
        """Test update_metadata handles missing memory."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)

        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": [], "metadatas": []}
        adapter._get_collection = MagicMock(return_value=mock_collection)

        result = await adapter._update_metadata({
            "memory_id": "nonexistent",
            "collection": "decisions",
            "metadata": {"key": "value"}
        })

        assert result.success is False
        assert "Memory not found" in result.error

    @pytest.mark.asyncio
    async def test_update_metadata_success(self):
        """Test update_metadata merges metadata correctly."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)

        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": ["mem123"],
            "metadatas": [{"existing": "value", "domain": "work"}]
        }
        adapter._get_collection = MagicMock(return_value=mock_collection)

        result = await adapter._update_metadata({
            "memory_id": "mem123",
            "collection": "decisions",
            "metadata": {"new_key": "new_value", "domain": "personal"}
        })

        assert result.success is True
        assert result.data["metadata"]["existing"] == "value"
        assert result.data["metadata"]["new_key"] == "new_value"
        assert result.data["metadata"]["domain"] == "personal"  # Overwritten


class TestChromaAdapterGetCollection:
    """Test ChromaAdapter._get_collection() caching."""

    def test_get_collection_creates_new(self):
        """Test _get_collection creates new collection."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        adapter._collections = {}
        adapter._client = MagicMock()
        mock_collection = MagicMock()
        adapter._client.get_or_create_collection.return_value = mock_collection

        result = adapter._get_collection("new_collection")

        assert result == mock_collection
        assert "new_collection" in adapter._collections
        adapter._client.get_or_create_collection.assert_called_once()

    def test_get_collection_returns_cached(self):
        """Test _get_collection returns cached collection."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        mock_collection = MagicMock()
        adapter._collections = {"cached": mock_collection}
        adapter._client = MagicMock()

        result = adapter._get_collection("cached")

        assert result == mock_collection
        adapter._client.get_or_create_collection.assert_not_called()


class TestChromaAdapterGenerateEmbedding:
    """Test ChromaAdapter._generate_embedding() method."""

    def test_generate_embedding_no_client(self):
        """Test _generate_embedding returns None without client."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        adapter._openai_client = None

        result = adapter._generate_embedding("test text")

        assert result is None

    def test_generate_embedding_success(self):
        """Test _generate_embedding returns embedding via batch delegation."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        mock_response = MagicMock()
        # Mock OpenAI API response with index field (required by batch method)
        mock_response.data = [MagicMock(embedding=[0.1] * 1536, index=0)]
        adapter._openai_client = MagicMock()
        adapter._openai_client.embeddings.create.return_value = mock_response

        result = adapter._generate_embedding("test text")

        assert result == [0.1] * 1536
        # Verify it calls batch API with single-item list
        adapter._openai_client.embeddings.create.assert_called_once()

    def test_generate_embedding_exception(self):
        """Test _generate_embedding handles exception."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        adapter._openai_client = MagicMock()
        adapter._openai_client.embeddings.create.side_effect = Exception("API error")

        result = adapter._generate_embedding("test text")

        assert result is None


class TestChromaAdapterClose:
    """Test ChromaAdapter.close() method."""

    @pytest.mark.asyncio
    async def test_close_clears_collections(self):
        """Test close clears collection cache."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        adapter._collections = {"a": MagicMock(), "b": MagicMock()}

        await adapter.close()

        assert len(adapter._collections) == 0


class TestChromaAdapterHealthCheck:
    """Test ChromaAdapter.health_check() method."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test health_check returns status."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        adapter._client = MagicMock()
        adapter._client.list_collections.return_value = [MagicMock(), MagicMock()]
        adapter._openai_client = MagicMock()
        adapter._persist_dir = "/tmp/test"

        result = await adapter.health_check()

        assert result.success is True
        assert result.data["status"] == "ok"
        assert result.data["adapter"] == "chroma"
        assert result.data["collections"] == 2
        assert result.data["embeddings"] == "available"

    @pytest.mark.asyncio
    async def test_health_check_no_openai(self):
        """Test health_check reports unavailable embeddings."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        adapter._client = MagicMock()
        adapter._client.list_collections.return_value = []
        adapter._openai_client = None
        adapter._persist_dir = "/tmp/test"

        result = await adapter.health_check()

        assert result.success is True
        assert result.data["embeddings"] == "unavailable"

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health_check handles connection failure."""
        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = object.__new__(ChromaAdapter)
        adapter._client = MagicMock()
        adapter._client.list_collections.side_effect = Exception("Connection failed")

        result = await adapter.health_check()

        assert result.success is False
        assert "connection failed" in result.error.lower()
