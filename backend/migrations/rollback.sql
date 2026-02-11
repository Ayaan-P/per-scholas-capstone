-- Rollback: Undo the agentic architecture migration
-- This script removes the new tables and restores the previous state
-- 
-- DANGER: This will DELETE all data in the new tables!
-- Only run this if you need to fully revert the migration.
-- 
-- Run: psql $DATABASE_URL -f rollback.sql
-- Or via Supabase SQL Editor
-- Created: 2025-02-10

-- ==============================================================================
-- CONFIRMATION CHECK
-- ==============================================================================
-- Uncomment the RAISE EXCEPTION to add a safety gate

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'ROLLBACK SCRIPT - AGENTIC ARCHITECTURE';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'This will DROP the following tables:';
    RAISE NOTICE '  - org_grants';
    RAISE NOTICE '  - org_briefs';
    RAISE NOTICE '  - user_saves';
    RAISE NOTICE '';
    RAISE NOTICE 'And remove associated:';
    RAISE NOTICE '  - Views (saved_opportunities_compat, user_saved_grants, org_brief_analytics)';
    RAISE NOTICE '  - Functions (record_brief_opened, record_brief_click)';
    RAISE NOTICE '  - Triggers and indexes';
    RAISE NOTICE '========================================';
    
    -- SAFETY GATE: Uncomment this to require explicit confirmation
    -- RAISE EXCEPTION 'SAFETY GATE: Comment out this line to proceed with rollback';
END $$;

-- ==============================================================================
-- STEP 1: Drop compatibility views
-- ==============================================================================

DROP VIEW IF EXISTS saved_opportunities_compat CASCADE;
DROP VIEW IF EXISTS user_saved_grants CASCADE;
DROP VIEW IF EXISTS org_brief_analytics CASCADE;

DO $$ BEGIN RAISE NOTICE 'Step 1: Dropped compatibility views'; END $$;

-- ==============================================================================
-- STEP 2: Drop helper functions
-- ==============================================================================

DROP FUNCTION IF EXISTS record_brief_opened(UUID) CASCADE;
DROP FUNCTION IF EXISTS record_brief_click(UUID, UUID, TEXT) CASCADE;

DO $$ BEGIN RAISE NOTICE 'Step 2: Dropped helper functions'; END $$;

-- ==============================================================================
-- STEP 3: Drop triggers
-- ==============================================================================

DROP TRIGGER IF EXISTS trigger_org_grants_updated_at ON org_grants;
DROP TRIGGER IF EXISTS trigger_org_briefs_updated_at ON org_briefs;
DROP TRIGGER IF EXISTS trigger_user_saves_updated_at ON user_saves;
DROP TRIGGER IF EXISTS trigger_user_saves_org_id ON user_saves;

DO $$ BEGIN RAISE NOTICE 'Step 3: Dropped triggers'; END $$;

-- ==============================================================================
-- STEP 4: Drop trigger functions
-- ==============================================================================

DROP FUNCTION IF EXISTS update_org_grants_timestamp() CASCADE;
DROP FUNCTION IF EXISTS update_org_briefs_timestamp() CASCADE;
DROP FUNCTION IF EXISTS update_user_saves_timestamp() CASCADE;
DROP FUNCTION IF EXISTS set_user_saves_org_id() CASCADE;

DO $$ BEGIN RAISE NOTICE 'Step 4: Dropped trigger functions'; END $$;

-- ==============================================================================
-- STEP 5: Record rollback in migration log
-- ==============================================================================

INSERT INTO migration_log (migration_name, completed_at, notes)
SELECT 
    'rollback_agentic_architecture',
    NOW(),
    jsonb_build_object(
        'org_grants_count_before', (SELECT COUNT(*) FROM org_grants),
        'org_briefs_count_before', (SELECT COUNT(*) FROM org_briefs),
        'user_saves_count_before', (SELECT COUNT(*) FROM user_saves),
        'reason', 'Manual rollback initiated'
    )::text
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'migration_log');

DO $$ BEGIN RAISE NOTICE 'Step 5: Recorded rollback in migration_log'; END $$;

-- ==============================================================================
-- STEP 6: Drop the new tables
-- ==============================================================================

-- Drop in reverse dependency order
DROP TABLE IF EXISTS user_saves CASCADE;
DROP TABLE IF EXISTS org_briefs CASCADE;
DROP TABLE IF EXISTS org_grants CASCADE;

DO $$ BEGIN RAISE NOTICE 'Step 6: Dropped new tables (org_grants, org_briefs, user_saves)'; END $$;

-- ==============================================================================
-- STEP 7: Restore saved_opportunities if it was renamed
-- ==============================================================================

DO $$
BEGIN
    -- If saved_opportunities was archived, restore it
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'saved_opportunities_archived'
    ) THEN
        ALTER TABLE saved_opportunities_archived RENAME TO saved_opportunities;
        RAISE NOTICE 'Step 7: Restored saved_opportunities from archive';
    ELSE
        RAISE NOTICE 'Step 7: saved_opportunities not archived, no restore needed';
    END IF;
END $$;

-- ==============================================================================
-- STEP 8: Restore original view if needed
-- ==============================================================================

DO $$
BEGIN
    -- Recreate the user_saved_opportunities view if it was dropped
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.views 
        WHERE table_name = 'user_saved_opportunities'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'saved_opportunities'
    ) THEN
        EXECUTE '
            CREATE OR REPLACE VIEW user_saved_opportunities AS
            SELECT
                id,
                user_id,
                opportunity_id,
                title,
                funder,
                amount,
                deadline,
                match_score,
                description,
                requirements,
                contact,
                application_url,
                source,
                llm_summary,
                detailed_match_reasoning,
                tags,
                winning_strategies,
                key_themes,
                recommended_metrics,
                considerations,
                similar_past_proposals,
                status,
                created_at,
                updated_at,
                saved_at
            FROM saved_opportunities
            WHERE user_id = auth.uid()
        ';
        RAISE NOTICE 'Step 8: Recreated user_saved_opportunities view';
    ELSE
        RAISE NOTICE 'Step 8: View restoration not needed';
    END IF;
END $$;

-- ==============================================================================
-- ROLLBACK COMPLETE
-- ==============================================================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'ROLLBACK COMPLETE';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'The agentic architecture tables have been removed.';
    RAISE NOTICE 'The system is back to using saved_opportunities.';
    RAISE NOTICE '';
    RAISE NOTICE 'If saved_opportunities was archived, it has been restored.';
    RAISE NOTICE 'Check your API endpoints are pointing to the correct tables.';
    RAISE NOTICE '========================================';
END $$;

-- ==============================================================================
-- VERIFICATION QUERY
-- ==============================================================================
-- Run this to verify rollback was successful:

-- SELECT 
--     'org_grants' as table_name, 
--     EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'org_grants') as exists
-- UNION ALL
-- SELECT 
--     'org_briefs', 
--     EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'org_briefs')
-- UNION ALL
-- SELECT 
--     'user_saves', 
--     EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'user_saves')
-- UNION ALL
-- SELECT 
--     'saved_opportunities', 
--     EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'saved_opportunities');
