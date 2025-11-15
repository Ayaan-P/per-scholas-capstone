-- Create opportunities table
CREATE TABLE IF NOT EXISTS opportunities (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    funder TEXT NOT NULL,
    amount INTEGER,
    deadline DATE,
    match_score INTEGER,
    description TEXT,
    requirements TEXT[],
    contact TEXT,
    application_url TEXT,
    llm_summary TEXT,
    detailed_match_reasoning TEXT,
    tags TEXT[],
    similar_past_proposals JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create jobs table for tracking search jobs
CREATE TABLE IF NOT EXISTS search_jobs (
    job_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    progress INTEGER DEFAULT 0,
    current_task TEXT,
    search_criteria JSONB,
    result JSONB,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Create proposals table
CREATE TABLE IF NOT EXISTS proposals (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    opportunity_id TEXT,
    opportunity_title TEXT,
    status TEXT DEFAULT 'draft',
    content TEXT,
    funding_amount INTEGER,
    deadline DATE,
    funder TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create analytics tracking tables
CREATE TABLE IF NOT EXISTS analytics_events (
    id SERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    event_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);