#!/usr/bin/env python3
"""
Morning Brief Generation Job

Runs daily at 8am for each active organization.
Selects top 3 grants and sends email brief.
"""

import os
import sys
import asyncio
from datetime import datetime, date
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from email_service import get_email_service


def _get_org_notification_prefs(org_id: int, supabase) -> dict:
    """Get notification preferences for an org, with defaults.
    
    Gracefully handles missing notification_preferences column — returns defaults
    if migration 006_notification_preferences.sql hasn't been run yet.
    """
    default_prefs = {
        "deadline_alerts_enabled": True,
        "deadline_alert_days": [2, 7, 30],
        "morning_briefs_enabled": True,
        "email_notifications_enabled": True
    }
    try:
        result = supabase.table("organization_config") \
            .select("notification_preferences") \
            .eq("id", org_id) \
            .limit(1) \
            .execute()
        
        if result.data and result.data[0].get("notification_preferences"):
            prefs = result.data[0]["notification_preferences"]
            return {**default_prefs, **prefs}
    except Exception as e:
        error_str = str(e)
        # Column doesn't exist — migration not run yet (Issue #62)
        if "notification_preferences does not exist" in error_str or "42703" in error_str:
            # Silent fallback to defaults — migration pending
            pass
        else:
            print(f"[BRIEF] Error fetching prefs for org {org_id}: {e}")
    
    return default_prefs


async def generate_brief_for_org(org_id: int, org_name: str, org_email: str, supabase):
    """
    Generate and send morning brief for one organization.
    
    Returns dict with status, grant_count, sent
    """
    email_service = get_email_service()
    
    print(f"\n[BRIEF] Processing org {org_id} ({org_name})")
    
    # Check notification preferences (Issue #59)
    prefs = _get_org_notification_prefs(org_id, supabase)
    
    if not prefs.get("email_notifications_enabled", True):
        print(f"[BRIEF] Org {org_id} has email notifications disabled, skipping")
        return {"status": "skipped", "reason": "email_disabled", "grant_count": 0}
    
    if not prefs.get("morning_briefs_enabled", True):
        print(f"[BRIEF] Org {org_id} has morning briefs disabled, skipping")
        return {"status": "skipped", "reason": "briefs_disabled", "grant_count": 0}
    
    # Get top grants for this org
    # Filter: match_score > 70, status = active, deadline in future
    today = date.today().isoformat()
    
    try:
        result = supabase.table("org_grants") \
            .select(
                "grant_id, match_score, llm_summary, scraped_grants(title, funder, amount, deadline, description)"
            ) \
            .eq("org_id", org_id) \
            .eq("status", "active") \
            .gte("match_score", 70) \
            .execute()
        
        grants_data = result.data
        
        if not grants_data:
            print(f"[BRIEF] No high-scoring grants for org {org_id}")
            return {
                "status": "skipped",
                "reason": "no_grants",
                "grant_count": 0
            }
        
        # Filter out past deadlines and flatten
        grants = []
        for item in grants_data:
            grant_info = item.get("scraped_grants", {})
            if not grant_info:
                continue
            
            deadline = grant_info.get("deadline")
            if deadline and deadline < today:
                continue  # Skip past deadlines
            
            grants.append({
                "grant_id": item["grant_id"],
                "title": grant_info.get("title", "Untitled"),
                "funder": grant_info.get("funder", "Unknown"),
                "amount": grant_info.get("amount", 0),
                "deadline": deadline or "TBD",
                "match_score": item.get("match_score", 0),
                "summary": item.get("llm_summary") or grant_info.get("description", "")[:300] or "No summary available"
            })
        
        if not grants:
            print(f"[BRIEF] All grants past deadline for org {org_id}")
            return {
                "status": "skipped",
                "reason": "all_expired",
                "grant_count": 0
            }
        
        # Sort by score descending, then deadline ascending (urgent first)
        grants.sort(
            key=lambda g: (
                -g["match_score"],  # Higher score first
                g["deadline"] if g["deadline"] != "TBD" else "9999-12-31"  # Sooner deadline first
            )
        )
        
        # Take top 3
        top_grants = grants[:3]
        
        print(f"[BRIEF] Selected {len(top_grants)} grants for org {org_id}")
        for i, g in enumerate(top_grants, 1):
            amount = g['amount'] or 0
            print(f"  {i}. {g['title']} ({g['match_score']}% match, ${amount:,})")
        
        # Send email
        result = await email_service.send_morning_brief(
            to=org_email,
            org_name=org_name,
            grants=top_grants
        )
        
        if result.get("status") == "sent":
            print(f"[BRIEF] ✅ Email sent to {org_email}")
            
            # Log to org_briefs table
            try:
                grant_ids = [g["grant_id"] for g in top_grants]
                
                # Generate markdown content for storage
                content_lines = [
                    f"# Daily Grant Brief for {org_name}",
                    f"*{len(top_grants)} Top Opportunities for {date.today().strftime('%B %d, %Y')}*",
                    ""
                ]
                
                for i, grant in enumerate(top_grants, 1):
                    amount = grant.get("amount") or 0
                    deadline = grant.get("deadline", "TBD")
                    content_lines.extend([
                        f"## {i}. {grant['title']}",
                        f"**Funder:** {grant['funder']}",
                        f"**Amount:** ${amount:,}" if amount else "**Amount:** Not specified",
                        f"**Deadline:** {deadline}",
                        f"**Match Score:** {grant['match_score']}%",
                        "",
                        grant.get("summary", "No summary available"),
                        "",
                        "---",
                        ""
                    ])
                
                brief_content = "\n".join(content_lines)
                
                # Snapshot of grant info at send time
                grant_summaries = [
                    {
                        "grant_id": g["grant_id"],
                        "title": g["title"],
                        "funder": g["funder"],
                        "amount": g.get("amount"),
                        "deadline": g.get("deadline"),
                        "match_score": g.get("match_score")
                    }
                    for g in top_grants
                ]
                
                supabase.table("org_briefs").insert({
                    "org_id": org_id,
                    "subject": f"☀️ Your Daily Grant Brief - {len(top_grants)} Top Opportunities",
                    "content": brief_content,
                    "content_format": "markdown",
                    "grant_ids": grant_ids,
                    "grant_summaries": grant_summaries,
                    "total_candidates": len(grants),
                    "delivery_channel": "email",
                    "delivery_address": org_email,
                    "delivered": True,
                    "sent_at": datetime.now().isoformat()
                }).execute()
                
                print(f"[BRIEF] Logged to org_briefs")
            except Exception as e:
                print(f"[BRIEF] ⚠️ Failed to log to org_briefs: {e}")
            
            return {
                "status": "sent",
                "grant_count": len(top_grants),
                "message_id": result.get("message_id")
            }
        else:
            print(f"[BRIEF] ❌ Email failed: {result.get('error')}")
            return {
                "status": "error",
                "error": result.get("error"),
                "grant_count": len(top_grants)
            }
    
    except Exception as e:
        print(f"[BRIEF] ❌ Error processing org {org_id}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "grant_count": 0
        }


async def main():
    """Main entry point - process all active orgs"""
    print(f"[BRIEF] Starting morning brief generation - {datetime.now()}")
    
    # Connect to database
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        print("[BRIEF] ❌ Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)
    
    supabase = create_client(supabase_url, supabase_key)
    
    # Get all active organizations
    # Join with users to get org name and email
    try:
        orgs_result = supabase.table("organization_config") \
            .select("id, name, users(email)") \
            .execute()
        
        orgs = orgs_result.data
        
        if not orgs:
            print("[BRIEF] No organizations found")
            return
        
        print(f"[BRIEF] Found {len(orgs)} organizations")
        
        # Process each org
        results = []
        for org in orgs:
            org_id = org["id"]
            org_name = org.get("name", "Your Organization")
            
            # Get first user email for this org
            users = org.get("users", [])
            if not users:
                print(f"[BRIEF] ⚠️ Org {org_id} ({org_name}) has no users, skipping")
                continue
            
            org_email = users[0].get("email")
            if not org_email:
                print(f"[BRIEF] ⚠️ Org {org_id} ({org_name}) has no email, skipping")
                continue
            
            result = await generate_brief_for_org(org_id, org_name, org_email, supabase)
            results.append({
                "org_id": org_id,
                "org_name": org_name,
                **result
            })
        
        # Summary
        print(f"\n[BRIEF] === Summary ===")
        sent_count = sum(1 for r in results if r.get("status") == "sent")
        skipped_count = sum(1 for r in results if r.get("status") == "skipped")
        error_count = sum(1 for r in results if r.get("status") == "error")
        
        print(f"[BRIEF] Sent: {sent_count}, Skipped: {skipped_count}, Errors: {error_count}")
        
        for result in results:
            status_emoji = {
                "sent": "✅",
                "skipped": "⏭️",
                "error": "❌"
            }.get(result["status"], "❓")
            
            print(f"[BRIEF] {status_emoji} {result['org_name']}: {result['status']}")
        
        print(f"[BRIEF] Complete - {datetime.now()}")
    
    except Exception as e:
        print(f"[BRIEF] ❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
