"""
Organization routes - Config, documents, and user initialization
Extracted from main.py (Issue #37)
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import httpx
from auth_service import get_current_user
from credits_service import CreditsService

router = APIRouter(prefix="/api", tags=["organization"])

# Module-level dependencies (set via set_dependencies)
_supabase = None
_supabase_admin = None
_supabase_url = None
_supabase_service_role_key = None


def set_dependencies(supabase, supabase_admin, supabase_url: str, supabase_service_role_key: str):
    """Set dependencies from main app"""
    global _supabase, _supabase_admin, _supabase_url, _supabase_service_role_key
    _supabase = supabase
    _supabase_admin = supabase_admin
    _supabase_url = supabase_url
    _supabase_service_role_key = supabase_service_role_key


# ============================================
# Pydantic Models
# ============================================

class OrganizationConfigRequest(BaseModel):
    name: str
    mission: str
    focus_areas: Optional[List[str]] = None
    impact_metrics: Optional[Dict[str, Any]] = None
    programs: Optional[List[str]] = None
    target_demographics: Optional[List[str]] = None


class DocumentExtractRequest(BaseModel):
    document_ids: List[str]


class ApplyExtractionRequest(BaseModel):
    extracted_data: Dict[str, Any]
    resolved_conflicts: Optional[Dict[str, Any]] = None
    source_document_ids: List[str]


class OrganizationConfig(BaseModel):
    id: Optional[str] = None
    name: str
    mission: str
    focus_areas: List[str]
    impact_metrics: Dict[str, Any]
    programs: List[str]
    target_demographics: List[str]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class UserInitializationRequest(BaseModel):
    email: str
    organization_name: str
    mission: Optional[str] = None
    role: Optional[str] = "admin"


# ============================================
# Helper Functions
# ============================================

def _make_org_config_auth_headers():
    """Create authorization headers for service role access to Supabase API"""
    return {
        "Authorization": f"Bearer {_supabase_service_role_key}",
        "apikey": _supabase_service_role_key,
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }


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
        result = _supabase.table("organization_config").select("*").limit(1).execute()
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
        return get_default_organization_config()
    except Exception as e:
        print(f"[ORG CONFIG] Error fetching config: {e}")
        return get_default_organization_config()


# ============================================
# Auth Routes
# ============================================

@router.post("/auth/initialize")
async def initialize_user(request: UserInitializationRequest, user_id: str = Depends(get_current_user)):
    """Initialize user after signup - creates user record and organization"""
    try:
        # Check if user already exists in users table
        user_check = _supabase.table("users").select("id").eq("id", user_id).execute()

        if user_check.data and len(user_check.data) > 0:
            # User already initialized
            return {"status": "already_initialized", "message": "User already initialized"}

        # Create organization config for the new user
        org_data = {
            "name": request.organization_name,
            "mission": request.mission or "Advancing opportunity through education and community development",
            "focus_areas": [],
            "impact_metrics": {},
            "programs": [],
            "target_demographics": [],
            "owner_id": user_id
        }

        org_result = _supabase.table("organization_config").insert(org_data).execute()

        if not org_result.data:
            raise HTTPException(status_code=500, detail="Failed to create organization")

        org_id = org_result.data[0].get("id")

        # Create user record
        user_data = {
            "id": user_id,
            "email": request.email,
            "organization_id": org_id,
            "role": request.role or "admin"
        }

        user_result = _supabase.table("users").insert(user_data).execute()

        if not user_result.data:
            raise HTTPException(status_code=500, detail="Failed to create user record")

        # Initialize credits for new user (Free tier - 5 credits/month)
        credits_result = CreditsService.initialize_user_credits(user_id, plan="free")
        if not credits_result["success"]:
            print(f"[AUTH] Warning: Failed to initialize credits for user {user_id}: {credits_result.get('error')}")

        # Initialize workspace for the organization (agentic architecture)
        workspace_initialized = False
        try:
            from workspace_service import get_workspace_service
            ws = get_workspace_service()
            ws.init_workspace(org_id)
            ws.sync_profile_from_db(org_id, org_data)
            workspace_initialized = True
            print(f"[AUTH] Workspace initialized for org {org_id}")
        except Exception as ws_err:
            print(f"[AUTH] Warning: Failed to initialize workspace: {ws_err}")

        return {
            "status": "initialized",
            "user_id": user_id,
            "organization_id": org_id,
            "message": "User initialized successfully",
            "credits_initialized": credits_result.get("success", False),
            "workspace_initialized": workspace_initialized
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTH] Error initializing user: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize user: {str(e)}")


# ============================================
# Organization Config Routes
# ============================================

@router.get("/organization/config")
async def get_organization_configuration(user_id: str = Depends(get_current_user)):
    """Get current organization configuration for authenticated user"""
    try:
        headers = _make_org_config_auth_headers()

        # Get user's organization from users table
        with httpx.Client() as client:
            user_url = f"{_supabase_url}/rest/v1/users?select=organization_id,email&id=eq.{user_id}"
            user_response = client.get(user_url, headers=headers)

        user_data = user_response.json() if user_response.status_code == 200 else []
        
        # If user doesn't exist in users table, auto-initialize them
        if not user_data or len(user_data) == 0:
            print(f"[ORG CONFIG] User {user_id} not in users table, auto-initializing")
            # Get email from Supabase auth
            with httpx.Client() as client:
                auth_url = f"{_supabase_url}/auth/v1/user"
                auth_response = client.get(auth_url, headers={
                    "Authorization": f"Bearer {_supabase_service_role_key}",
                    "apikey": _supabase_service_role_key
                })
            
            email = "user@example.com"  # Default fallback
            if auth_response.status_code == 200:
                auth_data = auth_response.json()
                email = auth_data.get("email", email)
            
            # Auto-initialize the user
            org_data = {
                "name": "My Organization",
                "mission": "",
                "focus_areas": [],
                "impact_metrics": {},
                "programs": [],
                "target_demographics": [],
                "owner_id": user_id
            }
            
            with httpx.Client() as client:
                org_response = client.post(
                    f"{_supabase_url}/rest/v1/organization_config",
                    headers=headers,
                    json=org_data
                )
            
            if org_response.status_code not in [200, 201]:
                raise HTTPException(status_code=500, detail="Failed to auto-create organization")
            
            org_result = org_response.json()
            organization_id = org_result[0].get("id") if org_result else None
            
            if not organization_id:
                raise HTTPException(status_code=500, detail="Failed to get organization ID")
            
            # Create user record
            user_data_insert = {
                "id": user_id,
                "email": email,
                "organization_id": organization_id,
                "role": "admin"
            }
            
            with httpx.Client() as client:
                user_insert_response = client.post(
                    f"{_supabase_url}/rest/v1/users",
                    headers=headers,
                    json=user_data_insert
                )
            
            print(f"[ORG CONFIG] Auto-initialized user {user_id} with org {organization_id}")
            user_data = [{"organization_id": organization_id, "email": email}]
        
        organization_id = user_data[0].get("organization_id")

        if not organization_id:
            raise HTTPException(status_code=404, detail="User has no organization")

        # Get organization config
        with httpx.Client() as client:
            config_url = f"{_supabase_url}/rest/v1/organization_config?select=*&id=eq.{organization_id}"
            config_response = client.get(config_url, headers=headers)

        if config_response.status_code != 200:
            raise HTTPException(status_code=404, detail="Organization config not found")

        config_data = config_response.json()
        if not config_data:
            raise HTTPException(status_code=404, detail="Organization config not found")

        config = config_data[0]
        # Return all fields
        return {
            "id": config.get("id"),
            "name": config.get("name"),
            "mission": config.get("mission"),
            "ein": config.get("ein"),
            "organization_type": config.get("organization_type", "nonprofit"),
            "tax_exempt_status": config.get("tax_exempt_status", "pending"),
            "years_established": config.get("years_established"),
            "annual_budget": config.get("annual_budget"),
            "staff_size": config.get("staff_size"),
            "board_size": config.get("board_size"),
            "website_url": config.get("website_url"),
            "contact_email": config.get("contact_email"),
            "contact_phone": config.get("contact_phone"),
            "primary_focus_area": config.get("primary_focus_area", ""),
            "secondary_focus_areas": config.get("secondary_focus_areas", []),
            "focus_areas": config.get("focus_areas", []),
            "service_regions": config.get("service_regions", []),
            "languages_served": config.get("languages_served", ["English"]),
            "key_programs": config.get("key_programs", []),
            "programs": config.get("programs", []),
            "target_populations": config.get("target_populations", []),
            "target_demographics": config.get("target_demographics", []),
            "key_partnerships": config.get("key_partnerships", []),
            "accreditations": config.get("accreditations", []),
            "preferred_grant_size_min": config.get("preferred_grant_size_min"),
            "preferred_grant_size_max": config.get("preferred_grant_size_max"),
            "grant_writing_capacity": config.get("grant_writing_capacity", "moderate"),
            "key_impact_metrics": config.get("key_impact_metrics", []),
            "impact_metrics": config.get("impact_metrics", {}),
            "success_stories": config.get("success_stories", []),
            "previous_grants": config.get("previous_grants", []),
            "funding_priorities": config.get("funding_priorities", []),
            "custom_search_keywords": config.get("custom_search_keywords", []),
            "excluded_keywords": config.get("excluded_keywords", []),
            "expansion_plans": config.get("expansion_plans"),
            "donor_restrictions": config.get("donor_restrictions"),
            "matching_fund_capacity": config.get("matching_fund_capacity", 0),
            "created_at": config.get("created_at"),
            "updated_at": config.get("updated_at")
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ORG CONFIG] Error getting config: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving configuration")


@router.post("/organization/config")
async def save_organization_configuration(config_request: OrganizationConfigRequest, user_id: str = Depends(get_current_user)):
    """Save or update organization configuration for authenticated user"""
    print(f"[ORG CONFIG POST] Handler called with user: {user_id}, config: {config_request}")
    try:
        headers = _make_org_config_auth_headers()

        # Get user's organization
        with httpx.Client() as client:
            user_url = f"{_supabase_url}/rest/v1/users?select=organization_id&id=eq.{user_id}"
            user_response = client.get(user_url, headers=headers)

        if user_response.status_code != 200:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = user_response.json()
        if not user_data or len(user_data) == 0:
            raise HTTPException(status_code=404, detail="User not found")

        organization_id = user_data[0].get("organization_id")

        config_data = {
            "name": config_request.name,
            "mission": config_request.mission,
            "focus_areas": config_request.focus_areas or [],
            "impact_metrics": config_request.impact_metrics or {},
            "programs": config_request.programs or [],
            "target_demographics": config_request.target_demographics or []
        }

        if organization_id:
            # Update existing config
            with httpx.Client() as client:
                update_response = client.patch(
                    f"{_supabase_url}/rest/v1/organization_config?id=eq.{organization_id}",
                    headers=headers,
                    json=config_data
                )

            if update_response.status_code in [200, 204]:
                # Fetch updated config to return
                with httpx.Client() as client:
                    fetch_response = client.get(
                        f"{_supabase_url}/rest/v1/organization_config?select=*&id=eq.{organization_id}",
                        headers=headers
                    )

                if fetch_response.status_code == 200:
                    config_list = fetch_response.json()
                    if config_list:
                        saved_config = config_list[0]
                        # Sync to workspace
                        try:
                            from workspace_service import get_workspace_service
                            ws = get_workspace_service()
                            ws.sync_profile_from_db(organization_id, saved_config)
                        except Exception as ws_err:
                            print(f"[ORG CONFIG] Workspace sync failed: {ws_err}")
                        return {
                            "status": "updated",
                            "id": saved_config.get("id"),
                            "name": saved_config.get("name"),
                            "mission": saved_config.get("mission"),
                            "focus_areas": saved_config.get("focus_areas"),
                            "impact_metrics": saved_config.get("impact_metrics"),
                            "programs": saved_config.get("programs"),
                            "target_demographics": saved_config.get("target_demographics"),
                            "updated_at": saved_config.get("updated_at")
                        }
        else:
            # Create new config
            config_data["owner_id"] = user_id
            with httpx.Client() as client:
                insert_response = client.post(
                    f"{_supabase_url}/rest/v1/organization_config",
                    headers=headers,
                    json=config_data
                )

            if insert_response.status_code in [200, 201]:
                insert_data = insert_response.json()
                if insert_data and len(insert_data) > 0:
                    saved_config = insert_data[0]
                    org_id = saved_config.get("id")

                    # Link user to organization
                    with httpx.Client() as client:
                        user_update = client.patch(
                            f"{_supabase_url}/rest/v1/users?id=eq.{user_id}",
                            headers=headers,
                            json={"organization_id": org_id}
                        )

                    # Init workspace for new org
                    try:
                        from workspace_service import get_workspace_service
                        ws = get_workspace_service()
                        ws.init_workspace(org_id)
                        ws.sync_profile_from_db(org_id, saved_config)
                    except Exception as ws_err:
                        print(f"[ORG CONFIG] Workspace init failed: {ws_err}")

                    return {
                        "status": "created",
                        "id": saved_config.get("id"),
                        "name": saved_config.get("name"),
                        "mission": saved_config.get("mission"),
                        "focus_areas": saved_config.get("focus_areas"),
                        "impact_metrics": saved_config.get("impact_metrics"),
                        "programs": saved_config.get("programs"),
                        "target_demographics": saved_config.get("target_demographics"),
                        "created_at": saved_config.get("created_at")
                    }

        raise HTTPException(status_code=500, detail="Failed to save configuration")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ORG CONFIG] Error saving: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save organization configuration: {str(e)}")


# ============================================
# Organization Document Routes
# ============================================

@router.post("/organization/documents/upload")
async def upload_organization_documents(
    files: List[UploadFile] = File(...),
    user_id: str = Depends(get_current_user)
):
    """Upload organization documents for LLM extraction."""
    from document_extraction_service import DocumentExtractionService
    from supabase import create_client, Client

    try:
        headers = _make_org_config_auth_headers()

        # Get user's organization
        with httpx.Client() as client:
            user_url = f"{_supabase_url}/rest/v1/users?select=organization_id&id=eq.{user_id}"
            user_response = client.get(user_url, headers=headers)

        if user_response.status_code != 200:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = user_response.json()
        if not user_data or len(user_data) == 0:
            raise HTTPException(status_code=404, detail="User not found")

        organization_id = user_data[0].get("organization_id")
        if not organization_id:
            raise HTTPException(status_code=400, detail="User has no organization. Please create organization profile first.")

        # Initialize supabase client for document service
        supabase: Client = create_client(_supabase_url, _supabase_service_role_key)
        doc_service = DocumentExtractionService(supabase)

        uploaded_docs = []
        allowed_types = {'pdf', 'docx', 'txt'}

        for file in files:
            # Validate file type
            file_ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
            if file_ext not in allowed_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {file_ext}. Allowed: PDF, DOCX, TXT"
                )

            # Read file content
            file_bytes = await file.read()
            file_size = len(file_bytes)

            # Check file size (max 50MB)
            if file_size > 50 * 1024 * 1024:
                raise HTTPException(status_code=400, detail=f"File {file.filename} exceeds 50MB limit")

            # Extract text
            try:
                extracted_text = doc_service.extract_text(file_bytes, file_ext)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to extract text from {file.filename}: {str(e)}")

            # Upload to Supabase storage
            storage_path = f"{organization_id}/{uuid.uuid4()}.{file_ext}"
            try:
                supabase.storage.from_('org-documents').upload(storage_path, file_bytes)
            except Exception as e:
                print(f"[DOC UPLOAD] Storage error: {e}")
                # Continue without storage - we have the text
                storage_path = f"extraction-only/{uuid.uuid4()}"

            # Save document record
            doc_record = await doc_service.save_document(
                organization_id=organization_id,
                filename=file.filename,
                file_type=file_ext,
                file_size=file_size,
                storage_path=storage_path,
                extracted_text=extracted_text
            )

            uploaded_docs.append({
                'id': doc_record['id'] if doc_record else None,
                'filename': file.filename,
                'file_type': file_ext,
                'file_size': file_size,
                'text_length': len(extracted_text)
            })

        return {
            'status': 'success',
            'uploaded': uploaded_docs,
            'count': len(uploaded_docs)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[DOC UPLOAD] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload documents: {str(e)}")


@router.post("/organization/documents/extract")
async def extract_organization_info(
    request: DocumentExtractRequest,
    user_id: str = Depends(get_current_user)
):
    """Extract organization info from uploaded documents using LLM."""
    from document_extraction_service import DocumentExtractionService
    from supabase import create_client, Client

    try:
        headers = _make_org_config_auth_headers()

        # Get user's organization
        with httpx.Client() as client:
            user_url = f"{_supabase_url}/rest/v1/users?select=organization_id&id=eq.{user_id}"
            user_response = client.get(user_url, headers=headers)

        if user_response.status_code != 200:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = user_response.json()
        organization_id = user_data[0].get("organization_id") if user_data else None

        if not organization_id:
            raise HTTPException(status_code=400, detail="User has no organization")

        # Initialize services
        supabase: Client = create_client(_supabase_url, _supabase_service_role_key)
        doc_service = DocumentExtractionService(supabase)

        # Get documents
        documents = []
        for doc_id in request.document_ids:
            result = supabase.table('organization_documents')\
                .select('filename, extracted_text')\
                .eq('id', doc_id)\
                .eq('organization_id', organization_id)\
                .execute()

            if result.data:
                doc = result.data[0]
                if doc.get('extracted_text'):
                    documents.append({
                        'filename': doc['filename'],
                        'text': doc['extracted_text']
                    })

        if not documents:
            raise HTTPException(status_code=400, detail="No valid documents found for extraction")

        # Extract organization info using LLM
        extraction_result = await doc_service.extract_organization_info(documents)

        if extraction_result.get('error'):
            raise HTTPException(status_code=500, detail=extraction_result['error'])

        # Get existing profile for smart merge
        with httpx.Client() as client:
            config_url = f"{_supabase_url}/rest/v1/organization_config?select=*&id=eq.{organization_id}"
            config_response = client.get(config_url, headers=headers)

        existing_profile = {}
        if config_response.status_code == 200:
            config_data = config_response.json()
            if config_data:
                existing_profile = config_data[0]

        # Smart merge
        merge_result = doc_service.smart_merge(
            existing_profile=existing_profile,
            extracted=extraction_result.get('extracted', {}),
            confidence=extraction_result.get('confidence', {})
        )

        return {
            'status': 'success',
            'extracted': extraction_result.get('extracted', {}),
            'confidence': extraction_result.get('confidence', {}),
            'merge_preview': {
                'new_fields': merge_result['new_fields'],
                'conflicts': merge_result['conflicts'],
                'unchanged': merge_result['unchanged']
            },
            'source_documents': extraction_result.get('source_documents', [])
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[DOC EXTRACT] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to extract organization info: {str(e)}")


@router.post("/organization/documents/apply")
async def apply_extracted_data(
    request: ApplyExtractionRequest,
    user_id: str = Depends(get_current_user)
):
    """Apply extracted data to organization profile with conflict resolution."""
    from document_extraction_service import DocumentExtractionService
    from supabase import create_client, Client

    try:
        headers = _make_org_config_auth_headers()

        # Get user's organization
        with httpx.Client() as client:
            user_url = f"{_supabase_url}/rest/v1/users?select=organization_id&id=eq.{user_id}"
            user_response = client.get(user_url, headers=headers)

        if user_response.status_code != 200:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = user_response.json()
        organization_id = user_data[0].get("organization_id") if user_data else None

        if not organization_id:
            raise HTTPException(status_code=400, detail="User has no organization")

        # Build update data from extracted + resolved conflicts
        update_data = {**request.extracted_data}
        if request.resolved_conflicts:
            update_data.update(request.resolved_conflicts)

        # Map extracted field names to database column names
        field_mapping = {
            'organization_name': 'name',
            'mission_statement': 'mission',
            'description': 'mission',
            'areas_of_focus': 'focus_areas',
            'key_programs': 'programs',
            'target_population': 'target_demographics',
            'target_populations': 'target_demographics',
            'demographics': 'target_demographics',
            'metrics': 'impact_metrics',
        }

        # Apply field mapping
        mapped_data = {}
        for k, v in update_data.items():
            if v is not None:
                mapped_key = field_mapping.get(k, k)
                mapped_data[mapped_key] = v

        # Valid columns in organization_config table (all fields)
        valid_columns = {
            'name', 'mission', 'focus_areas', 'impact_metrics', 'programs', 'target_demographics',
            'ein', 'organization_type', 'tax_exempt_status', 'years_established', 'annual_budget',
            'staff_size', 'board_size', 'website_url', 'contact_email', 'contact_phone',
            'primary_focus_area', 'secondary_focus_areas', 'service_regions', 'languages_served',
            'key_programs', 'target_populations', 'key_partnerships', 'accreditations',
            'preferred_grant_size_min', 'preferred_grant_size_max', 'grant_writing_capacity',
            'key_impact_metrics', 'success_stories', 'previous_grants', 'funding_priorities',
            'custom_search_keywords', 'excluded_keywords', 'expansion_plans', 'donor_restrictions',
            'matching_fund_capacity'
        }

        # Filter to valid columns only
        update_data = {k: v for k, v in mapped_data.items() if k in valid_columns}

        print(f"[APPLY] Updating org {organization_id} with: {update_data}")

        # Update organization config
        with httpx.Client() as client:
            update_response = client.patch(
                f"{_supabase_url}/rest/v1/organization_config?id=eq.{organization_id}",
                headers=headers,
                json=update_data
            )

        if update_response.status_code not in [200, 204]:
            raise HTTPException(status_code=500, detail="Failed to update organization profile")

        # Save extraction history
        supabase: Client = create_client(_supabase_url, _supabase_service_role_key)
        doc_service = DocumentExtractionService(supabase)
        await doc_service.save_extraction_history(
            organization_id=organization_id,
            extracted_data=request.extracted_data,
            source_document_ids=request.source_document_ids,
            confidence_scores={},
            applied=True
        )

        # Fetch and return updated profile
        with httpx.Client() as client:
            fetch_response = client.get(
                f"{_supabase_url}/rest/v1/organization_config?select=*&id=eq.{organization_id}",
                headers=headers
            )

        if fetch_response.status_code == 200:
            config_data = fetch_response.json()
            if config_data:
                return {
                    'status': 'success',
                    'message': 'Organization profile updated from documents',
                    'profile': config_data[0]
                }

        return {'status': 'success', 'message': 'Organization profile updated'}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[DOC APPLY] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to apply extracted data: {str(e)}")


@router.get("/organization/documents")
async def list_organization_documents(user_id: str = Depends(get_current_user)):
    """List all uploaded documents for user's organization."""
    from document_extraction_service import DocumentExtractionService
    from supabase import create_client, Client

    try:
        headers = _make_org_config_auth_headers()

        # Get user's organization
        with httpx.Client() as client:
            user_url = f"{_supabase_url}/rest/v1/users?select=organization_id&id=eq.{user_id}"
            user_response = client.get(user_url, headers=headers)

        if user_response.status_code != 200:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = user_response.json()
        organization_id = user_data[0].get("organization_id") if user_data else None

        if not organization_id:
            return {'documents': [], 'count': 0}

        supabase: Client = create_client(_supabase_url, _supabase_service_role_key)
        doc_service = DocumentExtractionService(supabase)

        documents = await doc_service.get_organization_documents(organization_id)

        return {
            'documents': documents,
            'count': len(documents)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[DOC LIST] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@router.delete("/organization/documents/{document_id}")
async def delete_organization_document(
    document_id: str,
    user_id: str = Depends(get_current_user)
):
    """Delete a document from user's organization."""
    from document_extraction_service import DocumentExtractionService
    from supabase import create_client, Client

    try:
        headers = _make_org_config_auth_headers()

        # Get user's organization
        with httpx.Client() as client:
            user_url = f"{_supabase_url}/rest/v1/users?select=organization_id&id=eq.{user_id}"
            user_response = client.get(user_url, headers=headers)

        if user_response.status_code != 200:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = user_response.json()
        organization_id = user_data[0].get("organization_id") if user_data else None

        if not organization_id:
            raise HTTPException(status_code=400, detail="User has no organization")

        supabase: Client = create_client(_supabase_url, _supabase_service_role_key)
        doc_service = DocumentExtractionService(supabase)

        deleted = await doc_service.delete_document(document_id, organization_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Document not found")

        return {'status': 'success', 'message': 'Document deleted'}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[DOC DELETE] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


@router.get("/organization/match-profile")
async def get_organization_match_profile(user_id: str = Depends(get_current_user)):
    """
    Return the organization's current matching profile — active search keywords,
    scoring weights, and excluded keywords. Lets users understand how grant
    discovery is personalized for their org.
    """
    try:
        from organization_matching_service import OrganizationMatchingService
        matching_service = OrganizationMatchingService(_supabase)
        org_profile = await matching_service.get_organization_profile(user_id)

        if not org_profile:
            return {
                "status": "no_profile",
                "message": "Complete your organization profile in Settings to enable personalized grant matching.",
                "primary_keywords": [],
                "secondary_keywords": [],
                "excluded_keywords": [],
                "scoring_weights": {},
                "matching_summary": {}
            }

        primary_keywords, secondary_keywords = matching_service.build_search_keywords(org_profile)
        scoring_weights = matching_service.get_matching_score_weights(org_profile)
        matching_summary = matching_service.get_matching_summary(org_profile)

        excluded_keywords = org_profile.get("excluded_keywords") or []
        if isinstance(excluded_keywords, str):
            import json
            try:
                excluded_keywords = json.loads(excluded_keywords)
            except Exception:
                excluded_keywords = []

        return {
            "status": "active",
            "organization_name": org_profile.get("name"),
            "primary_focus": org_profile.get("primary_focus_area"),
            "primary_keywords": primary_keywords,
            "secondary_keywords": secondary_keywords[:20],  # Cap for readability
            "excluded_keywords": excluded_keywords,
            "scoring_weights": scoring_weights,
            "preferred_grant_range": {
                "min": org_profile.get("preferred_grant_size_min"),
                "max": org_profile.get("preferred_grant_size_max"),
            },
            "grant_writing_capacity": org_profile.get("grant_writing_capacity", "moderate"),
            "target_populations": org_profile.get("target_populations", []),
            "service_regions": org_profile.get("service_regions", []),
            "matching_summary": matching_summary
        }

    except Exception as e:
        print(f"[MATCH PROFILE] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load match profile: {str(e)}")


# ============================================
# Notification Preferences
# ============================================

class NotificationPreferencesUpdate(BaseModel):
    deadline_alerts_enabled: Optional[bool] = None
    deadline_alert_days: Optional[List[int]] = None
    morning_briefs_enabled: Optional[bool] = None
    email_notifications_enabled: Optional[bool] = None


DEFAULT_NOTIFICATION_PREFERENCES = {
    "deadline_alerts_enabled": True,
    "deadline_alert_days": [2, 7, 30],
    "morning_briefs_enabled": True,
    "email_notifications_enabled": True
}


async def _get_org_id_for_user(user_id: str) -> Optional[int]:
    """Get org ID for the authenticated user"""
    try:
        result = _supabase.table("users").select("organization_id").eq("id", user_id).limit(1).execute()
        if result.data and result.data[0].get("organization_id"):
            return int(result.data[0]["organization_id"])
    except Exception as e:
        print(f"[NOTIF PREFS] Error getting org_id: {e}")
    return None


@router.get("/organization/notification-preferences")
async def get_notification_preferences(user_id: str = Depends(get_current_user)):
    """
    Get the organization's notification preferences.
    Returns default preferences if none are set.
    """
    try:
        org_id = await _get_org_id_for_user(user_id)
        if not org_id:
            return {
                "status": "no_org",
                "preferences": DEFAULT_NOTIFICATION_PREFERENCES,
                "message": "Using default preferences (no organization found)"
            }

        result = _supabase.table("organization_config") \
            .select("notification_preferences") \
            .eq("id", org_id) \
            .limit(1) \
            .execute()

        if result.data and result.data[0].get("notification_preferences"):
            prefs = result.data[0]["notification_preferences"]
            # Merge with defaults for any missing keys
            merged = {**DEFAULT_NOTIFICATION_PREFERENCES, **prefs}
            return {
                "status": "ok",
                "org_id": org_id,
                "preferences": merged
            }
        else:
            return {
                "status": "defaults",
                "org_id": org_id,
                "preferences": DEFAULT_NOTIFICATION_PREFERENCES,
                "message": "Using default preferences"
            }

    except Exception as e:
        print(f"[NOTIF PREFS] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load notification preferences: {str(e)}")


@router.patch("/organization/notification-preferences")
async def update_notification_preferences(
    updates: NotificationPreferencesUpdate,
    user_id: str = Depends(get_current_user)
):
    """
    Update the organization's notification preferences.
    Partial updates supported — only provided fields are changed.
    
    Fields:
      - deadline_alerts_enabled: bool — enable/disable deadline alert emails
      - deadline_alert_days: list[int] — which days to alert (e.g., [2, 7, 30])
      - morning_briefs_enabled: bool — enable/disable morning brief emails
      - email_notifications_enabled: bool — master toggle for all email notifications
    """
    try:
        org_id = await _get_org_id_for_user(user_id)
        if not org_id:
            raise HTTPException(status_code=400, detail="User has no organization")

        # Get current preferences
        result = _supabase.table("organization_config") \
            .select("notification_preferences") \
            .eq("id", org_id) \
            .limit(1) \
            .execute()

        current_prefs = DEFAULT_NOTIFICATION_PREFERENCES.copy()
        if result.data and result.data[0].get("notification_preferences"):
            current_prefs.update(result.data[0]["notification_preferences"])

        # Apply updates
        update_dict = updates.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            if value is not None:
                current_prefs[key] = value

        # Validate deadline_alert_days
        if "deadline_alert_days" in update_dict:
            days = update_dict["deadline_alert_days"]
            if not isinstance(days, list) or not all(isinstance(d, int) and d > 0 for d in days):
                raise HTTPException(
                    status_code=400,
                    detail="deadline_alert_days must be a list of positive integers"
                )
            # Sort and dedupe
            current_prefs["deadline_alert_days"] = sorted(set(days))

        # Save
        update_result = _supabase.table("organization_config") \
            .update({"notification_preferences": current_prefs}) \
            .eq("id", org_id) \
            .execute()

        if not update_result.data:
            raise HTTPException(status_code=404, detail="Organization not found")

        print(f"[NOTIF PREFS] Updated preferences for org {org_id}: {current_prefs}")

        return {
            "status": "updated",
            "org_id": org_id,
            "preferences": current_prefs
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[NOTIF PREFS] Update error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update notification preferences: {str(e)}")
