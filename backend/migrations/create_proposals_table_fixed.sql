-- Enable pgvector extension first (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- Drop table if exists to start fresh
DROP TABLE IF EXISTS proposals;

-- Create proposals table
CREATE TABLE proposals (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    file_path TEXT,
    content TEXT,
    embedding vector(384),
    rfp_name TEXT,
    outcome TEXT,
    submission_date DATE,
    award_amount INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create vector similarity index
CREATE INDEX proposals_embedding_idx ON proposals
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create regular indexes
CREATE INDEX idx_proposals_category ON proposals(category);
CREATE INDEX idx_proposals_outcome ON proposals(outcome);
CREATE INDEX idx_proposals_rfp_name ON proposals(rfp_name);

-- Create similarity search function
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
