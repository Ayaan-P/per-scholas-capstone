"""
Centralized search keyword configuration for all grant data sources
Maintains search terms in one location for easy management
"""

# Per Scholas mission-aligned search keywords
# Each keyword targets different aspects of technology workforce development

GRANT_SEARCH_KEYWORDS = [
    # Primary mission alignment - technology workforce development
    "technology workforce development",
    "digital skills training", 
    "cybersecurity training",
    "software development education",
    
    # STEM education focus
    "STEM education",
    "STEM workforce development",
    "computer science education",
    
    # Job training and placement
    "IT job training",
    "coding bootcamp funding",
    "tech apprenticeship",
    "digital literacy training",
    
    # Workforce readiness
    "workforce readiness technology",
    "technical skills development",
    "IT certification training",
    
    # Community and social impact
    "underserved communities technology",
    "diversity in tech training",
    "urban technology education"
]

# High-priority keywords (try these first)
HIGH_PRIORITY_KEYWORDS = [
    "technology workforce development",
    "digital skills training",
    "cybersecurity training",
    "software development education",
    "STEM workforce development"
]

# Specialized keywords for different funding sources
FEDERAL_KEYWORDS = [
    "technology workforce development",
    "cybersecurity training",
    "STEM workforce development",
    "IT job training",
    "digital skills training"
]

STATE_KEYWORDS = [
    "workforce development technology",
    "digital skills training",
    "community college technology",
    "tech workforce training",
    "coding education programs"
]

# Keywords specifically for SAM.gov (procurement opportunities)
SAM_GOV_KEYWORDS = [
    "technology training services",
    "cybersecurity training services", 
    "IT workforce development",
    "digital skills training services",
    "software development training",
    "STEM education services",
    "technical training programs"
]

# Keywords for Grants.gov (grant opportunities)
GRANTS_GOV_KEYWORDS = [
    "technology workforce development",
    "STEM education",
    "digital skills training",
    "cybersecurity training", 
    "software development education",
    "IT job training",
    "coding bootcamp funding"
]

def get_keywords_for_source(source: str) -> list:
    """
    Get appropriate keywords for a specific data source
    
    Args:
        source: Data source identifier ('sam_gov', 'grants_gov', 'state', 'federal')
    
    Returns:
        List of keywords optimized for that source
    """
    keyword_mapping = {
        'sam_gov': SAM_GOV_KEYWORDS,
        'grants_gov': GRANTS_GOV_KEYWORDS,
        'federal': FEDERAL_KEYWORDS,
        'state': STATE_KEYWORDS,
        'default': HIGH_PRIORITY_KEYWORDS
    }
    
    return keyword_mapping.get(source, keyword_mapping['default'])

def get_all_keywords() -> list:
    """Get all available search keywords"""
    return GRANT_SEARCH_KEYWORDS

def get_high_priority_keywords() -> list:
    """Get high-priority keywords for initial searches"""
    return HIGH_PRIORITY_KEYWORDS