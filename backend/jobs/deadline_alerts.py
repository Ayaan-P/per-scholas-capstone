#!/usr/bin/env python3
"""
Deadline Alert Job

Runs daily at 8 AM (alongside morning briefs).
Sends email alerts to organizations when saved grants are approaching deadlines:
  - 30 days out: "heads up" upcoming reminder
  - 7 days out:  "soon" alert
  - 2 days out:  "urgent" final warning

No dedup state needed — deadline windows are non-overlapping (30d, 7d, 2d),
so each grant triggers each alert exactly once when the job runs on that day.
"""

import os
import sys
import asyncio
from datetime import date, timedelta
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from email_service import get_email_service


# Deadline windows: (urgency_label, days_from_today, window_days)
# We check: deadline is within [today + days, today + days + window)
ALERT_WINDOWS = [
    ("urgent",   2,  1),   # deadline is 2 days from now
    ("soon",     7,  1),   # deadline is 7 days from now
    ("upcoming", 30, 1),   # deadline is 30 days from now
]


def _build_alert_date_ranges():
    """
    Return dict of urgency → (start_date_str, end_date_str) for query ranges.
    We use an inclusive 2-day window to tolerate slight date drift.
    """
    today = date.today()
    ranges = {}
    for urgency, days, _ in ALERT_WINDOWS:
        target = today + timedelta(days=days)
        # Allow ±1 day window to catch edge cases (grants posted with time components)
        start = (target - timedelta(days=1)).isoformat()
        end = (target + timedelta(days=1)).isoformat()
        ranges[urgency] = (start, end, days)
    return ranges


async def get_deadline_alerts_for_org(org_id: int, supabase) -> list:
    """
    For a given org, find saved/active grants with deadlines in the alert windows.
    Returns list of alert dicts (one per grant per urgency level).
    """
    date_ranges = _build_alert_date_ranges()
    alerts = []

    for urgency, (start_date, end_date, days_left) in date_ranges.items():
        try:
            result = supabase.table("org_grants") \
                .select(
                    "id, grant_id, match_score, status, "
                    "scraped_grants(id, title, funder, amount, deadline, application_url)"
                ) \
                .eq("org_id", org_id) \
                .in_("status", ["active", "saved", "in_progress"]) \
                .execute()

            if not result.data:
                continue

            for row in result.data:
                grant = row.get("scraped_grants", {})
                if not grant:
                    continue

                deadline_str = grant.get("deadline")
                if not deadline_str:
                    continue

                # Normalize: deadline may be a full timestamp or just a date
                deadline_date = deadline_str[:10]  # "YYYY-MM-DD"

                if start_date <= deadline_date <= end_date:
                    alerts.append({
                        "urgency": urgency,
                        "days_left": days_left,
                        "org_grant_id": row.get("id"),
                        "grant_id": row.get("grant_id"),
                        "title": grant.get("title", "Untitled"),
                        "funder": grant.get("funder", "Unknown"),
                        "amount": grant.get("amount", 0),
                        "deadline": deadline_date,
                        "application_url": grant.get("application_url", "https://fundfish.pro/dashboard"),
                        "match_score": row.get("match_score", 0),
                    })

        except Exception as e:
            print(f"[DEADLINE] Error querying org {org_id} for {urgency}: {e}")

    # Deduplicate by (grant_id, urgency) — shouldn't happen, but safety net
    seen = set()
    unique_alerts = []
    for a in alerts:
        key = (a["grant_id"], a["urgency"])
        if key not in seen:
            seen.add(key)
            unique_alerts.append(a)

    return unique_alerts


async def process_org_deadline_alerts(org_id: int, org_name: str, org_email: str, supabase):
    """
    Check and send deadline alerts for one organization.
    Returns dict with status and alert counts.
    """
    email_service = get_email_service()
    print(f"\n[DEADLINE] Processing org {org_id} ({org_name})")

    alerts = await get_deadline_alerts_for_org(org_id, supabase)

    if not alerts:
        print(f"[DEADLINE] No upcoming deadlines for org {org_id}")
        return {"status": "skipped", "reason": "no_alerts", "alert_count": 0}

    # Group by urgency for logging
    urgency_counts = {}
    for a in alerts:
        urgency_counts[a["urgency"]] = urgency_counts.get(a["urgency"], 0) + 1

    print(f"[DEADLINE] Found {len(alerts)} alerts: {urgency_counts}")

    result = await email_service.send_deadline_alert(
        to=org_email,
        org_name=org_name,
        alerts=alerts
    )

    if result.get("status") == "sent":
        print(f"[DEADLINE] ✅ Alert email sent to {org_email} ({len(alerts)} grants)")
        return {
            "status": "sent",
            "alert_count": len(alerts),
            "urgency_breakdown": urgency_counts,
            "message_id": result.get("message_id")
        }
    elif result.get("status") == "disabled":
        print(f"[DEADLINE] ⚠️ Email service disabled (RESEND_API_KEY not set)")
        return {"status": "disabled", "alert_count": len(alerts)}
    else:
        print(f"[DEADLINE] ❌ Email failed: {result.get('error')}")
        return {"status": "error", "error": result.get("error"), "alert_count": len(alerts)}


async def main():
    """Main entry point — process all orgs"""
    from datetime import datetime
    print(f"[DEADLINE] Starting deadline alert job — {datetime.now()}")

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        print("[DEADLINE] ❌ Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)

    supabase = create_client(supabase_url, supabase_key)

    # Get all orgs with their users' emails
    try:
        orgs_result = supabase.table("organization_config") \
            .select("id, name, users(email)") \
            .execute()
        orgs = orgs_result.data or []
    except Exception as e:
        print(f"[DEADLINE] ❌ Failed to fetch orgs: {e}")
        sys.exit(1)

    if not orgs:
        print("[DEADLINE] No organizations found")
        return

    print(f"[DEADLINE] Found {len(orgs)} organizations to check")

    results = []
    for org in orgs:
        org_id = org["id"]
        org_name = org.get("name", "Your Organization")
        users = org.get("users", [])

        if not users:
            print(f"[DEADLINE] ⚠️ Org {org_id} ({org_name}) has no users, skipping")
            continue

        org_email = users[0].get("email")
        if not org_email:
            print(f"[DEADLINE] ⚠️ Org {org_id} no email, skipping")
            continue

        result = await process_org_deadline_alerts(org_id, org_name, org_email, supabase)
        results.append({"org_id": org_id, "org_name": org_name, **result})

    # Summary
    print(f"\n[DEADLINE] === Summary ===")
    for r in results:
        emoji = {"sent": "✅", "skipped": "⏭️", "error": "❌", "disabled": "⚠️"}.get(r["status"], "❓")
        print(f"[DEADLINE] {emoji} {r['org_name']}: {r['status']} ({r.get('alert_count', 0)} alerts)")

    print(f"[DEADLINE] Complete — {datetime.now()}")


if __name__ == "__main__":
    asyncio.run(main())
