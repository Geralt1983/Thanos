# Integration Testing Guide for ChromaDB Batch Embedding

## Overview

This guide explains how to run integration tests for the ChromaDB batch embedding optimization. Integration tests validate the complete end-to-end functionality with actual ChromaDB instances.

## What Do Integration Tests Validate?

The integration tests cover all acceptance criteria for Phase 5 - Task 1:

### ✅ Test storing 10+ items in batch successfully
- Validates batch storage of 10 items
- Confirms all items stored in ChromaDB
- Verifies batch API called once (not sequentially)
- Tests with actual ChromaDB database

### ✅ Verify embeddings are generated correctly
- Tests embedding order preservation (critical!)
- Validates embeddings with shuffled API responses
- Confirms real embeddings work correctly (optional with API key)
- Tests embedding quality and semantic meaning

### ✅ Verify semantic search still works with batch-generated embeddings
- Tests search on batch-stored items
- Validates search returns relevant results
- Confirms embeddings are properly indexed
- Tests real semantic accuracy (optional with API key)

### ✅ No data corruption or quality issues
- Validates metadata matches content
- Confirms no cross-contamination between items
- Tests unique ID generation
- Verifies all metadata fields preserved
- Tests filtering of empty content items

## Quick Start

### 1. Install Dependencies

```bash
# Install ChromaDB (required for all integration tests)
pip install chromadb

# Install pytest if not already installed
pip install pytest pytest-asyncio
```

### 2. Run Basic Integration Tests (No API Key Required)

```bash
# Using the test runner script (recommended)
python3 ./run_integration_tests.py

# Or directly with pytest
pytest tests/integration/ -v
```

These tests use real ChromaDB but mock OpenAI API calls, so no API key is needed.

### 3. Run Tests with Real OpenAI API (Optional)

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="sk-..."

# Run real API tests
python3 ./run_integration_tests.py --real-api

# Or with pytest
pytest -m requires_openai tests/integration/ -v
```

## Test Execution Options

### Option 1: Using Test Runner Script (Recommended)

```bash
# Run all fast integration tests (mocked OpenAI)
python3 ./run_integration_tests.py

# Run tests with real OpenAI API
python3 ./run_integration_tests.py --real-api

# Run all tests including slow ones
python3 ./run_integration_tests.py --all
```

The test runner provides:
- Dependency checking
- Clear output
- API key validation
- Helpful error messages

### Option 2: Using pytest Directly

```bash
# All integration tests with mocked OpenAI
pytest tests/integration/ -v

# Only tests requiring real OpenAI API
pytest -m requires_openai tests/integration/ -v

# Exclude slow tests
pytest -m "integration and not slow" tests/integration/ -v

# Run specific test class
pytest tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingIntegration -v

# Run specific test
pytest tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingIntegration::test_store_batch_10_items_successfully -v
```

## Test Categories

### Category 1: Core Batch Operations (8 tests)
**Requirements:** ChromaDB only
**API Key:** Not required (mocked)
**Runtime:** Fast (~10-20 seconds)

Tests:
- ✅ Store 10+ items in batch successfully
- ✅ Batch embeddings maintain correct order
- ✅ Semantic search works after batch storage
- ✅ Large batch chunking (2148 items → 2048 + 100)
- ✅ No data corruption in batch operations
- ✅ Empty content items filtered correctly
- ✅ Batch API failure handling
- ✅ Empty batch handling

### Category 2: Real API Validation (3 tests)
**Requirements:** ChromaDB + OpenAI API key
**API Key:** Required
**Runtime:** Moderate (~30-60 seconds)
**Cost:** ~$0.01-0.02 per run

Tests:
- ✅ Real batch embedding generation
- ✅ Real embeddings quality and accuracy
- ✅ Actual performance improvement measurement

## Expected Results

### With Mocked OpenAI (Default)

```
tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingIntegration::test_store_batch_10_items_successfully PASSED
tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingIntegration::test_batch_embeddings_correct_order PASSED
tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingIntegration::test_semantic_search_after_batch_storage PASSED
tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingIntegration::test_large_batch_chunking PASSED
tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingIntegration::test_no_data_corruption_in_batch PASSED
tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingIntegration::test_batch_with_empty_content_items PASSED
tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingErrorHandling::test_batch_api_failure_handling PASSED
tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingErrorHandling::test_empty_batch_handling PASSED

=============================== 8 passed in 5.23s ===============================
```

### With Real OpenAI API

```
tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingWithRealOpenAI::test_real_batch_embedding_generation PASSED
tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingWithRealOpenAI::test_real_embeddings_quality PASSED
tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingWithRealOpenAI::test_performance_improvement_real_api PASSED

=== Performance Test Results ===
Items stored: 10
Batch operation time: 0.347s
Theoretical sequential time: ~2.0s (10 × 200ms)
Performance improvement: 82.7%
================================

=============================== 11 passed in 42.15s ===============================
```

## Verifying Acceptance Criteria

Each acceptance criterion has corresponding tests:

### ✅ Test storing 10+ items in batch successfully

**Test:** `test_store_batch_10_items_successfully`

**Validates:**
- 10 items stored via batch operation
- All items present in ChromaDB
- Batch API called once (not 10 times)
- Metadata preserved correctly

**How to run:**
```bash
pytest tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingIntegration::test_store_batch_10_items_successfully -v
```

### ✅ Verify embeddings are generated correctly

**Tests:**
- `test_batch_embeddings_correct_order` - Order preservation
- `test_real_batch_embedding_generation` - Real embeddings (requires API key)

**Validates:**
- Embeddings returned in correct order
- Order preserved even with shuffled API response
- Real embeddings work correctly
- ChromaDB stores embeddings properly

**How to run:**
```bash
# Test order preservation (mocked)
pytest tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingIntegration::test_batch_embeddings_correct_order -v

# Test real embeddings (requires OPENAI_API_KEY)
pytest tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingWithRealOpenAI::test_real_batch_embedding_generation -v
```

### ✅ Verify semantic search still works with batch-generated embeddings

**Tests:**
- `test_semantic_search_after_batch_storage` - Mocked search
- `test_real_embeddings_quality` - Real search accuracy (requires API key)

**Validates:**
- Search returns relevant results
- Embeddings correctly indexed for similarity search
- Real semantic meaning captured (with real API)

**How to run:**
```bash
# Test search with mocked embeddings
pytest tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingIntegration::test_semantic_search_after_batch_storage -v

# Test search quality with real embeddings (requires OPENAI_API_KEY)
pytest tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingWithRealOpenAI::test_real_embeddings_quality -v
```

### ✅ No data corruption or quality issues

**Tests:**
- `test_no_data_corruption_in_batch` - Data integrity
- `test_batch_embeddings_correct_order` - Order preservation
- `test_batch_with_empty_content_items` - Filtering correctness

**Validates:**
- Metadata matches content
- No cross-contamination
- Unique IDs generated
- All fields preserved
- Empty content filtered correctly

**How to run:**
```bash
pytest tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingIntegration::test_no_data_corruption_in_batch -v
```

## Troubleshooting

### Issue: "ChromaDB not available"

**Solution:**
```bash
pip install chromadb
```

### Issue: "OpenAI API key not available"

Tests requiring real OpenAI API are marked with `@pytest.mark.requires_openai` and will be **automatically skipped** if no API key is set.

**To run these tests:**
```bash
export OPENAI_API_KEY="sk-your-key-here"
pytest -m requires_openai tests/integration/ -v
```

### Issue: Tests are slow

Some tests make real API calls. To skip slow tests:
```bash
pytest -m "integration and not slow" tests/integration/ -v
```

### Issue: Import errors

**Solution:**
```bash
# Install all test dependencies
pip install pytest pytest-asyncio chromadb

# Make sure you're in the project root
cd /path/to/project
pytest tests/integration/ -v
```

## Performance Validation

The real API tests measure actual performance improvement:

**Expected Results:**
- 10 items: <1.5s batch time (vs ~2s sequential)
- Performance: 50-90% latency reduction
- API calls: 10 → 1 (90% reduction)

**Example Output:**
```
=== Performance Test Results ===
Items stored: 10
Batch operation time: 0.347s
Theoretical sequential time: ~2.0s (10 × 200ms)
Performance improvement: 82.7%
================================
```

## CI/CD Integration

Integration tests can be added to CI/CD pipelines:

```yaml
# GitHub Actions example
name: Integration Tests

on: [push, pull_request]

jobs:
  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install chromadb pytest pytest-asyncio
      - name: Run integration tests (mocked)
        run: |
          pytest tests/integration/ -v -m "not requires_openai"
      - name: Run integration tests (real API)
        if: ${{ secrets.OPENAI_API_KEY }}
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          pytest tests/integration/ -v -m requires_openai
```

## Manual Verification Checklist

After running integration tests, verify:

- [ ] All 8 core tests pass (mocked OpenAI)
- [ ] ChromaDB storage verified (items present in database)
- [ ] Batch API called once per batch (not sequentially)
- [ ] Semantic search returns relevant results
- [ ] No data corruption (metadata matches content)
- [ ] Large batch chunking works (2148 items → 2 chunks)
- [ ] Error handling works (API failures, empty batches)

**Optional with OpenAI API key:**
- [ ] Real embeddings generated successfully
- [ ] Semantic search accuracy validated
- [ ] Performance improvement measured (>50% reduction)

## Summary

The integration tests provide comprehensive validation of the batch embedding optimization:

1. **Core Functionality** - 8 tests validate basic operations with mocked OpenAI
2. **Real API Testing** - 3 tests validate with actual OpenAI embeddings (optional)
3. **Error Handling** - Validates graceful failure scenarios
4. **Performance** - Measures actual latency improvements

**All tests use real ChromaDB instances** to ensure the optimization works in production scenarios.

**Tests are safe to run repeatedly** - each test uses a temporary database that is automatically cleaned up.
