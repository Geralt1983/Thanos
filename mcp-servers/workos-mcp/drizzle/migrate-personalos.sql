-- PersonalOS Integration Migration
-- Adds: habits, habit_completions, energy_states, brain_dump tables
-- Adds: category column to tasks

-- Add category column to tasks (if not exists)
ALTER TABLE "tasks" ADD COLUMN IF NOT EXISTS "category" text DEFAULT 'work' NOT NULL;

-- Create habits table
CREATE TABLE IF NOT EXISTS "habits" (
  "id" serial PRIMARY KEY NOT NULL,
  "name" text NOT NULL,
  "description" text,
  "emoji" text,
  "frequency" text DEFAULT 'daily' NOT NULL,
  "target_count" integer DEFAULT 1,
  "current_streak" integer DEFAULT 0,
  "longest_streak" integer DEFAULT 0,
  "is_active" integer DEFAULT 1 NOT NULL,
  "sort_order" integer DEFAULT 0,
  "created_at" timestamp DEFAULT now() NOT NULL,
  "updated_at" timestamp DEFAULT now() NOT NULL
);

-- Create habit_completions table
CREATE TABLE IF NOT EXISTS "habit_completions" (
  "id" serial PRIMARY KEY NOT NULL,
  "habit_id" integer NOT NULL,
  "completed_at" timestamp DEFAULT now() NOT NULL,
  "note" text
);

-- Create energy_states table
CREATE TABLE IF NOT EXISTS "energy_states" (
  "id" serial PRIMARY KEY NOT NULL,
  "level" text NOT NULL,
  "source" text DEFAULT 'manual',
  "oura_readiness" integer,
  "oura_hrv" integer,
  "oura_sleep" integer,
  "note" text,
  "recorded_at" timestamp DEFAULT now() NOT NULL
);

-- Create brain_dump table
CREATE TABLE IF NOT EXISTS "brain_dump" (
  "id" serial PRIMARY KEY NOT NULL,
  "content" text NOT NULL,
  "category" text,
  "processed" integer DEFAULT 0,
  "processed_at" timestamp,
  "converted_to_task_id" integer,
  "created_at" timestamp DEFAULT now() NOT NULL
);

-- Add foreign key constraints
ALTER TABLE "habit_completions"
  ADD CONSTRAINT "habit_completions_habit_id_habits_id_fk"
  FOREIGN KEY ("habit_id") REFERENCES "habits"("id") ON DELETE CASCADE;

ALTER TABLE "brain_dump"
  ADD CONSTRAINT "brain_dump_converted_to_task_id_tasks_id_fk"
  FOREIGN KEY ("converted_to_task_id") REFERENCES "tasks"("id") ON DELETE SET NULL;

-- Create indexes
CREATE INDEX IF NOT EXISTS "habit_completions_habit_id_idx" ON "habit_completions" ("habit_id");
CREATE INDEX IF NOT EXISTS "habit_completions_completed_at_idx" ON "habit_completions" ("completed_at");
CREATE INDEX IF NOT EXISTS "energy_states_recorded_at_idx" ON "energy_states" ("recorded_at");
CREATE INDEX IF NOT EXISTS "brain_dump_processed_idx" ON "brain_dump" ("processed");
CREATE INDEX IF NOT EXISTS "brain_dump_created_at_idx" ON "brain_dump" ("created_at");
