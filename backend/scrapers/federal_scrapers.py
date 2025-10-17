"""
Federal grant database scrapers (SAM.gov, USASpending, etc.)
"""

import asyncio
import requests
import os
from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging

# Import centralized keyword configuration
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from search_keywords import get_keywords_for_source

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
        # Correct SAM.gov public opportunities API endpoint
        self.api_url = "https://api.sam.gov/opportunities/v2/search"
        self.base_web_url = "https://sam.gov/opp"
        self.api_key = os.getenv("SAM_GOV_API_KEY")
        
        if not self.api_key:
            logger.warning("SAM_GOV_API_KEY not found. Using public access with rate limits.")
        else:
            logger.info("SAM.gov API key configured successfully")

    def test_connection(self) -> Dict[str, Any]:
        """Test the SAM.gov API connection and validate API key"""
        try:
            # Test with a minimal request using correct public API parameters
            params = {
                'api_key': self.api_key,
                'postedFrom': (datetime.now() - timedelta(days=7)).strftime('%m/%d/%Y'),
                'postedTo': datetime.now().strftime('%m/%d/%Y'),
                'limit': 1,
                'offset': 0
            }

            headers = {
                'User-Agent': 'FundraisingCRO/1.0',
                'Accept': 'application/json'
            }

            logger.info(f"Testing SAM.gov public API connection to: {self.api_url}")
            logger.info(f"Using API key: {bool(self.api_key)}")
            logger.info(f"Parameters: {params}")

            response = requests.get(
                self.api_url,
                params=params,
                headers=headers,
                timeout=15
            )

            logger.info(f"Response status: {response.status_code}")
            
            # Log response content for debugging (first 500 chars)
            try:
                response_text = response.text[:500]
                logger.info(f"Response preview: {response_text}")
            except:
                pass

            result = {
                'status_code': response.status_code,
                'authenticated': bool(self.api_key),
                'connection_successful': response.status_code == 200,
                'message': '',
                'response_preview': response.text[:200] if response.text else ''
            }

            if response.status_code == 200:
                try:
                    data = response.json()
                    total_records = data.get('totalRecords', 0)
                    opportunities_data = data.get('opportunitiesData', [])
                    result['message'] = f"Connection successful. {total_records} total opportunities available."
                    result['total_opportunities'] = total_records
                    result['returned_opportunities'] = len(opportunities_data)
                except Exception as json_err:
                    result['message'] = f"API responded but JSON parsing failed: {json_err}"
            elif response.status_code == 400:
                result['message'] = f"Bad request - check parameters: {response.text[:100]}"
            elif response.status_code == 401:
                result['message'] = "Invalid or expired API key"
            elif response.status_code == 403:
                result['message'] = "Access forbidden - check API key permissions"
            elif response.status_code == 429:
                result['message'] = "Rate limit exceeded"
            elif response.status_code == 500:
                result['message'] = "SAM.gov server error - API may be temporarily unavailable"
            else:
                result['message'] = f"API returned status {response.status_code}: {response.text[:100]}"

            return result

        except requests.exceptions.Timeout:
            return {
                'status_code': 0,
                'authenticated': bool(self.api_key),
                'connection_successful': False,
                'message': "Request timed out"
            }
        except requests.exceptions.ConnectionError as e:
            return {
                'status_code': 0,
                'authenticated': bool(self.api_key),
                'connection_successful': False,
                'message': f"Connection error: {str(e)}"
            }
        except Exception as e:
            return {
                'status_code': 0,
                'authenticated': bool(self.api_key),
                'connection_successful': False,
                'message': f"Unexpected error: {str(e)}"
            }

    async def scrape(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Scrape opportunities from SAM.gov using multi-keyword search"""
        try:
            loop = asyncio.get_event_loop()
            
            # Get SAM.gov-specific keywords
            keywords = get_keywords_for_source('sam_gov')
            logger.info(f"Using {len(keywords)} keywords for SAM.gov search")
            
            all_opportunities = []
            
            # Search with each keyword
            for keyword in keywords:
                try:
                    logger.info(f"Searching SAM.gov with keyword: '{keyword}'")
                    keyword_opportunities = await loop.run_in_executor(
                        None, self._fetch_opportunities_with_keyword, keyword, limit // len(keywords) + 1
                    )
                    all_opportunities.extend(keyword_opportunities)
                    
                    # Small delay between searches to be respectful to the API
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Keyword search failed for '{keyword}': {e}")
                    continue
            
            # Remove duplicates based on opportunity ID
            unique_opportunities = self._deduplicate_opportunities(all_opportunities)
            
            # Limit to requested number
            final_opportunities = unique_opportunities[:limit]
            
            logger.info(f"SAM.gov multi-keyword search completed: {len(final_opportunities)} unique opportunities found")
            return final_opportunities

        except Exception as e:
            logger.error(f"SAM.gov scraper error: {e}")
            return []

    async def scrape_with_keyword(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Scrape opportunities from SAM.gov using a specific keyword"""
        try:
            loop = asyncio.get_event_loop()
            opportunities = await loop.run_in_executor(
                None, self._fetch_opportunities_with_keyword, keyword, limit
            )
            logger.info(f"SAM.gov keyword '{keyword}' search: {len(opportunities)} opportunities found")
            return opportunities
        except Exception as e:
            logger.error(f"SAM.gov keyword search error for '{keyword}': {e}")
            return []

    def _fetch_opportunities_with_keyword(self, keyword: str, limit: int) -> List[Dict[str, Any]]:
        """Fetch opportunities from SAM.gov public API with specific keyword"""
        try:
            # SAM.gov public API parameters with keyword search
            params = {
                'api_key': self.api_key,
                'postedFrom': (datetime.now() - timedelta(days=30)).strftime('%m/%d/%Y'),
                'postedTo': datetime.now().strftime('%m/%d/%Y'),
                'limit': min(limit, 100),  # API max is 100 per request
                'offset': 0,
                'ptype': 'o,k,g',  # Solicitations, Combined Synopsis, Grants
                'title': keyword  # Search in title field
            }

            # Headers for the public API
            headers = {
                'User-Agent': 'FundraisingCRO/1.0',
                'Accept': 'application/json'
            }

            logger.info(f"Fetching SAM.gov opportunities for keyword '{keyword}'")

            response = requests.get(
                self.api_url,
                params=params,
                headers=headers,
                timeout=30
            )

            logger.info(f"SAM.gov API response for '{keyword}': {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    opportunities = self._parse_sam_response(data)
                    logger.info(f"Found {len(opportunities)} opportunities for keyword '{keyword}'")
                    return opportunities
                except ValueError as json_err:
                    logger.error(f"JSON parsing error for keyword '{keyword}': {json_err}")
                    return []
            else:
                logger.warning(f"SAM.gov API returned {response.status_code} for keyword '{keyword}'")
                return []

        except Exception as e:
            logger.error(f"Error fetching SAM.gov opportunities for keyword '{keyword}': {e}")
            return []

    def _deduplicate_opportunities(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate opportunities based on ID"""
        seen_ids = set()
        unique_opportunities = []
        
        for opp in opportunities:
            opp_id = opp.get('id')
            if opp_id and opp_id not in seen_ids:
                seen_ids.add(opp_id)
                unique_opportunities.append(opp)
        
        logger.info(f"Deduplicated {len(opportunities)} opportunities to {len(unique_opportunities)} unique")
        return unique_opportunities

    def _fetch_opportunities(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch opportunities from SAM.gov public API with enhanced authentication"""
        try:
            # SAM.gov public API parameters - correct format
            params = {
                'api_key': self.api_key,
                'postedFrom': (datetime.now() - timedelta(days=30)).strftime('%m/%d/%Y'),
                'postedTo': datetime.now().strftime('%m/%d/%Y'),
                'limit': min(limit, 1000),  # API max is 1000
                'offset': 0,
                'ptype': 'o,k,g'  # Solicitations, Combined Synopsis, Grants
            }

            # Headers for the public API
            headers = {
                'User-Agent': 'FundraisingCRO/1.0',
                'Accept': 'application/json'
            }

            logger.info(f"Fetching SAM.gov opportunities from: {self.api_url}")
            logger.info(f"API key configured: {bool(self.api_key)}")
            logger.info(f"Parameters: {params}")

            response = requests.get(
                self.api_url,
                params=params,
                headers=headers,
                timeout=30
            )

            logger.info(f"SAM.gov API response: {response.status_code}")
            
            # Log response details for debugging
            if response.status_code != 200:
                logger.error(f"Response content: {response.text[:500]}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    opportunities = self._parse_sam_response(data)
                    logger.info(f"Successfully fetched {len(opportunities)} opportunities from SAM.gov")
                    return opportunities
                except ValueError as json_err:
                    logger.error(f"JSON parsing error: {json_err}")
                    logger.error(f"Response content: {response.text[:500]}")
                    return []
            elif response.status_code == 400:
                logger.error(f"SAM.gov API: Bad request - {response.text[:200]}")
                return []
            elif response.status_code == 401:
                logger.error("SAM.gov API: Invalid or expired API key")
                return []
            elif response.status_code == 403:
                logger.warning("SAM.gov API: Access forbidden - check API key permissions")
                return []
            elif response.status_code == 429:
                logger.warning("SAM.gov API: Rate limit exceeded")
                return []
            elif response.status_code == 500:
                logger.warning("SAM.gov API: Server error - service may be temporarily unavailable")
                return []
            else:
                logger.warning(f"SAM.gov API returned {response.status_code}: {response.text[:200]}")
                return []

        except requests.exceptions.Timeout:
            logger.error("SAM.gov API request timed out")
            return []
        except requests.exceptions.ConnectionError:
            logger.error("SAM.gov API connection error")
            return []
        except Exception as e:
            logger.error(f"Error fetching SAM.gov opportunities: {e}")
            return []

    def _parse_sam_response(self, data: Dict) -> List[Dict[str, Any]]:
        """Parse SAM.gov public API response"""
        grants = []

        try:
            # Public API response structure
            opportunities = data.get('opportunitiesData', [])

            for opp in opportunities:
                # Extract opportunity details from public API response
                solicitation_number = opp.get('solicitationNumber', '')
                title = opp.get('title', 'Federal Grant Opportunity')
                notice_id = opp.get('noticeId', '')

                grant = {
                    "id": f"sam-{solicitation_number or notice_id}",
                    "title": title,
                    "funder": opp.get('fullParentPathName', 'Federal Agency'),
                    "amount": self._parse_amount(opp.get('data', {}).get('award', {}).get('amount', '')),
                    "deadline": self._parse_date(opp.get('reponseDeadLine', '')),  # Note: API has typo "reponse"
                    "match_score": self._calculate_match_score(title),
                    "description": f"https://api.sam.gov/opportunities/v2/{notice_id or solicitation_number}/description",
                    "requirements": self._extract_requirements(opp.get('naicsCode', ''), opp.get('setAsideCode', '')),
                    "contact": self._extract_contact(opp.get('data', {}).get('pointOfContact', [])),
                    "application_url": opp.get('uiLink', f"https://sam.gov/opp/{notice_id}/view"),
                    "posted_date": opp.get('postedDate', ''),
                    "type": opp.get('type', ''),
                    "active": opp.get('active', 'Yes') == 'Yes'
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

    def _calculate_match_score(self, title: str, description: str = '') -> int:
        """Calculate relevance score using enhanced scoring"""
        try:
            from match_scoring import calculate_match_score
            grant_data = {
                'title': title,
                'description': description,
                'amount': 0  # Will be scored separately
            }
            return calculate_match_score(grant_data, [])
        except Exception as e:
            # Fallback to simple scoring
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

    def _extract_requirements(self, naics_code: str, set_aside: str) -> List[str]:
        """Extract requirements from NAICS and set-aside info"""
        requirements = []

        if set_aside:
            requirements.append(f"Set-aside type: {set_aside}")

        if naics_code:
            requirements.append(f"NAICS code: {naics_code}")

        if not requirements:
            requirements = ["See full opportunity details on SAM.gov"]

        return requirements[:4]

    def _extract_contact(self, contacts: List) -> str:
        """Extract primary contact email from contacts list"""
        try:
            if contacts and isinstance(contacts, list):
                primary_contact = next((c for c in contacts if c.get('type') == 'primary'), contacts[0] if contacts else {})
                return primary_contact.get('email', '')
        except:
            pass
        return ''


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
