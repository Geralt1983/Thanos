# Aho-Corasick Library Research & Recommendation

**Date:** 2026-01-11
**Task:** Subtask 4.1 - Research and select Aho-Corasick library
**Status:** Optional enhancement - not required for current system

---

## Executive Summary

After comprehensive research, **pyahocorasick** is recommended as the primary choice if Aho-Corasick optimization is implemented, with **ahocorasick_rs** as a higher-performance alternative worth considering.

**Current System Context:**
- Current implementation: Regex-based KeywordMatcher
- Performance: ~12.45 μs average (0.012 ms)
- Keyword count: 92 keywords across 4 agents
- Complexity: O(m) where m = message length

**Recommendation:** The current regex-based implementation is **sufficient** for our use case. Aho-Corasick is only beneficial when dealing with >500-1000 keywords.

---

## 1. Available Python Libraries

### 1.1 pyahocorasick ⭐ RECOMMENDED (if needed)

**Repository:** https://github.com/WojciechMula/pyahocorasick
**PyPI:** https://pypi.org/project/pyahocorasick/
**Documentation:** https://pyahocorasick.readthedocs.io/

**Key Features:**
- ✅ C-based implementation (high performance)
- ✅ Mature and well-documented
- ✅ Works on Python 3.10+
- ✅ Cross-platform (Linux, macOS, Windows)
- ✅ Memory efficient (2-4 bytes per letter)
- ✅ Picklable automaton (can save/load from disk)
- ✅ Both exact and approximate matching support

**Performance:**
- Typical worst-case = best-case runtime
- Performance primarily depends on input string size
- Significantly faster than pure Python implementations
- Optimal for 500+ keywords

**Pros:**
- Industry standard for Python Aho-Corasick
- Excellent documentation and examples
- Active maintenance
- Proven track record
- Supports both trie and automaton data structures

**Cons:**
- Requires C compilation (may complicate deployment)
- Python 3.10+ requirement (not an issue for our project)

---

### 1.2 ahocorasick_rs 🚀 HIGH PERFORMANCE ALTERNATIVE

**Repository:** https://github.com/G-Research/ahocorasick_rs
**PyPI:** https://pypi.org/project/ahocorasick-rs/

**Key Features:**
- ✅ Rust-based implementation
- ✅ **1.5× to 7× faster than pyahocorasick**
- ✅ Python bindings via PyO3
- ✅ Modern and actively maintained
- ✅ Pre-built wheels for major platforms

**Performance:**
- Benchmark: 1.5-7x faster than pyahocorasick depending on options
- Leverages Rust's safety and speed
- Excellent for high-throughput scenarios

**Pros:**
- Significantly faster than pyahocorasick
- Modern implementation with Rust safety guarantees
- Good for high-performance requirements
- Pre-built wheels simplify installation

**Cons:**
- Newer library (less battle-tested than pyahocorasick)
- Smaller community
- Less documentation than pyahocorasick
- May have different API compared to pyahocorasick

---

### 1.3 ahocorapy (Pure Python)

**Repository:** https://github.com/abusix/ahocorapy
**PyPI:** https://pypi.org/project/ahocorapy/

**Key Features:**
- ✅ Pure Python (no compilation needed)
- ✅ Suffix shortcutting optimization
- ⚠️ Better than py-aho-corasick, but slower than C/Rust implementations
- ⚠️ Higher setup overhead due to suffix optimization

**Performance:**
- With PyPy: Nearly as fast as pyahocorasick for searching
- With CPython: Significantly slower than pyahocorasick
- Higher setup overhead

**Pros:**
- No C/Rust compilation required
- Works with PyPy for near-native performance
- Easy to install and deploy

**Cons:**
- Much slower than C/Rust implementations with CPython
- Requires PyPy for competitive performance
- Higher setup overhead

---

### 1.4 py-aho-corasick ❌ NOT RECOMMENDED

**Repository:** https://github.com/Guangyi-Z/py-aho-corasick

**Key Features:**
- Pure Python implementation
- ❌ Poor performance
- ❌ Not actively maintained

**Verdict:** Not suitable for production use.

---

## 2. Performance Benchmarks

### 2.1 Comparative Performance

Based on research from multiple sources:

| Library | Implementation | Relative Speed | Setup Overhead | Notes |
|---------|---------------|----------------|----------------|-------|
| **ahocorasick_rs** | Rust | 1.5-7x faster | Low | Fastest option |
| **pyahocorasick** | C | Baseline (1x) | Low | Industry standard |
| **ahocorapy (PyPy)** | Python | ~0.9x | High | Requires PyPy |
| **ahocorapy (CPython)** | Python | ~0.3x | High | Slower |
| **py-aho-corasick** | Python | ~0.1x | Medium | Very slow |

**Benchmark Context:**
- Test: 50,000 keywords, 34,199 character input text
- C/Rust implementations "shatter" pure Python performance

### 2.2 Regex vs Aho-Corasick Crossover Point

**Key Findings:**
- **< 500 keywords:** Regex is competitive or faster
- **500-1000 keywords:** Aho-Corasick starts to show benefits
- **> 1000 keywords:** Aho-Corasick significantly outperforms regex

**Our Current System:**
- 92 keywords total
- Regex-based implementation: ~12.45 μs average
- **Conclusion:** Aho-Corasick not needed for current scale

---

## 3. Decision Matrix

### 3.1 Recommendation for This Project

**Context:**
- Current keywords: 92
- Current performance: ~12.45 μs (excellent)
- Expected growth: Unlikely to exceed 500 keywords

**Primary Recommendation:** **Continue using regex-based KeywordMatcher**

**If Aho-Corasick is implemented (optional):**

| Scenario | Recommended Library | Justification |
|----------|-------------------|---------------|
| **Default choice** | **pyahocorasick** | Mature, well-documented, proven |
| **Maximum performance** | **ahocorasick_rs** | 1.5-7x faster if benchmarks show benefit |
| **No compilation** | **ahocorapy** | Pure Python, but requires PyPy for speed |

### 3.2 Selection Criteria

**Choose pyahocorasick if:**
- ✅ You want the industry-standard solution
- ✅ Documentation and community support are priorities
- ✅ C compilation is acceptable
- ✅ Stability and proven track record matter

**Choose ahocorasick_rs if:**
- ✅ Maximum performance is critical
- ✅ 1.5-7x speedup over pyahocorasick is needed
- ✅ Rust toolchain is acceptable
- ✅ Willing to adopt newer technology

**Choose ahocorapy if:**
- ✅ No compilation dependencies allowed
- ✅ Using PyPy runtime
- ✅ Performance is less critical

---

## 4. Implementation Considerations

### 4.1 Installation

**pyahocorasick:**
```bash
pip install pyahocorasick
```
*Requires C compiler (GCC, MSVC, etc.)*

**ahocorasick_rs:**
```bash
pip install ahocorasick-rs
```
*Pre-built wheels available for major platforms*

**ahocorapy:**
```bash
pip install ahocorapy
```
*Pure Python - no compilation needed*

### 4.2 Basic Usage Comparison

**pyahocorasick:**
```python
import ahocorasick

# Build automaton
A = ahocorasick.Automaton()
for idx, keyword in enumerate(keywords):
    A.add_word(keyword, (idx, keyword))
A.make_automaton()

# Search
for end_index, (idx, keyword) in A.iter(text):
    print(f"Found '{keyword}' at position {end_index}")
```

**ahocorasick_rs:**
```python
from ahocorasick_rs import AhoCorasick

# Build automaton
ac = AhoCorasick(keywords)

# Search
for match in ac.find_matches_as_indexes(text):
    print(f"Match at {match}")
```

**ahocorapy:**
```python
from ahocorapy.keywordtree import KeywordTree

# Build tree
kwtree = KeywordTree()
for keyword in keywords:
    kwtree.add(keyword)
kwtree.finalize()

# Search
for keyword in kwtree.search_all(text):
    print(f"Found '{keyword}'")
```

### 4.3 Integration Strategy

**Recommended approach for Phase 4.2 (if implemented):**

```python
class TrieKeywordMatcher:
    """Aho-Corasick-based keyword matcher (alternative to regex)"""

    def __init__(self, agent_keywords: Dict[str, Dict[str, List[str]]]):
        try:
            import ahocorasick
            self._use_aho = True
            self._automaton = self._build_automaton(agent_keywords)
        except ImportError:
            # Fallback to regex-based matcher
            self._use_aho = False
            self._regex_matcher = KeywordMatcher(agent_keywords)

    def match(self, message: str) -> Dict[str, int]:
        if self._use_aho:
            return self._match_aho(message)
        else:
            return self._regex_matcher.match(message)
```

---

## 5. Cost-Benefit Analysis

### 5.1 Current System Performance

**Regex-based KeywordMatcher:**
- Performance: 12.45 μs average (0.012 ms)
- Complexity: O(m) where m = message length
- Keywords: 92 total
- Implementation: Simple, maintainable, no dependencies

### 5.2 Expected Aho-Corasick Benefits

**At current scale (92 keywords):**
- Expected speedup: 1.2-2x (minimal benefit)
- Additional complexity: Higher
- Dependencies: External C/Rust library
- Maintenance: More complex

**At larger scale (500+ keywords):**
- Expected speedup: 3-5x
- Complexity overhead: Justified
- Dependencies: Worth the tradeoff

### 5.3 Recommendation

**For current system:** ❌ **Do NOT implement Aho-Corasick**

**Reasons:**
1. Current performance is excellent (~12 μs)
2. 92 keywords is below the threshold where Aho-Corasick shines
3. Adds external dependency (C/Rust compilation)
4. Increases maintenance complexity
5. Minimal performance benefit vs. cost

**When to reconsider:**
- Keyword count grows beyond 500
- Message throughput increases significantly (>10,000 messages/sec)
- Performance benchmarks show regex degradation

---

## 6. Final Recommendation

### 6.1 For This Task (Subtask 4.1)

**Selected Library:** **pyahocorasick**

**Rationale:**
- If we implement Phase 4, pyahocorasick is the safe, proven choice
- Excellent documentation for future developers
- Industry standard with wide adoption
- Good balance of performance and stability

**Alternative:** **ahocorasick_rs** for maximum performance if benchmarks show the need

### 6.2 Implementation Decision

**Recommendation:** **SKIP Phase 4 entirely**

The current regex-based KeywordMatcher is:
- ✅ Fast enough (~12 μs average)
- ✅ Simple to maintain
- ✅ No external dependencies
- ✅ O(m) complexity achieved
- ✅ 100% backward compatible

Aho-Corasick should be reconsidered **only if**:
- Keyword count exceeds 500
- Performance benchmarks show regex degradation
- High-throughput scenarios emerge (>10k messages/sec)

---

## 7. References

### 7.1 Documentation

- [pyahocorasick PyPI](https://pypi.org/project/pyahocorasick/)
- [pyahocorasick Documentation](https://pyahocorasick.readthedocs.io/)
- [ahocorasick_rs GitHub](https://github.com/G-Research/ahocorasick_rs)
- [ahocorapy GitHub](https://github.com/abusix/ahocorapy)

### 7.2 Performance Articles

- [High-Performance Text String Processing in Python](https://medium.com/@tubelwj/high-performance-text-string-processing-in-python-regex-optimization-vs-aho-corasick-algorithm-03c844b6545e)
- [Optimizing Pattern Matching in Python Using Aho-Corasick](https://medium.com/@naveenkumarkattankk/optimizing-pattern-matching-in-python-using-the-aho-corasick-algorithm-f90a8feabdde)

### 7.3 Benchmarks

- ahocorasick_rs: 1.5-7x faster than pyahocorasick
- Crossover point: 500-1000 keywords where Aho-Corasick beats regex
- Our system: 92 keywords (well below threshold)

---

## 8. Implementation Plan (If Proceeding)

### Phase 4.2: Implement TrieKeywordMatcher

**Files to modify:**
- `Tools/intent_matcher.py` - Add TrieKeywordMatcher class
- `requirements.txt` - Add `pyahocorasick>=2.0.0`

**Implementation approach:**
```python
# Conditional import with fallback
try:
    import ahocorasick
    AHOCORASICK_AVAILABLE = True
except ImportError:
    AHOCORASICK_AVAILABLE = False

class TrieKeywordMatcher:
    # Implementation with fallback to KeywordMatcher
    pass
```

### Phase 4.3: Configuration Option

**Files to modify:**
- `Tools/thanos_orchestrator.py`

**Configuration:**
```python
def _get_intent_matcher(self, strategy='regex'):
    """
    strategy: 'regex' or 'trie'
    """
    if strategy == 'trie' and AHOCORASICK_AVAILABLE:
        return TrieKeywordMatcher(agent_keywords)
    else:
        return KeywordMatcher(agent_keywords)
```

### Phase 4.4: Benchmark Comparison

**Expected results:**
- Current (regex): ~12 μs
- Aho-Corasick: ~10-15 μs (minimal difference at 92 keywords)
- Conclusion: Not worth the added complexity

---

**Document Status:** Complete
**Decision:** Use **pyahocorasick** if implementing Phase 4, but **recommend skipping Phase 4** entirely
**Next Steps:** Update implementation plan to mark Phase 4 as optional/skipped
