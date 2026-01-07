import { neon } from "@neondatabase/serverless";

const url = process.env.WORKOS_DATABASE_URL;
if (!url) {
  console.error("WORKOS_DATABASE_URL required");
  process.exit(1);
}

const sql = neon(url);

const statements = [
  // Add new fields to habits table for improved streak tracking
  `ALTER TABLE "habits" ADD COLUMN IF NOT EXISTS "last_completed_date" date`,
  `ALTER TABLE "habits" ADD COLUMN IF NOT EXISTS "time_of_day" text DEFAULT 'anytime'`,
  `ALTER TABLE "habits" ADD COLUMN IF NOT EXISTS "category" text`,
];

console.log(`Running ${statements.length} statements...\n`);

for (const stmt of statements) {
  const preview = stmt.replace(/\s+/g, ' ').substring(0, 70);
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

console.log("\nMigration complete!");
