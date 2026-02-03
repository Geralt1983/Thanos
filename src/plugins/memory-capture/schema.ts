import { z } from 'zod';

export const MemoryCaptureConfigSchema = z.object({
  enabled: z.boolean().default(true),
  minChars: z.number().int().min(40).default(200),
  minIntervalSeconds: z.number().int().min(10).default(120),
  allowLLM: z.boolean().default(false),
  source: z.string().default('openclaw_plugin')
});

export type MemoryCaptureConfig = z.infer<typeof MemoryCaptureConfigSchema>;
