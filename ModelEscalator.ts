// ModelEscalator.ts: Event-driven model escalation for OpenClaw

import { execFile } from 'child_process';
import { promisify } from 'util';

const execFileAsync = promisify(execFile);

export enum ModelTier {
  HAIKU = 'anthropic/claude-3-5-haiku-20241022',
  SONNET = 'anthropic/claude-sonnet-4-0',
  OPUS = 'anthropic/claude-opus-4-5'
}

export type ModelId = ModelTier;

export type EscalationEventType =
  | 'user_message'
  | 'assistant_message'
  | 'response'
  | 'response_error'
  | 'token_usage'
  | 'latency'
  | 'tool_result'
  | 'manual';

export interface EscalationEvent<TPayload = unknown> {
  type: EscalationEventType;
  timestamp: number;
  payload: TPayload;
  source?: string;
}

export interface ComplexitySignal {
  pattern: string | RegExp;
  weight: number;
  tierHint?: ModelTier;
  description?: string;
}

export interface EscalationThresholds {
  sonnet: number;
  opus: number;
}

export interface LatencyThresholds {
  sonnet: number;
  opus: number;
}

export interface EscalationConfig {
  tokenThresholds: EscalationThresholds;
  scoreThresholds: EscalationThresholds;
  latencyThresholds: LatencyThresholds;
  signals: ComplexitySignal[];
  rules: EscalationRule[];
  maxEscalationLevel: ModelTier;
  preserveOriginalModel: boolean;
  allowDowngrade: boolean;
  sessionStatusJson: boolean;
  sessionStatusTimeoutMs: number;
  eventWindowMs: number;
  maxEvents: number;
  tokenCounter?: (text: string) => number;
  debug: boolean;
}

export interface OpenClawUsage {
  inputTokens?: number;
  outputTokens?: number;
  totalTokens?: number;
}

export interface OpenClawToolResult {
  name: string;
  ok: boolean;
  error?: string;
  latencyMs?: number;
}

export interface OpenClawResponse {
  model?: string;
  text?: string;
  usage?: OpenClawUsage;
  latencyMs?: number;
  status?: number;
  finishReason?: string;
  error?: string;
  toolResults?: OpenClawToolResult[];
}

export interface EscalationSuggestion {
  model: ModelTier;
  score?: number;
  reasons: string[];
  priority?: number;
  triggeredBy?: string;
}

export interface EscalationDecision {
  targetModel: ModelTier;
  reasons: string[];
  applied: boolean;
  suggestion: EscalationSuggestion | null;
  event: EscalationEvent;
}

export interface EscalationRule {
  id: string;
  events: EscalationEventType[] | '*';
  description?: string;
  priority?: number;
  cooldownMs?: number;
  evaluate: (event: EscalationEvent, state: EscalationState) => EscalationSuggestion | null;
}

export interface EscalationState {
  currentModel: ModelTier;
  originalModel: ModelTier | null;
  lastDecisionAt: number | null;
  lastSwitchAt: number | null;
  recentEvents: EscalationEvent[];
  rollingScore: number;
  errorCount: number;
  toolErrorCount: number;
}

export interface SessionAdapter {
  getCurrentModel(): Promise<ModelTier | null>;
  setModel(model: ModelTier): Promise<void>;
}

export interface RunResult<T> {
  result: T;
  decision: EscalationDecision | null;
  originalModel: ModelTier;
  targetModel: ModelTier;
}

class OpenClawSessionAdapter implements SessionAdapter {
  private json: boolean;
  private timeoutMs: number;

  constructor(options: Pick<EscalationConfig, 'sessionStatusJson' | 'sessionStatusTimeoutMs'>) {
    this.json = options.sessionStatusJson;
    this.timeoutMs = options.sessionStatusTimeoutMs;
  }

  async getCurrentModel(): Promise<ModelTier | null> {
    try {
      const args = ['session_status'];
      if (this.json) {
        args.push('--json');
      }
      const { stdout } = await execFileAsync('openclaw', args, { timeout: this.timeoutMs });
      return this.parseModel(stdout);
    } catch {
      return null;
    }
  }

  async setModel(model: ModelTier): Promise<void> {
    await execFileAsync('openclaw', ['session_status', `model=${model}`], {
      timeout: this.timeoutMs
    });
  }

  private parseModel(output: string): ModelTier | null {
    const trimmed = output.trim();
    if (!trimmed) return null;

    const fromJson = this.parseJsonModel(trimmed);
    if (fromJson) return fromJson;

    const match = trimmed.match(/model\s*[:=]\s*([^\s]+)/i);
    if (match && match[1]) {
      return this.normalizeModelId(match[1]);
    }

    const directMatch = trimmed.match(/anthropic\/[^\s]+/i);
    if (directMatch) {
      return this.normalizeModelId(directMatch[0]);
    }

    return null;
  }

  private parseJsonModel(raw: string): ModelTier | null {
    try {
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== 'object') return null;

      const candidates = [
        (parsed as { model?: string }).model,
        (parsed as { current_model?: string }).current_model,
        (parsed as { active_model?: string }).active_model,
        (parsed as { session?: { model?: string } }).session?.model,
        (parsed as { config?: { model?: string } }).config?.model
      ].filter(Boolean) as string[];

      for (const candidate of candidates) {
        const normalized = this.normalizeModelId(candidate);
        if (normalized) return normalized;
      }

      return null;
    } catch {
      return null;
    }
  }

  private normalizeModelId(model: string): ModelTier | null {
    const normalized = model.trim();
    switch (normalized) {
      case ModelTier.HAIKU:
        return ModelTier.HAIKU;
      case ModelTier.SONNET:
        return ModelTier.SONNET;
      case ModelTier.OPUS:
        return ModelTier.OPUS;
      default:
        return null;
    }
  }
}

const MODEL_ORDER: ModelTier[] = [ModelTier.HAIKU, ModelTier.SONNET, ModelTier.OPUS];

const defaultSignals: ComplexitySignal[] = [
  { pattern: 'architecture', weight: 3, tierHint: ModelTier.SONNET },
  { pattern: 'system design', weight: 4, tierHint: ModelTier.OPUS },
  { pattern: 'refactor', weight: 2, tierHint: ModelTier.SONNET },
  { pattern: 'migration', weight: 3, tierHint: ModelTier.SONNET },
  { pattern: 'optimization', weight: 3, tierHint: ModelTier.SONNET },
  { pattern: 'performance', weight: 2 },
  { pattern: 'scalability', weight: 3, tierHint: ModelTier.SONNET },
  { pattern: 'security', weight: 3, tierHint: ModelTier.SONNET },
  { pattern: 'concurrency', weight: 3, tierHint: ModelTier.OPUS },
  { pattern: 'distributed', weight: 3, tierHint: ModelTier.OPUS },
  { pattern: 'algorithm', weight: 2 },
  { pattern: 'complex', weight: 1 },
  { pattern: /\bproof\b/i, weight: 2 },
  { pattern: /\bformal\b/i, weight: 2 },
  { pattern: /\bdeep learning\b/i, weight: 3, tierHint: ModelTier.OPUS },
  { pattern: /\bmachine learning\b/i, weight: 2, tierHint: ModelTier.SONNET }
];

function buildDefaultRules(config: EscalationConfig): EscalationRule[] {
  return [
    {
      id: 'token-usage',
      events: ['token_usage', 'response'],
      priority: 2,
      evaluate: (event) => {
        const payload = event.payload as { totalTokens?: number };
        const totalTokens = payload?.totalTokens ?? 0;
        if (!totalTokens) return null;

        if (totalTokens >= config.tokenThresholds.opus) {
          return {
            model: ModelTier.OPUS,
            score: 4,
            reasons: [`token_usage>=${config.tokenThresholds.opus}`],
            triggeredBy: 'token-usage'
          };
        }

        if (totalTokens >= config.tokenThresholds.sonnet) {
          return {
            model: ModelTier.SONNET,
            score: 2,
            reasons: [`token_usage>=${config.tokenThresholds.sonnet}`],
            triggeredBy: 'token-usage'
          };
        }

        return null;
      }
    },
    {
      id: 'latency-spike',
      events: ['latency', 'response'],
      priority: 1,
      evaluate: (event) => {
        const payload = event.payload as { latencyMs?: number };
        const latency = payload?.latencyMs ?? 0;
        if (!latency) return null;

        if (latency >= config.latencyThresholds.opus) {
          return {
            model: ModelTier.OPUS,
            score: 2,
            reasons: [`latency>=${config.latencyThresholds.opus}ms`],
            triggeredBy: 'latency-spike'
          };
        }

        if (latency >= config.latencyThresholds.sonnet) {
          return {
            model: ModelTier.SONNET,
            score: 1,
            reasons: [`latency>=${config.latencyThresholds.sonnet}ms`],
            triggeredBy: 'latency-spike'
          };
        }

        return null;
      }
    },
    {
      id: 'response-error',
      events: ['response_error'],
      priority: 3,
      evaluate: (event, state) => {
        const payload = event.payload as { status?: number; error?: string };
        const status = payload?.status ?? 0;
        const isServerError = status >= 500 || !!payload?.error;

        if (isServerError && state.errorCount >= 1) {
          return {
            model: ModelTier.OPUS,
            score: 3,
            reasons: ['response_error:repeat'],
            triggeredBy: 'response-error'
          };
        }

        if (isServerError) {
          return {
            model: ModelTier.SONNET,
            score: 2,
            reasons: ['response_error'],
            triggeredBy: 'response-error'
          };
        }

        return null;
      }
    },
    {
      id: 'tool-failure',
      events: ['tool_result'],
      priority: 2,
      evaluate: (event, state) => {
        const payload = event.payload as OpenClawToolResult;
        if (!payload || payload.ok) return null;

        if (state.toolErrorCount >= 1) {
          return {
            model: ModelTier.OPUS,
            score: 2,
            reasons: [`tool_error:${payload.name}`],
            triggeredBy: 'tool-failure'
          };
        }

        return {
          model: ModelTier.SONNET,
          score: 1,
          reasons: [`tool_error:${payload.name}`],
          triggeredBy: 'tool-failure'
        };
      }
    },
    {
      id: 'context-signal',
      events: ['user_message', 'assistant_message'],
      priority: 1,
      evaluate: (event) => {
        const payload = event.payload as { text?: string; score?: number; tierHints?: ModelTier[] };
        const score = payload?.score ?? 0;
        const tierHints = payload?.tierHints ?? [];
        const reasons: string[] = [];
        let target = ModelTier.HAIKU;

        if (score >= config.scoreThresholds.opus) {
          target = ModelTier.OPUS;
          reasons.push(`signal_score>=${config.scoreThresholds.opus}`);
        } else if (score >= config.scoreThresholds.sonnet) {
          target = ModelTier.SONNET;
          reasons.push(`signal_score>=${config.scoreThresholds.sonnet}`);
        }

        for (const hint of tierHints) {
          target = compareModels(hint, target) > 0 ? hint : target;
        }

        if (target === ModelTier.HAIKU) return null;

        return {
          model: target,
          score,
          reasons: reasons.length ? reasons : ['context_signals'],
          triggeredBy: 'context-signal'
        };
      }
    }
  ];
}

export class ModelEscalator {
  private config: EscalationConfig;
  private adapter: SessionAdapter;
  private state: EscalationState;
  private ruleCooldowns: Map<string, number> = new Map();

  constructor(config: Partial<EscalationConfig> = {}, adapter?: SessionAdapter) {
    this.config = {
      tokenThresholds: { sonnet: 600, opus: 1200 },
      scoreThresholds: { sonnet: 6, opus: 10 },
      latencyThresholds: { sonnet: 7000, opus: 12000 },
      signals: defaultSignals,
      rules: [],
      maxEscalationLevel: ModelTier.OPUS,
      preserveOriginalModel: true,
      allowDowngrade: true,
      sessionStatusJson: true,
      sessionStatusTimeoutMs: 5000,
      eventWindowMs: 5 * 60 * 1000,
      maxEvents: 200,
      debug: false,
      ...config
    };

    if (!config.rules || !config.rules.length) {
      this.config.rules = buildDefaultRules(this.config);
    }

    this.adapter = adapter ?? new OpenClawSessionAdapter(this.config);

    this.state = {
      currentModel: ModelTier.HAIKU,
      originalModel: null,
      lastDecisionAt: null,
      lastSwitchAt: null,
      recentEvents: [],
      rollingScore: 0,
      errorCount: 0,
      toolErrorCount: 0
    };

    if (this.config.debug) {
      this.logDebug('ModelEscalator initialized', { config: this.config });
    }
  }

  async handleEvent(event: EscalationEvent): Promise<EscalationDecision | null> {
    this.recordEvent(event);
    this.updateCounters(event);

    const suggestions = this.evaluateRules(event);
    if (!suggestions.length) return null;

    const suggestion = this.pickSuggestion(suggestions);
    if (!suggestion) return null;

    const original = await this.getOriginalModel();
    const target = this.decideTargetModel(suggestion.model, original);
    const applied = target !== this.state.currentModel;

    if (applied) {
      await this.switchModel(target);
    }

    const decision: EscalationDecision = {
      targetModel: target,
      reasons: suggestion.reasons,
      applied,
      suggestion,
      event
    };

    this.state.lastDecisionAt = Date.now();
    return decision;
  }

  async ingestOpenClawResponse(response: OpenClawResponse): Promise<EscalationDecision | null> {
    const events = this.buildEventsFromResponse(response);
    let decision: EscalationDecision | null = null;

    for (const event of events) {
      const result = await this.handleEvent(event);
      if (result) {
        decision = this.pickStrongerDecision(decision, result);
      }
    }

    return decision;
  }

  async observeMessage(role: 'user' | 'assistant', text: string): Promise<EscalationDecision | null> {
    const assessment = this.assessContext(text);
    const event: EscalationEvent = {
      type: role === 'user' ? 'user_message' : 'assistant_message',
      timestamp: Date.now(),
      payload: { text, ...assessment },
      source: role
    };

    return this.handleEvent(event);
  }

  async runWithEscalation<T>(context: string, fn: () => Promise<T>): Promise<RunResult<T>> {
    const original = await this.getOriginalModel();
    const decision = await this.observeMessage('user', context);
    const target = decision?.targetModel ?? original;

    try {
      const result = await fn();
      return { result, decision, originalModel: original, targetModel: target };
    } finally {
      if (this.config.preserveOriginalModel && this.state.currentModel !== original) {
        await this.switchModel(original);
      }
    }
  }

  registerRule(rule: EscalationRule): void {
    this.config.rules = [...this.config.rules, rule];
  }

  removeRule(ruleId: string): void {
    this.config.rules = this.config.rules.filter((rule) => rule.id !== ruleId);
  }

  listRules(): EscalationRule[] {
    return [...this.config.rules];
  }

  updateConfig(partial: Partial<EscalationConfig>): void {
    this.config = { ...this.config, ...partial };
  }

  getConfig(): EscalationConfig {
    return { ...this.config };
  }

  async getCurrentModel(): Promise<ModelTier> {
    const sessionModel = await this.adapter.getCurrentModel();
    if (sessionModel) {
      this.state.currentModel = sessionModel;
      return sessionModel;
    }
    return this.state.currentModel;
  }

  async switchModel(model: ModelTier): Promise<void> {
    if (this.config.debug) {
      this.logDebug('Switching model via session_status', { model });
    }
    await this.adapter.setModel(model);
    this.state.currentModel = model;
    this.state.lastSwitchAt = Date.now();
  }

  private assessContext(text: string): { tokenCount: number; score: number; tierHints: ModelTier[] } {
    const tokenCount = this.countTokens(text);
    const lower = text.toLowerCase();
    let score = 0;
    const tierHints: ModelTier[] = [];

    if (tokenCount >= this.config.tokenThresholds.opus) {
      score += 4;
    } else if (tokenCount >= this.config.tokenThresholds.sonnet) {
      score += 2;
    }

    for (const signal of this.config.signals) {
      const matchCount = this.countSignalMatches(signal, lower);
      if (matchCount > 0) {
        score += signal.weight * matchCount;
        if (signal.tierHint) tierHints.push(signal.tierHint);
      }
    }

    return { tokenCount, score, tierHints };
  }

  private buildEventsFromResponse(response: OpenClawResponse): EscalationEvent[] {
    const now = Date.now();
    const events: EscalationEvent[] = [];

    events.push({
      type: 'response',
      timestamp: now,
      payload: {
        model: response.model,
        latencyMs: response.latencyMs,
        totalTokens: response.usage?.totalTokens
      },
      source: 'openclaw'
    });

    if (response.text) {
      events.push({
        type: 'assistant_message',
        timestamp: now,
        payload: { text: response.text, ...this.assessContext(response.text) },
        source: 'openclaw'
      });
    }

    if (response.usage?.totalTokens) {
      events.push({
        type: 'token_usage',
        timestamp: now,
        payload: { totalTokens: response.usage.totalTokens },
        source: 'openclaw'
      });
    }

    if (response.latencyMs) {
      events.push({
        type: 'latency',
        timestamp: now,
        payload: { latencyMs: response.latencyMs },
        source: 'openclaw'
      });
    }

    if (response.error || (response.status && response.status >= 400)) {
      events.push({
        type: 'response_error',
        timestamp: now,
        payload: { status: response.status, error: response.error },
        source: 'openclaw'
      });
    }

    if (response.toolResults?.length) {
      for (const toolResult of response.toolResults) {
        events.push({
          type: 'tool_result',
          timestamp: now,
          payload: toolResult,
          source: toolResult.name
        });
      }
    }

    return events;
  }

  private evaluateRules(event: EscalationEvent): EscalationSuggestion[] {
    const suggestions: EscalationSuggestion[] = [];

    for (const rule of this.config.rules) {
      if (!this.ruleApplies(rule, event.type)) continue;
      if (!this.cooldownPassed(rule)) continue;

      const suggestion = rule.evaluate(event, this.state);
      if (suggestion) {
        suggestions.push({
          ...suggestion,
          priority: suggestion.priority ?? rule.priority ?? 0
        });
        this.ruleCooldowns.set(rule.id, Date.now());
      }
    }

    return suggestions;
  }

  private pickSuggestion(suggestions: EscalationSuggestion[]): EscalationSuggestion | null {
    if (!suggestions.length) return null;

    return suggestions.reduce((best, current) => {
      if (!best) return current;

      const modelDelta = compareModels(current.model, best.model);
      if (modelDelta !== 0) return modelDelta > 0 ? current : best;

      const priorityDelta = (current.priority ?? 0) - (best.priority ?? 0);
      if (priorityDelta !== 0) return priorityDelta > 0 ? current : best;

      const scoreDelta = (current.score ?? 0) - (best.score ?? 0);
      return scoreDelta > 0 ? current : best;
    }, suggestions[0]);
  }

  private pickStrongerDecision(
    current: EscalationDecision | null,
    next: EscalationDecision
  ): EscalationDecision {
    if (!current) return next;

    const modelDelta = compareModels(next.targetModel, current.targetModel);
    if (modelDelta > 0) return next;
    if (modelDelta < 0) return current;

    if (next.reasons.length > current.reasons.length) return next;
    return current;
  }

  private ruleApplies(rule: EscalationRule, type: EscalationEventType): boolean {
    if (rule.events === '*') return true;
    return rule.events.includes(type);
  }

  private cooldownPassed(rule: EscalationRule): boolean {
    if (!rule.cooldownMs) return true;
    const last = this.ruleCooldowns.get(rule.id);
    if (!last) return true;
    return Date.now() - last >= rule.cooldownMs;
  }

  private recordEvent(event: EscalationEvent): void {
    this.state.recentEvents.push(event);
    const cutoff = Date.now() - this.config.eventWindowMs;

    this.state.recentEvents = this.state.recentEvents.filter(
      (stored) => stored.timestamp >= cutoff
    );

    if (this.state.recentEvents.length > this.config.maxEvents) {
      this.state.recentEvents = this.state.recentEvents.slice(-this.config.maxEvents);
    }
  }

  private updateCounters(event: EscalationEvent): void {
    if (event.type === 'response_error') {
      this.state.errorCount += 1;
    }
    if (event.type === 'tool_result') {
      const payload = event.payload as OpenClawToolResult;
      if (payload && !payload.ok) {
        this.state.toolErrorCount += 1;
      }
    }
  }

  private decideTargetModel(recommended: ModelTier, original: ModelTier): ModelTier {
    let target = recommended;

    if (!this.config.allowDowngrade) {
      target = compareModels(target, original) > 0 ? target : original;
    }

    return this.clampToMax(target);
  }

  private async getOriginalModel(): Promise<ModelTier> {
    if (this.state.originalModel) return this.state.originalModel;

    const sessionModel = await this.adapter.getCurrentModel();
    this.state.originalModel = sessionModel ?? this.state.currentModel;
    this.state.currentModel = this.state.originalModel;
    return this.state.originalModel;
  }

  private clampToMax(model: ModelTier): ModelTier {
    return compareModels(model, this.config.maxEscalationLevel) > 0
      ? this.config.maxEscalationLevel
      : model;
  }

  private countTokens(text: string): number {
    if (this.config.tokenCounter) {
      return this.config.tokenCounter(text);
    }
    return text.trim().split(/\s+/).filter(Boolean).length;
  }

  private countSignalMatches(signal: ComplexitySignal, context: string): number {
    if (typeof signal.pattern === 'string') {
      return context.includes(signal.pattern.toLowerCase()) ? 1 : 0;
    }

    const regex = new RegExp(
      signal.pattern.source,
      signal.pattern.flags.includes('g') ? signal.pattern.flags : `${signal.pattern.flags}g`
    );
    const matches = context.match(regex);
    return matches ? matches.length : 0;
  }

  private logDebug(message: string, meta: Record<string, unknown>): void {
    // eslint-disable-next-line no-console
    console.log(`[ModelEscalator] ${message}`, meta);
  }
}

function compareModels(a: ModelTier, b: ModelTier): number {
  return MODEL_ORDER.indexOf(a) - MODEL_ORDER.indexOf(b);
}

export default ModelEscalator;
