import { execFileSync, execSync } from "node:child_process";
import path from "node:path";
type PluginCfg = {
  thanosRoot?: string;
  pythonBin?: string;
  timeoutMs?: number;
  allowLlmCapture?: boolean;
  quietMode?: boolean;
  streaming?: boolean;
};

function resolveThanosRoot(api: any, cfg: PluginCfg): string {
  return (
    (typeof cfg.thanosRoot === "string" && cfg.thanosRoot.trim()) ||
    (typeof api.config?.agents?.defaults?.workspace === "string" &&
      api.config?.agents?.defaults?.workspace.trim()) ||
    process.cwd()
  );
}

function resolvePythonBin(cfg: PluginCfg): string {
  return (typeof cfg.pythonBin === "string" && cfg.pythonBin.trim()) || "python3";
}

function runThanosRoute(
  api: any,
  params: Record<string, unknown>,
): { content: string; usage?: unknown; capture?: unknown } {
  const pluginCfg = (api.pluginConfig ?? {}) as PluginCfg;
  const thanosRoot = resolveThanosRoot(api, pluginCfg);
  const pythonBin = resolvePythonBin(pluginCfg);
  const timeoutMs =
    typeof pluginCfg.timeoutMs === "number" && pluginCfg.timeoutMs > 0
      ? pluginCfg.timeoutMs
      : 30_000;

  const payload = {
    message: typeof params.message === "string" ? params.message : "",
    session_id: typeof params.sessionId === "string" ? params.sessionId : undefined,
    context: typeof params.context === "object" && params.context ? params.context : {},
    source: typeof params.source === "string" ? params.source : "openclaw",
    allow_llm_capture:
      typeof params.allowLlmCapture === "boolean"
        ? params.allowLlmCapture
        : Boolean(pluginCfg.allowLlmCapture),
  };

  const scriptPath = path.join(thanosRoot, "Tools", "openclaw_cli.py");
  const quietMode = pluginCfg.quietMode !== false; // Default to quiet
  const streaming = pluginCfg.streaming === true; // Default to no streaming
  const stdout = execFileSync(pythonBin, [scriptPath, "route"], {
    cwd: thanosRoot,
    timeout: timeoutMs,
    encoding: "utf-8",
    input: JSON.stringify(payload),
    env: {
      ...process.env,
      PATH: process.env.PATH ?? "",
      THANOS_QUIET_MODE: quietMode ? "1" : "0",
      THANOS_STREAMING: streaming ? "1" : "0",
      THANOS_SHOW_THINKING: "0",
    },
  });

  const parsed = JSON.parse(stdout);
  return {
    content: typeof parsed.content === "string" ? parsed.content : "",
    usage: parsed.usage,
    capture: parsed.capture,
  };
}

// RAG CLI wrapper functions
const NOTEBOOKS = ["orders_hod", "versacare", "drive_inbox", "harry", "ncdhhs_radiology", "ncdhhs_radiology_pdf"] as const;
type NotebookKey = typeof NOTEBOOKS[number];

const NOTEBOOK_ALIASES: Record<string, NotebookKey> = {
  // NCDHHS/Radiology -> ncdhhs_radiology_pdf (has 28 files, ncdhhs_radiology is empty)
  "ncdhhs": "ncdhhs_radiology_pdf",
  "nc dhhs": "ncdhhs_radiology_pdf",
  "radiology": "ncdhhs_radiology_pdf",
  "ncdhhs_radiology": "ncdhhs_radiology_pdf",
  "ncdhhs_radiology_pdf": "ncdhhs_radiology_pdf",

  // Orders/HOD -> orders_hod (has 6 files)
  "orders": "orders_hod",
  "hod": "orders_hod",
  "epic orders": "orders_hod",
  "epic": "orders_hod",
  "orders_hod": "orders_hod",

  // VersaCare aliases (0 files currently - will fail gracefully)
  "versacare": "versacare",
  "scottcare": "versacare",
  "kentucky": "versacare",
  "ky": "versacare",

  // Drive inbox (0 files currently)
  "inbox": "drive_inbox",
  "drive inbox": "drive_inbox",
  "drive_inbox": "drive_inbox",

  // Harry (0 files currently)
  "harry": "harry",
};

function normalizeNotebook(input: string): NotebookKey | null {
  const normalized = input.toLowerCase().trim().replace(/[-_\s]+/g, " ");
  if (NOTEBOOK_ALIASES[normalized]) return NOTEBOOK_ALIASES[normalized];
  // Try direct match
  if (NOTEBOOKS.includes(normalized as NotebookKey)) return normalized as NotebookKey;
  // Fuzzy match
  for (const [alias, key] of Object.entries(NOTEBOOK_ALIASES)) {
    if (normalized.includes(alias) || alias.includes(normalized)) return key;
  }
  return null;
}

function runRagCli(api: any, args: string[]): string {
  const pluginCfg = (api.pluginConfig ?? {}) as PluginCfg;
  const thanosRoot = resolveThanosRoot(api, pluginCfg);
  const scriptPath = path.join(thanosRoot, "scripts", "rag-cli.sh");

  try {
    const result = execSync(`bash "${scriptPath}" ${args.map(a => `"${a}"`).join(" ")}`, {
      cwd: thanosRoot,
      encoding: "utf-8",
      timeout: 120_000,
      env: {
        ...process.env,
        PATH: process.env.PATH ?? "",
      },
    });
    return result.trim();
  } catch (err: any) {
    return `Error: ${err.message || err}`;
  }
}

export default function register(api: any) {
  api.registerTool({
    name: "thanos_route",
    description:
      "Route a message through the Thanos orchestrator (OpenClaw harness) and return the response.",
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: {
        message: { type: "string" },
        sessionId: { type: "string" },
        context: { type: "object" },
        source: { type: "string" },
        allowLlmCapture: { type: "boolean" },
      },
      required: ["message"],
    },
    async execute(_id, params) {
      const result = runThanosRoute(api, params);
      return {
        content: [{ type: "text", text: result.content }],
        data: { capture: result.capture, usage: result.usage },
      };
    },
  });

  api.registerCommand({
    name: "thanos",
    description: "Route a message through Thanos orchestrator.",
    acceptsArgs: true,
    requireAuth: true,
    async handler(ctx) {
      const result = runThanosRoute(api, { message: ctx.args ?? "" });
      return { content: [{ type: "text", text: result.content }] };
    },
  });

  // RAG Tools - Direct execution without AI interpretation
  api.registerTool({
    name: "rag_sync",
    description: "Sync a Google Drive folder to an OpenAI vector store. Use this to ingest documents.",
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: {
        notebook: {
          type: "string",
          description: "Notebook key or alias (e.g., 'ncdhhs', 'orders', 'versacare', 'inbox', 'harry')",
        },
      },
      required: ["notebook"],
    },
    async execute(_id: unknown, params: { notebook: string }) {
      const key = normalizeNotebook(params.notebook);
      if (!key) {
        return {
          content: [{ type: "text", text: `Unknown notebook: "${params.notebook}". Available: ${NOTEBOOKS.join(", ")}` }],
        };
      }
      const result = runRagCli(api, ["sync", key]);
      return { content: [{ type: "text", text: result }] };
    },
  });

  api.registerTool({
    name: "rag_query",
    description: "Query a vector store with a natural language question. Returns semantically relevant results.",
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: {
        notebook: {
          type: "string",
          description: "Notebook key or alias (e.g., 'ncdhhs', 'orders', 'versacare', 'inbox', 'harry')",
        },
        question: {
          type: "string",
          description: "Natural language question to search for",
        },
      },
      required: ["notebook", "question"],
    },
    async execute(_id: unknown, params: { notebook: string; question: string }) {
      const key = normalizeNotebook(params.notebook);
      if (!key) {
        return {
          content: [{ type: "text", text: `Unknown notebook: "${params.notebook}". Available: ${NOTEBOOKS.join(", ")}` }],
        };
      }
      const result = runRagCli(api, ["query", key, params.question]);
      return { content: [{ type: "text", text: result }] };
    },
  });

  api.registerTool({
    name: "rag_list",
    description: "List all available RAG notebooks and their status.",
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: {},
    },
    async execute() {
      const result = runRagCli(api, ["list"]);
      return { content: [{ type: "text", text: result }] };
    },
  });

  api.registerTool({
    name: "rag_upload",
    description: "Upload a local file to a vector store.",
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: {
        notebook: {
          type: "string",
          description: "Notebook key or alias",
        },
        filepath: {
          type: "string",
          description: "Path to the local file to upload",
        },
      },
      required: ["notebook", "filepath"],
    },
    async execute(_id: unknown, params: { notebook: string; filepath: string }) {
      const key = normalizeNotebook(params.notebook);
      if (!key) {
        return {
          content: [{ type: "text", text: `Unknown notebook: "${params.notebook}". Available: ${NOTEBOOKS.join(", ")}` }],
        };
      }
      const result = runRagCli(api, ["upload", key, params.filepath]);
      return { content: [{ type: "text", text: result }] };
    },
  });

  // RAG Commands for direct CLI usage
  api.registerCommand({
    name: "rag",
    description: "RAG operations: sync, query, list, upload. Usage: /rag sync ncdhhs | /rag query orders 'question' | /rag list",
    acceptsArgs: true,
    requireAuth: true,
    async handler(ctx) {
      const args = (ctx.args ?? "").trim().split(/\s+/);
      const cmd = args[0]?.toLowerCase();

      if (!cmd || cmd === "help") {
        return {
          content: [{
            type: "text",
            text: `RAG CLI - OpenAI File Search Interface

Usage:
  /rag sync <notebook>              Sync Google Drive to vector store
  /rag query <notebook> "question"  Query the vector store
  /rag list                         List all notebooks
  /rag upload <notebook> <file>     Upload a file to vector store

Notebooks: ${NOTEBOOKS.join(", ")}
Aliases: ncdhhs, orders, versacare, inbox, harry, epic, ky, scottcare`,
          }],
        };
      }

      if (cmd === "list" || cmd === "ls") {
        const result = runRagCli(api, ["list"]);
        return { content: [{ type: "text", text: result }] };
      }

      if (cmd === "sync") {
        const notebook = args[1] || "drive_inbox";
        const key = normalizeNotebook(notebook);
        if (!key) {
          return { content: [{ type: "text", text: `Unknown notebook: "${notebook}". Available: ${NOTEBOOKS.join(", ")}` }] };
        }
        const result = runRagCli(api, ["sync", key]);
        return { content: [{ type: "text", text: result }] };
      }

      if (cmd === "query" || cmd === "q") {
        const notebook = args[1];
        const question = args.slice(2).join(" ").replace(/^["']|["']$/g, "");
        if (!notebook || !question) {
          return { content: [{ type: "text", text: "Usage: /rag query <notebook> \"question\"" }] };
        }
        const key = normalizeNotebook(notebook);
        if (!key) {
          return { content: [{ type: "text", text: `Unknown notebook: "${notebook}". Available: ${NOTEBOOKS.join(", ")}` }] };
        }
        const result = runRagCli(api, ["query", key, question]);
        return { content: [{ type: "text", text: result }] };
      }

      if (cmd === "upload") {
        const notebook = args[1];
        const filepath = args[2];
        if (!notebook || !filepath) {
          return { content: [{ type: "text", text: "Usage: /rag upload <notebook> <filepath>" }] };
        }
        const key = normalizeNotebook(notebook);
        if (!key) {
          return { content: [{ type: "text", text: `Unknown notebook: "${notebook}". Available: ${NOTEBOOKS.join(", ")}` }] };
        }
        const result = runRagCli(api, ["upload", key, filepath]);
        return { content: [{ type: "text", text: result }] };
      }

      return { content: [{ type: "text", text: `Unknown command: ${cmd}. Use /rag help for usage.` }] };
    },
  });
}
