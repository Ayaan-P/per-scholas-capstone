# FundFish Agent Templates

This directory contains the workspace templates for FundFish organization agents.

## Template Structure

```
fundfish/
├── PROFILE.md      # Organization profile template (synced from DB)
├── STYLE.md        # Writing style guide for proposals
├── TOOLS.md        # Reference for available agent tools
└── DECISIONS.md    # Learning log for agent decisions
```

## How Templates Are Used

When a new organization workspace is provisioned:

1. The provisioning script creates the workspace directory structure
2. Template files are copied as initial versions
3. `PROFILE.md` is immediately synced with org data from the database
4. Other files remain as templates for the agent/user to customize

## Template Variables

Templates support these placeholder variables (replaced during provisioning):

- `{{name}}` - Organization name
- `{{mission}}` - Mission statement
- `{{created_at}}` - Workspace creation timestamp
- `{{updated_at}}` - Last update timestamp
- `{{last_synced}}` - Last profile sync timestamp
- Other org fields as specified in PROFILE.md

## Customizing Templates

Edit these files to change the default content for new workspaces:

- **PROFILE.md** - Structure for org data display (mostly auto-populated)
- **STYLE.md** - Default writing guidelines (agent will refine based on feedback)
- **TOOLS.md** - API/tool documentation for agents
- **DECISIONS.md** - Learning log structure

## Provisioning

Use the provisioning script to create new workspaces:

```bash
# Provision a real organization
python scripts/provision_org_agent.py <org_id>

# Create a test organization
python scripts/provision_org_agent.py --create-test

# List all workspaces
python scripts/provision_org_agent.py --list

# Run cleanup on old sessions
python scripts/provision_org_agent.py --cleanup <org_id>
```

## Workspace Structure (After Provisioning)

```
/var/fundfish/workspaces/{org_id}/
├── PROFILE.md              # Synced org profile
├── STYLE.md                # Writing style guide
├── TOOLS.md                # Tool reference
├── DECISIONS.md            # Learning log
├── memory/
│   ├── YYYY-MM-DD.md       # Daily activity logs
│   ├── briefs/
│   │   └── YYYY-MM-DD.md   # Morning brief copies
│   └── sessions/
│       └── {session_id}.md # Chat session history
├── grants/
│   ├── grant-{id}.md       # Research notes per grant
│   ├── saved/              # Legacy: saved grants (JSON)
│   └── applied/            # Legacy: applied grants
├── proposals/
│   └── draft-{id}.md       # Proposal drafts
├── documents/
│   └── extracted/          # Extracted document text
└── archive/
    ├── sessions/           # Archived old sessions
    └── memory/             # Archived old memory files
```

## Environment Variables

- `FUNDFISH_WORKSPACE_ROOT` - Workspace root directory (default: `/var/fundfish/workspaces`)
- `SUPABASE_URL` - Supabase project URL (for DB sync)
- `SUPABASE_SERVICE_ROLE_KEY` - Service role key (for DB sync)

## Deployment on Hetzner Agent Host

The workspace root should be configured to match the Clawdbot agent workspace:

```bash
export FUNDFISH_WORKSPACE_ROOT=/home/clawdbot/agents/fundfish
```

This allows the agent bridge to route messages to persistent agent sessions with full workspace context.
