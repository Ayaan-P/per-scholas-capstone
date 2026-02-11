# Agentic Architecture Database Migration

**Created:** 2025-02-10  
**Author:** pm-fundfish (subagent)  
**Status:** Ready for Review

---

## Overview

This migration restructures the FundFish database from a user-centric model (`saved_opportunities`) to an organization-centric agentic model supporting:

- **AI agents** that score and analyze grants per organization
- **Morning briefs** sent to organizations with top grant recommendations
- **User bookmarks** for personal grant tracking

### Key Changes

| Before | After |
|--------|-------|
| `saved_opportunities` (user-saved grants) | `org_grants` (org-level AI analysis) |
| N/A | `org_briefs` (morning brief history) |
| N/A | `user_saves` (personal bookmarks) |

---

## Migration Files

| File | Purpose |
|------|---------|
| `001_org_grants.sql` | Create org_grants table for AI-scored grants |
| `002_org_briefs.sql` | Create org_briefs table for morning brief history |
| `003_user_saves.sql` | Create user_saves table for personal bookmarks |
| `migrate_saved_opportunities.sql` | Move data from saved_opportunities to new tables |
| `rollback.sql` | Undo migration if needed |

---

## New Schema

### org_grants
Stores org-specific state and AI analysis for each grant.

```sql
org_grants (
    id UUID PRIMARY KEY,
    org_id BIGINT → organization_config(id),
    grant_id UUID → scraped_grants(id),
    status TEXT,          -- active, dismissed, saved, applied, won, lost
    match_score INT,      -- 0-100
    llm_summary TEXT,     -- Brief AI summary
    match_reasoning TEXT, -- Detailed reasoning
    key_tags TEXT[],      -- Extracted tags
    effort_estimate TEXT, -- low, medium, high
    winning_strategies JSONB,
    ...
)
```

### org_briefs
Tracks morning briefs sent to organizations.

```sql
org_briefs (
    id UUID PRIMARY KEY,
    org_id BIGINT → organization_config(id),
    subject TEXT,
    content TEXT,
    grant_ids UUID[],     -- Featured grants
    delivery_channel TEXT,
    sent_at TIMESTAMPTZ,
    delivered BOOLEAN,
    opened BOOLEAN,
    clicked_grant_ids UUID[],
    ...
)
```

### user_saves
Personal user bookmarks (lightweight).

```sql
user_saves (
    id UUID PRIMARY KEY,
    user_id UUID → auth.users(id),
    grant_id UUID → scraped_grants(id),
    folder TEXT,
    notes TEXT,
    reminder_at TIMESTAMPTZ,
    ...
)
```

---

## Migration Steps

### Step 1: Backup (CRITICAL)
```bash
# Backup production database before migration
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Step 2: Create New Tables (Staging First)
Run on **staging** environment first:
```bash
psql $STAGING_DATABASE_URL -f 001_org_grants.sql
psql $STAGING_DATABASE_URL -f 002_org_briefs.sql
psql $STAGING_DATABASE_URL -f 003_user_saves.sql
```

Or via Supabase SQL Editor (one file at a time).

### Step 3: Verify Table Creation
```sql
SELECT table_name, column_name, data_type 
FROM information_schema.columns 
WHERE table_name IN ('org_grants', 'org_briefs', 'user_saves')
ORDER BY table_name, ordinal_position;
```

### Step 4: Migrate Data
```bash
psql $STAGING_DATABASE_URL -f migrate_saved_opportunities.sql
```

This will:
1. Map `saved_opportunities` entries to `scraped_grants` by `opportunity_id`
2. Create `user_saves` entries for each user's saved grants
3. Create `org_grants` entries grouped by organization
4. Create a compatibility view `saved_opportunities_compat`
5. Log the migration

### Step 5: Verify Migration
```sql
-- Check record counts
SELECT 'saved_opportunities' as source, COUNT(*) FROM saved_opportunities
UNION ALL
SELECT 'user_saves' as target, COUNT(*) FROM user_saves
UNION ALL
SELECT 'org_grants' as target, COUNT(*) FROM org_grants;

-- Check migration log
SELECT * FROM migration_log ORDER BY started_at DESC LIMIT 5;
```

### Step 6: Update API Endpoints
Update backend code to use new tables:

**Before (Python):**
```python
# Old way
saved = supabase.table('saved_opportunities').select('*').eq('user_id', user_id)
```

**After (Python):**
```python
# For personal saves
saves = supabase.table('user_saves').select('*, scraped_grants(*)').eq('user_id', user_id)

# For org-level AI analysis
org_grants = supabase.table('org_grants').select('*, scraped_grants(*)').eq('org_id', org_id)
```

### Step 7: Deploy to Production
After successful staging verification:
```bash
# Production backup first!
pg_dump $DATABASE_URL > backup_pre_agentic_$(date +%Y%m%d).sql

# Run migrations
psql $DATABASE_URL -f 001_org_grants.sql
psql $DATABASE_URL -f 002_org_briefs.sql  
psql $DATABASE_URL -f 003_user_saves.sql
psql $DATABASE_URL -f migrate_saved_opportunities.sql
```

### Step 8: Archive Old Table (After Verification)
Once confident:
```sql
ALTER TABLE saved_opportunities RENAME TO saved_opportunities_archived;
```

---

## Backward Compatibility

During migration, old code continues to work via:

1. **Compatibility View**: `saved_opportunities_compat` provides the old schema shape
2. **Original Table**: `saved_opportunities` is not dropped, just renamed after verification

### Transition Period Checklist
- [ ] New tables created
- [ ] Data migrated
- [ ] API endpoints updated to use new tables
- [ ] Frontend updated (if needed)
- [ ] Compatibility view working for any legacy code
- [ ] Old table archived (not dropped)
- [ ] Agents writing to org_grants

---

## Rollback Procedure

If issues are found:

```bash
psql $DATABASE_URL -f rollback.sql
```

This will:
1. Drop `org_grants`, `org_briefs`, `user_saves` tables
2. Drop associated views and functions
3. Restore `saved_opportunities` if it was archived
4. Recreate the `user_saved_opportunities` view

**Warning:** Rollback will DELETE all data in the new tables!

---

## Performance Considerations

### Indexes Created

**org_grants:**
- `(org_id, status, match_score DESC)` - Primary query pattern
- `(grant_id)` - Lookup by grant
- `(scored_at)` - Agent processing
- `USING GIN(key_tags)` - Tag filtering

**org_briefs:**
- `(org_id, sent_at DESC)` - Brief history
- `(scheduled_at) WHERE delivered = FALSE` - Pending briefs
- `USING GIN(grant_ids)` - Find briefs with specific grants

**user_saves:**
- `(user_id, saved_at DESC)` - User's saves
- `(user_id, folder, saved_at DESC)` - By folder
- `(reminder_at) WHERE reminder_sent = FALSE` - Upcoming reminders

### Query Patterns

**Get org's active grants sorted by score:**
```sql
SELECT og.*, sg.title, sg.deadline, sg.amount
FROM org_grants og
JOIN scraped_grants sg ON sg.id = og.grant_id
WHERE og.org_id = $1 
  AND og.status = 'active'
ORDER BY og.match_score DESC
LIMIT 20;
```

**Get pending briefs to send:**
```sql
SELECT * FROM org_briefs
WHERE delivered = FALSE
  AND scheduled_at <= NOW()
ORDER BY scheduled_at;
```

---

## Row Level Security

All new tables have RLS enabled with policies for:
- Users can access their own org's data
- Users can access their own saves
- Service role has full access (for agents)

---

## Testing

### Test Dataset Creation
If testing locally without production data:

```sql
-- Create test organization
INSERT INTO organization_config (name, mission)
VALUES ('Test Nonprofit', 'Testing agentic architecture');

-- Create test user
INSERT INTO users (id, email, organization_id)
VALUES (gen_random_uuid(), 'test@example.com', 1);

-- Create test grant
INSERT INTO scraped_grants (opportunity_id, title, funder, source)
VALUES ('TEST-001', 'Test Grant', 'Test Foundation', 'test');

-- Create test org_grant
INSERT INTO org_grants (org_id, grant_id, match_score, llm_summary)
SELECT 1, id, 85, 'This is a test grant summary'
FROM scraped_grants WHERE opportunity_id = 'TEST-001';

-- Create test brief
INSERT INTO org_briefs (org_id, subject, content, grant_ids, delivery_channel)
SELECT 1, 'Your Morning Brief', '# Test Brief\n\nHere are your grants...', 
       ARRAY[(SELECT id FROM scraped_grants WHERE opportunity_id = 'TEST-001')],
       'email';
```

### Verification Queries
```sql
-- Test org_grants view
SELECT * FROM org_grants WHERE org_id = 1;

-- Test org_briefs
SELECT * FROM org_briefs WHERE org_id = 1;

-- Test user_saves
SELECT * FROM user_saves WHERE user_id = (SELECT id FROM users LIMIT 1);

-- Test analytics view
SELECT * FROM org_brief_analytics;
```

---

## Open Questions

1. **Existing user_id in saved_opportunities**: Some entries may not have a user_id or the user may not have an org. These are skipped in migration.

2. **Unmapped opportunities**: Entries where `opportunity_id` doesn't match any `scraped_grants.opportunity_id` cannot be migrated to org_grants (no FK).

3. **Multi-user organizations**: Each user's save is migrated, but org_grants deduplicates by org+grant.

---

## Changelog

| Date | Change |
|------|--------|
| 2025-02-10 | Initial migration scripts created |

---

## Contact

Questions? Contact the main agent or check `AGENTIC_SPEC.md` for architecture context.
