-- Migration: Fix foreign key constraint to allow NULL user_id
-- Some saved_opportunities have NULL user_id (before migration), so we need to handle that
-- Solution: Drop the strict FK and allow NULL values

-- Drop the existing foreign key constraint
ALTER TABLE saved_opportunities
DROP CONSTRAINT IF EXISTS fk_saved_opportunities_user_id;

-- Re-add with proper handling of NULL values
-- PostgreSQL foreign keys automatically allow NULL, so just re-create without changes
ALTER TABLE saved_opportunities
ADD CONSTRAINT fk_saved_opportunities_user_id
FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
NOT DEFERRABLE;

-- Verify constraint
SELECT constraint_name, table_name
FROM information_schema.table_constraints
WHERE table_name = 'saved_opportunities' AND constraint_type = 'FOREIGN KEY';
