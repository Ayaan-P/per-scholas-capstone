from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from supabase import create_client, Client

# Import the Task function to call fundraising-cro agent
# Note: This would need to be properly imported from Claude Code
# from claude_code import Task

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

# Job tracking
jobs_db: Dict[str, Dict[str, Any]] = {}

class SearchCriteria(BaseModel):
    prompt: str
    focus_areas: Optional[List[str]] = None
    funding_range_min: Optional[int] = None
    funding_range_max: Optional[int] = None
    deadline_days: Optional[int] = None
    target_populations: Optional[List[str]] = None

class ProposalRequest(BaseModel):
    opportunity_id: str
    opportunity_title: str
    funder: str
    amount: int
    deadline: str
    description: str
    requirements: List[str]

# PerScholas organizational context
PER_SCHOLAS_CONTEXT = """
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

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "PerScholas Fundraising API"}

@app.post("/api/search-opportunities")
async def start_opportunity_search(criteria: SearchCriteria):
    """Search for opportunities using REAL fundraising-cro agent"""
    job_id = str(uuid.uuid4())

    # Initialize job
    jobs_db[job_id] = {
        "job_id": job_id,
        "status": "running",
        "progress": 0,
        "current_task": "Initializing fundraising-cro agent...",
        "result": None,
        "error": None,
        "created_at": datetime.now().isoformat()
    }

    try:
        # Update progress
        jobs_db[job_id]["progress"] = 20
        jobs_db[job_id]["current_task"] = "Executing fundraising-cro agent search..."

        # Build comprehensive prompt for fundraising-cro agent
        fundraising_prompt = f"""
I need you to find actual, current funding opportunities for Per Scholas.

Organization Context:
{PER_SCHOLAS_CONTEXT}

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

Additional search criteria:
- Focus areas: {criteria.focus_areas or ['technology training', 'workforce development']}
- Funding range: ${criteria.funding_range_min or 50000} - ${criteria.funding_range_max or 1000000}
- Deadline within: {criteria.deadline_days or 180} days
- Target populations: {criteria.target_populations or ['underserved communities', 'minorities', 'women']}

Return results in a structured format with an "opportunities" array containing these details.
Priority should be given to opportunities with deadlines in the next 3-6 months and funding amounts over $50,000.

Please provide at least 5-10 opportunities if available, ranked by match score and relevance to Per Scholas' mission.
"""

        # Update progress
        jobs_db[job_id]["progress"] = 50
        jobs_db[job_id]["current_task"] = "Fundraising-CRO agent analyzing requirements..."

        # CALL THE ACTUAL TASK TOOL HERE
        # This is where the real Claude Code integration happens
        # result = Task(
        #     subagent_type="fundraising-cro",
        #     description="Find funding opportunities",
        #     prompt=fundraising_prompt
        # )

        # For the actual implementation, you would uncomment above and remove the error below
        raise HTTPException(
            status_code=501,
            detail="Real Task tool integration needed. This endpoint requires calling the actual fundraising-cro agent through the Task tool."
        )

        # After getting real results from Task tool:
        # jobs_db[job_id]["progress"] = 90
        # jobs_db[job_id]["current_task"] = "Processing agent results..."

        # Parse and structure the agent response
        # opportunities = extract_opportunities_from_agent_response(result)

        # jobs_db[job_id]["status"] = "completed"
        # jobs_db[job_id]["progress"] = 100
        # jobs_db[job_id]["current_task"] = "Search completed successfully"
        # jobs_db[job_id]["result"] = {
        #     "opportunities": opportunities,
        #     "total_found": len(opportunities),
        #     "search_criteria": criteria.dict(),
        #     "agent_used": "fundraising-cro",
        #     "completed_at": datetime.now().isoformat()
        # }

    except Exception as e:
        jobs_db[job_id]["status"] = "failed"
        jobs_db[job_id]["error"] = str(e)
        jobs_db[job_id]["current_task"] = f"Error: {str(e)}"
        raise e

    return {"job_id": job_id, "status": "started"}

@app.post("/api/proposals/generate")
async def generate_proposal(request: ProposalRequest):
    """Generate proposal using REAL fundraising-cro agent"""
    job_id = str(uuid.uuid4())

    # Initialize job
    jobs_db[job_id] = {
        "job_id": job_id,
        "status": "running",
        "progress": 0,
        "current_task": "Initializing fundraising-cro agent for proposal generation...",
        "result": None,
        "error": None,
        "created_at": datetime.now().isoformat()
    }

    try:
        # Update progress
        jobs_db[job_id]["progress"] = 20
        jobs_db[job_id]["current_task"] = "Executing fundraising-cro proposal generation..."

        # Build proposal generation prompt
        proposal_prompt = f"""
I need you to generate a comprehensive grant proposal for Per Scholas.

Organization Context:
{PER_SCHOLAS_CONTEXT}

Opportunity Details:
Title: {request.opportunity_title}
Funder: {request.funder}
Amount: ${request.amount:,}
Deadline: {request.deadline}
Description: {request.description}
Requirements: {', '.join(request.requirements)}

Please execute your proposal generation protocol:
1. Create a compelling, professional grant proposal specifically tailored to this opportunity
2. Use Per Scholas organizational context and proven impact data
3. Address all funder requirements and priorities
4. Ensure compliance with standard grant proposal formats

The proposal should include these sections:
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
- Demonstrates Per Scholas' 20-year track record and 85% job placement rate
- Aligns with {request.funder}'s specific priorities and requirements
- Shows clear understanding of our target population's needs
- Presents realistic budget breakdown and implementation timeline
- Emphasizes diversity, equity, and inclusion outcomes
- Includes specific, measurable outcomes and evaluation methods

Generate a complete, professional grant proposal that maximizes our chances of funding success.
"""

        # Update progress
        jobs_db[job_id]["progress"] = 50
        jobs_db[job_id]["current_task"] = "Fundraising-CRO agent generating proposal..."

        # CALL THE ACTUAL TASK TOOL HERE
        # result = Task(
        #     subagent_type="fundraising-cro",
        #     description="Generate grant proposal",
        #     prompt=proposal_prompt
        # )

        # For the actual implementation, you would uncomment above and remove the error below
        raise HTTPException(
            status_code=501,
            detail="Real Task tool integration needed. This endpoint requires calling the actual fundraising-cro agent through the Task tool."
        )

        # After getting real results from Task tool:
        # jobs_db[job_id]["progress"] = 90
        # jobs_db[job_id]["current_task"] = "Processing proposal content..."

        # Extract proposal content from agent response
        # proposal_content = extract_proposal_from_agent_response(result)

        # Save to database
        # proposal_id = str(uuid.uuid4())
        # save_proposal_to_supabase(proposal_id, proposal_content, request)

        # jobs_db[job_id]["status"] = "completed"
        # jobs_db[job_id]["progress"] = 100
        # jobs_db[job_id]["current_task"] = "Proposal generation completed successfully"
        # jobs_db[job_id]["result"] = {
        #     "proposal_id": proposal_id,
        #     "proposal_content": proposal_content,
        #     "opportunity_title": request.opportunity_title,
        #     "agent_used": "fundraising-cro",
        #     "completed_at": datetime.now().isoformat()
        # }

    except Exception as e:
        jobs_db[job_id]["status"] = "failed"
        jobs_db[job_id]["error"] = str(e)
        jobs_db[job_id]["current_task"] = f"Error: {str(e)}"
        raise e

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
        return {"opportunities": []}

@app.get("/api/proposals")
async def get_proposals():
    """Get all proposals from database"""
    try:
        result = supabase.table("proposals").select("*").order("created_at", desc=True).execute()
        return {"proposals": result.data}
    except Exception as e:
        return {"proposals": []}

# Helper functions for when Task tool is actually integrated
def extract_opportunities_from_agent_response(agent_response: str) -> List[Dict[str, Any]]:
    """Extract structured opportunities data from fundraising-cro agent response"""
    # This would parse the agent's response and extract the opportunities
    # The agent should return structured data with opportunity details
    pass

def extract_proposal_from_agent_response(agent_response: str) -> str:
    """Extract proposal content from fundraising-cro agent response"""
    # This would parse the agent's response and extract the proposal text
    pass

def save_proposal_to_supabase(proposal_id: str, content: str, request: ProposalRequest):
    """Save generated proposal to Supabase database"""
    try:
        supabase.table("proposals").insert({
            "id": proposal_id,
            "title": f"Proposal for {request.opportunity_title}",
            "opportunity_id": request.opportunity_id,
            "opportunity_title": request.opportunity_title,
            "status": "draft",
            "content": content,
            "funding_amount": request.amount,
            "deadline": request.deadline,
            "funder": request.funder,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }).execute()
    except Exception as e:
        print(f"Error saving proposal to Supabase: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)