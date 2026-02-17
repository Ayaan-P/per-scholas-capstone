
## Auto-create org on agent onboarding [BUG]
**Added:** 2026-02-16
**Priority:** High

When a new user onboards via the Hetzner agent (not web app), no organization is created in `organization_config`. This breaks the qualification job.

**Fix:** Agent should check for existing org on first conversation. If none exists:
1. Ask for org name/mission
2. Create entry in `organization_config`
3. Store org_id for future sessions

**Discovered:** Qualification job ran in 12 seconds because org table was empty.

