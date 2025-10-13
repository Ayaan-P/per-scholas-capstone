"""
Email parser for extracting grant information from email content.

Handles various email formats from grant notification services, foundations,
and government agencies.
"""

import re
import dateutil.parser
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from bs4 import BeautifulSoup


class EmailGrantParser:
    """Parse emails to extract grant opportunity information."""

    # Common patterns for grant-related emails
    GRANT_KEYWORDS = [
        'grant', 'funding', 'opportunity', 'rfp', 'request for proposal',
        'application', 'deadline', 'award', 'foundation', 'nonprofit',
        'solicitation', 'nofo', 'notice of funding'
    ]

    # Patterns for extracting structured data
    AMOUNT_PATTERN = re.compile(r'\$\s*[\d,]+(?:\.\d{2})?(?:\s*(?:million|mil|thousand|k|M|K))?', re.IGNORECASE)
    DEADLINE_PATTERNS = [
        r'deadline[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
        r'due[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
        r'(?:due|deadline)[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
        r'applications?\s+(?:must\s+be\s+)?(?:received|submitted)(?:\s+by)?[:\s]*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
        r'submit(?:\s+by)?[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
        r'(\d{1,2}/\d{1,2}/\d{4})',
        r'(\d{4}-\d{2}-\d{2})',
    ]
    URL_PATTERN = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')

    def __init__(self):
        """Initialize the email parser."""
        pass

    def is_grant_related(self, subject: str, body: str) -> bool:
        """
        Determine if an email is grant-related.

        Args:
            subject: Email subject line
            body: Email body text

        Returns:
            True if email appears to be about grants
        """
        combined_text = f"{subject} {body}".lower()
        return any(keyword in combined_text for keyword in self.GRANT_KEYWORDS)

    def extract_html_text(self, html_content: str) -> str:
        """
        Extract clean text from HTML email content.

        Args:
            html_content: HTML string

        Returns:
            Clean text content
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text
        text = soup.get_text()

        # Break into lines and remove leading/trailing space
        lines = (line.strip() for line in text.splitlines())

        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))

        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)

        return text

    def extract_grant_amount(self, text: str) -> Optional[str]:
        """
        Extract grant amount from text.

        Args:
            text: Text to search

        Returns:
            Grant amount string or None
        """
        amounts = self.AMOUNT_PATTERN.findall(text)
        if amounts:
            # Return the largest amount found (likely the grant amount)
            return max(amounts, key=lambda x: self._normalize_amount(x))
        return None

    def _normalize_amount(self, amount_str: str) -> float:
        """Convert amount string to float for comparison."""
        # Remove $ and spaces
        amount_str = amount_str.replace('$', '').replace(',', '').strip()

        # Handle K/M suffixes
        multiplier = 1
        if amount_str.lower().endswith(('k', 'thousand')):
            multiplier = 1000
            amount_str = re.sub(r'[kK]|thousand', '', amount_str, flags=re.IGNORECASE)
        elif amount_str.lower().endswith(('m', 'mil', 'million')):
            multiplier = 1000000
            amount_str = re.sub(r'[mM]|mil|million', '', amount_str, flags=re.IGNORECASE)

        try:
            return float(amount_str.strip()) * multiplier
        except ValueError:
            return 0.0

    def extract_deadline(self, text: str) -> Optional[datetime]:
        """
        Extract application deadline from text.

        Args:
            text: Text to search

        Returns:
            Deadline datetime or None
        """
        for pattern in self.DEADLINE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                date_str = match.group(1) if match.lastindex else match.group(0)
                try:
                    # Parse the date
                    deadline = dateutil.parser.parse(date_str, fuzzy=True)

                    # Only return future dates
                    if deadline > datetime.now():
                        return deadline
                except (ValueError, TypeError):
                    continue

        return None

    def extract_urls(self, text: str) -> List[str]:
        """
        Extract all URLs from text.

        Args:
            text: Text to search

        Returns:
            List of URLs
        """
        urls = self.URL_PATTERN.findall(text)
        # Clean up URLs (remove trailing punctuation)
        cleaned_urls = []
        for url in urls:
            url = url.rstrip('.,;:!?)')
            cleaned_urls.append(url)
        return cleaned_urls

    def extract_organization(self, sender: str, text: str) -> Optional[str]:
        """
        Extract organization name from sender or content.

        Args:
            sender: Email sender
            text: Email body

        Returns:
            Organization name or None
        """
        # Try to extract from sender email
        if '@' in sender:
            domain = sender.split('@')[1].split('.')[0]
            # Clean up common domains
            if domain not in ['gmail', 'yahoo', 'outlook', 'hotmail']:
                return domain.title()

        # Try to find organization mentions in first few lines
        lines = text.split('\n')[:10]
        for line in lines:
            # Look for "From XYZ Foundation" or "XYZ Organization"
            org_match = re.search(r'(?:from|by)\s+([A-Z][A-Za-z\s]+(?:Foundation|Organization|Institute|Fund|Trust))', line)
            if org_match:
                return org_match.group(1).strip()

        return None

    def parse_email(
        self,
        subject: str,
        sender: str,
        body_text: str,
        body_html: Optional[str] = None,
        received_date: Optional[datetime] = None
    ) -> Optional[Dict]:
        """
        Parse an email and extract grant information.

        Args:
            subject: Email subject
            sender: Email sender
            body_text: Plain text body
            body_html: HTML body (optional)
            received_date: When email was received

        Returns:
            Dictionary with grant info, or None if not grant-related
        """
        # Use HTML if available, otherwise plain text
        if body_html:
            text_content = self.extract_html_text(body_html)
        else:
            text_content = body_text

        # Check if grant-related
        if not self.is_grant_related(subject, text_content):
            return None

        # Extract information
        grant_amount = self.extract_grant_amount(text_content)
        deadline = self.extract_deadline(text_content)
        urls = self.extract_urls(text_content)
        organization = self.extract_organization(sender, text_content)

        # Build grant dictionary
        grant_data = {
            'title': subject,  # Use subject as title
            'description': text_content[:500],  # First 500 chars as description
            'source': 'gmail_inbox',
            'source_url': urls[0] if urls else None,  # Use first URL as source
            'amount': grant_amount,
            'deadline': deadline.isoformat() if deadline else None,
            'eligibility': None,  # Could be extracted with more sophisticated NLP
            'focus_areas': self._extract_focus_areas(text_content),
            'organization': organization or 'Unknown',
            'scraped_at': (received_date or datetime.now()).isoformat(),
        }

        return grant_data

    def _extract_focus_areas(self, text: str) -> Optional[str]:
        """
        Extract focus areas/categories from text.

        Args:
            text: Email text content

        Returns:
            Comma-separated focus areas or None
        """
        # Common focus area keywords
        focus_keywords = {
            'education': ['education', 'school', 'student', 'learning', 'teacher'],
            'health': ['health', 'medical', 'healthcare', 'wellness', 'mental health'],
            'environment': ['environment', 'climate', 'sustainability', 'conservation'],
            'arts': ['arts', 'culture', 'museum', 'theater', 'music'],
            'community': ['community', 'neighborhood', 'local', 'civic'],
            'technology': ['technology', 'tech', 'digital', 'innovation', 'stem'],
            'social justice': ['justice', 'equity', 'diversity', 'inclusion', 'civil rights'],
        }

        text_lower = text.lower()
        found_areas = []

        for area, keywords in focus_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                found_areas.append(area)

        return ', '.join(found_areas) if found_areas else None

    def parse_batch(self, emails: List[Dict]) -> List[Dict]:
        """
        Parse multiple emails at once.

        Args:
            emails: List of email dictionaries with subject, sender, body, etc.

        Returns:
            List of parsed grant dictionaries
        """
        grants = []
        for email in emails:
            grant = self.parse_email(
                subject=email.get('subject', ''),
                sender=email.get('sender', ''),
                body_text=email.get('body_text', ''),
                body_html=email.get('body_html'),
                received_date=email.get('received_date')
            )
            if grant:
                grants.append(grant)

        return grants
