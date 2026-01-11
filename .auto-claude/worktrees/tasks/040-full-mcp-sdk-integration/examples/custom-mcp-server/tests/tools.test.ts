/**
 * Unit tests for tool handlers
 */

import { describe, it, expect, beforeEach } from "@jest/globals";
import { handleTaskTool } from "../src/tools/handlers.js";

describe("Task Tools", () => {
  beforeEach(() => {
    // Reset environment
    delete process.env.ALLOW_WRITE;
  });

  describe("task_list", () => {
    it("should list tasks with default parameters", async () => {
      const result = await handleTaskTool("task_list", {});

      expect(result.content).toHaveLength(1);
      expect(result.content[0].type).toBe("text");

      const data = JSON.parse(result.content[0].text);
      expect(data.tasks).toBeInstanceOf(Array);
      expect(data.count).toBeGreaterThan(0);
    });

    it("should filter by status", async () => {
      const result = await handleTaskTool("task_list", {
        status: "completed",
      });

      const data = JSON.parse(result.content[0].text);
      expect(data.tasks.every((t: any) => t.status === "completed")).toBe(true);
    });

    it("should respect limit parameter", async () => {
      const result = await handleTaskTool("task_list", { limit: 1 });

      const data = JSON.parse(result.content[0].text);
      expect(data.tasks.length).toBeLessThanOrEqual(1);
    });

    it("should validate limit is within range", async () => {
      await expect(
        handleTaskTool("task_list", { limit: 0 })
      ).rejects.toThrow();

      await expect(
        handleTaskTool("task_list", { limit: 101 })
      ).rejects.toThrow();
    });
  });

  describe("task_get", () => {
    it("should get a specific task", async () => {
      const result = await handleTaskTool("task_get", { task_id: "task-1" });

      const data = JSON.parse(result.content[0].text);
      expect(data.id).toBe("task-1");
      expect(data.title).toBeDefined();
    });

    it("should throw error for non-existent task", async () => {
      await expect(
        handleTaskTool("task_get", { task_id: "non-existent" })
      ).rejects.toThrow("Task not found");
    });

    it("should require task_id parameter", async () => {
      await expect(handleTaskTool("task_get", {})).rejects.toThrow();
    });
  });

  describe("task_create", () => {
    it("should create a task when write access enabled", async () => {
      process.env.ALLOW_WRITE = "true";

      const result = await handleTaskTool("task_create", {
        title: "Test task",
        description: "Test description",
        priority: "high",
      });

      const data = JSON.parse(result.content[0].text);
      expect(data.task.id).toBeDefined();
      expect(data.task.title).toBe("Test task");
      expect(data.task.priority).toBe("high");
    });

    it("should reject when write access disabled", async () => {
      await expect(
        handleTaskTool("task_create", { title: "Test" })
      ).rejects.toThrow("Write access not enabled");
    });

    it("should require title parameter", async () => {
      process.env.ALLOW_WRITE = "true";

      await expect(handleTaskTool("task_create", {})).rejects.toThrow();
    });

    it("should validate title length", async () => {
      process.env.ALLOW_WRITE = "true";

      await expect(
        handleTaskTool("task_create", { title: "" })
      ).rejects.toThrow();

      await expect(
        handleTaskTool("task_create", { title: "a".repeat(201) })
      ).rejects.toThrow();
    });
  });

  describe("task_update", () => {
    it("should update a task when write access enabled", async () => {
      process.env.ALLOW_WRITE = "true";

      const result = await handleTaskTool("task_update", {
        task_id: "task-1",
        title: "Updated title",
        status: "completed",
      });

      const data = JSON.parse(result.content[0].text);
      expect(data.task.title).toBe("Updated title");
      expect(data.task.status).toBe("completed");
    });

    it("should reject when write access disabled", async () => {
      await expect(
        handleTaskTool("task_update", { task_id: "task-1", title: "Test" })
      ).rejects.toThrow("Write access not enabled");
    });

    it("should require task_id parameter", async () => {
      process.env.ALLOW_WRITE = "true";

      await expect(
        handleTaskTool("task_update", { title: "Test" })
      ).rejects.toThrow();
    });
  });

  describe("task_delete", () => {
    it("should delete a task when write access enabled", async () => {
      process.env.ALLOW_WRITE = "true";

      const result = await handleTaskTool("task_delete", {
        task_id: "task-1",
      });

      const data = JSON.parse(result.content[0].text);
      expect(data.message).toContain("deleted successfully");
    });

    it("should reject when write access disabled", async () => {
      await expect(
        handleTaskTool("task_delete", { task_id: "task-1" })
      ).rejects.toThrow("Write access not enabled");
    });

    it("should require task_id parameter", async () => {
      process.env.ALLOW_WRITE = "true";

      await expect(handleTaskTool("task_delete", {})).rejects.toThrow();
    });
  });
});
