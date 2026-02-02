# DECISIONS.md — Owner Feedback & Priorities
# Updated by Maya when Ayaan gives direction. Read this FIRST every run.
# Last updated: 2026-01-31

## Important Context
- **Domain is fundfish.pro** — NOT fundfishpro.netlify.app. The agent was checking the wrong URL. Check the actual domain first before reporting the site as down.

## Pending Decisions (awaiting Ayaan's input)
- **Agentic pivot (partial)** — Proposal writer approved but scope is HARD — real grant proposals are 60+ pages with extensive user documentation. Don't underestimate this. Grant discovery and donor outreach: hold for now.

## Approved — Do These
- [x] **Verify site status** — fundfish.pro returns HTTP 200, served by Netlify. ✅ 2026-01-31
- [x] **API security** — Audited all endpoints, found 13 without auth, fixed all. Issue #27, commit c07d455. ✅ 2026-01-31
- [x] **Landing page** — Built full landing page (hero, features, CTA, footer). Issue #28, commit 532a9d8. ✅ 2026-01-31
- [x] **GA4 Analytics** — Added GA4 tracking script to layout.tsx. Placeholder ID `G-FUNDFISH` — needs real measurement ID from Ayaan. Issue #31. ✅ 2026-02-02
- [ ] **GA4 — Real Measurement ID** — Ayaan needs to create GA4 property and replace `G-FUNDFISH`. Issue #31.
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
