CREATE TABLE "brain_dump" (
	"id" serial PRIMARY KEY NOT NULL,
	"content" text NOT NULL,
	"category" text,
	"processed" integer DEFAULT 0,
	"processed_at" timestamp,
	"converted_to_task_id" integer,
	"created_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "client_memory" (
	"id" text PRIMARY KEY NOT NULL,
	"client_name" text NOT NULL,
	"tier" text DEFAULT 'active',
	"last_task_id" text,
	"last_task_description" text,
	"last_task_at" timestamp,
	"total_tasks" integer DEFAULT 0,
	"stale_days" integer DEFAULT 0,
	"notes" text,
	"sentiment" text DEFAULT 'neutral',
	"importance" text DEFAULT 'medium',
	"avoidance_score" integer DEFAULT 0,
	"blocker_reason" text,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL,
	CONSTRAINT "client_memory_client_name_unique" UNIQUE("client_name")
);
--> statement-breakpoint
CREATE TABLE "clients" (
	"id" serial PRIMARY KEY NOT NULL,
	"name" text NOT NULL,
	"type" text DEFAULT 'client' NOT NULL,
	"color" text,
	"is_active" integer DEFAULT 1 NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	CONSTRAINT "clients_name_unique" UNIQUE("name")
);
--> statement-breakpoint
CREATE TABLE "daily_goals" (
	"id" serial PRIMARY KEY NOT NULL,
	"date" date NOT NULL,
	"target_points" integer DEFAULT 18,
	"earned_points" integer DEFAULT 0,
	"task_count" integer DEFAULT 0,
	"current_streak" integer DEFAULT 0,
	"longest_streak" integer DEFAULT 0,
	"last_goal_hit_date" date,
	"daily_debt" integer DEFAULT 0,
	"weekly_debt" integer DEFAULT 0,
	"pressure_level" integer DEFAULT 0,
	"updated_at" timestamp with time zone DEFAULT now(),
	CONSTRAINT "daily_goals_date_unique" UNIQUE("date")
);
--> statement-breakpoint
CREATE TABLE "energy_states" (
	"id" serial PRIMARY KEY NOT NULL,
	"level" text NOT NULL,
	"source" text DEFAULT 'manual',
	"oura_readiness" integer,
	"oura_hrv" integer,
	"oura_sleep" integer,
	"note" text,
	"recorded_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "habit_completions" (
	"id" serial PRIMARY KEY NOT NULL,
	"habit_id" integer NOT NULL,
	"completed_at" timestamp DEFAULT now() NOT NULL,
	"note" text
);
--> statement-breakpoint
CREATE TABLE "habits" (
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
--> statement-breakpoint
CREATE TABLE "tasks" (
	"id" serial PRIMARY KEY NOT NULL,
	"client_id" integer,
	"title" text NOT NULL,
	"description" text,
	"status" text DEFAULT 'backlog' NOT NULL,
	"category" text DEFAULT 'work' NOT NULL,
	"value_tier" varchar(20) DEFAULT 'progress',
	"effort_estimate" integer DEFAULT 2,
	"effort_actual" integer,
	"drain_type" text,
	"sort_order" integer DEFAULT 0,
	"subtasks" jsonb DEFAULT '[]'::jsonb,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL,
	"completed_at" timestamp,
	"backlog_entered_at" timestamp with time zone,
	"points_ai_guess" integer,
	"points_final" integer,
	"points_adjusted_at" timestamp with time zone
);
--> statement-breakpoint
ALTER TABLE "brain_dump" ADD CONSTRAINT "brain_dump_converted_to_task_id_tasks_id_fk" FOREIGN KEY ("converted_to_task_id") REFERENCES "public"."tasks"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "habit_completions" ADD CONSTRAINT "habit_completions_habit_id_habits_id_fk" FOREIGN KEY ("habit_id") REFERENCES "public"."habits"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "tasks" ADD CONSTRAINT "tasks_client_id_clients_id_fk" FOREIGN KEY ("client_id") REFERENCES "public"."clients"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "brain_dump_processed_idx" ON "brain_dump" USING btree ("processed");--> statement-breakpoint
CREATE INDEX "brain_dump_created_at_idx" ON "brain_dump" USING btree ("created_at");--> statement-breakpoint
CREATE INDEX "energy_states_recorded_at_idx" ON "energy_states" USING btree ("recorded_at");--> statement-breakpoint
CREATE INDEX "habit_completions_habit_id_idx" ON "habit_completions" USING btree ("habit_id");--> statement-breakpoint
CREATE INDEX "habit_completions_completed_at_idx" ON "habit_completions" USING btree ("completed_at");--> statement-breakpoint
CREATE INDEX "tasks_status_idx" ON "tasks" USING btree ("status");--> statement-breakpoint
CREATE INDEX "tasks_client_id_idx" ON "tasks" USING btree ("client_id");--> statement-breakpoint
CREATE INDEX "tasks_completed_at_idx" ON "tasks" USING btree ("completed_at");