#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import * as crypto from "node:crypto";

const API_BASE = "https://api.todoist.com/api/v1";
const SYNC_API_BASE = "https://api.todoist.com/api/v1";

function getToken(): string {
  const token = process.env.TODOIST_API_TOKEN;
  if (!token) {
    throw new Error("TODOIST_API_TOKEN environment variable is required");
  }
  return token;
}

async function apiRequest(
  endpoint: string,
  method: string = "GET",
  body?: object,
  useSync: boolean = false
): Promise<any> {
  const base = useSync ? SYNC_API_BASE : API_BASE;
  const url = `${base}${endpoint}`;

  const headers: Record<string, string> = {
    Authorization: `Bearer ${getToken()}`,
    "Content-Type": "application/json",
  };

  const options: RequestInit = { method, headers };
  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(url, options);

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Todoist API error ${response.status}: ${text}`);
  }

  if (response.status === 204) {
    return { success: true };
  }

  return response.json();
}

async function syncRequest(payload: Record<string, any>): Promise<any> {
  const url = `${SYNC_API_BASE}/sync`;
  const headers: Record<string, string> = {
    Authorization: `Bearer ${getToken()}`,
    "Content-Type": "application/x-www-form-urlencoded",
  };
  const body = new URLSearchParams();
  for (const [key, value] of Object.entries(payload)) {
    if (value === undefined) continue;
    body.set(key, typeof value === "string" ? value : JSON.stringify(value));
  }

  const response = await fetch(url, { method: "POST", headers, body });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Todoist API error ${response.status}: ${text}`);
  }
  if (response.status === 204) {
    return { success: true };
  }
  return response.json();
}

// Tool definitions
const tools = [
  // Projects
  {
    name: "list_projects",
    description: "List all projects",
    inputSchema: { type: "object", properties: {} },
  },
  {
    name: "create_project",
    description: "Create a new project",
    inputSchema: {
      type: "object",
      properties: {
        name: { type: "string", description: "Project name" },
        color: { type: "string", description: "Color name (e.g., 'berry_red')" },
        parent_id: { type: "string", description: "Parent project ID" },
        is_favorite: { type: "boolean", description: "Mark as favorite" },
        view_style: { type: "string", enum: ["list", "board"], description: "View style" },
      },
      required: ["name"],
    },
  },
  {
    name: "get_project",
    description: "Get a project by ID",
    inputSchema: {
      type: "object",
      properties: { project_id: { type: "string", description: "Project ID" } },
      required: ["project_id"],
    },
  },
  {
    name: "update_project",
    description: "Update a project",
    inputSchema: {
      type: "object",
      properties: {
        project_id: { type: "string", description: "Project ID" },
        name: { type: "string", description: "New name" },
        color: { type: "string", description: "New color" },
        is_favorite: { type: "boolean", description: "Mark as favorite" },
        view_style: { type: "string", enum: ["list", "board"], description: "View style" },
      },
      required: ["project_id"],
    },
  },
  {
    name: "delete_project",
    description: "Delete a project",
    inputSchema: {
      type: "object",
      properties: { project_id: { type: "string", description: "Project ID" } },
      required: ["project_id"],
    },
  },

  // Sections
  {
    name: "list_sections",
    description: "List sections, optionally filtered by project",
    inputSchema: {
      type: "object",
      properties: { project_id: { type: "string", description: "Filter by project ID" } },
    },
  },
  {
    name: "create_section",
    description: "Create a new section",
    inputSchema: {
      type: "object",
      properties: {
        name: { type: "string", description: "Section name" },
        project_id: { type: "string", description: "Project ID" },
        order: { type: "number", description: "Order in project" },
      },
      required: ["name", "project_id"],
    },
  },
  {
    name: "get_section",
    description: "Get a section by ID",
    inputSchema: {
      type: "object",
      properties: { section_id: { type: "string", description: "Section ID" } },
      required: ["section_id"],
    },
  },
  {
    name: "update_section",
    description: "Update a section",
    inputSchema: {
      type: "object",
      properties: {
        section_id: { type: "string", description: "Section ID" },
        name: { type: "string", description: "New name" },
      },
      required: ["section_id", "name"],
    },
  },
  {
    name: "delete_section",
    description: "Delete a section",
    inputSchema: {
      type: "object",
      properties: { section_id: { type: "string", description: "Section ID" } },
      required: ["section_id"],
    },
  },

  // Tasks
  {
    name: "list_tasks",
    description: "List tasks with optional filters",
    inputSchema: {
      type: "object",
      properties: {
        project_id: { type: "string", description: "Filter by project" },
        section_id: { type: "string", description: "Filter by section" },
        parent_id: { type: "string", description: "Filter by parent task ID" },
        label: { type: "string", description: "Filter by label" },
        ids: {
          type: "array",
          items: { type: "string" },
          description: "Filter by specific task IDs",
        },
        cursor: { type: "string", description: "Pagination cursor" },
        limit: { type: "number", description: "Max tasks to return" },
        filter: {
          type: "string",
          description: "Todoist filter query (uses /tasks/filter endpoint)",
        },
        lang: { type: "string", description: "Language for filter query" },
      },
    },
  },
  {
    name: "create_task",
    description: "Create a new task",
    inputSchema: {
      type: "object",
      properties: {
        content: { type: "string", description: "Task content" },
        description: { type: "string", description: "Task description" },
        project_id: { type: "string", description: "Project ID" },
        section_id: { type: "string", description: "Section ID" },
        parent_id: { type: "string", description: "Parent task ID" },
        order: { type: "number", description: "Order in list" },
        labels: { type: "array", items: { type: "string" }, description: "Labels" },
        priority: { type: "number", enum: [1, 2, 3, 4], description: "Priority (1=normal, 4=urgent)" },
        due_string: { type: "string", description: "Due date in natural language" },
        due_date: { type: "string", description: "Due date (YYYY-MM-DD)" },
        due_datetime: { type: "string", description: "Due datetime (RFC3339)" },
        due_lang: { type: "string", description: "Language for due_string" },
        assignee_id: { type: "string", description: "Assignee user ID" },
      },
      required: ["content"],
    },
  },
  {
    name: "get_task",
    description: "Get a task by ID",
    inputSchema: {
      type: "object",
      properties: { task_id: { type: "string", description: "Task ID" } },
      required: ["task_id"],
    },
  },
  {
    name: "update_task",
    description: "Update a task",
    inputSchema: {
      type: "object",
      properties: {
        task_id: { type: "string", description: "Task ID" },
        content: { type: "string", description: "Task content" },
        description: { type: "string", description: "Task description" },
        labels: { type: "array", items: { type: "string" }, description: "Labels" },
        priority: { type: "number", enum: [1, 2, 3, 4], description: "Priority" },
        due_string: { type: "string", description: "Due date in natural language" },
        due_date: { type: "string", description: "Due date (YYYY-MM-DD)" },
        due_datetime: { type: "string", description: "Due datetime (RFC3339)" },
        assignee_id: { type: "string", description: "Assignee user ID" },
      },
      required: ["task_id"],
    },
  },
  {
    name: "complete_task",
    description: "Mark a task as complete",
    inputSchema: {
      type: "object",
      properties: { task_id: { type: "string", description: "Task ID" } },
      required: ["task_id"],
    },
  },
  {
    name: "reopen_task",
    description: "Reopen a completed task",
    inputSchema: {
      type: "object",
      properties: { task_id: { type: "string", description: "Task ID" } },
      required: ["task_id"],
    },
  },
  {
    name: "delete_task",
    description: "Delete a task",
    inputSchema: {
      type: "object",
      properties: { task_id: { type: "string", description: "Task ID" } },
      required: ["task_id"],
    },
  },
  {
    name: "move_task",
    description: "Move a task to a different project or section",
    inputSchema: {
      type: "object",
      properties: {
        task_id: { type: "string", description: "Task ID" },
        project_id: { type: "string", description: "Target project ID" },
        section_id: { type: "string", description: "Target section ID" },
        parent_id: { type: "string", description: "Target parent task ID" },
      },
      required: ["task_id"],
    },
  },

  // Labels
  {
    name: "list_labels",
    description: "List all personal labels",
    inputSchema: { type: "object", properties: {} },
  },
  {
    name: "create_label",
    description: "Create a new label",
    inputSchema: {
      type: "object",
      properties: {
        name: { type: "string", description: "Label name" },
        color: { type: "string", description: "Color name" },
        order: { type: "number", description: "Label order" },
        is_favorite: { type: "boolean", description: "Mark as favorite" },
      },
      required: ["name"],
    },
  },
  {
    name: "get_label",
    description: "Get a label by ID",
    inputSchema: {
      type: "object",
      properties: { label_id: { type: "string", description: "Label ID" } },
      required: ["label_id"],
    },
  },
  {
    name: "update_label",
    description: "Update a label",
    inputSchema: {
      type: "object",
      properties: {
        label_id: { type: "string", description: "Label ID" },
        name: { type: "string", description: "New name" },
        color: { type: "string", description: "New color" },
        order: { type: "number", description: "New order" },
        is_favorite: { type: "boolean", description: "Mark as favorite" },
      },
      required: ["label_id"],
    },
  },
  {
    name: "delete_label",
    description: "Delete a label",
    inputSchema: {
      type: "object",
      properties: { label_id: { type: "string", description: "Label ID" } },
      required: ["label_id"],
    },
  },

  // Comments
  {
    name: "list_comments",
    description: "List comments for a task or project",
    inputSchema: {
      type: "object",
      properties: {
        task_id: { type: "string", description: "Task ID" },
        project_id: { type: "string", description: "Project ID" },
      },
    },
  },
  {
    name: "create_comment",
    description: "Create a comment",
    inputSchema: {
      type: "object",
      properties: {
        content: { type: "string", description: "Comment content" },
        task_id: { type: "string", description: "Task ID" },
        project_id: { type: "string", description: "Project ID" },
      },
      required: ["content"],
    },
  },
  {
    name: "get_comment",
    description: "Get a comment by ID",
    inputSchema: {
      type: "object",
      properties: { comment_id: { type: "string", description: "Comment ID" } },
      required: ["comment_id"],
    },
  },
  {
    name: "update_comment",
    description: "Update a comment",
    inputSchema: {
      type: "object",
      properties: {
        comment_id: { type: "string", description: "Comment ID" },
        content: { type: "string", description: "New content" },
      },
      required: ["comment_id", "content"],
    },
  },
  {
    name: "delete_comment",
    description: "Delete a comment",
    inputSchema: {
      type: "object",
      properties: { comment_id: { type: "string", description: "Comment ID" } },
      required: ["comment_id"],
    },
  },

  // Filters (using Sync API)
  {
    name: "list_filters",
    description: "List all filters",
    inputSchema: { type: "object", properties: {} },
  },
  {
    name: "create_filter",
    description: "Create a new filter",
    inputSchema: {
      type: "object",
      properties: {
        name: { type: "string", description: "Filter name" },
        query: { type: "string", description: "Filter query" },
        color: { type: "string", description: "Color name" },
        is_favorite: { type: "boolean", description: "Mark as favorite" },
      },
      required: ["name", "query"],
    },
  },
  {
    name: "get_filter",
    description: "Get a filter by ID",
    inputSchema: {
      type: "object",
      properties: { filter_id: { type: "string", description: "Filter ID" } },
      required: ["filter_id"],
    },
  },
  {
    name: "update_filter",
    description: "Update a filter",
    inputSchema: {
      type: "object",
      properties: {
        filter_id: { type: "string", description: "Filter ID" },
        name: { type: "string", description: "New name" },
        query: { type: "string", description: "New query" },
        color: { type: "string", description: "New color" },
        is_favorite: { type: "boolean", description: "Mark as favorite" },
      },
      required: ["filter_id"],
    },
  },
  {
    name: "delete_filter",
    description: "Delete a filter",
    inputSchema: {
      type: "object",
      properties: { filter_id: { type: "string", description: "Filter ID" } },
      required: ["filter_id"],
    },
  },
];

// Tool handlers
async function handleTool(name: string, args: Record<string, any>): Promise<any> {
  switch (name) {
    // Projects
    case "list_projects":
      return apiRequest("/projects");
    case "create_project":
      return apiRequest("/projects", "POST", args);
    case "get_project":
      return apiRequest(`/projects/${args.project_id}`);
    case "update_project": {
      const { project_id, ...body } = args;
      return apiRequest(`/projects/${project_id}`, "POST", body);
    }
    case "delete_project":
      return apiRequest(`/projects/${args.project_id}`, "DELETE");

    // Sections
    case "list_sections": {
      const query = args.project_id ? `?project_id=${args.project_id}` : "";
      return apiRequest(`/sections${query}`);
    }
    case "create_section":
      return apiRequest("/sections", "POST", args);
    case "get_section":
      return apiRequest(`/sections/${args.section_id}`);
    case "update_section": {
      const { section_id, ...body } = args;
      return apiRequest(`/sections/${section_id}`, "POST", body);
    }
    case "delete_section":
      return apiRequest(`/sections/${args.section_id}`, "DELETE");

    // Tasks
    case "list_tasks": {
      if (args.filter) {
        const params = new URLSearchParams();
        params.set("query", args.filter);
        if (args.lang) params.set("lang", args.lang);
        if (args.cursor) params.set("cursor", args.cursor);
        if (args.limit !== undefined) params.set("limit", String(args.limit));
        const query = params.toString() ? `?${params.toString()}` : "";
        return apiRequest(`/tasks/filter${query}`);
      }
      const params = new URLSearchParams();
      if (args.project_id) params.set("project_id", args.project_id);
      if (args.section_id) params.set("section_id", args.section_id);
      if (args.parent_id) params.set("parent_id", args.parent_id);
      if (args.label) params.set("label", args.label);
      if (args.ids && Array.isArray(args.ids) && args.ids.length > 0) {
        params.set("ids", args.ids.join(","));
      }
      if (args.cursor) params.set("cursor", args.cursor);
      if (args.limit !== undefined) params.set("limit", String(args.limit));
      const query = params.toString() ? `?${params.toString()}` : "";
      return apiRequest(`/tasks${query}`);
    }
    case "create_task":
      return apiRequest("/tasks", "POST", args);
    case "get_task":
      return apiRequest(`/tasks/${args.task_id}`);
    case "update_task": {
      const { task_id, ...body } = args;
      return apiRequest(`/tasks/${task_id}`, "POST", body);
    }
    case "complete_task":
      return apiRequest(`/tasks/${args.task_id}/close`, "POST");
    case "reopen_task":
      return apiRequest(`/tasks/${args.task_id}/reopen`, "POST");
    case "delete_task":
      return apiRequest(`/tasks/${args.task_id}`, "DELETE");
    case "move_task": {
      const { task_id, ...body } = args;
      return apiRequest(`/tasks/${task_id}/move`, "POST", body);
    }

    // Labels
    case "list_labels":
      return apiRequest("/labels");
    case "create_label":
      return apiRequest("/labels", "POST", args);
    case "get_label":
      return apiRequest(`/labels/${args.label_id}`);
    case "update_label": {
      const { label_id, ...body } = args;
      return apiRequest(`/labels/${label_id}`, "POST", body);
    }
    case "delete_label":
      return apiRequest(`/labels/${args.label_id}`, "DELETE");

    // Comments
    case "list_comments": {
      const params = new URLSearchParams();
      if (args.task_id) params.set("task_id", args.task_id);
      if (args.project_id) params.set("project_id", args.project_id);
      return apiRequest(`/comments?${params.toString()}`);
    }
    case "create_comment":
      return apiRequest("/comments", "POST", args);
    case "get_comment":
      return apiRequest(`/comments/${args.comment_id}`);
    case "update_comment": {
      const { comment_id, ...body } = args;
      return apiRequest(`/comments/${comment_id}`, "POST", body);
    }
    case "delete_comment":
      return apiRequest(`/comments/${args.comment_id}`, "DELETE");

    // Filters (Sync API)
    case "list_filters":
      return syncRequest({ sync_token: "*", resource_types: ["filters"] });
    case "create_filter": {
      const temp_id = crypto.randomUUID();
      const uuid = crypto.randomUUID();
      const commandArgs: Record<string, any> = {
        name: args.name,
        query: args.query,
      };
      if (args.color !== undefined) commandArgs.color = args.color;
      if (args.is_favorite !== undefined)
        commandArgs.is_favorite = args.is_favorite;
      return syncRequest({
        commands: [
          {
            type: "filter_add",
            temp_id,
            uuid,
            args: commandArgs,
          },
        ],
      });
    }
    case "update_filter": {
      const uuid = crypto.randomUUID();
      const commandArgs: Record<string, any> = {
        id: args.filter_id,
      };
      if (args.name !== undefined) commandArgs.name = args.name;
      if (args.query !== undefined) commandArgs.query = args.query;
      if (args.color !== undefined) commandArgs.color = args.color;
      if (args.is_favorite !== undefined)
        commandArgs.is_favorite = args.is_favorite;
      return syncRequest({
        commands: [
          {
            type: "filter_update",
            uuid,
            args: commandArgs,
          },
        ],
      });
    }
    case "delete_filter": {
      const uuid = crypto.randomUUID();
      return syncRequest({
        commands: [
          {
            type: "filter_delete",
            uuid,
            args: { id: args.filter_id },
          },
        ],
      });
    }
    case "get_filter": {
      const listResult = await syncRequest({
        sync_token: "*",
        resource_types: ["filters"],
      });
      const filters = Array.isArray(listResult?.filters)
        ? listResult.filters
        : [];
      const match = filters.find(
        (filter: { id?: string | number }) =>
          filter.id !== undefined &&
          String(filter.id) === String(args.filter_id)
      );
      if (!match) {
        throw new Error(`Filter ${args.filter_id} not found`);
      }
      return match;
    }

    default:
      throw new Error(`Unknown tool: ${name}`);
  }
}

// Main server setup
const server = new Server(
  { name: "todoist-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools,
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  try {
    const result = await handleTool(name, args || {});
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      content: [{ type: "text", text: `Error: ${message}` }],
      isError: true,
    };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Todoist MCP server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
