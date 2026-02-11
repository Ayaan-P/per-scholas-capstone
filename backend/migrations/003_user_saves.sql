-- Migration: Create user_saves table for User Bookmarks
-- This table allows individual users to bookmark/save grants for personal tracking
-- Separate from org_grants which is org-level AI-scored state
-- 
-- Run: psql $DATABASE_URL -f 003_user_saves.sql
-- Or via Supabase SQL Editor
-- Created: 2025-02-10

-- ==============================================================================
-- TABLE: user_saves - Personal User Bookmarks
-- ==============================================================================
-- Lightweight table for users to save/bookmark grants for personal tracking.
-- This is separate from org_grants which handles org-level workflow state.

CREATE TABLE IF NOT EXISTS user_saves (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- User reference (the person saving)
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Grant reference
    grant_id UUID NOT NULL REFERENCES scraped_grants(id) ON DELETE CASCADE,
    
    -- User's personal organization (for context, optional)
    -- Denormalized for query convenience
    org_id BIGINT REFERENCES organization_config(id) ON DELETE SET NULL,
    
    -- Personal organization
    folder TEXT DEFAULT 'Default',           -- User-defined folder/category
    priority TEXT CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    
    -- Personal notes
    notes TEXT,                              -- User's private notes about this grant
    
    -- Reminder
    reminder_at TIMESTAMPTZ,                 -- Optional reminder date
    reminder_sent BOOLEAN DEFAULT FALSE,
    
    -- Status flags
    is_archived BOOLEAN DEFAULT FALSE,       -- Archived (hidden from main view)
    is_pinned BOOLEAN DEFAULT FALSE,         -- Pinned to top
    
    -- Sharing (within org)
    shared_with_org BOOLEAN DEFAULT FALSE,   -- Visible to other org members
    
    -- Timestamps
    saved_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique: one save per user+grant
    UNIQUE(user_id, grant_id)
);

-- ==============================================================================
-- INDEXES for Performance
-- ==============================================================================

-- Primary query: Get user's saved grants
CREATE INDEX idx_user_saves_user 
    ON user_saves(user_id, saved_at DESC);

-- Filter by folder
CREATE INDEX idx_user_saves_folder 
    ON user_saves(user_id, folder, saved_at DESC);

-- Filter archived/active
CREATE INDEX idx_user_saves_active 
    ON user_saves(user_id, is_archived, saved_at DESC);

-- Find saves by grant (for analytics)
CREATE INDEX idx_user_saves_grant 
    ON user_saves(grant_id);

-- Upcoming reminders
CREATE INDEX idx_user_saves_reminders 
    ON user_saves(reminder_at) 
    WHERE reminder_at IS NOT NULL AND reminder_sent = FALSE;

-- Shared within org
CREATE INDEX idx_user_saves_shared 
    ON user_saves(org_id, shared_with_org) 
    WHERE shared_with_org = TRUE;

-- ==============================================================================
-- TRIGGER: Auto-update updated_at timestamp
-- ==============================================================================

CREATE OR REPLACE FUNCTION update_user_saves_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_user_saves_updated_at ON user_saves;
CREATE TRIGGER trigger_user_saves_updated_at
    BEFORE UPDATE ON user_saves
    FOR EACH ROW EXECUTE FUNCTION update_user_saves_timestamp();

-- ==============================================================================
-- TRIGGER: Auto-populate org_id from users table
-- ==============================================================================

CREATE OR REPLACE FUNCTION set_user_saves_org_id()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.org_id IS NULL THEN
        SELECT organization_id INTO NEW.org_id
        FROM users
        WHERE users.id = NEW.user_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_user_saves_org_id ON user_saves;
CREATE TRIGGER trigger_user_saves_org_id
    BEFORE INSERT ON user_saves
    FOR EACH ROW EXECUTE FUNCTION set_user_saves_org_id();

-- ==============================================================================
-- ROW LEVEL SECURITY
-- ==============================================================================

ALTER TABLE user_saves ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view their own saves
CREATE POLICY "Users can view own saves"
    ON user_saves FOR SELECT
    USING (user_id = auth.uid());

-- Policy: Users can view saves shared with their org
CREATE POLICY "Users can view org shared saves"
    ON user_saves FOR SELECT
    USING (
        shared_with_org = TRUE
        AND org_id IN (
            SELECT organization_id FROM users 
            WHERE users.id = auth.uid()
        )
    );

-- Policy: Users can insert their own saves
CREATE POLICY "Users can create own saves"
    ON user_saves FOR INSERT
    WITH CHECK (user_id = auth.uid());

-- Policy: Users can update their own saves
CREATE POLICY "Users can update own saves"
    ON user_saves FOR UPDATE
    USING (user_id = auth.uid());

-- Policy: Users can delete their own saves
CREATE POLICY "Users can delete own saves"
    ON user_saves FOR DELETE
    USING (user_id = auth.uid());

-- Policy: Service role can access all
CREATE POLICY "Service role full access on user_saves"
    ON user_saves FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- ==============================================================================
-- HELPER VIEW: User's saved grants with full details
-- ==============================================================================

CREATE OR REPLACE VIEW user_saved_grants AS
SELECT 
    us.id as save_id,
    us.user_id,
    us.grant_id,
    us.folder,
    us.priority,
    us.notes,
    us.reminder_at,
    us.is_archived,
    us.is_pinned,
    us.shared_with_org,
    us.saved_at,
    
    -- Grant details from scraped_grants
    sg.opportunity_id,
    sg.title,
    sg.funder,
    sg.amount,
    sg.deadline,
    sg.description,
    sg.source,
    sg.award_floor,
    sg.award_ceiling,
    
    -- Deadline urgency
    CASE 
        WHEN sg.deadline IS NULL THEN 'unknown'
        WHEN sg.deadline < CURRENT_DATE THEN 'expired'
        WHEN sg.deadline <= CURRENT_DATE + INTERVAL '7 days' THEN 'urgent'
        WHEN sg.deadline <= CURRENT_DATE + INTERVAL '30 days' THEN 'soon'
        ELSE 'future'
    END as deadline_urgency
    
FROM user_saves us
JOIN scraped_grants sg ON sg.id = us.grant_id
WHERE us.user_id = auth.uid();

COMMENT ON VIEW user_saved_grants IS 
    'User''s saved grants with full grant details. Filtered to authenticated user.';

-- ==============================================================================
-- COMMENTS for Documentation
-- ==============================================================================

COMMENT ON TABLE user_saves IS 
    'Personal user bookmarks for grants. Lightweight alternative to org_grants for individual tracking.';

COMMENT ON COLUMN user_saves.folder IS 
    'User-defined folder/category for organizing saves (e.g., High Priority, Research, Later)';

COMMENT ON COLUMN user_saves.notes IS 
    'User''s private notes about this grant - not visible to others';

COMMENT ON COLUMN user_saves.reminder_at IS 
    'Optional reminder date/time - user will be notified';

COMMENT ON COLUMN user_saves.shared_with_org IS 
    'If TRUE, other members of the user''s org can see this save (excluding private notes)';

-- ==============================================================================
-- VERIFICATION QUERY
-- ==============================================================================
-- Run this after migration to verify the table was created:
-- SELECT column_name, data_type, is_nullable 
-- FROM information_schema.columns 
-- WHERE table_name = 'user_saves'
-- ORDER BY ordinal_position;
