"""
Standalone match scoring service for grant opportunities.
Does NOT require the semantic model - safe to use on resource-constrained servers.

This service scores grants based on:
- Core keyword matching (40 pts max)
- Context keyword matching (included in core scoring)
- Funding amount alignment (15 pts max)
- Deadline feasibility (5 pts max)
- Domain relevance penalties (negative points)
- Optional: Semantic similarity with RFPs (30 pts max) - if provided
"""

from typing import Dict, Any, List


def calculate_match_score(grant: Dict[str, Any], rfp_similarities: List[Dict[str, Any]] = []) -> int:
    """
    Calculate enhanced match score for a grant opportunity.

    Args:
        grant: Grant dictionary with 'title', 'description', 'amount', etc.
        rfp_similarities: Optional list of similar RFPs with 'similarity_score' field
                         (from semantic search - only if available)

    Returns:
        Match score from 5-100
    """
    base_score = 10  # Base score

    # Core Per Scholas keywords (40 points max - most important factor)
    core_keywords = [
        'technology', 'workforce', 'training', 'education', 'stem',
        'coding', 'cyber', 'digital', 'programming', 'software',
        'computer', 'it', 'technical'
    ]

    # Secondary context keywords (must have core + context for high scores)
    context_keywords = [
        'job', 'career', 'employment', 'skills', 'certification',
        'bootcamp', 'professional'
    ]

    # Get grant text
    title_lower = grant.get('title', '').lower()
    desc_lower = grant.get('description', '').lower()
    full_text = title_lower + ' ' + desc_lower

    # Count keyword matches
    core_matches = sum(1 for keyword in core_keywords if keyword in full_text)
    context_matches = sum(1 for keyword in context_keywords if keyword in full_text)

    # Calculate keyword score
    # Require at least 2 core keywords for decent score
    if core_matches >= 2:
        keyword_score = min(40, (core_matches * 8) + (context_matches * 2))
    elif core_matches == 1:
        keyword_score = min(15, core_matches * 8)
    else:
        keyword_score = 0  # No core keywords = very low relevance

    # Semantic similarity with historical RFPs (30 points max)
    # Only applied if rfp_similarities are provided
    semantic_score = 0
    if rfp_similarities:
        # Use the best similarity score but be more conservative
        best_similarity = max(rfp.get('similarity_score', 0) for rfp in rfp_similarities)
        # Only give significant points for very high similarity (>0.7)
        if best_similarity > 0.7:
            semantic_score = min(30, int((best_similarity - 0.5) * 60))
        else:
            semantic_score = min(10, int(best_similarity * 20))

    # Funding amount alignment (15 points max)
    amount = grant.get('amount', 0)
    amount_score = 0
    if 100000 <= amount <= 2000000:  # Per Scholas typical range
        amount_score = 15
    elif 50000 <= amount <= 5000000:  # Acceptable range
        amount_score = 8
    elif amount > 0:
        amount_score = 3

    # Deadline feasibility (5 points max - less important)
    deadline_score = 5  # Default to reasonable for now

    # Calculate total score
    total_score = base_score + keyword_score + semantic_score + amount_score + deadline_score

    # Additional penalty for clearly non-relevant domains
    excluded_domains = [
        'health', 'medical', 'hospital', 'clinical',
        'agriculture', 'farming', 'rural health',
        'environmental', 'climate'
    ]
    domain_penalty = 0
    for domain in excluded_domains:
        if domain in full_text:
            domain_penalty += 20

    # Final score with penalties applied
    final_score = max(5, total_score - domain_penalty)  # Minimum 5% score
    return min(100, final_score)


def get_score_breakdown(grant: Dict[str, Any], rfp_similarities: List[Dict[str, Any]] = []) -> Dict[str, Any]:
    """
    Get detailed breakdown of how the score was calculated.
    Useful for debugging and explaining scores to users.

    Returns:
        Dictionary with score components and explanations
    """
    # Core keywords
    core_keywords = [
        'technology', 'workforce', 'training', 'education', 'stem',
        'coding', 'cyber', 'digital', 'programming', 'software',
        'computer', 'it', 'technical'
    ]
    context_keywords = [
        'job', 'career', 'employment', 'skills', 'certification',
        'bootcamp', 'professional'
    ]

    title_lower = grant.get('title', '').lower()
    desc_lower = grant.get('description', '').lower()
    full_text = title_lower + ' ' + desc_lower

    core_matches = sum(1 for keyword in core_keywords if keyword in full_text)
    context_matches = sum(1 for keyword in context_keywords if keyword in full_text)

    matched_core = [kw for kw in core_keywords if kw in full_text]
    matched_context = [kw for kw in context_keywords if kw in full_text]

    # Calculate components
    base_score = 10

    if core_matches >= 2:
        keyword_score = min(40, (core_matches * 8) + (context_matches * 2))
    elif core_matches == 1:
        keyword_score = min(15, core_matches * 8)
    else:
        keyword_score = 0

    semantic_score = 0
    if rfp_similarities:
        best_similarity = max(rfp.get('similarity_score', 0) for rfp in rfp_similarities)
        if best_similarity > 0.7:
            semantic_score = min(30, int((best_similarity - 0.5) * 60))
        else:
            semantic_score = min(10, int(best_similarity * 20))

    amount = grant.get('amount', 0)
    if 100000 <= amount <= 2000000:
        amount_score = 15
    elif 50000 <= amount <= 5000000:
        amount_score = 8
    elif amount > 0:
        amount_score = 3
    else:
        amount_score = 0

    deadline_score = 5

    excluded_domains = [
        'health', 'medical', 'hospital', 'clinical',
        'agriculture', 'farming', 'rural health',
        'environmental', 'climate'
    ]
    matched_excluded = [domain for domain in excluded_domains if domain in full_text]
    domain_penalty = len(matched_excluded) * 20

    total_before_penalty = base_score + keyword_score + semantic_score + amount_score + deadline_score
    final_score = max(5, min(100, total_before_penalty - domain_penalty))

    return {
        'final_score': final_score,
        'components': {
            'base_score': base_score,
            'keyword_score': keyword_score,
            'semantic_score': semantic_score,
            'amount_score': amount_score,
            'deadline_score': deadline_score,
        },
        'penalties': {
            'domain_penalty': domain_penalty,
            'excluded_domains_found': matched_excluded
        },
        'matches': {
            'core_keywords': matched_core,
            'context_keywords': matched_context,
            'core_count': core_matches,
            'context_count': context_matches
        },
        'total_before_penalty': total_before_penalty
    }
