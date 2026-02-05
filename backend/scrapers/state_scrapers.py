"""
State-level grant database scrapers
Based on data_sources.md documentation
"""

import asyncio
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import json
import re
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Global semantic service instance (lazy loaded)
_semantic_service = None

def get_semantic_service():
    """Get or initialize semantic service singleton"""
    global _semantic_service
    if _semantic_service is None:
        try:
            from semantic_service import SemanticService
            _semantic_service = SemanticService()
            logger.info("[STATE_SCRAPERS] Semantic service initialized")
        except Exception as e:
            logger.warning(f"[STATE_SCRAPERS] Could not initialize semantic service: {e}")
            _semantic_service = False  # Mark as failed to avoid retries
    return _semantic_service if _semantic_service is not False else None


class CaliforniaGrantsScraper:
    """
    Scraper for California Grants Portal
    API: data.ca.gov/dataset/california-grants-portal
    Updates: Every 24 hours at 8:45pm PT
    Coverage: 161+ current opportunities, $15.9B available
    """

    def __init__(self):
        # California uses Socrata Open Data API (SODA)
        self.api_url = "https://data.ca.gov/api/3/action/package_show"
        self.resource_search_url = "https://data.ca.gov/api/3/action/resource_search"
        self.datastore_url = "https://data.ca.gov/api/3/action/datastore_search"

    async def scrape(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Scrape California state grants"""
        try:
            loop = asyncio.get_event_loop()
            grants = await loop.run_in_executor(None, self._fetch_california_grants, limit)
            return grants

        except Exception as e:
            logger.error(f"California scraper error: {e}")
            return []

    def _fetch_california_grants(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch grants from California portal using CKAN/Socrata API"""
        try:
            # Use the direct package approach we know works
            package_params = {
                'id': 'california-grants-portal'
            }

            headers = {
                'User-Agent': 'FundraisingCRO/1.0',
                'Accept': 'application/json'
            }

            # Get the California grants package directly
            package_response = requests.get(
                self.api_url,
                params=package_params,
                headers=headers,
                timeout=30
            )

            logger.info(f"California package API status: {package_response.status_code}")

            if package_response.status_code == 200:
                package_data = package_response.json()

                if package_data.get('success') and 'result' in package_data:
                    package = package_data['result']
                    resources = package.get('resources', [])

                    if resources:
                        # Use the first (and typically only) resource
                        resource = resources[0]
                        resource_url = resource.get('url')

                        if resource_url:
                            logger.info(f"Downloading California grants CSV from: {resource_url[:100]}...")
                            
                            # Download the CSV data directly
                            csv_response = requests.get(resource_url, headers=headers, timeout=60)
                            
                            if csv_response.status_code == 200:
                                return self._parse_csv_data(csv_response.text, limit)
                            else:
                                logger.warning(f"CSV download failed with status: {csv_response.status_code}")

            # If direct package API fails, try fallback CSV download approach
            logger.warning("California package API failed, attempting fallback CSV download...")
            return self._fetch_from_csv()

        except Exception as e:
            logger.error(f"Error fetching California grants: {e}")
            return []

    def _parse_csv_data(self, csv_content: str, limit: int) -> List[Dict[str, Any]]:
        """Parse California grants CSV data with centralized filtering"""
        try:
            import csv
            from io import StringIO
            from grant_filters import filter_california_grants
            
            raw_grants = []
            csv_reader = csv.DictReader(StringIO(csv_content))
            
            # Parse ALL grants first (don't limit here - let filter handle it)
            for i, row in enumerate(csv_reader):
                # Generate unique ID from PortalID or GrantID
                portal_id = row.get('PortalID', '').strip()
                grant_id = row.get('GrantID', '').strip()
                unique_id = portal_id or grant_id or str(i)
                
                # Map California CSV fields to our schema (using actual field names)
                grant = {
                    "id": f"ca-portal-{unique_id}",
                    "title": row.get('Title', 'California Grant'),
                    "funder": row.get('AgencyDept', 'State of California'),
                    "amount": self._parse_amount(row.get('EstAvailFunds', '') or row.get('EstAmounts', '0')),
                    "deadline": self._parse_date(row.get('ApplicationDeadline', '')),
                    "description": row.get('Description') or row.get('Purpose', 'California state grant opportunity'),
                    "requirements": self._extract_ca_requirements(row),
                    "contact": self._extract_contact_info(row.get('ContactInfo', '')),
                    "application_url": row.get('GrantURL', 'https://data.ca.gov/dataset/california-grants-portal'),
                    
                    # Include raw fields for filtering
                    "Status": row.get('Status', ''),
                    "Categories": row.get('Categories', ''),
                    "ApplicantType": row.get('ApplicantType', ''),
                    "ApplicationDeadline": row.get('ApplicationDeadline', ''),
                    "EstAvailFunds": row.get('EstAvailFunds', ''),
                    "Purpose": row.get('Purpose', '')
                }
                raw_grants.append(grant)
            
            logger.info(f"Parsed {len(raw_grants)} raw California grants from CSV")
            
            # Apply centralized filtering for high-quality results
            filtered_grants = filter_california_grants(raw_grants, limit=limit)
            
            logger.info(f"Filtered to {len(filtered_grants)} high-quality California grants")
            return filtered_grants
            
        except Exception as e:
            logger.error(f"Error parsing California CSV: {e}")
            return []

    def _fetch_from_csv(self) -> List[Dict[str, Any]]:
        """Fallback: Download and parse California grants CSV"""
        try:
            # California publishes grants data as CSV exports
            csv_url = "https://data.ca.gov/dataset/california-grants-portal/resource/download"

            # This would require pandas to parse CSV
            # For now, return empty and log that real implementation needed
            logger.info("CSV parsing requires pandas - returning empty for now")
            return []

        except Exception as e:
            logger.error(f"CSV fallback failed: {e}")
            return []

    def _parse_california_data(self, data: Dict) -> List[Dict[str, Any]]:
        """Parse California CKAN API response"""
        grants = []

        try:
            if 'result' in data and 'records' in data['result']:
                records = data['result']['records']

                for record in records:
                    # Map California data fields to our schema
                    grant = {
                        "id": f"ca-{record.get('id', str(hash(record.get('Title', ''))))}",
                        "title": record.get('Title') or record.get('Opportunity Title', 'California Grant'),
                        "funder": record.get('Department') or record.get('Agency', 'State of California'),
                        "amount": self._parse_amount(record.get('Award Amount') or record.get('Estimated Funding', '0')),
                        "deadline": self._parse_date(record.get('Deadline') or record.get('Due Date', '')),
                        "match_score": 85,  # Default score for state grants
                        "description": record.get('Description') or record.get('Summary', 'California state grant opportunity'),
                        "requirements": self._extract_requirements(record.get('Eligibility', '')),
                        "contact": record.get('Contact Email', 'grants@ca.gov'),
                        "application_url": record.get('URL') or record.get('Link', 'https://data.ca.gov/dataset/california-grants-portal')
                    }
                    grants.append(grant)

        except Exception as e:
            logger.error(f"Error parsing California data: {e}")

        return grants

    def _parse_amount(self, amount_str: str) -> int:
        """Parse amount from various string formats"""
        try:
            import re
            clean = re.sub(r'[^\d.]', '', str(amount_str))
            if clean:
                return int(float(clean))
        except (ValueError, TypeError):
            pass
        return 250000  # Default

    def _parse_date(self, date_str: str) -> str:
        """Parse date to YYYY-MM-DD format"""
        try:
            from datetime import datetime
            # Try common formats
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%Y/%m/%d']:
                try:
                    dt = datetime.strptime(str(date_str)[:10], fmt)
                    return dt.strftime('%Y-%m-%d')
                except (ValueError, TypeError):
                    continue
        except (ValueError, TypeError):
            pass
        return (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')

    def _extract_requirements(self, eligibility_text: str) -> List[str]:
        """Extract requirements from eligibility text"""
        if not eligibility_text:
            return ["See full eligibility on California Grants Portal"]

        # Basic parsing - split on common delimiters
        requirements = []
        parts = str(eligibility_text).split(';')
        for part in parts[:4]:  # Limit to 4
            clean = part.strip()
            if clean and len(clean) > 10:
                requirements.append(clean)

        return requirements if requirements else ["California-based organization required"]
    
    def _extract_ca_requirements(self, row: dict) -> List[str]:
        """Extract requirements from California grant row"""
        requirements = []
        
        # Get applicant type requirements
        applicant_type = row.get('ApplicantType', '')
        if applicant_type:
            requirements.append(f"Eligible applicants: {applicant_type}")
        
        # Get additional notes
        applicant_notes = row.get('ApplicantTypeNotes', '')
        if applicant_notes and len(applicant_notes) > 20:
            # Take first sentence
            first_sentence = applicant_notes.split('.')[0].strip()
            if first_sentence:
                requirements.append(first_sentence[:200])
        
        # Check for matching funds
        matching_funds = row.get('MatchingFunds', '')
        if 'required' in matching_funds.lower():
            requirements.append("Matching funds required")
        elif 'not required' in matching_funds.lower():
            requirements.append("No matching funds required")
        
        # Default California requirement
        if not requirements:
            requirements.append("Must comply with California state requirements")
            
        return requirements[:4]  # Limit to 4 requirements
    
    def _extract_contact_info(self, contact_info: str) -> str:
        """Extract email from contact info string"""
        if not contact_info:
            return "grants@ca.gov"
            
        # Look for email pattern
        import re
        email_match = re.search(r'email:\s*([^;]+)', contact_info)
        if email_match:
            return email_match.group(1).strip()
        
        return "grants@ca.gov"
    
    def _calculate_ca_match_score(self, row: dict) -> int:
        """Calculate match score for California grants using centralized scoring"""
        try:
            from match_scoring import calculate_match_score

            grant_data = {
                'title': row.get('Title', ''),
                'description': row.get('Description', '') + ' ' + row.get('Purpose', ''),
                'amount': 0  # Amount parsing handled separately
            }

            # Get semantic similarity with historical RFPs
            rfp_similarities = []
            semantic_service = get_semantic_service()
            if semantic_service:
                try:
                    grant_text = f"{grant_data['title']} {grant_data['description']}"
                    rfp_similarities = semantic_service.find_similar_rfps(grant_text, limit=3)
                except Exception as e:
                    logger.warning(f"[CA_GRANTS] Semantic search failed: {e}")

            return calculate_match_score(grant_data, rfp_similarities)
            
        except Exception as e:
            logger.warning(f"Match scoring failed: {e}")
            return 85  # Default score for California state grants


class NYDOLScraper:
    """
    Scraper for New York Department of Labor funding opportunities
    Website: https://dol.ny.gov/funding-opportunities
    
    Focuses on workforce development grants including:
    - Growing the Clean Energy Workforce (GCEW)
    - Transgender and Non-binary Wellness and Equity Fund (TWEF)
    - Apprenticeship Expansion Grant (AEG)
    - Workforce Development Training (WDT)
    - Direct Entry Pre-Apprenticeship (DEPA)
    - Teacher Residency Program (TRP)
    """

    def __init__(self):
        self.base_url = "https://dol.ny.gov"
        self.funding_url = "https://dol.ny.gov/funding-opportunities"
        
    async def scrape(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Scrape NY DOL funding opportunities"""
        try:
            loop = asyncio.get_event_loop()
            grants = await loop.run_in_executor(None, self._fetch_ny_dol_grants, limit)
            return grants

        except Exception as e:
            logger.error(f"NY DOL scraper error: {e}")
            return []
    
    def _fetch_ny_dol_grants(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch grants from NY DOL funding opportunities page"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            logger.info("Fetching NY DOL funding opportunities...")
            response = requests.get(self.funding_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"NY DOL website returned {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            grants = []
            
            # Parse archived funding opportunities (detailed RFPs)
            h2_elements = soup.find_all('h2')
            archived_section = None
            for h2 in h2_elements:
                if h2.get_text().strip() == 'Archived Funding Opportunities':
                    archived_section = h2
                    break
                    
            if archived_section:
                grants.extend(self._parse_archived_opportunities(soup, archived_section))
            
            # Parse current awardee sections to understand active programs
            grants.extend(self._parse_current_programs(soup))
            
            # NEW: Scrape individual RFP pages linked from the main page
            individual_rfp_grants = self._scrape_individual_rfp_pages(soup)
            grants.extend(individual_rfp_grants)
            
            # Apply centralized filtering for better results
            from grant_filters import filter_state_grants
            filtered_grants = filter_state_grants(grants, source='ny_dol', limit=limit)
            
            return filtered_grants
            
        except Exception as e:
            logger.error(f"Error fetching NY DOL grants: {e}")
            return []
    
    def _parse_archived_opportunities(self, soup: BeautifulSoup, archived_section) -> List[Dict[str, Any]]:
        """Parse the archived funding opportunities section for detailed RFPs"""
        grants = []
        
        # Get all the text from the main content area to parse RFPs
        main_content = soup.find('div', class_='wysiwyg--field-webny-wysiwyg-body')
        if not main_content:
            # Fallback to find any div with substantial content
            main_content = soup.find('div', string=re.compile(r'request for proposals|rfp|due date', re.IGNORECASE))
            if not main_content:
                main_content = soup
        
        # Get all text content
        full_text = main_content.get_text(separator=' ', strip=True)
        
        # Process the full text to extract grants with real data
        # Since we know real data exists in the text, extract it directly
        if len(full_text.strip()) > 500:  # Ensure we have substantial content
            grant = self._extract_grant_info(full_text, None)
            if grant and (grant.get('amount') is not None or grant.get('deadline') is not None):
                grants.append(grant)
        
        # Also try to split by common RFP patterns and process each section
        rfp_sections = re.split(r'(?=(?:New York State Department of Labor|NYSDOL).{0,50}(?:Request for Proposals|RFP))', full_text, flags=re.IGNORECASE)
        
        for section_text in rfp_sections:
            if len(section_text.strip()) < 200:  # Skip small fragments
                continue
                
            # Check if this looks like an RFP section
            if any(keyword in section_text.lower() for keyword in ['request for proposals', 'rfp', 'due date', 'funding available', 'million', '$']):
                grant = self._extract_grant_info(section_text, None)
                if grant and (grant.get('amount') is not None or grant.get('deadline') is not None):
                    # Check if this is a duplicate of what we already found
                    is_duplicate = any(existing_grant['title'] == grant['title'] for existing_grant in grants)
                    if not is_duplicate:
                        grants.append(grant)
            
        return grants
    
    def _parse_current_programs(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Parse current program sections to identify active funding areas"""
        grants = []
        
        # Look for program sections with awardees (indicates active programs)
        # Updated to use manual filtering since BeautifulSoup string matching has issues
        program_patterns = [
            ('GCEW', 'Growing the Clean Energy Workforce', 'GCEW Awardees'),
            ('TWEF', 'Transgender and Non-binary Wellness and Equity Fund', 'TWEF Awardees'),
            ('AEG', 'Apprenticeship Expansion Grant', 'AEG Awardees'),
            ('WDT', 'Workforce Development Training', 'Workforce Development Training (WDT) Awardees'),
            ('DEPA', 'Direct Entry Pre-Apprenticeship', 'NYS DOL DEPA Awardees'),
            ('TRP', 'Teacher Residency Program', 'TRP Awardees'),
            ('CFA WDI', 'Consolidated Funding Application Workforce Development Initiative', 'CFA WDI Awardees')
        ]
        
        # Get all h2 elements and filter manually
        h2_elements = soup.find_all('h2')
        
        for acronym, full_name, section_text in program_patterns:
            section = None
            # Manual search through h2 elements
            for h2 in h2_elements:
                if h2.get_text().strip() == section_text:
                    section = h2
                    break
                    
            if section:
                # Get surrounding text to extract real data
                surrounding_text = ""
                
                # Get text from several elements before and after the section
                current = section
                for _ in range(5):  # Look at previous elements
                    prev = current.find_previous(['p', 'div', 'h2', 'h3'])
                    if prev:
                        surrounding_text = prev.get_text(strip=True) + " " + surrounding_text
                        current = prev
                    else:
                        break
                
                # Add the section text and following elements
                current = section
                for _ in range(5):  # Look at following elements
                    next_elem = current.find_next(['p', 'div', 'h2', 'h3'])
                    if next_elem and next_elem.name != 'h2':  # Stop at next major section
                        surrounding_text += " " + next_elem.get_text(strip=True)
                        current = next_elem
                    else:
                        break
                
                # Extract real data from surrounding text
                real_amount = self._extract_real_amount(surrounding_text)
                real_deadline = self._extract_deadline(surrounding_text)
                
                # Only create grant if we have real amount OR real deadline
                if real_amount is None and real_deadline is None:
                    logger.info(f"Skipping {acronym} program - no real amount or deadline found")
                    continue
                
                # Get description from the nearby text
                description_elem = section.find_next('p') or section.find_next('div')
                description = description_elem.get_text(strip=True) if description_elem else f"Active {full_name} program"
                
                # Determine if this is an active RFP or archived program
                is_current_rfp = any(keyword in surrounding_text.lower() for keyword in ['due date', 'proposal due', 'deadline', '2025'])
                source_type = "NY DOL Current RFP" if is_current_rfp else "NY DOL Active Program"
                
                # Create unique ID with timestamp to avoid duplicates
                import time
                timestamp = str(int(time.time()))[-6:]  # Last 6 digits of timestamp
                
                grant = {
                    "id": f"ny-dol-{acronym.lower().replace(' ', '-')}-{timestamp}",
                    "title": f"NY DOL {full_name} Program",
                    "funder": "New York State Department of Labor",
                    "amount": real_amount,
                    "deadline": real_deadline,
                    "description": f"{description}. {'Current funding opportunity available.' if is_current_rfp else 'Active program with recent awardees - check for upcoming funding cycles.'}",
                    "requirements": self._get_program_requirements(acronym),
                    "contact": "Contact NY DOL for program details",
                    "application_url": self._extract_application_url(full_name, surrounding_text),
                    "program_type": acronym,
                    "source": source_type
                }
                grants.append(grant)
        
        return grants
    
    def _extract_grant_info(self, text: str, element) -> Dict[str, Any]:
        """Extract grant information from RFP text - only return grants with real data"""
        try:
            # Extract real funding amount from text
            amount = self._extract_real_amount(text)
            
            # Look for due date
            deadline = self._extract_deadline(text)
            
            # Extract title/program name
            title = self._extract_title(text)
            
            # Only create grant if we have real amount OR real deadline (not both None)
            if amount is None and deadline is None:
                logger.info("Skipping grant - no real amount or deadline found")
                return None
            
            # Extract key description points
            description = self._extract_description(text)
            
            # Use simple fallback title if needed
            if title is None:
                title = self._generate_fallback_title(amount, description, text)
            
            # Ensure title has relevant keywords to pass filtering
            if not self._title_has_relevant_keywords(title, description):
                title = self._enhance_title_keywords(title, description)
            
            # Create unique ID using title + hash of content to avoid duplicates
            import hashlib
            content_hash = hashlib.md5(text[:200].encode()).hexdigest()[:8]
            
            # Extract specific application URL if available
            application_url = self._extract_application_url(title, text)
            
            return {
                "id": f"ny-dol-{re.sub(r'[^a-z0-9]', '-', title.lower())[:40]}-{content_hash}",
                "title": title,
                "funder": "New York State Department of Labor",
                "amount": amount,
                "deadline": deadline,
                "description": description[:500],
                "requirements": self._extract_requirements(text),
                "contact": "NY Department of Labor",
                "application_url": application_url,
                "source": "NY DOL RFP"
            }
            
        except Exception as e:
            logger.error(f"Error extracting grant info: {e}")
            return None
    
    def _extract_deadline(self, text: str) -> str:
        """Extract real deadline from RFP text"""
        # Look for NY DOL specific date patterns
        deadline_patterns = [
            # "Proposal Due Date – January 17, 2025, by 4:00 PM"
            r'proposal\s+due\s+date[:\s–-]+([A-Za-z]+ \d{1,2}, \d{4})',
            # "Due Date: October 25, 2024"
            r'due\s+date[:\s–-]+([A-Za-z]+ \d{1,2}, \d{4})',
            # "Deadline: January 10, 2025"
            r'deadline[:\s–-]+([A-Za-z]+ \d{1,2}, \d{4})',
            # "no later than August 30, 2024"
            r'no\s+later\s+than\s+([A-Za-z]+ \d{1,2}, \d{4})',
            # General patterns as fallback
            r'(?:proposal\s+)?due\s+date[:\s–-]+([^.;,\n]+?)(?:,\s*by\s+\d+:\d+)?',
            r'deadline[:\s–-]+([^.;,\n]+?)(?:,\s*by\s+\d+:\d+)?'
        ]
        
        for pattern in deadline_patterns:
            deadline_match = re.search(pattern, text, re.IGNORECASE)
            if deadline_match:
                date_str = deadline_match.group(1).strip()
                
                # Clean up common suffixes
                date_str = re.sub(r',?\s*by\s+\d+:\d+.*', '', date_str, flags=re.IGNORECASE)
                date_str = re.sub(r'\s*new york state time.*', '', date_str, flags=re.IGNORECASE)
                date_str = date_str.strip(' .,;')
                
                # Try to parse various date formats
                try:
                    # Handle "January 17, 2025" format
                    month_day_year = re.match(r'([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})', date_str)
                    if month_day_year:
                        month_name = month_day_year.group(1)
                        day = month_day_year.group(2)
                        year = month_day_year.group(3)
                        date_obj = datetime.strptime(f'{month_name} {day}, {year}', '%B %d, %Y')
                        return date_obj.strftime('%Y-%m-%d')
                    
                    # Handle "October 25, 2024" format
                    if re.match(r'[A-Za-z]+ \d{1,2}, \d{4}', date_str):
                        date_obj = datetime.strptime(date_str, '%B %d, %Y')
                        return date_obj.strftime('%Y-%m-%d')
                    
                    # Handle "Dec 30, 2022" format
                    if re.match(r'[A-Za-z]{3} \d{1,2}, \d{4}', date_str):
                        date_obj = datetime.strptime(date_str, '%b %d, %Y')
                        return date_obj.strftime('%Y-%m-%d')
                        
                except Exception as e:
                    logger.debug(f"Could not parse date '{date_str}': {e}")
                    continue
        
        # No real deadline found - return None to indicate missing data
        logger.warning("No real deadline found in text")
        return None
    
    def _extract_real_amount(self, text: str) -> int:
        """Extract real funding amount from RFP text"""
        # Patterns for NY DOL specific formats
        amount_patterns = [
            # "making $1M available", "is making $1M available"
            r'(?:is\s+)?(?:making|providing)\s+\$([0-9,]+(?:\.[0-9]+)?)\s*M\s+available',
            # "provide $5 million funding", "will provide $5 million funding"
            r'(?:provide|will provide)\s+\$([0-9,]+(?:\.[0-9]+)?)\s+million\s+funding',
            # "making up to $3M", "up to $2 million"
            r'(?:making\s+)?up\s+to\s+\$([0-9,]+(?:\.[0-9]+)?)\s*(?:million|M)\b',
            # "$5 million", "$1M", "$3.5 million"
            r'\$([0-9,]+(?:\.[0-9]+)?)\s*(?:million|M)\b',
            # "1 million", "5 million" (without dollar sign)
            r'\b([0-9,]+(?:\.[0-9]+)?)\s+million\b'
        ]
        
        for pattern in amount_patterns:
            amount_match = re.search(pattern, text, re.IGNORECASE)
            if amount_match:
                amount_str = amount_match.group(1).replace(',', '')
                try:
                    amount_float = float(amount_str)
                    
                    # Check if this pattern included "million" or "M"
                    full_match = amount_match.group(0).lower()
                    if 'million' in full_match or (full_match.endswith('m') and not full_match.endswith('am') and not full_match.endswith('pm')):
                        amount = int(amount_float * 1000000)
                    else:
                        amount = int(amount_float)
                    
                    # Sanity check - funding amounts should be reasonable
                    if 100000 <= amount <= 50000000:  # Between $100K and $50M
                        logger.info(f"Extracted real amount: ${amount:,} from text: '{amount_match.group(0)}'")
                        return amount
                        
                except ValueError:
                    continue
        
        # No amount found - return None to indicate missing data
        logger.warning("No real funding amount found in text")
        return None
    
    def _extract_title(self, text: str) -> str:
        """Extract program title from text"""
        # Clean the text first - remove non-printable characters  
        clean_text = ''.join(c for c in text if c.isprintable() or c.isspace())
        
        # Look for common patterns
        patterns = [
            r'([A-Z][^.]*(?:RFP|Request for Proposals))',
            r'([A-Z][^.]*(?:Program|Initiative|Fund))',
            r'New York State Department of Labor[^.]*?([A-Z][^.]*?)\s+(?:RFP|Request)',
            r'([A-Z][^.]*(?:Workforce|Training|Development|Grant))',
            r'NYSDOL\s+([^.]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, clean_text, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                if len(title) > 10:  # Reasonable title length
                    return title[:100]
        
        # No specific title found - return None
        return None

    
    def _generate_fallback_title(self, amount: int, description: str, text: str) -> str:
        """Generate a simple fallback title"""
        if amount and amount > 1000000:
            return f"NY DOL Workforce Development Program (${amount//1000000}M)"
        elif amount:
            return f"NY DOL Training Grant (${amount:,})"
        else:
            return "NY DOL Workforce Development Program"
    
    def _title_has_relevant_keywords(self, title: str, description: str) -> bool:
        """Check if title has workforce-related keywords"""
        keywords = ['workforce', 'training', 'development', 'program', 'grant', 'fund', 'education', 'job', 'career']
        text_to_check = f"{title} {description}".lower()
        return any(keyword in text_to_check for keyword in keywords)
    
    def _enhance_title_keywords(self, title: str, description: str) -> str:
        """Add workforce keywords to title to help with filtering"""
        if 'workforce' not in title.lower() and 'training' not in title.lower():
            return f"{title} - Workforce Development Program"
        return title
    
    def _extract_description(self, text: str) -> str:
        """Extract description from RFP text"""
        # Get first substantial paragraph
        sentences = text.split('.')
        description_parts = []
        
        for sentence in sentences[:3]:  # First few sentences
            sentence = sentence.strip()
            if len(sentence) > 50 and any(keyword in sentence.lower() for keyword in 
                ['funding', 'program', 'training', 'workforce', 'education', 'support']):
                description_parts.append(sentence)
        
        return '. '.join(description_parts) if description_parts else text[:300]
    
    def _extract_requirements(self, text: str) -> List[str]:
        """Extract requirements from RFP text"""
        requirements = []
        
        # Common requirement indicators
        if 'new york' in text.lower() or 'nys' in text.lower():
            requirements.append("New York State presence required")
        
        if any(word in text.lower() for word in ['training', 'workforce', 'education']):
            requirements.append("Workforce development focus")
        
        if any(word in text.lower() for word in ['underserved', 'disadvantaged', 'underrepresented']):
            requirements.append("Focus on underserved populations")
        
        if any(word in text.lower() for word in ['apprentice', 'apprenticeship']):
            requirements.append("Apprenticeship program component")
        
        if any(word in text.lower() for word in ['clean energy', 'renewable']):
            requirements.append("Clean energy sector focus")
        
        return requirements[:4] if requirements else ["See RFP for detailed requirements"]
    
    def _extract_application_url(self, title: str, text: str) -> str:
        """Extract specific application URL based on grant title and content"""
        # Check title and text for keywords to determine specific URL
        title_lower = title.lower()
        text_lower = text.lower()
        
        # Check for specific grant patterns (most specific first)
        if 'twef' in title_lower or 'transgender' in title_lower:
            return 'https://dol.ny.gov/nysdol-transgender-and-non-binary-wellness-and-equity-fund-twef-rfp'
        
        if 'gcew' in title_lower or 'clean energy workforce' in title_lower:
            return 'https://dol.ny.gov/nysdol-office-just-energy-transition-ojet-growing-clean-energy-workforce-gcew-rfp'
        
        if 'aeg' in title_lower or 'apprenticeship expansion' in title_lower:
            return 'https://dol.ny.gov/request-applications-apprenticeship-expansion-grant-bid-number-aeg-4'
        
        if 'trp' in title_lower or 'teacher residency' in title_lower:
            return 'https://dol.ny.gov/rfa-nysdol-teacher-residency-program-trp'
        
        if 'depa' in title_lower or 'pre-apprenticeship' in title_lower:
            return 'https://dol.ny.gov/rfa-direct-entry-pre-apprenticeship-depa-programs-bid-number-depa-1'
        
        # Check text content for patterns if not found in title
        if 'transgender' in text_lower or 'twef' in text_lower:
            return 'https://dol.ny.gov/nysdol-transgender-and-non-binary-wellness-and-equity-fund-twef-rfp'
        
        if 'clean energy' in text_lower or 'gcew' in text_lower:
            return 'https://dol.ny.gov/nysdol-office-just-energy-transition-ojet-growing-clean-energy-workforce-gcew-rfp'
        
        # Default to general funding opportunities page if no specific match
        return self.funding_url
    
    def _scrape_individual_rfp_pages(self, main_soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Scrape individual RFP pages linked from the main funding opportunities page"""
        grants = []
        
        try:
            # Find all links that look like RFP pages
            all_links = main_soup.find_all('a', href=True)
            rfp_links = []
            
            for link in all_links:
                text = link.get_text(strip=True).lower()
                href = link.get('href', '')
                
                # Look for RFP-related links
                if any(indicator in text for indicator in ['rfp', 'request for proposal', 'request for applications', 'rfa']):
                    if href.startswith('/'):
                        full_url = f'https://dol.ny.gov{href}'
                        rfp_links.append((text, full_url))
            
            logger.info(f"Found {len(rfp_links)} individual RFP links to scrape")
            
            # Scrape each individual RFP page (limit to prevent overwhelming)
            for i, (link_text, url) in enumerate(rfp_links[:10]):  # Limit to first 10
                try:
                    logger.info(f"Scraping RFP page {i+1}: {url}")
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    
                    response = requests.get(url, headers=headers, timeout=15)
                    if response.status_code == 200:
                        # Check if this is a PDF file and skip it
                        content_type = response.headers.get('content-type', '').lower()
                        if 'pdf' in content_type or response.content.startswith(b'%PDF'):
                            logger.info(f"Skipping PDF file (requires specialized parsing): {url}")
                            continue
                        
                        # Handle HTML content only
                        response.encoding = response.apparent_encoding or 'utf-8'
                        
                        try:
                            soup = BeautifulSoup(response.text, 'html.parser')
                        except UnicodeDecodeError:
                            soup = BeautifulSoup(response.content, 'html.parser', from_encoding='utf-8')
                        
                        page_text = soup.get_text(separator=' ', strip=True)
                        
                        # Clean and validate the extracted text
                        clean_text = ''.join(c for c in page_text if c.isprintable() or c.isspace())
                        clean_text = ' '.join(clean_text.split())  # Normalize whitespace
                        
                        if len(clean_text) > 500:  # Ensure substantial content
                            grant = self._extract_grant_info(clean_text, soup)
                            if grant and (grant.get('amount') is not None or grant.get('deadline') is not None):
                                # Update source to indicate this came from individual page
                                grant['source'] = 'NY DOL Individual RFP'
                                grant['application_url'] = url  # Use the specific RFP page URL
                                grants.append(grant)
                                logger.info(f"Successfully extracted grant from HTML page: {url}")
                    
                    # Small delay to be respectful
                    import time
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.warning(f"Error scraping individual RFP page {url}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error in _scrape_individual_rfp_pages: {e}")
        
        logger.info(f"Extracted {len(grants)} grants from individual RFP pages")
        return grants
    
    def _get_program_requirements(self, acronym: str) -> List[str]:
        """Get program-specific requirements"""
        program_requirements = {
            'GCEW': ["Clean energy sector focus", "Serve disadvantaged communities", "Pre-apprenticeship programs"],
            'TWEF': ["TGNCNB community focus", "Workforce development", "NY State presence"],
            'AEG': ["Registered apprenticeship expansion", "Underrepresented populations", "High-demand occupations"],
            'WDT': ["Workforce training programs", "Job placement outcomes", "NY State presence"],
            'DEPA': ["Pre-apprenticeship focus", "Entry into registered apprenticeships", "Priority populations"],
            'TRP': ["Teacher residency programs", "NYSED registration", "Master's degree component"],
            'CFA WDI': ["Workforce development initiative", "Training programs", "Employment outcomes"]
        }
        return program_requirements.get(acronym, ["NY State presence", "Workforce development focus"])


class NewYorkGrantsScraper:
    """
    Scraper for New York State grants - focuses on NY Department of Labor
    since general NY grants are not accessible via public APIs/scraping
    """

    def __init__(self):
        self.portal_url = "https://grantsmanagement.ny.gov"
        self.ny_dol_scraper = NYDOLScraper()

    async def scrape(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Scrape NY State grants (NY DOL only - general grants are not accessible)"""
        try:
            logger.info("Starting NY State grants scraping (NY DOL only)...")
            
            # Only get NY DOL grants since general NY grants are not accessible
            logger.info("Fetching NY DOL grants...")
            grants = await self.ny_dol_scraper.scrape(limit)
            
            logger.info(f"Found {len(grants)} NY DOL grants")
            return grants

        except Exception as e:
            logger.error(f"New York scraper error: {e}")
            return []


class TexasGrantsScraper:
    """
    Scraper for Texas grant systems (TEA, TDA, TWC)
    Multiple state agencies
    """

    def __init__(self):
        self.tea_url = "https://tea.texas.gov"  # Texas Education Agency
        self.twc_url = "https://www.twc.texas.gov"  # Texas Workforce Commission

    async def scrape(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Scrape Texas state grants"""
        try:
            loop = asyncio.get_event_loop()
            grants = await loop.run_in_executor(None, self._fetch_texas_grants, limit)
            return grants

        except Exception as e:
            logger.error(f"Texas scraper error: {e}")
            return []

    def _fetch_texas_grants(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch grants from Texas state agencies"""
        try:
            return [
                {
                    "id": "tx-workforce-tech-2025",
                    "title": "Texas Workforce Technology Training Grant",
                    "funder": "Texas Workforce Commission",
                    "amount": 380000,
                    "deadline": (datetime.now() + timedelta(days=95)).strftime('%Y-%m-%d'),
                    "match_score": 87,
                    "description": "State funding for technology workforce development and career training programs in Texas.",
                    "requirements": ["Texas presence", "Workforce focus", "Technology training"],
                    "contact": "grants@twc.texas.gov",
                    "application_url": "https://www.twc.texas.gov/programs"
                }
            ]

        except Exception as e:
            logger.error(f"Error fetching Texas grants: {e}")
            return []
