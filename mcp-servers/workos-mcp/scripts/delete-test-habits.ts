import { drizzle } from 'drizzle-orm/neon-http';
import { neon } from '@neondatabase/serverless';
import * as schema from '../src/schema.js';
import { eq } from 'drizzle-orm';
import dotenv from 'dotenv';

dotenv.config();

async function deleteTestHabits() {
  const DATABASE_URL = process.env.DATABASE_URL;
  if (!DATABASE_URL) {
    console.error('DATABASE_URL not set');
    process.exit(1);
  }

  const sql = neon(DATABASE_URL);
  const db = drizzle(sql, { schema });

  // Get habits named 'Test habit'
  const habits = await db.select().from(schema.habits).where(eq(schema.habits.name, 'Test habit'));
  console.log('Found', habits.length, 'test habits to delete');

  for (const habit of habits) {
    // Delete completions first
    await db.delete(schema.habitCompletions).where(eq(schema.habitCompletions.habitId, habit.id));
    // Delete habit
    await db.delete(schema.habits).where(eq(schema.habits.id, habit.id));
    console.log('Deleted habit ID', habit.id, '-', habit.name);
  }

  console.log('Done - The Snap is complete.');
}

deleteTestHabits().catch(console.error);
