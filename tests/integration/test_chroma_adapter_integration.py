"""
Integration tests for ChromaDB adapter with batch embedding generation.

These tests use actual ChromaDB instances and (optionally) real OpenAI API calls
to validate the batch embedding optimization works correctly in real-world scenarios.

Tests can be run with pytest markers:
  - pytest -m integration         # Run all integration tests
  - pytest -m "integration and requires_openai"  # Tests that need OpenAI API key
  - pytest --skip-integration     # Skip all integration tests
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
import time

# Import ChromaDB if available
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

# Import OpenAI if available
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# Check if OpenAI API key is available
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HAS_OPENAI_CREDENTIALS = OPENAI_AVAILABLE and OPENAI_API_KEY is not None


# =============================================================================
# Pytest Markers and Fixtures
# =============================================================================

pytestmark = pytest.mark.integration


@pytest.fixture(scope="function")
def temp_chroma_dir():
    """Create a temporary directory for ChromaDB storage."""
    temp_dir = tempfile.mkdtemp(prefix="chroma_integration_test_")
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def chroma_client(temp_chroma_dir):
    """Create a ChromaDB client with temporary storage."""
    if not CHROMADB_AVAILABLE:
        pytest.skip("ChromaDB not available")

    client = chromadb.PersistentClient(path=temp_chroma_dir)
    yield client
    # Client cleanup happens when temp_chroma_dir is removed


@pytest.fixture(scope="function")
def chroma_adapter(temp_chroma_dir):
    """Create a ChromaAdapter instance with temporary storage."""
    if not CHROMADB_AVAILABLE:
        pytest.skip("ChromaDB not available")

    from Tools.adapters.chroma_adapter import ChromaAdapter

    # Mock OpenAI client to avoid real API calls by default
    with patch('Tools.adapters.chroma_adapter.OPENAI_AVAILABLE', True):
        adapter = ChromaAdapter(persist_directory=temp_chroma_dir)

        # Create a mock OpenAI client with realistic embedding responses
        mock_openai_client = MagicMock()
        mock_embeddings = MagicMock()
        mock_openai_client.embeddings = mock_embeddings
        adapter._openai_client = mock_openai_client

        yield adapter


@pytest.fixture(scope="function")
def chroma_adapter_with_real_openai(temp_chroma_dir):
    """
    Create a ChromaAdapter instance with real OpenAI API.

    Tests using this fixture will be skipped if OPENAI_API_KEY is not set.
    """
    if not CHROMADB_AVAILABLE:
        pytest.skip("ChromaDB not available")

    if not HAS_OPENAI_CREDENTIALS:
        pytest.skip("OpenAI API key not available (set OPENAI_API_KEY env var)")

    from Tools.adapters.chroma_adapter import ChromaAdapter

    adapter = ChromaAdapter(
        persist_directory=temp_chroma_dir,
        openai_api_key=OPENAI_API_KEY
    )
    yield adapter


# =============================================================================
# Integration Tests - Batch Operations with Mocked OpenAI
# =============================================================================

class TestChromaBatchEmbeddingIntegration:
    """Integration tests for batch embedding generation with ChromaDB."""

    @pytest.mark.asyncio
    async def test_store_batch_10_items_successfully(self, chroma_adapter):
        """
        Test storing 10+ items in batch successfully.

        Acceptance Criteria:
        - All 10 items stored successfully
        - ChromaDB contains all items with correct metadata
        - Batch embedding method called once
        """
        # Prepare mock OpenAI response for batch embedding
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1] * 1536, index=i)
            for i in range(10)
        ]
        chroma_adapter._openai_client.embeddings.create.return_value = mock_response

        # Prepare 10 test items
        items = [
            {
                "content": f"Test memory item {i} with unique content",
                "metadata": {
                    "date": "2026-01-11",
                    "domain": "testing",
                    "test_id": i
                }
            }
            for i in range(10)
        ]

        # Store batch
        result = await chroma_adapter._store_batch({
            "items": items,
            "collection": "observations"
        })

        # Verify success
        assert result.success is True
        assert result.data["stored"] == 10
        assert len(result.data["ids"]) == 10
        assert result.data["collection"] == "observations"

        # Verify batch API was called once
        assert chroma_adapter._openai_client.embeddings.create.call_count == 1

        # Verify all texts were sent in single batch
        call_args = chroma_adapter._openai_client.embeddings.create.call_args
        assert "input" in call_args.kwargs
        assert len(call_args.kwargs["input"]) == 10

        # Verify ChromaDB storage - get collection and check count
        collection = chroma_adapter._get_collection("observations")
        count_result = collection.count()
        assert count_result == 10

        # Verify metadata is preserved
        stored_data = collection.get(include=["metadatas", "documents"])
        assert len(stored_data["ids"]) == 10
        assert all("test_id" in meta for meta in stored_data["metadatas"])

    @pytest.mark.asyncio
    async def test_batch_embeddings_correct_order(self, chroma_adapter):
        """
        Test that embeddings maintain correct order matching input.

        Acceptance Criteria:
        - Embeddings returned in same order as inputs
        - ChromaDB stores documents with matching embeddings
        - Order preservation works even with shuffled API response
        """
        # Mock OpenAI response with NON-SEQUENTIAL indices to test sorting
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.5, 0.5] + [0.0] * 1534, index=2),
            MagicMock(embedding=[0.1, 0.1] + [0.0] * 1534, index=0),
            MagicMock(embedding=[0.3, 0.3] + [0.0] * 1534, index=1),
        ]
        chroma_adapter._openai_client.embeddings.create.return_value = mock_response

        items = [
            {"content": "First item", "metadata": {"order": 0}},
            {"content": "Second item", "metadata": {"order": 1}},
            {"content": "Third item", "metadata": {"order": 2}},
        ]

        result = await chroma_adapter._store_batch({
            "items": items,
            "collection": "patterns"
        })

        assert result.success is True
        assert result.data["stored"] == 3

        # Retrieve and verify order
        collection = chroma_adapter._get_collection("patterns")
        stored_ids = result.data["ids"]

        # Get items in stored order
        stored_data = collection.get(ids=stored_ids, include=["metadatas", "documents", "embeddings"])

        # Verify documents match input order
        assert stored_data["documents"][0] == "First item"
        assert stored_data["documents"][1] == "Second item"
        assert stored_data["documents"][2] == "Third item"

        # Verify embeddings match document order (not API response order)
        assert stored_data["embeddings"][0][0] == 0.1  # First embedding
        assert stored_data["embeddings"][1][0] == 0.3  # Second embedding
        assert stored_data["embeddings"][2][0] == 0.5  # Third embedding

    @pytest.mark.asyncio
    async def test_semantic_search_after_batch_storage(self, chroma_adapter):
        """
        Test that semantic search works correctly with batch-generated embeddings.

        Acceptance Criteria:
        - Items stored via batch can be found with semantic search
        - Search returns most relevant results
        - Embeddings are correctly indexed for similarity search
        """
        # Mock embeddings with distinct patterns for search testing
        # Items about "python" will have embedding [0.9, 0.1, ...]
        # Items about "javascript" will have embedding [0.1, 0.9, ...]
        mock_store_response = MagicMock()
        mock_store_response.data = [
            MagicMock(embedding=[0.9, 0.1] + [0.0] * 1534, index=0),  # python item
            MagicMock(embedding=[0.9, 0.1] + [0.0] * 1534, index=1),  # python item
            MagicMock(embedding=[0.1, 0.9] + [0.0] * 1534, index=2),  # javascript item
        ]
        chroma_adapter._openai_client.embeddings.create.return_value = mock_store_response

        # Store items
        items = [
            {"content": "Python is a great programming language", "metadata": {"lang": "python"}},
            {"content": "Python development best practices", "metadata": {"lang": "python"}},
            {"content": "JavaScript async await patterns", "metadata": {"lang": "javascript"}},
        ]

        store_result = await chroma_adapter._store_batch({
            "items": items,
            "collection": "decisions"
        })

        assert store_result.success is True

        # Mock search query embedding (similar to python items)
        mock_search_response = MagicMock()
        mock_search_response.data = [
            MagicMock(embedding=[0.9, 0.1] + [0.0] * 1534, index=0)
        ]
        chroma_adapter._openai_client.embeddings.create.return_value = mock_search_response

        # Perform semantic search
        search_result = await chroma_adapter._semantic_search({
            "query": "python programming",
            "collection": "decisions",
            "limit": 2
        })

        assert search_result.success is True
        assert len(search_result.data["results"]) <= 2

        # Verify search returns relevant results (python items, not javascript)
        results = search_result.data["results"]
        for result_item in results:
            # Both top results should be python-related
            assert "python" in result_item["content"].lower()

    @pytest.mark.asyncio
    async def test_large_batch_chunking(self, chroma_adapter):
        """
        Test that large batches (>2048 items) are chunked correctly.

        Acceptance Criteria:
        - Batches >2048 items are automatically chunked
        - All items are stored successfully
        - Multiple API calls made (one per chunk)
        """
        # Create a batch of 2148 items (will be chunked into 2048 + 100)
        batch_size = 2148

        # Mock embeddings for both chunks
        def mock_create_embeddings(**kwargs):
            input_texts = kwargs.get("input", [])
            num_texts = len(input_texts)
            mock_response = MagicMock()
            mock_response.data = [
                MagicMock(embedding=[0.1] * 1536, index=i)
                for i in range(num_texts)
            ]
            return mock_response

        chroma_adapter._openai_client.embeddings.create.side_effect = mock_create_embeddings

        # Prepare large batch
        items = [
            {"content": f"Item {i}", "metadata": {"item_id": i}}
            for i in range(batch_size)
        ]

        # Store batch
        result = await chroma_adapter._store_batch({
            "items": items,
            "collection": "observations"
        })

        # Verify all items stored
        assert result.success is True
        assert result.data["stored"] == batch_size

        # Verify chunking occurred (should be 2 API calls: 2048 + 100)
        assert chroma_adapter._openai_client.embeddings.create.call_count == 2

        # Verify chunk sizes
        calls = chroma_adapter._openai_client.embeddings.create.call_args_list
        assert len(calls[0].kwargs["input"]) == 2048  # First chunk
        assert len(calls[1].kwargs["input"]) == 100   # Second chunk

        # Verify ChromaDB storage
        collection = chroma_adapter._get_collection("observations")
        assert collection.count() == batch_size

    @pytest.mark.asyncio
    async def test_no_data_corruption_in_batch(self, chroma_adapter):
        """
        Test that batch operations don't cause data corruption.

        Acceptance Criteria:
        - Each item's metadata matches its content
        - No cross-contamination between items
        - IDs are unique
        - All metadata fields preserved
        """
        # Mock embeddings
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[float(i)] * 1536, index=i)
            for i in range(5)
        ]
        chroma_adapter._openai_client.embeddings.create.return_value = mock_response

        # Create items with unique, verifiable metadata
        items = [
            {
                "content": f"Unique content for item {i}",
                "metadata": {
                    "item_number": i,
                    "unique_key": f"value_{i}",
                    "category": f"cat_{i % 3}"
                }
            }
            for i in range(5)
        ]

        # Store batch
        result = await chroma_adapter._store_batch({
            "items": items,
            "collection": "commitments"
        })

        assert result.success is True
        stored_ids = result.data["ids"]

        # Verify all IDs are unique
        assert len(stored_ids) == len(set(stored_ids))

        # Retrieve all stored items
        collection = chroma_adapter._get_collection("commitments")
        stored_data = collection.get(
            ids=stored_ids,
            include=["metadatas", "documents", "embeddings"]
        )

        # Verify data integrity for each item
        for i in range(5):
            doc = stored_data["documents"][i]
            meta = stored_data["metadatas"][i]
            embedding = stored_data["embeddings"][i]

            # Verify content matches
            assert doc == f"Unique content for item {i}"

            # Verify metadata matches
            assert meta["item_number"] == i
            assert meta["unique_key"] == f"value_{i}"
            assert meta["category"] == f"cat_{i % 3}"

            # Verify embedding matches (first element should be float(i))
            assert embedding[0] == float(i)

            # Verify stored_at timestamp was added
            assert "stored_at" in meta

    @pytest.mark.asyncio
    async def test_batch_with_empty_content_items(self, chroma_adapter):
        """
        Test that items without content are filtered correctly.

        Acceptance Criteria:
        - Items without content are skipped
        - Items with content are stored
        - No errors from empty items
        """
        # Mock embeddings for 2 items (only items with content)
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1] * 1536, index=0),
            MagicMock(embedding=[0.2] * 1536, index=1),
        ]
        chroma_adapter._openai_client.embeddings.create.return_value = mock_response

        items = [
            {"content": "First item", "metadata": {"has_content": True}},
            {"content": "", "metadata": {"has_content": False}},  # Empty content
            {"content": "Second item", "metadata": {"has_content": True}},
            {"metadata": {"has_content": False}},  # No content key
        ]

        result = await chroma_adapter._store_batch({
            "items": items,
            "collection": "patterns"
        })

        # Only 2 items should be stored
        assert result.success is True
        assert result.data["stored"] == 2

        # Verify only valid items stored
        collection = chroma_adapter._get_collection("patterns")
        stored_data = collection.get(include=["metadatas"])

        assert all(meta["has_content"] is True for meta in stored_data["metadatas"])


# =============================================================================
# Integration Tests - With Real OpenAI API
# =============================================================================

class TestChromaBatchEmbeddingWithRealOpenAI:
    """
    Integration tests using real OpenAI API.

    These tests are skipped if OPENAI_API_KEY is not set.
    They validate the complete end-to-end flow with actual embeddings.
    """

    @pytest.mark.requires_openai
    @pytest.mark.asyncio
    async def test_real_batch_embedding_generation(self, chroma_adapter_with_real_openai):
        """
        Test batch embedding generation with real OpenAI API.

        Acceptance Criteria:
        - Real embeddings generated successfully
        - All items stored in ChromaDB
        - Semantic search returns semantically similar results
        """
        adapter = chroma_adapter_with_real_openai

        # Prepare test items with semantically related content
        items = [
            {"content": "The quick brown fox jumps over the lazy dog", "metadata": {"topic": "animals"}},
            {"content": "A fast auburn canine leaps above a sleepy hound", "metadata": {"topic": "animals"}},
            {"content": "Python is a popular programming language", "metadata": {"topic": "tech"}},
            {"content": "JavaScript runs in web browsers", "metadata": {"topic": "tech"}},
            {"content": "The weather is sunny today", "metadata": {"topic": "weather"}},
        ]

        # Measure performance
        start_time = time.time()
        result = await adapter._store_batch({
            "items": items,
            "collection": "observations"
        })
        batch_time = time.time() - start_time

        # Verify success
        assert result.success is True
        assert result.data["stored"] == 5

        # Verify reasonable performance (should be much faster than 5 sequential calls)
        # With 200ms per call, sequential would be ~1000ms, batch should be <500ms
        assert batch_time < 1.0, f"Batch operation took {batch_time:.2f}s (expected <1s)"

        # Test semantic search with similar query
        search_result = await adapter._semantic_search({
            "query": "tell me about dogs and foxes",
            "collection": "observations",
            "limit": 3
        })

        assert search_result.success is True
        results = search_result.data["results"]

        # Top results should be about animals (semantically similar)
        assert len(results) > 0
        # At least one of top 2 results should be animal-related
        top_topics = [r["metadata"]["topic"] for r in results[:2]]
        assert "animals" in top_topics

    @pytest.mark.requires_openai
    @pytest.mark.asyncio
    async def test_real_embeddings_quality(self, chroma_adapter_with_real_openai):
        """
        Test that real embeddings enable accurate semantic search.

        Acceptance Criteria:
        - Semantically similar queries return relevant results
        - Embeddings correctly capture semantic meaning
        - Search quality is high
        """
        adapter = chroma_adapter_with_real_openai

        # Store diverse content
        items = [
            {"content": "Machine learning algorithms for classification", "metadata": {"id": 1}},
            {"content": "Deep neural networks and backpropagation", "metadata": {"id": 2}},
            {"content": "Recipe for chocolate chip cookies", "metadata": {"id": 3}},
            {"content": "How to bake the perfect cake", "metadata": {"id": 4}},
            {"content": "Financial markets and stock trading", "metadata": {"id": 5}},
        ]

        store_result = await adapter._store_batch({
            "items": items,
            "collection": "decisions"
        })

        assert store_result.success is True

        # Search for ML-related content
        ml_search = await adapter._semantic_search({
            "query": "artificial intelligence and neural networks",
            "collection": "decisions",
            "limit": 2
        })

        assert ml_search.success is True
        ml_results = ml_search.data["results"]

        # Top results should be ML-related (IDs 1 or 2)
        assert len(ml_results) > 0
        top_result_ids = [r["metadata"]["id"] for r in ml_results]
        assert any(rid in [1, 2] for rid in top_result_ids), \
            f"Expected ML results (1,2), got {top_result_ids}"

        # Search for baking-related content
        baking_search = await adapter._semantic_search({
            "query": "cooking desserts and pastries",
            "collection": "decisions",
            "limit": 2
        })

        assert baking_search.success is True
        baking_results = baking_search.data["results"]

        # Top results should be baking-related (IDs 3 or 4)
        assert len(baking_results) > 0
        top_baking_ids = [r["metadata"]["id"] for r in baking_results]
        assert any(rid in [3, 4] for rid in top_baking_ids), \
            f"Expected baking results (3,4), got {top_baking_ids}"

    @pytest.mark.requires_openai
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_performance_improvement_real_api(self, chroma_adapter_with_real_openai):
        """
        Test actual performance improvement with real OpenAI API.

        This test measures real latency to validate the performance claims.

        Acceptance Criteria:
        - Batch operation completes in reasonable time
        - Performance is better than theoretical sequential time
        - Demonstrates the optimization benefit
        """
        adapter = chroma_adapter_with_real_openai

        # Prepare 10 items
        items = [
            {"content": f"Memory item {i} with unique content for testing batch performance", "metadata": {"index": i}}
            for i in range(10)
        ]

        # Measure batch operation time
        start_time = time.time()
        result = await adapter._store_batch({
            "items": items,
            "collection": "observations"
        })
        batch_time = time.time() - start_time

        assert result.success is True
        assert result.data["stored"] == 10

        # Expected performance:
        # - Sequential: 10 calls × 200ms = 2000ms
        # - Batch: 1 call × 300ms = 300ms
        # Allow some variance, but should be significantly faster than 2000ms
        assert batch_time < 1.5, \
            f"Batch operation took {batch_time:.2f}s (expected <1.5s for 10 items)"

        # Log performance for documentation
        print(f"\n=== Performance Test Results ===")
        print(f"Items stored: 10")
        print(f"Batch operation time: {batch_time:.3f}s")
        print(f"Theoretical sequential time: ~2.0s (10 × 200ms)")
        print(f"Performance improvement: {((2.0 - batch_time) / 2.0 * 100):.1f}%")
        print(f"================================\n")


# =============================================================================
# Integration Tests - Error Scenarios
# =============================================================================

class TestChromaBatchEmbeddingErrorHandling:
    """Integration tests for error handling in batch operations."""

    @pytest.mark.asyncio
    async def test_batch_api_failure_handling(self, chroma_adapter):
        """
        Test that batch API failures are handled gracefully.

        Acceptance Criteria:
        - API failure returns error result
        - No items stored in ChromaDB
        - Error message is informative
        """
        # Mock API failure
        chroma_adapter._openai_client.embeddings.create.side_effect = Exception("API Error")

        items = [
            {"content": f"Item {i}", "metadata": {"id": i}}
            for i in range(5)
        ]

        result = await chroma_adapter._store_batch({
            "items": items,
            "collection": "observations"
        })

        # Verify failure
        assert result.success is False
        assert "Could not generate embeddings" in result.error

        # Verify no items stored
        collection = chroma_adapter._get_collection("observations")
        assert collection.count() == 0

    @pytest.mark.asyncio
    async def test_empty_batch_handling(self, chroma_adapter):
        """
        Test that empty batches are handled correctly.

        Acceptance Criteria:
        - Empty batch returns error
        - No API calls made
        - Clear error message
        """
        result = await chroma_adapter._store_batch({
            "items": [],
            "collection": "observations"
        })

        assert result.success is False
        assert "No items provided" in result.error

        # Verify no API calls made
        assert chroma_adapter._openai_client.embeddings.create.call_count == 0


# =============================================================================
# Utility Functions
# =============================================================================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (uses real dependencies)"
    )
    config.addinivalue_line(
        "markers",
        "requires_openai: mark test as requiring OpenAI API key"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running"
    )
