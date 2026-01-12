import { pgTable, serial, text, integer, timestamp, jsonb, varchar, decimal, date, boolean, index } from "drizzle-orm/pg-core"
import type { InferSelectModel } from "drizzle-orm"
import { relations } from "drizzle-orm"

// =============================================================================
// CLIENTS
// =============================================================================
export const clients = pgTable("clients", {
  id: serial("id").primaryKey(),
  name: text("name").notNull().unique(),
  type: text("type").notNull().default("client"),
  color: text("color"),
  isActive: integer("is_active").notNull().default(1),
  createdAt: timestamp("created_at").defaultNow().notNull(),
})

// =============================================================================
// TASKS
// =============================================================================
export const tasks = pgTable("tasks", {
  id: serial("id").primaryKey(),
  clientId: integer("client_id").references(() => clients.id),
  title: text("title").notNull(),
  description: text("description"),
  status: text("status").notNull().default("backlog"),
  category: text("category").notNull().default("work"), // work, personal
  valueTier: varchar("value_tier", { length: 20 }).default("progress"),
  effortEstimate: integer("effort_estimate").default(2),
  effortActual: integer("effort_actual"),
  drainType: text("drain_type"),
  cognitiveLoad: text("cognitive_load"), // low, medium, high - mental complexity required
  sortOrder: integer("sort_order").default(0),
  subtasks: jsonb("subtasks").default([]),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
  completedAt: timestamp("completed_at"),
  backlogEnteredAt: timestamp("backlog_entered_at", { withTimezone: true }),
  pointsAiGuess: integer("points_ai_guess"),
  pointsFinal: integer("points_final"),
  pointsAdjustedAt: timestamp("points_adjusted_at", { withTimezone: true }),
}, (table) => [
  index("tasks_status_idx").on(table.status),
  index("tasks_client_id_idx").on(table.clientId),
  index("tasks_completed_at_idx").on(table.completedAt),
])

// =============================================================================
// DAILY GOALS
// =============================================================================
export const dailyGoals = pgTable("daily_goals", {
  id: serial("id").primaryKey(),
  date: date("date").unique().notNull(),
  targetPoints: integer("target_points").default(18),
  earnedPoints: integer("earned_points").default(0),
  taskCount: integer("task_count").default(0),
  currentStreak: integer("current_streak").default(0),
  longestStreak: integer("longest_streak").default(0),
  lastGoalHitDate: date("last_goal_hit_date"),
  dailyDebt: integer("daily_debt").default(0),
  weeklyDebt: integer("weekly_debt").default(0),
  pressureLevel: integer("pressure_level").default(0),
  adjustedTargetPoints: integer("adjusted_target_points"), // Energy-adjusted target points
  readinessScore: integer("readiness_score"), // Oura readiness score (0-100)
  energyLevel: text("energy_level"), // Derived energy level: high, medium, low
  adjustmentReason: text("adjustment_reason"), // Why target was adjusted
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
})

// =============================================================================
// CLIENT MEMORY
// =============================================================================
export const clientMemory = pgTable("client_memory", {
  id: text("id").primaryKey(),
  clientName: text("client_name").notNull().unique(),
  tier: text("tier").default("active"),
  lastTaskId: text("last_task_id"),
  lastTaskDescription: text("last_task_description"),
  lastTaskAt: timestamp("last_task_at"),
  totalTasks: integer("total_tasks").default(0),
  staleDays: integer("stale_days").default(0),
  notes: text("notes"),
  sentiment: text("sentiment").default("neutral"),
  importance: text("importance").default("medium"),
  avoidanceScore: integer("avoidance_score").default(0),
  blockerReason: text("blocker_reason"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
})

// =============================================================================
// HABITS (PersonalOS Integration)
// =============================================================================
export const habits = pgTable("habits", {
  id: serial("id").primaryKey(),
  name: text("name").notNull(),
  description: text("description"),
  emoji: text("emoji"),
  frequency: text("frequency").notNull().default("daily"), // daily, weekly, weekdays
  targetCount: integer("target_count").default(1), // times per frequency period
  currentStreak: integer("current_streak").default(0),
  longestStreak: integer("longest_streak").default(0),
  lastCompletedDate: date("last_completed_date"), // track last completion for streak logic
  timeOfDay: text("time_of_day").default("anytime"), // morning, evening, anytime
  category: text("category"), // health, productivity, relationship, personal
  isActive: integer("is_active").notNull().default(1),
  sortOrder: integer("sort_order").default(0),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
})

export const habitCompletions = pgTable("habit_completions", {
  id: serial("id").primaryKey(),
  habitId: integer("habit_id").references(() => habits.id).notNull(),
  completedAt: timestamp("completed_at").defaultNow().notNull(),
  note: text("note"),
}, (table) => [
  index("habit_completions_habit_id_idx").on(table.habitId),
  index("habit_completions_completed_at_idx").on(table.completedAt),
])

// =============================================================================
// ENERGY STATE (PersonalOS Integration)
// =============================================================================
export const energyStates = pgTable("energy_states", {
  id: serial("id").primaryKey(),
  level: text("level").notNull(), // high, medium, low
  source: text("source").default("manual"), // manual, oura
  ouraReadiness: integer("oura_readiness"),
  ouraHrv: integer("oura_hrv"),
  ouraSleep: integer("oura_sleep"),
  note: text("note"),
  recordedAt: timestamp("recorded_at").defaultNow().notNull(),
}, (table) => [
  index("energy_states_recorded_at_idx").on(table.recordedAt),
])

// =============================================================================
// BRAIN DUMP (PersonalOS Integration)
// =============================================================================
export const brainDump = pgTable("brain_dump", {
  id: serial("id").primaryKey(),
  content: text("content").notNull(),
  category: text("category"), // thought, task, idea, worry
  processed: integer("processed").default(0),
  processedAt: timestamp("processed_at"),
  convertedToTaskId: integer("converted_to_task_id").references(() => tasks.id),
  createdAt: timestamp("created_at").defaultNow().notNull(),
}, (table) => [
  index("brain_dump_processed_idx").on(table.processed),
  index("brain_dump_created_at_idx").on(table.createdAt),
])

// =============================================================================
// ENERGY FEEDBACK
// =============================================================================
export const energyFeedback = pgTable("energy_feedback", {
  id: serial("id").primaryKey(),
  taskId: integer("task_id").references(() => tasks.id).notNull(),
  suggestedEnergyLevel: text("suggested_energy_level").notNull(), // low, medium, high
  actualEnergyLevel: text("actual_energy_level").notNull(), // low, medium, high
  userFeedback: text("user_feedback"), // free-form feedback from user
  completedSuccessfully: boolean("completed_successfully").notNull(), // whether task was completed
  createdAt: timestamp("created_at").defaultNow().notNull(),
}, (table) => [
  index("energy_feedback_task_id_idx").on(table.taskId),
  index("energy_feedback_created_at_idx").on(table.createdAt),
])

// =============================================================================
// TYPE EXPORTS
// =============================================================================
export type Client = InferSelectModel<typeof clients>
export type Task = InferSelectModel<typeof tasks>
export type DailyGoal = InferSelectModel<typeof dailyGoals>
export type ClientMemory = InferSelectModel<typeof clientMemory>
export type Habit = InferSelectModel<typeof habits>
export type HabitCompletion = InferSelectModel<typeof habitCompletions>
export type EnergyState = InferSelectModel<typeof energyStates>
export type BrainDumpEntry = InferSelectModel<typeof brainDump>
export type EnergyFeedback = InferSelectModel<typeof energyFeedback>
export type TaskStatus = "active" | "queued" | "backlog" | "done"
export type EnergyLevel = "high" | "medium" | "low"
export type CognitiveLoad = "low" | "medium" | "high"

// =============================================================================
// RELATIONS
// =============================================================================
export const tasksRelations = relations(tasks, ({ one }) => ({
  client: one(clients, {
    fields: [tasks.clientId],
    references: [clients.id],
  }),
}))

export const clientsRelations = relations(clients, ({ many }) => ({
  tasks: many(tasks),
}))

export const habitsRelations = relations(habits, ({ many }) => ({
  completions: many(habitCompletions),
}))

export const habitCompletionsRelations = relations(habitCompletions, ({ one }) => ({
  habit: one(habits, {
    fields: [habitCompletions.habitId],
    references: [habits.id],
  }),
}))

export const brainDumpRelations = relations(brainDump, ({ one }) => ({
  convertedTask: one(tasks, {
    fields: [brainDump.convertedToTaskId],
    references: [tasks.id],
  }),
}))

export const energyFeedbackRelations = relations(energyFeedback, ({ one }) => ({
  task: one(tasks, {
    fields: [energyFeedback.taskId],
    references: [tasks.id],
  }),
}))
