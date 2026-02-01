"""
Credits system API routes for managing credit purchases, subscriptions, and usage.
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Header
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json

from auth_service import get_current_user, get_current_user_email
from credits_service import CreditsService
from stripe_service import StripeService

router = APIRouter(prefix="/api/credits", tags=["credits"])


# ===== PYDANTIC MODELS =====
class CreditBalanceResponse(BaseModel):
    user_id: str
    total_credits: int
    monthly_credits_used: int
    monthly_reset_date: str


class SubscriptionInfoResponse(BaseModel):
    plan_name: str
    monthly_credits: int
    status: str
    current_period_end: str


class CreditPackageInfo(BaseModel):
    id: str
    name: str
    credits: int
    price_usd: float
    description: str


class CreditPurchaseRequest(BaseModel):
    package_id: str  # '10_credits', '20_credits', '100_credits'
    success_url: str  # Where to redirect after successful payment
    cancel_url: str  # Where to redirect if payment canceled


class SubscriptionUpgradeRequest(BaseModel):
    plan: str  # 'pro'
    success_url: str
    cancel_url: str


class TransactionRecord(BaseModel):
    id: str
    transaction_type: str
    amount: int
    balance_after: int
    description: str
    created_at: str


# ===== ENDPOINTS =====

@router.get("/balance", response_model=CreditBalanceResponse)
async def get_credit_balance(user_id: str = Depends(get_current_user)):
    """Get user's current credit balance."""
    try:
        result = CreditsService.get_user_credits(user_id)
        if not result["success"]:
            # Auto-initialize credits for new users or users without credits
            init_result = CreditsService.initialize_user_credits(user_id, plan="free")
            if not init_result["success"]:
                raise HTTPException(status_code=500, detail=f"Failed to initialize credits: {init_result.get('error')}")
            result = CreditsService.get_user_credits(user_id)
            if not result["success"]:
                raise HTTPException(status_code=500, detail="Credits could not be initialized")

        data = result["data"]
        return CreditBalanceResponse(
            user_id=user_id,
            total_credits=data["total_credits"],
            monthly_credits_used=data["monthly_credits_used"],
            monthly_reset_date=data["monthly_reset_date"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching balance: {str(e)}")


@router.get("/subscription", response_model=SubscriptionInfoResponse)
async def get_subscription_info(user_id: str = Depends(get_current_user)):
    """Get user's current subscription plan."""
    try:
        result = CreditsService.get_user_subscription(user_id)
        if not result["success"]:
            # Auto-initialize subscription for new users
            init_result = CreditsService.initialize_user_credits(user_id, plan="free")
            if not init_result["success"]:
                raise HTTPException(status_code=500, detail=f"Failed to initialize subscription: {init_result.get('error')}")
            result = CreditsService.get_user_subscription(user_id)
            if not result["success"]:
                raise HTTPException(status_code=500, detail="Subscription could not be initialized")

        data = result["data"]
        return SubscriptionInfoResponse(
            plan_name=data["subscription_plans"]["name"],
            monthly_credits=data["subscription_plans"]["monthly_credits"],
            status=data["status"],
            current_period_end=data["current_period_end"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching subscription: {str(e)}")


@router.get("/packages")
async def get_credit_packages() -> Dict[str, Any]:
    """Get available credit packages for purchase."""
    packages = []
    for package_id, info in CreditsService.CREDIT_PACKAGES.items():
        packages.append({
            "id": package_id,
            "name": package_id.replace("_", " ").title(),
            "credits": info["credits"],
            "price_usd": info["price_cents"] / 100,
            "description": f"{info['credits']} credits for ${info['price_cents'] / 100:.2f}",
        })
    return {"packages": packages}


@router.post("/purchase/checkout")
async def create_purchase_checkout(
    request: CreditPurchaseRequest,
    user_id: str = Depends(get_current_user),
    email: str = Depends(get_current_user_email),
):
    """Create Stripe checkout session for credit package purchase."""
    try:
        result = StripeService.create_credit_purchase_session(
            user_id=user_id,
            email=email,
            package_id=request.package_id,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))

        return {
            "session_id": result["session_id"],
            "checkout_url": result["url"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating checkout session: {str(e)}")


@router.post("/subscription/upgrade")
async def create_subscription_upgrade(
    request: SubscriptionUpgradeRequest,
    user_id: str = Depends(get_current_user),
    email: str = Depends(get_current_user_email),
):
    """Create Stripe checkout session for subscription upgrade."""
    try:
        result = StripeService.create_subscription_session(
            user_id=user_id,
            email=email,
            plan=request.plan,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))

        return {
            "session_id": result["session_id"],
            "checkout_url": result["url"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating subscription: {str(e)}")


@router.get("/transactions")
async def get_credit_transactions(
    user_id: str = Depends(get_current_user),
    limit: int = 50,
):
    """Get transaction history for user."""
    try:
        result = CreditsService.get_credit_transactions(user_id, limit)
        if not result["success"]:
            raise HTTPException(status_code=404, detail="Transactions not found")

        return {
            "transactions": result["data"],
            "count": len(result["data"]),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching transactions: {str(e)}")


# ===== STRIPE WEBHOOK =====

@router.post("/webhook/stripe")
async def handle_stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
):
    """Handle Stripe webhook events."""
    try:
        if not stripe_signature:
            raise HTTPException(status_code=400, detail="Missing Stripe signature")

        # Get raw body
        body = await request.body()

        # Verify signature
        if not StripeService.verify_webhook_signature(body, stripe_signature):
            raise HTTPException(status_code=400, detail="Invalid Stripe signature")

        # Parse event
        event = json.loads(body)

        # Handle event
        result = StripeService.handle_webhook_event(event)

        if not result["success"]:
            return {"status": "error", "error": result.get("error")}

        return {"status": "success", "message": result.get("message")}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[STRIPE WEBHOOK] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Webhook processing error: {str(e)}")


# ===== INTERNAL ENDPOINTS (for backend use) =====

@router.post("/internal/deduct")
async def deduct_credits_internal(
    user_id: str,
    amount: int = 1,
    reference_id: str = None,
    request: Request = None,
):
    """
    Internal endpoint to deduct credits from user account.
    Called by search agent before execution.
    Protected: only accepts requests from localhost/internal callers.
    """
    # Security: restrict to internal/localhost callers only
    if request:
        client_host = request.client.host if request.client else None
        if client_host not in ("127.0.0.1", "::1", "localhost", None):
            raise HTTPException(status_code=403, detail="Internal endpoint - access denied")

    try:
        # Check if user has enough credits (with monthly reset if needed)
        CreditsService.reset_monthly_credits_if_needed(user_id)

        result = CreditsService.check_and_deduct_credits(user_id, amount, reference_id)

        if not result["success"]:
            return {
                "success": False,
                "error": result.get("error"),
                "available": result.get("available"),
            }

        return {
            "success": True,
            "new_balance": result["new_balance"],
            "amount_deducted": result["amount_deducted"],
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": f"Error deducting credits: {str(e)}"}


@router.get("/internal/balance/{user_id}")
async def get_balance_internal(user_id: str, request: Request = None):
    """Internal endpoint to get user's credit balance.
    Protected: only accepts requests from localhost/internal callers.
    """
    # Security: restrict to internal/localhost callers only
    if request:
        client_host = request.client.host if request.client else None
        if client_host not in ("127.0.0.1", "::1", "localhost", None):
            raise HTTPException(status_code=403, detail="Internal endpoint - access denied")

    try:
        # Check if monthly reset is needed
        CreditsService.reset_monthly_credits_if_needed(user_id)

        result = CreditsService.get_user_credits(user_id)
        if not result["success"]:
            return {"success": False, "error": "Credits not found"}

        return {
            "success": True,
            "total_credits": result["data"]["total_credits"],
            "monthly_credits_used": result["data"]["monthly_credits_used"],
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}
