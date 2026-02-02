import { z } from 'zod';

// Model configuration schema
export const ModelConfigSchema = z.object({
  name: z.string(),
  provider: z.string(),
  maxTokens: z.number().optional().default(4096),
  costPerThousandTokens: z.number().optional().default(0),
  capabilities: z.array(z.string()).optional().default([]),
  complexity: z.object({
    baseline: z.number().min(0).max(10).default(5),
    maxComplexity: z.number().min(0).max(10).default(10)
  })
});

export type ModelConfig = z.infer<typeof ModelConfigSchema>;

// Complexity scoring interfaces
export interface ComplexityScorer {
  calculateComplexity(input: string): number;
}

// Model request interface
export interface ModelRequest {
  input: string;
  maxTokens?: number;
}

// Escalation strategy types
export enum EscalationStrategy {
  LINEAR,
  EXPONENTIAL,
  ADAPTIVE
}

// Configuration for the entire ModelEscalator
export const ModelEscalatorConfigSchema = z.object({
  models: z.array(ModelConfigSchema),
  defaultStrategy: z.nativeEnum(EscalationStrategy).default(EscalationStrategy.ADAPTIVE),
  complexityThresholds: z.object({
    low: z.number().min(0).max(10).default(3),
    medium: z.number().min(0).max(10).default(6),
    high: z.number().min(0).max(10).default(9)
  })
});

export type ModelEscalatorConfig = z.infer<typeof ModelEscalatorConfigSchema>;