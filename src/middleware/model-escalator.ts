import { 
  EscalationConfig, 
  EscalationSessionState,
  EscalationDecision,
  ComplexityScore
} from '../types/escalator';
import { ComplexityAnalyzer } from './complexity-analyzer';
import { ModelResolver } from './model-resolver';
import { OpenClawMiddleware, Request, Response, NextFunction } from 'openclaw/types';

export class ModelEscalator implements OpenClawMiddleware {
  private complexityAnalyzer: ComplexityAnalyzer;
  private config: EscalationConfig;

  constructor(config?: Partial<EscalationConfig>) {
    this.complexityAnalyzer = new ComplexityAnalyzer();
    
    // Default configuration with sensible defaults
    this.config = {
      baseModel: 'anthropic/claude-3-haiku-20240307',
      escalationModels: [
        'anthropic/claude-3-haiku-20240307',
        'anthropic/claude-3-5-sonnet-20241022',
        'anthropic/claude-opus-4-5'
      ],
      escalationThresholds: {
        complexity: 60,
        cognitive_load: 50,
        technical_depth: 55
      },
      de_escalation_hysteresis: 20 // Prevent rapid oscillation
    };

    // Merge provided configuration
    if (config) {
      this.config = { ...this.config, ...config };
    }
  }

  /**
   * Main middleware method to intercept and potentially escalate model
   */
  async handle(req: Request, res: Response, next: NextFunction) {
    // Retrieve or initialize session state
    const sessionState = this.getSessionState(req);

    // Analyze conversation complexity
    const conversationHistory = this.extractConversationHistory(req);
    const complexityScore = this.complexityAnalyzer.analyzeComplexity(conversationHistory);

    // Determine escalation decision
    const escalationDecision = await this.decideModelEscalation(
      sessionState, 
      complexityScore
    );

    // Apply model escalation if needed
    if (escalationDecision.shouldEscalate && escalationDecision.targetModel) {
      req.modelId = escalationDecision.targetModel;
      sessionState.currentModel = escalationDecision.targetModel;
      sessionState.previousModels.push(escalationDecision.targetModel);
    }

    // Update session state
    this.updateSessionState(req, sessionState, complexityScore);

    next();
  }

  /**
   * Determine if model escalation is necessary
   */
  private async decideModelEscalation(
    sessionState: EscalationSessionState, 
    complexityScore: ComplexityScore
  ): Promise<EscalationDecision> {
    // Check if complexity exceeds thresholds
    const isComplexityHigh = 
      complexityScore.overall > this.config.escalationThresholds.complexity ||
      complexityScore.technical_depth > this.config.escalationThresholds.technical_depth ||
      complexityScore.cognitive_load > this.config.escalationThresholds.cognitive_load;

    // Prevent oscillation with hysteresis
    const timeSinceLastEscalation = Date.now() - sessionState.lastEscalationTimestamp;
    const hysteresisPeriod = 5 * 60 * 1000; // 5 minutes
    
    if (!isComplexityHigh || timeSinceLastEscalation < hysteresisPeriod) {
      return { shouldEscalate: false };
    }

    // Resolve next model in escalation chain
    const nextModel = await ModelResolver.resolveNextModel(
      sessionState.currentModel, 
      this.config
    );

    // If next model is different from current, escalate
    if (nextModel !== sessionState.currentModel) {
      return {
        shouldEscalate: true,
        targetModel: nextModel,
        reason: 'High complexity detected'
      };
    }

    return { shouldEscalate: false };
  }

  /**
   * Extract conversation history from request
   */
  private extractConversationHistory(req: Request): string[] {
    // Implementation depends on OpenClaw's session management
    // This is a placeholder - adapt to actual OpenClaw conversation tracking
    return req.conversationHistory || [];
  }

  /**
   * Retrieve or initialize session state
   */
  private getSessionState(req: Request): EscalationSessionState {
    if (!req.sessionState) {
      req.sessionState = {
        currentModel: this.config.baseModel,
        previousModels: [],
        lastEscalationTimestamp: 0,
        complexityHistory: [],
        tokenUsageHistory: []
      };
    }
    return req.sessionState as EscalationSessionState;
  }

  /**
   * Update session state with latest complexity information
   */
  private updateSessionState(
    req: Request, 
    sessionState: EscalationSessionState, 
    complexityScore: ComplexityScore
  ) {
    // Add complexity score to history
    sessionState.complexityHistory.push(complexityScore);

    // Trim history to prevent unbounded growth
    if (sessionState.complexityHistory.length > 50) {
      sessionState.complexityHistory.shift();
    }

    // Update token usage (placeholder - replace with actual token tracking)
    sessionState.tokenUsageHistory.push({
      modelId: req.modelId || this.config.baseModel,
      inputTokens: req.inputTokens || 0,
      outputTokens: req.outputTokens || 0,
      timestamp: Date.now()
    });

    // Trim token usage history
    if (sessionState.tokenUsageHistory.length > 100) {
      sessionState.tokenUsageHistory.shift();
    }
  }
}