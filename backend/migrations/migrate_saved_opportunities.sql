-- Migration: Move data from saved_opportunities to org_grants and user_saves
-- This script safely migrates existing data to the new agentic architecture
-- 
-- IMPORTANT: Run this AFTER 001_org_grants.sql, 002_org_briefs.sql, 003_user_saves.sql
-- 
-- Run: psql $DATABASE_URL -f migrate_saved_opportunities.sql
-- Or via Supabase SQL Editor
-- Created: 2025-02-10

-- ==============================================================================
-- PRE-MIGRATION CHECKS
-- ==============================================================================

DO $$
DECLARE
    saved_count INT;
    org_grants_exists BOOLEAN;
    user_saves_exists BOOLEAN;
BEGIN
    -- Check source table exists and has data
    SELECT COUNT(*) INTO saved_count FROM saved_opportunities;
    RAISE NOTICE 'Found % records in saved_opportunities', saved_count;
    
    -- Check target tables exist
    SELECT EXISTS(
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'org_grants'
    ) INTO org_grants_exists;
    
    SELECT EXISTS(
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'user_saves'
    ) INTO user_saves_exists;
    
    IF NOT org_grants_exists THEN
        RAISE EXCEPTION 'org_grants table does not exist. Run 001_org_grants.sql first.';
    END IF;
    
    IF NOT user_saves_exists THEN
        RAISE EXCEPTION 'user_saves table does not exist. Run 003_user_saves.sql first.';
    END IF;
    
    RAISE NOTICE 'Pre-migration checks passed. Ready to migrate.';
END $$;

-- ==============================================================================
-- STEP 1: Create temporary mapping table for opportunity_id -> grant_id
-- ==============================================================================
-- saved_opportunities uses TEXT opportunity_id, scraped_grants uses UUID id
-- We need to map between them

CREATE TEMP TABLE opportunity_grant_mapping AS
SELECT 
    so.id as saved_opp_id,
    so.opportunity_id as external_id,
    so.user_id,
    sg.id as grant_id
FROM saved_opportunities so
LEFT JOIN scraped_grants sg ON sg.opportunity_id = so.opportunity_id;

-- Report unmapped opportunities (these won't be migrated to org_grants)
DO $$
DECLARE
    unmapped_count INT;
BEGIN
    SELECT COUNT(*) INTO unmapped_count 
    FROM opportunity_grant_mapping 
    WHERE grant_id IS NULL;
    
    IF unmapped_count > 0 THEN
        RAISE NOTICE 'WARNING: % saved_opportunities have no matching scraped_grants (will be skipped for org_grants)', unmapped_count;
    END IF;
END $$;

-- ==============================================================================
-- STEP 2: Migrate to user_saves (personal bookmarks)
-- ==============================================================================
-- First, migrate opportunities that have matching scraped_grants

INSERT INTO user_saves (
    user_id,
    grant_id,
    org_id,
    folder,
    notes,
    saved_at,
    updated_at
)
SELECT 
    so.user_id,
    m.grant_id,
    u.organization_id as org_id,
    CASE 
        WHEN so.status = 'saved' THEN 'Saved'
        WHEN so.status = 'active' THEN 'Active'
        ELSE 'Migrated'
    END as folder,
    -- Combine any notes or context we might want to preserve
    NULLIF(TRIM(COALESCE(so.detailed_match_reasoning, '')), '') as notes,
    COALESCE(so.saved_at, so.created_at) as saved_at,
    COALESCE(so.updated_at, NOW()) as updated_at
FROM saved_opportunities so
JOIN opportunity_grant_mapping m ON m.saved_opp_id = so.id
LEFT JOIN users u ON u.id = so.user_id
WHERE m.grant_id IS NOT NULL
  AND so.user_id IS NOT NULL
ON CONFLICT (user_id, grant_id) DO UPDATE SET
    notes = COALESCE(EXCLUDED.notes, user_saves.notes),
    updated_at = NOW();

DO $$
DECLARE
    migrated_count INT;
BEGIN
    GET DIAGNOSTICS migrated_count = ROW_COUNT;
    RAISE NOTICE 'Migrated % records to user_saves', migrated_count;
END $$;

-- ==============================================================================
-- STEP 3: Migrate to org_grants (org-level AI analysis)
-- ==============================================================================
-- Group by org and grant to create org_grants entries

INSERT INTO org_grants (
    org_id,
    grant_id,
    status,
    match_score,
    llm_summary,
    match_reasoning,
    key_tags,
    effort_estimate,
    winning_strategies,
    key_themes,
    recommended_metrics,
    considerations,
    saved_at,
    saved_by,
    scored_at,
    scored_by,
    created_at,
    updated_at
)
SELECT DISTINCT ON (u.organization_id, m.grant_id)
    u.organization_id as org_id,
    m.grant_id,
    CASE 
        WHEN so.status IN ('applied', 'submitted') THEN 'applied'
        WHEN so.status = 'saved' THEN 'saved'
        WHEN so.status = 'dismissed' THEN 'dismissed'
        ELSE 'active'
    END as status,
    so.match_score,
    so.llm_summary,
    so.detailed_match_reasoning as match_reasoning,
    so.tags as key_tags,
    'medium' as effort_estimate, -- Default, can be re-scored later
    so.winning_strategies,
    so.key_themes,
    so.recommended_metrics,
    so.considerations,
    COALESCE(so.saved_at, so.created_at) as saved_at,
    so.user_id as saved_by,
    COALESCE(so.created_at, NOW()) as scored_at,
    'migrated_from_saved_opportunities' as scored_by,
    COALESCE(so.created_at, NOW()) as created_at,
    NOW() as updated_at
FROM saved_opportunities so
JOIN opportunity_grant_mapping m ON m.saved_opp_id = so.id
JOIN users u ON u.id = so.user_id
WHERE m.grant_id IS NOT NULL
  AND so.user_id IS NOT NULL
  AND u.organization_id IS NOT NULL
ORDER BY u.organization_id, m.grant_id, so.updated_at DESC
ON CONFLICT (org_id, grant_id) DO UPDATE SET
    -- Preserve existing if conflict, but update LLM fields if they're better
    llm_summary = COALESCE(EXCLUDED.llm_summary, org_grants.llm_summary),
    match_reasoning = COALESCE(EXCLUDED.match_reasoning, org_grants.match_reasoning),
    key_tags = COALESCE(EXCLUDED.key_tags, org_grants.key_tags),
    winning_strategies = CASE 
        WHEN org_grants.winning_strategies = '[]'::jsonb THEN EXCLUDED.winning_strategies
        ELSE org_grants.winning_strategies
    END,
    updated_at = NOW();

DO $$
DECLARE
    migrated_count INT;
BEGIN
    GET DIAGNOSTICS migrated_count = ROW_COUNT;
    RAISE NOTICE 'Migrated % records to org_grants', migrated_count;
END $$;

-- ==============================================================================
-- STEP 4: Create migration log entry
-- ==============================================================================

CREATE TABLE IF NOT EXISTS migration_log (
    id SERIAL PRIMARY KEY,
    migration_name TEXT NOT NULL,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    records_processed INT,
    notes TEXT
);

INSERT INTO migration_log (migration_name, completed_at, notes)
SELECT 
    'saved_opportunities_to_agentic',
    NOW(),
    jsonb_build_object(
        'source_count', (SELECT COUNT(*) FROM saved_opportunities),
        'user_saves_count', (SELECT COUNT(*) FROM user_saves),
        'org_grants_count', (SELECT COUNT(*) FROM org_grants),
        'unmapped_count', (SELECT COUNT(*) FROM opportunity_grant_mapping WHERE grant_id IS NULL)
    )::text;

-- ==============================================================================
-- STEP 5: Create backward compatibility view
-- ==============================================================================
-- This view makes the old code still work during transition

CREATE OR REPLACE VIEW saved_opportunities_compat AS
SELECT 
    og.id,
    sg.opportunity_id,
    us.user_id,
    sg.title,
    sg.funder,
    sg.amount,
    sg.deadline,
    sg.description,
    sg.requirements,
    sg.contact,
    sg.application_url,
    og.match_score,
    sg.source,
    og.llm_summary,
    og.match_reasoning as detailed_match_reasoning,
    og.key_tags as tags,
    og.winning_strategies,
    og.key_themes,
    og.recommended_metrics,
    og.considerations,
    '{}'::jsonb as similar_past_proposals,
    og.status,
    og.created_at,
    og.updated_at,
    us.saved_at
FROM org_grants og
JOIN scraped_grants sg ON sg.id = og.grant_id
LEFT JOIN user_saves us ON us.grant_id = og.grant_id 
    AND us.org_id = og.org_id;

COMMENT ON VIEW saved_opportunities_compat IS 
    'Backward compatibility view for old code during migration. Use org_grants + scraped_grants directly.';

-- ==============================================================================
-- CLEANUP (commented out - run manually after verification)
-- ==============================================================================

-- After verifying migration is successful:
-- 
-- 1. Update your API endpoints to use org_grants + user_saves
-- 2. Run these cleanup commands:
--
-- DROP VIEW IF EXISTS user_saved_opportunities CASCADE;
-- ALTER TABLE saved_opportunities RENAME TO saved_opportunities_archived;
-- 
-- Or if you want to keep the view for compatibility:
-- CREATE OR REPLACE VIEW saved_opportunities AS SELECT * FROM saved_opportunities_compat;

-- ==============================================================================
-- POST-MIGRATION VERIFICATION
-- ==============================================================================

DO $$
DECLARE
    source_count INT;
    user_saves_count INT;
    org_grants_count INT;
BEGIN
    SELECT COUNT(*) INTO source_count FROM saved_opportunities;
    SELECT COUNT(*) INTO user_saves_count FROM user_saves;
    SELECT COUNT(*) INTO org_grants_count FROM org_grants;
    
    RAISE NOTICE '========================================';
    RAISE NOTICE 'MIGRATION COMPLETE';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Source (saved_opportunities): % records', source_count;
    RAISE NOTICE 'Target (user_saves): % records', user_saves_count;
    RAISE NOTICE 'Target (org_grants): % records', org_grants_count;
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Verify data integrity manually';
    RAISE NOTICE '2. Update API endpoints to use new tables';
    RAISE NOTICE '3. Run rollback.sql if issues found';
    RAISE NOTICE '4. Archive saved_opportunities when ready';
    RAISE NOTICE '========================================';
END $$;

-- Drop temporary table
DROP TABLE IF EXISTS opportunity_grant_mapping;
