import { z } from 'zod';

// Define the model escalation configuration schema
export const ModelEscalatorConfigSchema = z.object({
  // Complexity thresholds for model escalation
  complexityThresholds: z.object({
    low: z.number().min(0).max(100).default(30),
    medium: z.number().min(0).max(100).default(60),
    high: z.number().min(0).max(100).default(90)
  }),

  // Token usage thresholds for escalation
  tokenThresholds: z.object({
    soft: z.number().min(0).default(3000),
    hard: z.number().min(0).default(6000)
  }),

  // Cost thresholds for model switching
  costThresholds: z.object({
    soft: z.number().min(0).default(0.05),
    hard: z.number().min(0).default(0.10)
  }),

  // Configured model hierarchy for escalation
  modelHierarchy: z.array(z.string()).min(1).default([
    'anthropic/claude-3-haiku-20240307', 
    'anthropic/claude-3-sonnet-20240229', 
    'anthropic/claude-3-opus-20240229'
  ]),

  // Hysteresis parameters for preventing rapid model switches
  hysteresis: z.object({
    cooldownSeconds: z.number().min(0).default(300),
    stabilityWindow: z.number().min(0).default(60)
  }).default({
    cooldownSeconds: 300,
    stabilityWindow: 60
  }),

  // Enable/disable the plugin
  enabled: z.boolean().default(true)
});

// Type for the configuration
export type ModelEscalatorConfig = z.infer<typeof ModelEscalatorConfigSchema>;