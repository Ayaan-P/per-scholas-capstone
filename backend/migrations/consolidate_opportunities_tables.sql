-- Migration: Consolidate opportunities and saved_opportunities into one unified table
-- Run this in Supabase SQL Editor

-- Step 1: Add LLM enhancement columns to saved_opportunities
ALTER TABLE saved_opportunities
ADD COLUMN IF NOT EXISTS llm_summary TEXT,
ADD COLUMN IF NOT EXISTS detailed_match_reasoning TEXT,
ADD COLUMN IF NOT EXISTS tags TEXT[],
ADD COLUMN IF NOT EXISTS similar_past_proposals JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active',
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Step 2: Create index for tags
CREATE INDEX IF NOT EXISTS idx_saved_opportunities_tags ON saved_opportunities USING GIN(tags);

-- Step 3: Create trigger for updated_at
CREATE OR REPLACE FUNCTION update_saved_opportunities_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_saved_opportunities_updated_at_trigger ON saved_opportunities;
CREATE TRIGGER update_saved_opportunities_updated_at_trigger
BEFORE UPDATE ON saved_opportunities
FOR EACH ROW EXECUTE FUNCTION update_saved_opportunities_updated_at();

-- Step 4: Migrate data from opportunities to saved_opportunities
-- Cast TEXT[] requirements to JSONB
INSERT INTO saved_opportunities (
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
    llm_summary,
    detailed_match_reasoning,
    tags,
    similar_past_proposals,
    status,
    created_at,
    source
)
SELECT
    o.id as opportunity_id,
    o.title,
    o.funder,
    o.amount,
    o.deadline,
    o.match_score,
    o.description,
    to_jsonb(o.requirements) as requirements,
    o.contact,
    o.application_url,
    o.llm_summary,
    o.detailed_match_reasoning,
    o.tags,
    o.similar_past_proposals,
    'active' as status,
    o.created_at,
    'migrated' as source
FROM opportunities o
WHERE NOT EXISTS (
    SELECT 1 FROM saved_opportunities so
    WHERE so.opportunity_id = o.id
)
ON CONFLICT (opportunity_id) DO UPDATE SET
    llm_summary = COALESCE(EXCLUDED.llm_summary, saved_opportunities.llm_summary),
    detailed_match_reasoning = COALESCE(EXCLUDED.detailed_match_reasoning, saved_opportunities.detailed_match_reasoning),
    tags = COALESCE(EXCLUDED.tags, saved_opportunities.tags),
    similar_past_proposals = COALESCE(EXCLUDED.similar_past_proposals, saved_opportunities.similar_past_proposals);

-- Step 5: Rename opportunities table to opportunities_deprecated
ALTER TABLE IF EXISTS opportunities RENAME TO opportunities_deprecated;

-- Step 6: Document the change
COMMENT ON TABLE saved_opportunities IS 'Unified opportunities table with vector embeddings and LLM enhancements. Replaces deprecated opportunities table.';

-- Verification (run these separately after migration)
-- SELECT COUNT(*) as saved_count FROM saved_opportunities;
-- SELECT COUNT(*) as deprecated_count FROM opportunities_deprecated;
