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

# Keywords for Grants.gov (grant opportunities) - COMPREHENSIVE for Per Scholas
# Organized by category for maximum coverage
GRANTS_GOV_KEYWORDS = [
    # Core technology workforce development
    "technology workforce development",
    "IT workforce development",
    "digital workforce development",
    "tech workforce training",
    "information technology training",

    # Skills training programs
    "digital skills training",
    "technical skills training",
    "technology skills development",
    "digital literacy",
    "computer skills training",
    "IT skills training",

    # Specific tech domains
    "cybersecurity training",
    "software development training",
    "software engineering education",
    "web development training",
    "cloud computing training",
    "data analytics training",
    "artificial intelligence training",
    "machine learning education",
    "network administration training",
    "database management training",

    # STEM education
    "STEM education",
    "STEM workforce",
    "STEM training",
    "computer science education",
    "technology education",
    "engineering education",

    # Job training and placement
    "job training technology",
    "IT job training",
    "tech job placement",
    "career training technology",
    "vocational training technology",
    "apprenticeship technology",
    "tech apprenticeship",

    # Coding and bootcamps
    "coding bootcamp",
    "coding education",
    "programming training",
    "software coding training",

    # Certifications and credentials
    "IT certification",
    "technology certification",
    "professional certification technology",
    "industry certification",
    "CompTIA training",
    "AWS certification",
    "Microsoft certification",

    # Workforce readiness
    "workforce readiness",
    "career readiness technology",
    "job readiness training",
    "employment training technology",
    "workforce preparation",

    # Adult and continuing education
    "adult education technology",
    "continuing education technology",
    "lifelong learning technology",
    "adult learner technology",
    "retraining programs",
    "upskilling technology",
    "reskilling programs",

    # Community and demographic focus
    "underserved communities technology",
    "underrepresented minorities technology",
    "diversity in tech",
    "women in technology",
    "veterans technology training",
    "low-income technology training",
    "urban technology education",
    "minority technology education",

    # Economic development
    "economic development technology",
    "community development technology",
    "workforce innovation",
    "employment innovation",

    # Education partnerships
    "community college technology",
    "workforce development partnership",
    "education industry partnership",
    "employer partnership training",

    # Specific programs and acts
    "WIOA",
    "Workforce Innovation Opportunity Act",
    "workforce development grant",
    "workforce training grant",
    "Perkins",
    "career technical education",
    "CTE technology",

    # Employer engagement
    "employer-led training",
    "industry-driven training",
    "on-the-job training technology",
    "work-based learning technology",

    # Youth and young adults
    "youth technology training",
    "young adult technology",
    "youth employment technology",
    "opportunity youth technology",

    # Displaced workers
    "displaced worker training",
    "worker retraining",
    "dislocated worker technology",
    "transitional employment",

    # Innovation and emerging tech
    "emerging technology training",
    "innovation workforce",
    "technology innovation education",
    "future of work",

    # Specific job roles
    "help desk training",
    "IT support training",
    "technical support training",
    "systems administration",
    "DevOps training",
    "quality assurance training",
    "project management technology"
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