-- Add new fields to scraped_grants table for agent-extracted data
ALTER TABLE scraped_grants
ADD COLUMN IF NOT EXISTS geographic_focus TEXT,
ADD COLUMN IF NOT EXISTS award_type TEXT,
ADD COLUMN IF NOT EXISTS anticipated_awards TEXT,
ADD COLUMN IF NOT EXISTS consortium_required BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS consortium_description TEXT,
ADD COLUMN IF NOT EXISTS rfp_attachment_requirements TEXT;

-- Create indexes for filtering
CREATE INDEX IF NOT EXISTS idx_scraped_grants_geographic_focus ON scraped_grants(geographic_focus);
CREATE INDEX IF NOT EXISTS idx_scraped_grants_award_type ON scraped_grants(award_type);
CREATE INDEX IF NOT EXISTS idx_scraped_grants_consortium ON scraped_grants(consortium_required);
