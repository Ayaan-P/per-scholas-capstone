"""
LLM Enhancement Service - Triggered when user saves a grant

When a grant is saved to the opportunities table, this service:
1. Generates LLM summary
2. Generates detailed match reasoning
3. Extracts tags
4. Finds similar past proposals from vector DB
5. Updates the opportunities table with enhanced data

All using Gemini API
"""

import os
import google.generativeai as genai
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import re
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


class LLMEnhancementService:
    """Enhance saved grants with LLM-powered insights."""

    def __init__(self):
        # Initialize Gemini
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not set")

        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-thinking-exp-01-21')

        # Initialize Supabase
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        self.supabase: Client = create_client(supabase_url, supabase_key)

        print("[LLM ENHANCEMENT] Service initialized")

    async def enhance_grant(self, grant: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main enhancement pipeline - called when grant is saved.

        Args:
            grant: Grant data from scraped_grants/dashboard table

        Returns:
            Enhanced grant data with LLM insights
        """
        print(f"[LLM ENHANCEMENT] Enhancing grant: {grant.get('title')}")

        # Generate LLM summary
        summary = await self._generate_summary(grant)

        # Generate detailed reasoning
        reasoning = await self._generate_reasoning(grant)

        # Extract tags
        tags = reasoning.get('tags', []) if reasoning else []

        # Find similar past proposals (from vector DB)
        similar_proposals = await self._find_similar_proposals(grant)

        # Build enhanced data
        enhanced = {
            **grant,
            'llm_summary': summary,
            'detailed_match_reasoning': reasoning.get('reasoning') if reasoning else None,
            'tags': tags,
            'similar_past_proposals': similar_proposals,
            'llm_enhanced_at': datetime.now().isoformat()
        }

        print(f"[LLM ENHANCEMENT] Enhancement complete")
        return enhanced

    async def _generate_summary(self, grant: Dict[str, Any]) -> str:
        """Generate concise LLM summary."""
        try:
            # Build comprehensive grant info for LLM
            award_info = ""
            if grant.get('award_floor') and grant.get('award_ceiling'):
                award_info = f"\nAward Range: ${grant.get('award_floor'):,} - ${grant.get('award_ceiling'):,}"
                if grant.get('expected_number_of_awards'):
                    award_info += f"\nExpected Awards: {grant.get('expected_number_of_awards')}"
            elif grant.get('amount'):
                award_info = f"\nAmount: ${grant.get('amount', 0):,}"

            eligibility_info = ""
            if grant.get('eligibility_explanation'):
                eligibility_info = f"\nEligibility: {grant.get('eligibility_explanation')[:200]}"

            cost_sharing_info = ""
            if grant.get('cost_sharing'):
                cost_sharing_info = f"\nCost Sharing: Required"
                if grant.get('cost_sharing_description'):
                    cost_sharing_info += f" - {grant.get('cost_sharing_description')[:100]}"

            prompt = f"""Summarize this grant opportunity:

Title: {grant.get('title')}
Funder: {grant.get('funder')}{award_info}
Deadline: {grant.get('deadline', 'Not specified')}

Full Description:
{grant.get('description', '')}{eligibility_info}{cost_sharing_info}

Write a clear 2-3 sentence summary of what this grant is for and what it funds."""

            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"[LLM ENHANCEMENT] Summary error: {e}")
            return f"Grant opportunity from {grant.get('funder')} for ${grant.get('amount', 0):,}"

    async def _generate_reasoning(self, grant: Dict[str, Any]) -> Optional[Dict]:
        """Generate detailed LLM reasoning with tags."""
        try:
            # Get score breakdown for context
            score_breakdown = self._get_score_breakdown(grant)

            # Build comprehensive grant context
            award_details = ""
            if grant.get('award_floor') and grant.get('award_ceiling'):
                award_details = f"\nAward Range: ${grant.get('award_floor'):,} - ${grant.get('award_ceiling'):,}"
                if grant.get('expected_number_of_awards'):
                    award_details += f" (Expected Awards: {grant.get('expected_number_of_awards')})"
            elif grant.get('amount'):
                award_details = f"\nAmount: ${grant.get('amount', 0):,}"

            eligibility_details = ""
            if grant.get('eligibility_explanation'):
                eligibility_details = f"\n\nEligibility Criteria:\n{grant.get('eligibility_explanation')[:300]}"

            cost_sharing_details = ""
            if grant.get('cost_sharing'):
                cost_sharing_details = f"\n\nCost Sharing: REQUIRED"
                if grant.get('cost_sharing_description'):
                    cost_sharing_details += f"\n{grant.get('cost_sharing_description')[:200]}"

            contact_info = ""
            if grant.get('contact_name') or grant.get('contact_phone'):
                contact_info = "\n\nProgram Contact:"
                if grant.get('contact_name'):
                    contact_info += f"\nName: {grant.get('contact_name')}"
                if grant.get('contact_phone'):
                    contact_info += f"\nPhone: {grant.get('contact_phone')}"

            additional_context = ""
            if grant.get('additional_info_text'):
                additional_context = f"\n\nAdditional Information:\n{grant.get('additional_info_text')[:300]}"

            prompt = f"""Analyze this grant for Per Scholas. Return ONLY valid JSON:

{{
  "tags": ["tag1", "tag2", "tag3"],
  "reasoning": "Detailed explanation of why this is a match"
}}

Grant: {grant.get('title')}
Funder: {grant.get('funder')}{award_details}
Deadline: {grant.get('deadline', 'Not specified')}
Match Score: {grant.get('match_score', 0)}%

Description: {grant.get('description', '')[:500]}{eligibility_details}{cost_sharing_details}{contact_info}{additional_context}

Score Breakdown:
- Base Score: {score_breakdown['components']['base_score']}
- Keyword Match Score: {score_breakdown['components']['keyword_score']}/40
- Amount Alignment Score: {score_breakdown['components']['amount_score']}/15
- Deadline Score: {score_breakdown['components']['deadline_score']}/5
- Total (before penalties): {score_breakdown['total_before_penalty']}

Matched Keywords:
- Core: {', '.join(score_breakdown['matches']['core_keywords'])}
- Context: {', '.join(score_breakdown['matches']['context_keywords'])}

Domain Penalties: {score_breakdown['penalties']['domain_penalty']} points
{f"⚠️ Non-relevant domains found: {', '.join(score_breakdown['penalties']['excluded_domains_found'])}" if score_breakdown['penalties']['excluded_domains_found'] else "✓ No domain penalties"}

Focus on: alignment with tech workforce training, target demographics, and program fit.
Consider eligibility requirements, cost sharing implications, and funding structure.
Use the score breakdown to explain specific strengths and weaknesses.
Generate 3-5 relevant tags based on the matched keywords and grant focus."""

            response = self.model.generate_content(prompt)

            # Extract JSON
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

            return None
        except Exception as e:
            print(f"[LLM ENHANCEMENT] Reasoning error: {e}")
            return None

    def _get_score_breakdown(self, grant: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed score breakdown for context."""
        try:
            from match_scoring import get_score_breakdown
            return get_score_breakdown(grant, [])
        except Exception as e:
            print(f"[LLM ENHANCEMENT] Error getting score breakdown: {e}")
            # Return minimal breakdown
            return {
                'final_score': grant.get('match_score', 0),
                'components': {
                    'base_score': 10,
                    'keyword_score': 0,
                    'semantic_score': 0,
                    'amount_score': 0,
                    'deadline_score': 5,
                },
                'penalties': {
                    'domain_penalty': 0,
                    'excluded_domains_found': []
                },
                'matches': {
                    'core_keywords': [],
                    'context_keywords': [],
                    'core_count': 0,
                    'context_count': 0
                },
                'total_before_penalty': 15
            }

    async def _find_similar_proposals(self, grant: Dict[str, Any]) -> List[Dict]:
        """Find similar past proposals using PGVector similarity search."""
        try:
            # Import semantic service for RFP similarity search
            from semantic_service import SemanticService

            semantic_service = SemanticService()

            # Create query text from grant
            query_text = f"{grant.get('title', '')} {grant.get('description', '')}"

            # Find similar RFPs (threshold 0.25 = 25% similarity minimum)
            similar_rfps = semantic_service.find_similar_rfps(query_text, limit=5)

            if similar_rfps:
                print(f"[LLM ENHANCEMENT] Found {len(similar_rfps)} similar RFPs for '{grant.get('title', 'Unknown')[:50]}...'")
                for rfp in similar_rfps:
                    print(f"  - {rfp.get('title', 'Unknown')[:60]}... (similarity: {rfp.get('similarity_score', 0):.2f})")

            return similar_rfps

        except Exception as e:
            print(f"[LLM ENHANCEMENT] Similarity search error: {e}")
            return []


# Convenience function for API endpoint
async def enhance_and_save_grant(grant_id: str, supabase: Client) -> Dict[str, Any]:
    """
    Enhancement pipeline triggered on save button.

    Args:
        grant_id: ID of grant in scraped_grants table
        supabase: Supabase client

    Returns:
        Enhanced grant data saved to unified saved_opportunities table
    """
    # 1. Fetch grant from scraped_grants
    result = supabase.table('scraped_grants').select('*').eq('id', grant_id).execute()
    if not result.data:
        raise ValueError(f"Grant {grant_id} not found")

    grant = result.data[0]

    # 2. Run LLM enhancement
    service = LLMEnhancementService()
    enhanced = await service.enhance_grant(grant)

    # 3. Save to unified saved_opportunities table
    opp_data = {
        'opportunity_id': enhanced.get('opportunity_id'),  # Use opportunity_id field from scraped_grants
        'title': enhanced.get('title'),
        'funder': enhanced.get('funder'),
        'amount': enhanced.get('amount'),
        'deadline': enhanced.get('deadline'),
        'match_score': enhanced.get('match_score'),
        'description': enhanced.get('description'),
        'requirements': enhanced.get('requirements', []),
        'contact': enhanced.get('contact', ''),
        'application_url': enhanced.get('application_url', ''),
        'source': enhanced.get('source', 'grants_gov'),
        'llm_summary': enhanced.get('llm_summary'),
        'detailed_match_reasoning': enhanced.get('detailed_match_reasoning'),
        'tags': enhanced.get('tags', []),
        'similar_past_proposals': enhanced.get('similar_past_proposals', []),
        'status': 'active',

        # UNIVERSAL COMPREHENSIVE FIELDS
        'contact_name': enhanced.get('contact_name'),
        'contact_phone': enhanced.get('contact_phone'),
        'contact_description': enhanced.get('contact_description'),
        'eligibility_explanation': enhanced.get('eligibility_explanation'),
        'cost_sharing': enhanced.get('cost_sharing'),
        'cost_sharing_description': enhanced.get('cost_sharing_description'),
        'additional_info_url': enhanced.get('additional_info_url'),
        'additional_info_text': enhanced.get('additional_info_text'),
        'archive_date': enhanced.get('archive_date'),
        'forecast_date': enhanced.get('forecast_date'),
        'close_date_explanation': enhanced.get('close_date_explanation'),
        'expected_number_of_awards': enhanced.get('expected_number_of_awards'),
        'award_floor': enhanced.get('award_floor'),
        'award_ceiling': enhanced.get('award_ceiling'),
        'attachments': enhanced.get('attachments', []),
        'version': enhanced.get('version'),
        'last_updated_date': enhanced.get('last_updated_date')
        # saved_at, created_at, updated_at are auto-generated
    }

    supabase.table('saved_opportunities').insert(opp_data).execute()

    return enhanced
