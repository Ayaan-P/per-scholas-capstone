# FundFish Agentic Architecture Spec

## Vision: AI-Powered Grant Discovery & Application Assistant

**Core Value Proposition:** Nonprofits wake up to a personalized brief of the top 3 grants they should apply for, with intelligent reasoning and one-click help to draft proposals.

---

## System Architecture

### **Layer 1: Discovery Agents**
Autonomous agents that find grants across multiple sources.

**Sources:**
- Grants.gov (federal)
- State grant portals (50 states)
- Foundation databases
- Local government sites
- News/announcements

**Agent Behavior:**
- Uses browser automation (Playwright + GPT-4V/Claude) instead of brittle scrapers
- Self-healing when sites change
- Extracts structured data (title, funder, amount, deadline, requirements, etc.)
- Writes to `scraped_grants` (global pool)

**Trigger:** Daily cron (staggered by source)

---

### **Layer 2: Org Qualification Agents**
One persistent agent per organization that learns and scores grants.

**Agent Capabilities:**
- Workspace with org profile, preferences, memory
- Scores grants based on mission alignment, capacity, past wins/losses
- Learns from user feedback (dismissals, saves, applications)
- Writes to `org_grants` (org-specific state)

**Trigger:** 
- Scheduled (nightly after discovery completes)
- On-demand (user opens dashboard, requests re-score)

**Processing Flow:**
```python
1. Read new grants from scraped_grants (WHERE created_at > last_run)
2. For each grant:
   - Check eligibility criteria
   - Score match (0-100)
   - Generate reasoning
   - Extract key tags
   - Write summary
3. Write to org_grants (grant_id, org_id, match_score, summary, reasoning, tags)
4. Log to workspace memory (decisions, patterns observed)
```

---

### **Layer 3: Morning Brief Agent**
Synthesizes top opportunities into a daily brief.

**Timing:** ~8am org's local timezone

**Workflow:**
```python
1. Query org_grants WHERE status='active' AND match_score > 70
2. Apply filters:
   - Deadline urgency (due within 30 days = higher priority)
   - Strategic fit (aligns with org's goals)
   - Effort/reward ratio (grant size vs application complexity)
   - Diversity (not all from same funder)
3. Select top 3 grants
4. Generate brief:
   - Compelling subject line
   - Executive summary
   - Grant #1, #2, #3 with:
     * Title & funder
     * Amount & deadline
     * Why it's a match (personalized reasoning)
     * Next steps / effort estimate
   - CTA: "Reply to discuss" or "Click to draft proposal"
5. Send via configured channel (email/WhatsApp/Slack)
6. Log to workspace memory
```

**Delivery Channels:**
- Email (HTML + plain text)
- WhatsApp (via wacli or business API)
- Slack (via webhook)
- In-app notification

---

### **Layer 4: Conversational Assistant**
Always-available chat interface for deeper work.

**User Interactions:**
- "Tell me more about grant #2"
- "Help me apply to this"
- "Draft a proposal for X"
- "Why did you score this grant so high?"
- "What grants are due this week?"
- "Update my profile - we launched a new program"

**Agent Context:**
- Session history
- Workspace memory (org profile, decisions, past briefs)
- Access to `org_grants` + `scraped_grants`
- Tool access: grants API, proposal drafts, document extraction

---

## Database Schema

### **scraped_grants** (Global Pool - Immutable)
```sql
CREATE TABLE scraped_grants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id TEXT UNIQUE,  -- External ID (e.g., from Grants.gov)
    
    -- Core fields
    title TEXT NOT NULL,
    funder TEXT,
    agency TEXT,
    amount_min BIGINT,
    amount_max BIGINT,
    deadline DATE,
    description TEXT,
    
    -- Details
    requirements JSONB,
    eligibility TEXT,
    application_url TEXT,
    contact_name TEXT,
    contact_email TEXT,
    
    -- Metadata
    source TEXT,  -- 'grants_gov', 'state_ca', 'foundation_x', 'Agent'
    geographic_focus TEXT,
    program_area TEXT[],
    
    -- Timestamps
    posted_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_scraped_grants_deadline ON scraped_grants(deadline);
CREATE INDEX idx_scraped_grants_source ON scraped_grants(source);
CREATE INDEX idx_scraped_grants_created ON scraped_grants(created_at DESC);
```

### **org_grants** (Org-Specific State & AI Analysis)
```sql
CREATE TABLE org_grants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organization_config(id) ON DELETE CASCADE,
    grant_id UUID NOT NULL REFERENCES scraped_grants(id) ON DELETE CASCADE,
    
    -- Status tracking
    status TEXT NOT NULL DEFAULT 'active',  -- active | dismissed | saved | applied
    
    -- AI-generated analysis
    match_score INT CHECK (match_score >= 0 AND match_score <= 100),
    llm_summary TEXT,  -- Short summary (2-3 sentences)
    match_reasoning TEXT,  -- Why this grant matches (structured)
    key_tags TEXT[],  -- ['workforce', 'tech-training', 'urban']
    
    -- Effort/strategy
    effort_estimate TEXT,  -- 'low', 'medium', 'high'
    winning_strategies JSONB,  -- Tips for application
    
    -- Timestamps
    tagged_at TIMESTAMPTZ DEFAULT NOW(),
    dismissed_at TIMESTAMPTZ,
    dismissed_by UUID REFERENCES users(id),
    applied_at TIMESTAMPTZ,
    
    UNIQUE(org_id, grant_id)
);

CREATE INDEX idx_org_grants_org ON org_grants(org_id, status, match_score DESC);
CREATE INDEX idx_org_grants_grant ON org_grants(grant_id);
CREATE INDEX idx_org_grants_deadline ON org_grants(org_id, status) INCLUDE (grant_id);
```

### **org_briefs** (Morning Brief History)
```sql
CREATE TABLE org_briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organization_config(id) ON DELETE CASCADE,
    
    -- Brief content
    subject TEXT NOT NULL,
    content TEXT NOT NULL,  -- Markdown or HTML
    grant_ids UUID[] NOT NULL,  -- Top 3 grants featured
    
    -- Delivery
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    delivery_channel TEXT,  -- 'email', 'whatsapp', 'slack'
    delivered BOOLEAN DEFAULT FALSE,
    opened BOOLEAN DEFAULT FALSE,
    
    -- Engagement
    clicked_grant_ids UUID[],  -- Which grants got clicks
    user_response TEXT,  -- If they replied
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_org_briefs_org ON org_briefs(org_id, sent_at DESC);
```

### **user_saves** (User Bookmarks - Optional)
```sql
CREATE TABLE user_saves (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    grant_id UUID NOT NULL REFERENCES scraped_grants(id) ON DELETE CASCADE,
    
    saved_at TIMESTAMPTZ DEFAULT NOW(),
    notes TEXT,
    folder TEXT,  -- 'High Priority', 'Research', etc.
    
    UNIQUE(user_id, grant_id)
);

CREATE INDEX idx_user_saves_user ON user_saves(user_id, saved_at DESC);
```

---

## Agent Workspace Structure

Each org gets a workspace directory on the agent host (Hetzner):

```
/home/clawdbot/agents/fundfish/{org_id}/
├── PROFILE.md              # Org mission, programs, metrics
├── STYLE.md                # Writing preferences
├── DECISIONS.md            # Learning log (what they like/dislike)
├── memory/
│   ├── 2026-02-10.md       # Daily activity log
│   ├── 2026-02-09.md
│   └── briefs/
│       ├── 2026-02-10.md   # Copy of morning brief
│       └── 2026-02-09.md
├── sessions/
│   ├── session-abc123.md   # Chat history
│   └── session-def456.md
├── grants/
│   ├── grant-xyz.md        # Deep research notes (optional)
│   └── ...
└── proposals/
    ├── draft-grant-xyz.md  # Proposal drafts
    └── ...
```

**Agent reads workspace on init** to load context.

---

## Implementation Phases

### **Phase 1: Database Restructure** (Week 1)
- [ ] Create `org_grants` table
- [ ] Create `org_briefs` table  
- [ ] Create `user_saves` table
- [ ] Migration script to move `saved_opportunities` → `org_grants`
- [ ] Update API endpoints to use new schema
- [ ] Deploy to staging, test, deploy to prod

### **Phase 2: Agent Infrastructure** (Week 1-2)
- [ ] Set up Hetzner agent provisioning system
- [ ] Create FundFish agent template (PROFILE.md, STYLE.md, TOOLS.md)
- [ ] Build workspace service (init, read, write, memory management)
- [ ] Implement agent bridge communication (FastAPI backend ↔ Clawdbot)
- [ ] Test with 1-2 orgs manually

### **Phase 3: Discovery Agents** (Week 2-3)
- [ ] Build browser-based grant scraper (Playwright + Claude/GPT-4V)
- [ ] Test on Grants.gov
- [ ] Extend to 3-5 state portals
- [ ] Schedule daily cron jobs
- [ ] Monitor and tune (error handling, rate limits)

### **Phase 4: Qualification Agent** (Week 2-3)
- [ ] Build scoring algorithm (match org profile to grant)
- [ ] Implement reasoning generation (LLM-based)
- [ ] Create processing job (triggered by cron or on-demand)
- [ ] Write to `org_grants` with scores, summaries, tags
- [ ] Log to workspace memory
- [ ] Test with real grant data

### **Phase 5: Morning Brief** (Week 3-4)
- [ ] Build brief generation logic (top 3 selection)
- [ ] Design email template (HTML + plain text)
- [ ] Set up email delivery (SendGrid, Postmark, or SMTP)
- [ ] Schedule daily cron (8am local time per org)
- [ ] Test with pilot users
- [ ] Add WhatsApp delivery (optional)

### **Phase 6: Conversational Assistant** (Week 4+)
- [ ] Enable chat interface (frontend component)
- [ ] Implement tool access (grants API, proposal generation)
- [ ] Add proposal drafting capability
- [ ] Test end-to-end workflow (brief → chat → apply)

### **Phase 7: Learning & Optimization** (Ongoing)
- [ ] Track user engagement (opens, clicks, applications)
- [ ] Implement feedback loop (dismissals improve scoring)
- [ ] A/B test brief formats, timing
- [ ] Add analytics dashboard (for internal monitoring)

---

## Tech Stack

**Backend:**
- FastAPI (existing)
- PostgreSQL (Supabase)
- Clawdbot agents on Hetzner (persistent workspaces)

**Discovery Agents:**
- Playwright (browser automation)
- GPT-4V or Claude Sonnet (vision + reasoning for adaptive scraping)

**Org Agents:**
- Clawdbot sessions (persistent, stateful)
- Claude Sonnet 4 (reasoning, scoring, writing)

**Delivery:**
- Email: SendGrid or Postmark
- WhatsApp: wacli or WhatsApp Business API
- Slack: Webhooks

**Scheduling:**
- Cron jobs on Hetzner (discovery, processing, briefs)

**Frontend:**
- Next.js (existing)
- Chat UI component (new)

---

## Success Metrics

**For Orgs:**
- Time saved (hours/week on grant discovery)
- Grants applied to (increase in volume)
- Win rate (% of applications that result in funding)
- User engagement (brief open rate, chat usage)

**For FundFish:**
- Active orgs (sending daily briefs)
- Agent uptime (reliability of discovery + processing)
- Processing speed (time from grant posted → scored → brief)
- Cost per org (LLM tokens + infrastructure)

---

## Open Questions

1. **Pricing model** - How do we charge? Per brief? Per org? Subscription tiers?
2. **Pilot orgs** - Start with Per Scholas only, or recruit 3-5 beta orgs?
3. **Discovery coverage** - How many sources to support in v1? (Federal + 5 states?)
4. **Brief frequency** - Daily? Weekly? User-configurable?
5. **Delivery preferences** - Email default, opt-in for WhatsApp/Slack?
6. **Multi-user orgs** - Who gets the brief? All users? Just admins?
7. **Proposal generation** - How deep to go? Outline only, or full draft?

---

## Next Steps

1. **Review this spec** - Get alignment on scope and approach
2. **Database migration** - Start with schema changes (low risk, high value)
3. **Agent infrastructure** - Set up workspace system on Hetzner
4. **Build discovery agent** - Prove out browser-based scraping on 1 source
5. **Pilot brief** - Send first morning brief to Per Scholas manually
6. **Automate** - Wire up cron jobs, test end-to-end

---

**Status:** Spec complete, ready to build.
**Owner:** Ayaan + sub-agents
**Timeline:** 4-6 weeks to MVP
