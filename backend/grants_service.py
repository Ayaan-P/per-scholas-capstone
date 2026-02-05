"""
Temporary service to pull real grant data from Grants.gov API
This demonstrates the backend working with real funding opportunities
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import xml.etree.ElementTree as ET
import re
from semantic_service import SemanticService
from organization_matching_service import OrganizationMatchingService

class GrantsGovService:
    def __init__(self, supabase_client=None):
        self.base_url = "https://www.grants.gov/web/grants/search-grants.html"
        # Grants.gov has a search API that returns XML
        self.api_url = "https://www.grants.gov/grantsws/rest/opportunities/search/"
        # Store Supabase client for caching match scores
        self.supabase = supabase_client
        # Initialize semantic service for enhanced scoring with RFP similarity
        try:
            self.semantic_service = SemanticService()
            print("[GRANTS] Semantic service initialized for RFP similarity matching")
        except Exception as e:
            print(f"[GRANTS] Could not initialize semantic service: {e}")
            self.semantic_service = None
        # Initialize organization matching service for org-aware scoring
        try:
            self.org_matching_service = OrganizationMatchingService(supabase_client) if supabase_client else None
            if self.org_matching_service:
                print("[GRANTS] Organization matching service initialized for org-aware grant matching")
        except Exception as e:
            print(f"[GRANTS] Could not initialize organization matching service: {e}")
            self.org_matching_service = None
        # Cache organization profiles to avoid repeated database queries
        self.org_profile_cache = {}

    def search_grants_via_script(self, keywords: str = "technology workforce", limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search grants using the grants-gov-fetch.sh script
        """
        try:
            import subprocess
            import os
            import re

            script_path = os.path.join(os.path.dirname(__file__), 'grants-gov-fetch.sh')

            result = subprocess.run([
                script_path,
                'search',
                keywords
            ], capture_output=True, text=True, timeout=30, cwd=os.path.dirname(__file__))

            if result.returncode == 0:
                # Remove ANSI color codes and parse JSON
                clean_output = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout)
                output_lines = clean_output.strip().split('\n')

                json_start = -1
                for i, line in enumerate(output_lines):
                    line_clean = line.strip()
                    if line_clean.startswith('{') and not line_clean.startswith('[INFO]'):
                        json_start = i
                        break

                if json_start >= 0:
                    json_output = '\n'.join(output_lines[json_start:])
                    grants_data = json.loads(json_output)

                    # Transform {"data": {"oppHits": [...]}} to our format
                    if 'data' in grants_data and 'oppHits' in grants_data['data']:
                        opportunities_list = []
                        for hit in grants_data['data']['oppHits'][:limit]:
                            opportunity = {
                                "id": hit.get('opportunityNumber', f"grant-{len(opportunities_list)+1}"),
                                "title": hit.get('opportunityTitle', 'Technology Grant'),
                                "funder": hit.get('agencyName', 'Federal Agency'),
                                "amount": int(hit.get('awardCeiling', 250000)) if hit.get('awardCeiling') else 250000,
                                "deadline": hit.get('closeDate', (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')),
                                "match_score": 85,
                                "description": hit.get('synopsis', 'Federal grant opportunity'),
                                "requirements": ["Federal compliance required"],
                                "contact": hit.get('contactEmail', 'grants@agency.gov'),
                                "application_url": hit.get('link', f"https://grants.gov/view/{hit.get('opportunityNumber', 'opportunity')}")
                            }
                            opportunities_list.append(opportunity)
                        return opportunities_list

            print(f"Grants script failed with return code {result.returncode}")
            return self._get_mock_grants()

        except Exception as e:
            print(f"Error calling grants script: {e}")
            return self._get_mock_grants()

    def search_grants(self, keywords: str = "technology workforce", limit: int = 5, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search grants.gov using the same API as the working shell script.
        If user_id is provided, uses organization-specific matching for more accurate results.
        """
        try:
            import requests

            # Fetch organization profile for org-aware matching if user_id provided
            org_profile = None
            if user_id and self.org_matching_service:
                try:
                    # Check cache first
                    if user_id in self.org_profile_cache:
                        org_profile = self.org_profile_cache[user_id]
                    else:
                        # Fetch from database
                        import asyncio
                        org_profile = asyncio.run(self.org_matching_service.get_organization_profile(user_id))
                        if org_profile:
                            self.org_profile_cache[user_id] = org_profile
                            print(f"[GRANTS SERVICE] Loaded organization profile for {org_profile.get('name', 'Unknown')}")
                except Exception as e:
                    print(f"[GRANTS SERVICE] Could not load org profile for user {user_id}: {e}")
                    org_profile = None

            # If org profile exists, build organization-specific search keywords
            if org_profile and self.org_matching_service:
                try:
                    primary_kw, secondary_kw = self.org_matching_service.build_search_keywords(org_profile)
                    # Use org-specific keywords for search
                    search_keywords = ' '.join(primary_kw + secondary_kw[:5])  # Use top secondary keywords
                    print(f"[GRANTS SERVICE] Using org-specific keywords: {search_keywords}")
                    keywords = search_keywords
                except Exception as e:
                    print(f"[GRANTS SERVICE] Could not build org keywords, using provided keywords: {e}")

            print(f"[GRANTS SERVICE] Searching for: {keywords}")

            # Use the same API endpoint as the working shell script
            api_url = "https://api.grants.gov/v1/api/search2"

            headers = {
                'User-Agent': 'FundraisingCRO:v1.0',
                'Content-Type': 'application/json'
            }

            payload = {
                "rows": limit,
                "keyword": keywords,
                "oppStatuses": "forecasted|posted"
            }

            print(f"[GRANTS SERVICE] Calling API: {api_url}")
            response = requests.post(api_url, json=payload, headers=headers, timeout=30)
            print(f"[GRANTS SERVICE] Response status: {response.status_code}")

            if response.status_code != 200:
                print(f"[GRANTS SERVICE] API failed, using mock data")
                return self._get_mock_grants()

            data = response.json()

            # Transform the response to our format
            if 'data' in data and 'oppHits' in data['data']:
                opportunities = []
                token = data.get('token', '')

                for hit in data['data']['oppHits'][:limit]:
                    # Get detailed info for each opportunity using the ID (not number)
                    opportunity_details = self._get_opportunity_details_with_token(hit.get('id', ''), token)

                    # Clean HTML entities from title and funder
                    title = hit.get('title', 'Federal Grant Opportunity')
                    title = re.sub(r'&amp;', '&', title)
                    title = re.sub(r'&[a-zA-Z0-9#]+;', '', title)

                    funder = hit.get('agency', 'Federal Agency')
                    funder = re.sub(r'&amp;', '&', funder)
                    funder = re.sub(r'&[a-zA-Z0-9#]+;', '', funder)

                    # Use actual field names from the API response
                    # Build the correct grants.gov URL using the ID (not the number)
                    opp_id = hit.get('id', '')
                    opp_number = hit.get('number', '')
                    grant_url = f"https://www.grants.gov/search-results-detail/{opp_id}" if opp_id else "https://www.grants.gov"

                    opp = {
                        "id": opp_number or f"grant-{len(opportunities)+1}",
                        "title": title,
                        "funder": funder,
                        "amount": opportunity_details.get('amount') or 750000,  # Use real amount or default
                        "deadline": self._parse_date(hit.get('closeDate', '')),
                        "description": opportunity_details.get('description') or self._clean_html_entities(f"Grant opportunity: {hit.get('title', 'Federal funding opportunity')}. Agency: {hit.get('agency', 'Federal Agency')}. Status: {hit.get('oppStatus', 'Posted')}."),
                        "requirements": self._extract_requirements(opportunity_details.get('description', hit.get('title', '') + ' ' + hit.get('agency', ''))),
                        "contact": opportunity_details.get('contact', f"Contact via grants.gov for opportunity {opp_number}"),
                        "application_url": grant_url,

                        # UNIVERSAL COMPREHENSIVE FIELDS from opportunity_details
                        "contact_name": opportunity_details.get('contact_name'),
                        "contact_phone": opportunity_details.get('contact_phone'),
                        "contact_description": opportunity_details.get('contact_description'),
                        "eligibility_explanation": opportunity_details.get('eligibility_explanation'),
                        "cost_sharing": opportunity_details.get('cost_sharing'),
                        "cost_sharing_description": opportunity_details.get('cost_sharing_description'),
                        "additional_info_url": opportunity_details.get('additional_info_url'),
                        "additional_info_text": opportunity_details.get('additional_info_text'),
                        "archive_date": opportunity_details.get('archive_date'),
                        "forecast_date": opportunity_details.get('forecast_date'),
                        "close_date_explanation": opportunity_details.get('close_date_explanation'),
                        "expected_number_of_awards": opportunity_details.get('expected_number_of_awards'),
                        "award_floor": opportunity_details.get('award_floor'),
                        "award_ceiling": opportunity_details.get('award_ceiling'),
                        "attachments": opportunity_details.get('attachments', []),
                        "version": opportunity_details.get('version'),
                        "last_updated_date": opportunity_details.get('last_updated_date')
                    }
                    # Calculate enhanced match score after building the full opportunity
                    # Pass org_profile for organization-specific scoring
                    opp["match_score"] = self._calculate_enhanced_match_score(opp, org_profile=org_profile)
                    opportunities.append(opp)

                print(f"[GRANTS SERVICE] Found {len(opportunities)} opportunities")
                return opportunities

            print(f"[GRANTS SERVICE] No oppHits in response, using mock data")
            return self._get_mock_grants()

        except Exception as e:
            print(f"[GRANTS SERVICE] Error fetching grants: {e}")
            return self._get_mock_grants()

    def _get_opportunity_details_with_token(self, opportunity_id: str, token: str) -> Dict[str, Any]:
        """Get detailed opportunity info using the fetchOpportunity API"""
        if not opportunity_id:
            return {}

        try:
            # Use the fetchOpportunity endpoint
            api_url = "https://api.grants.gov/v1/api/fetchOpportunity"

            headers = {
                'User-Agent': 'FundraisingCRO:v1.0',
                'Content-Type': 'application/json'
            }

            # Use the opportunity ID (not number) for fetchOpportunity
            payload = {
                "opportunityId": int(opportunity_id) if opportunity_id.isdigit() else opportunity_id
            }

            response = requests.post(api_url, json=payload, headers=headers, timeout=15)
            print(f"[GRANTS SERVICE] fetchOpportunity status: {response.status_code} for ID: {opportunity_id}")

            if response.status_code == 200:
                data = response.json()

                details = {}
                if 'data' in data and 'synopsis' in data['data']:
                    synopsis = data['data']['synopsis']

                    # Get funding amounts from synopsis
                    award_ceiling = synopsis.get('awardCeiling')
                    award_floor = synopsis.get('awardFloor')

                    # Parse the funding amount
                    amount = None
                    if award_ceiling:
                        amount = self._parse_amount(str(award_ceiling))
                    elif award_floor:
                        amount = self._parse_amount(str(award_floor))

                    details['amount'] = amount if amount and amount > 0 else None

                    # Clean HTML tags from description
                    raw_desc = synopsis.get('synopsisDesc', '').strip()
                    clean_desc = re.sub(r'<[^>]+>', '', raw_desc)  # Remove HTML tags
                    clean_desc = re.sub(r'&nbsp;', ' ', clean_desc)  # Replace &nbsp; with spaces
                    clean_desc = re.sub(r'&amp;', '&', clean_desc)  # Replace &amp; with &
                    clean_desc = re.sub(r'&lt;', '<', clean_desc)  # Replace &lt; with <
                    clean_desc = re.sub(r'&gt;', '>', clean_desc)  # Replace &gt; with >
                    clean_desc = re.sub(r'&quot;', '"', clean_desc)  # Replace &quot; with "
                    clean_desc = re.sub(r'&[a-zA-Z0-9#]+;', '', clean_desc)  # Remove remaining HTML entities
                    details['description'] = clean_desc.strip()

                    # EXISTING BASIC CONTACT
                    details['contact'] = synopsis.get('agencyContactEmail', '')

                    # UNIVERSAL FIELDS (work for all grant sources)
                    # Contact Information (expanded)
                    details['contact_name'] = synopsis.get('agencyContactName', '')
                    details['contact_phone'] = synopsis.get('agencyContactPhone', '')
                    details['contact_description'] = self._clean_html_entities(synopsis.get('agencyContactDescription', ''))

                    # Eligibility Information
                    details['eligibility_explanation'] = self._clean_html_entities(synopsis.get('applicantEligibilityDesc', ''))

                    # Cost Sharing
                    details['cost_sharing'] = synopsis.get('costSharingOrMatchingRequirement', 'No') == 'Yes'
                    details['cost_sharing_description'] = self._clean_html_entities(synopsis.get('costSharingDescription', ''))

                    # Additional Information
                    details['additional_info_url'] = synopsis.get('additionalInformationURL', '')
                    details['additional_info_text'] = self._clean_html_entities(synopsis.get('additionalInformationText', ''))

                    # Timeline Information
                    details['archive_date'] = synopsis.get('archiveDate') or None
                    details['forecast_date'] = synopsis.get('estimatedSynopsisPostDate') or None
                    details['close_date_explanation'] = self._clean_html_entities(synopsis.get('closeDateExplanation', ''))

                    # Award Information (range instead of single amount)
                    details['expected_number_of_awards'] = synopsis.get('expectedNumberOfAwards', '')
                    details['award_floor'] = self._parse_amount(str(award_floor)) if award_floor else None
                    details['award_ceiling'] = self._parse_amount(str(award_ceiling)) if award_ceiling else None

                    # Attachments - PDFs, solicitations, amendments
                    details['attachments'] = self._extract_attachments(synopsis)

                    # Version/Amendment Tracking
                    details['version'] = synopsis.get('version', '')
                    details['last_updated_date'] = synopsis.get('lastUpdatedDate', '')

                return details
            else:
                print(f"[GRANTS SERVICE] fetchOpportunity failed for {opportunity_id}: {response.status_code}")
                return {}

        except Exception as e:
            print(f"[GRANTS SERVICE] Error fetching opportunity {opportunity_id}: {e}")
            return {}

    def _parse_grants_response(self, data: Dict) -> List[Dict[str, Any]]:
        """Parse grants.gov API response into our standard format"""
        grants = []

        # Handle different response formats
        opportunities = data.get('oppHits', [])
        if not opportunities:
            opportunities = data.get('opportunities', [])

        for opp in opportunities[:5]:  # Limit to 5
            try:
                # Extract deadline
                deadline = opp.get('closeDate', opp.get('applicationDeadline'))
                if deadline:
                    deadline = self._parse_date(deadline)
                else:
                    deadline = (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')

                # Extract funding amount (often not specified)
                amount_text = opp.get('awardCeiling', opp.get('estimatedFunding', 'Not specified'))
                amount = self._parse_amount(amount_text)

                grant = {
                    "id": opp.get('opportunityNumber', f"grant-{len(grants)+1}"),
                    "title": opp.get('opportunityTitle', 'Technology Workforce Grant'),
                    "funder": opp.get('agencyName', opp.get('organizationName', 'Federal Agency')),
                    "amount": amount,
                    "deadline": deadline,
                    "description": opp.get('description', opp.get('synopsis', 'Federal grant opportunity for technology workforce development')),
                    "requirements": self._extract_requirements(opp.get('description', '')),
                    "contact": opp.get('contactEmail', 'grants@agency.gov'),
                    "application_url": opp.get('link', f"https://grants.gov/view/{opp.get('opportunityNumber', 'opportunity')}")
                }
                # Calculate enhanced match score after building the full grant
                # Note: org_profile is not available in _parse_grants_response, fallback to standard scoring
                grant["match_score"] = self._calculate_enhanced_match_score(grant, org_profile=None)

                grants.append(grant)

            except Exception as e:
                print(f"Error parsing grant opportunity: {e}")
                continue

        return grants if grants else self._get_mock_grants()

    def _clean_html_entities(self, text: str) -> str:
        """Clean HTML entities from text"""
        if not text:
            return text

        clean_text = re.sub(r'&amp;', '&', text)
        clean_text = re.sub(r'&lt;', '<', clean_text)
        clean_text = re.sub(r'&gt;', '>', clean_text)
        clean_text = re.sub(r'&quot;', '"', clean_text)
        clean_text = re.sub(r'&[a-zA-Z0-9#]+;', '', clean_text)
        return clean_text.strip()

    def _parse_date(self, date_str: str) -> str:
        """Parse various date formats to YYYY-MM-DD"""
        try:
            # Try different date formats
            formats = ['%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']

            for fmt in formats:
                try:
                    parsed = datetime.strptime(str(date_str)[:19], fmt)
                    return parsed.strftime('%Y-%m-%d')
                except ValueError:
                    continue

            # If all else fails, return future date
            return (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')

        except (ValueError, TypeError, AttributeError):
            return (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')

    def _parse_amount(self, amount_text: str) -> int:
        """Extract numeric amount from text"""
        try:
            if not amount_text or amount_text == 'Not specified':
                return 250000  # Default amount

            # Remove non-numeric characters except periods and commas
            clean = re.sub(r'[^\d.,]', '', str(amount_text))
            clean = clean.replace(',', '')

            if '.' in clean:
                return int(float(clean))
            else:
                return int(clean) if clean else 250000

        except (ValueError, TypeError, AttributeError):
            return 250000  # Default amount

    def _calculate_match_score(self, title: str) -> int:
        """Calculate match score based on keywords (legacy method)"""
        keywords = ['technology', 'workforce', 'training', 'education', 'stem', 'coding', 'cyber', 'digital']
        title_lower = title.lower()

        matches = sum(1 for keyword in keywords if keyword in title_lower)
        base_score = 70 + (matches * 5)

        return min(95, base_score)

    def _calculate_enhanced_match_score(self, grant: Dict[str, Any], org_profile: Optional[Dict[str, Any]] = None) -> int:
        """
        Calculate enhanced match score using semantic similarity with historical RFPs.
        If org_profile is provided, uses organization-specific matching for more accurate scoring.

        Args:
            grant: Grant opportunity dictionary
            org_profile: Optional organization profile for org-aware scoring

        Returns:
            Match score 0-100
        """
        try:
            # If organization profile provided, use org-aware scoring
            if org_profile and self.org_matching_service:
                try:
                    print(f"[GRANTS] Calculating org-aware match score for '{grant.get('title', 'Unknown')[:60]}...'")

                    # Build semantic similarity scores using semantic service
                    rfp_similarities = []
                    if self.semantic_service:
                        try:
                            grant_text = f"{grant.get('title', '')} {grant.get('description', '')}"
                            rfp_similarities = self.semantic_service.find_similar_rfps(grant_text, limit=3)
                        except Exception as e:
                            print(f"[GRANTS] Could not find similar RFPs: {e}")

                    # Get keyword matching score (using org-specific keywords)
                    primary_kw, secondary_kw = self.org_matching_service.build_search_keywords(org_profile)
                    all_keywords = primary_kw + secondary_kw
                    grant_text = (grant.get('title', '') + ' ' + grant.get('description', '')).lower()
                    keyword_matches = sum(1 for kw in all_keywords if kw.lower() in grant_text)
                    keyword_score = min(100, (keyword_matches * 10) if all_keywords else 0)

                    # Get semantic similarity score
                    semantic_score = 0
                    if rfp_similarities:
                        best_similarity = max(rfp.get('similarity_score', 0) for rfp in rfp_similarities)
                        if best_similarity >= 0.85:
                            semantic_score = min(100, int(85 + (best_similarity - 0.85) * 33))
                        elif best_similarity >= 0.70:
                            semantic_score = min(85, int(70 + (best_similarity - 0.70) * 66))
                        elif best_similarity >= 0.55:
                            semantic_score = min(70, int(55 + (best_similarity - 0.55) * 66))

                    # Calculate organization-aware match score
                    org_scores = self.org_matching_service.calculate_organization_match_score(
                        org_profile, grant, keyword_score, semantic_score
                    )
                    org_aware_score = int(org_scores.get('overall_score', 50))

                    print(f"[GRANTS] Org-aware score breakdown for '{grant.get('title', 'Unknown')[:50]}...':")
                    print(f"  Overall: {org_aware_score}, Keyword: {org_scores.get('keyword_matching', 0):.0f}, Semantic: {org_scores.get('semantic_similarity', 0):.0f}")
                    print(f"  Funding: {org_scores.get('funding_alignment', 0):.0f}, Demographics: {org_scores.get('demographic_alignment', 0):.0f}, Geographic: {org_scores.get('geographic_alignment', 0):.0f}")

                    return org_aware_score

                except Exception as e:
                    print(f"[GRANTS] Error in org-aware scoring, falling back to standard: {e}")

            # Check if this grant already exists in the database with a match score (fallback path)
            opportunity_id = grant.get('id') or grant.get('opportunity_id')
            if opportunity_id and self.supabase:
                try:
                    existing = self.supabase.table("scraped_grants")\
                        .select("match_score")\
                        .eq("opportunity_id", opportunity_id)\
                        .execute()

                    if existing.data and existing.data[0].get('match_score'):
                        cached_score = existing.data[0]['match_score']
                        print(f"[GRANTS] Using cached match score for '{grant.get('title', 'Unknown')[:50]}...': {cached_score}%")
                        return cached_score
                except Exception as e:
                    print(f"[GRANTS] Could not check for cached score: {e}")

            # Import the standalone scoring service (fallback to standard Per Scholas-specific scoring)
            from match_scoring import calculate_match_score

            # Find similar RFPs using semantic search if available
            rfp_similarities = []
            if self.semantic_service:
                try:
                    grant_text = f"{grant.get('title', '')} {grant.get('description', '')}"
                    rfp_similarities = self.semantic_service.find_similar_rfps(grant_text, limit=3)

                    if rfp_similarities:
                        print(f"[GRANTS] Found {len(rfp_similarities)} similar RFPs for '{grant.get('title', 'Unknown')[:50]}...'")
                        for rfp in rfp_similarities:
                            print(f"  - {rfp.get('title', 'Unknown')[:60]}... (similarity: {rfp.get('similarity_score', 0):.2f})")
                except Exception as e:
                    print(f"[GRANTS] Could not find similar RFPs: {e}")

            # Calculate enhanced score with semantic similarity
            # This gives us better scoring based on:
            # - Core keywords (40 pts)
            # - Semantic similarity with historical RFPs (30 pts) ← NEW!
            # - Funding amount alignment (15 pts)
            # - Deadline feasibility (5 pts)
            # - Domain penalties for non-relevant grants
            enhanced_score = calculate_match_score(grant, rfp_similarities)

            print(f"[GRANTS] Enhanced match score for '{grant.get('title', 'Unknown')[:60]}...': {enhanced_score}%")
            return enhanced_score

        except Exception as e:
            print(f"[GRANTS] Error calculating enhanced match score: {e}")
            # Fallback to legacy scoring
            return self._calculate_match_score(grant.get('title', ''))

    def _extract_requirements(self, description: str) -> List[str]:
        """Extract requirements from description"""
        if not description:
            return ["See full opportunity details on grants.gov"]

        # Clean HTML from description first
        clean_desc = re.sub(r'<[^>]+>', '', description)  # Remove HTML tags
        clean_desc = re.sub(r'&nbsp;', ' ', clean_desc)  # Replace &nbsp; with spaces
        clean_desc = re.sub(r'&amp;', '&', clean_desc)  # Replace &amp; with &
        clean_desc = re.sub(r'&lt;', '<', clean_desc)  # Replace &lt; with <
        clean_desc = re.sub(r'&gt;', '>', clean_desc)  # Replace &gt; with >
        clean_desc = re.sub(r'&quot;', '"', clean_desc)  # Replace &quot; with "
        clean_desc = re.sub(r'&[a-zA-Z0-9#]+;', '', clean_desc)  # Remove remaining HTML entities

        # Look for actual requirements in the text
        requirements = []
        desc_lower = clean_desc.lower()

        # Look for common requirement patterns
        requirement_patterns = [
            (r'must be.*?(?=\.|;|\n|$)', 'eligibility requirement'),
            (r'applicant.*?must.*?(?=\.|;|\n|$)', 'applicant requirement'),
            (r'eligible.*?organizations?.*?(?=\.|;|\n|$)', 'organization eligibility'),
            (r'required.*?to.*?(?=\.|;|\n|$)', 'general requirement'),
            (r'deadline.*?(?=\.|;|\n|$)', 'deadline requirement'),
            (r'matching.*?funds?.*?(?=\.|;|\n|$)', 'matching funds'),
            (r'collaboration.*?(?=\.|;|\n|$)', 'collaboration requirement'),
            (r'partnership.*?(?=\.|;|\n|$)', 'partnership requirement')
        ]

        for pattern, req_type in requirement_patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            for match in matches[:2]:  # Limit to 2 per pattern
                # Clean up the match
                clean_match = re.sub(r'<[^>]+>', '', match).strip()
                clean_match = re.sub(r'&nbsp;', ' ', clean_match)
                clean_match = re.sub(r'\s+', ' ', clean_match)
                if len(clean_match) > 10 and len(clean_match) < 150:  # Reasonable length
                    requirements.append(clean_match.capitalize())

        # If no specific requirements found, extract key phrases
        if not requirements:
            key_phrases = []
            if 'non-profit' in desc_lower or 'nonprofit' in desc_lower:
                key_phrases.append("Non-profit organization eligibility")
            if 'institution' in desc_lower and 'education' in desc_lower:
                key_phrases.append("Educational institution involvement")
            if 'collaboration' in desc_lower or 'partner' in desc_lower:
                key_phrases.append("Partnership or collaboration required")
            if 'community' in desc_lower:
                key_phrases.append("Community engagement component")
            if 'research' in desc_lower:
                key_phrases.append("Research component required")

            requirements = key_phrases[:4] if key_phrases else ["See full eligibility requirements on grants.gov"]

        return requirements[:4]  # Limit to 4 requirements for display

    def _extract_attachments(self, synopsis: dict) -> List[Dict[str, str]]:
        """Extract attachment information from Grants.gov synopsis"""
        attachments = []

        # Grants.gov provides attachments in relatedDocuments
        if 'relatedDocuments' in synopsis:
            for doc in synopsis.get('relatedDocuments', []):
                attachments.append({
                    'title': doc.get('description', doc.get('fileName', 'Document')),
                    'url': doc.get('url', ''),
                    'type': doc.get('fileType', 'pdf')
                })

        # Also check for attachmentLinks (alternative field name)
        if 'attachmentLinks' in synopsis:
            for link in synopsis.get('attachmentLinks', []):
                attachments.append({
                    'title': link.get('description', 'Attachment'),
                    'url': link.get('url', ''),
                    'type': 'pdf'
                })

        return attachments

    def _get_mock_grants(self) -> List[Dict[str, Any]]:
        """Fallback mock data if API fails"""
        return [
            {
                "id": "ed-stem-workforce-2025",
                "title": "Department of Education STEM Workforce Development Grant",
                "funder": "U.S. Department of Education",
                "amount": 750000,
                "deadline": "2025-03-15",
                "match_score": 94,
                "description": "Federal grant to support innovative STEM workforce development programs that prepare underrepresented populations for high-demand technology careers",
                "requirements": ["Educational institution partnership", "Focus on underrepresented groups", "Industry collaboration", "Measurable outcomes"],
                "contact": "stemgrants@ed.gov",
                "application_url": "https://grants.gov/view/ED-STEM-WORKFORCE-2025"
            },
            {
                "id": "nsf-ate-advanced-2025",
                "title": "NSF Advanced Technological Education Program",
                "funder": "National Science Foundation",
                "amount": 600000,
                "deadline": "2025-02-28",
                "match_score": 91,
                "description": "Support for community colleges and universities to improve technician education in high-technology fields critical to the nation's economic growth",
                "requirements": ["Community college involvement", "Technology focus", "Industry partnerships", "Student outcomes tracking"],
                "contact": "ate@nsf.gov",
                "application_url": "https://grants.gov/view/NSF-ATE-ADVANCED-2025"
            },
            {
                "id": "dol-wioa-tech-2025",
                "title": "DOL WIOA Technology Training Initiative",
                "funder": "U.S. Department of Labor",
                "amount": 850000,
                "deadline": "2025-04-30",
                "match_score": 89,
                "description": "Workforce Innovation and Opportunity Act funding for technology training programs serving displaced workers and underemployed individuals",
                "requirements": ["WIOA compliance", "Displaced worker focus", "Employer engagement", "Credential attainment"],
                "contact": "wioa@dol.gov",
                "application_url": "https://grants.gov/view/DOL-WIOA-TECH-2025"
            }
        ]

# Test function
def test_grants_service():
    """Test the grants service"""
    service = GrantsGovService()
    grants = service.search_grants("technology workforce development", limit=3)

    print(f"Found {len(grants)} grants:")
    for grant in grants:
        print(f"- {grant['title']} ({grant['funder']}) - ${grant['amount']:,}")

    return grants

if __name__ == "__main__":
    test_grants_service()