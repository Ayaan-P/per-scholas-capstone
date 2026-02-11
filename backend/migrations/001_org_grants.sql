-- Migration: Create org_grants table for Agentic Architecture
-- This table stores org-specific state and AI analysis for grants
-- Each org gets scored grants from the qualification agent
-- 
-- Run: psql $DATABASE_URL -f 001_org_grants.sql
-- Or via Supabase SQL Editor
-- Created: 2025-02-10

-- ==============================================================================
-- TABLE: org_grants - Org-Specific Grant State & AI Analysis
-- ==============================================================================
-- This replaces the per-user saved_opportunities model with an org-centric model
-- where AI agents process and score grants for each organization.

CREATE TABLE IF NOT EXISTS org_grants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Foreign keys
    org_id BIGINT NOT NULL REFERENCES organization_config(id) ON DELETE CASCADE,
    grant_id UUID NOT NULL REFERENCES scraped_grants(id) ON DELETE CASCADE,
    
    -- Status tracking (workflow state)
    status TEXT NOT NULL DEFAULT 'active' CHECK (
        status IN ('active', 'dismissed', 'saved', 'applied', 'won', 'lost')
    ),
    
    -- AI-generated analysis (from qualification agent)
    match_score INT CHECK (match_score >= 0 AND match_score <= 100),
    llm_summary TEXT,                    -- Short 2-3 sentence summary
    match_reasoning TEXT,                -- Detailed reasoning (why this grant matches)
    key_tags TEXT[],                     -- Tags like ['workforce', 'tech-training', 'urban']
    
    -- Effort/strategy guidance
    effort_estimate TEXT CHECK (effort_estimate IN ('low', 'medium', 'high')),
    winning_strategies JSONB DEFAULT '[]'::jsonb,  -- Tips for application
    key_themes JSONB DEFAULT '[]'::jsonb,          -- Language patterns to incorporate
    recommended_metrics JSONB DEFAULT '[]'::jsonb, -- Evidence/metrics to include
    considerations JSONB DEFAULT '[]'::jsonb,      -- Important factors to address
    
    -- User actions
    dismissed_at TIMESTAMPTZ,
    dismissed_by UUID REFERENCES auth.users(id),
    dismissed_reason TEXT,               -- Optional reason for dismissal
    saved_at TIMESTAMPTZ,
    saved_by UUID REFERENCES auth.users(id),
    applied_at TIMESTAMPTZ,
    applied_by UUID REFERENCES auth.users(id),
    
    -- Outcome tracking
    outcome TEXT CHECK (outcome IN ('pending', 'won', 'lost', 'withdrawn')),
    outcome_notes TEXT,
    outcome_at TIMESTAMPTZ,
    
    -- Agent tracking
    scored_at TIMESTAMPTZ DEFAULT NOW(),   -- When agent last scored this
    scored_by TEXT,                        -- Agent identifier (for debugging)
    score_version INT DEFAULT 1,           -- Version of scoring algorithm
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint: one entry per org+grant combination
    UNIQUE(org_id, grant_id)
);

-- ==============================================================================
-- INDEXES for Performance
-- ==============================================================================

-- Primary query pattern: Get grants for an org filtered by status, sorted by score
CREATE INDEX idx_org_grants_org_status_score 
    ON org_grants(org_id, status, match_score DESC);

-- Query by grant_id (e.g., find all orgs that have scored this grant)
CREATE INDEX idx_org_grants_grant 
    ON org_grants(grant_id);

-- For deadline-aware queries (joining with scraped_grants)
CREATE INDEX idx_org_grants_org_status 
    ON org_grants(org_id, status);

-- For agent processing (find unscored or stale scores)
CREATE INDEX idx_org_grants_scored_at 
    ON org_grants(scored_at);

-- GIN index for tag searching
CREATE INDEX idx_org_grants_tags 
    ON org_grants USING GIN(key_tags);

-- ==============================================================================
-- TRIGGER: Auto-update updated_at timestamp
-- ==============================================================================

CREATE OR REPLACE FUNCTION update_org_grants_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_org_grants_updated_at ON org_grants;
CREATE TRIGGER trigger_org_grants_updated_at
    BEFORE UPDATE ON org_grants
    FOR EACH ROW EXECUTE FUNCTION update_org_grants_timestamp();

-- ==============================================================================
-- ROW LEVEL SECURITY
-- ==============================================================================

ALTER TABLE org_grants ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view org_grants for their organization
CREATE POLICY "Users can view their org grants"
    ON org_grants FOR SELECT
    USING (
        org_id IN (
            SELECT organization_id FROM users 
            WHERE users.id = auth.uid()
        )
    );

-- Policy: Users can insert grants for their organization
CREATE POLICY "Users can add grants to their org"
    ON org_grants FOR INSERT
    WITH CHECK (
        org_id IN (
            SELECT organization_id FROM users 
            WHERE users.id = auth.uid()
        )
    );

-- Policy: Users can update grants for their organization
CREATE POLICY "Users can update their org grants"
    ON org_grants FOR UPDATE
    USING (
        org_id IN (
            SELECT organization_id FROM users 
            WHERE users.id = auth.uid()
        )
    );

-- Policy: Users can delete grants from their organization
CREATE POLICY "Users can delete their org grants"
    ON org_grants FOR DELETE
    USING (
        org_id IN (
            SELECT organization_id FROM users 
            WHERE users.id = auth.uid()
        )
    );

-- Policy: Service role (backend/agents) can do anything
CREATE POLICY "Service role full access on org_grants"
    ON org_grants FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- ==============================================================================
-- COMMENTS for Documentation
-- ==============================================================================

COMMENT ON TABLE org_grants IS 
    'Org-specific grant state and AI analysis. Each organization gets scored grants from the qualification agent.';

COMMENT ON COLUMN org_grants.status IS 
    'Workflow state: active (new/scored), dismissed (rejected), saved (bookmarked), applied (submitted), won/lost';

COMMENT ON COLUMN org_grants.match_score IS 
    'AI-calculated relevance score 0-100 based on org profile, mission alignment, and capacity';

COMMENT ON COLUMN org_grants.llm_summary IS 
    'Brief AI-generated summary (2-3 sentences) of why this grant might be a fit';

COMMENT ON COLUMN org_grants.match_reasoning IS 
    'Detailed AI reasoning explaining the match score and key alignment factors';

COMMENT ON COLUMN org_grants.key_tags IS 
    'Extracted tags for filtering (e.g., workforce, education, urban, equity)';

COMMENT ON COLUMN org_grants.effort_estimate IS 
    'AI estimate of application effort: low (simple), medium (moderate), high (complex)';

COMMENT ON COLUMN org_grants.winning_strategies IS 
    'JSON array of strategies from similar winning proposals that apply here';

COMMENT ON COLUMN org_grants.scored_by IS 
    'Identifier of the agent/model that generated this score (for debugging/versioning)';

-- ==============================================================================
-- VERIFICATION QUERY
-- ==============================================================================
-- Run this after migration to verify the table was created:
-- SELECT column_name, data_type, is_nullable 
-- FROM information_schema.columns 
-- WHERE table_name = 'org_grants'
-- ORDER BY ordinal_position;
