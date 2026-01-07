-- Add new fields to habits table for improved streak tracking
-- Migration: 0001_add_habit_fields

ALTER TABLE "habits" ADD COLUMN "last_completed_date" date;
ALTER TABLE "habits" ADD COLUMN "time_of_day" text DEFAULT 'anytime';
ALTER TABLE "habits" ADD COLUMN "category" text;
