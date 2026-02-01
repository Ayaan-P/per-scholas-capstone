# DECISIONS.md — Owner Feedback & Priorities
# Updated by Maya when Ayaan gives direction. Read this FIRST every run.
# Last updated: 2026-01-31

## Important Context
- **Domain is fundfish.pro** — NOT fundfishpro.netlify.app. The agent was checking the wrong URL. Check the actual domain first before reporting the site as down.

## Pending Decisions (awaiting Ayaan's input)
- **Agentic pivot** — 3 issues created (grant discovery, proposal writer, donor outreach). Ayaan is thinking on this. Do NOT start pivot work yet.

## Approved — Do These
- [x] **Verify site status** — fundfish.pro returns HTTP 200, served by Netlify. ✅ 2026-01-31
- [x] **API security** — Audited all endpoints, found 13 without auth, fixed all. Issue #27, commit c07d455. ✅ 2026-01-31
- [x] **Landing page** — Built full landing page (hero, features, CTA, footer). Issue #28, commit 532a9d8. ✅ 2026-01-31

## How to Work
- For each approved item: **plan first** — break into subtask issues on GitHub, THEN implement.
- Don't just jump into code. Create the issues so progress is trackable.

## Completed
- [x] Fixed stray `c` character in dashboard table (PR #14)
- [x] API security hardening — 13 endpoints secured (Issue #27, 2026-01-31)
- [x] Landing page for fundfish.pro (Issue #28, 2026-01-31)
