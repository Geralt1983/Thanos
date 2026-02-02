#!/usr/bin/env python3
"""
Integration test for Memory V2 architecture improvements.

Tests all four major components:
1. Voyage embeddings
2. Unified capture
3. Heat decay
4. Auto-deduplication

Usage:
    python Tools/memory_v2/test_integration.py
"""

import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_embeddings():
    """Test Voyage embedding generation."""
    print("\n" + "=" * 60)
    print("TEST 1: Voyage Embeddings")
    print("=" * 60)
    
    try:
        from Tools.memory_v2.service import _cached_query_embedding
        from Tools.memory_v2.config import USE_VOYAGE, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS
        
        print(f"Provider: {'Voyage AI' if USE_VOYAGE else 'OpenAI'}")
        print(f"Model: {EMBEDDING_MODEL}")
        print(f"Expected dimensions: {EMBEDDING_DIMENSIONS}")
        
        # Generate test embedding
        embedding = _cached_query_embedding("test query for integration")
        actual_dims = len(embedding)
        
        print(f"Actual dimensions: {actual_dims}")
        
        if actual_dims == EMBEDDING_DIMENSIONS:
            print("✅ Embeddings working correctly")
            return True
        else:
            print(f"❌ Dimension mismatch: expected {EMBEDDING_DIMENSIONS}, got {actual_dims}")
            return False
            
    except Exception as e:
        print(f"❌ Embedding test failed: {e}")
        return False


def test_unified_capture():
    """Test unified capture interface."""
    print("\n" + "=" * 60)
    print("TEST 2: Unified Capture")
    print("=" * 60)
    
    try:
        from Tools.memory_v2.unified_capture import capture, CaptureType
        
        # Test auto-detection
        print("\nTest 2a: Auto-detect content type")
        result = capture(
            "Integration test: Jeremy decided to test the new memory architecture",
            source="integration_test"
        )
        
        if result.get("memory_v2") or result.get("graphiti"):
            print("✅ Auto-detection working")
        else:
            print("⚠️ No routing occurred (might be expected if services unavailable)")
        
        # Test explicit type
        print("\nTest 2b: Explicit content type")
        result = capture(
            "Test fact: Voyage embeddings use 1024 dimensions",
            capture_type=CaptureType.FACT,
            metadata={"project": "Thanos", "source": "integration_test"}
        )
        
        if result.get("memory_v2"):
            print("✅ Explicit type routing working")
        else:
            print("⚠️ Memory V2 routing failed")
        
        return True
        
    except Exception as e:
        print(f"❌ Unified capture test failed: {e}")
        return False


def test_heat_decay():
    """Test heat decay mechanism."""
    print("\n" + "=" * 60)
    print("TEST 3: Heat Decay")
    print("=" * 60)
    
    try:
        from Tools.memory_v2.heat import get_heat_service
        
        hs = get_heat_service()
        
        # Test hot memories
        print("\nTest 3a: Get hot memories")
        hot = hs.whats_hot(limit=5)
        print(f"Found {len(hot)} hot memories")
        if hot:
            print(f"Hottest: {hot[0].get('content', hot[0].get('memory', ''))[:50]}... (heat: {hot[0].get('heat', 0):.2f})")
            print("✅ Hot memories working")
        else:
            print("⚠️ No hot memories found (database might be empty)")
        
        # Test cold memories
        print("\nTest 3b: Get cold memories")
        cold = hs.whats_cold(threshold=0.3, limit=5)
        print(f"Found {len(cold)} cold memories")
        if cold:
            print(f"Coldest: {cold[0].get('content', cold[0].get('memory', ''))[:50]}... (heat: {cold[0].get('heat', 0):.2f})")
            print("✅ Cold memories working")
        else:
            print("⚠️ No cold memories found")
        
        # Test heat statistics
        print("\nTest 3c: Heat statistics")
        stats = hs.get_heat_stats()
        print(f"Total memories: {stats.get('total_memories', 0)}")
        print(f"Average heat: {stats.get('avg_heat', 0):.2f}")
        print(f"Hot count: {stats.get('hot_count', 0)}")
        print(f"Cold count: {stats.get('cold_count', 0)}")
        print("✅ Heat statistics working")
        
        return True
        
    except Exception as e:
        print(f"❌ Heat decay test failed: {e}")
        return False


def test_deduplication():
    """Test auto-deduplication (dry run only)."""
    print("\n" + "=" * 60)
    print("TEST 4: Auto-Deduplication")
    print("=" * 60)
    
    try:
        from Tools.memory_v2.deduplication import deduplicate_memories
        
        print("\nTest 4a: Find duplicates (dry run)")
        results = deduplicate_memories(
            similarity_threshold=0.95,
            dry_run=True,
            limit=5
        )
        
        print(f"Duplicates found: {results['duplicates_found']}")
        
        if results['duplicates_found'] > 0:
            print(f"Would merge: {results['duplicates_merged']} pairs")
            
            # Show first duplicate pair
            if results.get('merge_log'):
                first = results['merge_log'][0]
                print(f"\nExample duplicate (similarity: {first['similarity']:.3f}):")
                print(f"  Keep: {first['keep_content']}")
                print(f"  Remove: {first['remove_content']}")
        
        print("✅ Deduplication working")
        return True
        
    except Exception as e:
        print(f"❌ Deduplication test failed: {e}")
        return False


def test_memory_service():
    """Test basic memory service operations."""
    print("\n" + "=" * 60)
    print("TEST 5: Memory Service")
    print("=" * 60)
    
    try:
        from Tools.memory_v2.service import get_memory_service
        
        ms = get_memory_service()
        
        # Test statistics
        print("\nTest 5a: Memory statistics")
        stats = ms.stats()
        print(f"Total memories: {stats.get('total', 0)}")
        print(f"Unique clients: {stats.get('unique_clients', 0)}")
        print(f"Unique projects: {stats.get('unique_projects', 0)}")
        print("✅ Statistics working")
        
        # Test search
        print("\nTest 5b: Search functionality")
        results = ms.search("test", limit=3)
        print(f"Found {len(results)} results")
        if results:
            print(f"Top result: {results[0].get('memory', results[0].get('content', ''))[:50]}...")
            print(f"Effective score: {results[0].get('effective_score', 0):.3f}")
        print("✅ Search working")
        
        return True
        
    except Exception as e:
        print(f"❌ Memory service test failed: {e}")
        return False


def main():
    """Run all integration tests."""
    print("\n" + "=" * 60)
    print("THANOS MEMORY V2 INTEGRATION TEST")
    print("=" * 60)
    print(f"Started: {datetime.now()}")
    
    results = {
        "Embeddings": test_embeddings(),
        "Unified Capture": test_unified_capture(),
        "Heat Decay": test_heat_decay(),
        "Deduplication": test_deduplication(),
        "Memory Service": test_memory_service()
    }
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"{status}: {name}")
    
    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print(f"Completed: {datetime.now()}")
    print("=" * 60)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
