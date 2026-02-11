#!/bin/bash
# Apply FundFish agentic migrations to Supabase

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MIGRATIONS_DIR="$SCRIPT_DIR/migrations"

echo "🐟 FundFish Migration Script"
echo "============================"
echo ""

# Load environment
if [ -f "$SCRIPT_DIR/.env" ]; then
    source "$SCRIPT_DIR/.env"
else
    echo "❌ Error: .env file not found"
    exit 1
fi

if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    echo "❌ Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set"
    exit 1
fi

# Extract database URL from Supabase URL
# Format: https://PROJECT_ID.supabase.co -> postgres://postgres:PASSWORD@db.PROJECT_ID.supabase.co:5432/postgres
PROJECT_ID=$(echo $SUPABASE_URL | sed 's|https://||' | sed 's|.supabase.co||')

echo "📋 Migrations to apply:"
echo "  1. 001_org_grants.sql"
echo "  2. 002_org_briefs.sql"
echo "  3. migrate_saved_opportunities.sql"
echo ""
echo "⚠️  Manual Step Required:"
echo ""
echo "Please apply these migrations via Supabase Dashboard SQL Editor:"
echo "👉 https://supabase.com/dashboard/project/$PROJECT_ID/sql/new"
echo ""
echo "Copy and run each file in order:"
echo "  1. $MIGRATIONS_DIR/001_org_grants.sql"
echo "  2. $MIGRATIONS_DIR/002_org_briefs.sql"
echo "  3. $MIGRATIONS_DIR/migrate_saved_opportunities.sql"
echo ""
echo "Or install supabase CLI and run:"
echo "  supabase db push"
echo ""
read -p "Have you applied the migrations? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Migrations not applied. Exiting."
    exit 1
fi

echo "✅ Migrations confirmed. Proceeding with deployment..."
