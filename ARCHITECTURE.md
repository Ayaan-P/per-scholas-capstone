# FundFish Architecture

> Last updated: 2026-02-18 by Maya
> Read this FIRST before touching FundFish.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FundFish System                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │   HETZNER    │    │    RENDER    │    │   NETLIFY    │               │
│  │  (Agents)    │    │  (Backend)   │    │  (Frontend)  │               │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘               │
│         │                   │                   │                        │
│         ▼                   ▼                   ▼                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │  Librarian   │    │   FastAPI    │    │   Next.js    │               │
│  │  Qualifier   │    │   + Email    │    │   Dashboard  │               │
│  │  Chat Agent  │    │   Service    │    │   + Chat UI  │               │
│  └──────────────┘    └──────────────┘    └──────────────┘               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Hetzner (46.225.82.130)

**Agent API:** `http://localhost:9090` (internal) / port 9090 (external)
**Auth Token:** `cdbe8e97d1fbaba8d0ce17bcdb202b4491ef8795fb4cf85cd8289f0173ff9a35`

#### Agents on Hetzner:

| Agent | user_id | Purpose |
|-------|---------|---------|
| Librarian | `fundfishmain` | Scrapes grants, adds to DB |
| Qualifier | (uses librarian) | Scores grants for each org |
| Chat Agent | `ff-{org_id}` | Handles user chat sessions |

#### Key Files on Hetzner:
- `/home/dytto-agent/workspaces/lib-fundfishmain/` — Librarian workspace
  - `TOOLS.md` — Database CRUD instructions
  - `supabase-grants.sh` — Script to insert/upsert grants
  - `send-email.sh` — Resend API wrapper (has RESEND_API_KEY)
  - `.env` — Supabase credentials
- `/home/dytto-agent/workspaces/ff-{org_name}/` — Per-org agent workspaces
  - `TOOLS.md` — Grant querying + scoring + email tools
  - `send-email.sh` — Copy of email script
  - `.env` — Supabase credentials
  - `USER.md` — Org ID and context

### 2. Render (per-scholas-capstone)

**URL:** `https://per-scholas-capstone.onrender.com`
**Service ID:** `srv-d5kejlvgi27c739pl6ag`

#### Key Services:
- **FastAPI Backend** — `/api/*` endpoints
- **Email Service** — Uses Resend API for morning briefs
- **Brief Scheduler** — APScheduler runs at 8 AM EST daily

#### Environment Variables (Render):
- `RESEND_API_KEY` — For sending emails ✓ SET
- `SUPABASE_URL` / `SUPABASE_KEY` — Database access
- `AGENT_BRIDGE_URL` — Points to Hetzner (http://46.225.82.130:9090)
- `AGENT_BRIDGE_TOKEN` — Auth for Hetzner agents

### 3. Netlify (Frontend)

**URL:** `https://fundfish.pro`
**Repo:** `frontend/` directory

### 4. Supabase (Database)

**URL:** `https://zjqwpvdcpzeguhdwrskr.supabase.co`

#### Key Tables:

| Table | Purpose |
|-------|---------|
| `scraped_grants` | Raw grants from all sources |
| `org_grants` | Scored/qualified grants per org |
| `org_briefs` | Sent brief history |
| `organization_config` | Org profiles |
| `users` | User accounts |

---

## Data Flow

### Grant Discovery (Daily)

```
Cron Job (Maya's clawdbot)
    │
    ▼
SSH to Hetzner
    │
    ▼
Invoke Librarian Agent (fundfishmain)
    │
    ├── Search grant sources (web, APIs)
    ├── Extract grant details
    └── Write to scraped_grants via supabase-grants.sh
```

**Cron:** Runs via Maya's clawdbot cron
**Script:** `~/.clawdbot/cron/jobs.json` (look for "HUNT FOR GRANTS")

### Grant Qualification (After Discovery)

```
Org's Personal Agent (ff-{org_name} on Hetzner)
    │
    ├── Query scraped_grants (last 24h)
    ├── Read org profile from USER.md or organization_config
    ├── Score each grant against org profile
    ├── Write to org_grants with:
    │   - match_score (0-100)
    │   - match_reasoning (why it fits)
    │   - llm_summary (what the grant funds + amount)
    │   - key_tags (keywords)
    │   - effort_estimate (low/medium/high)
    │   - winning_strategies (tips)
    └── If good matches found → send morning brief via send-email.sh
```

**Tools:** `/home/dytto-agent/workspaces/ff-{org}/TOOLS.md`
**Email:** `/home/dytto-agent/workspaces/ff-{org}/send-email.sh`

### Morning Brief (8 AM EST Daily)

```
Render APScheduler (brief_scheduler)
    │
    ▼
jobs/generate_briefs.py
    │
    ├── Query organization_config for all orgs
    ├── For each org:
    │   ├── Query org_grants (score > 70, active, future deadline)
    │   ├── Take top 3 grants
    │   └── Send email via Resend API
    └── Log to org_briefs table
```

**Trigger:** APScheduler in main.py (8 AM EST)
**Email Service:** `backend/email_service.py`

### User Chat

```
User (fundfish.pro/chat)
    │
    ▼
Render Backend (/api/workspace/chat)
    │
    ▼
Hetzner Agent Bridge (port 9090)
    │
    ▼
Chat Agent (ff-{org_id} or temp-{user_id})
    │
    └── Uses workspace context, grant search, etc.
```

---

## Known Issues & Fixes

### Issue: Funding amounts are NULL
**Location:** Librarian agent on Hetzner
**File:** `/home/dytto-agent/workspaces/fundfishmain/TOOLS.md` or `supabase-grants.sh`
**Problem:** Scraper isn't extracting amount, award_floor, award_ceiling
**Fix:** Update librarian's scraping prompts/tools to capture amounts

### Issue: Qualification missing analysis fields
**Location:** `~/clawd/agents/fundfish-qualifier/qualify-grants.sh`
**Problem:** Only wrote match_score and match_reasoning
**Fix:** ✅ FIXED 2026-02-18 — Now writes all 6 fields

### Issue: Chat returns 401
**Location:** Hetzner agent bridge
**Problem:** OAuth token refresh failing
**Fix:** Re-authenticate Clawdbot on Hetzner for anthropic OAuth

---

## Cron Jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| Librarian hunt | Daily | Find new grants |
| Qualification | After hunt | Score grants per org |
| Morning brief | 8 AM EST | Send email briefs |

---

## API Endpoints (Render)

### Health
- `GET /api/health` — Returns scheduler status

### Grants
- `GET /api/my-grants` — Get scored grants for authenticated user's org
- `POST /api/grants/dismiss` — Dismiss a grant

### Workspace/Chat
- `POST /api/workspace/chat` — Send message to agent
- `POST /api/workspace/ensure-org` — Create org during onboarding
- `GET /api/workspace/uploads` — List uploaded files

### Processing
- `POST /api/processing/generate-brief` — Manually trigger brief

---

## Debugging

### Check if librarian ran:
```bash
ssh hetzner "cat /home/dytto-agent/workspaces/fundfishmain/logs/$(date +%Y-%m-%d).md"
```

### Check scraped grants:
```bash
curl -s "$SUPABASE_URL/rest/v1/scraped_grants?select=title,amount,source&order=created_at.desc&limit=5" \
  -H "apikey: $SUPABASE_KEY"
```

### Check org_grants (scored):
```bash
curl -s "$SUPABASE_URL/rest/v1/org_grants?select=*&order=created_at.desc&limit=5" \
  -H "apikey: $SUPABASE_KEY"
```

### Trigger brief manually:
```bash
curl -X POST "https://per-scholas-capstone.onrender.com/api/processing/generate-brief" \
  -H "Authorization: Bearer <user_token>"
```

### Check Render logs:
```bash
bash ~/.claude/lib/render-logs.sh capstone --limit 50
```

---

## File Locations

### Local (Maya's machine)
- `~/projects/perscholas-fundraising-demo/` — Main repo
- `~/clawd/agents/fundfish-qualifier/` — Qualification scripts
- `~/.clawdbot/cron/jobs.json` — Cron job definitions
- `~/.clawdbot/agents/pm-fundfish/` — Zoe (PM agent) config

### Hetzner
- `/home/dytto-agent/workspaces/fundfishmain/` — Librarian
- `/home/dytto-agent/workspaces/ff-*/` — Per-org agents

### Render (deployed from repo)
- `backend/main.py` — FastAPI app + schedulers
- `backend/email_service.py` — Resend integration
- `backend/jobs/generate_briefs.py` — Brief generation
- `backend/jobs/process_grants.py` — Alternative scoring (not currently used)
- `backend/scoring_agent.py` — LLM-based scoring logic

---

## Contact

- **Ayaan** — Founder, has all credentials
- **Maya** — AI PM, manages agents
- **Zoe** — FundFish PM agent (@dytto_zoe)
