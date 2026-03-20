-- Migration: Add URL validation fields to scraped_grants table
-- Allows tracking whether grant URLs are accessible and valid
-- Created: 2026-03-20

-- Add URL validation status fields
ALTER TABLE scraped_grants
ADD COLUMN IF NOT EXISTS url_valid BOOLEAN DEFAULT true,
ADD COLUMN IF NOT EXISTS url_validation_error TEXT,
ADD COLUMN IF NOT EXISTS url_status_code INTEGER,
ADD COLUMN IF NOT EXISTS url_last_checked TIMESTAMP WITH TIME ZONE;

-- Create index for querying invalid URLs
CREATE INDEX IF NOT EXISTS idx_scraped_grants_url_valid ON scraped_grants(url_valid);

-- Add comments for documentation
COMMENT ON COLUMN scraped_grants.url_valid IS 'Whether the application_url is accessible (true if not checked)';
COMMENT ON COLUMN scraped_grants.url_validation_error IS 'Error message if URL validation failed';
COMMENT ON COLUMN scraped_grants.url_status_code IS 'HTTP status code from URL validation check';
COMMENT ON COLUMN scraped_grants.url_last_checked IS 'Timestamp of last URL validation check';

-- Verification query - check that columns were added
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'scraped_grants'
  AND column_name IN (
    'url_valid', 'url_validation_error', 'url_status_code', 'url_last_checked'
  )
ORDER BY column_name;
