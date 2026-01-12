# Energy Prioritization Service Tests

This directory contains unit tests for the energy-aware task prioritization service.

## Test Coverage

### `energy-prioritization.test.ts`

Comprehensive unit tests for the energy-prioritization service covering:

#### Core Functionality
- **Energy Mapping** (`mapReadinessToEnergyLevel`)
  - High energy: readiness >= 85
  - Medium energy: readiness 70-84
  - Low energy: readiness < 70
  - Boundary conditions (69, 70, 84, 85)

- **Task Scoring** (`calculateEnergyScore`)
  - **High Energy Scenarios:**
    - Perfect match: high cognitive load tasks (100+ points)
    - Bonuses: milestone/deliverable tasks (+20), deep work (+10), large tasks (+10)
    - Acceptable: medium cognitive load (50+ points)
    - Poor match: low cognitive load (0-49 points)

  - **Medium Energy Scenarios:**
    - Perfect match: medium cognitive load tasks (100+ points)
    - Bonuses: progress tasks (+20), shallow work (+10), medium effort (+5)
    - Acceptable: high/low cognitive load (50+ points)

  - **Low Energy Scenarios:**
    - Perfect match: low cognitive load tasks (100+ points)
    - Bonuses: checkbox tasks (+20), admin work (+10), quick wins (+15), personal tasks (+5)
    - Acceptable: medium cognitive load (50+ points)
    - Avoid: high cognitive load (0-49 points)

  - **Cross-Energy Bonuses:**
    - Active tasks (+5) to maintain momentum
    - Combined bonuses test (all applicable bonuses = ~155 points)

- **Task Ranking** (`rankTasksByEnergy`)
  - Correct sorting by energy score (descending)
  - Proper task selection for each energy level
  - Limit parameter functionality
  - Match reason inclusion

- **Daily Goal Adjustment** (`calculateDailyGoalAdjustment`)
  - High readiness (>= 85): +15% increase
  - Medium readiness (70-84): 0% adjustment
  - Low readiness (< 70): -25% reduction
  - Boundary conditions (69, 70, 84, 85)
  - Sleep score context in reasoning
  - Custom base target support

#### Edge Cases
- **Missing Oura Data:**
  - Null readiness score → default to medium energy, no adjustment
  - Null sleep score → still process readiness, omit sleep from reasoning
  - Tasks with null cognitive load → default to medium
  - Empty task array → return empty array
  - Single task → proper scoring and ranking

- **No Energy Logs:**
  - Very low readiness scores (10) → still maps correctly
  - Very high readiness scores (100) → still maps correctly
  - Different base targets → adjusted proportionally
  - Zero base target → handles gracefully

#### Realistic Scenarios
- Monday morning after poor sleep (readiness: 55)
- Friday feeling great (readiness: 92)
- ADHD user with low energy selecting tasks
- High energy day to maximize impact

## Running Tests

Since this is a TypeScript module using ES modules, run tests with `tsx`:

```bash
cd mcp-servers/workos-mcp
npx tsx tests/services/energy-prioritization.test.ts
```

Or from the main repo:

```bash
cd /Users/jeremy/Projects/Thanos/mcp-servers/workos-mcp
npx tsx tests/services/energy-prioritization.test.ts
```

## Test Output

The tests provide detailed output showing:
- ✅ Each passing assertion with description
- 📋 Test suite headers
- 🌅 Realistic scenario simulations with explanations
- 🎉 Summary of all passing test categories

## Coverage Summary

✅ **100% coverage of pure functions:**
- `mapReadinessToEnergyLevel()` - 11 test cases
- `calculateEnergyScore()` - 30+ test cases across all energy levels
- `rankTasksByEnergy()` - 10 test cases
- `calculateDailyGoalAdjustment()` - 15 test cases

✅ **Edge cases:**
- Missing data handling (null values)
- Boundary conditions
- Empty/single item arrays
- Extreme values

✅ **ADHD-specific scenarios:**
- Low energy task selection (momentum building)
- High energy optimization (deep work)
- Realistic user journeys

## Future Enhancements

To test database-dependent functions (`getEnergyContext`, `applyDailyGoalAdjustment`):
- Add integration tests with test database
- Mock Oura cache database access
- Test full workflow from data retrieval through persistence

## Notes

These tests focus on the **algorithmic correctness** of the energy-to-task matching logic and daily goal adjustment calculations. They ensure the core business logic works correctly regardless of data source (Oura, manual logs, or defaults).
