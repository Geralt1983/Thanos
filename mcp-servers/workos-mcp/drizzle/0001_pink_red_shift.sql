CREATE TABLE "energy_feedback" (
	"id" serial PRIMARY KEY NOT NULL,
	"task_id" integer NOT NULL,
	"suggested_energy_level" text NOT NULL,
	"actual_energy_level" text NOT NULL,
	"user_feedback" text,
	"completed_successfully" boolean NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "brain_dump" ADD COLUMN "context" text DEFAULT 'personal';--> statement-breakpoint
ALTER TABLE "client_memory" ADD COLUMN "risk_level" text DEFAULT 'normal';--> statement-breakpoint
ALTER TABLE "client_memory" ADD COLUMN "work_debt" text;--> statement-breakpoint
ALTER TABLE "daily_goals" ADD COLUMN "adjusted_target_points" integer;--> statement-breakpoint
ALTER TABLE "daily_goals" ADD COLUMN "readiness_score" integer;--> statement-breakpoint
ALTER TABLE "daily_goals" ADD COLUMN "energy_level" text;--> statement-breakpoint
ALTER TABLE "daily_goals" ADD COLUMN "adjustment_reason" text;--> statement-breakpoint
ALTER TABLE "habits" ADD COLUMN "last_completed_date" date;--> statement-breakpoint
ALTER TABLE "habits" ADD COLUMN "time_of_day" text DEFAULT 'anytime';--> statement-breakpoint
ALTER TABLE "habits" ADD COLUMN "category" text;--> statement-breakpoint
ALTER TABLE "tasks" ADD COLUMN "cognitive_load" text;--> statement-breakpoint
ALTER TABLE "energy_feedback" ADD CONSTRAINT "energy_feedback_task_id_tasks_id_fk" FOREIGN KEY ("task_id") REFERENCES "public"."tasks"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "energy_feedback_task_id_idx" ON "energy_feedback" USING btree ("task_id");--> statement-breakpoint
CREATE INDEX "energy_feedback_created_at_idx" ON "energy_feedback" USING btree ("created_at");--> statement-breakpoint
CREATE INDEX "brain_dump_context_idx" ON "brain_dump" USING btree ("context");