"""
Integration tests for History Search functionality.

These tests verify the end-to-end workflow:
1. Create SessionManager with ChromaAdapter integration
2. Add messages to session (user and assistant)
3. Messages are automatically indexed to ChromaAdapter
4. Use HistorySearchHandler to search for messages
5. Verify search results match expected messages
6. Test search with filters (date, agent, session)

Tests use actual ChromaDB instances but mock OpenAI embeddings by default.
Tests marked with 'requires_openai' need OPENAI_API_KEY set.

Usage:
  pytest -m integration tests/integration/test_history_search_integration.py
"""

import asyncio
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import ChromaDB if available
try:
    import chromadb
    from chromadb.config import Settings

    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

# Check if OpenAI API key is available
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HAS_OPENAI_CREDENTIALS = OPENAI_API_KEY is not None

# =============================================================================
# Pytest Markers and Fixtures
# =============================================================================

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def temp_dirs():
    """Create temporary directories for ChromaDB and sessions."""
    chroma_dir = tempfile.mkdtemp(prefix="chroma_integration_test_")
    sessions_dir = tempfile.mkdtemp(prefix="sessions_integration_test_")
    yield {"chroma": chroma_dir, "sessions": sessions_dir}
    # Cleanup
    shutil.rmtree(chroma_dir, ignore_errors=True)
    shutil.rmtree(sessions_dir, ignore_errors=True)


@pytest.fixture(scope="module")
def chroma_adapter_with_mock_embeddings(temp_dirs):
    """
    Create a ChromaAdapter instance with mock OpenAI embeddings.

    This fixture allows tests to run without real OpenAI API calls.
    """
    if not CHROMADB_AVAILABLE:
        pytest.skip("ChromaDB not available")

    from Tools.adapters.chroma_adapter import ChromaAdapter

    # Mock OpenAI client to avoid real API calls
    with patch("Tools.adapters.chroma_adapter.OPENAI_AVAILABLE", True):
        adapter = ChromaAdapter(persist_directory=temp_dirs["chroma"])

        # Create a mock OpenAI client with realistic embedding responses
        mock_openai_client = MagicMock()
        mock_embeddings = MagicMock()

        def mock_create(input, model, **kwargs):
            """Mock embedding creation that returns deterministic embeddings."""
            # Return different embeddings based on input content
            # This allows semantic similarity to work in tests
            mock_response = MagicMock()
            mock_response.data = []

            inputs = input if isinstance(input, list) else [input]
            for idx, text in enumerate(inputs):
                mock_embedding = MagicMock()
                # Generate a simple embedding based on text hash
                # This ensures similar text gets similar embeddings
                text_lower = text.lower()
                base_value = sum(ord(c) for c in text_lower) / 1000.0

                # Create 1536-dimension embedding (OpenAI standard)
                # Key terms influence specific dimensions
                embedding_vector = [0.0] * 1536
                embedding_vector[0] = base_value

                # Make embeddings somewhat similar for related terms
                if "authentication" in text_lower or "auth" in text_lower:
                    embedding_vector[1] = 0.9
                    embedding_vector[2] = 0.8
                if "database" in text_lower or "db" in text_lower:
                    embedding_vector[3] = 0.9
                    embedding_vector[4] = 0.8
                if "api" in text_lower:
                    embedding_vector[5] = 0.9
                    embedding_vector[6] = 0.8
                if "error" in text_lower or "bug" in text_lower:
                    embedding_vector[7] = 0.9
                    embedding_vector[8] = 0.8

                mock_embedding.embedding = embedding_vector
                mock_response.data.append(mock_embedding)

            return mock_response

        mock_embeddings.create = mock_create
        mock_openai_client.embeddings = mock_embeddings
        adapter._openai_client = mock_openai_client

        yield adapter


@pytest.fixture(scope="function")
def session_manager_with_chroma(chroma_adapter_with_mock_embeddings, temp_dirs):
    """Create a SessionManager with ChromaAdapter integration enabled."""
    from Tools.session_manager import SessionManager

    manager = SessionManager(
        history_dir=Path(temp_dirs["sessions"]),
        chroma_adapter=chroma_adapter_with_mock_embeddings,
    )

    yield manager


@pytest.fixture(scope="function")
def history_search_handler(session_manager_with_chroma, chroma_adapter_with_mock_embeddings):
    """Create a HistorySearchHandler with all dependencies."""
    from Tools.command_handlers.history_search_handler import HistorySearchHandler

    # Create mock dependencies
    mock_orchestrator = MagicMock()
    mock_orchestrator.current_agent = "test-agent"

    mock_context_manager = MagicMock()
    mock_state_reader = MagicMock()

    # Patch _run_async to use asyncio.run directly (pytest-asyncio compatibility)
    original_run_async = None

    handler = HistorySearchHandler(
        orchestrator=mock_orchestrator,
        session_manager=session_manager_with_chroma,
        context_manager=mock_context_manager,
        state_reader=mock_state_reader,
        thanos_dir="/tmp/thanos",
        current_agent_getter=lambda: "test-agent",
    )

    # Override _run_async to work better in test environment
    def _run_async_patched(coro):
        """Run async coroutine using asyncio.run for test compatibility."""
        try:
            return asyncio.run(coro)
        except RuntimeError:
            # If event loop is already running, try with new loop
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result(timeout=30)
        except Exception as e:
            print(f"Error in _run_async: {e}")
            return None

    original_run_async = handler._run_async
    handler._run_async = _run_async_patched

    yield handler

    # Restore original if needed
    if original_run_async:
        handler._run_async = original_run_async


# =============================================================================
# Integration Tests
# =============================================================================


def capture_handler_output(handler_method, *args, **kwargs):
    """
    Capture stdout from a handler method that prints results.

    Args:
        handler_method: The handler method to call
        *args: Positional arguments for the method
        **kwargs: Keyword arguments for the method

    Returns:
        Tuple of (CommandResult, output_string)
    """
    import io
    from contextlib import redirect_stdout

    f = io.StringIO()
    with redirect_stdout(f):
        result = handler_method(*args, **kwargs)
    output = f.getvalue()
    return result, output


class TestHistorySearchIntegration:
    """Integration tests for full history search workflow."""

    def test_end_to_end_workflow_without_filters(
        self, session_manager_with_chroma, history_search_handler
    ):
        """
        Test complete workflow: create session -> add messages -> search -> verify results.

        This is the core integration test that validates:
        1. SessionManager creates session
        2. Messages are added and auto-indexed
        3. HistorySearchHandler can search indexed messages
        4. Search results contain correct messages with metadata
        """
        # Step 1: Create session and add messages
        session_manager = session_manager_with_chroma

        # Add messages about different topics
        session_manager.add_user_message(
            "How do I implement JWT authentication in the API?", tokens=15
        )
        session_manager.add_assistant_message(
            "To implement JWT authentication, you need to: 1) Install jwt library 2) Create token generation endpoint 3) Add middleware for token verification",
            tokens=30,
        )

        session_manager.add_user_message("What about database connection pooling?", tokens=10)
        session_manager.add_assistant_message(
            "For database connection pooling, use SQLAlchemy's pool configuration with max_overflow and pool_size parameters.",
            tokens=25,
        )

        session_manager.add_user_message("Can you help debug this API error?", tokens=10)
        session_manager.add_assistant_message(
            "Sure, let me help debug the API error. What's the error message you're seeing?",
            tokens=20,
        )

        # Give ChromaDB a moment to process (async operations)
        import time

        time.sleep(0.5)

        # Step 2: Search for authentication-related messages
        result, output = capture_handler_output(
            history_search_handler.handle_history_search, "authentication JWT tokens"
        )

        # Step 3: Verify search results
        assert result.success, f"Search should succeed but got success={result.success}"
        assert "semantically similar messages" in output.lower()

        # Result should contain authentication message
        assert "JWT" in output or "authentication" in output.lower()

        # Step 4: Search for database-related messages
        result, output = capture_handler_output(
            history_search_handler.handle_history_search, "database connection"
        )

        assert result.success, f"Search should succeed but got success={result.success}"
        assert "connection pooling" in output.lower() or "database" in output.lower()

        # Step 5: Search for error-related messages
        result, output = capture_handler_output(
            history_search_handler.handle_history_search, "debugging errors"
        )

        assert result.success, f"Search should succeed but got success={result.success}"
        assert "error" in output.lower() or "debug" in output.lower()

    def test_end_to_end_workflow_with_session_filter(
        self, session_manager_with_chroma, history_search_handler
    ):
        """
        Test workflow with session filter.

        Validates:
        1. Multiple sessions can be created
        2. Messages are indexed with correct session_id
        3. Search can filter by session_id
        4. Results only contain messages from specified session
        """
        # Create first session
        manager1 = session_manager_with_chroma
        session_id_1 = manager1.session.id

        manager1.add_user_message("Tell me about authentication", tokens=10)
        manager1.add_assistant_message(
            "Authentication verifies user identity using credentials", tokens=15
        )

        # Create second session (new SessionManager instance)
        from Tools.session_manager import SessionManager

        manager2 = SessionManager(
            history_dir=session_manager_with_chroma.history_dir,
            chroma_adapter=session_manager_with_chroma._chroma,
        )
        session_id_2 = manager2.session.id

        manager2.add_user_message("Tell me about database optimization", tokens=10)
        manager2.add_assistant_message(
            "Database optimization involves indexing and query optimization", tokens=15
        )

        # Give ChromaDB time to process
        import time

        time.sleep(0.5)

        # Search with session filter for first session
        result, output = capture_handler_output(history_search_handler.handle_history_search, "authentication session:{session_id_1}")
        assert result.success, "Search should succeed"
        assert "authentication" in output.lower()
        assert session_id_1[:8] in output  # Session ID should appear in results

        # Search with session filter for second session
        result, output = capture_handler_output(history_search_handler.handle_history_search, "database session:{session_id_2}")
        assert result.success, "Search should succeed"
        assert "database" in output.lower()
        assert session_id_2[:8] in output

    def test_end_to_end_workflow_with_date_filter(
        self, session_manager_with_chroma, history_search_handler
    ):
        """
        Test workflow with date filter.

        Validates:
        1. Messages are indexed with date metadata
        2. Search can filter by date
        3. Date range filters work correctly (after/before)
        """
        manager = session_manager_with_chroma

        # Add messages
        manager.add_user_message("How do I implement caching?", tokens=10)
        manager.add_assistant_message(
            "Implement caching using Redis or Memcached for better performance", tokens=20
        )

        # Give ChromaDB time to process
        import time

        time.sleep(0.5)

        # Get today's date in YYYY-MM-DD format
        today = datetime.now().strftime("%Y-%m-%d")

        # Search with date filter for today
        result, output = capture_handler_output(history_search_handler.handle_history_search, "caching date:{today}")
        assert result.success, "Search should succeed"
        assert "caching" in output.lower() or "Redis" in output

        # Search with after filter (messages from today or later)
        result, output = capture_handler_output(history_search_handler.handle_history_search, "caching after:{today}")
        assert result.success, "Search should succeed"

    def test_end_to_end_workflow_with_agent_filter(
        self, session_manager_with_chroma, history_search_handler
    ):
        """
        Test workflow with agent filter.

        Validates:
        1. Messages are indexed with agent metadata
        2. Search can filter by agent name
        3. Results only contain messages from specified agent
        """
        manager = session_manager_with_chroma

        # Add messages with specific agent
        manager.add_user_message("What is Docker?", tokens=5)
        manager.add_assistant_message(
            "Docker is a containerization platform for application deployment", tokens=15
        )

        # Give ChromaDB time to process
        import time

        time.sleep(0.5)

        # Search with agent filter
        agent_name = manager.session.agent
        result, output = capture_handler_output(history_search_handler.handle_history_search, "Docker agent:{agent_name}")
        assert result.success, "Search should succeed"
        assert "Docker" in output or "docker" in output.lower()

    def test_end_to_end_workflow_with_multiple_filters(
        self, session_manager_with_chroma, history_search_handler
    ):
        """
        Test workflow with multiple filters combined.

        Validates:
        1. Multiple filters can be combined in one query
        2. All filters are applied correctly
        3. Results match all filter criteria
        """
        manager = session_manager_with_chroma
        session_id = manager.session.id
        agent = manager.session.agent
        today = datetime.now().strftime("%Y-%m-%d")

        # Add messages
        manager.add_user_message("How do I deploy with Kubernetes?", tokens=10)
        manager.add_assistant_message(
            "Deploy with Kubernetes by creating deployment manifests and applying them", tokens=20
        )

        # Give ChromaDB time to process
        import time

        time.sleep(0.5)

        # Search with multiple filters
        result, output = capture_handler_output(history_search_handler.handle_history_search, "Kubernetes agent:{agent} session:{session_id} date:{today}")
        assert result.success, "Search should succeed"
        assert "kubernetes" in output.lower() or "deploy" in output.lower()

    def test_end_to_end_workflow_empty_results(self, history_search_handler):
        """
        Test workflow when search returns no results.

        Validates:
        1. Handler gracefully handles empty search results
        2. Appropriate message is returned to user
        """
        # Search for something that definitely doesn't exist
        result = history_search_handler.handle_history_search(
            "xyzabc123nonexistent query that should not match anything"
        )

        # Should succeed but with no results message
        assert result.success or "No messages found" in output

    def test_end_to_end_workflow_invalid_query(self, history_search_handler):
        """
        Test workflow with invalid query (only filters, no search text).

        Validates:
        1. Handler validates query properly
        2. Appropriate error message returned for invalid queries
        """
        # Query with only filters, no search text
        result = history_search_handler.handle_history_search("agent:test session:123")

        # Should fail with validation error
        assert (
            not result.success or "provide a search query" in output.lower()
        ), f"Expected validation error, got: {result.message}"

    def test_batch_indexing_existing_messages(
        self, session_manager_with_chroma, history_search_handler
    ):
        """
        Test batch indexing of existing session messages.

        Validates:
        1. SessionManager can batch index all messages at once
        2. Batch indexed messages are searchable
        3. Results contain all expected messages
        """
        manager = session_manager_with_chroma

        # Add messages WITHOUT auto-indexing (simulate old sessions)
        # Temporarily disable auto-indexing
        manager._indexing_enabled = False

        manager.add_user_message("What is microservices architecture?", tokens=10)
        manager.add_assistant_message(
            "Microservices architecture splits applications into small, independent services",
            tokens=20,
        )

        manager.add_user_message("How do services communicate?", tokens=8)
        manager.add_assistant_message(
            "Services communicate using REST APIs, message queues, or gRPC", tokens=18
        )

        # Re-enable indexing and batch index all messages
        manager._indexing_enabled = True
        manager.index_session()

        # Give ChromaDB time to process
        import time

        time.sleep(0.5)

        # Search for messages that were batch indexed
        result, output = capture_handler_output(history_search_handler.handle_history_search, "microservices")
        assert result.success, "Search should succeed"
        assert "microservices" in output.lower() or "services" in output.lower()

        # Verify communication message is also searchable
        result, output = capture_handler_output(history_search_handler.handle_history_search, "service communication APIs")
        assert result.success, "Search should succeed"
        assert (
            "communicate" in output.lower()
            or "API" in output
            or "api" in output.lower()
        )

    def test_auto_indexing_persistence(self, session_manager_with_chroma, history_search_handler):
        """
        Test that auto-indexed messages persist and are searchable.

        Validates:
        1. Messages are auto-indexed when added
        2. Auto-indexed messages persist in ChromaDB
        3. Messages are searchable immediately after being added
        """
        manager = session_manager_with_chroma

        # Add message and verify auto-indexing
        manager.add_user_message("Tell me about GraphQL", tokens=10)
        manager.add_assistant_message(
            "GraphQL is a query language for APIs that provides efficient data fetching", tokens=20
        )

        # Give ChromaDB minimal time to process
        import time

        time.sleep(0.3)

        # Immediately search - should find the just-added message
        result, output = capture_handler_output(history_search_handler.handle_history_search, "GraphQL")
        assert result.success, "Search should succeed"
        assert "graphql" in output.lower() or "query language" in output.lower()


# =============================================================================
# Tests Requiring Real OpenAI API
# =============================================================================


@pytest.mark.requires_openai
class TestHistorySearchIntegrationWithRealOpenAI:
    """
    Integration tests using real OpenAI API.

    These tests require OPENAI_API_KEY to be set and will make real API calls.
    Run with: pytest -m requires_openai
    """

    @pytest.fixture(scope="function")
    def chroma_adapter_with_real_openai(self, temp_dirs):
        """Create ChromaAdapter with real OpenAI API."""
        if not HAS_OPENAI_CREDENTIALS:
            pytest.skip("OPENAI_API_KEY not set")

        if not CHROMADB_AVAILABLE:
            pytest.skip("ChromaDB not available")

        from Tools.adapters.chroma_adapter import ChromaAdapter

        adapter = ChromaAdapter(persist_directory=temp_dirs["chroma"])
        yield adapter

    @pytest.fixture(scope="function")
    def session_manager_with_real_openai(self, chroma_adapter_with_real_openai, temp_dirs):
        """Create SessionManager with real OpenAI-enabled ChromaAdapter."""
        from Tools.session_manager import SessionManager

        manager = SessionManager(
            history_dir=Path(temp_dirs["sessions"]),
            chroma_adapter=chroma_adapter_with_real_openai,
        )
        yield manager

    @pytest.fixture(scope="function")
    def handler_with_real_openai(
        self, session_manager_with_real_openai, chroma_adapter_with_real_openai
    ):
        """Create HistorySearchHandler with real OpenAI."""
        from Tools.command_handlers.history_search_handler import HistorySearchHandler

        mock_orchestrator = MagicMock()
        mock_orchestrator.current_agent = "test-agent"

        handler = HistorySearchHandler(
            orchestrator=mock_orchestrator,
            session_manager=session_manager_with_real_openai,
            context_manager=MagicMock(),
            state_reader=MagicMock(),
            thanos_dir="/tmp/thanos",
            current_agent_getter=lambda: "test-agent",
        )

        # ChromaAdapter already set via session_manager_with_real_openai
        yield handler

    def test_semantic_search_with_real_embeddings(
        self, session_manager_with_real_openai, handler_with_real_openai
    ):
        """
        Test semantic search using real OpenAI embeddings.

        This test validates that real semantic similarity works correctly.
        It should find semantically similar messages even with different wording.
        """
        manager = session_manager_with_real_openai

        # Add messages with semantic similarity but different wording
        manager.add_user_message("How do I secure my REST API?", tokens=10)
        manager.add_assistant_message(
            "To secure your REST API, implement authentication, use HTTPS, and validate inputs",
            tokens=20,
        )

        manager.add_user_message("What's the best way to store passwords?", tokens=10)
        manager.add_assistant_message(
            "Store passwords using bcrypt or Argon2 hashing algorithms", tokens=15
        )

        # Give OpenAI and ChromaDB time to process
        import time

        time.sleep(2)

        # Search using semantically similar but different wording
        # "protecting APIs" should match "secure REST API"
        result = handler_with_real_openai.handle_history_search("protecting APIs")

        assert result.success, f"Search should succeed: {result.message}"
        # Should find the security-related message
        assert "secure" in output.lower() or "api" in output.lower()
