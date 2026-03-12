# DECISIONS.md — Owner Feedback & Priorities
# Updated by Maya when Ayaan gives direction. Read this FIRST every run.
# Last updated: 2026-03-11

## From Chat (updated 2026-03-10)

### What Ayaan Said
- "There is only one librarian for all orgs as of now" — architecture clarification
- "Fuck if I know the only accounts are perscholeads@gmail.com and ayaansp@gmail.com why do you ask me pointless questions instead of using supabase" — don't ask Ayaan for data that's in Supabase, query it yourself
- "Sir if I'm logged into perscholas I should talk to perscholas agent no" — Per Scholas user should route to Per Scholas agent
- "The perscholas agent I talked to on the site is blank for some reason" — agent responses were blank (routing bug)
- "Tell it to go find the amounts and make sure you insert the current date into its context every time btw so it's not finding out of date stuff" — librarian needs current date context
- "Read the code first" — before asking questions, read the actual codebase
- "Why would it trigger from here and not hetzner" — cron should run directly on Hetzner, not SSH from local

### Known Issues (don't nag)
- **Agent routing bug** — ff-15 vs ff-perscholas mismatch FIXED (2026-03-10). Users table was empty, causing temp- prefix routing. Fixed by creating proper org records.
- **Librarian cron location** — was triggering via SSH from local machine, now runs directly on Hetzner at 3 AM
- **Two librarian workspaces existed** — `fundfish-librarian` (orphan) and `lib-fundfishmain` (active). Merged rules from orphan to active, orphan archived.
- **EXTRACTION_RULES.md was in wrong directory** — copied to correct workspace

### New Priorities
- **Librarian must insert current date in context** — so it doesn't find outdated grants
- **Query Supabase directly** — don't ask Ayaan for data that's queryable
- **One librarian for all orgs** — architecture confirmed

### Decisions Made
- Single librarian architecture confirmed (one librarian → scraped_grants → all org agents qualify)
- Cron moved to Hetzner (no more SSH roundtrip from local)
- Per Scholas user ID is `58ac6326-caef-4107-8032-f356a52ab149` (perscholasleads@gmail.com)

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

### ✅ Render Deploys Fixed (Issue #45 CLOSED 2026-02-16)
- **Priority:** CRITICAL → RESOLVED
- **Status:** ✅ FIXED
- **Resolution:** Verified working 2026-02-16. The `/api/my-grants` endpoint responds correctly, confirming commits through 4858a2f are deployed. Whatever caused the 2026-02-12 failures has been resolved.

### Claude API Key Invalid (Issue #42)
- **Priority:** HIGH
- **Status:** 🔴 BLOCKING
- **Discovered:** 2026-02-10
- **Details:** The ANTHROPIC_API_KEY in Render is invalid. AI state/local scraper is completely broken (0 grants found). Proposal generation using Claude is also affected.
- **Fix Required:** Verify/regenerate API key at console.anthropic.com and update in Render environment variables.

### ✅ Hetzner Agent Bridge OAuth — WORKING (2026-03-07)
- **Priority:** HIGH → RESOLVED
- **Status:** ✅ WORKING
- **Discovered:** 2026-02-16 (logs show errors from 2026-02-15)
- **Verified Working:** 2026-03-07 02:30 AM — Health check passed, librarian agent responded correctly
- **Test:** `curl -X POST http://46.225.82.130:9090/chat -d '{"user_id":"health-check","agent_type":"librarian","message":"ping"}'` returns valid response
- **Previous Issue:** OAuth token refresh errors have been resolved (either automatically or via manual re-auth)

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

### ✅ Match Profile Transparency UI (2026-02-22)
- **Status:** ✅ DONE
- **Details:** Added "🎯 Match Profile" tab to Settings showing primary keywords, secondary keywords, excluded keywords, and scoring weight bars. Lazy-loads via `/api/organization/match-profile`. Issue #51 CLOSED.

### ✅ Critical: Hardcoded org_id=15 in /api/opportunities (2026-02-22)
- **Status:** ✅ FIXED
- **Details:** The Per Scholas demo org_id was hardcoded. All users were seeing org 15's opportunities. Fixed with dynamic lookup via users table + organization_config fallback.

### ✅ Backend Pagination for Grants Endpoints (2026-02-22)
- **Status:** ✅ DONE
- **Details:** Added limit/offset to `/api/scraped-grants` (default limit=150) and `/api/my-grants`. Response includes `has_more` flag. Issue #52 created for frontend load-more UI.

### ✅ Blog post #3 (2026-02-22)
- **Status:** ✅ DONE
- **Title:** "Inside the Black Box: How FundFish Scores Grants for Your Nonprofit"
- **Angle:** Match profile transparency feature + agentic search research

### ✅ workspace_files Migration (2026-02-21)
- **Status:** ✅ DONE
- **Details:** Ran `005_create_workspace_files.sql` via Supabase Management API. Table now exists. Issue #43 CLOSED.

### ✅ excluded_keywords now active in grant matching (2026-02-21)
- **Status:** ✅ DONE
- **Details:** Fixed bug where org's exclusion list was stored but never applied. `should_filter_grant()` now checks excluded_keywords first. Applied in both `get_scraped_grants()` and `get_my_grants()`. Issue #49 CLOSED.
- **New endpoint:** `GET /api/organization/match-profile` returns active keywords, scoring weights, exclusions so users can see how their org profile affects discovery. Issue #51 created for frontend UI.

### ✅ Blog post #2 (2026-02-21)
- **Status:** ✅ DONE
- **Title:** "Why Grant Matching Needs to Know Your Mission (Not Just Your Keywords)"
- **Target keywords:** grant matching nonprofit, personalized grant discovery, AI grant search
- **Fixed:** Blog social meta images were pointing to localhost:3000 (Issue #50 CLOSED)
- **Fixed:** Blog link added to landing page footer

### ✅ Build Dev Blog (2026-02-19)
- **Priority:** Medium
- **Status:** ✅ DONE
- **Why:** FundFish already ranks for brand name. Blog content targeting grant/nonprofit keywords will capture organic traffic.
- **Scope:**
  1. ✅ Create `/blog` route in Next.js frontend
  2. ✅ Blog index page (list of posts, sorted by date)
  3. ✅ Individual post pages (render markdown from `blog/` directory)
  4. ✅ Basic styling consistent with site
  5. Optional: RSS feed for extra SEO
- **Content:** Blog posts live in `/blog/*.md` with front matter (title, date, tags, description)
- **First post:** ✅ "How We Refactored 3,000 Lines of Code to 600" published
- **Completed:** 2026-02-19, commit 47c7508
- **Approved by:** Ayaan (2026-02-18)

---

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
- [x] Dashboard wired to /api/my-grants (2026-02-14): Dashboard now uses getMyGrants() for authenticated users, displaying org-specific scored grants. Issue #44 CLOSED. Commit 4858a2f
- [x] Improved chat error handling (2026-02-16): Better error messages for agent unavailability (500s) and connection issues. Helps users understand temporary outages. Commit 71ab64f
- [x] OG image for social sharing (2026-02-17): Added dynamic OG/Twitter images using Next.js ImageResponse API. Branded 1200x630 card with logo, tagline, features. Issue #30 CLOSED. Commit f0f63e5
- [x] Created Issue #46 for agent onboarding org auto-create bug (2026-02-17): When users onboard via chat instead of web, no org gets created. Discovered in BACKLOG.md.
- [x] Agent onboarding org auto-create endpoint (2026-02-18): Added `POST /api/workspace/ensure-org` endpoint. Creates organization_config + users records if missing. Agent can call this during first conversation. Commit add1dcc. Issue #46 addressed (agent-side integration still needed).
- [x] Created Issue #47 for context window optimization (2026-02-18): Research-backed enhancement - as orgs add more documents, agent context grows and personalization effectiveness degrades (attention dilution). Future optimization.
- [x] Fixed Pydantic model ordering crash (2026-02-18): EnsureOrgRequest/UpdateProfileRequest were defined AFTER the endpoints that used them, causing NameError on backend startup. Commit 837f143.
- [x] Fixed session endpoint temp-org fallback (2026-02-18): Session list/get/add endpoints now handle users without orgs (temp-{user_id} pattern), consistent with chat endpoints. Fixes 400 errors for new users. Commit 290e83a.
- [x] Dev blog launched (2026-02-19): Created `/blog` route with markdown rendering, blog index, individual post pages. First post: "How We Refactored 3,000 Lines of Code to 600". Added gray-matter for front matter parsing. Updated Header nav + sitemap. Commit 47c7508.
- [x] RSS feed for blog (2026-02-20): Added `/blog/feed.xml` RSS 2.0 route with autodiscovery link in HTML head and RSS button on blog page. Issue #48 CLOSED. Commit 67b0dc5.
- [x] Enhanced fundfish-api.sh script (2026-02-20): Added `ensure-org` and `update-profile` commands to agent API script for easier onboarding flow. Part of Issue #46 agent-side integration.
- [x] Match Profile UI in Settings (2026-02-22): Added 🎯 Match Profile tab showing active keywords, scoring weights, excluded keywords. Lazy-loads from /api/organization/match-profile. Issue #51 CLOSED. Commit cc32e1d.
- [x] Fixed hardcoded org_id=15 in /api/opportunities (2026-02-22): All users were seeing Per Scholas demo org's opportunities. Fixed with dynamic lookup. Commit 9cf5fd9.
- [x] Backend pagination for grants endpoints (2026-02-22): Added limit/offset to /api/scraped-grants and /api/my-grants, default limit=150. Includes has_more flag. Commit 9cf5fd9.
- [x] Blog post #3 (2026-02-22): "Inside the Black Box: How FundFish Scores Grants for Your Nonprofit" — explains match profile + connects to agentic search research. Commit a3b94e7.
- [x] Removed DEBUG print statements from opportunities.py (2026-02-23): Cleaned 4 [DEBUG] prints + /tmp file write. Issue #53 CLOSED. Commit 89f01e9.
- [x] Load-more for Dashboard (2026-02-23): Frontend now tracks has_more flag and shows Load More button when backend has additional grants beyond the initial 150. Both grid + table views. api.ts getMyGrants/getScrapedGrants accept limit/offset. Commit 89f01e9. Issue #52 CLOSED 2026-02-24.
- [x] Blog post #4 (2026-02-23): "The Grant Deadline Problem: Why Most Nonprofits Miss Money They Could Have Won" — sets up case for deadline alerts + pipeline tracking features. Commit f1ec09a.
- [x] Created Issues #54, #55, #56, #57 (2026-02-23): Deadline alerts, server-side filtering, grant pipeline status tracking, agent-aware retrieval research.
- [x] Deadline alert emails (2026-02-24): Issue #54 CLOSED. backend/jobs/deadline_alerts.py queries org_grants for grants expiring in 30/7/2 days (non-overlapping windows). email_service.py gets send_deadline_alert() with urgency-coded HTML template (🔴 URGENT 2d / 🟡 SOON 7d / 🔵 UPCOMING 30d). Hooked into APScheduler at 8:15 AM EST. Commit 18c45c4.
- [x] Grant pipeline status tracking (2026-02-24): Issue #56 CLOSED. PATCH /api/my-grants/{grant_id}/status endpoint (active/saved/in_progress/submitted/won/lost/dismissed). Frontend: pipeline status dropdown on each grant card for authenticated users, optimistic UI, initializes from org_status. Commit 18c45c4.
- [x] Server-side search (2026-02-24): Issue #55 partial. GET /api/my-grants now accepts ?search= param. Case-insensitive match across title, funder, description, agency. api.ts updated. Commit 18c45c4.
- [x] Created Issues #58, #59, #60 (2026-02-24): Pipeline status filter tabs, notification preferences, EXACT paper inference-time personalization research.
- [x] Fixed org_briefs content null bug (2026-02-26): generate_briefs.py now populates content, grant_summaries, delivery_address. Issue #61 CLOSED. Commit d9cf0d2.
- [x] Server-side filtering backend (2026-02-26): /api/my-grants now supports category_id, min_amount, max_amount, due_within_days, sort_by, sort_dir. Issue #55 partially done (frontend migration pending). Commit 6a6a523.
- [x] Notification preferences (2026-02-26): New Settings tab for email/brief/deadline prefs. Backend respects prefs in deadline_alerts.py + generate_briefs.py. Issue #59 CLOSED. Commit 1b8e0ed.
- [x] Server-side filtering frontend (2026-02-27): Dashboard now passes filter params to API (search, category, amount range, deadline, sort). Debounced keyword search (300ms). Load More respects filters. Issue #55 CLOSED. Commit 40896a8.
- [x] Blog post #5 (2026-02-27): "From Chaos to Pipeline: How to Track Every Grant Application Without Losing Your Mind" — explains pipeline tracking + deadline alerts. Commit 0f1bb7b.
- [x] Updated sitemap (2026-02-27): Added all blog posts to sitemap.xml. Commit b2b0a72.
- [x] Blog content consolidation (2026-02-28): Recovered orphaned post from frontend/content/blog/ subdirectory, copied missing grant-pipeline-management post, removed legacy root blog/ directory. Now 10 blog posts active in frontend/content/. Commits fbd9646, 0dc0d92, 42d4ea2.
- [x] Updated sitemap with 3 missing posts (2026-02-28): Added grant-writing-tips, government-grants-guide, grant-pipeline-tracking to sitemap.xml. Commit fbd9646.
- [x] Research context for Issue #47 (2026-02-28): Added notes on DySCO (retrieval-head-guided attention, arXiv 2602.22175) and "Tell Me What To Learn" (natural language memory updates, arXiv 2602.23201) papers — both relevant to context window optimization.
- [x] Fixed notification_preferences column missing error (2026-03-01): Jobs were logging errors because migration 006 hadn't been run. Updated deadline_alerts.py, generate_briefs.py, and organization.py to gracefully handle missing column and return defaults. Issue #62 created for migration. Commit 9328d7e.
- [x] Updated sitemap with Feb 28 blog posts (2026-03-01): Added ai-grant-writing and how-to-apply-for-hud-grants posts. Commit 1e3ce0b.
- [x] Research context for Issues #47, #57 (2026-03-01): Added notes on ParamMem (parametric reflective memory), Tell Me What To Learn, and MTRAG-UN (RAG edge cases) papers from latest arxiv digests.
- [x] Updated sitemap with March 1 blog posts (2026-03-02): Added ai-grant-writing-for-nonprofits and grant-deadline-management-for-nonprofits to sitemap.xml. Commit 2fee37f.
- [x] Removed all print statements from opportunities.py (2026-03-02): Cleaned 20+ debug prints from opportunities routes. Follows Issue #53 pattern. Cleaner Render logs for production. Commit 5b07ba3.
- [x] Updated sitemap with March 3 blog post (2026-03-04): Added how-to-write-a-winning-grant-proposal to sitemap.xml. Commit 594f784.
- [x] Research context for Issues #47, #57 (2026-03-04): Added notes on "Do LLMs Benefit From Their Own Words?" (MIT CSAIL, context pollution/pruning) and AgenticOCR (query-driven document parsing) papers from March 2 arxiv digest. Both directly applicable to agent context optimization.
- [x] Updated sitemap with March 4 blog post (2026-03-05): Added what-to-include-in-a-grant-proposal-the-complete-checklist-for-nonprofits to sitemap.xml. Commit 9f67f92.
- [x] Logging cleanup (2026-03-05): Replaced all 83 print() statements in backend/routes/ with proper Python logging. All 10 route files updated. Issue #63 CLOSED. Commit 9f67f92.
- [x] Research context for Issues #47, #57 (2026-03-05): New papers from March 4 arxiv digest:
  - Speculative Speculative Decoding (Saguaro) by Tri Dao — 2x-5x faster inference
  - MOSAIC (Microsoft) — Safe multi-step tool use for agents, 50% harm reduction
  - CDI (Stanford/Microsoft) — Privacy defense for LLM agents, 94% preservation with 80% helpfulness
  - Graph-GRPO — Multi-agent topology optimization via GRPO
- [x] Blog post #6 (2026-03-06): "How to Find Foundation Grants for Nonprofits: The Complete Guide to Private Funding" — comprehensive guide to private/corporate/community foundations, research methods, relationship building. Targets new keywords: foundation grants, private foundations, corporate giving. Commit d13f5f8.
- [x] Updated sitemap with March 6 blog post (2026-03-06): Added how-to-find-foundation-grants-for-nonprofits to sitemap.xml. Commit d13f5f8.
- [x] Research context for Issues #47, #57 (2026-03-06): Added notes on Saguaro (Tri Dao inference speedup), MOSAIC (safe tool use), CDI (privacy defense), AgenticOCR (query-driven document parsing) from March 2+4 arxiv digests.
- [x] Closed Issue #39 (2026-03-08): Custom search keywords feature was already implemented. Backend has `custom_search_keywords` in organization_config, `build_search_keywords()` uses them dynamically, Settings UI has textarea input, Match Profile tab shows active keywords. Verified end-to-end working.
- [x] Blog post #7 (2026-03-08): "Common Grant Rejection Reasons (and How to Avoid Them)" — covers top 10 rejection reasons with prevention strategies. High-intent SEO target. Commit 0552449.
- [x] Updated sitemap with March 7 + March 8 blog posts (2026-03-08): Added grant-proposal-template and common-grant-rejection-reasons posts to sitemap.xml. Commit 0552449.
- [x] Updated sitemap with 2 missing March 8 posts (2026-03-09): Added how-to-manage-multiple-grant-applications and free-grant-search-tools-for-nonprofits. Commit d2f0c48.
- [x] Blog post #8 (2026-03-09): "How to Write a Grant Budget: The Complete Guide for Nonprofits" — comprehensive budgeting guide covering line-item vs functional budgets, budget narratives, indirect costs, matching funds, federal requirements, and common mistakes. High-intent keyword target: grant budget. Commit 1720433.
- [x] Migration 006_notification_preferences.sql (2026-03-10): Ran via Supabase Management API. notification_preferences JSONB column now exists in organization_config. Issue #62 CLOSED.
- [x] Issue #46 verified and closed (2026-03-10): Agent onboarding auto-create org fix confirmed working. Commit 6cc9464 adds auto_create_org_for_user() function. No more temp- prefix routing.
- [x] Blog post #9 (2026-03-10): "Grant Reporting Requirements: The Complete Guide to Post-Award Compliance" — covers financial/narrative/outcome reports, federal compliance (2 CFR 200), reporting systems, best practices, technology tools. High-intent keywords: grant reporting, grant compliance. Commit bf61a56.
- [x] Updated sitemap with missing March 10 post (2026-03-11): Added best-grant-databases-for-nonprofits post that was missed. Cleaned up stale BACKLOG.md (removed fixed Issue #46 bug). Commit b4a3ffa.
- [x] Updated sitemap with March 11 blog post (2026-03-12): Added small-nonprofit-funding-strategies-complete-2026-guide-sustainable-revenue-mix to sitemap.xml. Commit 9703d3b.
- [x] Blog post #10 (2026-03-12): "First-Time Grant Seeker's Guide: The Complete Beginner's Roadmap to Winning Funding" — comprehensive guide covering grant-readiness assessment, grant types, finding first grants, writing proposals, and building long-term success. Targets high-intent keywords: first grant, beginner grant writing. Commit 03b8c5b.
