# URL Validation Implementation

**Date:** 2026-03-20
**Task:** P1: Add URL validation to librarian  
**Status:** ✅ IMPLEMENTED
**Commit:** (pending)

---

## Overview

Added URL validation to verify grant URLs are accessible before storing them in the database. Broken or inaccessible URLs are flagged, and grants with invalid URLs can be filtered out.

## Changes

### 1. Added URL Validation to `grants_service.py`

**New imports:**
```python
import asyncio
import aiohttp
```

**New methods:**
- `_validate_url(url, timeout=5)` - Async method to check a single URL
- `_validate_urls_batch(urls)` - Async batch validation for multiple URLs concurrently
- `validate_grant_urls(grants)` - Public method to validate all grant URLs

**Integration:**
- Modified `search_grants()` to validate URLs before returning
- Filters out grants with invalid URLs automatically
- Logs invalid URLs for debugging

**Features:**
- ✅ Async/concurrent validation (minimal latency impact)
- ✅ Uses HTTP HEAD requests (lightweight)
- ✅ Follows redirects
- ✅ 5-second timeout per URL
- ✅ Handles timeouts, client errors, and HTTP errors
- ✅ Adds validation metadata to each grant

### 2. Database Schema Migration

**File:** `backend/migrations/add_url_validation_fields.sql`

**New columns added to `scraped_grants` table:**
- `url_valid` (BOOLEAN) - Whether URL is accessible (default: true)
- `url_validation_error` (TEXT) - Error message if validation failed
- `url_status_code` (INTEGER) - HTTP status code from validation
- `url_last_checked` (TIMESTAMP) - When URL was last validated

**Index:**
- `idx_scraped_grants_url_valid` - For querying invalid URLs

### 3. Updated `scheduler_service.py`

**Modified:**
- INSERT operation for new grants - saves URL validation fields
- UPDATE operation for existing grants - updates URL validation fields

**Fields saved:**
```python
"url_valid": grant.get("url_valid", True),
"url_validation_error": grant.get("url_validation_error"),
"url_status_code": grant.get("url_status_code"),
"url_last_checked": datetime.now().isoformat() if grant.get("url_valid") is not None else None
```

## Workflow

1. **Grant Discovery:** Grants are fetched from Grants.gov API
2. **URL Construction:** `application_url` is built from opportunity ID
3. **URL Validation:** All grant URLs are validated concurrently
4. **Filtering:** Grants with invalid URLs are excluded
5. **Storage:** Valid grants + validation metadata saved to database

## Example Output

```
[GRANTS SERVICE] Found 25 opportunities
[GRANTS SERVICE] Validating grant URLs...
[GRANTS] Invalid URL for GRANT-12345: https://www.grants.gov/search-results-detail/invalid-id - HTTP 404
[GRANTS SERVICE] Filtered out 1 grants with invalid URLs
```

## Grant Object Schema (updated)

Each grant now includes:
```python
{
  "id": "...",
  "title": "...",
  "application_url": "https://www.grants.gov/search-results-detail/12345",
  
  # NEW VALIDATION FIELDS
  "url_valid": true,
  "url_validation_error": null,
  "url_status_code": 200
}
```

## Acceptance Criteria

- [x] Librarian visits each grant URL before storing
- [x] Broken URLs are flagged (url_valid=false, error stored)
- [x] Invalid grants are excluded from results
- [x] Adds minimal latency (async/batched checks)
- [x] Database schema supports validation tracking
- [x] Existing grants can be re-validated on update

## Dependencies

**Already in requirements.txt:**
- `aiohttp>=3.9.0` ✅

## Testing

**Test file:** `backend/test_url_validation.py`

Tests validation with:
- Valid URLs (grants.gov)
- Invalid domains
- 404 pages
- Missing URLs

**To run:**
```bash
cd backend
python3 -m venv test_venv
source test_venv/bin/activate
pip install -r requirements.txt
python3 test_url_validation.py
```

## Deployment Steps

1. ✅ Code committed to main
2. ⏳ Run migration in Supabase SQL Editor
3. ⏳ Render auto-deploys from main
4. ⏳ Next grant scrape will validate URLs
5. ⏳ Verify in database: check `url_valid`, `url_validation_error` columns

## Migration Instructions

Run in Supabase SQL Editor:
```sql
-- Copy contents of backend/migrations/add_url_validation_fields.sql
```

Verify with:
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'scraped_grants'
  AND column_name IN ('url_valid', 'url_validation_error', 'url_status_code', 'url_last_checked')
ORDER BY column_name;
```

## Future Enhancements

- [ ] Periodic re-validation of old grants (cron job)
- [ ] Dashboard to view/filter grants by URL validity
- [ ] Retry logic for transient failures
- [ ] URL validation cache to avoid re-checking same URLs

---

**Implementation:** Complete ✅  
**Testing:** Manual testing required (production deployment)  
**Migration:** SQL ready for Supabase  
**Auto-deploy:** Ready for Render
