-- Migration: Create org_briefs table for Morning Brief History
-- This table stores the daily/periodic briefs sent to each organization
-- 
-- Run: psql $DATABASE_URL -f 002_org_briefs.sql
-- Or via Supabase SQL Editor
-- Created: 2025-02-10

-- ==============================================================================
-- TABLE: org_briefs - Morning Brief History
-- ==============================================================================
-- Tracks all briefs sent to organizations, including delivery status and engagement.

CREATE TABLE IF NOT EXISTS org_briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Organization reference
    org_id BIGINT NOT NULL REFERENCES organization_config(id) ON DELETE CASCADE,
    
    -- Brief content
    subject TEXT NOT NULL,                   -- Email subject or brief title
    content TEXT NOT NULL,                   -- Full brief content (Markdown or HTML)
    content_format TEXT DEFAULT 'markdown' CHECK (content_format IN ('markdown', 'html', 'plain')),
    
    -- Featured grants
    grant_ids UUID[] NOT NULL DEFAULT '{}',  -- Top 3 (or N) grants featured
    grant_summaries JSONB DEFAULT '[]'::jsonb, -- Snapshot of grant info at send time
    
    -- Selection metadata (why these grants were chosen)
    selection_criteria JSONB DEFAULT '{}'::jsonb,  -- Filters/weights used
    total_candidates INT,                          -- How many grants were considered
    
    -- Delivery
    delivery_channel TEXT NOT NULL DEFAULT 'email' CHECK (
        delivery_channel IN ('email', 'whatsapp', 'slack', 'in_app', 'sms')
    ),
    delivery_address TEXT,                   -- Email address, phone number, etc.
    scheduled_at TIMESTAMPTZ,                -- When brief was scheduled to send
    sent_at TIMESTAMPTZ,                     -- When actually sent
    delivered BOOLEAN DEFAULT FALSE,         -- Successfully delivered
    delivery_error TEXT,                     -- Error message if delivery failed
    delivery_attempts INT DEFAULT 0,         -- Number of send attempts
    
    -- Recipient(s)
    recipient_user_ids UUID[] DEFAULT '{}',  -- Which users received this brief
    
    -- Engagement tracking
    opened BOOLEAN DEFAULT FALSE,
    opened_at TIMESTAMPTZ,
    clicked_grant_ids UUID[] DEFAULT '{}',   -- Which grants got clicks
    click_events JSONB DEFAULT '[]'::jsonb,  -- Detailed click tracking [{grant_id, clicked_at, action}]
    
    -- User response
    user_response TEXT,                      -- If they replied to the brief
    response_sentiment TEXT CHECK (response_sentiment IN ('positive', 'neutral', 'negative')),
    response_at TIMESTAMPTZ,
    
    -- Agent metadata
    generated_by TEXT,                       -- Agent/model that created this brief
    generation_time_ms INT,                  -- How long brief generation took
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==============================================================================
-- INDEXES for Performance
-- ==============================================================================

-- Primary query: Get briefs for an org, most recent first
CREATE INDEX idx_org_briefs_org_sent 
    ON org_briefs(org_id, sent_at DESC);

-- Query pending/unsent briefs
CREATE INDEX idx_org_briefs_pending 
    ON org_briefs(scheduled_at) 
    WHERE delivered = FALSE;

-- Query by delivery channel
CREATE INDEX idx_org_briefs_channel 
    ON org_briefs(delivery_channel, sent_at DESC);

-- For engagement analytics
CREATE INDEX idx_org_briefs_opened 
    ON org_briefs(org_id, opened, sent_at DESC);

-- For finding briefs that featured specific grants
CREATE INDEX idx_org_briefs_grants 
    ON org_briefs USING GIN(grant_ids);

-- ==============================================================================
-- TRIGGER: Auto-update updated_at timestamp
-- ==============================================================================

CREATE OR REPLACE FUNCTION update_org_briefs_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_org_briefs_updated_at ON org_briefs;
CREATE TRIGGER trigger_org_briefs_updated_at
    BEFORE UPDATE ON org_briefs
    FOR EACH ROW EXECUTE FUNCTION update_org_briefs_timestamp();

-- ==============================================================================
-- ROW LEVEL SECURITY
-- ==============================================================================

ALTER TABLE org_briefs ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view briefs for their organization
CREATE POLICY "Users can view their org briefs"
    ON org_briefs FOR SELECT
    USING (
        org_id IN (
            SELECT organization_id FROM users 
            WHERE users.id = auth.uid()
        )
    );

-- Policy: Only service role can create/update briefs (agents send briefs)
CREATE POLICY "Service role can manage briefs"
    ON org_briefs FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- ==============================================================================
-- HELPER FUNCTION: Record brief engagement
-- ==============================================================================

CREATE OR REPLACE FUNCTION record_brief_opened(brief_id UUID)
RETURNS void AS $$
BEGIN
    UPDATE org_briefs
    SET opened = TRUE,
        opened_at = COALESCE(opened_at, NOW())
    WHERE id = brief_id
      AND opened = FALSE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION record_brief_click(
    brief_id UUID, 
    clicked_grant_id UUID,
    action TEXT DEFAULT 'view'
)
RETURNS void AS $$
BEGIN
    UPDATE org_briefs
    SET clicked_grant_ids = array_append(
            CASE WHEN clicked_grant_id = ANY(clicked_grant_ids) 
                 THEN clicked_grant_ids 
                 ELSE clicked_grant_ids 
            END,
            clicked_grant_id
        ),
        click_events = click_events || jsonb_build_object(
            'grant_id', clicked_grant_id,
            'clicked_at', NOW(),
            'action', action
        )
    WHERE id = brief_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ==============================================================================
-- COMMENTS for Documentation
-- ==============================================================================

COMMENT ON TABLE org_briefs IS 
    'History of morning briefs (or periodic summaries) sent to organizations. Tracks delivery and engagement.';

COMMENT ON COLUMN org_briefs.grant_ids IS 
    'Array of grant IDs (from scraped_grants) featured in this brief';

COMMENT ON COLUMN org_briefs.grant_summaries IS 
    'Snapshot of grant info at send time (in case grant data changes later)';

COMMENT ON COLUMN org_briefs.selection_criteria IS 
    'JSON object describing how grants were selected (filters, weights, urgency factors)';

COMMENT ON COLUMN org_briefs.click_events IS 
    'Detailed click tracking: [{grant_id, clicked_at, action}] for analytics';

COMMENT ON COLUMN org_briefs.generated_by IS 
    'Identifier of the agent/model that generated this brief (for A/B testing, debugging)';

-- ==============================================================================
-- SAMPLE VIEW: Brief Analytics
-- ==============================================================================

CREATE OR REPLACE VIEW org_brief_analytics AS
SELECT 
    org_id,
    COUNT(*) as total_briefs,
    COUNT(*) FILTER (WHERE delivered) as delivered_count,
    COUNT(*) FILTER (WHERE opened) as opened_count,
    ROUND(
        (COUNT(*) FILTER (WHERE opened)::numeric / NULLIF(COUNT(*) FILTER (WHERE delivered), 0)) * 100, 
        2
    ) as open_rate_pct,
    COUNT(*) FILTER (WHERE array_length(clicked_grant_ids, 1) > 0) as briefs_with_clicks,
    MAX(sent_at) as last_brief_sent,
    AVG(generation_time_ms) as avg_generation_time_ms
FROM org_briefs
GROUP BY org_id;

COMMENT ON VIEW org_brief_analytics IS 
    'Aggregated analytics per organization for brief engagement';

-- ==============================================================================
-- VERIFICATION QUERY
-- ==============================================================================
-- Run this after migration to verify the table was created:
-- SELECT column_name, data_type, is_nullable 
-- FROM information_schema.columns 
-- WHERE table_name = 'org_briefs'
-- ORDER BY ordinal_position;
