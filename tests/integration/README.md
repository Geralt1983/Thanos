# Integration Tests for ChromaDB Batch Embedding

> **📖 For comprehensive testing documentation**, see [TESTING_GUIDE.md](../../TESTING_GUIDE.md)
> in the project root. This README covers ChromaDB integration test specifics.

This directory contains integration tests for the ChromaDB adapter batch embedding optimization.

## Overview

Integration tests validate the complete end-to-end flow with actual dependencies:
- **ChromaDB**: Real database instances (in temporary directories)
- **OpenAI API**: Optional real API calls (requires API key)

These tests complement the unit tests by verifying:
1. Batch embedding generation works with actual ChromaDB
2. Semantic search operates correctly on batch-generated embeddings
3. No data corruption occurs in real-world scenarios
4. Performance improvements are realized with actual APIs

## Test Categories

### 1. Mock OpenAI Tests (Default)
Tests that use real ChromaDB but mock OpenAI API calls.

**Requirements:**
- ChromaDB installed (`pip install chromadb`)
- No API key needed

**Tests:**
- `TestChromaBatchEmbeddingIntegration` - Core batch functionality
- `TestChromaBatchEmbeddingErrorHandling` - Error scenarios

### 2. Real OpenAI Tests (Optional)
Tests that use both real ChromaDB and real OpenAI API.

**Requirements:**
- ChromaDB installed
- OpenAI API key set in `OPENAI_API_KEY` environment variable

**Tests:**
- `TestChromaBatchEmbeddingWithRealOpenAI` - End-to-end validation
- Performance benchmarks with actual API latency

## Running Tests

> For complete pytest command reference and advanced filtering options, see the
> [Test Execution Commands](../../TESTING_GUIDE.md#test-execution-commands) section
> in the main testing guide.

### All Integration Tests
```bash
# Run all integration tests with mocked OpenAI
pytest tests/integration/ -v

# Or using marker
pytest -m integration -v
```

### Skip Integration Tests
```bash
# Run only unit tests
pytest tests/unit/ -v
```

### Tests Requiring OpenAI API
```bash
# Set your API key
export OPENAI_API_KEY="sk-..."

# Run tests that need real OpenAI API
pytest -m requires_openai tests/integration/ -v
```

### Slow Tests
```bash
# Run only fast tests
pytest -m "not slow" tests/integration/ -v

# Run all tests including slow ones
pytest tests/integration/ -v
```

### Specific Test Classes
```bash
# Run only batch embedding tests with mocked OpenAI
pytest tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingIntegration -v

# Run only real API tests (requires OPENAI_API_KEY)
pytest tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingWithRealOpenAI -v

# Run only error handling tests
pytest tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingErrorHandling -v
```

## Test Coverage

### ✅ Core Functionality Tests
- [x] Store 10+ items in batch successfully
- [x] Verify embeddings maintain correct order
- [x] Semantic search works with batch-generated embeddings
- [x] Large batch chunking (>2048 items)
- [x] No data corruption in batch operations
- [x] Empty content filtering

### ✅ Real API Tests (require OPENAI_API_KEY)
- [x] Real batch embedding generation
- [x] Real embeddings quality and semantic accuracy
- [x] Actual performance improvement measurement

### ✅ Error Handling Tests
- [x] Batch API failure handling
- [x] Empty batch handling

## Expected Results

### With Mocked OpenAI (Default)
All tests should pass regardless of OpenAI API key:
```
tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingIntegration::test_store_batch_10_items_successfully PASSED
tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingIntegration::test_batch_embeddings_correct_order PASSED
tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingIntegration::test_semantic_search_after_batch_storage PASSED
tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingIntegration::test_large_batch_chunking PASSED
tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingIntegration::test_no_data_corruption_in_batch PASSED
tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingIntegration::test_batch_with_empty_content_items PASSED
tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingErrorHandling::test_batch_api_failure_handling PASSED
tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingErrorHandling::test_empty_batch_handling PASSED

======== 8 passed ========
```

### With Real OpenAI API
Additional tests run when `OPENAI_API_KEY` is set:
```
tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingWithRealOpenAI::test_real_batch_embedding_generation PASSED
tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingWithRealOpenAI::test_real_embeddings_quality PASSED
tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingWithRealOpenAI::test_performance_improvement_real_api PASSED

======== 11 passed ========
```

## Acceptance Criteria Validation

The integration tests validate all Phase 5 Task 1 acceptance criteria:

### ✅ Test storing 10+ items in batch successfully
**Validated by:** `test_store_batch_10_items_successfully`
- Stores 10 items in batch
- Verifies all items stored in ChromaDB
- Confirms batch API called once (not 10 times)

### ✅ Verify embeddings are generated correctly
**Validated by:**
- `test_batch_embeddings_correct_order` - Order preservation
- `test_real_batch_embedding_generation` - Real embeddings
- `test_real_embeddings_quality` - Embedding quality

### ✅ Verify semantic search still works with batch-generated embeddings
**Validated by:**
- `test_semantic_search_after_batch_storage` - Mocked search
- `test_real_batch_embedding_generation` - Real search
- `test_real_embeddings_quality` - Search accuracy

### ✅ No data corruption or quality issues
**Validated by:**
- `test_no_data_corruption_in_batch` - Data integrity
- `test_batch_embeddings_correct_order` - Order preservation
- `test_batch_with_empty_content_items` - Filtering correctness

## Troubleshooting

### "ChromaDB not available"
```bash
# Install ChromaDB
pip install chromadb

# Or install all test dependencies
pip install -r requirements-test.txt
```

### "OpenAI API key not available"
Tests marked with `@pytest.mark.requires_openai` will be **skipped** if no API key is set.

To run these tests:
```bash
export OPENAI_API_KEY="sk-your-key-here"
pytest -m requires_openai tests/integration/ -v
```

### Tests are slow
Some tests make real API calls and may be slow. Skip them:
```bash
pytest -m "integration and not slow" tests/integration/ -v
```

## Performance Expectations

With real OpenAI API:
- **10 items**: Batch operation should complete in <1.5s (vs ~2s sequential)
- **Performance improvement**: 50-90% latency reduction
- **API calls**: 10 → 1 (90% reduction)

## Test Isolation

All tests use temporary ChromaDB directories that are cleaned up after each test:
- No pollution between test runs
- Safe to run in parallel (with pytest-xdist)
- No manual cleanup required

## CI/CD Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# GitHub Actions example
- name: Run Integration Tests
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  run: |
    pytest tests/integration/ -v --tb=short
```

**Note:** Real OpenAI tests will be skipped in CI if API key is not provided.
