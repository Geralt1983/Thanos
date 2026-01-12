# Neo4j Cypher String Interpolation Security Analysis

**Task**: 012-neo4j-cypher-query-construction-uses-string-interp
**Date**: 2026-01-11
**Status**: Analysis Complete - Implementation Pending

## Executive Summary

This document analyzes all instances of string interpolation in Cypher query construction within `Tools/adapters/neo4j_adapter.py`. Five methods use string interpolation to build queries. The analysis categorizes each by risk level and documents which elements can be parameterized versus those that cannot due to Cypher limitations.

**Key Finding**: While all data values are properly parameterized, several query structure elements (WHERE clauses, relationship types, depth values) are built using string interpolation, creating potential injection vectors if user input is not properly validated.

**Critical Issues**:
- 🔴 `_find_related` has **NO validation** on `depth` or `relationship_type` parameters (HIGH RISK)
- ⚠️ `_link_nodes` has whitelist validation but could be strengthened
- ⚠️ WHERE clause methods are low-risk but should be refactored for consistency

---

## Instance 1: `_get_commitments` (Line 704)

### String Interpolation Pattern
```python
where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

query = f"""
MATCH (c:Commitment)
{where_clause}
RETURN c
ORDER BY c.created_at DESC
LIMIT $limit
"""
```

### Risk Level: **LOW-MEDIUM** ⚠️

**Analysis**:
- ✅ All data values are properly parameterized
- ✅ Condition strings are hardcoded, not derived from user input
- ⚠️ Query structure (WHERE clause) is built dynamically

**Can Be Parameterized?**
- WHERE clause structure: ❌ NO (Cypher limitation)
- Property names (e.g., `c.status`): ❌ NO (Cypher limitation)
- Filter values: ✅ YES (already parameterized)

---

## Instance 2: `_get_decisions` (Line 799)

### String Interpolation Pattern
```python
where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

query = f"""
MATCH (d:Decision)
{where_clause}
RETURN d
ORDER BY d.created_at DESC
LIMIT $limit
"""
```

### Risk Level: **LOW-MEDIUM** ⚠️

**Analysis**: Same pattern and risk profile as `_get_commitments`

---

## Instance 3: `_get_patterns` (Line 980)

### String Interpolation Pattern
```python
where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

query = f"""
MATCH (p:Pattern)
{where_clause}
RETURN p
ORDER BY p.strength DESC, p.last_observed DESC
LIMIT $limit
"""
```

### Risk Level: **LOW-MEDIUM** ⚠️

**Analysis**: Same pattern and risk profile as `_get_commitments` and `_get_decisions`

---

## Instance 4: `_link_nodes` (Line 1114) 🔴

### String Interpolation Pattern
```python
rel_type = args["relationship"].upper().replace(" ", "_")

# Validate relationship type
valid_rels = list(GRAPH_SCHEMA["relationships"].keys())
if rel_type not in valid_rels:
    return ToolResult.fail(
        f"Invalid relationship type. Valid types: {', '.join(valid_rels)}"
    )

query = f"""
MATCH (a {{id: $from_id}})
MATCH (b {{id: $to_id}})
CREATE (a)-[r:{rel_type} $props]->(b)
RETURN a, r, b
"""
```

### Risk Level: **MEDIUM-HIGH** 🔴

**Analysis**:
- ⚠️ User input directly influences query structure
- ✅ Whitelist validation provides strong protection
- ⚠️ Pattern is dangerous and could be copied incorrectly elsewhere

**Can Be Parameterized?**
- Relationship type: ❌ NO - **Documented Cypher limitation**
  - Invalid: `CREATE (a)-[r:$rel_type]->(b)`
  - Valid: `CREATE (a)-[r:LEADS_TO]->(b)` (literal only)

**Current Mitigations**:
- ✅ Whitelist validation against `GRAPH_SCHEMA["relationships"]`
- Valid types: `LEADS_TO`, `INVOLVES`, `LEARNED_FROM`, `DURING`, `IMPACTS`, `PRECEDED_BY`, `AT_ENERGY`

**Recommendations**:
1. Add regex check: `^[A-Z_]+$`
2. Add length validation (max 50 characters)
3. Use constants/enum instead of runtime dictionary
4. Add inline documentation explaining Cypher limitation
5. Add security tests for injection attempts

---

## Instance 5: `_find_related` (Line 1154, 1157) 🔴🔴🔴

### String Interpolation Pattern
```python
depth = args.get("depth", 2)
rel_filter = f":{args['relationship_type']}" if args.get("relationship_type") else ""

query = f"""
MATCH (n {{id: $node_id}})-[r{rel_filter}*1..{depth}]-(related)
RETURN DISTINCT related, type(r[0]) as relationship
LIMIT 50
"""
```

### Risk Level: **HIGH** 🔴🔴🔴

**Analysis**:
- 🔴 **NO validation** on `depth` parameter
- 🔴 **NO validation** on `relationship_type` parameter
- 🔴 Direct security vulnerability

**Can Be Parameterized?**
- Relationship type in pattern: ❌ NO (Cypher limitation)
- Variable path depth: ❌ NO (Cypher limitation)
  - Invalid: `MATCH (n)-[r*1..$depth]-(related)`
  - Valid: `MATCH (n)-[r*1..5]-(related)` (literal integers only)

**Exploitation Scenarios**:

```python
# Depth DoS Attack
# User provides: depth=999999
# Query: MATCH (n {id: $node_id})-[r*1..999999]-(related)
# Result: Catastrophic performance degradation

# Relationship Type Injection
# User provides: relationship_type="INVOLVES|LEADS_TO"
# Query: MATCH (n {id: $node_id})-[r:INVOLVES|LEADS_TO*1..2]-(related)
# Result: Valid Cypher, but unintended behavior
```

**Recommendations (URGENT)**:

1. **Depth Validation**:
```python
if not isinstance(depth, int):
    return ToolResult.fail("Depth must be an integer")
if depth < 1 or depth > 10:
    return ToolResult.fail("Depth must be between 1 and 10")
```

2. **Relationship Type Validation**:
```python
if args.get("relationship_type"):
    rel_type = args["relationship_type"].upper().replace(" ", "_")
    valid_rels = list(GRAPH_SCHEMA["relationships"].keys())
    if rel_type not in valid_rels:
        return ToolResult.fail(f"Invalid relationship type. Valid types: {', '.join(valid_rels)}")
    rel_filter = f":{rel_type}"
else:
    rel_filter = ""
```

---

## Summary Table

| Method | Line | Interpolated Element | User Controlled? | Validated? | Risk Level | Can Parameterize? |
|--------|------|---------------------|------------------|------------|------------|-------------------|
| `_get_commitments` | 704 | WHERE clause structure | Indirectly | Hardcoded | LOW-MEDIUM ⚠️ | ❌ NO |
| `_get_decisions` | 799 | WHERE clause structure | Indirectly | Hardcoded | LOW-MEDIUM ⚠️ | ❌ NO |
| `_get_patterns` | 980 | WHERE clause structure | Indirectly | Hardcoded | LOW-MEDIUM ⚠️ | ❌ NO |
| `_link_nodes` | 1114 | Relationship type | ✅ YES | ✅ YES | MEDIUM-HIGH 🔴 | ❌ NO |
| `_find_related` | 1154 | Relationship type | ✅ YES | ❌ NO | HIGH 🔴🔴 | ❌ NO |
| `_find_related` | 1157 | Depth value | ✅ YES | ❌ NO | HIGH 🔴🔴 | ❌ NO |

---

## Cypher Parameterization Limitations

### What CAN be Parameterized ✅

```cypher
-- Property values (data)
MATCH (n {name: $name})  ✅
WHERE n.age > $age       ✅
CREATE (n {props: $props}) ✅

-- Relationship properties
CREATE (a)-[r:KNOWS $props]->(b)  ✅

-- List parameters
WHERE n.id IN $id_list  ✅
```

### What CANNOT be Parameterized ❌

```cypher
-- Node labels
MATCH (n:$label)  ❌ INVALID
MATCH (n:Person)  ✅ Valid

-- Relationship types
CREATE (a)-[r:$rel_type]->(b)  ❌ INVALID
CREATE (a)-[r:KNOWS]->(b)      ✅ Valid

-- Property names
WHERE n.$prop_name = 'value'  ❌ INVALID
WHERE n.name = 'value'        ✅ Valid

-- Variable path lengths
MATCH (a)-[*1..$depth]-(b)  ❌ INVALID
MATCH (a)-[*1..5]-(b)       ✅ Valid

-- Operators
WHERE n.age $operator $value  ❌ INVALID
WHERE n.age > $value          ✅ Valid
```

**Reference**:
- [Neo4j Cypher Parameters Documentation](https://neo4j.com/docs/cypher-manual/current/syntax/parameters/)
- [Neo4j Driver Query Parameters](https://neo4j.com/docs/driver-manual/current/cypher-workflow/#query-parameters)

---

## Security Best Practices

Since Cypher limitations prevent parameterization of relationship types, node labels, property names, and path depths, we must use alternative security measures:

### 1. Whitelist Validation (REQUIRED)
```python
VALID_RELATIONSHIP_TYPES = {
    "LEADS_TO", "INVOLVES", "LEARNED_FROM",
    "DURING", "IMPACTS", "PRECEDED_BY", "AT_ENERGY"
}

def validate_relationship_type(rel_type: str) -> str:
    """
    Validate relationship type against whitelist.

    NOTE: Relationship types cannot be parameterized in Cypher.
    This is a documented Neo4j limitation.
    """
    normalized = rel_type.upper().replace(" ", "_")

    # Format validation (defense in depth)
    if not re.match(r'^[A-Z_]+$', normalized):
        raise ValueError(f"Invalid relationship type format: {rel_type}")

    # Whitelist check
    if normalized not in VALID_RELATIONSHIP_TYPES:
        raise ValueError(f"Invalid relationship type: {rel_type}")

    return normalized
```

### 2. Type Validation (REQUIRED)
```python
def validate_depth(depth: Any) -> int:
    """
    Validate path depth for graph traversal.

    NOTE: Variable path lengths cannot be parameterized in Cypher.
    """
    if not isinstance(depth, int):
        try:
            depth = int(depth)
        except (ValueError, TypeError):
            raise ValueError(f"Depth must be an integer")

    # Range check (prevent DoS)
    if depth < 1 or depth > 10:
        raise ValueError(f"Depth must be between 1 and 10")

    return depth
```

### 3. Range Validation (REQUIRED)
- Enforce reasonable bounds to prevent DoS
- Example: depth limited to 1-10, not 1-999999

### 4. Input Sanitization (DEFENSE IN DEPTH)
- Reject special characters, Unicode, control characters
- Normalize case (e.g., uppercase for relationship types)

### 5. Documentation (REQUIRED)
- Add inline comments explaining why interpolation is necessary
- Document Cypher limitations
- Add security warnings for future maintainers

### 6. Testing (REQUIRED)
- Test injection attempts via all user-controlled parameters
- Test edge cases and boundary conditions

---

## Implementation Roadmap

### Phase 1: URGENT - Fix `_find_related` ⏱️
Priority: **CRITICAL**

1. Add depth validation (integer, 1-10 range)
2. Add relationship type whitelist validation
3. Add inline documentation
4. Add security tests

### Phase 2: HIGH - Enhance `_link_nodes`
Priority: **HIGH**

1. Add regex validation for relationship type format
2. Use constants/enum instead of runtime dictionary
3. Add inline documentation
4. Add security tests

### Phase 3: MEDIUM - Refactor WHERE Clause Methods
Priority: **MEDIUM**

1. Extract common WHERE clause building logic
2. Add comments explaining pattern
3. Ensure consistency across all three methods

### Phase 4: LOW - Centralized Validation
Priority: **LOW**

1. Create shared validation functions
2. Reduce code duplication
3. Make security measures consistent

---

## Testing Requirements

### Security Tests (Required)

```python
def test_find_related_depth_validation():
    """Test that depth parameter is validated."""
    # Test negative depth
    # Test zero depth
    # Test excessive depth (>10)
    # Test non-integer depth

def test_find_related_relationship_type_validation():
    """Test that relationship type is validated."""
    # Test invalid relationship type
    # Test injection attempt
    # Test special characters

def test_link_nodes_relationship_type_validation():
    """Test that relationship type validation is robust."""
    # Test all valid types
    # Test invalid types
    # Test injection attempts
```

### Edge Case Tests (Required)

- Empty strings
- Null values
- Special characters in parameterized values
- Boundary conditions (max/min values)
- Unicode characters
- Very long strings

---

## Conclusion

**Current State**:
- ✅ All data values are properly parameterized
- ⚠️ WHERE clause building is low-risk (hardcoded conditions)
- 🔴 `_link_nodes` has adequate whitelist validation but could be enhanced
- 🔴🔴 `_find_related` has **NO validation** and represents the **highest risk**

**Required Actions**:
1. ⏱️ **URGENT**: Add validation to `_find_related` (depth and relationship_type)
2. Enhance `_link_nodes` validation
3. Refactor WHERE clause building for consistency
4. Add comprehensive security tests
5. Document Cypher limitations inline

**Long-term Strategy**:
- Create centralized validation utilities
- Use constants/enums for whitelisted values
- Maintain comprehensive security test suite
- Document security considerations for future maintainers

---

*This analysis completes Subtask 1.1 of Task 012. Next step: Research and validate against Neo4j official documentation (Subtask 1.2).*
