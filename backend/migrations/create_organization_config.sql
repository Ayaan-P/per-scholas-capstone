-- Create organization configuration table
CREATE TABLE IF NOT EXISTS organization_config (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL DEFAULT 'Your Organization',
    mission TEXT NOT NULL DEFAULT 'Advancing opportunity through education and community development',
    focus_areas JSONB DEFAULT '[]'::jsonb,
    impact_metrics JSONB DEFAULT '{}'::jsonb,
    programs JSONB DEFAULT '[]'::jsonb,
    target_demographics JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_organization_config_created ON organization_config(created_at DESC);

-- Allow only one organization config record (enforce via application logic)
ALTER TABLE organization_config ENABLE ROW LEVEL SECURITY;

-- Policy to allow all operations
CREATE POLICY "Allow all operations on organization_config"
    ON organization_config
    FOR ALL
    USING (true);

-- Create trigger to update updated_at timestamps
CREATE OR REPLACE FUNCTION update_organization_config_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_organization_config_updated_at BEFORE UPDATE ON organization_config
    FOR EACH ROW EXECUTE FUNCTION update_organization_config_timestamp();
