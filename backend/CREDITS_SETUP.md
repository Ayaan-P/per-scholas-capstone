# Credits System Setup Guide

This document explains how to set up and configure the credits system for the PerScholas fundraising platform.

## Overview

The credits system allows users to:
- Receive free monthly credits based on their subscription tier
- Purchase additional credits as needed
- Have credits deducted when running searches via the AI agent

### Pricing Tiers

**Subscription Tiers:**
- **Free**: 5 searches/month (included, no charge)
- **Pro**: 10 searches/month for $10/month (recurring)

**One-Time Credit Packages:**
- 10 credits for $10.00
- 20 credits for $20.00
- 100 credits for $100.00

Each search costs **1 credit**.

## Environment Variables

Add these variables to your `.env` file:

```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_live_...              # Your Stripe secret key
STRIPE_PUBLIC_KEY=pk_live_...              # Your Stripe public key
STRIPE_WEBHOOK_SECRET=whsec_...            # Stripe webhook signing secret

# Stripe Price IDs (set these after creating products in Stripe)
STRIPE_PRICE_PRO=price_...                 # Pro subscription ($10/month)
STRIPE_PRICE_10_CREDITS=price_...          # 10 credits one-time purchase
STRIPE_PRICE_20_CREDITS=price_...          # 20 credits one-time purchase
STRIPE_PRICE_100_CREDITS=price_...         # 100 credits one-time purchase
```

## Setting Up Stripe

### 1. Create Stripe Account
- Go to [stripe.com](https://stripe.com) and create an account
- Navigate to the [API Dashboard](https://dashboard.stripe.com/apikeys)
- Copy your Secret Key and Public Key

### 2. Create Products and Prices

#### Pro Subscription
```
Product Name: Search Agent Pro
Description: 10 searches per month
Price: $10.00 USD per month
Billing Period: Monthly
```

#### Credit Packages
```
Product Name: Search Credits - 10 Pack
Price: $10.00 USD (one-time)

Product Name: Search Credits - 20 Pack
Price: $20.00 USD (one-time)

Product Name: Search Credits - 100 Pack
Price: $100.00 USD (one-time)
```

### 3. Get Stripe Price IDs
After creating products:
1. Go to [Products page](https://dashboard.stripe.com/products)
2. Click each product
3. Copy the Price ID (format: `price_...`)
4. Add to `.env` file

### 4. Set Up Webhook

1. Go to [Webhooks page](https://dashboard.stripe.com/webhooks)
2. Add endpoint:
   - **URL**: `https://your-api-domain.com/api/credits/webhook/stripe`
   - **Events to listen for**:
     - `payment_intent.succeeded`
     - `customer.subscription.updated`
     - `customer.subscription.deleted`
     - `charge.refunded`

3. After creating, copy the Signing Secret and add to `.env`:
   ```
   STRIPE_WEBHOOK_SECRET=whsec_...
   ```

## Database Setup

Run the migration to create the credits tables:

```bash
# Using Supabase CLI
supabase db push

# Or manually run in Supabase SQL editor:
psql -U postgres -h localhost < /path/to/backend/supabase/migrations/create_credits_system.sql
```

This creates tables:
- `subscription_plans` - Available subscription tiers
- `credit_packages` - One-time purchase options
- `stripe_customers` - User-Stripe mappings
- `user_subscriptions` - User subscription status
- `user_credits` - Credit balances
- `credit_transactions` - Audit log of all credit movements
- `stripe_events` - Webhook event log

## API Endpoints

### Get Credit Balance
```
GET /api/credits/balance
Authorization: Bearer {token}
```

Response:
```json
{
  "user_id": "user-uuid",
  "total_credits": 5,
  "monthly_credits_used": 2,
  "monthly_reset_date": "2025-02-18"
}
```

### Get Subscription Info
```
GET /api/credits/subscription
Authorization: Bearer {token}
```

Response:
```json
{
  "plan_name": "free",
  "monthly_credits": 5,
  "status": "active",
  "current_period_end": "2025-02-18T00:00:00Z"
}
```

### Get Available Packages
```
GET /api/credits/packages
```

Response:
```json
{
  "packages": [
    {
      "id": "10_credits",
      "name": "10 Credits",
      "credits": 10,
      "price_usd": 10.00,
      "description": "10 credits for $10.00"
    },
    ...
  ]
}
```

### Create Credit Purchase Checkout
```
POST /api/credits/purchase/checkout
Authorization: Bearer {token}
Content-Type: application/json

{
  "package_id": "10_credits",
  "success_url": "https://your-app.com/payment-success",
  "cancel_url": "https://your-app.com/payment-cancelled"
}
```

Response:
```json
{
  "session_id": "cs_...",
  "checkout_url": "https://checkout.stripe.com/pay/cs_..."
}
```

### Create Subscription Upgrade Checkout
```
POST /api/credits/subscription/upgrade
Authorization: Bearer {token}
Content-Type: application/json

{
  "plan": "pro",
  "success_url": "https://your-app.com/upgrade-success",
  "cancel_url": "https://your-app.com/upgrade-cancelled"
}
```

### Get Transaction History
```
GET /api/credits/transactions?limit=50
Authorization: Bearer {token}
```

Response:
```json
{
  "transactions": [
    {
      "id": "txn-uuid",
      "transaction_type": "search_used",
      "amount": -1,
      "balance_after": 4,
      "description": "Search agent execution (cost: 1 credit)",
      "created_at": "2025-01-18T10:30:00Z"
    },
    ...
  ],
  "count": 10
}
```

## Search Endpoint Credit Integration

The `/api/search-opportunities` endpoint now:

1. Checks if user's monthly credits need resetting
2. Deducts 1 credit before starting search
3. Returns `402 Payment Required` if insufficient credits
4. Includes credit info in response:

```json
{
  "job_id": "job-uuid",
  "status": "started",
  "credits_used": 1,
  "new_balance": 4
}
```

## Webhook Event Handling

The system automatically handles these Stripe events:

### `payment_intent.succeeded`
- Fires when one-time credit purchase completes
- Adds credits to user account
- Logs transaction

### `customer.subscription.updated`
- Fires when subscription is activated or changed
- Updates user's subscription plan
- Resets monthly credit allocation

### `customer.subscription.deleted`
- Fires when subscription is canceled
- Downgrades user to free tier
- Resets monthly credits to free tier amount

### `charge.refunded`
- Fires when a charge is refunded
- Returns credits to user account
- Logs refund transaction

## Testing

### Test with Stripe CLI
```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe

# Listen for events
stripe listen --forward-to localhost:8000/api/credits/webhook/stripe

# Trigger test events
stripe trigger payment_intent.succeeded
stripe trigger customer.subscription.updated
```

### Test Credit Deduction
```bash
# Trigger a search (should deduct 1 credit)
curl -X POST http://localhost:8000/api/search-opportunities \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Find workforce development grants"
  }'

# Check balance (should decrease by 1)
curl http://localhost:8000/api/credits/balance \
  -H "Authorization: Bearer {token}"
```

## Monthly Credit Reset

Credits automatically reset on the user's monthly reset date. This happens:
- When user checks balance
- When user attempts a search
- At the `monthly_reset_date` timestamp

The reset is idempotent - it only happens once per month.

## Error Handling

### Insufficient Credits
Status: `402 Payment Required`
```json
{
  "detail": "Insufficient credits. Required: 1, Available: 0. Please purchase more credits"
}
```

### Invalid Package
Status: `400 Bad Request`
```json
{
  "detail": "Invalid package: invalid_package_id"
}
```

### Stripe Error
Status: `500 Internal Server Error`
```json
{
  "detail": "Error creating checkout session: ..."
}
```

## Troubleshooting

### Webhook not processing
1. Check webhook signing secret is correct
2. Verify webhook endpoint URL is accessible
3. Check Stripe dashboard webhook delivery logs
4. Look for errors in `stripe_events` table

### Credits not deducting
1. Verify user has active subscription/credits
2. Check `credit_transactions` table for logs
3. Ensure monthly reset date is in future

### Stripe customer not found
1. Verify user completed a transaction
2. Check `stripe_customers` table mapping
3. May need to recreate customer record

## Database Query Examples

### Check user's credit balance
```sql
SELECT * FROM user_credits WHERE user_id = 'user-uuid';
```

### View transaction history
```sql
SELECT * FROM credit_transactions
WHERE user_id = 'user-uuid'
ORDER BY created_at DESC;
```

### Find failed webhook events
```sql
SELECT * FROM stripe_events
WHERE processed = false OR error_message IS NOT NULL;
```

### Check subscription status
```sql
SELECT
  u.user_id,
  sp.name as plan,
  u.status,
  u.current_period_end
FROM user_subscriptions u
JOIN subscription_plans sp ON u.plan_id = sp.id;
```

## Production Considerations

1. **Use Stripe Live Keys** - Switch from test to live keys for production
2. **HTTPS Required** - Webhook endpoint must be HTTPS
3. **Rate Limiting** - Consider adding rate limits on credit purchases
4. **Monitoring** - Set up alerts for failed transactions
5. **Backup** - Regularly backup `credit_transactions` table
6. **PCI Compliance** - Use Stripe for all card handling (never store card data)
7. **Idempotency** - Stripe webhook events can be retried; ensure operations are idempotent

## Support

For issues or questions:
1. Check Stripe dashboard for event delivery status
2. Review logs in `stripe_events` table
3. Verify `.env` configuration
4. Check Supabase database for data integrity
