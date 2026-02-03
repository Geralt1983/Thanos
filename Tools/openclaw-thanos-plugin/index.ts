import { execFileSync } from "node:child_process";
import path from "node:path";
type PluginCfg = {
  thanosRoot?: string;
  pythonBin?: string;
  timeoutMs?: number;
  allowLlmCapture?: boolean;
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
  const stdout = execFileSync(pythonBin, [scriptPath, "route"], {
    cwd: thanosRoot,
    timeout: timeoutMs,
    encoding: "utf-8",
    input: JSON.stringify(payload),
    env: {
      ...process.env,
      PATH: process.env.PATH ?? "",
    },
  });

  const parsed = JSON.parse(stdout);
  return {
    content: typeof parsed.content === "string" ? parsed.content : "",
    usage: parsed.usage,
    capture: parsed.capture,
  };
}

export default function register(api: any) {
  api.registerTool({
    name: "thanos.route",
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
}
