"""
Grants.gov scraper using the official API
Reuses existing GrantsGovService logic
"""

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
