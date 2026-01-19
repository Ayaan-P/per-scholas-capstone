"""
Organization-Aware Grant Matching Service

This service enables intelligent grant matching for any nonprofit by leveraging
their comprehensive organizational profile. Instead of hardcoded matching for a
single mission, it dynamically builds search and scoring criteria based on the
organization's actual programs, focus areas, target populations, and goals.

Features:
- Dynamic keyword generation from organization profile
- Organization-specific match scoring
- Demographic and geographic matching
- Budget and capacity-aware filtering
- Custom priority weighting based on organization preferences
"""

from typing import Dict, List, Optional, Tuple
import json
from supabase import Client
from datetime import datetime


class OrganizationMatchingService:
    """
    Intelligent grant matching service that adapts to each organization's profile.
    """

    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client

    async def get_organization_profile(self, user_id: str) -> Optional[Dict]:
        """
        Fetch the organization profile for a user.

        Args:
            user_id: The authenticated user's ID

        Returns:
            Organization profile dict or None if not found
        """
        try:
            # Get user's organization
            user_response = self.supabase.table("users").select("organization_id").eq("id", user_id).single().execute()
            organization_id = user_response.data.get("organization_id")

            if not organization_id:
                return None

            # Get organization config
            org_response = (
                self.supabase.table("organization_config")
                .select("*")
                .eq("id", organization_id)
                .single()
                .execute()
            )

            return org_response.data
        except Exception as e:
            print(f"[OrganizationMatching] Error fetching org profile: {e}")
            return None

    def build_search_keywords(self, org_profile: Dict) -> Tuple[List[str], List[str]]:
        """
        Build dynamic search keywords from organization profile.

        Combines primary focus, secondary focus, programs, target populations,
        and custom keywords to create a comprehensive search strategy.

        Args:
            org_profile: Organization configuration dict

        Returns:
            Tuple of (primary_keywords, secondary_keywords)
        """
        keywords = {
            "primary": [],
            "secondary": [],
        }

        # Add primary focus area
        if org_profile.get("primary_focus_area"):
            focus = org_profile["primary_focus_area"].lower()
            keywords["primary"].append(focus)

            # Map focus areas to relevant grant keywords
            focus_keyword_map = {
                "education": ["education", "school", "student", "learning", "training", "curriculum"],
                "health": ["health", "healthcare", "medical", "wellness", "public-health", "disease"],
                "environment": ["environment", "conservation", "climate", "sustainability", "renewable"],
                "arts": ["art", "culture", "creative", "music", "theater", "humanities"],
                "social-services": ["social", "homeless", "poverty", "family", "welfare", "youth"],
                "workforce-development": ["workforce", "job", "employment", "skills", "career", "training"],
                "technology": ["technology", "digital", "tech", "software", "internet", "innovation"],
                "housing": ["housing", "homeless", "affordable", "shelter", "development"],
                "economic-development": ["economic", "business", "entrepreneurship", "community", "development"],
                "international": ["international", "global", "developing", "humanitarian", "aid"],
            }

            if focus in focus_keyword_map:
                keywords["secondary"].extend(focus_keyword_map[focus])

        # Add secondary focus areas
        if org_profile.get("secondary_focus_areas"):
            for secondary_focus in org_profile["secondary_focus_areas"]:
                if isinstance(secondary_focus, str):
                    keywords["secondary"].append(secondary_focus.lower())

        # Add keywords from programs
        if org_profile.get("key_programs"):
            programs = org_profile["key_programs"]
            if isinstance(programs, str):
                programs = json.loads(programs)

            for program in programs:
                if isinstance(program, dict):
                    if "name" in program:
                        keywords["secondary"].append(program["name"].lower())
                    if "description" in program:
                        # Extract key words from description (simple approach)
                        desc_words = program["description"].lower().split()
                        keywords["secondary"].extend([w.strip(".,;:") for w in desc_words[:5]])

        # Add target population keywords
        if org_profile.get("target_populations"):
            populations = org_profile["target_populations"]
            if isinstance(populations, str):
                populations = json.loads(populations)

            population_keyword_map = {
                "k-12 students": ["k-12", "elementary", "middle-school", "high-school"],
                "higher education": ["college", "university", "higher-education", "post-secondary"],
                "youth": ["youth", "teen", "adolescent", "young-adult"],
                "seniors": ["senior", "older-adult", "aging", "elderly"],
                "low-income families": ["low-income", "poverty", "disadvantaged", "underserved"],
                "underrepresented communities": ["underrepresented", "diversity", "equity", "inclusion"],
                "women": ["women", "women-led", "gender-equity"],
                "veterans": ["veteran", "military", "service-member"],
                "immigrants": ["immigrant", "refugee", "foreign-born"],
                "rural": ["rural", "agricultural", "frontier"],
                "urban": ["urban", "city", "metropolitan"],
                "lgbtq": ["lgbtq", "lgbtq+", "sexual-minority", "gender-minority"],
                "persons-with-disabilities": ["disability", "disabled", "accessible", "inclusion"],
            }

            for population in populations:
                if isinstance(population, str):
                    pop_lower = population.lower()
                    keywords["secondary"].append(pop_lower)
                    if pop_lower in population_keyword_map:
                        keywords["secondary"].extend(population_keyword_map[pop_lower])

        # Add custom search keywords
        if org_profile.get("custom_search_keywords"):
            custom = org_profile["custom_search_keywords"]
            if isinstance(custom, str):
                custom = json.loads(custom)
            keywords["secondary"].extend([k.lower() for k in custom if isinstance(k, str)])

        # Remove duplicates while preserving order
        keywords["primary"] = list(dict.fromkeys(keywords["primary"]))
        keywords["secondary"] = list(dict.fromkeys(keywords["secondary"]))

        return keywords["primary"], keywords["secondary"]

    def get_matching_score_weights(self, org_profile: Dict) -> Dict[str, float]:
        """
        Get customized scoring weights based on organization profile.

        Different organizations prioritize different factors:
        - Small orgs with limited capacity care more about deadline feasibility
        - Large orgs care more about opportunity size
        - Tech-focused orgs weight keyword matching heavily
        - Service organizations weight beneficiary alignment more

        Args:
            org_profile: Organization configuration dict

        Returns:
            Dict of scoring component weights
        """
        # Base weights
        weights = {
            "keyword_matching": 0.30,
            "semantic_similarity": 0.40,
            "funding_alignment": 0.15,
            "deadline_feasibility": 0.08,
            "demographic_alignment": 0.05,
            "geographic_alignment": 0.02,
        }

        # Adjust based on organization capacity
        grant_writing_capacity = org_profile.get("grant_writing_capacity", "moderate")
        if grant_writing_capacity == "limited":
            # Prioritize easier deadlines and smaller amounts
            weights["deadline_feasibility"] = 0.12
            weights["keyword_matching"] = 0.25

        elif grant_writing_capacity == "advanced":
            # Can handle complex opportunities, prioritize semantic match
            weights["semantic_similarity"] = 0.50
            weights["deadline_feasibility"] = 0.05

        # Adjust based on organization size (staff size as proxy)
        staff_size = org_profile.get("staff_size", 10)
        if staff_size < 5:
            # Tiny org, favor deadline feasibility
            weights["deadline_feasibility"] = 0.15
        elif staff_size > 50:
            # Larger org, can handle more complex opportunities
            weights["semantic_similarity"] = 0.45

        # Normalize weights to sum to 1.0
        total = sum(weights.values())
        weights = {k: v / total for k, v in weights.items()}

        return weights

    def get_geographic_match_score(self, org_profile: Dict, grant_geographic_focus: Optional[str]) -> float:
        """
        Score geographic alignment between organization service regions and grant focus.

        Args:
            org_profile: Organization profile
            grant_geographic_focus: Geographic focus from grant (city, state, region, or "National")

        Returns:
            Score 0-100
        """
        if not grant_geographic_focus:
            return 50  # Neutral score if no geographic info

        service_regions = org_profile.get("service_regions", [])
        if not service_regions:
            return 50  # Org hasn't specified service regions

        grant_focus = grant_geographic_focus.lower()

        # National grants are excellent for any org
        if "national" in grant_focus or "nationwide" in grant_focus or "united states" in grant_focus:
            return 100

        # Check for direct regional matches
        for region in service_regions:
            if isinstance(region, str):
                if region.lower() in grant_focus or grant_focus in region.lower():
                    return 90

        # Check for state-level match
        for region in service_regions:
            if isinstance(region, str) and len(region.split()) > 0:
                # Extract state from "City, State" format
                if "," in region:
                    state = region.split(",")[-1].strip()
                    if state.lower() in grant_focus:
                        return 75

        # Check for broader geographic relevance
        if "rural" in grant_focus and any("rural" in str(r).lower() for r in service_regions):
            return 70
        if "urban" in grant_focus and any("urban" in str(r).lower() or len(str(r).split()) > 1 for r in service_regions):
            return 70

        # No geographic match found
        return 25

    def get_demographic_match_score(self, org_profile: Dict, grant_description: str) -> float:
        """
        Score demographic alignment between organization's target populations
        and grant language/description.

        Args:
            org_profile: Organization profile
            grant_description: Full grant description/abstract

        Returns:
            Score 0-100
        """
        target_populations = org_profile.get("target_populations", [])
        if not target_populations:
            return 50

        description_lower = grant_description.lower()
        matches = 0

        # Keywords associated with each population group
        population_keywords = {
            "k-12 students": ["k-12", "elementary", "secondary", "school", "student"],
            "higher education": ["college", "university", "higher ed", "post-secondary"],
            "youth": ["youth", "teens", "adolescent", "young"],
            "seniors": ["senior", "older adult", "aging", "elderly"],
            "low-income": ["low-income", "low income", "poverty", "disadvantaged"],
            "underrepresented": ["underrepresented", "minority", "diversity", "equity"],
            "women": ["women", "women-led", "woman-owned"],
            "veterans": ["veteran", "military service", "armed forces"],
            "immigrants": ["immigrant", "refugee", "foreign-born"],
            "rural": ["rural", "agricultural", "frontier"],
            "urban": ["urban", "city", "metropolitan"],
            "lgbtq": ["lgbtq", "lgbtq+", "sexual minority", "gender minority"],
            "disabilities": ["disability", "disabled", "accessible", "ada"],
        }

        for population in target_populations:
            if isinstance(population, str):
                pop_lower = population.lower()
                keywords = population_keywords.get(pop_lower, [pop_lower])
                for keyword in keywords:
                    if keyword in description_lower:
                        matches += 1
                        break

        if not matches:
            return 25

        # Score based on percentage of target populations matched
        match_percentage = (matches / len(target_populations)) * 100
        return min(100, 50 + (match_percentage / 2))  # 50-100 range

    def get_funding_alignment_score(
        self,
        org_profile: Dict,
        grant_min_amount: Optional[int],
        grant_max_amount: Optional[int],
    ) -> float:
        """
        Score funding amount alignment with organization preferences.

        Args:
            org_profile: Organization profile
            grant_min_amount: Minimum grant amount (in smallest currency unit, e.g., cents)
            grant_max_amount: Maximum grant amount

        Returns:
            Score 0-100
        """
        preferred_min = org_profile.get("preferred_grant_size_min")
        preferred_max = org_profile.get("preferred_grant_size_max")

        # If org hasn't specified preferences, use reasonable defaults
        if not preferred_min:
            preferred_min = 10000 * 100  # $10k default minimum
        if not preferred_max:
            preferred_max = 1000000 * 100  # $1M default maximum

        # If grant amounts not specified, neutral score
        if not grant_min_amount and not grant_max_amount:
            return 50

        # Use grant max as the representative amount
        grant_amount = grant_max_amount or grant_min_amount

        if not grant_amount:
            return 50

        # Perfect score if amount is within preferred range
        if preferred_min <= grant_amount <= preferred_max:
            return 100

        # Score based on how far outside the range
        if grant_amount < preferred_min:
            # Too small
            ratio = grant_amount / preferred_min
            return 50 * ratio  # Scale from 0-50

        else:
            # Too large
            ratio = preferred_max / grant_amount
            return 50 + (50 * ratio)  # Scale from 50-100

    def should_filter_grant(
        self,
        org_profile: Dict,
        grant: Dict,
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if a grant should be filtered out based on organization constraints.

        Args:
            org_profile: Organization profile
            grant: Grant opportunity dict

        Returns:
            Tuple of (should_filter_out, reason)
        """
        # Check donor restrictions
        if org_profile.get("donor_restrictions"):
            restrictions = org_profile["donor_restrictions"].lower()
            grant_title = (grant.get("title", "") or "").lower()
            grant_agency = (grant.get("agency_name", "") or "").lower()

            if "no government" in restrictions and ("government" in grant_agency or "federal" in grant_agency):
                return True, "Organization does not accept government funding"

            if "no corporate" in restrictions and ("corporate" in grant_title or "corporate" in grant_agency):
                return True, "Organization does not accept corporate funding"

        # Check matching fund capacity
        if org_profile.get("matching_fund_capacity", 0) < 25:
            # Organization has very limited matching capacity
            if grant.get("cost_sharing_required", False):
                return True, "Grant requires cost-sharing; organization has limited capacity"

        # Check deadline feasibility for limited capacity organizations
        if org_profile.get("grant_writing_capacity") == "limited":
            deadline = grant.get("deadline")
            if deadline:
                try:
                    days_to_deadline = (datetime.fromisoformat(deadline.replace("Z", "+00:00")) - datetime.now(datetime.timezone.utc)).days
                    if days_to_deadline < 14:
                        return True, "Deadline too soon for organization's grant writing capacity"
                except Exception:
                    pass

        return False, None

    def calculate_organization_match_score(
        self,
        org_profile: Dict,
        grant: Dict,
        keyword_matching_score: float,
        semantic_similarity_score: float,
    ) -> Dict[str, float]:
        """
        Calculate comprehensive grant match score for an organization.

        Combines multiple scoring factors weighted by organization profile.

        Args:
            org_profile: Organization profile
            grant: Grant opportunity dict
            keyword_matching_score: Base keyword matching score (0-100)
            semantic_similarity_score: Semantic similarity score (0-100)

        Returns:
            Dict with overall score and component scores
        """
        weights = self.get_matching_score_weights(org_profile)

        # Component scores
        scores = {
            "keyword_matching": keyword_matching_score,
            "semantic_similarity": semantic_similarity_score,
            "funding_alignment": self.get_funding_alignment_score(
                org_profile,
                grant.get("estimated_funding_min"),
                grant.get("estimated_funding_max"),
            ),
            "deadline_feasibility": 100 if grant.get("deadline") else 50,  # Simplification
            "demographic_alignment": self.get_demographic_match_score(
                org_profile,
                (grant.get("synopsis") or "") + " " + (grant.get("description") or ""),
            ),
            "geographic_alignment": self.get_geographic_match_score(
                org_profile,
                grant.get("geographic_focus"),
            ),
        }

        # Calculate weighted overall score
        overall_score = sum(scores[key] * weights.get(key, 0) for key in scores)

        return {
            "overall_score": overall_score,
            "keyword_matching": scores["keyword_matching"],
            "semantic_similarity": scores["semantic_similarity"],
            "funding_alignment": scores["funding_alignment"],
            "deadline_feasibility": scores["deadline_feasibility"],
            "demographic_alignment": scores["demographic_alignment"],
            "geographic_alignment": scores["geographic_alignment"],
            "weights": weights,
        }

    def get_matching_summary(self, org_profile: Dict) -> Dict:
        """
        Generate a human-readable summary of the organization's matching profile.

        Helps organizations understand how grants will be matched to them.

        Args:
            org_profile: Organization profile

        Returns:
            Dict with matching summary details
        """
        primary_keywords, secondary_keywords = self.build_search_keywords(org_profile)

        return {
            "organization_name": org_profile.get("name"),
            "primary_focus": org_profile.get("primary_focus_area"),
            "secondary_focuses": org_profile.get("secondary_focus_areas", []),
            "service_regions": org_profile.get("service_regions", []),
            "target_populations": org_profile.get("target_populations", []),
            "primary_search_keywords": primary_keywords,
            "secondary_search_keywords": secondary_keywords,
            "preferred_grant_range": {
                "min": org_profile.get("preferred_grant_size_min"),
                "max": org_profile.get("preferred_grant_size_max"),
            },
            "grant_writing_capacity": org_profile.get("grant_writing_capacity", "moderate"),
            "staff_size": org_profile.get("staff_size"),
            "matching_fund_capacity_percent": org_profile.get("matching_fund_capacity", 0),
            "donor_restrictions": org_profile.get("donor_restrictions"),
        }
