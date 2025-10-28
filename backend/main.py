from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import asyncio
import uuid
import os
import subprocess
import tempfile
from grants_service import GrantsGovService
# from semantic_service import SemanticService  # Disabled for Render free tier
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
from supabase import create_client, Client
from dotenv import load_dotenv
from anthropic import Anthropic
from scheduler_service import SchedulerService

load_dotenv()

# Setup Claude Code authentication from environment variables on server
try:
    from setup_claude_auth import setup_claude_credentials
    if os.getenv('CLAUDE_ACCESS_TOKEN'):
        setup_claude_credentials()
        print("[STARTUP] Claude Code authentication configured successfully")
except Exception as e:
    print(f"[STARTUP] Warning: Could not setup Claude Code auth: {e}")

def create_claude_code_session(prompt: str, session_type: str = "fundraising-cro", timeout: int = 900) -> dict:
    """
    Create a Claude Code session similar to iron_man_wake_hybrid.py
    Returns structured response from Claude Code session
    """
    try:
        # Refresh token before running (in case it expired)
        try:
            from claude_token_refresh import refresh_claude_token
            refresh_claude_token()
        except Exception as e:
            print(f"[Claude Code Session] Warning: Token refresh failed: {e}")
            # Continue anyway - might still work

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
        # Using --print flag for non-interactive mode with WebSearch enabled
        # Using Haiku 4.5 for faster, cheaper responses
        result = subprocess.run([
            'claude',
            '--print',
            '--model', 'claude-haiku-4-5-20251001',
            '--allowed-tools', 'WebSearch', 'WebFetch', 'Bash', 'Read', 'Write',
            '--permission-mode', 'acceptEdits'
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
        print(f"[Claude Code Session] Stdout: {result.stdout}")

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
            error_msg = result.stderr if result.stderr else result.stdout
            print(f"[Claude Code Session] FAILED - Error: {error_msg}")
            return {
                'success': False,
                'output': result.stdout,
                'error': error_msg,
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
            import re

            # Log the raw response for debugging
            print(f"[PARSE] Raw response length: {len(orchestration_result)}")
            print(f"[PARSE] First 500 chars: {orchestration_result[:500]}")

            # First, strip markdown code blocks if present
            # Remove ```json and ``` markers
            clean_result = re.sub(r'```json\s*', '', orchestration_result)
            clean_result = re.sub(r'```\s*$', '', clean_result)
            clean_result = clean_result.strip()

            # Try to find just the JSON object/array in the response
            # Look for content between first { and last }
            json_match = re.search(r'\{.*\}', clean_result, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    if 'opportunities' in data:
                        print(f"[PARSE] Successfully parsed complete JSON with {len(data['opportunities'])} opportunities")
                        return data['opportunities']
                except Exception as e:
                    print(f"[PARSE] Failed to parse extracted JSON: {e}")

            # Try to extract JSON array with opportunities
            # Look for patterns like: "opportunities": [...]
            json_match = re.search(r'"opportunities"\s*:\s*\[.*?\](?=\s*[,}])', orchestration_result, re.DOTALL)
            if json_match:
                try:
                    # Wrap in object to make valid JSON
                    json_str = '{' + json_match.group() + '}'
                    data = json.loads(json_str)
                    print(f"[PARSE] Found opportunities array with {len(data['opportunities'])} items")
                    return data.get('opportunities', [])
                except Exception as e:
                    print(f"[PARSE] Failed to parse opportunities object: {e}")

            # Try to find complete JSON object
            json_match = re.search(r'\{[^{}]*"opportunities"[^{}]*\[[^\]]*\][^{}]*\}', orchestration_result, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    print(f"[PARSE] Found complete JSON object with {len(data.get('opportunities', []))} opportunities")
                    return data.get('opportunities', [])
                except Exception as e:
                    print(f"[PARSE] Failed to parse complete JSON: {e}")

            # Try to extract just an array
            json_match = re.search(r'\[\s*\{.*?\}\s*\]', orchestration_result, re.DOTALL)
            if json_match:
                try:
                    opportunities = json.loads(json_match.group())
                    print(f"[PARSE] Found JSON array with {len(opportunities)} items")
                    return opportunities
                except Exception as e:
                    print(f"[PARSE] Failed to parse JSON array: {e}")

        # If it's already structured data
        if hasattr(orchestration_result, 'get'):
            return orchestration_result.get('opportunities', [])
        elif isinstance(orchestration_result, list):
            return orchestration_result

        print(f"[PARSE] No JSON found in response, returning empty list")
        return []
    except Exception as e:
        print(f"[PARSE] Failed to parse orchestration response: {e}")
        import traceback
        traceback.print_exc()
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

# Semantic service for RFP matching - initialize eagerly for better performance
try:
    from semantic_service import SemanticService
    semantic_service = SemanticService()
    print("[MAIN] Semantic service initialized successfully")
except Exception as e:
    print(f"[MAIN] Could not initialize semantic service: {e}")
    semantic_service = None

# Initialize scheduler service (will start on app startup)
scheduler_service = None

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now - can restrict later
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

@app.on_event("startup")
async def startup_event():
    """Initialize scheduler on startup"""
    global scheduler_service
    scheduler_service = SchedulerService(supabase)
    scheduler_service.start()

@app.on_event("shutdown")
async def shutdown_event():
    """Stop scheduler on shutdown"""
    if scheduler_service:
        scheduler_service.stop()

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "PerScholas Fundraising API",
        "scheduler_running": scheduler_service is not None
    }

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
        # Query from unified saved_opportunities table
        result = supabase.table("saved_opportunities").select("*").order("saved_at", desc=True).execute()
        return {"opportunities": result.data}
    except Exception as e:
        # Fallback to in-memory cache if database is unavailable
        return {"opportunities": opportunities_db}

@app.get("/api/scraped-grants")
async def get_scraped_grants(
    source: Optional[str] = None
):
    """
    Get grants collected by scheduled scrapers

    Args:
        source: Filter by data source (grants_gov, state, local, etc.)
    """
    try:
        query = supabase.table("scraped_grants").select("*", count="exact")

        if source:
            query = query.eq("source", source)

        query = query.order("created_at", desc=True)

        result = query.execute()

        return {
            "grants": result.data,
            "count": len(result.data),
            "total": result.count if hasattr(result, 'count') else len(result.data),
            "source": source
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch scraped grants: {str(e)}")

@app.get("/api/scheduler/status")
async def get_scheduler_status():
    """Get status of scheduled scraping jobs"""
    if not scheduler_service:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")

    try:
        jobs = scheduler_service.get_job_status()
        scheduled_jobs = []

        # Get info about scheduled jobs
        for job in scheduler_service.scheduler.get_jobs():
            scheduled_jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None
            })

        return {
            "scheduler_running": True,
            "recent_jobs": jobs,
            "scheduled_jobs": scheduled_jobs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scheduler status: {str(e)}")

@app.post("/api/scheduler/run/{job_name}")
async def run_scheduler_job(job_name: str):
    """Manually trigger a scheduled scraping job"""
    if not scheduler_service:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")

    try:
        await scheduler_service.run_job_now(job_name)
        return {
            "status": "started",
            "job_name": job_name,
            "message": f"Job '{job_name}' triggered successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run job: {str(e)}")

@app.post("/api/scraped-grants/{grant_id}/save")
async def save_scraped_grant(grant_id: str):
    """Start LLM enhancement job for a scraped grant (async with progress tracking)"""
    try:
        # Fetch the grant from scraped_grants table
        result = supabase.table("scraped_grants").select("*").eq("id", grant_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Grant not found")

        grant = result.data[0]

        # Check if already saved in unified table
        existing = supabase.table("saved_opportunities").select("id").eq("opportunity_id", grant["opportunity_id"]).execute()

        if existing.data:
            return {
                "status": "already_saved",
                "message": "This grant is already in your pipeline"
            }

        # Create background job for LLM enhancement
        job_id = str(uuid.uuid4())

        jobs_db[job_id] = {
            "job_id": job_id,
            "status": "running",
            "progress": 0,
            "current_task": "Starting LLM enhancement...",
            "result": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
            "grant_id": grant_id,
            "grant_title": grant.get("title"),
            "source": grant.get("source", "grants_gov")  # Include source field for LLM enhancement
        }

        # Start background task
        asyncio.create_task(run_llm_enhancement(job_id, grant_id))

        return {
            "status": "processing",
            "job_id": job_id,
            "message": "Grant is being enhanced with AI insights...",
            "grant_title": grant.get("title")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start enhancement: {str(e)}")

@app.post("/api/opportunities/{opportunity_id}/generate-summary")
async def generate_opportunity_summary(opportunity_id: str):
    """Generate an AI-powered summary for a saved opportunity"""
    try:
        # Fetch the opportunity from saved_opportunities
        result = supabase.table("saved_opportunities").select("*").eq("id", opportunity_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Opportunity not found")
        
        opportunity = result.data[0]
        
        # Check if we have an Anthropic API key
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not anthropic_key or anthropic_key == "your_anthropic_key_here_if_you_have_one":
            # Return a structured summary without AI
            description = opportunity.get("description", "No description available")
            requirements = opportunity.get("requirements", [])
            
            return {
                "summary": {
                    "overview": description[:500] + ("..." if len(description) > 500 else ""),
                    "key_details": [
                        f"💰 Funding Amount: ${opportunity.get('amount', 0):,}",
                        f"🏢 Funder: {opportunity.get('funder', 'N/A')}",
                        f"📅 Deadline: {opportunity.get('deadline', 'N/A')}",
                        f"📊 Match Score: {opportunity.get('match_score', 0)}%",
                        f"📋 Requirements: {len(requirements)} listed" if requirements else "Requirements: See full description"
                    ],
                    "funding_priorities": [
                        "AI analysis not available - API key required",
                        "Review the full description for detailed funding priorities",
                        "Check the funder's website for additional context"
                    ]
                }
            }
        
        # Use Anthropic Claude to generate summary
        client = Anthropic(api_key=anthropic_key)
        
        prompt = f"""Analyze this grant opportunity and provide a comprehensive understanding of what this RFP offers.

Grant Details:
- Title: {opportunity.get('title', 'N/A')}
- Funder: {opportunity.get('funder', 'N/A')}
- Amount: ${opportunity.get('amount', 0):,}
- Deadline: {opportunity.get('deadline', 'N/A')}
- Match Score: {opportunity.get('match_score', 0)}%
- Description: {opportunity.get('description', 'N/A')}
- Requirements: {json.dumps(opportunity.get('requirements', []))}

Provide a structured analysis in JSON format with these sections:

1. "overview": A comprehensive 4-6 sentence summary that explains:
   - What this grant is funding (the main purpose and scope)
   - Who the intended beneficiaries are
   - What types of projects or activities are eligible
   - Any unique aspects or special focus areas

2. "key_details": Array of 6-8 specific, factual bullet points about:
   - Funding amount and award structure
   - Eligibility requirements
   - Application requirements or process details
   - Timeline and deadline information
   - Geographic restrictions or preferences
   - Priority areas or evaluation criteria
   - Matching funds requirements (if any)
   - Any other important conditions or constraints

3. "funding_priorities": Array of 3-5 bullet points describing what the funder is specifically looking to support or achieve with this grant

Return ONLY valid JSON, no other text."""

        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        # Parse the response
        summary_text = response.content[0].text
        try:
            summary = json.loads(summary_text)
        except:
            # If JSON parsing fails, create a structured response from the text
            summary = {
                "overview": summary_text[:500],
                "key_details": ["AI-generated insights available in overview"],
                "funding_priorities": ["Review the overview for detailed analysis"]
            }
        
        # Optionally save the summary back to the database
        # supabase.table("saved_opportunities").update({"ai_summary": summary}).eq("id", opportunity_id).execute()
        
        return {"summary": summary}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")

@app.post("/api/opportunities/{opportunity_id}/save")
async def save_opportunity(opportunity_id: str):
    """Save a specific opportunity to the database with RFP similarity analysis"""
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
        # Generate embedding and find similar RFPs using semantic service
        opportunity_text = f"{opportunity['title']} {opportunity['description']}"
        embedding = None
        similar_rfps = []

        if semantic_service:
            try:
                # Generate embedding for pgvector storage
                embedding = semantic_service.get_embedding(opportunity_text)
                print(f"[SAVE] Generated embedding for '{opportunity['title'][:50]}...'")

                # Find similar historical RFPs using semantic search
                similar_rfps = semantic_service.find_similar_rfps(opportunity_text, limit=5)

                if similar_rfps:
                    print(f"[SAVE] Found {len(similar_rfps)} similar RFPs:")
                    for rfp in similar_rfps:
                        print(f"  - {rfp.get('title', 'Unknown')[:60]}... (similarity: {rfp.get('similarity_score', 0):.2f})")
                else:
                    print("[SAVE] No similar RFPs found in database")
            except Exception as e:
                print(f"[SAVE] Error with semantic service: {e}")

        # Save to scraped_grants table first (consistent with grants.gov flow)
        scraped_data = {
            "opportunity_id": opportunity["id"],
            "title": opportunity["title"],
            "funder": opportunity["funder"],
            "amount": opportunity["amount"],
            "deadline": opportunity["deadline"],
            "description": opportunity["description"],
            "requirements": opportunity.get("requirements", []),
            "contact": opportunity.get("contact", ""),
            "application_url": opportunity.get("application_url", ""),
            "source": opportunity.get("source", "Agent"),  # Mark as Agent-discovered
            "contact_name": opportunity.get("contact_name"),
            "contact_phone": opportunity.get("contact_phone"),
            "contact_description": opportunity.get("contact_description"),
            "eligibility_explanation": opportunity.get("eligibility_explanation"),
            "cost_sharing": opportunity.get("cost_sharing", False),
            "cost_sharing_description": opportunity.get("cost_sharing_description"),
            "additional_info_url": opportunity.get("additional_info_url"),
            "additional_info_text": opportunity.get("additional_info_text"),
            "archive_date": opportunity.get("archive_date"),
            "forecast_date": opportunity.get("forecast_date"),
            "close_date_explanation": opportunity.get("close_date_explanation"),
            "expected_number_of_awards": opportunity.get("expected_number_of_awards"),
            "award_floor": opportunity.get("award_floor"),
            "award_ceiling": opportunity.get("award_ceiling"),
            "attachments": opportunity.get("attachments", []),
            "version": opportunity.get("version"),
            "last_updated_date": opportunity.get("last_updated_date")
        }

        print(f"[SAVE] Saving Agent grant to scraped_grants: {opportunity['title'][:50]}...")

        # Save to scraped_grants table
        result = supabase.table("scraped_grants").insert(scraped_data).execute()
        scraped_grant_id = result.data[0]["id"] if result.data else None

        if not scraped_grant_id:
            raise HTTPException(status_code=500, detail="Failed to save to scraped_grants")

        print(f"[SAVE] Saved to scraped_grants with ID: {scraped_grant_id}")

        # Also add to local cache
        opportunities_db.append(opportunity)

        # Create background job for LLM enhancement (same pattern as save_scraped_grant)
        enhancement_job_id = str(uuid.uuid4())

        jobs_db[enhancement_job_id] = {
            "job_id": enhancement_job_id,
            "status": "running",
            "progress": 0,
            "current_task": "Starting LLM enhancement...",
            "result": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
            "grant_id": scraped_grant_id,
            "grant_title": opportunity.get("title"),
            "source": opportunity.get("source", "Agent")
        }

        # Start background LLM enhancement task (will move to saved_opportunities)
        asyncio.create_task(run_llm_enhancement(enhancement_job_id, scraped_grant_id))

        return {
            "status": "processing",
            "opportunity_id": opportunity_id,
            "enhancement_job_id": enhancement_job_id,
            "similar_rfps": similar_rfps,
            "message": f"Opportunity saved! AI enhancement in progress... Found {len(similar_rfps)} similar historical RFPs." if similar_rfps else "Opportunity saved! AI enhancement in progress..."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save opportunity: {str(e)}")

@app.delete("/api/opportunities/{opportunity_id}")
async def delete_opportunity(opportunity_id: str):
    """Delete a saved opportunity from the database"""
    try:
        # Delete from saved_opportunities table
        result = supabase.table("saved_opportunities").delete().eq("id", opportunity_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Opportunity not found")

        # Also remove from local cache if exists
        global opportunities_db
        opportunities_db = [opp for opp in opportunities_db if opp.get("id") != opportunity_id]

        return {
            "status": "deleted",
            "opportunity_id": opportunity_id,
            "message": "Opportunity successfully removed"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete opportunity: {str(e)}")

@app.post("/api/opportunities/{opportunity_id}/add-to-rfp-db")
async def add_opportunity_to_rfp_database(opportunity_id: str):
    """
    Add a saved opportunity to the RFP database for algorithm training.
    This allows users to refine the matching algorithm through feedback.
    """
    try:
        # Fetch the opportunity from saved_opportunities (including existing embedding)
        result = supabase.table("saved_opportunities").select("*").eq("id", opportunity_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Opportunity not found")

        opportunity = result.data[0]

        # Check if already in RFP database
        existing_rfp = supabase.table("rfps").select("id").eq("title", opportunity["title"]).execute()

        if existing_rfp.data:
            return {
                "status": "already_exists",
                "message": "This opportunity is already in the RFP training database",
                "rfp_id": existing_rfp.data[0]["id"]
            }

        # Reuse existing embedding from saved_opportunities if available
        embedding = opportunity.get("embedding")

        if embedding:
            print(f"[ADD_TO_RFP_DB] Reusing existing embedding for '{opportunity['title'][:50]}...'")
        elif semantic_service:
            # Only generate new embedding if one doesn't exist
            try:
                opportunity_text = f"{opportunity['title']} {opportunity['description']}"
                embedding = semantic_service.get_embedding(opportunity_text)
                print(f"[ADD_TO_RFP_DB] Generated new embedding for '{opportunity['title'][:50]}...'")
            except Exception as e:
                print(f"[ADD_TO_RFP_DB] Error generating embedding: {e}")

        # Prepare RFP data
        rfp_data = {
            "title": opportunity["title"],
            "category": opportunity.get("source", "user_feedback"),
            "content": opportunity["description"],
            "file_path": None,  # No file path for user-added opportunities
            "created_at": datetime.now().isoformat()
        }

        # Add embedding if available
        if embedding:
            rfp_data["embedding"] = embedding
            print(f"[ADD_TO_RFP_DB] Including embedding in RFP data")

        # Insert into rfps table
        try:
            rfp_result = supabase.table("rfps").insert(rfp_data).execute()
        except Exception as db_error:
            # If it's a duplicate key error, the sequence might be out of sync
            error_str = str(db_error)
            if "duplicate key" in error_str.lower() or "23505" in error_str:
                # Try to fix the sequence by selecting max ID and resetting
                print(f"[ADD_TO_RFP_DB] Duplicate key error detected, attempting sequence fix...")

                # Get max ID from table
                max_result = supabase.table("rfps").select("id").order("id", desc=True).limit(1).execute()
                if max_result.data and len(max_result.data) > 0:
                    max_id = max_result.data[0]["id"]
                    print(f"[ADD_TO_RFP_DB] Max ID in table: {max_id}")

                # Re-raise with helpful message
                raise Exception(
                    f"Database sequence error. The rfps table auto-increment sequence is out of sync. "
                    f"Please run this SQL to fix it: "
                    f"SELECT setval('rfps_id_seq', (SELECT MAX(id) FROM rfps));"
                )
            raise

        if hasattr(rfp_result, 'error') and rfp_result.error:
            raise Exception(f"Database error: {rfp_result.error}")

        return {
            "status": "success",
            "message": "Successfully added to RFP training database",
            "rfp_id": rfp_result.data[0]["id"] if rfp_result.data else None,
            "has_embedding": embedding is not None,
            "opportunity_title": opportunity["title"]
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ADD_TO_RFP_DB] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add to RFP database: {str(e)}")

@app.post("/api/rfps/load")
async def load_rfps():
    """Load RFPs from directory into database (admin endpoint)"""
    try:
        # Load RFPs from directory
        # rfps = semantic_service.load_rfps_from_directory()  # Disabled for Render free tier
        rfps = []

        if not rfps:
            return {"status": "no_rfps", "message": "No RFPs found to load - semantic service disabled"}

        # Store in Supabase
        # success = semantic_service.store_rfps_in_supabase(rfps)  # Disabled for Render free tier
        success = False

        if success:
            return {
                "status": "success",
                "message": f"Successfully loaded {len(rfps)} RFPs into database",
                "count": len(rfps)
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to store RFPs in database")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load RFPs: {str(e)}")

@app.get("/api/rfps/similar/{opportunity_id}")
async def get_similar_rfps(opportunity_id: str):
    """Get similar RFPs for a saved opportunity using semantic search"""
    try:
        # Find opportunity in saved opportunities
        result = supabase.table("saved_opportunities").select("*").eq("opportunity_id", opportunity_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Saved opportunity not found")

        opportunity = result.data[0]
        opportunity_text = f"{opportunity['title']} {opportunity['description']}"

        # Find similar RFPs using semantic service
        similar_rfps = []
        if semantic_service:
            try:
                similar_rfps = semantic_service.find_similar_rfps(opportunity_text, limit=5)

                if similar_rfps:
                    print(f"[SIMILAR_RFPS] Found {len(similar_rfps)} similar RFPs for opportunity {opportunity_id}")
                    for rfp in similar_rfps:
                        print(f"  - {rfp.get('title', 'Unknown')[:60]}... (similarity: {rfp.get('similarity_score', 0):.2f})")
                else:
                    print(f"[SIMILAR_RFPS] No similar RFPs found for opportunity {opportunity_id}")
            except Exception as e:
                print(f"[SIMILAR_RFPS] Error finding similar RFPs: {e}")

        return {
            "opportunity": opportunity,
            "similar_rfps": similar_rfps
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding similar RFPs: {str(e)}")

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
        # Get opportunities count and funding from unified table
        opportunities_result = supabase.table("saved_opportunities").select("amount").execute()
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

async def run_llm_enhancement(job_id: str, grant_id: str):
    """Background task for LLM enhancement with progress updates"""
    job = jobs_db[job_id]

    try:
        from llm_enhancement_service import enhance_and_save_grant

        # Update progress
        job["current_task"] = "Generating AI summary..."
        job["progress"] = 25

        # Run LLM enhancement
        enhanced_grant = await enhance_and_save_grant(grant_id, supabase)

        # Update progress
        job["current_task"] = "Extracting tags and reasoning..."
        job["progress"] = 75

        # Mark complete
        job["status"] = "completed"
        job["progress"] = 100
        job["current_task"] = "Grant saved with AI insights!"
        job["result"] = {
            "grant_id": grant_id,
            "opportunity_id": enhanced_grant.get("opportunity_id"),
            "llm_summary": enhanced_grant.get("llm_summary"),
            "tags": enhanced_grant.get("tags", []),
            "detailed_reasoning": enhanced_grant.get("detailed_match_reasoning"),
            "completed_at": datetime.now().isoformat()
        }

    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        job["current_task"] = f"Error: {str(e)}"
        print(f"[LLM Enhancement Job] Failed: {e}")

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
            # Get existing opportunities to avoid duplicates from unified table
            try:
                existing_result = supabase.table("saved_opportunities").select("title, funder").execute()
                existing_opps = [f"{opp['title']} - {opp['funder']}" for opp in existing_result.data]
                existing_list = "; ".join(existing_opps) if existing_opps else "None"
            except:
                existing_list = "None"

            # Create comprehensive prompt for fundraising-cro agent
            orchestration_prompt = f"""You are a fundraising-cro agent for Per Scholas. Find MULTIPLE (3-5) REAL, CURRENT funding opportunities using web search and research.

Organization Context:
{per_scholas_context}

User Search Request: {criteria.prompt}

Execute this multi-step process:

1. Search current federal databases (GRANTS.gov, NSF, DOL) for technology workforce development opportunities
2. Research foundation grants from major funders aligned with our mission
3. Identify corporate funding programs for underserved communities
4. Filter for opportunities with deadlines in next 3-6 months and funding >$50k
5. Find at least 3-5 different opportunities from various sources

Existing opportunities to avoid duplicates: {existing_list}

CRITICAL OUTPUT FORMAT - READ CAREFULLY:
You MUST return ONLY raw JSON - NO markdown code blocks, NO explanatory text, NO ```json markers.
Your response should START with {{ and END with }}.

Example of CORRECT output:
{{
  "opportunities": [
    {{
      "id": "unique-id-string",
      "title": "Full grant title",
      "funder": "Organization name",
      "amount": 100000,
      "deadline": "2025-12-31",
      "description": "Detailed description of opportunity",
      "requirements": ["Requirement 1", "Requirement 2"],
      "contact": "email@agency.gov",
      "application_url": "https://...",
      "contact_name": "Contact Person Name or null",
      "contact_phone": "555-1234 or null",
      "contact_description": "Additional contact info or null",
      "eligibility_explanation": "Who can apply or null",
      "cost_sharing": false,
      "cost_sharing_description": "Cost sharing details or null",
      "additional_info_url": "https://... or null",
      "additional_info_text": "Extra info or null",
      "archive_date": "2025-12-31 or null",
      "forecast_date": "2025-01-01 or null",
      "close_date_explanation": "Deadline details or null",
      "expected_number_of_awards": "5-10 or null",
      "award_floor": 50000,
      "award_ceiling": 250000,
      "attachments": [],
      "version": "1 or null",
      "last_updated_date": "2025-01-01 or null"
    }}
  ]
}}

REQUIREMENTS:
- Return ONLY the JSON object (no markdown blocks, no extra text)
- Start with {{ and end with }}
- All string fields use double quotes
- amount, award_floor, award_ceiling are integers (no commas)
- deadline dates in YYYY-MM-DD format
- Do NOT include match_score (it will be calculated automatically)
- requirements is array of strings
- attachments is empty array [] (no attachment fetching)
- Use null for optional fields if no data available"""

            job["current_task"] = "Creating Claude Code fundraising session..."
            job["progress"] = 50

            # Create Claude Code session (with grants service fallback)
            print(f"[Claude Code Session] Starting fundraising opportunity discovery...")

            # Use grants service API if available, otherwise fall back to Claude Code
            use_api = False  # Set to False to use Claude Code instead

            if use_api:
                print(f"[Claude Code Session] Fetching real grants data...")
                search_keywords = criteria.prompt if criteria.prompt and criteria.prompt != "hi" else "technology workforce development"
                # Clean the search keywords - remove newlines and extra whitespace
                search_keywords = search_keywords.strip()
                print(f"[DEBUG] Search keywords: '{search_keywords}'")

                grants_service = GrantsGovService(supabase_client=supabase)
                real_grants = grants_service.search_grants(search_keywords, limit=10)
                print(f"[DEBUG] Retrieved {len(real_grants)} real grants")
                orchestration_result = json.dumps({"opportunities": real_grants})
            else:
                session_result = create_claude_code_session(
                    prompt=orchestration_prompt,
                    session_type="fundraising-cro",
                    timeout=900
                )

                if not session_result['success']:
                    raise Exception(f"Claude Code session failed: {session_result['error']}")

                orchestration_result = session_result['output']

            # Save raw response for debugging
            with open('/tmp/last_claude_response.txt', 'w') as f:
                f.write(orchestration_result)
            print(f"[DEBUG] Saved raw Claude response to /tmp/last_claude_response.txt")

            job["current_task"] = "Processing fundraising session results..."
            job["progress"] = 80

            # Parse the orchestrated response
            opportunities = parse_orchestration_response(orchestration_result)

            # Score opportunities using match_scoring (Claude is just a scraper)
            if opportunities and semantic_service:
                from match_scoring import calculate_match_score
                print(f"[SCORING] Scoring {len(opportunities)} opportunities from Claude agent...")

                for opp in opportunities:
                    try:
                        # Find similar RFPs for this opportunity
                        opp_text = f"{opp.get('title', '')} {opp.get('description', '')}"
                        similar_rfps = semantic_service.find_similar_rfps(opp_text, limit=5)

                        # Calculate real match score using similar RFPs
                        match_score = calculate_match_score(opp, similar_rfps)
                        opp['match_score'] = match_score

                        print(f"[SCORING] {opp.get('title', 'Unknown')[:60]}... = {match_score}% (found {len(similar_rfps)} similar RFPs)")
                    except Exception as e:
                        print(f"[SCORING] Error scoring opportunity: {e}")
                        opp['match_score'] = opp.get('match_score', 50)  # Keep Claude's estimate as fallback

            # Tag opportunities from Claude Agent with source="Agent"
            if not use_api and opportunities:
                for opp in opportunities:
                    opp['source'] = 'Agent'
                print(f"[DEBUG] Tagged {len(opportunities)} opportunities with source='Agent'")

        except Exception as e:
            print(f"Orchestration failed: {e}")
            opportunities = []

        # If no opportunities found, return empty result
        if not opportunities:
            opportunities = []

        # Auto-save disabled for demo - return opportunities directly
        saved_opportunities = opportunities
        # if opportunities:
        #     job["current_task"] = "Saving opportunities to database..."
        #     job["progress"] = 90

        #     for opp in opportunities:
        #         try:
        #             # Save to Supabase
        #             result = supabase.table("opportunities").insert({
        #                 "id": opp.get("id"),
        #                 "title": opp.get("title"),
        #                 "funder": opp.get("funder"),
        #                 "amount": opp.get("amount"),
        #                 "deadline": opp.get("deadline"),
        #                 "match_score": opp.get("match_score", 0),
        #                 "description": opp.get("description"),
        #                 "requirements": opp.get("requirements", []),
        #                 "contact": opp.get("contact"),
        #                 "application_url": opp.get("application_url"),
        #                 "status": "active",
        #                 "created_at": datetime.now().isoformat(),
        #                 "updated_at": datetime.now().isoformat()
        #             }).execute()
        #             saved_opportunities.append(opp)
        #             print(f"Saved opportunity: {opp.get('title')}")
        #         except Exception as e:
        #             print(f"Failed to save opportunity {opp.get('title')}: {e}")
        #             # Continue with other opportunities

        # Complete job with opportunities for user review
        job["status"] = "completed"
        job["progress"] = 100
        job["current_task"] = "Search completed successfully"
        job["result"] = {
            "opportunities": opportunities,
            "saved_opportunities": len(saved_opportunities),
            "total_found": len(opportunities),
            "search_criteria": criteria.model_dump(),
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

@app.get("/api/proposals/{proposal_id}/download")
async def download_proposal(proposal_id: int):
    """
    Serve a proposal PDF file from the server filesystem.

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

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)