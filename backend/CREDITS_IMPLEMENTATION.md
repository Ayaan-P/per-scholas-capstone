# Credits System Implementation Summary

## What Was Implemented

A complete credits system for the PerScholas fundraising platform that allows users to:
- Receive free monthly credits
- Purchase additional credits via Stripe
- Upgrade to a paid subscription tier
- Have credits deducted when running searches

## Files Created

### 1. **supabase/migrations/create_credits_system.sql**
   - Database schema with 7 new tables
   - Includes Row Level Security (RLS) policies
   - Auto-incremented pricing data

### 2. **credits_service.py**
   - Core credits management logic
   - Credit balance tracking
   - Transaction logging
   - Monthly reset handling
   - Stripe customer mapping

### 3. **stripe_service.py**
   - Stripe integration for payments
   - Checkout session creation
   - Webhook event handling
   - Signature verification
   - Automatic credit allocation on payment

### 4. **credits_routes.py**
   - RESTful API endpoints for credits management
   - Public endpoints (balance, subscription, packages)
   - Payment checkout endpoints
   - Stripe webhook receiver
   - Internal endpoints for backend operations

### 5. **main.py Updates**
   - Import credits services
   - Include credits router
   - Credit checking in auth initialization
   - Credit deduction in search endpoint
   - Monthly credit reset check before searches

### 6. **requirements.txt Update**
   - Added `stripe==7.4.0`

### 7. **Documentation**
   - `CREDITS_SETUP.md` - Complete setup guide
   - `.env.example` - Environment variable template
   - This file - Implementation overview

## Architecture

```
User (Frontend)
    ↓
FastAPI Routes (credits_routes.py)
    ↓
┌─────────────────────────────────────┐
│ CreditsService                      │
│ - Balance tracking                  │
│ - Credit deduction                  │
│ - Monthly reset                     │
│ - Subscription management           │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ StripeService                       │
│ - Checkout sessions                 │
│ - Webhook handling                  │
│ - Signature verification            │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Supabase Database                   │
│ - user_credits                      │
│ - credit_transactions               │
│ - user_subscriptions                │
│ - stripe_customers                  │
│ - stripe_events                     │
└─────────────────────────────────────┘
    ↓
Stripe API
```

## Pricing Model

### Subscription Tiers (Monthly Recurring)
- **Free**: 5 searches/month (default for new users)
- **Pro**: 10 searches/month for $10/month

### One-Time Credit Packages
- **10 credits**: $10.00
- **20 credits**: $20.00
- **100 credits**: $100.00

### Cost Per Search
- 1 credit per search execution

## Database Schema

### user_credits
```
- id (UUID, PK)
- user_id (UUID, FK → auth.users)
- total_credits (INTEGER) - Current balance
- monthly_credits_used (INTEGER) - Used in current cycle
- monthly_reset_date (DATE) - When monthly credits reset
```

### credit_transactions (Audit Log)
```
- id (UUID, PK)
- user_id (UUID, FK)
- transaction_type (TEXT) - 'search_used', 'monthly_grant', 'package_purchased', 'refund'
- amount (INTEGER) - Positive or negative
- balance_after (INTEGER) - Total after this transaction
- reference_id (TEXT) - Link to job/charge/etc
- reference_type (TEXT) - 'search', 'stripe_charge', 'manual'
- description (TEXT)
- created_at (TIMESTAMP)
```

### user_subscriptions
```
- id (UUID, PK)
- user_id (UUID, FK)
- plan_id (INTEGER, FK → subscription_plans)
- stripe_subscription_id (TEXT) - For recurring subscriptions
- status (TEXT) - 'active', 'canceled', 'past_due'
- current_period_start/end (TIMESTAMP)
- cancel_at_period_end (BOOLEAN)
```

### stripe_customers
```
- id (UUID, PK)
- user_id (UUID, FK)
- stripe_customer_id (TEXT) - Stripe ID
```

### stripe_events (Webhook Log)
```
- id (UUID, PK)
- event_id (TEXT) - Stripe event ID
- event_type (TEXT) - Type of event
- user_id (UUID, FK)
- raw_data (JSONB) - Full event payload
- processed (BOOLEAN)
- error_message (TEXT)
```

## API Endpoints

### Public Endpoints (Require Authentication)

#### `GET /api/credits/balance`
Returns current credit balance and monthly usage.

#### `GET /api/credits/subscription`
Returns user's current subscription plan and status.

#### `GET /api/credits/packages`
Returns available credit packages for purchase.

#### `POST /api/credits/purchase/checkout`
Creates Stripe checkout session for one-time credit purchase.

#### `POST /api/credits/subscription/upgrade`
Creates Stripe checkout session for subscription upgrade.

#### `GET /api/credits/transactions`
Returns transaction history (audit log).

### Internal Endpoints (Backend Use)

#### `POST /api/credits/internal/deduct`
Deducts credits before search execution (called by `/api/search-opportunities`).

#### `GET /api/credits/internal/balance/{user_id}`
Gets current balance (used by backend operations).

### Webhook Endpoints

#### `POST /api/credits/webhook/stripe`
Receives Stripe webhook events for:
- `payment_intent.succeeded` - One-time purchases
- `customer.subscription.updated` - Subscription changes
- `customer.subscription.deleted` - Subscription cancellation
- `charge.refunded` - Refunds

## Integration with Search Endpoint

When user calls `POST /api/search-opportunities`:

```
1. Reset monthly credits if needed
   ↓
2. Check if user has ≥1 credit
   ↓
3a. If insufficient: Return 402 Payment Required
   ↓
3b. If sufficient:
   - Deduct 1 credit
   - Log transaction
   - Start search job
   - Return new balance
```

## New User Onboarding Flow

1. User signs up via Supabase Auth
2. Frontend calls `POST /api/auth/initialize`
3. Backend creates:
   - User record
   - Organization config
   - **Credits account (Free plan, 5 credits/month)**
4. User sees "5 free searches this month"

## Credit Purchase Flow

1. User clicks "Buy Credits" → Selects package
2. Frontend calls `POST /api/credits/purchase/checkout`
3. Backend:
   - Gets/creates Stripe customer
   - Creates checkout session
   - Returns checkout URL
4. User redirected to Stripe checkout
5. User completes payment
6. Stripe fires `payment_intent.succeeded` webhook
7. Backend:
   - Receives webhook
   - Verifies signature
   - Adds credits to account
   - Logs transaction
8. User redirected to success page with updated balance

## Subscription Upgrade Flow

1. User clicks "Upgrade to Pro"
2. Frontend calls `POST /api/credits/subscription/upgrade`
3. Backend creates subscription checkout session
4. User completes payment
5. Stripe fires `customer.subscription.updated` webhook
6. Backend:
   - Updates subscription plan
   - Resets monthly credits to 10
   - Logs transaction
7. User now has 10 credits/month

## Testing Checklist

### Database
- [ ] Run migration: `supabase db push`
- [ ] Verify tables exist: Check Supabase dashboard
- [ ] Check RLS policies are enabled

### Environment Setup
- [ ] Set Stripe API keys in `.env`
- [ ] Create test products/prices in Stripe
- [ ] Add price IDs to `.env`
- [ ] Get webhook secret and add to `.env`

### API Endpoints
- [ ] Test `GET /api/credits/balance` (should return 5 for new user)
- [ ] Test `GET /api/credits/packages` (should list 3 packages)
- [ ] Test `POST /api/credits/purchase/checkout` (should return checkout URL)
- [ ] Test `GET /api/credits/transactions` (should return empty initially)

### Stripe Integration
- [ ] Set up webhook in Stripe dashboard
- [ ] Test with Stripe CLI: `stripe listen --forward-to localhost:8000/api/credits/webhook/stripe`
- [ ] Trigger test event: `stripe trigger payment_intent.succeeded`
- [ ] Verify webhook received and processed

### Credit Deduction
- [ ] Call `POST /api/search-opportunities` with sufficient credits
- [ ] Verify 1 credit deducted from balance
- [ ] Check transaction log shows "search_used"
- [ ] Verify response includes new balance
- [ ] Try search with 0 credits (should return 402)

### Subscription
- [ ] Upgrade to Pro plan via Stripe checkout
- [ ] Verify subscription marked as "active"
- [ ] Verify monthly_credits reset to 10
- [ ] Verify current_period_end set to 30 days from now
- [ ] Cancel subscription (should downgrade to free)

## Key Features

### 1. Automatic Monthly Reset
- Happens transparently when user:
  - Checks balance
  - Attempts search
  - Subscription period ends
- Only happens once per month (idempotent)

### 2. Comprehensive Audit Log
- Every credit movement logged
- Includes: type, amount, balance, reference, timestamp
- Used for billing reconciliation

### 3. Stripe Webhook Resilience
- Webhook events logged even if processing fails
- Failed events can be manually retried
- Event ID used to prevent duplicates

### 4. RLS Security
- Users can only view own credit data
- Service role for backend operations
- Public read access to plans/packages

### 5. Flexible Credit System
- Can be adjusted to any cost per search
- Can add new subscription tiers
- Can add new credit packages
- Can support promotional credits

## Future Enhancements

1. **Promotional Credits**
   - Referral bonuses
   - Launch promotions
   - Seasonal offers

2. **Admin Dashboard**
   - View user credit status
   - Manual credit grants
   - Refund processing
   - Revenue reporting

3. **Usage Analytics**
   - Track search patterns
   - Identify heavy users
   - Optimize pricing

4. **Automated Dunning**
   - Retry failed payments
   - Subscription management
   - Churn prevention

5. **Different Pricing Tiers**
   - Enterprise tier
   - Custom pricing
   - Volume discounts

## Troubleshooting

### Credits not deducting from search
1. Check user has active subscription
2. Verify `monthly_reset_date` hasn't passed
3. Look for errors in `stripe_events` table
4. Check server logs for exceptions

### Webhook not processing
1. Verify webhook URL is accessible
2. Check Stripe signing secret matches `.env`
3. Review Stripe dashboard webhook delivery logs
4. Check `stripe_events` table for failed events

### Stripe checkout not working
1. Verify price IDs in `.env` exist in Stripe
2. Check Stripe account is in correct mode (live vs test)
3. Verify webhook endpoint configured in Stripe

### User doesn't have initial credits
1. Check migration was run
2. Verify auth initialization called `CreditsService.initialize_user_credits()`
3. Check `user_credits` table for missing records

## Performance Considerations

- Credit checks are database queries - add caching if needed
- Webhook processing is asynchronous - safe for high volume
- Monthly reset is idempotent - can be called frequently
- Consider indexing on `user_id` in frequently queried tables

## Security Notes

- Never log sensitive Stripe data (card numbers)
- Use Stripe for all payment processing
- Verify webhook signatures on every event
- Stripe customer data is PII - handle carefully
- Webhook secret must be protected (keep in `.env`)

## Support

For questions or issues:
1. See `CREDITS_SETUP.md` for setup instructions
2. Check Stripe logs for payment issues
3. Review database schema in migration file
4. Check application logs for errors
