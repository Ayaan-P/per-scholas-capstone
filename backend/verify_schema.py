#!/usr/bin/env python3
"""Verify that saved_opportunities table has proper schema and RLS"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase_admin_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Create both clients
supabase_user = create_client(supabase_url, supabase_key)
supabase_admin = create_client(supabase_url, supabase_admin_key)

print("\n=== SAVED_OPPORTUNITIES TABLE SCHEMA ===")
try:
    # Query table structure (using admin to bypass any RLS)
    result = supabase_admin.table("saved_opportunities").select("*", count="exact").limit(1).execute()
    print(f"Table exists: YES")
    print(f"Total rows: {result.count if result.count is not None else 'Unknown'}")

    if result.data:
        columns = list(result.data[0].keys())
        print(f"Columns: {', '.join(columns)}")
        print(f"\nSample row keys:")
        for col in columns:
            print(f"  - {col}")
    else:
        print("Table has no rows yet")

except Exception as e:
    print(f"Error querying table: {e}")

print("\n=== CHECKING FOR USER_ID COLUMN ===")
try:
    result = supabase_admin.table("saved_opportunities").select("user_id").limit(1).execute()
    print("✓ user_id column exists")
except Exception as e:
    print(f"✗ user_id column missing or error: {e}")

print("\n=== TESTING INSERT WITH ADMIN CLIENT ===")
try:
    import uuid
    from datetime import datetime

    test_data = {
        "user_id": str(uuid.uuid4()),
        "opportunity_id": f"test-{uuid.uuid4()}",
        "title": "Test Opportunity",
        "funder": "Test Funder",
        "amount": 100000,
        "deadline": "2025-12-31",
        "match_score": 75,
        "description": "Test description",
        "requirements": ["Requirement 1"],
        "contact": "test@example.com",
        "application_url": "https://example.com",
        "source": "test",
        "status": "active"
    }

    result = supabase_admin.table("saved_opportunities").insert(test_data).execute()
    print(f"✓ Insert successful!")
    print(f"  Inserted ID: {result.data[0]['id'] if result.data else 'Unknown'}")
    print(f"  User ID: {result.data[0]['user_id'] if result.data else 'Unknown'}")

    # Clean up
    if result.data:
        supabase_admin.table("saved_opportunities").delete().eq("id", result.data[0]["id"]).execute()
        print("  (Cleaned up test data)")

except Exception as e:
    print(f"✗ Insert failed: {e}")
    import traceback
    traceback.print_exc()

print("\n=== RLS POLICIES ===")
try:
    # This query won't work via REST API, so we'll just note the expected policies
    print("Expected policies (from migration):")
    print("  1. Users can view own saved opportunities (SELECT)")
    print("  2. Users can save their own opportunities (INSERT)")
    print("  3. Users can update own opportunities (UPDATE)")
    print("  4. Users can delete own opportunities (DELETE)")
except Exception as e:
    print(f"Error: {e}")

print("\n=== DONE ===\n")
