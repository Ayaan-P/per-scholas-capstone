"""
RFPs routes - Issue #37 (main.py split)
Extracted: RFP loading, uploading, and similarity search

Routes:
- POST /api/rfps/load - Load RFPs from directory into database
- POST /api/rfps/upload - Upload and analyze an RFP document
- GET /api/rfps/similar/{opportunity_id} - Get similar RFPs for an opportunity
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import Optional, Dict, Any
from auth_service import get_current_user
from datetime import datetime
import uuid
import os
import json
import PyPDF2
import io
import google.generativeai as genai

router = APIRouter(prefix="/api/rfps", tags=["rfps"])

# Dependencies injected from main.py
_supabase = None
_supabase_admin = None
_semantic_service = None


def set_dependencies(supabase, supabase_admin, semantic_service=None):
    """Inject dependencies from main.py"""
    global _supabase, _supabase_admin, _semantic_service
    _supabase = supabase
    _supabase_admin = supabase_admin
    _semantic_service = semantic_service


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text content from a PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"[PDF EXTRACT] Error: {e}")
        return ""


def parse_amount(amount_text: Any) -> Optional[int]:
    """Parse amount text to integer"""
    if amount_text is None:
        return None
    if isinstance(amount_text, (int, float)):
        return int(amount_text)
    if isinstance(amount_text, str):
        # Remove common formatting
        cleaned = amount_text.replace('$', '').replace(',', '').replace(' ', '')
        # Handle ranges (take the max)
        if '-' in cleaned:
            parts = cleaned.split('-')
            cleaned = parts[-1]  # Take the higher value
        try:
            return int(float(cleaned))
        except (ValueError, TypeError):
            return None
    return None


async def analyze_uploaded_rfp(pdf_text: str, title: Optional[str] = None, funder: Optional[str] = None, deadline: Optional[str] = None) -> Dict[str, Any]:
    """Use Gemini to analyze an uploaded RFP document"""
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_key:
        # Return basic extracted info without AI analysis
        return {
            "title": title or "Uploaded RFP",
            "funder": funder or "Unknown",
            "deadline": deadline,
            "description": pdf_text[:2000] + "..." if len(pdf_text) > 2000 else pdf_text,
            "amount": None,
            "key_requirements": [],
            "tags": ["user-uploaded"]
        }

    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel('gemini-3-flash-preview')

    prompt = f"""Analyze this grant/RFP document and extract key information.

Document text:
{pdf_text[:15000]}

{'Title hint: ' + title if title else ''}
{'Funder hint: ' + funder if funder else ''}
{'Deadline hint: ' + deadline if deadline else ''}

Extract and return as JSON:
{{
    "title": "Full title of the grant/RFP",
    "funder": "Organization offering the grant",
    "deadline": "Application deadline (YYYY-MM-DD format if possible)",
    "amount": "Funding amount (number only, no symbols)",
    "description": "2-3 sentence summary of what this grant funds",
    "key_requirements": ["List of 3-5 key eligibility or application requirements"],
    "tags": ["List of 3-5 relevant category tags"]
}}

Return ONLY valid JSON, no other text."""

    try:
        response = model.generate_content(prompt)
        result_text = response.text

        # Try to parse JSON
        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{[^{}]*\}', result_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
            # Fallback to basic extraction
            return {
                "title": title or "Uploaded RFP",
                "funder": funder or "Unknown",
                "deadline": deadline,
                "description": result_text[:500],
                "amount": None,
                "key_requirements": [],
                "tags": ["user-uploaded"]
            }
    except Exception as e:
        print(f"[ANALYZE RFP] Error: {e}")
        return {
            "title": title or "Uploaded RFP",
            "funder": funder or "Unknown",
            "deadline": deadline,
            "description": "RFP document uploaded by user",
            "tags": ["user-uploaded"],
            "key_requirements": []
        }


@router.post("/load")
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


@router.post("/upload")
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
        result = _supabase_admin.table("saved_opportunities").insert(opportunity_data).execute()

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


@router.get("/similar/{opportunity_id}")
async def get_similar_rfps(opportunity_id: str, user_id: str = Depends(get_current_user)):
    """Get similar RFPs for a saved opportunity using semantic search"""
    try:
        # Find opportunity in saved opportunities
        result = _supabase.table("saved_opportunities").select("*").eq("opportunity_id", opportunity_id).eq("user_id", user_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Saved opportunity not found")

        opportunity = result.data[0]
        opportunity_text = f"{opportunity['title']} {opportunity['description']}"

        # Find similar RFPs using semantic service
        similar_rfps = []
        if _semantic_service:
            try:
                similar_rfps = _semantic_service.find_similar_rfps(opportunity_text, limit=5)

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
