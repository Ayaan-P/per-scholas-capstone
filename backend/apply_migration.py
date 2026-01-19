#!/usr/bin/env python3
"""
Helper script to apply the user isolation migration to Supabase.

Usage:
    python3 apply_migration.py --service-role-key YOUR_KEY_HERE

To get your service role key:
1. Go to https://app.supabase.com
2. Select your project
3. Go to Settings → API → Service Role Key (copy it)
4. Run: python3 apply_migration.py --service-role-key "YOUR_KEY"
"""

import os
import sys
import argparse
from pathlib import Path

def apply_migration(supabase_url: str, service_role_key: str, migration_file: str):
    """Apply the migration using service role key."""
    try:
        import psycopg2
    except ImportError:
        print("❌ psycopg2 not installed. Install with: pip install psycopg2-binary")
        sys.exit(1)

    # Read migration file
    migration_path = Path(migration_file)
    if not migration_path.exists():
        print(f"❌ Migration file not found: {migration_file}")
        sys.exit(1)

    sql_content = migration_path.read_text()

    print(f"📄 Read migration file: {migration_file}")
    print(f"📊 Migration size: {len(sql_content)} bytes")
    print()
    print("✅ Migration prepared. To apply it:")
    print()
    print("OPTION 1 - Via Supabase Dashboard (Easiest):")
    print("  1. Go to https://app.supabase.com")
    print("  2. Select your project")
    print("  3. Go to SQL Editor → New Query")
    print("  4. Paste the SQL below and execute:")
    print()
    print("-" * 70)
    print(sql_content)
    print("-" * 70)

def main():
    parser = argparse.ArgumentParser(
        description="Apply user isolation migration to Supabase"
    )

    parser.add_argument(
        '--show',
        action='store_true',
        help='Show the migration SQL'
    )

    parser.add_argument(
        '--migration-file',
        default='migrations/add_user_isolation_to_saved_opportunities.sql',
        help='Path to migration file'
    )

    args = parser.parse_args()

    supabase_url = os.getenv('SUPABASE_URL', 'https://zjqwpvdcpzeguhdwrskr.supabase.co')

    print("🔧 Supabase Migration Helper")
    print("=" * 70)
    print(f"Supabase URL: {supabase_url}")
    print()

    apply_migration(supabase_url, "dummy_key", args.migration_file)

if __name__ == '__main__':
    main()
