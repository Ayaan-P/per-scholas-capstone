-- Database schema for scheduled grant scraping
-- Run this in Supabase SQL Editor to create the scraped_grants table

-- Table for grants collected by scheduled scrapers
CREATE TABLE IF NOT EXISTS scraped_grants (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    opportunity_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    funder TEXT NOT NULL,
    amount INTEGER,
    deadline DATE,
    description TEXT,
    requirements JSONB DEFAULT '[]'::jsonb,
    contact TEXT,
    application_url TEXT,
    match_score INTEGER DEFAULT 0,
    source TEXT NOT NULL, -- 'grants_gov', 'state', 'local', 'sam_gov', etc.
    status TEXT DEFAULT 'active', -- 'active', 'expired', 'saved'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- UNIVERSAL FIELDS (work across all grant sources)
    -- Contact information (expanded)
    contact_name TEXT,
    contact_phone TEXT,
    contact_description TEXT,

    -- Eligibility information
    eligibility_explanation TEXT,

    -- Cost sharing
    cost_sharing BOOLEAN DEFAULT false,
    cost_sharing_description TEXT,

    -- Additional information
    additional_info_url TEXT,
    additional_info_text TEXT,

    -- Timeline fields
    archive_date DATE,
    forecast_date DATE,
    close_date_explanation TEXT,

    -- Award range (more useful than single amount)
    expected_number_of_awards TEXT,
    award_floor INTEGER,
    award_ceiling INTEGER,

    -- Attachments and version tracking
    attachments JSONB DEFAULT '[]'::jsonb,
    version TEXT,
    last_updated_date TIMESTAMP WITH TIME ZONE
);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_scraped_grants_source ON scraped_grants(source);
CREATE INDEX IF NOT EXISTS idx_scraped_grants_deadline ON scraped_grants(deadline);
CREATE INDEX IF NOT EXISTS idx_scraped_grants_status ON scraped_grants(status);
CREATE INDEX IF NOT EXISTS idx_scraped_grants_created_at ON scraped_grants(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scraped_grants_cost_sharing ON scraped_grants(cost_sharing);
CREATE INDEX IF NOT EXISTS idx_scraped_grants_forecast_date ON scraped_grants(forecast_date);
CREATE INDEX IF NOT EXISTS idx_scraped_grants_archive_date ON scraped_grants(archive_date);

-- Enable Row Level Security (optional - adjust policies as needed)
ALTER TABLE scraped_grants ENABLE ROW LEVEL SECURITY;

-- Policy to allow all operations (adjust for production)
CREATE POLICY "Allow all operations on scraped_grants"
    ON scraped_grants
    FOR ALL
    USING (true);

-- Table for tracking scraper job runs
CREATE TABLE IF NOT EXISTS scraper_jobs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    job_name TEXT NOT NULL,
    status TEXT NOT NULL, -- 'running', 'completed', 'failed'
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    grants_found INTEGER DEFAULT 0,
    error TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Index for job history
CREATE INDEX IF NOT EXISTS idx_scraper_jobs_name ON scraper_jobs(job_name);
CREATE INDEX IF NOT EXISTS idx_scraper_jobs_started ON scraper_jobs(started_at DESC);

-- Comments for documentation
COMMENT ON TABLE scraped_grants IS 'Grants automatically collected by scheduled scrapers from various data sources';
COMMENT ON COLUMN scraped_grants.source IS 'Data source identifier: grants_gov, state, local, sam_gov, etc.';
COMMENT ON COLUMN scraped_grants.match_score IS 'AI-calculated relevance score (0-100) for Per Scholas mission alignment';
COMMENT ON TABLE scraper_jobs IS 'Historical log of scraper job executions';
