"""
Grants.gov scraper using the official API
Reuses existing GrantsGovService logic with multi-keyword search
"""

import asyncio
from typing import List, Dict, Any
from grants_service import GrantsGovService

# Import centralized keyword configuration
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from search_keywords import get_keywords_for_source


class GrantsGovScraper:
    """Scraper for Grants.gov federal opportunities with multi-keyword search"""

    def __init__(self):
        self.grants_service = GrantsGovService()

    async def scrape(self, keywords: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Scrape grants from Grants.gov using multi-keyword search
        
        Args:
            keywords: Optional single keyword (for backward compatibility)
            limit: Total number of grants to return
        """
        try:
            all_grants = []
            
            if keywords:
                # Single keyword search (backward compatibility)
                loop = asyncio.get_event_loop()
                grants = await loop.run_in_executor(
                    None, self.grants_service.search_grants, keywords, limit
                )
                return grants
            else:
                # Multi-keyword search using centralized keywords
                keyword_list = get_keywords_for_source('grants_gov')
                grants_per_keyword = max(1, limit // len(keyword_list))
                
                loop = asyncio.get_event_loop()
                
                for keyword in keyword_list:
                    try:
                        grants = await loop.run_in_executor(
                            None, self.grants_service.search_grants, keyword, grants_per_keyword
                        )
                        all_grants.extend(grants)
                        
                        # Small delay between searches
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        print(f"Error searching with keyword '{keyword}': {e}")
                        continue
                
                # Remove duplicates and limit results
                unique_grants = self._deduplicate_grants(all_grants)
                return unique_grants[:limit]
                
        except Exception as e:
            print(f"Grants.gov scraper error: {e}")
            return []

    def _deduplicate_grants(self, grants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate grants based on ID"""
        seen_ids = set()
        unique_grants = []
        
        for grant in grants:
            grant_id = grant.get('id')
            if grant_id and grant_id not in seen_ids:
                seen_ids.add(grant_id)
                unique_grants.append(grant)
        
        return unique_grants

import asyncio
from typing import List, Dict, Any
from grants_service import GrantsGovService


class GrantsGovScraper:
    """Scraper for Grants.gov federal opportunities"""

    def __init__(self):
        self.grants_service = GrantsGovService()

    async def scrape(self, keywords: str = "technology workforce", limit: int = 10) -> List[Dict[str, Any]]:
        """
        Scrape grants from Grants.gov

        Args:
            keywords: Search keywords
            limit: Maximum number of grants to return

        Returns:
            List of grant opportunities
        """
        # Run the synchronous search in a thread pool
        loop = asyncio.get_event_loop()
        grants = await loop.run_in_executor(
            None,
            self.grants_service.search_grants,
            keywords,
            limit
        )

        return grants
