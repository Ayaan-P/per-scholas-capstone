
import os
from dotenv import load_dotenv

# Load environment variables FIRST, before any imports that need them
load_dotenv()

from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from auth_service import get_current_user, optional_token
import asyncio
import uuid
import subprocess
import tempfile
import io
from grants_service import GrantsGovService
# from semantic_service import SemanticService  # Disabled for Render free tier
from typing import List, Dict, Any, Optional
from credits_service import CreditsService
from credits_routes import router as credits_router
# Route modules (Issue #37 - splitting main.py)
from routes.health import router as health_router, set_scheduler_service as set_health_scheduler
from routes.categories import router as categories_router
from routes.scheduler import router as scheduler_router, set_dependencies as set_scheduler_deps
from routes.dashboard import router as dashboard_router, set_dependencies as set_dashboard_deps
from routes.organization import router as organization_router, set_dependencies as set_org_deps
from routes.proposals import router as proposals_router, set_dependencies as set_proposals_deps
from routes.workspace import router as workspace_router, set_dependencies as set_workspace_deps
from datetime import datetime, timedelta
import json
from supabase import create_client, Client
import google.generativeai as genai
from scheduler_service import SchedulerService
import PyPDF2
import httpx

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
        result = subprocess.run([
            'claude',
            '--print',
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
        except OSError:
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


def create_gemini_cli_session(prompt: str, session_type: str = "fundraising", timeout: int = 900) -> dict:
    """
    Create a Gemini CLI session for opportunity discovery
    Returns structured response from Gemini CLI session
    """
    try:
        # Create temporary file for the prompt
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(prompt)
            temp_prompt_file = f.name

        # Set up environment variables
        env = os.environ.copy()

        # Ensure GEMINI_API_KEY is set (should come from environment)
        if 'GEMINI_API_KEY' not in env:
            raise Exception("GEMINI_API_KEY environment variable not set")

        print(f"[Gemini CLI Session] Starting {session_type} session...")
        print(f"[Gemini CLI Session] Prompt length: {len(prompt)} chars")

        # Execute Gemini CLI session with web search enabled
        # Using positional prompt argument for one-shot (non-interactive) mode
        result = subprocess.run([
            'gemini',
            '--approval-mode', 'yolo',  # Auto-approve tool usage
            prompt
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        cwd=os.getcwd()
        )

        print(f"[Gemini CLI Session] Completed with return code: {result.returncode}")
        print(f"[Gemini CLI Session] Output length: {len(result.stdout)} chars")
        print(f"[Gemini CLI Session] Stdout: {result.stdout[:500]}...")  # Print first 500 chars

        if result.stderr:
            print(f"[Gemini CLI Session] Stderr: {result.stderr[:500]}...")

        # Clean up temp file
        try:
            os.unlink(temp_prompt_file)
        except OSError:
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
            print(f"[Gemini CLI Session] FAILED - Error: {error_msg}")
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
            'error': f'Gemini CLI session timed out after {timeout} seconds',
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
    except (TypeError, AttributeError):
        return ""

app = FastAPI(title="PerScholas Fundraising API")

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://zjqwpvdcpzeguhdwrskr.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpqcXdwdmRjcHplZ3VoZHdyc2tyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTgyNTczMzcsImV4cCI6MjA3MzgzMzMzN30.Ba46pLQFygSQoe-TZ4cRvLCpmT707zw2JT8qIRSjopU")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Anon client for regular queries
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Service role client for admin operations (bypasses RLS)
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) if SUPABASE_SERVICE_ROLE_KEY else supabase

# Helper function for creating auth headers for Supabase API calls
def _make_org_config_auth_headers():
    """Create authorization headers for service role access to Supabase API"""
    return {
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

# Gemini API configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

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

# Include credits router
app.include_router(credits_router)

# Include route modules (Issue #37 - splitting main.py)
app.include_router(health_router)
app.include_router(categories_router)
app.include_router(scheduler_router)
app.include_router(dashboard_router)
app.include_router(organization_router)
app.include_router(proposals_router)
app.include_router(workspace_router)

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

# ProposalRequest moved to routes/proposals.py (Issue #37)

class FeedbackRequest(BaseModel):
    feedback_type: str  # 'positive' or 'negative'
    user_id: str = "anonymous"

class UpdateOpportunityDescriptionRequest(BaseModel):
    description: str

class UpdateOpportunityNotesRequest(BaseModel):
    notes: str

# SchedulerSettingsRequest/Response moved to routes/scheduler.py (Issue #37)
# OrganizationConfigRequest, DocumentExtractRequest, ApplyExtractionRequest, 
# OrganizationConfig, UserInitializationRequest moved to routes/organization.py (Issue #37)

def get_default_organization_config():
    """Get default organization configuration"""
    return {
        "name": "Your Organization",
        "mission": "Advancing opportunity through technology and education",
        "focus_areas": ["Technology", "Education", "Community Development"],
        "impact_metrics": {
            "graduates": "1000+",
            "job_placement_rate": "85%",
            "salary_increase": "150%"
        },
        "programs": ["Training Program 1", "Training Program 2"],
        "target_demographics": ["Underrepresented communities", "Career changers", "Low-income individuals"]
    }

async def get_organization_config():
    """Fetch organization configuration from database or return default"""
    try:
        result = supabase.table("organization_config").select("*").limit(1).execute()
        if result.data and len(result.data) > 0:
            config = result.data[0]
            return {
                "id": config.get("id"),
                "name": config.get("name", "Your Organization"),
                "mission": config.get("mission", ""),
                "focus_areas": config.get("focus_areas", []),
                "impact_metrics": config.get("impact_metrics", {}),
                "programs": config.get("programs", []),
                "target_demographics": config.get("target_demographics", []),
                "created_at": config.get("created_at"),
                "updated_at": config.get("updated_at")
            }
    except Exception as e:
        print(f"[ORG CONFIG] Error fetching from database: {e}")

    # Return default config if database fails or empty
    default = get_default_organization_config()
    return {
        "id": None,
        "name": default["name"],
        "mission": default["mission"],
        "focus_areas": default["focus_areas"],
        "impact_metrics": default["impact_metrics"],
        "programs": default["programs"],
        "target_demographics": default["target_demographics"],
        "created_at": None,
        "updated_at": None
    }

def parse_amount(amount_text: Any) -> Optional[int]:
    """Parse funding amount from text, returning integer in dollars"""
    if not amount_text:
        return None

    if isinstance(amount_text, int):
        return amount_text

    # Convert to string if needed
    text = str(amount_text).lower()

    # Extract first number (with optional decimals) found in the string
    import re
    match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', text)
    if match:
        try:
            # Remove commas and convert to int
            num_str = match.group(1).replace(',', '')
            # If it has decimals, convert to int (remove decimals)
            if '.' in num_str:
                return int(float(num_str))
            return int(num_str)
        except (ValueError, AttributeError):
            return None

    return None

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF file bytes"""
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text.strip()
    except Exception as e:
        print(f"[PDF EXTRACTION] Error: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to extract text from PDF: {str(e)}")

async def analyze_uploaded_rfp(pdf_text: str, title: Optional[str] = None, funder: Optional[str] = None, deadline: Optional[str] = None) -> Dict[str, Any]:
    """Use Gemini to analyze uploaded RFP and extract metadata"""
    try:
        prompt = f"""Analyze this RFP/grant document and extract key information. Return a JSON object with:
- title: The grant/RFP title (use provided title if given, otherwise extract)
- funder: The funding organization (use provided if given, otherwise extract)
- deadline: Application deadline (use provided if given, otherwise extract)
- description: 2-3 sentence summary of the opportunity
- amount: Estimated funding amount if mentioned, or null
- tags: Array of 3-5 relevant tags/categories
- key_requirements: Array of main eligibility/requirement bullet points (3-5 items)

Document text:
{pdf_text[:4000]}

Provided title: {title or 'Not provided'}
Provided funder: {funder or 'Not provided'}
Provided deadline: {deadline or 'Not provided'}

Return ONLY valid JSON, no markdown or additional text."""

        gemini_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-3-flash-preview')
        response = model.generate_content(prompt)

        response_text = response.text
        # Parse JSON from response
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            extracted = json.loads(json_match.group())
        else:
            extracted = json.loads(response_text)

        return extracted
    except Exception as e:
        print(f"[RFP ANALYSIS] Error: {e}")
        # Return minimal structured data on error
        return {
            "title": title or "Uploaded RFP",
            "funder": funder or "Unknown",
            "deadline": deadline,
            "description": "RFP document uploaded by user",
            "tags": ["user-uploaded"],
            "key_requirements": []
        }

# Auth & Organization routes moved to routes/organization.py (Issue #37)
# Category routes moved to routes/categories.py (Issue #37)

@app.on_event("startup")
async def startup_event():
    """Initialize scheduler on startup"""
    global scheduler_service
    # Initialize category service early with a working client
    # (the module-level client in category_service.py may be None if SUPABASE_SERVICE_ROLE_KEY wasn't set at import time)
    from category_service import get_category_service
    get_category_service(supabase_admin)
    
    scheduler_service = SchedulerService(supabase)
    scheduler_service.start()
    
    # Inject dependencies into route modules (Issue #37)
    set_health_scheduler(scheduler_service)
    set_scheduler_deps(scheduler_service, supabase)
    set_dashboard_deps(supabase, jobs_db)
    set_org_deps(supabase, supabase_admin, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    # Pass Gemini as optional fallback - Claude API is now primary
    set_proposals_deps(supabase, jobs_db, create_gemini_cli_session, parse_proposal_orchestration_response)
    print("[STARTUP] Proposal generation configured: Claude API primary, Gemini CLI fallback")
    
    # Workspace service for agentic architecture
    set_workspace_deps(supabase, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    print("[STARTUP] Workspace service configured for per-org agent sessions")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop scheduler on shutdown"""
    if scheduler_service:
        scheduler_service.stop()

# Health and scheduler routes moved to routes/health.py and routes/scheduler.py (Issue #37)

@app.post("/api/search-opportunities")
async def start_opportunity_search(
    criteria: SearchCriteria,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """Start AI-powered opportunity discovery with organization-specific matching"""

    # Check if monthly credits need to be reset
    CreditsService.reset_monthly_credits_if_needed(user_id)

    # Check if user has enough credits for a search (1 credit per search)
    check_result = CreditsService.check_and_deduct_credits(user_id, amount=1, reference_id=None)
    if not check_result["success"]:
        raise HTTPException(
            status_code=402,  # Payment Required
            detail=f"Insufficient credits. {check_result.get('error', 'Please purchase more credits')}"
        )

    job_id = str(uuid.uuid4())

    # Update reference_id with job_id after deduction
    supabase_admin.table("credit_transactions").update({
        "reference_id": job_id
    }).eq("id", job_id).execute()  # This will need adjustment based on actual transaction ID

    # Initialize job
    jobs_db[job_id] = {
        "job_id": job_id,
        "status": "running",
        "progress": 0,
        "current_task": "Initializing AI agent...",
        "result": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "credits_deducted": 1,
        "new_balance": check_result["new_balance"]
    }

    # Start background task with user_id for organization-aware matching
    import asyncio
    asyncio.create_task(run_opportunity_search(job_id, criteria, user_id))

    return {
        "job_id": job_id,
        "status": "started",
        "credits_used": 1,
        "new_balance": check_result["new_balance"]
    }

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str, user_id: str = Depends(get_current_user)):
    """Get job status and results (requires authentication)"""
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")

    return jobs_db[job_id]

@app.get("/api/opportunities")
async def get_opportunities(user_id: str = Depends(get_current_user)):
    """Get user's saved opportunities from database (with RLS isolation)"""
    try:
        # Use admin client to bypass RLS, then filter by authenticated user_id for security
        result = supabase_admin.table("saved_opportunities").select("*").eq("user_id", user_id).order("saved_at", desc=True).execute()
        return {"opportunities": result.data}
    except Exception as e:
        print(f"[GET OPPORTUNITIES] Error: {e}")
        # Fallback to empty list if database unavailable
        return {"opportunities": []}

@app.get("/api/scraped-grants")
async def get_scraped_grants(
    source: Optional[str] = None,
    user_id: Optional[str] = Depends(optional_token)
):
    """
    Get grants collected by scheduled scrapers with personalized match scores (if authenticated)

    Args:
        source: Filter by data source (grants_gov, state, local, etc.)
        user_id: Optional authenticated user ID (from JWT token) - if provided, returns personalized scores
    """
    try:
        # Fetch grants from database
        query = supabase.table("scraped_grants").select("*", count="exact")

        if source:
            query = query.eq("source", source)

        query = query.order("created_at", desc=True)

        result = query.execute()
        grants = result.data

        # Calculate personalized match scores if user is authenticated
        org_profile = None
        if user_id:
            try:
                from organization_matching_service import OrganizationMatchingService
                from match_scoring import calculate_match_score

                matching_service = OrganizationMatchingService(supabase)
                org_profile = await matching_service.get_organization_profile(user_id)

                if org_profile:
                    # Recalculate match scores based on organization profile
                    for grant in grants:
                        # Calculate base keyword matching score using organization's keywords
                        primary_keywords, secondary_keywords = matching_service.build_search_keywords(org_profile)

                        # Get grant text
                        title_lower = (grant.get('title') or '').lower()
                        desc_lower = (grant.get('description') or '').lower()
                        full_text = title_lower + ' ' + desc_lower

                        # Count keyword matches
                        primary_matches = sum(1 for keyword in primary_keywords if keyword in full_text)
                        secondary_matches = sum(1 for keyword in secondary_keywords if keyword in full_text)

                        # Calculate keyword score (0-100)
                        if primary_matches >= 2:
                            keyword_score = min(100, (primary_matches * 15) + (secondary_matches * 3))
                        elif primary_matches == 1:
                            keyword_score = min(50, primary_matches * 15 + (secondary_matches * 2))
                        else:
                            keyword_score = max(10, secondary_matches * 2)

                        # For now, use 0 for semantic similarity (would need RFP embeddings)
                        semantic_score = 0

                        # Calculate organization-specific match score
                        org_match = matching_service.calculate_organization_match_score(
                            org_profile,
                            {
                                'title': grant.get('title'),
                                'description': grant.get('description'),
                                'synopsis': grant.get('description'),
                                'estimated_funding_min': grant.get('award_floor'),
                                'estimated_funding_max': grant.get('award_ceiling') or grant.get('amount'),
                                'deadline': grant.get('deadline'),
                                'geographic_focus': None,  # Could extract from grant if available
                            },
                            keyword_score,
                            semantic_score
                        )

                        # Update the match_score field with personalized score
                        grant['match_score'] = int(org_match['overall_score'])
                        grant['match_breakdown'] = {
                            'keyword_matching': org_match['keyword_matching'],
                            'funding_alignment': org_match['funding_alignment'],
                            'deadline_feasibility': org_match['deadline_feasibility'],
                            'demographic_alignment': org_match['demographic_alignment'],
                            'geographic_alignment': org_match['geographic_alignment'],
                        }
            except Exception as e:
                print(f"[GET SCRAPED GRANTS] Error calculating personalized scores: {e}")
                # Continue with generic scores from database

        return {
            "grants": grants,
            "count": len(grants),
            "total": result.count if hasattr(result, 'count') else len(grants),
            "source": source,
            "personalized": org_profile is not None
        }
    except Exception as e:
        print(f"[GET SCRAPED GRANTS] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch scraped grants: {str(e)}")

# Scheduler status and run routes moved to routes/scheduler.py (Issue #37)

@app.post("/api/scraped-grants/{grant_id}/save")
async def save_scraped_grant(grant_id: str, user_id: str = Depends(get_current_user)):
    """Start LLM enhancement job for a scraped grant (async with progress tracking)"""
    print(f"[SAVE GRANT] Request received for grant_id={grant_id}, user_id={user_id}")
    try:
        # Fetch the grant from scraped_grants table
        result = supabase.table("scraped_grants").select("*").eq("id", grant_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Grant not found")

        grant = result.data[0]

        # Check if already saved in unified table by this user
        existing = supabase.table("saved_opportunities").select("id").eq("opportunity_id", grant["opportunity_id"]).eq("user_id", user_id).execute()

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
            "source": grant.get("source", "grants_gov"),  # Include source field for LLM enhancement
            "user_id": user_id  # Store user_id for org-specific matching
        }

        # Start background task with user_id for org-specific matching
        asyncio.create_task(run_llm_enhancement(job_id, grant_id, user_id))

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
async def generate_opportunity_summary(opportunity_id: str, user_id: str = Depends(get_current_user)):
    """Generate an AI-powered summary for a saved opportunity"""
    try:
        # Fetch the opportunity from saved_opportunities, filtered by user_id for security
        result = supabase.table("saved_opportunities").select("*").eq("id", opportunity_id).eq("user_id", user_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Opportunity not found")
        
        opportunity = result.data[0]
        
        # Check if we have a Gemini API key
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        if not gemini_key:
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

        # Use Gemini to generate summary
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-3-flash-preview')

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

        response = model.generate_content(prompt)

        # Parse the response
        summary_text = response.text
        try:
            summary = json.loads(summary_text)
        except (json.JSONDecodeError, TypeError):
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
async def save_opportunity(opportunity_id: str, user_id: str = Depends(get_current_user)):
    """Save a specific opportunity to the database with RFP similarity analysis"""
    # Find opportunity in current job results
    opportunity = None
    for job in jobs_db.values():
        if job.get("result") and job["result"].get("opportunities"):
            for opp in job["result"]["opportunities"]:
                if opp["id"] == opportunity_id:
                    opportunity = opp
                    break

    # If not in search cache, check scraped_grants table
    if not opportunity:
        try:
            result = supabase.table("scraped_grants").select("*").eq("id", opportunity_id).execute()
            if result.data:
                grant = result.data[0]
                # Convert scraped_grant format to opportunity format
                opportunity = {
                    "id": grant.get("id"),
                    "title": grant.get("title"),
                    "funder": grant.get("funder"),
                    "amount": grant.get("amount"),
                    "deadline": grant.get("deadline"),
                    "description": grant.get("description"),
                    "requirements": grant.get("requirements", []),
                    "contact": grant.get("contact", ""),
                    "application_url": grant.get("application_url", ""),
                    "source": grant.get("source", ""),
                    "contact_name": grant.get("contact_name"),
                    "contact_phone": grant.get("contact_phone"),
                    "contact_description": grant.get("contact_description"),
                    "eligibility_explanation": grant.get("eligibility_explanation"),
                    "cost_sharing": grant.get("cost_sharing", False),
                    "cost_sharing_description": grant.get("cost_sharing_description"),
                    "additional_info_url": grant.get("additional_info_url"),
                    "additional_info_text": grant.get("additional_info_text"),
                    "archive_date": grant.get("archive_date"),
                    "forecast_date": grant.get("forecast_date"),
                    "close_date_explanation": grant.get("close_date_explanation"),
                    "expected_number_of_awards": grant.get("expected_number_of_awards"),
                    "award_floor": grant.get("award_floor"),
                    "award_ceiling": grant.get("award_ceiling"),
                    "attachments": grant.get("attachments", []),
                    "version": grant.get("version"),
                    "last_updated_date": grant.get("last_updated_date")
                }
        except Exception as e:
            print(f"[SAVE] Error checking scraped_grants: {e}")

    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found in search results or database")

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
            "source": opportunity.get("source", "Agent"),
            "user_id": user_id  # Store user_id for org-specific matching
        }

        # Start background LLM enhancement task (will move to saved_opportunities) with org-specific matching
        print(f"[SAVE] Creating background LLM enhancement task. user_id={user_id}, grant_id={scraped_grant_id}")
        asyncio.create_task(run_llm_enhancement(enhancement_job_id, scraped_grant_id, user_id))

        return {
            "status": "processing",
            "opportunity_id": opportunity_id,
            "enhancement_job_id": enhancement_job_id,
            "similar_rfps": similar_rfps,
            "message": f"Opportunity saved! AI enhancement in progress... Found {len(similar_rfps)} similar historical RFPs." if similar_rfps else "Opportunity saved! AI enhancement in progress..."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save opportunity: {str(e)}")


@app.patch("/api/opportunities/{opportunity_id}/description")
async def update_opportunity_description(opportunity_id: str, payload: UpdateOpportunityDescriptionRequest, user_id: str = Depends(get_current_user)):
    """Update the description of a saved opportunity"""
    new_description = payload.description.strip()
    if not new_description:
        raise HTTPException(status_code=400, detail="Description cannot be empty")

    updated_at = datetime.now().isoformat()
    updated_record = None
    supabase_error = None

    try:
        result = supabase.table("saved_opportunities").update({
            "description": new_description,
            "updated_at": updated_at
        }).eq("id", opportunity_id).eq("user_id", user_id).execute()

        if result.data:
            updated_record = result.data[0]
    except Exception as e:
        supabase_error = e

    if not updated_record:
        for opp in opportunities_db:
            if opp.get("id") == opportunity_id:
                opp["description"] = new_description
                opp["updated_at"] = updated_at
                updated_record = opp
                break

    if not updated_record:
        if supabase_error:
            raise HTTPException(status_code=500, detail=f"Failed to update opportunity description: {supabase_error}")
        raise HTTPException(status_code=404, detail="Opportunity not found")

    return {
        "status": "updated",
        "opportunity_id": opportunity_id,
        "description": updated_record.get("description", new_description),
        "updated_at": updated_record.get("updated_at", updated_at)
    }


@app.patch("/api/opportunities/{opportunity_id}/notes")
async def update_opportunity_notes(opportunity_id: str, payload: UpdateOpportunityNotesRequest, user_id: str = Depends(get_current_user)):
    """Update the notes of a saved opportunity"""
    new_notes = payload.notes.strip() if payload.notes else ""

    updated_at = datetime.now().isoformat()
    updated_record = None
    supabase_error = None

    try:
        result = supabase.table("saved_opportunities").update({
            "notes": new_notes,
            "updated_at": updated_at
        }).eq("id", opportunity_id).eq("user_id", user_id).execute()

        if result.data:
            updated_record = result.data[0]
    except Exception as e:
        supabase_error = e

    if not updated_record:
        for opp in opportunities_db:
            if opp.get("id") == opportunity_id:
                opp["notes"] = new_notes
                opp["updated_at"] = updated_at
                updated_record = opp
                break

    if not updated_record:
        if supabase_error:
            raise HTTPException(status_code=500, detail=f"Failed to update opportunity notes: {supabase_error}")
        raise HTTPException(status_code=404, detail="Opportunity not found")

    return {
        "status": "updated",
        "opportunity_id": opportunity_id,
        "notes": updated_record.get("notes", new_notes),
        "updated_at": updated_record.get("updated_at", updated_at)
    }


@app.delete("/api/opportunities/{opportunity_id}")
async def delete_opportunity(opportunity_id: str, user_id: str = Depends(get_current_user)):
    """Delete a saved opportunity from the database"""
    try:
        # Delete from saved_opportunities table by opportunity_id, not id
        result = supabase_admin.table("saved_opportunities").delete().eq("opportunity_id", opportunity_id).eq("user_id", user_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Opportunity not found")

        # Also remove from local cache if exists
        global opportunities_db
        opportunities_db = [opp for opp in opportunities_db if opp.get("opportunity_id") != opportunity_id]

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
async def add_opportunity_to_rfp_database(opportunity_id: str, user_id: str = Depends(get_current_user)):
    """
    Add a saved opportunity to the RFP database for algorithm training.
    This allows users to refine the matching algorithm through feedback.
    """
    try:
        # Fetch the opportunity from saved_opportunities (including existing embedding)
        result = supabase.table("saved_opportunities").select("*").eq("id", opportunity_id).eq("user_id", user_id).execute()

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

@app.post("/api/opportunities/{opportunity_id}/feedback")
async def submit_opportunity_feedback(opportunity_id: str, feedback: FeedbackRequest):
    """Submit user feedback for an opportunity (thumbs up/down)"""
    try:
        # Simple in-memory feedback store
        if not hasattr(get_opportunity_feedback_counts, 'feedback_store'):
            get_opportunity_feedback_counts.feedback_store = {}
        
        if opportunity_id not in get_opportunity_feedback_counts.feedback_store:
            get_opportunity_feedback_counts.feedback_store[opportunity_id] = {"positive": 0, "negative": 0}
        
        if feedback.feedback_type in ["positive", "negative"]:
            get_opportunity_feedback_counts.feedback_store[opportunity_id][feedback.feedback_type] += 1
        
        return {"message": "Feedback submitted successfully", "status": "success"}
        
    except Exception as e:
        return {"message": f"Feedback received: {feedback.feedback_type}", "status": "success"}

@app.get("/api/opportunities/{opportunity_id}/feedback")
async def get_opportunity_feedback(opportunity_id: str):
    """Get feedback summary for an opportunity"""
    try:
        return get_opportunity_feedback_counts(opportunity_id)
    except Exception as e:
        return {"positive": 0, "negative": 0}

def get_opportunity_feedback_counts(opportunity_id: str) -> Dict[str, int]:
    """Get feedback counts using in-memory store"""
    if not hasattr(get_opportunity_feedback_counts, 'feedback_store'):
        get_opportunity_feedback_counts.feedback_store = {}
    
    return get_opportunity_feedback_counts.feedback_store.get(opportunity_id, {"positive": 0, "negative": 0})

@app.post("/api/opportunities/{opportunity_id}/dismiss")
async def dismiss_opportunity(opportunity_id: str, user_id: str = Depends(get_current_user)):
    """Dismiss an opportunity from the dashboard (mark as not relevant, requires authentication)"""
    try:
        print(f"[DISMISS] Attempting to dismiss opportunity: {opportunity_id}")
        
        # Try to update in scraped_grants table (dashboard uses this)
        scraped_result = supabase.table("scraped_grants").update({
            "status": "dismissed"
        }).eq("id", opportunity_id).execute()
        
        print(f"[DISMISS] Scraped_grants update result: {len(scraped_result.data or []) > 0}")

        # If not found by id, try by opportunity_id field 
        if not scraped_result.data:
            scraped_alt_result = supabase.table("scraped_grants").update({
                "status": "dismissed" 
            }).eq("opportunity_id", opportunity_id).execute()
            
            print(f"[DISMISS] Scraped_grants alt update result: {len(scraped_alt_result.data or []) > 0}")
            
            if not scraped_alt_result.data:
                raise HTTPException(status_code=404, detail="Opportunity not found")

        print(f"[DISMISS] Successfully dismissed opportunity {opportunity_id}")
        return {
            "message": "Opportunity dismissed successfully",
            "status": "success",
            "opportunity_id": opportunity_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DISMISS] Error dismissing opportunity: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to dismiss opportunity: {str(e)}")

# NOTE: Duplicate /api/scraped-grants route removed — the authenticated version above handles this.
# The previous unauthenticated version was a security risk (exposed all grants without auth).

@app.post("/api/rfps/load")
async def load_rfps(user_id: str = Depends(get_current_user)):
    """Load RFPs from directory into database (admin endpoint, requires authentication)"""
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

@app.post("/api/rfps/upload")
async def upload_rfp(
    file: UploadFile = File(...),
    title: Optional[str] = None,
    funder: Optional[str] = None,
    deadline: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """Upload and analyze an RFP/grant document"""
    try:
        print(f"[RFP UPLOAD] Starting upload for user {user_id}")

        # Validate file is PDF
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        # Read file bytes
        file_bytes = await file.read()
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="File is empty")
        if len(file_bytes) > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(status_code=400, detail="File is too large (max 50MB)")

        print(f"[RFP UPLOAD] File size: {len(file_bytes)} bytes")

        # Extract text from PDF
        pdf_text = extract_text_from_pdf(file_bytes)
        if not pdf_text or len(pdf_text) < 50:
            raise HTTPException(status_code=400, detail="Could not extract meaningful text from PDF")

        print(f"[RFP UPLOAD] Extracted {len(pdf_text)} characters from PDF")

        # Analyze with Claude
        analyzed_data = await analyze_uploaded_rfp(pdf_text, title, funder, deadline)

        print(f"[RFP UPLOAD] Analysis complete: {analyzed_data.get('title')}")

        # Generate unique opportunity_id
        opportunity_id = f"user-upload-{uuid.uuid4()}"

        # Calculate match score (simple for now - will be enhanced based on org profile)
        match_score = 75  # Default score for user uploads

        # Prepare opportunity data for saving
        opportunity_data = {
            "opportunity_id": opportunity_id,
            "title": analyzed_data.get("title", title or "Uploaded RFP"),
            "description": analyzed_data.get("description", "User-uploaded grant opportunity"),
            "funder": analyzed_data.get("funder", funder or "Unknown"),
            "amount": parse_amount(analyzed_data.get("amount")),
            "deadline": analyzed_data.get("deadline", deadline),
            "requirements": analyzed_data.get("key_requirements", []),
            "tags": analyzed_data.get("tags", []),
            "source": "user_upload",
            "match_score": match_score,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "saved_at": datetime.now().isoformat(),
            "contact": "User uploaded document",
            "application_url": None,
            "embedding": None,
            "llm_summary": None,
            "detailed_match_reasoning": None,
            "winning_strategies": [],
            "key_themes": [],
            "recommended_metrics": [],
            "considerations": [],
            "similar_past_proposals": [],
            "status": "active"
        }

        # Save to database
        result = supabase_admin.table("saved_opportunities").insert(opportunity_data).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to save opportunity to database")

        print(f"[RFP UPLOAD] Successfully saved opportunity {opportunity_id}")

        # Return success response with analyzed data
        return {
            "message": "RFP uploaded and analyzed successfully",
            "title": analyzed_data.get("title", title or "Uploaded RFP"),
            "funder": analyzed_data.get("funder", funder or "Unknown"),
            "deadline": analyzed_data.get("deadline", deadline),
            "match_score": match_score,
            "llm_summary": analyzed_data.get("description", ""),
            "tags": analyzed_data.get("tags", []),
            "opportunity_id": opportunity_id
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[RFP UPLOAD] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/api/rfps/similar/{opportunity_id}")
async def get_similar_rfps(opportunity_id: str, user_id: str = Depends(get_current_user)):
    """Get similar RFPs for a saved opportunity using semantic search"""
    try:
        # Find opportunity in saved opportunities
        result = supabase.table("saved_opportunities").select("*").eq("opportunity_id", opportunity_id).eq("user_id", user_id).execute()

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

# Proposal routes moved to routes/proposals.py (Issue #37)

# Dashboard and analytics routes moved to routes/dashboard.py (Issue #37)

async def run_llm_enhancement(job_id: str, grant_id: str, user_id: str = None):
    """Background task for LLM enhancement with progress updates"""
    job = jobs_db[job_id]

    try:
        from llm_enhancement_service import enhance_and_save_grant

        # Update progress
        job["current_task"] = "Generating AI summary..."
        job["progress"] = 25

        # Run LLM enhancement with user_id for org-specific matching
        # Use admin client to bypass RLS and properly insert with user_id
        enhanced_grant = await enhance_and_save_grant(grant_id, supabase_admin, user_id)

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

async def run_opportunity_search(job_id: str, criteria: SearchCriteria, user_id: str = None):
    """Execute Claude Code fundraising-cro agent for opportunity discovery with org-aware matching"""
    print(f"[BACKGROUND TASK] Starting run_opportunity_search for job {job_id}, user {user_id}")
    job = jobs_db[job_id]

    try:
        print(f"[BACKGROUND TASK] Job found, current status: {job['status']}")
        # Update job status
        job["current_task"] = "Initializing fundraising-cro agent..."
        job["progress"] = 10

        # Get organization configuration
        org_config = await get_organization_config()

        # Build organization context from config
        programs_text = "\n".join([f"- {prog}" for prog in org_config.get("programs", ["Program 1", "Program 2"])])
        metrics = org_config.get("impact_metrics", {})
        metrics_text = "\n".join([f"- {k.replace('_', ' ').title()}: {v}" for k, v in metrics.items()])
        demographics_text = "\n".join([f"- {demo}" for demo in org_config.get("target_demographics", ["Diverse communities"])])

        organization_context = f"""
{org_config.get('name', 'Your Organization')} is a nonprofit organization dedicated to creating positive impact.

Mission: {org_config.get('mission', 'Advancing opportunity through education and community development.')}

Programs:
{programs_text}

Impact:
{metrics_text}

Target Demographics:
{demographics_text}
"""

        fundraising_prompt = f"""
I need you to find actual, current funding opportunities for {org_config.get('name', 'our organization')}.

Organization Context:
{organization_context}

User Search Request: {criteria.prompt}

Please execute your grant discovery protocol:
1. Search GRANTS.gov, NSF, DOL, and other federal databases for current opportunities
2. Find foundation grants from major funders
3. Look for corporate funding programs aligned with the organization's mission
4. Focus on opportunities that match {org_config.get('name', 'the organization')}'s mission and goals

For each opportunity found, provide:
- Title and funder organization
- Funding amount range
- Application deadline
- Match score (0-100) for fit based on mission alignment
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
                existing_result = supabase.table("saved_opportunities").select("title, funder").eq("user_id", user_id).execute()
                existing_opps = [f"{opp['title']} - {opp['funder']}" for opp in existing_result.data]
                existing_list = "; ".join(existing_opps) if existing_opps else "None"
            except Exception:
                existing_list = "None"

            # Create comprehensive prompt for fundraising-cro agent
            orchestration_prompt = f"""You are a fundraising-cro agent for {org_config.get('name', 'the organization')}. Find MULTIPLE (3-5) REAL, CURRENT funding opportunities using web search and research.

Organization Context:
{organization_context}

User Search Request: {criteria.prompt}

Execute this multi-step process:

1. Search current federal databases (GRANTS.gov, NSF, DOL) for relevant funding opportunities
2. Research foundation grants from major funders aligned with the organization's mission
3. Identify corporate funding programs supporting the organization's focus areas
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

            job["current_task"] = "Creating Gemini CLI fundraising session..."
            job["progress"] = 50

            # Create Gemini CLI session (with grants service fallback)
            print(f"[Gemini CLI Session] Starting fundraising opportunity discovery...")

            # Use grants service API if available, otherwise fall back to Gemini CLI
            use_api = False  # Set to False to use Gemini CLI instead

            if use_api:
                print(f"[Gemini CLI Session] Fetching real grants data...")
                search_keywords = criteria.prompt if criteria.prompt and criteria.prompt != "hi" else "technology workforce development"
                # Clean the search keywords - remove newlines and extra whitespace
                search_keywords = search_keywords.strip()
                print(f"[DEBUG] Search keywords: '{search_keywords}'")

                grants_service = GrantsGovService(supabase_client=supabase)
                # Pass user_id for organization-aware matching
                real_grants = grants_service.search_grants(search_keywords, limit=10, user_id=user_id)
                print(f"[DEBUG] Retrieved {len(real_grants)} real grants")
                orchestration_result = json.dumps({"opportunities": real_grants})
            else:
                session_result = create_gemini_cli_session(
                    prompt=orchestration_prompt,
                    session_type="fundraising",
                    timeout=900
                )

                if not session_result['success']:
                    raise Exception(f"Gemini CLI session failed: {session_result['error']}")

                orchestration_result = session_result['output']

            # Save raw response for debugging
            with open('/tmp/last_gemini_response.txt', 'w') as f:
                f.write(orchestration_result)
            print(f"[DEBUG] Saved raw Gemini response to /tmp/last_gemini_response.txt")

            job["current_task"] = "Processing fundraising session results..."
            job["progress"] = 80

            # Parse the orchestrated response
            opportunities = parse_orchestration_response(orchestration_result)

            # Score opportunities using match_scoring (Gemini is just a scraper)
            if opportunities and semantic_service:
                from match_scoring import calculate_match_score
                print(f"[SCORING] Scoring {len(opportunities)} opportunities from Gemini CLI agent...")

                for opp in opportunities:
                    try:
                        # Find similar RFPs for this opportunity
                        opp_text = f"{opp.get('title', '')} {opp.get('description', '')}"
                        similar_rfps = semantic_service.find_similar_rfps(opp_text, limit=5)

                        # Calculate real match score using similar RFPs (with feedback learning)
                        opportunity_id = opp.get('id') or opp.get('opportunity_id')
                        match_score = calculate_match_score(opp, similar_rfps, opportunity_id)
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

# run_proposal_generation and /api/proposals/{proposal_id}/download moved to routes/proposals.py (Issue #37)



if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT") or 8000)
    uvicorn.run(app, host="0.0.0.0", port=port)