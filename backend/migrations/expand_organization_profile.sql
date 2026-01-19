-- Expand organization_config table with comprehensive nonprofit profile fields
-- This supports any nonprofit to provide rich, detailed organizational data for intelligent grant matching

-- Add comprehensive organization profile columns
ALTER TABLE organization_config
ADD COLUMN IF NOT EXISTS ein TEXT UNIQUE,
ADD COLUMN IF NOT EXISTS organization_type TEXT DEFAULT 'nonprofit', -- nonprofit, social-enterprise, government, etc.
ADD COLUMN IF NOT EXISTS tax_exempt_status TEXT DEFAULT 'pending', -- pending, 501c3, other, none
ADD COLUMN IF NOT EXISTS years_established INTEGER,
ADD COLUMN IF NOT EXISTS annual_budget BIGINT, -- in cents or dollars depending on preference
ADD COLUMN IF NOT EXISTS staff_size INTEGER,
ADD COLUMN IF NOT EXISTS board_size INTEGER,
ADD COLUMN IF NOT EXISTS primary_focus_area TEXT, -- Primary mission/focus
ADD COLUMN IF NOT EXISTS secondary_focus_areas TEXT[], -- Array of secondary areas
ADD COLUMN IF NOT EXISTS key_programs JSONB DEFAULT '[]'::jsonb, -- Array of program objects {name, description, beneficiaries}
ADD COLUMN IF NOT EXISTS service_regions TEXT[], -- Geographic areas served
ADD COLUMN IF NOT EXISTS expansion_plans TEXT, -- Future geographic or program expansion plans
ADD COLUMN IF NOT EXISTS target_populations TEXT[], -- e.g., "K-12 students", "low-income families", "underrepresented communities"
ADD COLUMN IF NOT EXISTS languages_served TEXT[] DEFAULT '{"English"}'::text[], -- Languages served/supported
ADD COLUMN IF NOT EXISTS key_partnerships JSONB DEFAULT '[]'::jsonb, -- Array of partnership descriptions
ADD COLUMN IF NOT EXISTS accreditations TEXT[], -- Certifications, accreditations (e.g., "COE", "B-Corp")
ADD COLUMN IF NOT EXISTS preferred_grant_size_min BIGINT, -- Minimum ideal grant amount (cents)
ADD COLUMN IF NOT EXISTS preferred_grant_size_max BIGINT, -- Maximum ideal grant amount (cents)
ADD COLUMN IF NOT EXISTS preferred_grant_types TEXT[], -- Types of funding (e.g., "project-based", "general-support", "capacity-building", "research")
ADD COLUMN IF NOT EXISTS funding_priorities JSONB DEFAULT '[]'::jsonb, -- Specific funding goals with priorities
ADD COLUMN IF NOT EXISTS custom_search_keywords TEXT[], -- Custom keywords for grant matching beyond focus area
ADD COLUMN IF NOT EXISTS excluded_keywords TEXT[], -- Keywords to exclude from matching
ADD COLUMN IF NOT EXISTS key_impact_metrics JSONB DEFAULT '[]'::jsonb, -- Metrics that matter {metric_name, current_value, target_value, unit}
ADD COLUMN IF NOT EXISTS previous_grants JSONB DEFAULT '[]'::jsonb, -- Reference to past grants {funder, amount, year, outcome}
ADD COLUMN IF NOT EXISTS donor_restrictions TEXT, -- Any restrictions on funding acceptance
ADD COLUMN IF NOT EXISTS grant_writing_capacity TEXT DEFAULT 'moderate', -- limited, moderate, advanced
ADD COLUMN IF NOT EXISTS matching_fund_capacity NUMERIC(5,2) DEFAULT 0, -- % able to match grants
ADD COLUMN IF NOT EXISTS success_stories JSONB DEFAULT '[]'::jsonb, -- Array of impact stories {title, description}
ADD COLUMN IF NOT EXISTS website_url TEXT,
ADD COLUMN IF NOT EXISTS contact_email TEXT,
ADD COLUMN IF NOT EXISTS contact_phone TEXT,
ADD COLUMN IF NOT EXISTS logo_url TEXT;

-- Create index for geographic filtering
CREATE INDEX IF NOT EXISTS idx_organization_service_regions ON organization_config USING GIN (service_regions);

-- Create index for focus area filtering
CREATE INDEX IF NOT EXISTS idx_organization_primary_focus ON organization_config(primary_focus_area);

-- Create index for annual budget (for grant size matching)
CREATE INDEX IF NOT EXISTS idx_organization_annual_budget ON organization_config(annual_budget);

-- Create index for organization type
CREATE INDEX IF NOT EXISTS idx_organization_type ON organization_config(organization_type);

-- Add constraint to ensure valid organization types
ALTER TABLE organization_config
ADD CONSTRAINT valid_organization_type CHECK (
    organization_type IN ('nonprofit', 'social-enterprise', 'government', 'educational-institution', 'faith-based', 'community-based', 'other')
);

-- Add constraint for valid grant writing capacity levels
ALTER TABLE organization_config
ADD CONSTRAINT valid_grant_capacity CHECK (
    grant_writing_capacity IN ('limited', 'moderate', 'advanced')
);

-- Add constraint for valid tax exempt status
ALTER TABLE organization_config
ADD CONSTRAINT valid_tax_status CHECK (
    tax_exempt_status IN ('pending', '501c3', '501c6', '501c7', 'other', 'none')
);

-- Create a view for easier querying of organization profiles
CREATE OR REPLACE VIEW organization_profiles AS
SELECT
    id,
    name,
    mission,
    primary_focus_area,
    secondary_focus_areas,
    service_regions,
    annual_budget,
    staff_size,
    organization_type,
    tax_exempt_status,
    preferred_grant_size_min,
    preferred_grant_size_max,
    key_programs,
    target_populations,
    languages_served,
    key_partnerships,
    accreditations,
    years_established,
    grant_writing_capacity,
    matching_fund_capacity,
    custom_search_keywords,
    excluded_keywords,
    key_impact_metrics,
    previous_grants,
    success_stories,
    website_url,
    contact_email,
    created_at,
    updated_at
FROM organization_config
WHERE id IS NOT NULL; -- Ensure the view is always valid

-- Update RLS policy to allow authenticated users to manage their own organization
DROP POLICY IF EXISTS "Allow all operations on organization_config" ON organization_config;

CREATE POLICY "Users can view and update their own organization"
    ON organization_config
    FOR ALL
    USING (
        -- If owner_id column exists, use it; otherwise allow (for backward compatibility)
        CASE WHEN EXISTS(
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'organization_config' AND column_name = 'owner_id'
        ) THEN
            owner_id = auth.uid()
        ELSE
            true
        END
    )
    WITH CHECK (
        CASE WHEN EXISTS(
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'organization_config' AND column_name = 'owner_id'
        ) THEN
            owner_id = auth.uid()
        ELSE
            true
        END
    );

-- Add comment documentation
COMMENT ON TABLE organization_config IS 'Comprehensive nonprofit organization profile supporting intelligent grant matching for any nonprofit sector';

COMMENT ON COLUMN organization_config.primary_focus_area IS 'Primary mission/sector (e.g., education, health, environment, arts, social-services)';

COMMENT ON COLUMN organization_config.custom_search_keywords IS 'Custom keywords to boost in grant search matching (e.g., ["trauma-informed", "LGBTQ-affirming"])';

COMMENT ON COLUMN organization_config.preferred_grant_size_min IS 'Minimum ideal grant size in cents (smaller grants may be inefficient to pursue)';

COMMENT ON COLUMN organization_config.preferred_grant_size_max IS 'Maximum ideal grant size in cents (very large grants may have unrealistic requirements)';

COMMENT ON COLUMN organization_config.key_impact_metrics IS 'Metrics this organization tracks {metric_name, current_value, target_value, unit} for outcome reporting';

COMMENT ON COLUMN organization_config.grant_writing_capacity IS 'Self-assessment of grant writing capacity to filter appropriate opportunities';

COMMENT ON COLUMN organization_config.matching_fund_capacity IS 'Percentage of grant awards this org can match as local funding';

COMMENT ON COLUMN organization_config.previous_grants IS 'Historical grant information for context {funder, amount, year, outcome, description}';

COMMENT ON COLUMN organization_config.donor_restrictions IS 'Any restrictions on funding sources (e.g., no government funds, no corporate funders)';
