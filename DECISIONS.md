# DECISIONS.md — Owner Feedback & Priorities
# Updated by Maya when Ayaan gives direction. Read this FIRST every run.
# Last updated: 2026-02-03

## Important Context
- **Domain is fundfish.pro** — NOT fundfishpro.netlify.app. The agent was checking the wrong URL. Check the actual domain first before reporting the site as down.

## Pending Decisions (awaiting Ayaan's input)
- **Agentic pivot (partial)** — Proposal writer approved but scope is HARD — real grant proposals are 60+ pages with extensive user documentation. Don't underestimate this. Grant discovery and donor outreach: hold for now.

## Approved — Investigate ASAP

### Backend Scheduler Not Producing New Grants
- **Priority:** High
- **Status:** Not started
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

## Approved — Do These
- [x] **Verify site status** — fundfish.pro returns HTTP 200, served by Netlify. ✅ 2026-01-31
- [x] **API security** — Audited all endpoints, found 13 without auth, fixed all. Issue #27, commit c07d455. ✅ 2026-01-31
- [x] **Landing page** — Built full landing page (hero, features, CTA, footer). Issue #28, commit 532a9d8. ✅ 2026-01-31
- [x] **GA4 Analytics** — Added GA4 tracking script to layout.tsx. Placeholder ID `G-FUNDFISH` — needs real measurement ID from Ayaan. Issue #31. ✅ 2026-02-02
- [x] **GA4 — Real Measurement ID** — G-90C1JMVYN0 wired in commit b5d871b. Issue #31 closed. ✅ 2026-02-03
- [ ] **Polish existing features** — ONGOING. Auth fixes shipped, nav fixed, signup bug fixed. Continue polishing.

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
