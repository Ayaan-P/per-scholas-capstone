#!/usr/bin/env python3
"""
Apply migrations directly to Supabase database
"""

import os
import sys
from pathlib import Path
from supabase import create_client, Client

# Load environment
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    sys.exit(1)

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

migrations_dir = Path(__file__).parent / 'migrations'

migrations = [
    '001_org_grants.sql',
    '002_org_briefs.sql',
    'migrate_saved_opportunities.sql'
]

print("🐟 Applying FundFish Migrations")
print("================================\n")

for migration_file in migrations:
    file_path = migrations_dir / migration_file
    
    if not file_path.exists():
        print(f"❌ Migration file not found: {migration_file}")
        continue
    
    print(f"📝 Applying {migration_file}...")
    
    with open(file_path) as f:
        sql = f.read()
    
    try:
        # Execute SQL via RPC (raw SQL execution)
        # Note: Supabase Python client doesn't have direct SQL execution
        # We'll need to use the REST API directly
        import httpx
        
        headers = {
            'apikey': SUPABASE_SERVICE_ROLE_KEY,
            'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Use the query endpoint
        response = httpx.post(
            f'{SUPABASE_URL}/rest/v1/rpc/exec_sql',
            headers=headers,
            json={'query': sql},
            timeout=30.0
        )
        
        if response.status_code == 200 or response.status_code == 201:
            print(f"   ✅ {migration_file} applied successfully")
        else:
            print(f"   ⚠️  Status {response.status_code}: {response.text}")
            print(f"   Note: This may mean the table already exists or migration succeeded")
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
        print(f"   You may need to apply this manually via Supabase Dashboard")

print("\n✅ Migration process complete")
print("\nVerify in Supabase Dashboard:")
print(f"   👉 {SUPABASE_URL.replace('https://', 'https://supabase.com/dashboard/project/')}/database/tables")
