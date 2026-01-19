# FundSync Matching Algorithm Guide

## Overview

The FundSync matching algorithm intelligently matches nonprofit organizations with funding opportunities based on their comprehensive organizational profile. Unlike traditional keyword-matching, our system uses multi-factor scoring to evaluate grant alignment across multiple dimensions.

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│            GRANT OPPORTUNITY (Grants.gov, etc.)         │
├─────────────────────────────────────────────────────────┤
│ - Title, description, synopsis                          │
│ - Eligibility criteria, focus areas                      │
│ - Funding amount, deadline                              │
│ - Geographic focus, beneficiaries                       │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│    GRANT FILTER (grant_filters.py)                      │
├─────────────────────────────────────────────────────────┤
│ - Status: Open/Active?                                  │
│ - Deadline: Future & sufficient time?                   │
│ - Nonprofit eligible?                                   │
│ - Amount: Within reasonable range?                      │
│ - Keywords: Contains relevant terms?                    │
└──────────────────────────┬──────────────────────────────┘
                           │
                    [Passes Filter?]
                           │
                ┌──────────┴──────────┐
                │ Yes                 │ No
                ▼                     ▼
    ┌──────────────────┐      [Excluded]
    │ Grant Passes     │
    └────────┬─────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│  ORGANIZATION PROFILE (organization_config table)       │
├─────────────────────────────────────────────────────────┤
│ - Primary focus area, programs                          │
│ - Service regions, target populations                   │
│ - Grant writing capacity, preferred sizes               │
│ - Custom keywords, exclusions                           │
│ - Impact metrics, previous grants                       │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  ORGANIZATION MATCHING SERVICE                          │
│  (organization_matching_service.py)                     │
├─────────────────────────────────────────────────────────┤
│ OrganizationMatchingService:                            │
│ - get_organization_profile(user_id)                     │
│ - build_search_keywords(org_profile)                    │
│ - calculate_organization_match_score()                  │
│ - get_demographic_match_score()                         │
│ - get_geographic_match_score()                          │
│ - get_funding_alignment_score()                         │
│ - should_filter_grant()                                 │
└──────────────────────────┬──────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌─────────────────┐ ┌──────────────┐ ┌───────────────┐
│Keyword Matching │ │Semantic      │ │Funding/Geo/   │
│    Service      │ │Similarity    │ │Demographics   │
│(match_scoring)  │ │(semantic_    │ │Scoring        │
│                 │ │service.py)   │ │               │
│- Core keywords  │ │              │ │               │
│- Context keywords  │ - Vector db │ │               │
│- Scoring: 0-100 │ │  lookup      │ │               │
└────────┬────────┘ │ - Similarity │ └───────┬───────┘
         │          │   comparison │         │
         └──────────┴──────┬───────┴─────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│      WEIGHTED SCORE CALCULATION                         │
├─────────────────────────────────────────────────────────┤
│ Overall = (Keyword×30%) + (Semantic×40%) +             │
│          (Funding×15%) + (Deadline×8%) +               │
│          (Demographics×5%) + (Geographic×2%)           │
│                                                         │
│ Weights adjusted based on:                             │
│ - Organization capacity (limited/moderate/advanced)    │
│ - Organization size (staff, budget)                    │
│ - Geographic focus                                     │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  RANKED RESULTS                                         │
├─────────────────────────────────────────────────────────┤
│ 1. Grant A - 92/100 (Excellent fit)                    │
│ 2. Grant B - 78/100 (Very good fit)                    │
│ 3. Grant C - 68/100 (Good fit)                         │
│ ...                                                     │
└─────────────────────────────────────────────────────────┘
```

## Key Services

### 1. OrganizationMatchingService (`organization_matching_service.py`)

The core service that implements organization-aware matching.

#### Main Methods

**`get_organization_profile(user_id) → Dict`**
- Fetches organization config from database
- Includes all profile fields: focus areas, programs, target populations, preferences, etc.
- Returns complete organization profile or None if not found

**`build_search_keywords(org_profile) → Tuple[List[str], List[str]]`**
- Generates dynamic search keywords from organization profile
- Returns: (primary_keywords, secondary_keywords)
- Process:
  1. Add primary focus area as keyword
  2. Map focus area to relevant grant keywords
  3. Add secondary focus areas
  4. Extract keywords from program descriptions
  5. Add population-specific keywords
  6. Add custom search keywords from profile
  7. Deduplicate while preserving order

**Example:**
```python
org = {
    'primary_focus_area': 'education',
    'secondary_focus_areas': ['technology', 'workforce-development'],
    'key_programs': [
        {'name': 'STEM Academy', 'description': 'Coding and robotics for underserved youth'},
        {'name': 'Career Pathways', 'description': 'Job training and placement'}
    ],
    'custom_search_keywords': ['underrepresented', 'equity']
}

primary, secondary = matcher.build_search_keywords(org)
# primary: ['education']
# secondary: ['technology', 'workforce-development', 'school', 'student', 'learning',
#             'coding', 'robotics', 'underserved', 'youth', 'job', 'training',
#             'underrepresented', 'equity', ...]
```

**`get_matching_score_weights(org_profile) → Dict[str, float]`**
- Returns scoring component weights customized for the organization
- Adjusts based on:
  - Grant writing capacity (limited → higher deadline weight; advanced → higher semantic weight)
  - Organization size (tiny → higher deadline/deadline feasibility; large → can handle complexity)
- Returns normalized weights summing to 1.0

**Example:**
```python
# For limited-capacity organization
weights = {
    'keyword_matching': 0.25,      # Slightly lower
    'semantic_similarity': 0.38,   # Lower
    'funding_alignment': 0.15,
    'deadline_feasibility': 0.12,  # HIGHER (easier deadlines prioritized)
    'demographic_alignment': 0.05,
    'geographic_alignment': 0.05   # Slightly higher
}

# For advanced-capacity organization
weights = {
    'keyword_matching': 0.30,
    'semantic_similarity': 0.50,   # HIGHER (can handle complexity)
    'funding_alignment': 0.15,
    'deadline_feasibility': 0.03,  # Lower (tight deadlines OK)
    'demographic_alignment': 0.05,
    'geographic_alignment': 0.02,
}
```

**`get_demographic_match_score(org_profile, grant_description) → float (0-100)`**
- Scores how well grant beneficiaries match organization's target populations
- Algorithm:
  1. Extract all target populations from org profile
  2. For each population, search grant description for matching keywords
  3. Count how many target populations have keyword matches
  4. Score = 50 + (match_percentage / 2)
  5. Range: 25 (no matches) to 100 (all populations mentioned)

**Example:**
```python
org = {
    'target_populations': ['K-12 students', 'low-income families', 'underrepresented communities']
}
grant_desc = "This grant supports afterschool programs for low-income students in underrepresented communities..."

# Matches: 'low-income' ✓, 'underrepresented communities' ✓, 'students' ✓ (K-12)
# Score = 50 + (3/3 / 2) = 50 + 50 = 100
```

**`get_geographic_match_score(org_profile, grant_geographic_focus) → float (0-100)`**
- Scores geographic alignment
- Scoring logic:
  - National grants: 100 (available everywhere)
  - Direct regional match (e.g., "Los Angeles, CA" in both org and grant): 90
  - State-level match: 75
  - No match: 25
  - Broader geographic match (rural/urban): 70

**`get_funding_alignment_score(org_profile, grant_min, grant_max) → float (0-100)`**
- Scores if grant amount fits organization's preferences
- Within preferred range: 100
- Below preferred min: scales from 0-50 based on ratio
- Above preferred max: scales from 50-100 based on ratio

**Example:**
```python
org = {
    'preferred_grant_size_min': 25000,
    'preferred_grant_size_max': 500000
}

# Grant: $100,000
# Within range → Score = 100

# Grant: $10,000 (below min)
# Ratio = 10,000 / 25,000 = 0.4
# Score = 50 × 0.4 = 20 (below minimum range)

# Grant: $750,000 (above max)
# Ratio = 500,000 / 750,000 = 0.667
# Score = 50 + (50 × 0.667) = 83
```

**`calculate_organization_match_score(org_profile, grant, keyword_score, semantic_score) → Dict`**
- Main scoring method combining all factors
- Returns:
  ```python
  {
      'overall_score': 85.3,
      'keyword_matching': 75,
      'semantic_similarity': 90,
      'funding_alignment': 100,
      'deadline_feasibility': 85,
      'demographic_alignment': 80,
      'geographic_alignment': 95,
      'weights': { ... }
  }
  ```

**`should_filter_grant(org_profile, grant) → Tuple[bool, Optional[str]]`**
- Determines if grant should be excluded based on org constraints
- Checks:
  - Donor restrictions (e.g., "no government funding")
  - Matching fund capacity vs. grant requirements
  - Deadline feasibility for limited-capacity orgs
- Returns: (should_exclude: bool, reason: str)

**Example:**
```python
org = {
    'donor_restrictions': 'No government funding',
    'grant_writing_capacity': 'limited',
    'matching_fund_capacity': 0
}

grant = {
    'agency_name': 'Department of Labor',  # Government
    'cost_sharing_required': True,
    'deadline': '2026-01-20'  # 5 days away
}

# Checks:
# 1. "government" in agency_name and "No government" in restrictions → FILTER
# Result: (True, "Organization does not accept government funding")
```

### 2. Match Scoring Service (`match_scoring.py`)

Provides base keyword and semantic matching scores before organization context is applied.

**`calculate_match_score(grant, org_keywords) → float (0-100)`**
- Scores keyword relevance: 0-30 points
- Scores semantic similarity: 0-50 points
- Scores funding alignment: 0-15 points
- Scores deadline feasibility: 0-5 points
- Applies domain penalties (exclude health, agriculture, etc.)
- Applies user feedback adjustments (±10 points)

**`get_score_breakdown(score_dict) → str`**
- Returns human-readable explanation of scoring
- Useful for showing users why a grant scored as it did

### 3. Semantic Service (`semantic_service.py`)

Provides AI-powered semantic matching using embeddings.

**`find_similar_rfps(grant_description) → List[str]`**
- Finds historical RFPs similar to current grant
- Uses vector similarity search in pgvector
- Returns list of similar RFP IDs/descriptions

**`find_similar_proposals(grant_description) → List[Dict]`**
- Finds past successful proposals similar to current grant
- Returns proposals marked as "won" for reference
- Used by LLM service to suggest winning strategies

---

## Integration Points

### Where the Matching Algorithm is Called

#### 1. **Search Results Page** (Dashboard/Search)
When user searches for opportunities:
```python
# In backend route handler
org_profile = await org_service.get_organization_profile(user_id)
matcher = OrganizationMatchingService(supabase)

for grant in filtered_grants:
    should_exclude, reason = matcher.should_filter_grant(org_profile, grant)
    if should_exclude:
        continue

    score_dict = matcher.calculate_organization_match_score(
        org_profile,
        grant,
        base_keyword_score,  # from match_scoring
        semantic_similarity  # from semantic_service
    )

    grant['match_score'] = score_dict['overall_score']
    grant['score_breakdown'] = score_dict  # For detailed view
```

#### 2. **Opportunity Saving** (When user saves grant)
When user saves an opportunity, LLM enhancement happens:
```python
# In llm_enhancement_service
org_profile = await org_service.get_organization_profile(user_id)
matcher = OrganizationMatchingService(supabase)

# Get organization matching summary
org_summary = matcher.get_matching_summary(org_profile)

# Pass to Gemini for insights generation
insights = await generate_insights(
    grant,
    org_summary,
    org_profile
)
```

#### 3. **Profile Matching Preview**
When user views their profile:
```python
# In settings page backend
org_profile = await org_service.get_organization_profile(user_id)
matcher = OrganizationMatchingService(supabase)

summary = matcher.get_matching_summary(org_profile)
# Returns: {
#   'primary_keywords': [...],
#   'secondary_keywords': [...],
#   'service_regions': [...],
#   'target_populations': [...],
#   'preferred_grant_range': {...},
#   ...
# }
```

---

## Algorithm Customization

### Adjusting Scoring Weights

To change how much each factor matters:

1. **For Specific Organization Types:**
   ```python
   def get_matching_score_weights(self, org_profile):
       weights = {...}

       # For education nonprofits, emphasize demographic match
       if org_profile.get('primary_focus_area') == 'education':
           weights['demographic_alignment'] = 0.15  # Increased from 0.05
           weights['semantic_similarity'] = 0.30    # Decreased from 0.40
           # Renormalize
           total = sum(weights.values())
           weights = {k: v/total for k, v in weights.items()}

       return weights
   ```

2. **Based on Specific Preferences:**
   ```python
   # If org prioritizes matching funds strongly
   if org_profile.get('matching_fund_capacity', 0) > 50:
       weights['funding_alignment'] *= 1.2  # Weight more heavily
   ```

### Adding New Matching Factors

To add a new scoring dimension (e.g., "accreditation match"):

1. **Add calculation method:**
   ```python
   def get_accreditation_match_score(self, org_profile, grant) -> float:
       accredits = set(org_profile.get('accreditations', []))
       grant_required = set(grant.get('required_accreditations', []))

       if not grant_required:
           return 50  # Neutral if not specified

       if accredits >= grant_required:
           return 100  # Has all required

       matching = len(accredits & grant_required) / len(grant_required)
       return 50 + (matching * 50)
   ```

2. **Add to calculation method:**
   ```python
   def calculate_organization_match_score(self, org_profile, grant, ...):
       scores['accreditation_match'] = self.get_accreditation_match_score(org_profile, grant)
       weights['accreditation_match'] = 0.05  # New weight

       # Renormalize to maintain 1.0 total
       total = sum(weights.values())
       weights = {k: v/total for k, v in weights.items()}

       overall = sum(scores[key] * weights[key] for key in scores)
       return {'overall_score': overall, ...}
   ```

---

## Search Keyword Generation

The algorithm dynamically builds search queries based on organization profile:

```python
primary, secondary = matcher.build_search_keywords(org)

# Example output:
# primary = ['education']
# secondary = ['school', 'student', 'learning', 'training', 'curriculum',
#              'workforce', 'job', 'employment', 'stem', 'technology', ...]

# These are then used to build Grants.gov queries:
queries = [
    f"({' OR '.join(primary)})",  # Must have primary
    " AND " + f"({' OR '.join(secondary[:10])})",  # Boost with secondary
]
# Query: "(education) AND (school OR student OR learning OR training OR curriculum OR workforce OR job ...)"
```

---

## Performance Considerations

### Database Queries
- `get_organization_profile`: Single indexed lookup by user_id → fast
- `find_similar_rfps`: Vector similarity search (pgvector) → moderately fast
- Cache results for 15 minutes to avoid redundant searches

### Score Calculation
- Each organization match score calculation: O(n) where n = number of target populations + geographic regions
- Per grant: ~50-100ms (depending on description length)
- For 100 grants: ~5-10 seconds

### Optimization Strategies
1. **Batch Processing:** Calculate scores for all grants at once
2. **Caching:** Store org profile in memory during search session
3. **Lazy Loading:** Only calculate detailed scores when user clicks on grant
4. **Lazy Semantic Search:** Only run expensive semantic matching for top keyword matches

---

## Testing

### Test Cases

```python
# Test 1: Organization-specific keyword generation
org = {
    'primary_focus_area': 'education',
    'secondary_focus_areas': ['technology'],
    'key_programs': [{
        'name': 'Coding Bootcamp',
        'description': 'Teaching Python and JavaScript to underrepresented youth'
    }],
    'custom_search_keywords': ['equity']
}
primary, secondary = matcher.build_search_keywords(org)
assert 'education' in primary
assert 'technology' in secondary
assert 'coding' in secondary
assert 'equity' in secondary

# Test 2: Demographic matching
org = {'target_populations': ['K-12 students', 'low-income families']}
grant_desc = "Support for low-income elementary and middle school students..."
score = matcher.get_demographic_match_score(org, grant_desc)
assert score > 80  # Good match

# Test 3: Organization filtering
org = {
    'donor_restrictions': 'No military funding',
    'grant_writing_capacity': 'limited'
}
grant = {
    'agency_name': 'Department of Defense',
    'deadline': '2026-01-20'  # Very soon
}
exclude, reason = matcher.should_filter_grant(org, grant)
assert exclude == True
assert 'military' in reason.lower() or 'government' in reason.lower()
```

---

## Migration from Per Scholas-Specific to Organization-Agnostic

The old system hardcoded Per Scholas keywords:
```python
FIXED_KEYWORDS = ['technology', 'workforce', 'training', 'stem', 'coding', ...]
```

The new system generates keywords dynamically:
```python
# Old approach (Per Scholas only)
def search_grants(keywords=FIXED_KEYWORDS):
    return search_grants_api(keywords)

# New approach (any organization)
def search_grants(user_id):
    org = get_org_profile(user_id)
    keywords = build_search_keywords(org)
    return search_grants_api(keywords)
```

### Migration Checklist
- [ ] Update all grant search calls to use `build_search_keywords()`
- [ ] Update scoring to use `calculate_organization_match_score()` instead of hardcoded weights
- [ ] Update filter logic to use `should_filter_grant()`
- [ ] Test with multiple organization profiles (education, health, environment, etc.)
- [ ] Update frontend to show organization's keywords in settings preview
- [ ] Add matching summary page to show why grants are matched

---

## Future Enhancements

1. **Machine Learning Scoring**: Learn weights from user feedback
   - Track which grants user applies to vs. ignores
   - Adjust weights to maximize user engagement

2. **Time-Based Weighting**: Adjust based on season
   - Education grants peak in spring
   - Community development grants peak in fall

3. **Competitive Intelligence**: Factor in how similar organizations describe themselves
   - "If similar orgs are applying for X, weight it higher"

4. **Matching Fund Optimization**: Suggest which grants best leverage your matching capacity
   - Recommend grants where your 25% match goes furthest

5. **Grant Pipeline Analysis**: Predict grant success based on profile similarity to past winners
   - "Organizations like you have 60% success rate on grants from X funder"

---

*Last Updated: January 2026*
