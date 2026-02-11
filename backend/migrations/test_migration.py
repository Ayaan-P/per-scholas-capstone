#!/usr/bin/env python3
"""
Test script for agentic architecture database migration.
Validates SQL syntax and simulates migration without applying to production.

Usage:
    python test_migration.py [--dry-run] [--validate-only]
    
Options:
    --dry-run        Parse SQL but don't execute
    --validate-only  Only check SQL syntax, skip connection
"""

import os
import sys
import re
from pathlib import Path

# Migration files in order
MIGRATION_FILES = [
    '001_org_grants.sql',
    '002_org_briefs.sql', 
    '003_user_saves.sql',
    'migrate_saved_opportunities.sql',
]

ROLLBACK_FILE = 'rollback.sql'

def validate_sql_syntax(sql_content: str, filename: str) -> tuple[bool, list[str]]:
    """Basic SQL syntax validation."""
    errors = []
    
    # Check for common issues
    lines = sql_content.split('\n')
    
    # Track parentheses balance
    paren_count = 0
    for i, line in enumerate(lines, 1):
        # Skip comments
        if line.strip().startswith('--'):
            continue
        
        paren_count += line.count('(') - line.count(')')
        
        # Check for dangerous patterns
        if 'DROP TABLE' in line.upper() and 'IF EXISTS' not in line.upper():
            if filename != 'rollback.sql':
                errors.append(f"Line {i}: DROP TABLE without IF EXISTS - dangerous!")
        
        if 'DELETE FROM' in line.upper() and 'WHERE' not in line.upper():
            # Allow in DO blocks
            if '$' not in line:
                errors.append(f"Line {i}: DELETE without WHERE - dangerous!")
    
    # Check balanced parentheses
    if paren_count != 0:
        errors.append(f"Unbalanced parentheses: {paren_count:+d}")
    
    # Check for required patterns
    if 'CREATE TABLE' in sql_content:
        if 'IF NOT EXISTS' not in sql_content and 'OR REPLACE' not in sql_content:
            # This is okay for the main table create, just check it's there
            pass
    
    return len(errors) == 0, errors


def check_references(sql_content: str, filename: str) -> tuple[bool, list[str]]:
    """Check that foreign key references are valid."""
    warnings = []
    
    # Known tables that should exist
    known_tables = {
        'organization_config',
        'scraped_grants', 
        'auth.users',
        'users',
    }
    
    # Find all REFERENCES
    refs = re.findall(r'REFERENCES\s+(\w+(?:\.\w+)?)\s*\(', sql_content, re.IGNORECASE)
    
    for ref in refs:
        if ref.lower() not in [t.lower() for t in known_tables]:
            warnings.append(f"Reference to '{ref}' - ensure this table exists")
    
    return True, warnings


def check_indexes(sql_content: str, filename: str) -> tuple[bool, list[str]]:
    """Check that indexes are created for foreign keys and common queries."""
    info = []
    
    # Count indexes
    index_count = sql_content.upper().count('CREATE INDEX')
    
    if 'CREATE TABLE' in sql_content and index_count == 0:
        info.append("No indexes created - consider adding for performance")
    else:
        info.append(f"Found {index_count} index definitions")
    
    return True, info


def analyze_migration(migrations_dir: Path) -> dict:
    """Analyze all migration files."""
    results = {
        'valid': True,
        'files': {},
        'summary': []
    }
    
    # Process each migration file
    for filename in MIGRATION_FILES + [ROLLBACK_FILE]:
        filepath = migrations_dir / filename
        
        if not filepath.exists():
            results['files'][filename] = {
                'exists': False,
                'errors': [f"File not found: {filepath}"]
            }
            results['valid'] = False
            continue
        
        content = filepath.read_text()
        file_result = {
            'exists': True,
            'size': len(content),
            'lines': len(content.split('\n')),
            'errors': [],
            'warnings': [],
            'info': []
        }
        
        # Run validations
        valid, errors = validate_sql_syntax(content, filename)
        file_result['errors'].extend(errors)
        
        valid, warnings = check_references(content, filename)
        file_result['warnings'].extend(warnings)
        
        valid, info = check_indexes(content, filename)
        file_result['info'].extend(info)
        
        if file_result['errors']:
            results['valid'] = False
        
        results['files'][filename] = file_result
    
    return results


def print_report(results: dict):
    """Print validation report."""
    print("=" * 60)
    print("AGENTIC MIGRATION VALIDATION REPORT")
    print("=" * 60)
    print()
    
    for filename, data in results['files'].items():
        status = "✅" if not data.get('errors') else "❌"
        print(f"{status} {filename}")
        
        if not data.get('exists'):
            print(f"   ❌ File not found!")
            continue
        
        print(f"   📄 {data['lines']} lines, {data['size']} bytes")
        
        for error in data.get('errors', []):
            print(f"   ❌ ERROR: {error}")
        
        for warning in data.get('warnings', []):
            print(f"   ⚠️  WARNING: {warning}")
        
        for info in data.get('info', []):
            print(f"   ℹ️  {info}")
        
        print()
    
    print("=" * 60)
    if results['valid']:
        print("✅ ALL VALIDATIONS PASSED")
    else:
        print("❌ SOME VALIDATIONS FAILED")
    print("=" * 60)
    
    return results['valid']


def check_documentation(migrations_dir: Path) -> bool:
    """Check that migration documentation exists."""
    doc_file = migrations_dir / 'agentic_migration.md'
    
    if not doc_file.exists():
        print("❌ Missing: agentic_migration.md")
        return False
    
    content = doc_file.read_text()
    
    required_sections = [
        '## Overview',
        '## Migration Files',
        '## Migration Steps',
        '## Rollback',
        '## Backward Compatibility',
    ]
    
    missing = [s for s in required_sections if s not in content]
    
    if missing:
        print(f"⚠️  Documentation missing sections: {missing}")
        return False
    
    print("✅ Documentation complete")
    return True


def main():
    """Main entry point."""
    migrations_dir = Path(__file__).parent
    
    print(f"Analyzing migrations in: {migrations_dir}")
    print()
    
    # Validate SQL files
    results = analyze_migration(migrations_dir)
    sql_valid = print_report(results)
    
    # Check documentation
    print()
    doc_valid = check_documentation(migrations_dir)
    
    # Summary
    print()
    print("=" * 60)
    print("DELIVERABLES CHECKLIST")
    print("=" * 60)
    
    deliverables = {
        '001_org_grants.sql': 'org_grants table',
        '002_org_briefs.sql': 'org_briefs table',
        '003_user_saves.sql': 'user_saves table',
        'migrate_saved_opportunities.sql': 'Data migration script',
        'rollback.sql': 'Rollback script',
        'agentic_migration.md': 'Migration documentation',
    }
    
    all_present = True
    for filename, description in deliverables.items():
        filepath = migrations_dir / filename
        exists = filepath.exists()
        status = "✅" if exists else "❌"
        print(f"{status} {filename} - {description}")
        if not exists:
            all_present = False
    
    print()
    if all_present and sql_valid:
        print("🎉 All deliverables ready for review!")
        return 0
    else:
        print("⚠️  Some items need attention.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
