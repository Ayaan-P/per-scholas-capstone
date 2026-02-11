-- Emergency fix: Drop the auto-create trigger that's causing 500 errors on signup

-- Drop the trigger
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Drop the function
DROP FUNCTION IF EXISTS public.handle_new_user();

-- Note: We're reverting to the defensive backend approach where
-- GET /api/organization/config auto-creates missing org profiles
