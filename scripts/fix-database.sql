-- FundFish Database Cleanup
-- Run in Supabase SQL Editor

-- 1. Backfill null amounts from award_ceiling
UPDATE scraped_grants 
SET amount = COALESCE(award_ceiling, award_floor)
WHERE amount IS NULL;

-- 2. Normalize source names
UPDATE scraped_grants SET source = 'agent' WHERE source IN ('Agent', 'Agent
');
UPDATE scraped_grants SET source = 'grants_gov' WHERE source = 'grants.gov';

-- 3. Set default status where null
UPDATE scraped_grants SET status = 'active' WHERE status IS NULL;

-- 4. Remove exact duplicates by title (keep newest)
DELETE FROM scraped_grants a
USING scraped_grants b
WHERE a.id < b.id 
  AND a.title = b.title;

-- 5. Count results
SELECT 
  'Total grants' as metric, COUNT(*) as value FROM scraped_grants
UNION ALL
SELECT 'With amount', COUNT(*) FROM scraped_grants WHERE amount IS NOT NULL
UNION ALL
SELECT 'Active', COUNT(*) FROM scraped_grants WHERE status = 'active'
UNION ALL
SELECT 'Unique sources', COUNT(DISTINCT source) FROM scraped_grants;
