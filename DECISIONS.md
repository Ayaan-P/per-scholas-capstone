# DECISIONS.md — Owner Feedback & Priorities
# Updated by Maya when Ayaan gives direction. Read this FIRST every run.
# Last updated: 2026-01-31

## Important Context
- **Domain is fundfish.pro** — NOT fundfishpro.netlify.app. The agent was checking the wrong URL. Check the actual domain first before reporting the site as down.

## Pending Decisions (awaiting Ayaan's input)
- **Agentic pivot** — 3 issues created (grant discovery, proposal writer, donor outreach). Ayaan is thinking on this. Do NOT start pivot work yet.

## Approved — Do These
- [ ] **Verify site status** — Check fundfish.pro (the real domain), not the Netlify subdomain. Report actual status.
- [ ] **API security** — Harden all endpoints that skip auth. Plan this out: audit every endpoint, create GitHub issues for each fix, then implement.
- [ ] **Landing page** — Build a real landing page with conversion funnel. Plan this out: break into subtask issues (hero, features, CTA, etc.), then implement.

## How to Work
- For each approved item: **plan first** — break into subtask issues on GitHub, THEN implement.
- Don't just jump into code. Create the issues so progress is trackable.

## Completed
- [x] Fixed stray `c` character in dashboard table (PR #14)
