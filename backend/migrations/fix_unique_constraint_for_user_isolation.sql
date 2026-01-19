-- Fix unique constraint to allow same opportunity to be saved by different users
-- Drop the old unique constraint on just opportunity_id
ALTER TABLE saved_opportunities DROP CONSTRAINT IF EXISTS saved_opportunities_opportunity_id_key;

-- Create new unique constraint on (user_id, opportunity_id) so each user can save the same opportunity
ALTER TABLE saved_opportunities ADD CONSTRAINT saved_opportunities_user_opportunity_unique UNIQUE (user_id, opportunity_id);
