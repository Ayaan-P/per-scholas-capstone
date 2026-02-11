# FundFish Database Restructure — Multi-Tenant Architecture

## Current Problems

### 1. **scraped_grants is a Shared Pool with Global State**
- 286 grants, NO org_id
- `status=dismissed` affects ALL orgs
- 22 "dismissed" grants hidden from everyone
- No way to track which org dismissed what

### 2. **saved_opportunities Duplicates Everything**
Current schema has `user_id` and duplicates ALL grant fields:
```
opportunity_id, title, funder, amount, deadline, description, requirements,
contact, application_url, match_score, source, status, created_at, ...
(38 total columns)
```

This creates:
- Data duplication (same grant stored N times if N users save it)
- Sync issues (if grant updates, saved copies go stale)
- Wasted storage

### 3. **No Clear Separation of Concerns**
- `scraped_grants` = supposed to be the source of truth
- `saved_opportunities` = user saves, but has its own copy of all data
- `user_saved_opportunities` = exists but empty (dead table?)

### 4. **Librarian Writes to Global Pool**
- Librarian agent writes to `scraped_grants`
- No concept of "which org is this grant for?"
- Every org sees every grant

---

## Proposed Architecture

### Core Principle: **Separation of Global vs Per-Org vs Per-User**

```
┌─────────────────────┐
│  scraped_grants     │  ← GLOBAL POOL (immutable, shared)
│  - id (PK)          │     Librarian writes here
│  - opportunity_id   │     NO org_id, NO status
│  - title            │     Just raw grant data
│  - funder           │
│  - amount           │
│  - deadline         │
│  - source           │
│  - ...              │
└─────────────────────┘
         ↓
┌─────────────────────┐
│  org_grants         │  ← ORG-LEVEL (filtering, dismissals)
│  - org_id           │     Many-to-many: orgs × grants
│  - grant_id → FK    │     
│  - status           │     active | dismissed | saved
│  - match_score      │     Org-specific scoring
│  - notes            │     Org-specific notes
│  - tagged_at        │
└─────────────────────┘
         ↓
┌─────────────────────┐
│  user_saves         │  ← USER-LEVEL (bookmarks, starred)
│  - user_id          │     Many-to-many: users × grants
│  - grant_id → FK    │
│  - saved_at         │     User bookmarked it
│  - notes            │     User-specific notes
│  - folder           │     Optional organization
└─────────────────────┘
```

---

## New Schema

### 1. **scraped_grants** (unchanged, stays global)
```sql
-- Immutable grant data from scrapers
-- NO org_id, NO status, NO user-specific fields
CREATE TABLE scraped_grants (
    id UUID PRIMARY KEY,
    opportunity_id TEXT,
    title TEXT NOT NULL,
    funder TEXT,
    amount BIGINT,
    deadline DATE,
    description TEXT,
    source TEXT,  -- 'grants_gov', 'foundation', 'Agent', etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- All the Grants.gov fields
    requirements JSONB,
    application_url TEXT,
    contact_name TEXT,
    eligibility_explanation TEXT,
    geographic_focus TEXT,
    ... (keep all existing columns)
);
```

### 2. **org_grants** (NEW - org-specific grant tracking)
```sql
-- Which grants each org has seen/dismissed/saved
CREATE TABLE org_grants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organization_config(id) ON DELETE CASCADE,
    grant_id UUID NOT NULL REFERENCES scraped_grants(id) ON DELETE CASCADE,
    
    status TEXT NOT NULL DEFAULT 'active',  -- active | dismissed | saved
    match_score INT,  -- Org-specific AI match score
    notes TEXT,  -- Org-level notes
    
    tagged_at TIMESTAMPTZ DEFAULT NOW(),
    dismissed_at TIMESTAMPTZ,
    dismissed_by UUID REFERENCES users(id),
    
    UNIQUE(org_id, grant_id)
);

CREATE INDEX idx_org_grants_org ON org_grants(org_id, status);
CREATE INDEX idx_org_grants_grant ON org_grants(grant_id);
```

### 3. **user_saves** (NEW - user bookmarks)
```sql
-- User-specific bookmarks/stars
CREATE TABLE user_saves (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    grant_id UUID NOT NULL REFERENCES scraped_grants(id) ON DELETE CASCADE,
    
    saved_at TIMESTAMPTZ DEFAULT NOW(),
    notes TEXT,  -- User-specific notes
    folder TEXT,  -- Optional: "High Priority", "Research", etc.
    
    UNIQUE(user_id, grant_id)
);

CREATE INDEX idx_user_saves_user ON user_saves(user_id, saved_at DESC);
```

### 4. **Deprecate saved_opportunities**
```sql
-- Mark as legacy, stop writing to it
-- Migrate existing saves to org_grants + user_saves
-- Eventually drop the table
```

---

## Migration Plan

### Phase 1: Create New Tables (Non-Breaking)
```sql
-- Run the CREATE TABLE statements above
-- Existing app continues using scraped_grants + saved_opportunities
```

### Phase 2: Migrate Existing Data
```python
# For each row in saved_opportunities:
# 1. Ensure the grant exists in scraped_grants (or create it)
# 2. Insert into org_grants (org_id from user's org, status='saved')
# 3. Insert into user_saves (user_id from saved_opportunities.user_id)
```

### Phase 3: Update Application Code
```python
# OLD: SELECT * FROM scraped_grants WHERE status != 'dismissed'
# NEW: 
SELECT sg.* 
FROM scraped_grants sg
LEFT JOIN org_grants og ON og.grant_id = sg.id AND og.org_id = :current_org_id
WHERE og.status IS NULL OR og.status != 'dismissed'
ORDER BY sg.created_at DESC

# For user saves:
SELECT sg.*, us.saved_at, us.notes
FROM scraped_grants sg
JOIN user_saves us ON us.grant_id = sg.id
WHERE us.user_id = :current_user_id
ORDER BY us.saved_at DESC
```

### Phase 4: Update Librarian
```python
# Librarian continues writing to scraped_grants (global pool)
# NO CHANGE - librarian is org-agnostic
# Orgs discover grants through search, not automatic tagging
```

### Phase 5: Deprecate Legacy Tables
```sql
-- Once migration is complete and tested:
DROP TABLE IF EXISTS saved_opportunities;
DROP TABLE IF EXISTS user_saved_opportunities;
```

---

## Benefits

1. **True Multi-Tenancy**
   - Each org dismisses independently
   - Match scores are org-specific
   - No cross-org data leakage

2. **No Data Duplication**
   - Grant data stored once in scraped_grants
   - Org-level tracking in org_grants
   - User bookmarks in user_saves

3. **Cleaner Separation**
   - Global pool (scraped_grants) = immutable
   - Org tracking (org_grants) = filtering, scores
   - User saves (user_saves) = personal bookmarks

4. **Agentic Architecture Ready**
   - Each org's agent queries: scraped_grants + org_grants filtering
   - Agent can auto-tag grants for its org
   - Dismissals are org-scoped

5. **Better Analytics**
   - Track which orgs engage with which grants
   - See dismissal patterns per org
   - Improve match scoring based on org preferences

---

## Implementation Steps

1. ✅ Write this document
2. [ ] Create migration SQL scripts
3. [ ] Run migration on staging/dev
4. [ ] Test with real data
5. [ ] Update API endpoints
6. [ ] Deploy to prod
7. [ ] Monitor for issues
8. [ ] Drop legacy tables

---

## Questions to Resolve

1. **Auto-tagging:** Should new grants auto-create org_grants rows for all orgs? Or only when org first sees it?
2. **Match scoring:** Move match_score to org_grants (org-specific) or keep in scraped_grants (global)?
3. **Proposals:** How do proposals relate to grants? Through grant_id or opportunity_id?
4. **Search:** Does search query scraped_grants directly or through org_grants filter?

---

**Status:** Design complete, awaiting approval to implement.
