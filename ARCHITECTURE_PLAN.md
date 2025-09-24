# PerScholas Fundraising Demo - Architecture Plan

## Project Context
Northwestern capstone project for Per Scholas nonprofit organization to build an AI-powered intelligent lead generation tool for fundraising efficiency.

### Core Problem
- Fundraising team spends 20+ hours/week manually finding funding opportunities
- Proposal writing takes 5-20 hours per opportunity
- Limited capacity to pursue untapped funding sources

### Project Goals
- **Precision Targeting**: Semantic analysis of funding opportunities
- **Actionable Insights**: Quick assessment and qualification of leads
- **Efficiency & Scalability**: Streamline identification, qualification, cultivation

## Architecture Overview

### High-Level Design
```
[User-Friendly Web UI] → [API Gateway] → [Claude Code Agent] → [Data Layer]
                    ↓
              [Results Dashboard]
```

### Core Components

#### 1. Claude Code Fundraising Agent (Intelligent Backend)
**Role**: Primary intelligence engine that executes complex fundraising workflows

**Capabilities**:
- **Opportunity Discovery**: Scan government websites, grant databases, donor databases
- **Semantic Matching**: Analyze RFPs against Per Scholas mission/goals
- **Proposal Generation**: Create first drafts using organizational knowledge
- **Qualification Analysis**: Assess fit, likelihood, effort required
- **Research Automation**: Deep dive into funders, requirements, deadlines

**Tools Available**:
- Web scraping for RFP discovery
- Database querying for historical data
- Document analysis for proposal generation
- API integrations for funding databases
- Google Workspace for document management

#### 2. User-Friendly Frontend
**Target Users**: Per Scholas fundraising team (non-technical)

**Core Workflows**:
1. **Opportunity Discovery Dashboard**
   - "Find New Opportunities" button
   - Results displayed as cards with key info
   - Filtering by deadline, amount, fit score

2. **Proposal Generation Interface**
   - Upload RFP document or paste URL
   - "Generate Draft Proposal" action
   - Editable proposal with AI suggestions

3. **Pipeline Management**
   - Overview of all opportunities in progress
   - Status tracking (identified → qualified → applying)
   - Calendar integration for deadlines

**UX Principles**:
- One-click actions for complex workflows
- Clear visual hierarchy and status indicators
- Minimal technical jargon
- Mobile-responsive for field work

#### 3. API Gateway / Bridge Layer
**Role**: Translate web requests into Claude Code executions

**Architecture**:
- FastAPI/Flask backend service
- Queue system for processing requests
- WebSocket for real-time updates
- Session management for user context

**Flow**:
1. User clicks "Find Opportunities"
2. API creates background job
3. Spawns Claude Code agent with specific task
4. Agent executes complete workflow
5. Results stored in database
6. User notified via WebSocket
7. Dashboard updates with new opportunities

#### 4. Data Layer
**Storage Strategy**:
- **PostgreSQL**: Structured data (opportunities, proposals, users)
- **Vector Database**: Semantic search capabilities
- **File Storage**: Generated proposals, RFP documents
- **Cache Layer**: Frequently accessed data

**Key Tables**:
- `opportunities`: RFPs, grants, donor prospects
- `proposals`: Generated drafts and final versions
- `organizations`: Per Scholas info, past proposals
- `matching_history`: Learn from successful/failed matches

## Technical Implementation

### Backend Stack
- **Python**: Main language for Claude Code integration
- **FastAPI**: API layer for frontend communication
- **Celery/Redis**: Background job processing
- **PostgreSQL**: Primary database
- **ChromaDB/Pinecone**: Vector storage for semantic search

### Frontend Stack
- **React/Next.js**: Modern, responsive UI
- **TailwindCSS**: Rapid styling for clean UX
- **WebSocket client**: Real-time updates
- **Charts.js**: Data visualization for insights

### Claude Code Integration
```python
# Example workflow execution
def find_opportunities_workflow(criteria):
    claude_session = spawn_claude_code_agent()

    # Execute intelligent workflow
    result = claude_session.execute(f"""
    Find funding opportunities for Per Scholas with criteria: {criteria}

    Tasks:
    1. Search government grant databases
    2. Analyze RFPs for semantic match to our mission
    3. Qualify opportunities by fit score, deadline, effort
    4. Generate summary report with recommendations
    5. Store results in database with confidence scores
    """)

    return parse_and_store_results(result)
```

## Demo Workflow Examples

### 1. Opportunity Discovery
**User Action**: Click "Find IT Training Grants"
**Agent Execution**:
- Searches GRANTS.gov, foundation databases
- Analyzes descriptions for IT training keywords
- Cross-references Per Scholas program offerings
- Scores opportunities by alignment and feasibility
- Returns ranked list with deadlines and requirements

### 2. Proposal Generation
**User Action**: Upload RFP PDF for workforce development grant
**Agent Execution**:
- Extracts requirements from RFP document
- Retrieves relevant Per Scholas program data
- Analyzes past successful proposals for similar grants
- Generates customized first draft
- Highlights areas needing customization

### 3. Pipeline Analytics
**User Action**: View "My Funding Pipeline"
**Agent Execution**:
- Analyzes all opportunities in system
- Calculates probability scores based on deadlines, requirements
- Identifies highest-value opportunities needing attention
- Generates weekly priority recommendations

## Success Metrics
- **Time Reduction**: 20+ hours → 2-3 hours per week for opportunity discovery
- **Proposal Efficiency**: 5-20 hours → 1-2 hours for first drafts
- **Coverage Increase**: 3x more opportunities evaluated
- **Success Rate**: Higher win rate through better targeting

## Deployment Strategy
- **Development**: Local Claude Code + React frontend
- **Demo**: Containerized deployment on cloud platform
- **Production**: Scalable architecture with monitoring

## Next Steps
1. Build minimal frontend prototype
2. Integrate Claude Code as backend service
3. Implement core workflows (discovery, proposal generation)
4. Load test with real Per Scholas data
5. Prepare demo scenarios for presentation