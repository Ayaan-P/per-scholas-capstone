-- Create users table linked to organization_config
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    organization_id BIGINT REFERENCES organization_config(id) ON DELETE CASCADE,
    role TEXT DEFAULT 'admin', -- admin, member, viewer
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Link organization_config to a single owner user
ALTER TABLE organization_config ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES auth.users(id) ON DELETE SET NULL;

-- Create RLS policies for users table
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own profile"
    ON users FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile"
    ON users FOR UPDATE
    USING (auth.uid() = id);

-- RLS for organization_config - only organization members can access
ALTER TABLE organization_config ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow all operations on organization_config" ON organization_config;

CREATE POLICY "Organization members can access config"
    ON organization_config FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.organization_id = organization_config.id
            AND users.id = auth.uid()
        )
    );

-- Create index for faster user lookups
CREATE INDEX IF NOT EXISTS idx_users_organization_id ON users(organization_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_organization_config_owner_id ON organization_config(owner_id);

-- Create trigger to update users updated_at
CREATE OR REPLACE FUNCTION update_users_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_users_timestamp();
