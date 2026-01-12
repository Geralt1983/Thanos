-- Create energy_feedback table to track user feedback on energy-based task suggestions
-- Migration: 0004_add_energy_feedback_table

CREATE TABLE "energy_feedback" (
	"id" serial PRIMARY KEY NOT NULL,
	"task_id" integer NOT NULL,
	"suggested_energy_level" text NOT NULL,
	"actual_energy_level" text NOT NULL,
	"user_feedback" text,
	"completed_successfully" boolean NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	CONSTRAINT "energy_feedback_task_id_tasks_id_fk" FOREIGN KEY ("task_id") REFERENCES "tasks"("id") ON DELETE no action ON UPDATE no action
);
--> statement-breakpoint
CREATE INDEX "energy_feedback_task_id_idx" ON "energy_feedback" USING btree ("task_id");
--> statement-breakpoint
CREATE INDEX "energy_feedback_created_at_idx" ON "energy_feedback" USING btree ("created_at");
