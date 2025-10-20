-- Add structured LLM insight columns to saved_opportunities table
-- These fields store the structured JSON output from the LLM enhancement service

ALTER TABLE saved_opportunities
ADD COLUMN IF NOT EXISTS winning_strategies JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS key_themes JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS recommended_metrics JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS considerations JSONB DEFAULT '[]'::jsonb;

-- Add comments for documentation
COMMENT ON COLUMN saved_opportunities.winning_strategies IS 'Specific strategies from similar winning proposals that apply here';
COMMENT ON COLUMN saved_opportunities.key_themes IS 'Theme/language patterns from winning proposals to incorporate';
COMMENT ON COLUMN saved_opportunities.recommended_metrics IS 'Metrics or evidence that won funding in past proposals';
COMMENT ON COLUMN saved_opportunities.considerations IS 'Important factors or requirements to address in the proposal';

-- Create GIN indexes for efficient JSON queries
CREATE INDEX IF NOT EXISTS idx_saved_opportunities_winning_strategies ON saved_opportunities USING GIN(winning_strategies);
CREATE INDEX IF NOT EXISTS idx_saved_opportunities_key_themes ON saved_opportunities USING GIN(key_themes);
CREATE INDEX IF NOT EXISTS idx_saved_opportunities_recommended_metrics ON saved_opportunities USING GIN(recommended_metrics);
CREATE INDEX IF NOT EXISTS idx_saved_opportunities_considerations ON saved_opportunities USING GIN(considerations);
