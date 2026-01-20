"""
Stripe payment integration service for handling credit purchases and subscriptions.
"""

import os
import json
import hmac
import hashlib
from typing import Dict, Any, Optional
from decimal import Decimal

import stripe
from dotenv import load_dotenv

from credits_service import CreditsService

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


class StripeService:
    """Service for handling Stripe payments and subscriptions."""

    # Stripe product/price mapping (will be set up in Stripe dashboard)
    SUBSCRIPTION_PRICES = {
        "pro": os.getenv("STRIPE_PRICE_PRO", "price_pro_placeholder"),
    }

    PACKAGE_PRICES = {
        "10_credits": os.getenv("STRIPE_PRICE_10_CREDITS", "price_10_placeholder"),
        "20_credits": os.getenv("STRIPE_PRICE_20_CREDITS", "price_20_placeholder"),
        "100_credits": os.getenv("STRIPE_PRICE_100_CREDITS", "price_100_placeholder"),
    }

    @staticmethod
    def create_or_get_customer(user_id: str, email: str) -> Optional[str]:
        """Create or retrieve Stripe customer for a user."""
        try:
            # Check if customer already exists
            stripe_customer_id = CreditsService.get_stripe_customer_id(user_id)
            if stripe_customer_id:
                return stripe_customer_id

            # Create new customer
            customer = stripe.Customer.create(
                email=email,
                metadata={"user_id": user_id},
            )

            # Store mapping
            CreditsService.create_stripe_customer(user_id, customer.id)
            return customer.id
        except Exception as e:
            print(f"Error creating Stripe customer: {e}")
            return None

    @staticmethod
    def create_credit_purchase_session(
        user_id: str, email: str, package_id: str, success_url: str, cancel_url: str
    ) -> Dict[str, Any]:
        """Create Stripe checkout session for credit package purchase."""
        try:
            # Validate package
            if package_id not in StripeService.PACKAGE_PRICES:
                return {"success": False, "error": f"Invalid package: {package_id}"}

            # Get or create customer
            stripe_customer_id = StripeService.create_or_get_customer(user_id, email)
            if not stripe_customer_id:
                return {"success": False, "error": "Failed to create Stripe customer"}

            # Get package info
            package_info = CreditsService.CREDIT_PACKAGES.get(package_id)
            price_id = StripeService.PACKAGE_PRICES.get(package_id)

            # Create session
            session = stripe.checkout.Session.create(
                customer=stripe_customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=cancel_url,
                client_reference_id=user_id,
                metadata={
                    "user_id": user_id,
                    "package_id": package_id,
                    "credits": package_info["credits"],
                },
            )

            return {"success": True, "session_id": session.id, "url": session.url}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def create_subscription_session(
        user_id: str, email: str, plan: str, success_url: str, cancel_url: str
    ) -> Dict[str, Any]:
        """Create Stripe checkout session for subscription upgrade."""
        try:
            # Validate plan
            if plan not in StripeService.SUBSCRIPTION_PRICES:
                return {"success": False, "error": f"Invalid subscription plan: {plan}"}

            # Get or create customer
            stripe_customer_id = StripeService.create_or_get_customer(user_id, email)
            if not stripe_customer_id:
                return {"success": False, "error": "Failed to create Stripe customer"}

            price_id = StripeService.SUBSCRIPTION_PRICES.get(plan)

            # Create session
            session = stripe.checkout.Session.create(
                customer=stripe_customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                success_url=f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=cancel_url,
                client_reference_id=user_id,
                metadata={"user_id": user_id, "plan": plan},
            )

            return {"success": True, "session_id": session.id, "url": session.url}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def verify_webhook_signature(payload: bytes, signature: str) -> bool:
        """Verify Stripe webhook signature."""
        try:
            computed_signature = hmac.new(
                STRIPE_WEBHOOK_SECRET.encode(), payload, hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(computed_signature, signature)
        except Exception as e:
            print(f"Error verifying webhook signature: {e}")
            return False

    @staticmethod
    def handle_webhook_event(event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Stripe webhook events."""
        try:
            event_type = event["type"]
            event_data = event["data"]["object"]
            event_id = event["id"]

            # Log event
            user_id = event_data.get("metadata", {}).get("user_id")
            CreditsService.log_stripe_event(event_id, event_type, event, user_id)

            # Handle different event types
            if event_type == "payment_intent.succeeded":
                return StripeService._handle_payment_succeeded(event_data)
            elif event_type == "customer.subscription.updated":
                return StripeService._handle_subscription_updated(event_data)
            elif event_type == "customer.subscription.deleted":
                return StripeService._handle_subscription_canceled(event_data)
            elif event_type == "charge.refunded":
                return StripeService._handle_charge_refunded(event_data)
            else:
                return {"success": True, "message": f"Unhandled event type: {event_type}"}

        except Exception as e:
            error_msg = f"Error handling webhook: {str(e)}"
            print(error_msg)
            return {"success": False, "error": error_msg}

    @staticmethod
    def _handle_payment_succeeded(payment_intent: Dict) -> Dict[str, Any]:
        """Handle successful payment (one-time credit purchase)."""
        try:
            user_id = payment_intent.get("metadata", {}).get("user_id")
            package_id = payment_intent.get("metadata", {}).get("package_id")
            credits = int(payment_intent.get("metadata", {}).get("credits", 0))

            if not user_id or credits == 0:
                return {"success": False, "error": "Invalid payment metadata"}

            # Add credits to user
            result = CreditsService.add_credits(
                user_id,
                credits,
                f"Credit package purchased: {package_id}",
                reference_id=payment_intent["id"],
                reference_type="stripe_charge",
            )

            if result["success"]:
                CreditsService.mark_event_processed(payment_intent.get("id", ""))
                return {"success": True, "message": f"Added {credits} credits to user {user_id}"}
            else:
                return {"success": False, "error": result.get("error")}

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def _handle_subscription_updated(subscription: Dict) -> Dict[str, Any]:
        """Handle subscription update."""
        try:
            user_id = subscription.get("metadata", {}).get("user_id")
            plan = subscription.get("metadata", {}).get("plan")

            if not user_id or not plan:
                return {"success": False, "error": "Invalid subscription metadata"}

            # Update user subscription
            result = CreditsService.upgrade_subscription(
                user_id, plan, stripe_subscription_id=subscription["id"]
            )

            if result["success"]:
                CreditsService.mark_event_processed(subscription.get("id", ""))
                return {"success": True, "message": f"Updated subscription for user {user_id}"}
            else:
                return {"success": False, "error": result.get("error")}

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def _handle_subscription_canceled(subscription: Dict) -> Dict[str, Any]:
        """Handle subscription cancellation."""
        try:
            user_id = subscription.get("metadata", {}).get("user_id")

            if not user_id:
                return {"success": False, "error": "Invalid subscription metadata"}

            # Downgrade to free plan
            result = CreditsService.upgrade_subscription(user_id, "free")

            if result["success"]:
                CreditsService.mark_event_processed(subscription.get("id", ""))
                return {"success": True, "message": f"Downgraded user {user_id} to free plan"}
            else:
                return {"success": False, "error": result.get("error")}

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def _handle_charge_refunded(charge: Dict) -> Dict[str, Any]:
        """Handle refund."""
        try:
            user_id = charge.get("metadata", {}).get("user_id")
            amount_refunded = charge.get("amount_refunded", 0)

            if not user_id or amount_refunded == 0:
                return {"success": False, "error": "Invalid refund metadata"}

            # Calculate credits to refund (assuming $0.01 per credit)
            credits_to_refund = amount_refunded // 100

            # Add credits back
            result = CreditsService.add_credits(
                user_id,
                credits_to_refund,
                f"Refund processed for charge {charge['id']}",
                reference_id=charge["id"],
                reference_type="refund",
            )

            if result["success"]:
                CreditsService.mark_event_processed(charge.get("id", ""))
                return {"success": True, "message": f"Refunded {credits_to_refund} credits to user {user_id}"}
            else:
                return {"success": False, "error": result.get("error")}

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_session_details(session_id: str) -> Dict[str, Any]:
        """Get details of a checkout session."""
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            return {"success": True, "data": session}
        except Exception as e:
            return {"success": False, "error": str(e)}
