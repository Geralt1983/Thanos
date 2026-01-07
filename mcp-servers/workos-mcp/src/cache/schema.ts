import { sqliteTable, text, integer } from "drizzle-orm/sqlite-core";
import type { InferSelectModel } from "drizzle-orm";

// =============================================================================
// CACHED CLIENTS (mirrors Neon clients table)
// =============================================================================
export const cachedClients = sqliteTable("cached_clients", {
  id: integer("id").primaryKey(),
  name: text("name").notNull(),
  type: text("type").notNull().default("client"),
  color: text("color"),
  isActive: integer("is_active").notNull().default(1),
  createdAt: text("created_at").notNull(), // ISO string
});

// =============================================================================
// CACHED TASKS (mirrors Neon tasks table)
// =============================================================================
export const cachedTasks = sqliteTable("cached_tasks", {
  id: integer("id").primaryKey(),
  clientId: integer("client_id"),
  title: text("title").notNull(),
  description: text("description"),
  status: text("status").notNull().default("backlog"),
  category: text("category").notNull().default("work"),
  valueTier: text("value_tier").default("progress"),
  effortEstimate: integer("effort_estimate").default(2),
  effortActual: integer("effort_actual"),
  drainType: text("drain_type"),
  sortOrder: integer("sort_order").default(0),
  subtasks: text("subtasks").default("[]"), // JSON string
  createdAt: text("created_at").notNull(), // ISO string
  updatedAt: text("updated_at").notNull(), // ISO string
  completedAt: text("completed_at"), // ISO string
  backlogEnteredAt: text("backlog_entered_at"), // ISO string
  pointsAiGuess: integer("points_ai_guess"),
  pointsFinal: integer("points_final"),
  pointsAdjustedAt: text("points_adjusted_at"), // ISO string
});

// =============================================================================
// CACHED DAILY GOALS
// =============================================================================
export const cachedDailyGoals = sqliteTable("cached_daily_goals", {
  id: integer("id").primaryKey(),
  date: text("date").notNull().unique(),
  targetPoints: integer("target_points").default(18),
  earnedPoints: integer("earned_points").default(0),
  taskCount: integer("task_count").default(0),
  currentStreak: integer("current_streak").default(0),
  longestStreak: integer("longest_streak").default(0),
  lastGoalHitDate: text("last_goal_hit_date"),
  dailyDebt: integer("daily_debt").default(0),
  weeklyDebt: integer("weekly_debt").default(0),
  pressureLevel: integer("pressure_level").default(0),
  updatedAt: text("updated_at"), // ISO string
});

// =============================================================================
// CACHED HABITS
// =============================================================================
export const cachedHabits = sqliteTable("cached_habits", {
  id: integer("id").primaryKey(),
  name: text("name").notNull(),
  description: text("description"),
  emoji: text("emoji"),
  frequency: text("frequency").notNull().default("daily"),
  targetCount: integer("target_count").default(1),
  currentStreak: integer("current_streak").default(0),
  longestStreak: integer("longest_streak").default(0),
  isActive: integer("is_active").notNull().default(1),
  sortOrder: integer("sort_order").default(0),
  createdAt: text("created_at").notNull(),
  updatedAt: text("updated_at").notNull(),
});

// =============================================================================
// CACHE METADATA
// =============================================================================
export const cacheMeta = sqliteTable("cache_meta", {
  key: text("key").primaryKey(),
  value: text("value").notNull(),
  updatedAt: text("updated_at").notNull(), // ISO string
});

// =============================================================================
// TYPE EXPORTS
// =============================================================================
export type CachedClient = InferSelectModel<typeof cachedClients>;
export type CachedTask = InferSelectModel<typeof cachedTasks>;
export type CachedDailyGoal = InferSelectModel<typeof cachedDailyGoals>;
export type CachedHabit = InferSelectModel<typeof cachedHabits>;
export type CacheMeta = InferSelectModel<typeof cacheMeta>;
