"""
Grants.gov Discovery Agent

Implements browser-based grant discovery for Grants.gov using LLM vision.
Uses the DiscoveryAgent base class for self-healing scraping.

This agent:
1. Navigates to Grants.gov search
2. Filters for recent opportunities (last 7 days or custom)
3. Extracts structured data from search results
4. Gets detailed info from individual grant pages
5. Writes to scraped_grants table
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, quote

from .discovery_agent import DiscoveryAgent, ScrapedGrant, CostTracker


class GrantsGovAgent(DiscoveryAgent):
    """
    Discovery agent for Grants.gov federal grant opportunities.
    
    Uses LLM vision to:
    - Navigate the search interface
    - Parse search results dynamically
    - Extract detailed grant information
    - Handle pagination and filters
    """
    
    SEARCH_URL = "https://www.grants.gov/search-grants"
    API_URL = "https://api.grants.gov/v1/api/search2"
    DETAIL_API_URL = "https://api.grants.gov/v1/api/fetchOpportunity"
    
    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        headless: bool = True,
        use_api_fallback: bool = True,  # Use API when available for efficiency
        **kwargs
    ):
        super().__init__(model=model, headless=headless, **kwargs)
        self.use_api_fallback = use_api_fallback
    
    @property
    def source_name(self) -> str:
        return "grants_gov"
    
    @property
    def base_url(self) -> str:
        return "https://www.grants.gov"
    
    async def discover(
        self,
        keywords: List[str] = None,
        days_back: int = 7,
        max_grants: int = 50,
        use_vision: bool = True
    ) -> List[ScrapedGrant]:
        """
        Discover recent grant opportunities from Grants.gov.
        
        Args:
            keywords: List of search keywords. Defaults to workforce/technology terms.
            days_back: How many days back to search (default 7)
            max_grants: Maximum grants to return
            use_vision: Whether to use LLM vision for extraction (slower but more robust)
        
        Returns:
            List of ScrapedGrant objects
        """
        if keywords is None:
            keywords = [
                "workforce development",
                "technology training",
                "STEM education",
                "job training",
                "digital skills"
            ]
        
        all_grants = []
        seen_ids = set()
        
        print(f"[{self.source_name}] Starting discovery for {len(keywords)} keywords, last {days_back} days")
        
        for keyword in keywords:
            if len(all_grants) >= max_grants:
                break
                
            try:
                print(f"[{self.source_name}] Searching: '{keyword}'")
                
                # Try API first if available (more efficient)
                if self.use_api_fallback:
                    grants = await self._search_via_api(keyword, days_back)
                else:
                    grants = await self._search_via_browser(keyword, days_back, use_vision)
                
                # Deduplicate
                for grant in grants:
                    if grant.opportunity_id not in seen_ids:
                        seen_ids.add(grant.opportunity_id)
                        all_grants.append(grant)
                        
                        if len(all_grants) >= max_grants:
                            break
                
                # Rate limiting between keyword searches
                await self.wait_and_retry()
                
            except Exception as e:
                self.log_error('search', f"Failed to search '{keyword}': {e}")
                continue
        
        print(f"[{self.source_name}] Discovery complete: {len(all_grants)} unique grants found")
        return all_grants[:max_grants]
    
    async def _search_via_api(
        self, 
        keyword: str, 
        days_back: int,
        limit: int = 25
    ) -> List[ScrapedGrant]:
        """
        Search using Grants.gov REST API.
        More efficient than browser scraping when API is available.
        """
        import aiohttp
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        payload = {
            "keyword": keyword,
            "oppStatuses": "posted|forecasted",
            "rows": limit,
            "sortBy": "openDate|desc"  # Most recent first
        }
        
        headers = {
            'User-Agent': 'FundFish-DiscoveryAgent/1.0',
            'Content-Type': 'application/json'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.API_URL, 
                    json=payload, 
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        print(f"[{self.source_name}] API returned status {response.status}")
                        return []
                    
                    data = await response.json()
                    
                    if 'data' not in data or 'oppHits' not in data['data']:
                        print(f"[{self.source_name}] Unexpected API response format")
                        return []
                    
                    grants = []
                    for hit in data['data']['oppHits']:
                        # Filter by date if posted date is available
                        posted = hit.get('openDate') or hit.get('postedDate')
                        if posted:
                            try:
                                posted_dt = datetime.strptime(posted[:10], '%Y-%m-%d')
                                if posted_dt < start_date:
                                    continue  # Skip grants older than our window
                            except (ValueError, TypeError):
                                pass  # Include if we can't parse the date
                        
                        grant = await self._parse_api_hit(hit)
                        if grant:
                            grants.append(grant)
                    
                    print(f"[{self.source_name}] API found {len(grants)} grants for '{keyword}'")
                    return grants
                    
        except Exception as e:
            self.log_error('api', f"API search failed: {e}")
            return []
    
    async def _parse_api_hit(self, hit: Dict[str, Any]) -> Optional[ScrapedGrant]:
        """Parse a single API search result into ScrapedGrant"""
        try:
            opp_id = hit.get('number') or hit.get('opportunityNumber') or str(hit.get('id', ''))
            if not opp_id:
                return None
            
            # Clean HTML entities from title
            title = hit.get('title') or hit.get('opportunityTitle', 'Untitled Grant')
            title = self._clean_html(title)
            
            # Get funder/agency
            funder = hit.get('agency') or hit.get('agencyName', 'Unknown Agency')
            funder = self._clean_html(funder)
            
            # Parse deadline
            deadline = None
            close_date = hit.get('closeDate')
            if close_date:
                try:
                    deadline = close_date[:10]  # YYYY-MM-DD
                except (TypeError, IndexError):
                    pass
            
            # Build application URL
            internal_id = hit.get('id')
            app_url = f"https://www.grants.gov/search-results-detail/{internal_id}" if internal_id else None
            
            # Get detailed info if available
            details = await self._fetch_opportunity_details(internal_id) if internal_id else {}
            
            return ScrapedGrant(
                opportunity_id=opp_id,
                title=title,
                funder=funder,
                agency=funder,
                source=self.source_name,
                deadline=deadline,
                application_url=app_url,
                description=self._clean_html(details.get('description', '')),
                eligibility=details.get('eligibility'),
                amount_min=details.get('award_floor'),
                amount_max=details.get('award_ceiling'),
                contact_email=details.get('contact_email'),
                contact_name=details.get('contact_name'),
                posted_date=hit.get('openDate', '')[:10] if hit.get('openDate') else None,
                extraction_confidence=0.9  # High confidence for API data
            )
            
        except Exception as e:
            self.log_error('parse', f"Failed to parse API hit: {e}", {'hit_id': hit.get('id')})
            return None
    
    async def _fetch_opportunity_details(self, opportunity_id: str) -> Dict[str, Any]:
        """Fetch detailed opportunity info from API"""
        import aiohttp
        
        if not opportunity_id:
            return {}
        
        try:
            payload = {"opportunityId": int(opportunity_id)}
            headers = {
                'User-Agent': 'FundFish-DiscoveryAgent/1.0',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.DETAIL_API_URL,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status != 200:
                        return {}
                    
                    data = await response.json()
                    synopsis = data.get('data', {}).get('synopsis', {})
                    
                    return {
                        'description': self._clean_html(synopsis.get('synopsisDesc', '')),
                        'eligibility': self._clean_html(synopsis.get('applicantEligibilityDesc', '')),
                        'award_floor': self._parse_amount(synopsis.get('awardFloor')),
                        'award_ceiling': self._parse_amount(synopsis.get('awardCeiling')),
                        'contact_email': synopsis.get('agencyContactEmail', ''),
                        'contact_name': synopsis.get('agencyContactName', ''),
                        'cost_sharing': synopsis.get('costSharingOrMatchingRequirement', '') == 'Yes'
                    }
                    
        except Exception as e:
            print(f"[{self.source_name}] Could not fetch details for {opportunity_id}: {e}")
            return {}
    
    async def _search_via_browser(
        self,
        keyword: str,
        days_back: int,
        use_vision: bool = True
    ) -> List[ScrapedGrant]:
        """
        Search using browser automation with LLM vision.
        More robust to layout changes but slower and more expensive.
        """
        if not self.page:
            raise RuntimeError("Browser not started")
        
        # Navigate to search page
        await self.page.goto(self.SEARCH_URL, wait_until='networkidle')
        await asyncio.sleep(1)  # Wait for dynamic content
        
        # Take screenshot for analysis
        screenshot = await self.take_screenshot()
        
        if use_vision:
            # Use LLM vision to understand and interact with the page
            grants = await self._extract_with_vision(screenshot, keyword, days_back)
        else:
            # Fall back to basic text extraction
            grants = await self._extract_from_text(keyword)
        
        return grants
    
    async def _extract_with_vision(
        self,
        screenshot: bytes,
        keyword: str,
        days_back: int
    ) -> List[ScrapedGrant]:
        """
        Use LLM vision to understand the page and extract grant data.
        This is the self-healing approach - works even if the layout changes.
        """
        # First, find and fill the search box
        search_prompt = f"""Look at this Grants.gov search page screenshot.
        
I need to search for grants with keyword: "{keyword}"

Find the search input field and tell me how to interact with it.
Return JSON:
{{
    "search_input": {{
        "found": true/false,
        "selector_type": "css" | "text" | "aria" | "placeholder",
        "selector": "the selector or identifier",
        "already_has_text": true/false
    }},
    "search_button": {{
        "found": true/false,
        "selector_type": "css" | "text" | "aria",
        "selector": "the selector"
    }},
    "current_results_visible": true/false,
    "filters_visible": true/false
}}"""

        search_analysis = await self.analyze_with_vision(screenshot, search_prompt)
        
        try:
            analysis = json.loads(
                search_analysis[search_analysis.find('{'):search_analysis.rfind('}')+1]
            )
            
            # Try to fill search and submit
            search_input = analysis.get('search_input', {})
            search_button = analysis.get('search_button', {})
            
            if search_input.get('found'):
                # Clear and fill search
                if search_input['selector_type'] == 'placeholder':
                    await self.page.fill(f'[placeholder*="{search_input["selector"]}"]', keyword)
                elif search_input['selector_type'] == 'css':
                    await self.page.fill(search_input['selector'], keyword)
                elif search_input['selector_type'] == 'aria':
                    await self.page.fill(f'[aria-label*="{search_input["selector"]}"]', keyword)
                
                await asyncio.sleep(0.5)
                
                # Click search button
                if search_button.get('found'):
                    await self.click_element(search_button)
                else:
                    # Try pressing Enter
                    await self.page.keyboard.press('Enter')
                
                # Wait for results
                await self.page.wait_for_load_state('networkidle')
                await asyncio.sleep(2)  # Extra wait for dynamic content
                
        except (json.JSONDecodeError, Exception) as e:
            self.log_error('vision', f"Could not parse search analysis: {e}")
            # Fall back to common selectors
            try:
                await self.page.fill('input[type="text"]', keyword)
                await self.page.keyboard.press('Enter')
                await self.page.wait_for_load_state('networkidle')
            except Exception:
                pass
        
        # Take screenshot of results
        await asyncio.sleep(1)
        results_screenshot = await self.take_screenshot()
        
        # Extract grants from results page
        extract_prompt = """Look at this Grants.gov search results page.

Extract ALL visible grant opportunities. For each grant, extract:
- opportunity_id (the grant number/ID)
- title (the grant title)
- funder/agency (the funding organization)
- deadline (close date, if visible)
- posted_date (when it was posted, if visible)
- amount (award ceiling/floor if visible)
- brief description (if visible in the listing)

Return JSON array:
[
    {
        "opportunity_id": "...",
        "title": "...",
        "funder": "...",
        "deadline": "YYYY-MM-DD or null",
        "posted_date": "YYYY-MM-DD or null",
        "amount_max": number or null,
        "description": "..." or null
    },
    ...
]

Extract as many grants as you can see in the results. Be thorough."""

        results_analysis = await self.analyze_with_vision(results_screenshot, extract_prompt)
        
        grants = []
        try:
            # Parse the JSON array
            json_start = results_analysis.find('[')
            json_end = results_analysis.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                grant_list = json.loads(results_analysis[json_start:json_end])
                
                for g in grant_list:
                    grant = ScrapedGrant(
                        opportunity_id=g.get('opportunity_id', f'visual-{len(grants)}'),
                        title=g.get('title', 'Unknown Title'),
                        funder=g.get('funder', 'Unknown Funder'),
                        source=self.source_name,
                        deadline=g.get('deadline'),
                        posted_date=g.get('posted_date'),
                        amount_max=g.get('amount_max'),
                        description=g.get('description'),
                        extraction_confidence=0.75  # Lower confidence for vision extraction
                    )
                    grants.append(grant)
                
        except (json.JSONDecodeError, Exception) as e:
            self.log_error('extraction', f"Could not parse grant extraction: {e}")
        
        print(f"[{self.source_name}] Vision extracted {len(grants)} grants for '{keyword}'")
        return grants
    
    async def _extract_from_text(self, keyword: str) -> List[ScrapedGrant]:
        """Fallback: extract grants from page text content"""
        page_text = await self.get_page_text()
        
        prompt = f"""Extract grant opportunities from this Grants.gov page text.
        
The user searched for: "{keyword}"

For each grant found, extract:
- opportunity_id (grant number)
- title
- funder/agency
- deadline (if mentioned)
- any description

Return JSON array of grants. If no grants found, return empty array []."""

        response = await self.reason_about_text(page_text[:15000], prompt)  # Limit text size
        
        try:
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                grant_list = json.loads(response[json_start:json_end])
                
                return [
                    ScrapedGrant(
                        opportunity_id=g.get('opportunity_id', f'text-{i}'),
                        title=g.get('title', 'Unknown'),
                        funder=g.get('funder', 'Unknown'),
                        source=self.source_name,
                        deadline=g.get('deadline'),
                        description=g.get('description'),
                        extraction_confidence=0.6
                    )
                    for i, g in enumerate(grant_list)
                ]
        except (json.JSONDecodeError, Exception):
            pass
        
        return []
    
    def _clean_html(self, text: str) -> str:
        """Remove HTML tags and entities from text"""
        if not text:
            return ""
        
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', str(text))
        # Replace common entities
        clean = clean.replace('&amp;', '&')
        clean = clean.replace('&lt;', '<')
        clean = clean.replace('&gt;', '>')
        clean = clean.replace('&quot;', '"')
        clean = clean.replace('&nbsp;', ' ')
        # Remove remaining entities
        clean = re.sub(r'&[a-zA-Z0-9#]+;', '', clean)
        # Collapse whitespace
        clean = re.sub(r'\s+', ' ', clean)
        
        return clean.strip()
    
    def _parse_amount(self, amount) -> Optional[int]:
        """Parse funding amount to integer"""
        if not amount:
            return None
        try:
            if isinstance(amount, (int, float)):
                return int(amount)
            # Remove non-numeric characters
            clean = re.sub(r'[^\d.]', '', str(amount))
            if clean:
                return int(float(clean))
        except (ValueError, TypeError):
            pass
        return None


async def run_grants_gov_discovery(
    keywords: List[str] = None,
    days_back: int = 7,
    max_grants: int = 50,
    use_api: bool = True,
    supabase_client=None
) -> Dict[str, Any]:
    """
    Convenience function to run Grants.gov discovery.
    
    Args:
        keywords: Search keywords (defaults to workforce/tech terms)
        days_back: How many days back to search
        max_grants: Maximum grants to return
        use_api: Whether to use API (faster) or browser (more robust)
        supabase_client: Optional Supabase client for database storage
    
    Returns:
        Discovery results including grants, costs, and errors
    """
    agent = GrantsGovAgent(
        headless=True,
        use_api_fallback=use_api,
        supabase_client=supabase_client
    )
    
    return await agent.run(
        keywords=keywords,
        days_back=days_back,
        max_grants=max_grants,
        use_vision=not use_api  # Use vision for browser mode
    )


# Self-healing test utilities
class SelfHealingTest:
    """
    Utilities for testing the self-healing capabilities of the agent.
    Simulates layout changes and verifies the agent adapts.
    """
    
    @staticmethod
    def create_modified_html(original_html: str, modification_type: str) -> str:
        """
        Modify HTML to simulate layout changes.
        
        modification_type:
        - 'class_rename': Change CSS class names
        - 'id_change': Change element IDs
        - 'structure_change': Rearrange DOM structure
        - 'new_wrapper': Add wrapper divs
        """
        if modification_type == 'class_rename':
            # Change common class names
            modified = original_html.replace('search-results', 'opp-listings')
            modified = modified.replace('grant-title', 'opportunity-name')
            modified = modified.replace('grant-card', 'funding-item')
            return modified
            
        elif modification_type == 'id_change':
            # Change element IDs
            modified = original_html.replace('id="searchInput"', 'id="keywordField"')
            modified = modified.replace('id="results"', 'id="opportunityList"')
            return modified
            
        elif modification_type == 'structure_change':
            # This would require more complex DOM manipulation
            # For testing, we'll just add some wrapper divs
            modified = original_html.replace(
                '<div class="results">',
                '<section class="new-layout"><div class="inner-wrapper"><div class="results">'
            )
            return modified
            
        elif modification_type == 'new_wrapper':
            modified = original_html.replace(
                '<div class="grant-card',
                '<article class="opportunity-wrapper"><div class="grant-card'
            )
            return modified
        
        return original_html
    
    @staticmethod
    async def test_adaptation(agent: GrantsGovAgent, test_html: str) -> Dict[str, Any]:
        """
        Test if the agent can extract data from modified HTML.
        Returns success rate and extraction details.
        """
        # This would need a local test server to serve modified HTML
        # For now, we document the approach
        return {
            'test_type': 'self_healing',
            'note': 'Requires local test server with modified HTML',
            'approach': 'Agent uses LLM vision to understand layout visually, not via selectors'
        }


if __name__ == "__main__":
    # Quick test
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    async def test():
        result = await run_grants_gov_discovery(
            keywords=["workforce development", "technology training"],
            days_back=7,
            max_grants=10,
            use_api=True
        )
        
        print(f"\n=== Discovery Results ===")
        print(f"Success: {result['success']}")
        print(f"Grants found: {result['grants_found']}")
        print(f"Cost analysis: {result['cost_analysis']}")
        print(f"Errors: {len(result['errors'])}")
        
        for grant in result.get('grants', [])[:5]:
            print(f"\n- {grant['title'][:60]}...")
            print(f"  Funder: {grant['funder']}")
            print(f"  Deadline: {grant.get('deadline', 'N/A')}")
    
    asyncio.run(test())
