import { ModelConfig } from 'openclaw/types';

/**
 * Complexity scoring for conversation analysis
 */
export interface ComplexityScore {
  overall: number;        // 0-100 scale of conversation complexity
  cognitive_load: number; // Mental effort required
  technical_depth: number; // Depth of technical content
  creativity_level: number; // Level of creative/generative thinking needed
}

/**
 * Model availability and capability information
 */
export interface ModelAvailability {
  modelId: string;
  available: boolean;
  maxTokens: number;
  costPer1kInputTokens: number;
  costPer1kOutputTokens: number;
  lastAvailabilityCheck: number;
}

/**
 * Escalation configuration for model selection
 */
export interface EscalationConfig {
  baseModel: string;
  escalationThresholds: {
    complexity: number;
    cognitive_load: number;
    technical_depth: number;
  };
  escalationModels: string[];
  de_escalation_hysteresis: number;
}

/**
 * Session state for model escalation tracking
 */
export interface EscalationSessionState {
  currentModel: string;
  previousModels: string[];
  lastEscalationTimestamp: number;
  complexityHistory: ComplexityScore[];
  tokenUsageHistory: {
    modelId: string;
    inputTokens: number;
    outputTokens: number;
    timestamp: number;
  }[];
}

/**
 * Escalation decision payload
 */
export interface EscalationDecision {
  shouldEscalate: boolean;
  targetModel?: string;
  reason?: string;
}