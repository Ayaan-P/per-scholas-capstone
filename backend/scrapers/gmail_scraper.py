"""
Gmail Inbox Scraper for grant opportunities.

Fetches unread emails from Gmail inbox, parses them for grant information,
and marks them as processed.
"""

import os
import base64
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from email.utils import parsedate_to_datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .email_parser import EmailGrantParser


logger = logging.getLogger(__name__)


class GmailInboxScraper:
    """Scraper for Gmail inbox grant opportunities."""

    def __init__(self, token_path: Optional[str] = None):
        """
        Initialize Gmail scraper.

        Args:
            token_path: Path to gmail_token.json. If None, looks in backend directory.
        """
        if token_path is None:
            # Default to backend/gmail_token.json
            backend_dir = Path(__file__).parent.parent
            token_path = backend_dir / 'gmail_token.json'

        self.token_path = Path(token_path)
        self.service = None
        self.parser = EmailGrantParser()
        self.processed_label_id = None

        # Initialize Gmail service
        self._init_service()

    def _init_service(self):
        """Initialize Gmail API service."""
        if not self.token_path.exists():
            raise FileNotFoundError(
                f"Gmail token not found at {self.token_path}. "
                "Run gmail_auth_setup.py first to generate the token."
            )

        try:
            # Load credentials from token file
            creds = Credentials.from_authorized_user_file(
                str(self.token_path),
                scopes=[
                    'https://www.googleapis.com/auth/gmail.readonly',
                    'https://www.googleapis.com/auth/gmail.modify',
                ]
            )

            # Build service
            self.service = build('gmail', 'v1', credentials=creds)

            # Get or create processed label
            self._get_or_create_label()

            logger.info("Gmail service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Gmail service: {e}")
            raise

    def _get_or_create_label(self):
        """Get or create the 'GrantBot/Processed' label."""
        try:
            # List all labels
            labels = self.service.users().labels().list(userId='me').execute()
            label_list = labels.get('labels', [])

            # Look for our label
            for label in label_list:
                if label['name'] == 'GrantBot/Processed':
                    self.processed_label_id = label['id']
                    logger.info(f"Found existing label: {label['name']}")
                    return

            # Create label if it doesn't exist
            label = self.service.users().labels().create(
                userId='me',
                body={
                    'name': 'GrantBot/Processed',
                    'labelListVisibility': 'labelShow',
                    'messageListVisibility': 'show'
                }
            ).execute()

            self.processed_label_id = label['id']
            logger.info(f"Created new label: {label['name']}")

        except HttpError as e:
            logger.error(f"Error managing labels: {e}")
            raise

    def _get_message_details(self, message_id: str) -> Optional[Dict]:
        """
        Get full details of a message.

        Args:
            message_id: Gmail message ID

        Returns:
            Dictionary with message details or None
        """
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            return message

        except HttpError as e:
            logger.error(f"Error fetching message {message_id}: {e}")
            return None

    def _extract_email_data(self, message: Dict) -> Dict:
        """
        Extract structured data from Gmail message.

        Args:
            message: Gmail message object

        Returns:
            Dictionary with email data
        """
        headers = {h['name'].lower(): h['value'] for h in message['payload']['headers']}

        # Extract body
        body_text = ''
        body_html = None

        if 'parts' in message['payload']:
            # Multipart message
            for part in message['payload']['parts']:
                mime_type = part['mimeType']
                if mime_type == 'text/plain' and 'data' in part['body']:
                    body_text = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                elif mime_type == 'text/html' and 'data' in part['body']:
                    body_html = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
        else:
            # Single part message
            if 'data' in message['payload']['body']:
                body_data = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8', errors='ignore')
                if message['payload']['mimeType'] == 'text/html':
                    body_html = body_data
                else:
                    body_text = body_data

        # Parse received date
        received_date = None
        if 'date' in headers:
            try:
                received_date = parsedate_to_datetime(headers['date'])
            except Exception as e:
                logger.warning(f"Failed to parse date: {e}")

        return {
            'id': message['id'],
            'subject': headers.get('subject', 'No Subject'),
            'sender': headers.get('from', 'Unknown'),
            'body_text': body_text,
            'body_html': body_html,
            'received_date': received_date,
        }

    def _mark_as_processed(self, message_id: str):
        """
        Mark a message as processed by adding label and removing from UNREAD.

        Args:
            message_id: Gmail message ID
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={
                    'addLabelIds': [self.processed_label_id],
                    'removeLabelIds': ['UNREAD']
                }
            ).execute()

            logger.debug(f"Marked message {message_id} as processed")

        except HttpError as e:
            logger.error(f"Error marking message as processed: {e}")

    async def scrape(self, max_results: int = 50) -> List[Dict]:
        """
        Scrape unread emails from Gmail inbox for grant opportunities.

        Args:
            max_results: Maximum number of emails to process per run

        Returns:
            List of grant dictionaries
        """
        logger.info("Starting Gmail inbox scrape")
        grants = []

        try:
            # Query for unread messages in inbox
            results = self.service.users().messages().list(
                userId='me',
                labelIds=['INBOX'],
                q='is:unread',
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} unread messages")

            if not messages:
                return grants

            # Process each message
            for msg_ref in messages:
                message_id = msg_ref['id']

                # Get full message details
                message = self._get_message_details(message_id)
                if not message:
                    continue

                # Extract email data
                email_data = self._extract_email_data(message)

                # Parse for grant information
                grant = self.parser.parse_email(
                    subject=email_data['subject'],
                    sender=email_data['sender'],
                    body_text=email_data['body_text'],
                    body_html=email_data['body_html'],
                    received_date=email_data['received_date']
                )

                if grant:
                    # Add email-specific metadata
                    grant['email_id'] = message_id
                    grant['email_subject'] = email_data['subject']
                    grant['email_sender'] = email_data['sender']

                    grants.append(grant)
                    logger.info(f"Extracted grant from email: {email_data['subject']}")

                # Mark as processed (whether grant-related or not)
                self._mark_as_processed(message_id)

            logger.info(f"Scraped {len(grants)} grants from {len(messages)} emails")

        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
        except Exception as e:
            logger.error(f"Error during Gmail scrape: {e}", exc_info=True)

        return grants

    def get_stats(self) -> Dict:
        """
        Get statistics about inbox and processed emails.

        Returns:
            Dictionary with stats
        """
        try:
            # Unread count
            unread = self.service.users().messages().list(
                userId='me',
                labelIds=['INBOX'],
                q='is:unread',
                maxResults=1
            ).execute()

            # Processed count
            processed = self.service.users().messages().list(
                userId='me',
                labelIds=[self.processed_label_id],
                maxResults=1
            ).execute()

            return {
                'unread_count': unread.get('resultSizeEstimate', 0),
                'processed_count': processed.get('resultSizeEstimate', 0),
                'status': 'connected',
            }

        except HttpError as e:
            logger.error(f"Error getting stats: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }


# Convenience function for scheduler
async def scrape_gmail_inbox(max_results: int = 50) -> List[Dict]:
    """
    Scrape Gmail inbox for grant opportunities.

    Args:
        max_results: Maximum number of emails to process

    Returns:
        List of grant dictionaries
    """
    scraper = GmailInboxScraper()
    return await scraper.scrape(max_results=max_results)
