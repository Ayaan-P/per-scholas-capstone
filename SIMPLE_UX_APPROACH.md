# Simple UX-First Approach for PerScholas Demo

## What the kickoff deck actually asks for:

### Core Requirements:
1. **Intelligent Funding Opportunity Identification** - find relevant RFPs
2. **Automated First Draft Proposal Generation** - create viable drafts
3. **Enhanced Moves Management Automation** - streamline identification/qualification

### Current Pain Points:
- 20+ hours/week finding and vetting opportunities
- 5-20 hours writing each proposal
- Manual process limits capacity

## Minimal UX That Solves This:

### Page 1: Opportunity Dashboard
```
┌─────────────────────────────────────────┐
│ 🔍 Find New Opportunities              │
│ [Search Now] - runs Claude Code agent   │
│                                         │
│ Recent Opportunities:                   │
│ ┌─────────────────────────────────────┐ │
│ │ DOL Workforce Innovation - $250K    │ │
│ │ Due: Nov 15 | 95% match             │ │
│ │ [Generate Proposal]                 │ │
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ Gates Tech Equity - $100K           │ │
│ │ Due: Dec 1 | 78% match              │ │
│ │ [Generate Proposal]                 │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### Page 2: Proposal Generation
```
┌─────────────────────────────────────────┐
│ Generate Proposal for: DOL Workforce    │
│                                         │
│ 📎 RFP: workforce-innovation-2024.pdf   │
│ 🎯 Programs: [Software Eng] [Cloud]     │
│ 📍 Locations: [Chicago] [New York]      │
│                                         │
│ [Generate Draft] - runs Claude Code     │
│                                         │
│ Status: ⏳ Analyzing RFP... (2 min)     │
└─────────────────────────────────────────┘
```

## Technical Flow:

### When user clicks "Search Now":
1. Frontend: Show loading spinner
2. Backend: Spawn Claude Code with prompt:
   ```
   Find funding opportunities for Per Scholas IT training nonprofit.
   Search GRANTS.gov and foundation databases.
   Return top 10 opportunities with match scores.
   ```
3. Claude Code: Does the search, returns JSON
4. Frontend: Shows list of opportunities

### When user clicks "Generate Proposal":
1. Frontend: Simple form for RFP upload + program selection
2. Backend: Spawn Claude Code with prompt:
   ```
   Generate proposal draft for Per Scholas responding to this RFP.
   Use our organizational data and past successful proposals.
   ```
3. Claude Code: Analyzes RFP, generates draft
4. Frontend: Shows completed proposal sections

## No Cache Needed Initially:
- Fresh search each time (20 min wait is fine for demo)
- Fresh proposal each time (5 min wait is fine)
- Store results in simple database after completion
- Show previous results on dashboard

## Demo Script:
1. "This tool helps Per Scholas find relevant grants"
2. Click "Search Now" → show AI working for 2-3 minutes
3. Results appear: "Found 8 relevant opportunities"
4. Click on top match → "Generate Proposal"
5. Upload sample RFP → AI generates draft in 3-5 minutes
6. Show completed proposal: "What used to take 20 hours now takes 5 minutes"

## Implementation:
- **Frontend**: Simple React app with 2 pages
- **Backend**: FastAPI that spawns Claude Code processes
- **Claude Code**: Two main workflows (search, generate)
- **Database**: Just store completed results for display

This solves the core problem with minimal complexity.