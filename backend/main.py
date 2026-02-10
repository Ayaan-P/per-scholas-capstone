
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
from routes.grants import router as grants_router, set_dependencies as set_grants_deps
from routes.rfps import router as rfps_router, set_dependencies as set_rfps_deps
from routes.opportunities import router as opportunities_router, set_dependencies as set_opportunities_deps
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
app.include_router(grants_router)
app.include_router(rfps_router)
app.include_router(opportunities_router)

# In-memory job tracking (database for persistence)
jobs_db: Dict[str, Dict[str, Any]] = {}
opportunities_db: List[Dict[str, Any]] = []

# SearchRequest, SearchCriteria, JobStatus, FeedbackRequest, UpdateOpportunityDescriptionRequest,
# UpdateOpportunityNotesRequest moved to routes/opportunities.py (Issue #37)
# ProposalRequest moved to routes/proposals.py (Issue #37)

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
    
    # Grants routes (Issue #37)
    set_grants_deps(supabase, supabase_admin, jobs_db)
    print("[STARTUP] Grants routes configured")
    
    # RFPs routes (Issue #37)
    set_rfps_deps(supabase, supabase_admin, semantic_service)
    print("[STARTUP] RFPs routes configured")
    
    # Opportunities routes (Issue #37)
    from grants_service import GrantsGovService
    set_opportunities_deps(
        supabase, supabase_admin, jobs_db, opportunities_db,
        semantic_service, create_gemini_cli_session, parse_orchestration_response,
        get_organization_config, GrantsGovService
    )
    print("[STARTUP] Opportunities routes configured")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop scheduler on shutdown"""
    if scheduler_service:
        scheduler_service.stop()

# Health and scheduler routes moved to routes/health.py and routes/scheduler.py (Issue #37)
# Opportunities routes (search, jobs, save, feedback, dismiss) moved to routes/opportunities.py (Issue #37)


# Note: All code below was moved to routes/opportunities.py (Issue #37)
# Including: start_opportunity_search, get_job_status, get_opportunities,
# generate_opportunity_summary, save_opportunity, update_opportunity_description,
# update_opportunity_notes, delete_opportunity, add_opportunity_to_rfp_database,
# submit_opportunity_feedback, get_opportunity_feedback, dismiss_opportunity,
# get_opportunity_feedback_counts, run_opportunity_search

# Proposal routes moved to routes/proposals.py (Issue #37)


# The old code has been removed. See routes/opportunities.py for the refactored implementation.

# --- LEGACY CODE REMOVED ---
# All opportunities routes (search, jobs, save, feedback, dismiss) moved to routes/opportunities.py (Issue #37)
# run_opportunity_search also moved to routes/opportunities.py

# run_proposal_generation and /api/proposals/{proposal_id}/download moved to routes/proposals.py (Issue #37)



if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT") or 8000)
    uvicorn.run(app, host="0.0.0.0", port=port)