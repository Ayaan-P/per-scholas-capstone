-- Migration: Create proposals table for Per Scholas past proposal documents
-- This stores actual Per Scholas submissions with embeddings for similarity matching
-- Run this in Supabase SQL Editor
-- Created: 2025-10-19

-- Create proposals table
CREATE TABLE IF NOT EXISTS proposals (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL,  -- 'Federal' or 'State-Local'
    file_path TEXT,
    content TEXT,  -- Extracted text from proposal PDF
    embedding vector(384),  -- all-MiniLM-L6-v2 produces 384-dim vectors

    -- Metadata about the proposal
    rfp_name TEXT,  -- Which RFP this responded to (if known)
    outcome TEXT,  -- 'won', 'pending', 'declined', 'unknown'
    submission_date DATE,
    award_amount INTEGER,  -- If won, how much

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create vector similarity index using ivfflat
-- This enables fast cosine similarity searches
CREATE INDEX IF NOT EXISTS proposals_embedding_idx ON proposals
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_proposals_category ON proposals(category);
CREATE INDEX IF NOT EXISTS idx_proposals_outcome ON proposals(outcome);
CREATE INDEX IF NOT EXISTS idx_proposals_rfp_name ON proposals(rfp_name);

-- Add comments for documentation
COMMENT ON TABLE proposals IS 'Per Scholas past proposal submissions with embeddings for similarity matching';
COMMENT ON COLUMN proposals.title IS 'Proposal title extracted from filename';
COMMENT ON COLUMN proposals.content IS 'Full text extracted from proposal PDF (first 5000 chars)';
COMMENT ON COLUMN proposals.embedding IS 'Vector embedding of proposal content for semantic search';
COMMENT ON COLUMN proposals.rfp_name IS 'Name of RFP this proposal responded to (if identifiable)';
COMMENT ON COLUMN proposals.outcome IS 'Result of proposal: won, pending, declined, unknown';
COMMENT ON COLUMN proposals.award_amount IS 'Dollar amount awarded if proposal won';

-- Create function for similarity search
-- This is used by semantic_service.py to find similar proposals
CREATE OR REPLACE FUNCTION match_proposals(
    query_embedding vector(384),
    match_threshold float DEFAULT 0.5,
    match_count int DEFAULT 3
)
RETURNS TABLE (
    id bigint,
    title text,
    category text,
    content text,
    rfp_name text,
    outcome text,
    award_amount integer,
    file_path text,
    similarity_score float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        proposals.id,
        proposals.title,
        proposals.category,
        proposals.content,
        proposals.rfp_name,
        proposals.outcome,
        proposals.award_amount,
        proposals.file_path,
        1 - (proposals.embedding <=> query_embedding) as similarity_score
    FROM proposals
    WHERE 1 - (proposals.embedding <=> query_embedding) > match_threshold
    ORDER BY proposals.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Verification query
SELECT
    'proposals table created successfully' as status,
    COUNT(*) as proposal_count
FROM proposals;
