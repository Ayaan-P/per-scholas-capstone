-- Migration: Create workspace_files table for tracking uploaded documents
-- Created: 2026-02-12
-- Purpose: Track documents uploaded to Hetzner agent workspaces

CREATE TABLE IF NOT EXISTS workspace_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    content_type TEXT,
    uploaded_by TEXT NOT NULL,
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Optional metadata
    description TEXT,
    tags TEXT[],
    processed BOOLEAN DEFAULT FALSE,  -- Has agent processed this file?
    processed_at TIMESTAMPTZ,
    
    -- Constraints
    CONSTRAINT positive_file_size CHECK (file_size > 0)
);

-- Index for fast org lookups
CREATE INDEX IF NOT EXISTS idx_workspace_files_org_id ON workspace_files(org_id);

-- Index for listing recent uploads
CREATE INDEX IF NOT EXISTS idx_workspace_files_uploaded_at ON workspace_files(uploaded_at DESC);

-- RLS policies
ALTER TABLE workspace_files ENABLE ROW LEVEL SECURITY;

-- Service role can do anything
CREATE POLICY "Service role full access" ON workspace_files
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Authenticated users can see their org's files
CREATE POLICY "Users see own org files" ON workspace_files
    FOR SELECT TO authenticated
    USING (
        org_id IN (
            SELECT organization_id::text FROM users WHERE id = auth.uid()
        )
        OR org_id = CONCAT('temp-', auth.uid()::text)
    );

-- Authenticated users can upload to their org
CREATE POLICY "Users upload to own org" ON workspace_files
    FOR INSERT TO authenticated
    WITH CHECK (
        org_id IN (
            SELECT organization_id::text FROM users WHERE id = auth.uid()
        )
        OR org_id = CONCAT('temp-', auth.uid()::text)
    );

COMMENT ON TABLE workspace_files IS 'Tracks documents uploaded to Hetzner agent workspaces';
