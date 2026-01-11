"""
Quick test to verify Neo4jSessionContext implementation.
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add Tools directory to path to import directly
sys.path.insert(0, str(Path(__file__).parent / "Tools" / "adapters"))


async def test_session_context():
    """Test Neo4jSessionContext lifecycle."""
    print("Testing Neo4jSessionContext...")

    # Import the module directly
    import neo4j_adapter
    Neo4jSessionContext = neo4j_adapter.Neo4jSessionContext
    Neo4jAdapter = neo4j_adapter.Neo4jAdapter

    # Mock the driver and adapter
    mock_driver = MagicMock()
    mock_session = AsyncMock()
    mock_driver.session = MagicMock(return_value=mock_session)

    # Create a minimal adapter with mocked driver
    adapter = MagicMock(spec=Neo4jAdapter)
    adapter._driver = mock_driver

    # Test 1: Basic session context (no transaction)
    print("  ✓ Test 1: Basic session context")
    ctx = Neo4jSessionContext(adapter, database="neo4j", batch_transaction=False)

    session = await ctx.__aenter__()
    assert session == mock_session, "Should return session"
    assert mock_driver.session.called, "Should create session"

    await ctx.__aexit__(None, None, None)
    assert mock_session.close.called, "Should close session"
    print("    ✓ Session created and closed correctly")

    # Test 2: Transaction context
    print("  ✓ Test 2: Transaction batch context")
    mock_driver.reset_mock()
    mock_session.reset_mock()
    mock_transaction = AsyncMock()
    mock_session.begin_transaction = AsyncMock(return_value=mock_transaction)

    ctx = Neo4jSessionContext(adapter, database="neo4j", batch_transaction=True)

    tx = await ctx.__aenter__()
    assert tx == mock_transaction, "Should return transaction"
    assert mock_session.begin_transaction.called, "Should begin transaction"

    await ctx.__aexit__(None, None, None)
    assert mock_transaction.commit.called, "Should commit on success"
    assert mock_session.close.called, "Should close session"
    print("    ✓ Transaction created, committed, and cleaned up")

    # Test 3: Error handling and rollback
    print("  ✓ Test 3: Error handling and rollback")
    mock_driver.reset_mock()
    mock_session.reset_mock()
    mock_transaction.reset_mock()
    mock_session.begin_transaction = AsyncMock(return_value=mock_transaction)

    ctx = Neo4jSessionContext(adapter, database="neo4j", batch_transaction=True)
    await ctx.__aenter__()

    # Simulate error by passing exception info
    result = await ctx.__aexit__(ValueError, ValueError("test error"), None)

    assert mock_transaction.rollback.called, "Should rollback on error"
    assert not mock_transaction.commit.called, "Should not commit on error"
    assert mock_session.close.called, "Should close session even on error"
    assert result is False, "Should not suppress exceptions"
    print("    ✓ Transaction rolled back on error")

    # Test 4: Session context helper method
    print("  ✓ Test 4: session_context() helper method")

    # Create adapter with minimal mocking
    with patch('neo4j_adapter.NEO4J_AVAILABLE', True):
        with patch('neo4j_adapter.AsyncGraphDatabase'):
            adapter = Neo4jAdapter(
                uri="bolt://localhost:7687",
                username="neo4j",
                password="password",
                database="testdb"
            )

            # Test helper method
            ctx = adapter.session_context(batch_transaction=False)
            assert isinstance(ctx, Neo4jSessionContext), "Should return Neo4jSessionContext"
            assert ctx._database == "testdb", "Should use adapter's database"
            assert ctx._batch_transaction is False, "Should respect batch_transaction parameter"

            ctx = adapter.session_context(batch_transaction=True)
            assert ctx._batch_transaction is True, "Should support batch_transaction=True"
            print("    ✓ Helper method works correctly")

    print("\n✅ All tests passed!")


async def main():
    """Run tests."""
    try:
        await test_session_context()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
