#!/usr/bin/env python3
"""
FundFish Agent Provisioning Script

Initializes a workspace for a new organization:
1. Creates workspace directory structure
2. Syncs org profile from database
3. Sets up memory structure
4. Optionally notifies agent bridge

Usage:
    python provision_org_agent.py <org_id>
    python provision_org_agent.py --create-test  # Create test org
    python provision_org_agent.py --list         # List all workspaces
    python provision_org_agent.py --cleanup <org_id>  # Run cleanup on org

Environment:
    SUPABASE_URL - Supabase project URL
    SUPABASE_SERVICE_ROLE_KEY - Service role key for database access
    FUNDFISH_WORKSPACE_ROOT - Workspace root (default: /var/fundfish/workspaces)
    AGENT_BRIDGE_URL - URL of agent bridge on Hetzner (optional)
"""

import os
import sys
import json
import argparse
import httpx
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Note: workspace_service imported lazily after env var setup


def get_supabase_client() -> tuple[str, str]:
    """Get Supabase URL and service role key from environment"""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        # Try loading from .env file
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if "=" in line and not line.startswith("#"):
                        k, v = line.strip().split("=", 1)
                        if k == "SUPABASE_URL":
                            url = v.strip('"').strip("'")
                        elif k == "SUPABASE_SERVICE_ROLE_KEY":
                            key = v.strip('"').strip("'")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    
    return url, key


def fetch_org_config(org_id: str) -> Optional[Dict[str, Any]]:
    """Fetch organization config from Supabase"""
    try:
        supabase_url, supabase_key = get_supabase_client()
    except ValueError as e:
        print(f"⚠️ {e}")
        print("   Skipping database sync, using placeholder data.")
        return None
    
    headers = {
        "Authorization": f"Bearer {supabase_key}",
        "apikey": supabase_key,
    }
    
    url = f"{supabase_url}/rest/v1/organization_config?select=*&id=eq.{org_id}"
    
    try:
        with httpx.Client() as client:
            response = client.get(url, headers=headers)
            
            if response.status_code != 200:
                print(f"⚠️ Failed to fetch org config: {response.status_code}")
                return None
            
            data = response.json()
            if not data:
                print(f"⚠️ No organization found with ID: {org_id}")
                return None
            
            return data[0]
    except Exception as e:
        print(f"⚠️ Error fetching org config: {e}")
        return None


def create_test_org() -> Dict[str, Any]:
    """Create a test organization config"""
    return {
        "id": "test-org-001",
        "name": "Test Nonprofit Organization",
        "mission": "To demonstrate the FundFish agent system with realistic test data. We focus on technology education and workforce development.",
        "ein": "12-3456789",
        "organization_type": "nonprofit",
        "tax_exempt_status": "501(c)(3)",
        "years_established": 5,
        "website_url": "https://test-nonprofit.org",
        "contact_email": "grants@test-nonprofit.org",
        "contact_phone": "(555) 123-4567",
        "focus_areas": [
            "Technology Education",
            "Workforce Development",
            "Digital Literacy",
            "Career Training"
        ],
        "programs": [
            "Tech Skills Bootcamp - 12-week intensive coding program",
            "Digital Literacy for Seniors - Community workshops",
            "Youth STEM Summer Camp - K-12 program"
        ],
        "target_demographics": [
            "Adults seeking career change",
            "Underemployed workers",
            "First-generation college students",
            "Veterans transitioning to civilian careers"
        ],
        "service_regions": [
            "New York Metro Area",
            "New Jersey",
            "Connecticut"
        ],
        "annual_budget": 2500000,
        "staff_size": 25,
        "board_size": 9,
        "grant_writing_capacity": "moderate",
        "matching_fund_capacity": 20,
        "preferred_grant_size_min": 25000,
        "preferred_grant_size_max": 500000,
        "funding_priorities": [
            "Workforce development",
            "Technology training",
            "Career readiness"
        ],
        "impact_metrics": {
            "graduates_annually": 500,
            "job_placement_rate": "85%",
            "average_salary_increase": "45%",
            "employer_partnerships": 75
        },
        "previous_grants": [
            "DOL H-1B TechHire Grant - $2M (2023)",
            "State Workforce Innovation Grant - $500K (2022)",
            "Local Foundation Career Pathways - $150K (2024)"
        ],
        "key_partnerships": [
            "Local Community College",
            "State Workforce Development Board",
            "Tech Industry Consortium"
        ],
        "accreditations": [
            "WIOA Eligible Training Provider",
            "Better Business Bureau Accredited",
            "State Certified Training Organization"
        ]
    }


def provision_workspace(org_id: str, org_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Provision a workspace for an organization.
    
    Args:
        org_id: Organization ID
        org_config: Optional org config (will fetch from DB if not provided)
    
    Returns:
        Dict with provisioning results
    """
    from workspace_service import get_workspace_service
    ws = get_workspace_service()
    
    result = {
        "org_id": org_id,
        "timestamp": datetime.now().isoformat(),
        "steps": []
    }
    
    # Step 1: Initialize workspace structure
    print(f"\n📁 Initializing workspace for {org_id}...")
    init_result = ws.init_workspace(org_id)
    result["steps"].append({
        "name": "init_workspace",
        "success": True,
        "path": init_result["path"]
    })
    print(f"   ✓ Created at: {init_result['path']}")
    
    # Step 2: Fetch org config if not provided
    if org_config is None:
        print(f"\n🔍 Fetching organization config from database...")
        org_config = fetch_org_config(org_id)
        
        if org_config:
            result["steps"].append({
                "name": "fetch_config",
                "success": True,
                "org_name": org_config.get("name")
            })
            print(f"   ✓ Found: {org_config.get('name')}")
        else:
            result["steps"].append({
                "name": "fetch_config",
                "success": False,
                "error": "Config not found"
            })
            print("   ⚠️ Not found - using default profile template")
    
    # Step 3: Sync profile if we have config
    if org_config:
        print(f"\n📝 Syncing profile to workspace...")
        ws.sync_profile_from_db(org_id, org_config)
        result["steps"].append({
            "name": "sync_profile",
            "success": True
        })
        print("   ✓ Profile synced")
    
    # Step 4: Create initial memory entry
    print(f"\n🧠 Creating initial memory entry...")
    ws.log_memory(
        org_id,
        f"Workspace provisioned for organization: {org_config.get('name', org_id) if org_config else org_id}",
        "action"
    )
    result["steps"].append({
        "name": "init_memory",
        "success": True
    })
    print("   ✓ Memory initialized")
    
    # Step 5: Log initial decision
    print(f"\n✅ Recording initial decision log...")
    ws.update_decisions(
        org_id,
        "Workspace initialized - agent ready for grant discovery and matching"
    )
    result["steps"].append({
        "name": "init_decisions",
        "success": True
    })
    print("   ✓ Decisions log created")
    
    # Summary
    result["success"] = all(step.get("success", False) for step in result["steps"])
    
    print(f"\n{'='*50}")
    print(f"✓ Provisioning complete for: {org_id}")
    print(f"  Workspace: {init_result['path']}")
    if org_config:
        print(f"  Org name: {org_config.get('name')}")
    print(f"{'='*50}\n")
    
    return result


def list_workspaces():
    """List all provisioned workspaces"""
    from workspace_service import get_workspace_service
    ws = get_workspace_service()
    
    print(f"\n📂 Workspaces in: {ws.root}")
    print("="*50)
    
    if not ws.root.exists():
        print("(No workspaces yet)")
        return
    
    count = 0
    for org_dir in sorted(ws.root.iterdir()):
        if org_dir.is_dir():
            profile_path = org_dir / "PROFILE.md"
            has_profile = profile_path.exists()
            
            # Try to get org name from profile
            org_name = org_dir.name
            if has_profile:
                try:
                    content = profile_path.read_text()
                    for line in content.split("\n"):
                        if line.startswith("- **Name:**"):
                            org_name = line.split(":", 1)[1].strip()
                            break
                except:
                    pass
            
            # Get session count
            sessions_dir = org_dir / "memory" / "sessions"
            session_count = len(list(sessions_dir.glob("*.md"))) if sessions_dir.exists() else 0
            
            # Get memory file count
            memory_files = len([f for f in (org_dir / "memory").glob("*.md") if len(f.stem) == 10]) if (org_dir / "memory").exists() else 0
            
            print(f"\n  {org_dir.name}")
            print(f"    Name: {org_name}")
            print(f"    Sessions: {session_count} | Memory files: {memory_files}")
            print(f"    Profile: {'✓' if has_profile else '✗'}")
            
            count += 1
    
    print(f"\n{'='*50}")
    print(f"Total: {count} workspaces")


def run_cleanup(org_id: str):
    """Run cleanup on an organization's workspace"""
    from workspace_service import get_workspace_service
    ws = get_workspace_service()
    
    print(f"\n🧹 Running cleanup for {org_id}...")
    
    if not ws.workspace_exists(org_id):
        print(f"   ✗ Workspace not found")
        return
    
    result = ws.full_cleanup(org_id)
    
    print(f"   Sessions archived: {result.get('sessions_archived', 0)}")
    print(f"   Memory files archived: {result.get('memory_archived', 0)}")
    print(f"   ✓ Cleanup complete")


def main():
    parser = argparse.ArgumentParser(
        description="Provision FundFish agent workspaces",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "org_id",
        nargs="?",
        help="Organization ID to provision"
    )
    parser.add_argument(
        "--create-test",
        action="store_true",
        help="Create and provision a test organization"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all workspaces"
    )
    parser.add_argument(
        "--cleanup",
        metavar="ORG_ID",
        help="Run cleanup on specified org"
    )
    parser.add_argument(
        "--workspace-root",
        help="Override workspace root directory"
    )
    
    args = parser.parse_args()
    
    # Override workspace root if specified
    if args.workspace_root:
        os.environ["FUNDFISH_WORKSPACE_ROOT"] = args.workspace_root
    
    if args.list:
        list_workspaces()
    elif args.cleanup:
        run_cleanup(args.cleanup)
    elif args.create_test:
        test_config = create_test_org()
        result = provision_workspace(test_config["id"], test_config)
        print(json.dumps(result, indent=2))
    elif args.org_id:
        result = provision_workspace(args.org_id)
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
