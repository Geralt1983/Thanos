import { neon } from "@neondatabase/serverless";

const url = process.env.WORKOS_DATABASE_URL;
if (!url) {
  console.error("WORKOS_DATABASE_URL required");
  process.exit(1);
}

const sql = neon(url);

const statements = [
  // Add category column to tasks
  `ALTER TABLE "tasks" ADD COLUMN IF NOT EXISTS "category" text DEFAULT 'work' NOT NULL`,

  // Create habits table
  `CREATE TABLE IF NOT EXISTS "habits" (
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
  )`,

  // Create habit_completions table
  `CREATE TABLE IF NOT EXISTS "habit_completions" (
    "id" serial PRIMARY KEY NOT NULL,
    "habit_id" integer NOT NULL REFERENCES "habits"("id") ON DELETE CASCADE,
    "completed_at" timestamp DEFAULT now() NOT NULL,
    "note" text
  )`,

  // Create energy_states table
  `CREATE TABLE IF NOT EXISTS "energy_states" (
    "id" serial PRIMARY KEY NOT NULL,
    "level" text NOT NULL,
    "source" text DEFAULT 'manual',
    "oura_readiness" integer,
    "oura_hrv" integer,
    "oura_sleep" integer,
    "note" text,
    "recorded_at" timestamp DEFAULT now() NOT NULL
  )`,

  // Create brain_dump table
  `CREATE TABLE IF NOT EXISTS "brain_dump" (
    "id" serial PRIMARY KEY NOT NULL,
    "content" text NOT NULL,
    "category" text,
    "processed" integer DEFAULT 0,
    "processed_at" timestamp,
    "converted_to_task_id" integer REFERENCES "tasks"("id") ON DELETE SET NULL,
    "created_at" timestamp DEFAULT now() NOT NULL
  )`,

  // Create indexes
  `CREATE INDEX IF NOT EXISTS "habit_completions_habit_id_idx" ON "habit_completions" ("habit_id")`,
  `CREATE INDEX IF NOT EXISTS "habit_completions_completed_at_idx" ON "habit_completions" ("completed_at")`,
  `CREATE INDEX IF NOT EXISTS "energy_states_recorded_at_idx" ON "energy_states" ("recorded_at")`,
  `CREATE INDEX IF NOT EXISTS "brain_dump_processed_idx" ON "brain_dump" ("processed")`,
  `CREATE INDEX IF NOT EXISTS "brain_dump_created_at_idx" ON "brain_dump" ("created_at")`,
];

console.log(`Running ${statements.length} statements...\\n`);

for (const stmt of statements) {
  const preview = stmt.replace(/\\s+/g, ' ').substring(0, 70);
  try {
    await sql(stmt);
    console.log("✓", preview + "...");
  } catch (err) {
    if (err.message.includes("already exists") || err.message.includes("duplicate")) {
      console.log("⏭", preview + "... (already exists)");
    } else {
      console.error("✗", preview + "...");
      console.error("  Error:", err.message);
    }
  }
}

console.log("\\nMigration complete!");
