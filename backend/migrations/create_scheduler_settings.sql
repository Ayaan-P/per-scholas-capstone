-- Create scheduler_settings table for user preferences on scheduled jobs
CREATE TABLE IF NOT EXISTS scheduler_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Scheduler frequency preferences
    scheduler_frequency VARCHAR(20) DEFAULT 'weekly' CHECK (scheduler_frequency IN ('daily', 'weekly', 'biweekly', 'monthly')),

    -- Target locations for AI state/local opportunity scraping
    selected_states TEXT[] DEFAULT ARRAY['CA', 'NY', 'TX', 'GA', 'MD', 'MA', 'IL', 'CO', 'MI', 'IN', 'MO', 'PA', 'NC', 'FL', 'AZ', 'WA', 'VA', 'OH', 'TN'],
    selected_cities TEXT[] DEFAULT ARRAY['Los Angeles/San Francisco', 'New York/Newark', 'Dallas/Houston', 'Atlanta', 'Baltimore', 'Boston', 'Chicago', 'Denver', 'Detroit', 'Indianapolis', 'Kansas City/St. Louis', 'Philadelphia/Pittsburgh', 'Charlotte/Raleigh', 'Orlando/Tampa/Miami', 'Phoenix', 'Seattle', 'Washington DC/Virginia', 'Cincinnati/Columbus/Cleveland', 'Nashville'],

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for quick lookups
CREATE INDEX idx_scheduler_settings_updated_at ON scheduler_settings(updated_at);

-- Add RLS (Row Level Security) policies if needed
ALTER TABLE scheduler_settings ENABLE ROW LEVEL SECURITY;

-- Create policy to allow all reads and writes (can be restricted to specific users later)
CREATE POLICY "Allow all operations on scheduler_settings" ON scheduler_settings
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_scheduler_settings_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update updated_at
DROP TRIGGER IF EXISTS scheduler_settings_update_timestamp ON scheduler_settings;
CREATE TRIGGER scheduler_settings_update_timestamp
    BEFORE UPDATE ON scheduler_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_scheduler_settings_timestamp();
