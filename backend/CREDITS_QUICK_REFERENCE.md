# Credits System - Quick Reference

## Files Overview

| File | Purpose |
|------|---------|
| `credits_service.py` | Core credit logic (balance, deduction, reset) |
| `stripe_service.py` | Stripe API integration & webhook handling |
| `credits_routes.py` | REST API endpoints for credits |
| `main.py` | Updated to include credits in auth & search |
| `supabase/migrations/create_credits_system.sql` | Database schema |
| `CREDITS_SETUP.md` | Complete setup instructions |
| `CREDITS_IMPLEMENTATION.md` | Technical deep dive |
| `.env.example` | Environment variable template |

## Quick Setup (5 steps)

1. **Run migration:**
   ```bash
   supabase db push
   ```

2. **Update .env with Stripe keys:**
   ```bash
   STRIPE_SECRET_KEY=sk_live_...
   STRIPE_PUBLIC_KEY=pk_live_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   ```

3. **Create Stripe products and get price IDs:**
   - Pro subscription: $10/month → `STRIPE_PRICE_PRO=price_...`
   - 10 credits: $10 → `STRIPE_PRICE_10_CREDITS=price_...`
   - 20 credits: $20 → `STRIPE_PRICE_20_CREDITS=price_...`
   - 100 credits: $100 → `STRIPE_PRICE_100_CREDITS=price_...`

4. **Set up Stripe webhook:**
   - Endpoint: `https://your-domain/api/credits/webhook/stripe`
   - Events: payment_intent.succeeded, customer.subscription.updated, customer.subscription.deleted, charge.refunded

5. **Install stripe in requirements:**
   ```bash
   pip install -r requirements.txt
   ```

## Key Classes

### CreditsService
```python
from credits_service import CreditsService

# Get balance
CreditsService.get_user_credits(user_id)

# Deduct credits (called before search)
CreditsService.check_and_deduct_credits(user_id, amount=1)

# Add credits (called on payment)
CreditsService.add_credits(user_id, amount=10, reason="Package purchased")

# Initialize for new user
CreditsService.initialize_user_credits(user_id, plan="free")
```

### StripeService
```python
from stripe_service import StripeService

# Create checkout for credit purchase
StripeService.create_credit_purchase_session(user_id, email, "10_credits", ...)

# Create checkout for subscription upgrade
StripeService.create_subscription_session(user_id, email, "pro", ...)

# Handle webhook
StripeService.handle_webhook_event(event)
```

## Pricing

| Item | Cost | Monthly |
|------|------|---------|
| Free Plan | Free | 5 searches |
| Pro Plan | $10 | 10 searches |
| 10 Credits | $10 | One-time |
| 20 Credits | $20 | One-time |
| 100 Credits | $100 | One-time |

*Each search costs 1 credit*

## API Quick Reference

### For Frontend

Get balance:
```
GET /api/credits/balance
```

Get subscription:
```
GET /api/credits/subscription
```

Get packages:
```
GET /api/credits/packages
```

Buy credits (returns checkout URL):
```
POST /api/credits/purchase/checkout
{
  "package_id": "10_credits",
  "success_url": "https://app.com/success",
  "cancel_url": "https://app.com/cancel"
}
```

Upgrade subscription:
```
POST /api/credits/subscription/upgrade
{
  "plan": "pro",
  "success_url": "https://app.com/success",
  "cancel_url": "https://app.com/cancel"
}
```

### Search with Credits

Now requires credits:
```
POST /api/search-opportunities
```

Returns:
```json
{
  "job_id": "...",
  "status": "started",
  "credits_used": 1,
  "new_balance": 4
}
```

Insufficient credits returns `402 Payment Required`.

## Database Tables

```
subscription_plans
├─ id, name, monthly_credits, price_cents

credit_packages
├─ id, name, credits, price_cents

user_subscriptions
├─ user_id, plan_id, status, current_period_end

user_credits
├─ user_id, total_credits, monthly_credits_used, monthly_reset_date

credit_transactions (Audit Log)
├─ user_id, transaction_type, amount, balance_after, reference_id, created_at

stripe_customers
├─ user_id, stripe_customer_id

stripe_events (Webhook Log)
├─ event_id, event_type, raw_data, processed
```

## Transaction Types

| Type | Effect | Triggered By |
|------|--------|--------------|
| `monthly_grant` | +N credits | Monthly reset |
| `search_used` | -1 credit | Search execution |
| `package_purchased` | +N credits | Stripe webhook |
| `refund` | +N credits | Stripe webhook |

## Stripe Events Handled

| Event | Action |
|-------|--------|
| `payment_intent.succeeded` | Add one-time credits |
| `customer.subscription.updated` | Update subscription & reset monthly credits |
| `customer.subscription.deleted` | Downgrade to free tier |
| `charge.refunded` | Refund credits to user |

## Testing

### Test Credit Deduction
```bash
curl -X POST http://localhost:8000/api/search-opportunities \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Find grants"}'
```

### Check Balance
```bash
curl http://localhost:8000/api/credits/balance \
  -H "Authorization: Bearer $TOKEN"
```

### Simulate Stripe Event
```bash
stripe listen --forward-to localhost:8000/api/credits/webhook/stripe
stripe trigger payment_intent.succeeded
```

## Common Issues

| Issue | Solution |
|-------|----------|
| 402 error on search | User has 0 credits - purchase more |
| Webhook not received | Check Stripe webhook config & signature secret |
| Credits not added after purchase | Verify price IDs in `.env` match Stripe |
| User doesn't have initial 5 credits | Run migration & reinit user |

## Key Code Locations

- **Search integration**: `main.py` line 886-934
- **Auth initialization**: `main.py` line 600-603
- **Credit routes**: `credits_routes.py` (all endpoints)
- **Credit logic**: `credits_service.py` (all functions)
- **Stripe logic**: `stripe_service.py` (all payment handling)
- **Database schema**: `supabase/migrations/create_credits_system.sql`

## Frontend Integration Checklist

- [ ] Show credit balance on dashboard
- [ ] Display "X searches remaining this month"
- [ ] Show "Insufficient credits" error on search
- [ ] Add "Buy Credits" button with link to `/api/credits/purchase/checkout`
- [ ] Add "Upgrade to Pro" button with link to `/api/credits/subscription/upgrade`
- [ ] Show transaction history from `/api/credits/transactions`
- [ ] Display checkout URL from Stripe (redirect or embed)
- [ ] Handle success/cancel redirects after payment

## Environment Variables Checklist

```bash
# Required for Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLIC_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Required (set price IDs after creating in Stripe)
STRIPE_PRICE_PRO=price_...
STRIPE_PRICE_10_CREDITS=price_...
STRIPE_PRICE_20_CREDITS=price_...
STRIPE_PRICE_100_CREDITS=price_...
```

## Useful SQL Queries

Get user's current balance:
```sql
SELECT total_credits, monthly_credits_used, monthly_reset_date
FROM user_credits
WHERE user_id = 'user-uuid';
```

Get transaction history:
```sql
SELECT * FROM credit_transactions
WHERE user_id = 'user-uuid'
ORDER BY created_at DESC;
```

Check failed webhooks:
```sql
SELECT * FROM stripe_events
WHERE processed = false;
```

Get revenue (in cents):
```sql
SELECT SUM(amount * 100) as revenue_cents
FROM credit_transactions
WHERE transaction_type IN ('package_purchased', 'monthly_grant');
```

## Next Steps

1. Follow `CREDITS_SETUP.md` for complete setup
2. Test with Stripe test keys first
3. Switch to live keys for production
4. Implement frontend UI for credit displays & purchases
5. Monitor webhook delivery in Stripe dashboard
6. Set up alerts for failed transactions
