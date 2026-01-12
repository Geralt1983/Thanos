# Integration Tests - Oura MCP Server

## Overview

The integration tests verify end-to-end functionality of the Oura MCP server, testing the full flow from tool invocation through cache operations to API fallback.

## Running Integration Tests

```bash
cd mcp-servers/oura-mcp
npm run build
./test-integration-mcp-tools.mjs
```

## Test Coverage

### 12 Integration Test Cases

#### 1. Health Check Tool - System Status
**Purpose:** Verify the health check tool returns comprehensive system status

**Tests:**
- Overall status determination
- API connectivity check
- Cache database status
- Diagnostic recommendations
- Response structure validation

**Expected Behavior:**
- Returns valid status for all components
- Provides actionable recommendations
- Timestamps all diagnostics

---

#### 2. Cache-First Behavior - Empty Cache Falls Back to API
**Purpose:** Verify tools attempt API fetch when cache is empty

**Tests:**
- Clear cache before test
- Request current data
- Verify API fallback attempt
- Graceful handling when API unavailable

**Expected Behavior:**
- Tries cache first (miss)
- Falls back to API
- Handles API errors gracefully
- Returns helpful error messages when no data available

---

#### 3. Cache-First Behavior - Returns Cached Data When Available
**Purpose:** Verify tools prioritize cached data

**Tests:**
- Seed cache with mock readiness data
- Request same data
- Verify cache hit
- Validate response format

**Expected Behavior:**
- Returns cached data instantly
- Indicates "cache" as source
- No API call made
- Complete data structure returned

---

#### 4. Sleep Summary Tool - Cache Integration
**Purpose:** Verify sleep tool integrates correctly with cache

**Tests:**
- Seed cache with mock sleep data
- Request sleep summary
- Validate response structure
- Check all expected fields present

**Expected Behavior:**
- Returns cached sleep data
- Includes all sleep stages (REM, deep, light)
- Provides efficiency metrics
- Formats durations for readability

---

#### 5. Weekly Trends Tool - Multi-Source Cache Integration
**Purpose:** Verify trends tool aggregates data from multiple sources

**Tests:**
- Seed cache with 7 days of data (readiness, sleep, activity)
- Request weekly trends
- Verify statistical analysis
- Check pattern detection

**Expected Behavior:**
- Aggregates data from all three data types
- Calculates accurate statistics (avg, min, max)
- Detects trends (improving/declining/stable)
- Identifies cross-metric patterns
- Returns all 7 days of data

---

#### 6. Error Handling - Invalid Date Format
**Purpose:** Verify tools validate input parameters

**Tests:**
- Pass invalid date format
- Verify error response
- Check error message clarity

**Expected Behavior:**
- Rejects invalid date format
- Returns helpful error message
- Suggests correct format (YYYY-MM-DD)

---

#### 7. Error Handling - Missing Data Graceful Response
**Purpose:** Verify tools handle missing data gracefully

**Tests:**
- Request data for future date
- Verify graceful error handling
- Check error message quality

**Expected Behavior:**
- Doesn't crash or throw
- Returns structured error response
- Explains why data is unavailable

---

#### 8. Cache Statistics Verification
**Purpose:** Verify cache statistics tracking works correctly

**Tests:**
- Query cache statistics
- Verify all counts present
- Check structure of stats object

**Expected Behavior:**
- Returns entry counts for all data types
- Provides last sync timestamp
- Includes total entries count

---

#### 9. Tool Response Format Validation - Readiness
**Purpose:** Verify readiness tool returns properly structured responses

**Tests:**
- Request readiness data
- Validate response structure
- Check all required fields present
- Verify data types

**Expected Behavior:**
- All required fields present (date, score, interpretation, source)
- Contributors have score and meaning
- Metrics object included
- Proper data types used

---

#### 10. Tool Response Format Validation - Sleep
**Purpose:** Verify sleep tool returns properly structured responses

**Tests:**
- Request sleep data
- Validate response structure
- Check nested objects (stages, efficiency, timing)
- Verify data types

**Expected Behavior:**
- All required fields present
- Sleep stages properly structured
- Durations formatted for readability
- Contributors have explanations

---

#### 11. Default Parameters - Readiness Defaults to Today
**Purpose:** Verify default parameter behavior

**Tests:**
- Call tool without date parameter
- Verify defaults to today
- Check date calculation

**Expected Behavior:**
- Uses today's date when not specified
- Correctly calculates current date

---

#### 12. Default Parameters - Trends Defaults to 7 Days
**Purpose:** Verify trends tool default behavior

**Tests:**
- Call trends tool without parameters
- Verify defaults to 7 days
- Check period calculation

**Expected Behavior:**
- Uses 7 days as default period
- Calculates correct date range

---

## Test Scenarios Covered

### ✅ Cache-First Strategy
- Cache hit returns data instantly
- Cache miss triggers API fallback
- Stale cache used when API fails

### ✅ API Fallback
- Automatic API request on cache miss
- New data cached for future use
- Graceful handling of API errors

### ✅ Error Handling
- Invalid input validation
- Missing data graceful responses
- API unavailable scenarios
- Authentication errors

### ✅ Multi-Component Integration
- Tools + Cache integration
- Tools + API integration
- Cache + DB integration
- End-to-end data flow

### ✅ Response Format Validation
- Consistent structure across tools
- Proper data types
- Required fields present
- LLM-optimized formatting

### ✅ Default Behavior
- Sensible defaults for all tools
- Proper date handling
- Parameter validation

## Success Criteria

All 12 tests should pass, demonstrating:

1. **End-to-end functionality** - Tools work correctly from invocation to response
2. **Cache-first behavior** - Cache is checked before API calls
3. **API fallback** - API is used when cache is empty
4. **Error resilience** - Graceful handling of all error scenarios
5. **Data integrity** - Response formats are consistent and complete
6. **Integration quality** - All components work together seamlessly

## Running Individual Tests

The test file is structured to run all tests sequentially. Each test is independent and can be examined by reviewing the test output.

## Test Data

Integration tests use mock data to avoid dependency on API availability:

- **Mock Readiness Data**: Scores 80-92, all contributors populated
- **Mock Sleep Data**: 7.5 hours total, proper stage distribution
- **Mock Activity Data**: 8500 steps, balanced activity levels

This ensures tests are:
- Repeatable
- Fast (no API latency)
- Independent of external services
- Deterministic

## Troubleshooting

### Tests Fail Due to Missing Dependencies

```bash
npm install
npm run build
```

### Database Lock Errors

```bash
rm -rf ~/.oura-cache/oura-health.db
./test-integration-mcp-tools.mjs
```

### API Configuration Errors

Tests are designed to work without API credentials by using mock cached data. However, tests 1 and 2 will show degraded status without valid credentials - this is expected behavior.

## Next Steps

After integration tests pass:
1. Run full test suite: `./test-*.mjs`
2. Verify all acceptance criteria met
3. Test with real API credentials (optional)
4. Deploy to production environment
