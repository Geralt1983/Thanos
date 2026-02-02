import { z } from 'zod';

// Model Provider Configuration Schema
export const ModelProviderSchema = z.object({
  id: z.string(),
  name: z.string(),
  apiKey: z.string(),
  baseUrl: z.string().url(),
  maxTokens: z.number().positive().optional(),
  rateLimit: z.number().positive().optional()
});

// Complexity Detection Configuration
export const ComplexityRuleSchema = z.object({
  name: z.string(),
  maxTokens: z.number().positive(),
  minSpecialTokens: z.number().optional(),
  minContextTokens: z.number().optional()
});

// Main Configuration Schema
export const ModelEscalatorConfigSchema = z.object({
  providers: z.array(ModelProviderSchema),
  complexityRules: z.array(ComplexityRuleSchema),
  defaultProvider: z.string(),
  loggingLevel: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
  performanceThreshold: z.number().positive().default(500) // ms
});

// Type Exports
export type ModelProvider = z.infer<typeof ModelProviderSchema>;
export type ComplexityRule = z.infer<typeof ComplexityRuleSchema>;
export type ModelEscalatorConfig = z.infer<typeof ModelEscalatorConfigSchema>;