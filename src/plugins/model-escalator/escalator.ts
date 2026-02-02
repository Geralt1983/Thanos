import { ComplexityAnalyzer } from './complexity';
import { ModelEscalatorConfig } from './schema';

export class ModelEscalator {
  private config: ModelEscalatorConfig;
  private lastEscalationTimestamp: number = 0;
  private currentModelIndex: number = 0;
  private stabilityTracker: number[] = [];

  constructor(config: ModelEscalatorConfig) {
    this.config = config;
  }

  // Determine if a model switch is necessary
  shouldEscalateModel(conversationContext: any): boolean {
    if (!this.config.enabled) return false;

    const now = Date.now() / 1000;

    // Check cooldown period
    if (now - this.lastEscalationTimestamp < this.config.hysteresis.cooldownSeconds) {
      return false;
    }

    // Analyze complexity
    const complexityScore = ComplexityAnalyzer.analyzeComplexity(conversationContext);
    const tokenUsage = conversationContext.tokenUsage?.total || 0;
    const estimatedCost = conversationContext.tokenUsage?.cost || 0;

    // Check complexity thresholds
    if (complexityScore >= this.config.complexityThresholds.high) {
      return this.escalateModel();
    }

    // Check token usage thresholds
    if (tokenUsage >= this.config.tokenThresholds.hard) {
      return this.escalateModel();
    }

    // Check cost thresholds
    if (estimatedCost >= this.config.costThresholds.hard) {
      return this.escalateModel();
    }

    return false;
  }

  // Perform model escalation
  private escalateModel(): boolean {
    // Can't escalate further if at the top of the hierarchy
    if (this.currentModelIndex >= this.config.modelHierarchy.length - 1) {
      return false;
    }

    this.currentModelIndex++;
    this.lastEscalationTimestamp = Date.now() / 1000;
    
    // Track model stability
    this.stabilityTracker.push(this.lastEscalationTimestamp);
    this.pruneStabilityTracker();

    return true;
  }

  // Attempt de-escalation if conditions are met
  shouldDeescalateModel(conversationContext: any): boolean {
    const now = Date.now() / 1000;

    // Can't de-escalate if already at the lowest model
    if (this.currentModelIndex <= 0) return false;

    // Check stability window
    const stabilityPeriod = now - this.stabilityTracker[0];
    if (stabilityPeriod < this.config.hysteresis.stabilityWindow) {
      return false;
    }

    // Analyze complexity
    const complexityScore = ComplexityAnalyzer.analyzeComplexity(conversationContext);
    const tokenUsage = conversationContext.tokenUsage?.total || 0;

    // De-escalate if complexity is low and we've been stable
    if (complexityScore <= this.config.complexityThresholds.low && 
        tokenUsage <= this.config.tokenThresholds.soft) {
      this.currentModelIndex--;
      return true;
    }

    return false;
  }

  // Get the current model
  getCurrentModel(): string {
    return this.config.modelHierarchy[this.currentModelIndex];
  }

  // Prune stability tracker to prevent memory growth
  private pruneStabilityTracker() {
    const now = Date.now() / 1000;
    this.stabilityTracker = this.stabilityTracker.filter(
      timestamp => now - timestamp < this.config.hysteresis.cooldownSeconds
    );
  }
}