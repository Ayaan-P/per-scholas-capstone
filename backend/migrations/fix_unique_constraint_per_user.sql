-- Migration: Fix unique constraint on opportunity_id to be per-user, not global
-- Current constraint: UNIQUE(opportunity_id) - prevents ANY user from saving the same opportunity
-- Fixed constraint: UNIQUE(opportunity_id, user_id) - allows each user to save once

-- Step 1: Drop the old global unique constraint
ALTER TABLE saved_opportunities
DROP CONSTRAINT IF EXISTS saved_opportunities_opportunity_id_key;

-- Step 2: Create new unique constraint that's per-user
ALTER TABLE saved_opportunities
ADD CONSTRAINT saved_opportunities_opportunity_id_user_id_key
UNIQUE (opportunity_id, user_id);

-- Step 3: Verify the constraint
SELECT constraint_name, constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'saved_opportunities' AND constraint_type = 'UNIQUE'
ORDER BY constraint_name;
