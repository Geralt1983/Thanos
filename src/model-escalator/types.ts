import { ModelConfig } from '../core/config';

export interface ModelComplexityScore {
  score: number;
  factors: {
    tokenCount: number;
    contextDepth: number;
    semanticComplexity: number;
    languageSpecificity: number;
  };
}

export interface ModelEscalatorPlugin {
  name: string;
  analyze(input: string): Promise<ModelComplexityScore>;
  selectAppropriateModel(complexityScore: ModelComplexityScore): Promise<ModelConfig>;
}

export interface ModelEscalatorConfig {
  plugins: ModelEscalatorPlugin[];
  defaultModel: string;
  complexityThresholds: {
    low: number;
    medium: number;
    high: number;
  };
  performanceThresholds: {
    maxLatency: number;
    maxTokenConsumption: number;
  };
}

export enum ModelComplexityLevel {
  LOW = 'low',
  MEDIUM = 'medium', 
  HIGH = 'high'
}

export interface ModelSwitchEvent {
  originalModel: string;
  newModel: string;
  complexityLevel: ModelComplexityLevel;
  timestamp: number;
}