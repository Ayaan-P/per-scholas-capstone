#!/usr/bin/env python3
"""
Test URL validation for grants
Tests the new validate_grant_urls functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from grants_service import GrantsGovService

def test_url_validation():
    """Test URL validation with a mix of valid and invalid URLs"""
    
    service = GrantsGovService()
    
    # Test grants with various URL scenarios
    test_grants = [
        {
            "id": "TEST-001",
            "title": "Valid Grant",
            "application_url": "https://www.grants.gov"
        },
        {
            "id": "TEST-002", 
            "title": "Invalid Domain Grant",
            "application_url": "https://this-domain-definitely-does-not-exist-12345.com"
        },
        {
            "id": "TEST-003",
            "title": "404 Grant",
            "application_url": "https://www.grants.gov/this-page-does-not-exist-404"
        },
        {
            "id": "TEST-004",
            "title": "No URL Grant",
            "application_url": None
        }
    ]
    
    print("Testing URL validation...")
    print("=" * 60)
    
    validated_grants = service.validate_grant_urls(test_grants)
    
    for grant in validated_grants:
        print(f"\nGrant: {grant['id']} - {grant['title']}")
        print(f"  URL: {grant.get('application_url', 'N/A')}")
        print(f"  Valid: {grant.get('url_valid', 'unknown')}")
        print(f"  Status: {grant.get('url_status_code', 'N/A')}")
        print(f"  Error: {grant.get('url_validation_error', 'None')}")
    
    print("\n" + "=" * 60)
    
    # Count results
    valid_count = sum(1 for g in validated_grants if g.get('url_valid'))
    invalid_count = sum(1 for g in validated_grants if not g.get('url_valid'))
    
    print(f"\nResults:")
    print(f"  Valid URLs: {valid_count}")
    print(f"  Invalid URLs: {invalid_count}")
    print(f"  Total: {len(validated_grants)}")
    
    # Test filtering
    print("\n" + "=" * 60)
    print("\nFiltered grants (valid URLs only):")
    valid_grants = [g for g in validated_grants if g.get('url_valid', True)]
    for grant in valid_grants:
        print(f"  - {grant['id']}: {grant.get('application_url', 'N/A')}")
    
    print("\n✅ URL validation test complete!")

if __name__ == "__main__":
    test_url_validation()
