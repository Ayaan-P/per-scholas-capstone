# FundFish Complete Status Audit — 2026-02-10 23:20 EST

## ✅ What's Actually Working

### 1. Site & Infrastructure
- ✅ **fundfish.pro is LIVE** (HTTP 200, Netlify serving)
- ✅ **Backend deployed** on Render (standard plan, no spin-down)
- ✅ **Chat agent working** - session persistence, context memory
- ✅ **Database connected** - Supabase operational
- ✅ **Auth system** - Supabase auth, JWT tokens working
- ✅ **Agent infrastructure** - Hetzner templates, bridge mode, OAuth

### 2. Database Tables (CONFIRMED EXIST)
- ✅ **scraped_grants** - 286+ grants, actively populated by librarian
- ✅ **organization_config** - org profiles with mission/programs/etc
- ✅ **users** - linked to orgs
- ✅ **saved_opportunities** - legacy table, being phased out
- ✅ **proposals** - exists

### 3. Database Tables (MIGRATIONS EXIST, NOT CONFIRMED APPLIED)
- ⚠️ **org_grants** - Migration file exists (`001_org_grants.sql`)
- ⚠️ **org_briefs** - Migration file exists (`002_org_briefs.sql`)
- ⚠️ **user_saves** - Migration file exists (`003_user_saves.sql`)

**STATUS**: SQL files are ready but unknown if they've been run in production Supabase

### 4. Backend Code (BUILT, MAY NOT BE DEPLOYED)
- ✅ **Agent auto-fill profile** - POST /api/workspace/update-profile-from-agent
- ✅ **30-field extraction schema** - Both search agent and librarian have it
- ✅ **Modular routes** - 13 route files extracted from main.py
- ✅ **Processing endpoint** - POST /api/processing/qualify-grants EXISTS
- ✅ **Qualification agent script** - `backend/jobs/process_grants.py` EXISTS
- ✅ **Dashboard stats** - Tries to read from org_grants (but falls back to saved_opportunities if table doesn't exist)

### 5. Frontend
- ✅ **Dashboard page** - Calls `/scraped-grants` endpoint
- ✅ **Chat page** - Functional, agent working
- ✅ **Auth pages** - Signup/login working
- ❌ **No calls to qualification agent** - Frontend doesn't trigger processing

---

## 🔴 What's NOT Working / Missing

### Critical Gap #1: Grants Feed Still Uses scraped_grants
**Current flow:**
1. Dashboard calls `api.getScrapedGrants()`
2. Backend `/scraped-grants` endpoint reads from `scraped_grants` table
3. Backend recalculates match scores ON THE FLY per request
4. No org_grants table involvement

**Should be:**
1. Dashboard calls `/scraped-grants` or new endpoint
2. Backend reads from `org_grants` table (pre-scored, org-specific)
3. Scores already calculated, no re-computation

**The Problem:**
- `org_grants` table may not exist in production
- Even if it does, `/scraped-grants` endpoint doesn't query it
- Frontend has no way to trigger the qualification agent

---

### Critical Gap #2: Qualification Agent Not Wired
**What exists:**
- ✅ Script: `backend/jobs/process_grants.py`
- ✅ Endpoint: POST `/api/processing/qualify-grants`
- ✅ Routes imported in main.py

**What's missing:**
- ❌ Frontend doesn't call it
- ❌ No dashboard "Refresh Scores" button
- ❌ No cron job to run it nightly
- ❌ No automatic trigger when user signs up

**The gap:** The qualification agent can run, but nothing invokes it

---

### Critical Gap #3: Database Migrations May Not Be Applied

**Files exist:**
- `backend/migrations/001_org_grants.sql` (ready)
- `backend/migrations/002_org_briefs.sql` (ready)
- `backend/migrations/003_user_saves.sql` (ready)
- `backend/migrations/migrate_saved_opportunities.sql` (ready)

**Unknown:**
- Have these been run in production Supabase?
- Can't verify table existence remotely without service role key

**Impact:** If tables don't exist, all org_grants code fails silently

---

## 🎯 What Needs to Happen (Priority Order)

### STEP 1: Verify Database State
```bash
# Run in Supabase SQL Editor (or psql)
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('org_grants', 'org_briefs', 'user_saves');
```

If any missing → run the migrations in order:
1. `001_org_grants.sql`
2. `002_org_briefs.sql`
3. `003_user_saves.sql`
4. `migrate_saved_opportunities.sql` (if migrating existing data)

---

### STEP 2: Wire Qualification Agent

**Option A: Dashboard Button (Fastest)**

Add to `frontend/src/app/dashboard/page.tsx`:
```typescript
const refreshScores = async () => {
  const response = await api.qualifyGrants({ since_hours: 720 })
  if (response.ok) {
    alert("Scoring started! Refresh in 30 seconds.")
  }
}

// In UI:
<button onClick={refreshScores}>Refresh Match Scores</button>
```

Add to `frontend/src/utils/api.ts`:
```typescript
qualifyGrants: (data: { since_hours?: number }) =>
  authenticatedFetch(`${API_BASE_URL}/api/processing/qualify-grants`, {
    method: 'POST',
    body: JSON.stringify(data)
  }),
```

**Option B: Nightly Cron (Better Long-term)**

Create cron job that runs at 3:30 AM (after librarian adds grants):
```python
# In backend scheduler or separate cron
import requests

def run_qualification_for_all_orgs():
    # Get all org IDs from organization_config
    orgs = supabase.table("organization_config").select("id").execute()
    
    for org in orgs.data:
        requests.post(
            "http://localhost:8000/api/processing/qualify-grants",
            json={"org_id": str(org["id"]), "force": False}
        )
```

---

### STEP 3: Update Dashboard Query

**Current:** `/scraped-grants` reads from `scraped_grants` table

**Option A: Modify `/scraped-grants` endpoint**

In `backend/routes/grants.py` line ~70:
```python
@router.get("/scraped-grants")
async def get_scraped_grants(user_id: Optional[str] = Depends(optional_token)):
    if user_id:
        # Read from org_grants if authenticated
        org_id = await get_user_org_id(user_id)
        result = _supabase.table("org_grants") \
            .select("*, scraped_grants(*)") \
            .eq("org_id", org_id) \
            .neq("status", "dismissed") \
            .execute()
        grants = [
            {**row["scraped_grants"], "match_score": row["match_score"]} 
            for row in result.data
        ]
    else:
        # Public: read from scraped_grants (no scores)
        result = _supabase.table("scraped_grants").select("*").execute()
        grants = result.data
        for g in grants:
            g["match_score"] = None  # Hide scores for unauthenticated
    
    return {"grants": grants}
```

**Option B: Create new `/org-grants` endpoint (cleaner)**

Keep `/scraped-grants` for public dashboard, add new endpoint for authenticated.

---

## 📊 Current State Summary

| Component | Status | Blocker |
|-----------|--------|---------|
| Site Live | ✅ Working | None |
| Chat Agent | ✅ Working | None |
| Librarian | ✅ Working | None |
| Agent Infrastructure | ✅ Working | None |
| 30-Field Schema | ✅ Working | None |
| Database Tables (core) | ✅ Working | None |
| **org_grants table** | ⚠️ Unknown | Need to verify if migration was run |
| **org_briefs table** | ⚠️ Unknown | Need to verify if migration was run |
| **user_saves table** | ⚠️ Unknown | Need to verify if migration was run |
| Qualification Agent Script | ✅ Built | Not wired to frontend or cron |
| Qualification API Endpoint | ✅ Built | Not called by anything |
| Dashboard Grants Feed | ⚠️ Partial | Reads scraped_grants, should read org_grants |
| Morning Briefs | ❌ Not Built | Depends on org_grants + org_briefs |

---

## 🚀 Fastest Path to Working

**If you want it working NOW:**

1. **Verify tables exist** (5 min)
   - Open Supabase SQL Editor
   - Run: `SELECT * FROM org_grants LIMIT 1;`
   - If error → run migrations 001, 002, 003

2. **Add dashboard button** (10 min)
   - Frontend: Add "Refresh Scores" button
   - Calls POST /api/processing/qualify-grants
   - User clicks it, scores calculate

3. **Modify /scraped-grants** (15 min)
   - Change backend to read org_grants for authenticated users
   - Keep scraped_grants for public

**Total: ~30 minutes to working personalized dashboard**

---

## 💡 Why It's Close But Not There

**You built all the pieces:**
- Migrations (SQL ready)
- Qualification script (process_grants.py ready)
- API endpoint (POST /processing/qualify-grants ready)
- Dashboard code (tries to read org_grants)

**Missing links:**
- Migrations may not be applied
- Nothing invokes the qualification agent
- Main grants feed still bypasses org_grants

**It's like having all the parts of a car laid out, but not assembled.**

---

## 🎯 Recommendation

**Tonight:** Just verify if org_grants table exists. If not, run the 3 migrations.

**Tomorrow:** Wire up steps 2 & 3 above (button + endpoint change).

**By Tuesday:** You'll have fully personalized, org-specific scoring working end-to-end.

---

*Audit completed: 2026-02-10 23:20 EST by Maya*
