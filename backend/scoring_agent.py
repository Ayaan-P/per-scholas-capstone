"""
Qualification Agent - Grant Scoring & Analysis

Analyzes grants from scraped_grants and generates match scores + reasoning
for a specific organization. Writes qualified grants to org_grants.

Features:
- LLM-based scoring with Claude Sonnet for nuanced matching
- Rule-based pre-filtering for efficiency  
- Reads org profile from workspace (PROFILE.md)
- Structured scoring across 6 dimensions
- Explainable reasoning for each score
- Cost-optimized (<$0.05 per grant)
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import anthropic

# Scoring thresholds
HIGH_MATCH_THRESHOLD = 80
LOW_MATCH_THRESHOLD = 30
MINIMUM_VIABLE_SCORE = 20

# Scoring weights (must sum to 100)
SCORING_WEIGHTS = {
    "mission_alignment": 30,      # How well grant aligns with org mission
    "target_population": 20,      # Demographics and population fit
    "geographic_coverage": 15,    # Location match
    "funding_fit": 15,            # Amount vs org capacity
    "eligibility": 10,            # Requirements match
    "strategic_value": 10,        # Historical patterns, timing, strategic fit
}


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of a grant score"""
    mission_alignment: int        # 0-30 points
    target_population: int        # 0-20 points
    geographic_coverage: int      # 0-15 points
    funding_fit: int              # 0-15 points
    eligibility: int              # 0-10 points
    strategic_value: int          # 0-10 points
    
    @property
    def total(self) -> int:
        return (
            self.mission_alignment + 
            self.target_population + 
            self.geographic_coverage + 
            self.funding_fit + 
            self.eligibility + 
            self.strategic_value
        )
    
    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


@dataclass
class ScoringResult:
    """Complete result from scoring a grant"""
    grant_id: str
    match_score: int              # 0-100
    score_breakdown: ScoreBreakdown
    reasoning: str                # 2-3 sentence explanation
    summary: str                  # Brief grant summary
    key_tags: List[str]           # Extracted tags
    effort_estimate: str          # low/medium/high
    winning_strategies: List[str] # Tips for application
    processing_time_ms: int
    model_tokens_used: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "grant_id": self.grant_id,
            "match_score": self.match_score,
            "score_breakdown": self.score_breakdown.to_dict(),
            "reasoning": self.reasoning,
            "summary": self.summary,
            "key_tags": self.key_tags,
            "effort_estimate": self.effort_estimate,
            "winning_strategies": self.winning_strategies,
            "processing_time_ms": self.processing_time_ms,
            "model_tokens_used": self.model_tokens_used,
        }


class ScoringAgent:
    """
    Agent that scores grants for a specific organization.
    
    Uses a two-phase approach:
    1. Rule-based pre-filtering (fast, no API cost)
    2. LLM-based deep scoring (accurate, ~$0.02-0.05 per grant)
    
    Profile loading priority:
    1. Supabase organization_config (if supabase_client provided)
    2. Filesystem PROFILE.md (fallback)
    """
    
    def __init__(
        self, 
        org_id: str,
        workspace_root: str = "/var/fundfish/workspaces",
        model: str = "claude-sonnet-4-20250514",
        supabase_client = None
    ):
        self.org_id = org_id
        self.workspace_root = Path(workspace_root)
        self.model = model
        self.org_profile = None
        self.client = anthropic.Anthropic()
        self.supabase = supabase_client
        
        # Stats tracking
        self.stats = {
            "grants_processed": 0,
            "grants_pre_filtered": 0,
            "total_tokens": 0,
            "total_time_ms": 0,
        }
    
    def load_org_profile(self) -> Dict[str, Any]:
        """
        Load organization profile. Tries Supabase first, falls back to filesystem.
        """
        # Try Supabase first if client available
        if self.supabase:
            try:
                profile = self._load_profile_from_supabase()
                if profile:
                    self.org_profile = profile
                    return self.org_profile
            except Exception as e:
                print(f"[ScoringAgent] Supabase profile load failed: {e}, trying filesystem")
        
        # Fallback to filesystem PROFILE.md
        profile_path = self.workspace_root / self.org_id / "PROFILE.md"
        
        if not profile_path.exists():
            raise FileNotFoundError(f"No profile found in Supabase or at {profile_path}")
        
        content = profile_path.read_text()
        
        # Parse markdown profile into structured data
        self.org_profile = self._parse_profile_md(content)
        return self.org_profile
    
    def _load_profile_from_supabase(self) -> Optional[Dict[str, Any]]:
        """Load organization profile from Supabase organization_config table"""
        if not self.supabase:
            return None
        
        # org_id might be numeric (from org_grants) or string
        try:
            org_id_int = int(self.org_id)
            response = self.supabase.table("organization_config")\
                .select("*")\
                .eq("id", org_id_int)\
                .single()\
                .execute()
        except ValueError:
            # Not a numeric ID, try as string identifier
            response = self.supabase.table("organization_config")\
                .select("*")\
                .eq("name", self.org_id)\
                .limit(1)\
                .execute()
            if not response.data:
                return None
            response.data = response.data[0] if isinstance(response.data, list) else response.data
        
        data = response.data
        if not data:
            return None
        
        # Transform Supabase org config to scoring profile format
        profile = {
            "name": data.get("name", ""),
            "mission": data.get("mission", "") or data.get("description", ""),
            "ein": data.get("ein", ""),
            "focus_areas": self._parse_json_field(data.get("secondary_focus_areas", [])),
            "programs": self._parse_json_field(data.get("key_programs", [])),
            "target_demographics": self._parse_json_field(data.get("target_populations", [])),
            "geographic_focus": self._parse_json_field(data.get("service_regions", [])),
            "budget_range": {
                "min": data.get("preferred_grant_size_min") or 0,
                "max": data.get("preferred_grant_size_max") or 0
            },
            "staff_size": str(data.get("staff_size", "")) if data.get("staff_size") else "",
            "key_metrics": self._parse_json_field(data.get("key_impact_metrics", [])),
            "past_funders": self._extract_funders_from_grants(data.get("previous_grants", [])),
            "raw_content": "",  # No raw markdown from DB
            # Additional fields from org_config
            "primary_focus_area": data.get("primary_focus_area", ""),
            "annual_budget": data.get("annual_budget"),
            "custom_search_keywords": self._parse_json_field(data.get("custom_search_keywords", [])),
        }
        
        # Add primary focus area to focus_areas if not already there
        if profile["primary_focus_area"] and profile["primary_focus_area"] not in profile["focus_areas"]:
            profile["focus_areas"].insert(0, profile["primary_focus_area"])
        
        return profile
    
    def _parse_json_field(self, field) -> List[str]:
        """Parse a JSONB field that could be list, string, or None"""
        if not field:
            return []
        if isinstance(field, list):
            return [str(item) for item in field if item]
        if isinstance(field, str):
            try:
                parsed = json.loads(field)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed if item]
            except json.JSONDecodeError:
                return [field] if field else []
        return []
    
    def _extract_funders_from_grants(self, previous_grants) -> List[str]:
        """Extract funder names from previous_grants JSONB field"""
        funders = []
        grants = self._parse_json_field(previous_grants)
        for grant in grants:
            if isinstance(grant, dict):
                funder = grant.get("funder") or grant.get("source") or grant.get("name")
                if funder:
                    funders.append(funder)
            elif isinstance(grant, str):
                funders.append(grant)
        return funders
    
    def _parse_profile_md(self, content: str) -> Dict[str, Any]:
        """Parse PROFILE.md into structured data"""
        profile = {
            "name": "",
            "mission": "",
            "ein": "",
            "focus_areas": [],
            "programs": [],
            "target_demographics": [],
            "geographic_focus": [],
            "budget_range": {"min": 0, "max": 0},
            "staff_size": "",
            "key_metrics": [],
            "past_funders": [],
            "raw_content": content,
        }
        
        current_section = None
        lines = content.split("\n")
        
        for line in lines:
            line = line.strip()
            
            # Detect sections
            if line.startswith("## "):
                current_section = line[3:].lower().strip()
                continue
            
            if line.startswith("- **") and ":**" in line:
                # Parse key-value pairs like "- **Name:** Per Scholas"
                key, value = line.split(":**", 1)
                key = key.replace("- **", "").strip().lower()
                value = value.strip()
                
                if key == "name":
                    profile["name"] = value
                elif key == "mission":
                    profile["mission"] = value
                elif key == "ein":
                    profile["ein"] = value
            
            elif line.startswith("- ") and current_section:
                item = line[2:].strip()
                if item:
                    if "focus" in current_section:
                        profile["focus_areas"].append(item)
                    elif "program" in current_section:
                        profile["programs"].append(item)
                    elif "demographic" in current_section or "population" in current_section:
                        profile["target_demographics"].append(item)
                    elif "geographic" in current_section or "location" in current_section:
                        profile["geographic_focus"].append(item)
                    elif "funder" in current_section:
                        profile["past_funders"].append(item)
        
        return profile
    
    def pre_filter_grant(self, grant: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Fast rule-based pre-filtering before expensive LLM scoring.
        Returns (passes_filter, reason).
        """
        title = (grant.get("title") or "").lower()
        description = (grant.get("description") or "").lower()
        eligibility = (grant.get("eligibility") or "").lower()
        full_text = f"{title} {description} {eligibility}"
        
        # Hard exclusions - clearly wrong domains
        exclusion_keywords = [
            "agriculture", "farming", "livestock", "dairy",
            "petroleum", "mining", "fossil fuel",
            "tobacco", "gambling", "firearms",
            "international development abroad",  # if org is domestic-only
        ]
        
        for keyword in exclusion_keywords:
            if keyword in full_text:
                return False, f"Excluded domain: {keyword}"
        
        # Check for at least some relevance to org
        if self.org_profile:
            focus_areas = [f.lower() for f in self.org_profile.get("focus_areas", [])]
            programs = [p.lower() for p in self.org_profile.get("programs", [])]
            
            # Build relevance keywords from org profile
            relevance_keywords = set()
            for area in focus_areas + programs:
                relevance_keywords.update(area.split())
            
            # Remove common words
            common_words = {"and", "the", "for", "of", "in", "to", "a", "an", "with"}
            relevance_keywords -= common_words
            
            # Check if any relevance keywords appear
            matches = [kw for kw in relevance_keywords if kw in full_text]
            if len(matches) < 1 and len(relevance_keywords) > 0:
                return False, "No matching keywords from org focus areas"
        
        # Check deadline - skip if already passed
        deadline = grant.get("deadline")
        if deadline:
            try:
                if isinstance(deadline, str):
                    deadline_date = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
                else:
                    deadline_date = deadline
                
                if deadline_date.date() < datetime.now().date():
                    return False, "Deadline has passed"
            except Exception:
                pass  # If we can't parse deadline, don't filter
        
        return True, "Passes pre-filter"
    
    def score_grant(self, grant: Dict[str, Any], use_llm: bool = True) -> ScoringResult:
        """
        Score a single grant against the organization profile.
        
        Args:
            grant: Grant data from scraped_grants
            use_llm: Whether to use LLM for deep scoring (if False, uses rule-based only)
        
        Returns:
            ScoringResult with score, breakdown, reasoning, and metadata
        """
        start_time = time.time()
        tokens_used = 0
        
        if not self.org_profile:
            self.load_org_profile()
        
        # Pre-filter check
        passes, filter_reason = self.pre_filter_grant(grant)
        if not passes:
            self.stats["grants_pre_filtered"] += 1
            return ScoringResult(
                grant_id=grant.get("id", "unknown"),
                match_score=0,
                score_breakdown=ScoreBreakdown(0, 0, 0, 0, 0, 0),
                reasoning=f"Pre-filtered: {filter_reason}",
                summary="Grant filtered out during pre-screening.",
                key_tags=[],
                effort_estimate="n/a",
                winning_strategies=[],
                processing_time_ms=int((time.time() - start_time) * 1000),
                model_tokens_used=0,
            )
        
        if use_llm:
            result = self._score_with_llm(grant)
            tokens_used = result.model_tokens_used
        else:
            result = self._score_rule_based(grant)
        
        # Update stats
        self.stats["grants_processed"] += 1
        self.stats["total_tokens"] += tokens_used
        
        result.processing_time_ms = int((time.time() - start_time) * 1000)
        self.stats["total_time_ms"] += result.processing_time_ms
        
        return result
    
    def _score_with_llm(self, grant: Dict[str, Any]) -> ScoringResult:
        """Use Claude to generate nuanced scoring and reasoning"""
        
        # Build the scoring prompt
        prompt = self._build_scoring_prompt(grant)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                system="""You are a grant qualification specialist. Analyze grants for nonprofit organizations and provide structured scoring assessments.

Always respond with valid JSON matching this schema:
{
    "match_score": <0-100>,
    "score_breakdown": {
        "mission_alignment": <0-30>,
        "target_population": <0-20>,
        "geographic_coverage": <0-15>,
        "funding_fit": <0-15>,
        "eligibility": <0-10>,
        "strategic_value": <0-10>
    },
    "reasoning": "<2-3 sentence explanation of why this grant matches or doesn't>",
    "summary": "<Brief 2-sentence summary of what the grant funds>",
    "key_tags": ["<tag1>", "<tag2>", ...],
    "effort_estimate": "<low|medium|high>",
    "winning_strategies": ["<tip1>", "<tip2>"]
}"""
            )
            
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            
            # Parse response
            content = response.content[0].text
            
            # Extract JSON from response (handle potential markdown wrapping)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            data = json.loads(content.strip())
            
            breakdown = ScoreBreakdown(
                mission_alignment=min(30, max(0, data["score_breakdown"]["mission_alignment"])),
                target_population=min(20, max(0, data["score_breakdown"]["target_population"])),
                geographic_coverage=min(15, max(0, data["score_breakdown"]["geographic_coverage"])),
                funding_fit=min(15, max(0, data["score_breakdown"]["funding_fit"])),
                eligibility=min(10, max(0, data["score_breakdown"]["eligibility"])),
                strategic_value=min(10, max(0, data["score_breakdown"]["strategic_value"])),
            )
            
            return ScoringResult(
                grant_id=grant.get("id", "unknown"),
                match_score=min(100, max(0, breakdown.total)),
                score_breakdown=breakdown,
                reasoning=data.get("reasoning", ""),
                summary=data.get("summary", ""),
                key_tags=data.get("key_tags", [])[:5],  # Limit tags
                effort_estimate=data.get("effort_estimate", "medium"),
                winning_strategies=data.get("winning_strategies", [])[:3],
                processing_time_ms=0,  # Set later
                model_tokens_used=tokens_used,
            )
            
        except json.JSONDecodeError as e:
            print(f"[ScoringAgent] JSON parse error: {e}")
            return self._score_rule_based(grant)
        except Exception as e:
            print(f"[ScoringAgent] LLM error: {e}")
            return self._score_rule_based(grant)
    
    def _build_scoring_prompt(self, grant: Dict[str, Any]) -> str:
        """Build the prompt for LLM scoring"""
        
        org_context = f"""
## Organization Profile
- **Name:** {self.org_profile.get('name', 'Unknown')}
- **Mission:** {self.org_profile.get('mission', 'Not specified')}
- **Focus Areas:** {', '.join(self.org_profile.get('focus_areas', ['Not specified']))}
- **Programs:** {', '.join(self.org_profile.get('programs', ['Not specified']))}
- **Target Demographics:** {', '.join(self.org_profile.get('target_demographics', ['Not specified']))}
- **Geographic Focus:** {', '.join(self.org_profile.get('geographic_focus', ['Not specified']))}
"""
        
        grant_context = f"""
## Grant Opportunity
- **Title:** {grant.get('title', 'Unknown')}
- **Funder:** {grant.get('funder', 'Unknown')} / {grant.get('agency', '')}
- **Amount Range:** ${grant.get('amount_min', 0):,} - ${grant.get('amount_max', 0):,}
- **Deadline:** {grant.get('deadline', 'Not specified')}
- **Source:** {grant.get('source', 'Unknown')}
- **Geographic Focus:** {grant.get('geographic_focus', 'Not specified')}
- **Program Areas:** {', '.join(grant.get('program_area', []) or ['Not specified'])}

### Description
{grant.get('description', 'No description available')[:2000]}

### Eligibility
{grant.get('eligibility', 'Not specified')[:500]}

### Requirements
{json.dumps(grant.get('requirements', {}), indent=2)[:500] if grant.get('requirements') else 'Not specified'}
"""
        
        return f"""Score this grant opportunity for the organization.

{org_context}

{grant_context}

Evaluate across these dimensions (points available):
1. **Mission Alignment** (0-30): How well does this grant align with the org's mission and focus areas?
2. **Target Population** (0-20): Does the grant serve the same demographics/beneficiaries?
3. **Geographic Coverage** (0-15): Does geographic scope match?
4. **Funding Fit** (0-15): Is the funding amount appropriate for org's capacity?
5. **Eligibility** (0-10): Does the org meet stated requirements?
6. **Strategic Value** (0-10): Timing, funder relationship potential, strategic opportunity

Guidelines:
- A score of 80+ means "definitely apply"
- A score of 50-79 means "worth considering"
- A score below 30 means "likely not a fit"

Respond with JSON only."""
    
    def _score_rule_based(self, grant: Dict[str, Any]) -> ScoringResult:
        """Fallback rule-based scoring when LLM is unavailable"""
        
        title = (grant.get("title") or "").lower()
        description = (grant.get("description") or "").lower()
        eligibility = (grant.get("eligibility") or "").lower()
        full_text = f"{title} {description} {eligibility}"
        
        # Mission alignment (0-30)
        focus_areas = [f.lower() for f in self.org_profile.get("focus_areas", [])]
        programs = [p.lower() for p in self.org_profile.get("programs", [])]
        
        mission_keywords = set()
        for area in focus_areas + programs:
            # Add both multi-word phrases and individual words
            mission_keywords.add(area)
            for word in area.split():
                if len(word) > 3:  # Skip short words
                    mission_keywords.add(word)
        
        mission_matches = sum(1 for kw in mission_keywords if kw in full_text)
        mission_score = min(30, mission_matches * 3)
        
        # Target population (0-20) - use keyword expansion
        demographics = [d.lower() for d in self.org_profile.get("target_demographics", [])]
        
        # Expand demographics to common synonyms
        demo_keywords = set()
        demo_synonyms = {
            "unemployed": ["unemployed", "jobless", "out of work", "displaced"],
            "underemployed": ["underemployed", "underserved", "low-income", "low income", "disadvantaged"],
            "underrepresented": ["underrepresented", "underserved", "minority", "diverse", "diversity"],
            "low-income": ["low-income", "low income", "poverty", "economically disadvantaged", "lmi"],
            "adults": ["adult", "adults"],
            "career change": ["career change", "career changer", "career transition", "nontraditional"],
            "veterans": ["veteran", "veterans", "military"],
            "women": ["women", "woman", "female"],
        }
        
        for demo in demographics:
            demo_keywords.add(demo)
            for key, synonyms in demo_synonyms.items():
                if key in demo:
                    demo_keywords.update(synonyms)
        
        demo_matches = sum(1 for kw in demo_keywords if kw in full_text)
        population_score = min(20, demo_matches * 4)
        
        # Geographic (0-15)
        geo_focus = [g.lower() for g in self.org_profile.get("geographic_focus", [])]
        grant_geo = (grant.get("geographic_focus") or "").lower()
        geo_score = 10 if any(g in grant_geo or g in full_text for g in geo_focus) else 5
        
        # Funding fit (0-15)
        amount_max = grant.get("amount_max", 0) or 0
        if 100000 <= amount_max <= 2000000:
            funding_score = 15
        elif 50000 <= amount_max <= 5000000:
            funding_score = 10
        elif amount_max > 0:
            funding_score = 5
        else:
            funding_score = 8  # Unknown amount, give moderate score
        
        # Eligibility (0-10) - assume eligible unless known otherwise
        eligibility_score = 8
        
        # Strategic value (0-10)
        strategic_score = 5  # Default
        
        breakdown = ScoreBreakdown(
            mission_alignment=mission_score,
            target_population=population_score,
            geographic_coverage=geo_score,
            funding_fit=funding_score,
            eligibility=eligibility_score,
            strategic_value=strategic_score,
        )
        
        # Generate simple reasoning
        if breakdown.total >= 70:
            reasoning = f"Strong match based on {mission_matches} keyword alignments with org focus areas and {demo_matches} demographic matches."
        elif breakdown.total >= 50:
            reasoning = f"Moderate match with {mission_matches} keyword alignments. Review for strategic fit."
        elif breakdown.total >= 35:
            reasoning = f"Partial match with {mission_matches} keyword alignments. May require closer review."
        else:
            reasoning = f"Weak match. Limited alignment with organization's focus areas and programs."
        
        return ScoringResult(
            grant_id=grant.get("id", "unknown"),
            match_score=breakdown.total,
            score_breakdown=breakdown,
            reasoning=reasoning,
            summary=f"Grant from {grant.get('funder', 'Unknown funder')} for {grant.get('title', 'unknown purpose')[:100]}",
            key_tags=self._extract_tags(full_text),
            effort_estimate=self._estimate_effort(grant),
            winning_strategies=[],
            processing_time_ms=0,
            model_tokens_used=0,
        )
    
    def _extract_tags(self, text: str) -> List[str]:
        """Extract relevant tags from grant text"""
        tag_keywords = {
            "workforce": ["workforce", "employment", "job", "career"],
            "education": ["education", "training", "learning", "curriculum"],
            "technology": ["technology", "tech", "digital", "software", "cyber"],
            "youth": ["youth", "young", "student", "teen"],
            "underserved": ["underserved", "underrepresented", "low-income", "disadvantaged"],
            "urban": ["urban", "city", "metro"],
            "federal": ["federal", "government"],
            "stem": ["stem", "science", "engineering", "math"],
            "equity": ["equity", "diversity", "inclusion", "dei"],
        }
        
        tags = []
        for tag, keywords in tag_keywords.items():
            if any(kw in text for kw in keywords):
                tags.append(tag)
        
        return tags[:5]
    
    def _estimate_effort(self, grant: Dict[str, Any]) -> str:
        """Estimate application effort level"""
        # Heuristics based on funder and requirements
        funder = (grant.get("funder") or "").lower()
        requirements = grant.get("requirements") or {}
        
        # Federal grants typically require more effort
        if "federal" in funder or grant.get("source") == "grants_gov":
            return "high"
        
        # Foundation grants vary
        if isinstance(requirements, dict) and len(requirements) > 5:
            return "high"
        elif isinstance(requirements, dict) and len(requirements) > 2:
            return "medium"
        
        return "low"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        avg_time = (
            self.stats["total_time_ms"] / self.stats["grants_processed"]
            if self.stats["grants_processed"] > 0 else 0
        )
        
        # Estimate cost (Claude Sonnet: ~$3/M input, $15/M output)
        est_cost = (self.stats["total_tokens"] / 1_000_000) * 9  # Rough average
        
        return {
            **self.stats,
            "avg_processing_time_ms": avg_time,
            "estimated_cost_usd": round(est_cost, 4),
        }


# Convenience function for single grant scoring
def score_single_grant(
    grant: Dict[str, Any],
    org_id: str,
    workspace_root: str = "/var/fundfish/workspaces"
) -> ScoringResult:
    """Score a single grant for an organization"""
    agent = ScoringAgent(org_id, workspace_root)
    return agent.score_grant(grant)
