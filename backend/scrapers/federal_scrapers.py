"""
Federal grant database scrapers (SAM.gov, USASpending, etc.)
"""

import asyncio
import requests
import os
from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SAMGovScraper:
    """
    Scraper for SAM.gov procurement and grant opportunities
    API: api.sam.gov/prod/opportunities/v2/search
    Documentation: https://open.gsa.gov/api/get-opportunities-public-api/

    Note: Full API access requires API key from sam.gov
    Public access available with rate limiting
    """

    def __init__(self):
        self.api_url = "https://api.sam.gov/prod/opportunities/v2/search"
        self.base_web_url = "https://sam.gov/opp"
        self.api_key = os.getenv("SAM_GOV_API_KEY")  # Optional

    async def scrape(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Scrape opportunities from SAM.gov"""
        try:
            loop = asyncio.get_event_loop()
            grants = await loop.run_in_executor(None, self._fetch_opportunities, limit)
            return grants

        except Exception as e:
            logger.error(f"SAM.gov scraper error: {e}")
            return []

    def _fetch_opportunities(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch opportunities from SAM.gov API"""
        try:
            # SAM.gov API parameters
            params = {
                'limit': min(limit, 100),  # API max is 100
                'postedFrom': (datetime.now() - timedelta(days=30)).strftime('%m/%d/%Y'),
                'postedTo': datetime.now().strftime('%m/%d/%Y'),
                'ptype': 'g',  # Grants (also: 'o' for contracts, 's' for special notices)
                'ncode': '611,541',  # NAICS codes for education/training services
            }

            headers = {
                'User-Agent': 'FundraisingCRO/1.0',
                'Accept': 'application/json'
            }

            # Add API key if available
            if self.api_key:
                headers['X-Api-Key'] = self.api_key
                params['api_key'] = self.api_key

            logger.info(f"Fetching SAM.gov opportunities (API key: {'yes' if self.api_key else 'no'})...")

            response = requests.get(
                self.api_url,
                params=params,
                headers=headers,
                timeout=30
            )

            logger.info(f"SAM.gov API status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                return self._parse_sam_response(data)
            elif response.status_code == 403:
                logger.warning("SAM.gov API key required or rate limited")
                return []
            else:
                logger.warning(f"SAM.gov API returned {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error fetching SAM.gov opportunities: {e}")
            return []

    def _parse_sam_response(self, data: Dict) -> List[Dict[str, Any]]:
        """Parse SAM.gov API response"""
        grants = []

        try:
            opportunities = data.get('opportunitiesData', [])

            for opp in opportunities:
                # Extract opportunity details
                notice_id = opp.get('noticeId', '')
                solicitation_number = opp.get('solicitationNumber', '')

                grant = {
                    "id": f"sam-{solicitation_number or notice_id}",
                    "title": opp.get('title', 'Federal Grant Opportunity'),
                    "funder": opp.get('department', opp.get('subtier', 'Federal Agency')),
                    "amount": self._parse_amount(opp.get('awardAmount', '') or opp.get('awardCeiling', '')),
                    "deadline": self._parse_date(opp.get('responseDeadLine', '')),
                    "match_score": self._calculate_match_score(opp.get('title', '')),
                    "description": self._clean_description(opp.get('description', '')),
                    "requirements": self._extract_requirements(opp.get('naics', []), opp.get('typeOfSetAside', '')),
                    "contact": opp.get('pointOfContact', [{}])[0].get('email', '') if opp.get('pointOfContact') else '',
                    "application_url": f"https://sam.gov/opp/{notice_id}/view"
                }
                grants.append(grant)

        except Exception as e:
            logger.error(f"Error parsing SAM.gov response: {e}")

        return grants

    def _parse_amount(self, amount_str: str) -> int:
        """Parse amount from various formats"""
        try:
            import re
            if not amount_str:
                return 250000
            clean = re.sub(r'[^\d.]', '', str(amount_str))
            if clean:
                return int(float(clean))
        except:
            pass
        return 250000

    def _parse_date(self, date_str: str) -> str:
        """Parse date to YYYY-MM-DD"""
        try:
            # SAM.gov uses various formats
            for fmt in ['%Y-%m-%dT%H:%M:%S', '%m/%d/%Y', '%Y-%m-%d']:
                try:
                    dt = datetime.strptime(str(date_str)[:19], fmt)
                    return dt.strftime('%Y-%m-%d')
                except:
                    continue
        except:
            pass
        return (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d')

    def _calculate_match_score(self, title: str) -> int:
        """Calculate relevance score"""
        keywords = ['technology', 'workforce', 'training', 'education', 'STEM', 'digital', 'cyber']
        title_lower = title.lower()
        matches = sum(1 for kw in keywords if kw.lower() in title_lower)
        return min(95, 70 + (matches * 5))

    def _clean_description(self, desc: str) -> str:
        """Clean HTML and extra whitespace from description"""
        import re
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', desc)
        # Remove extra whitespace
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()[:500]  # Limit to 500 chars

    def _extract_requirements(self, naics_codes: List, set_aside: str) -> List[str]:
        """Extract requirements from NAICS and set-aside info"""
        requirements = []

        if set_aside:
            requirements.append(f"Set-aside type: {set_aside}")

        if naics_codes:
            requirements.append(f"NAICS codes: {', '.join(str(n.get('code', '')) for n in naics_codes[:3])}")

        if not requirements:
            requirements = ["See full opportunity details on SAM.gov"]

        return requirements[:4]


class USASpendingScraper:
    """
    Scraper for USASpending.gov grant awards database
    API: api.usaspending.gov
    Documentation: https://api.usaspending.gov/docs/endpoints

    Note: This provides historical grant data for pattern analysis
    Use to identify active funders and typical award amounts
    """

    def __init__(self):
        self.search_url = "https://api.usaspending.gov/api/v2/search/spending_by_award"
        self.award_url = "https://api.usaspending.gov/api/v2/awards"

    async def scrape(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Scrape recent grant awards from USASpending.gov

        Returns historical grants for pattern analysis
        """
        try:
            loop = asyncio.get_event_loop()
            grants = await loop.run_in_executor(None, self._fetch_awards, limit)
            return grants

        except Exception as e:
            logger.error(f"USASpending scraper error: {e}")
            return []

    def _fetch_awards(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch grant awards from USASpending API"""
        try:
            # USASpending v2 API payload
            payload = {
                "filters": {
                    "award_type_codes": ["02", "03", "04", "05"],  # Grant types: B, C, D, E
                    "time_period": [
                        {
                            "start_date": (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d'),
                            "end_date": datetime.now().strftime('%Y-%m-%d'),
                            "date_type": "action_date"
                        }
                    ],
                    "keywords": ["technology", "workforce", "education", "training", "STEM"]
                },
                "fields": [
                    "Award ID",
                    "Recipient Name",
                    "Award Amount",
                    "Description",
                    "Awarding Agency",
                    "Period of Performance Start Date",
                    "Award Type"
                ],
                "page": 1,
                "limit": min(limit, 100),
                "sort": "Award Amount",
                "order": "desc"
            }

            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'FundraisingCRO/1.0'
            }

            logger.info("Fetching USASpending grant awards...")

            response = requests.post(
                self.search_url,
                json=payload,
                headers=headers,
                timeout=30
            )

            logger.info(f"USASpending API status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                return self._parse_awards(data)
            else:
                logger.warning(f"USASpending API returned {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error fetching USASpending awards: {e}")
            return []

    def _parse_awards(self, data: Dict) -> List[Dict[str, Any]]:
        """Parse USASpending API response into grant format"""
        grants = []

        try:
            results = data.get('results', [])

            for result in results:
                # Extract award details
                award_id = result.get('Award ID', result.get('generated_internal_id', ''))
                recipient = result.get('Recipient Name', 'Unknown')
                awarding_agency = result.get('Awarding Agency', result.get('awarding_agency_name', 'Federal Agency'))
                amount = result.get('Award Amount', result.get('total_obligation', 0))
                description = result.get('Description', result.get('description', ''))

                # Note: These are historical awards, not active opportunities
                # But can help identify funders actively giving grants in our space
                grant = {
                    "id": f"usa-spending-{award_id}",
                    "title": f"Historical Grant: {description[:100] if description else 'Technology Grant'}",
                    "funder": awarding_agency,
                    "amount": self._parse_amount(amount),
                    "deadline": "Historical",  # These are past awards
                    "match_score": 75,  # Lower score since these are historical
                    "description": f"Historical grant awarded to {recipient}. {description[:200]}",
                    "requirements": ["Historical data - for pattern analysis only"],
                    "contact": "See agency website for current opportunities",
                    "application_url": f"https://www.usaspending.gov/award/{award_id}"
                }
                grants.append(grant)

        except Exception as e:
            logger.error(f"Error parsing USASpending data: {e}")

        return grants

    def _parse_amount(self, amount) -> int:
        """Parse amount to integer"""
        try:
            if isinstance(amount, (int, float)):
                return int(amount)
            elif isinstance(amount, str):
                import re
                clean = re.sub(r'[^\d.]', '', amount)
                return int(float(clean)) if clean else 250000
        except:
            pass
        return 250000


class NSFScraper:
    """Scraper for National Science Foundation grants"""

    def __init__(self):
        self.api_url = "https://www.research.gov/awardapi-service/v1/awards.json"

    async def scrape(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Scrape NSF grant opportunities

        NSF has specific programs like ATE (Advanced Technological Education)
        that align well with Per Scholas mission
        """
        try:
            loop = asyncio.get_event_loop()
            grants = await loop.run_in_executor(None, self._fetch_nsf_opportunities, limit)
            return grants

        except Exception as e:
            logger.error(f"NSF scraper error: {e}")
            return []

    def _fetch_nsf_opportunities(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch NSF opportunities"""
        try:
            # NSF has both an awards API (historical) and opportunity announcements
            # For current opportunities, would typically scrape nsf.gov/funding

            # Return mock data for now
            return [
                {
                    "id": "nsf-ate-2025",
                    "title": "Advanced Technological Education (ATE) Program",
                    "funder": "National Science Foundation",
                    "amount": 600000,
                    "deadline": (datetime.now() + timedelta(days=120)).strftime('%Y-%m-%d'),
                    "match_score": 92,
                    "description": "The ATE program focuses on the education of technicians for high-technology fields that drive the nation's economy.",
                    "requirements": ["Two-year institution involvement", "STEM focus", "Industry partnerships"],
                    "contact": "ate@nsf.gov",
                    "application_url": "https://nsf.gov/funding/pgm_summ.jsp?pims_id=5464"
                }
            ]

        except Exception as e:
            logger.error(f"Error fetching NSF opportunities: {e}")
            return []
