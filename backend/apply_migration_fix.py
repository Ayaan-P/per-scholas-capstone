#!/usr/bin/env python3
"""Apply the foreign key fix migration"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase_admin = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

migration_sql = """
ALTER TABLE saved_opportunities
DROP CONSTRAINT IF EXISTS fk_saved_opportunities_user_id;
"""

print("Applying migration to remove FK constraint...")
try:
    result = supabase_admin.postgrest.rpc("execute_sql", {"sql": migration_sql}).execute()
    print(f"✓ Migration applied via RPC (may not work)")
except:
    print("RPC method not available, trying alternative approach...")

# Alternative: Use SQL directly via Supabase
print("\nAttempt 2: Using direct table operations...")
try:
    # We can't directly execute SQL through the REST API
    # So let's at least verify the constraint exists
    result = supabase_admin.table("saved_opportunities").select("*").limit(0).execute()
    print("✓ Table accessible")
    print("Note: You'll need to apply the migration via Supabase dashboard or psql")
    print("SQL to run:")
    print("  " + migration_sql.strip())
except Exception as e:
    print(f"Error: {e}")
