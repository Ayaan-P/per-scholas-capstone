# Workspace Service Extensions

**Date:** 2026-02-10

## What Already Existed

The original `workspace_service.py` had:
- ✅ Workspace initialization (`init_workspace`, `workspace_exists`)
- ✅ Profile sync from DB (`sync_profile_from_db`)
- ✅ Session management (`create_session`, `append_to_session`, `get_session_history`, `list_sessions`)
- ✅ Grant saving (`save_grant`, `get_saved_grants`)
- ✅ Document extraction (`save_extracted_text`)
- ✅ Agent context builder (`get_agent_context`)
- ✅ Decisions logging (`update_decisions`)
- ✅ Default templates (`_default_profile`, `_default_style`, `_default_decisions`)

**Original structure:**
```
/workspaces/{org_id}/
├── PROFILE.md
├── STYLE.md
├── memory/
│   ├── sessions/*.md
│   └── decisions.md
├── grants/
│   ├── saved/*.json
│   └── applied/
└── documents/extracted/
```

## What Was Added (Extensions)

### 1. Daily Memory Logs (`memory/YYYY-MM-DD.md`)
```python
log_memory(org_id, entry, entry_type)  # Log with type (note, decision, observation, feedback, action)
get_memory(org_id, date)               # Get specific day's log
get_recent_memory(org_id, days=2)      # Get last N days for agent context
```

### 2. Brief History (`memory/briefs/YYYY-MM-DD.md`)
```python
save_brief(org_id, subject, content, grant_ids)  # Save morning brief
get_brief(org_id, date)                          # Get specific brief
list_briefs(org_id, limit=7)                     # List recent briefs
```

### 3. Grant Research Notes (`grants/grant-{id}.md`)
```python
save_grant_research(org_id, grant_id, grant_data, analysis, eligibility, notes)
get_grant_research(org_id, grant_id)
update_grant_notes(org_id, grant_id, notes)
list_grant_research(org_id)
```

### 4. Cleanup/Archiving
```python
cleanup_old_sessions(org_id, days=30)    # Archive sessions older than 30 days
cleanup_old_memory(org_id, max_files=90) # Keep max 90 daily memory files
full_cleanup(org_id)                     # Run all cleanup tasks
```

### 5. Template Loading
- Added TOOLS.md to default templates
- Added `_init_from_templates()` to load from `agent_templates/fundfish/`
- Falls back to inline defaults if templates missing

### 6. Enhanced `get_agent_context()`
Now includes:
- `profile` - PROFILE.md
- `style` - STYLE.md
- `tools` - TOOLS.md (new)
- `decisions` - DECISIONS.md
- `recent_memory` - Last 2 days of memory logs (new)

**Extended structure:**
```
/workspaces/{org_id}/
├── PROFILE.md
├── STYLE.md
├── TOOLS.md              # NEW
├── DECISIONS.md          # Moved from memory/
├── memory/
│   ├── YYYY-MM-DD.md     # NEW: Daily logs
│   ├── briefs/           # NEW
│   │   └── YYYY-MM-DD.md
│   └── sessions/*.md
├── grants/
│   ├── grant-{id}.md     # NEW: Research notes
│   ├── saved/*.json
│   └── applied/
├── proposals/            # NEW (directory only)
├── documents/extracted/
└── archive/              # NEW
    ├── sessions/
    └── memory/
```

## Backward Compatibility

✅ All original methods preserved with same signatures  
✅ Original directory structure maintained  
✅ `grants/saved/` JSON format still works (legacy)  
✅ `memory/sessions/` still works exactly as before  
✅ `get_agent_context()` returns same keys plus new ones  

## New Files Created

| File | Purpose |
|------|---------|
| `agent_templates/fundfish/PROFILE.md` | Profile template |
| `agent_templates/fundfish/STYLE.md` | Style guide template |
| `agent_templates/fundfish/TOOLS.md` | Tools reference template |
| `agent_templates/fundfish/DECISIONS.md` | Decisions log template |
| `agent_templates/README.md` | Template documentation |
| `scripts/provision_org_agent.py` | Provisioning script |
| `scripts/README.md` | Script documentation |
