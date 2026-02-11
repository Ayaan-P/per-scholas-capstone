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
        self.from_email = os.getenv('FROM_EMAIL', 'FundFish <noreply@ayaanpupala.com>')
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
        
        # Build HTML email (matches fundfish.pro design)
        from datetime import datetime
        
        # Color scheme for top 3 grants
        colors = ['#006fb4', '#009ee0', '#00476e']
        
        # Date formatting
        today = datetime.now().strftime("%A, %b %d")
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f8fafc;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8fafc; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width: 600px; width: 100%;">
                    <tr>
                        <td style="background: white; border-radius: 12px; box-shadow: 0 2px 12px -2px rgba(0, 0, 0, 0.08);">
                            <!-- Header with logo -->
                            <div style="padding: 24px 32px; border-bottom: 1px solid #e5e7eb;">
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td>
                                            <a href="https://fundfish.pro" style="display: inline-flex; align-items: center; text-decoration: none;">
                                                <img src="https://fundfish.pro/logo.png" alt="FundFish" width="40" height="40" style="display: block; border-radius: 10px; margin-right: 12px;" />
                                                <span style="font-size: 24px; font-weight: 700; color: #006fb4;">fundfish</span>
                                            </a>
                                        </td>
                                        <td align="right">
                                            <span style="font-size: 13px; color: #9ca3af;">{today}</span>
                                        </td>
                                    </tr>
                                </table>
                            </div>
                            
                            <!-- Body -->
                            <div style="padding: 32px;">
                                <h1 style="margin: 0 0 8px 0; font-size: 24px; font-weight: 700; color: #111827;">Your Top {len(grants)} Grant Opportunities</h1>
                                <p style="margin: 0 0 24px 0; font-size: 14px; color: #6b7280;">Personalized matches for {org_name}</p>
"""
        
        for i, grant in enumerate(grants):
            color = colors[i] if i < len(colors) else colors[-1]
            amount = grant.get('amount', 0)
            amount_str = f"Up to ${amount:,}" if amount else "Amount TBD"
            
            html += f"""
                                <div style="background: #f8fafc; padding: 20px; border-radius: 8px; border-left: 4px solid {color}; margin-bottom: 16px;">
                                    <div style="margin-bottom: 12px;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                                            <tr>
                                                <td>
                                                    <h2 style="margin: 0; font-size: 18px; font-weight: 600; color: #111827;">{grant.get('title', 'Untitled')}</h2>
                                                </td>
                                                <td align="right">
                                                    <span style="background: {color}; color: white; padding: 4px 12px; border-radius: 6px; font-size: 13px; font-weight: 600; white-space: nowrap;">{grant.get('match_score', 0)}% Match</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </div>
                                    <div style="margin: 12px 0;">
                                        <p style="margin: 4px 0; font-size: 14px; color: #6b7280;"><strong style="color: #374151;">Funder:</strong> {grant.get('funder', 'Unknown')}</p>
                                        <p style="margin: 4px 0; font-size: 14px; color: #6b7280;"><strong style="color: #374151;">Amount:</strong> {amount_str}</p>
                                        <p style="margin: 4px 0; font-size: 14px; color: #6b7280;"><strong style="color: #374151;">Deadline:</strong> {grant.get('deadline', 'TBD')}</p>
                                    </div>
                                    <p style="margin: 16px 0 0 0; font-size: 14px; color: #374151; line-height: 1.6;">{grant.get('summary', 'No summary available')}</p>
                                    <a href="https://fundfish.pro/opportunities" style="display: inline-block; margin-top: 16px; padding: 10px 20px; background: {color}; color: white; text-decoration: none; border-radius: 8px; font-size: 14px; font-weight: 600;">View Details →</a>
                                </div>
"""
        
        html += """
                            </div>
                            
                            <!-- Footer -->
                            <div style="padding: 24px 32px; border-top: 1px solid #e5e7eb; text-align: center; background: #f8fafc;">
                                <p style="margin: 0 0 8px 0; font-size: 13px; color: #6b7280;">Powered by AI · Updated daily</p>
                                <p style="margin: 0; font-size: 12px; color: #9ca3af;">
                                    <a href="https://fundfish.pro" style="color: #006fb4; text-decoration: none;">fundfish.pro</a> · 
                                    <a href="https://fundfish.pro/opportunities" style="color: #006fb4; text-decoration: none;">View all opportunities</a>
                                </p>
                            </div>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
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
