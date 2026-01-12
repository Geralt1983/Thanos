# Integration Tests - Energy-Aware Task Prioritization

This directory contains integration tests for the energy-aware task prioritization MCP tools.

## Test Coverage

### 1. **workos_get_energy_aware_tasks** - Energy-Based Task Selection

Tests the MCP tool that returns tasks ranked by energy level match:

- **High Energy Tests** (`testGetEnergyAwareTasksHighEnergy`)
  - Prioritizes high cognitive load tasks
  - Surfaces milestone and deliverable work
  - Favors deep work and large tasks
  - Validates scoring algorithm (100+ for perfect matches)
  - Ensures active tasks get momentum bonus

- **Medium Energy Tests** (`testGetEnergyAwareTasksMediumEnergy`)
  - Prioritizes medium cognitive load tasks
  - Surfaces progress-tier work
  - Allows variety of task types
  - Validates balanced recommendations

- **Low Energy Tests** (`testGetEnergyAwareTasksLowEnergy`)
  - Prioritizes low cognitive load tasks
  - Surfaces checkbox and admin work
  - Favors quick wins (effort <= 2)
  - Avoids high cognitive tasks (ranks them last)
  - Validates ADHD-friendly momentum building

### 2. **workos_override_energy_suggestion** - Manual Override

Tests user's ability to override auto-detected energy levels:

- **Override Scenarios** (`testEnergyOverride`)
  - Low readiness → User overrides to HIGH (e.g., after coffee/medication)
  - High readiness → User overrides to LOW (e.g., distracted/tired despite metrics)
  - Validates that override changes task recommendations
  - Validates cognitive load alignment with override energy level
  - ADHD-specific: Medication timing windows

### 3. **workos_adjust_daily_goal** - Readiness-Based Goal Adjustment

Tests daily target point adjustment based on Oura readiness scores:

- **High Readiness Tests** (`testDailyGoalAdjustmentHighReadiness`)
  - Readiness >= 85 → +15% target increase
  - Validates energy level mapping to "high"
  - Checks reasoning includes sleep score context
  - Example: 18pts base → 21pts adjusted

- **Medium Readiness Tests** (`testDailyGoalAdjustmentMediumReadiness`)
  - Readiness 70-84 → 0% adjustment (maintain standard target)
  - Validates energy level mapping to "medium"
  - Example: 18pts base → 18pts adjusted

- **Low Readiness Tests** (`testDailyGoalAdjustmentLowReadiness`)
  - Readiness < 70 → -25% target reduction
  - Validates energy level mapping to "low"
  - Checks reasoning mentions burnout prevention
  - Example: 18pts base → 14pts adjusted

- **Various Targets Tests** (`testDailyGoalAdjustmentVariousTargets`)
  - Tests with base targets: 12, 18, 24, 30 points
  - Validates percentage calculations work correctly across different targets

### 4. **Realistic User Workflows**

End-to-end scenarios simulating real-world usage:

- **Monday Morning Recovery** (`testRealisticWorkflows`)
  - Low readiness (58), poor sleep (52)
  - Reduced daily goal (-25%)
  - Quick wins only (effort <= 2)
  - Low cognitive load tasks

- **Friday High Energy Sprint**
  - High readiness (94), excellent sleep (90)
  - Increased daily goal (+15%)
  - High cognitive load tasks
  - Milestone/deliverable work prioritized

- **ADHD User with Medication**
  - Morning: Low readiness (65) → low cognitive tasks
  - After medication: User override → high cognitive tasks
  - Validates leveraging medication window for complex work
  - Tests context-aware override use case

## Running the Tests

### Run all integration tests:
```bash
npx tsx tests/integration/energy-aware.test.ts
```

### Run specific test suite:
```typescript
import { testGetEnergyAwareTasksHighEnergy } from './tests/integration/energy-aware.test.ts';
testGetEnergyAwareTasksHighEnergy();
```

## Test Output Format

Tests use custom assertion helpers that provide detailed output:

```
📋 Testing workos_get_energy_aware_tasks - High Energy
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Should return 5 tasks when limit=5
✅ Top task should have high cognitive load for high energy
✅ At least 2 of top 3 tasks should be high cognitive load
...

🎯 Top 5 tasks for HIGH energy:
   1. [HIGH] Architect new microservice
      Score: 138 | Perfect match: High cognitive load task for high energy. Bonus: High-value work best done with high energy
   2. [HIGH] Write technical spec
      Score: 130 | Perfect match: High cognitive load task for high energy. Bonus: High-value work best done with high energy
   ...

✨ High energy task selection tests passed!
```

## Integration vs Unit Tests

**Unit Tests** (`tests/services/energy-prioritization.test.ts`):
- Test pure functions in isolation
- Mock-free, no database required
- Fast execution
- 100% algorithmic coverage

**Integration Tests** (`tests/integration/energy-aware.test.ts`):
- Test service layer integration (simulates MCP tool handlers)
- Uses diverse task datasets
- Tests full workflows and scenarios
- Validates end-to-end behavior

## Test Data

All tests use `createDiverseTaskSet()` which provides 10 representative tasks:

- **High Cognitive (3):** Architecture, specs, complex bugs
- **Medium Cognitive (3):** Code reviews, documentation, refactoring
- **Low Cognitive (4):** Emails, admin work, filing, organizing

This dataset covers:
- All cognitive loads: high, medium, low
- All value tiers: milestone, deliverable, progress, checkbox
- All drain types: deep, shallow, admin
- All categories: work, personal
- All statuses: active, backlog
- Effort range: 1-8 points

## ADHD-Specific Features Tested

1. **Quick Wins on Low Energy** - Tasks with effort <= 2 get +15 bonus
2. **Momentum Building** - Active tasks get +5 bonus to finish what's started
3. **Medication Window Override** - User can manually set high energy despite low metrics
4. **Burnout Prevention** - Low readiness reduces target by 25%
5. **Energy Matching** - Cognitive load aligned with actual energy state

## Future Enhancements

Tests to add in future subtasks:

- Database integration (requires actual DB setup)
- MCP handler layer tests (requires handler files in worktree)
- Oura cache integration tests (subtask 6.3)
- Feedback loop tests (energy_feedback table)
- Multi-day pattern detection
- Time-of-day energy curves

## Success Criteria

All tests must pass for subtask 6.2 to be marked complete:

- ✅ High/medium/low energy task selection works correctly
- ✅ Override functionality changes recommendations appropriately
- ✅ Daily goal adjustments follow readiness thresholds (85, 70)
- ✅ Adjustment percentages correct (+15%, 0%, -25%)
- ✅ Realistic workflows demonstrate ADHD-friendly behavior
- ✅ All tasks have energy scores and match reasons
- ✅ Tasks properly sorted by energy score descending

## Notes

These integration tests are designed to be:
- **Self-documenting** - Clear scenario descriptions and console output
- **Fast** - No database or external dependencies
- **Deterministic** - Same input always produces same output
- **Comprehensive** - Covers happy path, edge cases, and realistic scenarios
- **ADHD-focused** - Validates features specifically for ADHD users

The tests simulate MCP tool handler behavior by directly calling the service layer functions that power the handlers. When the actual handler files exist, these tests will validate that the integration between handlers and services works correctly.
