"""Proposals routes for managing grant proposals"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import uuid

from auth_service import get_current_user
from claude_code_service import generate_proposal_content, create_claude_api_session, PER_SCHOLAS_CONTEXT

router = APIRouter(prefix="/api/proposals", tags=["proposals"])

# These will be injected from main.py
supabase = None
jobs_db = None
# Keep for backwards compatibility but prefer Claude API
create_gemini_cli_session = None
parse_proposal_orchestration_response = None


def set_dependencies(db, jobs, gemini_session_fn=None, parse_proposal_fn=None):
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
    """Execute proposal generation using Claude API (migrated from Gemini CLI)"""
    job = jobs_db[job_id]

    try:
        # Update job status
        job["current_task"] = "Initializing Claude API proposal generation..."
        job["progress"] = 10

        job["current_task"] = "Generating proposal with Claude API..."
        job["progress"] = 30

        print(f"[Proposal Generation] Starting for '{request.opportunity_title}'")

        # Use Claude API directly for proposal generation
        result = generate_proposal_content(
            opportunity_title=request.opportunity_title,
            funder=request.funder,
            amount=request.amount,
            deadline=request.deadline,
            description=request.description,
            requirements=request.requirements,
            timeout=300
        )

        job["progress"] = 70

        if not result['success']:
            # Fallback to Gemini CLI if Claude fails and Gemini is available
            if create_gemini_cli_session:
                print(f"[Proposal Generation] Claude API failed, falling back to Gemini CLI...")
                job["current_task"] = "Falling back to Gemini CLI..."
                
                proposal_prompt = f"""Generate a complete grant proposal for Per Scholas.

Organization Context:
{PER_SCHOLAS_CONTEXT}

Opportunity Details:
- Title: {request.opportunity_title}
- Funder: {request.funder}
- Amount: ${request.amount:,}
- Deadline: {request.deadline}
- Description: {request.description}
- Requirements: {', '.join(request.requirements)}

Generate a professional proposal with: Executive Summary, Organization Background, 
Project Description, Target Population, Implementation Plan, Budget Justification, 
Expected Outcomes, Sustainability Plan, and Conclusion."""

                gemini_result = create_gemini_cli_session(
                    prompt=proposal_prompt,
                    session_type="fundraising",
                    timeout=900
                )
                
                if gemini_result['success']:
                    proposal_content = gemini_result['output']
                else:
                    raise Exception(f"Both Claude API and Gemini CLI failed. Claude: {result['error']}, Gemini: {gemini_result['error']}")
            else:
                raise Exception(f"Claude API failed: {result['error']}")
        else:
            proposal_content = result['content']
            print(f"[Proposal Generation] Claude API succeeded, generated {len(proposal_content)} chars")
            if result.get('usage'):
                print(f"[Proposal Generation] Token usage: {result['usage']}")

        job["current_task"] = "Saving proposal to database..."
        job["progress"] = 85

        # If no content, raise error
        if not proposal_content:
            raise Exception("No proposal content was generated")

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
            print(f"[Proposal Generation] Saved proposal {proposal_id} to database")
        except Exception as e:
            print(f"[Proposal Generation] Error saving to Supabase: {e}")

        # Complete job
        job["status"] = "completed"
        job["progress"] = 100
        job["current_task"] = "Proposal generation completed successfully"
        job["result"] = {
            "proposal_id": proposal_id,
            "title": f"Proposal for {request.opportunity_title}",
            "content_length": len(proposal_content),
            "completed_at": datetime.now().isoformat(),
            "engine": "claude-api" if result.get('success') else "gemini-fallback"
        }

    except Exception as e:
        print(f"[Proposal Generation] FAILED: {str(e)}")
        job["status"] = "failed"
        job["error"] = str(e)
        job["current_task"] = f"Error: {str(e)}"
