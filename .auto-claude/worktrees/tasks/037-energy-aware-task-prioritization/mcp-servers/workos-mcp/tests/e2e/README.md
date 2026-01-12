# End-to-End Workflow Tests for Energy-Aware Task Prioritization

## Overview

These tests validate the **complete user workflow** from morning to evening, ensuring all components of the energy-aware task prioritization system work together correctly.

## Test Philosophy

Unlike unit tests (which test individual functions) or integration tests (which test tool interactions), these **end-to-end (e2e) tests simulate realistic user journeys** through the entire system:

1. **Morning**: User wakes up, checks Oura readiness, system adjusts daily goal
2. **Planning**: User gets energy-aware task recommendations
3. **Execution**: User selects and completes tasks
4. **Feedback**: User provides feedback on energy-task match
5. **Validation**: System verifies data consistency throughout

## What These Tests Cover

### ✅ Complete Data Flow
- Oura readiness score → Energy level mapping
- Energy level → Daily goal adjustment
- Energy level → Task prioritization
- Task completion → Feedback collection
- Data consistency across all stages

### ✅ Realistic User Scenarios
- **Low Energy Day** (Monday recovery): Poor sleep, reduced capacity
- **High Energy Day** (Friday sprint): Great sleep, ready for complex work
- **ADHD Override Scenario**: User knows their energy better than metrics

### ✅ Algorithm Validation
- Daily goal adjustment percentages (±15%, ±25%)
- Task scoring and ranking (0-165 points)
- Cognitive load matching (high/medium/low)
- Energy override functionality

### ✅ System Integration
- All services working together
- Data consistency across database tables
- Proper error handling and fallbacks
- User empowerment (override capability)

## Test Suites

### Test Suite 1: Monday Recovery Day (Low Energy)

**Scenario**: User had poor sleep over weekend, Oura readiness: 55

**Expected Behavior**:
- Energy Level: `low`
- Daily Goal: Reduced by 25% (18 → 13.5 points)
- Task Recommendations: Low cognitive load tasks prioritized
  - Admin tasks
  - Quick wins (< 1 hour)
  - Personal tasks
- User completes easy task successfully
- Feedback confirms perfect energy-task match

**What This Tests**:
- ✅ Low readiness → low energy mapping
- ✅ Goal reduction calculation (-25%)
- ✅ Low cognitive load task prioritization
- ✅ Momentum building for ADHD users
- ✅ Data consistency (readiness → energy → tasks → feedback)

### Test Suite 2: Friday High Energy Day

**Scenario**: User feeling great, Oura readiness: 92

**Expected Behavior**:
- Energy Level: `high`
- Daily Goal: Increased by 15% (18 → 20.7 points)
- Task Recommendations: High cognitive load tasks prioritized
  - Milestone/deliverable tasks
  - Deep work (architecture, design)
  - Large tasks (5-8 hours)
- User completes complex task successfully
- Feedback confirms perfect energy-task match

**What This Tests**:
- ✅ High readiness → high energy mapping
- ✅ Goal increase calculation (+15%)
- ✅ High cognitive load task prioritization
- ✅ Value tier bonus (milestone > deliverable > progress)
- ✅ Data consistency throughout workflow

### Test Suite 3: ADHD User with Energy Override

**Scenario**: Oura shows readiness: 65 (low), but user took ADHD medication and feels high energy

**Expected Behavior**:
- Auto-Detected Energy: `low` (from Oura 65)
- User Override: `high` (knows medication timing)
- Daily Goal: Increased to match override (+15%)
- Task Recommendations: High cognitive load tasks (respecting override)
- User completes complex task successfully
- Feedback validates override was correct

**What This Tests**:
- ✅ User override functionality
- ✅ ADHD-specific scenario (medication timing matters!)
- ✅ System respects user's self-knowledge
- ✅ Override data recorded for future learning
- ✅ Algorithm adapts to user feedback
- ✅ Medication-aware planning

**Why This Matters for ADHD Users**:
- Oura doesn't know about medication timing
- User knows: "I just took my meds, I have a 4-hour window"
- System empowers user to override auto-detection
- Feedback loop teaches system about user's patterns

## Running the Tests

### Prerequisites
- Node.js 18+ installed
- TypeScript compiler or `tsx` installed

### Run All E2E Tests
```bash
# Using tsx (recommended)
npx tsx ./tests/e2e/energy-workflow.test.ts

# Or using ts-node
npx ts-node ./tests/e2e/energy-workflow.test.ts

# Or compile first
npx tsc && node ./dist/tests/e2e/energy-workflow.test.js
```

### Expected Output

The tests produce detailed console output showing:

```
╔════════════════════════════════════════════════════════════════╗
║   ENERGY-AWARE TASK PRIORITIZATION: E2E WORKFLOW TESTS        ║
╚════════════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════════╗
║  TEST SUITE 1: MONDAY RECOVERY DAY (LOW ENERGY)              ║
╚═══════════════════════════════════════════════════════════════╝

🌅 STEP 1: Morning - Get Energy Context
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   Oura Readiness: 55/100
   Sleep Score: 62/100
   Mapped Energy Level: low
   ✓ Energy context retrieved successfully

🎯 STEP 2: Adjust Daily Goal
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   Base Daily Target: 18 points
   Adjusted Target: 14 points (-25%)
   Reason: Low readiness (55): Reduced target to protect energy and prevent burnout
   ✓ Daily goal adjusted for low energy
   ✓ Adjustment calculation verified: 18 * 0.75 = 14

... (detailed output for all steps)

╔════════════════════════════════════════════════════════════════╗
║  FINAL TEST RESULTS                                            ║
╚════════════════════════════════════════════════════════════════╝

   1. Monday Recovery Day (Low Energy): ✅ PASS
   2. Friday High Energy Day: ✅ PASS
   3. ADHD User with Energy Override: ✅ PASS

   Total: 3/3 tests passed

   🎉 ALL E2E WORKFLOW TESTS PASSED! 🎉
```

## Data Consistency Validation

Each test suite verifies data consistency by checking:

1. **Readiness Score Consistency**
   - Same readiness value throughout workflow
   - Properly stored in goal adjustment

2. **Energy Level Consistency**
   - Correctly mapped from readiness
   - Consistently used in task ranking
   - Recorded in feedback

3. **Task Recommendation Consistency**
   - Feedback task exists in recommendations
   - Rank and score recorded correctly
   - Cognitive load matches energy level

4. **Feedback Loop Integrity**
   - Suggested energy matches system recommendation
   - Actual energy captures user's experience
   - User feedback stored for learning

## Exit Codes

- **0**: All tests passed
- **1**: One or more tests failed

Use in CI/CD pipelines:
```bash
npx tsx ./tests/e2e/energy-workflow.test.ts || exit 1
```

## Test Data

### Mock Task Set
Each test uses a realistic task set with:
- **10 tasks** across all cognitive loads
- **High cognitive load** (3 tasks): Architecture, documentation, debugging
- **Medium cognitive load** (3 tasks): Implementation, code review, updates
- **Low cognitive load** (4 tasks): Admin, messages, scheduling, quick fixes

### Mock Database
Tests use an in-memory mock database that simulates:
- `energy_states` table (manual energy logs, Oura data)
- `daily_goals` table (target points, adjustments)
- `tasks` table (all task attributes)
- `energy_feedback` table (user feedback)

## Metrics Validated

### Daily Goal Adjustment Algorithm
- **Readiness >= 85**: +15% increase (18 → 21 points)
- **Readiness 70-84**: 0% adjustment (18 → 18 points)
- **Readiness < 70**: -25% reduction (18 → 14 points)

### Task Scoring Range
- **Minimum Score**: 0 points (worst energy match)
- **Maximum Score**: 165 points (perfect match + all bonuses)
- **Typical Scores**:
  - Perfect match: 60-100 points
  - Good match: 30-60 points
  - Poor match: 0-30 points

### Energy Level Mapping
- **High**: readiness >= 85
- **Medium**: readiness 70-84
- **Low**: readiness < 70

## Future Enhancements

These e2e tests could be extended to cover:

1. **Multi-Day Workflows**
   - Track energy patterns over a week
   - Validate streak protection logic
   - Test recovery recommendations

2. **Real Database Integration**
   - Test with actual SQLite/PostgreSQL
   - Validate database migrations
   - Test transaction handling

3. **MCP Tool Integration**
   - Test actual MCP tool handlers
   - Validate JSON response formats
   - Test error handling in MCP layer

4. **Coach Persona Integration**
   - Test morning briefing generation
   - Validate pattern detection queries
   - Test explanation templates

5. **Performance Testing**
   - Test with 1000+ tasks
   - Validate query performance
   - Test recommendation latency

## Related Tests

- **Unit Tests**: `tests/services/energy-prioritization.test.ts`
  - Tests individual functions in isolation
  - Validates core algorithm logic
  - Fast execution, high coverage

- **Integration Tests**: `tests/integration/energy-aware.test.ts`
  - Tests MCP tool interactions
  - Validates service layer integration
  - Tests realistic tool usage

- **Fallback Tests**: `tests/integration/oura-fallback.test.ts`
  - Tests graceful degradation
  - Validates fallback chain
  - Tests missing Oura data scenarios

## Contributing

When adding new e2e tests:

1. **Follow the 6-step workflow structure**:
   - Step 1: Get energy context
   - Step 2: Adjust daily goal
   - Step 3: Get task recommendations
   - Step 4: Complete task
   - Step 5: Provide feedback
   - Step 6: Verify consistency

2. **Use descriptive console output**:
   - Clear step headers
   - Detailed progress messages
   - Explicit pass/fail indicators
   - Summary statistics

3. **Validate data consistency**:
   - Check all data flows correctly
   - Verify no data loss
   - Confirm proper state management

4. **Test realistic scenarios**:
   - Use actual user stories
   - Include ADHD-specific patterns
   - Cover edge cases and overrides

## Questions?

For questions about these tests or the energy-aware prioritization system:
- See main documentation: `docs/energy-aware-prioritization.md`
- Review algorithm details: `src/services/energy-prioritization.ts`
- Check Coach integration: `Agents/Coach.md`
