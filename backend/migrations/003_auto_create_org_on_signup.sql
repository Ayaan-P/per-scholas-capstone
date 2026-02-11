-- Migration: Auto-create organization and user record on auth signup
-- This replaces the need for frontend to call /api/auth/initialize

-- Function to create org + user record when someone signs up
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
DECLARE
  new_org_id UUID;
BEGIN
  -- Create a default organization for the new user
  INSERT INTO public.organization_config (
    name,
    mission,
    focus_areas,
    impact_metrics,
    programs,
    target_demographics,
    owner_id
  ) VALUES (
    'My Organization',
    'Making an impact',
    ARRAY[]::TEXT[],
    '{}'::JSONB,
    ARRAY[]::TEXT[],
    ARRAY[]::TEXT[],
    NEW.id
  )
  RETURNING id INTO new_org_id;

  -- Create user record linked to the organization
  INSERT INTO public.users (
    id,
    email,
    organization_id,
    role
  ) VALUES (
    NEW.id,
    NEW.email,
    new_org_id,
    'admin'
  );

  -- Initialize credits (free tier - 5 credits/month)
  INSERT INTO public.user_credits (
    user_id,
    total_credits,
    monthly_credits_used,
    monthly_reset_date
  ) VALUES (
    NEW.id,
    5,
    0,
    CURRENT_DATE + INTERVAL '1 month'
  );

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger: Run function after auth.users insert
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();
