"""
Email delivery service - Morning briefs and notifications
"""

import os
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


class EmailService:
    """Send emails via Resend API"""
    
    def __init__(self):
        self.api_key = os.getenv('RESEND_API_KEY')
        self.from_email = os.getenv('FROM_EMAIL', 'FundFish <noreply@fundfish.pro>')
        self.enabled = bool(self.api_key)
        
        if not self.enabled:
            logger.warning("Email service disabled - RESEND_API_KEY not set")
        else:
            logger.info("Email service initialized with Resend")
    
    async def send_email(
        self,
        to: str,
        subject: str,
        html: str,
        text: Optional[str] = None
    ) -> dict:
        """
        Send an email via Resend.
        
        Args:
            to: Recipient email address
            subject: Email subject
            html: HTML body
            text: Plain text body (optional, will strip HTML if not provided)
        
        Returns:
            dict with status and message_id or error
        """
        if not self.enabled:
            logger.warning(f"Email to {to} not sent - service disabled")
            return {
                "status": "disabled",
                "error": "RESEND_API_KEY not configured"
            }
        
        try:
            import httpx
            
            # Strip HTML for plain text if not provided
            if not text:
                import re
                text = re.sub('<[^<]+?>', '', html)
            
            payload = {
                "from": self.from_email,
                "to": [to],
                "subject": subject,
                "html": html,
                "text": text
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.resend.com/emails",
                    json=payload,
                    headers=headers,
                    timeout=10.0
                )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Email sent to {to}: {data.get('id')}")
                return {
                    "status": "sent",
                    "message_id": data.get("id")
                }
            else:
                error = response.text
                logger.error(f"Email failed ({response.status_code}): {error}")
                return {
                    "status": "error",
                    "error": error
                }
        
        except Exception as e:
            logger.error(f"Email error: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def send_morning_brief(
        self,
        to: str,
        org_name: str,
        grants: List[dict]
    ) -> dict:
        """
        Send a morning brief email with top grants.
        
        Args:
            to: Recipient email
            org_name: Organization name
            grants: List of grant dicts (title, funder, amount, deadline, match_score, summary)
        
        Returns:
            dict with status
        """
        if not grants:
            logger.info(f"No grants to send to {org_name}")
            return {"status": "skipped", "reason": "no_grants"}
        
        # Build HTML email
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your Daily Grant Brief</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #00529B; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
        .grant {{ background: #f8f9fa; border-left: 4px solid #00529B; padding: 20px; margin: 20px 0; border-radius: 4px; }}
        .grant-title {{ font-size: 18px; font-weight: 600; color: #00529B; margin-bottom: 8px; }}
        .grant-meta {{ color: #666; font-size: 14px; margin: 8px 0; }}
        .match-score {{ display: inline-block; background: #28a745; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; }}
        .cta {{ display: inline-block; background: #00529B; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0;">🐟 Your Daily Grant Brief</h1>
            <p style="margin: 8px 0 0 0; opacity: 0.9;">Top {len(grants)} opportunities for {org_name}</p>
        </div>
        
        <div style="padding: 20px; background: white;">
            <p>Good morning! Here are today's top grant opportunities matched to your mission:</p>
"""
        
        for i, grant in enumerate(grants, 1):
            html += f"""
            <div class="grant">
                <div class="grant-title">#{i}. {grant.get('title', 'Untitled')}</div>
                <div class="grant-meta">
                    <strong>Funder:</strong> {grant.get('funder', 'Unknown')}<br>
                    <strong>Amount:</strong> ${grant.get('amount', 0):,}<br>
                    <strong>Deadline:</strong> {grant.get('deadline', 'TBD')}<br>
                    <span class="match-score">{grant.get('match_score', 0)}% Match</span>
                </div>
                <p style="margin-top: 12px;">{grant.get('summary', 'No summary available')}</p>
            </div>
"""
        
        html += """
            <div style="text-align: center;">
                <a href="https://fundfish.pro/opportunities" class="cta">View All Opportunities</a>
            </div>
        </div>
        
        <div class="footer">
            <p>FundFish - AI-powered grant discovery for nonprofits<br>
            <a href="https://fundfish.pro" style="color: #00529B;">fundfish.pro</a></p>
        </div>
    </div>
</body>
</html>
"""
        
        subject = f"☀️ Your Daily Grant Brief - {len(grants)} Top Opportunities"
        
        return await self.send_email(to, subject, html)


# Singleton
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create email service singleton"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
