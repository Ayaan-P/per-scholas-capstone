-- Migration: Add notes column to saved_opportunities table
-- Run this in Supabase SQL Editor

ALTER TABLE saved_opportunities
ADD COLUMN IF NOT EXISTS notes TEXT DEFAULT '';

-- Add comment
COMMENT ON COLUMN saved_opportunities.notes IS 'User notes about the opportunity';

