/**
 * Tool definitions for the custom task server
 *
 * Each tool defines:
 * - name: Unique identifier
 * - description: What the tool does
 * - inputSchema: JSON Schema for parameters
 */

export const taskTools = [
  {
    name: "task_list",
    description:
      "List all tasks with optional filtering. Returns task ID, title, status, priority, and creation date. " +
      "Use 'active' status to see only incomplete tasks, 'completed' for done tasks, or 'all' for everything. " +
      "Default limit is 10, maximum is 100.",
    inputSchema: {
      type: "object",
      properties: {
        status: {
          type: "string",
          enum: ["active", "completed", "all"],
          description: "Filter tasks by status",
          default: "active",
        },
        limit: {
          type: "number",
          description: "Maximum number of tasks to return",
          minimum: 1,
          maximum: 100,
          default: 10,
        },
        priority: {
          type: "string",
          enum: ["low", "medium", "high"],
          description: "Filter by priority level",
        },
      },
    },
  },
  {
    name: "task_get",
    description:
      "Get detailed information about a specific task. " +
      "Returns all task fields including title, description, status, priority, creation date, and completion date.",
    inputSchema: {
      type: "object",
      properties: {
        task_id: {
          type: "string",
          description: "The unique task identifier",
        },
      },
      required: ["task_id"],
    },
  },
  {
    name: "task_create",
    description:
      "Create a new task. Requires ALLOW_WRITE=true environment variable. " +
      "Returns the created task with assigned ID and timestamps. " +
      "Title is required, description and priority are optional.",
    inputSchema: {
      type: "object",
      properties: {
        title: {
          type: "string",
          description: "Task title (required)",
          minLength: 1,
          maxLength: 200,
        },
        description: {
          type: "string",
          description: "Detailed task description",
          maxLength: 2000,
        },
        priority: {
          type: "string",
          enum: ["low", "medium", "high"],
          description: "Task priority level",
          default: "medium",
        },
      },
      required: ["title"],
    },
  },
  {
    name: "task_update",
    description:
      "Update an existing task. Requires ALLOW_WRITE=true environment variable. " +
      "You can update title, description, status, and/or priority. " +
      "Only provided fields will be updated, others remain unchanged. " +
      "Returns the updated task.",
    inputSchema: {
      type: "object",
      properties: {
        task_id: {
          type: "string",
          description: "The unique task identifier",
        },
        title: {
          type: "string",
          description: "New task title",
          minLength: 1,
          maxLength: 200,
        },
        description: {
          type: "string",
          description: "New task description",
          maxLength: 2000,
        },
        status: {
          type: "string",
          enum: ["active", "completed"],
          description: "New task status",
        },
        priority: {
          type: "string",
          enum: ["low", "medium", "high"],
          description: "New priority level",
        },
      },
      required: ["task_id"],
    },
  },
  {
    name: "task_delete",
    description:
      "Delete a task. Requires ALLOW_WRITE=true environment variable. " +
      "This action is permanent and cannot be undone. " +
      "Returns confirmation of deletion.",
    inputSchema: {
      type: "object",
      properties: {
        task_id: {
          type: "string",
          description: "The unique task identifier",
        },
      },
      required: ["task_id"],
    },
  },
];
