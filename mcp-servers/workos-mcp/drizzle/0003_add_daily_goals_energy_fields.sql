-- Add energy-aware fields to daily_goals table for energy-based goal adjustment
-- Migration: 0003_add_daily_goals_energy_fields

ALTER TABLE "daily_goals" ADD COLUMN "adjusted_target_points" integer;
ALTER TABLE "daily_goals" ADD COLUMN "readiness_score" integer;
ALTER TABLE "daily_goals" ADD COLUMN "energy_level" text;
ALTER TABLE "daily_goals" ADD COLUMN "adjustment_reason" text;
