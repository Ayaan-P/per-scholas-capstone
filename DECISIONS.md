# DECISIONS.md — Owner Feedback & Priorities
# Updated by Maya when Ayaan gives direction. Read this FIRST every run.
# Last updated: 2026-02-13

## Important Context
- **Domain is fundfish.pro** — NOT fundfishpro.netlify.app. The agent was checking the wrong URL. Check the actual domain first before reporting the site as down.

## Pending Decisions (awaiting Ayaan's input)

### ✅ Document Upload Feature - COMPLETE (2026-02-11)
**Status:** ✅ DONE  
**Priority:** Medium (nice-to-have, not blocking)

**Completed:**
- ✅ Hetzner endpoint live: `POST http://46.225.82.130:9090/agent/upload`
- ✅ Render backend proxies uploads to Hetzner
- ✅ Files save to `/home/dytto-agent/workspaces/ff-{org_id}/uploads/`
- ✅ Chat UI upload button added (commit 1cce7bf, 2026-02-11)
- ✅ Agent TOOLS.md updated so agents know about `uploads/` directory
- ✅ Fixed api.ts syntax error (upload methods were outside object)
- ✅ Installed missing deps: react-markdown, remark-gfm, @phosphor-icons/react

**Optional remaining:** Create `workspace_files` database table for persistent file metadata

---

## Approved — Agentic Pivot (2026-02-06)

**FundFish is becoming an agent-first product.**

Agent template scaffolded at `~/clawd/agents/fundfish/`:
- `AGENTS.md` — Instructions for grant discovery + proposal writing
- `scripts/fundfish-api.sh` — FundFish API wrapper
- `config.json` — Clawdbot agent config
- Dytto context integration — Agent knows org profile, past grants, writing style

**Architecture:**
- Same Hetzner box as personal agents (different agent type)
- Each nonprofit gets their own agent instance
- Chat interface on fundfish.pro routes to their agent
- Dytto powers organizational context (mission, history, style)

**Next steps:**
1. Deploy agent template to Hetzner
2. Add fundfish agent type to bridge config
3. Build chat interface on fundfish.pro
4. Test end-to-end: signup → agent creation → grant search → proposal help

## Approved — Investigate ASAP

### Claude API Key Invalid (Issue #42)
- **Priority:** HIGH
- **Status:** 🔴 BLOCKING
- **Discovered:** 2026-02-10
- **Details:** The ANTHROPIC_API_KEY in Render is invalid. AI state/local scraper is completely broken (0 grants found). Proposal generation using Claude is also affected.
- **Fix Required:** Verify/regenerate API key at console.anthropic.com and update in Render environment variables.

### Backend Scheduler Not Producing New Grants
- **Priority:** High
- **Status:** ✅ FIXED (2026-02-04)
- **Details:** Ayaan reports no new grants showing up. The backend runs on paid Render (standard plan, no spin-down) with APScheduler. The scheduler should be running daily scrapes (Grants.gov, SAM.gov, DOL, USASpending) plus weekly AI state/local.
- **Investigate:**
  1. Check Render logs for the backend — are the scraper jobs actually firing?
  2. Are any scrapers erroring out? (API keys expired, rate limits, format changes)
  3. Is the Gemini CLI session working inside the Docker container? (AI state/local scraper depends on it)
  4. Is dedup logic too aggressive? (grants found but matching existing IDs)
  5. Check the `scraped_grants` table in Supabase — when was the last insert?
  6. Check `scheduler_settings` table — is the frequency configured correctly?
- **Fix it or report what's broken.**
- **Approved by:** Ayaan (2026-02-03)
- **Resolution (2026-02-04):**
  - **Bug 1 (Issue #34):** `category_service.py` initialized its own Supabase client at module level, falling back to `None`. The AI state/local scraper found 0 categories → scraped 0 grants. Fixed by passing working client from scheduler + initializing in startup_event.
  - **Bug 2 (Issue #35):** `match_score` was stored as float (e.g., `32.0`) but DB column is integer. 24+ grants per run failed silently. Fixed with `int()` casting.
  - **Bug 3:** Empty-string deadlines caused `invalid input syntax for type timestamp` errors. Fixed with sanitization.
  - **Grants.gov scraper IS working:** 159 grants saved this run, 251 total in DB.
  - **AI state/local scraper will resume** once the fix deploys — the `opportunity_categories` table has 5 categories ready.

## Approved — Do These
- [x] **Verify site status** — fundfish.pro returns HTTP 200, served by Netlify. ✅ 2026-01-31
- [x] **API security** — Audited all endpoints, found 13 without auth, fixed all. Issue #27, commit c07d455. ✅ 2026-01-31
- [x] **Landing page** — Built full landing page (hero, features, CTA, footer). Issue #28, commit 532a9d8. ✅ 2026-01-31
- [x] **GA4 Analytics** — Added GA4 tracking script to layout.tsx. Placeholder ID `G-FUNDFISH` — needs real measurement ID from Ayaan. Issue #31. ✅ 2026-02-02
- [x] **GA4 — Real Measurement ID** — G-90C1JMVYN0 wired in commit b5d871b. Issue #31 closed. ✅ 2026-02-03
- [x] **Polish existing features** — ✅ 2026-02-10. Auth fixes shipped, nav fixed, signup bug fixed, chat input polished, org profile auto-creation, agent auto-fill profile.
- [x] **Wire Qualification Agent (CRITICAL PATH)** — ✅ 2026-02-13. Scoring agent can load org profiles from Supabase. `/api/my-grants` endpoint reads from `org_grants`. Issue #44 created for dashboard wiring.
- [x] **Update Dashboard Query** — ✅ 2026-02-13. `/api/my-grants` endpoint added, reads from `org_grants` with fallback to `scraped_grants`. Dashboard needs to switch to this endpoint (Issue #44).
- [x] **Multi-Tenant Data Model (RESOLVED 2026-02-10)** — Architecture clarified: `scraped_grants` = global pool, `org_grants` = org-specific scores/status. No need for separate dismissals table - status lives in org_grants.

## How to Work
- For each approved item: **plan first** — break into subtask issues on GitHub, THEN implement.
- Don't just jump into code. Create the issues so progress is trackable.

## Completed
- [x] Fixed stray `c` character in dashboard table (PR #14)
- [x] API security hardening — 13 endpoints secured (Issue #27, 2026-01-31)
- [x] Landing page for fundfish.pro (Issue #28, 2026-01-31)
- [x] Credits routes use real Supabase JWT emails instead of placeholders (Issue #25, 2026-02-01)
- [x] Removed dead settings/page-old.tsx (Issue #24, 2026-02-01)
- [x] Removed all 58 console.log/error statements from frontend (Issue #16, 2026-02-01)
- [x] Added SEO: OpenGraph, Twitter Card, robots.txt, sitemap.xml (Issue #19, 2026-02-01)
- [x] Added error boundaries, loading skeletons, 404 page (Issue #17, 2026-02-01)
- [x] GA4 analytics tracking script added (Issue #31, 2026-02-02)
- [x] Fixed 10+ API endpoints missing authentication (2026-02-02)
- [x] Fixed signup page render-during-render bug (2026-02-02)
- [x] Added Proposals page to navigation (Issue #32, 2026-02-02)
- [x] Fixed About page back link for unauthenticated users (Issue #33, 2026-02-02)
- [x] GA4 real measurement ID wired (Issue #31 closed, 2026-02-03)
- [x] TypeScript cleanup: ALL 29 'any' types replaced with proper interfaces (Issue #29 CLOSED, 2026-02-03)
- [x] Fixed category service NoneType client breaking AI scraper (Issue #34, 2026-02-04)
- [x] Fixed match_score float→int insertion failures (Issue #35, 2026-02-04)
- [x] Fixed empty-string deadline insertion failures (2026-02-04)
- [x] Fixed ALL timestamp field sanitization (archive_date, forecast_date, etc) — was only handling deadline (2026-02-05)
- [x] Fixed 25 bare except clauses across 8 backend files (Issue #38 CLOSED, 2026-02-05)
- [x] Converted all Header/landing <a> tags to Next.js <Link> for client-side routing (Issue #36, 2026-02-04)
- [x] Updated sitemap.xml with /about page (2026-02-04)
- [x] BEGIN main.py split (Issue #37): Extracted health, categories, scheduler, dashboard routes to `routes/` package. main.py 3097→2816 lines (-281). Commit 77fe2a3 (2026-02-06)
- [x] CONTINUE main.py split (Issue #37): Extracted organization routes (auth init, org config, documents). main.py 2816→2147 lines (-669). Total: 3097→2147 (-950, -31%). Commit 8a365d1 (2026-02-07)
- [x] Fixed Gemini SDK API change for embeddings (Issue #41 CLOSED, 2026-02-07): output_dimensionality no longer supported
- [x] CONTINUE main.py split (Issue #37): Extracted proposals routes to routes/proposals.py. main.py 2147→1805 lines (-342). Total: 3097→1805 (-1292, -42%). Commit f92d210 (2026-02-08)
- [x] CONTINUE main.py split (Issue #37): Extracted grants routes to routes/grants.py. main.py 1813→1630 lines (-183). Commit 5b5c8ce (2026-02-09)
- [x] CONTINUE main.py split (Issue #37): Extracted RFPs routes to routes/rfps.py. main.py 1630→1475 lines (-155). Total: 3097→1475 (-1622, -52%). Commit 373b4ab (2026-02-09)
- [x] COMPLETE main.py split (Issue #37): Extracted opportunities routes to routes/opportunities.py. main.py 1475→601 lines (-874). Total: 3097→601 (-2496, -81%). Commit d2fc3e0 (2026-02-10)
- [x] Agent auto-fill profile endpoint (2026-02-10): POST /api/workspace/update-profile-from-agent allows agent to update org profile directly from conversation. Magic moment UX - profile auto-fills as users chat. Commit 8f42a4c
- [x] Defensive org profile creation (2026-02-10): GET /api/organization/config auto-creates missing org profiles with defaults. No more 404 errors. Commit 8faed4c
- [x] Database schema restoration for agents (2026-02-10): Restored complete 30-field extraction schema to search agent prompt and librarian TOOLS.md. Agents now capture contact info, consortium requirements, award details, geographic focus, attachment requirements - not just basics. Commits 6cfc457, 8620f46
- [x] Document upload UI complete (2026-02-11): Added file upload button to chat page, collapsible file list, fixed api.ts syntax error, installed missing deps. Commit 1cce7bf
- [x] Created workspace_files table migration (2026-02-12): Issue #43 created and migration file added. Table needed for tracking uploaded documents. Commit f5e32ed
- [x] Fixed org profile lookup errors (2026-02-12): OrganizationMatchingService.get_organization_profile() no longer throws on missing users/orgs. Uses safe array access instead of .single(). Commit 6ed6c57
- [x] Closed Issue #40 (2026-02-12): Gemini quota issue now obsolete — APScheduler disabled, scraping moved to Hetzner librarian
- [x] Scoring agent Supabase profile loading (2026-02-13): ScoringAgent now loads org profiles from organization_config table instead of requiring filesystem PROFILE.md. Enables scoring to run on Render backend. Commit 92385ef
- [x] /api/my-grants endpoint (2026-02-13): New endpoint reads pre-scored grants from org_grants table with fallback to scraped_grants. Includes dismiss endpoint. Issue #44 created for dashboard wiring. Commit 0665235
