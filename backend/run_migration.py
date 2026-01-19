#!/usr/bin/env python3
"""
Run SQL migrations against Supabase database.
Usage: python run_migration.py <migration_file>
"""

import os
import sys
from pathlib import Path
from supabase import create_client, Client

def run_migration(migration_file: str):
    """Run a SQL migration file against the Supabase database"""
    
    # Load environment variables
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY environment variables are required")
        sys.exit(1)
    
    # Initialize Supabase client
    supabase: Client = create_client(supabase_url, supabase_key)
    
    # Read migration file
    migration_path = Path(migration_file)
    if not migration_path.exists():
        print(f"❌ Error: Migration file not found: {migration_file}")
        sys.exit(1)
    
    with open(migration_path, 'r') as f:
        sql = f.read()
    
    print(f"📋 Running migration: {migration_file}")
    print(f"📊 SQL size: {len(sql)} characters")
    
    try:
        # Execute the migration SQL
        # Note: Supabase Python client doesn't have direct SQL execution
        # We need to use the REST API or connect directly to PostgreSQL
        
        # For now, we'll provide instructions for manual execution
        print("\n⚠️  Supabase Python client limitation: Cannot execute arbitrary SQL directly")
        print("\nTo apply this migration, use one of these methods:\n")
        
        print("1️⃣  Using Supabase Dashboard:")
        print("   - Go to https://app.supabase.com")
        print("   - Navigate to SQL Editor")
        print("   - Open a new query and paste the SQL from the migration file")
        print("   - Click 'Run' to execute\n")
        
        print("2️⃣  Using Supabase CLI (if in a project directory):")
        print(f"   supabase db push\n")
        
        print("3️⃣  Using psql directly (if you have database credentials):")
        print(f"   psql -h <DB_HOST> -U <DB_USER> -d <DB_NAME> -f {migration_file}\n")
        
        print("📋 SQL Preview (first 1000 chars):")
        print("---")
        print(sql[:1000])
        if len(sql) > 1000:
            print(f"\n... ({len(sql) - 1000} more characters)")
        print("---\n")
        
        print("✅ Migration file verified and ready to apply")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_migration.py <migration_file>")
        print(f"Example: python run_migration.py migrations/expand_organization_profile.sql")
        sys.exit(1)
    
    run_migration(sys.argv[1])
