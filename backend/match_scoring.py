"""
Standalone match scoring service for grant opportunities.
Does NOT require the semantic model - safe to use on resource-constrained servers.

This service scores grants based on:
- Core keyword matching (30 pts max)
- Context keyword matching (included in core scoring)
- Funding amount alignment (15 pts max)
- Deadline feasibility (5 pts max)
- Domain relevance penalties (negative points)
- Optional: Semantic similarity with RFPs (50 pts max) - if provided

Total max score: 100 points (30 keywords + 50 semantic + 15 amount + 5 deadline)
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
        Match score from 0-100
    """
    # Core Per Scholas keywords (30 points max)
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

    # Calculate keyword score (max 30 points)
    # Require at least 2 core keywords for decent score
    if core_matches >= 2:
        keyword_score = min(30, (core_matches * 6) + (context_matches * 1.5))
    elif core_matches == 1:
        keyword_score = min(12, core_matches * 6)
    else:
        keyword_score = 0  # No core keywords = very low relevance

    # Semantic similarity with historical RFPs (50 points max - INCREASED from 30)
    # Only applied if rfp_similarities are provided
    semantic_score = 0
    if rfp_similarities:
        # Use the best similarity score - calibrated to empirical RFP self-match data
        best_similarity = max(rfp.get('similarity_score', 0) for rfp in rfp_similarities)

        # RECALIBRATED scoring curve based on actual RFP self-matching:
        # Empirical data shows RFPs match themselves at 0.82-0.97 similarity
        # 0.85+ = excellent/perfect match (45-50 pts) - same or very similar RFP
        # 0.70-0.85 = very good match (35-45 pts) - highly relevant
        # 0.55-0.70 = good match (25-35 pts) - relevant
        # 0.40-0.55 = moderate match (15-25 pts) - somewhat relevant
        # 0.25-0.40 = weak match (5-15 pts) - minimal relevance
        if best_similarity >= 0.85:
            # Perfect match territory - map 0.85-1.0 to 45-50 points
            semantic_score = min(50, int(45 + (best_similarity - 0.85) * 33))
        elif best_similarity >= 0.70:
            # Very good match - map 0.70-0.85 to 35-45 points
            semantic_score = min(45, int(35 + (best_similarity - 0.70) * 66))
        elif best_similarity >= 0.55:
            # Good match - map 0.55-0.70 to 25-35 points
            semantic_score = min(35, int(25 + (best_similarity - 0.55) * 66))
        elif best_similarity >= 0.40:
            # Moderate match - map 0.40-0.55 to 15-25 points
            semantic_score = min(25, int(15 + (best_similarity - 0.40) * 66))
        elif best_similarity >= 0.25:
            # Weak match - map 0.25-0.40 to 5-15 points
            semantic_score = min(15, int(5 + (best_similarity - 0.25) * 66))

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
    total_score = keyword_score + semantic_score + amount_score + deadline_score

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
    final_score = max(0, total_score - domain_penalty)  # Minimum 0
    # Add 10 point boost to all scores
    final_score = final_score + 10
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
    if core_matches >= 2:
        keyword_score = min(30, (core_matches * 6) + (context_matches * 1.5))
    elif core_matches == 1:
        keyword_score = min(12, core_matches * 6)
    else:
        keyword_score = 0

    semantic_score = 0
    best_similarity = 0
    if rfp_similarities:
        best_similarity = max(rfp.get('similarity_score', 0) for rfp in rfp_similarities)
        # Match the same curve as calculate_match_score (RECALIBRATED)
        if best_similarity >= 0.85:
            semantic_score = min(50, int(45 + (best_similarity - 0.85) * 33))
        elif best_similarity >= 0.70:
            semantic_score = min(45, int(35 + (best_similarity - 0.70) * 66))
        elif best_similarity >= 0.55:
            semantic_score = min(35, int(25 + (best_similarity - 0.55) * 66))
        elif best_similarity >= 0.40:
            semantic_score = min(25, int(15 + (best_similarity - 0.40) * 66))
        elif best_similarity >= 0.25:
            semantic_score = min(15, int(5 + (best_similarity - 0.25) * 66))

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

    total_before_penalty = keyword_score + semantic_score + amount_score + deadline_score
    final_score = max(0, total_before_penalty - domain_penalty)
    final_score = final_score + 10  # Add 10 point boost to all scores
    final_score = min(100, final_score)

    return {
        'final_score': final_score,
        'components': {
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
        'semantic': {
            'best_similarity': best_similarity,
            'similarity_count': len(rfp_similarities) if rfp_similarities else 0
        },
        'total_before_penalty': total_before_penalty
    }
