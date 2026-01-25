"""
Document Extraction Service

Extracts structured organization profile data from uploaded documents (PDF, DOCX, TXT)
using LLM analysis. Supports smart merge with existing profile data.
"""

import os
import io
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from supabase import Client
from dotenv import load_dotenv

load_dotenv()


class DocumentExtractionService:
    """Extract organization info from uploaded documents."""

    # Valid field options for validation
    ORGANIZATION_TYPES = ['nonprofit', 'social-enterprise', 'government', 'educational-institution', 'faith-based', 'community-based', 'other']
    TAX_EXEMPT_STATUSES = ['pending', '501c3', '501c6', '501c7', 'other', 'none']
    GRANT_WRITING_CAPACITIES = ['limited', 'moderate', 'advanced']
    FOCUS_AREAS = ['education', 'health', 'environment', 'social-services', 'arts-culture', 'economic-development', 'housing', 'youth-development', 'workforce-development', 'community-development', 'technology', 'civil-rights', 'other']

    def __init__(self, supabase: Client):
        self.supabase = supabase

        # Initialize Gemini
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not set")

        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-3-flash-preview')

        print("[DOC EXTRACTION] Service initialized")

    def extract_text_from_pdf(self, file_bytes: bytes) -> str:
        """Extract text from PDF file."""
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text.strip()
        except Exception as e:
            print(f"[DOC EXTRACTION] PDF extraction error: {e}")
            raise ValueError(f"Failed to extract text from PDF: {e}")

    def extract_text_from_docx(self, file_bytes: bytes) -> str:
        """Extract text from DOCX file."""
        try:
            doc = Document(io.BytesIO(file_bytes))
            text = "\n".join([para.text for para in doc.paragraphs])
            return text.strip()
        except Exception as e:
            print(f"[DOC EXTRACTION] DOCX extraction error: {e}")
            raise ValueError(f"Failed to extract text from DOCX: {e}")

    def extract_text_from_txt(self, file_bytes: bytes) -> str:
        """Extract text from TXT file."""
        try:
            return file_bytes.decode('utf-8').strip()
        except UnicodeDecodeError:
            try:
                return file_bytes.decode('latin-1').strip()
            except Exception as e:
                print(f"[DOC EXTRACTION] TXT extraction error: {e}")
                raise ValueError(f"Failed to extract text from TXT: {e}")

    def extract_text(self, file_bytes: bytes, file_type: str) -> str:
        """Extract text from file based on type."""
        extractors = {
            'pdf': self.extract_text_from_pdf,
            'docx': self.extract_text_from_docx,
            'txt': self.extract_text_from_txt,
        }

        extractor = extractors.get(file_type.lower())
        if not extractor:
            raise ValueError(f"Unsupported file type: {file_type}")

        return extractor(file_bytes)

    async def extract_organization_info(self, documents: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Extract organization info from multiple documents using LLM.

        Args:
            documents: List of dicts with 'filename' and 'text' keys

        Returns:
            Dict with extracted fields and confidence scores
        """
        # Combine document texts
        combined_text = ""
        for doc in documents:
            combined_text += f"\n\n=== {doc['filename']} ===\n{doc['text'][:15000]}"  # Limit each doc

        # Truncate total if needed
        if len(combined_text) > 50000:
            combined_text = combined_text[:50000] + "\n...(truncated)"

        prompt = f"""Analyze these organization documents and extract structured information.
Return ONLY valid JSON with this exact structure (use null for fields you cannot determine):

{{
  "extracted": {{
    "name": "Organization legal name",
    "ein": "EIN/tax ID (format: XX-XXXXXXX)",
    "organization_type": "One of: nonprofit, social-enterprise, government, educational-institution, faith-based, community-based, other",
    "tax_exempt_status": "One of: pending, 501c3, 501c6, 501c7, other, none",
    "years_established": 2000,
    "annual_budget": 5000000,
    "staff_size": 50,
    "board_size": 12,
    "website_url": "https://example.org",
    "contact_email": "info@example.org",
    "contact_phone": "(555) 123-4567",

    "mission": "Full mission statement as written in documents",
    "primary_focus_area": "One of: education, health, environment, social-services, arts-culture, economic-development, housing, youth-development, workforce-development, community-development, technology, civil-rights, other",
    "secondary_focus_areas": ["array", "of", "focus", "areas"],
    "service_regions": ["geographic", "areas", "served"],
    "languages_served": ["English", "Spanish"],

    "key_programs": [
      {{"name": "Program name", "description": "What it does", "beneficiaries": "Who it serves"}}
    ],
    "target_populations": ["K-12 students", "unemployed adults"],
    "key_partnerships": [{{"partner": "Partner name", "type": "funding/programmatic/referral"}}],
    "accreditations": ["List of certifications"],

    "preferred_grant_size_min": 10000,
    "preferred_grant_size_max": 500000,
    "grant_writing_capacity": "One of: limited, moderate, advanced",

    "key_impact_metrics": [
      {{"metric_name": "Job placements", "current_value": "500", "target_value": "750", "unit": "per year"}}
    ],
    "success_stories": [
      {{"title": "Story title", "description": "Brief success story"}}
    ],
    "previous_grants": [
      {{"funder": "Funder name", "amount": 100000, "year": 2023, "outcome": "Successfully completed"}}
    ]
  }},
  "confidence": {{
    "name": 0.95,
    "ein": 0.90,
    "mission": 0.85,
    "annual_budget": 0.70
  }}
}}

For each field in "extracted", also provide a confidence score (0.0-1.0) in "confidence" based on how clearly the information was stated.
Only include confidence scores for fields you actually extracted (not null).

Documents to analyze:
{combined_text}

IMPORTANT:
- Use exact values from documents when possible
- For budget/amounts, extract as numbers without formatting
- For years_established, extract just the 4-digit year
- Match organization_type and tax_exempt_status to the allowed values exactly
- If a field has multiple possible values, choose the most authoritative source"""

        try:
            response = self.model.generate_content(prompt)

            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())

                # Validate and normalize extracted fields
                extracted = result.get('extracted', {})
                confidence = result.get('confidence', {})

                # Normalize enum fields
                if extracted.get('organization_type') and extracted['organization_type'] not in self.ORGANIZATION_TYPES:
                    extracted['organization_type'] = 'other'
                    confidence['organization_type'] = max(0, confidence.get('organization_type', 0.5) - 0.2)

                if extracted.get('tax_exempt_status') and extracted['tax_exempt_status'] not in self.TAX_EXEMPT_STATUSES:
                    extracted['tax_exempt_status'] = 'other'

                if extracted.get('grant_writing_capacity') and extracted['grant_writing_capacity'] not in self.GRANT_WRITING_CAPACITIES:
                    extracted['grant_writing_capacity'] = 'moderate'

                if extracted.get('primary_focus_area') and extracted['primary_focus_area'] not in self.FOCUS_AREAS:
                    extracted['primary_focus_area'] = 'other'

                return {
                    'extracted': extracted,
                    'confidence': confidence,
                    'source_documents': [d['filename'] for d in documents]
                }

            return {'extracted': {}, 'confidence': {}, 'error': 'Failed to parse LLM response'}

        except Exception as e:
            print(f"[DOC EXTRACTION] LLM extraction error: {e}")
            return {'extracted': {}, 'confidence': {}, 'error': str(e)}

    def smart_merge(
        self,
        existing_profile: Dict[str, Any],
        extracted: Dict[str, Any],
        confidence: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Smart merge extracted data with existing profile.

        Returns:
            Dict with:
            - new_fields: Fields that will be added (existing is null/empty)
            - conflicts: Fields where existing differs from extracted
            - unchanged: Fields that already match
            - merged: The resulting merged profile
        """
        new_fields = {}
        conflicts = {}
        unchanged = {}
        merged = {**existing_profile}

        for field, value in extracted.items():
            if value is None:
                continue

            existing_value = existing_profile.get(field)
            field_confidence = confidence.get(field, 0.5)

            # Check if field is empty/null in existing
            is_existing_empty = (
                existing_value is None or
                existing_value == '' or
                existing_value == [] or
                existing_value == {}
            )

            if is_existing_empty:
                # New field - will be added
                new_fields[field] = {
                    'value': value,
                    'confidence': field_confidence
                }
                merged[field] = value
            elif self._values_match(existing_value, value):
                # Values match - unchanged
                unchanged[field] = {
                    'value': existing_value,
                    'confidence': field_confidence
                }
            else:
                # Conflict - user must choose
                conflicts[field] = {
                    'existing': existing_value,
                    'extracted': value,
                    'confidence': field_confidence
                }
                # Don't change merged value - user must resolve

        return {
            'new_fields': new_fields,
            'conflicts': conflicts,
            'unchanged': unchanged,
            'merged': merged
        }

    def _values_match(self, existing: Any, extracted: Any) -> bool:
        """Check if two values are essentially the same."""
        if existing == extracted:
            return True

        # Normalize strings for comparison
        if isinstance(existing, str) and isinstance(extracted, str):
            return existing.strip().lower() == extracted.strip().lower()

        # Compare lists
        if isinstance(existing, list) and isinstance(extracted, list):
            return set(str(x).lower() for x in existing) == set(str(x).lower() for x in extracted)

        # Compare numbers with tolerance
        if isinstance(existing, (int, float)) and isinstance(extracted, (int, float)):
            if existing == 0 and extracted == 0:
                return True
            if existing == 0 or extracted == 0:
                return False
            return abs(existing - extracted) / max(abs(existing), abs(extracted)) < 0.01

        return False

    async def save_document(
        self,
        organization_id: int,
        filename: str,
        file_type: str,
        file_size: int,
        storage_path: str,
        extracted_text: str
    ) -> Dict[str, Any]:
        """Save document record to database."""
        doc_data = {
            'organization_id': organization_id,
            'filename': filename,
            'file_type': file_type,
            'file_size': file_size,
            'storage_path': storage_path,
            'extracted_text': extracted_text,
            'processed_at': datetime.now().isoformat()
        }

        result = self.supabase.table('organization_documents').insert(doc_data).execute()
        return result.data[0] if result.data else None

    async def save_extraction_history(
        self,
        organization_id: int,
        extracted_data: Dict[str, Any],
        source_document_ids: List[str],
        confidence_scores: Dict[str, float],
        applied: bool = False
    ) -> Dict[str, Any]:
        """Save extraction history for audit trail."""
        history_data = {
            'organization_id': organization_id,
            'extracted_data': extracted_data,
            'source_document_ids': source_document_ids,
            'confidence_scores': confidence_scores,
            'applied_at': datetime.now().isoformat() if applied else None
        }

        result = self.supabase.table('organization_extraction_history').insert(history_data).execute()
        return result.data[0] if result.data else None

    async def get_organization_documents(self, organization_id: int) -> List[Dict[str, Any]]:
        """Get all documents for an organization."""
        result = self.supabase.table('organization_documents')\
            .select('id, filename, file_type, file_size, uploaded_at, processed_at')\
            .eq('organization_id', organization_id)\
            .order('uploaded_at', desc=True)\
            .execute()
        return result.data if result.data else []

    async def delete_document(self, document_id: str, organization_id: int) -> bool:
        """Delete a document and its storage."""
        # Get document to find storage path
        result = self.supabase.table('organization_documents')\
            .select('storage_path')\
            .eq('id', document_id)\
            .eq('organization_id', organization_id)\
            .execute()

        if not result.data:
            return False

        storage_path = result.data[0].get('storage_path')

        # Delete from storage
        if storage_path:
            try:
                self.supabase.storage.from_('org-documents').remove([storage_path])
            except Exception as e:
                print(f"[DOC EXTRACTION] Storage delete error: {e}")

        # Delete from database
        self.supabase.table('organization_documents')\
            .delete()\
            .eq('id', document_id)\
            .eq('organization_id', organization_id)\
            .execute()

        return True
