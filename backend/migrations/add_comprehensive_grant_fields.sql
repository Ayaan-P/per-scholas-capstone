-- Migration: Add universal grant detail fields to scraped_grants table
-- These fields work across ALL grant sources (Grants.gov, SAM.gov, state, local, etc.)
-- Run this in Supabase SQL Editor
-- Created: 2025-10-19

-- Add contact information (expanded)
ALTER TABLE scraped_grants
ADD COLUMN IF NOT EXISTS contact_name TEXT,
ADD COLUMN IF NOT EXISTS contact_phone TEXT,
ADD COLUMN IF NOT EXISTS contact_description TEXT;

-- Add eligibility information
ALTER TABLE scraped_grants
ADD COLUMN IF NOT EXISTS eligibility_explanation TEXT;

-- Add cost sharing information
ALTER TABLE scraped_grants
ADD COLUMN IF NOT EXISTS cost_sharing BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS cost_sharing_description TEXT;

-- Add additional information fields
ALTER TABLE scraped_grants
ADD COLUMN IF NOT EXISTS additional_info_url TEXT,
ADD COLUMN IF NOT EXISTS additional_info_text TEXT;

-- Add timeline fields
ALTER TABLE scraped_grants
ADD COLUMN IF NOT EXISTS archive_date DATE,
ADD COLUMN IF NOT EXISTS forecast_date DATE,
ADD COLUMN IF NOT EXISTS close_date_explanation TEXT;

-- Add award amount range (better than single amount field)
ALTER TABLE scraped_grants
ADD COLUMN IF NOT EXISTS expected_number_of_awards TEXT,
ADD COLUMN IF NOT EXISTS award_floor INTEGER,
ADD COLUMN IF NOT EXISTS award_ceiling INTEGER;

-- Add attachments and version tracking
ALTER TABLE scraped_grants
ADD COLUMN IF NOT EXISTS attachments JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS version TEXT,
ADD COLUMN IF NOT EXISTS last_updated_date TIMESTAMP WITH TIME ZONE;

-- Create indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_scraped_grants_cost_sharing ON scraped_grants(cost_sharing);
CREATE INDEX IF NOT EXISTS idx_scraped_grants_forecast_date ON scraped_grants(forecast_date);
CREATE INDEX IF NOT EXISTS idx_scraped_grants_archive_date ON scraped_grants(archive_date);

-- Add comments for documentation
COMMENT ON COLUMN scraped_grants.contact_name IS 'Primary contact person name at funding agency';
COMMENT ON COLUMN scraped_grants.contact_phone IS 'Primary contact phone number';
COMMENT ON COLUMN scraped_grants.eligibility_explanation IS 'Detailed eligibility criteria text';
COMMENT ON COLUMN scraped_grants.cost_sharing IS 'Whether cost sharing or matching funds are required';
COMMENT ON COLUMN scraped_grants.attachments IS 'Array of related documents (solicitations, amendments) with URLs';
COMMENT ON COLUMN scraped_grants.award_floor IS 'Minimum award amount in dollars';
COMMENT ON COLUMN scraped_grants.award_ceiling IS 'Maximum award amount in dollars';

-- Verification query - check that columns were added
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'scraped_grants'
  AND column_name IN (
    'contact_name', 'contact_phone', 'eligibility_explanation', 'cost_sharing',
    'attachments', 'award_floor', 'award_ceiling', 'forecast_date'
  )
ORDER BY column_name;
