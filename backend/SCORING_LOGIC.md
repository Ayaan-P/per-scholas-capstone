# Grant Scoring Logic

## Overview

The Grant Qualification Agent scores grants for nonprofit organizations using a two-phase approach:

1. **Rule-Based Pre-Filtering** - Fast, no API cost, catches obvious mismatches
2. **LLM-Based Deep Scoring** - Nuanced analysis using Claude for qualified grants

## Scoring Dimensions

Total score: **0-100 points** across 6 dimensions:

| Dimension | Max Points | Description |
|-----------|------------|-------------|
| Mission Alignment | 30 | How well the grant aligns with org's mission and focus areas |
| Target Population | 20 | Does the grant serve the same demographics/beneficiaries? |
| Geographic Coverage | 15 | Does geographic scope match? |
| Funding Fit | 15 | Is the funding amount appropriate for org's capacity? |
| Eligibility | 10 | Does the org meet stated requirements? |
| Strategic Value | 10 | Timing, funder relationship potential, strategic opportunity |

## Score Interpretation

| Score Range | Meaning | Action |
|------------|---------|--------|
| **80-100** | Excellent match | Definitely apply - high priority |
| **60-79** | Good match | Worth considering - review details |
| **40-59** | Moderate match | Possible fit - needs analysis |
| **20-39** | Weak match | Unlikely fit - skip unless strategic |
| **0-19** | No match | Do not pursue |

## Pre-Filtering Rules

Grants are filtered **before** expensive LLM scoring based on:

### Hard Exclusions
Grants containing these keywords are automatically rejected:
- agriculture, farming, livestock, dairy
- petroleum, mining, fossil fuel
- tobacco, gambling, firearms
- international development abroad (for domestic orgs)

### Deadline Check
- Grants with passed deadlines are rejected

### Relevance Check
- Must have at least 1 keyword match from org's focus areas
- Empty or completely irrelevant grants are filtered

## LLM Scoring Prompt

The LLM receives:
1. **Organization Profile** - Mission, focus areas, programs, demographics, geography
2. **Grant Details** - Title, funder, amount, deadline, description, eligibility

It returns structured JSON with:
- Score breakdown per dimension
- 2-3 sentence reasoning
- Brief grant summary
- Key tags (up to 5)
- Effort estimate (low/medium/high)
- Winning strategies (tips for application)

## Rule-Based Fallback

When LLM is unavailable, scoring uses:

### Mission Alignment (0-30)
- Count keyword matches from org's focus areas in grant text
- 5 points per match, max 30

### Target Population (0-20)
- Match org's target demographics against grant description
- 7 points per match, max 20

### Geographic Coverage (0-15)
- Check if org's geographic focus appears in grant
- 10 points if match, 5 if unclear

### Funding Fit (0-15)
| Amount Range | Points |
|-------------|--------|
| $100K-$2M (ideal) | 15 |
| $50K-$5M (acceptable) | 10 |
| Other | 5 |
| Unknown | 8 |

### Eligibility (0-10)
- Default: 8 points (assume eligible unless known otherwise)

### Strategic Value (0-10)
- Default: 5 points

## Cost Optimization

Target: **<$0.05 per grant analyzed**

### Token Estimates (Claude Sonnet)
- Input: ~1,500 tokens (prompt + grant data)
- Output: ~300 tokens (JSON response)
- Total: ~1,800 tokens per grant

### Pricing (Claude Sonnet 4)
- Input: $3.00 / million tokens
- Output: $15.00 / million tokens
- **Estimated cost: ~$0.009 per grant**

### Optimization Strategies
1. Pre-filter obvious mismatches (no API cost)
2. Truncate descriptions to 2,000 chars
3. Batch processing for efficiency
4. Cache org profiles between runs

## Performance Targets

| Metric | Target | Actual |
|--------|--------|--------|
| Processing time | <5 seconds | ~1-2 seconds (LLM) |
| Cost per grant | <$0.05 | ~$0.01 |
| Pre-filter rate | 20-40% | Varies by org |

## Example Output

```json
{
  "grant_id": "grant-001",
  "match_score": 87,
  "score_breakdown": {
    "mission_alignment": 28,
    "target_population": 18,
    "geographic_coverage": 12,
    "funding_fit": 15,
    "eligibility": 8,
    "strategic_value": 6
  },
  "reasoning": "This grant directly funds technology workforce development for underserved populations, perfectly aligning with Per Scholas's core mission. The $500K-$2M range fits the organization's capacity, and the national scope covers all operating locations.",
  "summary": "DOL grant supporting nonprofit technology workforce training programs for underemployed adults in urban areas. Funds software development, cybersecurity, and IT certification pathways.",
  "key_tags": ["workforce", "technology", "underserved", "federal", "training"],
  "effort_estimate": "high",
  "winning_strategies": [
    "Emphasize track record of job placement rates",
    "Highlight partnerships with major tech employers"
  ]
}
```

## Files

| File | Purpose |
|------|---------|
| `scoring_agent.py` | Main scoring agent with LLM and rule-based scoring |
| `jobs/process_grants.py` | Batch processing job for cron/on-demand |
| `tests/test_scoring.py` | Test suite with sample grants |
| `SCORING_LOGIC.md` | This documentation |

## Future Enhancements

1. **Learning from Feedback** - Adjust scores based on user saves/dismissals
2. **Historical Patterns** - Boost grants from past successful funders
3. **Competitive Analysis** - Factor in application volume/competition
4. **Proposal Success Prediction** - Model win probability based on org fit
5. **Multi-org Optimization** - Batch score across multiple orgs efficiently
