"""
Centralized grant filtering framework for all scrapers.
Provides consistent filtering logic across federal, state, and local grant sources.
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
from search_keywords import get_keywords_for_source, get_high_priority_keywords

logger = logging.getLogger(__name__)


class GrantFilter:
    """
    Centralized filtering system for grant opportunities.
    Handles status, date, eligibility, category, amount, and relevance filtering.
    """
    
    def __init__(self, source: str = 'general'):
        """
        Initialize filter with source-specific configurations.
        
        Args:
            source: Data source ('california_state', 'grants_gov', 'state', etc.)
        """
        self.source = source
        self.keywords = get_keywords_for_source(source)
        
        # Default filter settings (can be customized per source)
        self.default_filters = {
            'active_only': True,
            'future_deadlines_only': True,
            'nonprofit_eligible': True,
            'minimum_amount': 10000,  # $10K minimum
            'maximum_amount': None,   # No maximum by default
            'require_keywords': True,
            'exclude_expired': True,
            'min_deadline_days': 14   # At least 14 days to apply
        }
    
    def apply_filters(self, grants: List[Dict[str, Any]], 
                     custom_filters: Optional[Dict[str, Any]] = None,
                     limit: int = 20) -> List[Dict[str, Any]]:
        """
        Apply comprehensive filtering to a list of grants.
        
        Args:
            grants: List of grant dictionaries
            custom_filters: Override default filters
            limit: Maximum number of grants to return
            
        Returns:
            Filtered and sorted list of grants
        """
        filters = {**self.default_filters, **(custom_filters or {})}
        
        logger.info(f"[{self.source}] Filtering {len(grants)} grants with filters: {filters}")
        
        filtered_grants = []
        
        for grant in grants:
            try:
                # Apply all filter checks
                if not self._passes_filters(grant, filters):
                    continue
                    
                # Calculate match score for ranking
                if not grant.get('match_score'):
                    grant['match_score'] = self._calculate_relevance_score(grant)
                
                filtered_grants.append(grant)
                
            except Exception as e:
                logger.warning(f"[{self.source}] Error filtering grant {grant.get('id', 'unknown')}: {e}")
                continue
        
        # Sort by match score (highest first) and limit results
        filtered_grants.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        limited_grants = filtered_grants[:limit]
        
        logger.info(f"[{self.source}] Filtered to {len(limited_grants)} high-quality grants")
        
        return limited_grants
    
    def _passes_filters(self, grant: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if grant passes all filter criteria"""
        
        # Status filter
        if filters.get('active_only') and not self._is_active_status(grant):
            return False
        
        # Date filters
        if filters.get('future_deadlines_only') and not self._has_future_deadline(grant, filters.get('min_deadline_days', 0)):
            return False
        
        if filters.get('exclude_expired') and self._is_expired(grant):
            return False
        
        # Eligibility filter
        if filters.get('nonprofit_eligible') and not self._is_nonprofit_eligible(grant):
            return False
        
        # Amount filters
        if not self._meets_amount_criteria(grant, filters.get('minimum_amount'), filters.get('maximum_amount')):
            return False
        
        # Keyword relevance filter
        if filters.get('require_keywords') and not self._has_relevant_keywords(grant):
            return False
        
        # Category relevance filter (source-specific)
        if not self._is_relevant_category(grant):
            return False
        
        return True
    
    def _is_active_status(self, grant: Dict[str, Any]) -> bool:
        """Check if grant has active status"""
        status = grant.get('status', '').lower().strip()
        
        # Different sources use different status fields
        if not status:
            # Try alternative status field names
            status = grant.get('Status', '').lower().strip()
        
        if not status:
            # If no status field, assume active if we have a title
            # Grants without deadlines might be rolling/ongoing opportunities
            return bool(grant.get('title'))
        
        # Active status indicators
        active_statuses = ['active', 'open', 'posted', 'available', 'current']
        inactive_statuses = ['closed', 'expired', 'inactive', 'cancelled', 'forecasted']
        
        # Check for inactive first (more specific)
        if any(inactive in status for inactive in inactive_statuses):
            return False
        
        # Check for active indicators
        if any(active in status for active in active_statuses):
            return True
        
        # If unclear, default to active (better to include than exclude)
        return True
    
    def _has_future_deadline(self, grant: Dict[str, Any], min_days: int = 0) -> bool:
        """Check if grant has future deadline with minimum notice"""
        deadline_str = grant.get('deadline') or grant.get('ApplicationDeadline', '')
        
        if not deadline_str:
            # No deadline might mean rolling/ongoing opportunity
            return True
        
        try:
            # Parse various date formats
            deadline = self._parse_deadline(deadline_str)
            if not deadline:
                return True  # Benefit of doubt for unparseable dates
            
            min_date = datetime.now() + timedelta(days=min_days)
            return deadline > min_date
            
        except Exception as e:
            logger.debug(f"Date parsing error for '{deadline_str}': {e}")
            return True  # Benefit of doubt
    
    def _is_expired(self, grant: Dict[str, Any]) -> bool:
        """Check if grant is definitively expired"""
        deadline_str = grant.get('deadline') or grant.get('ApplicationDeadline', '')
        
        if not deadline_str:
            return False
        
        try:
            deadline = self._parse_deadline(deadline_str)
            if deadline:
                return deadline < datetime.now()
        except (ValueError, TypeError):
            pass
        
        return False
    
    def _parse_deadline(self, deadline_str: str) -> Optional[datetime]:
        """Parse deadline string to datetime object"""
        if not deadline_str:
            return None
        
        # Common date formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%m-%d-%Y',
            '%Y/%m/%d'
        ]
        
        # Clean the string
        deadline_str = str(deadline_str).strip()
        
        for fmt in formats:
            try:
                return datetime.strptime(deadline_str[:19], fmt)
            except (ValueError, TypeError):
                continue
        
        return None
    
    def _is_nonprofit_eligible(self, grant: Dict[str, Any]) -> bool:
        """Check if grant is eligible for nonprofit organizations"""
        # Check applicant type fields
        applicant_fields = ['ApplicantType', 'applicant_type', 'eligibility', 'requirements']
        
        for field in applicant_fields:
            applicant_text = grant.get(field, '')
            if isinstance(applicant_text, list):
                applicant_text = ' '.join(applicant_text)
            applicant_text = str(applicant_text).lower()
            
            if applicant_text:
                # Positive indicators
                if any(indicator in applicant_text for indicator in ['nonprofit', 'non-profit', '501(c)', 'charitable']):
                    return True
                
                # If it explicitly excludes nonprofits
                if any(exclude in applicant_text for exclude in ['profit only', 'for-profit only', 'private company only']):
                    return False
        
        # If unclear, default to eligible (Per Scholas is a nonprofit)
        return True
    
    def _meets_amount_criteria(self, grant: Dict[str, Any], min_amount: Optional[int], max_amount: Optional[int]) -> bool:
        """Check if grant amount meets criteria"""
        amount = grant.get('amount', 0)
        
        if not isinstance(amount, (int, float)):
            try:
                amount = int(amount)
            except (ValueError, TypeError):
                # If amount is unclear, don't filter out (could be significant)
                return True
        
        if min_amount and amount > 0 and amount < min_amount:
            return False
        
        if max_amount and amount > max_amount:
            return False
        
        return True
    
    def _has_relevant_keywords(self, grant: Dict[str, Any]) -> bool:
        """Check if grant contains relevant keywords"""
        title = grant.get('title', '').lower()
        description = grant.get('description', '').lower()
        full_text = f"{title} {description}"
        
        # Use centralized keywords
        keywords = get_high_priority_keywords()
        
        # Check for any keyword matches
        for keyword in keywords:
            if keyword.lower() in full_text:
                return True
        
        # Also check individual terms from compound keywords
        important_terms = [
            'technology', 'workforce', 'training', 'education', 'stem',
            'coding', 'cyber', 'digital', 'programming', 'software',
            'computer', 'it', 'technical', 'skills'
        ]
        
        matches = sum(1 for term in important_terms if term in full_text)
        
        # Require at least 2 relevant terms for inclusion
        return matches >= 2
    
    def _is_relevant_category(self, grant: Dict[str, Any]) -> bool:
        """Check if grant category is relevant to Per Scholas mission"""
        category_fields = ['Categories', 'category', 'Type', 'type', 'Purpose', 'purpose']
        
        relevant_categories = [
            'education', 'training', 'workforce', 'employment', 'stem',
            'technology', 'digital', 'computer', 'cyber', 'skills',
            'job', 'career', 'professional', 'technical'
        ]
        
        # Categories to avoid
        irrelevant_categories = [
            'agriculture', 'farming', 'medical', 'health care', 'clinical',
            'environmental cleanup', 'climate change', 'arts only',
            'sports only', 'recreation only'
        ]
        
        category_text = ''
        for field in category_fields:
            field_value = grant.get(field, '')
            if isinstance(field_value, list):
                field_value = ' '.join(field_value)
            category_text += str(field_value).lower() + ' '
        
        # Check for irrelevant categories first
        if any(irrelevant in category_text for irrelevant in irrelevant_categories):
            # Only exclude if ONLY irrelevant (some grants span multiple areas)
            relevant_count = sum(1 for relevant in relevant_categories if relevant in category_text)
            if relevant_count == 0:
                return False
        
        # Check for relevant categories or default to include
        if not category_text.strip():
            return True  # No category info, don't exclude
        
        return any(relevant in category_text for relevant in relevant_categories)
    
    def _calculate_relevance_score(self, grant: Dict[str, Any]) -> int:
        """Calculate relevance score using centralized match scoring"""
        try:
            from match_scoring import calculate_match_score
            
            # Get semantic similarities if available
            rfp_similarities = []
            try:
                from semantic_service import SemanticService
                semantic_service = SemanticService()
                grant_text = f"{grant.get('title', '')} {grant.get('description', '')}"
                rfp_similarities = semantic_service.find_similar_rfps(grant_text, limit=3)
            except Exception as e:
                logger.debug(f"Semantic scoring unavailable: {e}")
            
            return calculate_match_score(grant, rfp_similarities)
            
        except Exception as e:
            logger.warning(f"Match scoring failed: {e}")
            return 50  # Default moderate score


# Convenience functions for common filtering scenarios

def filter_california_grants(grants: List[Dict[str, Any]], limit: int = 20) -> List[Dict[str, Any]]:
    """Filter California grants with state-specific optimizations"""
    filter_engine = GrantFilter('california_state')
    
    # California-specific filter settings
    ca_filters = {
        'active_only': True,
        'future_deadlines_only': True,
        'nonprofit_eligible': True,
        'minimum_amount': 25000,  # Higher minimum for CA
        'require_keywords': True,
        'min_deadline_days': 21   # More time needed for CA grants
    }
    
    return filter_engine.apply_filters(grants, ca_filters, limit)


def filter_state_grants(grants: List[Dict[str, Any]], source: str = 'state', limit: int = 20) -> List[Dict[str, Any]]:
    """Filter state grants with general state optimizations"""
    filter_engine = GrantFilter(source)
    
    # General state filter settings
    state_filters = {
        'active_only': True,
        'future_deadlines_only': True,
        'nonprofit_eligible': True,
        'minimum_amount': 10000,
        'require_keywords': True,
        'min_deadline_days': 14
    }
    
    return filter_engine.apply_filters(grants, state_filters, limit)


def filter_federal_grants(grants: List[Dict[str, Any]], source: str = 'grants_gov', limit: int = 20) -> List[Dict[str, Any]]:
    """Filter federal grants with federal-specific optimizations"""
    filter_engine = GrantFilter(source)
    
    # Federal filter settings (usually higher amounts, longer timelines)
    federal_filters = {
        'active_only': True,
        'future_deadlines_only': True,
        'nonprofit_eligible': True,
        'minimum_amount': 50000,  # Higher minimum for federal
        'require_keywords': True,
        'min_deadline_days': 30   # Federal grants need more prep time
    }
    
    return filter_engine.apply_filters(grants, federal_filters, limit)