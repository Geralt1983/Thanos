import { Plugin, PluginContext } from 'openclaw';
import { MemoryCaptureConfig, MemoryCaptureConfigSchema } from './schema';
import { spawn } from 'child_process';
import { existsSync } from 'fs';
import { join } from 'path';

type MessageContext = {
  session?: { id?: string };
  message?: { content?: unknown };
  response?: { content?: unknown };
  context?: { cwd?: string };
};

function normalizeContent(value: unknown): string {
  if (!value) return '';
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) {
    return value
      .map((item) => {
        if (typeof item === 'string') return item;
        if (typeof item === 'object' && item && 'text' in item) {
          return String((item as { text?: string }).text || '');
        }
        return '';
      })
      .filter(Boolean)
      .join('\n');
  }
  if (typeof value === 'object' && value && 'text' in value) {
    return String((value as { text?: string }).text || '');
  }
  return String(value);
}

function shouldCapture(text: string): boolean {
  const lower = text.toLowerCase();
  const keywords = [
    'decided', 'decision', 'chose', 'will use', 'fixed', 'resolved',
    'pattern', 'lesson', 'insight', 'root cause', 'bug', 'issue', 'plan',
    'commit', 'remember to', 'need to', 'must', 'should'
  ];
  return keywords.some((k) => lower.includes(k));
}

export class MemoryCapturePlugin implements Plugin {
  static metadata = {
    name: 'memory-capture',
    version: '1.0.0',
    description: 'Routes session learnings to Memory V2 + ByteRover',
    author: 'OpenClaw Team',
    dependencies: ['session']
  };

  private config: MemoryCaptureConfig;
  private lastCaptureBySession = new Map<string, number>();

  async init(context: PluginContext) {
    this.config = context.config.get(
      'session.memoryCapture',
      MemoryCaptureConfigSchema.parse({})
    );

    if (!this.config.enabled) return;

    // Best-effort: hook into post-processing events (if provided by OpenClaw)
    context.events.on('message:after-process', this.onAfterMessage.bind(this));
    context.events.on('message:after', this.onAfterMessage.bind(this));
  }

  private onAfterMessage(messageContext: MessageContext) {
    try {
      if (!this.config.enabled) return;

      const userText = normalizeContent(messageContext?.message?.content);
      const assistantText = normalizeContent(messageContext?.response?.content);
      const combined = `User: ${userText}\n\nAssistant: ${assistantText}`.trim();

      if (!combined || combined.length < this.config.minChars) return;
      if (!shouldCapture(combined)) return;

      const sessionId = messageContext?.session?.id || 'openclaw';
      const last = this.lastCaptureBySession.get(sessionId) || 0;
      const now = Date.now();
      if (now - last < this.config.minIntervalSeconds * 1000) return;
      this.lastCaptureBySession.set(sessionId, now);

      const payload = {
        session_id: sessionId,
        content: combined,
        cwd: messageContext?.context?.cwd || process.cwd(),
        allow_llm: this.config.allowLLM,
        source: this.config.source
      };

      const encoded = Buffer.from(JSON.stringify(payload)).toString('base64');

      const pythonCode = [
        'import os, json, base64',
        'from Tools.memory_capture_router import capture_from_text',
        'from Tools.session_discovery import infer_project_client',
        'payload = json.loads(base64.b64decode(os.environ.get("MEMORY_CAPTURE_PAYLOAD","")).decode("utf-8"))',
        'cwd = payload.get("cwd") or os.getcwd()',
        'project, client = infer_project_client(cwd)',
        'context = {"project": project, "client": client}',
        'capture_from_text(payload.get("content",""), context, payload.get("session_id","openclaw"), '
          + 'source=payload.get("source","openclaw_plugin"), allow_llm=payload.get("allow_llm", False))'
      ].join('; ');

      const venvPython = join(process.cwd(), '.venv', 'bin', 'python');
      const pythonExe = existsSync(venvPython) ? venvPython : 'python3';

      const child = spawn(pythonExe, ['-c', pythonCode], {
        cwd: process.cwd(),
        env: {
          ...process.env,
          MEMORY_CAPTURE_PAYLOAD: encoded,
          MEMORY_CAPTURE_DISABLE_MEM0: this.config.disableMem0 ? '1' : '0',
          MEMORY_CAPTURE_EMBED_TIMEOUT: String(this.config.embedTimeoutSeconds),
          MEMORY_CAPTURE_SKIP_BRV: this.config.skipByterover ? '1' : '0'
        },
        stdio: 'ignore'
      });

      // Safety: kill if it hangs
      const killTimer = setTimeout(() => child.kill('SIGKILL'), 8000);
      child.on('exit', () => clearTimeout(killTimer));
    } catch {
      // Fail silently - this should never block OpenClaw.
    }
  }

  static extendSchema(baseSchema: any) {
    return baseSchema.extend({
      memoryCapture: MemoryCaptureConfigSchema
    });
  }
}

export default MemoryCapturePlugin;
