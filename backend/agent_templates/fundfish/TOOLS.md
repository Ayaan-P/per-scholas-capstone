# FundFish Agent Tools

*Reference for tools available to your FundFish agent. This file helps the agent understand what it can do.*

---

## Grants API

### Search Grants
Query the global grants database with filters.

```
POST /api/grants/search
{
  "keywords": ["workforce", "technology"],
  "amount_min": 10000,
  "amount_max": 500000,
  "deadline_after": "2025-03-01",
  "geographic_focus": "national",
  "funders": ["DOL", "NSF"],
  "limit": 50
}
```

### Get Grant Details
Fetch full details for a specific grant.

```
GET /api/grants/{grant_id}
```

### Get Org Grants (Scored)
Get grants scored and analyzed for this org.

```
GET /api/grants/org/{org_id}?status=active&min_score=70&limit=20
```

### Update Grant Status
Mark a grant as saved, dismissed, or applied.

```
PATCH /api/grants/org/{org_id}/{grant_id}
{
  "status": "saved" | "dismissed" | "applied",
  "notes": "User feedback"
}
```

---

## Workspace Files

### Read Context
Read org profile, style guide, and decisions.

```
GET /api/workspace/context
```

### Write Memory
Log to daily memory file.

```
POST /api/workspace/memory
{
  "entry": "User preferred shorter briefs",
  "type": "decision" | "observation" | "feedback"
}
```

### Get Grant Research
Read research notes for a specific grant.

```
GET /api/workspace/grants/{grant_id}
```

### Save Grant Research
Write detailed research notes for a grant.

```
POST /api/workspace/grants/{grant_id}
{
  "analysis": "Detailed match analysis...",
  "eligibility_check": {...},
  "application_notes": "..."
}
```

---

## Proposal Tools

### Draft Proposal Section
Generate a draft of a proposal section.

```
POST /api/proposals/draft
{
  "grant_id": "uuid",
  "section": "executive_summary" | "need_statement" | "methodology" | "budget_narrative",
  "instructions": "Focus on workforce outcomes",
  "max_words": 500
}
```

### Review Proposal
Get feedback on a draft proposal.

```
POST /api/proposals/review
{
  "content": "Draft text...",
  "grant_id": "uuid",
  "criteria": ["clarity", "alignment", "evidence"]
}
```

### Extract Requirements
Parse grant requirements from documents.

```
POST /api/proposals/extract-requirements
{
  "document_id": "uuid"
}
```

---

## Brief Tools

### Generate Morning Brief
Create daily brief for org (called by cron, can also be triggered manually).

```
POST /api/briefs/generate
{
  "org_id": "uuid",
  "max_grants": 3,
  "include_deadlines": true
}
```

### Get Brief History
Retrieve past briefs.

```
GET /api/briefs/{org_id}?limit=7
```

---

## Document Tools

### Extract Text
Extract text from uploaded documents (PDF, DOCX).

```
POST /api/documents/extract
{
  "file_url": "https://...",
  "type": "rfp" | "previous_proposal" | "other"
}
```

### Search Documents
Search extracted document content.

```
POST /api/documents/search
{
  "query": "workforce training outcomes",
  "limit": 5
}
```

---

## Web Search

### Search for Grants
Search the web for grant opportunities.

```
POST /api/search/grants
{
  "query": "technology workforce training grants 2025",
  "limit": 10
}
```

### Research Funder
Look up information about a funder.

```
POST /api/search/funder
{
  "funder": "Department of Labor",
  "focus": "recent awards, priorities"
}
```

---

## Agent Configuration

### Environment
- **Workspace Root:** `/home/clawdbot/agents/fundfish/{org_id}/`
- **API Base:** `https://api.fundfish.org` or configured endpoint
- **Auth:** Bearer token passed in session context

### Rate Limits
- Search: 10 req/min
- Proposals: 5 req/min
- Documents: 20 req/min

### Best Practices
1. Cache grant details locally in workspace
2. Log decisions to memory files
3. Check workspace context before external calls
4. Respect user style preferences in all outputs

---
*Tool reference v1.0 — Update as new capabilities are added*
