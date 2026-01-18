-- Add context column to brain_dump table for work/personal filtering
ALTER TABLE brain_dump ADD COLUMN IF NOT EXISTS context TEXT DEFAULT 'personal';

-- Create index for context filtering
CREATE INDEX IF NOT EXISTS brain_dump_context_idx ON brain_dump (context);

-- Update existing entries to have default context
UPDATE brain_dump SET context = 'personal' WHERE context IS NULL;
