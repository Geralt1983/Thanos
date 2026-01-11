# Performance Benchmarks - Batch Embedding Generation

This directory contains performance benchmarks for the batch embedding generation optimization implemented in the ChromaAdapter.

## Overview

The batch embedding generation feature replaces sequential individual API calls to OpenAI with a single batch API call, resulting in significant latency reduction.

## Benchmark Results

### Test Configuration
- **Simulated API Latency**: ~200ms per call (realistic OpenAI API latency)
- **Test Sizes**: 10, 50, and 100 items
- **Runs per Test**: 3 (averaged)

### Results Summary

| Items | Sequential (Old) | Batch (New) | Latency Reduction | API Calls |
|-------|------------------|-------------|-------------------|-----------|
| 10    | 2043ms           | 210ms       | 89.7%             | 10 → 1    |
| 50    | 10194ms          | 231ms       | 97.7%             | 50 → 1    |
| 100   | 20470ms          | 255ms       | 98.8%             | 100 → 1   |

### Key Findings

1. **10 Items**:
   - Latency: 2043ms → 210ms (1833ms saved)
   - Reduction: 89.7%
   - API calls: 10 → 1 (90% reduction)

2. **50 Items**:
   - Latency: 10194ms → 231ms (9963ms saved)
   - Reduction: 97.7%
   - API calls: 50 → 1 (98% reduction)

3. **100 Items**:
   - Latency: 20470ms → 255ms (20215ms saved)
   - Reduction: 98.8%
   - API calls: 100 → 1 (99% reduction)

## Running the Benchmarks

To run the performance benchmarks:

```bash
python3 benchmarks/performance_benchmark.py
```

## Methodology

### Old Approach (Sequential)
```python
for item in items:
    embedding = _generate_embedding(item["content"])  # n API calls
    embeddings.append(embedding)
```

### New Approach (Batch)
```python
texts = [item["content"] for item in items]
embeddings = _generate_embeddings_batch(texts)  # 1 API call
```

## Performance Characteristics

- **Latency Reduction**: 90-99% depending on batch size
- **API Call Reduction**: 90-99% depending on batch size
- **Linear Scaling**: Larger batches show greater absolute time savings
- **Batch Size Limit**: OpenAI API supports up to 2048 items per request
- **Automatic Chunking**: Batches >2048 items are automatically chunked

## Real-World Impact

### Use Case: Storing 10 Conversation Memories
- **Before**: 2043ms (~2 seconds)
- **After**: 210ms (~0.2 seconds)
- **User Experience**: Near-instant vs noticeable delay

### Use Case: Bulk Import of 100 Historical Memories
- **Before**: 20470ms (~20.5 seconds)
- **After**: 255ms (~0.26 seconds)
- **User Experience**: Instant vs long wait

### Use Case: Daily Summary Storage (50 items)
- **Before**: 10194ms (~10.2 seconds)
- **After**: 231ms (~0.23 seconds)
- **User Experience**: Background task completes instantly

## Conclusion

Batch embedding generation provides:
- **90-99% latency reduction** across all batch sizes
- **90-99% reduction in API calls** (lower costs and rate limit usage)
- **Better user experience** with near-instant operations
- **Linear scaling** - more items = greater absolute time savings
- **No breaking changes** to existing functionality
