-- Migration: Temporarily disable user_id foreign key to unblock saving
-- Issue: auth.users table doesn't have all the user_ids being saved
-- Temporary solution: Remove FK constraint until auth setup is complete
-- TODO: Re-enable after fixing auth system

ALTER TABLE saved_opportunities
DROP CONSTRAINT IF EXISTS fk_saved_opportunities_user_id;

-- Note: This allows NULL user_id and non-existent user_ids
-- We'll re-enable the constraint after fixing Supabase auth setup
-- SELECT * FROM saved_opportunities WHERE user_id IS NOT NULL;
