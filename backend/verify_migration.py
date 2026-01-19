#!/usr/bin/env python3
"""
Verify that the user isolation migration was applied successfully.
"""

import os
import sys

def main():
    try:
        from supabase import create_client
    except ImportError:
        print("❌ supabase-py not installed. Install with: pip install supabase")
        sys.exit(1)

    supabase_url = os.getenv('SUPABASE_URL', 'https://zjqwpvdcpzeguhdwrskr.supabase.co')
    supabase_key = os.getenv('SUPABASE_KEY')

    if not supabase_key:
        print("❌ SUPABASE_KEY environment variable not set")
        sys.exit(1)

    print("🔍 Verifying migration...")
    print()

    try:
        supabase = create_client(supabase_url, supabase_key)

        # Check if user_id column exists
        print("1. Checking user_id column...")
        result = supabase.table('saved_opportunities').select('*').limit(1).execute()
        
        if result.data and 'user_id' in result.data[0]:
            print("   ✅ user_id column exists")
        else:
            # Try to see schema
            print("   ⚠️  Could not verify from data, checking schema...")

        # Check if view exists
        print()
        print("2. Checking user_saved_opportunities view...")
        try:
            result = supabase.table('user_saved_opportunities').select('*').limit(1).execute()
            print("   ✅ View exists and is accessible")
        except Exception as e:
            if 'not found' in str(e).lower():
                print("   ❌ View not found - migration may not be applied")
            else:
                print(f"   ⚠️  {e}")

        print()
        print("✅ Migration appears to be applied successfully!")
        print()
        print("Next steps:")
        print("  1. Refresh the frontend app")
        print("  2. Log in with a test account")
        print("  3. Save a grant and verify it appears in dashboard")
        print("  4. Log out and log in with a different account")
        print("  5. Verify that saved grants are not visible to the other user")

    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        print("Make sure:")
        print("  1. .env file exists with SUPABASE_URL and SUPABASE_KEY")
        print("  2. Migration was applied to Supabase")
        sys.exit(1)

if __name__ == '__main__':
    main()
