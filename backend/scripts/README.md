# FundFish Backend Scripts

Utility scripts for managing the FundFish agent infrastructure.

## provision_org_agent.py

Provision workspaces for organization agents.

### Usage

```bash
# Provision workspace for an existing organization (fetches config from DB)
python provision_org_agent.py <org_id>

# Create and provision a test organization
python provision_org_agent.py --create-test

# List all provisioned workspaces
python provision_org_agent.py --list

# Run cleanup (archive old sessions/memory files)
python provision_org_agent.py --cleanup <org_id>

# Override workspace root directory
python provision_org_agent.py --workspace-root /custom/path <org_id>
```

### What It Does

1. **Creates directory structure**
   - Core files: PROFILE.md, STYLE.md, TOOLS.md, DECISIONS.md
   - Memory directories: memory/, memory/sessions/, memory/briefs/
   - Grant tracking: grants/, grants/saved/, grants/applied/
   - Proposals: proposals/
   - Documents: documents/extracted/
   - Archive: archive/sessions/, archive/memory/

2. **Syncs organization profile**
   - Fetches org config from Supabase database
   - Populates PROFILE.md with org data
   - Falls back to template if DB unavailable

3. **Initializes memory**
   - Creates daily log entry for workspace provisioning
   - Records initial decision in DECISIONS.md

4. **Cleanup/archiving**
   - Archives sessions older than 30 days
   - Keeps max 90 daily memory files (archives older ones)

### Environment Variables

Required for database sync:
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` - Service role key

Optional:
- `FUNDFISH_WORKSPACE_ROOT` - Workspace root (default: /var/fundfish/workspaces)

### Example Output

```
📁 Initializing workspace for test-org-001...
   ✓ Created at: /var/fundfish/workspaces/test-org-001

🔍 Fetching organization config from database...
   ✓ Found: Test Nonprofit Organization

📝 Syncing profile to workspace...
   ✓ Profile synced

🧠 Creating initial memory entry...
   ✓ Memory initialized

✅ Recording initial decision log...
   ✓ Decisions log created

==================================================
✓ Provisioning complete for: test-org-001
  Workspace: /var/fundfish/workspaces/test-org-001
  Org name: Test Nonprofit Organization
==================================================
```

## Future Scripts

Planned additions:
- `sync_all_profiles.py` - Batch sync all org profiles from DB
- `generate_briefs.py` - Generate morning briefs for all orgs
- `run_discovery.py` - Run grant discovery agents
- `archive_workspaces.py` - Archive inactive org workspaces
