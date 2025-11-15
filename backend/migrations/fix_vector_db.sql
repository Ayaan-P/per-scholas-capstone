-- Fix Vector Database Schema and Functions
-- Run this in your Supabase SQL editor

-- 1. First, enable pgvector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create new table with proper vector type
CREATE TABLE IF NOT EXISTS rfps_new (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    file_path TEXT,
    content TEXT,
    embedding vector(384),  -- Proper pgvector type
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Migrate data from old table (convert string to vector)
-- Note: This will parse the string representation into actual vectors
INSERT INTO rfps_new (id, title, category, file_path, content, embedding, created_at, updated_at)
SELECT
    id,
    title,
    category,
    file_path,
    content,
    embedding::vector(384),  -- Cast string to vector
    created_at,
    updated_at
FROM rfps
ON CONFLICT (id) DO NOTHING;

-- 4. Drop old table and rename new one
DROP TABLE IF EXISTS rfps CASCADE;
ALTER TABLE rfps_new RENAME TO rfps;

-- 5. Create index for fast similarity search
CREATE INDEX IF NOT EXISTS rfps_embedding_idx
ON rfps USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 6. Drop existing function if it exists (to avoid signature conflicts)
DROP FUNCTION IF EXISTS match_rfps(vector, double precision, integer);
DROP FUNCTION IF EXISTS match_rfps(vector, float, int);

-- 7. Create similarity search function
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
    similarity_score float
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
        1 - (rfps.embedding <=> query_embedding) AS similarity_score
    FROM rfps
    WHERE 1 - (rfps.embedding <=> query_embedding) > match_threshold
    ORDER BY rfps.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 7. Grant necessary permissions
GRANT SELECT ON rfps TO anon, authenticated;
GRANT EXECUTE ON FUNCTION match_rfps TO anon, authenticated;

-- 8. Verify the setup
SELECT
    'Embeddings fixed!' as message,
    COUNT(*) as total_rfps,
    COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as rfps_with_embeddings,
    pg_typeof(embedding) as embedding_type
FROM rfps
GROUP BY pg_typeof(embedding);
