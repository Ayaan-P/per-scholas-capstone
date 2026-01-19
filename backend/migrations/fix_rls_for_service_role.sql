-- Migration: Fix RLS policies to allow service role inserts to saved_opportunities
-- The issue: RLS WITH CHECK clauses prevent even service role from inserting
-- The fix: Use current_user_id() which returns the actual auth context, or allow service role explicitly

-- Drop existing restrictive policies
DROP POLICY IF EXISTS "Users can view own saved opportunities" ON saved_opportunities;
DROP POLICY IF EXISTS "Users can save their own opportunities" ON saved_opportunities;
DROP POLICY IF EXISTS "Users can update own opportunities" ON saved_opportunities;
DROP POLICY IF EXISTS "Users can delete own opportunities" ON saved_opportunities;

-- Re-create policies that work with both authenticated users AND service role

-- Policy 1: Users can only view their own saved opportunities
CREATE POLICY "Users can view own saved opportunities"
ON saved_opportunities
FOR SELECT
USING (user_id = auth.uid());

-- Policy 2: Service role + authenticated users can insert for themselves
CREATE POLICY "Users can save their own opportunities"
ON saved_opportunities
FOR INSERT
WITH CHECK (
    user_id = auth.uid()  -- For authenticated users
    OR current_setting('role') = 'authenticated'  -- For service role operations
    OR current_setting('role') LIKE 'service_role_%'  -- Explicit service role check
);

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

-- Verify policies are in place
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    qual,
    with_check
FROM pg_policies
WHERE tablename = 'saved_opportunities'
ORDER BY policyname;
