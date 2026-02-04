"""
Service for managing opportunity categories and their configurations.
Handles category-based search prompts, keywords, and filtering.
"""

import os
import logging
from typing import Optional, List, Dict, Any
from supabase import create_client, Client

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://zjqwpvdcpzeguhdwrskr.supabase.co")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Initialize Supabase admin client (may be None if env var not set at import time)
supabase_admin: Client = None
if SUPABASE_SERVICE_ROLE_KEY:
    try:
        supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    except Exception as e:
        logger.warning(f"[CATEGORY] Could not create admin Supabase client: {e}")


class CategoryService:
    """Manages opportunity categories and their configurations."""

    def __init__(self, supabase_client: Client = None):
        self.supabase = supabase_client or supabase_admin
        self._categories_cache = None
        self._prompts_cache = None

    def get_all_categories(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Get all active opportunity categories."""
        if self._categories_cache and not force_refresh:
            return self._categories_cache

        try:
            result = self.supabase.table("opportunity_categories").select("*").eq("is_active", True).order("display_order").execute()
            self._categories_cache = result.data if result.data else []
            logger.info(f"[CATEGORY] Loaded {len(self._categories_cache)} categories")
            return self._categories_cache
        except Exception as e:
            logger.error(f"[CATEGORY] Error loading categories: {e}")
            return []

    def get_category_by_id(self, category_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific category by ID."""
        try:
            result = self.supabase.table("opportunity_categories").select("*").eq("id", category_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"[CATEGORY] Error loading category {category_id}: {e}")
            return None

    def get_category_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific category by name."""
        try:
            result = self.supabase.table("opportunity_categories").select("*").eq("name", name).single().execute()
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"[CATEGORY] Error loading category '{name}': {e}")
            return None

    def get_category_keywords(self, category_id: int) -> List[Dict[str, Any]]:
        """Get all keywords for a category, sorted by weight."""
        try:
            result = (
                self.supabase.table("category_keywords")
                .select("keyword, weight, is_required")
                .eq("category_id", category_id)
                .order("weight", desc=True)
                .execute()
            )
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"[CATEGORY] Error loading keywords for category {category_id}: {e}")
            return []

    def get_category_search_prompt(self, category_id: int) -> Optional[Dict[str, Any]]:
        """Get the search prompt configuration for a category."""
        if self._prompts_cache and category_id in self._prompts_cache:
            return self._prompts_cache[category_id]

        try:
            result = (
                self.supabase.table("category_search_prompts")
                .select("*")
                .eq("category_id", category_id)
                .single()
                .execute()
            )
            if not self._prompts_cache:
                self._prompts_cache = {}
            self._prompts_cache[category_id] = result.data if result.data else None
            return self._prompts_cache[category_id]
        except Exception as e:
            logger.error(f"[CATEGORY] Error loading search prompt for category {category_id}: {e}")
            return None

    def build_orchestration_prompt(
        self,
        category_id: int,
        location: tuple = None,
        organization_context: str = None,
        user_search_term: str = None,
    ) -> Optional[str]:
        """
        Build a Gemini orchestration prompt for a specific category.

        Args:
            category_id: The category ID
            location: Optional (state, city) tuple for location-specific searches
            organization_context: Optional organization context to include
            user_search_term: Optional user-provided search term to merge

        Returns:
            Formatted orchestration prompt or None if category not found
        """
        category = self.get_category_by_id(category_id)
        prompt_config = self.get_category_search_prompt(category_id)

        if not category or not prompt_config:
            logger.error(f"[CATEGORY] Cannot build prompt - missing category or config for ID {category_id}")
            return None

        # Build location part
        location_part = ""
        if location:
            state, city = location
            location_part = f" in {state} (specifically {city})"

        # Build focus areas part
        focus_areas = prompt_config.get("focus_areas", [])
        focus_areas_text = ""
        if focus_areas:
            focus_areas_text = ", " + ", ".join(focus_areas)

        # Build the base search request
        search_request = f"Find state and local {prompt_config.get('prompt_template', 'funding opportunities')}{location_part}{focus_areas_text}."

        # If user provided a search term, merge it
        if user_search_term:
            search_request = f"Focus on: {user_search_term}. {search_request}"

        # Build organization context section
        org_context_section = ""
        if organization_context:
            org_context_section = f"""
Organization Context:
{organization_context}
"""

        # Build the orchestration prompt
        intro = "You are a fundraising specialist helping find opportunities for this organization." if organization_context else "You are a grants research specialist building a comprehensive funding database."
        orchestration_prompt = f"""{intro} Find REAL, CURRENT funding opportunities using web research.
{org_context_section}
Search Request: {search_request}

Category Focus: {category.get('name')} opportunities

Minimum Funding: ${prompt_config.get('min_funding', 50000):,}
Deadline Window: Next {prompt_config.get('deadline_months', 6)} months

Execute this multi-step process:

1. Search federal databases (GRANTS.gov, NSF, DOL, SAM.gov) for relevant funding
2. Research foundation grants aligned with these focus areas
3. Identify corporate funding programs
4. Filter for opportunities with deadlines in the specified window and funding above minimum
5. Find at least 3-5 different opportunities from various sources

Return ONLY raw JSON - NO markdown code blocks, NO explanatory text.
Your response should START with {{ and END with }}.

Example format:
{{
  "opportunities": [
    {{
      "id": "unique-id",
      "title": "Full grant title",
      "funder": "Organization name",
      "amount": 100000,
      "deadline": "2025-12-31",
      "description": "Description",
      "requirements": ["Requirement 1", "Requirement 2"],
      "contact": "email@agency.gov",
      "application_url": "https://...",
      "eligibility_explanation": "Who can apply",
      "cost_sharing": false,
      "award_floor": 50000,
      "award_ceiling": 250000
    }}
  ]
}}

CRITICAL: Return ONLY the JSON object (no markdown, no extra text)."""

        return orchestration_prompt

    def categorize_opportunity(self, opportunity: Dict[str, Any]) -> Optional[int]:
        """
        Attempt to categorize an opportunity based on its title, description, and keywords.

        Args:
            opportunity: Dictionary with title, description, requirements, tags, etc.

        Returns:
            Category ID if matched, None otherwise
        """
        text_to_search = " ".join(
            [
                opportunity.get("title", ""),
                opportunity.get("description", ""),
                " ".join(opportunity.get("requirements", [])),
                " ".join(opportunity.get("tags", [])),
            ]
        ).lower()

        categories = self.get_all_categories()
        best_match = None
        best_score = 0

        for category in categories:
            keywords = self.get_category_keywords(category["id"])
            score = 0

            for kw_data in keywords:
                keyword = kw_data["keyword"].lower()
                weight = kw_data.get("weight", 1.0)
                is_required = kw_data.get("is_required", False)

                if keyword in text_to_search:
                    score += weight
                    if is_required:
                        # Required keywords boost score significantly
                        score *= 2

            if score > best_score:
                best_score = score
                best_match = category["id"]

        if best_match:
            logger.info(f"[CATEGORY] Categorized opportunity as {best_match} (score: {best_score})")
            return best_match

        return None

    def get_categories_for_display(self) -> List[Dict[str, Any]]:
        """Get categories formatted for frontend display."""
        categories = self.get_all_categories()
        return [
            {
                "id": cat["id"],
                "name": cat["name"],
                "description": cat["description"],
                "color": cat.get("color_hex", "#3B82F6"),
                "icon": cat.get("icon"),
            }
            for cat in categories
        ]


# Global instance
_category_service = None


def get_category_service(supabase_client: Client = None) -> CategoryService:
    """Get or create the global category service instance.
    
    Args:
        supabase_client: Optional Supabase client to use. If provided on first call,
                        it will be used instead of the module-level admin client.
    """
    global _category_service
    if _category_service is None:
        client = supabase_client or supabase_admin
        if client is None:
            logger.error("[CATEGORY] No Supabase client available! SUPABASE_SERVICE_ROLE_KEY may not be set.")
        _category_service = CategoryService(client)
    return _category_service
