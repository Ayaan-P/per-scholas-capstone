-- Migration: Add user_id column and RLS policies to saved_opportunities table
-- This ensures each user can only see their own saved grants

-- Step 1: Add user_id column to saved_opportunities
ALTER TABLE saved_opportunities
ADD COLUMN IF NOT EXISTS user_id UUID;

-- Step 2: Add foreign key constraint to auth.users
ALTER TABLE saved_opportunities
ADD CONSTRAINT fk_saved_opportunities_user_id
FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- Step 3: Create index on user_id for fast filtering
CREATE INDEX IF NOT EXISTS idx_saved_opportunities_user_id ON saved_opportunities(user_id);

-- Step 4: Drop old RLS policies if they exist
DROP POLICY IF EXISTS "Public read access" ON saved_opportunities;
DROP POLICY IF EXISTS "Enable insert for authenticated users only" ON saved_opportunities;
DROP POLICY IF EXISTS "Enable update for authenticated users only" ON saved_opportunities;
DROP POLICY IF EXISTS "Enable delete for authenticated users only" ON saved_opportunities;

-- Step 5: Enable RLS
ALTER TABLE saved_opportunities ENABLE ROW LEVEL SECURITY;

-- Step 6: Create new RLS policies for user isolation
-- Policy 1: Users can only view their own saved opportunities
CREATE POLICY "Users can view own saved opportunities"
ON saved_opportunities
FOR SELECT
USING (user_id = auth.uid());

-- Policy 2: Users can insert opportunities for themselves
CREATE POLICY "Users can save their own opportunities"
ON saved_opportunities
FOR INSERT
WITH CHECK (user_id = auth.uid());

-- Policy 3: Users can update their own opportunities
CREATE POLICY "Users can update own opportunities"
ON saved_opportunities
FOR UPDATE
USING (user_id = auth.uid())
WITH CHECK (user_id = auth.uid());

-- Policy 4: Users can delete their own opportunities
CREATE POLICY "Users can delete own opportunities"
ON saved_opportunities
FOR DELETE
USING (user_id = auth.uid());

-- Step 7: Create a view for convenient querying
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
WHERE user_id = auth.uid();

-- Verification queries (run after migration completes):
-- SELECT COUNT(*) as total_saved FROM saved_opportunities;
-- SELECT user_id, COUNT(*) as count FROM saved_opportunities GROUP BY user_id;
-- SELECT * FROM user_saved_opportunities; -- Should show only your saved opportunities
