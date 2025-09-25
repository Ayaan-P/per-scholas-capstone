from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import uuid
import os
import subprocess
import tempfile
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
from supabase import create_client, Client
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

def create_claude_code_session(prompt: str, session_type: str = "fundraising-cro", timeout: int = 900) -> dict:
    """
    Create a Claude Code session similar to iron_man_wake_hybrid.py
    Returns structured response from Claude Code session
    """
    try:
        # Create temporary file for the prompt if needed
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(prompt)
            temp_prompt_file = f.name

        # Set up environment variables similar to iron_man_wake
        env = os.environ.copy()

        # Configure Claude Code environment for non-interactive session
        env.update({
            'CLAUDE_NON_INTERACTIVE': 'true',
            'CLAUDE_OUTPUT_FORMAT': 'json',
            'CLAUDE_SESSION_TYPE': session_type
        })

        print(f"[Claude Code Session] Starting {session_type} session...")
        print(f"[Claude Code Session] Prompt length: {len(prompt)} chars")

        # Execute Claude Code session similar to iron_man_wake but non-interactive
        # Using --print flag for non-interactive mode
        result = subprocess.run([
            'claude', '--print'
        ],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        cwd=os.getcwd()
        )

        print(f"[Claude Code Session] Completed with return code: {result.returncode}")
        print(f"[Claude Code Session] Output length: {len(result.stdout)} chars")

        if result.stderr:
            print(f"[Claude Code Session] Stderr: {result.stderr}")

        # Clean up temp file
        try:
            os.unlink(temp_prompt_file)
        except:
            pass

        if result.returncode == 0:
            return {
                'success': True,
                'output': result.stdout,
                'error': None,
                'session_type': session_type
            }
        else:
            return {
                'success': False,
                'output': result.stdout,
                'error': result.stderr,
                'session_type': session_type
            }

    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'output': '',
            'error': f'Claude Code session timed out after {timeout} seconds',
            'session_type': session_type
        }
    except Exception as e:
        return {
            'success': False,
            'output': '',
            'error': str(e),
            'session_type': session_type
        }

def parse_orchestration_response(orchestration_result):
    """Parse Claude Code orchestration result to extract structured opportunities"""
    try:
        if isinstance(orchestration_result, str):
            # Try to extract JSON from the orchestrated response
            import re
            json_match = re.search(r'\[.*\]', orchestration_result, re.DOTALL)
            if json_match:
                opportunities = json.loads(json_match.group())
                return opportunities

            # Try to find JSON object with opportunities array
            json_match = re.search(r'\{.*"opportunities".*\}', orchestration_result, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data.get('opportunities', [])

        # If it's already structured data
        if hasattr(orchestration_result, 'get'):
            return orchestration_result.get('opportunities', [])
        elif isinstance(orchestration_result, list):
            return orchestration_result

        return []
    except Exception as e:
        print(f"Failed to parse orchestration response: {e}")
        return []

def parse_proposal_orchestration_response(orchestration_result):
    """Parse Claude Code orchestration result for proposal generation"""
    try:
        if isinstance(orchestration_result, str):
            return orchestration_result
        elif hasattr(orchestration_result, 'get'):
            return orchestration_result.get('proposal_content', str(orchestration_result))
        return str(orchestration_result)
    except:
        return ""

app = FastAPI(title="PerScholas Fundraising API")

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://zjqwpvdcpzeguhdwrskr.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpqcXdwdmRjcHplZ3VoZHdyc2tyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTgyNTczMzcsImV4cCI6MjA3MzgzMzMzN30.Ba46pLQFygSQoe-TZ4cRvLCpmT707zw2JT8qIRSjopU")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Anthropic client configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.vercel.app", "https://*.netlify.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job tracking (database for persistence)
jobs_db: Dict[str, Dict[str, Any]] = {}
opportunities_db: List[Dict[str, Any]] = []

class SearchRequest(BaseModel):
    prompt: str

class SearchCriteria(BaseModel):
    prompt: str
    focus_areas: Optional[List[str]] = None
    funding_range_min: Optional[int] = None
    funding_range_max: Optional[int] = None
    deadline_days: Optional[int] = None
    target_populations: Optional[List[str]] = None

class JobStatus(BaseModel):
    job_id: str
    status: str  # "running", "completed", "failed"
    progress: int
    current_task: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ProposalRequest(BaseModel):
    opportunity_id: str
    opportunity_title: str
    funder: str
    amount: int
    deadline: str
    description: str
    requirements: List[str]

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "PerScholas Fundraising API"}

@app.post("/api/search-opportunities")
async def start_opportunity_search(
    criteria: SearchCriteria,
    background_tasks: BackgroundTasks
):
    """Start AI-powered opportunity discovery"""
    job_id = str(uuid.uuid4())

    # Initialize job
    jobs_db[job_id] = {
        "job_id": job_id,
        "status": "running",
        "progress": 0,
        "current_task": "Initializing AI agent...",
        "result": None,
        "error": None,
        "created_at": datetime.now().isoformat()
    }

    # Start background task
    import asyncio
    asyncio.create_task(run_opportunity_search(job_id, criteria))

    return {"job_id": job_id, "status": "started"}

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get job status and results"""
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")

    return jobs_db[job_id]

@app.get("/api/opportunities")
async def get_opportunities():
    """Get all saved opportunities from database"""
    try:
        result = supabase.table("opportunities").select("*").execute()
        return {"opportunities": result.data}
    except Exception as e:
        return {"opportunities": opportunities_db}

@app.post("/api/opportunities/{opportunity_id}/save")
async def save_opportunity(opportunity_id: str):
    """Save a specific opportunity to the database"""
    # Find opportunity in current job results
    opportunity = None
    for job in jobs_db.values():
        if job.get("result") and job["result"].get("opportunities"):
            for opp in job["result"]["opportunities"]:
                if opp["id"] == opportunity_id:
                    opportunity = opp
                    break

    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    try:
        supabase.table("opportunities").insert({
            "id": opportunity["id"],
            "title": opportunity["title"],
            "funder": opportunity["funder"],
            "amount": opportunity["amount"],
            "deadline": opportunity["deadline"],
            "match_score": opportunity["match_score"],
            "description": opportunity["description"],
            "requirements": opportunity["requirements"],
            "contact": opportunity["contact"],
            "application_url": opportunity["application_url"],
            "created_at": datetime.now().isoformat()
        }).execute()

        # Also add to local cache
        opportunities_db.append(opportunity)

        return {"status": "saved", "opportunity_id": opportunity_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save opportunity: {str(e)}")

@app.get("/api/proposals")
async def get_proposals():
    """Get all proposals from database"""
    try:
        result = supabase.table("proposals").select("*").order("created_at", desc=True).execute()
        return {"proposals": result.data}
    except Exception as e:
        return {"proposals": []}

@app.post("/api/proposals/generate")
async def generate_proposal(
    request: ProposalRequest,
    background_tasks: BackgroundTasks
):
    """Generate a proposal using Claude Code"""
    job_id = str(uuid.uuid4())

    # Initialize job
    jobs_db[job_id] = {
        "job_id": job_id,
        "status": "running",
        "progress": 0,
        "current_task": "Initializing proposal generation...",
        "result": None,
        "error": None,
        "created_at": datetime.now().isoformat()
    }

    # Start background task
    background_tasks.add_task(run_proposal_generation, job_id, request)

    return {"job_id": job_id, "status": "started"}

@app.put("/api/proposals/{proposal_id}/status")
async def update_proposal_status(proposal_id: str, status_update: dict):
    """Update proposal status"""
    try:
        supabase.table("proposals").update({
            "status": status_update["status"],
            "updated_at": datetime.now().isoformat()
        }).eq("id", proposal_id).execute()

        return {"status": "updated", "proposal_id": proposal_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update proposal: {str(e)}")

@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        # Get opportunities count and funding
        opportunities_result = supabase.table("opportunities").select("amount").execute()
        opportunities = opportunities_result.data

        # Get proposals count
        proposals_result = supabase.table("proposals").select("id, status").execute()
        proposals = proposals_result.data

        # Calculate stats
        total_opportunities = len(opportunities)
        total_proposals = len(proposals)
        total_funding = sum(opp.get("amount", 0) for opp in opportunities)

        approved_proposals = len([p for p in proposals if p.get("status") == "approved"])
        submitted_proposals = len([p for p in proposals if p.get("status") in ["submitted", "approved"]])

        return {
            "totalOpportunities": total_opportunities,
            "totalProposals": total_proposals,
            "totalFunding": total_funding,
            "recentSearches": len(jobs_db),
            "avgMatchScore": 85
        }
    except Exception as e:
        return {
            "totalOpportunities": 0,
            "totalProposals": 0,
            "totalFunding": 0,
            "recentSearches": 0,
            "avgMatchScore": 0
        }

@app.get("/api/dashboard/activity")
async def get_dashboard_activity():
    """Get recent activity"""
    activities = []

    # Add recent job activities
    for job in list(jobs_db.values())[-5:]:
        if job.get("status") == "completed":
            activities.append({
                "id": job["job_id"],
                "type": "search",
                "description": f"Completed search: {job.get('result', {}).get('total_found', 0)} opportunities found",
                "timestamp": job.get("created_at", datetime.now().isoformat())
            })

    return {"activities": activities}

@app.get("/api/analytics")
async def get_analytics(range: str = "30d"):
    """Get analytics data"""
    # Mock analytics data
    return {
        "searchMetrics": {
            "totalSearches": len(jobs_db),
            "successfulSearches": len([j for j in jobs_db.values() if j.get("status") == "completed"]),
            "avgOpportunitiesPerSearch": 4.2,
            "avgMatchScore": 85
        },
        "opportunityMetrics": {
            "totalOpportunities": 15,
            "savedOpportunities": 8,
            "totalFundingValue": 1250000,
            "avgFundingAmount": 156250
        },
        "proposalMetrics": {
            "totalProposals": 3,
            "submittedProposals": 2,
            "approvedProposals": 1,
            "successRate": 33
        },
        "timeSeriesData": [
            {"date": (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d"), "searches": 2, "opportunities": 8, "proposals": 1},
            {"date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"), "searches": 1, "opportunities": 4, "proposals": 0},
            {"date": (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d"), "searches": 3, "opportunities": 12, "proposals": 2},
            {"date": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"), "searches": 1, "opportunities": 3, "proposals": 0},
            {"date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"), "searches": 2, "opportunities": 7, "proposals": 1},
            {"date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"), "searches": 1, "opportunities": 5, "proposals": 0},
            {"date": datetime.now().strftime("%Y-%m-%d"), "searches": 0, "opportunities": 0, "proposals": 0}
        ],
        "topFunders": [
            {"name": "U.S. Department of Labor", "opportunityCount": 3, "totalFunding": 450000},
            {"name": "Gates Foundation", "opportunityCount": 2, "totalFunding": 300000},
            {"name": "Ford Foundation", "opportunityCount": 2, "totalFunding": 250000},
            {"name": "JPMorgan Chase Foundation", "opportunityCount": 1, "totalFunding": 200000},
            {"name": "Google.org", "opportunityCount": 1, "totalFunding": 75000}
        ]
    }

async def run_opportunity_search(job_id: str, criteria: SearchCriteria):
    """Execute Claude Code fundraising-cro agent for opportunity discovery"""
    print(f"[BACKGROUND TASK] Starting run_opportunity_search for job {job_id}")
    job = jobs_db[job_id]

    try:
        print(f"[BACKGROUND TASK] Job found, current status: {job['status']}")
        # Update job status
        job["current_task"] = "Initializing fundraising-cro agent..."
        job["progress"] = 10

        # Prepare context for fundraising agent
        per_scholas_context = """
Per Scholas is a leading national nonprofit that advances economic equity through rigorous,
tuition-free technology training for individuals from underrepresented communities.

Mission: To advance economic equity by providing access to technology careers for individuals
from underrepresented communities.

Programs:
- Cybersecurity Training (16-week intensive program)
- Cloud Computing (AWS/Azure certification tracks)
- Software Development (Full-stack development)
- IT Support (CompTIA certification preparation)

Impact:
- 20,000+ graduates to date
- 85% job placement rate
- 150% average salary increase
- 24 markets across the United States
- Focus on underrepresented minorities, women, veterans

Target Demographics:
- Individuals from underrepresented communities
- Women seeking technology careers
- Veterans transitioning to civilian workforce
- Career changers from declining industries
- Low-income individuals seeking economic mobility
"""

        fundraising_prompt = f"""
I need you to find actual, current funding opportunities for Per Scholas.

Organization Context:
{per_scholas_context}

User Search Request: {criteria.prompt}

Please execute your grant discovery protocol:
1. Search GRANTS.gov, NSF, DOL, and other federal databases for current opportunities
2. Find foundation grants from major funders (Gates, Ford, JPMorgan Chase, Google.org, etc.)
3. Look for corporate funding programs focused on workforce development and technology equity
4. Focus specifically on opportunities that align with Per Scholas' mission of technology training for underserved communities

For each opportunity found, provide:
- Title and funder organization
- Funding amount range
- Application deadline
- Match score (0-100) for Per Scholas fit based on mission alignment
- Detailed description and key requirements
- Contact information and application URL if available

Return results in a structured format with an "opportunities" array containing these details.
Priority should be given to opportunities with deadlines in the next 3-6 months and funding amounts over $50,000.
"""

        job["current_task"] = "Executing fundraising-cro agent search..."
        job["progress"] = 30

        # Use the new Claude Code session creation
        try:
            # Get existing opportunities to avoid duplicates
            try:
                existing_result = supabase.table("opportunities").select("title, funder").execute()
                existing_opps = [f"{opp['title']} - {opp['funder']}" for opp in existing_result.data]
                existing_list = "; ".join(existing_opps) if existing_opps else "None"
            except:
                existing_list = "None"

            # Create comprehensive prompt for fundraising-cro agent
            orchestration_prompt = f"""You are a fundraising-cro agent for Per Scholas. Use your Task tool to systematically find and analyze current funding opportunities.

Organization Context:
{per_scholas_context}

User Search Request: {criteria.prompt}

Execute this multi-step process:

1. Search current federal databases (GRANTS.gov, NSF, DOL) for technology workforce development opportunities
2. Research foundation grants from major funders aligned with our mission
3. Identify corporate funding programs for underserved communities
4. Filter for opportunities with deadlines in next 3-6 months and funding >$50k

Existing opportunities to avoid duplicates: {existing_list}

For each NEW opportunity found, return structured data with:
- id: unique identifier
- title: opportunity title
- funder: funding organization
- amount: funding amount (integer)
- deadline: application deadline (YYYY-MM-DD format)
- match_score: 0-100 alignment score with Per Scholas mission
- description: detailed description
- requirements: array of key requirements
- contact: contact information if available
- application_url: application URL if available

Return as JSON array in "opportunities" field."""

            job["current_task"] = "Creating Claude Code fundraising session..."
            job["progress"] = 50

            # Create Claude Code session (with dummy data fallback)
            print(f"[Claude Code Session] Starting fundraising opportunity discovery...")

            # TODO: Remove this dummy data when Claude Code is installed on server
            use_dummy_data = True  # Set to False when Claude Code is available

            if use_dummy_data:
                print(f"[Claude Code Session] Using dummy data for development...")
                orchestration_result = '''
{
  "opportunities": [
    {
      "id": "nsf-ate-2024",
      "title": "NSF Advanced Technological Education (ATE) Program",
      "funder": "National Science Foundation",
      "amount": 300000,
      "deadline": "2025-01-15",
      "match_score": 95,
      "description": "Supports education programs that prepare technicians for high-technology fields that drive the nation's economy",
      "requirements": ["Community college partnership", "Industry collaboration", "STEM focus", "Underrepresented populations"],
      "contact": "ate@nsf.gov",
      "application_url": "https://www.nsf.gov/funding/pgm_summ.jsp?pims_id=5464"
    },
    {
      "id": "dol-apprenticeship-2024",
      "title": "DOL Apprenticeship Building America Grant",
      "funder": "U.S. Department of Labor",
      "amount": 500000,
      "deadline": "2025-02-28",
      "match_score": 88,
      "description": "Expand apprenticeship programs in technology and cybersecurity sectors",
      "requirements": ["Registered apprenticeship", "Technology focus", "Employer partnerships", "Diverse recruitment"],
      "contact": "apprenticeship@dol.gov",
      "application_url": "https://www.dol.gov/agencies/eta/apprenticeship"
    },
    {
      "id": "google-grow-2024",
      "title": "Google.org Grow with Google Community Grants",
      "funder": "Google.org",
      "amount": 150000,
      "deadline": "2025-03-31",
      "match_score": 92,
      "description": "Support organizations helping people gain digital skills and economic opportunity",
      "requirements": ["Digital skills training", "Economic mobility", "Underserved communities", "Measurable outcomes"],
      "contact": "grow@google.org",
      "application_url": "https://grow.google/programs/"
    }
  ]
}
                '''.strip()
            else:
                session_result = create_claude_code_session(
                    prompt=orchestration_prompt,
                    session_type="fundraising-cro",
                    timeout=900
                )

                if not session_result['success']:
                    raise Exception(f"Claude Code session failed: {session_result['error']}")

                orchestration_result = session_result['output']
            job["current_task"] = "Processing fundraising session results..."
            job["progress"] = 80

            # Parse the orchestrated response
            opportunities = parse_orchestration_response(orchestration_result)

        except Exception as e:
            print(f"Orchestration failed: {e}")
            opportunities = []

        # If no opportunities found, return empty result
        if not opportunities:
            opportunities = []

        # Auto-save opportunities to database
        saved_opportunities = []
        if opportunities:
            job["current_task"] = "Saving opportunities to database..."
            job["progress"] = 90

            for opp in opportunities:
                try:
                    # Save to Supabase
                    result = supabase.table("opportunities").insert({
                        "id": opp.get("id"),
                        "title": opp.get("title"),
                        "funder": opp.get("funder"),
                        "amount": opp.get("amount"),
                        "deadline": opp.get("deadline"),
                        "match_score": opp.get("match_score", 0),
                        "description": opp.get("description"),
                        "requirements": opp.get("requirements", []),
                        "contact": opp.get("contact"),
                        "application_url": opp.get("application_url"),
                        "status": "active",
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }).execute()
                    saved_opportunities.append(opp)
                    print(f"Saved opportunity: {opp.get('title')}")
                except Exception as e:
                    print(f"Failed to save opportunity {opp.get('title')}: {e}")
                    # Continue with other opportunities

        # Complete job with opportunities for user review
        job["status"] = "completed"
        job["progress"] = 100
        job["current_task"] = "Search completed successfully"
        job["result"] = {
            "opportunities": opportunities,
            "saved_opportunities": len(saved_opportunities),
            "total_found": len(opportunities),
            "search_criteria": criteria.dict(),
            "completed_at": datetime.now().isoformat()
        }

    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        job["current_task"] = f"Error: {str(e)}"

async def run_proposal_generation(job_id: str, request: ProposalRequest):
    """Execute Claude Code agent for proposal generation"""
    job = jobs_db[job_id]

    try:
        # Update job status
        job["current_task"] = "Initializing Claude Code proposal agent..."
        job["progress"] = 10

        # Create Claude Code prompt for proposal generation
        claude_prompt = f"""
You are a grant proposal writing expert for Per Scholas, a nonprofit focused on technology workforce development for underserved communities.

Generate a comprehensive grant proposal for the following opportunity:

Opportunity Title: {request.opportunity_title}
Funder: {request.funder}
Funding Amount: ${request.amount:,}
Deadline: {request.deadline}
Description: {request.description}
Requirements: {', '.join(request.requirements)}

Create a professional grant proposal that includes:

1. Executive Summary
2. Organization Background (Per Scholas)
3. Project Description and Goals
4. Target Population and Need Assessment
5. Implementation Plan and Timeline
6. Budget Justification
7. Expected Outcomes and Evaluation
8. Sustainability Plan
9. Conclusion

Ensure the proposal:
- Aligns with Per Scholas' mission of providing technology training to underserved communities
- Addresses the specific requirements and priorities of {request.funder}
- Demonstrates clear impact and measurable outcomes
- Shows understanding of the target population's needs
- Presents a realistic budget and timeline
- Emphasizes diversity, equity, and inclusion

The proposal should be compelling, professional, and specifically tailored to this opportunity.
"""

        job["current_task"] = "Executing Claude Code proposal generation..."
        job["progress"] = 30

        # Use the new Claude Code session creation for proposal generation
        try:
            # Per Scholas context for proposal generation
            per_scholas_context = """
Per Scholas is a leading national nonprofit that advances economic equity through rigorous,
tuition-free technology training for individuals from underrepresented communities.

Mission: To advance economic equity by providing access to technology careers for individuals
from underrepresented communities.

Programs:
- Cybersecurity Training (16-week intensive program)
- Cloud Computing (AWS/Azure certification tracks)
- Software Development (Full-stack development)
- IT Support (CompTIA certification preparation)

Impact:
- 20,000+ graduates to date
- 85% job placement rate
- 150% average salary increase
- 24 markets across the United States
- Focus on underrepresented minorities, women, veterans

Target Demographics:
- Individuals from underrepresented communities
- Women seeking technology careers
- Veterans transitioning to civilian workforce
- Career changers from declining industries
- Low-income individuals seeking economic mobility
"""

            # Comprehensive orchestration prompt for proposal generation
            proposal_orchestration_prompt = f"""You are a comprehensive proposal generation system for Per Scholas. Use your Task tool to orchestrate multiple specialized agents for creating a winning grant proposal.

Organization Context:
{per_scholas_context}

Opportunity Details:
Title: {request.opportunity_title}
Funder: {request.funder}
Amount: ${request.amount:,}
Deadline: {request.deadline}
Description: {request.description}
Requirements: {', '.join(request.requirements)}

Multi-Agent Orchestration Plan:

1. Use fundraising-cro agent for:
   - Grant writing best practices
   - Funder research and alignment
   - Compliance requirements analysis
   - Proposal structure and sections

2. Use financial-cfo agent for:
   - Budget development and justification
   - ROI calculations and projections
   - Cost-effectiveness analysis
   - Financial sustainability planning

3. Use product-cpo agent for:
   - Impact metrics and measurement
   - Program effectiveness data
   - User outcomes and success rates
   - Evaluation methodology

4. Use marketing-cmo agent for:
   - Compelling messaging and positioning
   - Stakeholder engagement strategy
   - Communication and dissemination plan

Generate a complete, professional grant proposal with these sections:
1. Executive Summary
2. Organization Background
3. Project Description and Goals
4. Target Population and Need Assessment
5. Implementation Plan and Timeline
6. Budget Justification
7. Expected Outcomes and Evaluation
8. Sustainability Plan
9. Conclusion

The proposal should be compelling, data-driven, and specifically tailored to {request.funder}'s priorities and requirements."""

            job["current_task"] = "Creating Claude Code proposal session..."
            job["progress"] = 50

            # Create Claude Code session for proposal generation (with dummy data fallback)
            print(f"[Claude Code Session] Starting proposal generation...")

            # TODO: Remove this dummy data when Claude Code is installed on server
            use_dummy_data = True  # Set to False when Claude Code is available

            if use_dummy_data:
                print(f"[Claude Code Session] Using dummy data for proposal generation...")
                proposal_result = f'''
# Grant Proposal: {request.opportunity_title}

## Executive Summary
Per Scholas requests ${request.funding_amount:,} from {request.funder} to expand our proven technology workforce development program, directly addressing the critical need for skilled tech professionals from underrepresented communities.

## Organization Background
Per Scholas is a leading nonprofit that advances economic equity through rigorous, tuition-free technology training programs. Since 1995, we have graduated over 18,000 students with an average starting salary of $52,000—a 3x increase from their pre-program earnings.

## Project Description and Goals
This initiative will:
- Train 250 additional learners in high-demand technology roles
- Achieve 85% job placement rate within 180 days
- Generate $13M in aggregate annual wage increases
- Partner with 50+ employers for direct hiring pathways

## Target Population and Need Assessment
We serve adults from communities that have been systemically excluded from economic opportunity:
- 65% people of color
- 50% women and gender-expansive individuals
- 70% earning less than $30,000 annually
- Average age: 32 years old

## Implementation Plan and Timeline
**Phase 1 (Months 1-6):** Program expansion and curriculum development
**Phase 2 (Months 7-18):** Student recruitment and training delivery
**Phase 3 (Months 19-24):** Job placement and career support services

## Budget Justification
- Instruction and curriculum: 45% (${int(request.funding_amount * 0.45):,})
- Student support services: 25% (${int(request.funding_amount * 0.25):,})
- Employer engagement: 20% (${int(request.funding_amount * 0.20):,})
- Administrative costs: 10% (${int(request.funding_amount * 0.10):,})

## Expected Outcomes and Evaluation
- 250 program graduates
- 85% job placement rate
- $52,000 average starting salary
- 90% job retention at 12 months
- ROI of 400% through increased tax revenue and reduced social services

## Sustainability Plan
Per Scholas will sustain this program through diversified funding including corporate partnerships, government contracts, and earned revenue from employer-paid training services.

## Conclusion
This partnership with {request.funder} will create lasting economic mobility for underserved communities while addressing critical workforce needs in the technology sector. Together, we can build a more equitable and prosperous future.

---
*Generated on {datetime.now().strftime("%B %d, %Y")} for {request.funder}*
                '''.strip()
            else:
                session_result = create_claude_code_session(
                    prompt=proposal_orchestration_prompt,
                    session_type="fundraising-cro",
                    timeout=900
                )

                if not session_result['success']:
                    raise Exception(f"Claude Code session failed: {session_result['error']}")

                proposal_result = session_result['output']
            job["current_task"] = "Processing proposal session results..."
            job["progress"] = 80

            # Parse the orchestrated proposal
            proposal_content = parse_proposal_orchestration_response(proposal_result)

        except Exception as e:
            print(f"Proposal orchestration failed: {e}")
            proposal_content = ""

        # If no content from agent, raise error
        if not proposal_content:
            raise Exception("Fundraising agent failed to generate proposal content")

        # Save proposal to database
        proposal_id = str(uuid.uuid4())

        try:
            supabase.table("proposals").insert({
                "id": proposal_id,
                "title": f"Proposal for {request.opportunity_title}",
                "opportunity_id": request.opportunity_id,
                "opportunity_title": request.opportunity_title,
                "status": "draft",
                "content": proposal_content,
                "funding_amount": request.amount,
                "deadline": request.deadline,
                "funder": request.funder,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }).execute()
        except Exception as e:
            print(f"Error saving proposal to Supabase: {e}")

        # Complete job
        job["status"] = "completed"
        job["progress"] = 100
        job["current_task"] = "Proposal generation completed successfully"
        job["result"] = {
            "proposal_id": proposal_id,
            "title": f"Proposal for {request.opportunity_title}",
            "content_length": len(proposal_content),
            "completed_at": datetime.now().isoformat()
        }

    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        job["current_task"] = f"Error: {str(e)}"

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)