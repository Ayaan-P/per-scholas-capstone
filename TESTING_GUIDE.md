# Organization-Agnostic Grant Matching System - Testing Guide

## Overview

This guide provides step-by-step instructions to verify that the organization-agnostic grant matching system is working correctly end-to-end.

## Prerequisites

1. **SQL Migration Applied**: The `expand_organization_profile.sql` migration must be applied to your Supabase database
   - Instructions: Run `python3 apply_migration.py` in the backend directory
   - Or manually apply via Supabase dashboard → SQL Editor → Copy/paste migration → Run

2. **Dependencies Installed**:
   ```bash
   cd backend
   pip install -r requirements.txt
   cd ../frontend
   npm install
   ```

3. **Environment Variables Set**:
   - Backend: `.env` with `SUPABASE_URL`, `SUPABASE_KEY`
   - Frontend: `.env.local` with `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`

---

## Phase 1: Database Schema Verification

### 1.1 Check Migration Applied Successfully

**Test**: Verify new columns exist in organization_config table

```bash
# In Supabase SQL Editor, run:
SELECT column_name FROM information_schema.columns
WHERE table_name = 'organization_config'
ORDER BY column_name;
```

**Expected Results**:
- Should see 30+ new columns including:
  - `ein`
  - `organization_type`
  - `primary_focus_area`
  - `secondary_focus_areas` (array)
  - `key_programs` (jsonb)
  - `annual_budget`
  - `grant_writing_capacity`
  - `custom_search_keywords` (array)
  - `preferred_grant_size_min`, `preferred_grant_size_max`
  - And ~20+ more

### 1.2 Verify Indexes Created

**Test**: Check that new indexes exist

```bash
# In Supabase SQL Editor:
SELECT indexname FROM pg_indexes
WHERE tablename = 'organization_config';
```

**Expected Results**:
- `idx_organization_service_regions` (GIN index on array field)
- `idx_organization_primary_focus`
- `idx_organization_annual_budget`
- `idx_organization_type`

### 1.3 Verify Constraints Created

**Test**: Check constraints

```bash
# In Supabase SQL Editor:
SELECT constraint_name, constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'organization_config';
```

**Expected Results**:
- `valid_organization_type` (CHECK constraint)
- `valid_grant_capacity` (CHECK constraint)
- `valid_tax_status` (CHECK constraint)

### 1.4 Verify View Created

**Test**: Check organization_profiles view exists

```bash
# In Supabase SQL Editor:
SELECT * FROM organization_profiles LIMIT 1;
```

**Expected Results**:
- Query succeeds (or returns empty if no data yet)
- Shows consolidated view of organization data

---

## Phase 2: Backend Service Verification

### 2.1 Test OrganizationMatchingService Initialization

**Test**: Verify OrganizationMatchingService imports and initializes correctly

```bash
cd backend
python3 -c "from organization_matching_service import OrganizationMatchingService; print('✓ OrganizationMatchingService imports successfully')"
```

**Expected Results**:
- No import errors
- Message prints successfully

### 2.2 Test Organization Profile Fetching

**Test**: Create a test organization and verify profile fetching works

1. Insert test data into Supabase:
   ```bash
   # In Supabase SQL Editor:
   INSERT INTO organization_config (
     name,
     mission,
     organization_type,
     primary_focus_area,
     secondary_focus_areas,
     annual_budget,
     grant_writing_capacity,
     custom_search_keywords
   ) VALUES (
     'Test Nonprofit',
     'We provide job training to low-income adults',
     'nonprofit',
     'workforce-development',
     ARRAY['social-services', 'economic-development'],
     500000,
     'moderate',
     ARRAY['trauma-informed', 'community-led']
   ) RETURNING id;
   ```

2. Note the returned `id` (will be used below)

3. Test the service:
   ```bash
   python3 << 'EOF'
   import asyncio
   from supabase import create_client
   from organization_matching_service import OrganizationMatchingService
   import os

   async def test():
       supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
       service = OrganizationMatchingService(supabase)

       # Use the ID from the INSERT statement above
       org_profile = await service.get_organization_profile("INSERT_ID_HERE")
       print("✓ Organization profile fetched:")
       print(f"  Name: {org_profile['name']}")
       print(f"  Focus: {org_profile['primary_focus_area']}")
       print(f"  Capacity: {org_profile['grant_writing_capacity']}")

   asyncio.run(test())
   EOF
   ```

**Expected Results**:
- Profile fetches successfully
- All fields populated correctly
- No errors

### 2.3 Test Keyword Building

**Test**: Verify dynamic keyword generation from organization profile

```bash
python3 << 'EOF'
import asyncio
from supabase import create_client
from organization_matching_service import OrganizationMatchingService
import os

async def test():
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    service = OrganizationMatchingService(supabase)

    org_profile = await service.get_organization_profile("INSERT_ID_HERE")
    keywords = service.build_search_keywords(org_profile)

    print("✓ Generated search keywords:")
    print(f"  Primary: {keywords['primary']}")
    print(f"  Secondary: {keywords['secondary']}")

asyncio.run(test())
EOF
```

**Expected Results**:
- Primary keywords include: "workforce development", "job training", "low-income"
- Secondary keywords include focus areas and custom keywords
- Keywords are organized into logical groups

### 2.4 Test Grants Service Integration

**Test**: Verify grants_service calls organization matching service

```bash
python3 << 'EOF'
import asyncio
from grants_service import GrantsGovService
from supabase import create_client
import os

async def test():
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    service = GrantsGovService(supabase)

    # Test with user_id
    results = service.search_grants(
        keywords="technology training",
        limit=3,
        user_id="INSERT_ID_HERE"
    )

    print(f"✓ Search completed with {len(results)} results")
    if results:
        print(f"  First grant: {results[0].get('title')}")
        print(f"  Match score: {results[0].get('match_score')}")

asyncio.run(test())
EOF
```

**Expected Results**:
- Search completes without errors
- Returns grant results
- Results include match scores (0-100)

---

## Phase 3: Frontend Verification

### 3.1 Verify Settings Page Loads

**Test**: Navigate to settings page and verify UI loads

1. Start development server:
   ```bash
   cd frontend
   npm run dev
   ```

2. Log in to application

3. Navigate to `/settings`

**Expected Results**:
- Page loads without errors
- 5 tabs visible: Basic, Mission, Programs, Funding, Impact
- Form fields display correctly

### 3.2 Test Basic Information Tab

**Test**: Fill in and submit basic organization information

1. Click "Basic" tab
2. Fill in fields:
   - Organization Name: "Test Nonprofit"
   - Organization Type: "nonprofit"
   - EIN: "12-3456789"
   - Tax Exempt Status: "501c3"
   - Years Established: 2015
   - Annual Budget: 500000
   - Staff Size: 15
   - Board Size: 9
   - Website: "https://example.org"
   - Contact Email: "grants@example.org"
   - Contact Phone: "(555) 123-4567"

3. Click Submit/Save

**Expected Results**:
- Form submits without errors
- Success message appears
- Data persists on page reload

### 3.3 Test Mission & Focus Tab

**Test**: Fill in mission-related fields

1. Click "Mission" tab
2. Fill in fields:
   - Organization Mission: "We provide job training and placement services to empower low-income adults"
   - Primary Focus Area: "workforce-development"
   - Secondary Focus Areas: Select "social-services" and "economic-development"
   - Service Regions: Enter "Los Angeles, CA" and "San Diego, CA"
   - Expansion Plans: "Plan to expand to Orange County in 2025"
   - Languages Served: Select "English" and "Spanish"

3. Click Submit

**Expected Results**:
- Multi-select fields work correctly
- Text fields accept input
- Data saves properly

### 3.4 Test Programs Tab

**Test**: Add and manage programs

1. Click "Programs" tab
2. Click "Add Program"
3. Fill in:
   - Program Name: "Job Training & Placement"
   - Description: "12-week vocational training with job placement, serving 30 participants per cohort"
4. Click "Add"
5. Fill in other fields:
   - Target Populations: Select "low-income families" and "K-12 students"
   - Key Partnerships: Add "Community College", "Workforce Board"
   - Accreditations: Add "CARF", "ISO 9001"

6. Click Submit

**Expected Results**:
- Program can be added/edited/deleted
- Array fields work correctly
- Complex nested objects save properly

### 3.5 Test Funding Tab

**Test**: Configure funding preferences

1. Click "Funding" tab
2. Fill in:
   - Grant Writing Capacity: "moderate"
   - Min Grant Size: 25000
   - Max Grant Size: 500000
   - Matching Fund Capacity: 25%
   - Grant Types: Select "project-based", "general-support", "capacity-building"
   - Custom Keywords: Add "trauma-informed", "community-led"
   - Excluded Keywords: Add "military", "fossil-fuel"
   - Donor Restrictions: "No corporate funders from extractive industries"

3. Click Submit

**Expected Results**:
- All input types work correctly
- Arrays can add/remove items
- Numeric fields validate properly

### 3.6 Test Impact Tab

**Test**: Add impact metrics and success stories

1. Click "Impact" tab
2. Add Key Metric:
   - Metric Name: "Job Placement Rate"
   - Current Value: 75
   - Target Value: 85
   - Unit: "percent"
3. Click "Add Metric"
4. Add Success Story:
   - Title: "From Unemployed to Manager"
   - Description: "Maria was unemployed for 18 months. After our program, she landed a job and was promoted to manager within 6 months..."
5. Click "Add Story"
6. Add Previous Grant:
   - Funder: "California Workforce Development Board"
   - Amount: 150000
   - Year: 2023
   - Outcome: "Successfully served 75 participants"

7. Click Submit

**Expected Results**:
- Complex nested objects save correctly
- JSONB data persists
- Arrays can add/remove items

---

## Phase 4: End-to-End Matching Verification

### 4.1 Test Grant Search with Organization Profile

**Test**: Perform grant search and verify organization-aware matching

1. From the dashboard, click "Search Opportunities"
2. Enter search term: "workforce training"
3. Check "Use my organization profile" (if checkbox available)
4. Click Search

**Expected Results**:
- Search completes successfully
- Results include match scores specific to organization
- Results should prioritize workforce-focused grants
- Results avoid unrelated areas

### 4.2 Verify Match Score Breakdown

**Test**: Check that match scores reflect organization profile

1. In backend logs, look for output like:
   ```
   [ORG MATCH] Score breakdown for grant "...":
   - Overall Score: 82
   - Keyword Match: 85
   - Semantic Similarity: 80
   - Funding Alignment: 78
   - Deadline Feasibility: 85
   - Demographics Match: 75
   - Geographic Match: 70
   ```

**Expected Results**:
- Scores show org-aware calculations (not hardcoded Per Scholas)
- Different grants have different scores based on org profile
- Log shows detailed breakdown of each component

### 4.3 Verify Filtering Logic

**Test**: Confirm that grants outside criteria are filtered

1. Set narrow criteria:
   - Max Grant Size: $100,000
   - Grant Writing Capacity: Limited
   - Excluded Keywords: "international"

2. Search for grants

**Expected Results**:
- Grants larger than $100K are filtered out or ranked lower
- International grants do not appear
- Limited capacity affects deadline feasibility scores

---

## Phase 5: Comparison Testing

### 5.1 Org-Aware vs. Standard Matching

**Test**: Compare results with vs. without organization profile

1. **With Organization Profile**:
   - Log in as user with complete profile
   - Search for "training"
   - Note results and scores

2. **Without Organization Profile**:
   - Log in as user without/empty profile
   - Search for same term
   - Note results and scores

**Expected Results**:
- With profile: Results are more specific and lower-ranked grants
- Without profile: Results use generic/Per Scholas matching
- Different users get different results for same search

### 5.2 Verify Fallback Behavior

**Test**: Ensure system works even if organization profile not available

1. In grants_service.py, temporarily disable org matching
2. Search for grants
3. Verify results still appear (using fallback scoring)

**Expected Results**:
- System doesn't crash when org_profile unavailable
- Falls back to standard matching algorithm
- User still gets grant results

---

## Phase 6: Performance Verification

### 6.1 Test Database Query Performance

**Test**: Verify caching prevents N+1 queries

1. Enable query logging in Supabase
2. Perform multiple searches in quick succession
3. Check query count

**Expected Results**:
- First search: 1 organization_config query + grant search
- Second search: 0 organization_config queries (uses cache)
- Cache reduces database load

### 6.2 Test Load Performance

**Test**: Verify system handles multiple concurrent searches

```bash
# In separate terminals, start multiple searches
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/search-opportunities \
    -H "Authorization: Bearer TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"prompt": "workforce training grants"}' &
done
```

**Expected Results**:
- All searches complete successfully
- No timeout errors
- Response times reasonable (< 30 seconds)

---

## Troubleshooting Guide

### Issue: "Column does not exist" error

**Solution**: Migration not applied
- Run: `python3 apply_migration.py`
- Or manually apply via Supabase dashboard

### Issue: OrganizationMatchingService import error

**Solution**: Ensure file exists and Python path is correct
```bash
# Verify file exists
ls -la organization_matching_service.py

# Ensure backend directory is in Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Issue: Settings page doesn't save data

**Solution**: Check Supabase RLS policies
- Go to Supabase → Security → RLS Policies
- Verify "Users can view and update their own organization" policy exists
- Check that policy includes new columns in SELECT/UPDATE

### Issue: Match scores all zeros or very low

**Solution**: Organization profile not being fetched
- Check that user_id is being passed correctly through API
- Verify user has an organization_config record
- Check backend logs for error messages

### Issue: Database schema validation errors

**Solution**: Constraints being violated
- Check data types match schema (e.g., annual_budget should be integer/number)
- Verify organization_type is one of valid options
- Ensure grant_writing_capacity is 'limited', 'moderate', or 'advanced'

---

## Success Criteria Checklist

- [ ] Phase 1: All migration components verified (columns, indexes, constraints, view)
- [ ] Phase 2: Backend services initialize and function correctly
- [ ] Phase 3: Frontend settings page loads and saves data in all 5 tabs
- [ ] Phase 4: End-to-end search works and shows org-specific results
- [ ] Phase 5: Org-aware matching differs from standard matching
- [ ] Phase 6: Performance meets expectations (queries cached, concurrent searches handled)

---

## Next Steps After Testing

1. **Fix any issues found** using troubleshooting guide
2. **Gather user feedback** on settings page UX
3. **Monitor logs** for any errors in production
4. **Iterate on algorithm weights** if match quality could be improved
5. **Add admin dashboard** for monitoring matching performance
6. **Consider integration tests** to catch future regressions

---

*This testing guide ensures the organization-agnostic matching system is working correctly before rollout.*
