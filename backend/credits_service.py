"""
Credits system service for managing user credits, subscriptions, and usage tracking.
Integrates with Stripe for payment processing and subscription management.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from decimal import Decimal
import httpx

from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Create Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Ensure service role authentication headers are set
def _make_auth_headers():
    """Create authorization headers for service role access."""
    return {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apikey": SUPABASE_KEY,
    }


class CreditsService:
    """Service for managing user credits, subscriptions, and transactions."""

    # Credit costs
    SEARCH_COST = 1  # Cost per search in credits

    # Subscription tier info
    SUBSCRIPTION_TIERS = {
        "free": {"monthly_credits": 5, "price_cents": 0},
        "pro": {"monthly_credits": 10, "price_cents": 1000},  # $10/month
    }

    # Credit packages
    CREDIT_PACKAGES = {
        "10_credits": {"credits": 10, "price_cents": 1000},  # $10
        "20_credits": {"credits": 20, "price_cents": 2000},  # $20
        "100_credits": {"credits": 100, "price_cents": 10000},  # $100
    }

    @staticmethod
    def initialize_user_credits(user_id: str, plan: str = "free") -> Dict[str, Any]:
        """Initialize credits for a new user (called during signup)."""
        try:
            headers = _make_auth_headers()
            headers["Content-Type"] = "application/json"

            with httpx.Client() as client:
                # Check if subscription already exists
                sub_url = f"{SUPABASE_URL}/rest/v1/user_subscriptions?select=id&user_id=eq.{user_id}"
                sub_response = client.get(sub_url, headers=headers)
                existing_sub = sub_response.json() if sub_response.status_code == 200 else []

                if not existing_sub:
                    # Get subscription plan
                    plan_url = f"{SUPABASE_URL}/rest/v1/subscription_plans?select=id,monthly_credits&name=eq.{plan}"
                    plan_response = client.get(plan_url, headers=headers)
                    if plan_response.status_code != 200:
                        return {"success": False, "error": f"Could not fetch subscription plan: {plan_response.text}"}

                    plan_data = plan_response.json()
                    if not plan_data:
                        return {"success": False, "error": f"Subscription plan '{plan}' not found"}

                    plan_id = plan_data[0]["id"]

                    # Create subscription
                    sub_insert_url = f"{SUPABASE_URL}/rest/v1/user_subscriptions"
                    sub_insert_response = client.post(sub_insert_url, headers=headers, json={
                        "user_id": user_id,
                        "plan_id": plan_id,
                        "status": "active",
                        "current_period_start": datetime.now().isoformat(),
                        "current_period_end": (datetime.now() + timedelta(days=30)).isoformat(),
                    })
                    if sub_insert_response.status_code not in [200, 201]:
                        return {"success": False, "error": f"Failed to create subscription: {sub_insert_response.text}"}

                # Check if credits record already exists
                credits_url = f"{SUPABASE_URL}/rest/v1/user_credits?select=id&user_id=eq.{user_id}"
                credits_response = client.get(credits_url, headers=headers)
                existing_credits = credits_response.json() if credits_response.status_code == 200 else []

                if existing_credits:
                    # Credits already exist, return success
                    return {"success": True, "data": existing_credits}

                # Initialize credits record
                next_reset = (datetime.now() + timedelta(days=30)).date()
                credits_insert_url = f"{SUPABASE_URL}/rest/v1/user_credits"
                credits_insert_response = client.post(credits_insert_url, headers=headers, json={
                    "user_id": user_id,
                    "total_credits": CreditsService.SUBSCRIPTION_TIERS.get(plan, {}).get("monthly_credits", 5),
                    "monthly_credits_used": 0,
                    "monthly_reset_date": next_reset.isoformat(),
                })

                if credits_insert_response.status_code not in [200, 201]:
                    return {"success": False, "error": f"Failed to initialize credits: {credits_insert_response.text}"}

                # Handle empty response (204 No Content)
                if credits_insert_response.status_code == 201 and credits_insert_response.text:
                    return {"success": True, "data": credits_insert_response.json()}
                else:
                    # If response is empty, fetch the created record to confirm
                    credits_url = f"{SUPABASE_URL}/rest/v1/user_credits?select=*&user_id=eq.{user_id}"
                    verify_response = client.get(credits_url, headers=headers)
                    if verify_response.status_code == 200:
                        data = verify_response.json()
                        return {"success": True, "data": data[0] if data else {}}
                    return {"success": True, "data": {}}
        except Exception as e:
            print(f"[DEBUG] initialize_user_credits exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_user_credits(user_id: str) -> Dict[str, Any]:
        """Get current credit balance for a user."""
        try:
            # Use direct HTTP request with service role auth to bypass RLS issues
            url = f"{SUPABASE_URL}/rest/v1/user_credits?select=user_id,total_credits,monthly_credits_used,monthly_reset_date&user_id=eq.{user_id}"
            headers = _make_auth_headers()
            headers["Content-Type"] = "application/json"

            with httpx.Client() as client:
                response = client.get(url, headers=headers)
                print(f"[DEBUG] get_user_credits status: {response.status_code}")

            if response.status_code != 200:
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}

            data = response.json()
            print(f"[DEBUG] get_user_credits data: {data}")
            if isinstance(data, list) and len(data) > 0:
                return {"success": True, "data": data[0]}
            return {"success": False, "error": "User credits not found"}
        except Exception as e:
            print(f"[DEBUG] get_user_credits exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_user_subscription(user_id: str) -> Dict[str, Any]:
        """Get user's current subscription plan."""
        try:
            url = f"{SUPABASE_URL}/rest/v1/user_subscriptions?select=*,subscription_plans(name,monthly_credits)&user_id=eq.{user_id}"
            headers = _make_auth_headers()
            headers["Content-Type"] = "application/json"

            with httpx.Client() as client:
                response = client.get(url, headers=headers)

            if response.status_code != 200:
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}

            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                return {"success": True, "data": data[0]}
            return {"success": False, "error": "User subscription not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def check_and_deduct_credits(user_id: str, amount: int = 1, reference_id: str = None) -> Dict[str, Any]:
        """
        Check if user has enough credits and deduct if they do.
        Returns success/failure and updated balance.
        """
        try:
            # Get current credits
            credits_response = CreditsService.get_user_credits(user_id)
            if not credits_response["success"]:
                return {"success": False, "error": "Could not fetch user credits"}

            current_balance = credits_response["data"]["total_credits"]

            # Check if enough credits
            if current_balance < amount:
                return {
                    "success": False,
                    "error": f"Insufficient credits. Required: {amount}, Available: {current_balance}",
                    "available": current_balance,
                }

            # Deduct credits
            new_balance = current_balance - amount
            headers = _make_auth_headers()
            headers["Content-Type"] = "application/json"

            with httpx.Client() as client:
                # Update user_credits
                update_url = f"{SUPABASE_URL}/rest/v1/user_credits?user_id=eq.{user_id}"
                update_response = client.patch(update_url, headers=headers, json={
                    "total_credits": new_balance,
                    "monthly_credits_used": credits_response["data"]["monthly_credits_used"] + amount,
                })
                if update_response.status_code not in [200, 204]:
                    return {"success": False, "error": f"Failed to deduct credits: {update_response.text}"}

                # Log transaction
                insert_url = f"{SUPABASE_URL}/rest/v1/credit_transactions"
                insert_response = client.post(insert_url, headers=headers, json={
                    "user_id": user_id,
                    "transaction_type": "search_used",
                    "amount": -amount,
                    "balance_after": new_balance,
                    "reference_id": reference_id,
                    "reference_type": "search",
                    "description": f"Search agent execution (cost: {amount} credit{'s' if amount > 1 else ''})",
                })
                if insert_response.status_code not in [200, 201]:
                    return {"success": False, "error": f"Failed to log transaction: {insert_response.text}"}

            return {"success": True, "new_balance": new_balance, "amount_deducted": amount}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def add_credits(
        user_id: str, amount: int, reason: str, reference_id: str = None, reference_type: str = None
    ) -> Dict[str, Any]:
        """Add credits to user account (for purchases or refunds)."""
        try:
            # Get current balance
            credits_response = CreditsService.get_user_credits(user_id)
            if not credits_response["success"]:
                return {"success": False, "error": "Could not fetch user credits"}

            current_balance = credits_response["data"]["total_credits"]
            new_balance = current_balance + amount

            headers = _make_auth_headers()
            headers["Content-Type"] = "application/json"

            with httpx.Client() as client:
                # Update balance
                update_url = f"{SUPABASE_URL}/rest/v1/user_credits?user_id=eq.{user_id}"
                update_response = client.patch(update_url, headers=headers, json={
                    "total_credits": new_balance,
                    "last_credited_at": datetime.now().isoformat(),
                })
                if update_response.status_code not in [200, 204]:
                    return {"success": False, "error": f"Failed to add credits: {update_response.text}"}

                # Log transaction
                insert_url = f"{SUPABASE_URL}/rest/v1/credit_transactions"
                insert_response = client.post(insert_url, headers=headers, json={
                    "user_id": user_id,
                    "transaction_type": "package_purchased" if amount > 0 else "refund",
                    "amount": amount,
                    "balance_after": new_balance,
                    "reference_id": reference_id,
                    "reference_type": reference_type or "manual",
                    "description": reason,
                })
                if insert_response.status_code not in [200, 201]:
                    return {"success": False, "error": f"Failed to log transaction: {insert_response.text}"}

            return {"success": True, "new_balance": new_balance, "amount_added": amount}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def upgrade_subscription(user_id: str, plan: str, stripe_subscription_id: str = None) -> Dict[str, Any]:
        """Upgrade user to a new subscription plan."""
        try:
            headers = _make_auth_headers()
            headers["Content-Type"] = "application/json"

            with httpx.Client() as client:
                # Get new plan
                plan_url = f"{SUPABASE_URL}/rest/v1/subscription_plans?select=id,monthly_credits&name=eq.{plan}"
                plan_response = client.get(plan_url, headers=headers)
                if plan_response.status_code != 200:
                    return {"success": False, "error": f"Could not fetch subscription plan: {plan_response.text}"}

                plan_data = plan_response.json()
                if not plan_data:
                    return {"success": False, "error": f"Subscription plan '{plan}' not found"}

                plan_id = plan_data[0]["id"]
                monthly_credits = plan_data[0]["monthly_credits"]

                # Update subscription
                sub_url = f"{SUPABASE_URL}/rest/v1/user_subscriptions?user_id=eq.{user_id}"
                sub_response = client.patch(sub_url, headers=headers, json={
                    "plan_id": plan_id,
                    "stripe_subscription_id": stripe_subscription_id,
                    "status": "active",
                    "current_period_start": datetime.now().isoformat(),
                    "current_period_end": (datetime.now() + timedelta(days=30)).isoformat(),
                })
                if sub_response.status_code not in [200, 204]:
                    return {"success": False, "error": f"Failed to update subscription: {sub_response.text}"}

                # Update monthly credits allocation
                next_reset = (datetime.now() + timedelta(days=30)).date()
                credits_url = f"{SUPABASE_URL}/rest/v1/user_credits?user_id=eq.{user_id}"
                credits_response = client.patch(credits_url, headers=headers, json={
                    "total_credits": monthly_credits,
                    "monthly_credits_used": 0,
                    "monthly_reset_date": next_reset.isoformat(),
                })
                if credits_response.status_code not in [200, 204]:
                    return {"success": False, "error": f"Failed to update credits: {credits_response.text}"}

            return {"success": True, "new_plan": plan, "monthly_credits": monthly_credits}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_credit_transactions(user_id: str, limit: int = 50) -> Dict[str, Any]:
        """Get transaction history for a user."""
        try:
            response = (
                supabase.table("credit_transactions")
                .select("transaction_type,amount,balance_after,description,created_at")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return {"success": True, "data": response.data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def create_stripe_customer(user_id: str, stripe_customer_id: str) -> Dict[str, Any]:
        """Create mapping between user and Stripe customer."""
        try:
            response = supabase.table("stripe_customers").insert({
                "user_id": user_id,
                "stripe_customer_id": stripe_customer_id,
            }).execute()
            return {"success": True, "data": response.data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_stripe_customer_id(user_id: str) -> Optional[str]:
        """Get Stripe customer ID for a user."""
        try:
            response = supabase.table("stripe_customers").select("stripe_customer_id").eq("user_id", user_id).single().execute()
            return response.data["stripe_customer_id"] if response.data else None
        except Exception:
            return None

    @staticmethod
    def log_stripe_event(event_id: str, event_type: str, raw_data: Dict, user_id: str = None) -> Dict[str, Any]:
        """Log Stripe webhook event for auditing."""
        try:
            response = supabase.table("stripe_events").insert({
                "event_id": event_id,
                "event_type": event_type,
                "user_id": user_id,
                "raw_data": raw_data,
            }).execute()
            return {"success": True, "data": response.data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def mark_event_processed(event_id: str, error_message: str = None) -> Dict[str, Any]:
        """Mark a Stripe event as processed."""
        try:
            response = supabase.table("stripe_events").update({
                "processed": True,
                "error_message": error_message,
            }).eq("event_id", event_id).execute()
            return {"success": True, "data": response.data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def reset_monthly_credits_if_needed(user_id: str) -> Dict[str, Any]:
        """Reset monthly credits if the reset date has passed."""
        try:
            credits_response = CreditsService.get_user_credits(user_id)
            if not credits_response["success"]:
                return {"success": False, "error": "Could not fetch user credits"}

            credits_data = credits_response["data"]
            reset_date = datetime.fromisoformat(credits_data["monthly_reset_date"]).date()

            # Check if reset date has passed
            if reset_date <= datetime.now().date():
                # Get current subscription
                sub_response = CreditsService.get_user_subscription(user_id)
                if sub_response["success"]:
                    monthly_credits = sub_response["data"]["subscription_plans"]["monthly_credits"]

                    # Reset credits
                    next_reset = (datetime.now() + timedelta(days=30)).date()
                    supabase.table("user_credits").update({
                        "total_credits": monthly_credits,
                        "monthly_credits_used": 0,
                        "monthly_reset_date": next_reset.isoformat(),
                    }).eq("user_id", user_id).execute()

                    # Log the reset
                    supabase.table("credit_transactions").insert({
                        "user_id": user_id,
                        "transaction_type": "monthly_grant",
                        "amount": monthly_credits,
                        "balance_after": monthly_credits,
                        "description": f"Monthly credit reset ({monthly_credits} credits)",
                    }).execute()

                    return {"success": True, "credits_reset": monthly_credits}

            return {"success": True, "credits_reset": False}
        except Exception as e:
            return {"success": False, "error": str(e)}
