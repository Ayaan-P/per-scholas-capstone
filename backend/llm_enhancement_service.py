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
            prompt = f"""Summarize this grant opportunity for Per Scholas (technology workforce training nonprofit):

Title: {grant.get('title')}
Funder: {grant.get('funder')}
Amount: ${grant.get('amount', 0):,}
Description: {grant.get('description', '')[:500]}

Write 2-3 sentences explaining why this is a good match and what the opportunity is."""

            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"[LLM ENHANCEMENT] Summary error: {e}")
            return f"Grant opportunity from {grant.get('funder')} for ${grant.get('amount', 0):,}"

    async def _generate_reasoning(self, grant: Dict[str, Any]) -> Optional[Dict]:
        """Generate detailed LLM reasoning with tags."""
        try:
            prompt = f"""Analyze this grant for Per Scholas. Return ONLY valid JSON:

{{
  "tags": ["tag1", "tag2", "tag3"],
  "reasoning": "Detailed explanation of why this is a match"
}}

Grant: {grant.get('title')}
Funder: {grant.get('funder')}
Description: {grant.get('description', '')[:500]}

Focus on: alignment with tech workforce training, target demographics, and program fit."""

            response = self.model.generate_content(prompt)

            # Extract JSON
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

            return None
        except Exception as e:
            print(f"[LLM ENHANCEMENT] Reasoning error: {e}")
            return None

    async def _find_similar_proposals(self, grant: Dict[str, Any]) -> List[Dict]:
        """Find similar past proposals using PGVector similarity search."""
        try:
            # Query PGVector DB for similar proposals
            # This requires the pgvector extension and proper setup
            result = self.supabase.rpc('match_proposals', {
                'query_text': f"{grant.get('title')} {grant.get('description', '')}",
                'match_count': 3
            }).execute()

            if hasattr(result, 'data') and result.data:
                return result.data

            return []
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
        Enhanced grant data saved to opportunities table
    """
    # 1. Fetch grant from scraped_grants
    result = supabase.table('scraped_grants').select('*').eq('id', grant_id).execute()
    if not result.data:
        raise ValueError(f"Grant {grant_id} not found")

    grant = result.data[0]

    # 2. Run LLM enhancement
    service = LLMEnhancementService()
    enhanced = await service.enhance_grant(grant)

    # 3. Save to opportunities table
    opp_data = {
        'id': enhanced.get('opportunity_id'),  # Use opportunity_id field from scraped_grants
        'title': enhanced.get('title'),
        'funder': enhanced.get('funder'),
        'amount': enhanced.get('amount'),
        'deadline': enhanced.get('deadline'),
        'match_score': enhanced.get('match_score'),
        'description': enhanced.get('description'),
        'requirements': enhanced.get('requirements', []),
        'contact': enhanced.get('contact', ''),
        'application_url': enhanced.get('application_url', ''),
        'llm_summary': enhanced.get('llm_summary'),
        'detailed_match_reasoning': enhanced.get('detailed_match_reasoning'),
        'tags': enhanced.get('tags', []),
        'similar_past_proposals': enhanced.get('similar_past_proposals', [])
        # created_at is auto-generated
    }

    supabase.table('opportunities').insert(opp_data).execute()

    return enhanced
