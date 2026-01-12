-- Add cognitive_load field to tasks table for energy-aware task prioritization
-- Migration: 0002_add_cognitive_load

ALTER TABLE "tasks" ADD COLUMN "cognitive_load" text DEFAULT 'medium';
