-- Add LLM enhancement columns to opportunities table

ALTER TABLE opportunities
ADD COLUMN IF NOT EXISTS llm_summary TEXT,
ADD COLUMN IF NOT EXISTS detailed_match_reasoning TEXT,
ADD COLUMN IF NOT EXISTS tags TEXT[],
ADD COLUMN IF NOT EXISTS similar_past_proposals JSONB DEFAULT '[]'::jsonb;

-- Add index for tags
CREATE INDEX IF NOT EXISTS idx_opportunities_tags ON opportunities USING GIN(tags);
