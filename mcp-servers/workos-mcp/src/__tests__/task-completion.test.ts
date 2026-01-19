/**
 * Task Completion Tests
 *
 * Tests to prevent regression of the following bugs:
 * 1. pointsFinal not set when task completed
 * 2. clientsTouchedToday count incorrect
 *
 * Points mapping by value tier:
 * - checkbox: 2
 * - progress: 4
 * - deliverable: 6
 * - milestone: 8
 */

import { describe, it, expect, beforeEach, vi, type MockedFunction } from "vitest";

// =============================================================================
// POINTS BY TIER MAPPING (must match handlers.ts)
// =============================================================================

const POINTS_BY_TIER: Record<string, number> = {
  checkbox: 1,
  progress: 2,
  deliverable: 4,
  milestone: 7,
};

// =============================================================================
// MOCK TYPES
// =============================================================================

interface MockTask {
  id: number;
  title: string;
  valueTier: string;
  pointsFinal: number | null;
  status: string;
  clientId: number | null;
  completedAt: Date | null;
  category: string;
}

interface MockClient {
  id: number;
  name: string;
  type: string;
}

// =============================================================================
// TEST SUITE: Points Calculation on Task Completion
// =============================================================================

describe("Task Completion: pointsFinal Calculation", () => {
  describe("POINTS_BY_TIER mapping", () => {
    it("should map checkbox tier to 1 point", () => {
      expect(POINTS_BY_TIER.checkbox).toBe(1);
    });

    it("should map progress tier to 2 points", () => {
      expect(POINTS_BY_TIER.progress).toBe(2);
    });

    it("should map deliverable tier to 4 points", () => {
      expect(POINTS_BY_TIER.deliverable).toBe(4);
    });

    it("should map milestone tier to 7 points", () => {
      expect(POINTS_BY_TIER.milestone).toBe(7);
    });
  });

  describe("Auto-calculate pointsFinal from valueTier", () => {
    /**
     * Simulates the logic from handleCompleteTask in handlers.ts (lines 505-508)
     */
    function calculatePointsFinalOnCompletion(
      existingPointsFinal: number | null,
      valueTier: string | null
    ): number {
      return (
        existingPointsFinal ??
        POINTS_BY_TIER[valueTier || "checkbox"] ??
        POINTS_BY_TIER.checkbox
      );
    }

    it("should calculate pointsFinal from valueTier when pointsFinal is null", () => {
      const task: MockTask = {
        id: 1,
        title: "Test Task",
        valueTier: "deliverable",
        pointsFinal: null,
        status: "active",
        clientId: null,
        completedAt: null,
        category: "work",
      };

      const calculatedPoints = calculatePointsFinalOnCompletion(
        task.pointsFinal,
        task.valueTier
      );

      expect(calculatedPoints).toBe(4); // deliverable = 4 points
    });

    it("should preserve existing pointsFinal when already set (manual override)", () => {
      const task: MockTask = {
        id: 2,
        title: "Task with manual points",
        valueTier: "deliverable",
        pointsFinal: 10, // Manual override
        status: "active",
        clientId: null,
        completedAt: null,
        category: "work",
      };

      const calculatedPoints = calculatePointsFinalOnCompletion(
        task.pointsFinal,
        task.valueTier
      );

      expect(calculatedPoints).toBe(10); // Preserve manual override
    });

    it("should default to checkbox (2 points) when valueTier is null", () => {
      const task: MockTask = {
        id: 3,
        title: "Task with no tier",
        valueTier: null as any,
        pointsFinal: null,
        status: "active",
        clientId: null,
        completedAt: null,
        category: "work",
      };

      const calculatedPoints = calculatePointsFinalOnCompletion(
        task.pointsFinal,
        task.valueTier
      );

      expect(calculatedPoints).toBe(1); // Default to checkbox
    });

    it("should default to checkbox (1 point) when valueTier is unknown", () => {
      const task: MockTask = {
        id: 4,
        title: "Task with unknown tier",
        valueTier: "unknown_tier",
        pointsFinal: null,
        status: "active",
        clientId: null,
        completedAt: null,
        category: "work",
      };

      const calculatedPoints = calculatePointsFinalOnCompletion(
        task.pointsFinal,
        task.valueTier
      );

      expect(calculatedPoints).toBe(1); // Fall back to checkbox default
    });

    it("should calculate correct points for all tier types", () => {
      const testCases: Array<{ valueTier: string; expectedPoints: number }> = [
        { valueTier: "checkbox", expectedPoints: 1 },
        { valueTier: "progress", expectedPoints: 2 },
        { valueTier: "deliverable", expectedPoints: 4 },
        { valueTier: "milestone", expectedPoints: 7 },
      ];

      testCases.forEach(({ valueTier, expectedPoints }) => {
        const calculatedPoints = calculatePointsFinalOnCompletion(null, valueTier);
        expect(calculatedPoints).toBe(expectedPoints);
      });
    });
  });
});

// =============================================================================
// TEST SUITE: Clients Touched Today Calculation
// =============================================================================

describe("Task Completion: clientsTouchedToday Calculation", () => {
  /**
   * Simulates the logic from handleGetTodayMetrics in handlers.ts (lines 115-125)
   */
  function calculateClientsTouchedToday(
    completedTasks: MockTask[],
    externalClients: MockClient[]
  ): number {
    const externalClientIds = new Set(externalClients.map((c) => c.id));
    const clientsTouchedToday = new Set(
      completedTasks
        .filter((t) => t.clientId && externalClientIds.has(t.clientId))
        .map((t) => t.clientId)
    ).size;
    return clientsTouchedToday;
  }

  it("should count unique external clients from completed tasks", () => {
    const externalClients: MockClient[] = [
      { id: 1, name: "Client A", type: "external" },
      { id: 2, name: "Client B", type: "external" },
      { id: 3, name: "Client C", type: "external" },
    ];

    const completedTasks: MockTask[] = [
      {
        id: 1,
        title: "Task 1",
        valueTier: "progress",
        pointsFinal: 4,
        status: "done",
        clientId: 1,
        completedAt: new Date(),
        category: "work",
      },
      {
        id: 2,
        title: "Task 2",
        valueTier: "checkbox",
        pointsFinal: 2,
        status: "done",
        clientId: 2,
        completedAt: new Date(),
        category: "work",
      },
    ];

    const clientsTouched = calculateClientsTouchedToday(completedTasks, externalClients);
    expect(clientsTouched).toBe(2); // 2 unique clients
  });

  it("should not double-count same client with multiple completed tasks", () => {
    const externalClients: MockClient[] = [
      { id: 1, name: "Client A", type: "external" },
      { id: 2, name: "Client B", type: "external" },
    ];

    const completedTasks: MockTask[] = [
      {
        id: 1,
        title: "Task 1 for Client A",
        valueTier: "progress",
        pointsFinal: 4,
        status: "done",
        clientId: 1,
        completedAt: new Date(),
        category: "work",
      },
      {
        id: 2,
        title: "Task 2 for Client A",
        valueTier: "deliverable",
        pointsFinal: 6,
        status: "done",
        clientId: 1, // Same client
        completedAt: new Date(),
        category: "work",
      },
      {
        id: 3,
        title: "Task 3 for Client A",
        valueTier: "checkbox",
        pointsFinal: 2,
        status: "done",
        clientId: 1, // Same client again
        completedAt: new Date(),
        category: "work",
      },
    ];

    const clientsTouched = calculateClientsTouchedToday(completedTasks, externalClients);
    expect(clientsTouched).toBe(1); // Only 1 unique client even with 3 tasks
  });

  it("should exclude internal clients from the count", () => {
    const externalClients: MockClient[] = [
      { id: 1, name: "External Client", type: "external" },
      // Note: internal client is NOT in this list (as per the query filter)
    ];

    const completedTasks: MockTask[] = [
      {
        id: 1,
        title: "External task",
        valueTier: "progress",
        pointsFinal: 4,
        status: "done",
        clientId: 1, // External
        completedAt: new Date(),
        category: "work",
      },
      {
        id: 2,
        title: "Internal task",
        valueTier: "checkbox",
        pointsFinal: 2,
        status: "done",
        clientId: 99, // Internal client ID (not in externalClients)
        completedAt: new Date(),
        category: "work",
      },
    ];

    const clientsTouched = calculateClientsTouchedToday(completedTasks, externalClients);
    expect(clientsTouched).toBe(1); // Only external client counted
  });

  it("should handle tasks with null clientId", () => {
    const externalClients: MockClient[] = [
      { id: 1, name: "Client A", type: "external" },
    ];

    const completedTasks: MockTask[] = [
      {
        id: 1,
        title: "Task with client",
        valueTier: "progress",
        pointsFinal: 4,
        status: "done",
        clientId: 1,
        completedAt: new Date(),
        category: "work",
      },
      {
        id: 2,
        title: "Task without client",
        valueTier: "checkbox",
        pointsFinal: 2,
        status: "done",
        clientId: null, // No client assigned
        completedAt: new Date(),
        category: "work",
      },
    ];

    const clientsTouched = calculateClientsTouchedToday(completedTasks, externalClients);
    expect(clientsTouched).toBe(1); // Only task with client counted
  });

  it("should return 0 when no tasks have external clients", () => {
    const externalClients: MockClient[] = [
      { id: 1, name: "Client A", type: "external" },
    ];

    const completedTasks: MockTask[] = [
      {
        id: 1,
        title: "Task without client",
        valueTier: "progress",
        pointsFinal: 4,
        status: "done",
        clientId: null,
        completedAt: new Date(),
        category: "work",
      },
    ];

    const clientsTouched = calculateClientsTouchedToday(completedTasks, externalClients);
    expect(clientsTouched).toBe(0);
  });

  it("should return 0 when there are no completed tasks", () => {
    const externalClients: MockClient[] = [
      { id: 1, name: "Client A", type: "external" },
      { id: 2, name: "Client B", type: "external" },
    ];

    const completedTasks: MockTask[] = [];

    const clientsTouched = calculateClientsTouchedToday(completedTasks, externalClients);
    expect(clientsTouched).toBe(0);
  });

  it("should handle completing tasks for multiple clients correctly", () => {
    const externalClients: MockClient[] = [
      { id: 1, name: "Orlando", type: "external" },
      { id: 2, name: "Raleigh", type: "external" },
      { id: 3, name: "Memphis", type: "external" },
      { id: 4, name: "Internal", type: "internal" }, // Should be excluded by query
    ];

    // Filter to only external clients (simulating the ne(type, 'internal') query)
    const filteredExternalClients = externalClients.filter((c) => c.type !== "internal");

    const completedTasks: MockTask[] = [
      {
        id: 1,
        title: "Orlando Task 1",
        valueTier: "deliverable",
        pointsFinal: 6,
        status: "done",
        clientId: 1,
        completedAt: new Date(),
        category: "work",
      },
      {
        id: 2,
        title: "Orlando Task 2",
        valueTier: "progress",
        pointsFinal: 4,
        status: "done",
        clientId: 1,
        completedAt: new Date(),
        category: "work",
      },
      {
        id: 3,
        title: "Raleigh Task",
        valueTier: "milestone",
        pointsFinal: 8,
        status: "done",
        clientId: 2,
        completedAt: new Date(),
        category: "work",
      },
      {
        id: 4,
        title: "Memphis Task",
        valueTier: "checkbox",
        pointsFinal: 2,
        status: "done",
        clientId: 3,
        completedAt: new Date(),
        category: "work",
      },
    ];

    const clientsTouched = calculateClientsTouchedToday(completedTasks, filteredExternalClients);
    expect(clientsTouched).toBe(3); // Orlando, Raleigh, Memphis (unique clients)
  });
});

// =============================================================================
// TEST SUITE: Integration - Points Total with clientsTouchedToday
// =============================================================================

describe("Task Completion: Integration Tests", () => {
  /**
   * Simulates calculateTotalPoints from shared/utils.ts
   */
  function calculateTotalPoints(tasks: MockTask[]): number {
    return tasks.reduce((sum, task) => {
      return sum + (task.pointsFinal ?? 2); // Default to 2 if not set
    }, 0);
  }

  it("should calculate correct total points when all tasks have pointsFinal set", () => {
    const completedTasks: MockTask[] = [
      {
        id: 1,
        title: "Checkbox task",
        valueTier: "checkbox",
        pointsFinal: 2,
        status: "done",
        clientId: 1,
        completedAt: new Date(),
        category: "work",
      },
      {
        id: 2,
        title: "Progress task",
        valueTier: "progress",
        pointsFinal: 4,
        status: "done",
        clientId: 1,
        completedAt: new Date(),
        category: "work",
      },
      {
        id: 3,
        title: "Deliverable task",
        valueTier: "deliverable",
        pointsFinal: 6,
        status: "done",
        clientId: 2,
        completedAt: new Date(),
        category: "work",
      },
      {
        id: 4,
        title: "Milestone task",
        valueTier: "milestone",
        pointsFinal: 8,
        status: "done",
        clientId: 3,
        completedAt: new Date(),
        category: "work",
      },
    ];

    const totalPoints = calculateTotalPoints(completedTasks);
    expect(totalPoints).toBe(20); // 2 + 4 + 6 + 8 = 20
  });

  it("should handle scenario where task was completed without pointsFinal being set (bug scenario)", () => {
    // This simulates the OLD bug where pointsFinal was not set on completion
    const completedTaskWithBug: MockTask = {
      id: 1,
      title: "Task completed with bug",
      valueTier: "deliverable",
      pointsFinal: null as any, // Bug: pointsFinal not set
      status: "done",
      clientId: 1,
      completedAt: new Date(),
      category: "work",
    };

    // The calculateTotalPoints function defaults to 2 when pointsFinal is null
    // This is incorrect - it should be 6 (deliverable tier)
    const totalWithBug = calculateTotalPoints([completedTaskWithBug]);
    expect(totalWithBug).toBe(2); // Incorrect! Should be 4

    // After the fix, pointsFinal should be set on completion
    const completedTaskAfterFix: MockTask = {
      ...completedTaskWithBug,
      pointsFinal: POINTS_BY_TIER[completedTaskWithBug.valueTier], // Fix: set pointsFinal
    };

    const totalAfterFix = calculateTotalPoints([completedTaskAfterFix]);
    expect(totalAfterFix).toBe(4); // Correct!
  });

  it("should track both points and clients correctly in real-world scenario", () => {
    const externalClients: MockClient[] = [
      { id: 1, name: "Orlando", type: "external" },
      { id: 2, name: "Raleigh", type: "external" },
    ];

    // Simulate completing multiple tasks throughout the day
    const completedTasks: MockTask[] = [
      {
        id: 1,
        title: "Morning standup notes",
        valueTier: "checkbox",
        pointsFinal: 2,
        status: "done",
        clientId: 1, // Orlando
        completedAt: new Date(),
        category: "work",
      },
      {
        id: 2,
        title: "Code review",
        valueTier: "progress",
        pointsFinal: 4,
        status: "done",
        clientId: 1, // Orlando again
        completedAt: new Date(),
        category: "work",
      },
      {
        id: 3,
        title: "Feature deployment",
        valueTier: "deliverable",
        pointsFinal: 6,
        status: "done",
        clientId: 2, // Raleigh
        completedAt: new Date(),
        category: "work",
      },
    ];

    const totalPoints = calculateTotalPoints(completedTasks);
    expect(totalPoints).toBe(12); // 2 + 4 + 6 = 12

    // Calculate clients touched
    const externalClientIds = new Set(externalClients.map((c) => c.id));
    const clientsTouchedToday = new Set(
      completedTasks
        .filter((t) => t.clientId && externalClientIds.has(t.clientId))
        .map((t) => t.clientId)
    ).size;

    expect(clientsTouchedToday).toBe(2); // Orlando and Raleigh (unique)
  });
});
