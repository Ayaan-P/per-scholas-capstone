-- Add source column to saved_opportunities table
-- Run this in your Supabase SQL Editor

ALTER TABLE saved_opportunities ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'grants_gov';

-- Verify the column was added
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'saved_opportunities' AND column_name = 'source';

