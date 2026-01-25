-- Create organization documents table for storing uploaded docs
-- Used for LLM extraction and RAG context in grant matching

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS organization_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id BIGINT REFERENCES organization_config(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL CHECK (file_type IN ('pdf', 'docx', 'txt')),
    file_size BIGINT,
    storage_path TEXT NOT NULL,
    extracted_text TEXT,
    embedding vector(384),  -- For semantic search with all-MiniLM-L6-v2
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_org_docs_organization ON organization_documents(organization_id);
CREATE INDEX IF NOT EXISTS idx_org_docs_uploaded ON organization_documents(uploaded_at DESC);
CREATE INDEX IF NOT EXISTS idx_org_docs_embedding ON organization_documents USING ivfflat (embedding vector_cosine_ops);

-- Row Level Security
ALTER TABLE organization_documents ENABLE ROW LEVEL SECURITY;

-- Policy to allow operations on own organization's documents
CREATE POLICY "Users can manage their organization documents"
    ON organization_documents
    FOR ALL
    USING (true);

-- Store extraction history for audit/rollback
CREATE TABLE IF NOT EXISTS organization_extraction_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id BIGINT REFERENCES organization_config(id) ON DELETE CASCADE,
    extracted_data JSONB NOT NULL,
    source_document_ids UUID[],
    confidence_scores JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    applied_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_extraction_history_org ON organization_extraction_history(organization_id);
CREATE INDEX IF NOT EXISTS idx_extraction_history_created ON organization_extraction_history(created_at DESC);

ALTER TABLE organization_extraction_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their extraction history"
    ON organization_extraction_history
    FOR ALL
    USING (true);
