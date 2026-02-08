"""Proposals routes for managing grant proposals"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import uuid

from auth_service import get_current_user

router = APIRouter(prefix="/api/proposals", tags=["proposals"])

# These will be injected from main.py
supabase = None
jobs_db = None
create_gemini_cli_session = None
parse_proposal_orchestration_response = None


def set_dependencies(db, jobs, gemini_session_fn, parse_proposal_fn):
    """Allow main.py to inject dependencies"""
    global supabase, jobs_db, create_gemini_cli_session, parse_proposal_orchestration_response
    supabase = db
    jobs_db = jobs
    create_gemini_cli_session = gemini_session_fn
    parse_proposal_orchestration_response = parse_proposal_fn


class ProposalRequest(BaseModel):
    opportunity_id: str
    opportunity_title: str
    funder: str
    amount: int
    deadline: str
    description: str
    requirements: List[str]


@router.get("")
async def get_proposals(user_id: str = Depends(get_current_user)):
    """Get all proposals from database (requires authentication)"""
    try:
        result = supabase.table("proposals").select("*").order("created_at", desc=True).execute()
        return {"proposals": result.data}
    except Exception as e:
        return {"proposals": []}


@router.post("/generate")
async def generate_proposal(
    request: ProposalRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """Generate a proposal using Claude Code (requires authentication)"""
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


@router.put("/{proposal_id}/status")
async def update_proposal_status(proposal_id: str, status_update: dict, user_id: str = Depends(get_current_user)):
    """Update proposal status (requires authentication)"""
    try:
        supabase.table("proposals").update({
            "status": status_update["status"],
            "updated_at": datetime.now().isoformat()
        }).eq("id", proposal_id).execute()

        return {"status": "updated", "proposal_id": proposal_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update proposal: {str(e)}")


@router.get("/{proposal_id}/download")
async def download_proposal(proposal_id: int, user_id: str = Depends(get_current_user)):
    """
    Serve a proposal PDF file from the server filesystem (requires authentication).

    Args:
        proposal_id: The ID of the proposal in the database

    Returns:
        FileResponse with the PDF file
    """
    try:
        # Get proposal from database to retrieve file_path
        result = supabase.table('proposals').select('*').eq('id', proposal_id).execute()

        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")

        proposal = result.data[0]
        file_path = proposal.get('file_path')

        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"Proposal file not found at {file_path}")

        # Extract filename from path
        filename = os.path.basename(file_path)

        return FileResponse(
            path=file_path,
            media_type='application/pdf',
            filename=filename,
            headers={
                "Content-Disposition": f"inline; filename={filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to serve proposal {proposal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to serve proposal: {str(e)}")


async def run_proposal_generation(job_id: str, request: ProposalRequest):
    """Execute Claude Code agent for proposal generation"""
    job = jobs_db[job_id]

    try:
        # Update job status
        job["current_task"] = "Initializing Claude Code proposal agent..."
        job["progress"] = 10

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

        # Create Claude Code session for proposal generation (with dummy content fallback)
        print(f"[Claude Code Session] Starting proposal generation...")

        # Use dummy proposal content if Claude Code not available, otherwise use Claude Code
        use_api = False  # Set to False to use Claude Code instead

        if use_api:
            print(f"[Claude Code Session] Using dummy proposal template...")
            proposal_result = f'''
# Grant Proposal: {request.opportunity_title}

## Executive Summary
Per Scholas requests ${request.amount:,} from {request.funder} to expand our proven technology workforce development program, directly addressing the critical need for skilled tech professionals from underrepresented communities.

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
- Instruction and curriculum: 45% (${int(request.amount * 0.45):,})
- Student support services: 25% (${int(request.amount * 0.25):,})
- Employer engagement: 20% (${int(request.amount * 0.20):,})
- Administrative costs: 10% (${int(request.amount * 0.10):,})

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
            session_result = create_gemini_cli_session(
                prompt=proposal_orchestration_prompt,
                session_type="fundraising",
                timeout=900
            )

            if not session_result['success']:
                raise Exception(f"Gemini CLI session failed: {session_result['error']}")

            proposal_result = session_result['output']

        job["current_task"] = "Processing proposal session results..."
        job["progress"] = 80

        # Parse the orchestrated proposal
        proposal_content = parse_proposal_orchestration_response(proposal_result)

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
