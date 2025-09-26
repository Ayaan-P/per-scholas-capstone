-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create RFPs table with vector embeddings
CREATE TABLE IF NOT EXISTS rfps (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('Federal', 'Local-State')),
    file_path TEXT,
    content TEXT,
    embedding vector(384),  -- all-MiniLM-L6-v2 produces 384-dimensional vectors
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS rfps_embedding_idx ON rfps
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create saved opportunities table to link with RFP matches
CREATE TABLE IF NOT EXISTS saved_opportunities (
    id BIGSERIAL PRIMARY KEY,
    opportunity_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    funder TEXT,
    amount INTEGER,
    deadline DATE,
    description TEXT,
    requirements JSONB,
    contact TEXT,
    application_url TEXT,
    match_score INTEGER,
    embedding vector(384),
    saved_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for opportunity embeddings
CREATE INDEX IF NOT EXISTS saved_opportunities_embedding_idx ON saved_opportunities
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create proposals table for storing past proposals
CREATE TABLE IF NOT EXISTS proposals (
    id BIGSERIAL PRIMARY KEY,
    rfp_id BIGINT REFERENCES rfps(id),
    title TEXT NOT NULL,
    status TEXT CHECK (status IN ('submitted', 'awarded', 'rejected', 'in_progress')),
    submission_date DATE,
    award_amount INTEGER,
    content TEXT,  -- Proposal content/summary
    file_path TEXT,  -- Path to proposal document
    lessons_learned TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create function to match RFPs by semantic similarity
CREATE OR REPLACE FUNCTION match_rfps(
    query_embedding vector(384),
    match_threshold float DEFAULT 0.5,
    match_count int DEFAULT 3
)
RETURNS TABLE (
    id bigint,
    title text,
    category text,
    content text,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        rfps.id,
        rfps.title,
        rfps.category,
        rfps.content,
        1 - (rfps.embedding <=> query_embedding) as similarity
    FROM rfps
    WHERE 1 - (rfps.embedding <=> query_embedding) > match_threshold
    ORDER BY rfps.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Create function to find similar saved opportunities
CREATE OR REPLACE FUNCTION match_opportunities(
    query_embedding vector(384),
    match_threshold float DEFAULT 0.5,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id bigint,
    opportunity_id text,
    title text,
    funder text,
    amount integer,
    description text,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        saved_opportunities.id,
        saved_opportunities.opportunity_id,
        saved_opportunities.title,
        saved_opportunities.funder,
        saved_opportunities.amount,
        saved_opportunities.description,
        1 - (saved_opportunities.embedding <=> query_embedding) as similarity
    FROM saved_opportunities
    WHERE 1 - (saved_opportunities.embedding <=> query_embedding) > match_threshold
    ORDER BY saved_opportunities.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Create triggers to update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_rfps_updated_at BEFORE UPDATE ON rfps
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_proposals_updated_at BEFORE UPDATE ON proposals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert some sample data (if needed for testing)
-- This would be replaced by actual RFP loading process