from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import uuid
import subprocess
import tempfile
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
from supabase import create_client, Client

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
SUPABASE_URL = "https://zjqwpvdcpzeguhdwrskr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpqcXdwdmRjcHplZ3VoZHdyc2tyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTgyNTczMzcsImV4cCI6MjA3MzgzMzMzN30.Ba46pLQFygSQoe-TZ4cRvLCpmT707zw2JT8qIRSjopU"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.vercel.app"],
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

        # Let Claude Code orchestrate the entire fundraising workflow intelligently
        try:
            # Get existing opportunities to avoid duplicates
            try:
                existing_result = supabase.table("opportunities").select("title, funder").execute()
                existing_opps = [f"{opp['title']} - {opp['funder']}" for opp in existing_result.data]
                existing_list = "; ".join(existing_opps) if existing_opps else "None"
            except:
                existing_list = "None"

            # Ultra-simple prompt that definitely works with duplicate checking
            orchestration_prompt = f"""Use your Task tool to call the fundraising-cro agent:

Find 3 NEW technology workforce grants that are NOT duplicates of these existing ones: {existing_list}

Return JSON array with title, funder, amount, deadline fields."""

            job["current_task"] = "Claude Code orchestrating fundraising workflow..."
            job["progress"] = 50

            # Call Claude Code with --print flag for non-interactive mode using stdin
            print(f"[Claude Code] Starting orchestration for job {job_id}...")
            print(f"[Claude Code] Prompt length: {len(orchestration_prompt)} chars")

            result = subprocess.run([
                'claude', '-p'
            ], input=orchestration_prompt, capture_output=True, text=True, timeout=900)

            print(f"[Claude Code] Completed with return code: {result.returncode}")
            print(f"[Claude Code] Output length: {len(result.stdout)} chars")
            print(f"[Claude Code] Stdout: {result.stdout[:500]}")  # First 500 chars
            if result.stderr:
                print(f"[Claude Code] Stderr: {result.stderr}")

            if result.returncode == 0:
                orchestration_result = result.stdout
            else:
                raise Exception(f"Claude Code failed: {result.stderr}")

            job["current_task"] = "Processing orchestrated results..."
            job["progress"] = 80

            # Parse the orchestrated response
            opportunities = parse_orchestration_response(orchestration_result)

        except Exception as e:
            print(f"Orchestration failed: {e}")
            opportunities = []

        # If no opportunities found, return empty result
        if not opportunities:
            opportunities = []

        # Complete job with opportunities for user review
        job["status"] = "completed"
        job["progress"] = 100
        job["current_task"] = "Search completed successfully"
        job["result"] = {
            "opportunities": opportunities,
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

        # Let Claude Code orchestrate the entire proposal generation workflow
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

            # Intelligent orchestration for proposal generation
            proposal_orchestration_prompt = f"""
You are an intelligent proposal generation orchestration system for Per Scholas. Analyze this opportunity and orchestrate the appropriate agents to create the best possible grant proposal.

Organization Context:
{per_scholas_context}

Opportunity Details:
Title: {request.opportunity_title}
Funder: {request.funder}
Amount: ${request.amount:,}
Deadline: {request.deadline}
Description: {request.description}
Requirements: {', '.join(request.requirements)}

Database Schema for proposals table:
- id (TEXT): unique identifier
- title (TEXT): proposal title
- opportunity_id (TEXT): linked opportunity ID
- opportunity_title (TEXT): opportunity name
- status (TEXT): draft/submitted/approved
- content (TEXT): full proposal content
- funding_amount (INTEGER): requested amount
- deadline (DATE): submission deadline
- funder (TEXT): funding organization
- created_at/updated_at (TIMESTAMPTZ): timestamps

Your task: Intelligently orchestrate agents to create a compelling, winning grant proposal.

Available specialized agents:
- fundraising-cro: Grant writing expertise, compliance, funder research
- marketing-cmo: Messaging strategy, content optimization, positioning
- financial-cfo: Budget analysis, ROI calculations, financial projections
- product-cpo: Impact metrics, user research, outcome measurement

Make autonomous decisions about:
1. Which agents to use for different proposal sections
2. How to optimize messaging for this specific funder
3. What financial analysis and projections to include
4. How to structure the proposal for maximum impact
5. Quality control and compliance checking

Generate a complete, professional grant proposal that maximizes Per Scholas' chances of winning this funding.
"""

            job["current_task"] = "Claude Code orchestrating proposal generation..."
            job["progress"] = 50

            # Call Claude Code for proposal orchestration using stdin
            result = subprocess.run([
                'claude', '-p'
            ], input=proposal_orchestration_prompt, capture_output=True, text=True, timeout=900)

            if result.returncode == 0:
                proposal_result = result.stdout
            else:
                raise Exception(f"Claude Code failed: {result.stderr}")

            job["current_task"] = "Processing orchestrated proposal..."
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
    uvicorn.run(app, host="0.0.0.0", port=8001)