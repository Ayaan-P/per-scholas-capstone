-- Credits system for search agent usage
-- Run this migration in Supabase to add credit-based functionality

-- ===== SUBSCRIPTION PLANS =====
CREATE TABLE IF NOT EXISTS subscription_plans (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE, -- 'free', 'pro'
    monthly_credits INTEGER NOT NULL,
    price_cents INTEGER NOT NULL, -- Price in cents (0 for free)
    price_currency TEXT DEFAULT 'usd',
    stripe_price_id TEXT, -- Stripe Price ID for recurring billing
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default subscription plans
INSERT INTO subscription_plans (name, monthly_credits, price_cents, stripe_price_id, description)
VALUES
    ('free', 5, 0, NULL, 'Free tier with 5 searches per month'),
    ('pro', 10, 1000, NULL, 'Pro tier with 10 searches per month ($10/month)')
ON CONFLICT (name) DO NOTHING;

-- ===== CREDIT PACKAGES (One-time purchases) =====
CREATE TABLE IF NOT EXISTS credit_packages (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE, -- '10_credits', '20_credits', '100_credits'
    credits INTEGER NOT NULL,
    price_cents INTEGER NOT NULL, -- Price in cents
    price_currency TEXT DEFAULT 'usd',
    stripe_price_id TEXT, -- Stripe Product ID for one-time purchases
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default credit packages
INSERT INTO credit_packages (name, credits, price_cents, stripe_price_id, description)
VALUES
    ('10_credits', 10, 1000, NULL, '10 credits for $10.00'),
    ('20_credits', 20, 2000, NULL, '20 credits for $20.00'),
    ('100_credits', 100, 10000, NULL, '100 credits for $100.00')
ON CONFLICT (name) DO NOTHING;

-- ===== STRIPE CUSTOMERS =====
CREATE TABLE IF NOT EXISTS stripe_customers (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    stripe_customer_id TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stripe_customers_user_id ON stripe_customers(user_id);
CREATE INDEX IF NOT EXISTS idx_stripe_customers_stripe_id ON stripe_customers(stripe_customer_id);

-- ===== USER SUBSCRIPTIONS =====
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    plan_id INTEGER NOT NULL REFERENCES subscription_plans(id),
    stripe_subscription_id TEXT, -- Stripe subscription ID for Pro tier
    status TEXT DEFAULT 'active', -- 'active', 'canceled', 'past_due'
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    cancel_at_period_end BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_status ON user_subscriptions(status);

-- ===== USER CREDITS =====
CREATE TABLE IF NOT EXISTS user_credits (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    total_credits INTEGER DEFAULT 0, -- Total credits across all sources
    monthly_credits_used INTEGER DEFAULT 0, -- Used in current month
    monthly_reset_date DATE, -- Date when monthly credits reset
    last_credited_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_credits_user_id ON user_credits(user_id);

-- ===== CREDIT TRANSACTIONS (Audit log) =====
CREATE TABLE IF NOT EXISTS credit_transactions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    transaction_type TEXT NOT NULL, -- 'search_used', 'monthly_grant', 'package_purchased', 'refund'
    amount INTEGER NOT NULL, -- Credit amount (negative for deductions)
    balance_after INTEGER NOT NULL, -- Total credits after this transaction
    reference_id TEXT, -- e.g., search_job_id, stripe_charge_id, etc.
    reference_type TEXT, -- e.g., 'search', 'stripe_charge', 'manual'
    description TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id ON credit_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_type ON credit_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_created ON credit_transactions(created_at DESC);

-- ===== STRIPE EVENTS (Webhook logging) =====
CREATE TABLE IF NOT EXISTS stripe_events (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE, -- Stripe event ID
    event_type TEXT NOT NULL, -- 'payment_intent.succeeded', 'customer.subscription.updated', etc.
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    raw_data JSONB NOT NULL,
    processed BOOLEAN DEFAULT false,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stripe_events_event_id ON stripe_events(event_id);
CREATE INDEX IF NOT EXISTS idx_stripe_events_user_id ON stripe_events(user_id);
CREATE INDEX IF NOT EXISTS idx_stripe_events_processed ON stripe_events(processed);
CREATE INDEX IF NOT EXISTS idx_stripe_events_created ON stripe_events(created_at DESC);

-- ===== ROW LEVEL SECURITY =====
ALTER TABLE subscription_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_packages ENABLE ROW LEVEL SECURITY;
ALTER TABLE stripe_customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_credits ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE stripe_events ENABLE ROW LEVEL SECURITY;

-- Public can view subscription plans and packages
CREATE POLICY "Allow public read on subscription_plans"
    ON subscription_plans FOR SELECT USING (true);

CREATE POLICY "Allow public read on credit_packages"
    ON credit_packages FOR SELECT USING (true);

-- Service role policies (backend operations - check role first)
CREATE POLICY "Service role full access to stripe_customers"
    ON stripe_customers FOR ALL USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Service role full access to user_subscriptions"
    ON user_subscriptions FOR ALL USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Service role full access to user_credits"
    ON user_credits FOR ALL USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Service role full access to credit_transactions"
    ON credit_transactions FOR ALL USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Service role full access to stripe_events"
    ON stripe_events FOR ALL USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');

-- User policies (authenticated users - see only their own data)
CREATE POLICY "Users can view own stripe_customers"
    ON stripe_customers FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can view own subscriptions"
    ON user_subscriptions FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can view own credits"
    ON user_credits FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can view own transactions"
    ON credit_transactions FOR SELECT USING (auth.uid() = user_id);

-- ===== COMMENTS =====
COMMENT ON TABLE subscription_plans IS 'Monthly subscription tiers with recurring credit allocation';
COMMENT ON TABLE credit_packages IS 'One-time credit purchase options';
COMMENT ON TABLE stripe_customers IS 'Mapping between users and Stripe customer IDs';
COMMENT ON TABLE user_subscriptions IS 'User subscription status and billing cycle info';
COMMENT ON TABLE user_credits IS 'Current credit balance and usage tracking';
COMMENT ON TABLE credit_transactions IS 'Audit log of all credit movements';
COMMENT ON TABLE stripe_events IS 'Webhook event log for reconciliation';
